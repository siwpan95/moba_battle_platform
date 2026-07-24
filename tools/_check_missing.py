import json, os
# 查找遗漏的13个英雄名所在的JSON文件并打印其hero.name和hero.name_en
targets = ['Azzen', 'Wukong', 'Yan', 'Yorn', 'Zanis', 'Roger', 'Sora', 'Valir', 'X.Borg', 'Yu_Zhong', 'Zetian', 'D.Va']
CARDS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "character_cards")
for root, dirs, files in os.walk(CARDS):
    for f in files:
        if f == '_index.json': continue
        name_part = f.replace('.json','')
        for t in targets:
            if name_part == t or name_part.startswith(t):
                card = json.load(open(os.path.join(root, f), 'r', encoding='utf-8'))
                print(f'{f:30s}  name={card["hero"]["name"]}  name_en={card["hero"]["name_en"]}  game_cn={card["game"]["name_cn"]}')
