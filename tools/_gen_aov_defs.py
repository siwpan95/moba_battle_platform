#!/usr/bin/env python3
"""Generate AoV hero definitions file for batch skill generation."""
import json

aov_heroes = {
    'tank': [
        'Arduin', 'Arthur', 'Ata', 'Baldum', 'Chaugnar', 'Cresht', 'Grakk',
        'Lumburr', 'Maloch', 'Omega', 'Ormarr', 'Skud', 'Taara', 'Toro',
        'Wiro', 'Xeniel', 'Ybneth', 'Zip', 'Gildur'
    ],
    'fighter': [
        'Airi', 'Allain', 'Amily', 'Aoi', 'Astrid', 'Bijan', 'Dextra',
        'Errol', 'Florentino', 'KilGroth', 'Lu Bu', 'Max', 'Omen',
        'Qi', 'Riktor', 'Rourke', 'Ryoma', 'Superman', 'Tachi', 'Veres',
        'Volkath', 'Wonder Woman', 'Wukong', 'Yan', 'Zanis', 'Zuka'
    ],
    'assassin': [
        'Enzo', 'Kaine', 'Keera', 'Kriknak', 'Paine', 'Quillen',
        'Sinestrea', 'Zephys'
    ],
    'mage': [
        'Aleister', 'AzzenKa', 'Darcy', 'Diaochan', 'Dirak',
        'Iggy', 'Ignis', 'Ilumia', 'Ishar', 'Jinnar', 'Krizzix', 'Lauriel',
        'Liliana', 'Lorion', 'Marja', 'Mganga', 'Natalya', 'Preyta',
        'Raz', 'Sephera', 'Tulen', 'Veera', 'Yue', 'Zata'
    ],
    'marksman': [
        'Bonnie', 'Bright', 'Brunhilda', 'Capheny', 'Elsu', 'Elandorr',
        'Fennik', 'Hayate', 'Laville', 'Lindis', 'Moren', 'Slimz',
        'Stuart', 'Teeri', 'TelAnnas', 'Thorne', 'Wisp'
    ],
    'support': [
        'Alice', 'Annette', 'Arum', 'Aya', 'Helen', 'Ming',
        'Rouie', 'Roxie', 'TeeMee'
    ]
}

skill_names = {
    'tank': {'Q': 'Heavy Slam', 'W': 'Iron Fortress', 'E': 'Unyielding Will', 'R': 'Earthshatter'},
    'fighter': {'Q': 'Blade Rush', 'W': 'War Stomp', 'E': 'Battle Spirit', 'R': 'Final Stand'},
    'assassin': {'Q': 'Shadow Strike', 'W': 'Venom Blade', 'E': 'Flicker Step', 'R': 'Death Mark'},
    'mage': {'Q': 'Arcane Bolt', 'W': 'Mystic Cage', 'E': 'Eldritch Flow', 'R': 'Cataclysm'},
    'marksman': {'Q': 'Piercing Shot', 'W': 'Hunters Trap', 'E': 'Evasive Roll', 'R': 'Barrage'},
    'support': {'Q': 'Sacred Light', 'W': 'Guardian Blessing', 'E': 'Warding Aura', 'R': 'Divine Intervention'}
}

hero_defs = []
for role, heroes in aov_heroes.items():
    for name in heroes:
        hero_defs.append({
            'name': name,
            'role': role,
            'skills': skill_names[role]
        })

with open('tools/hero_defs_aov.json', 'w', encoding='utf-8') as f:
    json.dump(hero_defs, f, ensure_ascii=False, indent=2)

print(f'Generated {len(hero_defs)} AoV hero definitions')
for role in ['tank','fighter','assassin','mage','marksman','support']:
    count = sum(1 for h in hero_defs if h['role'] == role)
    print(f'  {role}: {count}')
