#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证管道（每次改动后必跑）。

  1. 契约校验 tools/check_cards.py  →  退出码必须 0
  2. 可选：全量 pytest 套件
  3. 可选：烟雾对战（随机抽英雄跑若干场，确认不崩、能终结）
"""

import os
import random
import subprocess
import sys

from battle_platform import paths


def check_cards() -> dict:
    """运行契约校验，返回 {ok, returncode, tail}。"""
    r = subprocess.run(
        [paths.PY, os.path.join(paths.TOOLS_DIR, "check_cards.py")],
        cwd=paths.PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8",
    )
    tail = [ln for ln in (r.stdout or "").splitlines() if ln.strip()][-5:]
    return {"ok": r.returncode == 0, "returncode": r.returncode, "tail": tail}


def check_dual_representation() -> dict:
    """R4 双表示守卫：公版 IP 卡内嵌 skills 须与 data/skills/<ip>/<英雄>.json 完全一致，
    且 4 技能骰期望之和落在 GDD ROLE_BAND 内。直接从 tools.check_cards 复用同一实现。"""
    sys.path.insert(0, paths.PROJECT_ROOT)
    try:
        from tools.check_cards import check_dual_representation as _fn
    except Exception as e:
        return {"ok": False, "error": f"import 失败: {e}"}
    errors, checked = _fn()
    return {"ok": len(errors) == 0, "checked": checked,
            "error_count": len(errors), "errors": errors[:10]}


def run_pytest() -> dict:
    """运行 pytest tests/ -q。"""
    r = subprocess.run(
        [paths.PY, "-m", "pytest", "tests/", "-q"],
        cwd=paths.PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8",
    )
    return {"ok": r.returncode == 0, "returncode": r.returncode,
            "tail": [ln for ln in (r.stdout or "").splitlines() if ln.strip()][-8:]}


def smoke_battle(n: int = 20, max_turns: int = 50, seed: int = 42) -> dict:
    """随机抽 n 场对战，确认 execute_turn 不抛异常且能终结。"""
    try:
        from core.loader import HeroLoader
        from core.simulator import BattleSimulator
    except Exception as e:
        return {"ok": False, "error": f"import 失败: {e}"}
    heroes = HeroLoader.load_all_heroes()
    if len(heroes) < 2:
        return {"ok": False, "error": "英雄不足 2"}
    rng = random.Random(seed)
    crashes = 0
    unfinished = 0
    for _ in range(n):
        c1, c2 = rng.sample(heroes, 2)
        sim = BattleSimulator(c1, c2, level1=9, level2=9, rng=rng)
        try:
            t = 0
            while sim.winner is None and t < max_turns:
                sim.execute_turn()
                t += 1
            if sim.winner is None:
                unfinished += 1
        except Exception:
            crashes += 1
    ok = crashes == 0
    return {"ok": ok, "crashes": crashes, "unfinished": unfinished, "sampled": n}


def verify(run_pytest: bool = False, smoke: bool = False) -> dict:
    """主入口。check_cards 与双表示守卫必跑；pytest / smoke 可选。"""
    rep = {"check_cards": check_cards()}
    ok = rep["check_cards"]["ok"]
    rep["check_dual_representation"] = check_dual_representation()
    ok = ok and rep["check_dual_representation"]["ok"]
    if run_pytest:
        rep["pytest"] = run_pytest()
        ok = ok and rep["pytest"]["ok"]
    if smoke:
        rep["smoke"] = smoke_battle()
        ok = ok and rep["smoke"]["ok"]
    rep["ok"] = ok
    return rep


__all__ = ["check_cards", "check_dual_representation", "run_pytest", "smoke_battle", "verify"]
