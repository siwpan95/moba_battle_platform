#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""engine.py 数值公式单元测试（锁死公式契约，Tessa 已实跑校验用例）。"""

from core.engine import BattleEngine, ability_modifier


def test_physical_damage_formula_and_floor():
    # 正常减伤
    r = BattleEngine.physical_damage(60, 15, 1.0)
    assert r["raw"] == 60.0
    assert r["final"] == 55.5          # 60*(1-15*0.005)
    assert r["reduction_pct"] == 7.5

    # 高减伤触底 30%
    r = BattleEngine.physical_damage(50, 200, 1.0)
    assert r["final"] == 15.0          # 保底 50*0.3

    # 极端减伤不穿透（保底仍生效）
    r = BattleEngine.physical_damage(10, 300, 1.0)
    assert r["final"] == 3.0           # 保底 10*0.3


def test_magic_damage_formula_and_floor():
    r = BattleEngine.magic_damage(40, 5, 1.0)
    assert r["raw"] == 40.0
    assert r["final"] == 34.0          # 40*(1-5*0.03)
    assert r["reduction_pct"] == 15.0

    # 负豁免不减伤
    r = BattleEngine.magic_damage(40, -1, 1.0)
    assert r["final"] == 40.0
    assert r["reduction_pct"] == 0.0

    # 高豁免触底 30%
    r = BattleEngine.magic_damage(30, 33, 1.0)
    assert r["final"] == 9.0           # 保底 30*0.3
    assert r["reduction_pct"] == 99.0


def test_crit_chance_bounds():
    assert BattleEngine.calc_crit_chance(0) == 0.10
    assert BattleEngine.calc_crit_chance(2) == 0.14
    assert BattleEngine.calc_crit_chance(5) == 0.20
    # 下限 5%
    assert BattleEngine.calc_crit_chance(-3) == 0.05
    assert BattleEngine.calc_crit_chance(-10) == 0.05


def test_crit_damage_multiplier():
    assert BattleEngine.crit_damage_multiplier(0) == 1.5
    assert BattleEngine.crit_damage_multiplier(2) == 1.6
    assert BattleEngine.crit_damage_multiplier(5) == 1.75
    # 负 DEX 下限
    assert BattleEngine.crit_damage_multiplier(-5) == 1.25


def test_attack_power_primary_stat():
    # fighter 用 STR
    assert BattleEngine.attack_power("fighter", 50, 3, 2) == 53.0
    # assassin / marksman 用 DEX
    assert BattleEngine.attack_power("assassin", 50, 3, 2) == 52.0
    assert BattleEngine.attack_power("marksman", 50, 3, 2) == 52.0


def test_magic_power_bonus():
    assert BattleEngine.magic_power_bonus(40, -1) == 38.8
    assert BattleEngine.magic_power_bonus(40, 3) == 43.6


def test_ability_modifier():
    assert ability_modifier(17) == 3
    assert ability_modifier(10) == 0
    assert ability_modifier(8) == -1


class _FixedRng:
    """返回固定值的伪 rng，便于断言骰子结果。"""

    def __init__(self, val: int):
        self.val = val

    def randint(self, a, b):
        return self.val


def test_skill_raw_damage_no_damage_returns_zero():
    # 无 damage 字段 / 骰数为 0 → 0
    assert BattleEngine.skill_raw_damage(None, {}, _FixedRng(3)) == 0
    assert BattleEngine.skill_raw_damage({"name": "Q"}, {}, _FixedRng(3)) == 0
    assert BattleEngine.skill_raw_damage(
        {"damage": {"dice_count": 0, "dice_size": 6}}, {}, _FixedRng(3)) == 0


def test_skill_raw_damage_rolls_and_applies_bonus():
    skill = {"damage": {"dice_count": 2, "dice_size": 6, "bonus_attr": "STR"}}
    attrs = {"STR": {"modifier": 3}}
    # 两颗 d6 都掷出 3 → 6，+ STR 调整 3 = 9
    assert BattleEngine.skill_raw_damage(skill, attrs, _FixedRng(3)) == 9


def test_apply_mitigation_physical():
    r = BattleEngine.apply_mitigation(100, 20, False)
    assert r["final"] == 90.0          # 100*(1-20*0.005)
    assert r["reduction_pct"] == 10.0
    # 高 AC 触底 30%
    r = BattleEngine.apply_mitigation(100, 200, False)
    assert r["final"] == 30.0


def test_apply_mitigation_magic():
    r = BattleEngine.apply_mitigation(100, 5, True)
    assert r["final"] == 85.0          # 100*(1-5*0.03)
    assert r["reduction_pct"] == 15.0
    # 高豁免触底 30%
    r = BattleEngine.apply_mitigation(100, 33, True)
    assert r["final"] == 30.0
