#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════╗
║        MOBA 英雄大乱斗 — 1v1 对战平台              ║
║   基于 D&D 5e 数值框架 + 1500+ 真实MOBA英雄卡池    ║
╚══════════════════════════════════════════════════════╝

战斗公式继承 D&D:
  • 物理伤害 = ATK × (1 − 对方AC × 0.005)  [最低30%]
  • 法术伤害 = AP × 技能倍率 × (1 − 对方WIS豁免 × 0.03)  [最低30%]
  • 暴击概率 = 基础10% + DEX调整×2%  [最低5%]
  • 暴击伤害 = 基础150% + DEX调整×5%
  • HP = 职业生命骰 + CON调整×等级 + 每级HP增量×(等级−1)

模块架构:
  core/engine.py   — 统一战斗引擎（物理/法术伤害、暴击、属性加成）
  core/config.py   — 全局常量与汉化映射表
  core/loader.py   — 英雄加载器（扫描角色卡目录）
  core/simulator.py — 战斗模拟器（等级插值、技能冷却、回合执行）
  ui/ui.py       — tkinter GUI 主窗口
  main.py     — 入口文件（本文件）
"""

import tkinter as tk
from tkinter import ttk

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ui.ui import BattlePlatform


if __name__ == "__main__":
    root = tk.Tk()

    # 设置 ttk 主题样式
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure(
        "TCombobox", fieldbackground="#21262d", background="#21262d",
        foreground="#f0f6fc", arrowcolor="#f0f6fc"
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", "#21262d")],
        foreground=[("readonly", "#f0f6fc")],
    )

    app = BattlePlatform(root)
    root.mainloop()
