#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""英雄加载器 —— 扫描角色卡目录，加载全部英雄"""

import json
import os
import sys
from collections import OrderedDict
from typing import Iterator, Tuple
from .config import GAME_NAME_CN, CARDS_DIR
from .paths import SKILLS_DIR
from . import schema


def iter_card_files(root: str) -> Iterator[Tuple[str, str, str]]:
    """统一扫描角色卡文件的迭代器（ADR-005）。

    递归遍历 root 下所有子目录，跳过 _ 前缀的文件与目录。
    返回 (filepath, relative_game_dir, stem) 三元组。

    使用方：
      - HeroLoader.load_all_heroes
      - tools/check_cards.py
      - tools/card_tool.load_existing_cards
    """
    root = os.path.abspath(root)
    for dirpath, dirnames, filenames in os.walk(root):
        # 跳过 _ 前缀目录（不进入、不遍历其子目录）
        dirnames[:] = [d for d in dirnames if not d.startswith("_")]
        for filename in filenames:
            if filename.startswith("_") or not filename.endswith(".json"):
                continue
            filepath = os.path.join(dirpath, filename)
            rel_dir = os.path.relpath(dirpath, root)
            stem = filename[:-5]  # strip ".json"
            yield filepath, rel_dir, stem


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

        for filepath, game_dir, _filename_stem in iter_card_files(CARDS_DIR):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    card = json.load(f)
                # 从 skills DB 注入技能（ADR-005 技能分离）：DB 有则覆盖，无则保留原值
                # 必须在 _normalize_card 之前，否则 None skills 会被错误归一为 []
                HeroLoader._inject_skills(card, game_id=game_dir, filename_stem=_filename_stem)
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
                card["_filename"] = _filename_stem
                heroes.append(card)
            except Exception as e:
                print(f"[警告] 加载失败: {filepath} — {e}")
        if normalized_count:
            print(f"[信息] 已归一化 {normalized_count} 张 dict 格式角色卡为 list[skill]（防御性兼容，详见 ADR-001）")
        if contract_violations:
            print(f"[信息] {contract_violations} 张卡存在契约告警（详见上方），请使用 tools/check_cards.py 查验后手动修复（切勿盲目运行迁移脚本）")
        return heroes

    @staticmethod
    def _normalize_card(card: dict) -> tuple[dict, bool]:
        """将不兼容的 skills 格式归一化为 list[skill]，防御对战崩溃（事故 SEV-2 止血）。

        归一化逻辑集中在 core.schema.normalize_skills（单一真相，ADR-001）。
        返回 (card, was_normalized)。
        """
        skills = card.get("skills")
        if skills is None or skills == []:
            return card, False   # ADR-005 合法空技能，非破损
        if isinstance(skills, list) and all(isinstance(s, dict) for s in skills):
            return card, False
        normalized, _warnings = schema.normalize_skills(skills)
        card["skills"] = normalized
        return card, True

    @staticmethod
    def _norm_name(name: str) -> str:
        """英雄名归一化：去空格、去单双引号/连字符、转小写，用于跨拼写容错匹配。"""
        if not name:
            return ""
        s = name.strip().lower()
        for ch in ("'", '"', "·", "•", "-", "_", " "):
            s = s.replace(ch, "")
        return s

    @staticmethod
    def _resolve_skill_pool(ip_dir: str):
        """解析技能池目录 data/skills/<ip>/。

        返回 (pool_dir, stem_index) 或 (None, None)；
        stem_index 为 {归一化文件名: 真实文件名} 的索引（缓存）。
        """
        cache = getattr(HeroLoader, "_SKILL_POOL_CACHE", None)
        if cache is None:
            cache = {}
            HeroLoader._SKILL_POOL_CACHE = cache
        if ip_dir in cache:
            return cache[ip_dir]
        pool_dir = os.path.join(SKILLS_DIR, ip_dir)
        if not os.path.isdir(pool_dir):
            cache[ip_dir] = (None, None)
            return (None, None)
        stem_index = {}
        for fn in os.listdir(pool_dir):
            if fn.endswith(".json"):
                base = fn[:-5]
                stem_index[HeroLoader._norm_name(base)] = fn
        cache[ip_dir] = (pool_dir, stem_index)
        return (pool_dir, stem_index)

    @staticmethod
    def _read_skill_file(pool_dir: str, filename: str):
        """从技能池读取单个英雄技能文件，失败返回 None。"""
        try:
            with open(os.path.join(pool_dir, filename), "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    @staticmethod
    def _inject_skills(card: dict, game_id: str, filename_stem: str = None) -> None:
        """从技能池注入英雄技能到卡片。

        技能池（推荐）：data/skills/<ip>/<英雄>.json，每英雄独立文件。
        查找候选顺序（均做归一化容错，如 Eland'orr vs Elandorr）：
          1. 角色卡文件名 stem
          2. hero.name
          3. hero.name_en
        命中则 card["skills"] = 该文件内容。

        仅当技能池无匹配且卡片自身也没有 skills 时，才打印告警
        （避免自带技能的中文卡刷屏）。
        """
        ip_dir = os.path.normpath(game_id).split(os.sep)[0]
        if ip_dir in (".", ""):
            ip_dir = game_id

        hero = card.get("hero", {})
        hero_name = hero.get("name", "")
        hero_name_en = hero.get("name_en", "")

        # 1) 技能池目录优先
        pool_dir, stem_index = HeroLoader._resolve_skill_pool(ip_dir)
        if pool_dir is not None:
            candidates = []
            if filename_stem:
                candidates.append(filename_stem)
            candidates += [hero_name, hero_name_en]
            for c in candidates:
                nc = HeroLoader._norm_name(c)
                if nc and nc in stem_index:
                    skills = HeroLoader._read_skill_file(pool_dir, stem_index[nc])
                    if skills is not None:
                        card["skills"] = skills
                        return
            # 1.5) 双向兼容：英文名 -> 中文名 反查后重试
            # （基于该 IP 中文角色卡的 name_en 字段，使英文原名文件也能命中中文名技能文件）
            from .skill_pool import resolve_pool_key
            resolved = resolve_pool_key(ip_dir, hero_name, hero_name_en)
            if resolved is not None:
                nr = HeroLoader._norm_name(resolved)
                if nr and nr in stem_index:
                    skills = HeroLoader._read_skill_file(pool_dir, stem_index[nr])
                    if skills is not None:
                        card["skills"] = skills
                        return
            if not card.get("skills"):
                label = hero_name or hero_name_en or filename_stem
                if label:
                    print(f"[技能注入] {label!r} 未在技能池 ({ip_dir!r}) 中找到匹配，且卡片自身也无 skills")
            return

    @staticmethod
    def build_hero_dict(heroes: list) -> OrderedDict:
        """构建 {显示名: 角色卡} 的有序字典（使用中文游戏名）。

        重名检测（ADR-005）：当不同卡片产生相同显示名时，产出 WARNING 日志并以
        ``<game_id>/<filename>`` 消歧，禁止静默覆盖。
        """
        result = OrderedDict()
        collisions = 0
        for card in sorted(heroes, key=lambda h: (
            h.get("game", {}).get("name", ""),
            h.get("hero", {}).get("name", "")
        )):
            game_name = card.get("game", {}).get("name", "?")
            game_cn = GAME_NAME_CN.get(game_name, game_name)
            hero_name = card.get("hero", {}).get("name", "?")
            display = f"[{game_cn}] {hero_name}"
            if display in result:
                collisions += 1
                # 用 _game_dir + _filename 构造消歧键（loader 注入的运行时字段）
                game_dir = card.get("_game_dir", "?")
                filename = card.get("_filename", "?")
                disambiguated = f"{display} <{game_dir}/{filename}>"
                # 若消歧键也碰撞，追加序号
                base_disamb = disambiguated
                suffix = 1
                while disambiguated in result:
                    suffix += 1
                    disambiguated = f"{base_disamb}#{suffix}"
                print(f"[WARNING] 显示名碰撞: {display}"
                      f" — 已有来自 {result[display].get('_game_dir','?')}/{result[display].get('_filename','?')}"
                      f"，新卡 {game_dir}/{filename} 以 '{disambiguated}' 消歧",
                      file=sys.stderr)
                result[disambiguated] = card
            else:
                result[display] = card
        if collisions:
            print(f"[WARNING] build_hero_dict: 共 {collisions} 次显示名碰撞，已消歧（详见上方）", file=sys.stderr)
        return result


# 模块级便捷函数：与 F.2 验证命令 `from core.loader import load_all_heroes` 对齐
# （底层仍是 HeroLoader.load_all_heroes 静态方法，行为不变）
load_all_heroes = HeroLoader.load_all_heroes
