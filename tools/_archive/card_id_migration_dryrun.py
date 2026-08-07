"""C-5 card_id 迁移 dry-run 脚本（只读，不修改数据）。"""
import json
import os
import sys
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CARDS_DIR = os.path.join(PROJECT_ROOT, "data", "character_cards")
sys.path.insert(0, PROJECT_ROOT)

old_ids = []
new_ids_set = set()
prefix_collisions = defaultdict(list)
id_changes = []

for dirpath, dirnames, filenames in os.walk(CARDS_DIR):
    dirnames[:] = [d for d in dirnames if not d.startswith("_")]
    for fn in filenames:
        if fn.startswith("_") or not fn.endswith(".json"):
            continue
        fp = os.path.join(dirpath, fn)
        rel_dir = os.path.relpath(dirpath, CARDS_DIR)
        stem = fn[:-5]
        try:
            with open(fp, "r", encoding="utf-8") as f:
                card = json.load(f)
        except Exception:
            continue
        old_id = card.get("card_id", "?")
        old_prefix = old_id.split("-")[0] if "-" in old_id else old_id

        # New card_id: <game_dir>:<hero_slug>
        new_id = f"{rel_dir}:{stem}"

        old_ids.append(old_id)
        prefix_collisions[old_prefix].append(old_id)
        id_changes.append((old_id, new_id, fp, rel_dir))

        if new_id in new_ids_set:
            print(f"[COLLISION] {new_id} (from {fp})", file=sys.stderr)
        new_ids_set.add(new_id)

total = len(old_ids)
changed = sum(1 for o, n, fp, d in id_changes if o != n)
unchanged = total - changed
new_collisions = total - len(new_ids_set)

# Find multi-game prefix collisions
prefix_games = defaultdict(set)
for old_id, new_id, fp, rel_dir in id_changes:
    prefix = old_id.split("-")[0] if "-" in old_id else old_id
    prefix_games[prefix].add(rel_dir)

multi_game_prefixes = {p: gs for p, gs in prefix_games.items() if len(gs) > 1}

lines = []
lines.append("# card_id 迁移 dry-run 报告")
lines.append("")
lines.append(f"**日期**: 2026-08-05")
lines.append(f"**总卡数**: {total}")
lines.append(f"**card_id 将变更**: {changed} ({changed*100//total if total else 0}%)")
lines.append(f"**card_id 不变**: {unchanged}")
lines.append(f"**新 card_id 唯一性**: {'PASS (目录+文件名天然唯一)' if new_collisions == 0 else f'FAIL ({new_collisions} collisions)'}")
lines.append("")
lines.append("## 旧 card_id 前缀碰撞现状")
lines.append("")
for prefix, games in sorted(multi_game_prefixes.items()):
    lines.append(f"- `{prefix}`: {len(prefix_collisions[prefix])} cards across {len(games)} games: {sorted(games)}")
lines.append("")
lines.append("## 变更样本（前15条）")
lines.append("")
for old, new, fp, d in id_changes[:15]:
    lines.append(f"- `{old}` → `{new}`")
    lines.append(f"  - 文件: {fp}")
if changed > 15:
    lines.append(f"- ... 共 {changed} 条变更")
lines.append("")
lines.append("## 新 card_id 格式示例（每游戏1条）")
lines.append("")
seen = set()
for old, new, fp, d in id_changes:
    if d not in seen:
        seen.add(d)
        lines.append(f"- `{d}`: `{new}`")
lines.append("")
lines.append("## 迁移方案")
lines.append("")
lines.append("- **新格式**: `<game_id>:<hero_slug>`（与物理路径同构）")
lines.append("- **旧 card_id**: 保留为 `legacy_card_id` 字段一个版本周期")
lines.append("- **迁移脚本**: `tools/_archive/migrate_card_ids.py`（一次性执行）")
lines.append("- **幂等性**: 新 ID 由目录+文件名派生，局部生成 `--game <IP>` 不再重写既有 ID")

report = "\n".join(lines)
print(report)

out_path = os.path.join(PROJECT_ROOT, "tools", "_archive", "card_id_migration_dryrun.md")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(report)
print(f"\n报告已写入: {out_path}")
