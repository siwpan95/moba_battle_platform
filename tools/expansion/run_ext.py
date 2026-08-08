#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IP 扩充编排器（第二批 _ext 模块）。

扫描 tools/expansion/ip_*_ext.py，把每个模块声明的新英雄编译写入：
  - data/skills/<game_id>/<hero>.json   技能血肉
  - data/source/<game_id>/heroes.json   源名册
  - data/analysis/all_heroes_unified.json  统一名册

builder.write_ip 是幂等的：同名英雄覆盖技能、unified 按 (game,name) 去重。

用法::

    python -m tools.expansion.run_ext --check        # 仅编译校验
    python -m tools.expansion.run_ext                # 校验 + 写盘
    python -m tools.expansion.run_ext --cards        # 写盘后重生成本 IP 角色卡
"""

from __future__ import annotations

import argparse
import importlib
import os
import pkgutil
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tools.expansion.builder import (  # noqa: E402
    ROLE_BAND, compile_hero, dice_expectation, write_ip,
)


def _discover_ext_modules() -> list[str]:
    """返回所有 tools/expansion/ip_*_ext.py 的模块后缀名（去掉 ip_ 前缀和 _ext 后缀）。"""
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    out = []
    for fn in os.listdir(pkg_dir):
        if fn.startswith("ip_") and fn.endswith("_ext.py"):
            # ip_chinese_ext.py -> chinese
            mid = fn[len("ip_"):-len("_ext.py")]
            out.append(mid)
    return sorted(out)


def _load(ip: str):
    return importlib.import_module(f"tools.expansion.ip_{ip}_ext")


def check(ip: str) -> tuple[int, int]:
    """编译校验一个 _ext 模块，返回 (英雄数, 技能数)。任一违规抛异常。"""
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
            assert s["type"] in ("物理", "法术", "混合", "真实"), \
                f"{h['name']}/{s['name']} type 非法: {s['type']}"
            assert len(s["description"]) >= 20, \
                f"{h['name']}/{s['name']} 描述过短({len(s['description'])}字)"
        names = [s["name"] for s in sk]
        assert len(set(names)) == 4, f"{h['name']} 技能重名 {names}"
        n_sk += len(sk)
    return len(mod.HEROES), n_sk


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ip", help="单个 _ext 后缀，如 chinese")
    ap.add_argument("--all", action="store_true", help="处理全部 _ext 模块（默认）")
    ap.add_argument("--check", action="store_true", help="仅编译校验，不写盘")
    ap.add_argument("--cards", action="store_true", help="写盘后重新生成角色卡")
    args = ap.parse_args()

    targets = [_discover_ext_modules()] if False else _discover_ext_modules()
    if args.ip:
        targets = [args.ip]
    elif not args.all and not args.ip:
        # 默认全部
        pass
    if not targets:
        print("未发现任何 ip_*_ext.py 模块。")
        return 0

    # 跳过导入失败的模块
    ready = []
    for ip in targets:
        try:
            _load(ip)
            ready.append(ip)
        except Exception as e:
            print(f"  · 跳过 {ip}_ext（导入失败: {e}）")
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
        displays.append((mod.DISPLAY, mod.GAME_ID))
        print(f"  → 写入 {mod.GAME_ID}: 新增 {res['new']} / 技能文件 {res['skills']} / "
              f"source 共 {res['total_source']}")

    if args.cards:
        print("\n重新生成角色卡 …")
        for disp, gid in displays:
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
