#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Headless 对战模拟入口（自动化 / 定时任务专用，无需 GUI）。

流程：
  1. core.loader.load_all_heroes() 扫描全部角色卡
  2. 随机抽取 2 名英雄（1 级），BattleSimulator 跑完整对战
  3. 逐回合日志 + 胜负摘要写入 output/battle_YYYYMMDD_HHMMSS.log（UTF-8）
  4. stdout 打印单行摘要（便于自动化捕获退出状态）

用法：
  E:\\moba_battle_platform\\.venv\\Scripts\\python.exe run_battle.py
  python run_battle.py --level 18          # 指定等级
  python run_battle.py --seed 42           # 固定随机种子（可复现）
  python run_battle.py --rounds 3          # 连跑 3 场，每场独立日志

退出码：0 = 至少完成一场对战；1 = 加载/运行异常未产出任何日志。
"""

import argparse
import datetime as _dt
import os
import random
import sys

# 让脚本无论从哪个 cwd 调用都能 import core（PYTHONSAFEPATH 友好）
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

OUTPUT_DIR = os.path.join(_PROJECT_ROOT, "output")


def _reconfigure_stdout():
    """Windows 控制台 GBK 坑兜底：重定向/管道用 UTF-8，TTY 仅容错。"""
    try:
        enc = sys.stdout.encoding.lower()
    except Exception:
        enc = ""
    if sys.stdout.isatty() and enc in ("cp936", "gbk", ""):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    elif not sys.stdout.isatty():
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _run_one_battle(level: int, seed=None) -> dict:
    """跑一场对战，返回结果 dict。失败抛异常由上层捕获。"""
    from core.loader import load_all_heroes
    from core.simulator import BattleSimulator

    heroes = load_all_heroes()
    if not heroes:
        raise RuntimeError("load_all_heroes() 返回空列表：角色卡目录缺失或无可用卡")

    rng = random.Random(seed)
    c1, c2 = rng.sample(heroes, 2)
    sim = BattleSimulator(c1, c2, level1=level, level2=level, rng=rng)

    # simulator.execute_turn() 返回当回合 logs 但不累积到 sim.logs（设计如此），
    # 调用方需自行累积全部回合日志。
    all_logs = []
    while not sim.is_over:
        all_logs.extend(sim.execute_turn())

    g1 = c1.get("game", {}).get("name", "?")
    g2 = c2.get("game", {}).get("name", "?")
    return {
        "hero1": sim.hero1, "game1": g1,
        "hero2": sim.hero2, "game2": g2,
        "level": level,
        "winner": sim.winner,
        "rounds": sim.rounds,
        "hp1": sim.hp1, "max_hp1": sim.max_hp1,
        "hp2": sim.hp2, "max_hp2": sim.max_hp2,
        "logs": all_logs,
    }


def _format_result(r: dict) -> str:
    winner_txt = {
        1: f"{r['hero1']} 胜", 2: f"{r['hero2']} 胜", 0: "平局"
    }.get(r["winner"], "未知")
    header = (
        f"=== 对战结果 ===\n"
        f"时间: {_dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"等级: Lv{r['level']}\n"
        f"方1: [{r['game1']}] {r['hero1']}  HP {r['hp1']}/{r['max_hp1']}\n"
        f"方2: [{r['game2']}] {r['hero2']}  HP {r['hp2']}/{r['max_hp2']}\n"
        f"胜负: {winner_txt}  |  回合数: {r['rounds']}\n"
        f"--- 战斗日志 ---\n"
    )
    body = "\n".join(r["logs"]) if r["logs"] else "(无日志)"
    return header + body + "\n"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="MOBA headless 对战模拟")
    p.add_argument("--level", type=int, default=1, help="双方等级 1-18（默认 1）")
    p.add_argument("--seed", type=int, default=None, help="随机种子（可复现）")
    p.add_argument("--rounds", type=int, default=1, help="连跑场数（默认 1）")
    args = p.parse_args(argv)

    _reconfigure_stdout()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    ok = 0
    for i in range(max(1, args.rounds)):
        # 每场独立种子：未给 seed 则用系统随机，避免 N 场完全相同
        seed = args.seed if args.seed is not None else random.randrange(2**31)
        stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = os.path.join(OUTPUT_DIR, f"battle_{stamp}_{i+1}.log")
        try:
            res = _run_one_battle(args.level, seed)
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(_format_result(res))
            ok += 1
            winner_txt = {1: res["hero1"], 2: res["hero2"], 0: "平局"}.get(
                res["winner"], "?")
            print(f"[OK] {stamp} 场{i+1} | [{res['game1']}] {res['hero1']} vs "
                  f"[{res['game2']}] {res['hero2']} | {winner_txt} 胜 | "
                  f"{res['rounds']}回合 | 日志: {log_path}")
        except Exception as e:
            # 单场失败不阻断后续场；错误也落盘便于排查
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(f"=== 对战异常 ===\n时间: {stamp}\n错误: {e!r}\n")
            print(f"[FAIL] {stamp} 场{i+1} | {e!r} | 日志: {log_path}",
                  file=sys.stderr)

    return 0 if ok > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
