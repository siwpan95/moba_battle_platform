#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""core.mechanics D&D 机制单元测试（A3 消费路线）。

覆盖：effect 类别归一、骰子、DC 解析、豁免检定。
"""

from core.mechanics import (
    categorize_effect, roll_dice, roll_dice_expr,
    parse_dc, roll_saving_throw,
)


class _FixedRng:
    def __init__(self, val: int):
        self.val = val

    def randint(self, a, b):
        return self.val


def test_categorize_effect_aliases():
    # 控制类多写法归一
    assert categorize_effect({"type": "stun"}) == "control"
    assert categorize_effect({"type": "眩晕"}) == "control"
    assert categorize_effect({"type": "knockback"}) == "control"
    # 持续伤害
    assert categorize_effect({"type": "bleed"}) == "dot"
    assert categorize_effect({"type": "灼烧"}) == "dot"
    # 护盾 / 斩杀 / 真伤
    assert categorize_effect({"type": "shield"}) == "shield"
    assert categorize_effect({"type": "execute"}) == "execute"
    assert categorize_effect({"type": "pierce"}) == "true_dmg"


def test_categorize_effect_unknown_is_flavor():
    assert categorize_effect({"type": "whatever-nonsense"}) == "flavor"
    assert categorize_effect({"type": ""}) == "flavor"
    assert categorize_effect({}) == "flavor"
    assert categorize_effect("not-a-dict") == "flavor"


def test_roll_dice_basic():
    assert roll_dice(0, 6, _FixedRng(3)) == 0
    assert roll_dice(2, 6, _FixedRng(3)) == 6     # 3 + 3
    assert roll_dice(3, 4, _FixedRng(2)) == 6     # 2 + 2 + 2


def test_roll_dice_expr_attr_substitution():
    # "1d8+WIS", WIS 调整 +2, 骰固定掷 4 → 4 + 2 = 6
    mods = {"STR": 0, "DEX": 0, "CON": 0, "INT": 0, "WIS": 2, "CHA": 0}
    assert roll_dice_expr("1d8+WIS", mods, _FixedRng(4)) == 6


def test_parse_dc_formula():
    mods = {"STR": 3, "DEX": 0, "CON": 0, "INT": 0, "WIS": 0, "CHA": 0}
    # 8 + PROF(2) + STR(3) = 13
    assert parse_dc("8+PROF+STR", 2, mods) == 13
    # 缺省公式 → 8 + prof
    assert parse_dc(None, 2, mods) == 10


def test_roll_saving_throw_success_and_fail():
    saving = {"attr": "STR", "dc_formula": "8+PROF+STR", "on_save": "半伤"}
    mods = {"STR": 3, "_prof": 2}
    # 掷出 20 → 20 + 3 = 23 >= 13 → 半伤
    assert roll_saving_throw(saving, mods, _FixedRng(20)) == "半伤"
    # 掷出 1 → 1 + 3 = 4 < 13 → 失败（全额命中）
    assert roll_saving_throw(saving, mods, _FixedRng(1)) is None
