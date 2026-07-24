#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对战冒烟测试：验证 dict 卡不再崩溃、归一化后英雄可玩、HP 不越界。"""

from core.simulator import BattleSimulator


def _make_card(name, role, skills):
    return {
        "hero": {"name": name},
        "game": {"name": "test", "universal_role": role},
        "attributes": {
            "STR": {"score": 16, "modifier": 3},
            "DEX": {"score": 14, "modifier": 2},
            "CON": {"score": 14, "modifier": 2},
            "INT": {"score": 10, "modifier": 0},
            "WIS": {"score": 10, "modifier": 0},
            "CHA": {"score": 10, "modifier": 0},
        },
        "stats_lv1": {
            "hp": 600, "ac": 18, "physical_atk": 60, "magic_power": 40,
            "prof_bonus": 2, "crit_chance": 5, "crit_damage": 150,
            "cdr_pct": 0, "heal_bonus_pct": 0, "cc_resist_pct": 0,
            "save_bonuses": {k: 2 for k in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]},
        },
        "stats_lv18": {"hp": 1200, "ac": 22, "physical_atk": 120, "magic_power": 80},
        "skills": skills,
    }


def test_dict_skills_no_longer_crashes():
    """回归：skills 为 dict 时，模拟器不应再抛 KeyError（Cody A1 / 事故 SEV-2 止血）。"""
    dict_card = _make_card("DictHero", "fighter",
                           {"name": "火球术", "key": "Q", "type": "法术", "cooldown": 0})
    list_card = _make_card("ListHero", "mage",
                           [{"name": "Q"}, {"name": "W"}, {"name": "E"}, {"name": "R"}])
    sim = BattleSimulator(dict_card, list_card, 10, 10)
    # 不应抛异常
    for _ in range(50):
        sim.execute_turn()
    assert True


def test_normalized_single_skill_hero_playable():
    """迁移后的单技能英雄（list[单元素]）可完整对战且 HP 不越界。"""
    single = _make_card("SingleSkill", "fighter", [{"name": "Q", "type": "物理", "cooldown": 0}])
    other = _make_card("Full", "mage", [{"name": "Q"}, {"name": "W"}, {"name": "E"}, {"name": "R"}])
    sim = BattleSimulator(single, other, 8, 8)
    for _ in range(50):
        sim.execute_turn()
        assert 0 <= sim.hp1 <= sim.max_hp1
        assert 0 <= sim.hp2 <= sim.max_hp2
        if sim.hp1 <= 0 or sim.hp2 <= 0:
            break
    assert sim.hp1 >= 0 and sim.hp2 >= 0


def test_skill_with_dice_effects_and_saving_throw_no_crash():
    """A3 消费路线：带 damage 骰 + effects + saving_throw 的技能应真正生效且不崩。

    此前的实现会把嵌套 attributes 直接传给 roll_saving_throw、并对 None 技能
    调用 skill.get，导致真实数据（64% 技能带 saving_throw）对战时崩溃。
    """
    skill = {
        "name": "火球术", "key": "Q", "type": "法术", "cooldown": 0,
        "damage": {"dice_count": 3, "dice_size": 6, "bonus_attr": "INT"},
        "effects": [{"type": "stun", "target": "敌方", "duration": 1}],
        "saving_throw": {"attr": "DEX", "dc_formula": "8+PROF+DEX", "on_save": "半伤"},
    }
    caster = _make_card("Caster", "mage", [skill, {"name": "W"}, {"name": "E"}, {"name": "R"}])
    target = _make_card("Target", "fighter", [{"name": "Q"}, {"name": "W"}, {"name": "E"}, {"name": "R"}])
    sim = BattleSimulator(caster, target, 5, 5)
    for _ in range(80):
        sim.execute_turn()
        assert 0 <= sim.hp1 <= sim.max_hp1
        assert 0 <= sim.hp2 <= sim.max_hp2
        if sim.hp1 <= 0 or sim.hp2 <= 0:
            break
    assert sim.hp1 >= 0 and sim.hp2 >= 0
