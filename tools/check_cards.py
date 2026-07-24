#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CI 卡数据契约校验（A7 门禁）。

扫描 data/character_cards 下全部角色卡，发现以下情况即非零退出，阻断合并/发布：
  - 仍存在 dict 格式 skills（双 schema 残留，事故 SEV-2 根因）
  - 违反 core.schema.validate_card 契约（如缺失 hero.name、属性 modifier、技能 type 非法）

用法：
    python tools/check_cards.py
"""
import sys
import os
import json
import glob

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARDS_DIR = os.path.join(PROJECT_ROOT, "data", "character_cards")
sys.path.insert(0, PROJECT_ROOT)

from core import schema


def main() -> int:
    files = glob.glob(os.path.join(CARDS_DIR, "**", "*.json"), recursive=True)
    errors: list = []
    scanned = 0
    for f in files:
        if os.path.basename(f).startswith("_"):
            continue
        try:
            with open(f, "r", encoding="utf-8") as fh:
                card = json.load(fh)
        except Exception as e:
            errors.append(f"{f}: JSON 解析失败 {e}")
            continue
        scanned += 1
        if isinstance(card.get("skills"), dict):
            errors.append(f"{f}: 仍存在 dict 格式 skills（双 schema 残留，SEV-2 根因）")
        problems = schema.validate_card(card)
        for p in problems:
            errors.append(f"{f}: {p}")

    print(f"契约校验 {scanned} 张卡，发现问题 {len(errors)} 项")
    for e in errors:
        print("  - " + e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
