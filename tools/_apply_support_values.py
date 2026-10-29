#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给 support 卡的「治疗 / 护盾」effect 补显式数值（骰子表达式）。

背景
----
support 卡的治疗/护盾 effect 此前没有 `value` 字段，simulator 的 `_effect_value()`
会走兜底分支 `int(max_hp * 0.1)`——即每次治疗恢复 10% 最大生命。这在 support
镜像对局中导致「双方回血速度 >= 互相掉血速度」，对局永远打不完（lv18 女娲 vs
山鲁佐德 300 回合双方满血未终结）。设计侧已交付显式数值表，本脚本负责落地。

`value_expr` 为骰子表达式字符串（如 "2d8+WIS"），simulator `_effect_value()`
已支持 `isinstance(v, str)` -> `roll_dice_expr(v, attr_mods, rng)` 解析路径。

严格约束（工程落地任务，不触碰设计）：
  1. 只给命中的 effect **新增** "value" 字段；
     duration / target / desc / type 等一律保持原样，不改不删。
  2. 字节级安全：写盘前先校验「把原始对象重新序列化 == 原始字节」，
     不成立直接跳过并告警，避免伪 diff。
  3. 结构化 diff 断言：变更必须全部是 `...effects[i].value <added>` 形态，
     出现任何「修改既有值 / 删除字段 / 新增其它字段」一律拒绝写盘。
  4. 幂等：effect 已有 value 则跳过（不覆盖已有数值）。
  5. 写盘后回读复验。

数据源：
  数值表   design/support_numeric_fix.json
           { ip_id: { 英雄中文名: { skill_key: { "治疗"|"护盾": "2d8+WIS" } } } }
  技能文件 data/skills/<ip>/<hero>.json
  骨头卡   data/character_cards/<ip>/<hero>.json  (内嵌 skills)

用法：
    python tools/_apply_support_values.py --dry-run
    python tools/_apply_support_values.py
"""

import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FIX_PATH = os.path.join(ROOT, "design", "support_numeric_fix.json")
SKILLS_DIR = os.path.join(ROOT, "data", "skills")
CARDS_DIR = os.path.join(ROOT, "data", "character_cards")

IP_IDS = [
    "arthurian_legend",
    "egyptian_mythology",
    "hindu_mythology",
    "chinese_mythology",
    "japanese_mythology",
    "celtic_mythology",
    "slavic_mythology",
    "aztec_mythology",
    "arabian_nights",
]

TARGET_TYPES = ("治疗", "护盾")

# 允许「新增」的路径白名单：只有 effects[i].value
RE_SKILL_VALUE = re.compile(r"^\[\d+\]\.effects\[\d+\]\.value <added>$")
RE_CARD_VALUE = re.compile(r"^\.skills\[\d+\]\.effects\[\d+\]\.value <added>$")

warnings = []


def warn(msg):
    warnings.append(msg)


# --------------------------------------------------------------------------
# IO helpers
# --------------------------------------------------------------------------

def read_json_file(path):
    raw = io.open(path, "rb").read()
    data = json.loads(raw.decode("utf-8"))
    newline = "\r\n" if b"\r\n" in raw else "\n"
    return data, raw, newline


def serialize(data, newline):
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if newline != "\n":
        text = text.replace("\n", newline)
    return text.encode("utf-8")


def roundtrip_safe(data, raw, newline):
    return serialize(data, newline) == raw


# --------------------------------------------------------------------------
# 结构化 diff：区分「新增字段」与「修改/删除」
# --------------------------------------------------------------------------

def diff_paths(a, b, prefix=""):
    """递归比较，产出差异路径。新增字段标 <added>，删除标 <removed>。"""
    out = []
    if type(a) is not type(b) and not (
        isinstance(a, (int, float)) and isinstance(b, (int, float))
    ):
        out.append(prefix + " <type>")
        return out
    if isinstance(a, dict):
        ka, kb = set(a.keys()), set(b.keys())
        for k in sorted(kb - ka):
            out.append(prefix + "." + str(k) + " <added>")
        for k in sorted(ka - kb):
            out.append(prefix + "." + str(k) + " <removed>")
        for k in a:
            if k in b:
                out.extend(diff_paths(a[k], b[k], prefix + "." + str(k)))
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append(prefix + " <len>")
            return out
        for i, (x, y) in enumerate(zip(a, b)):
            out.extend(diff_paths(x, y, prefix + "[%d]" % i))
    else:
        if a != b:
            out.append(prefix + " <changed>")
    return out


# --------------------------------------------------------------------------
# 核心：给 effect 补 value
# --------------------------------------------------------------------------

def apply_values(skill_list, skmap, where, hero_label):
    """就地给命中的 effect 新增 value。返回 (新增数, 跳过已有数, [(key,type,expr)])。"""
    added = 0
    skipped = 0
    detail = []
    by_key = {}
    for s in skill_list:
        if isinstance(s, dict) and isinstance(s.get("key"), str):
            by_key.setdefault(s["key"].upper(), s)

    for skill_key in sorted(skmap.keys()):
        types = skmap[skill_key]
        skill = by_key.get(str(skill_key).upper())
        if skill is None:
            warn("%s | %s 未找到技能 key=%s，跳过" % (hero_label, where, skill_key))
            continue
        effects = skill.get("effects")
        if not isinstance(effects, list):
            warn("%s | %s key=%s 无 effects list，跳过" % (hero_label, where, skill_key))
            continue
        for ty in sorted(types.keys()):
            expr = types[ty]
            if ty not in TARGET_TYPES:
                warn("%s | %s key=%s 数值表出现非治疗/护盾类型 %r，跳过"
                     % (hero_label, where, skill_key, ty))
                continue
            if not isinstance(expr, str) or not expr.strip():
                warn("%s | %s key=%s type=%s 数值表值非法(%r)，跳过"
                     % (hero_label, where, skill_key, ty, expr))
                continue
            hits = [e for e in effects if isinstance(e, dict) and e.get("type") == ty]
            if not hits:
                warn("%s | %s key=%s 未找到 type=%s 的 effect，跳过"
                     % (hero_label, where, skill_key, ty))
                continue
            if len(hits) > 1:
                warn("%s | %s key=%s 存在 %d 个 type=%s 的 effect，全部套用同一表达式"
                     % (hero_label, where, skill_key, len(hits), ty))
            for eff in hits:
                if "value" in eff:
                    skipped += 1  # 幂等：不覆盖已有数值
                    continue
                eff["value"] = expr
                added += 1
                detail.append((skill_key, ty, expr))
    return added, skipped, detail


def main():
    dry_run = "--dry-run" in sys.argv

    if not os.path.isfile(FIX_PATH):
        print("数值表不存在: %s" % FIX_PATH)
        return 2
    fix = json.load(io.open(FIX_PATH, encoding="utf-8"))

    stats = {
        "cards_in_table": 0,
        "cards_seen": 0,
        "cards_changed": 0,
        "eff_added_skills": 0,
        "eff_added_cards": 0,
        "eff_skipped_existing": 0,
        "files_written": 0,
        "files_skipped_unsafe": 0,
        "verify_failed": 0,
    }
    samples = []

    for ip in sorted(fix.keys()):
        if ip not in IP_IDS:
            warn("数值表出现 9 IP 之外的 ip_id: %s，整体跳过（安全边界）" % ip)
            continue
        for hero in sorted(fix[ip].keys()):
            stats["cards_in_table"] += 1
            skmap = fix[ip][hero]
            hero_label = "%s/%s" % (ip, hero)
            skill_path = os.path.join(SKILLS_DIR, ip, hero + ".json")
            card_path = os.path.join(CARDS_DIR, ip, hero + ".json")

            if not os.path.isfile(skill_path):
                warn("%s | 技能文件缺失 %s，跳过" % (hero_label, skill_path))
                continue
            if not os.path.isfile(card_path):
                warn("%s | 骨头卡缺失 %s，跳过" % (hero_label, card_path))
                continue
            stats["cards_seen"] += 1

            try:
                skills, skill_raw, skill_nl = read_json_file(skill_path)
                card, card_raw, card_nl = read_json_file(card_path)
            except Exception as e:
                warn("%s | 文件解析失败: %s" % (hero_label, e))
                continue

            if not isinstance(skills, list):
                warn("%s | 技能文件不是 list，跳过" % hero_label)
                continue

            role = ((card.get("game") or {}).get("universal_role"))
            if role != "support":
                warn("%s | universal_role=%r 非 support（数值表声明为 support 卡）"
                     % (hero_label, role))

            before_skills = json.loads(skill_raw.decode("utf-8"))
            before_card = json.loads(card_raw.decode("utf-8"))

            n1, sk1, detail = apply_values(skills, skmap, "skills", hero_label)

            card_skills = card.get("skills")
            n2, sk2 = 0, 0
            if isinstance(card_skills, list):
                n2, sk2, _ = apply_values(card_skills, skmap, "card.skills", hero_label)
            elif card_skills is None:
                warn("%s | 骨头卡无 skills 字段" % hero_label)
            else:
                warn("%s | 骨头卡 skills 非 list(%s)，跳过内嵌补值"
                     % (hero_label, type(card_skills).__name__))

            stats["eff_skipped_existing"] += sk1 + sk2

            if n1 == 0 and n2 == 0:
                continue  # 幂等

            stats["cards_changed"] += 1
            stats["eff_added_skills"] += n1
            stats["eff_added_cards"] += n2
            if len(samples) < 4 and detail:
                samples.append((hero_label, detail))

            for path, data, raw, nl, before, allow_re in (
                (skill_path, skills, skill_raw, skill_nl, before_skills, RE_SKILL_VALUE),
                (card_path, card, card_raw, card_nl, before_card, RE_CARD_VALUE),
            ):
                rel = os.path.relpath(path, ROOT)
                if not roundtrip_safe(before, raw, nl):
                    warn("%s | %s 序列化风格不一致，拒绝写盘（防伪 diff）" % (hero_label, rel))
                    stats["files_skipped_unsafe"] += 1
                    continue

                bad = [p for p in diff_paths(before, data) if not allow_re.match(p)]
                if bad:
                    warn("%s | %s 检测到白名单外变更 %s，拒绝写盘" % (hero_label, rel, bad[:5]))
                    stats["files_skipped_unsafe"] += 1
                    continue

                if dry_run:
                    continue

                payload = serialize(data, nl)
                with io.open(path, "wb") as fh:
                    fh.write(payload)
                if io.open(path, "rb").read() != payload:
                    warn("%s | %s 写后复验失败" % (hero_label, rel))
                    stats["verify_failed"] += 1
                    continue
                stats["files_written"] += 1

    mode = "DRY_RUN（不写盘）" if dry_run else "WRITE（已写盘）"
    print("=" * 60)
    print("support 治疗/护盾 显式数值落地   模式: %s" % mode)
    print("=" * 60)
    print("数值表卡数     : %d" % stats["cards_in_table"])
    print("磁盘命中卡数   : %d" % stats["cards_seen"])
    print("改动卡数       : %d" % stats["cards_changed"])
    print("新增 value(skills) : %d" % stats["eff_added_skills"])
    print("新增 value(骨头卡) : %d" % stats["eff_added_cards"])
    print("幂等跳过(已有value): %d" % stats["eff_skipped_existing"])
    print("写入文件       : %d" % stats["files_written"])
    print("安全跳过文件   : %d" % stats["files_skipped_unsafe"])
    print("写后复验失败   : %d" % stats["verify_failed"])
    print("warning        : %d" % len(warnings))
    for w in warnings:
        print("  - " + w)

    if samples:
        print("-" * 60)
        print("补值样例：")
        for hero_label, detail in samples:
            print("  [%s]" % hero_label)
            for key, ty, expr in detail:
                print("      %s %s -> value=%s" % (key, ty, expr))
    print("=" * 60)

    if stats["files_skipped_unsafe"] or stats["verify_failed"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
