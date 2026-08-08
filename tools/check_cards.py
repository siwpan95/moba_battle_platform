#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CI 卡数据契约校验（A7 门禁）。

扫描 data/character_cards 下全部角色卡，发现以下情况即非零退出，阻断合并/发布：
  - 仍存在 dict 格式 skills（双 schema 残留，事故 SEV-2 根因）
  - 违反 core.schema.validate_card 契约（如缺失 hero.name、属性 modifier、技能 type 非法）

用法：
    python tools/check_cards.py
"""
import sys
import os
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARDS_DIR = os.path.join(PROJECT_ROOT, "data", "character_cards")
sys.path.insert(0, PROJECT_ROOT)

from core import schema
from core.loader import iter_card_files


def _load_json(path):
    """读取 JSON，失败返回 None。"""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _role_en(card, role_dice, cn2en):
    """从卡内 game.universal_role（或中文名回退）解析英文角色键。"""
    g = card.get("game", {}) if isinstance(card, dict) else {}
    uni = g.get("universal_role")
    if uni in role_dice:
        return uni
    return cn2en.get(g.get("native_role") or g.get("role_name"))


def check_dual_representation():
    """R4 双表示 CI 守卫——仅针对 9 个公版 IP（PUBLIC_IPS，策展真相源由 per-hero 技能文件掌管）。

    每张公版 IP 卡须满足：
      1. 存在对应 per-hero 技能文件 data/skills/<ip>/<英雄>.json
      2. card.skills 为 list，且长度与技能文件一致
      3. card.skills 与技能文件 name 顺序/集合完全一致
      4. 每个技能 (dice_count, dice_size) 与技能文件一致
      5. 每个技能 description 与技能文件一致
      6. 4 技能骰期望之和落在 GDD ROLE_BAND[role] 区间内

    返回 (errors: list[str], checked: int)。任一条件不满足即产出 error。
    """
    from battle_platform.workflows import p0d_dice_rebalance as p0d
    errors = []
    pub = set(p0d.PUBLIC_IPS)
    band = p0d.ROLE_BAND
    valid_roles = p0d.ROLE_DICE
    cn2en = p0d.CN2EN
    sk_dir = os.path.join(PROJECT_ROOT, "data", "skills")
    checked = 0
    for filepath, gid, stem in iter_card_files(CARDS_DIR):
        if gid not in pub:
            continue
        sp = os.path.join(sk_dir, gid, stem + ".json")
        if not os.path.exists(sp):
            errors.append(f"{filepath}: 公版IP 缺失 per-hero 技能文件 {sp}")
            continue
        sf = _load_json(sp)
        card = _load_json(filepath)
        if not isinstance(sf, list) or card is None or not isinstance(card.get("skills"), list):
            errors.append(f"{filepath}: 技能数据不可比（卡内嵌 skills 缺失或非 list）")
            checked += 1
            continue
        cs = card["skills"]
        if len(cs) != len(sf):
            errors.append(f"{filepath}: 内嵌 skills 长度 {len(cs)} 与技能文件 {len(sf)} 不一致")
            checked += 1
            continue
        cnames = [s.get("name") for s in cs]
        snames = [s.get("name") for s in sf]
        if cnames != snames:
            errors.append(f"{filepath}: 内嵌 skills 名称顺序/集合 与技能文件不一致")
            checked += 1
            continue

        def dice_of(s):
            d = s.get("damage") or {}
            return (d.get("dice_count"), d.get("dice_size"))

        for i, (a, b) in enumerate(zip(cs, sf)):
            if dice_of(a) != dice_of(b):
                errors.append(f"{filepath}: 第{i+1}技能骰不一致 卡{dice_of(a)} vs 文件{dice_of(b)}")
            if (a.get("description") or "") != (b.get("description") or ""):
                errors.append(f"{filepath}: 第{i+1}技能描述不一致")
        role = _role_en(card, valid_roles, cn2en)
        if role in band:
            s = p0d.band_sum(cs)
            lo, hi = band[role]
            if not (lo <= s <= hi):
                errors.append(f"{filepath}: 骰期望之和 {round(s, 1)} 越界 role={role} 带[{lo},{hi}]")
        checked += 1
    return errors, checked


def main() -> int:
    errors: list = []
    scanned = 0
    seen_ids: dict = {}  # card_id -> first filepath
    for filepath, _game_dir, _stem in iter_card_files(CARDS_DIR):
        try:
            with open(filepath, "r", encoding="utf-8") as fh:
                card = json.load(fh)
        except Exception as e:
            errors.append(f"{filepath}: JSON 解析失败 {e}")
            continue
        scanned += 1
        if isinstance(card.get("skills"), dict):
            errors.append(f"{filepath}: 仍存在 dict 格式 skills（双 schema 残留，SEV-2 根因）")
        problems = schema.validate_card(card)
        for p in problems:
            errors.append(f"{filepath}: {p}")
        # ADR-005: card_id 全局唯一性断言
        cid = card.get("card_id")
        if cid:
            if cid in seen_ids:
                errors.append(f"{filepath}: card_id 重复 '{cid}'（首次出现在 {seen_ids[cid]}）")
            else:
                seen_ids[cid] = filepath

    # R4 双表示守卫：公版 IP 卡内嵌 skills 须与 per-hero 技能文件完全一致且骰期望在带内
    derrs, dchecked = check_dual_representation()
    for e in derrs:
        errors.append("[双表示] " + e)

    print(f"契约校验 {scanned} 张卡，发现问题 {len(errors)} 项")
    unique_ids = len(seen_ids)
    if unique_ids != scanned:
        print(f"  card_id 唯一性: {unique_ids}/{scanned}（{'通过' if unique_ids == scanned else '存在重复'}）")
    if dchecked:
        print(f"  双表示守卫: 校验公版IP卡 {dchecked} 张，问题 {len(derrs)} 项")
    for e in errors:
        print("  - " + e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
