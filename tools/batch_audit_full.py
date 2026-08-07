#!/usr/bin/env python
"""全量扫描：每 IP 技能名质量分布 + 模板技能占比"""
import json, os, re
from collections import defaultdict

cards_dir = 'data/character_cards'
ips = sorted([d for d in os.listdir(cards_dir)
              if os.path.isdir(os.path.join(cards_dir, d)) and not d.startswith('_')])

GENERIC_PLACEHOLDER = re.compile(
    r'^(技能[一二三四五六七八九十]|大招|技能\d|Skill\s*\d|Ability\s*\d|[QEWR]$)'
)

TEMPLATE_PREFIX = re.compile(
    r'^(战士|法师|射手|坦克|辅助|刺客)[·.]'
)

IP_SPECIFIC_STRONG = [
    'league_of_legends', 'dota2', 'honor_of_kings', 'arena_of_valor',
    'heroes_of_the_storm', 'smite', 'mobile_legends_bang_bang',
    'demon_slayer', 'one_piece', 'harry_potter', 'hong_kong_comics',
    'three_kingdoms', 'journey_to_the_west', 'fengshen_yanyi',
    'greek_mythology', 'norse_mythology', 'cthulhu_mythos',
    'world_generals', 'three_body', 'dc', 'marvel_super_war', 'mcu',
    'overwatch2', 'genshin', 'pokemon_unite', 'onmyoji_arena',
    'feiren_xueyuan', 'shuguang_heroes', 'yinghunzhiren', 'vainglory',
    '300_heroes',
]

print("=" * 80)
print("全量技能质量分析：模板泛称 vs IP 特色 vs 占位符")
print("=" * 80)

for ip in ips:
    ip_path = os.path.join(cards_dir, ip)
    files = sorted([f for f in os.listdir(ip_path) if f.endswith('.json')])
    
    total_skills = 0
    placeholder_skills = 0  # "技能一","大招" 
    template_skills = 0     # "战士·旋风斩","法师·元素风暴"
    ip_flavored_skills = 0  # real names
    other_skills = 0
    
    heroes_with_placeholder = 0
    heroes_all_template = 0
    heroes_all_ip = 0
    heroes_mixed = 0
    
    for f in files:
        fpath = os.path.join(ip_path, f)
        with open(fpath, 'r', encoding='utf-8') as fh:
            card = json.load(fh)
        
        skills = card.get('skills', [])
        has_placeholder = False
        has_template = False
        has_ip = False
        
        for sk in skills:
            sn = sk.get('name', '')
            total_skills += 1
            
            if GENERIC_PLACEHOLDER.match(sn.strip()):
                placeholder_skills += 1
                has_placeholder = True
            elif TEMPLATE_PREFIX.match(sn.strip()):
                template_skills += 1
                has_template = True
            else:
                ip_flavored_skills += 1
                has_ip = True
        
        # Classify hero
        if has_placeholder and not has_ip and not has_template:
            heroes_with_placeholder += 1
        elif has_template and not has_ip:
            heroes_all_template += 1
        elif has_ip and not has_template and not has_placeholder:
            heroes_all_ip += 1
        else:
            heroes_mixed += 1  # mixed
    
    total_heroes = len(files)
    pct_ip = ip_flavored_skills / max(total_skills, 1) * 100
    
    # Determine grade
    if heroes_all_ip >= total_heroes * 0.7:
        grade_detail = "A-技能有IP特色但缺描述"
    elif heroes_all_ip >= total_heroes * 0.3:
        grade_detail = "B-部分IP特色+部分模板"
    else:
        grade_detail = "C-大量模板占位"
    
    print(f"\n[{ip}] ({total_heroes}英雄)")
    print(f"  技能分布: IP特色={ip_flavored_skills} 模板={template_skills} 占位符={placeholder_skills}  ({pct_ip:.0f}% IP)")
    print(f"  英雄分布: 全IP特色={heroes_all_ip} 全模板={heroes_all_template} 混合={heroes_mixed} 全占位符={heroes_with_placeholder}")
    print(f"  诊断: {grade_detail}")

# Summary
print("\n" + "=" * 80)
print("分级小结")
print("=" * 80)
