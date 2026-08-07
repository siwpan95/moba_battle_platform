#!/usr/bin/env python3
"""Gate C/D 全量平衡回归仿真 — Wave 0 数据再生后。

采样协议（GDD §4.3）：
  L9, seed=20260805, 60 回合上限
  采样 ≥120 英雄（确保覆盖 12 个大盘 IP + 12 个完整 IP，均匀分布）
  每英雄 vs 全池随机对手 40 局
  分层对位：T1 vs T4、T1 vs T3（vainglory 仅存 7 张）

产出：全量 C-1~C-12 + C-13/C-14 指标，与 GDD §1.9 基线对比。
"""

import sys, os, json, random, time, statistics, math
from collections import defaultdict, Counter

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from core.loader import HeroLoader
from core.simulator import BattleSimulator

# ── Tier 分类 ────────────────────────────────────────────────────────────

def _load_template_names() -> set:
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

def run_one_battle(card_a: dict, card_b: dict, battle_seed: int, max_turns: int = 60):
    """返回 {winner, turns, timeout?, hp_a_final, hp_b_final, damage_per_turn_a, damage_per_turn_b}"""
    rng = random.Random(battle_seed)
    sim = BattleSimulator(card_a, card_b, level1=9, level2=9, rng=rng)
    hp_a_init = sim.hp1
    hp_b_init = sim.hp2

    for _ in range(max_turns):
        logs = sim.execute_turn()
        winner = None
        for line in logs:
            if "获得胜利" in line:
                if sim.hero1 in line:
                    winner = "A"
                elif sim.hero2 in line:
                    winner = "B"
                break
        if winner:
            dmg_a = max(0, hp_a_init - sim.hp1)
            dmg_b = max(0, hp_b_init - sim.hp2)
            return {"winner": winner, "turns": sim.turn,
                    "hp_a_final": sim.hp1, "hp_b_final": sim.hp2,
                    "dmg_per_turn_a": dmg_a / max(1, sim.turn),
                    "dmg_per_turn_b": dmg_b / max(1, sim.turn)}

    # 超时
    dmg_a = max(0, hp_a_init - sim.hp1)
    dmg_b = max(0, hp_b_init - sim.hp2)
    if sim.hp1 > sim.hp2:
        return {"winner": "A", "turns": max_turns, "timeout": True,
                "hp_a_final": sim.hp1, "hp_b_final": sim.hp2,
                "dmg_per_turn_a": dmg_a / max_turns,
                "dmg_per_turn_b": dmg_b / max_turns}
    elif sim.hp2 > sim.hp1:
        return {"winner": "B", "turns": max_turns, "timeout": True,
                "hp_a_final": sim.hp1, "hp_b_final": sim.hp2,
                "dmg_per_turn_a": dmg_a / max_turns,
                "dmg_per_turn_b": dmg_b / max_turns}
    else:
        return {"winner": "draw", "turns": max_turns, "timeout": True,
                "hp_a_final": sim.hp1, "hp_b_final": sim.hp2,
                "dmg_per_turn_a": dmg_a / max_turns,
                "dmg_per_turn_b": dmg_b / max_turns}


# ── 采样：按 IP 均匀分布 ───────────────────────────────────────────────────

def sample_heroes_by_ip(heroes, rng, target=120):
    """确保 12 大盘 IP + 12 完整 IP 均匀覆盖，每 IP 至少采样比例分配。"""
    # 分组
    LARGE_IPS = ["league_of_legends", "300_heroes", "mobile_legends_bang_bang",
                 "smite", "dota2", "honor_of_kings", "arena_of_valor",
                 "yinghunzhiren", "heroes_of_the_storm", "onmyoji_arena",
                 "pokemon_unite", "marvel_super_war"]
    # vainglory 在大盘IP里但真实覆盖0%，单独处理
    
    ip_cards = defaultdict(list)
    for h in heroes:
        game_dir = h.get("_game_dir", "unknown")
        if game_dir == "character_cards":
            continue  # skip _index
        ip_cards[game_dir].append(h)
    
    sampled = []
    # 每IP按占比采样
    total_valid = sum(len(v) for k, v in ip_cards.items())
    for ip, cards in sorted(ip_cards.items()):
        proportion = len(cards) / total_valid
        n_from_ip = max(1, round(target * proportion))
        n_from_ip = min(n_from_ip, len(cards))
        if cards:
            picked = rng.sample(cards, n_from_ip)
            sampled.extend(picked)
    
    # 如果不足 target，从 T1 和 T4 补
    if len(sampled) < target:
        t1_cards = [h for h in heroes if classify_tier(h) == "T1_real" and h not in sampled]
        t4_cards = [h for h in heroes if classify_tier(h) == "T4_template" and h not in sampled]
        remaining = target - len(sampled)
        extra_t1 = min(remaining // 2, len(t1_cards))
        extra_t4 = min(remaining - extra_t1, len(t4_cards))
        if t1_cards:
            sampled.extend(rng.sample(t1_cards, extra_t1))
        if t4_cards:
            sampled.extend(rng.sample(t4_cards, extra_t4))
    
    return sampled


# ── 主流程 ──────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print(" Gate C 平衡门控 — Wave 0 数据再生后全量回归")
    print(" L9 / seed=20260805 / 60回合上限")
    print("=" * 70)

    # [1] 加载
    print("\n[1] 加载全量英雄...")
    all_raw = HeroLoader.load_all_heroes()
    # 过滤掉 _index
    heroes = [h for h in all_raw if h.get("_game_dir") != "character_cards"]
    print(f"    有效英雄: {len(heroes)} / 总加载: {len(all_raw)}")

    # [2] 分层
    tier_buckets = defaultdict(list)
    for h in heroes:
        tier_buckets[classify_tier(h)].append(h)
    
    print("\n[2] Post Wave 0 分层分布:")
    for t in ["T1_real", "T2_partial", "T4_template", "T3_stub"]:
        cards = tier_buckets[t]
        print(f"    {t}: {len(cards)} 名")
        if t == "T3_stub":
            for c in cards:
                ip = c.get("_game_dir", "?")
                name = c.get("hero", {}).get("name", "?")
                n_skills = len(c.get("skills", [])) if isinstance(c.get("skills", []), list) else 0
                print(f"      → {ip}/{name} ({n_skills}槽)")

    # [3] 采样 — 按 IP 均匀
    rng = random.Random(20260805)
    sampled = sample_heroes_by_ip(heroes, rng, target=130)
    
    tier_sample = defaultdict(list)
    ip_sample = defaultdict(list)
    for h in sampled:
        tier_sample[classify_tier(h)].append(h)
        ip_sample[h.get("_game_dir", "?")].append(h)
    
    print(f"\n[3] 采样 {len(sampled)} 名英雄")
    print(f"    覆盖 IP: {len(ip_sample)} 个")
    for t in ["T1_real", "T2_partial", "T4_template", "T3_stub"]:
        n = len(tier_sample[t])
        pct = n / len(sampled) * 100 if sampled else 0
        print(f"    {t}: {n} 名 ({pct:.0f}%)")
    # 检查 IP 覆盖
    large_covered = sum(1 for ip in ["league_of_legends","300_heroes","mobile_legends_bang_bang",
        "smite","dota2","honor_of_kings","arena_of_valor","yinghunzhiren",
        "heroes_of_the_storm","onmyoji_arena","pokemon_unite","marvel_super_war"]
        if ip in ip_sample)
    complete_ips = sum(1 for ip in ip_sample if len(ip_sample[ip]) > 0)
    print(f"    大盘IP覆盖: {large_covered}/12")
    print(f"    总IP覆盖: {complete_ips}/24")

    # [4] 全局随机对局
    N_BATTLES = 40
    MASTER_SEED = 20260805
    battle_rng = random.Random(MASTER_SEED)
    all_pool = heroes  # 全池随机对手

    total_battles = len(sampled) * N_BATTLES
    print(f"\n[4] 执行 {total_battles} 局全局随机对战...")
    t0 = time.time()

    hero_results = {}
    all_turns = []
    all_damages = []  # per-battle avg damage per turn (of the sampled hero)
    match_results = []
    global_dmg_per_turn = []  # all battle damage values

    for hi, hero_card in enumerate(sampled):
        hero_name = f"{hero_card.get('_game_dir','?')}/{hero_card['hero']['name']}"
        hero_tier = classify_tier(hero_card)
        wins = losses = draws = 0
        turns_list = []
        damages_list = []
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
            damages_list.append(result["dmg_per_turn_a"])
            all_damages.append(result["dmg_per_turn_a"])
            global_dmg_per_turn.append(result["dmg_per_turn_a"])
            global_dmg_per_turn.append(result["dmg_per_turn_b"])
            if result.get("timeout"):
                timeout_count += 1

            if (hi * N_BATTLES + bi + 1) % 600 == 0:
                elapsed = time.time() - t0
                done = hi * N_BATTLES + bi + 1
                rate = done / elapsed
                eta = (total_battles - done) / rate if rate > 0 else 0
                print(f"    {done}/{total_battles} ({elapsed:.0f}s, {rate:.0f}局/s, ETA {eta:.0f}s)")

        wr = wins / N_BATTLES
        hero_results[hero_name] = {
            "tier": hero_tier,
            "ip": hero_card.get("_game_dir", "?"),
            "wins": wins, "losses": losses, "draws": draws,
            "win_rate": wr,
            "turns_p50": statistics.median(turns_list),
            "turns_p95": sorted(turns_list)[int(len(turns_list) * 0.95)],
            "dmg_p50": statistics.median(damages_list) if damages_list else 0,
            "timeouts": timeout_count,
        }

    elapsed = time.time() - t0
    print(f"    完成: {total_battles} 局, {elapsed:.0f}s ({total_battles/elapsed:.1f}局/s)")

    # [5] 分层对位专项（T1 vs T4, T1 vs T3）
    print(f"\n[5] 分层对位专项...")
    matchup_configs = [
        ("T1_real", "T4_template", 600),
        ("T1_real", "T3_stub", min(300, len(tier_buckets["T3_stub"]) * 40)),
    ]
    matchup_results = {}
    matchup_rng = random.Random(MASTER_SEED + 9999)

    for t_a, t_b, n_battles in matchup_configs:
        pool_a = tier_buckets[t_a]
        pool_b = tier_buckets[t_b]
        if not pool_a or not pool_b or n_battles <= 0:
            print(f"    {t_a} vs {t_b}: 跳过（池空）")
            continue
        
        wins_a = losses_a = draws_a = 0
        for bi in range(n_battles):
            card_a = matchup_rng.choice(pool_a)
            card_b = matchup_rng.choice(pool_b)
            bseed = MASTER_SEED * 20000 + bi
            result = run_one_battle(card_a, card_b, bseed)
            if result["winner"] == "A":
                wins_a += 1
            elif result["winner"] == "B":
                losses_a += 1
            else:
                draws_a += 1
        
        wr_a = wins_a / n_battles
        matchup_results[f"{t_a}_vs_{t_b}"] = {
            "wr_a": wr_a, "wins": wins_a, "losses": losses_a, "draws": draws_a, "n": n_battles
        }
        print(f"    {t_a} vs {t_b}: A胜率={wr_a:.1%} ({wins_a}/{n_battles})")

    # [6] 指标计算
    win_rates = [r["win_rate"] for r in hero_results.values()]
    mean_wr = statistics.mean(win_rates)
    sigma_wr = statistics.stdev(win_rates) * 100 if len(win_rates) > 1 else 0  # pp
    below_40 = sum(1 for wr in win_rates if wr < 0.40)
    above_60 = sum(1 for wr in win_rates if wr > 0.60)
    extremes = sum(1 for wr in win_rates if wr < 0.25 or wr > 0.75)
    extreme_heroes = [(n, r["win_rate"], r["tier"], r["ip"]) for n, r in hero_results.items()
                      if r["win_rate"] < 0.25 or r["win_rate"] > 0.75]

    turns_sorted = sorted(all_turns)
    turns_p50 = statistics.median(all_turns)
    turns_p95 = turns_sorted[int(len(turns_sorted) * 0.95)]
    turns_p5 = turns_sorted[int(len(turns_sorted) * 0.05)]

    timeout_pct = sum(1 for t in all_turns if t >= 60) / len(all_turns)

    # 每回合伤害
    dmg_sorted = sorted(global_dmg_per_turn)
    dmg_p5 = dmg_sorted[int(len(dmg_sorted) * 0.05)]
    dmg_p50 = statistics.median(global_dmg_per_turn)
    dmg_p95 = dmg_sorted[int(len(dmg_sorted) * 0.95)]
    dmg_p95_p50_ratio = dmg_p95 / dmg_p50 if dmg_p50 > 0 else float('inf')

    # 骰期望与CD合规
    dice_ok = 0; cd_ok = 0; n_valid = 0
    for h in sampled:
        skills = h.get("skills", [])
        if isinstance(skills, list) and len(skills) >= 4:
            n_valid += 1
            e = dice_expectation(skills)
            if 24.0 <= e <= 34.0:
                dice_ok += 1
            acd = avg_cooldown(skills)
            s0cd = skills[0].get("cooldown", 0) if skills else 99
            if acd <= 3.0 and s0cd == 0:
                cd_ok += 1

    # 全局随机对局下的分层对位（从 match_results 聚合）
    tier_matchups = defaultdict(lambda: {"wins": 0, "total": 0})
    for hero_tier, opp_tier, outcome in match_results:
        key = f"{hero_tier}_vs_{opp_tier}"
        tier_matchups[key]["total"] += 1
        if outcome == "win":
            tier_matchups[key]["wins"] += 1

    # ═════════════════════════════════════════════════════════════════
    # 输出
    # ═════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print(" Gate C 指标汇总 — 对比 GDD §1.9 修复前基线")
    print("=" * 70)

    BASELINE = {
        "mean_wr": 0.493, "sigma": 33.3, "below_40_pct": 0.381,
        "above_60_pct": 0.398, "extremes": "大量",
        "turns_p50": 19, "turns_p95": 61, "timeout_pct": 0.068,
        "dmg_p50": 22, "dmg_p95_p50": 2.68, "dmg_p5": 0,
        "t1_vs_t4": 0.881, "t1_vs_t3": 0.987,
    }

    def fmt_delta(cur, base, unit="", lower_better=True):
        if isinstance(base, str):
            return f"(基线: {base})"
        delta = cur - base
        arrow = "↓" if delta < 0 else "↑" if delta > 0 else "→"
        return f"(基线: {base}{unit}, Δ={arrow}{abs(delta):.1f}{unit})"

    print(f"\n  {'指标':<30} {'本轮实测':>12} {'修复前基线':>18} {'趋势'}")
    print(f"  {'-'*30} {'-'*12} {'-'*18} {'-'*20}")
    print(f"  {'全池胜率均值':<30} {mean_wr:>11.1%}  {BASELINE['mean_wr']:>17.1%}  {fmt_delta(mean_wr, BASELINE['mean_wr'], '', False)}")
    print(f"  {'全池胜率 σ':<30} {sigma_wr:>10.1f}pp  {BASELINE['sigma']:>16.1f}pp  {fmt_delta(sigma_wr, BASELINE['sigma'], 'pp')}")
    print(f"  {'胜率 <40% 占比':<30} {below_40/len(win_rates):>11.1%}  {BASELINE['below_40_pct']:>17.1%}  {fmt_delta(below_40/len(win_rates), BASELINE['below_40_pct'], '', False)}")
    print(f"  {'胜率 >60% 占比':<30} {above_60/len(win_rates):>11.1%}  {BASELINE['above_60_pct']:>17.1%}  {fmt_delta(above_60/len(win_rates), BASELINE['above_60_pct'], '', False)}")
    print(f"  {'极值英雄 (<25%/>75%)':<30} {extremes:>12}  {BASELINE['extremes']:>18}  {'—'}")
    print(f"  {'回合数 P50':<30} {turns_p50:>12.0f}  {BASELINE['turns_p50']:>18}  {fmt_delta(turns_p50, BASELINE['turns_p50'], '')}")
    print(f"  {'回合数 P95':<30} {turns_p95:>12.0f}  {BASELINE['turns_p95']:>18}  {fmt_delta(turns_p95, BASELINE['turns_p95'], '')}")
    print(f"  {'60回合未分胜负率':<30} {timeout_pct:>11.1%}  {BASELINE['timeout_pct']:>17.1%}  {fmt_delta(timeout_pct, BASELINE['timeout_pct'], '', False)}")
    print(f"  {'每回合伤害 P50':<30} {dmg_p50:>12.1f}  {BASELINE['dmg_p50']:>18}  {fmt_delta(dmg_p50, BASELINE['dmg_p50'], '')}")
    print(f"  {'伤害 P95/P50 比':<30} {dmg_p95_p50_ratio:>12.2f}  {BASELINE['dmg_p95_p50']:>18}  {fmt_delta(dmg_p95_p50_ratio, BASELINE['dmg_p95_p50'], '')}")
    print(f"  {'每回合伤害 P5':<30} {dmg_p5:>12.1f}  {BASELINE['dmg_p5']:>18}  {fmt_delta(dmg_p5, BASELINE['dmg_p5'], '')}")

    # ── 分层对位 ──
    print(f"\n  {'分层对位胜率 (A方)':<30} {'本轮实测':>12} {'修复前基线':>18}")
    print(f"  {'-'*30} {'-'*12} {'-'*18}")
    mr = matchup_results
    for key, base_key in [("T1_real_vs_T4_template", "t1_vs_t4"), ("T1_real_vs_T3_stub", "t1_vs_t3")]:
        if key in mr:
            d = mr[key]
            base_val = BASELINE[base_key]
            print(f"  {key:<30} {d['wr_a']:>11.1%}  {base_val:>17.1%}  {fmt_delta(d['wr_a'], base_val, '', False)}")
    # 全局随机中碰到的分层
    for key in sorted(tier_matchups.keys()):
        d = tier_matchups[key]
        if d["total"] >= 10:
            wr = d["wins"] / d["total"]
            print(f"  {key + ' (随机)':<30} {wr:>11.1%}  {'—':>18}  (n={d['total']})")

    # ── 分层胜率统计 ──
    print(f"\n  {'分层':<15} {'均值':>8} {'σ':>8} {'最小':>8} {'最大':>8} {'n':>5}")
    print(f"  {'-'*15} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*5}")
    tier_wr = defaultdict(list)
    for name, r in hero_results.items():
        tier_wr[r["tier"]].append(r["win_rate"])
    for t in ["T1_real", "T2_partial", "T4_template", "T3_stub"]:
        wrs = tier_wr.get(t, [])
        if wrs:
            tier_sigma = (statistics.stdev(wrs) * 100) if len(wrs) > 1 else 0
            print(f"  {t:<15} {statistics.mean(wrs):>7.1%}  {tier_sigma:>7.1f}pp  {min(wrs):>7.1%}  {max(wrs):>7.1%}  {len(wrs):>5}")

    print(f"\n  骰期望配额 (24-34): {dice_ok}/{n_valid}")
    print(f"  CD 合规 (avg≤3.0, slot0=0): {cd_ok}/{n_valid}")

    # ═════════════════════════════════════════════════════════════════
    # Gate C 逐项判定
    # ═════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print(" Gate C 逐项判定 (GDD §4.3)")
    print("=" * 70)

    results = {}
    n_all = len(win_rates)

    def judge(cid, label, value, threshold_str, ok):
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"  C-{cid}: {label} → {value} (阈值: {threshold_str}) [{status}]")
        return status

    results["C-1"]  = judge("1",  f"单英雄胜率落入40-60%占比", f"{sum(1 for wr in win_rates if 0.40 <= wr <= 0.60)}/{n_all} = {sum(1 for wr in win_rates if 0.40 <= wr <= 0.60)/n_all:.1%}", "≥90%", sum(1 for wr in win_rates if 0.40 <= wr <= 0.60)/n_all >= 0.90)
    results["C-2"]  = judge("2",  f"全池胜率σ", f"{sigma_wr:.1f}pp", "≤20pp (Wave 0)", sigma_wr <= 20)
    results["C-3"]  = judge("3",  f"胜率<40%英雄占比", f"{below_40}/{n_all} = {below_40/n_all:.1%}", "≤10%", below_40/n_all <= 0.10)
    results["C-4"]  = judge("4",  f"胜率>60%英雄占比", f"{above_60}/{n_all} = {above_60/n_all:.1%}", "≤10%", above_60/n_all <= 0.10)
    results["C-5"]  = judge("5",  f"极值英雄 (<25%或>75%)", f"{extremes} 名", "==0", extremes == 0)
    results["C-10"] = judge("10", f"回合数 P50", f"{turns_p50:.0f}", "12-25", 12 <= turns_p50 <= 25)
    results["C-11"] = judge("11", f"回合数 P95", f"{turns_p95:.0f}", "≤45", turns_p95 <= 45)
    results["C-12"] = judge("12", f"60回合未分胜负率", f"{timeout_pct:.1%}", "≤3%", timeout_pct <= 0.03)
    results["C-7"]  = judge("7",  f"伤害P50", f"{dmg_p50:.1f}", "18-28", 18 <= dmg_p50 <= 28)
    results["C-8"]  = judge("8",  f"伤害P95/P50", f"{dmg_p95_p50_ratio:.2f}", "≤3.0", dmg_p95_p50_ratio <= 3.0)
    results["C-9"]  = judge("9",  f"伤害P5", f"{dmg_p5:.1f}", "≥5", dmg_p5 >= 5)

    # C-6 分层对位
    c6_ok = True
    print(f"\n  C-6: 分层对位 (45-55%):")
    for key, base_key in [("T1_real_vs_T4_template", "t1_vs_t4"), ("T1_real_vs_T3_stub", "t1_vs_t3")]:
        if key in mr:
            wr = mr[key]["wr_a"]
            ok = 0.45 <= wr <= 0.55
            c6_ok = c6_ok and ok
            print(f"    {key}: {wr:.1%} → {'PASS' if ok else 'FAIL'}")
    results["C-6"] = "✅ PASS" if c6_ok else "❌ FAIL"
    if c6_ok:
        print(f"  C-6: 整体 → ✅ PASS")
    else:
        print(f"  C-6: 整体 → ❌ FAIL")

    # C-13/C-14
    results["C-13"] = judge("13", f"骰期望配额", f"{dice_ok}/{n_valid}", "100%", dice_ok == n_valid) if n_valid > 0 else "N/A"
    results["C-14"] = judge("14", f"CD合规", f"{cd_ok}/{n_valid}", "100%", cd_ok == n_valid) if n_valid > 0 else "N/A"

    fail_count = sum(1 for v in results.values() if "FAIL" in str(v))
    pass_count = sum(1 for v in results.values() if "PASS" in str(v))
    print(f"\n  Gate C 总体: {pass_count} PASS / {fail_count} FAIL / {len(results)} 总判据")

    if fail_count == 0:
        print("  **Gate C 判定: PASS** ✅")
    else:
        print(f"  **Gate C 判定: {'CONCERNS' if fail_count <= 3 else 'FAIL'}**")

    # 极值英雄详情
    if extreme_heroes:
        print(f"\n  极值英雄详情 ({len(extreme_heroes)} 名):")
        for name, wr, tier, ip in sorted(extreme_heroes, key=lambda x: x[1]):
            print(f"    [{tier}] {ip} {name}: {wr:.1%}")

    print("\n=== Gate C 仿真完成 ===")

    # 返回数据供报告使用
    return {
        "sampled_n": len(sampled),
        "ip_coverage": len(ip_sample),
        "total_battles": total_battles,
        "mean_wr": mean_wr,
        "sigma_wr": sigma_wr,
        "below_40": below_40,
        "above_60": above_60,
        "extremes": extremes,
        "extreme_heroes": extreme_heroes,
        "turns_p50": turns_p50,
        "turns_p95": turns_p95,
        "turns_p5": turns_p5,
        "timeout_pct": timeout_pct,
        "dmg_p5": dmg_p5,
        "dmg_p50": dmg_p50,
        "dmg_p95": dmg_p95,
        "dmg_p95_p50_ratio": dmg_p95_p50_ratio,
        "tier_wr": {t: (statistics.mean(wrs) if wrs else 0, statistics.stdev(wrs) if len(wrs) > 1 else 0, len(wrs))
                     for t, wrs in tier_wr.items()},
        "matchup_results": matchup_results,
        "tier_matchups": {k: v for k, v in tier_matchups.items() if v["total"] >= 10},
        "dice_ok": dice_ok,
        "cd_ok": cd_ok,
        "n_valid": n_valid,
        "results": results,
        "hero_results": hero_results,
    }

if __name__ == "__main__":
    data = main()
