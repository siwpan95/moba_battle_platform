#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""战斗模拟器 —— 管理单场对战的完整流程，支持 1-18 级。

A3 消费路线（坐实 D&D 5e 框架）：
  • 伤害来自技能自带 damage 骰（BattleEngine.skill_raw_damage），不再用写死倍率
  • 技能 effects（控制/护盾/减伤/治疗/吸血/持续伤害/斩杀/真伤/增益/易伤…）真正生效
  • 带 saving_throw 的技能让防御方掷豁免（半伤/无效）
详见 ADR-003 消费路径与交付报告。
"""

import random
from .engine import BattleEngine
from .config import HP_SCALE, DAMAGE_SCALE, ROLE_NAME_CN
from .mechanics import categorize_effect, roll_saving_throw

# 伤害放大系数：把数据骰期望（~15）放大到与 HP 量级匹配（lv1≈18 / lv18≈78 单技能）
DND_DAMAGE_SCALE = 5.5
# 增益/易伤/暴击/反弹数值
BUFF_BONUS_PCT = 15
VULN_BONUS_PCT = 20
CRIT_BONUS = 0.15
REFLECT_PCT = 15
DOT_DEFAULT = 6  # 未给 dmg_per_turn 时每回合默认持续伤害


class BattleSimulator:
    """管理单场对战的完整流程，支持 1-18 级"""

    def __init__(self, card1: dict, card2: dict, level1: int = 1, level2: int = 1, rng=None):
        self.card1 = card1
        self.card2 = card2
        self.hero1 = card1["hero"]["name"]
        self.hero2 = card2["hero"]["name"]
        self.level1 = max(1, min(18, level1))
        self.level2 = max(1, min(18, level2))

        self.stats1 = self._calc_stats_for_level(card1, self.level1)
        self.stats2 = self._calc_stats_for_level(card2, self.level2)
        self.attrs1 = card1["attributes"]
        self.attrs2 = card2["attributes"]

        self.skills1 = card1.get("skills", [])
        self.skills2 = card2.get("skills", [])

        self.hp1 = self.stats1["hp"]
        self.hp2 = self.stats2["hp"]
        self.max_hp1 = self.hp1
        self.max_hp2 = self.hp2

        self.cd1 = [0, 0, 0, 0]
        self.cd2 = [0, 0, 0, 0]
        self.skill_cooldowns = [0, 1, 2, 4]

        self.turn = 1
        self.logs = []
        self.winner = None  # 0|1|2，避免胜利后重复调用 execute_turn

        # 超时判负：回合数硬上限，保证任何对局都必然终结（杜绝无限循环）。
        # 需要更长/更短的对局可在构造后直接改写 sim.max_rounds。
        self.max_rounds = 120
        self.rounds = 0

        # A3 状态系统
        self.rng = rng or random.Random()
        self.timed1 = []
        self.timed2 = []

        # 按攻击方自身等级缩放伤害（修跨级 avg_level 偏置）
        self.damage_scale1 = 1.0 + (self.level1 - 1) * 0.20
        self.damage_scale2 = 1.0 + (self.level2 - 1) * 0.20
        # 随机先手（修 P1 恒先手偏置 63.3%）
        self.first_mover = 1 if self.rng.random() < 0.5 else 2

    @property
    def is_over(self) -> bool:
        """比赛是否已结束（与 winner 配套，替换中文日志解析）。"""
        return self.winner is not None

    # ── 属性/状态辅助 ──
    @staticmethod
    def _calc_stats_for_level(card: dict, level: int) -> dict:
        lv1 = card["stats_lv1"]
        lv18 = card["stats_lv18"]
        growth = card.get("growth_per_level", {})
        t = (level - 1) / 17.0

        def _lerp(key, default_growth=0):
            v1 = lv1.get(key, 0)
            v18 = lv18.get(key, 0)
            if abs(v18 - v1) < 0.01:
                g = growth.get(key, default_growth)
                return round(v1 + g * (level - 1))
            return round(v1 + (v18 - v1) * t)

        sv1 = lv1.get("save_bonuses", {})
        sv18 = lv18.get("save_bonuses", {})
        save_bonuses = {}
        for ab in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]:
            s1 = sv1.get(ab, 0)
            s18 = sv18.get(ab, 0)
            save_bonuses[ab] = round(s1 + (s18 - s1) * t) if s18 != s1 else s1

        stats = {
            "level": level,
            "hp": _lerp("hp", growth.get("hp", 8)),
            "ac": _lerp("ac"),
            "physical_atk": _lerp("physical_atk", growth.get("atk", 2.5)),
            "magic_power": _lerp("magic_power", growth.get("ap", 1.5)),
            "prof_bonus": lv1.get("prof_bonus", 2),
            "atk_speed_pct": lv1.get("atk_speed_pct", 0),
            "crit_chance": lv1.get("crit_chance", lv1.get("crit_pct", 0)),
            "crit_damage": lv1.get("crit_damage", 150.0),
            "cdr_pct": lv1.get("cdr_pct", 0),
            "heal_bonus_pct": lv1.get("heal_bonus_pct", 0),
            "cc_resist_pct": lv1.get("cc_resist_pct", 0),
            "save_bonuses": save_bonuses,
        }
        if lv1.get("hp", 999) < 100 and "hp_dnd_raw" not in lv1:
            stats["hp"] = int(stats["hp"] * HP_SCALE)
        return stats

    def _attr_mods(self, attrs):
        return {ab: (attrs.get(ab) or {}).get("modifier", 0)
                for ab in ("STR", "DEX", "CON", "INT", "WIS", "CHA")}

    def _timed(self, side):
        return self.timed1 if side == 1 else self.timed2

    def _controlled(self, side):
        return any(t["kind"] == "control" for t in self._timed(side))

    def _has(self, side, kind):
        return any(t["kind"] == kind for t in self._timed(side))

    def _sum(self, side, kind):
        return sum(t.get("value", 0) for t in self._timed(side) if t["kind"] == kind)

    def _add(self, side, kind, turns, value=0):
        self._timed(side).append(
            {"kind": kind, "turns": max(1, int(turns or 1)), "value": value})

    def _add_shield(self, side, turns, value):
        self._add(side, "shield", turns, value)

    def _shield_pool(self, side):
        return sum(t["value"] for t in self._timed(side) if t["kind"] == "shield")

    def _absorb_shield(self, side, amount):
        if amount <= 0:
            return
        for t in self._timed(side):
            if t["kind"] == "shield" and amount > 0:
                take = min(t["value"], amount)
                t["value"] -= take
                amount -= take

    def _decay_timed(self, side):
        tl = self._timed(side)
        for t in tl:
            t["turns"] -= 1
        self._timed(side)[:] = [t for t in tl if t["turns"] > 0]

    def _effect_value(self, eff, attrs, side):
        v = eff.get("value")
        # 如果 value 是骰子表达式字符串（如 "2d8+WIS"），走 roll_dice_expr 解析
        if isinstance(v, str):
            from .mechanics import roll_dice_expr
            v = roll_dice_expr(v, self._attr_mods(attrs), self.rng)
        if v is None:
            vf = eff.get("value_formula")
            if vf:
                from .mechanics import roll_dice_expr
                v = roll_dice_expr(vf, self._attr_mods(attrs), self.rng)
        if v is None or v == 0:
            v = int((self.max_hp1 if side == 1 else self.max_hp2) * 0.1)
        return max(1, int(v))

    # ── 技能辅助 ──
    def _get_skill(self, card, idx):
        skills = card.get("skills", [])
        if isinstance(skills, dict):
            return None
        if isinstance(skills, list) and idx < len(skills):
            return skills[idx]
        return None

    def _skill_name(self, card, idx):
        sk = self._get_skill(card, idx)
        if sk is None:
            return ["技能一", "技能二", "技能三", "大招"][idx]
        if isinstance(sk, dict):
            return sk.get("name", f"技能{idx+1}")
        return sk.split(":")[0] if ":" in sk else sk

    def _skill_desc(self, card, idx):
        sk = self._get_skill(card, idx)
        if sk is None:
            return f"技能{idx+1}"
        if isinstance(sk, dict):
            return sk.get("description", sk.get("name", f"技能{idx+1}"))
        s = str(sk)
        if ":" in s:
            return s.split(":", 1)[1].strip()
        return s

    def _skill_cooldown(self, card, idx) -> int:
        sk = self._get_skill(card, idx)
        if isinstance(sk, dict):
            return sk.get("cooldown", self.skill_cooldowns[idx])
        return self.skill_cooldowns[idx]

    # ── 回合流程 ──
    def execute_turn(self) -> list:
        if self.winner is not None:
            return []  # 比赛已结束，幂等返回
        self.rounds += 1
        logs = []
        logs.extend(self._tick_dot(1))
        logs.extend(self._tick_dot(2))
        if self.hp2 <= 0:
            self.winner = 1
            logs.append(f"💀 {self.hero2} 被击败！")
            logs.append(f"🏆 {self.hero1} 获得胜利！")
            self._end_turn()
            return logs
        if self.hp1 <= 0:
            self.winner = 2
            logs.append(f"💀 {self.hero1} 被击败！")
            logs.append(f"🏆 {self.hero2} 获得胜利！")
            self._end_turn()
            return logs

        # 随机先手（修 P1 先手偏置 63.3%）
        side_a, side_b = (1, 2) if self.first_mover == 1 else (2, 1)

        logs.extend(self._hero_act(side_a, self.card1 if side_a == 1 else self.card2,
                                   self.stats1 if side_a == 1 else self.stats2,
                                   self.attrs1 if side_a == 1 else self.attrs2,
                                   self.skills1 if side_a == 1 else self.skills2,
                                   self.cd1 if side_a == 1 else self.cd2))
        if self.hp2 <= 0:
            self.winner = 1
            logs.append(f"💀 {self.hero2} 被击败！")
            logs.append(f"🏆 {self.hero1} 获得胜利！")
            self._end_turn()
            return logs
        if self.hp1 <= 0:
            self.winner = 2
            logs.append(f"💀 {self.hero1} 被击败！")
            logs.append(f"🏆 {self.hero2} 获得胜利！")
            self._end_turn()
            return logs

        logs.extend(self._hero_act(side_b, self.card2 if side_b == 2 else self.card1,
                                   self.stats2 if side_b == 2 else self.stats1,
                                   self.attrs2 if side_b == 2 else self.attrs1,
                                   self.skills2 if side_b == 2 else self.skills1,
                                   self.cd2 if side_b == 2 else self.cd1))
        if self.hp1 <= 0:
            self.winner = 2
            logs.append(f"💀 {self.hero1} 被击败！")
            logs.append(f"🏆 {self.hero2} 获得胜利！")
            self._end_turn()
            return logs
        if self.hp2 <= 0:
            self.winner = 1
            logs.append(f"💀 {self.hero2} 被击败！")
            logs.append(f"🏆 {self.hero1} 获得胜利！")
            self._end_turn()
            return logs

        if self.winner is None and self.rounds >= self.max_rounds:
            logs.extend(self._judge_timeout())

        self._end_turn()
        return logs

    def _judge_timeout(self) -> list:
        """超时判负：达到回合上限仍未分胜负时，按当前血量比例裁定胜方。

        血量比例高者胜；完全相同则判平局（winner=0）。
        存在此裁定后，execute_turn 最多被有效执行 max_rounds 次，
        任何对局（含双辅助互奶的高治疗量对局）都不会无限循环。
        """
        r1 = (self.hp1 / self.max_hp1) if self.max_hp1 else 0.0
        r2 = (self.hp2 / self.max_hp2) if self.max_hp2 else 0.0
        logs = [
            f"⏱️ 超时判负 | 达到回合上限 {self.max_rounds}，按血量比例裁定："
            f"{self.hero1} {self.hp1}/{self.max_hp1}({r1:.1%}) vs "
            f"{self.hero2} {self.hp2}/{self.max_hp2}({r2:.1%})"
        ]
        if r1 > r2:
            self.winner = 1
            logs.append(f"🏆 {self.hero1} 血量比例领先，超时判负获胜！")
        elif r2 > r1:
            self.winner = 2
            logs.append(f"🏆 {self.hero2} 血量比例领先，超时判负获胜！")
        else:
            self.winner = 0
            logs.append("🤝 双方血量比例相同，超时判负为平局！")
        return logs

    def _end_turn(self):
        """回合收尾：CD递减、timed衰减、回合计数递增。"""
        for i in range(4):
            if self.cd1[i] > 0:
                self.cd1[i] -= 1
            if self.cd2[i] > 0:
                self.cd2[i] -= 1
        self._decay_timed(1)
        self._decay_timed(2)
        self.turn += 1

    def _tick_dot(self, side) -> list:
        logs = []
        name = self.hero1 if side == 1 else self.hero2
        for t in self._timed(side):
            if t["kind"] != "dot":
                continue
            d = max(1, int(t.get("value", DOT_DEFAULT)))  # _add 写入 key="value"，此处对齐
            if side == 1:
                self.hp1 = max(0, self.hp1 - d)
            else:
                self.hp2 = max(0, self.hp2 - d)
            remain = self.hp1 if side == 1 else self.hp2
            logs.append(f"第{self.turn}回合 | {name} 持续伤害 {d}点（剩余{remain}）")
        return logs

    def _hero_act(self, side, card, stats, attrs, skills, cds) -> list:
        """英雄单回合行动编排：选技能 → 结算伤害 → 施加效果。

        原为 199 行单体方法（圈复杂度过高），按 ADR-003 消费路线拆为：
          - _choose_skill          : AI 选技能
          - _extract_instant_flags : 提取斩杀/真伤标志
          - _resolve_damage        : 伤害结算（骰子→减伤→暴击→豁免→斩杀→护盾→扣血）
          - _apply_effects         : 20 类 effects 施加
        """
        logs = []
        hero_name = card["hero"]["name"]
        role = card.get("game", {}).get("universal_role", "fighter")
        role_cn = ROLE_NAME_CN.get(role, role)
        enemy_side = 2 if side == 1 else 1
        enemy_stats = self.stats2 if side == 1 else self.stats1
        enemy_attrs = self.attrs2 if side == 1 else self.attrs1

        if self._controlled(side):
            logs.append(f"第{self.turn}回合 | {hero_name}({role_cn}) 被控制，无法行动！")
            return logs

        skill_idx = self._choose_skill(cds, len(skills))
        skill = self._get_skill(card, skill_idx)
        skill_name = self._skill_name(card, skill_idx)
        skill_desc = self._skill_desc(card, skill_idx)
        cds[skill_idx] = self._skill_cooldown(card, skill_idx)

        if isinstance(skill, dict) and skill.get("type") == "法术":
            is_magic = True
        elif isinstance(skill, dict) and skill.get("type") == "物理":
            is_magic = False
        else:
            is_magic = (role == "mage")

        execute_th, true_dmg = self._extract_instant_flags(skill)

        dmg = self._resolve_damage(
            side, card, attrs, skill, skill_idx, skill_desc, role_cn, is_magic,
            execute_th, true_dmg, enemy_side, enemy_stats, enemy_attrs, cds, logs)

        self._apply_effects(
            side, card, stats, attrs, skill, dmg, hero_name,
            enemy_side, enemy_attrs, logs)

        return logs

    def _choose_skill(self, cds, n_skills: int = 4) -> int:
        """AI 选技能：优先大招(50%) → 按权重抽取可用技能。"""
        n = max(1, n_skills)
        available = [i for i in range(n) if cds[i] <= 0]
        if not available:
            available = [0]
        weights = {0: 40, 1: 30, 2: 20}
        ult = n - 1
        if ult in available and self.rng.random() < 0.5:
            return ult
        return self.rng.choices(
            available, weights=[weights.get(i, 20) for i in available])[0]

    @staticmethod
    def _extract_instant_flags(skill):
        """第一遍遍历 effects，提取瞬时标志（斩杀阈值 / 是否真伤）。"""
        execute_th = None
        true_dmg = False
        for eff in ((skill or {}).get("effects") or []):
            cat = categorize_effect(eff)
            if cat == "execute":
                raw = eff.get("threshold", 30)
                try:
                    execute_th = float(raw)
                except (ValueError, TypeError):
                    execute_th = 30
                    # 非数值 threshold（如 "HP<20%"）告警但不崩溃
                    if isinstance(raw, str):
                        pass  # 静默回退，避免日志噪音
            elif cat == "true_dmg":
                true_dmg = True
        return execute_th, true_dmg

    def _resolve_damage(self, side, card, attrs, skill, skill_idx, skill_desc,
                        role_cn, is_magic, execute_th, true_dmg,
                        enemy_side, enemy_stats, enemy_attrs, cds, logs) -> int:
        """结算技能伤害：骰子 → 减伤 → 暴击 → 豁免 → 斩杀 → 减/易/增伤 → 护盾 → 扣血。"""
        hero_name = card["hero"]["name"]
        raw = BattleEngine.skill_raw_damage(skill, attrs, self.rng)

        if raw <= 0:
            logs.append(f"第{self.turn}回合 | {hero_name}({role_cn}) 释放【{skill_desc}】（无伤害，施放效果）")
            return 0

        enemy_ac_or_wis = (enemy_stats["ac"] if not is_magic
                           else enemy_stats["save_bonuses"].get("WIS", 0))
        dm = BattleEngine.apply_mitigation(raw, enemy_ac_or_wis, is_magic)
        crit_chance = BattleEngine.calc_crit_chance(self._dex_mod(card)) + self._sum(side, "crit")
        crit_chance = min(0.95, crit_chance)
        is_crit = self.rng.random() < crit_chance
        crit_mark = ""
        if is_crit:
            crit_mult = BattleEngine.crit_damage_multiplier(self._dex_mod(card))
            dm["final"] = round(dm["final"] * crit_mult, 1)
            crit_mark = "💥暴击! "
        final = dm["final"] * DAMAGE_SCALE * (self.damage_scale1 if side == 1 else self.damage_scale2) * DND_DAMAGE_SCALE
        dmg = int(max(1, final))

        # 防御方豁免
        on_save = None
        st = skill.get("saving_throw") if isinstance(skill, dict) else None
        if st:
            enemy_mods = self._attr_mods(enemy_attrs)
            enemy_mods["_prof"] = enemy_stats.get("prof_bonus", 2)
            on_save = roll_saving_throw(st, enemy_mods, self.rng)
        if on_save == "无效":
            dmg = 0
        elif on_save == "半伤":
            dmg = dmg // 2

        # 斩杀
        if execute_th is not None:
            enemy_hp_now = self.hp2 if side == 1 else self.hp1
            enemy_max = self.max_hp2 if side == 1 else self.max_hp1
            if enemy_max > 0 and enemy_hp_now / enemy_max * 100 < execute_th:
                dmg *= 2
                logs.append(f"  ⚔️ 斩杀触发！({enemy_hp_now}/{enemy_max})")

        # 减伤 / 易伤 / 增伤
        if not true_dmg and self._has(enemy_side, "reduce"):
            dmg = int(dmg * 0.5)
        if not true_dmg:
            dmg = int(dmg * (1 + self._sum(enemy_side, "vuln") / 100.0))
        dmg = int(dmg * (1 + self._sum(side, "bonus") / 100.0))

        # 护盾吸收
        if not true_dmg:
            pool = self._shield_pool(enemy_side)
            absorbed = min(dmg, pool)
            if absorbed > 0:
                self._absorb_shield(enemy_side, absorbed)
                dmg -= absorbed
                logs.append(f"  🛡️ 护盾吸收 {absorbed}点")
        dmg = max(0, dmg)

        if side == 1:
            self.hp2 = max(0, self.hp2 - dmg)
            remain = self.hp2
            target = self.hero2
        else:
            self.hp1 = max(0, self.hp1 - dmg)
            remain = self.hp1
            target = self.hero1

        is_skill = skill_idx > 0
        skill_mark = f"【{skill_desc}】" if is_skill else "普攻"
        log = f"第{self.turn}回合 | {hero_name}({role_cn}) {skill_mark} → {target}"
        log += f" | {crit_mark}{('法术' if is_magic else '物理')}伤害 {dmg}点"
        if on_save:
            log += f" | 豁免:{on_save}"
        log += f" | {target} 剩余生命:{remain}"
        if cds[skill_idx] > 0:
            log += f" | 冷却:{cds[skill_idx]}回合"
        logs.append(log)
        return dmg

    def _apply_effects(self, side, card, stats, attrs, skill, dmg, hero_name,
                       enemy_side, enemy_attrs, logs) -> None:
        """第二遍遍历 effects，施加 20 类持续/瞬时效果（控制/护盾/减伤/治疗/吸血…）。"""
        for eff in ((skill or {}).get("effects") or []):
            cat = categorize_effect(eff)
            dur = eff.get("duration", 1) or 1
            if cat == "control":
                if self._has(enemy_side, "immune"):
                    logs.append(f"  🛡️ {self.hero2 if side==1 else self.hero1} 免疫控制")
                    continue
                cc = stats.get("cc_resist_pct", 0) or 0
                turns = max(1, int(dur) - int(cc / 50))
                self._add(enemy_side, "control", turns)
                tgt = self.hero2 if side == 1 else self.hero1
                logs.append(f"  🔒 {tgt} 被控制 {turns} 回合（{eff.get('type')}）")
            elif cat == "shield":
                v = self._effect_value(eff, attrs, side)
                self._add_shield(side, dur, v)
                logs.append(f"  🛡️ {hero_name} 获得护盾 {v}点")
            elif cat == "reduce":
                self._add(side, "reduce", dur)
                logs.append(f"  🛡️ {hero_name} 减伤生效")
            elif cat == "heal":
                v = self._effect_value(eff, attrs, side)
                if side == 1:
                    before = self.hp1
                    self.hp1 = min(self.max_hp1, self.hp1 + v)
                    healed = self.hp1 - before
                else:
                    before = self.hp2
                    self.hp2 = min(self.max_hp2, self.hp2 + v)
                    healed = self.hp2 - before
                logs.append(f"  💚 {hero_name} 恢复 {healed}点")
            elif cat == "lifesteal":
                pct = eff.get("value", 30) or 30
                heal = int(dmg * pct / 100)
                if heal > 0:
                    if side == 1:
                        self.hp1 = min(self.max_hp1, self.hp1 + heal)
                    else:
                        self.hp2 = min(self.max_hp2, self.hp2 + heal)
                    logs.append(f"  💚 {hero_name} 吸血恢复 {heal}点")
            elif cat == "dot":
                from .mechanics import roll_dice_expr
                per = eff.get("dmg_per_turn")
                if per:
                    per = roll_dice_expr(per, self._attr_mods(enemy_attrs), self.rng)
                else:
                    per = DOT_DEFAULT
                self._add(enemy_side, "dot", dur, int(per))
                tgt = self.hero2 if side == 1 else self.hero1
                logs.append(f"  🔥 {tgt} 陷入持续伤害（{per}/回合，{dur}回合）")
            elif cat in ("buff", "accel"):
                self._add(side, "bonus", dur, BUFF_BONUS_PCT)
                logs.append(f"  ⬆️ {hero_name} 增益（伤害+{BUFF_BONUS_PCT}%）")
            elif cat in ("sunder", "vuln"):
                self._add(enemy_side, "vuln", dur, VULN_BONUS_PCT)
                tgt = self.hero2 if side == 1 else self.hero1
                logs.append(f"  ⬇️ {tgt} 易伤（受伤+{VULN_BONUS_PCT}%）")
            elif cat == "crit":
                self._add(side, "crit", dur, CRIT_BONUS)
                logs.append(f"  ⬆️ {hero_name} 暴击率+{int(CRIT_BONUS*100)}%")
            elif cat == "reflect":
                self._add(side, "bonus", dur, REFLECT_PCT)
                logs.append(f"  ↩️ {hero_name} 反弹/增伤生效")
            elif cat == "immune":
                self._add(side, "immune", dur)
                logs.append(f"  🛡️ {hero_name} 免疫控制")
            elif cat == "cleanse":
                tl = self._timed(side)
                self._timed(side)[:] = [t for t in tl
                                        if t["kind"] not in ("control", "dot", "vuln")]
                logs.append(f"  ✨ {hero_name} 净化负面效果")
            elif cat == "revive":
                logs.append(f"  💀 {hero_name} 触发复活效果（演练：记日志）")
            elif cat == "slow":
                self._add(enemy_side, "vuln", dur, VULN_BONUS_PCT)
                tgt = self.hero2 if side == 1 else self.hero1
                logs.append(f"  🐢 {tgt} 被减速（受伤+{VULN_BONUS_PCT}%）")
            else:  # aoe / invis / flavor
                logs.append(f"  ✦ D&D效果：{eff.get('type')}（{eff.get('desc','')}）")

    # ── 属性取值器（保留供其它模块/测试使用）──
    def _dex_mod(self, card):
        return card["attributes"]["DEX"]["modifier"]
