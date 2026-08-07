#!/usr/bin/env python3
"""Wave 0-D 模板骰值校标传播：将 _templates.json 的角色校标应用到所有 T4 英雄卡。

校标规则（GDD §3.2）：
  tank(坦克): 1d12, fighter(战士): 2d6, assassin(刺客): 2d8,
  mage(法师): 3d4, marksman(射手): 2d6, support(辅助): 1d12
  CD: [0, 1, 2, 4]

用法：python tools/_archive/wave0d_calibrate.py [--dry-run]
"""

import json, os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.loader import HeroLoader

ROLE_CALIBRATION = {
    '坦克': {'dice_count': 1, 'dice_size': 12},
    '战士': {'dice_count': 2, 'dice_size': 6},
    '刺客': {'dice_count': 2, 'dice_size': 8},
    '法师': {'dice_count': 3, 'dice_size': 4},
    '射手': {'dice_count': 2, 'dice_size': 6},
    '辅助': {'dice_count': 1, 'dice_size': 12},
}

CALIBRATED_CDS = [0, 1, 2, 4]

ROLE_PREFIXES = ['坦克', '战士', '刺客', '法师', '射手', '辅助']


def _is_template_name(name):
    """Check if skill name is a template name (from gate_cd_sim.py)."""
    TEMPLATE_NAMES = set()
    try:
        tmpl_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'skills', '_templates.json')
        tmpl_path = os.path.normpath(tmpl_path)
        with open(tmpl_path, 'r', encoding='utf-8') as f:
            tmpl = json.load(f)
        def _collect(obj):
            if isinstance(obj, dict):
                if "name" in obj and isinstance(obj["name"], str):
                    TEMPLATE_NAMES.add(obj["name"])
                for v in obj.values():
                    _collect(v)
            elif isinstance(obj, list):
                for item in obj:
                    _collect(item)
        _collect(tmpl)
    except Exception:
        pass

    ROLE_PREFIXES_LOCAL = ("坦克", "战士", "刺客", "法师", "射手", "辅助")
    GENERIC_PATTERNS = ("技能一", "技能二", "技能三", "技能四", "大招", "火球术",
                        "治疗术", "护盾", "冲锋", "箭雨", "毒刃", "暗影步",
                        "D&D", "DnD", "dnd")
    if not name or not isinstance(name, str):
        return True
    if name in TEMPLATE_NAMES:
        return True
    if name.startswith(ROLE_PREFIXES_LOCAL):
        return True
    for pat in GENERIC_PATTERNS:
        if pat in name:
            return True
    return False


def classify_tier(card):
    skills = card.get("skills", [])
    if not isinstance(skills, list):
        return "T3_stub"
    effective = skills[:4]
    if len(effective) < 4:
        return "T3_stub"
    real_count = sum(1 for s in effective
                     if isinstance(s.get("name"), str) and not _is_template_name(s["name"]))
    if real_count == 4:
        return "T1_real"
    elif real_count > 0:
        return "T2_partial"
    else:
        return "T4_template"


def detect_role(skills):
    """Detect role from first skill name prefix."""
    for s in skills[:4]:
        name = s.get('name', '')
        for role in ROLE_PREFIXES:
            if name.startswith(role + '·') or name.startswith(role + ':'):
                return role
    return None


def infer_role(skills):
    """Infer role from current dice pattern for generic-named heroes."""
    first_skill = skills[0]
    dmg = first_skill.get('damage', {})
    dc, ds = dmg.get('dice_count', 0), dmg.get('dice_size', 0)
    if dc == 1 and ds == 10:
        return '坦克'  # 1d10 → tank
    elif dc == 1 and ds == 8:
        return '刺客'  # 1d8 → assassin
    elif dc == 2 and ds == 6:
        return '法师'  # 2d6 → mage
    else:
        return '战士'  # default


def main():
    dry_run = '--dry-run' in sys.argv

    print("=" * 70)
    print(" Wave 0-D 骰值校标传播 — 模板→英雄卡")
    if dry_run:
        print(" [DRY RUN 模式]")
    print("=" * 70)

    heroes = HeroLoader.load_all_heroes()
    print(f"\n加载 {len(heroes)} 名英雄")

    # Group by source file
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    file_groups = {}
    for h in heroes:
        tier = classify_tier(h)
        if tier != 'T4_template':
            continue
        skills = h.get('skills', [])
        if not isinstance(skills, list) or len(skills) < 4:
            continue
        game_dir = h.get('_game_dir', '?')
        filename = h.get('_filename', '?')
        filepath = os.path.join(PROJECT_ROOT, 'data', 'character_cards', game_dir, filename + '.json')
        file_groups.setdefault(filepath, []).append(h)

    role_counts = Counter()
    generic_count = 0
    generic_detected = Counter()
    updated_files = 0
    updated_heroes = 0

    for filepath, heroes_in_file in sorted(file_groups.items()):
        if not os.path.exists(filepath):
            continue
        with open(filepath, 'r', encoding='utf-8') as f:
            card = json.load(f)

        skills = card.get('skills', [])
        if not isinstance(skills, list) or len(skills) < 4:
            continue

        role = detect_role(skills)
        if role is None:
            role = infer_role(skills)
            generic_count += 1
            generic_detected[role] += 1
        else:
            role_counts[role] += 1

        calib = ROLE_CALIBRATION.get(role)
        if calib is None:
            continue

        changed = False
        for i, s in enumerate(skills[:4]):
            if 'damage' not in s:
                s['damage'] = {}
            old_dc = s['damage'].get('dice_count')
            old_ds = s['damage'].get('dice_size')
            old_cd = s.get('cooldown')

            s['damage']['dice_count'] = calib['dice_count']
            s['damage']['dice_size'] = calib['dice_size']
            if i < len(CALIBRATED_CDS):
                s['cooldown'] = CALIBRATED_CDS[i]

            if old_dc != calib['dice_count'] or old_ds != calib['dice_size'] or old_cd != CALIBRATED_CDS[i]:
                changed = True

        if changed:
            updated_heroes += 1
            if not dry_run:
                card['skills'] = skills
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(card, f, ensure_ascii=False, indent=2)
            updated_files += 1

    print(f"\n校准计划:")
    for role in ['坦克', '战士', '刺客', '法师', '射手', '辅助']:
        cnt = role_counts[role] + generic_detected.get(role, 0)
        calib = ROLE_CALIBRATION[role]
        exp = calib['dice_count'] * (calib['dice_size'] + 1) / 2
        print(f"  [{role}] {cnt:>4} 名 → {calib['dice_count']}d{calib['dice_size']} (期望={exp:.1f})")
    print(f"  其中 {generic_count} 名无前缀英雄已推断角色")
    print(f"\n实际更新: {updated_heroes} 名英雄 / {updated_files} 个文件")
    print(f"CD 标定: {CALIBRATED_CDS}")

    if dry_run:
        print("\n[DRY RUN] 未实际写入。移除 --dry-run 以执行。")
    else:
        print("\n✅ 校准完成。可重跑 gate_cd_sim.py 验证。")

if __name__ == '__main__':
    main()
