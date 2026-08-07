#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时审计：空技能卡进入战斗后的退化行为（论证契约必须硬失败）。"""
import os
import random
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.simulator import BattleSimulator

lines = []


def mk(name, skills):
    return {
        "hero": {"name": name},
        "attributes": {a: {"modifier": 2} for a in ("STR", "DEX", "CON", "INT", "WIS", "CHA")},
        "stats_lv1": {"hp": 300, "ac": 10, "physical_atk": 10, "magic_power": 10,
                      "prof_bonus": 2, "hp_dnd_raw": 1},
        "stats_lv18": {"hp": 900, "ac": 20, "physical_atk": 40, "magic_power": 40},
        "skills": skills,
        "game": {"universal_role": "fighter"},
    }


# 空技能卡 vs 空技能卡（ADR-005 新 IP 卡漏过门禁后的运行时形态）
s = BattleSimulator(mk("新英雄A", []), mk("新英雄B", []), 10, 10, rng=random.Random(1))
turns = 0
ended = False
for _ in range(200):
    lg = s.execute_turn()
    turns += 1
    if any("获得胜利" in x for x in lg):
        ended = True
        break
lines.append("[空技能卡对战] 200 回合内分出胜负 = %s，实际跑了 %d 回合" % (ended, turns))
lines.append("  hp1=%d/%d  hp2=%d/%d" % (s.hp1, s.max_hp1, s.hp2, s.max_hp2))
lines.append("  末回合日志样本: %r" % (lg[:2],))

with open(os.path.join(PROJECT_ROOT, "scripts", "_archi_gate_audit.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
