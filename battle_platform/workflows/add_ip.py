#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工作流一：新增 IP。

按真实磁盘格式落地一个新游戏：
  1. 建目录 data/skills/<game_id>/ 与 data/character_cards/<game_id>/
  2. 建空源数据 data/source/<game_id>/heroes.json = []
  3. 在 core/registry.py 的 GAME_REGISTRY 中追加条目（幂等）

注意：技能血肉采用「每英雄一个文件」的真实格式，因此 skills 目录初始为空，
不写单文件 {英雄:技能} 的过期格式。
"""

import json
import os

from battle_platform import paths
from battle_platform.engine import registry


def add_ip(game_id: str, display: str, cn: str, hero_file: str = "heroes.json") -> dict:
    """注册并落地一个新 IP。返回改动摘要。

    game_id 用小写 snake_case（与 data/source/<game_id> 目录一致）。
    """
    if not game_id or " " in game_id:
        raise ValueError(f"game_id 必须小写 snake_case，收到 {game_id!r}")

    changed = {"game_id": game_id, "registered": False, "dirs": [], "source": False}

    # 1) 目录
    for d in (os.path.join(paths.SKILLS_DIR, game_id),
              os.path.join(paths.CARDS_DIR, game_id),
              os.path.join(paths.SOURCE_DIR, game_id)):
        os.makedirs(d, exist_ok=True)
        changed["dirs"].append(d)

    # 2) 空 source
    src = paths.source_file(game_id)
    if not os.path.exists(src):
        with open(src, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        changed["source"] = True

    # 3) registry（幂等：已存在则跳过）
    if game_id not in registry.GAME_REGISTRY:
        _register(game_id, display, cn, hero_file)
        changed["registered"] = True
    return changed


def _register(game_id: str, display: str, cn: str, hero_file: str) -> None:
    """在 GAME_REGISTRY 的闭合 '}' 前插入新条目。"""
    reg_path = os.path.join(paths.PROJECT_ROOT, "core", "registry.py")
    text = open(reg_path, encoding="utf-8").read()
    start = text.index("GAME_REGISTRY = {")
    # 找到 GAME_REGISTRY 块之后第一个处于行首的 '}'（即该 dict 的闭合）
    close = text.index("\n}", start)
    entry = (f'    "{game_id}":               {{"display": "{display}", '
             f'"cn": "{cn}", "hero_file": "{hero_file}"}},\n')
    new_text = text[:close + 1] + entry + text[close + 1:]
    with open(reg_path, "w", encoding="utf-8") as f:
        f.write(new_text)
    # 刷新已加载的模块缓存，使后续 import 拿到最新注册表
    registry.GAME_REGISTRY[game_id] = {"display": display, "cn": cn, "hero_file": hero_file}


__all__ = ["add_ip"]
