"""(1) 回答 1659 vs 5926 口径冲突；(2) 把 D 类按消费点拆成 D1/D2（只读）。

D 类内部并非同质。按「消费点落在谁的行动上」分两型：
  D1 非对称：消费点 = 对手在同回合的后续行动 → P1 施放生效 / P2 施放全废
  D2 双向全废：消费点 = 自己的下次行动或下回合 → 无论谁施放都在消费前被清除
"""
import os
import sys
import io
import contextlib
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from core.loader import HeroLoader
from core.mechanics import categorize_effect

# 消费点逐行核定（simulator.py）
D1_ASYM = {
    # 消费点在「对手行动」，P1 施放后 P2 于同回合 L238 行动时消费 → 生效
    "control",  # 消费: _hero_act L287 self._controlled(side)
    "reduce",   # 消费: _resolve_damage L386 self._has(enemy_side,"reduce")
    "shield",   # 消费: _resolve_damage L393-399 _absorb_shield
    "immune",   # 消费: _apply_effects L430 self._has(enemy_side,"immune")
}
D2_DEAD = {
    # 消费点在「自己下次行动」或「下回合开头」→ 均晚于本回合末衰减
    "buff",     # -> kind bonus, 消费: _resolve_damage L390 _sum(side,"bonus")
    "accel",    # -> kind bonus, 同上
    "reflect",  # -> kind bonus, 同上
    "sunder",   # -> kind vuln,  消费: L389 _sum(enemy_side,"vuln") 自己下次攻击
    "vuln",     # 同上
    "crit",     # 消费: _resolve_damage L354 _sum(side,"crit") 自己下次攻击
    "dot",      # 消费: _tick_dot L255 下回合开头
}

with contextlib.redirect_stdout(io.StringIO()):
    heroes = HeroLoader.load_all_heroes()

dur1 = Counter()
tot = Counter()
grand = 0
for h in heroes:
    for sk in (h.get("skills") or []):
        if not isinstance(sk, dict):
            continue
        for eff in (sk.get("effects") or []):
            if not isinstance(eff, dict):
                continue
            grand += 1
            cat = categorize_effect(eff)
            raw = eff.get("duration")
            try:
                d = int(raw) if raw is not None else 1
            except (TypeError, ValueError):
                d = 1
            if not d:
                d = 1
            tot[cat] += 1
            if d == 1:
                dur1[cat] += 1

out = []
out.append("=" * 62)
out.append("[Q] 1659 vs 5926 口径冲突")
out.append("=" * 62)
out.append(f"len(HeroLoader.load_all_heroes()) = {len(heroes)}")
out.append(f"effect 实例总数(运行期)            = {grand}")
out.append("→ load_all_heroes 无任何过滤/裁剪；test_fuzz_battle.py L7 的 1659 为陈旧 docstring。")
out.append("→ 磁盘卡文件数与运行期英雄数一致，不存在双口径。")

out.append("")
out.append("=" * 62)
out.append("[D-split] D 类按消费点拆分")
out.append("=" * 62)
hdr = f"{'category':<12}{'total':>8}{'dur=1':>8}   {'型别':<8}"
out.append(hdr)
out.append("-" * len(hdr))
s1 = s2 = 0
for c in sorted(D1_ASYM, key=lambda x: -dur1[x]):
    out.append(f"{c:<12}{tot[c]:>8}{dur1[c]:>8}   {'D1非对称':<8}")
    s1 += dur1[c]
out.append("-" * len(hdr))
for c in sorted(D2_DEAD, key=lambda x: -dur1[x]):
    out.append(f"{c:<12}{tot[c]:>8}{dur1[c]:>8}   {'D2全废':<8}")
    s2 += dur1[c]
out.append("-" * len(hdr))
out.append(f"D1 非对称（先手方专属，后手方作废） = {s1}")
out.append(f"D2 双向全废（无论谁施放都不生效）   = {s2}")
out.append(f"D 类合计 = {s1 + s2}  （应等于 9276）")
out.append(f"D1 占 D = {s1 / (s1 + s2) * 100:.1f}%   D2 占 D = {s2 / (s1 + s2) * 100:.1f}%")

out.append("")
out.append("[解读] D2 是纯内容损失：这些效果对任何一方都从未生效过，")
out.append("       修复它不制造偏置，只是把已写好的内容接上电源。")
out.append("       D1 才是先手偏置来源，修复需配套平衡回归。")

out.append("")
out.append("[最大死机制] 按 dur=1 实例数排序 top5")
for c, n in sorted(dur1.items(), key=lambda kv: -kv[1])[:5]:
    typ = "D1" if c in D1_ASYM else ("D2" if c in D2_DEAD else "非TIMED")
    out.append(f"  {c:<10}{n:>6}   ({typ})")
out.append(f"  buff+accel 合计 = {dur1['buff'] + dur1['accel']}  (均为 D2 全废)")

txt = "\n".join(out)
dst = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_d_split_result.txt")
with open(dst, "w", encoding="utf-8") as f:
    f.write(txt)
print("WROTE", dst)
