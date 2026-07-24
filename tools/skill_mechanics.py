#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MOBA → D&D 5e 技能机制映射引擎

将 "Q:致命打击-沉默+加速" 这样的描述字符串，
转换为 D&D 5e 结构化技能数据：伤害骰、豁免检定、附加效果、冷却等。

核心思路：
  1. 关键词解析 → 识别伤害类型、效果类型、目标类型
  2. 职业匹配 → 根据角色定位选择合适的伤害骰和DC公式
  3. D&D 参考 → 类似法术/特性映射到 d20 系统数值
"""

import re
import random
from typing import Dict, List, Optional

# ==========================================
# 技能结构化 Schema
# ==========================================
# 最终产出的技能格式：
# {
#     "name": "致命打击",
#     "key": "Q",
#     "type": "物理",              # 物理 / 法术
#     "action": "动作",            # 动作 / 附赠动作 / 反应
#     "range": "近战",            # 近战 / 远程 / 自身
#     "target": "单体",           # 单体 / 范围 / 自身
#     "aoe_radius": null,         # 范围技能半径(尺)
#
#     "damage": {                  # 伤害骰
#         "dice_count": 1,
#         "dice_size": 8,
#         "bonus_attr": "STR",     # 伤害加值属性
#         "type": "挥砍",          # D&D 伤害类型
#     },
#
#     "saving_throw": {            # 豁免检定（可选，None=自动命中）
#         "attr": "CON",           # 豁免属性
#         "dc_formula": "8+PROF+STR",  # DC 公式
#         "on_save": "半伤",       # 半伤 / 无效 / 部分
#     },
#
#     "effects": [                 # 附加效果列表
#         {"type": "沉默", "duration": 1, "target": "敌方", "dc_attr": null},
#         {"type": "加速", "duration": 1, "target": "自身", "value": 10},
#     ],
#
#     "cooldown": 0,              # 冷却回合数
#     "description": "完整的D&D风味描述"
# }

# ==========================================
# D&D 伤害类型
# ==========================================
PHYSICAL_DMG_TYPES = ["挥砍", "穿刺", "钝击"]
MAGICAL_DMG_TYPES = ["火焰", "寒冷", "闪电", "雷鸣", "毒素", "强酸", "力场", "光耀", "黯蚀", "心灵"]

# ==========================================
# 职业 → 技能骰子模板
# ==========================================
# 不同职业的基础技能伤害骰不同
CLASS_DAMAGE_DICE = {
    "tank":     {"melee": (1, 10), "spell": (1, 6)},   # 坦克：高基础伤害骰
    "fighter":  {"melee": (1, 8),  "spell": (1, 6)},   # 战士
    "assassin": {"melee": (1, 6),  "spell": (1, 4)},   # 刺客：依赖暴击而非骰子
    "mage":     {"melee": (1, 4),  "spell": (1, 8)},   # 法师：法术为主
    "marksman": {"melee": (1, 8),  "spell": (1, 6)},   # 射手
    "support":  {"melee": (1, 6),  "spell": (1, 6)},   # 辅助
}

# 技能位 → 骰子数量乘数
SKILL_TIER_MULT = {
    0: 1.0,   # 普攻 / Q
    1: 1.5,   # W
    2: 1.2,   # E
    3: 2.5,   # R（大招）
}

# ==========================================
# 关键词 → D&D 机制映射
# ==========================================

# 效果关键词映射
EFFECT_KEYWORDS = {
    # 控制类
    "沉默":   {"type": "沉默", "duration": 1, "dc_attr": "CON", "desc": "目标无法施法/使用法术技能"},
    "眩晕":   {"type": "眩晕", "duration": 1, "dc_attr": "CON", "desc": "目标失去动作"},
    "击飞":   {"type": "击飞", "duration": 1, "dc_attr": "STR", "desc": "目标被击飞，失去动作"},
    "击退":   {"type": "击退", "duration": 1, "dc_attr": "STR", "desc": "目标被推开10尺"},
    "冻结":   {"type": "麻痹", "duration": 1, "dc_attr": "CON", "desc": "目标被冻结，无法行动"},
    "禁锢":   {"type": "束缚", "duration": 1, "dc_attr": "STR", "desc": "目标无法移动"},
    "嘲讽":   {"type": "魅惑", "duration": 1, "dc_attr": "WIS", "desc": "目标必须攻击施法者"},
    "魅惑":   {"type": "魅惑", "duration": 2, "dc_attr": "WIS", "desc": "目标被魅惑"},
    "恐惧":   {"type": "恐惧", "duration": 1, "dc_attr": "WIS", "desc": "目标陷入恐惧"},
    "减速":   {"type": "减速", "duration": 2, "dc_attr": None, "desc": "目标速度减半"},
    "致盲":   {"type": "目盲", "duration": 1, "dc_attr": "CON", "desc": "目标陷入目盲"},

    # 增益类
    "加速":   {"type": "加速", "duration": 2, "value": 15, "desc": "速度+15尺"},
    "护盾":   {"type": "护盾", "duration": 2, "value_formula": "2*LVL+CHA", "desc": "获得临时生命"},
    "减伤":   {"type": "减伤", "duration": 2, "value": 50, "desc": "受到伤害减半"},
    "治疗":   {"type": "治疗", "value_formula": "1d8+WIS", "desc": "恢复生命"},
    "回复":   {"type": "治疗", "value_formula": "1d6+WIS", "desc": "恢复生命"},
    "吸血":   {"type": "吸血", "value": 30, "desc": "造成伤害的30%转化为治疗"},
    "隐身":   {"type": "隐形", "duration": 2, "desc": "变为隐形"},
    "霸体":   {"type": "免疫控制", "duration": 1, "desc": "免疫控制效果"},
    "净化":   {"type": "净化", "desc": "移除负面效果"},
    "攻速":   {"type": "攻速强化", "duration": 2, "value": 30, "desc": "攻击速度+30%"},
    "暴击":   {"type": "暴击强化", "duration": 2, "value_formula": "PROF*5", "desc": "暴击率提升"},

    # 伤害类
    "斩杀":   {"type": "斩杀", "threshold": 30, "desc": "目标生命<30%时伤害翻倍"},
    "灼烧":   {"type": "持续伤害", "duration": 2, "dmg_per_turn": "1d4", "desc": "每回合受到火焰伤害"},
    "毒":     {"type": "持续伤害", "duration": 3, "dmg_per_turn": "1d4", "desc": "每回合受到毒素伤害"},
    "真伤":   {"type": "真实伤害", "desc": "无视护甲和魔抗"},
    "标记":   {"type": "标记", "duration": 3, "desc": "标记目标，后续攻击增伤"},

    # 位移类
    "突进":   {"type": "位移", "value": 30, "desc": "向目标方向移动30尺"},
    "冲刺":   {"type": "位移", "value": 30, "desc": "向目标方向移动30尺"},
    "位移":   {"type": "位移", "value": 20, "desc": "短距离传送/移动"},
    "闪现":   {"type": "位移", "value": 60, "desc": "传送至可见位置"},
    "翻滚":   {"type": "位移", "value": 15, "desc": "向任意方向翻滚15尺"},
    "后跳":   {"type": "位移", "value": 20, "desc": "向后跳跃20尺"},
    "换位":   {"type": "换位", "desc": "与目标交换位置"},

    # 特殊机制
    "分身":   {"type": "分身", "duration": 3, "desc": "召唤一个镜像分身"},
    "变身":   {"type": "变身", "duration": 3, "desc": "变身为强化形态"},
    "钩子":   {"type": "钩拽", "dc_attr": "DEX", "desc": "将目标拉向自己"},
    "复活":   {"type": "复活", "desc": "复活一名友方单位"},

    # 多段攻击
    "多段":   {"type": "连击", "value": 3, "desc": "多次攻击"},
    "三段":   {"type": "连击", "value": 3, "desc": "三段攻击"},
    "五段":   {"type": "连击", "value": 5, "desc": "五段攻击"},
    "旋转":   {"type": "范围攻击", "desc": "攻击周围所有敌人"},
    "环形":   {"type": "地形", "desc": "创造环形障碍"},
    "全图":   {"type": "全图", "desc": "影响整个战场"},
    "飞行物": {"type": "格挡远程", "desc": "摧毁飞行中的远程攻击"},
    "视野":   {"type": "侦查", "duration": 5, "desc": "获得区域视野"},
    "回复":   {"type": "治疗", "value_formula": "1d6+WIS", "desc": "恢复生命"},
}

# 伤害类型关键词映射
DMG_TYPE_KEYWORDS = {
    "火": "火焰", "火焰": "火焰", "灼烧": "火焰", "烧": "火焰",
    "冰": "寒冷", "冰冻": "寒冷", "冰冻": "寒冷", "冻": "寒冷",
    "电": "闪电", "闪电": "闪电", "雷": "闪电", "雷电": "闪电",
    "毒": "毒素", "毒素": "毒素",
    "暗": "黯蚀", "暗影": "黯蚀", "黑暗": "黯蚀",
    "光": "光耀", "圣光": "光耀", "神圣": "光耀",
    "斩": "挥砍", "砍": "挥砍", "劈": "挥砍", "刃": "挥砍",
    "刺": "穿刺", "箭": "穿刺", "枪": "穿刺",
    "锤": "钝击", "砸": "钝击", "拳": "钝击", "掌": "钝击",
}

# 范围关键词 → AOE 半径
AOE_KEYWORDS = {
    "范围": 15, "扇形": 15, "锥形": 15, "圆形": 10,
    "全图": None, "全屏": None,
    "弹跳": 30, "弹射": 20,
    "大范围": 20, "群体": 15,
    "全队": None, "多目标": 15,
}


# ==========================================
# 技能字符串 → 结构化 D&D 技能 转换器
# ==========================================

def parse_skill_string(skill_str: str) -> dict:
    """
    解析 "Q:致命打击-沉默+加速" / "1:誓约之盾-沉默突进" 等格式。
    返回中间表示：{"key": "Q", "name": "致命打击", "keywords": ["沉默", "加速"], "desc": "..."}
    """
    result = {"key": "", "name": "", "keywords": [], "desc": ""}

    # 提取技能键位
    key_match = re.match(r'^([A-Za-z0-9]+)[:：]', skill_str)
    if key_match:
        result["key"] = key_match.group(1)
        remaining = skill_str[key_match.end():]
    else:
        remaining = skill_str

    # 分离名称和描述
    if "-" in remaining:
        parts = remaining.split("-", 1)
        result["name"] = parts[0].strip()
        desc_part = parts[1]
    elif "——" in remaining:
        parts = remaining.split("——", 1)
        result["name"] = parts[0].strip()
        desc_part = parts[1]
    else:
        result["name"] = remaining.strip()
        return result

    # 解析关键词（用 + / / 分隔）
    keyword_tokens = re.split(r'[+/、]', desc_part)
    for token in keyword_tokens:
        token = token.strip()
        if not token:
            continue
        # 去除纯描述性噪声词
        noise = {"伤害", "攻击", "强化", "单体", "远程", "近战", "技能", "形态", "切换",
                 "范围", "职业", "法伤", "物理", "法术", "击"}
        if token in noise:
            continue
        # 过滤纯单字符噪声
        if len(token) <= 1 and token not in EFFECT_KEYWORDS and token not in DMG_TYPE_KEYWORDS:
            continue
        result["keywords"].append(token)

    result["desc"] = desc_part
    return result


def build_dnd_skill(parsed: dict, role: str, skill_index: int, hero_name: str = "") -> dict:
    """
    将解析后的技能字符串构建为完整的 D&D 结构化技能。

    参数:
        parsed: parse_skill_string 的输出
        role: 英雄的通用定位 (tank/fighter/assassin/mage/marksman/support)
        skill_index: 技能位 (0=Q/普攻, 1=W, 2=E, 3=R/大招)
        hero_name: 英雄名（用于个性化）
    """
    key = parsed["key"]
    name = parsed["name"]
    keywords = parsed["keywords"]

    # 1. 判断技能类型（物理/法术）
    if role == "mage":
        skill_type = "法术"
    else:
        skill_type = "物理"

    # 2. 判断范围和目标
    is_ranged = any(k in keywords for k in ["远程", "射", "枪", "箭", "炮", "镖", "弹", "poke",
                                              "狙击", "飞", "投", "宝珠", "流星", "暗杀",
                                              "飞弹", "手里剑", "飞镖", "光束", "激光"])
    is_self = any(k in keywords for k in ["自身", "脱战", "回复", "防御", "格挡", "减伤",
                                            "韧性", "回血", "治疗"])
    is_aoe = False
    aoe_radius = None

    for kw, radius in AOE_KEYWORDS.items():
        if kw in keywords or kw in parsed["desc"]:
            is_aoe = True
            aoe_radius = radius
            break

    # 3. 确定伤害骰
    dice_pool = CLASS_DAMAGE_DICE.get(role, CLASS_DAMAGE_DICE["fighter"])
    if skill_type == "法术":
        base_dice = dice_pool["spell"]
    elif is_ranged:
        base_dice = (1, 8)  # 远程武器标准
    else:
        base_dice = dice_pool["melee"]

    mult = SKILL_TIER_MULT.get(skill_index, 1.0)
    dice_count = max(1, round(base_dice[0] * mult))
    dice_size = base_dice[1]

    # 大招升级骰子
    if skill_index == 3:
        if dice_size <= 6:
            dice_size += 2
        elif dice_size <= 8:
            dice_size += 2

    # 确定伤害加值属性
    if skill_type == "法术":
        bonus_attr = "INT"
    elif role in ("assassin", "marksman"):
        bonus_attr = "DEX"
    else:
        bonus_attr = "STR"

    # 4. 确定伤害类型
    dmg_type = "挥砍"  # 默认
    for kw, dt in DMG_TYPE_KEYWORDS.items():
        if kw in keywords or kw in name:
            dmg_type = dt
            break
    if skill_type == "法术" and dmg_type in PHYSICAL_DMG_TYPES:
        dmg_type = "力场"  # 法术默认力场伤害

    # 5. 解析附加效果
    effects = []
    for kw in keywords:
        if kw in EFFECT_KEYWORDS:
            effect_def = EFFECT_KEYWORDS[kw].copy()
            eff = {
                "type": effect_def["type"],
                "desc": effect_def.get("desc", ""),
            }
            if "duration" in effect_def:
                eff["duration"] = effect_def["duration"]
            if "dc_attr" in effect_def and effect_def["dc_attr"]:
                eff["dc_attr"] = effect_def["dc_attr"]
            if "value" in effect_def:
                eff["value"] = effect_def["value"]
            if "value_formula" in effect_def:
                eff["value_formula"] = effect_def["value_formula"]
            if "threshold" in effect_def:
                eff["threshold"] = effect_def["threshold"]
            if "dmg_per_turn" in effect_def:
                eff["dmg_per_turn"] = effect_def["dmg_per_turn"]

            # 确定效果目标
            beneficial = effect_def["type"] in ("加速", "护盾", "减伤", "治疗", "回复",
                                                  "吸血", "隐身", "霸体", "净化", "攻速",
                                                  "暴击", "暴击强化", "攻速强化", "免疫控制",
                                                  "复活", "隐形")
            displacement = effect_def["type"] in ("位移", "换位")
            eff["target"] = "自身" if (beneficial or displacement) else "敌方"
            effects.append(eff)

    # 6. 构建豁免检定（有控制效果时需要）
    saving_throw = None
    control_effects = [e for e in effects if e.get("dc_attr")]
    if control_effects:
        dc_attr = control_effects[0]["dc_attr"]
        if skill_type == "法术":
            dc_formula = f"8+PROF+INT"
        elif role in ("assassin", "marksman"):
            dc_formula = f"8+PROF+DEX"
        else:
            dc_formula = f"8+PROF+STR"
        saving_throw = {
            "attr": dc_attr,
            "dc_formula": dc_formula,
            "on_save": "无效",
        }

    # 7. 冷却
    cooldowns = {0: 0, 1: 1, 2: 2, 3: 4}
    cooldown = cooldowns.get(skill_index, 0)

    # 8. 范围和目标确定
    if is_self:
        range_type = "自身"
        target_type = "自身"
    elif is_ranged:
        range_type = f"{30 + aoe_radius * 2}尺" if aoe_radius else "60尺"
        target_type = "范围" if is_aoe else "单体"
    else:
        range_type = "近战"
        target_type = "范围" if is_aoe else "单体"

    # 9. 构建描述
    dmg_desc = f"{dice_count}d{dice_size}+{bonus_attr}"
    desc_parts = [f"{dmg_desc} {dmg_type}伤害"]
    for eff in effects:
        dur = f"{eff['duration']}回合" if eff.get("duration") else ""
        desc_parts.append(f"{eff['desc']}{dur}")
    description = "。".join(desc_parts) + "。"

    skill = {
        "name": name,
        "key": key,
        "type": skill_type,
        "action": "动作",
        "range": range_type,
        "target": target_type,
        "damage": {
            "dice_count": dice_count,
            "dice_size": dice_size,
            "bonus_attr": bonus_attr,
            "type": dmg_type,
        },
        "effects": effects,
        "cooldown": cooldown,
        "description": description,
    }

    if saving_throw:
        skill["saving_throw"] = saving_throw
    if aoe_radius:
        skill["aoe_radius"] = aoe_radius

    return skill


def convert_skill_to_dnd(skill_str: str, role: str, skill_index: int, hero_name: str = "") -> dict:
    """一键转换：字符串技能 → D&D 结构化技能"""
    parsed = parse_skill_string(skill_str)
    return build_dnd_skill(parsed, role, skill_index, hero_name)


def convert_skill_set(skill_strings: list, role: str) -> list:
    """批量转换一个英雄的4个技能"""
    result = []
    for i, s in enumerate(skill_strings):
        result.append(convert_skill_to_dnd(s, role, i))
    return result


# ==========================================
# 回退：通用技能模板（结构化版本）
# ==========================================

TEMPLATE_SKILLS_DND = {
    "tank": [
        {"name": "护盾猛击", "key": "Q", "type": "物理", "action": "动作", "range": "近战", "target": "单体",
         "damage": {"dice_count": 1, "dice_size": 10, "bonus_attr": "STR", "type": "钝击"},
         "effects": [{"type": "减速", "duration": 1, "desc": "速度减半", "target": "敌方"}],
         "saving_throw": {"attr": "STR", "dc_formula": "8+PROF+STR", "on_save": "无效"},
         "cooldown": 0, "description": "1d10+STR 钝击伤害。目标需通过STR豁免否则速度减半1回合。"},
    ],
    "fighter": [
        {"name": "旋风斩", "key": "Q", "type": "物理", "action": "动作", "range": "近战", "target": "范围",
         "damage": {"dice_count": 1, "dice_size": 8, "bonus_attr": "STR", "type": "挥砍"},
         "effects": [], "aoe_radius": 5, "cooldown": 0,
         "description": "1d8+STR 挥砍伤害，命中5尺内所有敌人。"},
    ],
    "assassin": [
        {"name": "暗杀", "key": "Q", "type": "物理", "action": "动作", "range": "近战", "target": "单体",
         "damage": {"dice_count": 2, "dice_size": 6, "bonus_attr": "DEX", "type": "穿刺"},
         "effects": [], "cooldown": 0,
         "description": "2d6+DEX 穿刺伤害。若目标生命低于一半，伤害翻倍。"},
    ],
    "mage": [
        {"name": "火球术", "key": "Q", "type": "法术", "action": "动作", "range": "60尺", "target": "范围",
         "damage": {"dice_count": 2, "dice_size": 6, "bonus_attr": "INT", "type": "火焰"},
         "effects": [], "aoe_radius": 10, "saving_throw": {"attr": "DEX", "dc_formula": "8+PROF+INT", "on_save": "半伤"},
         "cooldown": 0, "description": "2d6+INT 火焰伤害，10尺半径范围。DEX豁免减半。"},
    ],
    "marksman": [
        {"name": "穿刺箭", "key": "Q", "type": "物理", "action": "动作", "range": "120尺", "target": "单体",
         "damage": {"dice_count": 1, "dice_size": 8, "bonus_attr": "DEX", "type": "穿刺"},
         "effects": [], "cooldown": 0,
         "description": "1d8+DEX 穿刺伤害，射程120尺。"},
    ],
    "support": [
        {"name": "治疗波", "key": "Q", "type": "法术", "action": "动作", "range": "30尺", "target": "自身",
         "damage": {"dice_count": 1, "dice_size": 8, "bonus_attr": "WIS", "type": "光耀"},
         "effects": [{"type": "治疗", "value_formula": "1d8+WIS", "desc": "恢复生命", "target": "自身"}],
         "cooldown": 0, "description": "恢复1d8+WIS生命值。"},
    ],
}


def get_template_skills_dnd(role: str) -> list:
    """获取 D&D 格式的通用技能模板"""
    templates = TEMPLATE_SKILLS_DND.get(role, TEMPLATE_SKILLS_DND["fighter"])

    # 组装完整4技能
    result = []
    skill_defs = [
        (0, templates[0]),
        (1, {"name": "技能二", "key": "W", "type": templates[0]["type"], "action": "动作",
             "range": templates[0]["range"], "target": templates[0]["target"],
             "damage": {"dice_count": 2, "dice_size": templates[0]["damage"]["dice_size"],
                        "bonus_attr": templates[0]["damage"]["bonus_attr"],
                        "type": templates[0]["damage"]["type"]},
             "effects": [], "cooldown": 1,
             "description": f"2{templates[0]['damage']['dice_size']}+{templates[0]['damage']['bonus_attr']} 伤害。冷却1回合。"}),
        (2, {"name": "技能三", "key": "E", "type": templates[0]["type"], "action": "附赠动作",
             "range": "自身", "target": "自身",
             "damage": {"dice_count": 0, "dice_size": 0, "bonus_attr": "CON", "type": "力场"},
             "effects": [{"type": "加速", "duration": 2, "value": 15, "desc": "速度+15尺", "target": "自身"}],
             "cooldown": 2,
             "description": "自身速度+15尺，持续2回合。冷却2回合。"}),
        (3, {"name": "大招", "key": "R", "type": templates[0]["type"], "action": "动作",
             "range": "60尺", "target": "范围",
             "damage": {"dice_count": 4, "dice_size": templates[0]["damage"]["dice_size"],
                        "bonus_attr": templates[0]["damage"]["bonus_attr"],
                        "type": templates[0]["damage"]["type"]},
             "effects": [], "aoe_radius": 15,
             "saving_throw": {"attr": "DEX", "dc_formula": "8+PROF+INT",
                              "on_save": "半伤"},
             "cooldown": 4,
             "description": f"4{templates[0]['damage']['dice_size']}+{templates[0]['damage']['bonus_attr']} 范围伤害。DEX豁免减半。冷却4回合。"}),
    ]
    for idx, skill in skill_defs:
        result.append(skill)
    return result


# ==========================================
# 演示
# ==========================================

if __name__ == "__main__":
    # 演示几个转换
    examples = [
        ("盖伦", "fighter", ["Q:致命打击-沉默+加速", "W:勇气-减伤+韧性", "E:审判-范围旋转伤害", "R:德玛西亚正义-斩杀"]),
        ("阿狸", "mage",    ["Q:欺诈宝珠-来回法伤", "W:妖异狐火-三团狐火", "E:魅惑妖术-魅惑控制", "R:灵魄突袭-三段冲刺"]),
        ("劫", "assassin",  ["Q:影奥义诸刃-飞镖", "W:影奥义分身-换位", "E:影奥义鬼斩-旋转斩", "R:禁奥义瞬狱影杀阵-死亡印记"]),
        ("石头人", "tank",  ["Q:地震碎片-滚石减速", "W:雷霆拍击-强化普攻", "E:大地震颤-减攻速", "R:势不可挡-冲撞击飞"]),
        ("艾希", "marksman",["Q:射手的专注-箭雨", "W:万箭齐发-扇形减速", "E:鹰击长空-全图视野", "R:魔法水晶箭-远程眩晕"]),
        ("索拉卡", "support",["Q:流星坠落-范围减速+治疗", "W:星之灌注-治疗友军", "E:星体结界-沉默禁锢", "R:祈愿-全图治疗"]),
    ]

    print("=" * 80)
    print("  MOBA → D&D 5e 技能转换演示")
    print("=" * 80)

    for hero_name, role, old_skills in examples:
        print(f"\n{'─' * 60}")
        print(f"  {hero_name} ({role})")
        print(f"{'─' * 60}")
        new_skills = convert_skill_set(old_skills, role)
        for s in new_skills:
            print(f"\n  [{s['key']}] {s['name']}")
            print(f"    类型: {s['type']} | 射程: {s['range']} | 目标: {s['target']}")
            print(f"    伤害: {s['damage']['dice_count']}d{s['damage']['dice_size']}+{s['damage']['bonus_attr']} ({s['damage']['type']})")
            if s.get("saving_throw"):
                st = s["saving_throw"]
                print(f"    豁免: {st['attr']} DC={st['dc_formula']} ({st['on_save']})")
            if s["effects"]:
                for e in s["effects"]:
                    dur = f" {e['duration']}回合" if e.get("duration") else ""
                    print(f"    效果: [{e['target']}]{e['desc']}{dur}")
            print(f"    冷却: {s['cooldown']}回合")
            print(f"    {s['description']}")

    print(f"\n{'─' * 60}")
    print(f"  转换完成！")
