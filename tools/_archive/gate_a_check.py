#!/usr/bin/env python3
"""Gate A 结构完整度检查脚本（严守真 / 只读）。"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.loader import iter_card_files
from core.config import CARDS_DIR

# Load template names
tmpl_path = os.path.join(os.path.dirname(CARDS_DIR), "skills", "_templates.json")
tmpl_names = set()
with open(tmpl_path, "r", encoding="utf-8") as f:
    tmpl = json.load(f)
def _collect(obj):
    if isinstance(obj, dict):
        if "name" in obj and isinstance(obj["name"], str):
            tmpl_names.add(obj["name"])
        for v in obj.values():
            _collect(v)
    elif isinstance(obj, list):
        for item in obj:
            _collect(item)
_collect(tmpl)

ROLE_PFX = ("坦克", "战士", "刺客", "法师", "射手", "辅助")
GENERIC = ("技能一", "技能二", "技能三", "技能四", "大招", "火球术",
           "治疗术", "护盾", "冲锋", "箭雨", "毒刃", "暗影步", "D&D", "DnD", "dnd")

def is_template(n):
    if not n or not isinstance(n, str):
        return True
    if n in tmpl_names:
        return True
    if n.startswith(ROLE_PFX):
        return True
    for p in GENERIC:
        if p in n:
            return True
    return False

total = 0
a1_fail = 0
a2_fail = 0
a3_fail = 0
a7_total = 0
a7_cards = 0
empty_slots = 0
zero_dice = 0

for filepath, game_dir, stem in iter_card_files(CARDS_DIR):
    with open(filepath, "r", encoding="utf-8") as f:
        card = json.load(f)
    total += 1
    skills = card.get("skills", [])
    if not isinstance(skills, list):
        a1_fail += 1
        continue
    n = len(skills)
    if n != 4:
        a1_fail += 1
    if n > 4:
        a7_total += (n - 4)
        a7_cards += 1

    # Slot 0-3 fill
    filled = min(n, 4)
    empty_slots += (4 - filled)

    # A-2
    any_template = False
    for i in range(min(4, n)):
        s = skills[i]
        name = s.get("name", "")
        if not isinstance(name, str) or not name or is_template(name):
            any_template = True
            break
    if any_template:
        a2_fail += 1

    # A-3
    dice_ok = 0
    for i in range(min(4, n)):
        dmg = skills[i].get("damage", {})
        if isinstance(dmg, dict) and dmg.get("dice_count", 0) > 0:
            dice_ok += 1
        else:
            zero_dice += 1
    if dice_ok < 3:
        a3_fail += 1

print(f"Total cards: {total}")
print(f"A-1 FAIL (len!=4): {a1_fail}/{total} (threshold: 0)")
print(f"A-2 FAIL (template names): {a2_fail}/{total} (threshold: 0)")
print(f"A-3 FAIL (dice<3/4): {a3_fail}/{total} (threshold: 0)")
print(f"A-7 FAIL (dead data): {a7_total} entries across {a7_cards} cards (threshold: 0)")
print(f"Empty slots (0-3 unfilled): {empty_slots}/{total*4} = {empty_slots/(total*4):.1%}")
print(f"Zero dice_count slots: {zero_dice}")
print(f"4-slot fill rate: {(total*4 - empty_slots)/(total*4):.1%}")
