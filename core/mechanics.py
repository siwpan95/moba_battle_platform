#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D&D 5e 机制处理器（A3 消费路线核心）。

把技能 effects / saving_throw 真正接入战斗。本模块以纯函数为主，便于单测，
且不依赖 simulator / engine（避免循环依赖）；simulator 负责维护状态并调用本模块。

消费的数据结构（来自 core/schema.skill，已存在于 1659 张角色卡）：
    damage: {dice_count, dice_size, bonus_attr, type}
    effects: [ {type, target(自身/敌方), duration, value?, value_formula?, desc} ]
    saving_throw: {attr, dc_formula, on_save(半伤/无效/部分)}
    aoe_radius: number

注意：真实数据里 effect.type 是中英混用、同义多词（stun/眩晕/knockback/击退…），
因此本模块用「别名归一表」把它们收敛到受控的机制类别，未识别的归为 flavor（仅记日志）。
"""

from __future__ import annotations

import random
import re
from typing import Any, Dict, List, Optional

__all__ = [
    "roll_dice", "roll_dice_expr", "categorize_effect",
    "parse_dc", "roll_saving_throw",
    "CATEGORY_CONTROL", "CATEGORY_SLOW", "CATEGORY_FLAVOR",
]


# ── 机制类别别名表（真实数据里出现的各种写法 → 归一类别）──
_CONTROL = {"stun", "眩晕", "hold", "束缚", "禁锢", "prone", "倒地", "击飞", "麻痹",
            "石化", "震慑", "沉默", "魅惑", "恐惧", "混乱", "暗示", "制服", "冻结",
            "控制", "knockback", "击退", "干扰", "压制"}
_SLOW = {"slow", "减速", "致盲", "目盲"}                     # 弱化（伤害减半）
_SHIELD = {"shield", "护盾"}
_REDUCE = {"减伤", "防御"}                                   # 自身受伤减半
_HEAL = {"heal", "治疗", "回复", "回血"}
_LIFESTEAL = {"吸血", "lifesteal"}
_DOT = {"bleed", "灼烧", "中毒", "burn", "poison", "持续伤害", "痛苦", "重伤",
        "剧毒", "dot", "重创"}                                # 持续伤害
_EXECUTE = {"execute", "处决", "斩杀"}                        # 斩杀（低血翻倍）
_TRUEDMG = {"pierce", "真实伤害", "穿透", "true_damage"}     # 无视减伤/护盾
_BUFF = {"buff", "增益", "强化", "附魔", "攻击增益", "狂暴", "增援"}  # 自身增伤
_ACCEL = {"加速", "dash", "攻速强化", "冲锋", "accel", "haste"}     # 自身增伤(小)
_SUNDER = {"sunder", "破甲"}                                 # 敌方受伤+
_VULN = {"mark", "标记", "vuln", "易伤"}                     # 敌方受伤+
_CRIT = {"crit", "暴击", "暴击强化"}                          # 暴击率+
_REFLECT = {"reflect", "反弹"}                               # 受击反伤
_IMMUNE = {"immune", "免疫", "免疫控制"}                      # 免疫控制
_INVIS = {"invis", "隐身", "隐形", "潜行"}                    # 仅日志
_CLEANSE = {"cleanse", "净化", "驱散"}                        # 清负面
_REVIVE = {"revive", "复活"}                                  # 特殊
_AOE = {"aoe", "范围攻击"}                                    # 仅日志

_CATEGORY_TABLES = [
    (_CONTROL, "control"), (_SLOW, "slow"), (_SHIELD, "shield"),
    (_REDUCE, "reduce"), (_HEAL, "heal"), (_LIFESTEAL, "lifesteal"),
    (_DOT, "dot"), (_EXECUTE, "execute"), (_TRUEDMG, "true_dmg"),
    (_BUFF, "buff"), (_ACCEL, "accel"), (_SUNDER, "sunder"),
    (_VULN, "vuln"), (_CRIT, "crit"), (_REFLECT, "reflect"),
    (_IMMUNE, "immune"), (_INVIS, "invis"), (_CLEANSE, "cleanse"),
    (_REVIVE, "revive"), (_AOE, "aoe"),
]

CATEGORY_CONTROL = "control"
CATEGORY_SLOW = "slow"
CATEGORY_FLAVOR = "flavor"


def categorize_effect(eff: Any) -> str:
    """把 effect.type 归一为受控机制类别；未识别 → 'flavor'（仅记日志）。"""
    if not isinstance(eff, dict):
        return CATEGORY_FLAVOR
    t = eff.get("type")
    if not t:
        return CATEGORY_FLAVOR
    t = str(t).strip().lower()
    for table, name in _CATEGORY_TABLES:
        if t in table:
            return name
    return CATEGORY_FLAVOR


# ── 骰子 ──
def roll_dice(count: int, size: int, rng: Any = random) -> int:
    """掷 count 颗 size 面骰，返回总和。count<=0 或 size<=0 返回 0。"""
    count = max(0, int(count))
    size = max(1, int(size))
    return sum(rng.randint(1, size) for _ in range(count))


_DICE_RE = re.compile(r"(\d+)d(\d+)", re.I)


def roll_dice_expr(expr: Any, attr_mods: Dict[str, int], rng: Any = random) -> int:
    """解析 "1d8+WIS" 这类表达式并掷骰。属性名替换为 attr_mods 的值。"""
    if not expr:
        return 0
    s = str(expr)
    for ab in ("STR", "DEX", "CON", "INT", "WIS", "CHA"):
        s = re.sub(r"\b" + ab + r"\b", str(attr_mods.get(ab, 0)), s, flags=re.I)
    s = _DICE_RE.sub(lambda m: str(roll_dice(int(m.group(1)), int(m.group(2)), rng)), s)
    if re.fullmatch(r"[0-9+\-*/\s]+", s):
        try:
            return int(eval(s))
        except Exception:
            return 0
    return 0


# ── 豁免检定 ──
def parse_dc(formula: Any, prof_bonus: int, attr_mods: Dict[str, int]) -> int:
    """解析 DC 公式（如 '8+PROF+STR'）→ 整数 DC。仅允许数字与运算符。"""
    if not formula:
        return 8 + prof_bonus
    s = str(formula).upper().replace("PROF", str(prof_bonus))
    for ab in ("STR", "DEX", "CON", "INT", "WIS", "CHA"):
        s = s.replace(ab, str(attr_mods.get(ab, 0)))
    if re.fullmatch(r"[0-9+\-*/\s]+", s):
        try:
            return int(eval(s))
        except Exception:
            return 8 + prof_bonus
    return 8 + prof_bonus


def roll_saving_throw(
    saving_throw: Any,
    defender_attr_mods: Dict[str, int],
    rng: Any = random,
) -> Optional[str]:
    """对防御方掷豁免。成功返回 on_save（半伤/无效/部分），失败返回 None（全额命中）。

    参数:
        saving_throw: 技能上的 saving_throw 字典 {attr, dc_formula, on_save}
        defender_attr_mods: 防御方属性调整值 dict（card["attributes"][*]["modifier"]）
    """
    if not isinstance(saving_throw, dict):
        return None
    attr = saving_throw.get("attr")
    dc = parse_dc(saving_throw.get("dc_formula"),
                   defender_attr_mods.get("_prof", 2),
                   defender_attr_mods)
    bonus = defender_attr_mods.get(attr, 0) if attr else 0
    roll = rng.randint(1, 20) + bonus
    if roll >= dc:
        return saving_throw.get("on_save", "半伤")
    return None
