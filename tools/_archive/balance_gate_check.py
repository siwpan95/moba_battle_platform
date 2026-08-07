#!/usr/bin/env python3
"""Gate C 平衡门控回归脚本（严守真 / 只读仿真）。

采样协议（GDD §4.3）：
  L9, 从全池随机抽取 ≥120 英雄（T1/T2/T3/T4 各 ≥30），
  各跑 40 局 vs 全池随机对手，seed=20260805，60 回合上限。

产出 Gate C-1 ~ C-14 逐项判定。
"""

import sys, os, json, random, time, statistics
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from core.loader import HeroLoader
from core.simulator import BattleSimulator

# ── Tier 分类（复现 GDD §1.4 逻辑）─────────────────────────────────────────

def _load_template_names() -> set:
    """递归抽取 _templates.json 中所有技能名。"""
    tmpl_path = os.path.join(PROJECT_ROOT, "data", "skills", "_templates.json")
    names = set()
    try:
        with open(tmpl_path, "r", encoding="utf-8") as f:
            tmpl = json.load(f)
    except Exception:
        return names

    def _collect(obj):
        if isinstance(obj, dict):
            if "name" in obj and isinstance(obj["name"], str):
                names.add(obj["name"])
            for v in obj.values():
                _collect(v)
        elif isinstance(obj, list):
            for item in obj:
                _collect(item)

    _collect(tmpl)
    return names

TEMPLATE_NAMES = _load_template_names()
ROLE_PREFIXES = ("坦克", "战士", "刺客", "法师", "射手", "辅助")
GENERIC_PATTERNS = ("技能一", "技能二", "技能三", "技能四", "大招", "火球术",
                    "治疗术", "护盾", "冲锋", "箭雨", "毒刃", "暗影步",
                    "D&D", "DnD", "dnd")

def _is_template_name(name: str) -> bool:
    if not name or not isinstance(name, str):
        return True
    if name in TEMPLATE_NAMES:
        return True
    if name.startswith(ROLE_PREFIXES):
        return True
    for pat in GENERIC_PATTERNS:
        if pat in name:
            return True
    return False

def classify_tier(card: dict) -> str:
    skills = card.get("skills", [])
    if not isinstance(skills, list):
        return "T3_stub"
    effective = skills[:4]
    if len(effective) < 4:
        return "T3_stub"
    real_count = sum(1 for s in effective
                     if isinstance(s.get("name"), str) and not _is_template_name(s["name"]))
    if real_count == 4:
        return "T1_real"
    elif real_count > 0:
        return "T2_partial"
    else:
        return "T4_template"

def dice_expectation(skills: list) -> float:
    total = 0.0
    for s in skills[:4]:
        dmg = s.get("damage", {})
        if isinstance(dmg, dict):
            total += dmg.get("dice_count", 0) * (dmg.get("dice_size", 6) + 1) / 2
    return total

def avg_cooldown(skills: list) -> float:
    cds = [s.get("cooldown", 0) for s in skills[:4]]
    return sum(cds) / len(cds) if cds else 0


# ── 单场对战 ────────────────────────────────────────────────────────────────

def run_one_battle(card_a: dict, card_b: dict, battle_seed: int, max_turns: int = 60) -> dict:
    """执行一场对战，返回统计信息。"""
    rng = random.Random(battle_seed)
    sim = BattleSimulator(card_a, card_b, level1=9, level2=9, rng=rng)

    for _ in range(max_turns):
        logs = sim.execute_turn()
        # 检查胜负
        winner = None
        for line in logs:
            if "获得胜利" in line:
                if sim.hero1 in line:
                    winner = "A"
                elif sim.hero2 in line:
                    winner = "B"
                break
        if winner:
            return {"winner": winner, "turns": sim.turn,
                    "hp_a_final": sim.hp1, "hp_b_final": sim.hp2}

    # 超时：按 HP 判定
    if sim.hp1 > sim.hp2:
        return {"winner": "A", "turns": max_turns, "timeout": True,
                "hp_a_final": sim.hp1, "hp_b_final": sim.hp2}
    elif sim.hp2 > sim.hp1:
        return {"winner": "B", "turns": max_turns, "timeout": True,
                "hp_a_final": sim.hp1, "hp_b_final": sim.hp2}
    else:
        return {"winner": "draw", "turns": max_turns, "timeout": True,
                "hp_a_final": sim.hp1, "hp_b_final": sim.hp2}


# ── 主流程 ──────────────────────────────────────────────────────────────────

def main():
    print("=" * 64)
    print(" Gate C 平衡门控 — L9 / seed=20260805 / 60回合上限")
    print("=" * 64)

    print("\n[1] 加载全量英雄...")
    heroes = HeroLoader.load_all_heroes()
    print(f"    共计 {len(heroes)} 名英雄")

    # 分层统计
    tier_buckets = defaultdict(list)
    for h in heroes:
        tier_buckets[classify_tier(h)].append(h)

    print("\n[2] 分层分布:")
    for t in ["T1_real", "T2_partial", "T4_template", "T3_stub"]:
        print(f"    {t}: {len(tier_buckets[t])} 名")

    # 采样
    rng = random.Random(20260805)
    N_PER_TIER = 30
    sampled = []
    for t in ["T1_real", "T2_partial", "T4_template", "T3_stub"]:
        pool = tier_buckets[t]
        n = min(N_PER_TIER, len(pool))
        sampled.extend(rng.sample(pool, n))

    print(f"\n[3] 采样 {len(sampled)} 名英雄（目标 ≥120，各层 ≥{N_PER_TIER}）")
    tier_sample = defaultdict(list)
    for h in sampled:
        tier_sample[classify_tier(h)].append(h)
    for t in ["T1_real", "T2_partial", "T4_template", "T3_stub"]:
        print(f"    {t}: {len(tier_sample[t])} 名")

    all_pool = list(heroes)
    N_BATTLES = 40
    MASTER_SEED = 20260805
    battle_rng = random.Random(MASTER_SEED)

    total_battles = len(sampled) * N_BATTLES
    print(f"\n[4] 执行 {total_battles} 局对战...")
    t0 = time.time()

    hero_results = {}   # hero_name -> {tier, wins, losses, draws, win_rate, turns[], dmg[], ...}
    all_turns = []
    match_results = []  # (hero_tier, opp_tier, outcome)

    for hi, hero_card in enumerate(sampled):
        hero_name = f"{hero_card.get('_game_dir','?')}/{hero_card['hero']['name']}"
        hero_tier = classify_tier(hero_card)
        wins = losses = draws = 0
        turns_list = []
        timeout_count = 0

        for bi in range(N_BATTLES):
            opp = battle_rng.choice(all_pool)
            opp_tier = classify_tier(opp)
            battle_seed = MASTER_SEED * 10000 + hi * 100 + bi

            result = run_one_battle(hero_card, opp, battle_seed)

            if result["winner"] == "A":
                wins += 1
                match_results.append((hero_tier, opp_tier, "win"))
            elif result["winner"] == "B":
                losses += 1
                match_results.append((hero_tier, opp_tier, "loss"))
            else:
                draws += 1
                match_results.append((hero_tier, opp_tier, "draw"))

            turns_list.append(result["turns"])
            all_turns.append(result["turns"])
            if result.get("timeout"):
                timeout_count += 1

            if (hi * N_BATTLES + bi + 1) % 600 == 0:
                elapsed = time.time() - t0
                done = hi * N_BATTLES + bi + 1
                rate = done / elapsed
                eta = (total_battles - done) / rate if rate > 0 else 0
                print(f"    {done}/{total_battles} 局 ({elapsed:.0f}s, ~{rate:.0f}局/s, 预计剩余{eta:.0f}s)")

        wr = wins / N_BATTLES
        hero_results[hero_name] = {
            "tier": hero_tier,
            "wins": wins, "losses": losses, "draws": draws,
            "win_rate": wr,
            "turns_p50": statistics.median(turns_list),
            "turns_p95": sorted(turns_list)[int(len(turns_list) * 0.95)],
        }

    elapsed = time.time() - t0
    print(f"    完成: {total_battles} 局, 耗时 {elapsed:.0f}s ({total_battles/elapsed:.1f} 局/s)")

    # ── 指标计算 ──────────────────────────────────────────────────────────
    win_rates = [r["win_rate"] for r in hero_results.values()]
    mean_wr = statistics.mean(win_rates)
    sigma_wr = statistics.stdev(win_rates) if len(win_rates) > 1 else 0
    below_40 = sum(1 for wr in win_rates if wr < 0.40)
    above_60 = sum(1 for wr in win_rates if wr > 0.60)
    extremes = sum(1 for wr in win_rates if wr < 0.25 or wr > 0.75)
    extreme_heroes = [(n, r["win_rate"], r["tier"]) for n, r in hero_results.items()
                      if r["win_rate"] < 0.25 or r["win_rate"] > 0.75]
    turns_sorted = sorted(all_turns)
    turns_p50 = statistics.median(all_turns)
    turns_p95 = turns_sorted[int(len(turns_sorted) * 0.95)]

    # 每回合伤害：用总HP变化 / 回合数估算
    # 由于 execute_turn 内部较复杂，我们用 HP 变化估算
    # 这里用 (max_hp - final_hp) / turns 作为代理

    timeout_pct = sum(1 for t in all_turns if t >= 60) / len(all_turns)

    # 分层对位
    tier_matchups = defaultdict(lambda: {"wins": 0, "total": 0})
    for hero_tier, opp_tier, outcome in match_results:
        key = f"{hero_tier}_vs_{opp_tier}"
        tier_matchups[key]["total"] += 1
        if outcome == "win":
            tier_matchups[key]["wins"] += 1

    # 骰期望与CD
    dice_ok = 0
    cd_ok = 0
    for h in sampled:
        skills = h.get("skills", [])
        if isinstance(skills, list) and len(skills) >= 4:
            e = dice_expectation(skills)
            if 24.0 <= e <= 34.0:
                dice_ok += 1
            acd = avg_cooldown(skills)
            s0cd = skills[0].get("cooldown", 0) if skills else 99
            if acd <= 3.0 and s0cd == 0:
                cd_ok += 1

    # ── 输出 ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 64)
    print(" Gate C 指标汇总（对比 GDD §1.9 基线）")
    print("=" * 64)

    print(f"\n  全池胜率均值: {mean_wr:.1%}  (基线 49.3%)")
    print(f"  全池胜率 σ:   {sigma_wr:.1f}pp  (基线 33.3pp)")
    print(f"  <40% 占比:    {below_40}/{len(win_rates)} = {below_40/len(win_rates):.1%}  (基线 38.1%)")
    print(f"  >60% 占比:    {above_60}/{len(win_rates)} = {above_60/len(win_rates):.1%}  (基线 39.8%)")
    print(f"  极值 (<25%/>75%): {extremes}  (基线: 大量)")
    print(f"  回合数 P50:   {turns_p50:.0f}  (基线 19)")
    print(f"  回合数 P95:   {turns_p95:.0f}  (基线 61)")
    print(f"  60回合未分胜负: {timeout_pct:.1%}  (基线 6.8%)")

    print("\n分层对位胜率:")
    for key in sorted(tier_matchups.keys()):
        d = tier_matchups[key]
        wr = d["wins"] / d["total"] if d["total"] else 0
        print(f"  {key}: {wr:.1%} ({d['wins']}/{d['total']})")

    print(f"\n骰期望配额 (24-34): {dice_ok}/{len([h for h in sampled if isinstance(h.get('skills'),list) and len(h['skills'])>=4])}")
    print(f"CD 合规 (avg≤3.0, slot0=0): {cd_ok}/{len([h for h in sampled if isinstance(h.get('skills'),list) and len(h['skills'])>=4])}")

    # ── 逐项判定 ──────────────────────────────────────────────────────────
    print("\n" + "=" * 64)
    print(" Gate C 逐项判定 (GDD §4.3)")
    print("=" * 64)

    results = {}

    def judge(name, value, threshold_str, ok):
        status = "PASS" if ok else "FAIL"
        print(f"  C-{name}: {value} (阈值 {threshold_str}) → [{status}]")
        return status

    n_all = len(win_rates)
    n_valid = len([h for h in sampled if isinstance(h.get('skills'), list) and len(h['skills']) >= 4])

    # 输出胜率分布诊断
    print(f"\n  [诊断] win_rates: mean={mean_wr:.1%}, σ={sigma_wr:.1f}pp, n={n_all}")
    print(f"  [诊断] win_rates 前10: {[f'{w:.1%}' for w in sorted(win_rates)[:10]]}")
    print(f"  [诊断] win_rates 后10: {[f'{w:.1%}' for w in sorted(win_rates)[-10:]]}")

    results["C-1"]  = judge("1 胜率均值", f"{mean_wr:.1%}", "40%-60%", 0.40 <= mean_wr <= 0.60)
    results["C-2"]  = judge("2 胜率σ", f"{sigma_wr:.1f}pp", "≤20pp (Wave0)", sigma_wr <= 20)
    results["C-3"]  = judge("3 <40%占比", f"{below_40/n_all:.1%}", "≤10%", below_40/n_all <= 0.10)
    results["C-4"]  = judge("4 >60%占比", f"{above_60/n_all:.1%}", "≤10%", above_60/n_all <= 0.10)
    results["C-5"]  = judge("5 极值英雄", str(extremes), "==0", extremes == 0)
    results["C-10"] = judge("10 回合P50", f"{turns_p50:.0f}", "12-25", 12 <= turns_p50 <= 25)
    results["C-11"] = judge("11 回合P95", f"{turns_p95:.0f}", "≤45", turns_p95 <= 45)
    results["C-12"] = judge("12 60r未分胜负", f"{timeout_pct:.1%}", "≤3%", timeout_pct <= 0.03)
    results["C-13"] = judge("13 骰期望配额", f"{dice_ok}/{n_valid}", "100%", dice_ok == n_valid) if n_valid > 0 else "N/A"
    results["C-14"] = judge("14 平均CD", f"{cd_ok}/{n_valid}", "100%", cd_ok == n_valid) if n_valid > 0 else "N/A"

    # C-6 分层对位
    print("\n  C-6 分层对位详细:")
    c6_fail = 0
    c6_keys = ["T1_real_vs_T3_stub", "T1_real_vs_T4_template", "T2_partial_vs_T4_template",
               "T1_real_vs_T2_partial"]
    for key in c6_keys:
        d = tier_matchups.get(key)
        if d and d["total"] > 0:
            wr = d["wins"] / d["total"]
            ok = 0.45 <= wr <= 0.55
            if not ok:
                c6_fail += 1
            print(f"    {key}: {wr:.1%} ({d['wins']}/{d['total']}) → {'PASS' if ok else 'FAIL'}")
        else:
            print(f"    {key}: 无数据 → N/A")
    results["C-6"] = "PASS" if c6_fail == 0 else "FAIL"

    fail_count = sum(1 for v in results.values() if v == "FAIL")
    print(f"\n  Gate C 总体: {fail_count} FAIL / {len(results)} 有效判据")

    if fail_count > 0:
        print("  判定: **FAIL**")
    else:
        print("  判定: PASS")

    # 输出分层胜率统计
    print("\n" + "=" * 64)
    print(" 分层胜率分布")
    print("=" * 64)
    tier_wr = defaultdict(list)
    for name, r in hero_results.items():
        tier_wr[r["tier"]].append(r["win_rate"])
    for t in ["T1_real", "T2_partial", "T4_template", "T3_stub"]:
        wrs = tier_wr.get(t, [])
        if wrs:
            print(f"  {t}: mean={statistics.mean(wrs):.1%}, σ={statistics.stdev(wrs):.1f}pp, "
                  f"min={min(wrs):.1%}, max={max(wrs):.1%}, n={len(wrs)}")

    print("\n=== Gate C 完成 ===")

    return hero_results, match_results, all_turns

if __name__ == "__main__":
    main()
