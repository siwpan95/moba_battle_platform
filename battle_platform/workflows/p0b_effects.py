#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工作流三：P0-B effects 补全。

针对技能名已合理、但 effects 缺失/为空的技能，按技能名关键词推断 effects。
只补充 effects，保持已有 name/damage/cooldown/description 不变。

effect.type 使用中文受控词（与 core/mechanics.py 别名表一致，亦即
data/skills 真实磁盘格式）：眩晕/束缚/护盾/减速/治疗/灼烧/中毒/处决/
破甲/恐惧/魅惑/增益/加速/隐身/净化/复活 …
"""

import json
import os

from battle_platform import paths

# (子串, effect_type, target, duration)
# 顺序即优先级：靠前的先命中。
_KW = [
    ("斩", "处决", "敌方", 0), ("杀", "处决", "敌方", 0), ("灭", "处决", "敌方", 0),
    ("处决", "处决", "敌方", 0), ("屠", "处决", "敌方", 0),
    ("盾", "护盾", "自身", 2), ("守护", "护盾", "自身", 2), ("结界", "护盾", "自身", 2),
    ("壁", "护盾", "自身", 2),
    ("火", "灼烧", "敌方", 2), ("炎", "灼烧", "敌方", 2), ("灼", "灼烧", "敌方", 2),
    ("焰", "灼烧", "敌方", 2),
    ("冰", "减速", "敌方", 2), ("冻", "减速", "敌方", 2), ("寒", "减速", "敌方", 2),
    ("霜", "减速", "敌方", 2),
    ("晕", "眩晕", "敌方", 1), ("眩", "眩晕", "敌方", 1), ("懵", "眩晕", "敌方", 1),
    ("加", "增益", "自身", 2), ("增", "增益", "自身", 2), ("强", "增益", "自身", 2),
    ("励", "增益", "自身", 2),
    ("闪", "加速", "自身", 1), ("疾", "加速", "自身", 1), ("速", "加速", "自身", 1),
    ("冲", "加速", "自身", 1),
    ("疗", "治疗", "自身", 0), ("愈", "治疗", "自身", 0), ("治", "治疗", "自身", 0),
    ("乳", "治疗", "自身", 0),
    ("缚", "束缚", "敌方", 2), ("困", "束缚", "敌方", 2), ("禁", "束缚", "敌方", 2),
    ("锁", "束缚", "敌方", 2),
    ("破", "破甲", "敌方", 2), ("穿", "破甲", "敌方", 2), ("裂", "破甲", "敌方", 2),
    ("惧", "恐惧", "敌方", 1), ("恐", "恐惧", "敌方", 1), ("惶", "恐惧", "敌方", 1),
    ("魅", "魅惑", "敌方", 1), ("惑", "魅惑", "敌方", 1),
    ("毒", "中毒", "敌方", 2), ("蚀", "中毒", "敌方", 2),
    ("隐", "隐身", "自身", 1), ("遁", "隐身", "自身", 1),
    ("净", "净化", "自身", 0), ("驱", "净化", "自身", 0), ("解", "净化", "自身", 0),
    ("复", "复活", "自身", 0), ("活", "复活", "自身", 0), ("生", "复活", "自身", 0),
]


def _infer(name: str):
    for sub, etype, target, dur in _KW:
        if sub in name:
            return etype, target, dur
    return None


def complete_effects(game_id: str, dry_run: bool = False) -> dict:
    """补完该 IP 缺 effects 的技能。返回 {added, scanned, files}。

    dry_run=True 时只统计、不写盘。
    """
    pool = os.path.join(paths.SKILLS_DIR, game_id)
    if not os.path.isdir(pool):
        return {"added": 0, "scanned": 0, "files": []}
    added = 0
    scanned = 0
    touched = []
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
            scanned += 1
            effs = s.get("effects") or []
            if effs:
                continue
            guess = _infer(s.get("name", ""))
            if not guess:
                continue
            etype, target, dur = guess
            eff = {"type": etype, "target": target}
            if dur:
                eff["duration"] = dur
            eff["desc"] = ""
            s.setdefault("effects", []).append(eff)
            added += 1
            dirty = True
        if dirty:
            touched.append(fn)
            if not dry_run:
                with open(fp, "w", encoding="utf-8") as f:
                    json.dump(skills, f, ensure_ascii=False, indent=2)
    return {"added": added, "scanned": scanned, "files": touched}


def missing_count(game_id: str) -> tuple:
    """返回 (缺 effects 的技能数, 总技能数)。"""
    pool = os.path.join(paths.SKILLS_DIR, game_id)
    total = miss = 0
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
                if not (s.get("effects") or []):
                    miss += 1
    return miss, total


__all__ = ["complete_effects", "missing_count"]
