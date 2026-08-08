#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P0-D 骰骨架回调：把偏离 GDD §3.2 配额带的英雄拉回官方骨架。

背景
----
实测 9 个公版 IP 共 577 名英雄中，仅 **辅助** 存在骰值漂移：
  - 官方骨架 (builder.ROLE_DICE["support"])  (1,6)(2,6)(1,8)(3,6) = 25.5  x84
  - 历史遗留骨架                              (1,8)(2,6)(1,8)(3,8) = 29.5  x32   <- 越界
配额带 support = [24, 27]，29.5 超上限 2.5。其余五个角色 0 越界。

口径
----
GDD §3.2 的配额带约束的是「**单英雄 4 技能 damage 骰期望之和**」，
而非单技能均值。骰期望 = dice_count x (dice_size + 1) / 2。
effects[].value（治疗/护盾量）属于独立设计轴，不计入配额带，本流程不改动。

关键约束
--------
R1 之后技能描述**内嵌骰式**（形如 "3d8+WIS光耀伤害。..."），
因此改骰必须同步改写描述里的骰式 token，否则叙事与数值脱节。

用法
----
from battle_platform.workflows import p0d_dice_rebalance as p0d
rep = p0d.audit()                      # 只读审计
rep = p0d.rebalance_all(dry_run=False) # 应用回调
"""
import os
import re
import json
import glob

from .. import paths  # 触发 sys.path 引导

# 单一事实源：直接复用 builder 的骨架与配额带定义，避免常量二次维护
from tools.expansion.builder import ROLE_DICE, ROLE_BAND

# 本流程默认作用于 9 个公版神话 IP
PUBLIC_IPS = [
    "egyptian_mythology", "hindu_mythology", "celtic_mythology",
    "japanese_mythology", "chinese_mythology", "slavic_mythology",
    "aztec_mythology", "arthurian_legend", "arabian_nights",
]

CN2EN = {
    "坦克": "tank", "战士": "fighter", "刺客": "assassin",
    "法师": "mage", "射手": "marksman", "辅助": "support",
}

_DICE_TOKEN = re.compile(r"\d+d\d+")


def dice_expectation(dice_count, dice_size):
    """单技能骰期望。"""
    if not dice_count or not dice_size:
        return 0.0
    return dice_count * (dice_size + 1) / 2.0


def _role_en(card):
    g = card.get("game", {}) if isinstance(card, dict) else {}
    uni = g.get("universal_role")
    if uni in ROLE_DICE:
        return uni
    return CN2EN.get(g.get("native_role") or g.get("role_name"))


def _load(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def band_sum(skills):
    """英雄 4 技能 damage 骰期望之和。"""
    return sum(
        dice_expectation((s.get("damage") or {}).get("dice_count"),
                         (s.get("damage") or {}).get("dice_size"))
        for s in skills if isinstance(s, dict)
    )


def _sync_description(desc, dice_count, dice_size):
    """把描述里第一个骰式 token 同步为新骰值（保留 +ATTR 与其余文字）。"""
    if not desc:
        return desc
    return _DICE_TOKEN.sub(f"{dice_count}d{dice_size}", desc, count=1)


def audit(game_ids=None):
    """只读审计：返回越界英雄清单与统计。"""
    game_ids = game_ids or PUBLIC_IPS
    rows = []
    total = 0
    for g in game_ids:
        for cf in sorted(glob.glob(os.path.join(paths.CARDS_DIR, g, "*.json"))):
            stem = os.path.splitext(os.path.basename(cf))[0]
            card = _load(cf)
            if not card:
                continue
            role = _role_en(card)
            if role not in ROLE_BAND:
                continue
            skills = _load(paths.skill_file(g, stem))
            if not isinstance(skills, list):
                continue
            total += 1
            s = band_sum(skills)
            lo, hi = ROLE_BAND[role]
            if not (lo <= s <= hi):
                rows.append({"game_id": g, "stem": stem, "role": role,
                             "sum": round(s, 1), "band": [lo, hi]})
    return {"checked": total, "out_of_band": len(rows), "rows": rows}


def rebalance_all(game_ids=None, dry_run=False):
    """把越界英雄的 4 技能 damage 骰回调为 builder.ROLE_DICE 官方骨架，
    并同步描述内嵌的骰式。"""
    rep = audit(game_ids)
    fixed = 0
    desc_synced = 0
    errors = []
    samples = []
    for row in rep["rows"]:
        g, stem, role = row["game_id"], row["stem"], row["role"]
        sp = paths.skill_file(g, stem)
        skills = _load(sp)
        if not isinstance(skills, list):
            errors.append(f"{g}/{stem}: 技能文件不可读")
            continue
        skeleton = ROLE_DICE[role]
        before = round(band_sum(skills), 1)
        changed = False
        for i, s in enumerate(skills):
            if not isinstance(s, dict) or i >= len(skeleton):
                continue
            dm = s.get("damage")
            if not isinstance(dm, dict):
                continue
            dc, ds = skeleton[i]
            if dm.get("dice_count") == dc and dm.get("dice_size") == ds:
                continue
            dm["dice_count"], dm["dice_size"] = dc, ds
            new_desc = _sync_description(s.get("description"), dc, ds)
            if new_desc != s.get("description"):
                s["description"] = new_desc
                desc_synced += 1
            changed = True
        if not changed:
            continue
        after = round(band_sum(skills), 1)
        if len(samples) < 6:
            samples.append(f"{g}/{stem} [{role}] {before} -> {after}")
        if not dry_run:
            try:
                with open(sp, "w", encoding="utf-8") as f:
                    json.dump(skills, f, ensure_ascii=False, indent=2)
            except Exception as e:
                errors.append(f"{g}/{stem} write: {e}")
                continue
        fixed += 1
    return {"checked": rep["checked"], "out_of_band_before": rep["out_of_band"],
            "fixed": fixed, "desc_synced": desc_synced,
            "errors": errors, "samples": samples}


if __name__ == "__main__":
    import sys
    dr = "--dry" in sys.argv
    a = audit()
    print(f"审计：{a['checked']} 名英雄，越界 {a['out_of_band']} 名")
    r = rebalance_all(dry_run=dr)
    print(f"回调 {r['fixed']} 名，同步描述骰式 {r['desc_synced']} 条，错误 {len(r['errors'])}")
    for s in r["samples"]:
        print("   " + s)
    print("复审：", audit()["out_of_band"], "名越界" if dr else "名越界（应为 0）")
