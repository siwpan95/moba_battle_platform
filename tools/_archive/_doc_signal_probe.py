#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读探针：0 技能僵局英雄是否留下可观测信号？

决定 Runbook 能否写"排查时看这条日志"。
捕获 loader 的 stdout/stderr，并复算 check_cards 门禁对同一张卡的判定。
"""
import os
import sys
import io
import json
import shutil
import tempfile
import contextlib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

import core.loader as loader  # noqa: E402
from core.loader import HeroLoader  # noqa: E402
from core import schema  # noqa: E402

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

tmp = tempfile.mkdtemp(prefix="doc_signal_")
orig_cards_dir = loader.CARDS_DIR
try:
    cards_dir = os.path.join(tmp, "character_cards")
    os.makedirs(cards_dir)
    # 根目录直属卡（game_dir='.'），无 skills 键
    with open(os.path.join(cards_dir, "rootcard.json"), "w", encoding="utf-8") as fh:
        json.dump(CARD, fh, ensure_ascii=False)

    loader.CARDS_DIR = cards_dir
    loader._SKILLS_DB_CACHE.clear()

    buf_out, buf_err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
        heroes = HeroLoader.load_all_heroes()

    log("=== loader 运行时信号 ===")
    so = [l for l in buf_out.getvalue().splitlines() if l.strip()]
    se = [l for l in buf_err.getvalue().splitlines() if l.strip()]
    log(f"stdout 行数 = {len(so)}")
    for l in so:
        log("  OUT| " + l)
    log(f"stderr 行数 = {len(se)}")
    for l in se:
        log("  ERR| " + l)
    log(f"加载卡数 = {len(heroes)}, 技能数 = {[len(h.get('skills') or []) for h in heroes]}")

    log("")
    log("=== 门禁 A（check_cards / validate_card）对同一张卡的判定 ===")
    # 门禁读的是磁盘态：skills 键缺失
    with open(os.path.join(cards_dir, "rootcard.json"), "r", encoding="utf-8") as fh:
        disk_card = json.load(fh)
    log(f"磁盘态 skills = {disk_card.get('skills')!r}")
    log(f"validate_card(磁盘态) = {schema.validate_card(disk_card)}  <- 空=通过")

    # 运行时态：注入失败后被归一为 []
    rt = heroes[0]
    log(f"运行时态 skills = {rt.get('skills')!r}")
    log(f"validate_card(运行时态) = {schema.validate_card(rt)}")
finally:
    loader.CARDS_DIR = orig_cards_dir
    loader._SKILLS_DB_CACHE.clear()
    shutil.rmtree(tmp, ignore_errors=True)

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_signal_result.txt"),
          "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT))
