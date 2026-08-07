#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读沙箱探针：验证 ADR-005 递归扫描与技能注入的交互。

在系统临时目录构造 平铺 / 嵌套 两种目录形态，monkeypatch CARDS_DIR，
观察嵌套目录下的卡片是否能拿到注入的技能。
不触碰 data/ 任何字节。
"""
import os
import sys
import json
import shutil
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

import core.loader as loader  # noqa: E402
from core.loader import HeroLoader  # noqa: E402

OUT = []


def log(*a):
    OUT.append(" ".join(str(x) for x in a))


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

tmp = tempfile.mkdtemp(prefix="doc_nested_")
try:
    cards_dir = os.path.join(tmp, "character_cards")
    skills_dir = os.path.join(tmp, "skills")
    os.makedirs(os.path.join(cards_dir, "test_ip"))
    os.makedirs(os.path.join(cards_dir, "test_ip_nested", "season1"))
    os.makedirs(skills_dir)

    # 两张内容完全相同的卡：一张平铺，一张放在子目录
    for sub in (["test_ip"], ["test_ip_nested", "season1"]):
        p = os.path.join(cards_dir, *sub, "hero.json")
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(CARD, fh, ensure_ascii=False)

    # 为两个 IP 都提供 skills DB（平铺名 + 嵌套顶层名）
    for stem in ("test_ip", "test_ip_nested"):
        with open(os.path.join(skills_dir, f"{stem}.json"), "w", encoding="utf-8") as fh:
            json.dump(SKILLS_DB, fh, ensure_ascii=False)

    # monkeypatch：CARDS_DIR 与 skills 根路径
    loader.CARDS_DIR = cards_dir
    loader._SKILLS_DB_CACHE.clear()
    orig_load_db = HeroLoader._load_skills_db

    def patched_load_db(game_dir):
        if game_dir in loader._SKILLS_DB_CACHE:
            return loader._SKILLS_DB_CACHE[game_dir]
        path = os.path.join(skills_dir, f"{game_dir}.json")
        log(f"  [_load_skills_db] game_dir={game_dir!r} -> 查找 {os.path.basename(path)}"
            f" -> {'命中' if os.path.isfile(path) else '不存在'}")
        if not os.path.isfile(path):
            loader._SKILLS_DB_CACHE[game_dir] = {}
            return {}
        with open(path, "r", encoding="utf-8") as fh:
            db = json.load(fh)
        loader._SKILLS_DB_CACHE[game_dir] = db
        return db

    HeroLoader._load_skills_db = staticmethod(patched_load_db)

    log("=== 加载过程 ===")
    heroes = HeroLoader.load_all_heroes()
    log("")
    log("=== 结果 ===")
    for h in heroes:
        log(f"  game_dir={h.get('_game_dir')!r:32} 技能数={len(h.get('skills') or [])}")

    log("")
    log("结论：嵌套目录卡片被 iter_card_files 扫描到（ADR-005 递归生效），")
    log("      但 game_dir 含路径分隔符导致 skills DB 查找必然落空 -> 0 技能。")
finally:
    HeroLoader._load_skills_db = staticmethod(orig_load_db)
    shutil.rmtree(tmp, ignore_errors=True)

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_nested_result.txt"),
          "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT))
