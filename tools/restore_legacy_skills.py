#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从归档的旧大 json (skills_legacy_big/<ip>.json) 恢复缺失的中文技能文件。

依据 tools/_tmp_76.json 中 has_src 清单：每个英雄的旧大json条目(英文key) ->
恢复为 data/skills/<ip>/<中文名>.json。

不联网、不改动角色卡。支持 --dry 预览。
"""
import os, json, argparse, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEGACY = os.path.join(ROOT, "tools", "_archive", "skills_legacy_big")
SKILLS = os.path.join(ROOT, "data", "skills")
LIST = os.path.join(ROOT, "tools", "_tmp_76.json")
sys.path.insert(0, ROOT)
from core.skill_pool import safe_name, write_hero_skill


def norm(s):
    s = (s or "").strip().lower()
    for ch in ("'", '"', "·", "•", "-", "_", " "):
        s = s.replace(ch, "")
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    data = json.load(open(LIST, encoding="utf-8"))
    rows = data["has_src"]
    ok = skip = miss = 0
    for ip, cn, en in rows:
        p = os.path.join(LEGACY, ip + ".json")
        if not os.path.isfile(p):
            miss += 1; continue
        db = json.load(open(p, encoding="utf-8"))
        hit = None
        for k, v in db.items():
            if norm(k) in (norm(cn), norm(en)):
                hit = v; break
        if hit is None:
            miss += 1; continue
        dst = os.path.join(SKILLS, ip, f"{safe_name(cn)}.json")
        if os.path.exists(dst):
            skip += 1; continue
        if args.dry:
            ok += 1
            print(f"[dry] 将写 {ip}/{safe_name(cn)}.json (源key≈{en or cn})")
        else:
            write_hero_skill(ip, cn, hit)
            ok += 1
    print(f"完成: 写入/计划={ok} 已存在跳过={skip} 未找到源={miss}")
    if args.dry:
        print("(dry-run 未写入)")


if __name__ == "__main__":
    main()
