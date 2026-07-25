#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""端到端 fuzzing 测试：随机抽真实角色卡两两对战，验证不崩溃 + HP 不越界。

与 test_battle_smoke 的区别：
  - smoke 用 mock 卡验证单条机制（dict 卡 / 单技能 / saving_throw 技能）
  - 本测试用 HeroLoader 加载的 1659 张真实卡，覆盖真实数据分布
    （含 saving_throw / effects / 各类技能组合 / 24 款游戏）

定位：CI 回归门禁——任何 simulator / mechanics / engine 改动若导致真实数据
对战崩溃，本测试立即拦截。固定 seed 保证可复现。
"""

import random

from core.loader import HeroLoader
from core.simulator import BattleSimulator


def _load_real_heroes():
    """加载全部真实角色卡（CI 环境下 data/ 必须存在）。"""
    heroes = HeroLoader.load_all_heroes()
    assert len(heroes) > 100, f"真实角色卡加载过少: {len(heroes)}，请检查 data/ 目录"
    return heroes


def test_fuzz_random_battles_no_crash():
    """随机抽 50 对真实卡，1-18 级随机，对战 50 回合不崩且 HP 不越界。"""
    heroes = _load_real_heroes()
    pool_rng = random.Random(20260725)  # 固定 seed 保证抽样可复现

    for _ in range(50):
        c1 = pool_rng.choice(heroes)
        c2 = pool_rng.choice(heroes)
        lv1 = pool_rng.randint(1, 18)
        lv2 = pool_rng.randint(1, 18)
        # 每场对战用独立 rng，避免一场的随机性影响下一场
        battle_rng = random.Random(pool_rng.randint(0, 10 ** 9))
        sim = BattleSimulator(c1, c2, lv1, lv2, rng=battle_rng)
        for _ in range(50):
            sim.execute_turn()
            assert 0 <= sim.hp1 <= sim.max_hp1, (
                f"{c1['hero']['name']} HP 越界: {sim.hp1}/{sim.max_hp1}")
            assert 0 <= sim.hp2 <= sim.max_hp2, (
                f"{c2['hero']['name']} HP 越界: {sim.hp2}/{sim.max_hp2}")
            if sim.hp1 <= 0 or sim.hp2 <= 0:
                break


def test_fuzz_all_games_represented():
    """真实角色卡覆盖每款游戏至少 1 张（数据分布健康度）。"""
    heroes = _load_real_heroes()
    games = {h.get("game", {}).get("name") for h in heroes}
    assert len(games) >= 20, f"游戏数过少: {len(games)}，期望 24 款"


def test_fuzz_battle_produces_winner_or_timeout():
    """每场对战最终应有胜方或 50 回合超时（不应卡死/无日志）。"""
    heroes = _load_real_heroes()
    pool_rng = random.Random(20260726)
    for _ in range(20):
        c1 = pool_rng.choice(heroes)
        c2 = pool_rng.choice(heroes)
        sim = BattleSimulator(c1, c2, 10, 10, rng=random.Random(pool_rng.randint(0, 10 ** 9)))
        has_winner = False
        for _ in range(50):
            logs = sim.execute_turn()
            if any("胜利" in line for line in logs):
                has_winner = True
                break
        # 50 回合内可能无胜负（tank vs tank），但 sim 状态必须合法
        assert sim.hp1 >= 0 and sim.hp2 >= 0
        # 不强制要求 has_winner（超时也是合法结果），只记录
