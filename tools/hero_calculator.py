#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MOBA 英雄数值计算器 —— 基于 D&D 5e 规则
支持：购点计算、属性调整值、HP/AC/伤害模拟、等级成长
"""

import json
import math
import sys
import os
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# 引用统一战斗引擎（与 main.py / card_tool.py 一致的 PROJECT_ROOT 引导）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from core.engine import BattleEngine

# ==========================================
# D&D 5e 核心常量
# ==========================================

ABILITY_NAMES = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
ABILITY_NAMES_CN = ["力量", "敏捷", "体质", "智力", "感知", "魅力"]

# 购点花费表（目标值 → 累计花费）
POINT_BUY_COST = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
POINT_BUY_MAX = 27

# 标准数组（PHB p.13）
STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]

# 熟练加值表
PROFICIENCY_BONUS = {
    1: 2, 2: 2, 3: 2, 4: 2,
    5: 3, 6: 3, 7: 3, 8: 3,
    9: 4, 10: 4, 11: 4, 12: 4,
    13: 5, 14: 5, 15: 5, 16: 5,
    17: 6, 18: 6
}

# 职业定义
CLASS_DEFS = {
    "tank": {
        "name": "坦克",
        "dnd_class": "野蛮人",
        "hit_die": 12,
        "hp_per_level": 7,
        "primary": ["STR", "CON"],
        "save_prof": ["STR", "CON"],
    },
    "fighter": {
        "name": "战士",
        "dnd_class": "战士",
        "hit_die": 10,
        "hp_per_level": 6,
        "primary": ["STR", "DEX"],
        "save_prof": ["STR", "CON"],
    },
    "assassin": {
        "name": "刺客",
        "dnd_class": "游荡者",
        "hit_die": 8,
        "hp_per_level": 5,
        "primary": ["DEX"],
        "save_prof": ["DEX", "INT"],
    },
    "mage": {
        "name": "法师",
        "dnd_class": "法师",
        "hit_die": 6,
        "hp_per_level": 4,
        "primary": ["INT"],
        "save_prof": ["INT", "WIS"],
    },
    "marksman": {
        "name": "射手",
        "dnd_class": "游侠",
        "hit_die": 10,
        "hp_per_level": 6,
        "primary": ["DEX", "WIS"],
        "save_prof": ["STR", "DEX"],
    },
    "support": {
        "name": "辅助",
        "dnd_class": "牧师",
        "hit_die": 8,
        "hp_per_level": 5,
        "primary": ["WIS", "CHA"],
        "save_prof": ["WIS", "CHA"],
    },
}


def ability_modifier(score: int) -> int:
    """D&D 5e 属性调整值：⌊(score - 10) / 2⌋"""
    return (score - 10) // 2


def roll_4d6_drop_lowest() -> int:
    """D&D 5e 经典骰点：4d6 取最高 3 个"""
    import random
    return sum(sorted([random.randint(1, 6) for _ in range(4)])[1:])


def roll_abilities() -> Dict[str, int]:
    """4d6k3 × 6 生成六维属性（D&D 风味）"""
    import random
    return {attr: roll_4d6_drop_lowest() for attr in ABILITY_NAMES}


def point_buy_cost(scores: Dict[str, int]) -> Tuple[int, bool]:
    """计算购点总花费，返回 (花费, 是否合法)"""
    total = 0
    for attr in ABILITY_NAMES:
        score = scores.get(attr, 8)
        if score < 8 or score > 15:
            return total, False
        total += POINT_BUY_COST[score]
    return total, total <= POINT_BUY_MAX


@dataclass
class HeroStats:
    """英雄数值快照"""
    level: int
    hp: int
    ac: int
    physical_atk: int
    magic_power: int
    atk_speed_pct: float
    crit_chance: float     # 暴击概率(百分比)
    crit_damage: float     # 暴击伤害(百分比)
    cdr_pct: float
    heal_bonus_pct: float
    cc_resist_pct: float
    prof_bonus: int
    save_bonuses: Dict[str, int]


class HeroBuilder:
    """基于 D&D 5e 规则的 MOBA 英雄构建器"""
    
    def __init__(self, role: str, name: str = "未命名"):
        self.role = role
        self.name = name
        self.class_def = CLASS_DEFS.get(role, CLASS_DEFS["fighter"])
        self.scores = {attr: 8 for attr in ABILITY_NAMES}  # 起始全部 8
        self.racial_bonuses = {attr: 0 for attr in ABILITY_NAMES}
        self.level = 1
        self.asi_used = 0  # 已使用的属性提升次数
        self.equipment_ac = 0
        self.weapon_dice = 6  # 默认 d6
    
    def set_ability(self, attr: str, value: int):
        """设置单个属性值"""
        if attr in ABILITY_NAMES:
            self.scores[attr] = max(8, min(15, value))
    
    def buy_scores(self, scores: Dict[str, int]) -> Tuple[int, bool]:
        """购点分配六维属性"""
        self.scores = {attr: scores.get(attr, 8) for attr in ABILITY_NAMES}
        cost, valid = point_buy_cost(self.scores)
        return cost, valid
    
    def apply_racial_bonus(self, bonus: Dict[str, int]):
        """应用种族加值"""
        for attr, val in bonus.items():
            if attr in ABILITY_NAMES:
                self.racial_bonuses[attr] = val
    
    def get_effective_score(self, attr: str) -> int:
        """获取最终属性值（购点 + 种族 + ASI）"""
        base = self.scores.get(attr, 8)
        racial = self.racial_bonuses.get(attr, 0)
        return base + racial
    
    def get_mod(self, attr: str) -> int:
        """获取属性调整值"""
        return ability_modifier(self.get_effective_score(attr))
    
    def get_proficiency_bonus(self) -> int:
        """获取当前熟练加值"""
        return PROFICIENCY_BONUS.get(self.level, 2)
    
    def calculate_hp(self) -> int:
        """计算当前HP"""
        base_hp = self.class_def["hit_die"]
        con_mod = self.get_mod("CON")
        hp_per_lvl = self.class_def["hp_per_level"]
        return base_hp + con_mod * self.level + hp_per_lvl * (self.level - 1)
    
    def calculate_ac(self) -> int:
        """计算防御等级"""
        dex_mod = self.get_mod("DEX")
        # 职业护甲基础
        armor_base = {"tank": 2, "fighter": 3, "assassin": 1, "mage": 0, "marksman": 2, "support": 2}
        return 10 + dex_mod + armor_base.get(self.role, 1) + self.equipment_ac
    
    def calculate_physical_atk(self) -> int:
        """计算物理攻击力"""
        str_mod = self.get_mod("STR")
        dex_mod = self.get_mod("DEX")
        prof = self.get_proficiency_bonus()
        # 根据职业使用不同主属性
        if self.role in ("assassin", "marksman"):
            primary_mod = dex_mod
        else:
            primary_mod = str_mod
        return 30 + primary_mod * 5 + prof * 3
    
    def calculate_magic_power(self) -> int:
        """计算法术强度"""
        int_mod = self.get_mod("INT")
        prof = self.get_proficiency_bonus()
        return 25 + int_mod * 6 + prof * 2
    
    def get_stats(self) -> HeroStats:
        """获取完整数值快照"""
        dex_mod = self.get_mod("DEX")
        wis_mod = self.get_mod("WIS")
        cha_mod = self.get_mod("CHA")
        prof = self.get_proficiency_bonus()
        
        return HeroStats(
            level=self.level,
            hp=self.calculate_hp(),
            ac=self.calculate_ac(),
            physical_atk=self.calculate_physical_atk(),
            magic_power=self.calculate_magic_power(),
            atk_speed_pct=round(dex_mod * 1.0, 1),
            crit_chance=round(max(5.0, 10.0 + dex_mod * 2.0), 1),   # 暴击概率(百分比)
            crit_damage=round(150.0 + dex_mod * 5.0, 1),             # 暴击伤害(百分比)
            cdr_pct=round(wis_mod * 1.0, 1),
            heal_bonus_pct=round(cha_mod * 2.0, 1),
            cc_resist_pct=round(wis_mod * 1.0, 1),
            prof_bonus=prof,
            save_bonuses={
                attr: self.get_mod(attr) + (prof if attr in self.class_def["save_prof"] else 0)
                for attr in ABILITY_NAMES
            }
        )
    
    def simulate_level_up(self, target_level: int) -> List[HeroStats]:
        """模拟升级过程，返回每级数值"""
        results = []
        original_level = self.level
        for lv in range(1, target_level + 1):
            self.level = lv
            # ASI: Lv4, 8, 12, 16 时自动提升主属性
            if lv in (4, 8, 12, 16):
                self.asi_used += 1
            results.append(self.get_stats())
        self.level = original_level
        return results
    
    def print_sheet(self):
        """打印角色卡"""
        stats = self.get_stats()
        
        print(f"\n{'='*60}")
        print(f"  {self.name}  |  {self.class_def['name']} ({self.class_def['dnd_class']})")
        print(f"  等级 {self.level}  |  熟练加值 +{stats.prof_bonus}")
        print(f"{'='*60}")
        
        print(f"\n  ┌─ 六维属性 ─────────────────────┐")
        print(f"  │ {'属性':<6} {'原始':>3} {'种族':>3} {'最终':>3} {'调整':>4} │")
        for attr, cn in zip(ABILITY_NAMES, ABILITY_NAMES_CN):
            final = self.get_effective_score(attr)
            mod = ability_modifier(final)
            racial = self.racial_bonuses.get(attr, 0)
            mark = "←主属性" if attr in self.class_def["primary"] else ""
            print(f"  │ {cn:<6} {self.scores[attr]:>3} {racial:+>3} {final:>3} {mod:+>4}  {mark} │")
        print(f"  └────────────────────────────────┘")
        
        print(f"\n  ┌─ 战斗数值 ──────────────────────┐")
        print(f"  │ 生命值 HP:      {stats.hp:>6}              │")
        print(f"  │ 防御 AC:        {stats.ac:>6}              │")
        print(f"  │ 物理攻击 ATK:   {stats.physical_atk:>6}              │")
        print(f"  │ 法术强度 AP:    {stats.magic_power:>6}              │")
        print(f"  │ 攻击速度:       {stats.atk_speed_pct:>+5.1f}%             │")
        print(f"  │ 暴击概率:       {stats.crit_chance:>+5.1f}%             │")
        print(f"  │ 暴击伤害:       {stats.crit_damage:>+5.1f}%             │")
        print(f"  │ 冷却缩减 CDR:   {stats.cdr_pct:>+5.1f}%             │")
        print(f"  │ 治疗加成:       {stats.heal_bonus_pct:>+5.1f}%             │")
        print(f"  └────────────────────────────────┘")
        
        print(f"\n  ┌─ 豁免加值 ──────────────────────┐")
        for attr, cn in zip(ABILITY_NAMES, ABILITY_NAMES_CN):
            save = stats.save_bonuses[attr]
            prof_mark = " (擅长)" if attr in self.class_def["save_prof"] else ""
            print(f"  │ {cn}豁免: {save:+>3}{prof_mark:<6}              │")
        print(f"  └────────────────────────────────┘")
    
    def to_dict(self) -> dict:
        """导出为字典"""
        stats = self.get_stats()
        return {
            "name": self.name,
            "role": self.role,
            "role_cn": self.class_def["name"],
            "dnd_class": self.class_def["dnd_class"],
            "hit_die": self.class_def["hit_die"],
            "level": self.level,
            "scores": {attr: self.get_effective_score(attr) for attr in ABILITY_NAMES},
            "modifiers": {attr: self.get_mod(attr) for attr in ABILITY_NAMES},
            "prof_bonus": stats.prof_bonus,
            "hp": stats.hp,
            "ac": stats.ac,
            "physical_atk": stats.physical_atk,
            "magic_power": stats.magic_power,
            "atk_speed_pct": stats.atk_speed_pct,
            "crit_chance": stats.crit_chance,
            "crit_damage": stats.crit_damage,
            "cdr_pct": stats.cdr_pct,
            "heal_bonus_pct": stats.heal_bonus_pct,
            "save_bonuses": stats.save_bonuses,
            "primary_abilities": self.class_def["primary"],
            "save_proficiencies": self.class_def["save_prof"],
        }


def demo_six_roles():
    """演示六大职业的默认购点构建"""
    # 各职业的标准购点模板
    templates = {
        "tank":     {"STR": 15, "DEX": 10, "CON": 15, "INT": 8,  "WIS": 10, "CHA": 10},
        "fighter":  {"STR": 15, "DEX": 12, "CON": 14, "INT": 8,  "WIS": 10, "CHA": 8},
        "assassin": {"STR": 10, "DEX": 15, "CON": 12, "INT": 8,  "WIS": 10, "CHA": 13},
        "mage":     {"STR": 8,  "DEX": 10, "CON": 12, "INT": 15, "WIS": 13, "CHA": 10},
        "marksman": {"STR": 8,  "DEX": 15, "CON": 14, "INT": 8,  "WIS": 12, "CHA": 10},
        "support":  {"STR": 10, "DEX": 10, "CON": 14, "INT": 8,  "WIS": 13, "CHA": 15},
    }
    
    # 种族加成模板
    racial_templates = {
        "tank":     {"STR": 2, "CON": 2},
        "fighter":  {"STR": 2, "DEX": 1},
        "assassin": {"DEX": 2, "CHA": 1},
        "mage":     {"INT": 2, "WIS": 1},
        "marksman": {"DEX": 2, "WIS": 1},
        "support":  {"WIS": 1, "CHA": 2},
    }
    
    heroes = {}
    for role in ["tank", "fighter", "assassin", "mage", "marksman", "support"]:
        hb = HeroBuilder(role, f"示例{CLASS_DEFS[role]['name']}")
        hb.buy_scores(templates[role])
        hb.apply_racial_bonus(racial_templates[role])
        heroes[role] = hb
    
    return heroes


def demo_level_progression():
    """演示角色从1级到18级的成长曲线"""
    hb = HeroBuilder("fighter", "成长演示·战士")
    hb.buy_scores({"STR": 15, "DEX": 12, "CON": 14, "INT": 8, "WIS": 10, "CHA": 8})
    hb.apply_racial_bonus({"STR": 2, "DEX": 1})
    
    progression = hb.simulate_level_up(18)
    return progression


# ==========================================
# 模拟战斗引擎
# ==========================================

class CombatSimulator:
    """基于 D&D 5e 的战斗模拟 —— 薄封装层，委托给统一 BattleEngine"""
    
    @staticmethod
    def physical_damage(attacker: HeroStats, defender: HeroStats, skill_mult: float = 1.0) -> dict:
        """物理普攻/技能伤害"""
        result = BattleEngine.physical_damage(attacker.physical_atk, defender.ac, skill_mult)
        # 转换为旧接口兼容格式
        return {
            "type": "物理",
            "raw": result["raw"],
            "reduced": result["final"],
            "reduction_pct": result["reduction_pct"],
        }
    
    @staticmethod
    def magic_damage(attacker: HeroStats, defender: HeroStats, skill_mult: float = 1.0) -> dict:
        """法术技能伤害"""
        wis_save = defender.save_bonuses.get("WIS", 0)
        result = BattleEngine.magic_damage(attacker.magic_power, wis_save, skill_mult)
        return {
            "type": "法术",
            "raw": result["raw"],
            "reduced": result["final"],
            "reduction_pct": result["reduction_pct"],
        }


def main():
    print("=" * 60)
    print("  MOBA 英雄数值计算器 —— 基于 D&D 5e 规则")
    print("=" * 60)
    
    # 1. 六大职业演示
    print("\n\n【一、六大职业 1 级数值对比】\n")
    heroes = demo_six_roles()
    
    comparison_table = []
    for role, hb in heroes.items():
        stats = hb.get_stats()
        comparison_table.append(stats)
        hb.print_sheet()
    
    # 汇总对比
    print("\n  ┌─ 横向对比 ────────────────────────────────────────┐")
    print(f"  │ {'职业':<8} {'HP':>5} {'AC':>4} {'ATK':>5} {'AP':>5} {'攻速%':>6} {'暴率%':>6} {'暴伤%':>6} {'CDR%':>5} {'治疗%':>5} │")
    for role, hb in heroes.items():
        s = hb.get_stats()
        print(f"  │ {hb.class_def['name']:<8} {s.hp:>5} {s.ac:>4} {s.physical_atk:>5} {s.magic_power:>5} {s.atk_speed_pct:>+5.1f} {s.crit_chance:>+5.1f} {s.crit_damage:>+5.1f} {s.cdr_pct:>+5.1f} {s.heal_bonus_pct:>+5.1f} │")
    print(f"  └─────────────────────────────────────────────────┘")
    
    # 2. 等级成长曲线
    print("\n\n【二、战士 1-18 级成长曲线】\n")
    progression = demo_level_progression()
    
    print(f"  {'等级':<6} {'HP':>5} {'AC':>4} {'ATK':>5} {'熟练':>4} {'STR':>4} {'DEX':>4}")
    print(f"  {'-'*35}")
    key_levels = [1, 4, 5, 8, 9, 12, 13, 16, 17, 18]
    for i in range(len(progression)):
        if (i + 1) in key_levels:
            s = progression[i]
            # 模拟ASI后的属性增长
            hb = HeroBuilder("fighter", "")
            hb.buy_scores({"STR": 15, "DEX": 12, "CON": 14, "INT": 8, "WIS": 10, "CHA": 8})
            hb.apply_racial_bonus({"STR": 2, "DEX": 1})
            # 添加 ASI
            asi_count = (i + 1) // 4
            str_bonus = min(asi_count, 5) * 2  # 每次 ASI +2 STR
            eff_str = hb.get_effective_score("STR") + str_bonus
            eff_dex = hb.get_effective_score("DEX")
            print(f"  Lv{i+1:<4} {s.hp:>5} {10+hb.get_mod('DEX')+3:>4} {s.physical_atk:>5} +{s.prof_bonus:>3} {eff_str:>4} {eff_dex:>4}")
    print()
    
    # 3. 战斗伤害模拟
    print("\n【三、战斗伤害模拟】\n")
    
    tank = heroes["tank"].get_stats()
    mage = heroes["mage"].get_stats()
    assassin = heroes["assassin"].get_stats()
    
    sim = CombatSimulator()
    
    # 刺客 → 法师 (物理)
    dmg = sim.physical_damage(assassin, mage, 1.5)
    print(f"  刺客(ATK {assassin.physical_atk}) → 法师(AC {mage.ac})")
    print(f"    物理技能(×1.5): 原始 {dmg['raw']} → 实际 {dmg['reduced']} (减免 {dmg['reduction_pct']}%)")
    
    # 刺客 → 坦克 (物理)
    dmg = sim.physical_damage(assassin, tank, 1.5)
    print(f"  刺客(ATK {assassin.physical_atk}) → 坦克(AC {tank.ac})")
    print(f"    物理技能(×1.5): 原始 {dmg['raw']} → 实际 {dmg['reduced']} (减免 {dmg['reduction_pct']}%)")
    
    # 法师 → 坦克 (法伤)
    dmg = sim.magic_damage(mage, tank, 2.0)
    print(f"  法师(AP {mage.magic_power}) → 坦克(WIS豁免 {tank.save_bonuses['WIS']})")
    print(f"    法伤技能(×2.0): 原始 {dmg['raw']} → 实际 {dmg['reduced']} (减免 {dmg['reduction_pct']}%)")
    
    # 法师 → 刺客 (法伤)
    dmg = sim.magic_damage(mage, assassin, 2.0)
    print(f"  法师(AP {mage.magic_power}) → 刺客(WIS豁免 {assassin.save_bonuses['WIS']})")
    print(f"    法伤技能(×2.0): 原始 {dmg['raw']} → 实际 {dmg['reduced']} (减免 {dmg['reduction_pct']}%)")
    
    # 4. 导出 JSON
    print("\n\n【四、导出】\n")
    output = {
        "framework": "基于D&D 5e规则的MOBA英雄数值体系",
        "version": "1.1",
        "roles": {}
    }
    for role, hb in heroes.items():
        output["roles"][role] = hb.to_dict()
    
    # 添加成长曲线
    output["progression_demo"] = {
        "role": "fighter",
        "levels": [
            {"level": i+1, "hp": s.hp, "ac": s.ac, "atk": s.physical_atk, "prof": s.prof_bonus}
            for i, s in enumerate(progression) if (i+1) in [1,4,5,8,9,12,13,16,17,18]
        ]
    }
    
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hero_stats_demo.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"  ✓ 数值示例 → {output_path}")
    
    print("\n" + "=" * 60)
    print("  计算完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
