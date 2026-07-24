import json, os

ascii_names = []
total = 0
CARDS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "character_cards")
for root, dirs, files in os.walk(CARDS):
    for f in files:
        if not f.endswith('.json') or f == '_index.json':
            continue
        total += 1
        p = os.path.join(root, f)
        try:
            card = json.load(open(p, 'r', encoding='utf-8'))
            name = card['hero']['name']
            game_cn = card['game']['name_cn']
            if all(ord(c) < 128 for c in name):
                ascii_names.append(game_cn + ': ' + name)
        except:
            pass

print('总计角色卡:', total)
print('仍为英文名:', len(ascii_names))
for n in sorted(ascii_names):
    print('  -', n)
