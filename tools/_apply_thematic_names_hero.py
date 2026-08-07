#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按「hero 级主题化技能命名表」批量改写 9 个公版 IP 的技能 name 字段。

与上一轮 `_apply_thematic_names.py`（ip × role 粒度，同 role 共用一套名）的区别：
本轮命名表下探到 **单英雄** 粒度，每个英雄拥有专属的 Q/W/E/R 四个技能名，
本脚本会**覆盖**上一轮写入的 role 级名字。

严格约束（工程落地任务，不触碰设计）：
  1. 只改写技能 dict 的 "name" 字符串；其它字段、属性、文件一律不动。
  2. 字节级安全：写盘前先校验「把原始对象重新序列化 == 原始字节」，
     不成立说明本脚本的格式化风格与该文件不一致，直接跳过并告警，
     避免因缩进/换行/转义差异产生大面积伪 diff。
  3. 结构化 diff 断言：改动路径必须严格匹配技能 name 的白名单正则
     （skills 文件 `[i].name`；骨头卡 `.skills[i].name`），
     命中 hero.name / game.name 等同名字段一律拒绝写盘。
  4. 幂等：name 已经等于目标值则不写盘，重复运行为无变化。
  5. 写盘后回读复验，断言磁盘内容 == 预期字节。

数据源：
  命名表   design/skill_naming/thematic_skill_names_hero.json
           { ip_id: { 英雄中文名: { "Q"/"W"/"E"/"R": name } } }
  技能文件 data/skills/<ip>/<hero>.json            (list of 4 skill dict，含 key/name)
  骨头卡   data/character_cards/<ip>/<hero>.json   (内嵌 skills list，同样含 key/name)

英雄定位：命名表的 key = 文件名 stem = card.hero.name。

用法：
    F:/Python314/python.exe tools/_apply_thematic_names_hero.py --dry-run
    F:/Python314/python.exe tools/_apply_thematic_names_hero.py
"""

import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NAMES_PATH = os.path.join(ROOT, "design", "skill_naming", "thematic_skill_names_hero.json")
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

VALID_SLOTS = {"Q", "W", "E", "R"}

# 允许变更的路径白名单（严格：只有技能 name）
RE_SKILL_NAME = re.compile(r"^\[\d+\]\.name$")        # data/skills/<ip>/<hero>.json
RE_CARD_NAME = re.compile(r"^\.skills\[\d+\]\.name$")  # data/character_cards/<ip>/<hero>.json

warnings = []


def warn(msg):
    warnings.append(msg)


# --------------------------------------------------------------------------
# IO helpers：保持原文件的换行风格与结尾字节
# --------------------------------------------------------------------------

def read_json_file(path):
    """返回 (data, raw_bytes, newline)。"""
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
    """原对象重新序列化后是否与原始字节完全一致。"""
    return serialize(data, newline) == raw


# --------------------------------------------------------------------------
# 结构化 diff：确认只有技能 name 变了
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

def rename_skill_list(skill_list, slot_map, where, hero_label):
    """就地按 key 匹配改写 name，返回 (改动数, [(slot, old, new)])。

    严格按 key 匹配，不做顺序兜底：key 缺失/非法直接告警跳过，
    避免命名表与实际槽位错位造成静默串名。
    """
    changed = 0
    detail = []
    for i, skill in enumerate(skill_list):
        if not isinstance(skill, dict):
            warn("%s | %s 第 %d 个技能不是 dict，跳过" % (hero_label, where, i))
            continue
        key = skill.get("key")
        if not isinstance(key, str) or key.upper() not in VALID_SLOTS:
            warn("%s | %s 第 %d 个技能 key 缺失/非法(%r)，跳过（不做顺序兜底）"
                 % (hero_label, where, i, key))
            continue
        slot = key.upper()
        if slot not in slot_map:
            warn("%s | %s 槽位 %s 不在命名表中，保留原名 %r"
                 % (hero_label, where, slot, skill.get("name")))
            continue
        new_name = slot_map[slot]
        if not isinstance(new_name, str) or not new_name.strip():
            warn("%s | %s 槽位 %s 命名表值非法(%r)，保留原名"
                 % (hero_label, where, slot, new_name))
            continue
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
        "heroes_in_table": 0,
        "heroes_seen": 0,
        "heroes_changed": 0,
        "skills_changed": 0,
        "card_skills_changed": 0,
        "files_written": 0,
        "files_skipped_unsafe": 0,
        "verify_failed": 0,
    }
    samples = []

    for ip in IP_IDS:
        if ip not in names:
            warn("命名表缺少 IP: %s，该 IP 全部跳过" % ip)
            continue
        sdir = os.path.join(SKILLS_DIR, ip)
        cdir = os.path.join(CARDS_DIR, ip)
        if not os.path.isdir(sdir):
            warn("IP 技能目录缺失: %s" % sdir)
            continue

        for hero in sorted(names[ip].keys()):
            stats["heroes_in_table"] += 1
            slot_map = names[ip][hero]
            hero_label = "%s/%s" % (ip, hero)
            skill_path = os.path.join(sdir, hero + ".json")
            card_path = os.path.join(cdir, hero + ".json")

            if not os.path.isfile(skill_path):
                warn("%s | 技能文件缺失 %s，跳过" % (hero_label, skill_path))
                continue
            if not os.path.isfile(card_path):
                warn("%s | 骨头卡缺失 %s，跳过" % (hero_label, card_path))
                continue
            stats["heroes_seen"] += 1

            try:
                skills, skill_raw, skill_nl = read_json_file(skill_path)
                card, card_raw, card_nl = read_json_file(card_path)
            except Exception as e:
                warn("%s | 文件解析失败: %s" % (hero_label, e))
                continue

            if not isinstance(skills, list):
                warn("%s | 技能文件不是 list，跳过" % hero_label)
                continue

            # 交叉校验：命名表 key 应就是 card.hero.name
            card_hero_name = ((card.get("hero") or {}).get("name"))
            if card_hero_name != hero:
                warn("%s | card.hero.name=%r 与文件名 stem 不一致" % (hero_label, card_hero_name))

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
            stats["card_skills_changed"] += n2
            if len(samples) < 5 and detail:
                samples.append((hero_label, detail))

            # --- 字节级安全校验 + 写盘 ---
            for path, data, raw, nl, before, allow_re in (
                (skill_path, skills, skill_raw, skill_nl, before_skills, RE_SKILL_NAME),
                (card_path, card, card_raw, card_nl, before_card, RE_CARD_NAME),
            ):
                rel = os.path.relpath(path, ROOT)
                if not roundtrip_safe(before, raw, nl):
                    warn("%s | %s 序列化风格不一致，拒绝写盘（防伪 diff）" % (hero_label, rel))
                    stats["files_skipped_unsafe"] += 1
                    continue

                # 结构化断言：改动路径必须严格命中技能 name 白名单
                bad = [p for p in diff_paths(before, data) if not allow_re.match(p)]
                if bad:
                    warn("%s | %s 检测到白名单外字段变化 %s，拒绝写盘"
                         % (hero_label, rel, bad[:5]))
                    stats["files_skipped_unsafe"] += 1
                    continue

                if dry_run:
                    continue

                payload = serialize(data, nl)
                with io.open(path, "wb") as fh:
                    fh.write(payload)
                # 写后复验
                if io.open(path, "rb").read() != payload:
                    warn("%s | %s 写后复验失败" % (hero_label, rel))
                    stats["verify_failed"] += 1
                    continue
                stats["files_written"] += 1

    # ---------------- 报告 ----------------
    mode = "DRY_RUN（不写盘）" if dry_run else "WRITE（已写盘）"
    print("=" * 60)
    print("hero 级主题化技能命名落地   模式: %s" % mode)
    print("=" * 60)
    print("命名表英雄     : %d" % stats["heroes_in_table"])
    print("磁盘命中英雄   : %d" % stats["heroes_seen"])
    print("改动英雄       : %d" % stats["heroes_changed"])
    print("改动技能(skills)   : %d" % stats["skills_changed"])
    print("改动技能(骨头卡)   : %d" % stats["card_skills_changed"])
    print("写入文件       : %d" % stats["files_written"])
    print("安全跳过文件   : %d" % stats["files_skipped_unsafe"])
    print("写后复验失败   : %d" % stats["verify_failed"])
    print("warning        : %d" % len(warnings))
    for w in warnings:
        print("  - " + w)

    if samples:
        print("-" * 60)
        print("改名样例：")
        for hero_label, detail in samples:
            print("  [%s]" % hero_label)
            for slot, old, new in detail:
                print("      %s: %s  ->  %s" % (slot, old, new))
    print("=" * 60)

    if stats["files_skipped_unsafe"] or stats["verify_failed"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
