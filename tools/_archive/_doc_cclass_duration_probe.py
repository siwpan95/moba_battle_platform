"""C 类缺陷修复后的「真实激活量级」取数（只读）。

回答唯一决定性问题：把 control/reduce/true_dmg 补进各自别名表后，
新激活的实例里有多少是「有效时长>=2」（双方对称生效），
有多少是 dur=1（受 D 类时序缺陷影响，退化为先手方专属）。
"""
import os
import sys
import io
import contextlib
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from core.loader import HeroLoader
from core.mechanics import categorize_effect, _CATEGORY_TABLES

with contextlib.redirect_stdout(io.StringIO()):
    heroes = HeroLoader.load_all_heroes()

# 所有类别输出名
OUTPUT_NAMES = {name for _tbl, name in _CATEGORY_TABLES}
# 自身输出名不在自己表里的类别 = C 类
missing = {}
for tbl, name in _CATEGORY_TABLES:
    if name not in tbl:
        missing[name] = tbl
out = []
out.append(f"[C0] 输出名不在自身别名表内的类别: {sorted(missing)}")

stat = defaultdict(lambda: Counter())
raw_type_seen = defaultdict(Counter)

for h in heroes:
    for sk in (h.get("skills") or []):
        if not isinstance(sk, dict):
            continue
        for eff in (sk.get("effects") or []):
            if not isinstance(eff, dict):
                continue
            cat = categorize_effect(eff)
            if cat != "flavor":
                continue
            t = eff.get("type")
            if not t:
                continue
            t = str(t).strip().lower()
            if t not in missing:
                continue
            # 这是 C 类：写法正是某类别的输出名，却因该表不含自身而落 flavor
            raw = eff.get("duration")
            try:
                d = int(raw) if raw is not None else 1
            except (TypeError, ValueError):
                d = 1
            if not d:
                d = 1
            s = stat[t]
            s["total"] += 1
            s["dur1" if d == 1 else "dur_ge2"] += 1
            if raw is None:
                s["no_dur_field"] += 1
            s[f"d{min(d, 4)}"] += 1
            raw_type_seen[t][str(raw)] += 1

hdr = f"{'规格名(未注册)':<16}{'总实例':>8}{'dur=1':>8}{'有效>=2':>9}{'>=2占比':>9}{'无duration':>11}"
out.append("")
out.append("[C1] C 类实例的时长分布 —— 修复后真实激活量级")
out.append(hdr)
out.append("-" * len(hdr))
tot_all = tot_ge2 = 0
for t, s in sorted(stat.items(), key=lambda kv: -kv[1]["total"]):
    pct = f"{s['dur_ge2'] / s['total'] * 100:.1f}%" if s["total"] else "-"
    out.append(f"{t:<16}{s['total']:>8}{s['dur1']:>8}{s['dur_ge2']:>9}{pct:>9}"
               f"{s['no_dur_field']:>11}")
    tot_all += s["total"]
    tot_ge2 += s["dur_ge2"]
out.append("-" * len(hdr))
out.append(f"{'合计':<16}{tot_all:>8}{tot_all - tot_ge2:>8}{tot_ge2:>9}")

out.append("")
out.append("[C2] duration 原始取值分布（确认 dur=1 是显式写的还是字段缺失默认的）")
for t, c in raw_type_seen.items():
    out.append(f"  {t}: {c.most_common(8)}")

# 对照：当前已生效的 control 实例时长分布
alive = Counter()
for h in heroes:
    for sk in (h.get("skills") or []):
        if not isinstance(sk, dict):
            continue
        for eff in (sk.get("effects") or []):
            if not isinstance(eff, dict):
                continue
            if categorize_effect(eff) != "control":
                continue
            raw = eff.get("duration")
            try:
                d = int(raw) if raw is not None else 1
            except (TypeError, ValueError):
                d = 1
            alive["total"] += 1
            alive["dur1" if (d or 1) == 1 else "dur_ge2"] += 1

out.append("")
out.append(f"[C3] 对照·当前已生效 control: 总 {alive['total']}，"
           f"dur=1 {alive['dur1']}，有效>=2 {alive['dur_ge2']}")
out.append(f"[C3] 修复后 control 生效总量: {alive['total']} + {stat['control']['total']} "
           f"= {alive['total'] + stat['control']['total']}")
out.append(f"[C3] 其中对称生效(>=2): {alive['dur_ge2']} + {stat['control']['dur_ge2']} "
           f"= {alive['dur_ge2'] + stat['control']['dur_ge2']}")
out.append(f"[C3] 其中先手专属(dur=1): {alive['dur1']} + {stat['control']['dur1']} "
           f"= {alive['dur1'] + stat['control']['dur1']}")

txt = "\n".join(out)
dst = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_cclass_duration_result.txt")
with open(dst, "w", encoding="utf-8") as f:
    f.write(txt)
print("WROTE", dst)
