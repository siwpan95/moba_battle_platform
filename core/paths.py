#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""项目路径常量 —— 单一真相（ADR-002 拆分自 core.config）。

其它模块统一从此处取路径，避免在 loader / tools / ui 各处散落 os.path.join。
"""

import os

__all__ = [
    "CORE_DIR", "PROJECT_ROOT", "BASE_DIR", "FONT_DIR",
    "CARDS_DIR", "SOURCE_DIR", "SKILLS_DIR", "ANALYSIS_JSON",
]

# battle_platform/core
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
# battle_platform
PROJECT_ROOT = os.path.dirname(CORE_DIR)
# 保留别名以兼容（ui 实际未用）
BASE_DIR = PROJECT_ROOT

FONT_DIR = os.path.join(PROJECT_ROOT, "assets", "fonts")
CARDS_DIR = os.path.join(PROJECT_ROOT, "data", "character_cards")
# 供 tools 与 loader 共用，集中路径来源
SOURCE_DIR = os.path.join(PROJECT_ROOT, "data", "source")
SKILLS_DIR = os.path.join(PROJECT_ROOT, "data", "skills")
ANALYSIS_JSON = os.path.join(PROJECT_ROOT, "data", "analysis", "all_heroes_unified.json")
