#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读探针：核验 iter_card_files 的 game_dir=='.' 变体（根目录直属卡片）。

回答两个问题：
  Q1 data/character_cards/ 根目录下当前是否已有直属 .json 卡片？（现存缺陷 or 潜伏问题）
  Q2 若有，_load_skills_db 会拼出什么路径、注入是否必然落空？

不修改 data/ 任何字节；沙箱部分落在系统临时目录。
"""
import os
import sys
import json
import shutil
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

import core.loader as loader  # noqa: E402
from core.loader import iter_card_files, HeroLoader  # noqa: E402
from core.paths import PROJECT_ROOT  # noqa: E402

OUT = []


def log(*a):
    OUT.append(" ".join(str(x) for x in a))


CARDS = os.path.join(ROOT, "data", "character_cards")

# ---------- Q1: 真实仓库根目录直属卡片 ----------
log("=== Q1: data/character_cards/ 根目录直属 .json ===")

all_root_json = sorted(f for f in os.listdir(CARDS)
                       if f.endswith(".json") and os.path.isfile(os.path.join(CARDS, f)))
log(f"根目录全部 .json 文件（含 _ 前缀） = {len(all_root_json)}: {all_root_json}")

# iter_card_files 实际会产出的、game_dir == '.' 的条目
dot_entries = [(fp, rel, stem) for fp, rel, stem in iter_card_files(CARDS) if rel == "."]
log(f"iter_card_files 产出 game_dir=='.' 的卡片数 = {len(dot_entries)}")
for fp, rel, stem in dot_entries[:10]:
    log(f"   - {stem}.json")

log("")
log(f"结论 Q1: {'现存缺陷（根目录已有直属卡）' if dot_entries else '潜伏问题（根目录当前无直属卡，定级维持潜伏）'}")

# ---------- Q2: 路径拼接实证 ----------
log("")
log("=== Q2: game_dir=='.' 时 _load_skills_db 的拼接结果 ===")
constructed = os.path.join(PROJECT_ROOT, "data", "skills", f"{'.'}.json")
log(f"拼接路径 = ...{os.sep}data{os.sep}skills{os.sep}{os.path.basename(constructed)}")
log(f"os.path.isfile 该路径 = {os.path.isfile(constructed)}")
log(f"basename 字面量 = {os.path.basename(constructed)!r}   （即 '..json'）")

# ---------- Q3: 沙箱端到端复现 ----------
log("")
log("=== Q3: 沙箱端到端（根目录直属卡 vs 正常 IP 目录卡）===")

CARD = {
    "card_id": "TST-0001",
    "hero": {"name": "测试英雄"},
    "game": {"name": "Test IP"},
    "attributes": {k: {"score": 12, "modifier": 1}
                   for k in ("STR", "DEX", "CON", "INT", "WIS", "CHA")},
}
SKILLS_DB = {
    "测试英雄": [
        {"name": f"技能{i}", "key": k, "type": "物理", "cooldown": c,
         "damage": {"dice_count": 1, "dice_size": 6, "bonus": 0},
         "effects": [], "description": "d"}
        for i, (k, c) in enumerate(zip("QWER", [0, 1, 2, 4]))
    ]
}

tmp = tempfile.mkdtemp(prefix="doc_rootdir_")
orig_cards_dir = loader.CARDS_DIR
orig_load_db = HeroLoader._load_skills_db
try:
    cards_dir = os.path.join(tmp, "character_cards")
    skills_dir = os.path.join(tmp, "skills")
    os.makedirs(os.path.join(cards_dir, "test_ip"))
    os.makedirs(skills_dir)

    # A: 正常 IP 子目录        B: 直接丢在根目录（新人最自然的动作）
    with open(os.path.join(cards_dir, "test_ip", "hero.json"), "w", encoding="utf-8") as fh:
        json.dump(CARD, fh, ensure_ascii=False)
    with open(os.path.join(cards_dir, "rootcard.json"), "w", encoding="utf-8") as fh:
        json.dump(CARD, fh, ensure_ascii=False)

    with open(os.path.join(skills_dir, "test_ip.json"), "w", encoding="utf-8") as fh:
        json.dump(SKILLS_DB, fh, ensure_ascii=False)

    loader.CARDS_DIR = cards_dir
    # Tessa 提醒的缓存污染：每次沙箱前必须清
    loader._SKILLS_DB_CACHE.clear()

    def patched_load_db(game_dir):
        if game_dir in loader._SKILLS_DB_CACHE:
            log(f"  [_load_skills_db] game_dir={game_dir!r} -> 命中缓存 "
                f"(空={not loader._SKILLS_DB_CACHE[game_dir]})")
            return loader._SKILLS_DB_CACHE[game_dir]
        path = os.path.join(skills_dir, f"{game_dir}.json")
        exists = os.path.isfile(path)
        log(f"  [_load_skills_db] game_dir={game_dir!r} -> 查找 {os.path.basename(path)!r}"
            f" -> {'命中' if exists else '不存在'}")
        if not exists:
            loader._SKILLS_DB_CACHE[game_dir] = {}
            return {}
        with open(path, "r", encoding="utf-8") as fh:
            db = json.load(fh)
        loader._SKILLS_DB_CACHE[game_dir] = db
        return db

    HeroLoader._load_skills_db = staticmethod(patched_load_db)

    heroes = HeroLoader.load_all_heroes()
    log("")
    for h in sorted(heroes, key=lambda x: str(x.get("_game_dir"))):
        log(f"  game_dir={str(h.get('_game_dir'))!r:12} filename={str(h.get('_filename'))!r:12}"
            f" 技能数={len(h.get('skills') or [])}")

    # ---------- Q4: 缓存污染实证（Tessa 提醒的测试陷阱）----------
    log("")
    log("=== Q4: _SKILLS_DB_CACHE 跨用例污染实证 ===")
    log(f"沙箱结束时缓存键 = {sorted(loader._SKILLS_DB_CACHE.keys())}")
    log(f"其中值为空 dict 的键 = {sorted(k for k, v in loader._SKILLS_DB_CACHE.items() if not v)}")
    log("  ^ 这些空值会被后续用例复用，即使那时 DB 实际存在 —— 必须用 fixture 清理")
finally:
    HeroLoader._load_skills_db = staticmethod(orig_load_db)
    loader.CARDS_DIR = orig_cards_dir
    loader._SKILLS_DB_CACHE.clear()
    shutil.rmtree(tmp, ignore_errors=True)

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_rootdir_result.txt"),
          "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT))
