#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""英雄加载器 —— 扫描角色卡目录，加载全部英雄"""

import json
import os
from collections import OrderedDict
from .config import GAME_NAME_CN, CARDS_DIR
from . import schema


class HeroLoader:
    """加载角色卡JSON"""

    @staticmethod
    def load_all_heroes() -> list:
        """扫描所有游戏目录，加载全部英雄"""
        heroes = []
        normalized_count = 0
        contract_violations = 0
        if not os.path.isdir(CARDS_DIR):
            print(f"[警告] 角色卡目录不存在: {CARDS_DIR}")
            return heroes

        for game_dir in os.listdir(CARDS_DIR):
            game_path = os.path.join(CARDS_DIR, game_dir)
            if not os.path.isdir(game_path) or game_dir.startswith("_"):
                continue
            for filename in os.listdir(game_path):
                if filename.endswith(".json"):
                    filepath = os.path.join(game_path, filename)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            card = json.load(f)
                        card, was_normalized = HeroLoader._normalize_card(card)
                        if was_normalized:
                            normalized_count += 1
                        # 契约校验（仅告警，不阻断加载）
                        problems = schema.validate_card(card)
                        if problems:
                            contract_violations += 1
                            print(f"[契约警告] {filepath} — " + "; ".join(problems[:3])
                                  + ("..." if len(problems) > 3 else ""))
                        card["_game_dir"] = game_dir
                        card["_filename"] = filename.replace(".json", "")
                        heroes.append(card)
                    except Exception as e:
                        print(f"[警告] 加载失败: {filepath} — {e}")
        if normalized_count:
            print(f"[信息] 已归一化 {normalized_count} 张 dict 格式角色卡为 list[skill]（防御性兼容，详见 ADR-001）")
        if contract_violations:
            print(f"[信息] {contract_violations} 张卡存在契约告警（详见上方），建议用 tools/migrate_skills_format.py 修复或 CI 拦截")
        return heroes

    @staticmethod
    def _normalize_card(card: dict) -> tuple[dict, bool]:
        """将不兼容的 skills 格式归一化为 list[skill]，防御对战崩溃（事故 SEV-2 止血）。

        归一化逻辑集中在 core.schema.normalize_skills（单一真相，ADR-001）。
        返回 (card, was_normalized)。
        """
        skills = card.get("skills")
        if isinstance(skills, list) and all(isinstance(s, dict) for s in skills):
            return card, False
        normalized, _warnings = schema.normalize_skills(skills)
        card["skills"] = normalized
        return card, True

    @staticmethod
    def build_hero_dict(heroes: list) -> OrderedDict:
        """构建 {显示名: 角色卡} 的有序字典（使用中文游戏名）"""
        result = OrderedDict()
        for card in sorted(heroes, key=lambda h: (
            h.get("game", {}).get("name", ""),
            h.get("hero", {}).get("name", "")
        )):
            game_name = card.get("game", {}).get("name", "?")
            game_cn = GAME_NAME_CN.get(game_name, game_name)
            hero_name = card.get("hero", {}).get("name", "?")
            display = f"[{game_cn}] {hero_name}"
            result[display] = card
        return result


# 模块级便捷函数：与 F.2 验证命令 `from core.loader import load_all_heroes` 对齐
# （底层仍是 HeroLoader.load_all_heroes 静态方法，行为不变）
load_all_heroes = HeroLoader.load_all_heroes
