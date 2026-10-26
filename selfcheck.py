#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""moba-battle 无头自检：伤害公式 + 真实角色卡对战推进（不 import tkinter）。

``core/simulator.py`` 经 ``core/engine.py -> core/mechanics.py`` 依赖
``alloy.trpg.dice``。本机 ``.venv`` 里的 alloy 是指向同级仓 ``G:\\repos\\an-engine``
的 editable 安装，但 editable finder 只映射了 ``alloy`` 包本身，而
``alloy/__init__.py`` 会 ``import allin_engine`` —— 只加仓根到 sys.path 即可补齐
（不改动项目自身，也不需要安装任何东西）。

验证点
------
1. 战斗公式：物理/法术减伤、30% 保底、暴击率下限与暴伤倍率、D&D 属性调整值、
   技能伤害骰（含 bonus_attr）。
2. 真实数据 + 状态推进：从 ``data/character_cards/league_of_legends`` 读两张真实
   角色卡，用 loader 的真实技能注入逻辑补齐技能；用固定 seed 跑完整场对战，
   验证血量边界、胜负标记、回合上限与幂等性，并验证同 seed 结果可复现。
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.dont_write_bytecode = True          # 不在项目里留 .pyc
try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
SIBLING_AN_ENGINE = ROOT.parent / "an-engine"     # 提供 alloy 依赖的 allin_engine

sys.path.insert(0, str(ROOT))
if SIBLING_AN_ENGINE.is_dir():
    sys.path.insert(0, str(SIBLING_AN_ENGINE))


class CheckError(RuntimeError):
    pass


def check(condition, message):
    if not condition:
        raise CheckError(message)


def check_formulas(BattleEngine, ability_modifier):
    physical = BattleEngine.physical_damage(100, 20)
    check(physical == {"raw": 100.0, "final": 90.0, "reduction_pct": 10.0},
          f"physical_damage(100,20) 结果错误：{physical!r}")
    check(BattleEngine.physical_damage(100, 400)["final"] == 30.0,
          "物理伤害 30% 保底未生效")
    magic = BattleEngine.magic_damage(100, 10)
    check(magic == {"raw": 100.0, "final": 70.0, "reduction_pct": 30.0},
          f"magic_damage(100,10) 结果错误：{magic!r}")
    check(BattleEngine.magic_damage(100, 100)["final"] == 30.0,
          "法术伤害 30% 保底未生效")
    check(BattleEngine.calc_crit_chance(-10) == 0.05, "暴击率下限不是 5%")
    check(abs(BattleEngine.crit_damage_multiplier(10) - 2.0) < 1e-9,
          "暴伤倍率不是 150% + DEX*5%")
    check(ability_modifier(17) == 3, "D&D 属性调整值公式错误")

    skill = {"damage": {"dice_count": 2, "dice_size": 6, "bonus_attr": "STR"}}
    attrs = {"STR": {"modifier": 3}}
    rolled = BattleEngine.skill_raw_damage(skill, attrs, random.Random(5))
    check(5 <= rolled <= 15, f"2d6+3 技能伤害越界：{rolled}")
    check(BattleEngine.skill_raw_damage({}, attrs) == 0, "无伤害技能应返回 0")


def pick_real_cards(HeroLoader):
    """从真实角色卡里取两张技能池可命中的卡（loader 的真实注入逻辑）。"""
    card_dir = ROOT / "data" / "character_cards" / "league_of_legends"
    check(card_dir.is_dir(), f"角色卡目录不存在：{card_dir}")
    files = sorted(p for p in card_dir.rglob("*.json") if not p.name.startswith("_"))
    check(files, f"角色卡目录为空：{card_dir}")

    picked = []
    for path in files:
        with path.open("r", encoding="utf-8") as handle:
            card = json.load(handle)
        HeroLoader._inject_skills(card, game_id=path.parent.name,
                                  filename_stem=path.stem)
        card, _normalized = HeroLoader._normalize_card(card)
        if card.get("skills"):
            picked.append(card)
        if len(picked) == 2:
            break
    check(len(picked) == 2, "没有找到两张带技能的真实角色卡（技能池缺失？）")
    return picked


def check_level_scaling(BattleSimulator, card):
    lv1 = BattleSimulator._calc_stats_for_level(card, 1)
    lv18 = BattleSimulator._calc_stats_for_level(card, 18)
    check(lv1["level"] == 1 and lv18["level"] == 18, "等级插值未记录等级")
    check(lv1["hp"] > 0 and lv18["hp"] > lv1["hp"],
          f"18 级血量未高于 1 级：{lv1['hp']} -> {lv18['hp']}")
    check(lv18["ac"] == card["stats_lv18"]["ac"], "18 级 AC 与角色卡不一致")
    check(lv18["physical_atk"] == card["stats_lv18"]["physical_atk"],
          "18 级攻击力与角色卡不一致")


def run_battle(BattleSimulator, cards, seed):
    sim = BattleSimulator(cards[0], cards[1], 5, 5, rng=random.Random(seed))
    turns = 0
    while not sim.is_over and turns < sim.max_rounds:
        sim.execute_turn()
        turns += 1
    return sim, turns


def check_battle(BattleSimulator, cards):
    sim, turns = run_battle(BattleSimulator, cards, 7)
    check(sim.is_over, f"对战在 {turns} 回合后仍未结束（winner=None）")
    check(turns <= sim.max_rounds, f"对战超过回合上限：{turns} > {sim.max_rounds}")
    check(sim.winner in (0, 1, 2), f"胜负标记非法：{sim.winner!r}")
    check(0 <= sim.hp1 <= sim.max_hp1, f"1 号血量越界：{sim.hp1}/{sim.max_hp1}")
    check(0 <= sim.hp2 <= sim.max_hp2, f"2 号血量越界：{sim.hp2}/{sim.max_hp2}")
    check(sim.execute_turn() == [], "胜负已定后 execute_turn 仍产生行动（非幂等）")

    again, turns_again = run_battle(BattleSimulator, cards, 7)
    check((again.winner, turns_again, again.hp1, again.hp2)
          == (sim.winner, turns, sim.hp1, sim.hp2),
          "同一 seed 的对战结果不可复现")
    return sim.winner, turns


def main():
    from core.engine import BattleEngine, ability_modifier
    from core.loader import HeroLoader
    from core.simulator import BattleSimulator

    check_formulas(BattleEngine, ability_modifier)
    cards = pick_real_cards(HeroLoader)
    check_level_scaling(BattleSimulator, cards[0])
    winner, turns = check_battle(BattleSimulator, cards)
    skills = sum(len(card.get("skills") or []) for card in cards)
    print(
        "selfcheck ok: damage formulas (physical/magic floor 30%%, crit min 5%%, "
        "2d6+bonus dice) + 2 real cards (%d skills) + seeded battle (%d turns, winner=%d)"
        % (skills, turns, winner)
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - 自检入口需要把任何失败转成 FAIL + 退出码 1
        print(f"FAIL: {type(exc).__name__}: {exc}")
        raise SystemExit(1)
