#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导出孤儿英文英雄的待填译名表（汉化放回用）。

输入：tools/_archive/character_cards_en/<ip>/*.json 与 tools/_archive/skills_en/<ip>/*.json
      （这些是"无中文对应"的纯英文英雄，无法机械汉化）

输出：
  - tools/_archive/hanize_table.csv   待人工补全的中文译名表
  - tools/_archive/hanize_table.json  同上，便于批量脚本读取

每行一个孤儿英文英雄（按 en_name 去重合并卡/技能存在性）：
  ip, en_name, has_card, has_skill, cn_name(待填)

注：若 cn_name 留空，批量汉化脚本会跳过该英雄。
"""
import os, json, csv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARC = os.path.join(ROOT, "tools", "_archive")


def is_cn(s):
    return any("\u4e00" <= c <= "\u9fff" for c in s)


def norm(s):
    s = (s or "").strip().lower()
    for ch in ("'", '"', "·", "•", "-", "_", " "):
        s = s.replace(ch, "")
    return s


def main():
    rows = {}  # (ip, en_name) -> dict
    # 英文卡
    cards_dir = os.path.join(ARC, "character_cards_en")
    if os.path.isdir(cards_dir):
        for ip in os.listdir(cards_dir):
            d = os.path.join(cards_dir, ip)
            if not os.path.isdir(d):
                continue
            for f in os.listdir(d):
                if not f.endswith(".json"):
                    continue
                o = json.load(open(os.path.join(d, f), encoding="utf-8"))
                h = o.get("hero", {})
                en = h.get("name_en") or h.get("name", "")
                en = en.strip()
                if not en:
                    continue
                key = (ip, norm(en))
                rows.setdefault(key, {"ip": ip, "en_name": en, "has_card": False, "has_skill": False, "cn_name": ""})
                rows[key]["has_card"] = True
    # 英文技能
    skills_dir = os.path.join(ARC, "skills_en")
    if os.path.isdir(skills_dir):
        for ip in os.listdir(skills_dir):
            d = os.path.join(skills_dir, ip)
            if not os.path.isdir(d):
                continue
            for f in os.listdir(d):
                if not f.endswith(".json"):
                    continue
                en = f[:-5].strip()
                if not en:
                    continue
                key = (ip, norm(en))
                rows.setdefault(key, {"ip": ip, "en_name": en, "has_card": False, "has_skill": False, "cn_name": ""})
                rows[key]["has_skill"] = True

    out_rows = sorted(rows.values(), key=lambda r: (r["ip"], r["en_name"].lower()))
    # CSV
    csv_path = os.path.join(ARC, "hanize_table.csv")
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as fp:
        w = csv.DictWriter(fp, fieldnames=["ip", "en_name", "has_card", "has_skill", "cn_name"])
        w.writeheader()
        for r in out_rows:
            w.writerow(r)
    # JSON
    json_path = os.path.join(ARC, "hanize_table.json")
    with open(json_path, "w", encoding="utf-8") as fp:
        json.dump(out_rows, fp, ensure_ascii=False, indent=2)

    total = len(out_rows)
    both = sum(1 for r in out_rows if r["has_card"] and r["has_skill"])
    only_card = sum(1 for r in out_rows if r["has_card"] and not r["has_skill"])
    only_skill = sum(1 for r in out_rows if r["has_skill"] and not r["has_card"])
    print(f"导出孤儿英文英雄总数: {total}")
    print(f"  卡+技能齐全: {both}")
    print(f"  仅卡: {only_card}")
    print(f"  仅技能: {only_skill}")
    print(f"CSV -> {csv_path}")
    print(f"JSON-> {json_path}")


if __name__ == "__main__":
    main()
