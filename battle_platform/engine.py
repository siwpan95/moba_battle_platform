#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""引擎外观层（facade）。

薄封装：对包内工作流暴露上级引擎的关键能力，避免各处重复 import。
只导入轻量模块（loader / registry / mechanics），重活（card_tool 生成、
check_cards 校验）走子进程，避免在 import 期拉起整套生成链路。
"""

from battle_platform import paths  # 触发 sys.path 引导
from core import loader as loader
from core import registry as registry
from core import mechanics as mechanics
from core.loader import HeroLoader


def load_heroes():
    """加载全量角色卡（含技能注入）。"""
    return HeroLoader.load_all_heroes()


def categorize_effect(eff: dict):
    """把 effect dict 归一为受控类别（control/slow/.../flavor）。"""
    return mechanics.categorize_effect(eff)


__all__ = ["loader", "registry", "mechanics", "HeroLoader", "load_heroes", "categorize_effect"]
