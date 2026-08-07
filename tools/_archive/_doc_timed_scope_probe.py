"""独立复算 code-reviewer 的 9276 / 30.6% / 45.2%，并核对口径边界（只读）。

方法与 code-reviewer 不同：他自静态库+注入推导，本探针直接按
simulator._apply_effects 的实际分支归属，把类别分为
  TIMED   —— 走 self._add(...)，受 _decay_timed 回合末衰减影响
  INSTANT —— 当场结算完毕，duration 对其无意义
  LOGONLY —— 仅打日志
再统计 TIMED 中 dur=1 的实例数。两条路径独立，能对上才可信。
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

# 依据 simulator.py L429-499 逐分支核定
TIMED = {          # 调用 self._add / _add_shield → 进 _timed 列表
    "control",     # L435
    "shield",      # L440 _add_shield
    "reduce",      # L443
    "dot",         # L472
    "buff",        # L476 -> kind "bonus"
    "accel",       # L476 -> kind "bonus"
    "sunder",      # L479 -> kind "vuln"
    "vuln",        # L479 -> kind "vuln"
    "crit",        # L483
    "reflect",     # L486 -> kind "bonus"
    "immune",      # L489
}
INSTANT = {        # 当场结算，无 timed 项
    "heal",        # L446-455 直接改 hp
    "lifesteal",   # L456-464 直接改 hp
    "cleanse",     # L491-495 立即清列表
    "revive",      # L496 仅日志(特殊)
    "execute",     # 走 _extract_instant_flags，非 effects 分支
    "true_dmg",    # 同上
}
LOGONLY = {"aoe", "invis", "flavor"}
NOBRANCH = {"slow"}   # A 类：认出来了但 _apply_effects 无分支，落 L498 else

with contextlib.redirect_stdout(io.StringIO()):
    heroes = HeroLoader.load_all_heroes()

dur1 = Counter()
tot = Counter()
grand = 0
skill_count_dist = Counter()

for h in heroes:
    sk_list = h.get("skills") or []
    skill_count_dist[len(sk_list)] += 1
    for sk in sk_list:
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
out.append(f"运行期 effect 实例总数: {grand}")
out.append(f"英雄总数: {len(heroes)}")
out.append(f"[技能数分布] {dict(sorted(skill_count_dist.items()))}")

t_dur1 = sum(dur1[c] for c in TIMED)
t_tot = sum(tot[c] for c in TIMED)
i_dur1 = sum(dur1[c] for c in INSTANT)
l_dur1 = sum(dur1[c] for c in LOGONLY)
slow_all = sum(tot[c] for c in NOBRANCH)

out.append("")
out.append("[1] TIMED 类别（受 _decay_timed 影响）dur=1 明细")
hdr = f"{'category':<12}{'total':>8}{'dur=1':>8}"
out.append(hdr)
out.append("-" * len(hdr))
for c in sorted(TIMED, key=lambda x: -dur1[x]):
    out.append(f"{c:<12}{tot[c]:>8}{dur1[c]:>8}")
out.append("-" * len(hdr))
out.append(f"{'TIMED 合计':<12}{t_tot:>8}{t_dur1:>8}")

out.append("")
out.append(f"[2] D 类（纯时序失效）实例数 = {t_dur1}")
out.append(f"    占运行期总实例比 = {t_dur1 / grand * 100:.2f}%")
out.append(f"[3] slow 无分支（A 类，全时长失效） = {slow_all}")
out.append(f"[4] D + A 合计 = {t_dur1 + slow_all}"
           f"  占比 = {(t_dur1 + slow_all) / grand * 100:.2f}%")

out.append("")
out.append("[5] 口径对照：为何不能用 70.72%")
all_dur1 = sum(dur1.values())
out.append(f"    全部类别 dur=1 = {all_dur1} ({all_dur1 / grand * 100:.2f}%)")
out.append(f"    其中 INSTANT 类 dur=1 = {i_dur1}（duration 对其无意义，不应计入）")
out.append(f"    其中 LOGONLY 类 dur=1 = {l_dur1}（本就只打日志，不应计入）")
out.append(f"    其中 NOBRANCH(slow) dur=1 = {dur1['slow']}（属 A 类，不应重复计入 D 类）")
out.append(f"    扣除后 = {all_dur1} - {i_dur1} - {l_dur1} - {dur1['slow']} = "
           f"{all_dur1 - i_dur1 - l_dur1 - dur1['slow']}")

out.append("")
out.append("[6] control 后手方失效率（对照 code-reviewer 的 95.6%）")
out.append(f"    当前已生效 control: total={tot['control']}, dur=1={dur1['control']}, "
           f"占比={dur1['control'] / tot['control'] * 100:.2f}%")

txt = "\n".join(out)
dst = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_timed_scope_result.txt")
with open(dst, "w", encoding="utf-8") as f:
    f.write(txt)
print("WROTE", dst)
