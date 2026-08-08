#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工作流四：P1 英雄池扩充。

为短板 IP 追加角色：把英雄技能写入 data/skills/<game_id>/<英雄>.json，
并把英雄名追加进 data/source/<game_id>/heroes.json。

英雄技能既可由调用方直接给出「4 个技能 dict 的 list」（贴近真实磁盘格式），
也可通过 build_from_spec() 复用 tools/expansion/builder 的骰型/CD 自动推导，
保证数值落 GDD §3.2 配额带。
"""

import json
import os

from battle_platform import paths


def add_heroes(game_id: str, heroes: list) -> dict:
    """heroes: [{"name":..., "skills":[4 个技能 dict]}, ...]。

    返回 {added, skipped(重名), skill_files, source_total}。
    """
    pool = os.path.join(paths.SKILLS_DIR, game_id)
    os.makedirs(pool, exist_ok=True)
    src = paths.source_file(game_id)
    os.makedirs(os.path.dirname(src), exist_ok=True)
    have = set()
    if os.path.exists(src):
        try:
            have = {e.get("name") for e in json.load(open(src, encoding="utf-8"))}
        except (json.JSONDecodeError, OSError):
            have = set()

    added = 0
    skipped = []
    written = []
    for h in heroes:
        name = h["name"]
        skills = h["skills"]
        if not isinstance(skills, list) or len(skills) != 4:
            raise ValueError(f"{name}: 必须恰好 4 个技能，实得 {len(skills) if isinstance(skills, list) else '非list'}")
        if name in have:
            skipped.append(name)
            continue
        with open(os.path.join(pool, f"{name}.json"), "w", encoding="utf-8") as f:
            json.dump(skills, f, ensure_ascii=False, indent=2)
        have.add(name)
        added += 1
        written.append(name)

    # 同步 source
    src_list = []
    if os.path.exists(src):
        try:
            src_list = json.load(open(src, encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            src_list = []
    for name in written:
        src_list.append({"name": name})
    with open(src, "w", encoding="utf-8") as f:
        json.dump(src_list, f, ensure_ascii=False, indent=2)

    return {"added": added, "skipped": skipped, "skill_files": written,
            "source_total": len(src_list)}


def build_from_spec(game_id: str, specs: list) -> dict:
    """specs: [hero(name, name_en, title, role, skills=[...], dmg=...) 返回的对象]。

    复用 tools.expansion.builder.compile_hero 把「手写素材」编译成 4 个合规技能 dict，
    再走 add_heroes 落盘。builder 自动推导骰型/CD/豁免/射程并保证配额带。
    """
    try:
        from tools.expansion.builder import compile_hero
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"无法导入 tools.expansion.builder：{e}")
    heroes = []
    for h in specs:
        skills = compile_hero(h)
        heroes.append({"name": h["name"], "skills": skills})
    return add_heroes(game_id, heroes)


__all__ = ["add_heroes", "build_from_spec"]
