#!/usr/bin/env python3
"""批量生成缺卡的角色卡骨头（stats/card_id），skills 由 loader 注入。"""
import json, os, sys, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.registry import GAME_REGISTRY

cd = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'character_cards')
sd = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'skills')

role_attrs = {
    'fighter': {'STR':17,'DEX':12,'CON':15,'INT':10,'WIS':12,'CHA':10},
    'assassin': {'STR':12,'DEX':17,'CON':12,'INT':12,'WIS':13,'CHA':10},
    'mage': {'STR':10,'DEX':12,'CON':13,'INT':17,'WIS':14,'CHA':10},
    'tank': {'STR':15,'DEX':10,'CON':17,'INT':10,'WIS':12,'CHA':12},
    'marksman': {'STR':10,'DEX':17,'CON':14,'INT':10,'WIS':13,'CHA':10},
    'support': {'STR':10,'DEX':12,'CON':13,'INT':14,'WIS':17,'CHA':12},
}
role_hitdie = {'fighter':10,'assassin':8,'mage':6,'tank':12,'marksman':10,'support':8}

total_new = 0

for gd in sorted(os.listdir(cd)):
    gp = os.path.join(cd, gd)
    if not os.path.isdir(gp) or gd.startswith('_'): continue

    sp = os.path.join(sd, f'{gd}.json')
    if not os.path.exists(sp): continue
    with open(sp, 'r', encoding='utf-8') as f:
        db = json.load(f)

    existing = set()
    for fname in os.listdir(gp):
        if fname.endswith('.json') and not fname.startswith('_'):
            existing.add(fname[:-5])

    reg = GAME_REGISTRY.get(gd, {'display': gd, 'cn': gd})
    game_display = reg['display']
    game_cn = reg['cn']

    for hero_name, skills in db.items():
        if hero_name in existing:
            continue
        if not isinstance(skills, list) or len(skills) < 4:
            continue

        # 推断 role
        roles_found = set()
        for s in skills:
            if not isinstance(s, dict):
                continue
            for e in s.get('effects', []):
                t = e.get('type', '')
                if t in ('heal', 'shield', 'cleanse', 'buff'):
                    roles_found.add('support')
                if t in ('execute', 'invis'):
                    roles_found.add('assassin')

        role = 'fighter'
        if 'support' in roles_found:
            role = 'support'
        elif 'assassin' in roles_found:
            role = 'assassin'

        attrs = role_attrs.get(role, role_attrs['fighter'])
        dex_mod = max(0, (attrs['DEX'] - 10) // 2)

        card = {
            'card_id': f'{gd}:{hero_name}',
            'hero': {'name': hero_name, 'name_en': hero_name, 'alias': '', 'title': hero_name},
            'game': {'name': game_display, 'name_cn': game_cn, 'universal_role': role},
            'source': '',
            'difficulty': 3,
            'playstyle_tags': [],
            'attributes': {k: {'score': v, 'modifier': (v - 10) // 2, 'name_cn': k} for k, v in attrs.items()},
            'primary_abilities': {'STR': attrs['STR'], 'DEX': attrs['DEX']},
            'hit_die': role_hitdie.get(role, 10),
            'stats_lv1': {'hp': 12, 'ac': 10 + dex_mod, 'atk': attrs['STR'], 'ap': max(attrs['INT'], attrs['WIS'])},
            'stats_lv18': {'hp': 120, 'ac': 12 + dex_mod},
            'growth_per_level': {'hp': 6, 'atk': 1, 'ap': 1},
        }

        safe_name = re.sub(r'[\\/:*?"<>|]', '_', hero_name)
        card_path = os.path.join(gp, f'{safe_name}.json')
        with open(card_path, 'w', encoding='utf-8') as f:
            json.dump(card, f, ensure_ascii=False, indent=2)
        total_new += 1

print(f'生成新卡: {total_new}')
