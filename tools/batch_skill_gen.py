#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量 MOBA 技能 → D&D 5e 生成器
读取 source heroes.json，WebSearch/手动提供技能名，调用 skill_mechanics 生成。
"""

import json
import sys
import os

# Add tools to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')))
from skill_mechanics import (
    convert_skill_to_dnd, convert_skill_set,
    CLASS_DAMAGE_DICE, SKILL_TIER_MULT,
    DMG_TYPE_KEYWORDS, EFFECT_KEYWORDS,
    get_template_skills_dnd
)
from core.skill_pool import write_hero_skill

# ==========================================
# 角色 → D&D 属性偏好映射
# ==========================================
ROLE_ATTR_MAP = {
    "tank": {"bonus": "STR", "dc": "STR", "dmg_types": ["钝击", "挥砍"]},
    "fighter": {"bonus": "STR", "dc": "STR", "dmg_types": ["挥砍", "钝击"]},
    "assassin": {"bonus": "DEX", "dc": "DEX", "dmg_types": ["穿刺", "挥砍"]},
    "mage": {"bonus": "INT", "dc": "INT", "dmg_types": ["火焰", "寒冷", "闪电", "力场", "黯蚀"]},
    "marksman": {"bonus": "DEX", "dc": "DEX", "dmg_types": ["穿刺"]},
    "support": {"bonus": "WIS", "dc": "WIS", "dmg_types": ["光耀", "力场"]},
}

# ==========================================
# CD 映射：Q/W/E/R → 0/1/2/4
# ==========================================
KEY_CD_MAP = {"Q": 0, "W": 1, "E": 2, "R": 4, "P": 4}

# ==========================================
# 英雄技能模板（按角色预设 QWER 用法）
# ==========================================
ROLE_SKILL_PROFILES = {
    "tank": {
        "Q": {"type": "物理", "range": "近战", "target": "单体",
              "dice": (1, 10), "dmg_type": "钝击",
              "effect_hint": "减速/眩晕"},
        "W": {"type": "物理", "range": "近战", "target": "范围",
              "dice": (2, 10), "dmg_type": "钝击",
              "aoe": 5, "effect_hint": "嘲讽/击退"},
        "E": {"type": "物理", "range": "自身", "target": "自身",
              "dice": (0, 0), "dmg_type": "力场",
              "effect_hint": "护盾/减伤/回复"},
        "R": {"type": "物理", "range": "近战", "target": "范围",
              "dice": (4, 10), "dmg_type": "钝击",
              "aoe": 15, "effect_hint": "击飞/眩晕/群控"},
    },
    "fighter": {
        "Q": {"type": "物理", "range": "近战", "target": "单体",
              "dice": (1, 8), "dmg_type": "挥砍",
              "effect_hint": "突进/减速"},
        "W": {"type": "物理", "range": "近战", "target": "范围",
              "dice": (2, 8), "dmg_type": "挥砍",
              "aoe": 5, "effect_hint": "范围/连击"},
        "E": {"type": "物理", "range": "自身", "target": "自身",
              "dice": (0, 0), "dmg_type": "力场",
              "effect_hint": "加速/位移/霸体"},
        "R": {"type": "物理", "range": "近战", "target": "范围",
              "dice": (4, 8), "dmg_type": "挥砍",
              "aoe": 10, "effect_hint": "斩杀/击飞/强化"},
    },
    "assassin": {
        "Q": {"type": "物理", "range": "近战", "target": "单体",
              "dice": (2, 6), "dmg_type": "穿刺",
              "effect_hint": "突进/标记"},
        "W": {"type": "物理", "range": "近战", "target": "单体",
              "dice": (2, 6), "dmg_type": "挥砍",
              "effect_hint": "位移/分身/隐身"},
        "E": {"type": "物理", "range": "自身", "target": "自身",
              "dice": (0, 0), "dmg_type": "力场",
              "effect_hint": "加速/净化/后跳"},
        "R": {"type": "物理", "range": "60尺", "target": "单体",
              "dice": (5, 6), "dmg_type": "穿刺",
              "effect_hint": "斩杀/多段/真伤"},
    },
    "mage": {
        "Q": {"type": "法术", "range": "60尺", "target": "单体",
              "dice": (2, 6), "dmg_type": "火焰",
              "effect_hint": "灼烧/减速"},
        "W": {"type": "法术", "range": "60尺", "target": "范围",
              "dice": (3, 6), "dmg_type": "寒冷",
              "aoe": 10, "effect_hint": "冻结/范围"},
        "E": {"type": "法术", "range": "自身", "target": "自身",
              "dice": (0, 0), "dmg_type": "力场",
              "effect_hint": "位移/护盾/控制"},
        "R": {"type": "法术", "range": "100尺", "target": "范围",
              "dice": (6, 6), "dmg_type": "闪电",
              "aoe": 20, "effect_hint": "大范围AOE/眩晕"},
    },
    "marksman": {
        "Q": {"type": "物理", "range": "120尺", "target": "单体",
              "dice": (1, 8), "dmg_type": "穿刺",
              "effect_hint": "强化射击/减速"},
        "W": {"type": "物理", "range": "120尺", "target": "范围",
              "dice": (2, 8), "dmg_type": "穿刺",
              "aoe": 10, "effect_hint": "箭雨/扇形"},
        "E": {"type": "物理", "range": "自身", "target": "自身",
              "dice": (0, 0), "dmg_type": "力场",
              "effect_hint": "位移/加速/视野"},
        "R": {"type": "物理", "range": "150尺", "target": "单体",
              "dice": (4, 8), "dmg_type": "穿刺",
              "effect_hint": "远程狙击/眩晕/斩杀"},
    },
    "support": {
        "Q": {"type": "法术", "range": "30尺", "target": "单体",
              "dice": (1, 8), "dmg_type": "光耀",
              "effect_hint": "治疗/减速"},
        "W": {"type": "法术", "range": "30尺", "target": "范围",
              "dice": (2, 6), "dmg_type": "光耀",
              "aoe": 10, "effect_hint": "群体治疗/护盾"},
        "E": {"type": "法术", "range": "60尺", "target": "单体",
              "dice": (1, 6), "dmg_type": "力场",
              "effect_hint": "控制/沉默/禁锢"},
        "R": {"type": "法术", "range": "60尺", "target": "范围",
              "dice": (4, 6), "dmg_type": "光耀",
              "aoe": 20, "effect_hint": "群体治疗/复活/净化"},
    },
}


def build_skill_from_profile(hero_name, role, key, skill_name, desc_hint="", override=None):
    """基于角色模板生成单个 D&D 技能。

    Args:
        hero_name: 英雄名
        role: universal_role (tank/fighter/assassin/mage/marksman/support)
        key: Q/W/E/R
        skill_name: 技能中文/英文名
        desc_hint: 额外描述关键词（用于匹配效果别名表）
        override: dict of field overrides for customization

    Returns:
        D&D structured skill dict
    """
    profile = ROLE_SKILL_PROFILES.get(role, ROLE_SKILL_PROFILES["fighter"])
    slot = profile.get(key, profile["Q"])
    attr = ROLE_ATTR_MAP.get(role, ROLE_ATTR_MAP["fighter"])

    cd = KEY_CD_MAP.get(key, 0)

    # 尝试用 skill_mechanics 解析
    skill_str = f"{key}:{skill_name}"
    if desc_hint:
        skill_str += f"-{desc_hint}"

    # 直接用模板构建（更可控）
    dice_count = slot["dice"][0]
    dice_size = slot["dice"][1]
    skill_type = slot["type"]
    is_damaging = dice_count > 0

    # 构建 damage
    damage = None
    if is_damaging:
        damage = {
            "dice_count": dice_count,
            "dice_size": dice_size,
            "bonus_attr": attr["bonus"],
            "type": slot["dmg_type"],
        }

    # 构建 effects
    effects = []
    effect_hint = slot.get("effect_hint", "")
    desc_parts = []

    if is_damaging:
        dmg_str = f"{dice_count}d{dice_size}+{attr['bonus']} {slot['dmg_type']}伤害"
        desc_parts.append(dmg_str)
    else:
        dmg_str = ""

    # 解析 desc_hint 中的效果关键词
    if desc_hint:
        for keyword, eff_def in EFFECT_KEYWORDS.items():
            if keyword in desc_hint:
                is_beneficial = eff_def["type"] in (
                    "加速", "护盾", "减伤", "治疗", "回复", "吸血", "隐身",
                    "霸体", "净化", "攻速强化", "暴击强化", "免疫控制", "复活", "隐形",
                    "攻速", "暴击"
                )
                is_displacement = eff_def["type"] in ("位移", "换位")
                eff = {
                    "type": eff_def["type"],
                    "desc": eff_def.get("desc", ""),
                    "target": "自身" if (is_beneficial or is_displacement) else "敌方",
                }
                if "duration" in eff_def:
                    eff["duration"] = eff_def["duration"]
                if "dc_attr" in eff_def and eff_def["dc_attr"]:
                    eff["dc_attr"] = eff_def["dc_attr"]
                if "value" in eff_def:
                    eff["value"] = eff_def["value"]
                if "value_formula" in eff_def:
                    eff["value_formula"] = eff_def["value_formula"]
                if "threshold" in eff_def:
                    eff["threshold"] = eff_def["threshold"]
                if "dmg_per_turn" in eff_def:
                    eff["dmg_per_turn"] = eff_def["dmg_per_turn"]
                effects.append(eff)

                dur_str = f"{eff_def.get('duration','')}回合" if eff_def.get("duration") else ""
                desc_parts.append(f"{eff_def.get('desc','')}{dur_str}")

    description = "。".join(desc_parts) + "。" if desc_parts else f"{skill_name}。"

    # 构建 saving_throw（如果有控制效果）
    saving_throw = None
    control_effects = [e for e in effects if e.get("dc_attr")]
    if control_effects:
        saving_throw = {
            "attr": control_effects[0]["dc_attr"],
            "dc_formula": f"8+PROF+{attr['dc']}",
            "on_save": "无效",
        }

    skill = {
        "name": skill_name,
        "key": key,
        "type": skill_type,
        "action": "动作",
        "range": slot["range"],
        "target": slot["target"],
        "cooldown": cd,
        "description": description,
    }

    if damage:
        skill["damage"] = damage
    else:
        skill["damage"] = {"dice_count": 0, "dice_size": 0, "bonus_attr": "CON", "type": "力场"}

    if effects:
        skill["effects"] = effects
    if saving_throw:
        skill["saving_throw"] = saving_throw
    if "aoe" in slot and slot["aoe"]:
        skill["aoe_radius"] = slot["aoe"]

    # 应用 override
    if override:
        for k, v in override.items():
            if k == "effects" and isinstance(v, list):
                skill["effects"] = v
            elif k == "damage" and isinstance(v, dict):
                skill["damage"] = v
            else:
                skill[k] = v

    return skill


def build_hero_skills(hero_name, role, skill_names, desc_hints=None):
    """为一个英雄生成 4 个 D&D 技能。

    Args:
        hero_name: 英雄名
        role: universal_role
        skill_names: dict like {"Q": "技能名", "W": "技能名", "E": "技能名", "R": "技能名"}
        desc_hints: dict like {"Q": "关键词1+关键词2", ...}

    Returns:
        list of 4 skill dicts
    """
    if desc_hints is None:
        desc_hints = {}

    skills = []
    for key in ["Q", "W", "E", "R"]:
        name = skill_names.get(key, f"{hero_name}技{key}")
        hint = desc_hints.get(key, "")
        skill = build_skill_from_profile(hero_name, role, key, name, hint)
        skills.append(skill)
    return skills


def load_source_heroes(game_key):
    """加载源英雄数据，返回 {hero_name: {role, universal_role}}"""
    path_map = {
        "dota2": "data/source/dota2/heroes.json",
        "mlbb": "data/source/mobile_legends_bang_bang/heroes.json",
        "yinghun": "data/source/yinghunzhiren/heroes.json",
    }
    path = path_map.get(game_key)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    result = {}
    for h in data["heroes"]:
        name = h.get("name_cn") or h.get("name")
        result[name] = {
            "name": h.get("name", name),
            "role": h.get("role", ""),
            "universal_role": h.get("universal_role", "fighter"),
        }
    return result


def load_existing_skills(skills_path):
    """加载已有技能数据，优先从技能池目录读取，回退旧大文件。

    返回 {英雄名: skills} 字典，供缺失英雄判断使用。
    """
    ip = os.path.splitext(os.path.basename(skills_path))[0]
    pool = os.path.join(os.path.dirname(skills_path), ip)
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
        return data
    if os.path.exists(skills_path):
        with open(skills_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def merge_and_save(existing, new_skills, skills_path):
    """合并新技能并保存到技能池：data/skills/<ip>/<英雄>.json（每英雄独立文件）。

    skills_path 形如 data/skills/<ip>.json，从中提取 ip 作为池目录名。
    """
    existing.update(new_skills)
    ip = os.path.splitext(os.path.basename(skills_path))[0]
    for name, skills in existing.items():
        write_hero_skill(ip, name, skills)
    return existing


def get_missing_heroes(game_key):
    """获取尚未生成技能的英雄列表"""
    path_map = {
        "dota2": ("data/source/dota2/heroes.json", "data/skills/dota2.json"),
        "mlbb": ("data/source/mobile_legends_bang_bang/heroes.json", "data/skills/mobile_legends_bang_bang.json"),
        "yinghun": ("data/source/yinghunzhiren/heroes.json", "data/skills/yinghunzhiren.json"),
    }
    src_path, sk_path = path_map.get(game_key)
    src = load_source_heroes(game_key)
    existing = load_existing_skills(sk_path)

    missing = []
    for name, info in src.items():
        if name not in existing:
            missing.append((name, info))
    return missing


# ==========================================
# 预置 Dota2 技能名映射（基于 Dota 2 Wiki/source）
# ==========================================
DOTA2_SKILL_NAMES = {
    "上古巨神": {"Q": "回音重踏", "W": "星体游魂", "E": "自然秩序", "R": "裂地沟壑",
                 "hints": {"Q": "眩晕+范围", "W": "位移+减速", "E": "减伤+减速", "R": "范围+减速+眩晕"}},
    "不朽尸王": {"Q": "腐朽", "W": "噬魂", "E": "墓碑", "R": "血肉傀儡",
                 "hints": {"Q": "范围+减伤", "W": "治疗+范围", "E": "召唤+减速", "R": "变身+强化"}},
    "亚巴顿": {"Q": "迷雾缠绕", "W": "无光之盾", "E": "霜之哀伤", "R": "回光返照",
               "hints": {"Q": "治疗+远程", "W": "护盾+范围", "E": "减速+攻速", "R": "霸体+治疗"}},
    "伐木机": {"Q": "死亡旋风", "W": "伐木锯链", "E": "活性护甲", "R": "锯齿飞轮",
               "hints": {"Q": "范围+真伤", "W": "位移+突进", "E": "护盾+减伤", "R": "范围+减速"}},
    "修补匠": {"Q": "激光", "W": "热导飞弹", "E": "进击的机械", "R": "再装填",
               "hints": {"Q": "致盲+远程", "W": "范围+远程", "E": "攻速+位移", "R": "刷新+强化"}},
    "先知": {"Q": "发芽", "W": "传送", "E": "自然之怒", "R": "自然之怒",
             "hints": {"Q": "禁锢+地形", "W": "位移+全图", "E": "攻速+召唤", "R": "全图+弹跳"}},
    "光之守卫": {"Q": "冲击波", "W": "法力流失", "E": "查克拉魔法", "R": "灵魂形态",
                 "hints": {"Q": "范围+远程", "W": "沉默+减速", "E": "回复+护盾", "R": "变身+强化"}},
    "克林克兹": {"Q": "灼热之箭", "W": "扫射", "E": "骨隐步", "R": "死亡契约",
                 "hints": {"Q": "灼烧+远程", "W": "攻速+加速", "E": "隐身+加速", "R": "斩杀+吸血"}},
    "全能骑士": {"Q": "洗礼", "W": "驱逐", "E": "退化光环", "R": "守护天使",
                 "hints": {"Q": "治疗+远程", "W": "霸体+护盾", "E": "减速+减伤", "R": "护盾+减伤+全队"}},
    "兽王": {"Q": "野性之斧", "W": "野性呼唤", "E": "原始之怒", "R": "原始咆哮",
             "hints": {"Q": "范围+挥砍", "W": "召唤+攻速", "E": "攻速+强化", "R": "眩晕+击退"}},
    "军团指挥官": {"Q": "压倒性优势", "W": "强攻", "E": "勇气之霎", "R": "决斗",
                  "hints": {"Q": "范围+攻速", "W": "治疗+加速", "E": "吸血+反击", "R": "嘲讽+单挑"}},
    "冥界亚龙": {"Q": "毒性攻击", "W": "幽冥剧毒", "E": "腐蚀皮肤", "R": "蝮蛇突袭",
                 "hints": {"Q": "毒+减速", "W": "毒+范围", "E": "毒+护盾", "R": "毒+减速+远程"}},
    "冥魂大帝": {"Q": "冥火爆击", "W": "吸血光环", "E": "致命一击", "R": "重生",
                 "hints": {"Q": "眩晕+远程", "W": "吸血+光环", "E": "暴击+强化", "R": "复活+范围"}},
    "凤凰": {"Q": "凤凰冲击", "W": "烈火精灵", "E": "烈日炙烤", "R": "超新星",
             "hints": {"Q": "位移+灼烧", "W": "灼烧+远程", "E": "灼烧+范围", "R": "范围+灼烧+复活"}},
    "剃刀": {"Q": "等离子场", "W": "静电连接", "E": "不稳定电流", "R": "风暴之眼",
             "hints": {"Q": "范围+闪电", "W": "减伤+攻速", "E": "加速+净化", "R": "闪电+范围"}},
    "剧毒术士": {"Q": "瘴气", "W": "毒刺", "E": "瘟疫守卫", "R": "剧毒新星",
                 "hints": {"Q": "毒+减速+远程", "W": "毒+减速", "E": "召唤+毒", "R": "毒+范围+持续"}},
    "半人马战行者": {"Q": "马蹄践踏", "W": "双刃剑", "E": "反击", "R": "奔袭冲撞",
                     "hints": {"Q": "眩晕+范围", "W": "范围+真伤", "E": "反击+护盾", "R": "加速+击飞+全队"}},
    "卓尔游侠": {"Q": "霜冻之箭", "W": "狂风", "E": "精准光环", "R": "射手天赋",
                 "hints": {"Q": "减速+远程", "W": "击退+沉默", "E": "攻速+光环", "R": "暴击+斩杀"}},
    "发条技师": {"Q": "弹幕冲击", "W": "能量齿轮", "E": "火箭弹幕", "R": "发射钩爪",
                 "hints": {"Q": "眩晕+范围", "W": "地形+禁锢", "E": "范围+灼烧", "R": "钩子+突进+眩晕"}},
    "变体精灵": {"Q": "波浪形态", "W": "变体攻击", "E": "属性转换", "R": "变形",
                 "hints": {"Q": "位移+范围", "W": "击退+眩晕", "E": "变身+回复", "R": "变身+复制"}},
    "司夜刺客": {"Q": "穿刺", "W": "法力燃烧", "E": "尖刺外壳", "R": "复仇",
                 "hints": {"Q": "眩晕+击飞+范围", "W": "沉默+灼烧", "E": "护盾+反击", "R": "隐身+穿刺"}},
    "哈斯卡": {"Q": "沸血之矛", "W": "心炎", "E": "狂战士之血", "R": "牺牲",
               "hints": {"Q": "灼烧+远程", "W": "击退+范围", "E": "攻速+吸血", "R": "突进+眩晕+斩杀"}},
    "噬魂鬼": {"Q": "狂暴", "W": "盛宴", "E": "撕裂伤口", "R": "感染",
               "hints": {"Q": "霸体+攻速", "W": "吸血+斩杀", "E": "减速+吸血", "R": "隐身+突进"}},
    "圣堂刺客": {"Q": "折光", "W": "隐匿", "E": "灵能之刃", "R": "灵能陷阱",
                 "hints": {"Q": "护盾+攻速", "W": "隐身+暴击", "E": "范围+穿刺", "R": "减速+视野"}},
    "复仇之魂": {"Q": "魔法箭", "W": "恐怖波动", "E": "复仇光环", "R": "移形换位",
                 "hints": {"Q": "眩晕+远程", "W": "减伤+范围", "E": "攻速+光环", "R": "换位+位移"}},
    "大地之灵": {"Q": "巨石冲击", "W": "巨石翻滚", "E": "地磁之握", "R": "磁化",
                 "hints": {"Q": "击退+眩晕", "W": "位移+减速", "E": "沉默+减速", "R": "范围+眩晕"}},
    "天怒法师": {"Q": "奥术脉冲", "W": "震荡光弹", "E": "上古封印", "R": "神秘闪光",
                 "hints": {"Q": "范围+减速", "W": "减速+远程", "E": "沉默+减伤", "R": "范围+连击"}},
    "天涯墨客": {"Q": "墨涌", "W": "幻影之拥", "E": "暗绘", "R": "缚魂",
                 "hints": {"Q": "减速+范围", "W": "位移+范围", "E": "分身+召唤", "R": "禁锢+链接"}},
    "天穹守望者": {"Q": "闪光幽魂", "W": "磁场", "E": "火花幽魂", "R": "风暴双雄",
                   "hints": {"Q": "范围+闪电", "W": "护盾+攻速", "E": "召唤+灼烧", "R": "分身+复制"}},
    "娜迦海妖": {"Q": "激流", "W": "镜像", "E": "诱捕", "R": "海妖之歌",
                 "hints": {"Q": "范围+减速", "W": "分身+连击", "E": "禁锢+减速", "R": "范围+眩晕+魅惑"}},
    "宙斯": {"Q": "弧形闪电", "W": "雷击", "E": "静电场", "R": "雷神之怒",
             "hints": {"Q": "弹跳+闪电", "W": "闪电+眩晕", "E": "闪电+范围", "R": "全图+闪电"}},
    "寒冬飞龙": {"Q": "极寒之拥", "W": "碎裂冲击", "E": "严寒灼烧", "R": "寒冬诅咒",
                 "hints": {"Q": "治疗+护盾", "W": "范围+减速", "E": "灼烧+远程", "R": "嘲讽+禁锢"}},
    "小小": {"Q": "山崩", "W": "投掷", "E": "长大", "R": "抓树",
             "hints": {"Q": "眩晕+范围", "W": "击飞+位移", "E": "变身体型", "R": "范围+击飞"}},
    "巫妖": {"Q": "寒霜爆发", "W": "冰霜护甲", "E": "邪恶祭祀", "R": "连环霜冻",
             "hints": {"Q": "范围+减速", "W": "护盾+减速", "E": "回复+眩晕", "R": "弹跳+冻结"}},
    "巫医": {"Q": "麻痹药剂", "W": "巫毒疗法", "E": "诅咒", "R": "死亡守卫",
             "hints": {"Q": "眩晕+弹跳", "W": "治疗+范围", "E": "毒+范围", "R": "召唤+远程"}},
    "帕格纳": {"Q": "幽冥爆轰", "W": "衰老", "E": "幽冥守卫", "R": "生命汲取",
               "hints": {"Q": "范围+黯蚀", "W": "减伤+禁锢", "E": "召唤+灼烧", "R": "吸血+链接"}},
    "帕克": {"Q": "幻象法球", "W": "新月之痕", "E": "相位转移", "R": "梦境缠绕",
             "hints": {"Q": "范围+位移", "W": "范围+沉默", "E": "位移+闪避", "R": "禁锢+眩晕+范围"}},
    "幽鬼": {"Q": "幽鬼之刃", "W": "荒芜", "E": "折射", "R": "鬼影重重",
             "hints": {"Q": "减速+位移", "W": "真伤+暴击", "E": "减伤+反击", "R": "分身+全图"}},
    "幻影长矛手": {"Q": "灵魂之矛", "W": "神行百变", "E": "幻影冲锋", "R": "并列",
                   "hints": {"Q": "减速+远程", "W": "分身+位移", "E": "突进+加速", "R": "分身+连击"}},
    "干扰者": {"Q": "雷霆之击", "W": "恶念瞥视", "E": "动能立场", "R": "静态风暴",
               "hints": {"Q": "闪电+范围", "W": "位移+换位", "E": "禁锢+地形", "R": "沉默+范围+闪电"}},
}

# ==========================================
# 预置 MLBB 技能名映射
# ==========================================
MLBB_SKILL_NAMES = {
    "Aamon": {"Q": "Soul Shards", "W": "Slayer Shards", "E": "Endless Shards", "R": "Demonic Power",
              "hints": {"Q": "远程+标记", "W": "范围+突进", "E": "隐身+加速", "R": "斩杀+强化"}},
    "Alice": {"Q": "Blood Ode", "W": "Blood Awe", "E": "Blood Ancestry", "R": "Blood Symphony",
              "hints": {"Q": "范围+吸血", "W": "禁锢+眩晕", "E": "吸血+强化", "R": "范围+治疗"}},
    "Alpha": {"Q": "Rotary Impact", "W": "Force Swing", "E": "Spear of Alpha", "R": "Beta's Wrath",
              "hints": {"Q": "范围+旋转", "W": "击飞+位移", "E": "眩晕+远程", "R": "突进+范围"}},
    "Angela": {"Q": "Love Waves", "W": "Puppet-on-a-String", "E": "Heartguard", "R": "Guardian Angel",
               "hints": {"Q": "治疗+远程", "W": "禁锢+减速", "E": "护盾+加速", "R": "护盾+全队"}},
    "Argus": {"Q": "Demonic Grip", "W": "Meteoric Sword", "E": "Eternal Evil", "R": "Metamorphosis",
              "hints": {"Q": "钩子+眩晕", "W": "突进+击飞", "E": "吸血+攻速", "R": "变身+霸体"}},
    "Arlott": {"Q": "Dauntless", "W": "Judgment", "E": "Vengeance", "R": "Final Slash",
               "hints": {"Q": "突进+范围", "W": "眩晕+击飞", "E": "护盾+减伤", "R": "范围+斩杀"}},
    "Atlas": {"Q": "Annihilate", "W": "Perfect Match", "E": "Titanic Fury", "R": "Mecha Sentry",
              "hints": {"Q": "范围+眩晕", "W": "禁锢+钩子", "E": "加速+护盾", "R": "范围+嘲讽"}},
    "Aulus": {"Q": "Undying Fury", "W": "Power of Unity", "E": "Rallying Cry", "R": "War Axe",
              "hints": {"Q": "攻速+强化", "W": "护盾+范围", "E": "加速+攻速", "R": "范围+击飞"}},
    "Aurora": {"Q": "Frost Shock", "W": "Bitter Frost", "E": "Cold Rush", "R": "Blizzard",
               "hints": {"Q": "减速+远程", "W": "冻结+范围", "E": "位移+冻结", "R": "范围+冻结+眩晕"}},
    "Badang": {"Q": "Qigong Fist", "W": "Fist Break", "E": "Fist Wind", "R": "Warrior's Oath",
               "hints": {"Q": "击退+远程", "W": "突进+眩晕", "E": "护盾+攻速", "R": "范围+击飞+连击"}},
    "Balmond": {"Q": "Soul Lock", "W": "Cyclone Sweep", "E": "Lethal Counter", "R": "Berserker Rage",
                "hints": {"Q": "突进+减速", "W": "旋转+范围", "E": "吸血+攻速", "R": "范围+斩杀"}},
    "Bane": {"Q": "Shark Bite", "W": "Ale", "E": "Deadly Catch", "R": "Crab Claw Cannon",
             "hints": {"Q": "远程+减速", "W": "治疗+加速", "E": "钩子+眩晕", "R": "范围+远程"}},
    "Barats": {"Q": "I'm Big!", "W": "So-Called Teamwork", "E": "Missile Expert", "R": "Detona's Welcome",
               "hints": {"Q": "吞噬+变身", "W": "击飞+突进", "E": "远程+减速", "R": "范围+眩晕"}},
    "Baxia": {"Q": "Baxia's Unity", "W": "Shield of the Just", "E": "Tortoise Charge", "R": "Guardian Spirit",
              "hints": {"Q": "范围+减速", "W": "护盾+减伤", "E": "突进+击退", "R": "护盾+全队"}},
    "Beatrix": {"Q": "Renner/Wesker/Nibiru", "W": "Tactical Reposition", "E": "Mechanical Genius", "R": "Special Ammo",
                "hints": {"Q": "远程+切换", "W": "位移+后跳", "E": "暴击+强化", "R": "范围+远程"}},
    "Belerick": {"Q": "Nature's Vengeance", "W": "Wrath of the Forest", "E": "Ancient Roots", "R": "Healing Seed",
                 "hints": {"Q": "范围+嘲讽", "W": "护盾+反击", "E": "禁锢+眩晕", "R": "治疗+范围"}},
    "Benedetta": {"Q": "Elapsed Daytime", "W": "An Eye for an Eye", "E": "Shadow Slash", "R": "Moonlit Dance",
                  "hints": {"Q": "突进+穿刺", "W": "格挡+反击", "E": "范围+挥砍", "R": "位移+斩击+霸体"}},
    "Brody": {"Q": "Abyss Impact", "W": "Corrosive Strike", "E": "Torn-Apart Memory", "R": "Deadly Blow",
              "hints": {"Q": "范围+远程", "W": "减速+标记", "E": "位移+眩晕", "R": "远程+斩杀"}},
    "Bruno": {"Q": "Volley Shot", "W": "Flying Tackle", "E": "Power Shot", "R": "Worldie",
              "hints": {"Q": "远程+范围", "W": "位移+眩晕", "E": "击退+远程", "R": "远程+眩晕+全图"}},
    "Carmilla": {"Q": "Crimson Flower", "W": "Bloodbath", "E": "Vampire Pact", "R": "Curse of Blood",
                 "hints": {"Q": "范围+吸血", "W": "减速+范围", "E": "护盾+链接", "R": "范围+禁锢+眩晕"}},
    "Cecilion": {"Q": "Fallen Ones", "W": "Sanguine Rose", "E": "Bat Swarm", "R": "Moonlit Waltz",
                 "hints": {"Q": "远程+弹跳", "W": "禁锢+远程", "E": "位移+加速", "R": "范围+全图"}},
    "Chang'e": {"Q": "Starmoon Shockwave", "W": "Crescent Moon", "E": "Lunar Orbit", "R": "Meteor Shower",
                "hints": {"Q": "远程+减速", "W": "护盾+加速", "E": "范围+灼烧", "R": "范围+持续+远程"}},
    "Chip": {"Q": "Chip Away", "W": "Recycle", "E": "Scrap Shield", "R": "Scrap Storm",
             "hints": {"Q": "远程+标记", "W": "回复+加速", "E": "护盾+减伤", "R": "范围+弹跳"}},
    "Cici": {"Q": "Yo-Yo Strike", "W": "Bounce", "E": "String Snap", "R": "Yo-Yo Frenzy",
             "hints": {"Q": "远程+弹跳", "W": "位移+加速", "E": "禁锢+减速", "R": "范围+连击"}},
    "Claude": {"Q": "Art of Thievery", "W": "Battle Mirror Image", "E": "Burning Aroma", "R": "Blazing Duet",
               "hints": {"Q": "远程+攻速", "W": "分身+位移", "E": "加速+护盾", "R": "范围+分身+连击"}},
    "Cyclops": {"Q": "Stardust Shock", "W": "Planets Attack", "E": "Star Power", "R": "Stellar Burst",
                "hints": {"Q": "远程+弹跳", "W": "范围+减速", "E": "攻速+强化", "R": "范围+禁锢"}},
    "Diggie": {"Q": "Auto Alarm Bomb", "W": "Reverse Time", "E": "Time Journey", "R": "Time Freeze",
               "hints": {"Q": "召唤+灼烧", "W": "护盾+净化", "E": "位移+加速", "R": "范围+禁锢+净化"}},
    "Dyrroth": {"Q": "Burst Strike", "W": "Spectre Step", "E": "Circle of Fate", "R": "Abysm Strike",
                "hints": {"Q": "突进+范围", "W": "位移+穿刺", "E": "范围+吸血", "R": "突进+斩杀"}},
    "Edith": {"Q": "Overload", "W": "Lightning Bolt", "E": "Ion Cannon", "R": "Primal Wrath",
              "hints": {"Q": "闪电+范围", "W": "眩晕+远程", "E": "远程+击退", "R": "变身+击飞+范围"}},
    "Esmeralda": {"Q": "Frostmoon Shield", "W": "Stardust Dance", "E": "Falling Comet", "R": "Frostmoon's Wrath",
                  "hints": {"Q": "护盾+减速", "W": "位移+范围", "E": "远程+击飞", "R": "范围+禁锢"}},
    "Estes": {"Q": "Moonlight Immersion", "W": "Domain of Moon Goddess", "E": "Scripture of the Moon Elf",
              "R": "Blessing of Moon Goddess",
              "hints": {"Q": "治疗+链接", "W": "范围+治疗", "E": "减速+护盾", "R": "治疗+全队"}},
    "Faramis": {"Q": "Shadow Stampede", "W": "Ghost Bursters", "E": "Nether Realm", "R": "Cult Altar",
                "hints": {"Q": "范围+击退", "W": "召唤+范围", "E": "位移+护盾", "R": "复活+全队"}},
    "Floryn": {"Q": "Sow", "W": "Sprout", "E": "Bloom", "R": "Harvest",
               "hints": {"Q": "远程+治疗", "W": "眩晕+范围", "E": "护盾+加速", "R": "治疗+全队"}},
    "Fredrinn": {"Q": "Piercing Strike", "W": "Brave Assault", "E": "Energy Eruption", "R": "Appraiser's Wrath",
                 "hints": {"Q": "突进+穿刺", "W": "击飞+范围", "E": "护盾+嘲讽", "R": "范围+眩晕+斩杀"}},
    "Freya": {"Q": "Leap of Faith", "W": "Spirit Combo", "E": "Tempest of Blades", "R": "Valkyrie",
              "hints": {"Q": "突进+击飞", "W": "连击+范围", "E": "护盾+攻速", "R": "范围+击飞"}},
    "Gatotkaca": {"Q": "Blast Iron Fist", "W": "Unbreakable", "E": "Avatar of Guardian", "R": "Wrath of Heaven",
                  "hints": {"Q": "远程+击退", "W": "嘲讽+护盾", "E": "突进+眩晕", "R": "突进+范围+击飞"}},
    "Gloo": {"Q": "Stick-Slip", "W": "Glue Shot", "E": "Gooey Bomb", "R": "Split Split",
             "hints": {"Q": "减速+范围", "W": "禁锢+远程", "E": "范围+灼烧", "R": "分身+连击"}},
    "Gord": {"Q": "Mystic Projectile", "W": "Mystic Injunction", "E": "Mystic Gush", "R": "Mystic Fury",
             "hints": {"Q": "远程+弹跳", "W": "眩晕+范围", "E": "减速+范围", "R": "远程+持续+灼烧"}},
    "Granger": {"Q": "Rhapsody", "W": "Rondo", "E": "Death Sonata", "R": "Capriccio",
                "hints": {"Q": "远程+穿刺", "W": "位移+加速", "E": "范围+击退", "R": "远程+斩杀+范围"}},
}

# ==========================================
# 预置 英魂之刃 技能名映射
# ==========================================
YINGHUN_SKILL_NAMES = {
    "丛林之子": {"Q": "野性投掷", "W": "自然伪装", "E": "兽群呼唤", "R": "丛林之王",
                 "hints": {"Q": "远程+减速", "W": "隐身+加速", "E": "召唤+攻速", "R": "变身+范围"}},
    "二郎神杨戬": {"Q": "天眼通", "W": "七十二变", "E": "三尖两刃", "R": "哮天犬",
                   "hints": {"Q": "远程+视野", "W": "分身+位移", "E": "范围+挥砍", "R": "召唤+突进"}},
    "五彩神石": {"Q": "七彩光华", "W": "金刚不坏", "E": "石破天惊", "R": "女娲神石",
                 "hints": {"Q": "远程+致盲", "W": "护盾+减伤", "E": "范围+眩晕", "R": "范围+治疗"}},
    "亚瑟王": {"Q": "誓约之剑", "W": "骑士荣耀", "E": "圣盾守护", "R": "王者裁决",
               "hints": {"Q": "范围+挥砍", "W": "护盾+嘲讽", "E": "减伤+护盾", "R": "范围+斩杀+眩晕"}},
    "企鹅": {"Q": "冰锥射击", "W": "滑冰突进", "E": "寒冰屏障", "R": "暴风雪",
             "hints": {"Q": "远程+减速", "W": "位移+击退", "E": "护盾+减伤", "R": "范围+冻结"}},
    "八岐大蛇": {"Q": "八岐毒牙", "W": "蛇蜕", "E": "毒雾弥漫", "R": "八岐降临",
                 "hints": {"Q": "毒+远程", "W": "位移+净化", "E": "毒+范围", "R": "变身+毒+范围"}},
    "冥王哈迪斯": {"Q": "冥界之门", "W": "死亡之触", "E": "暗影护盾", "R": "冥王审判",
                   "hints": {"Q": "位移+范围", "W": "远程+吸血", "E": "护盾+恐惧", "R": "范围+斩杀+眩晕"}},
    "冰雪女王": {"Q": "冰霜射线", "W": "冰川路径", "E": "冰晶护盾", "R": "极寒风暴",
                 "hints": {"Q": "远程+减速", "W": "位移+冻结", "E": "护盾+减伤", "R": "范围+冻结+眩晕"}},
    "凯撒大帝": {"Q": "凯撒之矛", "W": "军团冲锋", "E": "帝皇威压", "R": "罗马之怒",
                 "hints": {"Q": "远程+穿刺", "W": "突进+范围", "E": "减速+恐惧", "R": "范围+击飞"}},
    "判官钟馗": {"Q": "判官笔", "W": "勾魂锁", "E": "镇魂印", "R": "轮回审判",
                 "hints": {"Q": "远程+标记", "W": "钩子+眩晕", "E": "范围+沉默", "R": "范围+斩杀"}},
    "司马懿": {"Q": "狼顾之策", "W": "鹰视之谋", "E": "隐忍", "R": "篡政",
               "hints": {"Q": "远程+标记", "W": "视野+减速", "E": "隐身+位移", "R": "范围+斩杀+眩晕"}},
    "周瑜": {"Q": "火攻", "W": "东风", "E": "水军统帅", "R": "火烧赤壁",
             "hints": {"Q": "范围+灼烧", "W": "加速+范围", "E": "护盾+治疗", "R": "范围+灼烧+持续"}},
    "哪吒": {"Q": "乾坤圈", "W": "混天绫", "E": "风火轮", "R": "三头六臂",
             "hints": {"Q": "远程+击退", "W": "禁锢+减速", "E": "加速+位移", "R": "变身+连击+范围"}},
    "图坦卡蒙": {"Q": "法老诅咒", "W": "圣甲虫", "E": "金字塔护盾", "R": "木乃伊之怒",
                 "hints": {"Q": "毒+远程", "W": "召唤+减速", "E": "护盾+反击", "R": "范围+眩晕+缠绕"}},
    "圣女贞德": {"Q": "圣光之矛", "W": "神圣旗帜", "E": "信仰守护", "R": "圣女降临",
                 "hints": {"Q": "远程+光耀", "W": "攻速+光环", "E": "护盾+治疗", "R": "治疗+全队+复活"}},
    "地狱火": {"Q": "地狱烈焰", "W": "熔岩护盾", "E": "陨石冲击", "R": "末日审判",
               "hints": {"Q": "范围+灼烧", "W": "护盾+灼烧", "E": "突进+击飞", "R": "范围+灼烧+眩晕"}},
    "地狱领主": {"Q": "死亡缠绕", "W": "骸骨之盾", "E": "冥界光环", "R": "亡灵大军",
                 "hints": {"Q": "远程+吸血", "W": "护盾+减伤", "E": "减速+光环", "R": "召唤+范围"}},
    "埃及艳后": {"Q": "魅惑之舞", "W": "蛇蝎美人", "E": "尼罗河祝福", "R": "艳后之怒",
                 "hints": {"Q": "魅惑+远程", "W": "毒+减速", "E": "治疗+护盾", "R": "范围+魅惑"}},
    "大天使": {"Q": "圣光裁决", "W": "天使之翼", "E": "神圣庇护", "R": "审判之光",
               "hints": {"Q": "远程+光耀", "W": "位移+加速", "E": "护盾+治疗", "R": "范围+光耀+全队"}},
    "天蓬元帅": {"Q": "九齿钉耙", "W": "天罡三十六变", "E": "天河水军", "R": "猪突猛进",
                 "hints": {"Q": "范围+挥砍", "W": "分身+位移", "E": "护盾+减伤", "R": "突进+击飞+范围"}},
    "奥丁": {"Q": "永恒之枪", "W": "渡鸦之眼", "E": "英灵殿护盾", "R": "诸神黄昏",
             "hints": {"Q": "远程+穿刺", "W": "视野+标记", "E": "护盾+减伤", "R": "范围+眩晕+强化"}},
    "女武神": {"Q": "女武神之矛", "W": "瓦尔基里冲锋", "E": "英灵祝福", "R": "女武神降临",
               "hints": {"Q": "远程+穿刺", "W": "突进+击飞", "E": "治疗+攻速", "R": "范围+治疗+强化"}},
    "嫦娥": {"Q": "月华", "W": "玉兔", "E": "广寒宫", "R": "奔月",
             "hints": {"Q": "远程+减速", "W": "召唤+减速", "E": "护盾+减伤", "R": "位移+范围+治疗"}},
    "孙尚香": {"Q": "红莲箭", "W": "千金一掷", "E": "灵巧翻滚", "R": "枭姬",
               "hints": {"Q": "远程+穿刺", "W": "范围+减速", "E": "位移+加速", "R": "范围+连击"}},
    "小乔": {"Q": "扇舞", "W": "落樱", "E": "琴心", "R": "天香",
             "hints": {"Q": "远程+范围", "W": "减速+范围", "E": "护盾+治疗", "R": "范围+治疗+魅惑"}},
    "小龙女": {"Q": "玉女剑法", "W": "古墓派轻功", "E": "玉蜂针", "R": "左右互搏",
               "hints": {"Q": "连击+挥砍", "W": "位移+加速", "E": "远程+毒", "R": "连击+攻速+分身"}},
    "山丘之王": {"Q": "雷霆之锤", "W": "风暴之锤", "E": "山丘护盾", "R": "天神下凡",
                 "hints": {"Q": "远程+眩晕", "W": "范围+击退", "E": "护盾+减伤", "R": "变身+霸体+强化"}},
    "布丁": {"Q": "布丁弹射", "W": "果冻护盾", "E": "糖浆陷阱", "R": "布丁炸弹",
             "hints": {"Q": "远程+弹跳", "W": "护盾+减伤", "E": "减速+禁锢", "R": "范围+眩晕"}},
    "布鲁": {"Q": "暗影突刺", "W": "暗影步", "E": "暗影之刃", "R": "暗影风暴",
             "hints": {"Q": "突进+穿刺", "W": "隐身+加速", "E": "标记+暴击", "R": "范围+连击"}},
    "小鹿": {"Q": "自然之触", "W": "魅惑", "E": "自然之力", "R": "森林之怒",
             "hints": {"Q": "治疗+远程", "W": "魅惑+控制", "E": "加速+攻速", "R": "范围+治疗"}},
    "斯巴达": {"Q": "斯巴达之矛", "W": "盾牌猛击", "E": "战斗怒吼", "R": "斯巴达之怒",
               "hints": {"Q": "远程+穿刺", "W": "眩晕+击退", "E": "护盾+攻速", "R": "范围+击飞+强化"}},
    "死亡骑士": {"Q": "死亡缠绕", "W": "亡者大军", "E": "不死亡灵", "R": "死亡凋零",
                 "hints": {"Q": "远程+吸血", "W": "召唤+范围", "E": "护盾+减伤", "R": "范围+毒+减速"}},
    "狼王沃夫": {"Q": "狼牙撕咬", "W": "狼群召唤", "E": "嗜血", "R": "狼王变身",
                 "hints": {"Q": "突进+流血", "W": "召唤+范围", "E": "吸血+攻速", "R": "变身+加速+强化"}},
    "疯狂博士": {"Q": "疯狂药剂", "W": "实验体", "E": "基因突变", "R": "疯狂实验室",
                 "hints": {"Q": "远程+毒", "W": "召唤+眩晕", "E": "变身+攻速", "R": "范围+毒+眩晕"}},
    "红炎双刃": {"Q": "烈焰斩", "W": "火焰冲锋", "E": "燃烧之盾", "R": "炎爆",
                 "hints": {"Q": "范围+灼烧", "W": "突进+击退", "E": "护盾+灼烧", "R": "范围+灼烧+眩晕"}},
    "黑胡子船长": {"Q": "加农炮轰", "W": "朗姆酒", "E": "海盗钩", "R": "黑珍珠号",
                   "hints": {"Q": "远程+范围", "W": "治疗+加速", "E": "钩子+眩晕", "R": "范围+击飞"}},
    "精灵王子": {"Q": "精灵箭矢", "W": "森林之跃", "E": "风之祝福", "R": "精灵风暴",
                 "hints": {"Q": "远程+穿刺", "W": "位移+后跳", "E": "加速+攻速", "R": "范围+箭雨"}},
    "金乌": {"Q": "太阳射线", "W": "三足金乌", "E": "日冕护盾", "R": "太阳风暴",
             "hints": {"Q": "远程+灼烧", "W": "范围+致盲", "E": "护盾+灼烧", "R": "范围+灼烧+致盲"}},
    "猎魔人": {"Q": "圣银弩箭", "W": "恶魔猎手", "E": "追踪标记", "R": "猎魔时刻",
               "hints": {"Q": "远程+穿刺", "W": "位移+加速", "E": "标记+暴击", "R": "攻速+连击"}},
    "李探花": {"Q": "小李飞刀", "W": "探花步", "E": "醉拳", "R": "飞刀绝技",
               "hints": {"Q": "远程+穿刺", "W": "位移+闪避", "E": "攻速+暴击", "R": "远程+斩杀+标记"}},
}


# 尝试从扩展数据覆盖
try:
    from skill_data_extended import SKILL_MAPS as EXTENDED_SKILL_MAPS
    DOTA2_SKILL_NAMES = EXTENDED_SKILL_MAPS.get("dota2", DOTA2_SKILL_NAMES)
    MLBB_SKILL_NAMES = EXTENDED_SKILL_MAPS.get("mlbb", MLBB_SKILL_NAMES)
    YINGHUN_SKILL_NAMES = EXTENDED_SKILL_MAPS.get("yinghun", YINGHUN_SKILL_NAMES)
    print("Loaded extended skill maps.")
except ImportError:
    print("Extended skill maps not found, using built-in.")


if __name__ == "__main__":
    print("Batch skill generator loaded.")
    print(f"DOTA2_SKILL_NAMES: {len(DOTA2_SKILL_NAMES)} heroes")
    print(f"MLBB_SKILL_NAMES: {len(MLBB_SKILL_NAMES)} heroes")
    print(f"YINGHUN_SKILL_NAMES: {len(YINGHUN_SKILL_NAMES)} heroes")
