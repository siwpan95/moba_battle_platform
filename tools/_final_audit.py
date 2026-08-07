#!/usr/bin/env python3
"""Final quality audit for P0-A completion."""
import json

hok = json.load(open('data/skills/honor_of_kings.json', 'r', encoding='utf-8'))
aov = json.load(open('data/skills/arena_of_valor.json', 'r', encoding='utf-8'))

print(f'=== FINAL TOTALS ===')
print(f'Honor of Kings: {len(hok)} heroes (target: 116)')
print(f'Arena of Valor: {len(aov)} heroes (target: 115)')
print(f'Combined: {len(hok) + len(aov)} heroes')

def audit(data, label):
    total_skills = 0
    skills_with_effects = 0
    skills_with_save = 0
    total_effects = 0
    cd_issues = 0
    dice_issues = 0
    
    for name, skills in data.items():
        if len(skills) != 4:
            print(f'  WARN: {name} has {len(skills)} skills')
            continue
        cds = [s.get('cooldown', -1) for s in skills]
        if cds != [0, 1, 2, 4]:
            cd_issues += 1
        for s in skills:
            total_skills += 1
            effs = s.get('effects', [])
            if effs:
                skills_with_effects += 1
                total_effects += len(effs)
            if s.get('saving_throw'):
                skills_with_save += 1
            dmg = s.get('damage', {})
            if not dmg or 'dice_count' not in dmg:
                dice_issues += 1
    
    print(f'\n--- {label} ---')
    print(f'  Total skills: {total_skills}')
    print(f'  Skills with effects: {skills_with_effects} ({100*skills_with_effects/total_skills:.0f}%)')
    print(f'  Total effects: {total_effects}')
    print(f'  Avg effects/skill: {total_effects/total_skills:.1f}')
    print(f'  Skills with saving_throw: {skills_with_save} ({100*skills_with_save/total_skills:.0f}%)')
    print(f'  CD pattern issues: {cd_issues}')
    print(f'  Dice issues: {dice_issues}')

audit(hok, 'Honor of Kings')
audit(aov, 'Arena of Valor')

print('\n=== DICE EXPECTANCY SPOT CHECK ===')
roles_check = {
    'honor_of_kings': {
        'tank': '白起', 'fighter': '曹操', 'assassin': '阿轲',
        'mage': '扁鹊', 'marksman': '狄仁杰', 'support': '蔡文姬'
    },
    'arena_of_valor': {
        'tank': 'Arduin', 'fighter': 'Airi', 'assassin': 'Enzo',
        'mage': 'Aleister', 'marksman': 'Bonnie', 'support': 'Alice'
    }
}
targets = {
    'tank': (24, 27), 'fighter': (27, 30), 'assassin': (32, 34),
    'mage': (30, 33), 'marksman': (29, 32), 'support': (24, 27)
}

all_pass = True
for game, heroes in roles_check.items():
    data = hok if game == 'honor_of_kings' else aov
    for role, name in heroes.items():
        if name in data:
            skills = data[name]
            exp = sum(s['damage']['dice_count'] * (s['damage']['dice_size'] + 1) / 2 for s in skills)
            lo, hi = targets[role]
            status = 'PASS' if lo <= exp <= hi else 'FAIL'
            if status == 'FAIL':
                all_pass = False
            print(f'  {game}/{name}({role}): exp={exp:.1f} [{lo},{hi}] {status}')
        else:
            print(f'  {game}/{name}({role}): NOT FOUND')
            all_pass = False

print(f'\n=== OVERALL: {"ALL CHECKS PASSED" if all_pass else "SOME CHECKS FAILED"} ===')
