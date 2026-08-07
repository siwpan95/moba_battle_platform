#!/usr/bin/env python3
"""批量创建英雄定义JSON并调用batch_gen_skills入库。"""
import json, subprocess, sys, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ═══════════════ Honor of Kings 第3-4批 ═══════════════
hok3 = {
    '霍去病': {'role': 'fighter', 'signature': {'E': ['accel'], 'R': ['buff']}},
    '卫青': {'role': 'tank', 'signature': {'W': ['shield'], 'R': ['control']}},
    '岳飞': {'role': 'fighter', 'signature': {'Q': ['sunder'], 'R': ['execute']}},
    '戚继光': {'role': 'fighter', 'signature': {'W': ['reduce'], 'R': ['buff']}},
    '穆桂英': {'role': 'fighter', 'signature': {'E': ['accel'], 'Q': ['sunder']}},
    '樊梨花': {'role': 'fighter', 'signature': {'Q': ['buff'], 'R': ['control']}},
    '秦琼': {'role': 'tank', 'signature': {'W': ['shield'], 'E': ['control']}},
    '尉迟恭': {'role': 'tank', 'signature': {'W': ['reduce'], 'R': ['reflect']}},
    '薛仁贵': {'role': 'marksman', 'signature': {'Q': ['vuln'], 'R': ['execute']}},
    '狄青': {'role': 'fighter', 'signature': {'E': ['accel'], 'R': ['buff']}},
    '孙武': {'role': 'mage', 'signature': {'W': ['control'], 'R': ['vuln']}},
    '李广': {'role': 'marksman', 'signature': {'Q': ['vuln'], 'R': ['dot']}},
    '养由基': {'role': 'marksman', 'signature': {'W': ['slow'], 'R': ['execute']}},
    '王翦': {'role': 'fighter', 'signature': {'Q': ['buff'], 'R': ['control']}},
    '蒙毅': {'role': 'tank', 'signature': {'W': ['shield'], 'R': ['reflect']}},
}
hok4 = {
    '太乙天尊': {'role': 'support', 'signature': {'W': ['heal'], 'R': ['shield']}},
    '元始天尊': {'role': 'mage', 'signature': {'W': ['control'], 'R': ['dot']}},
    '通天教主': {'role': 'mage', 'signature': {'Q': ['dot'], 'R': ['control']}},
    '陆压道人': {'role': 'assassin', 'signature': {'E': ['invis'], 'R': ['execute']}},
    '镇元大仙': {'role': 'support', 'signature': {'W': ['shield'], 'E': ['heal']}},
    '慈航道人': {'role': 'support', 'signature': {'W': ['heal'], 'R': ['cleanse']}},
    '多宝道人': {'role': 'tank', 'signature': {'W': ['shield'], 'R': ['reflect']}},
    '金灵圣母': {'role': 'mage', 'signature': {'Q': ['slow'], 'R': ['dot']}},
    '无当圣母': {'role': 'support', 'signature': {'W': ['heal'], 'E': ['buff']}},
    '赵公明': {'role': 'fighter', 'signature': {'Q': ['buff'], 'R': ['sunder']}},
    '云霄娘娘': {'role': 'mage', 'signature': {'W': ['control'], 'E': ['accel']}},
    '碧霄娘娘': {'role': 'mage', 'signature': {'Q': ['dot'], 'R': ['slow']}},
    '琼霄娘娘': {'role': 'support', 'signature': {'W': ['heal'], 'E': ['cleanse']}},
    '申公豹': {'role': 'mage', 'signature': {'E': ['accel'], 'R': ['control']}},
    '石矶娘娘': {'role': 'tank', 'signature': {'W': ['reduce'], 'R': ['control']}},
}

for fname, heroes in [('_batch_hok_3.json', hok3), ('_batch_hok_4.json', hok4)]:
    with open(fname, 'w', encoding='utf-8') as f:
        json.dump(heroes, f, ensure_ascii=False, indent=2)
    print(f"Created {fname}: {len(heroes)} heroes")

# Run generators
for batch in ['_batch_hok_3.json', '_batch_hok_4.json']:
    subprocess.run([sys.executable, 'tools/batch_gen_skills.py', 'honor_of_kings', batch], check=True)
