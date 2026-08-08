#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IP 扩充编排器。

用法::

    python -m tools.expansion.run --check              # 仅编译校验，不写盘
    python -m tools.expansion.run --ip egyptian        # 写入单个 IP
    python -m tools.expansion.run --all                # 写入全部 IP
    python -m tools.expansion.run --all --cards        # 写入并重新生成角色卡

写盘顺序（重要）：先写 data/skills/<ip>/ 技能池，再更新
data/analysis/all_heroes_unified.json，最后跑 card_tool generate ——
因为 card_generator.get_skills() 会从技能池读取"血肉"注入角色卡。
"""

from __future__ import annotations

import argparse
import importlib
import os
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tools.expansion.builder import (  # noqa: E402
    ROLE_BAND, compile_hero, dice_expectation, write_ip,
)

# 已就绪的 IP 素材模块（模块名后缀 -> tools.expansion.ip_<name>）
IP_MODULES = [
    "egyptian", "hindu", "celtic", "japanese", "chinese",
    "slavic", "aztec", "arthurian", "arabian",
]


def _load(ip: str):
    return importlib.import_module(f"tools.expansion.ip_{ip}")


def check(ip: str) -> tuple[int, int]:
    """编译校验一个 IP，返回 (英雄数, 技能数)。任一违规抛异常。"""
    mod = _load(ip)
    n_sk = 0
    for h in mod.HEROES:
        sk = compile_hero(h)
        exp = dice_expectation(sk)
        lo, hi = ROLE_BAND[h["role"]]
        assert lo <= exp <= hi, f"{h['name']} 骰期望 {exp} 越界 [{lo},{hi}]"
        assert [s["cooldown"] for s in sk] == [0, 1, 2, 4], f"{h['name']} CD 异常"
        for s in sk:
            assert s["name"], f"{h['name']} 技能名缺失"
            assert s["type"] in ("物理", "法术", "混合", "真实"), f"{h['name']}/{s['name']} type 非法"
            assert len(s["description"]) >= 20, f"{h['name']}/{s['name']} 描述过短"
        names = [s["name"] for s in sk]
        assert len(set(names)) == 4, f"{h['name']} 技能重名 {names}"
        n_sk += len(sk)
    return len(mod.HEROES), n_sk


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ip", help="单个 IP 后缀，如 egyptian")
    ap.add_argument("--all", action="store_true", help="处理全部已就绪 IP")
    ap.add_argument("--check", action="store_true", help="仅编译校验")
    ap.add_argument("--cards", action="store_true", help="写盘后重新生成角色卡")
    args = ap.parse_args()

    targets = IP_MODULES if args.all else ([args.ip] if args.ip else [])
    if not targets:
        ap.error("需指定 --ip 或 --all")

    # 跳过尚未编写素材的 IP
    ready = []
    for ip in targets:
        try:
            _load(ip)
            ready.append(ip)
        except ModuleNotFoundError:
            print(f"  · 跳过 {ip}（素材模块未就绪）")
    targets = ready

    total_h = total_s = 0
    for ip in targets:
        n_h, n_s = check(ip)
        total_h += n_h
        total_s += n_s
        print(f"  ✓ {ip:12s} 编译通过：{n_h} 英雄 / {n_s} 技能")
    print(f"\n编译校验合计：{total_h} 英雄 / {total_s} 技能")

    if args.check:
        return 0

    displays = []
    for ip in targets:
        mod = _load(ip)
        res = write_ip(mod.GAME_ID, mod.DISPLAY, mod.SOURCE_CN, mod.HEROES)
        displays.append(mod.DISPLAY)
        print(f"  → 写入 {mod.GAME_ID}: 新增 {res['new']} / 技能文件 {res['skills']} / "
              f"source 共 {res['total_source']}")

    if args.cards:
        print("\n重新生成角色卡 …")
        for disp in displays:
            r = subprocess.run(
                [sys.executable, os.path.join(PROJECT_ROOT, "tools", "card_tool.py"),
                 "generate", "--game", disp],
                cwd=os.path.join(PROJECT_ROOT, "tools"),
                capture_output=True, text=True, encoding="utf-8",
            )
            tail = [ln for ln in (r.stdout or "").splitlines() if "✓" in ln or "完成" in ln]
            print(f"  {disp}: " + (" | ".join(tail) if tail else (r.stderr or "")[-200:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
