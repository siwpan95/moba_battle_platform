#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""英雄目录：筛选与摘要的领域逻辑（从 ui 下沉，ADR-002 范畴）。

ui/ui.py 只负责视图（Combobox / Label / Canvas）；过滤与英雄摘要的纯逻辑集中于此，
便于单测与复用，也避免 ui 再次内联 taxonomy 反查。
"""

from collections import OrderedDict

from .registry import GAME_NAME_CN, ATTR_NAME_CN, ROLE_NAME_CN, game_cn, role_cn_to_en
from .simulator import BattleSimulator

__all__ = ["filter_cards", "describe_card"]


def filter_cards(heroes_dict, game_filter="全部游戏", role_filter="全部位置", search_query=""):
    """按 游戏 + 位置 + 关键词 三层过滤，返回 OrderedDict（保持原顺序）。

    heroes_dict : {显示名: 角色卡}
    game_filter / role_filter / search_query : 与 ui 的 Combobox / Entry 取值对齐
    """
    role_en = role_cn_to_en(role_filter) if role_filter != "全部位置" else None
    q = (search_query or "").strip().lower()
    filtered = OrderedDict()
    for key, card in heroes_dict.items():
        if game_filter != "全部游戏":
            if game_cn(card) != game_filter:
                continue
        if role_en is not None:
            card_role = card.get("game", {}).get("universal_role", "")
            if card_role != role_en:
                continue
        if q:
            hero = card.get("hero", {})
            game_name = card.get("game", {}).get("name", "").lower()
            if not (q in hero.get("name", "").lower()
                    or q in hero.get("name_en", "").lower()
                    or q in game_name
                    or q in key.lower()):
                continue
        filtered[key] = card
    return filtered


def describe_card(card, level=1):
    """生成英雄信息摘要（按等级显示），供 ui 的 _get_card_info 调用。"""
    if not card:
        return "未选择"

    hero = card.get("hero", {})
    game = card.get("game", {})
    attrs = card.get("attributes", {})
    skills = card.get("skills", [])

    game_cn_name = game_cn(card)
    role = game.get("role_name", "?")
    diff = card.get("difficulty", 3)
    diff_stars = "★" * diff + "☆" * (5 - diff)
    lvl_stats = BattleSimulator._calc_stats_for_level(card, level)

    info = f"来自: {game_cn_name} | 定位: {role} | 难度: {diff_stars}\n"
    info += (
        f"Lv.{level}  生命:{lvl_stats['hp']}  攻击:{lvl_stats['physical_atk']}"
        f"  法强:{lvl_stats['magic_power']}  护甲:{lvl_stats['ac']}\n"
    )
    crit_chance = lvl_stats.get('crit_chance', lvl_stats.get('crit_pct', 0))
    crit_damage = lvl_stats.get('crit_damage', 150.0)
    info += f"暴击率:{crit_chance}%  暴击伤害:{crit_damage}%"

    attr_parts = []
    for abbr in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]:
        a = attrs.get(abbr, {})
        cn = ATTR_NAME_CN.get(abbr, abbr)
        attr_parts.append(f"{cn}:{a.get('score', '?')}({a.get('modifier', 0):+d})")
    info += "属性: " + "  ".join(attr_parts)

    if skills:
        skill_lines = []
        for s in skills:
            if isinstance(s, dict):
                # 结构化 D&D 技能
                dmg = s.get("damage", {})
                dmg_str = f"{dmg.get('dice_count', 0)}d{dmg.get('dice_size', 0)}+{dmg.get('bonus_attr', '?')}"
                line = f"  [{s.get('key', '?')}] {s.get('name', '?')} | {dmg_str} {dmg.get('type', '')} | CD:{s.get('cooldown', 0)}"
                skill_lines.append(line)
            elif isinstance(s, str):
                if ":" in s:
                    key, desc = s.split(":", 1)
                    skill_lines.append(f"  {key.strip()}: {desc.strip()}")
                else:
                    skill_lines.append(f"  {s}")
        info += "\n技能:\n" + "\n".join(skill_lines)

    return info
