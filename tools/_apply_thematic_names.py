#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按「主题化技能命名表」批量改写 9 个公版 IP 的技能 name 字段。

严格约束（工程落地任务，不触碰设计）：
  1. 只改写技能 dict 的 "name" 字符串；其它字段、属性、文件一律不动。
  2. 字节级安全：写盘前先校验「把原始对象重新序列化 == 原始字节」，
     不成立说明本脚本的格式化风格与该文件不一致，直接跳过并告警，
     避免因缩进/换行/转义差异产生大面积伪 diff。
  3. 幂等：name 已经等于目标值则不写盘，重复运行为无变化。
  4. 写盘后回读做结构化 diff，断言「除目标 name 外无任何字段变化」。

数据源：
  命名表   design/skill_naming/thematic_skill_names.json
           { ip_id: { role: { "Q"/"W"/"E"/"R": name } } }
  技能文件 data/skills/<ip>/<hero>.json            (list of 4 skill dict)
  骨头卡   data/character_cards/<ip>/<hero>.json   (game.universal_role + 内嵌 skills)

用法：
    F:/Python314/python.exe tools/_apply_thematic_names.py --dry-run
    F:/Python314/python.exe tools/_apply_thematic_names.py
"""

import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NAMES_PATH = os.path.join(ROOT, "design", "skill_naming", "thematic_skill_names.json")
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

SLOT_ORDER = ["Q", "W", "E", "R"]
VALID_SLOTS = set(SLOT_ORDER)

warnings = []


def warn(msg):
    warnings.append(msg)


# --------------------------------------------------------------------------
# IO helpers：保持原文件的换行风格与结尾字节
# --------------------------------------------------------------------------

def read_json_file(path):
    """返回 (data, raw_bytes, newline)。"""
    raw = io.open(path, "rb").read()
    text = raw.decode("utf-8")
    data = json.loads(text)
    newline = "\r\n" if b"\r\n" in raw else "\n"
    return data, raw, newline


def serialize(data, newline):
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if newline != "\n":
        text = text.replace("\n", newline)
    return text.encode("utf-8")


def roundtrip_safe(data, raw, newline):
    """原对象重新序列化后是否与原始字节完全一致。"""
    return serialize(data, newline) == raw


# --------------------------------------------------------------------------
# 结构化 diff：确认只有 name 变了
# --------------------------------------------------------------------------

def diff_paths(a, b, prefix=""):
    """递归比较两个 JSON 对象，产出所有不一致的路径。"""
    out = []
    if type(a) is not type(b) and not (
        isinstance(a, (int, float)) and isinstance(b, (int, float))
    ):
        out.append(prefix + " <type>")
        return out
    if isinstance(a, dict):
        if set(a.keys()) != set(b.keys()):
            out.append(prefix + " <keys>")
            return out
        for k in a:
            out.extend(diff_paths(a[k], b[k], prefix + "." + str(k)))
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append(prefix + " <len>")
            return out
        for i, (x, y) in enumerate(zip(a, b)):
            out.extend(diff_paths(x, y, prefix + "[%d]" % i))
    else:
        if a != b:
            out.append(prefix)
    return out


# --------------------------------------------------------------------------
# 核心改名
# --------------------------------------------------------------------------

def slot_of(skill, index):
    """取技能槽位：优先 key 字段，缺失则按列表顺序兜底。"""
    key = skill.get("key")
    if isinstance(key, str) and key.upper() in VALID_SLOTS:
        return key.upper(), False
    if 0 <= index < len(SLOT_ORDER):
        return SLOT_ORDER[index], True
    return None, True


def rename_skill_list(skill_list, slot_map, where, hero_label):
    """就地改写 name，返回 (改动数, [(slot, old, new)])。"""
    changed = 0
    detail = []
    for i, skill in enumerate(skill_list):
        if not isinstance(skill, dict):
            warn("%s | %s 第 %d 个技能不是 dict，跳过" % (hero_label, where, i))
            continue
        slot, fallback = slot_of(skill, i)
        if slot is None:
            warn("%s | %s 第 %d 个技能无法判定槽位，保留原名" % (hero_label, where, i))
            continue
        if fallback:
            warn("%s | %s 第 %d 个技能 key 缺失/非法(%r)，按顺序兜底为 %s"
                 % (hero_label, where, i, skill.get("key"), slot))
        if slot not in slot_map:
            warn("%s | %s 槽位 %s 不在命名表中，保留原名 %r"
                 % (hero_label, where, slot, skill.get("name")))
            continue
        new_name = slot_map[slot]
        old_name = skill.get("name")
        if old_name != new_name:
            skill["name"] = new_name
            changed += 1
            detail.append((slot, old_name, new_name))
    return changed, detail


def main():
    dry_run = "--dry-run" in sys.argv

    if not os.path.isfile(NAMES_PATH):
        print("命名表不存在: %s" % NAMES_PATH)
        return 2
    names = json.load(io.open(NAMES_PATH, encoding="utf-8"))

    stats = {
        "heroes_seen": 0,
        "heroes_changed": 0,
        "skills_changed": 0,
        "files_written": 0,
        "files_skipped_unsafe": 0,
    }
    samples = []

    for ip in IP_IDS:
        sdir = os.path.join(SKILLS_DIR, ip)
        cdir = os.path.join(CARDS_DIR, ip)
        if not os.path.isdir(sdir):
            warn("IP 技能目录缺失: %s" % sdir)
            continue
        if ip not in names:
            warn("命名表缺少 IP: %s，该 IP 全部跳过" % ip)
            continue

        for fn in sorted(os.listdir(sdir)):
            if not fn.endswith(".json"):
                continue
            hero = fn[:-5]
            hero_label = "%s/%s" % (ip, hero)
            skill_path = os.path.join(sdir, fn)
            card_path = os.path.join(cdir, fn)
            stats["heroes_seen"] += 1

            if not os.path.isfile(card_path):
                warn("%s | 骨头卡缺失 %s，跳过（无法确定 role）" % (hero_label, card_path))
                continue

            # --- 读卡取 role ---
            try:
                card, card_raw, card_nl = read_json_file(card_path)
            except Exception as e:
                warn("%s | 骨头卡解析失败: %s" % (hero_label, e))
                continue
            role = (card.get("game") or {}).get("universal_role")
            if not isinstance(role, str) or not role:
                warn("%s | game.universal_role 缺失或非法(%r)，跳过" % (hero_label, role))
                continue
            role = role.strip().lower()
            if role not in names[ip]:
                warn("%s | role %r 不在命名表 names[%s] 中，跳过" % (hero_label, role, ip))
                continue
            slot_map = names[ip][role]

            # --- 读技能文件 ---
            try:
                skills, skill_raw, skill_nl = read_json_file(skill_path)
            except Exception as e:
                warn("%s | 技能文件解析失败: %s" % (hero_label, e))
                continue
            if not isinstance(skills, list):
                warn("%s | 技能文件不是 list，跳过" % hero_label)
                continue

            before_skills = json.loads(skill_raw.decode("utf-8"))
            before_card = json.loads(card_raw.decode("utf-8"))

            # --- 改名 ---
            n1, detail = rename_skill_list(skills, slot_map, "skills", hero_label)

            card_skills = card.get("skills")
            n2 = 0
            if isinstance(card_skills, list):
                n2, _ = rename_skill_list(card_skills, slot_map, "card.skills", hero_label)
            elif card_skills is None:
                warn("%s | 骨头卡无 skills 字段" % hero_label)
            else:
                warn("%s | 骨头卡 skills 非 list(%s)，跳过内嵌改名"
                     % (hero_label, type(card_skills).__name__))

            if n1 == 0 and n2 == 0:
                continue  # 幂等：已是目标值

            stats["heroes_changed"] += 1
            stats["skills_changed"] += n1
            if len(samples) < 5 and detail:
                samples.append((hero_label, role, detail))

            # --- 字节级安全校验 + 写盘 ---
            for path, data, raw, nl, before in (
                (skill_path, skills, skill_raw, skill_nl, before_skills),
                (card_path, card, card_raw, card_nl, before_card),
            ):
                if not roundtrip_safe(before, raw, nl):
                    warn("%s | %s 序列化风格不一致，拒绝写盘（防伪 diff）"
                         % (hero_label, os.path.relpath(path, ROOT)))
                    stats["files_skipped_unsafe"] += 1
                    continue

                # 结构化断言：只有 name 变了
                bad = [p for p in diff_paths(before, data)
                       if not p.endswith(".name")]
                if bad:
                    warn("%s | %s 检测到非 name 字段变化 %s，拒绝写盘"
                         % (hero_label, os.path.relpath(path, ROOT), bad[:5]))
                    stats["files_skipped_unsafe"] += 1
                    continue

                if dry_run:
                    continue
                with io.open(path, "wb") as fh:
                    fh.write(serialize(data, nl))
                stats["files_written"] += 1

    # ---------------- 报告 ----------------
    mode = "DRY_RUN（不写盘）" if dry_run else "WRITE（已写盘）"
    print("=" * 60)
    print("模式: %s" % mode)
    print("=" * 60)
    print("扫描英雄       : %d" % stats["heroes_seen"])
    print("改动英雄       : %d" % stats["heroes_changed"])
    print("改动技能(条)   : %d" % stats["skills_changed"])
    print("写入文件       : %d" % stats["files_written"])
    print("安全跳过文件   : %d" % stats["files_skipped_unsafe"])
    print("warning        : %d" % len(warnings))
    for w in warnings:
        print("  - " + w)

    if samples:
        print("-" * 60)
        print("改名样例：")
        for hero_label, role, detail in samples:
            print("  [%s] role=%s" % (hero_label, role))
            for slot, old, new in detail:
                print("      %s: %s  ->  %s" % (slot, old, new))
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
