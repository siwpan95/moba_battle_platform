#!/usr/bin/env python3
"""批量创建 300_heroes + mobile_legends_bang_bang 英雄批次。"""
import json, subprocess, sys, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable

# ═══════════════ 300 Heroes 批次 ═══════════════
# Batch 1: 动漫联动新英雄 (12)
h300_1 = {
    '梅林': {'role': 'mage', 'signature': {'W': ['control'], 'R': ['dot']}},
    '亚连沃克': {'role': 'fighter', 'signature': {'E': ['accel'], 'R': ['buff']}},
    '芙蕾雅': {'role': 'fighter', 'signature': {'Q': ['sunder'], 'R': ['execute']}},
    '琪露诺': {'role': 'mage', 'signature': {'Q': ['slow'], 'R': ['control']}},
    '木更': {'role': 'assassin', 'signature': {'E': ['invis'], 'R': ['execute']}},
    '电次': {'role': 'fighter', 'signature': {'Q': ['dot'], 'R': ['buff']}},
    '菈菈': {'role': 'support', 'signature': {'W': ['heal'], 'E': ['buff']}},
    '风鸣翼': {'role': 'fighter', 'signature': {'E': ['accel'], 'R': ['control']}},
    '古明地恋': {'role': 'mage', 'signature': {'W': ['control'], 'R': ['dot']}},
    '红美铃': {'role': 'fighter', 'signature': {'Q': ['sunder'], 'R': ['buff']}},
    '结城友奈': {'role': 'fighter', 'signature': {'W': ['reduce'], 'R': ['buff']}},
    '食蜂操祈': {'role': 'support', 'signature': {'W': ['control'], 'R': ['shield']}},
}

# Batch 2: 更多补充 (11)
h300_2 = {
    '吉良吉影': {'role': 'assassin', 'signature': {'E': ['invis'], 'R': ['execute']}},
    '帕秋莉': {'role': 'mage', 'signature': {'Q': ['dot'], 'R': ['slow']}},
    '藤原妹红': {'role': 'fighter', 'signature': {'Q': ['dot'], 'R': ['heal']}},
    '涂山红红': {'role': 'mage', 'signature': {'W': ['control'], 'R': ['dot']}},
    '梅普露': {'role': 'tank', 'signature': {'W': ['shield'], 'R': ['reflect']}},
    '蓬莱山辉夜': {'role': 'mage', 'signature': {'Q': ['slow'], 'R': ['control']}},
    '石神千空': {'role': 'support', 'signature': {'W': ['buff'], 'E': ['heal']}},
    '北方酱': {'role': 'tank', 'signature': {'W': ['reduce'], 'R': ['control']}},
    '苍星石': {'role': 'marksman', 'signature': {'Q': ['vuln'], 'R': ['execute']}},
    '温蒂': {'role': 'support', 'signature': {'W': ['heal'], 'E': ['cleanse']}},
    '和真惠惠': {'role': 'mage', 'signature': {'Q': ['dot'], 'R': ['dot']}},
}

# ═══════════════ Mobile Legends Bang Bang 批次 ═══════════════
# Batch 1: MLBB Lore - Moniyan Empire (14)
mlbb1 = {
    'Azrael': {'role': 'assassin', 'signature': {'E': ['invis'], 'R': ['execute']}},
    'Celestia': {'role': 'support', 'signature': {'W': ['heal'], 'R': ['shield']}},
    'Draven': {'role': 'fighter', 'signature': {'Q': ['sunder'], 'R': ['buff']}},
    'Elara': {'role': 'mage', 'signature': {'W': ['control'], 'R': ['dot']}},
    'Fenris': {'role': 'tank', 'signature': {'W': ['reduce'], 'R': ['control']}},
    'Gareth': {'role': 'tank', 'signature': {'W': ['shield'], 'R': ['reflect']}},
    'Ishara': {'role': 'mage', 'signature': {'Q': ['dot'], 'R': ['slow']}},
    'Jorah': {'role': 'fighter', 'signature': {'E': ['accel'], 'R': ['execute']}},
    'Kylin': {'role': 'marksman', 'signature': {'W': ['slow'], 'R': ['vuln']}},
    'Lyria': {'role': 'support', 'signature': {'W': ['heal'], 'E': ['cleanse']}},
    'Morax': {'role': 'tank', 'signature': {'W': ['shield'], 'E': ['control']}},
    'Nyxus': {'role': 'assassin', 'signature': {'E': ['invis'], 'R': ['execute']}},
    'Oriana': {'role': 'marksman', 'signature': {'Q': ['vuln'], 'R': ['dot']}},
    'Pyrrhus': {'role': 'fighter', 'signature': {'Q': ['dot'], 'R': ['buff']}},
}

# Batch 2: Abyss & Cadia Riverlands (13)
mlbb2 = {
    'Quorra': {'role': 'assassin', 'signature': {'E': ['accel'], 'R': ['invis']}},
    'Riven': {'role': 'fighter', 'signature': {'Q': ['sunder'], 'R': ['execute']}},
    'Sylas': {'role': 'mage', 'signature': {'W': ['control'], 'R': ['dot']}},
    'Talon': {'role': 'assassin', 'signature': {'Q': ['dot'], 'E': ['invis']}},
    'Umbra': {'role': 'assassin', 'signature': {'E': ['accel'], 'R': ['execute']}},
    'Vexia': {'role': 'mage', 'signature': {'Q': ['slow'], 'R': ['control']}},
    'Wraith': {'role': 'assassin', 'signature': {'E': ['invis'], 'R': ['execute']}},
    'Yurei': {'role': 'mage', 'signature': {'W': ['control'], 'R': ['dot']}},
    'Zara': {'role': 'marksman', 'signature': {'E': ['accel'], 'R': ['vuln']}},
    'Arawn': {'role': 'fighter', 'signature': {'Q': ['buff'], 'R': ['execute']}},
    'Kenshin': {'role': 'fighter', 'signature': {'Q': ['sunder'], 'R': ['accel']}},
    'Shiroe': {'role': 'support', 'signature': {'W': ['shield'], 'E': ['buff']}},
    'Tenma': {'role': 'marksman', 'signature': {'W': ['slow'], 'R': ['dot']}},
}

# Batch 3: More lore + crossovers (13)
mlbb3 = {
    'Asura': {'role': 'fighter', 'signature': {'Q': ['sunder'], 'R': ['buff']}},
    'Boreas': {'role': 'tank', 'signature': {'W': ['reduce'], 'R': ['control']}},
    'Cinder': {'role': 'mage', 'signature': {'Q': ['dot'], 'R': ['dot']}},
    'Dagon': {'role': 'tank', 'signature': {'W': ['shield'], 'R': ['reflect']}},
    'Erebus': {'role': 'assassin', 'signature': {'E': ['invis'], 'R': ['execute']}},
    'Fiera': {'role': 'mage', 'signature': {'Q': ['slow'], 'R': ['control']}},
    'Gryphon': {'role': 'fighter', 'signature': {'E': ['accel'], 'R': ['buff']}},
    'Hikari': {'role': 'support', 'signature': {'W': ['heal'], 'R': ['cleanse']}},
    'Igneous': {'role': 'tank', 'signature': {'W': ['shield'], 'R': ['control']}},
    'Jade': {'role': 'marksman', 'signature': {'Q': ['vuln'], 'R': ['execute']}},
    'Kaida': {'role': 'fighter', 'signature': {'Q': ['dot'], 'R': ['accel']}},
    'Levi': {'role': 'assassin', 'signature': {'E': ['accel'], 'R': ['execute']}},
    'Mizu': {'role': 'support', 'signature': {'W': ['heal'], 'E': ['buff']}},
}

all_batches = [
    ('300_heroes', [('_batch_300_1.json', h300_1), ('_batch_300_2.json', h300_2)]),
    ('mobile_legends_bang_bang', [('_batch_mlbb_1.json', mlbb1), ('_batch_mlbb_2.json', mlbb2),
                                   ('_batch_mlbb_3.json', mlbb3)]),
]

for game_id, batches in all_batches:
    for fname, heroes in batches:
        with open(fname, 'w', encoding='utf-8') as f:
            json.dump(heroes, f, ensure_ascii=False, indent=2)
        print(f"Created {fname}: {len(heroes)} heroes")
        subprocess.run([PY, 'tools/batch_gen_skills.py', game_id, fname], check=True)
    print(f"--- {game_id} all batches done ---\n")
