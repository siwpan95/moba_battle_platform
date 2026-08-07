#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量 MOBA 技能入库管道
用法: python run_batch.py <game> <batch_id> [--dry-run]
"""

import json
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from batch_skill_gen import (
    load_source_heroes, load_existing_skills, merge_and_save,
    get_missing_heroes, build_hero_skills,
    ROLE_SKILL_PROFILES, ROLE_ATTR_MAP, KEY_CD_MAP
)

# 优先用扩展数据
try:
    from skill_data_extended import SKILL_MAPS as EXTENDED_SKILL_MAPS
    SKILL_NAME_MAPS = EXTENDED_SKILL_MAPS
    print("Using extended skill name maps.")
except ImportError:
    from batch_skill_gen import DOTA2_SKILL_NAMES, MLBB_SKILL_NAMES, YINGHUN_SKILL_NAMES
    SKILL_NAME_MAPS = {
        "dota2": DOTA2_SKILL_NAMES,
        "mlbb": MLBB_SKILL_NAMES,
        "yinghun": YINGHUN_SKILL_NAMES,
    }
    print("Using built-in skill name maps.")

SKILLS_PATH_MAP = {
    "dota2": "data/skills/dota2.json",
    "mlbb": "data/skills/mobile_legends_bang_bang.json",
    "yinghun": "data/skills/yinghunzhiren.json",
}

BATCH_SIZE = 40


def get_fallback_skills(hero_name, role):
    """当没有预置技能名时，用角色模板生成通用技能名"""
    profiles = {
        "tank": {"Q": "盾击", "W": "震荡波", "E": "坚盾", "R": "大地之怒"},
        "fighter": {"Q": "斩击", "W": "旋风斩", "E": "战吼", "R": "终极一击"},
        "assassin": {"Q": "暗杀", "W": "影步", "E": "烟雾弹", "R": "死亡标记"},
        "mage": {"Q": "奥术飞弹", "W": "元素之怒", "E": "魔法护盾", "R": "陨星坠落"},
        "marksman": {"Q": "精准射击", "W": "箭雨", "E": "闪避突进", "R": "致命一击"},
        "support": {"Q": "治愈之光", "W": "守护祝福", "E": "净化", "R": "神圣干涉"},
    }
    return profiles.get(role, profiles["fighter"])


def run_batch(game, batch_id, dry_run=False):
    """处理一批英雄技能"""
    missing = get_missing_heroes(game)
    skill_map = SKILL_NAME_MAPS.get(game, {})
    skills_path = SKILLS_PATH_MAP[game]

    start = batch_id * BATCH_SIZE
    end = min(start + BATCH_SIZE, len(missing))
    batch_heroes = missing[start:end]

    if not batch_heroes:
        print(f"[{game}] Batch {batch_id}: No more heroes to process!")
        return {}

    print(f"[{game}] Batch {batch_id}: Processing {len(batch_heroes)} heroes ({start}-{end-1} of {len(missing)} missing)")
    print(f"  First: {batch_heroes[0][0]}, Last: {batch_heroes[-1][0]}")

    new_skills = {}
    fallback_count = 0

    for hero_name, info in batch_heroes:
        role = info["universal_role"]

        if hero_name in skill_map:
            # 使用预置技能名
            sm = skill_map[hero_name]
            skill_names = {k: v for k, v in sm.items() if k != "hints"}
            desc_hints = sm.get("hints", {})
            skills = build_hero_skills(hero_name, role, skill_names, desc_hints)
        else:
            # 回退：通用技能名 + 角色模板
            fallback_count += 1
            fb_names = get_fallback_skills(hero_name, role)
            skills = build_hero_skills(hero_name, role, fb_names, {})

        new_skills[hero_name] = skills

    print(f"  Generated: {len(new_skills)} heroes ({fallback_count} fallback)")

    if dry_run:
        print("  [DRY RUN] Would write to:", skills_path)
        # Print sample
        for h in list(new_skills.keys())[:2]:
            print(f"  Sample {h}:")
            for s in new_skills[h]:
                print(f"    [{s['key']}] {s['name']} CD={s['cooldown']} {s['description'][:60]}...")
        return new_skills

    # 合并并保存
    existing = load_existing_skills(skills_path)
    merge_and_save(existing, new_skills, skills_path)

    # 验证（技能池模式：统计池目录）
    pool = os.path.join(os.path.dirname(skills_path),
                        os.path.splitext(os.path.basename(skills_path))[0])
    if os.path.isdir(pool):
        hero_files = [fn for fn in os.listdir(pool) if fn.endswith(".json")]
        total_heroes = len(hero_files)
        total_skills = 0
        for fn in hero_files:
            try:
                with open(os.path.join(pool, fn), "r", encoding="utf-8") as f:
                    total_skills += len(json.load(f))
            except (json.JSONDecodeError, OSError):
                continue
    else:
        with open(skills_path, "r", encoding="utf-8") as f:
            verify = json.load(f)
        total_heroes = len(verify)
        total_skills = sum(len(v) for v in verify.values())

    print(f"  Saved! Total: {total_heroes} heroes, {total_skills} skills in {skills_path}")

    # 检查质量问题
    issues = []
    for hname, hskills in verify.items():
        keys = [s["key"] for s in hskills]
        if set(keys) != {"Q", "W", "E", "R"}:
            issues.append(f"  BAD KEYS: {hname} has keys {keys}")
        for s in hskills:
            if s["cooldown"] not in [0, 1, 2, 4]:
                issues.append(f"  BAD CD: {hname}/{s['key']} CD={s['cooldown']}")
            if "damage" in s and s["damage"]["dice_count"] < 0:
                issues.append(f"  BAD DICE: {hname}/{s['key']}")

    if issues:
        print(f"  WARNINGS ({len(issues)}):")
        for i in issues[:10]:
            print(f"    {i}")

    return new_skills


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MOBA Skill Batch Importer")
    parser.add_argument("game", choices=["dota2", "mlbb", "yinghun"])
    parser.add_argument("batch_id", type=int, help="0-based batch index")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    run_batch(args.game, args.batch_id, args.dry_run)
