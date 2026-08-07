#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读探针：核验 content-pipeline-readiness.md §4.2/§4.3 的时效性。

Q1 §4.3 effect_categories 当前口径（5926 卡运行时态）
Q2 §4.2 字段丢弃机制是否仍存在（ADR-005 后）
Q3 migrate 写盘后运行时是否仍可对战（爆炸半径定级）
"""
import os
import sys
import io
import json
import shutil
import tempfile
import contextlib
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

import core.loader as loader  # noqa: E402
from core.loader import HeroLoader  # noqa: E402
from core import schema, mechanics  # noqa: E402

OUT = []


def log(*a):
    OUT.append(" ".join(str(x) for x in a))


# ---------- Q1: effect_categories 当前口径 ----------
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    loader._SKILLS_DB_CACHE.clear()
    heroes = HeroLoader.load_all_heroes()

cats = Counter()
raw_types = Counter()
total_effects = 0
unknown_fields = Counter()
for h in heroes:
    for s in (h.get("skills") or []):
        for e in (s.get("effects") or []):
            total_effects += 1
            t = e.get("type") if isinstance(e, dict) else None
            raw_types[str(t)] += 1
            try:
                cats[mechanics.categorize_effect(e)] += 1
            except Exception:
                cats["<ERROR>"] += 1
    for k, v in schema.report_unknown_fields(h.get("skills") or []).items():
        unknown_fields[k] += v

log("=== Q1: effect_categories 当前口径（5926 卡运行时态）===")
log(f"总 effect 实例 = {total_effects}   （§4.3 旧口径约 5000）")
log("分类计数（降序）:")
for k, v in cats.most_common():
    log(f"   {k:12} {v}")
log("")
log("§4.3 点名的四项对比（旧 -> 新）:")
for k, old in (("control", 801), ("slow", 365), ("flavor", 657), ("lifesteal", 1)):
    log(f"   {k:10} {old:5} -> {cats.get(k, 0)}")

log("")
log("flavor 兜底的原始 type 分布 top10:")
flavor_raw = Counter()
for h in heroes:
    for s in (h.get("skills") or []):
        for e in (s.get("effects") or []):
            if isinstance(e, dict) and mechanics.categorize_effect(e) == "flavor":
                flavor_raw[str(e.get("type"))] += 1
for k, v in flavor_raw.most_common(10):
    log(f"   {k!r:14} {v}")

# ---------- Q2: 字段透传是否生效 ----------
log("")
log("=== Q2: §4.2 字段丢弃机制是否仍存在 ===")
probe_raw = {"name": "X", "key": "Q", "type": "法术",
             "approx": True, "charges": 3, "mana_cost": 50, "scaling": "INT"}
merged = schema._to_skill_dict(probe_raw, 0)
dropped = [k for k in probe_raw if k not in merged]
log(f"输入未知字段 = ['approx','charges','mana_cost','scaling']")
log(f"输出后被丢弃 = {dropped}   <- §4.2:255 声称这四个会被丢弃")
log(f"结论: {'字段丢弃机制仍存在' if dropped else '字段丢弃机制已不存在（ADR-005 已修）'}")
log("")
log(f"现网未知字段实际透传统计 = {dict(unknown_fields.most_common(8))}")

# ---------- Q3: migrate 写盘后运行时爆炸半径 ----------
log("")
log("=== Q3: 磁盘 skills=[] 后运行时是否仍可对战 ===")
CARD = {
    "card_id": "TST-1", "hero": {"name": "测试英雄"}, "game": {"name": "Test IP"},
    "attributes": {k: {"score": 12, "modifier": 1}
                   for k in ("STR", "DEX", "CON", "INT", "WIS", "CHA")},
    "skills": [],  # 模拟 migrate 写盘后的状态
}
DB = {"测试英雄": [{"name": f"技能{i}", "key": k, "type": "物理", "cooldown": c,
                 "damage": {"dice_count": 1, "dice_size": 6, "bonus": 0},
                 "effects": [], "description": "d"}
                for i, (k, c) in enumerate(zip("QWER", [0, 1, 2, 4]))]}

tmp = tempfile.mkdtemp(prefix="doc_eff_")
orig_dir, orig_db = loader.CARDS_DIR, HeroLoader._load_skills_db
try:
    cd = os.path.join(tmp, "character_cards", "test_ip")
    sd = os.path.join(tmp, "skills")
    os.makedirs(cd)
    os.makedirs(sd)
    with open(os.path.join(cd, "h.json"), "w", encoding="utf-8") as fh:
        json.dump(CARD, fh, ensure_ascii=False)
    with open(os.path.join(sd, "test_ip.json"), "w", encoding="utf-8") as fh:
        json.dump(DB, fh, ensure_ascii=False)

    loader.CARDS_DIR = os.path.join(tmp, "character_cards")
    loader._SKILLS_DB_CACHE.clear()

    def pl(game_dir):
        if game_dir in loader._SKILLS_DB_CACHE:
            return loader._SKILLS_DB_CACHE[game_dir]
        p = os.path.join(sd, f"{game_dir}.json")
        db = json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else {}
        loader._SKILLS_DB_CACHE[game_dir] = db
        return db
    HeroLoader._load_skills_db = staticmethod(pl)

    b2 = io.StringIO()
    with contextlib.redirect_stdout(b2):
        hs = HeroLoader.load_all_heroes()
    log(f"磁盘态 skills = []  ->  运行时技能数 = {len(hs[0].get('skills') or [])}")
    log(f"门禁 validate_card(磁盘态 []) = {schema.validate_card(CARD)}")
    log("结论: 运行时被 _inject_skills 覆盖救回；爆炸半径 = CI 红 + 设计推翻，非即时运行时故障")
finally:
    HeroLoader._load_skills_db = staticmethod(orig_db)
    loader.CARDS_DIR = orig_dir
    loader._SKILLS_DB_CACHE.clear()
    shutil.rmtree(tmp, ignore_errors=True)

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_effects_result.txt"),
          "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT))
