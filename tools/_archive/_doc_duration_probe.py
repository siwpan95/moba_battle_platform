"""D 类时序缺陷取数探针（只读，不修改 data/）。

产出：
  A. category x duration 交叉表（testing-expert 明确索要）
  B. 每类别「有效时长>=2」的实例数（真正的战斗学量级）
  C. dot 专项：dmg_per_turn 字段实际携带情况（per_turn 键名错配的爆炸半径）
  D. 分 IP 注入未命中数（静态，无需跑仿真）
  E. 卡片 IP 字段名确认
"""
import os
import sys
from collections import defaultdict, Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

import io
import contextlib

from core.loader import HeroLoader
from core.mechanics import categorize_effect

buf = io.StringIO()

# 加载时会打印大量契约告警，吞掉
with contextlib.redirect_stdout(io.StringIO()):
    heroes = HeroLoader.load_all_heroes()

out = []
out.append(f"卡片总数: {len(heroes)}")

# ---- E. 字段名确认 ----
if heroes:
    k = sorted(heroes[0].keys())
    out.append(f"\n[E] 首张卡 top-level keys: {k}")
    out.append(f"[E] _game_dir 示例: {heroes[0].get('_game_dir')!r}")
    g = heroes[0].get("game")
    if isinstance(g, dict):
        out.append(f"[E] game.source 示例: {g.get('source')!r}")
    else:
        out.append(f"[E] game 字段类型: {type(g).__name__} 值={g!r}")

# ---- A/B/C ----
DUR_KEYS = ("1", "2", "3", ">=4")


def bucket(d):
    if d <= 1:
        return "1"
    if d == 2:
        return "2"
    if d == 3:
        return "3"
    return ">=4"


cross = defaultdict(lambda: Counter())
cat_total = Counter()
cat_ge2 = Counter()
no_dur_field = Counter()
total_eff = 0

dot_with_field = 0
dot_total = 0
dot_field_samples = Counter()

for h in heroes:
    for sk in (h.get("skills") or []):
        if not isinstance(sk, dict):
            continue
        for eff in (sk.get("effects") or []):
            if not isinstance(eff, dict):
                continue
            total_eff += 1
            cat = categorize_effect(eff)
            raw = eff.get("duration")
            if raw is None:
                no_dur_field[cat] += 1
            try:
                d = int(raw) if raw is not None else 1
            except (TypeError, ValueError):
                d = 1
            if not d:
                d = 1
            cross[cat][bucket(d)] += 1
            cat_total[cat] += 1
            if d >= 2:
                cat_ge2[cat] += 1
            if cat == "dot":
                dot_total += 1
                if eff.get("dmg_per_turn") is not None:
                    dot_with_field += 1
                    dot_field_samples[str(eff.get("dmg_per_turn"))] += 1

out.append(f"\n[A] effect 实例总数: {total_eff}")
out.append("\n[A] category x duration 交叉表")
hdr = f"{'category':<12}{'total':>8}{'dur=1':>8}{'dur=2':>8}{'dur=3':>8}{'>=4':>8}{'无duration字段':>16}{'有效>=2':>9}{'>=2占比':>9}"
out.append(hdr)
out.append("-" * len(hdr))
for cat, tot in cat_total.most_common():
    c = cross[cat]
    ge2 = cat_ge2[cat]
    pct = f"{ge2 / tot * 100:.1f}%" if tot else "-"
    out.append(f"{cat:<12}{tot:>8}{c['1']:>8}{c['2']:>8}{c['3']:>8}{c['>=4']:>8}"
               f"{no_dur_field[cat]:>16}{ge2:>9}{pct:>9}")

sum_ge2 = sum(cat_ge2.values())
sum_dur1 = sum(cross[c]["1"] for c in cat_total)
out.append("-" * len(hdr))
out.append(f"{'合计':<12}{total_eff:>8}{sum_dur1:>8}{'':>8}{'':>8}{'':>8}"
           f"{sum(no_dur_field.values()):>16}{sum_ge2:>9}"
           f"{sum_ge2 / total_eff * 100:.1f}%".rjust(9))
out.append(f"\n[A] dur=1 占比: {sum_dur1 / total_eff * 100:.2f}%  "
           f"(= D 类时序缺陷影响面)")

out.append(f"\n[C] dot 实例 {dot_total}，其中携带 dmg_per_turn 字段: {dot_with_field}")
out.append(f"[C] dmg_per_turn 取值 top10: {dot_field_samples.most_common(10)}")

# ---- D. 分 IP 注入未命中 ----
out.append("\n[D] 分 IP 技能注入情况（miss = 运行期技能数<3；zero = 0 技能必僵局）")
ip = defaultdict(lambda: {"n": 0, "miss": 0, "zero": 0})
for h in heroes:
    key = h.get("_game_dir") or "unknown"
    b = ip[key]
    b["n"] += 1
    n_sk = len(h.get("skills") or [])
    if n_sk < 3:
        b["miss"] += 1
    if n_sk == 0:
        b["zero"] += 1
hdr2 = f"{'IP(_game_dir)':<28}{'cards':>7}{'miss<3':>8}{'zero':>6}{'miss%':>8}"
out.append(hdr2)
out.append("-" * len(hdr2))
for key, v in sorted(ip.items(), key=lambda kv: -kv[1]["miss"]):
    if v["miss"] == 0:
        continue
    out.append(f"{key:<28}{v['n']:>7}{v['miss']:>8}{v['zero']:>6}"
               f"{v['miss'] / v['n'] * 100:>7.1f}%")
tm = sum(v["miss"] for v in ip.values())
tz = sum(v["zero"] for v in ip.values())
out.append("-" * len(hdr2))
out.append(f"{'合计':<28}{len(heroes):>7}{tm:>8}{tz:>6}")
out.append(f"[D] 有 miss 的 IP 数: {sum(1 for v in ip.values() if v['miss'])} / {len(ip)}")

txt = "\n".join(out)
dst = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_duration_result.txt")
with open(dst, "w", encoding="utf-8") as f:
    f.write(txt)
print("WROTE", dst)
