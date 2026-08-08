#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""路径引导 + 项目根解析。

battle_platform/ 是 G:/moba_battle_platform/ 的子目录；真正的引擎
（core/ data/ tools/）在父目录。本模块在 import 时把父目录与 tools/
加入 sys.path，使包内任何模块都能 `from core...` / `from tools...`。
"""

import os
import sys

# battle_platform 目录本身
BP_DIR = os.path.dirname(os.path.abspath(__file__))
# 项目根：battle_platform 的父目录，即 G:/moba_battle_platform
PROJECT_ROOT = os.path.dirname(BP_DIR)
TOOLS_DIR = os.path.join(PROJECT_ROOT, "tools")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
SKILLS_DIR = os.path.join(DATA_DIR, "skills")        # data/skills/<game_id>/<英雄>.json
CARDS_DIR = os.path.join(DATA_DIR, "character_cards")
SOURCE_DIR = os.path.join(DATA_DIR, "source")
ANALYSIS_DIR = os.path.join(DATA_DIR, "analysis")

# embeddable Python（F:/Python314）不会自动把脚本目录加入 sys.path，
# 且 ._pth / PYTHONSAFEPATH 会禁用该行为 → 必须显式引导。
for _p in (PROJECT_ROOT, TOOLS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# 运行 Python 解释器（与项目约定一致）
PY = r"F:/Python314/python.exe"


def skill_file(game_id: str, hero: str) -> str:
    """每英雄技能文件路径 data/skills/<game_id>/<英雄>.json。"""
    return os.path.join(SKILLS_DIR, game_id, f"{hero}.json")


def card_file(game_id: str, hero: str) -> str:
    return os.path.join(CARDS_DIR, game_id, f"{hero}.json")


def source_file(game_id: str) -> str:
    return os.path.join(SOURCE_DIR, game_id, "heroes.json")
