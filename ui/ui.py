#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对战平台 UI —— tkinter GUI 主窗口"""

import tkinter as tk
from tkinter import ttk, font as tkfont
import random
import sys
import os
import threading
from collections import OrderedDict

# 日志与润色后日志的保存目录（硬编码）
SAVE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs"
)

from core.config import FONT_DIR, ROLE_NAME_CN, game_cn
from core.catalog import filter_cards, describe_card
from core.loader import HeroLoader
from core.simulator import BattleSimulator


class BattlePlatform:
    """MOBA 英雄大乱斗 — 1v1 对战平台主窗口"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("MOBA 英雄大乱斗 — 1v1 对战平台")
        self.root.geometry("1150x820")
        self.root.configure(bg="#0d1117")

        # 状态变量
        self.heroes_dict = OrderedDict()
        self.card1 = None
        self.card2 = None
        self.battle_log_lines = []
        self.current_line = 0
        self.log_count = 0  # 日志总行数（与动画进度 current_line 解耦，修复快速模拟计数 bug）
        self.is_battling = False
        self.after_id = None
        self.log_y = 10
        self.line_height = 32
        self.simulator = None
        self.all_logs = []
        self.log_lines = []  # 已显示日志的纯文本缓存（供复制/分享）
        self.polish_thread = None  # 日志润色后台线程（避免阻塞 GUI）

        # 筛选状态
        self.game_filter_var = tk.StringVar(value="全部游戏")
        self.role_filter_var = tk.StringVar(value="全部位置")
        self.available_games = []
        self.filtered_dict = OrderedDict()

        # 加载字体
        self._load_fonts()

        # 加载英雄
        self._load_heroes()

        # 创建UI
        self._create_ui()

        # 初始提示
        self._add_log("⚔️  MOBA 英雄大乱斗 — 1v1 对战平台", "#58a6ff")
        self._add_log("选择两位英雄，调整等级（1-18），点击「开始对战」", "#8b949e")
        if self.heroes_dict:
            games = {c.get("game", {}).get("name") for c in self.heroes_dict.values()}
            self._add_log(
                f"已加载 {len(self.heroes_dict)} 位英雄，来自 {len(games)} 款 MOBA 游戏",
                "#8b949e"
            )

    # ── 字体加载 ──────────────────────────────

    def _load_fonts(self):
        """加载中文字体（优先使用项目自带字体，回退到系统字体）"""
        self.available_fonts = []
        font_files = {
            "simhei.ttf": "SimHei",
            "simkai.ttf": "KaiTi",
            "HanChanGaoHeiTi-2.otf": "Chill G Sans Medium",
        }

        for filename, family_name in font_files.items():
            font_path = os.path.join(FONT_DIR, filename)
            if not os.path.exists(font_path):
                continue

            registered = False
            try:
                if sys.platform == "win32":
                    import ctypes
                    FR_PRIVATE = 0x10
                    ctypes.windll.gdi32.AddFontResourceExW(font_path, FR_PRIVATE, 0)
                    ctypes.windll.user32.SendMessageW(0xFFFF, 0x001D, 0, 0)
                    registered = True
            except Exception:
                pass

            if registered:
                self.available_fonts.append(family_name)

        self.fallback_fonts = ["Microsoft YaHei", "SimHei", "SimSun", "KaiTi", "FangSong"]
        if not self.available_fonts:
            self.available_fonts = self.fallback_fonts

        self.primary_font = "Microsoft YaHei"
        for f in self.available_fonts + self.fallback_fonts:
            try:
                test_font = tkfont.Font(family=f, size=10)
                self.primary_font = f
                break
            except Exception:
                continue

        self.default_font = (self.primary_font, 10)
        self.title_font = (self.primary_font, 18, "bold")
        self.header_font = (self.primary_font, 12, "bold")
        self.subtitle_font = (self.primary_font, 9)
        self.small_font = (self.primary_font, 8)
        self.vs_font = (self.primary_font, 16, "bold")

    # ── 英雄加载 ──────────────────────────────

    def _load_heroes(self):
        """加载英雄池"""
        heroes = HeroLoader.load_all_heroes()
        self.heroes_dict = HeroLoader.build_hero_dict(heroes)
        games_set = []
        for card in self.heroes_dict.values():
            game_name = game_cn(card)
            if game_name not in games_set:
                games_set.append(game_name)
        self.available_games = sorted(games_set)

    # ── 界面构建 ──────────────────────────────

    def _create_ui(self):
        """构建界面"""
        main_frame = tk.Frame(self.root, bg="#0d1117")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        # 标题
        title_frame = tk.Frame(main_frame, bg="#161b22", height=50)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        title_frame.pack_propagate(False)
        title = tk.Label(
            title_frame, text="⚔️  MOBA 英雄大乱斗",
            font=self.title_font, fg="#f0f6fc", bg="#161b22"
        )
        title.pack(side=tk.LEFT, padx=20, pady=8)
        subtitle = tk.Label(
            title_frame, text="基于 D&D 5e 数值框架 | 1500+ 真实英雄",
            font=self.subtitle_font, fg="#8b949e", bg="#161b22"
        )
        subtitle.pack(side=tk.RIGHT, padx=20, pady=8)

        # 选择区
        select_frame = tk.Frame(main_frame, bg="#161b22")
        select_frame.pack(fill=tk.X, pady=(0, 10))

        # 筛选栏
        filter_bar = tk.Frame(select_frame, bg="#21262d", height=42)
        filter_bar.pack(fill=tk.X, padx=8, pady=(8, 4))
        filter_bar.pack_propagate(False)

        tk.Label(filter_bar, text="🎮 游戏:", font=self.subtitle_font,
                fg="#8b949e", bg="#21262d").pack(side=tk.LEFT, padx=(12, 4))
        game_values = ["全部游戏"] + self.available_games
        self.game_combo = ttk.Combobox(
            filter_bar, textvariable=self.game_filter_var,
            font=self.default_font, state="readonly", width=14, values=game_values
        )
        self.game_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.game_combo.bind("<<ComboboxSelected>>", self._on_filter_change)

        tk.Label(filter_bar, text="📍 位置:", font=self.subtitle_font,
                fg="#8b949e", bg="#21262d").pack(side=tk.LEFT, padx=(4, 4))
        role_values = ["全部位置"] + list(ROLE_NAME_CN.values())
        self.role_combo = ttk.Combobox(
            filter_bar, textvariable=self.role_filter_var,
            font=self.default_font, state="readonly", width=10, values=role_values
        )
        self.role_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.role_combo.bind("<<ComboboxSelected>>", self._on_filter_change)

        self.filter_count_label = tk.Label(
            filter_bar, text="", font=self.subtitle_font, fg="#58a6ff", bg="#21262d"
        )
        self.filter_count_label.pack(side=tk.LEFT, padx=(4, 0))

        # 搜索框
        tk.Label(filter_bar, text="🔍 搜索:", font=self.subtitle_font,
                fg="#8b949e", bg="#21262d").pack(side=tk.RIGHT, padx=(4, 12))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search)
        self.search_entry = tk.Entry(
            filter_bar, textvariable=self.search_var,
            font=self.default_font, width=14,
            bg="#0d1117", fg="#f0f6fc", insertbackground="#f0f6fc"
        )
        self.search_entry.pack(side=tk.RIGHT, padx=(0, 8))

        # 英雄选择行
        hero_row = tk.Frame(select_frame, bg="#161b22")
        hero_row.pack(fill=tk.X, padx=8, pady=(6, 10))

        # 英雄1
        p1_frame = tk.Frame(hero_row, bg="#161b22")
        p1_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        tk.Label(p1_frame, text="🔴 蓝方英雄", font=self.header_font,
                fg="#f85149", bg="#161b22").pack(anchor=tk.W)
        self.p1_var = tk.StringVar()
        self.p1_combo = ttk.Combobox(
            p1_frame, textvariable=self.p1_var,
            font=self.default_font, state="readonly", width=35
        )
        self.p1_combo.pack(fill=tk.X, pady=5)
        self.p1_combo.bind("<<ComboboxSelected>>", self._on_select_p1)
        self.p1_info = tk.Label(
            p1_frame, text="未选择", font=self.small_font,
            fg="#8b949e", bg="#161b22", justify=tk.LEFT, anchor=tk.W, wraplength=350
        )
        self.p1_info.pack(fill=tk.X, pady=2)

        p1_lvl_frame = tk.Frame(p1_frame, bg="#161b22")
        p1_lvl_frame.pack(fill=tk.X, pady=(2, 0))
        tk.Label(p1_lvl_frame, text="等级:", font=self.subtitle_font,
                fg="#8b949e", bg="#161b22").pack(side=tk.LEFT)
        self.p1_level_var = tk.IntVar(value=1)
        self.p1_level_spin = tk.Spinbox(
            p1_lvl_frame, from_=1, to=18, textvariable=self.p1_level_var,
            font=self.subtitle_font, width=4, bg="#21262d", fg="#f0f6fc",
            buttonbackground="#30363d", command=self._on_level_change
        )
        self.p1_level_spin.pack(side=tk.LEFT, padx=5)

        # VS
        vs_frame = tk.Frame(hero_row, bg="#161b22", width=80)
        vs_frame.pack(side=tk.LEFT, pady=30)
        vs_frame.pack_propagate(False)
        tk.Label(vs_frame, text="⚡VS⚡", font=self.vs_font,
                fg="#d2a8ff", bg="#161b22").pack(expand=True)

        # 英雄2
        p2_frame = tk.Frame(hero_row, bg="#161b22")
        p2_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        tk.Label(p2_frame, text="🔵 红方英雄", font=self.header_font,
                fg="#58a6ff", bg="#161b22").pack(anchor=tk.W)
        self.p2_var = tk.StringVar()
        self.p2_combo = ttk.Combobox(
            p2_frame, textvariable=self.p2_var,
            font=self.default_font, state="readonly", width=35
        )
        self.p2_combo.pack(fill=tk.X, pady=5)
        self.p2_combo.bind("<<ComboboxSelected>>", self._on_select_p2)
        self.p2_info = tk.Label(
            p2_frame, text="未选择", font=self.small_font,
            fg="#8b949e", bg="#161b22", justify=tk.LEFT, anchor=tk.W, wraplength=350
        )
        self.p2_info.pack(fill=tk.X, pady=2)

        p2_lvl_frame = tk.Frame(p2_frame, bg="#161b22")
        p2_lvl_frame.pack(fill=tk.X, pady=(2, 0))
        tk.Label(p2_lvl_frame, text="等级:", font=self.subtitle_font,
                fg="#8b949e", bg="#161b22").pack(side=tk.LEFT)
        self.p2_level_var = tk.IntVar(value=1)
        self.p2_level_spin = tk.Spinbox(
            p2_lvl_frame, from_=1, to=18, textvariable=self.p2_level_var,
            font=self.subtitle_font, width=4, bg="#21262d", fg="#f0f6fc",
            buttonbackground="#30363d", command=self._on_level_change
        )
        self.p2_level_spin.pack(side=tk.LEFT, padx=5)

        # 按钮区
        btn_frame = tk.Frame(main_frame, bg="#0d1117")
        btn_frame.pack(fill=tk.X, pady=(0, 8))

        self.btn_battle = tk.Button(
            btn_frame, text="⚔️  开始对战", command=self._start_battle,
            font=self.header_font, bg="#238636", fg="white",
            activebackground="#2ea043", relief=tk.FLAT, padx=30, pady=6,
            cursor="hand2", state=tk.DISABLED
        )
        self.btn_battle.pack(side=tk.LEFT, padx=5)

        self.btn_random = tk.Button(
            btn_frame, text="🎲 随机英雄", command=self._random_heroes,
            font=self.default_font, bg="#21262d", fg="#f0f6fc",
            relief=tk.FLAT, padx=20, pady=6, cursor="hand2"
        )
        self.btn_random.pack(side=tk.LEFT, padx=5)

        btn_speed = tk.Button(
            btn_frame, text="⏩ 快速模拟(无动画)", command=self._quick_sim,
            font=self.default_font, bg="#21262d", fg="#f0f6fc",
            relief=tk.FLAT, padx=12, pady=6, cursor="hand2"
        )
        btn_speed.pack(side=tk.LEFT, padx=5)

        self.btn_clear = tk.Button(
            btn_frame, text="🗑️ 清空日志", command=self._clear_log,
            font=self.default_font, bg="#21262d", fg="#f0f6fc",
            relief=tk.FLAT, padx=20, pady=6, cursor="hand2"
        )
        self.btn_clear.pack(side=tk.RIGHT, padx=5)

        self.btn_copy = tk.Button(
            btn_frame, text="📋 复制日志", command=self._copy_log,
            font=self.default_font, bg="#21262d", fg="#f0f6fc",
            relief=tk.FLAT, padx=16, pady=6, cursor="hand2"
        )
        self.btn_copy.pack(side=tk.RIGHT, padx=5)

        self.btn_save = tk.Button(
            btn_frame, text="💾 保存日志", command=self._save_log,
            font=self.default_font, bg="#21262d", fg="#f0f6fc",
            relief=tk.FLAT, padx=16, pady=6, cursor="hand2"
        )
        self.btn_save.pack(side=tk.RIGHT, padx=5)

        # 速度控制
        tk.Label(btn_frame, text="速度:", font=self.subtitle_font,
                fg="#8b949e", bg="#0d1117").pack(side=tk.RIGHT, padx=(15, 2))
        self.speed_var = tk.DoubleVar(value=0.4)
        speed_scale = tk.Scale(
            btn_frame, from_=0.1, to=1.5, resolution=0.1,
            variable=self.speed_var, orient=tk.HORIZONTAL, length=100,
            bg="#21262d", fg="#f0f6fc", highlightthickness=0,
            troughcolor="#30363d", activebackground="#238636"
        )
        speed_scale.pack(side=tk.RIGHT, padx=2)

        # 战斗日志区
        log_frame = tk.Frame(main_frame, bg="#161b22")
        log_frame.pack(fill=tk.BOTH, expand=True)

        log_label_frame = tk.Frame(log_frame, bg="#161b22")
        log_label_frame.pack(fill=tk.X, padx=10, pady=(8, 0))
        tk.Label(log_label_frame, text="📜 战斗日志", font=self.header_font,
                fg="#f0f6fc", bg="#161b22").pack(side=tk.LEFT)
        self.log_count_label = tk.Label(
            log_label_frame, text="", font=self.subtitle_font, fg="#8b949e", bg="#161b22"
        )
        self.log_count_label.pack(side=tk.RIGHT)

        # 日志润色入口（把当前战斗日志改写为港漫风武侠短篇）
        self.btn_polish = tk.Button(
            log_label_frame, text="✨ 日志润色", command=self._polish_log,
            font=self.default_font, bg="#6e40c9", fg="white",
            activebackground="#8957e5", relief=tk.FLAT, padx=14, pady=4,
            cursor="hand2", state=tk.DISABLED
        )
        self.btn_polish.pack(side=tk.RIGHT, padx=(5, 12))

        # DeepSeek API Key 设置入口（key 仅存本地私人令牌.txt，不入库）
        self.btn_key = tk.Button(
            log_label_frame, text="🔑 密钥", command=self._open_key_settings,
            font=self.default_font, bg="#30363d", fg="#f0f6fc",
            activebackground="#484f58", relief=tk.FLAT, padx=10, pady=4,
            cursor="hand2"
        )
        self.btn_key.pack(side=tk.RIGHT, padx=(5, 0))

        self.polish_master_var = tk.StringVar(value="随机风格")
        self.polish_master_combo = ttk.Combobox(
            log_label_frame, textvariable=self.polish_master_var,
            font=self.default_font, state="readonly", width=12,
            values=["随机风格"]
        )
        self.polish_master_combo.pack(side=tk.RIGHT, padx=4)

        canvas_frame = tk.Frame(log_frame, bg="#0d1117")
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        self.canvas = tk.Canvas(canvas_frame, bg="#0d1117", highlightthickness=0)
        self.scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)

        # 初始化筛选
        self._apply_filters()

    # ── 筛选逻辑 ──────────────────────────────

    def _apply_filters(self, base_dict=None):
        """应用游戏+位置+搜索三层过滤（纯逻辑下沉至 core.catalog.filter_cards）"""
        base = base_dict or self.heroes_dict
        self.filtered_dict = filter_cards(
            base,
            self.game_filter_var.get(),
            self.role_filter_var.get(),
            self.search_var.get(),
        )

        names = list(self.filtered_dict.keys())
        self.p1_combo["values"] = names
        self.p2_combo["values"] = names

        total = len(base) if base else len(self.heroes_dict)
        self.filter_count_label.config(text=f"({len(self.filtered_dict)}/{total})")

        if self.p1_var.get() not in self.filtered_dict:
            self.p1_var.set("")
            self.card1 = None
            self.p1_info.config(text="未选择")
        if self.p2_var.get() not in self.filtered_dict:
            self.p2_var.set("")
            self.card2 = None
            self.p2_info.config(text="未选择")
        self._check_ready()

    def _on_filter_change(self, event=None):
        self._apply_filters()

    def _on_search(self, *args):
        self._apply_filters()

    # ── 英雄选择 ──────────────────────────────

    def _get_card_info(self, card: dict, level: int = 1) -> str:
        """获取英雄信息摘要（按等级显示）—— 逻辑下沉至 core.catalog.describe_card"""
        return describe_card(card, level)

    def _on_select_p1(self, event=None):
        key = self.p1_var.get()
        self.card1 = self.heroes_dict.get(key)
        self._refresh_p1_info()
        self._check_ready()

    def _on_select_p2(self, event=None):
        key = self.p2_var.get()
        self.card2 = self.heroes_dict.get(key)
        self._refresh_p2_info()
        self._check_ready()

    def _on_level_change(self):
        self._refresh_p1_info()
        self._refresh_p2_info()

    def _refresh_p1_info(self):
        if self.card1:
            lv = self.p1_level_var.get()
            self.p1_info.config(text=self._get_card_info(self.card1, lv))

    def _refresh_p2_info(self):
        if self.card2:
            lv = self.p2_level_var.get()
            self.p2_info.config(text=self._get_card_info(self.card2, lv))

    def _check_ready(self):
        if self.card1 and self.card2:
            self.btn_battle.config(state=tk.NORMAL)
        else:
            self.btn_battle.config(state=tk.DISABLED)

    # ── 随机英雄 ──────────────────────────────

    def _random_heroes(self):
        """随机选择两位英雄（在筛选结果内）"""
        pool = self.filtered_dict if self.filtered_dict else self.heroes_dict
        if not pool:
            return
        keys = list(pool.keys())
        if len(keys) < 2:
            return

        p1_key = random.choice(keys)
        remaining = [k for k in keys if k != p1_key]
        p2_key = random.choice(remaining)

        self.p1_var.set(p1_key)
        self._on_select_p1()
        self.p2_var.set(p2_key)
        self._on_select_p2()

        self._add_log("🎲 随机选择英雄", "#d2a8ff")

    # ── 对战流程 ──────────────────────────────

    def _start_battle(self):
        """开始对战（带动画）"""
        if self.is_battling or not self.card1 or not self.card2:
            return

        lv1 = self.p1_level_var.get()
        lv2 = self.p2_level_var.get()

        self.is_battling = True
        self.btn_battle.config(state=tk.DISABLED, text="⚔️  对战中...")
        self._clear_log()

        self.simulator = BattleSimulator(self.card1, self.card2, lv1, lv2)

        self._add_log("═" * 60, "#30363d")
        self._add_log(
            f"⚔️  Lv.{lv1} {self.card1['hero']['name']}  VS  Lv.{lv2} {self.card2['hero']['name']}",
            "#f0f6fc"
        )
        self._add_log(
            f"   [{self.card1['game']['role_name']}] "
            f"生命:{self.simulator.max_hp1}  攻击:{self.simulator.stats1['physical_atk']}  "
            f"法强:{self.simulator.stats1['magic_power']}  护甲:{self.simulator.stats1['ac']}",
            "#8b949e"
        )
        self._add_log(
            f"   [{self.card2['game']['role_name']}] "
            f"生命:{self.simulator.max_hp2}  攻击:{self.simulator.stats2['physical_atk']}  "
            f"法强:{self.simulator.stats2['magic_power']}  护甲:{self.simulator.stats2['ac']}",
            "#8b949e"
        )
        self._add_log("═" * 60, "#30363d")

        # 预生成全部日志
        self.all_logs = []
        max_turns = 50
        try:
            for _ in range(max_turns):
                logs = self.simulator.execute_turn()
                self.all_logs.extend(logs)
                if "被击败" in " ".join(logs):
                    break
        except Exception as e:
            # 防御性兜底：任何对战异常都不应击穿 GUI（事故 SEV-2 止血 A1）
            self._add_log(f"⚠️ 对战异常（已拦截，不影响界面）: {e}", "#f85149")
            self.is_battling = False
            self.btn_battle.config(state=tk.NORMAL, text="⚔️  开始对战")
            return

        self.current_line = 0
        self._animate()

    def _quick_sim(self):
        """快速模拟（无动画）"""
        if not self.card1 or not self.card2:
            return

        lv1 = self.p1_level_var.get()
        lv2 = self.p2_level_var.get()
        sim = BattleSimulator(self.card1, self.card2, lv1, lv2)
        self._clear_log()

        self._add_log("═" * 60, "#30363d")
        self._add_log(
            f"⚡ 快速模拟: Lv.{lv1} {self.card1['hero']['name']} VS Lv.{lv2} {self.card2['hero']['name']}",
            "#d2a8ff"
        )
        self._add_log(
            f"   [{self.card1['game']['role_name']}] "
            f"生命:{sim.max_hp1}  攻击:{sim.stats1['physical_atk']}  "
            f"法强:{sim.stats1['magic_power']}  护甲:{sim.stats1['ac']}",
            "#8b949e"
        )
        self._add_log(
            f"   [{self.card2['game']['role_name']}] "
            f"生命:{sim.max_hp2}  攻击:{sim.stats2['physical_atk']}  "
            f"法强:{sim.stats2['magic_power']}  护甲:{sim.stats2['ac']}",
            "#8b949e"
        )
        self._add_log("═" * 60, "#30363d")

        max_turns = 50
        try:
            for _ in range(max_turns):
                logs = sim.execute_turn()
                for log in logs:
                    if "被击败" in log or "胜利" in log:
                        self._add_log(log, "#ffa657" if "胜利" in log else "#f85149")
                    else:
                        self._add_log(log, "#e6edf3")
                if "被击败" in " ".join(logs):
                    break
        except Exception as e:
            # 防御性兜底：任何对战异常都不应击穿 GUI（事故 SEV-2 止血 A1）
            self._add_log(f"⚠️ 对战异常（已拦截，不影响界面）: {e}", "#f85149")
            return

    def _animate(self):
        """逐行动画"""
        if self.current_line < len(self.all_logs):
            line = self.all_logs[self.current_line]

            if "被击败" in line:
                color = "#ff7b72"
            elif "胜利" in line:
                color = "#d2a8ff"
            elif "暴击" in line:
                color = "#ffa657"
            elif "恢复" in line:
                color = "#7ee787"
            elif line.startswith("回合"):
                color = "#e6edf3"
            else:
                color = "#c9d1d9"

            self._add_log(line, color)
            self.current_line += 1

            speed_ms = int(self.speed_var.get() * 1000)
            self.after_id = self.root.after(speed_ms, self._animate)
        else:
            self._on_battle_end()

    def _on_battle_end(self):
        """对战结束"""
        self.is_battling = False
        self.btn_battle.config(state=tk.NORMAL, text="⚔️  开始对战")
        self._add_log("═" * 60, "#30363d")

    # ── 日志 ──────────────────────────────────

    def _add_log(self, text: str, color: str = "#c9d1d9"):
        """Canvas 添加日志行"""
        self.log_lines.append(text)
        self.canvas.create_text(
            10, self.log_y, anchor="nw", text=text,
            fill=color, font=self.default_font
        )
        self.log_y += self.line_height
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        self.canvas.yview_moveto(1)
        self.log_count += 1
        self.log_count_label.config(text=f"共 {self.log_count} 行")
        # 有日志后开放「日志润色」入口
        if self.btn_polish["state"] == tk.DISABLED:
            self.btn_polish.config(state=tk.NORMAL)

    def _clear_log(self):
        """清空日志"""
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        self.is_battling = False
        self.btn_battle.config(
            state=tk.NORMAL if self.card1 and self.card2 else tk.DISABLED,
            text="⚔️  开始对战"
        )
        self.canvas.delete("all")
        self.log_y = 10
        self.all_logs = []
        self.log_lines = []
        self.current_line = 0
        self.log_count = 0
        self.log_count_label.config(text="")
        # 清空日志后关闭「日志润色」入口
        self.btn_polish.config(state=tk.DISABLED)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ── 日志复制 / 分享 ──────────────────────

    def _copy_log(self):
        """复制全部日志文本到剪贴板"""
        if not self.log_lines:
            self._add_log("⚠️ 暂无日志可复制", "#f85149")
            return
        text = "\n".join(self.log_lines)
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self._add_log(f"📋 已复制 {len(self.log_lines)} 行日志到剪贴板", "#7ee787")
        except Exception as e:
            self._add_log(f"⚠️ 复制失败: {e}", "#f85149")

    def _save_log(self):
        """将日志保存为文本文件（分享用），固定写入 SAVE_DIR"""
        if not self.log_lines:
            self._add_log("⚠️ 暂无日志可保存", "#f85149")
            return
        from datetime import datetime
        try:
            os.makedirs(SAVE_DIR, exist_ok=True)
            default_name = f"battle_log_{datetime.now():%Y%m%d_%H%M%S}.txt"
            path = os.path.join(SAVE_DIR, default_name)
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(self.log_lines))
            self._add_log(f"💾 日志已保存: {path}", "#7ee787")
        except Exception as e:
            self._add_log(f"⚠️ 保存失败: {e}", "#f85149")
        except Exception as e:
            self._add_log(f"⚠️ 保存失败: {e}", "#f85149")

    # ── 日志润色 ──────────────────────────────

    def _open_key_settings(self):
        """打开 DeepSeek API Key 设置弹窗（key 仅保存到本地私人令牌.txt）。"""
        try:
            log_polish = self._ensure_polish_imports()
        except Exception as e:
            self._add_log(f"⚠️ 润色模块加载失败: {e}", "#f85149")
            return

        cur_key, cur_model = log_polish.load_token_file()
        win = tk.Toplevel(self.root)
        win.title("🔑 DeepSeek API Key 设置")
        win.geometry("560x320")
        win.configure(bg="#0d1117")
        try:
            win.transient(self.root)
            win.grab_set()
        except Exception:
            pass

        tip = ("API Key 仅保存在本地文件「私人令牌.txt」（已被 .gitignore 忽略，"
               "不会进入代码或仓库）。\n可在 DeepSeek 开放平台申请。")
        tk.Label(win, text=tip, font=self.subtitle_font, fg="#8b949e",
                 bg="#0d1117", justify=tk.LEFT, wraplength=520).pack(
            anchor=tk.W, padx=16, pady=(14, 8))

        row1 = tk.Frame(win, bg="#0d1117")
        row1.pack(fill=tk.X, padx=16, pady=4)
        tk.Label(row1, text="API Key", font=self.default_font, fg="#f0f6fc",
                 bg="#0d1117", width=12, anchor=tk.W).pack(side=tk.LEFT)
        key_var = tk.StringVar(value=cur_key or "")
        key_entry = tk.Entry(row1, textvariable=key_var, font=self.default_font,
                             show="•", bg="#161b22", fg="#f0f6fc",
                             insertbackground="#f0f6fc", relief=tk.FLAT)
        key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        show_var = tk.BooleanVar(value=False)

        def _toggle_show():
            key_entry.config(show="" if show_var.get() else "•")

        tk.Checkbutton(row1, text="显示明文", variable=show_var,
                       command=_toggle_show, font=self.subtitle_font,
                       fg="#8b949e", bg="#0d1117", selectcolor="#161b22",
                       activebackground="#0d1117").pack(side=tk.LEFT)

        row2 = tk.Frame(win, bg="#0d1117")
        row2.pack(fill=tk.X, padx=16, pady=4)
        tk.Label(row2, text="模型名", font=self.default_font, fg="#f0f6fc",
                 bg="#0d1117", width=12, anchor=tk.W).pack(side=tk.LEFT)
        model_var = tk.StringVar(value=cur_model or "deepseek-v4-pro")
        tk.Entry(row2, textvariable=model_var, font=self.default_font,
                 bg="#161b22", fg="#f0f6fc", insertbackground="#f0f6fc",
                 relief=tk.FLAT).pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn_bar = tk.Frame(win, bg="#0d1117")
        btn_bar.pack(fill=tk.X, padx=16, pady=(14, 0))

        def _save():
            key = key_var.get().strip()
            model = model_var.get().strip() or "deepseek-v4-pro"
            if not key:
                self._add_log("⚠️ API Key 不能为空", "#f85149")
                return
            try:
                log_polish.save_token_file(key, model)
            except Exception as e:
                self._add_log(f"⚠️ 保存 API Key 失败: {e}", "#f85149")
                return
            self._add_log("🔑 API Key 已保存到本地「私人令牌.txt」（不入库）", "#7ee787")
            win.destroy()

        tk.Button(btn_bar, text="保存", command=_save, font=self.default_font,
                  bg="#238636", fg="white", activebackground="#2ea043",
                  relief=tk.FLAT, padx=18, pady=4, cursor="hand2").pack(side=tk.RIGHT)
        tk.Button(btn_bar, text="取消", command=win.destroy, font=self.default_font,
                  bg="#30363d", fg="#f0f6fc", activebackground="#484f58",
                  relief=tk.FLAT, padx=18, pady=4, cursor="hand2").pack(
            side=tk.RIGHT, padx=(0, 8))

    def _ensure_polish_imports(self):
        """懒加载日志润色依赖（tools 不在默认路径，且需避免阻塞启动）"""
        if getattr(self, "_log_polish_mod", None) is None:
            # ui.py 位于 <root>/ui/ui.py，项目根为 ui 目录的上级
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            sys.path.insert(0, project_root)  # 使 tools 作为 namespace 包可导入
            import tools.log_polish as log_polish  # noqa: E402
            from tools.hk_comic_styles import list_master_names  # noqa: E402
            self._log_polish_mod = log_polish
            self._polish_master_names = list_master_names()
            # 填充风格下拉框
            names = ["随机风格"] + self._polish_master_names
            self.polish_master_combo.config(values=names)
            if self.polish_master_var.get() not in names:
                self.polish_master_var.set("随机风格")
        return self._log_polish_mod

    def _polish_log(self):
        """将当前战斗日志润色为港漫风武侠短篇（在线润色，后台执行避免卡界面）"""
        if not self.log_lines:
            self._add_log("⚠️ 暂无可润色的战斗日志，请先开始一场对战", "#f85149")
            return
        if self.polish_thread and self.polish_thread.is_alive():
            return  # 润色进行中，忽略重复点击

        try:
            log_polish = self._ensure_polish_imports()
        except Exception as e:
            self._add_log(f"⚠️ 润色模块加载失败: {e}", "#f85149")
            return

        master_sel = self.polish_master_var.get()
        master = None if master_sel == "随机风格" else master_sel

        # 适配 log_polish 期望的「单场」日志格式（以【第 N/M 场】起头）
        raw_log = "\n".join(self.log_lines)
        styled_input = "【第 1/1 场】\n" + raw_log

        # 凭据优先级：环境变量 / 私人令牌.txt / 内置默认值
        try:
            api_key, model = log_polish.resolve_credentials()
        except Exception as e:
            self.btn_polish.config(state=tk.NORMAL, text="✨ 日志润色")
            self._add_log(f"⚠️ 读取润色凭据失败: {e}", "#f85149")
            return

        if not api_key:
            # 未配置 API Key：引导到设置弹窗，而不是发起必然失败的请求
            self._add_log("⚠️ 尚未配置 DeepSeek API Key，请先在设置弹窗中填入", "#f85149")
            self._open_key_settings()
            return

        self._add_log("✨ 正在润色日志（港漫风武侠短篇），请稍候…", "#d2a8ff")
        self.btn_polish.config(state=tk.DISABLED, text="✨ 润色中…")

        def _worker():
            try:
                # polish_match 期望 match 为 dict（含 index/header/body），
                # 需先按【第 N/M 场】切分出单场结构，不能直接传原始字符串。
                matches = log_polish.split_matches(styled_input)
                if not matches:
                    raise ValueError("未能从当前日志中解析出可润色的场次")
                result = log_polish.polish_match(
                    matches[0], api_key, master=master, model=model)
                self.root.after(0, self._show_polish_result, result, master_sel)
            except Exception as e:
                # 原样展示真实错误，便于排查（网络/鉴权/模型名等）
                self.root.after(0, self._on_polish_error, str(e))

        self.polish_thread = threading.Thread(target=_worker, daemon=True)
        self.polish_thread.start()

    def _on_polish_error(self, msg: str):
        self.btn_polish.config(state=tk.NORMAL, text="✨ 日志润色")
        self._add_log(f"⚠️ 日志润色失败: {msg}", "#f85149")

    def _show_polish_result(self, result, master_sel: str):
        self.btn_polish.config(state=tk.NORMAL, text="✨ 日志润色")
        # polish_match 返回 dict，润色正文在 result["story"]；兼容直接返回字符串的情况
        if isinstance(result, dict):
            story = result.get("story") or result.get("text") or ""
            master_used = result.get("master") or master_sel
            works = result.get("works", "")
            self._add_log(
                f"✅ 日志润色完成（风格：{master_used}，{len(story)} 字），已弹出预览窗口",
                "#7ee787")
            self._open_polish_window(story, master_used, works)
        else:
            self._add_log("✅ 日志润色完成，已弹出预览窗口", "#7ee787")
            self._open_polish_window(str(result), master_sel, "")

    def _open_polish_window(self, result: str, master_sel: str, works: str = ""):
        """弹出润色结果预览窗口（支持复制/保存）"""
        self.polish_result = result  # 缓存，供保存/复制闭包使用
        win = tk.Toplevel(self.root)
        win.title("✨ 日志润色 · 港漫风武侠短篇")
        win.geometry("720x560")
        win.configure(bg="#0d1117")
        try:
            win.transient(self.root)
            win.grab_set()
        except Exception:
            pass

        header = tk.Frame(win, bg="#161b22")
        header.pack(fill=tk.X, padx=12, pady=(12, 6))
        tk.Label(header, text=f"风格：{master_sel}",
                font=self.header_font, fg="#d2a8ff", bg="#161b22").pack(side=tk.LEFT)
        if works:
            tk.Label(header, text=f"· {works}", font=self.subtitle_font,
                    fg="#8b949e", bg="#161b22").pack(side=tk.LEFT, padx=(8, 0))

        btn_bar = tk.Frame(win, bg="#0d1117")
        btn_bar.pack(fill=tk.X, padx=12, pady=(0, 6))

        def _copy():
            try:
                win.clipboard_clear()
                win.clipboard_append(self.polish_result)
                _flash("📋 已复制")
            except Exception as e:
                import traceback
                traceback.print_exc()
                self._add_log(f"⚠️ 复制失败: {e}", "#f85149")
                _flash(f"⚠️ 复制失败: {e}")

        def _save():
            from datetime import datetime
            import traceback
            try:
                os.makedirs(SAVE_DIR, exist_ok=True)
                default_name = f"polished_log_{datetime.now():%Y%m%d_%H%M%S}.txt"
                path = os.path.join(SAVE_DIR, default_name)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.polish_result)
                self._add_log(f"💾 润色日志已保存: {path}", "#7ee787")
                _flash(f"💾 已保存: {os.path.basename(path)}")
            except Exception as e:
                traceback.print_exc()
                self._add_log(f"⚠️ 润色日志保存失败: {e}", "#f85149")
                _flash(f"⚠️ 保存失败: {e}")

        status_var = tk.StringVar(value="")
        def _flash(text):
            status_var.set(text)
            win.after(2000, lambda: status_var.set(""))

        tk.Button(btn_bar, text="📋 复制", command=_copy,
                font=self.default_font, bg="#238636", fg="white",
                activebackground="#2ea043", relief=tk.FLAT, padx=14, pady=4,
                cursor="hand2").pack(side=tk.LEFT, padx=4)
        tk.Button(btn_bar, text="💾 保存", command=_save,
                font=self.default_font, bg="#1f6feb", fg="white",
                activebackground="#388bfd", relief=tk.FLAT, padx=14, pady=4,
                cursor="hand2").pack(side=tk.LEFT, padx=4)
        tk.Label(btn_bar, textvariable=status_var,
                font=self.subtitle_font, fg="#7ee787", bg="#0d1117").pack(
                side=tk.LEFT, padx=8)

        text_frame = tk.Frame(win, bg="#0d1117")
        text_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        txt = tk.Text(text_frame, wrap=tk.WORD, bg="#161b22", fg="#e6edf3",
                    font=self.default_font, relief=tk.FLAT, padx=14, pady=12,
                    insertbackground="#e6edf3")
        txt.insert("1.0", result)
        txt.config(state=tk.DISABLED)
        txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll = tk.Scrollbar(text_frame, command=txt.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        txt.config(yscrollcommand=scroll.set)

        win.update_idletasks()
        win.minsize(520, 400)
