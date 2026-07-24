#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一战斗引擎 —— 简化 ARPG 战斗模型（受 D&D 5e 启发，并非完整 D&D 5e 实现）
battle_platform 和 _design 模块共用此引擎，消除代码重复。

核心公式（结算时还会乘以 DAMAGE_SCALE=0.35 与等级缩放，见 config.py）：
  • 物理伤害 = ATK × 倍率 × (1 − AC×0.005)  [最低30%]
  • 法术伤害 = AP × 倍率 × (1 − WIS豁免×0.03)  [最低30%]
  • 暴击概率 = 基础10% + DEX调整×2%  [最低5%]
  • 暴击伤害 = 基础150% + DEX调整×5%

注：技能的详细 D&D 效果（effects / aoe / saving_throw / 位移 / 吸血等）
由 tools/skill_mechanics.py 定义，并在 A3 消费路线中由 core/simulator.py 真正消费
（见 ADR-003）：伤害取自技能自带 damage 骰，effects 经 core/mechanics.categorize_effect
归一后生效，带 saving_throw 的技能触发防御方豁免。engine 仅提供基础结算公式。
"""

import random
from .mechanics import roll_dice

# ==========================================
# 战斗公式
# ==========================================

def ability_modifier(score: int) -> int:
    """D&D 5e 属性调整值：(score - 10) // 2"""
    return (score - 10) // 2


class BattleEngine:
    """D&D 5e 风格战斗引擎 —— 所有战斗计算的核心"""

    @staticmethod
    def skill_raw_damage(skill, attacker_attrs, rng=random) -> int:
        """基于技能自带 damage 骰 + bonus_attr 调整值计算原始伤害（A3 消费路线，坐实 D&D 5e）。

        数据来源：skill["damage"] = {dice_count, dice_size, bonus_attr, type}
        无伤害技能（dice_count/size 为 0，如自身 buff/治疗）返回 0。
        """
        if not isinstance(skill, dict):
            return 0
        dmg = skill.get("damage") or {}
        count = int(dmg.get("dice_count", 0) or 0)
        size = int(dmg.get("dice_size", 0) or 0)
        if count <= 0 or size <= 0:
            return 0
        bonus = 0
        bonus_attr = dmg.get("bonus_attr")
        if bonus_attr and isinstance(attacker_attrs, dict):
            a = attacker_attrs.get(bonus_attr)
            if isinstance(a, dict):
                bonus = int(a.get("modifier", 0) or 0)
        return max(1, roll_dice(count, size, rng) + bonus)

    @staticmethod
    def apply_mitigation(raw, ac_or_wis, is_magic) -> dict:
        """应用物理(AC)或法术(WIS豁免)减伤，保底30%（与 D&D 减伤精神一致）。"""
        if is_magic:
            reduction = max(0.0, (ac_or_wis or 0) * 0.03)
        else:
            reduction = (ac_or_wis or 0) * 0.005
        reduced = raw * (1 - reduction)
        reduced = max(raw * 0.3, reduced)
        return {"raw": round(raw, 1), "final": round(reduced, 1),
                "reduction_pct": round(reduction * 100, 1)}

    @staticmethod
    def physical_damage(atk: float, target_ac: int, skill_mult: float = 1.0) -> dict:
        """
        物理伤害计算。

        参数:
            atk: 攻击方的物理攻击力
            target_ac: 目标护甲值
            skill_mult: 技能倍率（普攻=1.0, 技能一=1.3, 技能二=1.1, 大招=2.0）

        返回:
            {"raw": 原始伤害, "final": 实际伤害, "reduction_pct": 减免百分比}
        """
        raw = atk * skill_mult
        reduction = target_ac * 0.005
        reduced = raw * (1 - reduction)
        reduced = max(raw * 0.3, reduced)  # 最低30%伤害
        return {
            "raw": round(raw, 1),
            "final": round(reduced, 1),
            "reduction_pct": round(reduction * 100, 1),
        }

    @staticmethod
    def magic_damage(ap: float, target_wis_save: int, skill_mult: float = 1.0) -> dict:
        """
        法术伤害计算。

        参数:
            ap: 攻击方的法术强度
            target_wis_save: 目标的感知豁免加值
            skill_mult: 技能倍率

        返回:
            {"raw": 原始伤害, "final": 实际伤害, "reduction_pct": 减免百分比}
        """
        raw = ap * skill_mult
        reduction = max(0.0, target_wis_save * 0.03)
        reduced = raw * (1 - reduction)
        reduced = max(raw * 0.3, reduced)  # 最低30%伤害
        return {
            "raw": round(raw, 1),
            "final": round(reduced, 1),
            "reduction_pct": round(reduction * 100, 1),
        }

    @staticmethod
    def crit_damage_multiplier(dex_mod: int) -> float:
        """暴击伤害倍率：基础150% + DEX调整×5%"""
        return (150.0 + dex_mod * 5.0) / 100.0

    @staticmethod
    def calc_crit_chance(dex_mod: int) -> float:
        """暴击概率：基础10% + DEX调整×2%，最低5%"""
        return max(0.05, 0.1 + dex_mod * 0.02)

    @staticmethod
    def attack_power(role: str, physical_atk: float, str_mod: int, dex_mod: int) -> float:
        """
        计算实际攻击力（含主属性加成）。

        刺客/射手用敏捷，其余用力。
        """
        if role in ("assassin", "marksman"):
            return physical_atk * (1 + dex_mod * 0.02)
        return physical_atk * (1 + str_mod * 0.02)

    @staticmethod
    def magic_power_bonus(magic_power: float, int_mod: int) -> float:
        """计算实际法术强度（含智力加成）。"""
        return magic_power * (1 + int_mod * 0.03)


# ==========================================
# D&D 5e 核心常量（可能与 _design 重复，但保证 engine 自包含）
# ==========================================

PROFICIENCY_BONUS = {
    1: 2, 2: 2, 3: 2, 4: 2,
    5: 3, 6: 3, 7: 3, 8: 3,
    9: 4, 10: 4, 11: 4, 12: 4,
    13: 5, 14: 5, 15: 5, 16: 5,
    17: 6, 18: 6,
}

# 注：原 CLASS_DEFS（职业生命骰/主属性/豁免）为死代码（全仓无引用），已按 ADR-002 删除；
# 若需统一的角色/职业 taxonomy，应集中在 core/registry.py 单一来源。
