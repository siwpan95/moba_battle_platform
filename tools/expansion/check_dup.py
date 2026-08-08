#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""预检查：列出各 _ext 模块中与已有 source/heroes.json 重名的英雄。

builder.write_ip 会无条件覆盖技能文件，所以写入前必须确认 _ext 模块里的
新英雄名不与 source 已有名重复（否则会 clobber 已有技能）。

用法： python -m tools.expansion.check_dup
"""

from __future__ import annotations

import importlib
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

SOURCE_DIR = os.path.join(PROJECT_ROOT, "data", "source")


def _discover_ext() -> list[str]:
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    out = []
    for fn in os.listdir(pkg_dir):
        if fn.startswith("ip_") and fn.endswith("_ext.py"):
            out.append(fn[len("ip_"):-len("_ext.py")])
    return sorted(out)


def main() -> int:
    total_dup = 0
    for ip in _discover_ext():
        try:
            mod = importlib.import_module(f"tools.expansion.ip_{ip}_ext")
        except Exception as e:
            print(f"  ✗ {ip}_ext 导入失败: {e}")
            continue
        src_path = os.path.join(SOURCE_DIR, mod.GAME_ID, "heroes.json")
        existing = set()
        if os.path.exists(src_path):
            with open(src_path, encoding="utf-8") as f:
                existing = {h.get("name") for h in json.load(f)}
        new_names = [h["name"] for h in mod.HEROES]
        # 模块内自重名
        seen = {}
        internal_dup = []
        for n in new_names:
            seen[n] = seen.get(n, 0) + 1
            if seen[n] == 2:
                internal_dup.append(n)
        # 与 source 重名
        cross_dup = [n for n in new_names if n in existing]
        status = "OK" if not (internal_dup or cross_dup) else "DUP"
        print(f"  [{status}] {ip:10s} 新增={len(new_names):3d} 模块内重名={internal_dup} 与source重名={cross_dup[:10]}{'...' if len(cross_dup)>10 else ''}")
        total_dup += len(internal_dup) + len(cross_dup)
    print(f"\n合计冲突 {total_dup} 处")
    return 0 if total_dup == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
