#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""迁移脚本：把 dict 格式 skills 的角色卡改写为 list[skill]（A4 永久修复）。

背景：角色卡库约 42.2%（700/1659 张）skills 为「扁平单技能 dict」，
导致 simulator 用整数下标访问时开战即崩（SEV-2）。本脚本把磁盘数据
永久归一化为 list 格式，从根消除双 schema。

- 扁平单技能 dict（字段名键：name/key/type/...）→ [原始 dict]（保留全部真实字段）
- 槽位键 dict（'0'/'1'/'2'/'3'）→ 按槽位排序的 list
- 已是 list / 缺失 → 不动

用法：
    python tools/migrate_skills_format.py --dry-run
    python tools/migrate_skills_format.py
"""
import json
import os
import argparse
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARDS_DIR = os.path.join(PROJECT_ROOT, "data", "character_cards")
sys.path.insert(0, PROJECT_ROOT)

from core import schema  # 单一真相：归一化逻辑集中在 core.schema（ADR-001）


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只统计不写盘")
    args = ap.parse_args()

    changed = 0
    scanned = 0
    for root, _, files in os.walk(CARDS_DIR):
        for fn in files:
            if not fn.endswith(".json") or fn.startswith("_"):
                continue
            path = os.path.join(root, fn)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    card = json.load(f)
            except Exception as e:
                print(f"[跳过] 解析失败 {path}: {e}")
                continue
            scanned += 1
            skills = card.get("skills")
            if isinstance(skills, list):
                continue
            normalized, _warnings = schema.normalize_skills(skills)
            if isinstance(skills, list):
                continue
            changed += 1
            if args.dry_run:
                continue
            card["skills"] = normalized
            with open(path, "w", encoding="utf-8") as f:
                json.dump(card, f, ensure_ascii=False, indent=2)

    print(f"扫描角色卡: {scanned}")
    print(f"将改写(dict→list): {changed}" + ("（dry-run，未写盘）" if args.dry_run else "（已写盘）"))


if __name__ == "__main__":
    main()
