import json, os
ascii_names = []
total = 0
CARDS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "character_cards")
for root, dirs, files in os.walk(CARDS):
    for fname in files:
        if not fname.endswith(".json") or fname == "_index.json":
            continue
        total += 1
        path = os.path.join(root, fname)
        card = json.load(open(path, "r", encoding="utf-8"))
        name = card["hero"]["name"]
        if all(ord(c) < 128 for c in name):
            ascii_names.append(card["game"]["name_cn"] + ": " + name)
print(f"总计: {total} 张角色卡")
print(f"英文名残留: {len(ascii_names)} 个")
for n in sorted(ascii_names):
    print(f"  - {n}")
