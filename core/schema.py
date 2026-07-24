#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""角色卡数据契约（as-code 单一真相，ADR-001）。

卡数据链路：tools/ 生成 -> core/loader 加载 -> core/simulator/ui 消费。
历史上 skills 字段出现了「扁平单技能 dict」「槽位键 dict」「list[skill]」三种表示，
导致 42% 英雄开战即崩（事故 SEV-2）。本模块把规范表示集中为一处：

    skills: list[Skill]   # 长度通常为 4（对应 Q/W/E/R）

并承担两件事：
  1. normalize_skills：把任意历史/异常表示归一为 list[Skill]（共享给 loader 与迁移脚本）。
  2. validate_card：按契约校验一张卡，返回问题列表（空=通过），供加载期告警与 CI 门禁使用。

本模块不依赖 core 内其他模块，可独立被 loader / 迁移脚本 / CI 导入。
"""

from __future__ import annotations

from typing import Any

# 槽位索引 -> 默认槽位键（Q/W/E/R）
SLOT_KEYS = ["Q", "W", "E", "R"]
# 技能 type 的合法取值（与卡库实际数据 + simulator 的消费逻辑保持一致，均为中文）
#   物理 / 法术：simulator 据此选择物理/法术伤害公式；混合 / 真实：走 else 分支
_VALID_TYPES = ("物理", "法术", "混合", "真实")


def _to_skill_dict(raw: Any, slot: int) -> dict:
    """把一个任意技能元素规范化为引擎消费的 dict。"""
    if not isinstance(raw, dict):
        raw = {}
    return {
        "name": str(raw.get("name", f"技能{SLOT_KEYS[slot]}")),
        "key": str(raw.get("key", SLOT_KEYS[slot])),
        "type": str(raw.get("type", "物理")),
        "cooldown": int(raw.get("cooldown", 0) or 0),
        "description": str(raw.get("description", "")),
        "damage": raw.get("damage") or {},
        "effects": raw.get("effects"),
        "aoe_radius": raw.get("aoe_radius"),
        "saving_throw": raw.get("saving_throw"),
        "action": str(raw.get("action", "")),
        "range": raw.get("range"),
        "target": raw.get("target"),
    }


def normalize_skills(skills: Any) -> tuple[list, list]:
    """把任意 skills 表示归一为 list[skill] dict。

    返回 (normalized_list, warnings)。

    规则：
      - list[skill]            -> 逐元素规范化后原样返回
      - 扁平单技能 dict（字段名键） -> 包成长度 1 的 list（保留真实字段）
      - 槽位键 dict（'0'/'1'/'2'/'3'）-> 按槽位展开成 list[4]
      - 缺失 / 其它类型       -> 空 list
    """
    warnings: list = []
    if skills is None:
        return [], ["skills 缺失，归一为空 list"]
    if isinstance(skills, list):
        return [_to_skill_dict(s, i) for i, s in enumerate(skills)], warnings
    if isinstance(skills, dict):
        keys = {str(k) for k in skills.keys()}
        slot_keys = {str(i) for i in range(4)}
        if keys and keys.issubset(slot_keys):
            out = [_to_skill_dict(skills.get(str(i)), i) for i in range(4)]
            warnings.append("skills 为槽位键 dict，已按槽位展开为 list[4]")
            return out, warnings
        warnings.append("skills 为扁平单技能 dict，已包成 list[1]")
        return [_to_skill_dict(skills, 0)], warnings
    warnings.append(f"skills 类型异常({type(skills).__name__})，归一为空 list")
    return [], warnings


def validate_card(card: Any) -> list:
    """按契约校验一张角色卡，返回问题列表（空=通过）。

    契约要点：
      - skills 必须是 list[dict]，且每个元素有 name、合法 type
      - 六维属性 attributes.{STR..CHA}.modifier 必须存在
      - hero.name 必须存在
    """
    if not isinstance(card, dict):
        return ["card 非 dict"]
    problems: list = []
    skills = card.get("skills")
    if not isinstance(skills, list):
        problems.append("skills 不是 list（契约要求 list[Skill]）")
    else:
        if len(skills) == 0:
            problems.append("skills 为空 list")
        for i, s in enumerate(skills):
            if not isinstance(s, dict):
                problems.append(f"skills[{i}] 非 dict")
                continue
            if not s.get("name"):
                problems.append(f"skills[{i}].name 缺失")
            if s.get("type") not in _VALID_TYPES:
                problems.append(f"skills[{i}].type 非法: {s.get('type')!r}")
    for attr in ("STR", "DEX", "CON", "INT", "WIS", "CHA"):
        a = (card.get("attributes") or {}).get(attr)
        if not isinstance(a, dict) or "modifier" not in a:
            problems.append(f"attributes.{attr}.modifier 缺失")
    hero = card.get("hero")
    if not isinstance(hero, dict) or not hero.get("name"):
        problems.append("hero.name 缺失")
    return problems
