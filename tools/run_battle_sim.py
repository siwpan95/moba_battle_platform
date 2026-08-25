#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对战模拟测试 —— 批量跑真实英雄卡对战，保留完整逐回合日志。

用法：
    python tools/run_battle_sim.py                     # 默认 30 场，9 级，种子 2026
    python tools/run_battle_sim.py -n 100 --level 12
    python tools/run_battle_sim.py -n 50 --ip mythology_greek
    python tools/run_battle_sim.py --hero1 "宙斯" --hero2 "雅典娜" -n 5

产物（默认写入 logs/）：
    logs/battle_<时间戳>.log    逐回合完整对战日志（UTF-8 文本）
    logs/battle_<时间戳>.json   结构化结果汇总（每场胜负/回合数/剩余血量 + 总体统计）
"""

import argparse
import json
import os
import random
import sys
import time
from collections import Counter
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.loader import HeroLoader                      # noqa: E402
from core.simulator import BattleSimulator              # noqa: E402
from core.paths import PROJECT_ROOT                     # noqa: E402


def pick_heroes(heroes, ip=None, name=None):
    """按 IP 目录 / 英雄名过滤英雄卡。"""
    out = heroes
    if ip:
        out = [h for h in out if ip in (h.get("_game_dir") or "")]
    if name:
        key = HeroLoader._norm_name(name)
        out = [h for h in out
               if key in HeroLoader._norm_name(h.get("hero", {}).get("name", ""))
               or key in HeroLoader._norm_name(h.get("_filename", ""))]
    return out


def hero_label(card):
    game = card.get("game", {}).get("name") or card.get("_game_dir", "?")
    return f"{card.get('hero', {}).get('name', '?')}[{game}]"


def run_one(c1, c2, level1, level2, rng, max_turns):
    """跑单场对战，返回 (结果 dict, 日志行列表)。"""
    sim = BattleSimulator(c1, c2, level1=level1, level2=level2, rng=rng)
    lines = []
    header = (f"{hero_label(c1)} (Lv{sim.level1}, HP {sim.max_hp1}) "
              f"VS {hero_label(c2)} (Lv{sim.level2}, HP {sim.max_hp2})"
              f"   先手: {'P1' if sim.first_mover == 1 else 'P2'}")
    lines.append(header)

    t0 = time.perf_counter()
    error = None
    turns = 0
    try:
        while sim.winner is None and turns < max_turns:
            turn_logs = sim.execute_turn()
            turns += 1
            lines.extend(turn_logs)
    except Exception as e:  # 崩溃也要留证据
        error = f"{type(e).__name__}: {e}"
        lines.append(f"!!! 引擎异常: {error}")
    elapsed = time.perf_counter() - t0

    if sim.winner == 1:
        verdict = f"胜者: {hero_label(c1)}"
    elif sim.winner == 2:
        verdict = f"胜者: {hero_label(c2)}"
    elif sim.winner == 0:
        verdict = "平局"
    else:
        verdict = f"未分胜负（达到 max_turns={max_turns}）"
    lines.append(f"—— 结束于第 {turns} 回合 | {verdict} | "
                 f"HP {sim.hp1}/{sim.max_hp1} vs {sim.hp2}/{sim.max_hp2} | "
                 f"耗时 {elapsed*1000:.1f}ms")

    result = {
        "p1": hero_label(c1), "p2": hero_label(c2),
        "level1": sim.level1, "level2": sim.level2,
        "first_mover": sim.first_mover,
        "winner": sim.winner, "turns": turns,
        "hp1": sim.hp1, "max_hp1": sim.max_hp1,
        "hp2": sim.hp2, "max_hp2": sim.max_hp2,
        "finished": sim.winner is not None,
        "error": error,
        "elapsed_ms": round(elapsed * 1000, 2),
        "log_lines": len(lines),
    }
    return result, lines


def main(argv=None):
    ap = argparse.ArgumentParser(description="对战模拟测试并保留日志")
    ap.add_argument("-n", "--num", type=int, default=30, help="对战场次（默认 30）")
    ap.add_argument("--level", type=int, default=9, help="双方等级（默认 9）")
    ap.add_argument("--level2", type=int, default=None, help="P2 等级（默认同 --level）")
    ap.add_argument("--seed", type=int, default=2026, help="随机种子（默认 2026）")
    ap.add_argument("--max-turns", type=int, default=200, help="单场回合上限（默认 200）")
    ap.add_argument("--ip", default=None, help="限定 IP 目录关键字，如 mythology_greek")
    ap.add_argument("--hero1", default=None, help="固定 P1 英雄名（模糊匹配）")
    ap.add_argument("--hero2", default=None, help="固定 P2 英雄名（模糊匹配）")
    ap.add_argument("--outdir", default=os.path.join(PROJECT_ROOT, "logs"), help="日志输出目录")
    # —— 日志润色（可选，不影响原有测试流程）——
    ap.add_argument("--polish", action="store_true",
                    help="测试结束后调用 DeepSeek 把对战日志润色为武侠短篇")
    ap.add_argument("--polish-num", type=int, default=1,
                    help="润色前 N 场（默认 1；配合 --polish 使用）")
    ap.add_argument("--polish-master", default=None,
                    help="固定港漫名家风格（默认从名单随机）")
    ap.add_argument("--polish-model", default="deepseek-v4-pro", help="润色所用模型")
    ap.add_argument("--api-key", default=None, help="DeepSeek API Key")
    a = ap.parse_args(argv)

    level2 = a.level2 if a.level2 is not None else a.level

    print("正在加载英雄卡…")
    heroes = HeroLoader.load_all_heroes()
    print(f"已加载英雄卡: {len(heroes)}")

    pool = pick_heroes(heroes, ip=a.ip)
    if len(pool) < 2:
        print(f"[错误] 可用英雄不足 2（ip={a.ip}）", file=sys.stderr)
        return 2

    pool1 = pick_heroes(pool, name=a.hero1) if a.hero1 else pool
    pool2 = pick_heroes(pool, name=a.hero2) if a.hero2 else pool
    if not pool1 or not pool2:
        print("[错误] hero1/hero2 未匹配到英雄", file=sys.stderr)
        return 2

    rng = random.Random(a.seed)
    os.makedirs(a.outdir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(a.outdir, f"battle_{stamp}.log")
    json_path = os.path.join(a.outdir, f"battle_{stamp}.json")

    results = []
    winners = Counter()
    with open(log_path, "w", encoding="utf-8") as fp:
        fp.write("=" * 78 + "\n")
        fp.write(f"MOBA 对战模拟测试日志\n")
        fp.write(f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
        fp.write(f"场次: {a.num} | 等级: P1={a.level} P2={level2} | 种子: {a.seed} | "
                 f"回合上限: {a.max_turns}\n")
        fp.write(f"英雄池: {len(pool)}（IP 过滤: {a.ip or '全部'}）\n")
        fp.write("=" * 78 + "\n\n")

        for i in range(1, a.num + 1):
            if a.hero1 or a.hero2:
                c1 = rng.choice(pool1)
                c2 = rng.choice([h for h in pool2 if h is not c1] or pool2)
            else:
                c1, c2 = rng.sample(pool, 2)
            res, lines = run_one(c1, c2, a.level, level2, rng, a.max_turns)
            res["match"] = i
            results.append(res)
            winners[res["winner"]] += 1

            fp.write(f"\n{'─' * 78}\n【第 {i}/{a.num} 场】{lines[0]}\n{'─' * 78}\n")
            for ln in lines[1:]:
                fp.write(ln + "\n")
            print(f"[{i}/{a.num}] {res['p1']} vs {res['p2']} → "
                  f"{'P' + str(res['winner']) if res['winner'] else ('平局' if res['winner'] == 0 else '未终结')}"
                  f" ({res['turns']} 回合)")

        crashes = [r for r in results if r["error"]]
        unfinished = [r for r in results if not r["finished"]]
        turn_list = [r["turns"] for r in results]
        summary = {
            "total": len(results),
            "p1_win": winners[1], "p2_win": winners[2], "draw": winners[0],
            "unfinished": len(unfinished),
            "crashes": len(crashes),
            "avg_turns": round(sum(turn_list) / len(turn_list), 2) if turn_list else 0,
            "min_turns": min(turn_list) if turn_list else 0,
            "max_turns_used": max(turn_list) if turn_list else 0,
            "avg_elapsed_ms": round(sum(r["elapsed_ms"] for r in results) / len(results), 2),
            "seed": a.seed, "level1": a.level, "level2": level2,
            "hero_pool": len(pool), "ip_filter": a.ip,
        }

        fp.write("\n" + "=" * 78 + "\n统计汇总\n" + "=" * 78 + "\n")
        for k, v in summary.items():
            fp.write(f"  {k}: {v}\n")
        if crashes:
            fp.write("\n崩溃场次:\n")
            for r in crashes:
                fp.write(f"  #{r['match']} {r['p1']} vs {r['p2']} — {r['error']}\n")

    with open(json_path, "w", encoding="utf-8") as fp:
        json.dump({"summary": summary, "matches": results}, fp,
                  ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print("=" * 60)
    print(f"对战日志: {log_path}")
    print(f"结果汇总: {json_path}")

    if a.polish:
        print("\n" + "=" * 60)
        print("开始润色对战日志为武侠短篇…")
        try:
            from tools.log_polish import polish_log_file, resolve_api_key
            n = max(1, min(a.polish_num, len(results)))
            pr = polish_log_file(
                log_path, resolve_api_key(a.api_key),
                indices=list(range(1, n + 1)),
                master_name=a.polish_master,
                seed=a.seed, outdir=a.outdir,
                model=a.polish_model)
            print(f"润色完成：成功 {pr['ok']} 篇，失败 {pr['failed']} 篇")
            if pr["md"]:
                print(f"武侠短篇: {pr['md']}")
                print(f"短篇汇总: {pr['json']}")
        except Exception as e:
            # 润色失败不影响对战测试本身的结论
            print(f"[润色失败] {type(e).__name__}: {e}", file=sys.stderr)

    return 1 if crashes else 0


if __name__ == "__main__":
    sys.exit(main())
