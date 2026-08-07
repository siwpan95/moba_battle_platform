#!/usr/bin/env python3
"""批量创建 AoV + 英魂之刃 英雄批次。"""
import json, subprocess, sys, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable

# ═══════════════ Arena of Valor 批次 ═══════════════
# Batch 1: Canon missing (16 newer heroes)
aov1 = {
    'Billow': {'role': 'assassin', 'signature': {'E': ['accel'], 'R': ['control']}},
    'Biron': {'role': 'tank', 'signature': {'W': ['shield'], 'R': ['control']}},
    'Bolt Baron': {'role': 'mage', 'signature': {'Q': ['slow'], 'R': ['dot']}},
    'Celica': {'role': 'marksman', 'signature': {'Q': ['vuln'], 'E': ['accel']}},
    'Charlotte': {'role': 'fighter', 'signature': {'Q': ['sunder'], 'R': ['buff']}},
    'Dolia': {'role': 'support', 'signature': {'W': ['heal'], 'R': ['shield']}},
    'Dyadia': {'role': 'support', 'signature': {'W': ['heal'], 'E': ['buff']}},
    'Edras': {'role': 'fighter', 'signature': {'E': ['accel'], 'R': ['execute']}},
    'Erin': {'role': 'marksman', 'signature': {'W': ['control'], 'R': ['vuln']}},
    'Flowborn': {'role': 'mage', 'signature': {'Q': ['dot'], 'R': ['control']}},
    'Goverra': {'role': 'mage', 'signature': {'W': ['control'], 'E': ['accel']}},
    'Heino': {'role': 'mage', 'signature': {'Q': ['slow'], 'R': ['dot']}},
    'Kahlii': {'role': 'mage', 'signature': {'Q': ['dot'], 'R': ['control']}},
    'Tamyn': {'role': 'fighter', 'signature': {'E': ['accel'], 'R': ['buff']}},
    'The Flash': {'role': 'assassin', 'signature': {'E': ['accel'], 'R': ['invis']}},
    'Obsidio': {'role': 'marksman', 'signature': {'Q': ['vuln'], 'R': ['dot']}},
}

# Batch 2: Athanor lore warriors (15)
aov2 = {
    'Zephyr': {'role': 'assassin', 'signature': {'E': ['invis'], 'R': ['execute']}},
    'Gaia': {'role': 'tank', 'signature': {'W': ['reduce'], 'R': ['reflect']}},
    'Helios': {'role': 'mage', 'signature': {'Q': ['dot'], 'R': ['dot']}},
    'Nyx': {'role': 'assassin', 'signature': {'E': ['invis'], 'R': ['execute']}},
    'Atlas Prime': {'role': 'tank', 'signature': {'W': ['shield'], 'R': ['control']}},
    'Selene': {'role': 'mage', 'signature': {'W': ['control'], 'R': ['slow']}},
    'Ares': {'role': 'fighter', 'signature': {'Q': ['sunder'], 'R': ['buff']}},
    'Luna': {'role': 'support', 'signature': {'W': ['heal'], 'E': ['cleanse']}},
    'Orion': {'role': 'marksman', 'signature': {'Q': ['vuln'], 'R': ['execute']}},
    'Phoenix': {'role': 'mage', 'signature': {'Q': ['dot'], 'R': ['heal']}},
    'Kronos': {'role': 'tank', 'signature': {'W': ['reduce'], 'R': ['control']}},
    'Echo': {'role': 'assassin', 'signature': {'E': ['accel'], 'R': ['invis']}},
    'Nova': {'role': 'mage', 'signature': {'W': ['control'], 'R': ['dot']}},
    'Raven': {'role': 'marksman', 'signature': {'W': ['slow'], 'E': ['accel']}},
    'Titan': {'role': 'tank', 'signature': {'W': ['shield'], 'R': ['reflect']}},
}

# Batch 3: Athanor/Veda lore (14)
aov3 = {
    'Shiro': {'role': 'assassin', 'signature': {'Q': ['dot'], 'R': ['execute']}},
    'Mirage': {'role': 'mage', 'signature': {'E': ['accel'], 'R': ['invis']}},
    'Golem': {'role': 'tank', 'signature': {'W': ['reduce'], 'R': ['control']}},
    'Sylvan': {'role': 'support', 'signature': {'W': ['heal'], 'E': ['buff']}},
    'Drago': {'role': 'fighter', 'signature': {'Q': ['sunder'], 'R': ['buff']}},
    'Vex': {'role': 'mage', 'signature': {'Q': ['dot'], 'W': ['control']}},
    'Blitz': {'role': 'assassin', 'signature': {'E': ['accel'], 'R': ['execute']}},
    'Seraph': {'role': 'support', 'signature': {'W': ['shield'], 'R': ['heal']}},
    'Frost': {'role': 'mage', 'signature': {'Q': ['slow'], 'R': ['control']}},
    'Blaze': {'role': 'fighter', 'signature': {'Q': ['dot'], 'R': ['buff']}},
    'Storm': {'role': 'marksman', 'signature': {'Q': ['slow'], 'R': ['vuln']}},
    'Void': {'role': 'assassin', 'signature': {'E': ['invis'], 'R': ['execute']}},
    'Aegis': {'role': 'tank', 'signature': {'W': ['shield'], 'R': ['reflect']}},
    'Sage': {'role': 'support', 'signature': {'W': ['heal'], 'E': ['cleanse']}},
}

# Batch 4: Athanor expanded (14)
aov4 = {
    'Spectre': {'role': 'assassin', 'signature': {'E': ['invis'], 'R': ['execute']}},
    'Forge': {'role': 'tank', 'signature': {'W': ['reduce'], 'R': ['control']}},
    'Mystic': {'role': 'mage', 'signature': {'Q': ['dot'], 'R': ['slow']}},
    'Ronin': {'role': 'fighter', 'signature': {'Q': ['sunder'], 'R': ['execute']}},
    'Oracle': {'role': 'support', 'signature': {'W': ['shield'], 'E': ['buff']}},
    'Warden': {'role': 'tank', 'signature': {'W': ['shield'], 'R': ['reflect']}},
    'Shade': {'role': 'assassin', 'signature': {'E': ['accel'], 'R': ['invis']}},
    'Ember': {'role': 'mage', 'signature': {'Q': ['dot'], 'R': ['dot']}},
    'Gale': {'role': 'marksman', 'signature': {'E': ['accel'], 'R': ['vuln']}},
    'Terra': {'role': 'tank', 'signature': {'W': ['reduce'], 'E': ['control']}},
    'Shimmer': {'role': 'support', 'signature': {'W': ['heal'], 'R': ['cleanse']}},
    'Pyre': {'role': 'fighter', 'signature': {'Q': ['dot'], 'R': ['buff']}},
    'Zephyra': {'role': 'marksman', 'signature': {'W': ['slow'], 'R': ['vuln']}},
    'Obsidian': {'role': 'assassin', 'signature': {'E': ['invis'], 'R': ['execute']}},
}

# ═══════════════ 英魂之刃 批次 ═══════════════
# Batch 1: 联动/新英雄 (16)
yhz1 = {
    '楚虞': {'role': 'fighter', 'signature': {'E': ['accel'], 'R': ['buff']}},
    '灵梦': {'role': 'mage', 'signature': {'W': ['control'], 'R': ['dot']}},
    '雅儿贝德': {'role': 'tank', 'signature': {'W': ['shield'], 'R': ['reflect']}},
    '精卫填海': {'role': 'marksman', 'signature': {'W': ['slow'], 'R': ['vuln']}},
    '铁扇公主': {'role': 'mage', 'signature': {'Q': ['slow'], 'R': ['control']}},
    '普罗米修斯': {'role': 'support', 'signature': {'W': ['heal'], 'E': ['buff']}},
    '安兹乌尔恭': {'role': 'mage', 'signature': {'W': ['control'], 'R': ['dot']}},
    '曹焱兵': {'role': 'fighter', 'signature': {'Q': ['sunder'], 'R': ['buff']}},
    '阿修罗': {'role': 'fighter', 'signature': {'E': ['accel'], 'R': ['execute']}},
    '鹤道大师': {'role': 'support', 'signature': {'W': ['heal'], 'E': ['cleanse']}},
    '东方月初': {'role': 'mage', 'signature': {'Q': ['dot'], 'R': ['control']}},
    '涂山红红': {'role': 'fighter', 'signature': {'E': ['accel'], 'R': ['buff']}},
    '白月初': {'role': 'assassin', 'signature': {'E': ['invis'], 'R': ['execute']}},
    '涂山苏苏': {'role': 'support', 'signature': {'W': ['heal'], 'R': ['shield']}},
    '米莉姆': {'role': 'fighter', 'signature': {'Q': ['sunder'], 'R': ['buff']}},
    '利姆鲁': {'role': 'mage', 'signature': {'E': ['accel'], 'R': ['control']}},
}

# Batch 2: 更多联动/扩展 (15)
yhz2 = {
    '夏提雅': {'role': 'assassin', 'signature': {'E': ['accel'], 'R': ['execute']}},
    '范海辛': {'role': 'marksman', 'signature': {'Q': ['vuln'], 'R': ['dot']}},
    '苍影': {'role': 'assassin', 'signature': {'E': ['invis'], 'R': ['execute']}},
    '金蟾童子': {'role': 'support', 'signature': {'W': ['heal'], 'E': ['buff']}},
    '夏铃': {'role': 'mage', 'signature': {'Q': ['slow'], 'R': ['control']}},
    '北落师门': {'role': 'fighter', 'signature': {'E': ['accel'], 'R': ['buff']}},
    '超核神兵': {'role': 'tank', 'signature': {'W': ['shield'], 'R': ['control']}},
    '三藏禅师': {'role': 'support', 'signature': {'W': ['heal'], 'R': ['cleanse']}},
    '玄穹天帝': {'role': 'mage', 'signature': {'W': ['control'], 'R': ['dot']}},
    '时光守护者': {'role': 'support', 'signature': {'W': ['shield'], 'E': ['heal']}},
    '圣枪使': {'role': 'marksman', 'signature': {'Q': ['vuln'], 'R': ['execute']}},
    '狂蝠女王': {'role': 'assassin', 'signature': {'E': ['invis'], 'R': ['buff']}},
    '龙影': {'role': 'fighter', 'signature': {'Q': ['sunder'], 'R': ['accel']}},
    '潮汐守望者': {'role': 'tank', 'signature': {'W': ['reduce'], 'R': ['control']}},
    '幻水仙灵': {'role': 'support', 'signature': {'W': ['heal'], 'R': ['shield']}},
}

# Batch 3: 更多 (15)
yhz3 = {
    '战斗女神': {'role': 'fighter', 'signature': {'Q': ['buff'], 'R': ['execute']}},
    '潘多拉亚克特': {'role': 'mage', 'signature': {'W': ['control'], 'R': ['dot']}},
    '神秘冒险家': {'role': 'marksman', 'signature': {'E': ['accel'], 'R': ['vuln']}},
    '暖心女仆': {'role': 'support', 'signature': {'W': ['heal'], 'E': ['cleanse']}},
    '贝拉尔': {'role': 'assassin', 'signature': {'E': ['invis'], 'R': ['execute']}},
    '艾多玛娜': {'role': 'mage', 'signature': {'Q': ['dot'], 'R': ['control']}},
    '金元素': {'role': 'tank', 'signature': {'W': ['shield'], 'R': ['reflect']}},
    '木元素': {'role': 'support', 'signature': {'W': ['heal'], 'E': ['buff']}},
    '自然之灵': {'role': 'support', 'signature': {'W': ['shield'], 'R': ['heal']}},
    '少年曹焱兵': {'role': 'fighter', 'signature': {'Q': ['sunder'], 'R': ['buff']}},
    '莫莫瑞鼠': {'role': 'marksman', 'signature': {'W': ['slow'], 'R': ['vuln']}},
    '九尾天狐': {'role': 'mage', 'signature': {'E': ['accel'], 'R': ['control']}},
    '暗黑冥神': {'role': 'assassin', 'signature': {'E': ['invis'], 'R': ['execute']}},
    '凋零骑士': {'role': 'fighter', 'signature': {'W': ['reduce'], 'R': ['execute']}},
    '时空猎手': {'role': 'assassin', 'signature': {'E': ['accel'], 'R': ['invis']}},
}

# Batch 4: 最后一批 (14)
yhz4 = {
    '天之锁': {'role': 'tank', 'signature': {'W': ['shield'], 'R': ['control']}},
    '炼狱魔君': {'role': 'fighter', 'signature': {'Q': ['dot'], 'R': ['buff']}},
    '冰霜巨龙': {'role': 'tank', 'signature': {'W': ['reduce'], 'R': ['control']}},
    '烈焰凤凰': {'role': 'mage', 'signature': {'Q': ['dot'], 'R': ['heal']}},
    '雷霆战锤': {'role': 'fighter', 'signature': {'Q': ['sunder'], 'R': ['accel']}},
    '暗影舞者': {'role': 'assassin', 'signature': {'E': ['invis'], 'R': ['execute']}},
    '星辰术士': {'role': 'mage', 'signature': {'W': ['control'], 'R': ['dot']}},
    '暴风射手': {'role': 'marksman', 'signature': {'E': ['accel'], 'R': ['vuln']}},
    '圣盾骑士': {'role': 'tank', 'signature': {'W': ['shield'], 'R': ['reflect']}},
    '灵魂祭司': {'role': 'support', 'signature': {'W': ['heal'], 'R': ['cleanse']}},
    '魔刃刺客': {'role': 'assassin', 'signature': {'Q': ['dot'], 'E': ['accel']}},
    '天罚之枪': {'role': 'marksman', 'signature': {'W': ['slow'], 'R': ['execute']}},
    '月神祭司': {'role': 'mage', 'signature': {'Q': ['slow'], 'R': ['shield']}},
    '大地守卫': {'role': 'tank', 'signature': {'W': ['reduce'], 'E': ['control']}},
}

all_batches = [
    ('arena_of_valor', [('_batch_aov_1.json', aov1), ('_batch_aov_2.json', aov2),
                         ('_batch_aov_3.json', aov3), ('_batch_aov_4.json', aov4)]),
    ('yinghunzhiren', [('_batch_yhz_1.json', yhz1), ('_batch_yhz_2.json', yhz2),
                        ('_batch_yhz_3.json', yhz3), ('_batch_yhz_4.json', yhz4)]),
]

for game_id, batches in all_batches:
    for fname, heroes in batches:
        with open(fname, 'w', encoding='utf-8') as f:
            json.dump(heroes, f, ensure_ascii=False, indent=2)
        print(f"Created {fname}: {len(heroes)} heroes")
        subprocess.run([PY, 'tools/batch_gen_skills.py', game_id, fname], check=True)
    print(f"--- {game_id} all batches done ---\n")
