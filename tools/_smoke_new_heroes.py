#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""定向烟雾对战 —— 9 个新公版 IP 主题化技能改名后的对战回归验证。

背景
----
9 个新公版 IP（共 164 英雄）的 656 个技能刚从通用 D&D 名改成主题化名
（只改 skills[*].name，skills 文件与 character_cards 内嵌均已同步）。
本脚本在质量门跑定向烟雾对战，确认改名没有破坏任何对战逻辑。

校验断言（每场对战）
------------------
  A1  全程 execute_turn() 不抛任何异常（捕获并按类型计数）
  A2  每回合后 0 <= hp <= max_hp（双方）
  A3  在 MAX_TURNS(300) 回合内 winner is not None（能终结，无死循环）
  A4  记录耗时 / 胜方 / 总回合数（报告用）
  A0  附加：卡面完整性（4 个技能 + 每个技能 name 非空）—— 直接针对本次改名

判定
----
  0 失败 0 异常                 -> PASS
  仅非崩溃性问题（如未终结）    -> CONCERNS
  出现异常/崩溃                 -> FAIL

用法
----
  F:/Python314/python.exe G:/moba_battle_platform/tools/_smoke_new_heroes.py
  可选参数： --level N (默认 1)   --seed N (默认 20250607)   --verbose

只读脚本：不修改任何 data/ 文件、不修改源码、不提交。
作者：严守真（quality-lead）
"""

import argparse
import os
import random
import sys
import time
import traceback
from collections import Counter, defaultdict

# ── 路径修正 ──
# F:/Python314 解释器会把 sys.path[0] 设为 python zip，必须手动插入项目根目录
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

# 控制台输出中文/emoji 保护
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from core.loader import HeroLoader          # noqa: E402
from core.simulator import BattleSimulator  # noqa: E402

MAX_TURNS = 300

NEW_IPS = [
    "arthurian_legend", "egyptian_mythology", "hindu_mythology",
    "chinese_mythology", "japanese_mythology", "celtic_mythology",
    "slavic_mythology", "aztec_mythology", "arabian_nights",
]

IP_CN = {
    "arthurian_legend": "亚瑟王传说",
    "egyptian_mythology": "埃及神话",
    "hindu_mythology": "印度神话",
    "chinese_mythology": "中国神话",
    "japanese_mythology": "日本神话",
    "celtic_mythology": "凯尔特神话",
    "slavic_mythology": "斯拉夫神话",
    "aztec_mythology": "阿兹特克神话",
    "arabian_nights": "一千零一夜",
}

# ── 18 个代表英雄：每 IP 2 个，6 种 role 全覆盖 ──
# (game_id, 英雄名, 期望role)
ROSTER = [
    ("arthurian_legend",   "亚瑟王",          "fighter"),
    ("arthurian_legend",   "加拉哈德",        "tank"),
    ("egyptian_mythology", "阿努比斯",        "tank"),
    ("egyptian_mythology", "荷鲁斯",          "marksman"),
    ("hindu_mythology",    "湿婆",            "assassin"),
    ("hindu_mythology",    "因陀罗",          "mage"),
    ("chinese_mythology",  "二郎真君",        "fighter"),
    ("chinese_mythology",  "女娲",            "support"),
    ("japanese_mythology", "天照大神",        "mage"),
    ("japanese_mythology", "龙神",            "tank"),
    ("celtic_mythology",   "库丘林",          "fighter"),
    ("celtic_mythology",   "卢",              "marksman"),
    ("slavic_mythology",   "科谢伊",          "assassin"),
    ("slavic_mythology",   "芭芭雅嘎",        "mage"),
    ("aztec_mythology",    "特斯卡特利波卡",  "assassin"),
    ("aztec_mythology",    "查尔奇乌特利奎",  "support"),
    ("arabian_nights",     "阿拉丁",          "assassin"),
    ("arabian_nights",     "山鲁佐德",        "support"),
]

# ── 20 场对战矩阵 ──
# (英雄A, 英雄B, 对战类型标签)
MATCHES = [
    # ① 同 IP 内战 ×9（每个新 IP 一场）
    ("亚瑟王",         "加拉哈德",        "同IP内战·战士vs坦克"),
    ("阿努比斯",       "荷鲁斯",          "同IP内战·坦克vs射手"),
    ("湿婆",           "因陀罗",          "同IP内战·刺客vs法师"),
    ("二郎真君",       "女娲",            "同IP内战·战士vs辅助"),
    ("天照大神",       "龙神",            "同IP内战·法师vs坦克"),
    ("库丘林",         "卢",              "同IP内战·战士vs射手"),
    ("科谢伊",         "芭芭雅嘎",        "同IP内战·刺客vs法师"),
    ("特斯卡特利波卡", "查尔奇乌特利奎",  "同IP内战·刺客vs辅助"),
    ("阿拉丁",         "山鲁佐德",        "同IP内战·刺客vs辅助"),
    # ② 跨 IP 同 role ×6（6 种 role 各一场镜像对决）
    ("亚瑟王",         "库丘林",          "跨IP同role·战士镜像"),
    ("加拉哈德",       "阿努比斯",        "跨IP同role·坦克镜像"),
    ("因陀罗",         "天照大神",        "跨IP同role·法师镜像"),
    ("湿婆",           "科谢伊",          "跨IP同role·刺客镜像"),
    ("荷鲁斯",         "卢",              "跨IP同role·射手镜像"),
    ("女娲",           "山鲁佐德",        "跨IP同role·辅助镜像"),
    # ③ 跨 IP 异 role ×5（典型克制组合）
    ("龙神",           "卢",              "跨IP异role·坦克vs射手"),
    ("芭芭雅嘎",       "阿拉丁",          "跨IP异role·法师vs刺客"),
    ("二郎真君",       "特斯卡特利波卡",  "跨IP异role·战士vs刺客"),
    ("加拉哈德",       "查尔奇乌特利奎",  "跨IP异role·坦克vs辅助"),
    ("天照大神",       "荷鲁斯",          "跨IP异role·法师vs射手"),
]


# ══════════════════════════════════════════════════════════════
#  卡片加载
# ══════════════════════════════════════════════════════════════
def load_new_ip_cards():
    """方案 A：走 HeroLoader 拿运行时一致的卡（含 skills DB 注入），按目录过滤 9 个新 IP。"""
    all_cards = HeroLoader.load_all_heroes()
    pool = defaultdict(dict)  # game_id -> {hero_name: card}
    for c in all_cards:
        gid = (c.get("_game_dir") or "").replace("\\", "/").split("/")[0]
        if gid in NEW_IPS:
            pool[gid][c["hero"]["name"]] = c
    return all_cards, pool


def check_card_integrity(card, expect_role):
    """A0 卡面完整性：4 个技能 + 每个技能 name 非空（直接针对本次改名）。"""
    problems = []
    skills = card.get("skills") or []
    if len(skills) != 4:
        problems.append("技能数=%d（期望4）" % len(skills))
    for i, sk in enumerate(skills):
        if not isinstance(sk, dict):
            problems.append("技能%d 非 dict（%s）" % (i + 1, type(sk).__name__))
            continue
        nm = sk.get("name")
        if not nm or not str(nm).strip():
            problems.append("技能%d name 为空" % (i + 1))
    role = (card.get("game") or {}).get("universal_role")
    if role != expect_role:
        problems.append("role=%s（期望%s）" % (role, expect_role))
    return problems


# ══════════════════════════════════════════════════════════════
#  单场对战
# ══════════════════════════════════════════════════════════════
def run_battle(card1, card2, level, seed, verbose=False):
    """跑一场对战，返回结果 dict。四条断言全部在此校验。"""
    res = {
        "hero1": card1["hero"]["name"], "hero2": card2["hero"]["name"],
        "role1": (card1.get("game") or {}).get("universal_role"),
        "role2": (card2.get("game") or {}).get("universal_role"),
        "winner": None, "turns": 0, "elapsed": 0.0,
        "ok": True, "exc_type": None, "exc_msg": "", "traceback": "",
        "hp_violations": [], "terminated": False,
        "hp1": None, "hp2": None, "max_hp1": None, "max_hp2": None,
    }
    t0 = time.perf_counter()
    try:
        sim = BattleSimulator(card1, card2, level1=level, level2=level,
                              rng=random.Random(seed))
        res["max_hp1"], res["max_hp2"] = sim.max_hp1, sim.max_hp2

        for turn in range(1, MAX_TURNS + 1):
            logs = sim.execute_turn()                     # A1：不得抛异常
            if verbose and logs:
                for ln in logs:
                    print("      " + ln)

            # A2：HP 边界
            if not (0 <= sim.hp1 <= sim.max_hp1):
                res["hp_violations"].append(
                    "T%d %s hp1=%s/%s" % (turn, res["hero1"], sim.hp1, sim.max_hp1))
            if not (0 <= sim.hp2 <= sim.max_hp2):
                res["hp_violations"].append(
                    "T%d %s hp2=%s/%s" % (turn, res["hero2"], sim.hp2, sim.max_hp2))

            res["turns"] = turn
            if sim.winner is not None:                    # A3：能终结
                res["terminated"] = True
                res["winner"] = sim.winner
                break

        res["hp1"], res["hp2"] = sim.hp1, sim.hp2
    except Exception as e:                                # A1 失败
        res["ok"] = False
        res["exc_type"] = type(e).__name__
        res["exc_msg"] = str(e)[:300]
        res["traceback"] = traceback.format_exc()

    res["elapsed"] = time.perf_counter() - t0
    if res["hp_violations"]:
        res["ok"] = False
    if res["ok"] and not res["terminated"]:
        res["ok"] = False                                 # 300 回合未终结
    return res


# ══════════════════════════════════════════════════════════════
#  主流程
# ══════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser(description="9 个新公版 IP 定向烟雾对战")
    ap.add_argument("--level", type=int, default=1, help="双方等级（默认 1）")
    ap.add_argument("--seed", type=int, default=20250607, help="RNG 基准种子（可复现）")
    ap.add_argument("--verbose", action="store_true", help="打印每回合战斗日志")
    args = ap.parse_args()

    print("=" * 78)
    print("  定向烟雾对战 —— 9 个新公版 IP 主题化技能改名回归验证")
    print("  等级=%d  种子=%d  回合上限=%d" % (args.level, args.seed, MAX_TURNS))
    print("=" * 78)

    # ── 加载 ──
    t_load = time.perf_counter()
    all_cards, pool = load_new_ip_cards()
    print("\n[加载] 全库 %d 张卡，%.2fs" % (len(all_cards), time.perf_counter() - t_load))
    total_new = sum(len(v) for v in pool.values())
    print("[加载] 9 个新 IP 命中 %d 英雄：" % total_new)
    for gid in NEW_IPS:
        print("        %-22s %-8s %3d 英雄" % (gid, IP_CN[gid], len(pool[gid])))

    # ── 取代表英雄 + A0 完整性检查 ──
    print("\n" + "-" * 78)
    print("  代表英雄（%d 个）与卡面完整性检查" % len(ROSTER))
    print("-" * 78)
    cards = {}
    integrity_fail = []
    missing = []
    by_ip = defaultdict(list)
    role_count = Counter()

    for gid, name, expect_role in ROSTER:
        card = pool.get(gid, {}).get(name)
        if card is None:
            missing.append("%s/%s" % (gid, name))
            print("  [缺失] %-14s (%s)" % (name, gid))
            continue
        cards[name] = card
        by_ip[gid].append((name, expect_role))
        role_count[expect_role] += 1
        probs = check_card_integrity(card, expect_role)
        skill_names = [s.get("name") for s in card.get("skills", []) if isinstance(s, dict)]
        if probs:
            integrity_fail.append((name, probs))
            print("  [异常] %-14s %-9s %s" % (name, expect_role, "; ".join(probs)))
        else:
            print("  [OK]   %-14s %-9s %-12s 技能: %s"
                  % (name, expect_role, IP_CN[gid], " / ".join(skill_names)))

    print("\n  role 覆盖: %s" % dict(role_count))
    all_roles = {"fighter", "mage", "tank", "assassin", "marksman", "support"}
    missing_roles = all_roles - set(role_count)
    print("  6 role 全覆盖: %s" % ("是" if not missing_roles else "否，缺 %s" % missing_roles))
    print("  9 IP 全覆盖: %s" % ("是" if len(by_ip) == 9 else "否，仅 %d" % len(by_ip)))

    if missing:
        print("\n[致命] 以下英雄未找到，无法继续：%s" % ", ".join(missing))
        return 2

    # ── 跑对战 ──
    print("\n" + "-" * 78)
    print("  对战执行（%d 场）" % len(MATCHES))
    print("-" * 78)
    print("  %-3s %-31s %-21s %-10s %-6s %s"
          % ("#", "对阵", "类型", "胜方", "回合", "耗时"))
    print("  " + "-" * 74)

    results = []
    for idx, (h1, h2, tag) in enumerate(MATCHES, 1):
        c1, c2 = cards.get(h1), cards.get(h2)
        if c1 is None or c2 is None:
            print("  %-3d [跳过] %s vs %s（英雄缺失）" % (idx, h1, h2))
            continue
        r = run_battle(c1, c2, args.level, args.seed + idx, verbose=args.verbose)
        r["idx"], r["tag"] = idx, tag
        results.append(r)

        vs = "%s(%s) vs %s(%s)" % (h1, r["role1"], h2, r["role2"])
        if r["exc_type"]:
            win = "异常:" + r["exc_type"]
        elif not r["terminated"]:
            win = "未终结!"
        elif r["winner"] == 1:
            win = h1[:8]
        elif r["winner"] == 2:
            win = h2[:8]
        else:
            win = "平局"
        flag = "" if r["ok"] else "   <<< FAIL"
        print("  %-3d %-31s %-21s %-10s %-6d %.3fs%s"
              % (idx, vs, tag, win, r["turns"], r["elapsed"], flag))
        if r["hp_violations"]:
            for v in r["hp_violations"][:3]:
                print("        [HP越界] " + v)
        if r["traceback"]:
            for ln in r["traceback"].strip().splitlines()[-4:]:
                print("        | " + ln)

    # ── 汇总 ──
    total = len(results)
    passed = sum(1 for r in results if r["ok"])
    failed = total - passed
    exc_types = Counter(r["exc_type"] for r in results if r["exc_type"])
    hp_bad = [r for r in results if r["hp_violations"]]
    unterminated = [r for r in results if not r["exc_type"] and not r["terminated"]]

    print("\n" + "=" * 78)
    print("  汇总")
    print("=" * 78)
    print("  总场次        : %d" % total)
    print("  PASS          : %d" % passed)
    print("  失败          : %d" % failed)
    print("  抛异常场次    : %d %s"
          % (sum(exc_types.values()), dict(exc_types) if exc_types else ""))
    print("  HP 越界场次   : %d" % len(hp_bad))
    print("  300回合未终结 : %d" % len(unterminated))
    print("  卡面完整性异常: %d" % len(integrity_fail))

    if results:
        turns = [r["turns"] for r in results if r["terminated"]]
        if turns:
            print("\n  回合数分布    : min=%d  max=%d  avg=%.1f"
                  % (min(turns), max(turns), sum(turns) / len(turns)))
        print("  总耗时        : %.2fs（单场均 %.3fs）"
              % (sum(r["elapsed"] for r in results),
                 sum(r["elapsed"] for r in results) / len(results)))
        w1 = sum(1 for r in results if r["winner"] == 1)
        w2 = sum(1 for r in results if r["winner"] == 2)
        print("  胜方分布      : P1=%d  P2=%d  未决=%d" % (w1, w2, total - w1 - w2))
        long_games = [r for r in results if r["terminated"] and r["turns"] >= MAX_TURNS * 0.5]
        if long_games:
            print("  超长对局(>=150回合): %d 场" % len(long_games))
            for r in long_games:
                print("        #%d %s vs %s -> %d 回合"
                      % (r["idx"], r["hero1"], r["hero2"], r["turns"]))

    # ── QA 判定 ──
    crash = sum(exc_types.values()) > 0 or len(hp_bad) > 0
    concern = len(unterminated) > 0 or len(integrity_fail) > 0

    print("\n" + "=" * 78)
    if crash:
        verdict, code = "FAIL", 1
        print("  QA 判定：FAIL —— 存在崩溃性失败（异常或 HP 越界），改名可能破坏对战逻辑")
    elif concern:
        verdict, code = "CONCERNS", 0
        print("  QA 判定：CONCERNS —— 无崩溃，但存在非崩溃性问题（见下）")
    else:
        verdict, code = "PASS", 0
        print("  QA 判定：PASS —— %d 场对战 0 异常 0 越界 0 卡死，改名未破坏对战逻辑" % total)
    print("=" * 78)

    if crash or concern:
        print("\n  问题清单：")
        for r in results:
            if r["exc_type"]:
                print("    - #%d %s vs %s -> %s: %s"
                      % (r["idx"], r["hero1"], r["hero2"], r["exc_type"], r["exc_msg"]))
            for v in r["hp_violations"]:
                print("    - #%d %s vs %s -> HP越界 %s"
                      % (r["idx"], r["hero1"], r["hero2"], v))
            if not r["exc_type"] and not r["terminated"]:
                print("    - #%d %s vs %s -> %d 回合未分胜负（HP %s/%s vs %s/%s）"
                      % (r["idx"], r["hero1"], r["hero2"], r["turns"],
                         r["hp1"], r["max_hp1"], r["hp2"], r["max_hp2"]))
        for name, probs in integrity_fail:
            print("    - 卡面 %s: %s" % (name, "; ".join(probs)))

    print("\n[verdict] %s" % verdict)
    return code


if __name__ == "__main__":
    sys.exit(main())
