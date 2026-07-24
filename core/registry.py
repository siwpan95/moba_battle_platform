#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""游戏 / 角色 / 属性 注册表与汉化映射 —— 单一真相（ADR-002）。

原散落于 core.config 的 taxonomy 收敛于此；core.config 改为再导出外观层，
调用方 `from core.config import GAME_NAME_CN, ...` 零改动。

提供的辅助函数（消解曾经的重复逻辑）：
  - role_cn_to_en(中文定位) -> 英文 universal_role
  - game_cn(card|game_en, fallback) -> 中文游戏名
"""

import os

__all__ = [
    "GAME_REGISTRY", "REGISTRY_BY_DISPLAY", "REGISTRY_BY_ID",
    "GAME_NAME_CN", "HERO_FILE_CANDIDATES",
    "detect_hero_file",
    "ATTR_NAME_CN", "STAT_NAME_CN", "ROLE_NAME_CN",
    "role_cn_to_en", "game_cn",
]

# ==========================================
# 游戏注册表（单一真相）
# game_id 即 data/source/ 现有小写 snake_case 目录名；
# 三处数据（source/ character_cards/ skills/）统一对齐到该 game_id。
# ==========================================
GAME_REGISTRY = {
    "300_heroes":              {"display": "300 Heroes",              "cn": "300英雄",     "hero_file": "heroes.json"},
    "arena_of_valor":          {"display": "Arena of Valor",          "cn": "传说对决",    "hero_file": "heroes.json"},
    "dota2":                   {"display": "Dota 2",                  "cn": "刀塔2",       "hero_file": "heroes.json"},
    "feiren_xueyuan":          {"display": "Extraordinary Ones",      "cn": "非人学园",    "hero_file": "heroes.json"},
    "heroes_of_the_storm":     {"display": "Heroes of the Storm",     "cn": "风暴英雄",    "hero_file": "heroes.json"},
    "hong_kong_comics":        {"display": "港漫群英",                "cn": "港漫群英",    "hero_file": "heroes.json"},
    "honor_of_kings":          {"display": "Honor of Kings",          "cn": "王者荣耀",    "hero_file": "heroes.json"},
    "league_of_legends":       {"display": "League of Legends",       "cn": "英雄联盟",    "hero_file": "champions.json"},
    "marvel_super_war":        {"display": "Marvel Super War",        "cn": "漫威超级战争", "hero_file": "heroes.json"},
    "mobile_legends_bang_bang": {"display": "Mobile Legends: Bang Bang", "cn": "无尽对决",  "hero_file": "heroes.json"},
    "onmyoji_arena":           {"display": "Onmyoji Arena",           "cn": "决战！平安京", "hero_file": "shikigami.json"},
    "pokemon_unite":            {"display": "Pokemon UNITE",            "cn": "宝可梦大集结", "hero_file": "pokemon.json"},
    "shuguang_heroes":         {"display": "Dawn Heroes",             "cn": "曙光英雄",    "hero_file": "heroes.json"},
    "smite":                   {"display": "SMITE",                   "cn": "神之浩劫",    "hero_file": "gods.json"},
    "vainglory":               {"display": "Vainglory",               "cn": "虚荣",        "hero_file": "heroes.json"},
    "yinghunzhiren":           {"display": "Heroes Evolved",          "cn": "英魂之刃",    "hero_file": "heroes.json"},
    "genshin":                 {"display": "Genshin Impact",          "cn": "原神",        "hero_file": "genshin.json"},
    "overwatch2":              {"display": "Overwatch 2",             "cn": "守望先锋2",   "hero_file": "overwatch2.json"},
    "mcu":                     {"display": "Marvel Cinematic Universe", "cn": "漫威电影宇宙", "hero_file": "mcu.json"},
    "dc":                      {"display": "DC Universe",             "cn": "DC宇宙",      "hero_file": "dc.json"},
    "harry_potter":            {"display": "Harry Potter",            "cn": "哈利波特",    "hero_file": "harry_potter.json"},
    "three_body":              {"display": "The Three-Body Problem",  "cn": "三体",        "hero_file": "three_body.json"},
    "demon_slayer":            {"display": "Demon Slayer",            "cn": "鬼灭之刃",    "hero_file": "demon_slayer.json"},
    "one_piece":               {"display": "One Piece",               "cn": "海贼王",      "hero_file": "one_piece.json"},
}

# 显示名 -> game_id（按显示名反查目录 id）
REGISTRY_BY_DISPLAY = {v["display"]: k for k, v in GAME_REGISTRY.items()}
# game_id -> 注册表条目（别名，等同于 GAME_REGISTRY 本身）
REGISTRY_BY_ID = GAME_REGISTRY

# 源英雄数据文件名候选（不同游戏命名不统一，按此优先级探测）
HERO_FILE_CANDIDATES = ("heroes.json", "champions.json", "shikigami.json", "pokemon.json", "gods.json",
                         "genshin.json", "overwatch2.json", "mcu.json", "dc.json",
                         "harry_potter.json", "three_body.json", "demon_slayer.json", "one_piece.json")


def detect_hero_file(game_dir: str) -> str:
    """探测源游戏目录内的英雄数据文件名（不同游戏命名不统一）。

    候选见 HERO_FILE_CANDIDATES，存在即返回，否则回退 "heroes.json"。
    从 tools/card_tool.py 的 _detect_hero_file 提升为共享实现，避免重复逻辑。
    """
    for c in HERO_FILE_CANDIDATES:
        if os.path.exists(os.path.join(game_dir, c)):
            return c
    return "heroes.json"  # 默认回退


# 汉化映射表（单一真相：从 GAME_REGISTRY 派生，display -> 中文名）
GAME_NAME_CN = {v["display"]: v["cn"] for v in GAME_REGISTRY.values()}

ATTR_NAME_CN = {
    "STR": "力量", "DEX": "敏捷", "CON": "体质",
    "INT": "智力", "WIS": "感知", "CHA": "魅力",
}

STAT_NAME_CN = {
    "hp": "生命", "physical_atk": "攻击", "magic_power": "法强",
    "ac": "护甲", "atk_speed_pct": "攻速", "crit_chance": "暴击概率",
    "crit_damage": "暴击伤害", "cdr_pct": "冷却",
    "heal_bonus_pct": "治疗加成", "cc_resist_pct": "韧性",
}

ROLE_NAME_CN = {
    "fighter":   "战士",  "assassin":  "刺客",
    "marksman":  "射手",  "mage":      "法师",
    "support":   "辅助",  "tank":      "坦克",
}


# ==========================================
# 辅助函数：消解曾经在 ui / loader 内联的重复反查逻辑
# ==========================================
def role_cn_to_en(role_cn: str):
    """中文角色定位 -> 英文 universal_role（ROLE_NAME_CN 的反查）。"""
    return {v: k for k, v in ROLE_NAME_CN.items()}.get(role_cn)


def game_cn(card_or_en, fallback=None):
    """英文 game_id -> 中文游戏名。

    接受两种入参：
      - 角色卡 dict：自动取 game.name，无映射时回退 card.game.name_cn（再无则原值）
      - 纯英文 id 字符串：fallback 为空时回退原值
    """
    if isinstance(card_or_en, dict):
        g = card_or_en.get("game", {})
        en = g.get("name", "")
        return GAME_NAME_CN.get(en, g.get("name_cn", en) if fallback is None else fallback)
    en = card_or_en or ""
    return GAME_NAME_CN.get(en, en if fallback is None else fallback)
