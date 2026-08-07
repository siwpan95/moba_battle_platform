#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MOBA 英雄角色卡生成器
基于 D&D 5e 数值框架 + 英雄池角色分析数据
为 16 款游戏 1503 位英雄每人生成一张完整角色卡 JSON
"""

import json
import os
import sys
import random
import math
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

# 英雄名中文化映射
try:
    from hero_name_mapping import HERO_NAME_CN
except ImportError:
    HERO_NAME_CN = {}

# ==========================================
# 路径配置
# ==========================================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 让 tools 脚本能导入 core 包（与 main.py / hero_calculator.py 一致）
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# 游戏注册表 / 汉化表 / 平衡参数 单一真相，从 core.config 导入，避免与本地重复定义漂移
from core.config import GAME_NAME_CN, REGISTRY_BY_DISPLAY, REGISTRY_BY_ID, HP_SCALE
from core import schema

INPUT_JSON = os.path.join(PROJECT_ROOT, "data", "analysis", "all_heroes_unified.json")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "character_cards")


def _slugify(name: str) -> str:
    """通用 slug 兜底：未登记游戏时按旧规则推导小写目录名。"""
    return name.replace(" ", "_").replace("/", "_").replace(":", "").replace("\\", "_")

# ==========================================
# D&D 5e 核心常量
# ==========================================
ABILITY_NAMES = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
ABILITY_CN = {"STR": "力量", "DEX": "敏捷", "CON": "体质", "INT": "智力", "WIS": "感知", "CHA": "魅力"}

# 游戏名汉化：GAME_NAME_CN 现已从 core.config 导入（单一真相），此处不再重复定义
# HP 缩放倍率（D&D血量→MOBA血量）单一真相见 core.balance.HP_SCALE（已随 core.config 导入）

def ability_mod(score): return (score - 10) // 2

PROF_BONUS = {1:2,2:2,3:2,4:2, 5:3,6:3,7:3,8:3, 9:4,10:4,11:4,12:4, 13:5,14:5,15:5,16:5, 17:6,18:6}

CLASS_DEF = {
    "tank":     {"hit_die": 12, "hp_per_lvl": 7,  "armor": 2, "primary": ("STR","CON"), "save": ("STR","CON")},
    "fighter":  {"hit_die": 10, "hp_per_lvl": 6,  "armor": 3, "primary": ("STR","DEX"), "save": ("STR","CON")},
    "assassin": {"hit_die": 8,  "hp_per_lvl": 5,  "armor": 1, "primary": ("DEX",),      "save": ("DEX","INT")},
    "mage":     {"hit_die": 6,  "hp_per_lvl": 4,  "armor": 0, "primary": ("INT",),      "save": ("INT","WIS")},
    "marksman": {"hit_die": 10, "hp_per_lvl": 6,  "armor": 3, "primary": ("DEX","WIS"), "save": ("STR","DEX")},
    "support":  {"hit_die": 8,  "hp_per_lvl": 5,  "armor": 2, "primary": ("WIS","CHA"), "save": ("WIS","CHA")},
}

# 角色定位的中英文对照
ROLE_CN = {"tank": "坦克", "fighter": "战士", "assassin": "刺客", "mage": "法师", "marksman": "射手", "support": "辅助"}
ROLE_DND = {"tank": "野蛮人", "fighter": "战士", "assassin": "游荡者", "mage": "法师", "marksman": "游侠", "support": "牧师"}

# ==========================================
# D&D 5e 属性生成 —— 严格遵循车卡流程
# ==========================================

# 购点花费表（最终值 → 花费）
POINT_BUY_COST = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
POINT_BUY_MAX = 27

# 标准数组（不花点数，公平分配）
STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]

# 六大职业的属性优先级（标准数组按此顺序分配高→低）
ROLE_STANDARD_ARRAY = {
    # 15→主属性一, 14→主属性二, 13→体质/副属性, 12→副属性, 10→副属性, 8→短板
    "tank":     {"STR": 15, "CON": 14, "WIS": 13, "DEX": 12, "CHA": 10, "INT": 8},
    "fighter":  {"STR": 15, "DEX": 14, "CON": 13, "WIS": 12, "CHA": 10, "INT": 8},
    "assassin": {"DEX": 15, "CHA": 14, "CON": 13, "STR": 12, "WIS": 10, "INT": 8},
    "mage":     {"INT": 15, "WIS": 14, "CON": 13, "DEX": 12, "CHA": 10, "STR": 8},
    "marksman": {"DEX": 15, "WIS": 14, "CON": 13, "STR": 12, "CHA": 10, "INT": 8},
    "support":  {"CHA": 15, "WIS": 14, "CON": 13, "DEX": 12, "STR": 10, "INT": 8},
}

# 种族加值（在主属性上 +2/+1，模拟 D&D 种族选择）
RACIAL_BONUS = {
    "tank":     {"STR": 2, "CON": 2},
    "fighter":  {"STR": 2, "DEX": 1},
    "assassin": {"DEX": 2, "CHA": 1},
    "mage":     {"INT": 2, "WIS": 1},
    "marksman": {"DEX": 2, "WIS": 1},
    "support":  {"WIS": 1, "CHA": 2},
}

# 购点模板（用于非标准数组的细粒度分配，每种职业27点最优解）
ROLE_TEMPLATES = {
    "tank":     {"STR": 15, "DEX": 10, "CON": 15, "INT": 8,  "WIS": 10, "CHA": 10},
    "fighter":  {"STR": 15, "DEX": 12, "CON": 14, "INT": 8,  "WIS": 10, "CHA": 8},
    "assassin": {"STR": 10, "DEX": 15, "CON": 12, "INT": 8,  "WIS": 10, "CHA": 13},
    "mage":     {"STR": 8,  "DEX": 10, "CON": 12, "INT": 15, "WIS": 13, "CHA": 10},
    "marksman": {"STR": 8,  "DEX": 15, "CON": 14, "INT": 8,  "WIS": 12, "CHA": 10},
    "support":  {"STR": 10, "DEX": 10, "CON": 14, "INT": 8,  "WIS": 13, "CHA": 15},
}


def validate_point_buy(scores: dict) -> tuple:
    """校验购点合法性，返回 (总花费, 是否合法, 违规项列表)"""
    violations = []
    total = 0
    for attr in ABILITY_NAMES:
        val = scores.get(attr, 8)
        if val < 8:
            violations.append(f"{attr}={val}<8")
        elif val > 15:
            violations.append(f"{attr}={val}>15")
        cost = POINT_BUY_COST.get(val)
        if cost is None:
            violations.append(f"{attr}={val}不在购点表")
        else:
            total += cost
    if total > POINT_BUY_MAX:
        violations.append(f"总花费{total}>{POINT_BUY_MAX}")
    return total, len(violations) == 0, violations


def generate_abilities(role: str, method: str = "standard_array") -> dict:
    """
    D&D 5e 车卡核心：生成六维属性值。

    方法:
      - standard_array: 标准数组 [15,14,13,12,10,8]，按角色优先级分配（零随机，严格合规）
      - point_buy: 27点购点，从角色模板微调，允许主属性间小幅度交换
      - roll: 4d6 取最高3个 ×6 次（真·D&D 风味）
    """
    if method == "standard_array":
        base = ROLE_STANDARD_ARRAY.get(role, ROLE_STANDARD_ARRAY["fighter"]).copy()
        # 标准数组不做任何调整 → 保证严格合规
        return base

    elif method == "point_buy":
        template = ROLE_TEMPLATES.get(role, ROLE_TEMPLATES["fighter"])
        base = template.copy()
        cost, valid, violations = validate_point_buy(base)
        if not valid:
            base = ROLE_STANDARD_ARRAY.get(role, ROLE_STANDARD_ARRAY["fighter"]).copy()
        else:
            # 购点允许在两主属性间微调 ±1（保持花费不变）
            primary = CLASS_DEF.get(role, CLASS_DEF["fighter"])["primary"]
            if len(primary) >= 2 and random.random() < 0.4:
                a, b = primary[0], primary[1]
                if random.random() < 0.5:
                    base[a] = min(15, base[a] + 1)
                    base[b] = max(8, base[b] - 1)
                else:
                    base[b] = min(15, base[b] + 1)
                    base[a] = max(8, base[a] - 1)
        return base

    elif method == "roll":
        rolls = sorted(
            [sum(sorted([random.randint(1, 6) for _ in range(4)])[1:]) for _ in range(6)],
            reverse=True
        )
        priority = list(ROLE_STANDARD_ARRAY.get(role, ROLE_STANDARD_ARRAY["fighter"]).keys())
        base = {attr: rolls[i] for i, attr in enumerate(priority)}
        return base

    else:
        return ROLE_STANDARD_ARRAY.get(role, ROLE_STANDARD_ARRAY["fighter"]).copy()

# ==========================================
# 技能数据加载（从 skills/*.json 按需加载，不再内联在源码中）
# ==========================================
SKILLS_DIR = os.path.join(PROJECT_ROOT, "data", "skills")

# 技能文件统一用 game_id（小写 slug）定位 skills/<game_id>.json，
# 不再维护 display→stem 硬编码表；显示名 → game_id 由 REGISTRY_BY_DISPLAY 派生。
_skill_cache = {}
_template_cache = None


def _skill_file_stem(game: str) -> str:
    """技能文件 stem = game_id；未登记游戏回退到小写 slug 推导（兼容新游戏）。"""
    gid = REGISTRY_BY_DISPLAY.get(game)
    if gid:
        return gid
    return _slugify(game).lower()


def _load_skill_json(game: str) -> dict:
    """按需加载单个游戏的技能数据。

    优先从技能池目录 data/skills/<game_id>/ 读取（每英雄一个文件），
    合并为 {英雄名: skills} 返回；若该游戏尚未迁移为池，则回退旧大文件
    data/skills/<game_id>.json。
    """
    if game in _skill_cache:
        return _skill_cache[game]
    stem = _skill_file_stem(game)
    # 优先技能池目录
    pool = os.path.join(SKILLS_DIR, stem)
    if os.path.isdir(pool):
        data = {}
        for fn in os.listdir(pool):
            if fn.endswith(".json"):
                fp = os.path.join(pool, fn)
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        data[fn[:-5]] = json.load(f)
                except (json.JSONDecodeError, OSError):
                    continue
        _skill_cache[game] = data
        return data
    # 回退旧大文件
    filepath = os.path.join(SKILLS_DIR, f"{stem}.json")
    if not os.path.exists(filepath):
        _skill_cache[game] = {}
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    _skill_cache[game] = data
    return data


def _load_templates() -> dict:
    """加载通用技能模板"""
    global _template_cache
    if _template_cache is not None:
        return _template_cache
    filepath = os.path.join(SKILLS_DIR, "_templates.json")
    if not os.path.exists(filepath):
        _template_cache = {}
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        _template_cache = json.load(f)
    return _template_cache


# ==========================================
# 旧的硬编码技能映射已移除：技能文件统一为 skills/<game_id>.json
# get_skills() 作为统一入口，按 game_id 取详细数据，缺失则回退通用模板
# ==========================================

def _build_placeholder_skill(slot: int) -> dict:
    """构建一个占位技能（用于模板不足4个时的补齐）。"""
    key = ["Q", "W", "E", "R"][slot]
    return {
        "name": f"技能{['一','二','三','四'][slot]}",
        "key": key,
        "type": "物理",
        "action": "动作",
        "range": "近战",
        "target": "单体",
        "damage": {"dice_count": 1, "dice_size": 6, "bonus_attr": "STR", "type": "钝击"},
        "effects": [],
        "cooldown": slot + 1 if slot > 0 else 0,
        "description": f"占位技能{slot+1}（待补录真实技能数据）",
        "approx": True,
    }


def _flatten_templates(templates: list) -> list:
    """展平 _templates.json 中混合的 [dict, dict, ..., [dict,...]] 结构为纯 skill dict 列表。

    _templates.json 的 role 条目形状：
      - 前 4 个元素通常是独立 skill dict（Q/W/E/R）
      - 第 5+ 个元素是子列表（QWER×3 的重复捆绑）
    此函数将其全部展平为单个 skill dict 的 list。
    """
    flat: list = []
    for item in templates:
        if isinstance(item, dict):
            flat.append(item)
        elif isinstance(item, list):
            for sub in item:
                if isinstance(sub, dict):
                    flat.append(sub)
    return flat


def get_skills(hero_name: str, hero_name_en: str, game: str, role: str) -> list:
    """获取英雄技能，优先级：详细数据库 > 通用模板。

    返回契约：list[Skill]，长度恒为 4（ADR-001 / ADR-005）。
    """
    names_to_try = [hero_name, hero_name_en]

    # 精确匹配：按 game_id 加载对应技能文件
    skill_db = _load_skill_json(game)

    # 精确匹配失败时尝试模糊匹配（用注册表显示名键集）
    if not skill_db:
        for g_key in REGISTRY_BY_DISPLAY:
            if g_key in game or game in g_key:
                skill_db = _load_skill_json(g_key)
                break

    if skill_db:
        for name in names_to_try:
            if name in skill_db:
                skills = skill_db[name]
                if isinstance(skills, list):
                    return skills
                # 技能库内存储为单 dict 等异常格式时，仍然回退模板
                break

    # 回退到通用模板（占位游戏 skills={} 也会落到这里，属预期，不报错）
    templates = _load_templates().get(role, [])
    if not templates:
        # 无模板：生成 4 个纯占位技能
        return [_build_placeholder_skill(i) for i in range(4)]

    flat = _flatten_templates(templates)
    if len(flat) < 4:
        selected = flat.copy()
        while len(selected) < 4:
            selected.append(_build_placeholder_skill(len(selected)))
    else:
        # ADR-005 C2: 基于英雄名的确定性多样化选择（替代 random.sample）
        # hash(hero_name) 保证：同英雄每次同结果（幂等），不同英雄不同组合（多样化）
        seed = hash(hero_name) % len(flat) if len(flat) > 0 else 0
        selected = []
        for i in range(4):
            idx = (seed + i) % len(flat)
            selected.append(flat[idx])

    # 按 key 重新分配 Q/W/E/R + CD 对齐引擎节奏
    # G-2: 槽0 CD=0, 平均≤3.0, 最大≤5
    key_cd = {"Q": 0, "W": 1, "E": 2, "R": 4}
    for i, skill in enumerate(selected):
        key = ["Q", "W", "E", "R"][i]
        skill["key"] = key
        skill["cooldown"] = key_cd[key]
        # ADR-005 C3: 模板占位标记（Wave 1 真技能替换时区分"已精修"和"待精修"）
        skill["approx"] = True
    return selected


def calc_combat_stats(scores: dict, role: str, level: int) -> dict:
    """基于 D&D 5e 计算战斗数值（HP已按MOBA规模缩放）"""
    cd = CLASS_DEF[role]
    prof = PROF_BONUS.get(level, 2)
    
    mod = {attr: ability_mod(scores.get(attr, 10)) for attr in ABILITY_NAMES}
    con_mod = mod["CON"]
    
    # D&D 原始HP（供参考），再乘以缩放系数
    hp_dnd = cd["hit_die"] + con_mod * level + cd["hp_per_lvl"] * (level - 1)
    hp = int(max(1, hp_dnd) * HP_SCALE)
    ac = 10 + mod["DEX"] + cd["armor"]
    
    # 攻击力计算
    if role in ("assassin", "marksman"):
        atk = 30 + mod["DEX"] * 5 + prof * 3
    else:
        atk = 30 + mod["STR"] * 5 + prof * 3
    
    ap = 25 + mod["INT"] * 6 + prof * 2
    
    return {
        "level": level,
        "hp": hp,                    # 已缩放
        "hp_dnd_raw": hp_dnd,        # D&D原始值（参考用）
        "ac": ac,
        "physical_atk": atk,
        "magic_power": ap,
        "prof_bonus": prof,
        "atk_speed_pct": round(mod["DEX"] * 1.0, 1),
        "crit_chance": round(max(5.0, 10.0 + mod["DEX"] * 2.0), 1),   # 暴击概率(百分比)
        "crit_damage": round(150.0 + mod["DEX"] * 5.0, 1),             # 暴击伤害(百分比)
        "cdr_pct": round(mod["WIS"] * 1.0, 1),
        "heal_bonus_pct": round(mod["CHA"] * 2.0, 1),
        "cc_resist_pct": round(mod["WIS"] * 1.0, 1),
        "save_bonuses": {
            attr: mod[attr] + (prof if attr in cd["save"] else 0)
            for attr in ABILITY_NAMES
        }
    }


def assign_difficulty(hero_name: str, role: str, game: str) -> int:
    """分配难度等级 1-5"""
    # 高操作英雄关键词
    high_skill = ["亚索", "劫", "锐雯", "盲僧", "豹女", "卡莎", "阿卡丽", "永恩", "刀妹",
                  "祈求者", "影魔", "卡尔", "帕吉",
                  "露娜", "关羽", "公孙离", "上官婉儿", "元歌", "马超", "镜",
                  "Fanny", "Ling", "Gusion", "Lancelot", "Hayabusa",
                  "Loki", "Abathur", "Zeratul", "Tracer", "Genji",
                  "蜘蛛侠", "黑寡妇"]
    
    low_skill = ["盖伦", "安妮", "艾希", "石头人", "提莫",
                 "冰女", "斧王",
                 "亚瑟", "妲己", "安琪拉", "后羿",
                 "Layla", "Nana", "Miya", "Eudora", "Rafaela",
                 "皮卡丘", "卡比兽",
                 "Zeus", "Ra", "Ymir",
                 "Raynor", "Valla", "Li Li"]
    
    for h in high_skill:
        if h in hero_name:
            return 5 if role == "assassin" else 4
    
    for h in low_skill:
        if h in hero_name:
            return 1
    
    difficulty_map = {"tank": 2, "fighter": 3, "assassin": 4, "mage": 3, "marksman": 2, "support": 2}
    return difficulty_map.get(role, 3)


def assign_playstyle(role: str, hero_name: str, skills: list) -> list:
    """分配玩法标签"""
    tags = set()

    role_tags = {
        "tank": ["前排", "先手", "承伤"],
        "fighter": ["突进", "持续输出", "缠斗"],
        "assassin": ["收割", "切入", "爆发"],
        "mage": ["远程", "AOE", "控制"],
        "marksman": ["远程", "持续输出", "核心"],
        "support": ["保护", "治疗", "增益"],
    }
    tags.update(role_tags.get(role, []))

    # 从技能提取摘要文本（兼容新旧格式）
    skills_text = ""
    for s in skills:
        if isinstance(s, dict):
            skills_text += s.get("description", "") + " "
            skills_text += s.get("name", "") + " "
        else:
            skills_text += str(s) + " "
    if any(k in skills_text for k in ["隐身", "stealth", "Vanish", "Smoke"]): tags.add("潜行")
    if any(k in skills_text for k in ["钩", "hook", "Hook", "Pull", "拉"]): tags.add("钩子")
    if any(k in skills_text for k in ["斩杀", "execute", "Execution", "Assassinate"]): tags.add("斩杀")
    if any(k in skills_text for k in ["变身", "transform", "Metamorphosis", "形态"]): tags.add("变身")
    if any(k in skills_text for k in ["治疗", "heal", "Healing", "Restore", "Cure"]): tags.add("治疗")
    if any(k in skills_text for k in ["护盾", "shield", "Shield", "Barrier", "Block"]): tags.add("护盾")
    if any(k in skills_text for k in ["全图", "global", "World", "Global"]): tags.add("全图支援")
    if any(k in skills_text for k in ["分身", "clone", "Decoy", "Clone"]): tags.add("分身")
    if any(k in skills_text for k in ["毒", "poison", "Poison", "Toxic", "Venom"]): tags.add("持续伤害")
    if any(k in skills_text for k in ["眩晕", "冻结", "stun", "Stun", "Freeze", "Root"]): tags.add("硬控制")
    if any(k in skills_text for k in ["闪现", "位移", "dash", "Blink", "Teleport"]): tags.add("高机动")
    
    return sorted(list(tags))[:8]


def generate_character_card(hero: dict, rng_seed: int) -> dict:
    """为单个英雄生成完整角色卡。

    ADR-005: card_id 语义从"生成序号"改为 <game_id>:<hero_slug>，
    与物理路径同构、局部生成幂等。旧 card_id 保留为 legacy_card_id。
    """
    random.seed(rng_seed)
    
    name_raw = hero.get("name", "未知")
    name_en_raw = hero.get("name_en", "")
    game = hero.get("game", "")
    # 应用英雄名中文化映射：如果原始名字在映射表中则翻译，否则保留原名
    name = HERO_NAME_CN.get(name_raw, name_raw)
    # 如果原始名字已经是中文（不在映射表中），则 name_en 保持不变
    # 如果原始名字被翻译了，将原始英文名移到 name_en
    if name_raw in HERO_NAME_CN and not name_en_raw:
        name_en = name_raw
    else:
        name_en = name_en_raw
    alias = hero.get("alias", "")
    native_role = hero.get("native_role", "")
    universal_role = hero.get("universal_role", "fighter")
    source = hero.get("source", "")
    difficulty = assign_difficulty(name, universal_role, game)
    
    # 1. D&D 5e 属性生成（标准数组 + 种族加值）
    base_scores = generate_abilities(universal_role, method="standard_array")
    racial = RACIAL_BONUS.get(universal_role, {"STR": 2, "DEX": 1})
    final_scores = {attr: min(20, base_scores[attr] + racial.get(attr, 0)) for attr in ABILITY_NAMES}
    modifiers = {attr: ability_mod(final_scores[attr]) for attr in ABILITY_NAMES}
    
    # 2. 战斗数值
    stats_lv1 = calc_combat_stats(final_scores, universal_role, 1)
    stats_lv18 = calc_combat_stats(final_scores, universal_role, 18)
    
    # 3. 技能
    skills = get_skills(name, name_en, game, universal_role)
    
    # 4. 标签
    playstyle = assign_playstyle(universal_role, name, skills)
    
    # 5. card_id: ADR-005 稳定标识 = <game_id>:<hero_slug>
    game_id = REGISTRY_BY_DISPLAY.get(game, _slugify(game))
    hero_slug = name.replace("/", "_").replace(" ", "_").replace(":", "")
    # TODO: 旧 card_id 过渡期结束后移除 legacy_card_id
    legacy_card_id = f"{game[:3].upper()}-{rng_seed:04d}"
    
    # 6. 组装角色卡
    card = {
        "card_id": f"{game_id}:{hero_slug}",
        "legacy_card_id": legacy_card_id,
        "hero": {
            "name": name,
            "name_en": name_en,
            "alias": alias,
            "title": alias if alias else name_en,
        },
        "game": {
            "name": game,
            "name_cn": GAME_NAME_CN.get(game, game),
            "native_role": native_role,
            "universal_role": universal_role,
            "role_name": ROLE_CN.get(universal_role, ""),
            "role_dnd_class": ROLE_DND.get(universal_role, ""),
        },
        "source": source,
        "difficulty": difficulty,
        "playstyle_tags": playstyle,
        "attributes": {
            attr: {
                "score": final_scores[attr],
                "modifier": modifiers[attr],
                "name_cn": ABILITY_CN[attr],
            }
            for attr in ABILITY_NAMES
        },
        "primary_abilities": list(CLASS_DEF[universal_role]["primary"]),
        "hit_die": CLASS_DEF[universal_role]["hit_die"],
        "stats_lv1": stats_lv1,
        "stats_lv18": stats_lv18,
        "growth_per_level": {
            "hp": int((CLASS_DEF[universal_role]["hp_per_lvl"] + modifiers["CON"]) * HP_SCALE),
            "atk": 2.5,
            "ap": 1.5,
        },
        "skills": skills,
    }
    
    return card


def main():
    print("=" * 60)
    print("  MOBA 英雄角色卡生成器")
    print("  基于 D&D 5e + 英雄池角色分析数据")
    print("=" * 60)
    
    # 加载数据
    print("\n[1/3] 加载英雄数据...")
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    heroes = data["heroes"]
    print(f"  ✓ 加载 {len(heroes)} 位英雄")
    
    # 按游戏分组
    by_game = defaultdict(list)
    for h in heroes:
        by_game[h["game"]].append(h)
    
    # 生成角色卡
    print("\n[2/3] 生成角色卡...")
    total = 0
    game_counts = {}
    
    for game_name, game_heroes in sorted(by_game.items()):
        # 为每个游戏创建子目录（统一用 game_id；未登记则回退小写 slug）
        safe_name = REGISTRY_BY_DISPLAY.get(game_name, _slugify(game_name))
        game_dir = os.path.join(OUTPUT_DIR, safe_name)
        os.makedirs(game_dir, exist_ok=True)
        
        count = 0
        for idx, hero in enumerate(game_heroes):
            card = generate_character_card(hero, total + idx + 1000)

            # 契约校验：fail-fast，拒绝写盘（ADR-005）
            violations = schema.validate_card(card)
            if violations:
                hero_name = hero.get("name", f"hero_{idx}")
                print(f"  ✗ 契约校验失败 [{game_name}] {hero_name}: {'; '.join(violations)}", file=sys.stderr)
                print(f"    拒绝写盘，跳过该英雄。请检查 get_skills() 返回值或模板数据。", file=sys.stderr)
                continue
            
            # 文件名：安全化英雄名
            hero_filename = hero.get("name", f"hero_{idx}")
            hero_filename = hero_filename.replace("/", "_").replace(" ", "_").replace(":", "")
            filepath = os.path.join(game_dir, f"{hero_filename}.json")
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(card, f, ensure_ascii=False, indent=2)
            count += 1
        
        game_counts[game_name] = count
        total += count
        print(f"  ✓ {game_name}: {count} 张角色卡")
    
    # 生成索引
    print("\n[3/3] 生成索引文件...")
    index = {
        "project": "MOBA英雄角色卡",
        "framework": "基于D&D 5e规则的数值体系",
        "total_cards": total,
        "total_games": len(game_counts),
        "games": {
            REGISTRY_BY_DISPLAY.get(name, _slugify(name)): {
                "display": name,
                "count": cnt,
                "directory": REGISTRY_BY_DISPLAY.get(name, _slugify(name)),
            }
            for name, cnt in sorted(game_counts.items())
        },
        "card_schema": {
            "attributes": "六维属性(STR/DEX/CON/INT/WIS/CHA)，含属性值和调整值",
            "stats": "1级和18级战斗数值(生命 / 护甲 / 攻击 / 法强 / 冷却 / 暴击率 / 暴击伤害 / 攻速 / 豁免)",
            "skills": "4个技能(3个基础+1个大招)，含中文功能描述",
            "difficulty": "1-5星难度评级",
            "playstyle_tags": "最多8个玩法标签，支持搜索筛选",
        }
    }
    
    index_path = os.path.join(OUTPUT_DIR, "_index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print(f"  完成！共生成 {total} 张角色卡")
    print(f"  分布在 {len(game_counts)} 个游戏文件夹中")
    print(f"  索引文件: {index_path}")
    print("=" * 60)
    
    # 展示几张示例卡
    print("\n\n【示例角色卡预览】\n")
    sample_dirs = list(game_counts.keys())[:5]
    for game_name in sample_dirs:
        safe_name = REGISTRY_BY_DISPLAY.get(game_name, _slugify(game_name))
        game_dir = os.path.join(OUTPUT_DIR, safe_name)
        files = os.listdir(game_dir)
        if files:
            sample_path = os.path.join(game_dir, files[0])
            with open(sample_path, "r", encoding="utf-8") as f:
                card = json.load(f)
            game_cn = GAME_NAME_CN.get(game_name, game_name)
            print(f"  [{game_cn}] {card['hero']['name']}")
            print(f"    定位: {card['game']['role_name']} | 难度: {'★'*card['difficulty']}")
            print(f"    属性: 力量{card['attributes']['STR']['score']} 敏捷{card['attributes']['DEX']['score']} 体质{card['attributes']['CON']['score']} 智力{card['attributes']['INT']['score']} 感知{card['attributes']['WIS']['score']} 魅力{card['attributes']['CHA']['score']}")
            print(f"    Lv1: 生命{card['stats_lv1']['hp']} 护甲{card['stats_lv1']['ac']} 攻击{card['stats_lv1']['physical_atk']} 法强{card['stats_lv1']['magic_power']}")
            print(f"    技能: {' | '.join(s['name'] if isinstance(s, dict) else str(s) for s in card['skills'])}")
            print()


if __name__ == "__main__":
    main()
