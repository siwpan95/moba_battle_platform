#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读探针：核验 skills 注入契约（game_dir <-> data/skills/<game_dir>.json）。

由技术文档师用于文档准确性核验，不参与运行时，不写入任何数据。
"""
import os
import sys
import glob
import json

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from core.loader import iter_card_files, HeroLoader  # noqa: E402

CARDS = os.path.join(ROOT, "data", "character_cards")
SKILLS = os.path.join(ROOT, "data", "skills")

OUT = []


def print(*args, **kwargs):  # noqa: A001 - 重定向到 UTF-8 文件，规避 Windows 控制台编码
    OUT.append(" ".join(str(a) for a in args))


dirs = {}
nested = set()
for fp, rel, stem in iter_card_files(CARDS):
    dirs.setdefault(rel, 0)
    dirs[rel] += 1
    if os.sep in rel or "/" in rel:
        nested.add(rel)

print("game_dir 取值数 =", len(dirs))
print("嵌套 game_dir 数 =", len(nested), sorted(nested)[:5])

db_files = set(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(SKILLS, "*.json")))
print("skills DB 文件数 =", len(db_files))

missing = sorted(d for d in dirs if d not in db_files)
print("有卡目录但无 skills DB 的 IP =", len(missing))
for m in missing[:15]:
    print("   -", m, f"({dirs[m]} 张卡)")

# 逐卡核验：注入是否命中
miss_hero = 0
hit = 0
no_db = 0
samples = []
for fp, rel, stem in iter_card_files(CARDS):
    try:
        with open(fp, "r", encoding="utf-8") as fh:
            card = json.load(fh)
    except Exception:
        continue
    db = HeroLoader._load_skills_db(rel)
    if not db:
        no_db += 1
        continue
    hero = card.get("hero", {})
    if hero.get("name") in db or (hero.get("name_en") and hero.get("name_en") in db):
        hit += 1
    else:
        miss_hero += 1
        if len(samples) < 8:
            samples.append((rel, hero.get("name"), type(card.get("skills")).__name__))

print()
print(f"注入命中 = {hit}")
print(f"DB 存在但英雄名未命中 = {miss_hero}")
print(f"该 IP 无 DB 文件 = {no_db}")
print("未命中样本 (game_dir, hero.name, 磁盘 skills 类型):")
for s in samples:
    print("   ", s)

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_probe_result.txt"),
          "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT))
