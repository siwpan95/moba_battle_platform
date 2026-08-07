#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wave 0 数据再生 dry-run：预览 `generate --all` 会把 1659 张卡改成什么样。
**绝不写盘** —— 仅对比新/旧卡差异并产出变更报告。

用法：
  python tools/_archive/wave0_dryrun.py [--sample N] [--output report.md]

  --sample N   仅抽样 N 张卡做耗时外推（默认全量 1659）
  --output     报告输出路径（默认 production/wave0-dryrun-report.md）
"""

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from typing import Dict, List, Tuple

# ── 路径设置 ──────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "tools"))

from hero_name_mapping import HERO_NAME_CN
from core.config import GAME_REGISTRY, REGISTRY_BY_DISPLAY, REGISTRY_BY_ID, GAME_NAME_CN
from core.registry import ROLE_NAME_CN

# ── 导入生成器核心函数 ───────────────────────────────────
from card_generator import (
    generate_character_card, get_skills,
    ABILITY_NAMES, ABILITY_CN,
    CLASS_DEF, ROLE_CN, ROLE_DND,
)

INPUT_JSON = os.path.join(PROJECT_ROOT, "data", "analysis", "all_heroes_unified.json")
CARDS_DIR = os.path.join(PROJECT_ROOT, "data", "character_cards")


# ═══════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════

def slugify(name: str) -> str:
    return name.replace(" ", "_").replace("/", "_").replace(":", "").replace("\\", "_")


def load_heroes() -> list:
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        return json.load(f).get("heroes", [])


def build_hero_lookup(heroes: list) -> dict:
    """构建 (game_display, hero_translated_name) → hero_dict 的查找表。"""
    lookup = {}
    for h in heroes:
        game = h["game"]
        raw_name = h["name"]
        translated = HERO_NAME_CN.get(raw_name, raw_name)
        lookup.setdefault(game, {})[translated] = h
        lookup.setdefault(game, {})[raw_name] = h
    return lookup


def load_existing_cards() -> List[Tuple[str, dict]]:
    """加载所有磁盘卡片，返回 [(rel_path, card_dict), ...]"""
    cards = []
    for dirpath, dirnames, filenames in os.walk(CARDS_DIR):
        dirnames[:] = [d for d in dirnames if not d.startswith("_")]
        for fn in filenames:
            if fn.startswith("_") or not fn.endswith(".json"):
                continue
            filepath = os.path.join(dirpath, fn)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    card = json.load(f)
                rel = os.path.relpath(filepath, CARDS_DIR)
                cards.append((rel, card))
            except Exception as e:
                print(f"[WARN] 加载失败 {filepath}: {e}", file=sys.stderr)
    return cards


def compute_new_card_id(game_display: str, hero_translated_name: str) -> str:
    """计算 ADR-005 新 card_id = <game_id>:<hero_slug>"""
    game_id = REGISTRY_BY_DISPLAY.get(game_display, slugify(game_display).lower())
    hero_slug = slugify(hero_translated_name)
    return f"{game_id}:{hero_slug}"


def classify_old_card(card: dict) -> str:
    """按旧卡 skills 长度分类。"""
    skills = card.get("skills", [])
    if not isinstance(skills, list):
        return "non_list"
    n = len(skills)
    if n == 1:
        return "list_1"
    elif n == 4:
        return "list_4"
    elif n == 12:
        return "list_12"
    elif n == 3:
        return "list_3"
    else:
        return f"list_{n}"


def skills_fingerprint(skills: list) -> str:
    """生成技能列表的指纹：4个key对应的技能名拼接。"""
    if not skills or not isinstance(skills, list):
        return "NONE"
    parts = []
    for s in skills:
        if isinstance(s, dict):
            parts.append(f"{s.get('key','?')}:{s.get('name','?')}")
        else:
            parts.append(str(s)[:30])
    return "|".join(parts)


def compare_cards(old_card: dict, new_card: dict) -> dict:
    """逐卡对比，返回差异摘要。"""
    result = {
        "old_card_id": old_card.get("card_id", "?"),
        "new_card_id": new_card.get("card_id", "?"),
        "card_id_changed": old_card.get("card_id") != new_card.get("card_id"),
        "old_skills_len": len(old_card.get("skills", [])),
        "new_skills_len": len(new_card.get("skills", [])),
        "skills_len_changed": len(old_card.get("skills", [])) != len(new_card.get("skills", [])),
        "old_skills_fp": skills_fingerprint(old_card.get("skills", [])),
        "new_skills_fp": skills_fingerprint(new_card.get("skills", [])),
        "skills_content_changed": (
            skills_fingerprint(old_card.get("skills", []))
            != skills_fingerprint(new_card.get("skills", []))
        ),
        "old_class": classify_old_card(old_card),
    }
    result["change_category"] = _categorize(result, old_card, new_card)
    # 技能槽真正被填充：旧卡不足4槽 且 新卡为4槽
    result["skills_filled"] = (
        len(old_card.get("skills", [])) != 4
        and len(new_card.get("skills", [])) == 4
    )
    return result


def _categorize(r: dict, old_card: dict, new_card: dict) -> str:
    """分类变更类型。"""
    old_len = r["old_skills_len"]
    new_len = r["new_skills_len"]

    if old_len == 1 and new_len == 4:
        return "list_1_to_4"
    elif old_len == 12 and new_len == 4:
        return "list_12_to_4"
    elif old_len == 3 and new_len == 4:
        return "list_3_to_4"
    elif old_len == 3 and new_len == 3:
        # Vainglory 有真实 A/B/U 技能数据，保持 3 技能（card_id 变更）
        if r["skills_content_changed"]:
            return "list_3_content_changed"
        else:
            return "card_id_only"
    elif old_len == 4 and new_len == 4:
        if r["skills_content_changed"]:
            return "list_4_content_changed"
        else:
            return "card_id_only"
    elif old_len != 4 and new_len == 4:
        return f"list_{old_len}_to_4"
    else:
        return "other"


def ip_from_game(game_display: str) -> str:
    """从游戏显示名提取 IP（优先用中文名）。"""
    cn = GAME_NAME_CN.get(game_display, game_display)
    # 特殊归类
    ip_map = {
        "300英雄": "300大作战",
        "传说对决": "传说对决",
        "刀塔2": "Dota",
        "非人学园": "非人学园",
        "风暴英雄": "暴雪",
        "港漫群英": "港漫",
        "王者荣耀": "王者荣耀",
        "英雄联盟": "英雄联盟",
        "漫威超级战争": "漫威",
        "无尽对决": "无尽对决",
        "决战！平安京": "阴阳师",
        "宝可梦大集结": "宝可梦",
        "曙光英雄": "曙光英雄",
        "神之浩劫": "SMITE",
        "虚荣": "虚荣",
        "英魂之刃": "英魂之刃",
        "原神": "原神",
        "守望先锋2": "暴雪",
        "漫威电影宇宙": "漫威",
        "DC宇宙": "DC",
        "哈利波特": "哈利波特",
        "三体": "三体",
        "鬼灭之刃": "鬼灭之刃",
        "海贼王": "海贼王",
    }
    return ip_map.get(cn, cn)


# ═══════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════

def run_dryrun(sample_size: int = None) -> Tuple[dict, list, float]:
    """
    执行 dry-run 对比。

    Returns:
        (summary_dict, detail_list, elapsed_seconds)
    """
    print("=" * 60)
    print("  Wave 0 数据再生 dry-run")
    print("=" * 60)

    # 1. 加载数据
    print("\n[1/4] 加载数据...")
    heroes = load_heroes()
    hero_lookup = build_hero_lookup(heroes)
    disk_cards = load_existing_cards()
    print(f"  ✓ 统一数据: {len(heroes)} 位英雄")
    print(f"  ✓ 磁盘卡片: {len(disk_cards)} 张")

    if sample_size and sample_size < len(disk_cards):
        import random
        random.seed(42)
        disk_cards = random.sample(disk_cards, sample_size)
        print(f"  ⚠ 抽样模式: {sample_size} 张")

    # 2. 逐卡对比
    print(f"\n[2/4] 逐卡生成 & 对比... (不写盘)")
    t0 = time.time()
    details = []
    unmatched = 0
    schema_errors = 0

    for idx, (rel_path, old_card) in enumerate(disk_cards):
        game_display = old_card.get("game", {}).get("name", "")
        hero_name = old_card.get("hero", {}).get("name", "")

        # 匹配 hero 数据
        hero_entry = None
        if game_display in hero_lookup:
            hero_entry = hero_lookup[game_display].get(hero_name)

        if hero_entry is None:
            unmatched += 1
            details.append({
                "rel_path": rel_path,
                "old_card_id": old_card.get("card_id", "?"),
                "error": f"无法匹配 hero 条目: game={game_display}, hero={hero_name}",
            })
            continue

        # 生成新卡
        try:
            new_card = generate_character_card(hero_entry, idx + 1000)
        except Exception as e:
            details.append({
                "rel_path": rel_path,
                "old_card_id": old_card.get("card_id", "?"),
                "error": f"生成失败: {e}",
            })
            continue

        # 契约校验
        from core import schema
        violations = schema.validate_card(new_card)
        if violations:
            schema_errors += 1

        # 对比
        diff = compare_cards(old_card, new_card)
        diff["rel_path"] = rel_path
        diff["game_display"] = game_display
        diff["hero_name"] = hero_name
        diff["ip"] = ip_from_game(game_display)
        diff["schema_violations"] = violations
        details.append(diff)

        if (idx + 1) % 200 == 0:
            print(f"    已处理 {idx+1}/{len(disk_cards)}...")

    elapsed = time.time() - t0
    print(f"  ✓ 完成 {len(details)} 张卡对比，耗时 {elapsed:.1f}s")

    if unmatched:
        print(f"  ⚠ 无法匹配: {unmatched} 张")
    if schema_errors:
        print(f"  ⚠ 契约校验失败: {schema_errors} 张（新生成卡）")

    # 3. 汇总统计
    print(f"\n[3/4] 汇总统计...")
    summary = _build_summary(details, elapsed, sample_size, len(disk_cards), len(heroes))

    # 4. 打印摘要
    print(f"\n[4/4] 摘要:")
    _print_summary(summary)

    return summary, details, elapsed


def _build_summary(details: list, elapsed: float, sample_size: int,
                   processed: int, total_heroes: int) -> dict:
    """从详情列表构建汇总统计。"""
    by_category = defaultdict(list)
    by_ip = defaultdict(lambda: defaultdict(int))

    for d in details:
        cat = d.get("change_category", "error")
        by_category[cat].append(d)
        ip = d.get("ip", "未知")
        by_ip[ip]["total"] += 1
        by_ip[ip][cat] += 1

    # 统计
    total = len(details)
    list_1_to_4 = len(by_category.get("list_1_to_4", []))
    list_12_to_4 = len(by_category.get("list_12_to_4", []))
    list_3_to_4 = len(by_category.get("list_3_to_4", []))
    list_3_content_changed = len(by_category.get("list_3_content_changed", []))
    card_id_only = len(by_category.get("card_id_only", []))
    list_4_content_changed = len(by_category.get("list_4_content_changed", []))
    other = len(by_category.get("other", []))
    errors = len(by_category.get("error", [])) if "error" in by_category else sum(
        1 for d in details if "error" in d)

    # 涉及 IP
    ips_involved = sorted(by_ip.keys())

    # card_id 变更统计
    card_id_changed = sum(1 for d in details if d.get("card_id_changed"))

    # skills 内容不变的卡（仅 card_id 变）
    skills_unchanged = sum(
        1 for d in details
        if not d.get("skills_content_changed") and not d.get("skills_len_changed")
        and "error" not in d
    )

    # skills slots filled (从非4槽变为4槽)
    slots_filled = sum(1 for d in details if d.get("skills_filled"))

    # 估算全量耗时
    if sample_size:
        est_total = elapsed / sample_size * total_heroes
    else:
        est_total = elapsed

    # card_id_only 中区分"原4槽完整"和"原3槽(Vainglory真实数据)"
    card_id_only_ex_list3 = sum(
        1 for d in by_category.get("card_id_only", [])
        if d.get("old_class") == "list_3"
    )
    card_id_only_list4 = card_id_only - card_id_only_ex_list3

    return {
        "total_cards": total,
        "errors": errors,
        "ips_involved": ips_involved,
        "ip_count": len(ips_involved),
        # 按变更类型
        "list_1_to_4": list_1_to_4,
        "list_1_to_4_ips": _ips_for_cat(by_category, "list_1_to_4"),
        "list_12_to_4": list_12_to_4,
        "list_12_to_4_ips": _ips_for_cat(by_category, "list_12_to_4"),
        "list_3_to_4": list_3_to_4,
        "list_3_to_4_ips": _ips_for_cat(by_category, "list_3_to_4"),
        "list_3_content_changed": list_3_content_changed,
        "card_id_only": card_id_only,
        "card_id_only_list4": card_id_only_list4,
        "card_id_only_ex_list3": card_id_only_ex_list3,
        "card_id_only_ips": _ips_for_cat(by_category, "card_id_only"),
        "list_4_content_changed": list_4_content_changed,
        "card_id_changed": card_id_changed,
        "skills_unchanged": skills_unchanged,
        "slots_filled": slots_filled,
        # 按 IP
        "by_ip": dict(by_ip),
        # 耗时
        "elapsed_sec": elapsed,
        "sample_size": sample_size,
        "processed": processed,
        "total_heroes": total_heroes,
        "est_full_time_sec": est_total,
    }


def _ips_for_cat(by_category: dict, cat: str) -> list:
    """某类别涉及的 IP 列表。"""
    ips = set()
    for d in by_category.get(cat, []):
        ips.add(d.get("ip", "未知"))
    return sorted(ips)


def _print_summary(s: dict):
    """终端打印摘要。"""
    print(f"    总卡数: {s['total_cards']}")
    print(f"    错误: {s['errors']}")
    print(f"    涉及 IP: {s['ip_count']} 个")
    print(f"    ")
    print(f"    card_id 会变: {s['card_id_changed']} 张 (应全部)")
    print(f"    skills 内容不变: {s['skills_unchanged']} 张")
    print(f"    技能槽填充: {s['slots_filled']} 张 (从 <4 → 4)")
    print(f"    ")
    print(f"    list[1] → list[4]: {s['list_1_to_4']} 张")
    print(f"    list[12] → list[4]: {s['list_12_to_4']} 张")
    print(f"    list[3] → list[4]: {s['list_3_to_4']} 张")
    print(f"    list[3] 内容变: {s.get('list_3_content_changed', 0)} 张")
    print(f"    list[4] 内容变: {s['list_4_content_changed']} 张")
    print(f"    仅 card_id 变: {s['card_id_only']} 张 (其中原4槽: {s.get('card_id_only_list4', '?')}, 原3槽Vainglory: {s.get('card_id_only_ex_list3', '?')})")
    print(f"    ")
    print(f"    耗时: {s['elapsed_sec']:.1f}s (处理 {s['processed']} 张)")
    if s.get("sample_size"):
        print(f"    全量预估: ~{s['est_full_time_sec']:.0f}s")


# ═══════════════════════════════════════════════════════════
# 报告生成
# ═══════════════════════════════════════════════════════════

def generate_report(summary: dict, details: list, output_path: str):
    """生成 Markdown 变更报告。"""
    lines = []
    w = lines.append

    w("# Wave 0 数据再生 dry-run 变更报告")
    w("")
    w(f"**生成时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    w(f"**工具**: `tools/_archive/wave0_dryrun.py`")
    w(f"**模式**: {'抽样 ' + str(summary['sample_size']) + ' 张' if summary.get('sample_size') else '全量 ' + str(summary['total_cards']) + ' 张'}")
    w("")
    w("---")
    w("")

    # ── 总览 ──
    w("## 1. 总览")
    w("")
    w(f"| 指标 | 数值 |")
    w(f"|------|------|")
    w(f"| 磁盘卡片总数 | **{summary['total_cards']}** |")
    w(f"| 涉及 IP 数 | {summary['ip_count']} |")
    w(f"| card_id 会变更 | **{summary['card_id_changed']}** 张（全量） |")
    w(f"| skills 内容不变（仅 card_id 变） | {summary['skills_unchanged']} 张 |")
    w(f"| 技能槽填充（<4 → 4） | **{summary['slots_filled']}** 张 |")
    w(f"| 错误/无法处理 | {summary['errors']} 张 |")
    w(f"| dry-run 耗时 | {summary['elapsed_sec']:.1f}s |")
    if summary.get("sample_size"):
        w(f"| 全量预估耗时 | ~{summary['est_full_time_sec']:.0f}s (~{summary['est_full_time_sec']/60:.1f}min) |")
    else:
        w(f"| 全量实际耗时 | {summary['elapsed_sec']:.1f}s (~{summary['elapsed_sec']/60:.1f}min) |")
    w("")

    # ── 按变更类型 ──
    w("## 2. 按变更类型分类")
    w("")
    w("| 变更类型 | 数量 | 占比 | 涉及 IP |")
    w("|----------|------|------|---------|")

    total = summary['total_cards']
    rows = [
        ("🔴 list[1]（残卡 → list[4]）", summary['list_1_to_4'],
         ", ".join(summary['list_1_to_4_ips'][:8]) + ("..." if len(summary['list_1_to_4_ips']) > 8 else "")),
        ("🟡 list[12]（死数据冗余 → list[4]）", summary['list_12_to_4'],
         ", ".join(summary['list_12_to_4_ips'][:8]) + ("..." if len(summary['list_12_to_4_ips']) > 8 else "")),
        ("🟠 list[3]（Vainglory 真实数据 → list[3]，仅 card_id 变）", summary.get('card_id_only_ex_list3', 0),
         "虚荣 (Vainglory) — A/B/U 键位，技能 DB 有真实数据"),
        ("🟢 card_id 变更（全量）", summary['card_id_changed'],
         f"全部 {summary['ip_count']} 个 IP"),
        ("🟢 无实质变化（仅 card_id，原4槽）", summary.get('card_id_only_list4', summary['card_id_only']),
         ", ".join(summary['card_id_only_ips'][:8]) + ("..." if len(summary['card_id_only_ips']) > 8 else "")),
        ("🔵 list[4] 内容变化（同4槽但技能不同）", summary['list_4_content_changed'],
         ", ".join(summary.get('list_4_content_changed_ips', summary['card_id_only_ips']))[:60]),
    ]
    for label, count, ips in rows:
        pct = f"{count/total*100:.1f}%" if total > 0 else "0%"
        w(f"| {label} | {count} | {pct} | {ips} |")
    w("")

    # ── card_id 格式说明 ──
    w("### 2.1 card_id 格式变更说明")
    w("")
    w("旧格式示例: `ARE-1247`, `300-1080`, `LOL-1400`（前缀+序号，不稳定）")
    w("新格式示例: `arena_of_valor:爱里`, `300_heroes:零二`（`game_id:hero_slug`，幂等稳定）")
    w("")
    w("这是 **ADR-005** 规定的破坏性变更：card_id 从\"生成序号\"语义变为\"物理路径同构\"语义。")
    w("全部 1659 张卡的 card_id 都会变为新格式。")
    w("")

    # ── list[1] 详情 ──
    if summary['list_1_to_4'] > 0:
        w("### 2.2 list[1] → list[4]：残卡修复详情")
        w("")
        w(f"共 **{summary['list_1_to_4']}** 张卡当前仅有 1 个占位技能，")
        w("再生后将获得完整的 4 技能（Q/W/E/R）。这些卡来自技能数据库缺失或模板回退异常的游戏。")
        w("")
        w("**涉及 IP**:")
        for ip in summary['list_1_to_4_ips']:
            count = summary['by_ip'].get(ip, {}).get('list_1_to_4', 0)
            w(f"- {ip}: {count} 张")
        w("")

    # ── list[12] 详情 ──
    if summary['list_12_to_4'] > 0:
        w("### 2.3 list[12] → list[4]：死数据冗余清理")
        w("")
        w(f"共 **{summary['list_12_to_4']}** 张卡当前包含 12 个技能（`_flatten_templates` 旧 bug 导致")
        w("模板子列表未去重全部展平）。再生后 `get_skills()` 将只返回 4 个技能。")
        w("")
        w("**涉及 IP**:")
        for ip in summary['list_12_to_4_ips']:
            count = summary['by_ip'].get(ip, {}).get('list_12_to_4', 0)
            w(f"- {ip}: {count} 张")
        w("")

    # ── Vainglory list[3] 特殊说明 ──
    if summary.get('card_id_only_ex_list3', 0) > 0:
        w("### 2.4 Vainglory list[3]：真实技能数据（非缺陷）")
        w("")
        w(f"共 **{summary['card_id_only_ex_list3']}** 张 Vainglory（虚荣）卡当前为 3 技能（A/B/U 键位），")
        w("再生后仍为 3 技能，内容不变。这些卡技能数据库中有真实数据（如\"阿喀琉斯射击\"、\"银舞\"等），")
        w("使用原游戏键位格式（非 Q/W/E/R），且条目数为 3。**这不是缺陷**，是对原游戏技能系统的忠实还原。")
        w("")
        w("唯一变更：card_id 格式从 `VAI-NNNN` → `vainglory:<英雄名>`。")
        w("")

    # ── 仅 card_id 变更 ──
    if summary['card_id_only'] > 0:
        w("### 2.5 仅 card_id 变更（已完整卡）")
        w("")
        c4 = summary.get('card_id_only_list4', 0)
        c3 = summary.get('card_id_only_ex_list3', 0)
        w(f"共 **{summary['card_id_only']}** 张卡 skills 内容与再生后完全一致，唯一变更是 card_id 格式。")
        w(f"其中 {c4} 张是标准 list[4] 卡（Q/W/E/R 四槽完整），")
        w(f"{c3} 张是 Vainglory list[3] 卡（A/B/U 键位，技能数据库有真实数据，保持 3 技能不变）。")
        w("")

    # ── 按 IP 分布 ──
    w("## 3. 按 IP 分布")
    w("")
    w("| IP | 总卡数 | list[1]→4 | list[12]→4 | list[3]变 | 仅card_id | 内容变 |")
    w("|----|--------|-----------|------------|---------|-----------|--------|")

    for ip in sorted(summary['by_ip'].keys()):
        stats = summary['by_ip'][ip]
        # list[3]变 = list_3_to_4 + list_3_content_changed (Vainglory 真实数据不变的不在此列，归入 card_id_only)
        list3_changed = stats.get('list_3_to_4', 0) + stats.get('list_3_content_changed', 0)
        w(f"| {ip} | {stats['total']} "
          f"| {stats.get('list_1_to_4', 0)} "
          f"| {stats.get('list_12_to_4', 0)} "
          f"| {list3_changed} "
          f"| {stats.get('card_id_only', 0)} "
          f"| {stats.get('list_4_content_changed', 0)} |")
    w("")

    # ── 风险提示 ──
    w("## 4. 风险提示")
    w("")
    w("### 4.1 card_id 破坏性变更（🔴 高风险）")
    w("")
    w("- **影响范围**: 全部 1659 张卡")
    w("- **破坏性质**: 所有依赖旧 card_id 的外部引用（数据库、API、缓存、URL）将失效")
    w("- **缓解措施**: 新卡保留 `legacy_card_id` 字段供过渡期回查；外部系统需同步更新引用")
    w("")
    w("### 4.2 list[4] 已完整卡的 card_id 变更")
    w("")
    w(f"- 共 {summary['card_id_only']} 张卡 skills 内容不变但 card_id 会变")
    w("- 这些卡的数据质量本身合格，card_id 变更是格式统一化的副作用")
    w("- **建议**: 对这些卡，card_id 变更不可避免（新格式是幂等衍生的），但数据内容不需重新生成")
    w("")
    w("### 4.3 list[4] 内容变化")
    w("")
    w(f"- 共 {summary['list_4_content_changed']} 张卡已有 4 技能但再生后技能名称/描述不同")
    w("- 原因：`get_skills()` 中 `random.sample(flat, 4)` 非确定性——模板回退路径每次随机选不同组合")
    w("- 这不影响数据完整性，但意味着\"看起来一样的卡\"也会变内容")
    w("")

    # ── 建议 ──
    w("## 5. 建议")
    w("")
    w("### 5.1 是否可只 regener 有缺陷卡？")
    w("")
    w("**技术上可行，但不推荐。**")
    w("")
    w("理由：")
    w("1. card_id 格式变更（ADR-005）是全量的——即使只 regener 缺陷卡，已完整卡的 card_id 仍是旧格式，")
    w("   会导致同一项目内 card_id 格式不统一，破坏 ADR-005 的幂等保证")
    w("2. 如果将 card_id 迁移和 skills 修复分开执行：")
    w("   - **Phase A**: 全量运行 card_id 迁移脚本（仅改 card_id，不动 skills）→ 已完整卡零风险")
    w(f"   - **Phase B**: 仅 regener 缺陷卡（list[1]: {summary['list_1_to_4']} 张 + list[12]: {summary['list_12_to_4']} 张 + list[3]: {summary['list_3_to_4']} 张）→ 仅改有问题的卡")
    w("3. 或者：全量 regenerate 并接受全部 1659 张卡都会变化（card_id 全变 + 缺陷卡 skills 修复）")
    w("")
    w("### 5.2 推荐方案")
    w("")
    w("| 方案 | 变更范围 | 风险 | 推荐度 |")
    w("|------|----------|------|--------|")
    w(f"| **A. 全量 regenerate** | 全部 1659 张（card_id + skills） | 最大范围变更，需完整回归测试 | ⭐⭐⭐ |")
    w(f"| **B. 分阶段** | Phase A: card_id 迁移 1659 张 → Phase B: skills 修复 {summary['list_1_to_4'] + summary['list_12_to_4'] + summary['list_3_to_4']} 张 | 可控，两次部署 | ⭐⭐⭐⭐（推荐） |")
    w(f"| **C. 仅修复缺陷卡** | {summary['list_1_to_4'] + summary['list_12_to_4'] + summary['list_3_to_4']} 张（card_id + skills） | card_id 格式不统一 | ⭐⭐ |")
    w("")
    w("### 5.3 list[4] 模板技能的随机性问题")
    w("")
    w(f"{summary['list_4_content_changed']} 张已有 4 技能的卡在再生后技能内容也会变化（模板随机选择）。")
    w("如果希望这些卡的内容保持稳定，需要在 `get_skills()` 的模板回退路径中使用")
    w("基于英雄名的确定性选择取代 `random.sample()`。")
    w("")
    w("---")
    w("")
    w(f"*报告由 `wave0_dryrun.py` 自动生成，未对 `data/character_cards/` 做任何写操作。*")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n✓ 报告已写入: {output_path}")


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Wave 0 数据再生 dry-run")
    parser.add_argument("--sample", type=int, default=None,
                        help="抽样数量（用于耗时估算；默认全量）")
    parser.add_argument("--output", type=str,
                        default=os.path.join(PROJECT_ROOT, "production", "wave0-dryrun-report.md"),
                        help="报告输出路径")
    args = parser.parse_args()

    summary, details, elapsed = run_dryrun(sample_size=args.sample)
    generate_report(summary, details, args.output)

    # 回传主理人的一句话
    msg = (
        f"Wave 0 dry-run 完成：{summary['total_cards']} 张卡中 "
        f"list[1]→4: {summary['list_1_to_4']} 张, "
        f"list[12]→4: {summary['list_12_to_4']} 张, "
        f"list[3]→4: {summary['list_3_to_4']} 张, "
        f"仅card_id变: {summary['card_id_only']} 张, "
        f"涉及 {summary['ip_count']} 个 IP。"
        f"报告: {args.output}"
    )
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")
    return msg


if __name__ == "__main__":
    main()
