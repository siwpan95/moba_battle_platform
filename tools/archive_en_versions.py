#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""归档英文名版本，统一以中文版为主。

策略（详见对话 ADR）：
- 英文名角色卡  -> tools/_archive/character_cards_en/<ip>/
- 英文名技能文件：
    * 能通过该 IP 中文卡的 hero.name_en 字段映射回中文名的
      -> 重命名为中文名，留在 data/skills/<ip>/（补全中文英雄技能）
    * 孤儿（对应纯英文英雄、无中文卡）-> tools/_archive/skills_en/<ip>/
- 旧式大文件 data/skills/<ip>.json（已弃用的回退）-> tools/_archive/skills_legacy_big/
- data/skills/_templates.json 保留（模板非数据）。

运行后验证：python -c "from core.loader import load_all_heroes; h=load_all_heroes()"
"""
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
CARDS = os.path.join(DATA, "character_cards")
SKILLS = os.path.join(DATA, "skills")
ARCHIVE = os.path.join(ROOT, "tools", "_archive")


def is_cn(s: str) -> bool:
    return any("\u4e00" <= c <= "\u9fff" for c in s)


def norm(s: str) -> str:
    s = (s or "").strip().lower()
    for ch in ("'", '"', "·", "•", "-", "_", " "):
        s = s.replace(ch, "")
    return s


def build_en2cn(ip: str):
    """该 IP 中文卡的 name_en -> 中文名（归一化 key）。"""
    en2cn = {}
    cd = os.path.join(CARDS, ip)
    if not os.path.isdir(cd):
        return en2cn
    for f in os.listdir(cd):
        if not f.endswith(".json"):
            continue
        try:
            o = json.load(open(os.path.join(cd, f), encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        h = o.get("hero", {})
        nm = h.get("name", "")
        ne = h.get("name_en", "")
        if is_cn(nm) and ne:
            en2cn[norm(ne)] = (nm, f)
    return en2cn


def main():
    arc_cards = os.path.join(ARCHIVE, "character_cards_en")
    arc_skills_en = os.path.join(ARCHIVE, "skills_en")
    arc_legacy = os.path.join(ARCHIVE, "skills_legacy_big")
    os.makedirs(arc_cards, exist_ok=True)
    os.makedirs(arc_skills_en, exist_ok=True)
    os.makedirs(arc_legacy, exist_ok=True)

    ips = sorted(d for d in os.listdir(CARDS) if not d.startswith("_") and os.path.isdir(os.path.join(CARDS, d)))

    stat = dict(card_moved=0, skill_remap_cn=0, skill_orphan=0, legacy_moved=0)

    for ip in ips:
        en2cn = build_en2cn(ip)
        cd = os.path.join(CARDS, ip)
        sd = os.path.join(SKILLS, ip)

        # 1) 英文名角色卡 -> archive/character_cards_en/<ip>/
        dst_card = os.path.join(arc_cards, ip)
        for f in os.listdir(cd):
            if not f.endswith(".json"):
                continue
            src = os.path.join(cd, f)
            try:
                o = json.load(open(src, encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            nm = o.get("hero", {}).get("name", "")
            if not is_cn(nm):
                os.makedirs(dst_card, exist_ok=True)
                shutil.move(src, os.path.join(dst_card, f))
                stat["card_moved"] += 1

        # 2) 英文名技能文件
        if os.path.isdir(sd):
            dst_skill_en = os.path.join(arc_skills_en, ip)
            for f in os.listdir(sd):
                if not f.endswith(".json"):
                    continue
                base = f[:-5]
                if is_cn(base):
                    continue  # 已是中文名，保留
                src = os.path.join(sd, f)
                cn = en2cn.get(norm(base))
                if cn:
                    cn_name = cn[0]
                    # 目标文件名安全化（沿用 core.skill_pool.safe_name 规则的最简版）
                    safe = cn_name
                    dst = os.path.join(sd, f"{safe}.json")
                    if os.path.exists(dst):
                        # 重名（极少见）：保留两者，英文原文件归档
                        os.makedirs(dst_skill_en, exist_ok=True)
                        shutil.move(src, os.path.join(dst_skill_en, f))
                        stat["skill_orphan"] += 1
                    else:
                        shutil.move(src, dst)
                        stat["skill_remap_cn"] += 1
                else:
                    os.makedirs(dst_skill_en, exist_ok=True)
                    shutil.move(src, os.path.join(dst_skill_en, f))
                    stat["skill_orphan"] += 1

        # 3) 旧式大文件
        big = os.path.join(SKILLS, f"{ip}.json")
        if os.path.isfile(big):
            shutil.move(big, os.path.join(arc_legacy, f"{ip}.json"))
            stat["legacy_moved"] += 1

    print("归档完成:", stat)


if __name__ == "__main__":
    main()
