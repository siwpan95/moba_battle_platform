#!/usr/bin/env python
"""批量扫描：风格/技能名/描述质量评估"""
import json, os, re
from collections import defaultdict

cards_dir = 'data/character_cards'
ips = sorted([d for d in os.listdir(cards_dir)
              if os.path.isdir(os.path.join(cards_dir, d)) and not d.startswith('_')])

GENERIC_SKILL_PATTERNS = [
    r'^技能[一二三四五六七八九十]$',
    r'^Skill\s*[1-4IV]$',
    r'^技能\s*[1-4]$',
    r'^一技能$', r'^二技能$', r'^三技能$', r'^四技能$',
    r'^被动$', r'^被动技能$',
    r'^Q$', r'^W$', r'^E$', r'^R$',
    r'^Ability\s*[1-4]$',
]

def is_generic_skill_name(name):
    if not name:
        return True
    for pat in GENERIC_SKILL_PATTERNS:
        if re.match(pat, name.strip()):
            return True
    return False

def assess_card(card, ip):
    """Return assessment dict for a single card"""
    issues = []
    
    # Check skills
    skills = card.get('skills', [])
    generic_skills = []
    real_skills = []
    for sk in skills:
        sn = sk.get('name', '')
        if is_generic_skill_name(sn):
            generic_skills.append(sn)
        else:
            real_skills.append(sn)
    
    if generic_skills and not real_skills:
        issues.append('ALL_GENERIC_SKILLS')
    elif generic_skills:
        issues.append('PARTIAL_GENERIC_SKILLS')
    
    # Check description
    desc = card.get('description', '')
    if not desc or desc.strip() == '':
        issues.append('NO_DESC')
    elif len(desc) < 30:
        issues.append('SHORT_DESC')
    
    # Check effects
    effects = card.get('effects', [])
    if not effects:
        issues.append('NO_EFFECTS')
    
    # Check if effects are template-like (very short, generic)
    if effects:
        # Check if all effects are very simple
        simple_count = 0
        for ef in effects:
            ef_desc = ef.get('description', '') if isinstance(ef, dict) else str(ef)
            if len(str(ef_desc)) < 20:
                simple_count += 1
        if simple_count == len(effects) and len(effects) > 0:
            issues.append('TEMPLATE_EFFECTS')
    
    return {
        'generic_skills': generic_skills,
        'real_skills': real_skills,
        'desc_len': len(desc),
        'effect_count': len(effects),
        'issues': issues,
    }

# Sample up to 5 random cards per IP
import random
random.seed(42)

print("=" * 70)
print("问题三：风格抽样评估（每 IP 最多 5 张）")
print("=" * 70)

for ip in ips:
    ip_path = os.path.join(cards_dir, ip)
    files = sorted([f for f in os.listdir(ip_path) if f.endswith('.json')])
    sample = random.sample(files, min(5, len(files)))
    
    ip_generic_count = 0
    ip_no_desc_count = 0
    ip_template_count = 0
    ip_sample_count = len(sample)
    
    details = []
    
    for f in sample:
        fpath = os.path.join(ip_path, f)
        with open(fpath, 'r', encoding='utf-8') as fh:
            card = json.load(fh)
        
        assess = assess_card(card, ip)
        
        all_generic = 'ALL_GENERIC_SKILLS' in assess['issues']
        no_desc = 'NO_DESC' in assess['issues']
        template = 'TEMPLATE_EFFECTS' in assess['issues']
        
        if all_generic:
            ip_generic_count += 1
        if no_desc:
            ip_no_desc_count += 1
        if template:
            ip_template_count += 1
        
        skill_names = [s.get('name','?') for s in card.get('skills', [])]
        details.append({
            'file': f,
            'hero_name': card.get('hero', {}).get('name', '?'),
            'skill_names': skill_names,
            'desc_len': assess['desc_len'],
            'effect_count': assess['effect_count'],
            'issues': assess['issues'],
        })
    
    # Classify IP
    issue_score = ip_generic_count + ip_no_desc_count * 2 + ip_template_count
    if ip_generic_count >= ip_sample_count * 0.5:
        grade = 'A'  # Urgent
    elif ip_generic_count > 0 or ip_no_desc_count > 0 or ip_template_count > 0:
        grade = 'B'  # Needs improvement
    else:
        grade = 'C'  # Good
    
    print(f"\n[{ip}] 抽样={ip_sample_count}  全泛称技能={ip_generic_count}  无描述={ip_no_desc_count}  模板effects={ip_template_count}  评级={grade}")
    
    # Show one detail example
    if details:
        d = details[0]
        print(f"  例: {d['file']} hero={d['hero_name']} skills={d['skill_names']} desc_len={d['desc_len']} issues={d['issues']}")
    
    # If issues found, show all problem cards
    problem_details = [d for d in details if d['issues']]
    for d in problem_details:
        print(f"  ⚠ {d['file']}: skills={d['skill_names']} issues={d['issues']}")
