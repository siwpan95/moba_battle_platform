#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""根据译名表把孤儿英文英雄汉化放回两池（中文为主）。

前置：运行 export_hanize_table.py 生成 tools/_archive/hanize_table.csv/.json，
      人工补全 cn_name 列（中文译名）。

本脚本读取 hanize_table.json，仅处理 cn_name 非空的条目：
  - 归档卡 tools/_archive/character_cards_en/<ip>/<en_name>.json
        -> data/character_cards/<ip>/<cn_name>.json
  - 归档技能 tools/_archive/skills_en/<ip>/<en_name>.json
        -> data/skills/<ip>/<cn_name>.json  (经 core.skill_pool.write_hero_skill)
  同时把卡内 hero.name / hero.name_en 同步为 中文 / 英文原名，
  并在该 IP 反查索引（缓存）中本就由 name_en 提供双向兼容。

跳过规则：cn_name 为空、目标已存在、源文件缺失。

运行：
  python tools/hanize_restore.py [--dry]
"""
import os, json, argparse, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARC = os.path.join(ROOT, "tools", "_archive")
CARDS = os.path.join(ROOT, "data", "character_cards")
SKILLS = os.path.join(ROOT, "data", "skills")

sys_path = ROOT
import sys
sys.path.insert(0, sys_path)
from core.skill_pool import safe_name, write_hero_skill


def norm(s):
    s = (s or "").strip().lower()
    for ch in ("'", '"', "·", "•", "-", "_", " "):
        s = s.replace(ch, "")
    return s


def find_src(src_dir, ip, en_name):
    """在归档目录中按归一化英文名定位源文件。"""
    d = os.path.join(src_dir, ip)
    if not os.path.isdir(d):
        return None
    target = norm(en_name)
    for f in os.listdir(d):
        if f.endswith(".json") and norm(f[:-5]) == target:
            return os.path.join(d, f)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="只统计不写入")
    args = ap.parse_args()

    table = json.load(open(os.path.join(ARC, "hanize_table.json"), encoding="utf-8"))
    todo = [r for r in table if r.get("cn_name", "").strip()]
    print(f"译名表共 {len(table)} 条，其中已填 cn_name: {len(todo)}")

    stat = dict(card_ok=0, card_skip=0, skill_ok=0, skill_skip=0, missing_src=0)
    for r in todo:
        ip = r["ip"]; en = r["en_name"].strip(); cn = r["cn_name"].strip()

        # 卡
        if r.get("has_card"):
            src = find_src(os.path.join(ARC, "character_cards_en"), ip, en)
            if not src:
                stat["missing_src"] += 1
            else:
                dst = os.path.join(CARDS, ip, f"{safe_name(cn)}.json")
                if os.path.exists(dst):
                    stat["card_skip"] += 1
                elif args.dry:
                    stat["card_ok"] += 1
                else:
                    o = json.load(open(src, encoding="utf-8"))
                    o.setdefault("hero", {})["name"] = cn
                    o["hero"]["name_en"] = en
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    json.dump(o, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
                    stat["card_ok"] += 1
        # 技能
        if r.get("has_skill"):
            src = find_src(os.path.join(ARC, "skills_en"), ip, en)
            if not src:
                stat["missing_src"] += 1
            else:
                dst = os.path.join(SKILLS, ip, f"{safe_name(cn)}.json")
                if os.path.exists(dst):
                    stat["skill_skip"] += 1
                elif args.dry:
                    stat["skill_ok"] += 1
                else:
                    skills = json.load(open(src, encoding="utf-8"))
                    write_hero_skill(ip, cn, skills)
                    stat["skill_skip"] += 0
                    stat["skill_ok"] += 1

    print("结果:", stat)
    if args.dry:
        print("(dry-run 未写入)")


if __name__ == "__main__":
    main()
