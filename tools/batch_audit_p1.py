#!/usr/bin/env python
"""批量扫描：文件名中英分布 + hero.name 对齐 + approx 标记"""
import json, os, re
from collections import defaultdict

cards_dir = 'data/character_cards'
ips = sorted([d for d in os.listdir(cards_dir)
              if os.path.isdir(os.path.join(cards_dir, d)) and not d.startswith('_')])

results = {}

for ip in ips:
    ip_path = os.path.join(cards_dir, ip)
    files = sorted([f for f in os.listdir(ip_path) if f.endswith('.json')])
    hero_count = len(files)

    pure_en = []
    pure_cn = []
    mixed = []
    mismatches = []
    approx_count = 0
    total = 0

    for f in files:
        fpath = os.path.join(ip_path, f)
        try:
            with open(fpath, 'r', encoding='utf-8') as fh:
                card = json.load(fh)
        except Exception:
            continue

        total += 1
        fname_noext = f.replace('.json', '')

        has_cn = bool(re.search(r'[\u4e00-\u9fff]', fname_noext))
        has_en = bool(re.search(r'[a-zA-Z]', fname_noext))

        if has_cn and has_en:
            mixed.append(f)
        elif has_cn:
            pure_cn.append(f)
        elif has_en:
            pure_en.append(f)
        # else: purely numeric/symbol — edge case

        hero_name = card.get('hero', {}).get('name', '')
        if hero_name and hero_name != fname_noext:
            mismatches.append((f, hero_name))

        if card.get('approx', False):
            approx_count += 1

    results[ip] = {
        'count': hero_count,
        'pure_en': pure_en,
        'pure_cn': pure_cn,
        'mixed': mixed,
        'mismatches': mismatches,
        'approx_count': approx_count,
        'total': total,
    }

# === OUTPUT ===
print("=" * 70)
print("全量扫描结果：IP 英雄数 + 文件名语言分布 + approx 统计")
print("=" * 70)

for ip in sorted(results.keys()):
    r = results[ip]
    print(f"\n[{ip}] 英雄数={r['count']}  approx={r['approx_count']}/{r['total']}  纯英文文件名={len(r['pure_en'])}  纯中文={len(r['pure_cn'])}  混合={len(r['mixed'])}  名称不一致={len(r['mismatches'])}")

# Full mismatch details
print("\n\n=== 文件名 vs hero.name 不一致详情 ===")
for ip in sorted(results.keys()):
    r = results[ip]
    for fname, hname in r['mismatches']:
        print(f"  {ip}/{fname}  ->  hero.name=\"{hname}\"")

# Full English/Mixed filename lists
print("\n\n=== 纯英文文件名清单 ===")
for ip in sorted(results.keys()):
    r = results[ip]
    for f in r['pure_en']:
        print(f"  {ip}/{f}")

print("\n\n=== 中英混合文件名清单 ===")
for ip in sorted(results.keys()):
    r = results[ip]
    for f in r['mixed']:
        print(f"  {ip}/{f}")

# Summary stats
total_approx = sum(r['approx_count'] for r in results.values())
total_cards = sum(r['total'] for r in results.values())
print(f"\n\n=== 全局统计 ===")
print(f"总 IP 数: {len(ips)}")
print(f"总卡数: {total_cards}")
print(f"Approx 卡数: {total_approx} ({total_approx/total_cards*100:.1f}%)")
