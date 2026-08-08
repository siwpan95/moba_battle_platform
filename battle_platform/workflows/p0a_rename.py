#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工作流二：P0-A 模板技能名改写。

检测技能名为模板泛称（如「战士·旋风斩」「法师·元素风暴」）的 IP，
并提供改名映射应用能力。改名映射由调用方提供（神话题材可直接映射神话能力；
商业 MOBA 需 WebSearch 后 D&D 风味改写，禁止逐字复制 wiki）。

只改 skills 文件里的 name 字段，不触碰 damage/effects/cooldown/description。
"""

import json
import os
import re

from battle_platform import paths

# 模板技能名特征：以 6 种定位中文前缀 + 间隔号「·」开头
_TEMPLATE_RE = re.compile(r"^(战士|法师|坦克|刺客|射手|辅助)·")

# 更宽松的模板判定：含「·」且左侧为已知泛称前缀之一（兼容全角/半角）
_TEMPLATE_RE_LOOSE = re.compile(r"^(战士|法师|坦克|刺客|射手|辅助)\s*[·\.]\s*")


def detect_template_skills(game_id: str) -> list:
    """扫描该 IP 全部技能文件，返回模板名技能清单。

    返回 [{"hero":..., "file":..., "index":..., "name":...}, ...]
    """
    pool = os.path.join(paths.SKILLS_DIR, game_id)
    if not os.path.isdir(pool):
        return []
    hits = []
    for fn in sorted(os.listdir(pool)):
        if not fn.endswith(".json"):
            continue
        hero = fn[:-5]
        try:
            skills = json.load(open(os.path.join(pool, fn), encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for i, s in enumerate(skills):
            name = s.get("name", "")
            if _TEMPLATE_RE.match(name) or _TEMPLATE_RE_LOOSE.match(name):
                hits.append({"hero": hero, "file": fn, "index": i, "name": name})
    return hits


def template_ratio(game_id: str) -> tuple:
    """返回 (模板技能数, 总技能数)。"""
    pool = os.path.join(paths.SKILLS_DIR, game_id)
    total = templ = 0
    if os.path.isdir(pool):
        for fn in sorted(os.listdir(pool)):
            if not fn.endswith(".json"):
                continue
            try:
                skills = json.load(open(os.path.join(pool, fn), encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            for s in skills:
                total += 1
                nm = s.get("name", "")
                if _TEMPLATE_RE.match(nm) or _TEMPLATE_RE_LOOSE.match(nm):
                    templ += 1
    return templ, total


def apply_renames(game_id: str, mapping: dict) -> int:
    """应用改名映射 {旧技能名: 新技能名}，返回改动条数。

    凡 skills 文件中 name 命中 mapping 键的，统一改名。
    """
    pool = os.path.join(paths.SKILLS_DIR, game_id)
    if not os.path.isdir(pool):
        return 0
    changed = 0
    for fn in sorted(os.listdir(pool)):
        if not fn.endswith(".json"):
            continue
        fp = os.path.join(pool, fn)
        try:
            skills = json.load(open(fp, encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        dirty = False
        for s in skills:
            old = s.get("name", "")
            if old in mapping:
                s["name"] = mapping[old]
                changed += 1
                dirty = True
        if dirty:
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(skills, f, ensure_ascii=False, indent=2)
    return changed


__all__ = ["detect_template_skills", "template_ratio", "apply_renames"]
