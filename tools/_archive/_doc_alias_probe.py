#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读探针：别名表是否接受自身的输出类别名作为输入？

若不接受，则数据里写规范类别名（如 type:"control"）反而会被判为未识别 -> flavor。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from core import mechanics  # noqa: E402

OUT = []


def log(*a):
    OUT.append(" ".join(str(x) for x in a))


log("=== 输出类别名 是否被自身别名表接受 ===")
broken = []
for table, name in mechanics._CATEGORY_TABLES:
    got = mechanics.categorize_effect({"type": name})
    ok = (got == name)
    if not ok:
        broken.append(name)
    log(f"   type={name!r:12} -> categorize_effect = {got!r:10} {'OK' if ok else '<<< 自身类别名不被接受'}")

log("")
log(f"自身类别名不被接受的类别 = {broken}")
log("")
log("对应别名表内容:")
for table, name in mechanics._CATEGORY_TABLES:
    if name in broken:
        log(f"   {name:10} = {sorted(table)}")

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_alias_result.txt"),
          "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT))
