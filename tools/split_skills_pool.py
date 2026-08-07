#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拆分技能大文件为技能池：data/skills/<ip>.json -> data/skills/<ip>/<key>.json。

每个英雄的技能数组独立成一个文件，文件名用原 skills DB 的 key（英雄标识）。
保留 _templates.json（模板，非英雄技能）与原始 <ip>.json（作为回退，验证后手动删除）。
"""
import os, json, sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.paths import SKILLS_DIR

ILLEGAL = '/\\:*?"<>|'


def safe_name(key: str) -> str:
    s = key.strip()
    for ch in ILLEGAL:
        s = s.replace(ch, "_")
    return s or "unnamed"


def main():
    files = [f for f in os.listdir(SKILLS_DIR)
             if f.endswith(".json") and f != "_templates.json"]
    total = 0
    for f in sorted(files):
        ip = f[:-5]
        src = os.path.join(SKILLS_DIR, f)
        try:
            db = json.load(open(src, encoding="utf-8"))
        except Exception as e:
            print(f"[!] {f} 解析失败：{e}")
            continue
        if not isinstance(db, dict):
            print(f"[!] {f} 不是字典结构，跳过")
            continue
        outdir = os.path.join(SKILLS_DIR, ip)
        os.makedirs(outdir, exist_ok=True)
        n = 0
        for key, skills in db.items():
            dst = os.path.join(outdir, safe_name(key) + ".json")
            json.dump(skills, open(dst, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=2)
            n += 1
        total += n
        print(f"{ip}: {n} 个技能文件 -> {outdir}")
    print(f"\n总计生成技能文件：{total}")


if __name__ == "__main__":
    main()
