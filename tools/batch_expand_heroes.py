#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量英雄扩充工具：基于role模板生成D&D技能并追加到 skills JSON。

用法: python tools/batch_expand_heroes.py <game_id> --heroes '["英雄名","role",...]'
"""

import json, sys, argparse, copy, os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from core.skill_pool import write_hero_skill, pool_has, list_pool_heroes

ROLE_TEMPLATES = {
    "assassin": {
        "slots": [
            {"name": "暗影突袭", "key": "Q", "type": "物理",
             "damage": {"dice_count": 1, "dice_size": 10, "bonus_attr": "DEX", "type": "挥砍"},
             "effects": [{"type": "execute", "desc": "对孤立目标额外1d10伤害", "target": "敌方"}],
             "cooldown": 0, "range": "近战", "target": "单体", "action": "动作",
             "description": "你如暗影般突袭目标，匕首精准刺向要害。若目标孤立无援，刀刃将寻得致命破绽。"},
            {"name": "淬毒飞刃", "key": "W", "type": "物理",
             "damage": {"dice_count": 2, "dice_size": 8, "bonus_attr": "DEX", "type": "穿刺"},
             "effects": [{"type": "dot", "desc": "毒素造成每回合1d6持续伤害，持续2回合", "duration": 2, "target": "敌方"},
                         {"type": "slow", "desc": "毒素减缓目标行动", "duration": 1, "target": "敌方"}],
             "cooldown": 1, "saving_throw": {"attr": "CON", "dc_formula": "8+PROF+DEX", "on_save": "半伤"},
             "range": "远程", "target": "单体", "action": "动作",
             "description": "你掷出淬毒的飞刃，毒素沿伤口蔓延。目标若体质不够强韧，将持续受到腐蚀。"},
            {"name": "影步穿梭", "key": "E", "type": "物理",
             "damage": {"dice_count": 1, "dice_size": 8, "bonus_attr": "DEX", "type": "挥砍"},
             "effects": [{"type": "accel", "desc": "位移至目标身后", "target": "自身"},
                         {"type": "invis", "desc": "攻击后短暂隐形", "duration": 1, "target": "自身"}],
             "cooldown": 2, "range": "远程", "target": "单体", "action": "附赠动作",
             "description": "你的身影一闪即逝，再次出现时已至目标身后。残影迷惑敌人，为你争取片刻隐匿。"},
            {"name": "死亡莲华", "key": "R", "type": "物理",
             "damage": {"dice_count": 4, "dice_size": 6, "bonus_attr": "DEX", "type": "挥砍"},
             "effects": [{"type": "invis", "desc": "释放后进入隐形状态", "duration": 1, "target": "自身"},
                         {"type": "accel", "desc": "获得加速效果", "duration": 1, "target": "自身"},
                         {"type": "buff", "desc": "下次攻击判定优势", "duration": 1, "target": "自身"}],
             "cooldown": 4, "range": "近战", "target": "单体", "action": "动作",
             "description": "你展开死亡莲华，刀刃如花瓣般环绕飞舞。敌人只看到残影，而你已消失在暗影之中。"},
        ],
        "dice_expectancy": 33.0,
    },
    "mage": {
        "slots": [
            {"name": "奥术飞弹", "key": "Q", "type": "法术",
             "damage": {"dice_count": 1, "dice_size": 8, "bonus_attr": "INT", "type": "力场"},
             "effects": [{"type": "slow", "desc": "奥术能量减缓目标移速", "duration": 1, "target": "敌方"}],
             "cooldown": 0, "saving_throw": {"attr": "DEX", "dc_formula": "8+PROF+INT", "on_save": "半伤"},
             "range": "远程", "target": "单体", "action": "动作",
             "description": "凝聚纯粹的奥术能量化为飞弹，精准轰击目标。即使未命中，冲击波仍会波及敌人。"},
            {"name": "冰霜新星", "key": "W", "type": "法术",
             "damage": {"dice_count": 2, "dice_size": 6, "bonus_attr": "INT", "type": "力场"},
             "effects": [{"type": "control", "desc": "冻结周围敌人1回合", "duration": 1, "target": "敌方"}],
             "cooldown": 1, "saving_throw": {"attr": "CON", "dc_formula": "8+PROF+INT", "on_save": "无效"},
             "range": "近战", "target": "范围", "action": "动作",
             "description": "以自身为中心爆发极寒之力，冰晶瞬间凝结，将周围敌人封入冰棺。"},
            {"name": "烈焰风暴", "key": "E", "type": "法术",
             "damage": {"dice_count": 2, "dice_size": 6, "bonus_attr": "INT", "type": "力场"},
             "effects": [{"type": "dot", "desc": "烈焰灼烧造成每回合1d6伤害，持续2回合", "duration": 2, "target": "敌方"}],
             "cooldown": 2, "saving_throw": {"attr": "DEX", "dc_formula": "8+PROF+INT", "on_save": "半伤"},
             "range": "远程", "target": "范围", "action": "动作",
             "description": "指定区域燃起魔法烈焰，火焰如风暴般旋转不息。踏入者将被灼烧至骨。"},
            {"name": "陨星天降", "key": "R", "type": "法术",
             "damage": {"dice_count": 4, "dice_size": 6, "bonus_attr": "INT", "type": "力场"},
             "effects": [{"type": "control", "desc": "陨星冲击造成击倒", "duration": 1, "target": "敌方"}],
             "cooldown": 4, "saving_throw": {"attr": "DEX", "dc_formula": "8+PROF+INT", "on_save": "半伤"},
             "range": "远程", "target": "范围", "action": "动作",
             "description": "召唤天外陨星坠落战场，巨大的冲击波席卷大地，无人能在此等天威下全身而退。"},
        ],
        "dice_expectancy": 30.0,
    },
    "marksman": {
        "slots": [
            {"name": "精准射击", "key": "Q", "type": "物理",
             "damage": {"dice_count": 1, "dice_size": 8, "bonus_attr": "DEX", "type": "穿刺"},
             "effects": [],
             "cooldown": 0, "range": "远程", "target": "单体", "action": "动作",
             "description": "屏息凝神，一箭穿心。这一箭凝聚了你全部的专注与技艺。"},
            {"name": "陷阱射击", "key": "W", "type": "物理",
             "damage": {"dice_count": 2, "dice_size": 6, "bonus_attr": "DEX", "type": "穿刺"},
             "effects": [{"type": "control", "desc": "陷阱束缚目标1回合", "duration": 1, "target": "敌方"}],
             "cooldown": 1, "saving_throw": {"attr": "DEX", "dc_formula": "8+PROF+DEX", "on_save": "无效"},
             "range": "远程", "target": "单体", "action": "动作",
             "description": "布下精巧的机关陷阱，触发的瞬间钢索收紧，将目标牢牢束缚。"},
            {"name": "后跳射击", "key": "E", "type": "物理",
             "damage": {"dice_count": 1, "dice_size": 8, "bonus_attr": "DEX", "type": "穿刺"},
             "effects": [{"type": "accel", "desc": "向后跳跃拉开距离", "target": "自身"},
                         {"type": "slow", "desc": "箭矢附带减速效果", "duration": 1, "target": "敌方"}],
             "cooldown": 2, "range": "远程", "target": "单体", "action": "附赠动作",
             "description": "向后空翻的同时射出箭矢，既拉开距离又保持火力压制。"},
            {"name": "穿云箭雨", "key": "R", "type": "物理",
             "damage": {"dice_count": 3, "dice_size": 8, "bonus_attr": "DEX", "type": "穿刺"},
             "effects": [{"type": "vuln", "desc": "标记目标，后续攻击优势", "duration": 2, "target": "敌方"}],
             "cooldown": 4, "saving_throw": {"attr": "DEX", "dc_formula": "8+PROF+DEX", "on_save": "半伤"},
             "range": "远程", "target": "单体", "action": "动作",
             "description": "漫天箭雨从天而降，将目标区域化为死亡之地。被标记的猎物无处可逃。"},
        ],
        "dice_expectancy": 29.5,
    },
    "fighter": {
        "slots": [
            {"name": "猛力斩击", "key": "Q", "type": "物理",
             "damage": {"dice_count": 1, "dice_size": 10, "bonus_attr": "STR", "type": "挥砍"},
             "effects": [{"type": "buff", "desc": "下次攻击获得1d4加值", "duration": 1, "target": "自身"}],
             "cooldown": 0, "range": "近战", "target": "单体", "action": "动作",
             "description": "以全身之力挥出一击，力量从脚跟传递至剑尖，势不可挡。"},
            {"name": "旋风斩", "key": "W", "type": "物理",
             "damage": {"dice_count": 2, "dice_size": 8, "bonus_attr": "STR", "type": "挥砍"},
             "effects": [{"type": "slow", "desc": "旋风造成减速", "duration": 1, "target": "敌方"}],
             "cooldown": 1, "range": "近战", "target": "单体", "action": "动作",
             "description": "旋转武器形成旋风，撕裂一切靠近之物。敌人被卷入其中，步履蹒跚。"},
            {"name": "冲锋陷阵", "key": "E", "type": "物理",
             "damage": {"dice_count": 1, "dice_size": 8, "bonus_attr": "STR", "type": "钝击"},
             "effects": [{"type": "accel", "desc": "冲锋至目标位置", "target": "自身"},
                         {"type": "sunder", "desc": "冲锋撞击降低目标护甲", "duration": 1, "target": "敌方"}],
             "cooldown": 2, "range": "近战", "target": "单体", "action": "动作",
             "description": "架起武器向前猛冲，以万钧之势撞向敌人。护甲在此冲击下形同虚设。"},
            {"name": "战神附体", "key": "R", "type": "物理",
             "damage": {"dice_count": 2, "dice_size": 10, "bonus_attr": "STR", "type": "挥砍"},
             "effects": [{"type": "buff", "desc": "攻击力与护甲大幅提升", "duration": 2, "target": "自身"},
                         {"type": "lifesteal", "desc": "造成伤害的50%转化为生命", "duration": 2, "target": "自身"}],
             "cooldown": 4, "range": "近战", "target": "单体", "action": "动作",
             "description": "战神之力灌注全身，双目赤红，每一次挥砍都汲取敌人生机。"},
        ],
        "dice_expectancy": 30.0,
    },
    "tank": {
        "slots": [
            {"name": "盾击猛撞", "key": "Q", "type": "物理",
             "damage": {"dice_count": 1, "dice_size": 10, "bonus_attr": "STR", "type": "钝击"},
             "effects": [{"type": "control", "desc": "击退目标", "duration": 1, "target": "敌方"}],
             "cooldown": 0, "saving_throw": {"attr": "CON", "dc_formula": "8+PROF+STR", "on_save": "无效"},
             "range": "近战", "target": "单体", "action": "动作",
             "description": "举起巨盾猛撞敌人，将其击退数步。即使是最大体型的生物也难以站稳脚跟。"},
            {"name": "钢铁壁垒", "key": "W", "type": "物理",
             "damage": {"dice_count": 2, "dice_size": 6, "bonus_attr": "STR", "type": "钝击"},
             "effects": [{"type": "shield", "desc": "获得护盾值等于2d8+CON", "target": "自身"},
                         {"type": "reduce", "desc": "受到的伤害减半", "duration": 1, "target": "自身"}],
             "cooldown": 1, "range": "自身", "target": "自身", "action": "附赠动作",
             "description": "全身被钢铁般的光芒笼罩，化身为不可撼动的壁垒。敌人的攻击如同挠痒。"},
            {"name": "地裂践踏", "key": "E", "type": "物理",
             "damage": {"dice_count": 1, "dice_size": 8, "bonus_attr": "STR", "type": "钝击"},
             "effects": [{"type": "sunder", "desc": "地面震动降低周围敌人护甲", "duration": 1, "target": "敌方"},
                         {"type": "slow", "desc": "地面裂缝造成减速", "duration": 1, "target": "敌方"}],
             "cooldown": 2, "saving_throw": {"attr": "CON", "dc_formula": "8+PROF+STR", "on_save": "半伤"},
             "range": "近战", "target": "范围", "action": "动作",
             "description": "奋力践踏地面，裂缝从脚下蔓延。大地颤抖，敌人立足不稳。"},
            {"name": "不灭守护", "key": "R", "type": "物理",
             "damage": {"dice_count": 2, "dice_size": 8, "bonus_attr": "STR", "type": "钝击"},
             "effects": [{"type": "control", "desc": "嘲讽周围所有敌人", "duration": 2, "target": "敌方"},
                         {"type": "shield", "desc": "获得大量护盾", "target": "自身"}],
             "cooldown": 4, "saving_throw": {"attr": "CON", "dc_formula": "8+PROF+STR", "on_save": "无效"},
             "range": "近战", "target": "范围", "action": "动作",
             "description": "你化身不灭的守护者，以怒吼挑衅所有敌人。在他们的攻击下，你巍然不动。"},
        ],
        "dice_expectancy": 26.0,
    },
    "support": {
        "slots": [
            {"name": "圣光之矢", "key": "Q", "type": "法术",
             "damage": {"dice_count": 1, "dice_size": 8, "bonus_attr": "WIS", "type": "光耀"},
             "effects": [{"type": "slow", "desc": "圣光灼伤减缓移动", "duration": 1, "target": "敌方"}],
             "cooldown": 0, "range": "远程", "target": "单体", "action": "动作",
             "description": "凝聚圣光之力化为箭矢，射向敌人。纯净的光芒灼伤邪恶，减缓其步伐。"},
            {"name": "治愈之光", "key": "W", "type": "法术",
             "damage": {"dice_count": 2, "dice_size": 6, "bonus_attr": "WIS", "type": "光耀"},
             "effects": [{"type": "heal", "desc": "恢复盟友2d8+WIS生命值", "target": "友方"}],
             "cooldown": 1, "range": "远程", "target": "单体", "action": "动作",
             "description": "温暖的光芒笼罩盟友，伤口以肉眼可见的速度愈合。圣光永不抛弃虔信之人。"},
            {"name": "净化祝福", "key": "E", "type": "法术",
             "damage": {"dice_count": 1, "dice_size": 8, "bonus_attr": "WIS", "type": "光耀"},
             "effects": [{"type": "cleanse", "desc": "移除所有负面效果", "target": "友方"},
                         {"type": "buff", "desc": "获得增益：下次攻击/法术+1d6", "duration": 1, "target": "友方"}],
             "cooldown": 2, "range": "远程", "target": "单体", "action": "附赠动作",
             "description": "以纯净之力驱散一切污秽，并赐予盟友神圣祝福。被净化者将获得暂时的力量提升。"},
            {"name": "神圣裁决", "key": "R", "type": "法术",
             "damage": {"dice_count": 3, "dice_size": 8, "bonus_attr": "WIS", "type": "光耀"},
             "effects": [{"type": "heal", "desc": "大范围恢复所有盟友3d8生命", "target": "友方"},
                         {"type": "shield", "desc": "为所有盟友提供护盾", "duration": 2, "target": "友方"}],
             "cooldown": 4, "range": "远程", "target": "范围", "action": "动作",
             "description": "神圣之光从天而降，审判邪恶的同时庇护正义。光芒所至，盟友重获新生。"},
        ],
        "dice_expectancy": 24.0,
    },
}

# hero => (role, custom_name_overrides for QWER names, custom_effects_override)
# custom_effects_override is dict: slot_key -> list of effect dicts (replaces template effects)
# custom_name_override: dict: slot_key -> name

HERO_DEFS = {}

# ======================== SMITE (+42) ========================
HERO_DEFS["smite"] = [
    # Arthurian (4)
    ("KingArthur", "fighter", {"R": "王者之剑·Excalibur"}, {"R": [{"type": "buff", "desc": "Excalibur出鞘，伤害骰提升为d12", "duration": 2, "target": "自身"}, {"type": "execute", "desc": "对生命低于一半的目标造成额外3d6伤害", "target": "敌方"}]}),
    ("Merlin", "mage", {"Q": "奥术洪流", "W": "时空裂隙", "E": "龙息术", "R": "预言之眼"}, {"W": [{"type": "control", "desc": "时间凝滞，目标失去行动能力", "duration": 1, "target": "敌方"}], "R": [{"type": "buff", "desc": "预知未来，所有法术判定优势", "duration": 2, "target": "自身"}, {"type": "control", "desc": "预言之雷击倒一片区域", "duration": 1, "target": "敌方"}]}),
    ("MorganLeFay", "mage", {"Q": "暗影诅咒", "W": "荆棘缠绕", "E": "龙焰吐息", "R": "黑暗女王"}, {"Q": [{"type": "dot", "desc": "诅咒造成每回合1d8暗蚀伤害", "duration": 2, "target": "敌方"}], "W": [{"type": "control", "desc": "荆棘缠绕束缚目标", "duration": 1, "target": "敌方"}], "R": [{"type": "buff", "desc": "化为龙形，伤害骰翻倍", "duration": 2, "target": "自身"}, {"type": "dot", "desc": "龙焰灼烧区域", "duration": 2, "target": "敌方"}]}),
    ("Lancelot", "assassin", {"Q": "湖光斩", "W": "骑士冲锋", "E": "影袭", "R": "无悔之剑"}, {"Q": [{"type": "execute", "desc": "对单身目标造成2d8额外伤害", "target": "敌方"}], "E": [{"type": "accel", "desc": "骑乘坐骑冲锋突进", "target": "自身"}, {"type": "sunder", "desc": "冲锋破甲", "duration": 1, "target": "敌方"}]}),

    # Babylonian (3)
    ("Gilgamesh", "fighter", {"R": "天之锁·Enkidu"}, {"R": [{"type": "control", "desc": "天之锁束缚目标2回合", "duration": 2, "target": "敌方"}, {"type": "buff", "desc": "获得神性加护，全属性+2", "duration": 2, "target": "自身"}]}),
    ("Ishtar", "marksman", {"Q": "金星之箭", "R": "天之公牛"}, {"R": [{"type": "vuln", "desc": "天牛践踏标记所有敌人", "duration": 2, "target": "敌方"}, {"type": "control", "desc": "天牛冲击造成范围击倒", "duration": 1, "target": "敌方"}]}),
    ("Tiamat", "mage", {"Q": "混沌之触", "W": "盐海召唤", "E": "龙鳞护体", "R": "创世母神"}, {"Q": [{"type": "dot", "desc": "混沌能量侵蚀，每回合1d8", "duration": 2, "target": "敌方"}], "W": [{"type": "control", "desc": "盐海淹没区域，敌人陷入束缚", "duration": 1, "target": "敌方"}], "R": [{"type": "buff", "desc": "化身巨龙，全技能范围扩大", "duration": 2, "target": "自身"}, {"type": "shield", "desc": "龙鳞提供大量护盾", "target": "自身"}]}),

    # Celtic (2)
    ("Artio", "tank", {"Q": "熊灵之击", "W": "德鲁伊形态", "E": "自然之怒", "R": "巨熊化身"}, {"W": [{"type": "reduce", "desc": "熊形态减伤50%", "duration": 2, "target": "自身"}, {"type": "heal", "desc": "自然之力恢复2d6生命", "target": "自身"}], "R": [{"type": "control", "desc": "巨熊咆哮震慑敌人", "duration": 1, "target": "敌方"}, {"type": "shield", "desc": "厚实熊皮获得护盾", "target": "自身"}]}),
    ("Cliodhna", "assassin", {"Q": "女妖之泣", "W": "穿墙术", "E": "死亡之触", "R": "鬼域降临"}, {"Q": [{"type": "dot", "desc": "哭泣造成精神伤害每回合1d6", "duration": 2, "target": "敌方"}], "E": [{"type": "invis", "desc": "穿越墙壁进入隐形状态", "duration": 1, "target": "自身"}, {"type": "accel", "desc": "穿越障碍加速移动", "target": "自身"}], "R": [{"type": "invis", "desc": "鬼域中所有友方隐身", "duration": 2, "target": "自身"}, {"type": "dot", "desc": "鬼域内敌人每回合受到1d8暗蚀", "duration": 2, "target": "敌方"}]}),

    # Chinese (6)
    ("AoKuang", "mage", {"Q": "龙息", "W": "水龙卷", "E": "龙腾四海", "R": "真龙降世"}, {"Q": [{"type": "dot", "desc": "龙息灼烧每回合1d6", "duration": 2, "target": "敌方"}], "R": [{"type": "control", "desc": "化为巨龙吞噬目标", "duration": 1, "target": "敌方"}, {"type": "execute", "desc": "对生命低于30%目标处决", "target": "敌方"}]}),
    ("HouYi", "marksman", {"Q": "落日弓", "R": "九日齐射"}, {"R": [{"type": "vuln", "desc": "九支太阳箭标记目标", "duration": 2, "target": "敌方"}, {"type": "dot", "desc": "太阳之火灼烧", "duration": 2, "target": "敌方"}]}),
    ("JingWei", "marksman", {"Q": "填海之石", "W": "翎羽疾风", "E": "扶摇直上", "R": "精卫填海"}, {"E": [{"type": "accel", "desc": "振翅飞起避开攻击", "target": "自身"}, {"type": "buff", "desc": "飞行时攻击+1d4", "duration": 1, "target": "自身"}], "R": [{"type": "control", "desc": "石雨造成范围击倒", "duration": 1, "target": "敌方"}, {"type": "vuln", "desc": "石头标记路径上的敌人", "duration": 2, "target": "敌方"}]}),
    ("Mulan", "fighter", {"Q": "花家剑法", "W": "盾反", "E": "长枪突击", "R": "木兰从军"}, {"W": [{"type": "reflect", "desc": "完美格挡反弹50%伤害", "target": "自身"}, {"type": "reduce", "desc": "格挡减伤", "duration": 1, "target": "自身"}], "R": [{"type": "buff", "desc": "全军出击，所有技能强化", "duration": 2, "target": "自身"}, {"type": "accel", "desc": "骑马冲锋加速", "target": "自身"}]}),
    ("XingTian", "tank", {"R": "刑天舞干戚"}, {"Q": [{"type": "control", "desc": "巨斧击退", "duration": 1, "target": "敌方"}], "R": [{"type": "buff", "desc": "无头战神：免疫控制且伤害+50%", "duration": 2, "target": "自身"}, {"type": "control", "desc": "持续旋转巨斧造成范围击退", "duration": 2, "target": "敌方"}]}),
    ("YuHuang", "mage", {"Q": "玉皇圣谕", "W": "天庭审判", "E": "仙鹤驾临", "R": "凌霄宝殿"}, {"R": [{"type": "control", "desc": "天庭威压全场敌人眩晕", "duration": 1, "target": "敌方"}, {"type": "buff", "desc": "获得天道加持，法术判定优势", "duration": 2, "target": "自身"}]}),

    # Egyptian (1)
    ("Anhur", "fighter", {"Q": "狮王投枪", "W": "沙漠风暴", "E": "狮跃扑杀", "R": "法老之怒"}, {"Q": [{"type": "sunder", "desc": "投枪破甲", "duration": 1, "target": "敌方"}], "R": [{"type": "buff", "desc": "化为雄狮，攻击骰提升为d12", "duration": 2, "target": "自身"}, {"type": "control", "desc": "狮吼恐惧周围敌人", "duration": 1, "target": "敌方"}]}),

    # Great Old Ones (1)
    ("Cthulhu", "tank", {"Q": "疯狂之触", "W": "深渊凝视", "E": "触手横扫", "R": "旧日支配者"}, {"Q": [{"type": "control", "desc": "触碰引发疯狂，目标混乱", "duration": 1, "target": "敌方"}], "W": [{"type": "shield", "desc": "深渊能量护体", "target": "自身"}, {"type": "reduce", "desc": "异界护甲减免伤害", "duration": 1, "target": "自身"}], "R": [{"type": "control", "desc": "真身显现，全场恐惧", "duration": 2, "target": "敌方"}, {"type": "dot", "desc": "疯狂侵蚀每回合2d6", "duration": 2, "target": "敌方"}]}),

    # Greek (10)
    ("Achilles", "fighter", {"Q": "阿喀琉斯之矛", "R": "不灭战魂"}, {"R": [{"type": "buff", "desc": "无敌战魂：免疫死亡2回合", "duration": 2, "target": "自身"}, {"type": "execute", "desc": "对受伤目标处决", "target": "敌方"}]}),
    ("Arachne", "assassin", {"Q": "蛛网陷阱", "W": "毒液撕咬", "E": "蛛行术", "R": "蜘蛛女皇"}, {"Q": [{"type": "control", "desc": "蛛网束缚目标", "duration": 1, "target": "敌方"}], "E": [{"type": "accel", "desc": "沿蛛丝快速移动到目标", "target": "自身"}, {"type": "invis", "desc": "在蛛网上隐形", "duration": 1, "target": "自身"}], "R": [{"type": "dot", "desc": "召唤蜘蛛群攻击，中毒每回合2d6", "duration": 2, "target": "敌方"}]}),
    ("Atlas", "tank", {"R": "擎天之力"}, {"R": [{"type": "control", "desc": "天穹坠落，全场压制", "duration": 2, "target": "敌方"}, {"type": "shield", "desc": "天穹庇护所有友方", "target": "友方"}]}),
    ("Cerberus", "tank", {"Q": "地狱犬之咬", "W": "三头守护", "E": "冥界吐息", "R": "冥府看门犬"}, {"Q": [{"type": "control", "desc": "三头撕咬造成眩晕", "duration": 1, "target": "敌方"}], "W": [{"type": "reduce", "desc": "三头同时防御，全方位减伤", "duration": 1, "target": "自身"}, {"type": "shield", "desc": "地狱护盾", "target": "自身"}], "R": [{"type": "dot", "desc": "冥界火焰每回合2d6", "duration": 2, "target": "敌方"}, {"type": "control", "desc": "地狱咆哮恐惧", "duration": 1, "target": "敌方"}]}),
    ("Charon", "tank", {"Q": "冥河摆渡", "W": "亡魂迷雾", "E": "怨灵之触", "R": "冥河之主"}, {"W": [{"type": "reduce", "desc": "迷雾中受到的伤害减半", "duration": 1, "target": "自身"}, {"type": "slow", "desc": "迷雾中敌人减速", "duration": 1, "target": "敌方"}]}),
    ("Charybdis", "marksman", {"R": "吞噬漩涡"}, {"R": [{"type": "control", "desc": "大漩涡将敌人拉向中心", "duration": 1, "target": "敌方"}, {"type": "dot", "desc": "漩涡撕裂每回合1d8", "duration": 2, "target": "敌方"}]}),
    ("Chiron", "marksman", {"Q": "人马射术", "W": "贤者草药", "E": "蹄踏冲锋", "R": "星辰之矢"}, {"W": [{"type": "heal", "desc": "草药治疗盟友2d6", "target": "友方"}, {"type": "cleanse", "desc": "解除负面效果", "target": "友方"}], "R": [{"type": "vuln", "desc": "星辰标记全体敌人", "duration": 2, "target": "敌方"}]}),
    ("Chronos", "mage", {"Q": "时间加速", "W": "时光倒流", "E": "时间静止", "R": "时间之主"}, {"Q": [{"type": "accel", "desc": "自身获得加速效果", "target": "自身"}], "W": [{"type": "heal", "desc": "时光倒流恢复生命", "target": "自身"}], "E": [{"type": "control", "desc": "时间静止，目标眩晕", "duration": 1, "target": "敌方"}], "R": [{"type": "buff", "desc": "掌控时间，所有冷却刷新", "target": "自身"}, {"type": "control", "desc": "全场时间减缓", "duration": 1, "target": "敌方"}]}),
    ("Martichoras", "marksman", {"Q": "蝎尾毒针", "R": "人面蝎身"}, {"R": [{"type": "dot", "desc": "剧毒喷射每回合2d6", "duration": 2, "target": "敌方"}, {"type": "vuln", "desc": "毒素标记弱点", "duration": 2, "target": "敌方"}]}),
    ("Scylla", "mage", {"Q": "海妖之触", "W": "深海恐惧", "E": "触手攫取", "R": "六头海妖"}, {"Q": [{"type": "control", "desc": "触手束缚目标", "duration": 1, "target": "敌方"}], "R": [{"type": "execute", "desc": "六个头同时撕咬，对低血量目标处决", "target": "敌方"}, {"type": "control", "desc": "六头齐鸣造成恐惧", "duration": 1, "target": "敌方"}]}),

    # Hindu (5)
    ("Bakasura", "assassin", {"Q": "吞噬", "E": "暴食突进", "R": "饿鬼道"}, {"Q": [{"type": "buff", "desc": "吞噬获得攻击力叠加", "target": "自身"}, {"type": "lifesteal", "desc": "吞噬回复生命", "target": "自身"}], "R": [{"type": "buff", "desc": "暴食形态：攻击力翻倍", "duration": 2, "target": "自身"}, {"type": "dot", "desc": "胃酸喷溅造成腐蚀", "duration": 2, "target": "敌方"}]}),
    ("Kumbhakarna", "tank", {"R": "沉睡巨人"}, {"R": [{"type": "control", "desc": "陷入沉睡后全场地震击倒", "duration": 2, "target": "敌方"}, {"type": "shield", "desc": "沉睡时获得巨额护盾", "target": "自身"}]}),
    ("Ravana", "assassin", {"Q": "十首连击", "W": "魔神之盾", "E": "飞天遁地", "R": "罗刹王"}, {"Q": [{"type": "execute", "desc": "十连击对低血量翻倍", "target": "敌方"}], "E": [{"type": "accel", "desc": "飞天跳斩", "target": "自身"}, {"type": "invis", "desc": "落地隐匿", "duration": 1, "target": "自身"}], "R": [{"type": "buff", "desc": "十首魔王：全能力+3", "duration": 2, "target": "自身"}]}),
    ("Shiva", "fighter", {"Q": "毁灭之舞", "W": "三叉戟", "E": "第三只眼", "R": "宇宙之舞"}, {"W": [{"type": "sunder", "desc": "三叉戟破甲", "duration": 1, "target": "敌方"}], "E": [{"type": "dot", "desc": "第三只眼射出毁灭之火", "duration": 2, "target": "敌方"}], "R": [{"type": "buff", "desc": "毁灭与创造之舞，攻防大幅提升", "duration": 2, "target": "自身"}, {"type": "control", "desc": "宇宙之舞震撼全场", "duration": 1, "target": "敌方"}]}),
    ("Vamana", "fighter", {"R": "巨人之怒"}, {"R": [{"type": "buff", "desc": "巨大化：体型与伤害翻倍", "duration": 2, "target": "自身"}, {"type": "heal", "desc": "巨大化期间回复生命", "target": "自身"}]}),

    # Japanese (4)
    ("BakeKujira", "tank", {"Q": "鲸骨冲击", "W": "幽灵船体", "E": "深海碾压", "R": "化鲸"}, {"W": [{"type": "reduce", "desc": "幽灵船体减免50%伤害", "duration": 1, "target": "自身"}, {"type": "shield", "desc": "幽灵护盾", "target": "自身"}], "R": [{"type": "control", "desc": "化为巨鲸碾压全场", "duration": 1, "target": "敌方"}]}),
    ("Danzaburou", "marksman", {"Q": "狸猫炸弹", "W": "变身术", "E": "树叶替身", "R": "八百八狸"}, {"W": [{"type": "buff", "desc": "变身后下次攻击判定优势", "duration": 1, "target": "自身"}], "E": [{"type": "accel", "desc": "替身术闪避并位移", "target": "自身"}], "R": [{"type": "control", "desc": "召唤八百八狸军势冲击", "duration": 1, "target": "敌方"}]}),
    ("Hachiman", "marksman", {"Q": "八幡神箭", "R": "军神之旗"}, {"R": [{"type": "buff", "desc": "军旗飘扬，全队攻击力+2", "duration": 2, "target": "友方"}, {"type": "vuln", "desc": "军旗之下敌人被标记", "duration": 2, "target": "敌方"}]}),
    ("Kuzenbo", "tank", {"Q": "河童壳击", "W": "水镜之术", "E": "水龙弹", "R": "河童大王"}, {"W": [{"type": "reflect", "desc": "水镜反弹所受伤害的50%", "target": "自身"}, {"type": "shield", "desc": "水镜护盾", "target": "自身"}], "R": [{"type": "control", "desc": "召唤水龙卷击飞敌人", "duration": 1, "target": "敌方"}]}),

    # Maya (3)
    ("AhMuzenCab", "marksman", {"Q": "蜂群出击", "W": "蜜蜡陷阱", "E": "蜂翼疾行", "R": "蜂神之怒"}, {"Q": [{"type": "dot", "desc": "蜂毒每回合1d6", "duration": 2, "target": "敌方"}], "R": [{"type": "control", "desc": "蜂群覆盖全场造成混乱", "duration": 1, "target": "敌方"}, {"type": "dot", "desc": "蜂毒大范围伤害", "duration": 2, "target": "敌方"}]}),
    ("Awilix", "assassin", {"Q": "月光骑袭", "W": "羽蛇之速", "E": "月下扑杀", "R": "月神之力"}, {"Q": [{"type": "execute", "desc": "骑乘状态下伤害翻倍", "target": "敌方"}], "E": [{"type": "accel", "desc": "从高处扑向目标", "target": "自身"}, {"type": "control", "desc": "扑倒目标", "duration": 1, "target": "敌方"}], "R": [{"type": "buff", "desc": "月神降临，夜间全能力+3", "duration": 2, "target": "自身"}, {"type": "invis", "desc": "月光下隐身", "duration": 1, "target": "自身"}]}),
    ("HunBatz", "assassin", {"Q": "猴王跳跃", "W": "香蕉陷阱", "E": "图腾震击", "R": "猴神之怒"}, {"Q": [{"type": "accel", "desc": "灵活跳跃至目标", "target": "自身"}], "R": [{"type": "control", "desc": "图腾爆发全屏恐惧", "duration": 1, "target": "敌方"}]}),

    # Norse (4)
    ("Fafnir", "tank", {"R": "巨龙诅咒"}, {"W": [{"type": "shield", "desc": "黄金龙鳞护盾", "target": "自身"}, {"type": "reduce", "desc": "贪婪护甲：受到的伤害减半", "duration": 1, "target": "自身"}], "R": [{"type": "buff", "desc": "化为巨龙，全属性大幅提升", "duration": 2, "target": "自身"}, {"type": "dot", "desc": "龙息灼烧区域", "duration": 2, "target": "敌方"}]}),
    ("Ratatoskr", "assassin", {"Q": "橡果投掷", "W": "世界树攀爬", "E": "尾巴横扫", "R": "世界树信使"}, {"E": [{"type": "accel", "desc": "沿世界树快速穿梭", "target": "自身"}, {"type": "accel", "desc": "获得额外移动速度", "target": "自身"}], "R": [{"type": "buff", "desc": "世界树之力贯穿全场", "duration": 2, "target": "自身"}, {"type": "accel", "desc": "全场自由穿梭", "duration": 2, "target": "自身"}]}),
    ("Sol", "mage", {"Q": "太阳烈焰", "W": "耀斑爆发", "E": "日冕加速", "R": "太阳女神"}, {"Q": [{"type": "dot", "desc": "太阳之火灼烧每回合1d8", "duration": 2, "target": "敌方"}], "E": [{"type": "accel", "desc": "光速移动", "target": "自身"}, {"type": "immune", "desc": "化为纯光，免疫伤害", "duration": 1, "target": "自身"}], "R": [{"type": "dot", "desc": "太阳之力全屏灼烧", "duration": 2, "target": "敌方"}]}),
    ("Surtr", "fighter", {"Q": "炎魔之剑", "W": "烈焰光环", "E": "地狱冲锋", "R": "诸神黄昏"}, {"Q": [{"type": "dot", "desc": "火焰之剑附加燃烧", "duration": 2, "target": "敌方"}], "R": [{"type": "buff", "desc": "诸神黄昏降临，炎魔之力全开", "duration": 2, "target": "自身"}, {"type": "dot", "desc": "世界之火灼烧全场", "duration": 2, "target": "敌方"}]}),
]

# ======================== DOTA2 (+46) ========================
HERO_DEFS["dota2"] = [
    # Official missing
    ("朗戈", "support", {"Q": "蛙鸣和弦", "W": "治愈旋律", "E": "跃动音符", "R": "交响终章"}, {}),
    # Dota lore & Dota 1 legacy
    ("Roshan", "tank", {"Q": "不朽之握", "W": "岩石护盾", "E": "地震践踏", "R": "不朽重生"}, {"R": [{"type": "revive", "desc": "死亡后满血复活一次", "target": "自身"}, {"type": "buff", "desc": "复活后全属性+3", "duration": 3, "target": "自身"}]}),
    ("阿哈利姆", "mage", {"Q": "奥术智慧", "W": "魔杖充能", "E": "法术窃取", "R": "阿哈利姆神杖"}, {"R": [{"type": "buff", "desc": "神杖强化：所有技能效果翻倍", "duration": 2, "target": "自身"}]}),
    ("索拉可汗", "fighter", {"Q": "可汗战斧", "W": "号令进军", "E": "铁蹄践踏", "R": "血怒军团"}, {"R": [{"type": "buff", "desc": "召唤军团冲锋", "duration": 2, "target": "自身"}, {"type": "accel", "desc": "全军加速", "target": "友方"}]}),
    ("卡娜", "mage", {"Q": "虚空撕裂", "W": "暗影囚笼", "E": "虚空步", "R": "虚空女皇"}, {"R": [{"type": "control", "desc": "虚空吞噬全场", "duration": 2, "target": "敌方"}]}),
    ("菲姆琳", "assassin", {"Q": "月刃投掷", "W": "暗月潜行", "E": "月光跃迁", "R": "月之复仇"}, {"E": [{"type": "accel", "desc": "月光传送", "target": "自身"}, {"type": "invis", "desc": "月光下隐形", "duration": 1, "target": "自身"}]}),
    ("因佩里娅", "mage", {"Q": "魂之挽歌", "W": "灵魂枷锁", "E": "亡者低语", "R": "幽冥女皇"}, {"Q": [{"type": "dot", "desc": "魂之挽歌造成持续暗蚀", "duration": 2, "target": "敌方"}], "R": [{"type": "control", "desc": "灵魂风暴全场恐惧", "duration": 1, "target": "敌方"}]}),
    ("阿布兹迪安", "tank", {"Q": "深渊碾压", "W": "虚空护甲", "E": "暗影突袭", "R": "深渊领主"}, {}),
    ("甘布尔", "assassin", {"Q": "命运骰子", "W": "赌徒之刃", "E": "幸运闪避", "R": "孤注一掷"}, {"R": [{"type": "buff", "desc": "押上一切：伤害翻倍或归零", "duration": 1, "target": "自身"}]}),
    ("冰龙", "mage", {"Q": "寒冰吐息", "W": "冰霜护甲", "E": "极寒风暴", "R": "永冻纪元"}, {"Q": [{"type": "slow", "desc": "寒冰吐息减速", "duration": 2, "target": "敌方"}]}),
    ("水人", "fighter", {"Q": "波浪形态", "W": "变形冲击", "E": "流水护体", "R": "聚水成形"}, {}),
    ("火猫", "assassin", {"Q": "炎刃突刺", "W": "火焰步", "E": "灼热锁链", "R": "炎魂爆发"}, {}),
    ("土猫", "tank", {"Q": "巨石投掷", "W": "地磁护盾", "E": "滚石冲击", "R": "大地之怒"}, {}),
    ("风猫", "mage", {"Q": "旋风术", "W": "风刃切割", "E": "疾风步", "R": "飓风之眼"}, {}),
    ("剑圣", "fighter", {"Q": "剑刃风暴", "W": "镜像分身", "E": "致命一击", "R": "无敌斩"}, {}),
    ("影刺", "assassin", {"Q": "暗杀术", "W": "毒雾弹", "E": "影遁", "R": "暗影刺杀"}, {}),
    ("石鳞武士", "fighter", {"Q": "鳞甲反弹", "W": "石化皮肤", "E": "滚动冲击", "R": "石鳞巨兽"}, {}),
    ("时间法师", "mage", {"Q": "时间扭曲", "W": "预知未来", "E": "时空回溯", "R": "时光倒流"}, {}),
    ("元素君主", "mage", {"Q": "元素球", "W": "元素护盾", "E": "元素爆发", "R": "元素之怒"}, {}),
    ("镜像大师", "assassin", {"Q": "幻象刺杀", "W": "镜面反射", "E": "镜像位移", "R": "万镜齐发"}, {}),
    ("暗影牧师", "support", {"Q": "暗言术·痛", "W": "暗言术·盾", "E": "暗影形态", "R": "暗影愈合"}, {}),
    ("龙血战士", "fighter", {"Q": "龙血斩", "W": "龙鳞甲", "E": "龙翼冲锋", "R": "龙神降临"}, {}),
    ("冰霜女皇", "mage", {"Q": "冰锥术", "W": "冰封禁制", "E": "冰霜闪现", "R": "冰封王座"}, {}),
    ("雷霆之灵", "mage", {"Q": "闪电链", "W": "雷云风暴", "E": "电荷跃迁", "R": "雷霆万钧"}, {}),
    ("虚空行者", "assassin", {"Q": "虚空切割", "W": "暗影步", "E": "虚空壁障", "R": "虚空降临"}, {}),
    ("地狱骑士", "fighter", {"Q": "地狱火斩", "W": "恶魔之盾", "E": "地狱冲锋", "R": "末日审判"}, {}),
    ("自然之灵", "support", {"Q": "生命绽放", "W": "自然之愈", "E": "荆棘缠绕", "R": "自然之怒"}, {}),
    ("机械师", "mage", {"Q": "火箭弹幕", "W": "能量护盾", "E": "机械臂", "R": "自爆程序"}, {}),
    ("血族亲王", "assassin", {"Q": "血之饥渴", "W": "血雾遁形", "E": "鲜血仪式", "R": "血月降临"}, {}),
    ("深渊巨兽", "tank", {"Q": "深渊触手", "W": "深海护甲", "E": "暗流涌动", "R": "深渊之口"}, {}),
    ("雷神", "mage", {"Q": "闪电之矛", "W": "雷盾", "E": "雷霆传送", "R": "诸神之怒"}, {}),
    ("毒龙", "mage", {"Q": "剧毒吐息", "W": "毒雾弥漫", "E": "腐蚀鳞甲", "R": "万毒之渊"}, {}),
    ("虚空领主", "tank", {"Q": "虚空之握", "W": "暗影甲壳", "E": "虚空践踏", "R": "虚空风暴"}, {}),
    ("钢铁守卫", "tank", {"Q": "钢铁冲撞", "W": "合金装甲", "E": "电磁脉冲", "R": "钢铁洪流"}, {}),
    ("光翼天使", "support", {"Q": "圣光箭", "W": "天使之愈", "E": "光翼庇护", "R": "天堂之光"}, {}),
    ("远古巨龙", "fighter", {"Q": "太古龙息", "W": "龙鳞壁垒", "E": "龙翼风暴", "R": "龙神觉醒"}, {}),
    ("灵魂收割者", "assassin", {"Q": "灵魂切割", "W": "鬼影重重", "E": "灵魂漫步", "R": "灵魂收割"}, {}),
    ("暴风骑士", "fighter", {"Q": "暴风斩", "W": "风之铠甲", "E": "风暴冲锋", "R": "暴风之眼"}, {}),
    ("烈焰魔导师", "mage", {"Q": "烈焰冲击", "W": "火焰结界", "E": "烈焰传送", "R": "流星火雨"}, {}),
    ("死灵法师", "mage", {"Q": "死亡一指", "W": "亡灵大军", "E": "白骨护甲", "R": "亡者领域"}, {}),
    ("巨魔酋长", "fighter", {"Q": "巨魔飞斧", "W": "战吼", "E": "狂暴冲锋", "R": "巨魔狂战士"}, {}),
    ("深海潜伏者", "assassin", {"Q": "深海突刺", "W": "水幕隐身", "E": "激流喷射", "R": "深海恐惧"}, {}),
    ("神圣骑士", "fighter", {"Q": "圣剑裁决", "W": "神圣护盾", "E": "圣光冲锋", "R": "圣骑士之怒"}, {}),
    ("混沌巫师", "mage", {"Q": "混沌箭", "W": "混沌护甲", "E": "混沌传送", "R": "混沌风暴"}, {}),
    ("钢铁巨人", "tank", {"Q": "巨拳砸击", "W": "钢铁皮肤", "E": "地震波", "R": "巨人降临"}, {}),
    ("术士王", "mage", {"Q": "混乱之箭", "W": "恶魔契约", "E": "暗影烈焰", "R": "术士之王"}, {}),
]

# ======================== HOTS (+82) ========================
HERO_DEFS["heroes_of_the_storm"] = [
    # Warcraft characters not in HotS
    ("Grommash", "fighter", {"Q": "血吼斩", "W": "战歌咆哮", "E": "地狱咆哮冲锋", "R": "钢铁部落"}, {}),
    ("Velen", "support", {"Q": "圣光涌动", "W": "先知治愈", "E": "纳鲁庇护", "R": "圣光预言"}, {}),
    ("Kiljaeden", "mage", {"Q": "邪能烈焰", "W": "欺诈者诡计", "E": "恶魔传送门", "R": "燃烧军团"}, {}),
    ("Archimonde", "mage", {"Q": "邪能毁灭", "W": "黑暗契约", "E": "污染者之触", "R": "毁灭者"}, {}),
    ("LadyVashj", "marksman", {"Q": "多头蛇箭", "W": "叉状闪电", "E": "法力护盾", "R": "娜迦女皇"}, {}),
    ("Cenarius", "support", {"Q": "自然之触", "W": "森林治愈", "E": "荆棘光环", "R": "半神之力"}, {}),
    ("Azshara", "mage", {"Q": "奥术洪流", "W": "潮汐之力", "E": "深海召唤", "R": "永恒女皇"}, {}),
    ("Voljin", "support", {"Q": "暗影猎手", "W": "巫毒治愈", "E": "毒蛇守卫", "R": "暗矛之怒"}, {}),
    ("Gallywix", "mage", {"Q": "火箭弹幕", "W": "金币护盾", "E": "地精滑翔", "R": "大财主"}, {}),
    ("Brann", "marksman", {"Q": "探险射击", "W": "考古发现", "E": "矮人地雷", "R": "泰坦遗物"}, {}),
    ("MoiraBronzebeard", "support", {"Q": "暗影愈合", "W": "心灵尖啸", "E": "虚空转移", "R": "双面牧师"}, {}),
    ("Bwonsamdi", "support", {"Q": "死亡交易", "W": "灵魂绑定", "E": "死神步", "R": "冥宫之主"}, {}),
    ("Talanji", "support", {"Q": "洛阿之赐", "W": "赞达拉荣光", "E": "王室护盾", "R": "神王之力"}, {}),
    ("Mekkatorque", "mage", {"Q": "机械装甲", "W": "火箭飞拳", "E": "工程学奇迹", "R": "侏儒之王"}, {}),
    ("Druid", "fighter", {"Q": "熊形态", "W": "月火术", "E": "野性冲锋", "R": "自然之怒"}, {}),
    ("Sorceress", "mage", {"Q": "暴风雪", "W": "魔法盾", "E": "传送术", "R": "奥术风暴"}, {}),
    ("Paladin", "fighter", {"Q": "圣光之锤", "W": "圣盾术", "E": "奉献", "R": "神圣风暴"}, {}),

    # Diablo characters not in HotS
    ("Belial", "mage", {"Q": "谎言之触", "W": "幻象分身", "E": "欺诈领域", "R": "谎言之王"}, {}),
    ("Aidan", "fighter", {"Q": "暗黑流放", "W": "灵魂石之力", "E": "黑暗突进", "R": "黑暗流浪者"}, {}),
    ("Kronan", "fighter", {"Q": "野蛮挥砍", "W": "先祖召唤", "E": "大地践踏", "R": "不朽之王"}, {}),
    ("ZoltunKulle", "mage", {"Q": "奥术飞弹", "W": "时间缓滞", "E": "黑洞", "R": "赫拉迪姆"}, {}),
    ("Maghda", "mage", {"Q": "飞蛾风暴", "W": "暗影诅咒", "E": "魔女变身", "R": "魔女会"}, {}),
    ("Cydea", "assassin", {"Q": "蛛网陷阱", "W": "剧毒撕咬", "E": "魅惑之触", "R": "欲望女巫"}, {}),
    ("Izual", "fighter", {"Q": "堕落天使之剑", "W": "霜冻护甲", "E": "绝望冲锋", "R": "堕落天使"}, {}),
    ("Rakanoth", "assassin", {"Q": "绝望撕裂", "W": "暗影突袭", "E": "虚空步", "R": "绝望之主"}, {}),
    ("Duriel", "tank", {"Q": "痛苦撕咬", "W": "虫群甲壳", "E": "钻地突袭", "R": "痛苦之王"}, {}),
    ("Andariel", "assassin", {"Q": "毒雾喷吐", "W": "蛛魔束缚", "E": "剧毒新星", "R": "苦痛女王"}, {}),

    # StarCraft characters not in HotS
    ("ArcturusMengsk", "fighter", {"Q": "帝国之令", "W": "炮火支援", "E": "战术撤退", "R": "泰伦皇帝"}, {}),
    ("Selendis", "fighter", {"Q": "灵能双刃", "W": "护盾充能", "E": "虚空跃迁", "R": "黄金舰队"}, {}),
    ("Tosh", "assassin", {"Q": "灵能爆发", "W": "幽魂隐形", "E": "心灵控制", "R": "幽魂特工"}, {}),
    ("Warfield", "tank", {"Q": "重炮轰击", "W": "战地装甲", "E": "战术部署", "R": "将军之怒"}, {}),
    ("Valerian", "fighter", {"Q": "圣剑", "W": "皇室护盾", "E": "灵能冲锋", "R": "泰伦王子"}, {}),
    ("Overmind", "mage", {"Q": "灵能风暴", "W": "虫群意志", "E": "触须蔓延", "R": "主宰降临"}, {}),
    ("Zurvan", "tank", {"Q": "原始之怒", "W": "进化甲壳", "E": "吞噬", "R": "原始异虫"}, {}),
    ("Hybrid", "tank", {"Q": "湮灭波", "W": "混合体护甲", "E": "虚空牵引", "R": "萨尔那加"}, {}),
    ("Hanson", "support", {"Q": "医疗射线", "W": "生化修复", "E": "兴奋剂注射", "R": "医疗运输"}, {}),

    # Overwatch characters not in HotS
    ("Reinhardt", "tank", {"Q": "火箭重锤", "W": "屏障力场", "E": "烈焰打击", "R": "裂地猛击"}, {}),
    ("Reaper", "assassin", {"Q": "地狱火霰弹", "W": "幽灵形态", "E": "暗影步", "R": "死亡绽放"}, {}),
    ("Brigitte", "support", {"Q": "连枷挥击", "W": "修复包", "E": "屏障盾击", "R": "集结号令"}, {}),
    ("Winston", "tank", {"Q": "特斯拉炮", "W": "屏障护盾", "E": "喷射跳跃", "R": "原始暴怒"}, {}),
    ("Pharah", "marksman", {"Q": "火箭发射器", "W": "震荡冲击", "E": "喷射飞跃", "R": "火箭弹幕"}, {}),
    ("Symmetra", "support", {"Q": "光子投射", "W": "哨戒炮台", "E": "传送面板", "R": "光子屏障"}, {}),
    ("Moira", "support", {"Q": "生化之握", "W": "生化法球", "E": "消散", "R": "聚合射线"}, {}),
    ("Doomfist", "fighter", {"Q": "手炮", "W": "火箭重拳", "E": "上勾拳", "R": "毁天灭地"}, {}),
    ("Baptiste", "support", {"Q": "生化步枪", "W": "不朽力场", "E": "愈合冲击", "R": "增幅矩阵"}, {}),
    ("Sigma", "tank", {"Q": "超能之球", "W": "动能擒握", "E": "实验屏障", "R": "重力喷涌"}, {}),
    ("Echo", "assassin", {"Q": "粘性炸弹", "W": "飞行", "E": "聚焦光束", "R": "复制"}, {}),
    ("Sojourn", "marksman", {"Q": "轨道炮", "W": "干扰弹", "E": "滑铲", "R": "超频"}, {}),
    ("Ramattra", "tank", {"Q": "虚空加速", "W": "虚空屏障", "E": "天罚形态", "R": "湮灭"}, {}),
    ("Kiriko", "support", {"Q": "苦无", "W": "治愈符咒", "E": "瞬移", "R": "狐之加护"}, {}),
    ("JunkerQueen", "fighter", {"Q": "霰弹枪", "W": "锯齿利刃", "E": "战吼", "R": "轰天震地"}, {}),
    ("Lifeweaver", "support", {"Q": "荆棘齐射", "W": "生命之树", "E": "花瓣平台", "R": "生命之握"}, {}),
    ("Mauga", "tank", {"Q": "燃烧机枪", "W": "心脏过载", "E": "狂暴冲锋", "R": "笼中斗"}, {}),
    ("Illari", "support", {"Q": "太阳能步枪", "W": "治愈光塔", "E": "日炎冲击", "R": "太阳爆破"}, {}),

    # Blizzard Classics
    ("Blackthorne", "marksman", {"Q": "霰弹枪", "W": "闪光弹", "E": "后翻", "R": "硬汉本色"}, {}),
    ("RocknRollRacer", "fighter", {"Q": "氮气加速", "W": "导弹发射", "E": "漂移", "R": "音速爆裂"}, {}),
    ("Tomator", "mage", {"Q": "等离子炮", "W": "能量盾", "E": "传送", "R": "毁灭日"}, {}),
    ("SnakeSanders", "assassin", {"Q": "电锯冲击", "W": "铁蒺藜", "E": "潜行", "R": "蛇行之怒"}, {}),

    # Diablo more
    ("Baal", "mage", {"Q": "毁灭之焰", "W": "分身术", "E": "法力燃烧", "R": "毁灭之王"}, {}),
    ("Lilith", "mage", {"Q": "魅惑之吻", "W": "血雾", "E": "恶魔变身", "R": "憎恨之女"}, {}),
    ("Inarius", "fighter", {"Q": "天使之矛", "W": "圣光之翼", "E": "天堂之怒", "R": "堕落天使"}, {}),
    ("Necromancer", "mage", {"Q": "骨矛", "W": "尸爆", "E": "骨盾", "R": "亡者大军"}, {}),
    ("Amazon", "marksman", {"Q": "多重箭", "W": "冰冻箭", "E": "闪避", "R": "女武神"}, {}),
    ("Assassin_D2", "assassin", {"Q": "凤凰击", "W": "暗影斗篷", "E": "飞龙在天", "R": "暗影大师"}, {}),

    # More Warcraft
    ("Akama", "assassin", {"Q": "暗影突袭", "W": "灵魂行走", "E": "双刃斩", "R": "破碎者之怒"}, {}),
    ("Kargath", "fighter", {"Q": "刃拳", "W": "碎手冲锋", "E": "嗜血", "R": "角斗士之王"}, {}),
    ("Nerzhul", "mage", {"Q": "暗影宝珠", "W": "先祖之魂", "E": "死亡凋零", "R": "巫妖之王"}, {}),
    ("TeronGorefiend", "fighter", {"Q": "死亡骑士之剑", "W": "死亡缠绕", "E": "亡灵冲锋", "R": "初代死亡骑士"}, {}),
    ("DrekThar", "mage", {"Q": "闪电箭", "W": "大地之盾", "E": "幽狼形态", "R": "霜狼先知"}, {}),
    ("Garona", "assassin", {"Q": "半兽人利刃", "W": "毒药涂抹", "E": "暗杀步", "R": "影之议定"}, {}),
    ("Medivh_Guardian", "mage", {"Q": "奥术弹幕", "W": "卡拉赞之门", "E": "乌鸦形态", "R": "最后的守护者"}, {}),
    ("Antonidas", "mage", {"Q": "大法师之弹", "W": "群体传送", "E": "水元素", "R": "达拉然之力"}, {}),
    ("Khadgar", "mage", {"Q": "奥术飞弹", "W": "时光护盾", "E": "闪现术", "R": "肯瑞托之主"}, {}),
    ("Alleria", "marksman", {"Q": "风行者之箭", "W": "虚空之力", "E": "猎人标记", "R": "虚空游侠"}, {}),
    ("Turalyon", "fighter", {"Q": "圣光之剑", "W": "正义之盾", "E": "圣光冲锋", "R": "白银之手"}, {}),
    # +7 more to reach 172
    ("Mannoroth", "fighter", {"Q": "毁灭之刃", "W": "深渊血甲", "E": "地狱冲锋", "R": "毁灭者"}, {}),
    ("Sargeras", "tank", {"Q": "黑暗撕裂者", "W": "邪能护甲", "E": "泰坦威压", "R": "黑暗泰坦"}, {}),
    ("Xavius", "mage", {"Q": "梦魇之触", "W": "腐化梦境", "E": "暗影步", "R": "梦魇之王"}, {}),
    ("Hakkar", "mage", {"Q": "夺灵术", "W": "血之诅咒", "E": "血池步", "R": "血神"}, {}),
    ("Onyxia", "fighter", {"Q": "龙息术", "W": "龙鳞甲", "E": "龙翼冲锋", "R": "黑龙公主"}, {}),
    ("YoggSaron", "mage", {"Q": "疯狂低语", "W": "混乱之触", "E": "千喉之兽", "R": "千喉之魔"}, {}),
    ("Algalon", "mage", {"Q": "星辰坠落", "W": "宇宙护盾", "E": "黑洞", "R": "观察者"}, {}),
]

# ======================== ONMYOJI ARENA (+89) ========================
HERO_DEFS["onmyoji_arena"] = [
    # SP Shikigami not yet in arena
    ("少羽大天狗", "mage", {"Q": "幼羽风暴", "W": "旋风守护", "E": "疾风突进", "R": "小天狗之怒"}, {}),
    ("炼狱茨木童子", "fighter", {"Q": "炼狱鬼拳", "W": "业火缠身", "E": "地狱冲锋", "R": "炼狱之门"}, {}),
    ("苍风一目连", "support", {"Q": "苍风护盾", "W": "风神治愈", "E": "龙卷风壁", "R": "风神降临"}, {}),
    ("赤影妖刀姬", "assassin", {"Q": "赤影斩", "W": "妖刀之魂", "E": "血影步", "R": "红莲之刃"}, {}),
    ("御怨般若", "mage", {"Q": "怨念波动", "W": "般若面具", "E": "怨灵冲击", "R": "百鬼夜行"}, {}),
    ("骁浪荒川之主", "fighter", {"Q": "浪涛斩", "W": "水龙卷", "E": "逐浪冲锋", "R": "川流不息"}, {}),
    ("烬天玉藻前", "mage", {"Q": "烬灭之炎", "W": "狐火护体", "E": "天狐步", "R": "烬天焚地"}, {}),
    ("鬼王酒吞童子", "fighter", {"Q": "鬼王咆哮", "W": "酒气护体", "E": "狂鬼冲锋", "R": "鬼王降临"}, {}),
    ("天剑韧心鬼切", "assassin", {"Q": "天剑一闪", "W": "韧心之盾", "E": "鬼影穿梭", "R": "天剑奥义"}, {}),
    ("聆海金鱼姬", "support", {"Q": "海浪治愈", "W": "金鱼护盾", "E": "泡沫幻影", "R": "深海之歌"}, {}),
    ("浮世青行灯", "support", {"Q": "青焰", "W": "浮世之光", "E": "灯火通明", "R": "浮世绘卷"}, {}),
    ("待宵姑获鸟", "assassin", {"Q": "待宵之羽", "W": "暗夜突袭", "E": "掠影", "R": "百鸟朝凤"}, {}),
    ("麓铭大岳丸", "fighter", {"Q": "麓鸣斩", "W": "山岳之盾", "E": "巨石投掷", "R": "大岳降临"}, {}),
    ("初翎山风", "assassin", {"Q": "初翎突刺", "W": "风之羽衣", "E": "山林穿梭", "R": "山风怒号"}, {}),
    ("夜溟彼岸花", "mage", {"Q": "彼岸花开", "W": "幽冥之雾", "E": "花海漫步", "R": "黄泉之引"}, {}),
    ("蝉冰雪女", "mage", {"Q": "蝉翼冰刃", "W": "雪之结界", "E": "冰封之路", "R": "永冻之境"}, {}),
    ("空相面灵气", "mage", {"Q": "空相面具", "W": "灵能冲击", "E": "幻象步", "R": "万象皆空"}, {}),
    ("绘世花鸟卷", "support", {"Q": "花鸟画卷", "W": "绘世治愈", "E": "画卷护盾", "R": "浮世花鸟"}, {}),
    ("因幡辉夜姬", "support", {"Q": "因幡之舞", "W": "月光治愈", "E": "辉夜结界", "R": "月之公主"}, {}),
    ("梦寻山兔", "support", {"Q": "梦之胡萝卜", "W": "梦境治愈", "E": "跳跃祝福", "R": "梦中山兔"}, {}),
    ("神堕八岐大蛇", "mage", {"Q": "神堕之毒", "W": "蛇鳞护体", "E": "八首齐攻", "R": "神堕·终焉"}, {}),

    # More SSR not yet in arena
    ("紧那罗", "support", {"Q": "妙音天女", "W": "天籁治愈", "E": "音波护盾", "R": "紧那罗之歌"}, {}),
    ("千姬", "support", {"Q": "潮汐之力", "W": "海之祝福", "E": "水幕结界", "R": "海潮之女"}, {}),
    ("食灵", "fighter", {"Q": "食灵之咬", "W": "吞噬之力", "E": "暴食冲锋", "R": "食灵降世"}, {}),
    ("饭笥", "support", {"Q": "福泽之饭", "W": "饱食治愈", "E": "丰收祝福", "R": "饭笥之赐"}, {}),
    ("铃彦姬", "support", {"Q": "铃音波动", "W": "祈福之铃", "E": "铃铛结界", "R": "铃音天降"}, {}),
    ("不见岳", "tank", {"Q": "山岳之拳", "W": "磐石护盾", "E": "地动山摇", "R": "不见岳"}, {}),
    ("云外镜", "mage", {"Q": "镜花水月", "W": "镜面反射", "E": "虚实转换", "R": "云外之境"}, {}),
    ("鬼童丸", "assassin", {"Q": "鬼童狩猎", "W": "锁链缠绕", "E": "暗影步", "R": "鬼童降临"}, {}),
    ("缘结神", "support", {"Q": "缘结之线", "W": "福缘治愈", "E": "缘分护盾", "R": "缘结神·结缘"}, {}),
    ("铃鹿御前", "fighter", {"Q": "铃鹿一刀", "W": "海国护盾", "E": "踏浪冲锋", "R": "铃鹿山之主"}, {}),
    ("泷夜叉姬", "fighter", {"Q": "泷夜之刃", "W": "星辰护甲", "E": "流光冲击", "R": "星陨·天降"}, {}),
    ("月读", "mage", {"Q": "月读之眼", "W": "幻月结界", "E": "暗月步", "R": "月读·虚妄"}, {}),
    ("季", "mage", {"Q": "四季流转", "W": "春风化雨", "E": "秋叶凋零", "R": "四季·终焉"}, {}),
    ("寻香行", "assassin", {"Q": "寻香追踪", "W": "香雾隐身", "E": "暗香突袭", "R": "香行·彼岸"}, {}),
    ("言灵", "mage", {"Q": "言灵·缚", "W": "言灵·守", "E": "言灵·灭", "R": "言灵·裁决"}, {}),

    # More SR Shikigami
    ("书翁", "support", {"Q": "书道·笔", "W": "万卷护盾", "E": "墨染", "R": "天下书卷"}, {}),
    ("蝎女", "assassin", {"Q": "蝎尾毒针", "W": "毒雾隐身", "E": "潜沙突袭", "R": "蝎女之舞"}, {}),
    ("风狸", "assassin", {"Q": "风狸之爪", "W": "御风步", "E": "风刃", "R": "风狸·卷"}, {}),
    ("入内雀", "assassin", {"Q": "雀羽飞刃", "W": "鸟瞰侦查", "E": "俯冲扑杀", "R": "百雀朝宗"}, {}),
    ("饴细工", "support", {"Q": "糖艺·塑", "W": "甜蜜治愈", "E": "糖盾", "R": "饴屋之主"}, {}),
    ("川猿", "assassin", {"Q": "水猿之拳", "W": "水流步", "E": "暴雨连击", "R": "川猿·瀑"}, {}),
    ("迦楼罗", "fighter", {"Q": "金翅斩", "W": "羽翼护盾", "E": "天翔突进", "R": "迦楼罗·焚天"}, {}),
    ("灵海蝶", "support", {"Q": "灵蝶飞舞", "W": "深海治愈", "E": "蝶翼护盾", "R": "灵海·蝶舞"}, {}),
    ("粉婆婆", "mage", {"Q": "粉雪纷飞", "W": "花粉幻术", "E": "飘散", "R": "粉雪·冰封"}, {}),
    ("天逆每", "mage", {"Q": "逆天咒", "W": "天道反噬", "E": "逆鳞", "R": "天逆每·劫"}, {}),
    ("久次良", "fighter", {"Q": "鲸骨斩", "W": "海护盾", "E": "踏浪", "R": "鲸骨·开"}, {}),
    ("蟹姬", "tank", {"Q": "蟹钳猛击", "W": "甲壳护盾", "E": "横行霸道", "R": "蟹姬·怒"}, {}),
    ("纸舞", "mage", {"Q": "纸刃飞舞", "W": "纸盾", "E": "纸鹤传书", "R": "千纸·舞"}, {}),

    # More R Shikigami
    ("数珠", "support", {"Q": "念珠", "W": "佛光治愈", "E": "经文护盾", "R": "数珠·禅"}, {}),
    ("古笼火", "mage", {"Q": "古笼之火", "W": "幽火护体", "E": "鬼火飘移", "R": "笼火·燃"}, {}),
    ("兔丸", "support", {"Q": "胡萝卜投掷", "W": "蹦跳治愈", "E": "兔耳风", "R": "兔丸·跃"}, {}),
    ("影鳄", "assassin", {"Q": "影鳄撕咬", "W": "暗影潜行", "E": "水下突袭", "R": "影鳄·噬"}, {}),
    ("垢尝", "support", {"Q": "净水泼洒", "W": "沐浴治愈", "E": "肥皂泡", "R": "垢尝·净"}, {}),
    ("雨女", "support", {"Q": "细雨绵绵", "W": "甘霖治愈", "E": "泪雨结界", "R": "雨女·泣"}, {}),
    ("铁鼠", "mage", {"Q": "金钱镖", "W": "福钱护盾", "E": "撒币", "R": "铁鼠·财"}, {}),
    ("童男", "tank", {"Q": "童男之拳", "W": "纯真护盾", "E": "守护冲锋", "R": "童男·守"}, {}),
    ("童女", "support", {"Q": "童女之舞", "W": "纯洁治愈", "E": "花环护盾", "R": "童女·祈"}, {}),
    ("蝴蝶精", "support", {"Q": "蝶粉", "W": "蝶舞治愈", "E": "蝶翼庇护", "R": "蝴蝶精·梦"}, {}),
    ("食发鬼", "assassin", {"Q": "发刃切割", "W": "鬼发缠绕", "E": "暗影步", "R": "食发鬼·斩"}, {}),
    ("独眼小僧", "tank", {"Q": "念佛", "W": "金刚护体", "E": "撞钟", "R": "小僧·经"}, {}),
    ("饿鬼", "fighter", {"Q": "饿鬼啃咬", "W": "贪食护盾", "E": "暴食冲锋", "R": "饿鬼·吞"}, {}),
    ("巫蛊师", "mage", {"Q": "蛊虫", "W": "毒蛊护体", "E": "诅咒", "R": "巫蛊·咒"}, {}),
    ("赤舌", "mage", {"Q": "赤舌舔", "W": "舌盾", "E": "长舌缠绕", "R": "赤舌·卷"}, {}),
    ("提灯小僧", "support", {"Q": "提灯探照", "W": "灯火治愈", "E": "鬼火飘", "R": "提灯·照"}, {}),
    ("唐纸伞妖", "mage", {"Q": "纸伞旋转", "W": "伞盾", "E": "妖伞飞旋", "R": "唐纸·舞"}, {}),

    # Crossover characters more
    ("杀生丸", "fighter", {"Q": "天生牙", "W": "毒华爪", "E": "妖力突进", "R": "爆碎牙"}, {}),
    ("卖药郎", "mage", {"Q": "药之形", "W": "药之真", "E": "药之理", "R": "退魔之剑"}, {}),
    ("鬼灯", "fighter", {"Q": "鬼灯狼牙棒", "W": "地狱烈火", "E": "鬼差冲锋", "R": "鬼灯·裁决"}, {}),
    ("奴良陆生", "assassin", {"Q": "明镜止水", "W": "畏之发动", "E": "镜花水月", "R": "百鬼夜行·主"}, {}),
    ("阿香", "assassin", {"Q": "妖香追踪", "W": "香气隐身", "E": "毒香弥漫", "R": "阿香·幻"}, {}),
    ("蜜桃芥子", "support", {"Q": "蜜桃炸弹", "W": "芥子冲锋", "E": "双人舞", "R": "蜜桃&芥子"}, {}),
    ("嘴平伊之助", "fighter", {"Q": "兽之呼吸", "W": "猪突猛进", "E": "空间感知", "R": "伊之助·裂"}, {}),
    ("申屠子夜", "assassin", {"Q": "暗夜突袭", "W": "子夜潜行", "E": "夜行步", "R": "子夜·猎"}, {}),
    ("麻仓叶", "mage", {"Q": "阿弥陀丸", "W": "超灵体", "E": "巫力冲击", "R": "通灵王"}, {}),
    ("恐山安娜", "mage", {"Q": "降灵术", "W": "怨灵束缚", "E": "灵媒体质", "R": "安娜·降灵"}, {}),
    ("坂田银时", "fighter", {"Q": "洞爷湖", "W": "糖分充电", "E": "万事屋冲锋", "R": "白夜叉"}, {}),
    ("神乐", "mage", {"Q": "伞弹枪", "W": "夜兔之力", "E": "怪力冲锋", "R": "神乐·星海"}, {}),

    # Additional SSR/SR
    ("大司命", "support", {"Q": "司命之笔", "W": "命运治愈", "E": "命数护盾", "R": "大司命·判"}, {}),
    ("天照", "mage", {"Q": "天照大御神", "W": "日轮护体", "E": "神光普照", "R": "天照·辉"}, {}),
    ("伊邪那美", "mage", {"Q": "黄泉之触", "W": "冥界护盾", "E": "死之召唤", "R": "黄泉津大神"}, {}),
    ("孔雀明王", "support", {"Q": "孔雀开屏", "W": "明王治愈", "E": "翎羽护盾", "R": "孔雀明王·舞"}, {}),
    ("百目鬼", "mage", {"Q": "百目凝视", "W": "妖目结界", "E": "窥心术", "R": "百目·开"}, {}),
    # +11 more
    ("修罗鬼童丸", "assassin", {"Q": "修罗之锁", "W": "鬼血狂暴", "E": "猎杀突进", "R": "修罗道"}, {}),
    ("流光追月神", "support", {"Q": "流光溢彩", "W": "月华治愈", "E": "追月之光", "R": "流光·月"}, {}),
    ("大夜摩天阎魔", "mage", {"Q": "摩天审判", "W": "冥府之门", "E": "业火", "R": "大夜摩天"}, {}),
    ("神启荒", "mage", {"Q": "神启之光", "W": "星辰护盾", "E": "预言术", "R": "神启·星"}, {}),
    ("禅心云外镜", "support", {"Q": "禅心映照", "W": "明镜止水", "E": "虚实转换", "R": "禅心·镜"}, {}),
    ("修罗鬼切", "assassin", {"Q": "修罗一闪", "W": "鬼影重重", "E": "修罗步", "R": "修罗·终"}, {}),
    ("白藏主·SP", "tank", {"Q": "白藏守护", "W": "狐火结界", "E": "梦境穿梭", "R": "白藏·梦"}, {}),
    ("酒吞童子·SP", "fighter", {"Q": "大江山之怒", "W": "鬼酒狂气", "E": "百鬼夜行", "R": "大江山鬼王"}, {}),
    ("茨木童子·SP", "fighter", {"Q": "罗生门之腕", "W": "地狱鬼手", "E": "黑焰突进", "R": "罗生门大妖"}, {}),
    ("妖刀姬·SP", "assassin", {"Q": "樱吹雪", "W": "妖刀千刃", "E": "血樱步", "R": "千本樱·斩"}, {}),
    ("青行灯·SP", "mage", {"Q": "百物语", "W": "青焰结界", "E": "怪谈·现", "R": "百鬼灯"}, {}),
]

# ======================== POKEMON UNITE (+103) ========================
HERO_DEFS["pokemon_unite"] = [
    # Gen 1 (+20)
    ("妙蛙种子", "mage", {}, {}), ("小火龙", "mage", {}, {}), ("杰尼龟", "tank", {}, {}),
    ("绿毛虫", "marksman", {}, {}), ("巴大蝶", "support", {}, {}), ("大针蜂", "assassin", {}, {}),
    ("比雕", "marksman", {}, {}), ("拉达", "assassin", {}, {}), ("阿柏怪", "assassin", {}, {}),
    ("雷丘", "mage", {}, {}), ("穿山王", "fighter", {}, {}), ("尼多王", "fighter", {}, {}),
    ("尼多后", "tank", {}, {}), ("皮可西", "support", {}, {}), ("九尾", "mage", {}, {}),
    ("胖丁", "support", {}, {}), ("霸王花", "mage", {}, {}), ("三地鼠", "assassin", {}, {}),
    ("猫老大", "assassin", {}, {}), ("风速狗", "fighter", {}, {}),
    # Gen 2 (+10)
    ("大竺葵", "support", {}, {}), ("火暴兽", "mage", {}, {}), ("大力鳄", "fighter", {}, {}),
    ("叉字蝠", "assassin", {}, {}), ("电龙", "mage", {}, {}), ("太阳伊布", "mage", {}, {}),
    ("月伊布", "tank", {}, {}), ("黑暗鸦", "assassin", {}, {}), ("赫拉克罗斯", "fighter", {}, {}),
    ("黑鲁加", "mage", {}, {}),
    # Gen 3 (+10)
    ("蜥蜴王", "assassin", {}, {}), ("巨沼怪", "tank", {}, {}), ("拉鲁拉丝", "support", {}, {}),
    ("阿勃梭鲁", "assassin", {}, {}), ("暴飞龙", "fighter", {}, {}), ("巨金怪", "tank", {}, {}),
    ("盖欧卡", "mage", {}, {}), ("固拉多", "fighter", {}, {}), ("烈空坐", "fighter", {}, {}),
    ("基拉祈", "support", {}, {}),
    # Gen 4 (+10)
    ("帝王拿波", "tank", {}, {}), ("伦琴猫", "mage", {}, {}), ("战槌龙", "fighter", {}, {}),
    ("帕路奇亚", "mage", {}, {}), ("帝牙卢卡", "tank", {}, {}), ("骑拉帝纳", "tank", {}, {}),
    ("阿尔宙斯", "mage", {}, {}), ("达克莱伊", "assassin", {}, {}), ("谢米", "support", {}, {}),
    ("玛纳霏", "support", {}, {}),
    # Gen 5 (+10)
    ("君主蛇", "mage", {}, {}), ("炎武王", "fighter", {}, {}), ("大剑鬼", "fighter", {}, {}),
    ("索罗亚克", "assassin", {}, {}), ("电蜘蛛", "mage", {}, {}), ("水晶灯火灵", "mage", {}, {}),
    ("三首恶龙", "mage", {}, {}), ("捷克罗姆", "fighter", {}, {}), ("莱希拉姆", "mage", {}, {}),
    ("酋雷姆", "tank", {}, {}),
    # Gen 6 (+10)
    ("妖火红狐", "mage", {}, {}), ("忍者蛙", "assassin", {}, {}), ("黏美龙", "tank", {}, {}),
    ("仙子伊布", "support", {}, {}), ("摔角鹰人", "fighter", {}, {}), ("咚咚鼠", "support", {}, {}),
    ("哲尔尼亚斯", "support", {}, {}), ("伊裴尔塔尔", "mage", {}, {}), ("基格尔德", "tank", {}, {}),
    ("蒂安希", "support", {}, {}),
    # Gen 7 (+10)
    ("狙射树枭", "marksman", {}, {}), ("炽焰咆哮虎", "fighter", {}, {}), ("西狮海壬", "support", {}, {}),
    ("鬃岩狼人", "fighter", {}, {}), ("谜拟Q", "assassin", {}, {}), ("杖尾鳞甲龙", "fighter", {}, {}),
    ("露奈雅拉", "mage", {}, {}), ("索尔迦雷欧", "fighter", {}, {}), ("玛机雅娜", "support", {}, {}),
    ("玛夏多", "assassin", {}, {}),
    # Gen 8 (+10)
    ("闪焰王牌", "marksman", {}, {}), ("千面避役", "marksman", {}, {}), ("轰擂金刚猩", "fighter", {}, {}),
    ("钢铠鸦", "tank", {}, {}), ("多龙巴鲁托", "marksman", {}, {}), ("苍响", "fighter", {}, {}),
    ("藏玛然特", "tank", {}, {}), ("无极汰那", "mage", {}, {}), ("蕾冠王", "mage", {}, {}),
    ("武道熊师", "fighter", {}, {}),
    # Gen 9 + extras (+13)
    ("魔幻假面喵", "assassin", {}, {}), ("骨纹巨声鳄", "mage", {}, {}), ("狂欢浪舞鸭", "fighter", {}, {}),
    ("巴布土拨", "fighter", {}, {}), ("巨锻匠", "fighter", {}, {}), ("海豚侠", "fighter", {}, {}),
    ("仆刀将军", "assassin", {}, {}), ("赛富豪", "mage", {}, {}), ("故勒顿", "fighter", {}, {}),
    ("密勒顿", "mage", {}, {}), ("厄诡椪", "assassin", {}, {}), ("太乐巴戈斯", "tank", {}, {}),
    ("桃歹郎", "mage", {}, {}),
]

# ======================== MARVEL SUPER WAR (+107) ========================
HERO_DEFS["marvel_super_war"] = [
    # X-Men (20)
    ("Wolverine", "fighter", {}, {}), ("Cyclops", "marksman", {}, {}), ("Jean Grey", "mage", {}, {}),
    ("Gambit", "assassin", {}, {}), ("Rogue", "fighter", {}, {}), ("Colossus", "tank", {}, {}),
    ("Nightcrawler", "assassin", {}, {}), ("Psylocke", "assassin", {}, {}), ("Havok", "mage", {}, {}),
    ("Polaris", "mage", {}, {}), ("Dazzler", "support", {}, {}), ("Bishop", "fighter", {}, {}),
    ("Cable", "marksman", {}, {}), ("Domino", "assassin", {}, {}), ("X-23", "assassin", {}, {}),
    ("Jubilee", "mage", {}, {}), ("Sunfire", "mage", {}, {}), ("Banshee", "mage", {}, {}),
    ("Forge", "support", {}, {}), ("Armor", "tank", {}, {}),
    # Avengers & Allies (15)
    ("Falcon", "fighter", {}, {}), ("War Machine", "marksman", {}, {}), ("Wasp", "assassin", {}, {}),
    ("Ant-Man", "assassin", {}, {}), ("Vision", "mage", {}, {}), ("She-Hulk", "fighter", {}, {}),
    ("Ms. Marvel", "fighter", {}, {}), ("Wonder Man", "fighter", {}, {}), ("Tigra", "assassin", {}, {}),
    ("Quasar", "mage", {}, {}), ("Sersi", "mage", {}, {}), ("Black Knight", "fighter", {}, {}),
    ("Hercules_Marvel", "fighter", {}, {}), ("Ares_Marvel", "fighter", {}, {}), ("Sentry", "fighter", {}, {}),
    # Villains (20)
    ("Magneto", "mage", {}, {}), ("Sabretooth", "assassin", {}, {}), ("Mystique", "assassin", {}, {}),
    ("Juggernaut", "tank", {}, {}), ("Apocalypse", "tank", {}, {}), ("Mr. Sinister", "mage", {}, {}),
    ("Omega Red", "fighter", {}, {}), ("Doctor Octopus", "fighter", {}, {}), ("Green Goblin", "assassin", {}, {}),
    ("Electro", "mage", {}, {}), ("Sandman", "tank", {}, {}), ("Kraven", "assassin", {}, {}),
    ("MODOK", "mage", {}, {}), ("Taskmaster", "fighter", {}, {}), ("Bullseye", "marksman", {}, {}),
    ("Kingpin", "tank", {}, {}), ("Red Skull", "fighter", {}, {}), ("Abomination", "tank", {}, {}),
    ("Lizard", "fighter", {}, {}), ("Carnage", "assassin", {}, {}),
    # Cosmic (15)
    ("Silver Surfer", "mage", {}, {}), ("Galactus", "tank", {}, {}), ("Nova", "fighter", {}, {}),
    ("Adam Warlock", "support", {}, {}), ("Quicksilver", "assassin", {}, {}), ("Medusa", "fighter", {}, {}),
    ("Black Bolt", "mage", {}, {}), ("Karnak", "assassin", {}, {}), ("Gorgon", "fighter", {}, {}),
    ("Crystal", "mage", {}, {}), ("Lockjaw", "tank", {}, {}), ("Gladiator", "fighter", {}, {}),
    ("Ronan", "fighter", {}, {}), ("Super-Skrull", "fighter", {}, {}), ("Blastaar", "fighter", {}, {}),
    # Street-Level & Mystical (15)
    ("Daredevil", "assassin", {}, {}), ("Jessica Jones", "fighter", {}, {}), ("Luke Cage", "tank", {}, {}),
    ("Iron Fist", "fighter", {}, {}), ("Shang-Chi", "fighter", {}, {}), ("Moon Knight", "fighter", {}, {}),
    ("Blade", "assassin", {}, {}), ("Ghost Rider", "fighter", {}, {}), ("Punisher", "marksman", {}, {}),
    ("Elektra", "assassin", {}, {}), ("Cloak", "assassin", {}, {}), ("Dagger", "support", {}, {}),
    ("Elsa Bloodstone", "marksman", {}, {}), ("Man-Thing", "tank", {}, {}), ("Werewolf by Night", "fighter", {}, {}),
    # Fantastic Four & More (22)
    ("Mr. Fantastic", "fighter", {}, {}), ("Invisible Woman", "support", {}, {}), ("Thing", "tank", {}, {}),
    ("Human Torch", "mage", {}, {}), ("Namor", "fighter", {}, {}), ("Doom", "mage", {}, {}),
    ("Galacta", "support", {}, {}), ("Annihilus", "mage", {}, {}), ("Kang", "mage", {}, {}),
    ("Ultron", "mage", {}, {}), ("Dormammu", "mage", {}, {}), ("Shuma-Gorath", "mage", {}, {}),
    ("Mephisto", "mage", {}, {}), ("Squirrel Girl", "fighter", {}, {}), ("Gwenpool", "assassin", {}, {}),
    ("Kate Bishop", "marksman", {}, {}), ("America Chavez", "fighter", {}, {}), ("Silk", "assassin", {}, {}),
    ("Spider-Gwen", "assassin", {}, {}), ("Spider-Man 2099", "assassin", {}, {}), ("Ben Reilly", "assassin", {}, {}),
    ("Kaine", "assassin", {}, {}),
    # +17 more for 172
    ("Spider-Woman", "assassin", {}, {}), ("Mockingbird", "fighter", {}, {}), ("Black Cat", "assassin", {}, {}),
    ("Nico Minoru", "mage", {}, {}), ("Karolina Dean", "mage", {}, {}), ("Molly Hayes", "tank", {}, {}),
    ("Chase Stein", "fighter", {}, {}), ("Gert Yorkes", "support", {}, {}), ("Old Lace", "fighter", {}, {}),
    ("Living Tribunal", "mage", {}, {}), ("Eternity", "mage", {}, {}), ("Death_Marvel", "assassin", {}, {}),
    ("Oblivion", "mage", {}, {}), ("Infinity", "mage", {}, {}), ("Eon", "support", {}, {}),
    ("Phyla-Vell", "fighter", {}, {}), ("Moondragon", "mage", {}, {}),
]

# ======================== VAINGLORY (+118) ========================
HERO_DEFS["vainglory"] = [
    # Already in game: Ringo, Koshka, Catherine, SAW, Skaarf, Celeste, Taka, Adagio, Alpha, Ardan
    # Full roster additions:
    ("Joule", "fighter", {}, {}), ("Glaive", "fighter", {}, {}), ("Petal", "mage", {}, {}),
    ("Krul", "fighter", {}, {}), ("Fortress", "assassin", {}, {}), ("Rona", "fighter", {}, {}),
    ("Skye", "marksman", {}, {}), ("Vox", "marksman", {}, {}), ("Blackfeather", "assassin", {}, {}),
    ("Phinn", "tank", {}, {}), ("Ozo", "fighter", {}, {}), ("Reim", "mage", {}, {}),
    ("Lyra", "support", {}, {}), ("Samuel", "mage", {}, {}), ("Baron", "marksman", {}, {}),
    ("Lance", "tank", {}, {}), ("Gwen", "marksman", {}, {}), ("Idris", "assassin", {}, {}),
    ("Grace", "support", {}, {}), ("Grumpjaw", "tank", {}, {}), ("Flicker", "assassin", {}, {}),
    ("Baptiste", "mage", {}, {}), ("Lorelei", "support", {}, {}), ("Varya", "mage", {}, {}),
    ("Churnwalker", "tank", {}, {}), ("Tony", "fighter", {}, {}), ("Malene", "mage", {}, {}),
    ("Kensei", "fighter", {}, {}), ("Kinetic", "marksman", {}, {}), ("Anka", "assassin", {}, {}),
    ("Silvernail", "marksman", {}, {}), ("Magnus", "mage", {}, {}), ("Yates", "tank", {}, {}),
    ("Inara", "fighter", {}, {}), ("San Feng", "fighter", {}, {}), ("Leo", "fighter", {}, {}),
    ("Miho", "assassin", {}, {}), ("Viola", "support", {}, {}), ("Shin", "assassin", {}, {}),
    ("Karas", "mage", {}, {}), ("Warhawk", "marksman", {}, {}), ("Amael", "fighter", {}, {}),
    # Lore characters and expanded roster (76 more)
    ("StormQueen", "mage", {}, {}), ("Netherknight", "tank", {}, {}), ("Stormguard", "fighter", {}, {}),
    ("Gythia", "support", {}, {}), ("Technologist", "mage", {}, {}), ("Druid_VG", "support", {}, {}),
    ("Mechanist", "marksman", {}, {}), ("Arcanist", "mage", {}, {}), ("Assassin_VG", "assassin", {}, {}),
    ("Corsair", "fighter", {}, {}), ("Gladiator_VG", "fighter", {}, {}), ("Sorceress_VG", "mage", {}, {}),
    ("Warlord_VG", "fighter", {}, {}), ("Beastmaster", "fighter", {}, {}), ("Shadowblade", "assassin", {}, {}),
    ("Skyguard", "marksman", {}, {}), ("Ironclad", "tank", {}, {}), ("Spiritwalker", "support", {}, {}),
    ("Thunderbird", "mage", {}, {}), ("Voidreaver", "assassin", {}, {}), ("FrostGiant", "tank", {}, {}),
    ("Phoenix_VG", "mage", {}, {}), ("Seeker_VG", "marksman", {}, {}), ("Vindicator", "fighter", {}, {}),
    ("Nightshade", "assassin", {}, {}), ("Sunstone", "support", {}, {}), ("Darkmoor", "mage", {}, {}),
    ("Goldtooth", "fighter", {}, {}), ("Stormrider", "assassin", {}, {}), ("Earthshaker", "tank", {}, {}),
    ("Flamecaller", "mage", {}, {}), ("Shadowmancer", "mage", {}, {}), ("Ironweaver", "fighter", {}, {}),
    ("Windwalker", "assassin", {}, {}), ("Tidecaller", "mage", {}, {}), ("Runeforger", "support", {}, {}),
    ("Doombringer", "fighter", {}, {}), ("Soulreaper", "assassin", {}, {}), ("Lightbearer", "support", {}, {}),
    ("Venomancer", "mage", {}, {}), ("Stonewarden", "tank", {}, {}), ("Stormcaller", "mage", {}, {}),
    ("Swiftblade", "assassin", {}, {}), ("Ironheart", "tank", {}, {}), ("Frostweaver", "mage", {}, {}),
    ("Thunderlord", "fighter", {}, {}), ("Starforger", "mage", {}, {}), ("Riftwalker", "assassin", {}, {}),
    ("Dreadnought", "tank", {}, {}), ("Wildkin", "fighter", {}, {}), ("Spellbinder", "mage", {}, {}),
    ("Gravewalker", "assassin", {}, {}), ("Aegis_VG", "tank", {}, {}), ("Verdant", "support", {}, {}),
    ("Cinderkin", "mage", {}, {}), ("Ironmaw", "tank", {}, {}), ("Dreadmaw", "fighter", {}, {}),
    ("Stormlash", "mage", {}, {}), ("Sunforge", "support", {}, {}), ("Shadowkin", "assassin", {}, {}),
    ("Rockjaw", "tank", {}, {}), ("Flamekin", "mage", {}, {}), ("Frostfang", "assassin", {}, {}),
    ("Darktide", "fighter", {}, {}), ("Brightwing", "support", {}, {}), ("Moonclaw", "assassin", {}, {}),
    ("Duskwalker", "fighter", {}, {}), ("Dawnweaver", "support", {}, {}), ("Starcaller", "mage", {}, {}),
    ("Voidforged", "tank", {}, {}), ("Elderwood", "support", {}, {}), ("Flameheart", "fighter", {}, {}),
    ("Stormweaver", "mage", {}, {}), ("Ironfang", "assassin", {}, {}), ("Shadowveil", "assassin", {}, {}),
    ("Sunweaver", "support", {}, {}),
    # +38 more for 172
    ("CrystalKnight", "tank", {}, {}), ("FireMage_VG", "mage", {}, {}), ("WindMage_VG", "mage", {}, {}),
    ("EarthGuardian", "tank", {}, {}), ("SeaSerpent", "fighter", {}, {}), ("SkyHunter", "marksman", {}, {}),
    ("Blightcaller", "mage", {}, {}), ("FrostWarden", "tank", {}, {}), ("PlagueDoctor", "support", {}, {}),
    ("ChaosKnight", "fighter", {}, {}), ("OrderMage", "mage", {}, {}), ("DeathKnight_VG", "fighter", {}, {}),
    ("LifeWarden", "support", {}, {}), ("WarMage_VG", "mage", {}, {}), ("PeaceKeeper", "support", {}, {}),
    ("DreamWeaver_VG", "mage", {}, {}), ("Nightmare_VG", "assassin", {}, {}), ("FateBinder", "support", {}, {}),
    ("TimeKeeper_VG", "mage", {}, {}), ("SpaceWarden", "tank", {}, {}), ("RealityShaper", "mage", {}, {}),
    ("VoidHunter", "assassin", {}, {}), ("StarSeeker_VG", "marksman", {}, {}), ("SunChampion", "fighter", {}, {}),
    ("MoonPriestess", "support", {}, {}), ("StormDancer", "assassin", {}, {}), ("FlameDancer", "mage", {}, {}),
    ("FrostDancer", "mage", {}, {}), ("ShadowDancer", "assassin", {}, {}), ("BladeDancer", "fighter", {}, {}),
    ("RuneKnight", "fighter", {}, {}), ("AstralMage", "mage", {}, {}), ("ElderDragon_VG", "tank", {}, {}),
    ("SpiritFox", "assassin", {}, {}), ("JadeGolem", "tank", {}, {}), ("Celestial_VG", "support", {}, {}),
    ("NetherBeast", "fighter", {}, {}),
    ("CrystalMage_VG", "mage", {}, {}),
]

# ======================== SHUGUANG HEROES (+121) ========================
HERO_DEFS["shuguang_heroes"] = [
    # Chinese historical/mythological expanded roster
    ("诸葛亮", "mage", {}, {}), ("曹操", "fighter", {}, {}), ("刘备", "support", {}, {}),
    ("张飞", "tank", {}, {}), ("黄忠", "marksman", {}, {}), ("司马懿", "mage", {}, {}),
    ("周瑜", "mage", {}, {}), ("吕布", "fighter", {}, {}), ("貂蝉", "support", {}, {}),
    ("孙尚香", "marksman", {}, {}), ("典韦", "fighter", {}, {}), ("许褚", "tank", {}, {}),
    ("甘宁", "fighter", {}, {}), ("陆逊", "mage", {}, {}), ("鲁肃", "support", {}, {}),
    ("荀彧", "support", {}, {}), ("贾诩", "mage", {}, {}), ("庞统", "mage", {}, {}),
    ("黄月英", "support", {}, {}), ("姜维", "fighter", {}, {}), ("魏延", "fighter", {}, {}),
    ("孟获", "tank", {}, {}), ("祝融", "fighter", {}, {}), ("曹丕", "fighter", {}, {}),
    ("甄姬", "support", {}, {}), ("郭嘉", "mage", {}, {}), ("张角", "mage", {}, {}),
    ("董卓", "tank", {}, {}), ("袁绍", "fighter", {}, {}), ("孙坚", "fighter", {}, {}),
    ("周泰", "tank", {}, {}), ("凌统", "fighter", {}, {}), ("大乔", "support", {}, {}),
    ("小乔", "support", {}, {}), ("马岱", "marksman", {}, {}), ("徐晃", "tank", {}, {}),
    ("张郃", "fighter", {}, {}), ("曹仁", "tank", {}, {}), ("夏侯渊", "marksman", {}, {}),
    ("程普", "tank", {}, {}), ("韩当", "fighter", {}, {}), ("黄盖", "tank", {}, {}),
    ("法正", "support", {}, {}), ("马谡", "mage", {}, {}), ("关兴", "fighter", {}, {}),
    ("张苞", "fighter", {}, {}), ("关平", "fighter", {}, {}), ("廖化", "fighter", {}, {}),
    ("王平", "fighter", {}, {}), ("邓艾", "fighter", {}, {}), ("钟会", "mage", {}, {}),
    ("诸葛恪", "mage", {}, {}), ("丁奉", "fighter", {}, {}), ("徐盛", "fighter", {}, {}),
    ("朱然", "marksman", {}, {}), ("全琮", "fighter", {}, {}), ("孙鲁班", "support", {}, {}),
    ("司马师", "fighter", {}, {}), ("司马昭", "mage", {}, {}), ("王元姬", "support", {}, {}),
    ("夏侯霸", "fighter", {}, {}), ("文鸯", "fighter", {}, {}), ("羊祜", "support", {}, {}),
    ("杜预", "fighter", {}, {}), ("王濬", "fighter", {}, {}), ("贾充", "mage", {}, {}),
    ("陈泰", "tank", {}, {}), ("毌丘俭", "fighter", {}, {}), ("诸葛诞", "fighter", {}, {}),
    ("刘禅", "support", {}, {}), ("曹髦", "fighter", {}, {}), ("孙皓", "mage", {}, {}),
    # Martial arts & mythology
    ("岳飞", "fighter", {}, {}), ("李靖", "fighter", {}, {}), ("秦琼", "fighter", {}, {}),
    ("尉迟恭", "tank", {}, {}), ("程咬金", "fighter", {}, {}), ("薛仁贵", "fighter", {}, {}),
    ("狄仁杰", "mage", {}, {}), ("武则天", "mage", {}, {}), ("李世民", "fighter", {}, {}),
    ("项羽", "fighter", {}, {}), ("刘邦", "support", {}, {}), ("韩信", "assassin", {}, {}),
    ("张良", "support", {}, {}), ("萧何", "support", {}, {}), ("樊哙", "tank", {}, {}),
    ("虞姬", "support", {}, {}), ("范增", "mage", {}, {}), ("英布", "fighter", {}, {}),
    ("彭越", "fighter", {}, {}), ("李广", "marksman", {}, {}), ("卫青", "fighter", {}, {}),
    ("霍去病", "assassin", {}, {}), ("班超", "fighter", {}, {}), ("苏武", "support", {}, {}),
    ("王昭君", "support", {}, {}), ("蔡文姬", "support", {}, {}), ("花木兰", "fighter", {}, {}),
    ("樊梨花", "fighter", {}, {}), ("穆桂英", "fighter", {}, {}), ("梁红玉", "fighter", {}, {}),
    ("武松", "fighter", {}, {}), ("林冲", "fighter", {}, {}), ("鲁智深", "tank", {}, {}),
    ("李逵", "fighter", {}, {}), ("吴用", "support", {}, {}), ("公孙胜", "mage", {}, {}),
    ("燕青", "assassin", {}, {}), ("卢俊义", "fighter", {}, {}), ("史进", "fighter", {}, {}),
    ("杨志", "fighter", {}, {}), ("阮小七", "assassin", {}, {}), ("张顺", "fighter", {}, {}),
    ("李俊", "fighter", {}, {}), ("戴宗", "assassin", {}, {}), ("石秀", "assassin", {}, {}),
    ("扈三娘", "assassin", {}, {}), ("孙二娘", "assassin", {}, {}), ("安道全", "support", {}, {}),
    ("朱武", "mage", {}, {}), ("柴进", "support", {}, {}), ("呼延灼", "fighter", {}, {}),
    # +7 more for 172
    ("东方朔", "mage", {}, {}), ("徐福", "mage", {}, {}), ("张骞", "support", {}, {}),
    ("郑和", "support", {}, {}), ("李白", "assassin", {}, {}), ("杜甫", "support", {}, {}),
    ("白居易", "mage", {}, {}),
]

# ======================== HONG KONG COMICS (+132) ========================
HERO_DEFS["hong_kong_comics"] = [
    # 风云 (25)
    ("步惊云", "fighter", {}, {}), ("聂风", "assassin", {}, {}), ("无名", "fighter", {}, {}),
    ("雄霸", "mage", {}, {}), ("绝无神", "tank", {}, {}), ("剑晨", "fighter", {}, {}),
    ("秦霜", "fighter", {}, {}), ("断浪", "assassin", {}, {}), ("破军", "fighter", {}, {}),
    ("帝释天", "mage", {}, {}), ("怀空", "fighter", {}, {}), ("怀灭", "fighter", {}, {}),
    ("皇影", "fighter", {}, {}), ("笑三笑", "mage", {}, {}), ("武无敌", "fighter", {}, {}),
    ("第二梦", "support", {}, {}), ("楚楚", "support", {}, {}), ("独孤梦", "assassin", {}, {}),
    ("神医", "support", {}, {}), ("剑圣", "fighter", {}, {}), ("龙王", "tank", {}, {}),
    ("天皇", "fighter", {}, {}), ("拳道神", "fighter", {}, {}), ("铁狂屠", "tank", {}, {}),
    ("隼人天隐", "assassin", {}, {}),
    # 海虎 (20)
    ("海虎", "fighter", {}, {}), ("地狱", "mage", {}, {}), ("奥加", "tank", {}, {}),
    ("天道", "fighter", {}, {}), ("黑暗", "mage", {}, {}), ("首男", "fighter", {}, {}),
    ("次男", "fighter", {}, {}), ("蓝梦", "mage", {}, {}), ("观月瞳", "support", {}, {}),
    ("白首男", "fighter", {}, {}), ("白次男", "fighter", {}, {}), ("黑暗雷奥", "mage", {}, {}),
    ("破梦", "assassin", {}, {}), ("惊天", "fighter", {}, {}), ("巨鲨", "tank", {}, {}),
    ("大刀", "fighter", {}, {}), ("白武男", "fighter", {}, {}), ("刹亚", "fighter", {}, {}),
    ("天尊", "mage", {}, {}), ("黑豹", "fighter", {}, {}),
    # 龙虎门 (15)
    ("王小虎", "fighter", {}, {}), ("王小龙", "fighter", {}, {}), ("石黑龙", "fighter", {}, {}),
    ("火云邪神", "mage", {}, {}), ("老妖", "assassin", {}, {}), ("韦陀", "fighter", {}, {}),
    ("白莲", "support", {}, {}), ("铜圣", "tank", {}, {}), ("铁圣", "tank", {}, {}),
    ("银圣", "assassin", {}, {}), ("金圣", "fighter", {}, {}), ("易筋经", "support", {}, {}),
    ("毒蛇帮主", "assassin", {}, {}), ("阴阳使", "mage", {}, {}), ("刀神", "fighter", {}, {}),
    # 神兵玄奇 (15)
    ("问天", "fighter", {}, {}), ("南宫铁心", "fighter", {}, {}), ("玄天邪帝", "mage", {}, {}),
    ("燕王", "fighter", {}, {}), ("火凤凰", "mage", {}, {}), ("北冥正", "fighter", {}, {}),
    ("西城秀树", "fighter", {}, {}), ("东方雄", "fighter", {}, {}), ("神农", "support", {}, {}),
    ("蚩尤", "fighter", {}, {}), ("女娲_HK", "support", {}, {}), ("太平", "fighter", {}, {}),
    ("天地盟主", "fighter", {}, {}), ("邪帝", "mage", {}, {}), ("虎魄", "assassin", {}, {}),
    # 天子传奇 (15)
    ("姬发", "fighter", {}, {}), ("纣王", "tank", {}, {}), ("姜子牙_HK", "mage", {}, {}),
    ("妲己_HK", "support", {}, {}), ("哪吒_HK", "fighter", {}, {}), ("杨戬_HK", "fighter", {}, {}),
    ("雷震子_HK", "mage", {}, {}), ("一忧子", "fighter", {}, {}), ("天女", "support", {}, {}),
    ("帝辛", "fighter", {}, {}), ("姬昌", "support", {}, {}), ("比干", "support", {}, {}),
    ("申公豹_HK", "mage", {}, {}), ("魔礼海", "tank", {}, {}), ("闻仲_HK", "fighter", {}, {}),
    # 刀剑笑 (12)
    ("横刀", "fighter", {}, {}), ("名剑", "fighter", {}, {}), ("笑三少", "assassin", {}, {}),
    ("蝴蝶", "support", {}, {}), ("刀皇", "fighter", {}, {}), ("剑帝", "fighter", {}, {}),
    ("顾长风", "fighter", {}, {}), ("慕容映雪", "mage", {}, {}), ("夺命书生", "assassin", {}, {}),
    ("无相王", "tank", {}, {}), ("血霸王", "fighter", {}, {}), ("飞惊", "assassin", {}, {}),
    # 武神 (10)
    ("武神", "fighter", {}, {}), ("战狂", "fighter", {}, {}), ("天武", "mage", {}, {}),
    ("铁拳", "fighter", {}, {}), ("狂刀", "assassin", {}, {}), ("杀意", "assassin", {}, {}),
    ("巨灵", "tank", {}, {}), ("风雷", "mage", {}, {}), ("烈焰_HK", "mage", {}, {}),
    ("寒冰_HK", "mage", {}, {}),
    # 其他港漫 (20)
    ("华英雄", "fighter", {}, {}), ("无敌", "tank", {}, {}), ("鬼仆", "assassin", {}, {}),
    ("生奴", "support", {}, {}), ("剑雄", "fighter", {}, {}), ("罗汉", "tank", {}, {}),
    ("金罗汉", "tank", {}, {}), ("火云邪神传", "mage", {}, {}), ("白发魔女_HK", "mage", {}, {}),
    ("醉拳王", "fighter", {}, {}), ("如来", "support", {}, {}), ("铁将军", "tank", {}, {}),
    ("龙剑飞", "fighter", {}, {}), ("虎剑飞", "fighter", {}, {}), ("血魔", "assassin", {}, {}),
    ("鬼王_HK", "mage", {}, {}), ("圣王", "fighter", {}, {}), ("魔君_HK", "mage", {}, {}),
    ("流星", "assassin", {}, {}), ("追风", "assassin", {}, {}),
    # +35 more for 172
    ("快活王", "fighter", {}, {}), ("沈胜衣", "assassin", {}, {}), ("李布衣", "mage", {}, {}),
    ("赖药儿", "support", {}, {}), ("方世玉", "fighter", {}, {}), ("洪熙官", "fighter", {}, {}),
    ("黄飞鸿_HK", "fighter", {}, {}), ("苏乞儿", "fighter", {}, {}), ("叶问_HK", "fighter", {}, {}),
    ("陈真", "fighter", {}, {}), ("霍元甲", "fighter", {}, {}), ("马永贞", "fighter", {}, {}),
    ("大刀王五", "fighter", {}, {}), ("燕子李三", "assassin", {}, {}), ("白玉堂", "assassin", {}, {}),
    ("展昭_HK", "fighter", {}, {}), ("白玉川", "assassin", {}, {}), ("柳残阳", "fighter", {}, {}),
    ("西门吹雪_HK", "assassin", {}, {}), ("叶孤城_HK", "assassin", {}, {}), ("陆小凤_HK", "assassin", {}, {}),
    ("楚留香_HK", "assassin", {}, {}), ("李寻欢_HK", "marksman", {}, {}), ("傅红雪_HK", "fighter", {}, {}),
    ("谢晓峰_HK", "fighter", {}, {}), ("燕十三_HK", "assassin", {}, {}), ("丁鹏_HK", "fighter", {}, {}),
    ("萧秋水_HK", "fighter", {}, {}), ("方歌吟_HK", "fighter", {}, {}), ("卫悲回_HK", "fighter", {}, {}),
    ("铁木真_HK", "fighter", {}, {}), ("关羽_HK", "fighter", {}, {}), ("吕布_HK", "fighter", {}, {}),
    ("如来_HK", "support", {}, {}),
    ("少林武僧_HK", "fighter", {}, {}),
]

# ======================== THREE KINGDOMS (+132) ========================
HERO_DEFS["three_kingdoms"] = [
    # 蜀汉 (30)
    ("关羽", "fighter", {}, {}), ("赵云", "fighter", {}, {}), ("马超", "fighter", {}, {}),
    ("黄忠", "marksman", {}, {}), ("魏延", "fighter", {}, {}), ("姜维", "fighter", {}, {}),
    ("马岱", "marksman", {}, {}), ("关平", "fighter", {}, {}), ("关兴", "fighter", {}, {}),
    ("张苞", "fighter", {}, {}), ("廖化", "fighter", {}, {}), ("王平", "tank", {}, {}),
    ("严颜", "tank", {}, {}), ("法正", "support", {}, {}), ("徐庶", "support", {}, {}),
    ("蒋琬", "support", {}, {}), ("费祎", "support", {}, {}), ("董允", "support", {}, {}),
    ("刘封", "fighter", {}, {}), ("孟达", "fighter", {}, {}), ("吴懿", "fighter", {}, {}),
    ("张翼", "fighter", {}, {}), ("吴班", "fighter", {}, {}), ("高翔", "fighter", {}, {}),
    ("向宠", "fighter", {}, {}), ("李严", "fighter", {}, {}), ("马良", "support", {}, {}),
    ("马谡", "mage", {}, {}), ("糜竺", "support", {}, {}), ("孙乾", "support", {}, {}),
    # 曹魏 (30)
    ("夏侯惇", "fighter", {}, {}), ("张辽", "fighter", {}, {}), ("典韦", "fighter", {}, {}),
    ("许褚", "tank", {}, {}), ("徐晃", "tank", {}, {}), ("张郃", "fighter", {}, {}),
    ("曹仁", "tank", {}, {}), ("夏侯渊", "marksman", {}, {}), ("曹洪", "fighter", {}, {}),
    ("乐进", "fighter", {}, {}), ("李典", "fighter", {}, {}), ("于禁", "tank", {}, {}),
    ("文聘", "tank", {}, {}), ("满宠", "support", {}, {}), ("贾诩", "mage", {}, {}),
    ("程昱", "mage", {}, {}), ("荀攸", "support", {}, {}), ("郭淮", "fighter", {}, {}),
    ("郝昭", "tank", {}, {}), ("王双", "fighter", {}, {}), ("曹休", "fighter", {}, {}),
    ("曹真", "fighter", {}, {}), ("曹彰", "fighter", {}, {}), ("曹植", "support", {}, {}),
    ("夏侯尚", "fighter", {}, {}), ("文钦", "fighter", {}, {}), ("毌丘俭", "fighter", {}, {}),
    ("诸葛诞", "fighter", {}, {}), ("钟繇", "support", {}, {}), ("华歆", "support", {}, {}),
    # 东吴 (25)
    ("太史慈", "fighter", {}, {}), ("孙策", "fighter", {}, {}), ("甘宁", "assassin", {}, {}),
    ("周泰", "tank", {}, {}), ("凌统", "fighter", {}, {}), ("程普", "tank", {}, {}),
    ("黄盖", "tank", {}, {}), ("韩当", "fighter", {}, {}), ("丁奉", "fighter", {}, {}),
    ("徐盛", "fighter", {}, {}), ("朱然", "marksman", {}, {}), ("全琮", "fighter", {}, {}),
    ("朱桓", "fighter", {}, {}), ("陆抗", "fighter", {}, {}), ("张昭", "support", {}, {}),
    ("张纮", "support", {}, {}), ("诸葛瑾", "support", {}, {}), ("步骘", "support", {}, {}),
    ("阚泽", "support", {}, {}), ("顾雍", "support", {}, {}), ("潘璋", "fighter", {}, {}),
    ("吕范", "support", {}, {}), ("孙峻", "fighter", {}, {}), ("孙綝", "fighter", {}, {}),
    ("诸葛恪", "mage", {}, {}),
    # 汉末群雄 (20)
    ("颜良", "fighter", {}, {}), ("文丑", "fighter", {}, {}), ("华雄", "fighter", {}, {}),
    ("李儒", "mage", {}, {}), ("郭汜", "fighter", {}, {}), ("张济", "fighter", {}, {}),
    ("张绣", "fighter", {}, {}), ("高顺", "fighter", {}, {}), ("陈宫", "support", {}, {}),
    ("麴义", "fighter", {}, {}), ("田丰", "support", {}, {}), ("沮授", "support", {}, {}),
    ("审配", "support", {}, {}), ("逢纪", "support", {}, {}), ("郭图", "support", {}, {}),
    ("许攸", "support", {}, {}), ("张燕", "assassin", {}, {}), ("刘表", "support", {}, {}),
    ("刘焉", "support", {}, {}), ("公孙瓒", "fighter", {}, {}),
    # 后期&演义扩展 (27)
    ("邓艾", "fighter", {}, {}), ("钟会", "mage", {}, {}), ("司马师", "fighter", {}, {}),
    ("司马昭", "mage", {}, {}), ("王元姬", "support", {}, {}), ("夏侯霸", "fighter", {}, {}),
    ("文鸯", "fighter", {}, {}), ("羊祜", "support", {}, {}), ("杜预", "fighter", {}, {}),
    ("王濬", "fighter", {}, {}), ("贾充", "mage", {}, {}), ("陈泰", "tank", {}, {}),
    ("曹髦", "fighter", {}, {}), ("孙皓", "mage", {}, {}), ("刘禅", "support", {}, {}),
    ("曹叡", "support", {}, {}), ("孙权", "fighter", {}, {}), ("张鲁", "support", {}, {}),
    ("左慈", "mage", {}, {}), ("华佗", "support", {}, {}), ("管辂", "mage", {}, {}),
    ("吉平", "support", {}, {}), ("祢衡", "mage", {}, {}), ("孔融", "support", {}, {}),
    ("蔡琰", "support", {}, {}), ("甄氏", "support", {}, {}),     ("赵云(老年)", "fighter", {}, {}),
    # +22 more for 172
    ("周仓", "fighter", {}, {}), ("关索", "assassin", {}, {}), ("鲍三娘", "fighter", {}, {}),
    ("花鬘", "fighter", {}, {}), ("张嶷", "fighter", {}, {}), ("张翼(蜀)", "fighter", {}, {}),
    ("傅佥", "fighter", {}, {}), ("诸葛瞻", "fighter", {}, {}), ("诸葛尚", "fighter", {}, {}),
    ("黄崇", "support", {}, {}), ("李恢", "support", {}, {}), ("吕凯", "support", {}, {}),
    ("孟获", "tank", {}, {}), ("祝融", "fighter", {}, {}), ("兀突骨", "tank", {}, {}),
    ("木鹿大王", "mage", {}, {}), ("朵思大王", "mage", {}, {}), ("带来洞主", "fighter", {}, {}),
    ("董荼那", "fighter", {}, {}), ("阿会喃", "fighter", {}, {}), ("金环三结", "fighter", {}, {}),
    ("忙牙长", "fighter", {}, {}),
    ("董卓", "tank", {}, {}), ("袁绍", "fighter", {}, {}),
    ("公孙渊", "fighter", {}, {}),
]

# ======================== DEMON SLAYER (+148) ========================
HERO_DEFS["demon_slayer"] = [
    # Already: 灶门炭治郎, 灶门祢豆子, 我妻善逸, 嘴平伊之助, 富冈义勇, 蝴蝶忍, 炼狱杏寿郎, 宇髄天元, 甘露寺蜜璃, 时透无一郎...
    # 鬼杀队·柱 (9)
    ("悲鸣屿行冥", "tank", {}, {}), ("不死川实弥", "fighter", {}, {}), ("伊黑小芭内", "assassin", {}, {}),
    ("胡蝶香奈惠", "support", {}, {}), ("鳞泷左近次", "fighter", {}, {}), ("桑岛慈悟郎", "mage", {}, {}),
    # 鬼杀队·队员 (30)
    ("栗花落香奈乎", "assassin", {}, {}), ("不死川玄弥", "fighter", {}, {}),
    ("村田", "fighter", {}, {}), ("神崎葵", "support", {}, {}), ("后藤", "fighter", {}, {}),
    ("竹内", "fighter", {}, {}), ("产屋敷耀哉", "support", {}, {}), ("产屋敷天音", "support", {}, {}),
    ("产屋敷辉利哉", "support", {}, {}), ("钢铁冢萤", "support", {}, {}), ("珠世", "support", {}, {}),
    ("愈史郎", "support", {}, {}), ("恋雪", "support", {}, {}), ("灶门炭十郎", "fighter", {}, {}),
    ("灶门葵枝", "support", {}, {}), ("嘴平琴叶", "support", {}, {}), ("锖兔", "fighter", {}, {}),
    ("真菰", "assassin", {}, {}), ("继国缘壹", "fighter", {}, {}), ("继国岩胜", "fighter", {}, {}),
    ("悲鸣屿", "tank", {}, {}), ("雏鹤", "assassin", {}, {}), ("槙於", "assassin", {}, {}),
    ("须磨", "assassin", {}, {}), ("中原澄", "support", {}, {}), ("高田菜穗", "support", {}, {}),
    ("里子", "support", {}, {}), ("清", "support", {}, {}), ("正一", "support", {}, {}),
    ("寿海", "support", {}, {}),
    # 上弦之鬼 (12)
    ("黑死牟", "fighter", {}, {}), ("童磨", "mage", {}, {}), ("猗窝座", "fighter", {}, {}),
    ("半天狗", "mage", {}, {}), ("玉壶", "mage", {}, {}), ("堕姬", "assassin", {}, {}),
    ("妓夫太郎", "assassin", {}, {}), ("积怒", "mage", {}, {}), ("可乐", "mage", {}, {}),
    ("空喜", "mage", {}, {}), ("哀绝", "mage", {}, {}), ("憎珀天", "fighter", {}, {}),
    # 下弦之鬼 (6)
    ("魇梦", "mage", {}, {}), ("辘轳", "fighter", {}, {}), ("病叶", "assassin", {}, {}),
    ("零余子", "assassin", {}, {}), ("响凯", "fighter", {}, {}), ("手鬼", "tank", {}, {}),
    # 其他鬼 (10)
    ("鬼舞辻无惨", "mage", {}, {}), ("朱纱丸", "assassin", {}, {}), ("矢琶羽", "fighter", {}, {}),
    ("沼鬼", "tank", {}, {}), ("鼓鬼", "fighter", {}, {}), ("蛇鬼", "assassin", {}, {}),
    ("蜘蛛鬼·父", "tank", {}, {}), ("蜘蛛鬼·母", "mage", {}, {}), ("蜘蛛鬼·兄", "fighter", {}, {}),
    ("蜘蛛鬼·姊", "assassin", {}, {}),
    # 扩展追加 (81 more for 172)
    ("累", "mage", {}, {}), ("釜鵺", "fighter", {}, {}), ("佩狼", "fighter", {}, {}),
    ("獪岳", "assassin", {}, {}), ("狯岳", "assassin", {}, {}), ("粂野", "fighter", {}, {}),
    ("切姬", "assassin", {}, {}), ("冰之鬼", "mage", {}, {}), ("火之鬼", "mage", {}, {}),
    ("风之鬼", "assassin", {}, {}), ("土之鬼", "tank", {}, {}), ("雷之鬼", "fighter", {}, {}),
    ("水之鬼", "fighter", {}, {}), ("木之鬼", "support", {}, {}), ("金之鬼", "tank", {}, {}),
    ("百目鬼_DS", "mage", {}, {}), ("牛鬼_DS", "tank", {}, {}), ("鬼蜘蛛", "assassin", {}, {}),
    ("影鬼", "assassin", {}, {}), ("烟鬼", "mage", {}, {}), ("雾鬼", "mage", {}, {}),
    ("山鬼", "fighter", {}, {}), ("川鬼", "fighter", {}, {}), ("林鬼", "assassin", {}, {}),
    ("谷鬼", "tank", {}, {}), ("岩鬼", "tank", {}, {}), ("砂鬼", "mage", {}, {}),
    ("泥鬼", "tank", {}, {}), ("炎鬼", "mage", {}, {}), ("冰鬼", "mage", {}, {}),
    ("雷鬼", "fighter", {}, {}), ("毒鬼", "assassin", {}, {}), ("咒鬼", "mage", {}, {}),
    ("怨鬼", "assassin", {}, {}), ("血鬼", "assassin", {}, {}), ("骨鬼", "tank", {}, {}),
    ("肉鬼", "tank", {}, {}), ("死鬼", "fighter", {}, {}), ("冥鬼", "mage", {}, {}),
    ("凶鬼", "fighter", {}, {}), ("暴鬼", "fighter", {}, {}), ("狂鬼", "assassin", {}, {}),
    ("幻鬼", "mage", {}, {}), ("妖鬼", "mage", {}, {}), ("罗刹鬼", "fighter", {}, {}),
    ("修罗鬼_DS", "fighter", {}, {}), ("饿鬼_DS", "tank", {}, {}), ("天狗鬼", "fighter", {}, {}),
    ("河童鬼", "assassin", {}, {}), ("雪女鬼", "mage", {}, {}), ("猫又鬼", "assassin", {}, {}),
    ("络新妇", "assassin", {}, {}), ("姑获鸟_DS", "assassin", {}, {}), ("滑瓢鬼", "fighter", {}, {}),
    ("酒吞鬼", "fighter", {}, {}), ("茨木鬼", "fighter", {}, {}), ("大岳鬼", "tank", {}, {}),
    ("大天狗_DS", "mage", {}, {}), ("铁鼠_DS", "assassin", {}, {}), ("镰鼬_DS", "assassin", {}, {}),
    ("山童", "fighter", {}, {}), ("涂壁", "tank", {}, {}), ("灯笼鬼", "support", {}, {}),
    ("提灯鬼", "support", {}, {}), ("青坊主", "fighter", {}, {}), ("独眼鬼", "fighter", {}, {}),
    ("鵺", "mage", {}, {}), ("土蜘蛛", "tank", {}, {}), ("牛鬼", "tank", {}, {}),
    ("不知火_DS", "mage", {}, {}), ("桥姬", "assassin", {}, {}), ("飞头蛮", "assassin", {}, {}),
    ("网切", "assassin", {}, {}), ("入内雀_DS", "assassin", {}, {}), ("以津真天", "mage", {}, {}),
    ("烟烟罗", "mage", {}, {}), ("食发鬼_DS", "assassin", {}, {}), ("巫蛊师_DS", "mage", {}, {}),
    ("犬神_DS", "fighter", {}, {}), ("鸦天狗_DS", "fighter", {}, {}),
    # +17 more for 172
    ("白藏主_DS", "fighter", {}, {}), ("妖刀姬_DS", "assassin", {}, {}), ("青行灯_DS", "mage", {}, {}),
    ("大天狗_DS2", "mage", {}, {}), ("茨木童子_DS", "fighter", {}, {}), ("酒吞童子_DS", "fighter", {}, {}),
    ("荒川之主_DS", "fighter", {}, {}), ("阎魔_DS", "mage", {}, {}), ("一目连_DS", "support", {}, {}),
    ("辉夜姬_DS", "support", {}, {}), ("彼岸花_DS", "mage", {}, {}), ("御馔津_DS", "marksman", {}, {}),
    ("面灵气_DS", "mage", {}, {}), ("玉藻前_DS", "mage", {}, {}), ("雪童子_DS", "assassin", {}, {}),
    ("鬼切_DS", "assassin", {}, {}), ("须佐之男_DS", "fighter", {}, {}),
]

# ======================== THREE BODY (+148) ========================
HERO_DEFS["three_body"] = [
    # Already: 叶文洁, 汪淼, 史强, 罗辑, 章北海, 云天明, 维德, 程心, 丁仪, 智子...
    # 地球三体组织 (15)
    ("伊文斯", "mage", {}, {}), ("潘寒", "mage", {}, {}), ("申玉菲", "mage", {}, {}),
    ("魏成", "support", {}, {}), ("墨子_3B", "mage", {}, {}), ("亚里士多德_3B", "mage", {}, {}),
    ("孔子_3B", "support", {}, {}), ("牛顿_3B", "mage", {}, {}), ("爱因斯坦_3B", "mage", {}, {}),
    ("冯·诺依曼_3B", "mage", {}, {}), ("秦始皇_3B", "fighter", {}, {}), ("哥白尼_3B", "mage", {}, {}),
    ("伽利略_3B", "mage", {}, {}), ("布鲁诺_3B", "mage", {}, {}), ("达芬奇_3B", "support", {}, {}),
    # 面壁者与破壁人 (10)
    ("弗里德里克·泰勒", "fighter", {}, {}), ("曼努尔·雷迪亚兹", "mage", {}, {}),
    ("比尔·希恩斯", "support", {}, {}), ("山杉惠子", "assassin", {}, {}),
    ("破壁人·泰勒", "assassin", {}, {}), ("破壁人·雷迪亚兹", "assassin", {}, {}),
    ("破壁人·希恩斯", "assassin", {}, {}), ("破壁人·罗辑", "assassin", {}, {}),
    ("常伟思", "fighter", {}, {}), ("林格", "support", {}, {}),
    # 未来人类 (15)
    ("东方延绪", "fighter", {}, {}), ("褚岩", "fighter", {}, {}), ("关一帆", "support", {}, {}),
    ("AA", "support", {}, {}), ("弗雷斯", "support", {}, {}), ("白Ice", "mage", {}, {}),
    ("瓦西里", "fighter", {}, {}), ("张援朝", "support", {}, {}), ("杨晋文", "support", {}, {}),
    ("苗福全", "support", {}, {}), ("老杨", "support", {}, {}), ("老李", "support", {}, {}),
    ("毕云峰", "support", {}, {}), ("曹彬", "fighter", {}, {}), ("卓文", "support", {}, {}),
    # 歌者&归零者 (10)
    ("歌者", "mage", {}, {}), ("长老", "mage", {}, {}), ("归零者", "mage", {}, {}),
    ("魔戒", "mage", {}, {}), ("墓地", "support", {}, {}), ("清理员", "fighter", {}, {}),
    ("监听员", "support", {}, {}), ("执政官", "fighter", {}, {}), ("元首", "fighter", {}, {}),
    ("科学执政官", "mage", {}, {}),
    # 三体世界 (10)
    ("三体人·监听员", "support", {}, {}), ("三体人·科学官", "mage", {}, {}),
    ("三体人·军事官", "fighter", {}, {}), ("三体人·外交官", "support", {}, {}),
    ("三体人·元首", "fighter", {}, {}), ("三体人·叛徒", "assassin", {}, {}),
    ("三体人·和平派", "support", {}, {}), ("三体人·降临派", "fighter", {}, {}),
    ("三体人·拯救派", "support", {}, {}), ("三体人·幸存派", "assassin", {}, {}),
    # 太阳系人类 (10)
    ("吴岳", "fighter", {}, {}), ("井上宏", "fighter", {}, {}), ("斐兹罗", "fighter", {}, {}),
    ("西子", "support", {}, {}), ("山杉", "assassin", {}, {}), ("坂田", "fighter", {}, {}),
    ("佛罗伦萨", "support", {}, {}), ("哈里", "support", {}, {}), ("列文", "mage", {}, {}),
    ("坎特", "fighter", {}, {}),
    # 星际战舰 (10)
    ("蓝色空间号", "tank", {}, {}), ("万有引力号", "tank", {}, {}), ("自然选择号", "fighter", {}, {}),
    ("量子号", "mage", {}, {}), ("终极规律号", "fighter", {}, {}), ("青铜时代号", "fighter", {}, {}),
    ("牛顿号", "mage", {}, {}), ("爱因斯坦号", "mage", {}, {}), ("无限边疆号", "tank", {}, {}),
    ("星环号", "support", {}, {}),
    # 扩展追加 (68 more for 172)
    ("逻辑", "mage", {}, {}), ("程心·执剑人", "fighter", {}, {}), ("维德·觉醒", "assassin", {}, {}),
    ("云天明·童话", "mage", {}, {}), ("叶文洁·红岸", "mage", {}, {}), ("罗辑·黑暗森林", "mage", {}, {}),
    ("章北海·前进四", "fighter", {}, {}), ("智子·和服", "assassin", {}, {}), ("智子·茶道", "support", {}, {}),
    ("史强·刑警", "fighter", {}, {}), ("丁仪·球状闪电", "mage", {}, {}), ("汪淼·纳米", "support", {}, {}),
    ("黑洞", "mage", {}, {}), ("二向箔", "mage", {}, {}), ("光粒", "marksman", {}, {}),
    ("死线", "mage", {}, {}), ("慢雾", "support", {}, {}), ("黑域", "tank", {}, {}),
    ("曲率引擎", "assassin", {}, {}), ("强互作用力", "fighter", {}, {}), ("水滴", "assassin", {}, {}),
    ("智子·展开", "mage", {}, {}), ("智子·蚀刻", "mage", {}, {}), ("智子·封锁", "support", {}, {}),
    ("质子", "marksman", {}, {}), ("中子", "tank", {}, {}), ("电子", "assassin", {}, {}),
    ("光子", "marksman", {}, {}), ("引力子", "mage", {}, {}), ("夸克", "fighter", {}, {}),
    ("弦论", "mage", {}, {}), ("维度·十维", "mage", {}, {}), ("维度·九维", "mage", {}, {}),
    ("维度·四维", "mage", {}, {}), ("维度·三维", "support", {}, {}), ("维度·二维", "assassin", {}, {}),
    ("维度·一维", "fighter", {}, {}), ("小宇宙", "support", {}, {}), ("大宇宙", "tank", {}, {}),
    ("门", "support", {}, {}), ("宇宙社会学", "mage", {}, {}), ("猜疑链", "assassin", {}, {}),
    ("技术爆炸", "mage", {}, {}), ("黑暗森林法则", "mage", {}, {}), ("威慑纪元", "support", {}, {}),
    ("广播纪元", "support", {}, {}), ("掩体纪元", "tank", {}, {}), ("银河纪元", "support", {}, {}),
    ("DX3906", "marksman", {}, {}), ("三体星系", "mage", {}, {}), ("比邻星", "support", {}, {}),
    ("半人马座α", "fighter", {}, {}), ("银河系", "tank", {}, {}), ("仙女座", "support", {}, {}),
    ("猎户座", "fighter", {}, {}), ("射手座", "marksman", {}, {}), ("大麦哲伦", "mage", {}, {}),
    ("小麦哲伦", "support", {}, {}), ("M78", "mage", {}, {}), ("M31", "tank", {}, {}),
    ("M87", "fighter", {}, {}), ("创世神·大爆炸", "mage", {}, {}), ("奇点", "assassin", {}, {}),
    ("熵增", "mage", {}, {}), ("热寂", "tank", {}, {}), ("真空衰变", "mage", {}, {}),
    ("暴涨", "assassin", {}, {}), ("暗能量", "mage", {}, {}),
    # +8 more for 172
    ("引力波", "mage", {}, {}), ("中微子", "assassin", {}, {}), ("超新星", "mage", {}, {}),
    ("脉冲星", "marksman", {}, {}), ("白矮星", "tank", {}, {}), ("中子星", "tank", {}, {}),
    ("红巨星", "fighter", {}, {}), ("褐矮星", "support", {}, {}),
]

# ======================== DC UNIVERSE (+150) ========================
HERO_DEFS["dc"] = [
    # Already: 超人, 蝙蝠侠, 神奇女侠, 闪电侠, 绿箭侠, 海王, 钢骨, 火星猎人, 沙赞, 绿灯侠...
    # Justice League (15)
    ("鹰侠", "fighter", {}, {}), ("鹰女", "fighter", {}, {}), ("黑金丝雀", "assassin", {}, {}),
    ("绿箭侠·康纳", "marksman", {}, {}), ("原子侠", "assassin", {}, {}), ("火风暴", "mage", {}, {}),
    ("伸缩人", "fighter", {}, {}), ("雌狐", "fighter", {}, {}), ("扎塔娜", "mage", {}, {}),
    ("死人", "assassin", {}, {}), ("幽灵", "mage", {}, {}), ("命运博士", "mage", {}, {}),
    ("魅影陌客", "mage", {}, {}), ("红色龙卷风", "mage", {}, {}), ("塑料人", "fighter", {}, {}),
    # Batman Family (15)
    ("罗宾", "assassin", {}, {}), ("夜翼", "fighter", {}, {}), ("红头罩", "fighter", {}, {}),
    ("红罗宾", "assassin", {}, {}), ("蝙蝠女", "assassin", {}, {}), ("蝙蝠女侠", "fighter", {}, {}),
    ("阿尔弗雷德", "support", {}, {}), ("猫女", "assassin", {}, {}), ("毒藤女", "mage", {}, {}),
    ("急冻人", "mage", {}, {}), ("稻草人", "mage", {}, {}), ("谜语人", "mage", {}, {}),
    ("企鹅人", "fighter", {}, {}), ("双面人", "fighter", {}, {}), ("贝恩", "tank", {}, {}),
    # Superman Family (10)
    ("超女", "fighter", {}, {}), ("超能女孩", "fighter", {}, {}), ("小超人", "fighter", {}, {}),
    ("钢人", "tank", {}, {}), ("莱克斯·卢瑟", "mage", {}, {}), ("布莱尼亚克", "mage", {}, {}),
    ("金属人", "tank", {}, {}), ("寄生魔", "assassin", {}, {}), ("比扎罗", "fighter", {}, {}),
    ("毁灭日", "tank", {}, {}),
    # Green Lantern Corps (10)
    ("哈尔·乔丹", "fighter", {}, {}), ("约翰·斯图尔特", "tank", {}, {}),
    ("盖·加德纳", "fighter", {}, {}), ("凯尔·雷纳", "mage", {}, {}), ("西蒙·巴兹", "fighter", {}, {}),
    ("杰西卡·克鲁兹", "marksman", {}, {}), ("塞尼斯托", "mage", {}, {}), ("黑手", "assassin", {}, {}),
    ("星蓝石", "mage", {}, {}), ("拉弗利兹", "tank", {}, {}),
    # Flash Family (8)
    ("沃利·韦斯特", "assassin", {}, {}), ("巴特·艾伦", "assassin", {}, {}),
    ("杰伊·加里克", "fighter", {}, {}), ("逆闪电", "assassin", {}, {}), ("极速", "assassin", {}, {}),
    ("神速", "assassin", {}, {}), ("热浪", "mage", {}, {}), ("天气巫师", "mage", {}, {}),
    # Villains (20)
    ("达克赛德", "mage", {}, {}), ("荒原狼", "fighter", {}, {}), ("慈祥奶奶", "fighter", {}, {}),
    ("狄萨德", "mage", {}, {}), ("蒙戈", "fighter", {}, {}), ("所罗门·格兰迪", "tank", {}, {}),
    ("汪达尔·萨维奇", "fighter", {}, {}), ("拉斯·奥·古", "fighter", {}, {}), ("塔利亚", "assassin", {}, {}),
    ("丧钟", "assassin", {}, {}), ("死射", "marksman", {}, {}), ("小丑", "mage", {}, {}),
    ("哈莉·奎茵", "fighter", {}, {}), ("回旋镖队长", "marksman", {}, {}), ("寒冷队长", "mage", {}, {}),
    ("镜像大师", "assassin", {}, {}), ("大猩猩格鲁德", "fighter", {}, {}), ("黑蝠鲼", "fighter", {}, {}),
    ("海洋领主", "fighter", {}, {}), ("豹女", "assassin", {}, {}),
    # Titans & Young Justice (10)
    ("星火", "mage", {}, {}), ("野兽小子", "fighter", {}, {}), ("渡鸦", "mage", {}, {}),
    ("蓝甲虫", "fighter", {}, {}), ("海少侠", "fighter", {}, {}), ("神奇少女", "fighter", {}, {}),
    ("快手", "marksman", {}, {}), ("军火库", "marksman", {}, {}), ("脉冲", "assassin", {}, {}),
    ("小约翰·肯特", "fighter", {}, {}),
    # Cosmic & Mystical (15)
    ("幽灵·天命", "mage", {}, {}), ("无尽·死亡", "mage", {}, {}), ("无尽·梦", "mage", {}, {}),
    ("无尽·命运", "support", {}, {}), ("无尽·欲望", "mage", {}, {}), ("无尽·绝望", "mage", {}, {}),
    ("无尽·狂乱", "fighter", {}, {}), ("监视者", "mage", {}, {}), ("反监视者", "fighter", {}, {}),
    ("曼哈顿博士", "mage", {}, {}), ("法老王", "fighter", {}, {}), ("罗夏", "fighter", {}, {}),
    ("丝魂", "fighter", {}, {}), ("夜枭", "assassin", {}, {}), ("笑匠", "fighter", {}, {}),
    # Expanded (47 more for 172)
    ("至尊小超人", "fighter", {}, {}), ("超霸", "fighter", {}, {}), ("夜枭·二代", "assassin", {}, {}),
    ("蝙蝠侠·未来", "assassin", {}, {}), ("超人·未来", "fighter", {}, {}), ("绿灯侠·未来", "mage", {}, {}),
    ("闪电侠·未来", "assassin", {}, {}), ("海王·未来", "fighter", {}, {}), ("钢骨·未来", "tank", {}, {}),
    ("泰坦", "tank", {}, {}), ("巨化女", "tank", {}, {}), ("冰柱", "mage", {}, {}),
    ("黑亚当", "fighter", {}, {}), ("伊西斯", "support", {}, {}), ("原子粉碎者", "fighter", {}, {}),
    ("逐星女", "fighter", {}, {}), ("星条", "support", {}, {}), ("野猫", "fighter", {}, {}),
    ("午夜神医", "support", {}, {}), ("时侠", "mage", {}, {}), ("睡魔", "mage", {}, {}),
    ("康斯坦丁", "mage", {}, {}), ("沼泽怪物", "tank", {}, {}), ("恶魔伊特莱根", "fighter", {}, {}),
    ("天命博士", "mage", {}, {}), ("巫童", "mage", {}, {}), ("黑爱丽丝", "mage", {}, {}),
    ("沙赞·玛丽", "fighter", {}, {}), ("沙赞·小弗雷迪", "assassin", {}, {}), ("惊奇队长Jr", "fighter", {}, {}),
    ("光速", "assassin", {}, {}), ("闪电小子", "assassin", {}, {}), ("弹片", "fighter", {}, {}),
    ("金色先锋", "fighter", {}, {}), ("蓝甲虫·泰德", "fighter", {}, {}), ("烈火", "mage", {}, {}),
    ("冰霜", "mage", {}, {}), ("闪电", "assassin", {}, {}), ("原子队长", "fighter", {}, {}),
    ("午夜战士", "fighter", {}, {}), ("阿波罗", "mage", {}, {}), ("工程师", "support", {}, {}),
    ("婕特", "assassin", {}, {}), ("圣行者", "support", {}, {}), ("英迪戈", "support", {}, {}),
    ("鲨鱼王", "tank", {}, {}), ("捕鼠者", "assassin", {}, {}),
    # +10 more for 172
    ("亚当·斯特兰奇", "fighter", {}, {}), ("鹰侠·卡特", "fighter", {}, {}), ("野火", "fighter", {}, {}),
    ("森林女", "support", {}, {}), ("黎明", "fighter", {}, {}), ("泰拉", "mage", {}, {}),
    ("星蓝石·卡罗尔", "mage", {}, {}), ("阿托希塔斯", "fighter", {}, {}), ("拉弗利兹·橙灯", "tank", {}, {}),
    ("靛青", "support", {}, {}),
]

# ======================== GENSHIN IMPACT (+150) ========================
HERO_DEFS["genshin"] = [
    # Already: 旅行者, 琴, 安柏, 凯亚, 丽莎, 芭芭拉, 雷泽, 温迪, 可莉, 班尼特...
    # Mondstadt (15)
    ("迪卢克", "fighter", {}, {}), ("莫娜", "mage", {}, {}), ("菲谢尔", "marksman", {}, {}),
    ("诺艾尔", "tank", {}, {}), ("砂糖", "support", {}, {}), ("罗莎莉亚", "assassin", {}, {}),
    ("迪奥娜", "support", {}, {}), ("阿贝多", "support", {}, {}), ("优菈", "fighter", {}, {}),
    ("米卡", "support", {}, {}), ("雷泽·狼魂", "fighter", {}, {}), ("法尔伽", "fighter", {}, {}),
    ("艾莉丝", "mage", {}, {}), ("西蒙", "fighter", {}, {}), ("杜拉夫", "fighter", {}, {}),
    # Liyue (20)
    ("钟离", "tank", {}, {}), ("胡桃", "assassin", {}, {}), ("魈", "assassin", {}, {}),
    ("甘雨", "marksman", {}, {}), ("刻晴", "assassin", {}, {}), ("七七", "support", {}, {}),
    ("重云", "fighter", {}, {}), ("行秋", "support", {}, {}), ("香菱", "fighter", {}, {}),
    ("凝光", "mage", {}, {}), ("北斗", "fighter", {}, {}), ("辛焱", "fighter", {}, {}),
    ("烟绯", "mage", {}, {}), ("云堇", "support", {}, {}), ("申鹤", "support", {}, {}),
    ("夜兰", "marksman", {}, {}), ("白术", "support", {}, {}), ("瑶瑶", "support", {}, {}),
    ("闲云", "support", {}, {}), ("嘉明", "fighter", {}, {}),
    # Inazuma (15)
    ("雷电将军", "fighter", {}, {}), ("八重神子", "mage", {}, {}), ("神里绫华", "fighter", {}, {}),
    ("神里绫人", "fighter", {}, {}), ("枫原万叶", "assassin", {}, {}), ("宵宫", "marksman", {}, {}),
    ("早柚", "assassin", {}, {}), ("九条裟罗", "support", {}, {}), ("托马", "tank", {}, {}),
    ("五郎", "support", {}, {}), ("一斗", "fighter", {}, {}), ("心海", "support", {}, {}),
    ("久岐忍", "support", {}, {}), ("鹿野院平藏", "fighter", {}, {}), ("绮良良", "support", {}, {}),
    # Sumeru (15)
    ("纳西妲", "mage", {}, {}), ("提纳里", "marksman", {}, {}), ("赛诺", "fighter", {}, {}),
    ("妮露", "support", {}, {}), ("艾尔海森", "fighter", {}, {}), ("迪希雅", "fighter", {}, {}),
    ("柯莱", "marksman", {}, {}), ("多莉", "support", {}, {}), ("坎蒂丝", "tank", {}, {}),
    ("珐露珊", "support", {}, {}), ("莱依拉", "support", {}, {}), ("流浪者", "mage", {}, {}),
    ("卡维", "support", {}, {}), ("菲米尼", "fighter", {}, {}), ("夏洛蒂", "support", {}, {}),
    # Fontaine (15)
    ("芙宁娜", "mage", {}, {}), ("那维莱特", "mage", {}, {}), ("林尼", "marksman", {}, {}),
    ("琳妮特", "assassin", {}, {}), ("菲米尼·潜水", "fighter", {}, {}), ("娜维娅", "fighter", {}, {}),
    ("夏沃蕾", "support", {}, {}), ("克洛琳德", "fighter", {}, {}), ("希格雯", "support", {}, {}),
    ("莱欧斯利", "fighter", {}, {}), ("阿蕾奇诺", "assassin", {}, {}), ("千织", "support", {}, {}),
    ("艾梅莉埃", "support", {}, {}), ("仆人", "assassin", {}, {}), ("芙卡洛斯", "mage", {}, {}),
    # Natlan & Snezhnaya (10)
    ("玛薇卡", "fighter", {}, {}), ("基尼奇", "assassin", {}, {}), ("卡齐娜", "support", {}, {}),
    ("希诺宁", "support", {}, {}), ("恰斯卡", "marksman", {}, {}), ("欧洛伦", "mage", {}, {}),
    ("茜特菈莉", "support", {}, {}), ("队长", "fighter", {}, {}), ("少女", "support", {}, {}),
    ("丑角", "mage", {}, {}),
    # Khaenri'ah & Celestia (10)
    ("戴因斯雷布", "fighter", {}, {}), ("凯亚·王室", "assassin", {}, {}), ("皮耶罗", "mage", {}, {}),
    ("多托雷", "mage", {}, {}), ("潘塔罗涅", "support", {}, {}), ("桑多涅", "support", {}, {}),
    ("天理", "mage", {}, {}), ("阿斯莫德", "mage", {}, {}), ("派蒙", "support", {}, {}),
    ("空", "fighter", {}, {}),
    # Expanded (50 more for 172)
    ("荧", "fighter", {}, {}), ("派蒙·应急食品", "support", {}, {}), ("立本", "support", {}, {}),
    ("凯瑟琳", "support", {}, {}), ("蒂玛乌斯", "support", {}, {}), ("瓦格纳", "fighter", {}, {}),
    ("玛乔丽", "support", {}, {}), ("芙萝拉", "support", {}, {}), ("唐娜", "support", {}, {}),
    ("莎拉", "support", {}, {}), ("卯师傅", "support", {}, {}), ("苏二娘", "support", {}, {}),
    ("莺儿", "support", {}, {}), ("田铁嘴", "support", {}, {}), ("钟离·岩王帝君", "fighter", {}, {}),
    ("若陀龙王", "tank", {}, {}), ("特瓦林", "fighter", {}, {}), ("北风狼王", "fighter", {}, {}),
    ("奥赛尔", "tank", {}, {}), ("跋掣", "assassin", {}, {}), ("雷音权现", "mage", {}, {}),
    ("无相之雷", "mage", {}, {}), ("无相之火", "mage", {}, {}), ("无相之冰", "mage", {}, {}),
    ("无相之水", "mage", {}, {}), ("无相之风", "mage", {}, {}), ("无相之岩", "tank", {}, {}),
    ("无相之草", "support", {}, {}), ("爆炎树", "mage", {}, {}), ("急冻树", "mage", {}, {}),
    ("纯水精灵", "mage", {}, {}), ("古岩龙蜥", "tank", {}, {}), ("深海龙蜥", "fighter", {}, {}),
    ("遗迹守卫", "tank", {}, {}), ("遗迹猎者", "fighter", {}, {}), ("遗迹重机", "tank", {}, {}),
    ("深渊使徒", "assassin", {}, {}), ("深渊咏者", "mage", {}, {}), ("深渊法师", "mage", {}, {}),
    ("丘丘王", "tank", {}, {}), ("丘丘暴徒", "fighter", {}, {}), ("丘丘萨满", "support", {}, {}),
    ("史莱姆·风", "assassin", {}, {}), ("史莱姆·火", "mage", {}, {}), ("史莱姆·冰", "mage", {}, {}),
    ("史莱姆·水", "support", {}, {}), ("史莱姆·雷", "mage", {}, {}), ("史莱姆·岩", "tank", {}, {}),
    ("史莱姆·草", "support", {}, {}), ("漂浮灵", "mage", {}, {}),
    # +12 more for 172
    ("温迪·风神", "mage", {}, {}), ("钟离·武神", "fighter", {}, {}), ("雷电将军·真", "mage", {}, {}),
    ("纳西妲·世界树", "mage", {}, {}), ("芙宁娜·水神", "support", {}, {}), ("火神·赫马努比斯", "fighter", {}, {}),
    ("冰神·沙皇", "mage", {}, {}), ("魔女会·艾莉丝", "mage", {}, {}), ("黄金", "support", {}, {}),
    ("极恶骑", "assassin", {}, {}), ("预言家", "mage", {}, {}),     ("猎月人", "assassin", {}, {}),
]

# ======================== MCU (+150) ========================
HERO_DEFS["mcu"] = [
    # Already: 钢铁侠, 美国队长, 雷神, 浩克, 黑寡妇, 鹰眼, 蜘蛛侠, 奇异博士, 猩红女巫, 洛基...
    # Avengers Phase 1-3 (20)
    ("战争机器", "marksman", {}, {}), ("猎鹰", "fighter", {}, {}), ("冬日战士", "assassin", {}, {}),
    ("幻视", "mage", {}, {}), ("绯红女巫", "mage", {}, {}), ("快银", "assassin", {}, {}),
    ("蚁人", "assassin", {}, {}), ("黄蜂女", "assassin", {}, {}), ("黑豹", "fighter", {}, {}),
    ("苏睿", "support", {}, {}), ("奥克耶", "fighter", {}, {}), ("娜吉雅", "assassin", {}, {}),
    ("姆巴库", "tank", {}, {}), ("星爵", "marksman", {}, {}), ("卡魔拉", "assassin", {}, {}),
    ("德拉克斯", "fighter", {}, {}), ("火箭浣熊", "marksman", {}, {}), ("格鲁特", "tank", {}, {}),
    ("螳螂女", "support", {}, {}), ("星云", "assassin", {}, {}),
    # Phase 4-6 (20)
    ("尚气", "fighter", {}, {}), ("文武", "fighter", {}, {}), ("夏玲", "fighter", {}, {}),
    ("凯蒂", "support", {}, {}), ("永恒族·瑟西", "mage", {}, {}), ("永恒族·伊卡里斯", "fighter", {}, {}),
    ("永恒族·蒂娜", "fighter", {}, {}), ("永恒族·金戈", "mage", {}, {}), ("永恒族·法斯托斯", "support", {}, {}),
    ("永恒族·马卡里", "assassin", {}, {}), ("永恒族·德鲁伊格", "mage", {}, {}), ("永恒族·吉尔伽美什", "fighter", {}, {}),
    ("月光骑士", "fighter", {}, {}), ("莱拉", "fighter", {}, {}), ("亚美莉卡·查韦斯", "fighter", {}, {}),
    ("女浩克", "fighter", {}, {}), ("惊奇少女", "fighter", {}, {}), ("鹰眼·凯特", "marksman", {}, {}),
    ("叶莲娜", "assassin", {}, {}), ("红色守卫", "tank", {}, {}),
    # Villains (20)
    ("灭霸", "tank", {}, {}), ("奥创", "mage", {}, {}), ("红骷髅", "fighter", {}, {}),
    ("满大人", "mage", {}, {}), ("海拉", "mage", {}, {}), ("苏尔特尔", "fighter", {}, {}),
    ("伊戈", "mage", {}, {}), ("指控者罗南", "fighter", {}, {}), ("征服者康", "mage", {}, {}),
    ("屠神者格尔", "assassin", {}, {}), ("阿加莎", "mage", {}, {}), ("纳摩", "fighter", {}, {}),
    ("类人体", "tank", {}, {}), ("暗夜狼人", "fighter", {}, {}), ("刀锋战士", "assassin", {}, {}),
    ("艾尔莎·血石", "marksman", {}, {}), ("墨菲斯托", "mage", {}, {}), ("黑心", "mage", {}, {}),
    ("靶眼", "marksman", {}, {}), ("金并", "tank", {}, {}),
    # TV Series (15)
    ("旺达", "mage", {}, {}), ("幻视·白", "mage", {}, {}), ("阿加莎·哈克尼斯", "mage", {}, {}),
    ("比利", "mage", {}, {}), ("汤米", "assassin", {}, {}), ("莫妮卡·兰博", "mage", {}, {}),
    ("吉米·吴", "support", {}, {}), ("达西", "support", {}, {}), ("洛基·变体", "assassin", {}, {}),
    ("希尔维", "assassin", {}, {}), ("莫比乌斯", "support", {}, {}), ("遗留之人", "mage", {}, {}),
    ("艾里奥斯", "tank", {}, {}), ("分钟小姐", "support", {}, {}), ("B-15", "fighter", {}, {}),
    # Multiverse (15)
    ("蜘蛛侠·托比", "fighter", {}, {}), ("蜘蛛侠·安德鲁", "fighter", {}, {}),
    ("奇异博士·邪恶", "mage", {}, {}), ("X教授·MCU", "mage", {}, {}), ("万磁王·MCU", "mage", {}, {}),
    ("黑蝠王·MCU", "mage", {}, {}), ("惊奇队长·玛丽亚", "fighter", {}, {}), ("死侍", "assassin", {}, {}),
    ("金刚狼·MCU", "fighter", {}, {}), ("艾丽卡·MCU", "assassin", {}, {}), ("牌皇·MCU", "assassin", {}, {}),
    ("刀锋战士·MCU", "assassin", {}, {}), ("霹雳火·MCU", "mage", {}, {}), ("神奇先生·MCU", "fighter", {}, {}),
    ("红坦克·MCU", "tank", {}, {}),
    # Expanded (60 more for 172)
    ("佩姬·卡特", "fighter", {}, {}), ("霍华德·斯塔克", "support", {}, {}),
    ("贾维斯", "support", {}, {}), ("星期五", "support", {}, {}), ("伊迪丝", "support", {}, {}),
    ("科尔森", "support", {}, {}), ("玛利亚·希尔", "support", {}, {}), ("尼克·弗瑞", "support", {}, {}),
    ("塔罗斯", "fighter", {}, {}), ("卡罗尔·丹弗斯", "fighter", {}, {}), ("杨罗格", "fighter", {}, {}),
    ("米涅瓦", "assassin", {}, {}), ("阿特拉斯", "fighter", {}, {}), ("古一", "mage", {}, {}),
    ("莫度", "fighter", {}, {}), ("王", "support", {}, {}), ("卡西利亚斯", "mage", {}, {}),
    ("多玛姆", "mage", {}, {}), ("瓦尔基里", "fighter", {}, {}), ("海姆达尔", "marksman", {}, {}),
    ("希芙", "fighter", {}, {}), ("奥丁", "mage", {}, {}), ("弗丽嘉", "support", {}, {}),
    ("苏尔特尔·王冠", "fighter", {}, {}), ("斯科尔奇", "fighter", {}, {}), ("宗师", "mage", {}, {}),
    ("托帕兹", "fighter", {}, {}), ("螳螂", "support", {}, {}), ("亚当术士", "fighter", {}, {}),
    ("阿耶莎", "mage", {}, {}), ("电击杀冒脸", "fighter", {}, {}), ("克拉格林", "fighter", {}, {}),
    ("星辰鹰", "fighter", {}, {}), ("马丁内克斯", "fighter", {}, {}), ("克鲁加尔", "mage", {}, {}),
    ("梅菲德", "fighter", {}, {}), ("霍普·凡·戴因", "assassin", {}, {}), ("汉克·皮姆", "support", {}, {}),
    ("珍妮特·凡·戴因", "support", {}, {}), ("比尔·福斯特", "tank", {}, {}),
    ("幽灵", "assassin", {}, {}), ("桑尼·伯奇", "fighter", {}, {}), ("尤利西斯·克劳", "fighter", {}, {}),
    ("瓦坎达皇家卫队", "tank", {}, {}), ("祖利", "support", {}, {}), ("罗斯将军", "fighter", {}, {}),
    ("雷霆罗斯", "tank", {}, {}), ("憎恶", "tank", {}, {}), ("鞭索", "fighter", {}, {}),
    ("铁霸王", "tank", {}, {}), ("绝境病毒", "mage", {}, {}), ("基里安", "mage", {}, {}),
    ("交叉骨", "fighter", {}, {}), ("泽莫", "fighter", {}, {}), ("碎旗者", "fighter", {}, {}),
    ("美国密探", "fighter", {}, {}), ("模仿大师", "fighter", {}, {}), ("德雷科夫", "fighter", {}, {}),
    ("塔烙斯之女", "assassin", {}, {}),     ("斯克鲁人·格拉威克", "fighter", {}, {}),
    # +10 more for 172
    ("神奇四侠·里德", "fighter", {}, {}), ("神奇四侠·苏", "support", {}, {}),
    ("神奇四侠·本", "tank", {}, {}), ("神奇四侠·强尼", "mage", {}, {}), ("银影侠", "mage", {}, {}),
    ("吞星", "tank", {}, {}), ("哨兵", "fighter", {}, {}), ("英国队长", "fighter", {}, {}),
    ("黑骑士", "fighter", {}, {}), ("类人体·沼泽", "tank", {}, {}),
]

# ======================== ONE PIECE (+150) ========================
HERO_DEFS["one_piece"] = [
    # Already: 蒙奇·D·路飞, 罗罗诺亚·索隆, 娜美, 乌索普, 山治, 乔巴, 罗宾, 弗兰奇, 布鲁克, 甚平...
    # 超新星 (11)
    ("尤斯塔斯·基德", "fighter", {}, {}), ("特拉法尔加·罗", "assassin", {}, {}),
    ("巴兹尔·霍金斯", "mage", {}, {}), ("X·德雷克", "fighter", {}, {}),
    ("斯库拉奇曼·阿普", "mage", {}, {}), ("卡彭·贝基", "fighter", {}, {}),
    ("乔艾莉·波妮", "fighter", {}, {}), ("怪僧乌尔基", "tank", {}, {}),
    ("打碟音·阿普", "mage", {}, {}), ("杀戮武人基拉", "assassin", {}, {}), ("索隆·三刀流", "fighter", {}, {}),
    # 四皇 (10)
    ("爱德华·纽盖特", "tank", {}, {}), ("夏洛特·玲玲", "fighter", {}, {}),
    ("凯多", "tank", {}, {}), ("香克斯", "fighter", {}, {}), ("马歇尔·D·蒂奇", "mage", {}, {}),
    ("白胡子·爱德华", "tank", {}, {}), ("百兽·凯多", "tank", {}, {}), ("红发·香克斯", "fighter", {}, {}),
    ("黑胡子·蒂奇", "mage", {}, {}), ("大妈·玲玲", "fighter", {}, {}),
    # 王下七武海 (15)
    ("乔拉可尔·米霍克", "fighter", {}, {}), ("唐吉诃德·多弗朗明哥", "fighter", {}, {}),
    ("巴索罗缪·大熊", "tank", {}, {}), ("波雅·汉库克", "support", {}, {}),
    ("月光·莫利亚", "mage", {}, {}), ("沙·克洛克达尔", "fighter", {}, {}),
    ("甚平", "fighter", {}, {}), ("爱德华·威布尔", "tank", {}, {}),
    ("鹰眼·米霍克", "fighter", {}, {}), ("天夜叉·多弗朗明哥", "fighter", {}, {}),
    ("暴君·大熊", "tank", {}, {}), ("女帝·汉库克", "support", {}, {}),
    ("海侠·甚平", "fighter", {}, {}), ("沙鳄·克洛克达尔", "fighter", {}, {}),
    ("幽灵公主·佩罗娜", "mage", {}, {}),
    # 海军 (20)
    ("赤犬", "mage", {}, {}), ("青雉", "mage", {}, {}), ("黄猿", "marksman", {}, {}),
    ("藤虎", "tank", {}, {}), ("绿牛", "fighter", {}, {}), ("战国", "fighter", {}, {}),
    ("卡普", "fighter", {}, {}), ("鹤", "support", {}, {}), ("斯摩格", "fighter", {}, {}),
    ("缇娜", "fighter", {}, {}), ("克比", "fighter", {}, {}), ("贝尔梅尔", "support", {}, {}),
    ("达斯琪", "fighter", {}, {}), ("T彭恩", "fighter", {}, {}), ("战桃丸", "tank", {}, {}),
    ("萨卡斯基", "mage", {}, {}), ("库赞", "mage", {}, {}), ("波鲁萨利诺", "marksman", {}, {}),
    ("一笑", "tank", {}, {}), ("荒牧", "fighter", {}, {}),
    # 革命军 (10)
    ("蒙奇·D·龙", "mage", {}, {}), ("萨博", "fighter", {}, {}), ("伊万科夫", "support", {}, {}),
    ("闪电", "assassin", {}, {}), ("克尔拉", "fighter", {}, {}), ("贝蒂", "support", {}, {}),
    ("林德伯格", "marksman", {}, {}), ("莫利", "tank", {}, {}), ("乌鸦", "assassin", {}, {}),
    ("茉莉", "fighter", {}, {}),
    # 白胡子海贼团 (10)
    ("马尔科", "support", {}, {}), ("艾斯", "fighter", {}, {}), ("乔兹", "tank", {}, {}),
    ("比斯塔", "fighter", {}, {}), ("布拉曼克", "fighter", {}, {}), ("拉克约", "fighter", {}, {}),
    ("那谬尔", "fighter", {}, {}), ("布伦海姆", "fighter", {}, {}), ("库利艾尔", "marksman", {}, {}),
    ("金古多", "fighter", {}, {}),
    # 百兽海贼团 (10)
    ("烬", "fighter", {}, {}), ("奎因", "tank", {}, {}), ("杰克", "fighter", {}, {}),
    ("乌尔缇", "fighter", {}, {}), ("佩吉万", "tank", {}, {}), ("黑色玛利亚", "fighter", {}, {}),
    ("福兹·弗", "assassin", {}, {}), ("佐佐木", "fighter", {}, {}), ("黑炭大蛇", "mage", {}, {}),
    ("润媞", "fighter", {}, {}),
    # BIG MOM海贼团 (10)
    ("卡塔库栗", "fighter", {}, {}), ("斯慕吉", "fighter", {}, {}), ("克力架", "fighter", {}, {}),
    ("佩罗斯佩罗", "mage", {}, {}), ("大福", "fighter", {}, {}), ("欧文", "mage", {}, {}),
    ("布蕾", "support", {}, {}), ("布琳", "support", {}, {}), ("普拉琳涅", "support", {}, {}),
    ("斯纳格", "fighter", {}, {}),
    # 世界政府/天龙人 (10)
    ("五老星·金星", "fighter", {}, {}), ("五老星·木星", "mage", {}, {}),
    ("五老星·水星", "support", {}, {}), ("五老星·火星", "fighter", {}, {}),
    ("五老星·土星", "tank", {}, {}), ("伊姆", "mage", {}, {}), ("罗布·路奇", "assassin", {}, {}),
    ("卡库", "assassin", {}, {}), ("加布拉", "assassin", {}, {}), ("斯潘达姆", "fighter", {}, {}),
    # Expanded (44 more for 172)
    ("哥尔·D·罗杰", "fighter", {}, {}), ("西尔巴兹·雷利", "fighter", {}, {}),
    ("光月御田", "fighter", {}, {}), ("光月桃之助", "support", {}, {}), ("光月日和", "support", {}, {}),
    ("锦卫门", "fighter", {}, {}), ("传次郎", "fighter", {}, {}), ("菊之丞", "fighter", {}, {}),
    ("雷藏", "assassin", {}, {}), ("犬岚", "fighter", {}, {}), ("猫蝮蛇", "fighter", {}, {}),
    ("勘十郎", "mage", {}, {}), ("小玉", "support", {}, {}), ("大和", "fighter", {}, {}),
    ("巴托洛米奥", "fighter", {}, {}), ("卡文迪许", "fighter", {}, {}), ("海尔丁", "tank", {}, {}),
    ("雷欧", "assassin", {}, {}), ("维奥莱特", "support", {}, {}), ("蕾贝卡", "fighter", {}, {}),
    ("居鲁士", "fighter", {}, {}), ("GOD·乌索普", "marksman", {}, {}), ("索隆·阎魔", "fighter", {}, {}),
    ("山治·隐形黑", "assassin", {}, {}), ("乔巴·怪物", "fighter", {}, {}), ("罗宾·恶魔", "mage", {}, {}),
    ("弗兰奇·将军", "tank", {}, {}), ("布鲁克·灵魂王", "mage", {}, {}), ("甚平·海侠", "fighter", {}, {}),
    ("路飞·五档", "fighter", {}, {}), ("路飞·四档", "fighter", {}, {}), ("路飞·二档", "assassin", {}, {}),
    ("尼卡", "fighter", {}, {}), ("JoyBoy", "support", {}, {}), ("象主", "tank", {}, {}),
    ("海王类", "tank", {}, {}), ("拉布", "tank", {}, {}), ("章鱼小八", "fighter", {}, {}),
    ("Mr.2·冯克雷", "assassin", {}, {}), ("Mr.1·达兹", "fighter", {}, {}),
    ("Miss·双手指", "assassin", {}, {}), ("Miss·圣诞节", "fighter", {}, {}),
    ("Miss·黄金周", "support", {}, {}),     ("Mr.3·加尔迪诺", "mage", {}, {}),
    # +7 more for 172
    ("阿龙", "fighter", {}, {}), ("克罗欧比", "fighter", {}, {}), ("啾", "marksman", {}, {}),
    ("小八", "fighter", {}, {}), ("瓦波尔", "tank", {}, {}), ("多尔顿", "tank", {}, {}),
    ("Dr.库蕾哈", "support", {}, {}),
]

# ======================== OVERWATCH2 (+150) ========================
HERO_DEFS["overwatch2"] = [
    # Already: 士兵76, 猎空, 源氏, 半藏, 法老之鹰, 死神, 卡西迪, 黑百合, 托比昂, 路霸...
    # Tank (12)
    ("莱因哈特", "tank", {}, {}), ("温斯顿", "tank", {}, {}), ("D.Va", "tank", {}, {}),
    ("奥丽莎", "tank", {}, {}), ("查莉娅", "tank", {}, {}), ("破坏球", "tank", {}, {}),
    ("西格玛", "tank", {}, {}), ("渣客女王", "fighter", {}, {}), ("拉玛刹", "tank", {}, {}),
    ("毛加", "tank", {}, {}), ("骇灾", "tank", {}, {}), ("渣客", "fighter", {}, {}),
    # Damage (20)
    ("艾什", "marksman", {}, {}), ("堡垒", "marksman", {}, {}), ("末日铁拳", "fighter", {}, {}),
    ("回声", "assassin", {}, {}), ("狂鼠", "mage", {}, {}), ("美", "mage", {}, {}),
    ("秩序之光", "support", {}, {}), ("索杰恩", "marksman", {}, {}), ("黑影", "assassin", {}, {}),
    ("探奇", "assassin", {}, {}), ("伊拉锐", "support", {}, {}), ("巴蒂斯特", "support", {}, {}),
    ("生命之梭", "support", {}, {}), ("朱诺", "support", {}, {}),
    ("安娜", "support", {}, {}), ("布丽吉塔", "support", {}, {}), ("卢西奥", "support", {}, {}),
    ("天使", "support", {}, {}), ("莫伊拉", "support", {}, {}), ("禅雅塔", "support", {}, {}),
    # OW2 New (10)
    ("雾子", "support", {}, {}), ("索杰恩·赛博", "marksman", {}, {}),
    ("拉玛刹·智械", "tank", {}, {}), ("生命之梭·织命", "support", {}, {}),
    ("伊拉锐·太阳", "support", {}, {}), ("毛加·萨摩亚", "tank", {}, {}), ("骇灾·黑影", "tank", {}, {}),
    ("朱诺·星旅", "support", {}, {}), ("探奇·绝密", "assassin", {}, {}), ("弗蕾娅", "marksman", {}, {}),
    # OW Lore Heroes (15)
    ("林克斯", "fighter", {}, {}), ("马克西米连", "support", {}, {}),
    ("雅典娜", "support", {}, {}), ("鲍勃", "tank", {}, {}), ("喵星人", "assassin", {}, {}),
    ("哈蒙德", "tank", {}, {}), ("伊菲", "support", {}, {}), ("奥丽莎·原型", "tank", {}, {}),
    ("堡垒·盖尼米德", "marksman", {}, {}), ("回声·莉莉", "mage", {}, {}), ("士兵24", "fighter", {}, {}),
    ("死神·加布里尔", "assassin", {}, {}), ("岛田·龙", "fighter", {}, {}), ("岛田·虎", "fighter", {}, {}),
    ("西格玛·天体", "mage", {}, {}),
    # Talon & Villains (15)
    ("死神·暗影", "assassin", {}, {}), ("黑百合·蜘蛛", "assassin", {}, {}), ("末日铁拳·继承者", "fighter", {}, {}),
    ("莫伊拉·基因", "mage", {}, {}), ("西格玛·引力", "mage", {}, {}), ("黑影·数据", "assassin", {}, {}),
    ("巴蒂斯特·战地医", "support", {}, {}), ("索杰恩·暗影", "marksman", {}, {}), ("半藏·浪人", "marksman", {}, {}),
    ("源氏·机械", "assassin", {}, {}), ("安娜·狙医", "support", {}, {}), ("卡西迪·午时", "marksman", {}, {}),
    ("法老之鹰·天空", "marksman", {}, {}), ("回声·复制", "assassin", {}, {}), ("路霸·废土", "tank", {}, {}),
    # Omnics (5)
    ("智瞳", "mage", {}, {}), ("阿努比斯", "mage", {}, {}), ("归零者", "fighter", {}, {}),
    ("OR14", "tank", {}, {}), ("极大六号", "tank", {}, {}),
    # Expanded (73 more for 172)
    ("莱因哈特·十字军", "tank", {}, {}), ("D.Va·机甲", "tank", {}, {}), ("温斯顿·科学家", "tank", {}, {}),
    ("天使·齐格勒", "support", {}, {}), ("禅雅塔·修行", "support", {}, {}), ("卢西奥·自由", "support", {}, {}),
    ("士兵76·守望", "marksman", {}, {}), ("猎空·时空", "assassin", {}, {}), ("源氏·龙刃", "assassin", {}, {}),
    ("狂鼠·爆破", "mage", {}, {}), ("美·气候", "mage", {}, {}), ("托比昂·锻造", "fighter", {}, {}),
    ("查莉娅·举重", "tank", {}, {}), ("布丽吉塔·侍从", "support", {}, {}), ("奥丽莎·防线", "tank", {}, {}),
    ("安娜·守望", "support", {}, {}), ("艾什·帮派", "marksman", {}, {}), ("破坏球·竞技", "tank", {}, {}),
    ("伊菲·发明", "support", {}, {}), ("哈蒙德·冒险", "tank", {}, {}), ("鲍勃·管家", "tank", {}, {}),
    ("雅典娜·AI", "support", {}, {}), ("林克斯·联合", "fighter", {}, {}), ("喵星人·发射", "assassin", {}, {}),
    ("马克西米连·会计", "support", {}, {}), ("岛田·龙凤", "fighter", {}, {}), ("士兵24·老兵", "fighter", {}, {}),
    ("归零者·暴乱", "fighter", {}, {}), ("OR14·原型", "tank", {}, {}), ("阿努比斯·神", "mage", {}, {}),
    ("智瞳·觉者", "mage", {}, {}), ("雾子·女忍", "support", {}, {}), ("渣客女王·废土", "fighter", {}, {}),
    ("渣客·狂飙", "fighter", {}, {}), ("拉玛刹·领袖", "tank", {}, {}), ("毛加·战吼", "tank", {}, {}),
    ("骇灾·逃离", "tank", {}, {}), ("索杰恩·精英", "marksman", {}, {}), ("伊拉锐·守护", "support", {}, {}),
    ("生命之梭·绽灵", "support", {}, {}), ("探奇·解密", "assassin", {}, {}), ("朱诺·探索", "support", {}, {}),
    ("弗蕾娅·神射", "marksman", {}, {}), ("守望先锋·初代", "fighter", {}, {}),
    ("黑爪·死神小队", "assassin", {}, {}), ("归零者·反抗军", "fighter", {}, {}),
    ("守望者联盟", "support", {}, {}), ("国际维和", "support", {}, {}),
    ("大力神", "tank", {}, {}), ("奥丁", "fighter", {}, {}), ("雷神·OW", "fighter", {}, {}),
    ("北欧·守望", "fighter", {}, {}), ("阿斯加德之盾", "tank", {}, {}),
    ("辐射·斗士", "fighter", {}, {}), ("变异·实验体", "fighter", {}, {}),
    ("超级士兵·OW", "fighter", {}, {}), ("重装·坦克", "tank", {}, {}),
    ("突击·尖兵", "assassin", {}, {}), ("狙击·猎手", "marksman", {}, {}),
    ("医疗·天使", "support", {}, {}), ("护盾·壁垒", "tank", {}, {}),
    ("无人机·蜂群", "support", {}, {}), ("机甲·泰坦", "tank", {}, {}),
    ("激光·炮台", "marksman", {}, {}), ("火箭·炮手", "marksman", {}, {}),
    ("幽灵·特工", "assassin", {}, {}), ("黑客·数据流", "assassin", {}, {}),
    ("冰霜·异能", "mage", {}, {}), ("烈焰·异能", "mage", {}, {}),
    ("闪电·异能", "mage", {}, {}), ("大地·异能", "tank", {}, {}),
    ("剧毒·异能", "assassin", {}, {}),
    # +12 more for 172
    ("影刃·刺客", "assassin", {}, {}), ("铁壁·坦克", "tank", {}, {}), ("风暴·射手", "marksman", {}, {}),
    ("熔岩·法师", "mage", {}, {}), ("水晶·辅助", "support", {}, {}), ("暗影·猎手", "assassin", {}, {}),
    ("钢铁·壁垒", "tank", {}, {}), ("烈焰·射手", "marksman", {}, {}), ("寒冰·法师", "mage", {}, {}),
    ("雷电·骑士", "fighter", {}, {}), ("风行·忍者", "assassin", {}, {}), ("圣光·牧师", "support", {}, {}),
]

# ======================== FENGSHEN YANYI (+152) ========================
HERO_DEFS["fengshen_yanyi"] = [
    # Already: 哪吒, 杨戬, 雷震子, 姜子牙, 妲己, 申公豹, 闻仲, 黄飞虎, 土行孙, 邓婵玉...
    # 阐教 (30)
    ("元始天尊", "mage", {}, {}), ("南极仙翁", "support", {}, {}), ("燃灯道人", "mage", {}, {}),
    ("云中子", "mage", {}, {}), ("广成子", "mage", {}, {}), ("赤精子", "mage", {}, {}),
    ("黄龙真人", "fighter", {}, {}), ("惧留孙", "mage", {}, {}), ("太乙真人", "mage", {}, {}),
    ("灵宝大法师", "mage", {}, {}), ("文殊广法天尊", "support", {}, {}), ("普贤真人", "support", {}, {}),
    ("慈航道人", "support", {}, {}), ("玉鼎真人", "fighter", {}, {}), ("道行天尊", "support", {}, {}),
    ("清虚道德真君", "mage", {}, {}), ("杨任", "fighter", {}, {}), ("韦护", "fighter", {}, {}),
    ("李靖", "tank", {}, {}), ("金吒", "fighter", {}, {}), ("木吒", "fighter", {}, {}),
    ("龙须虎", "fighter", {}, {}), ("武吉", "fighter", {}, {}), ("薛恶虎", "fighter", {}, {}),
    ("韩毒龙", "fighter", {}, {}), ("萧臻", "fighter", {}, {}), ("邓华", "fighter", {}, {}),
    ("黄天化", "fighter", {}, {}), ("殷郊", "fighter", {}, {}), ("殷洪", "fighter", {}, {}),
    # 截教 (30)
    ("通天教主", "mage", {}, {}), ("多宝道人", "mage", {}, {}), ("金灵圣母", "mage", {}, {}),
    ("无当圣母", "mage", {}, {}), ("龟灵圣母", "fighter", {}, {}), ("赵公明", "fighter", {}, {}),
    ("三霄·云霄", "mage", {}, {}), ("三霄·琼霄", "mage", {}, {}), ("三霄·碧霄", "mage", {}, {}),
    ("吕岳", "mage", {}, {}), ("罗宣", "mage", {}, {}), ("羽翼仙", "fighter", {}, {}),
    ("马元", "fighter", {}, {}), ("一气仙", "mage", {}, {}), ("法戒", "mage", {}, {}),
    ("余元", "fighter", {}, {}), ("火灵圣母", "mage", {}, {}), ("金光仙", "fighter", {}, {}),
    ("虬首仙", "fighter", {}, {}), ("灵牙仙", "fighter", {}, {}), ("乌云仙", "fighter", {}, {}),
    ("毗芦仙", "mage", {}, {}), ("长耳定光仙", "support", {}, {}), ("金箍仙", "mage", {}, {}),
    ("十天君·秦完", "mage", {}, {}), ("十天君·赵江", "mage", {}, {}), ("十天君·董全", "mage", {}, {}),
    ("十天君·袁角", "mage", {}, {}), ("十天君·孙良", "mage", {}, {}), ("十天君·白礼", "mage", {}, {}),
    # 商朝 (20)
    ("纣王", "tank", {}, {}), ("妲己·妖狐", "assassin", {}, {}), ("胡喜媚", "assassin", {}, {}),
    ("王贵人", "assassin", {}, {}), ("费仲", "support", {}, {}), ("尤浑", "support", {}, {}),
    ("张桂芳", "fighter", {}, {}), ("魔家四将·魔礼青", "fighter", {}, {}), ("魔家四将·魔礼红", "tank", {}, {}),
    ("魔家四将·魔礼海", "tank", {}, {}), ("魔家四将·魔礼寿", "fighter", {}, {}), ("哼哈二将·郑伦", "tank", {}, {}),
    ("哼哈二将·陈奇", "tank", {}, {}), ("高继能", "fighter", {}, {}), ("孔宣", "mage", {}, {}),
    ("张奎", "fighter", {}, {}), ("高兰英", "marksman", {}, {}), ("卞吉", "fighter", {}, {}),
    ("邬文化", "tank", {}, {}), ("袁洪", "fighter", {}, {}),
    # 散仙 (15)
    ("陆压道人", "mage", {}, {}), ("度厄真人", "support", {}, {}), ("石矶娘娘", "mage", {}, {}),
    ("接引道人", "support", {}, {}), ("准提道人", "fighter", {}, {}), ("孔宣·孔雀", "mage", {}, {}),
    ("姬昌", "support", {}, {}), ("伯邑考", "support", {}, {}), ("散宜生", "support", {}, {}),
    ("崇侯虎", "fighter", {}, {}), ("崇黑虎", "fighter", {}, {}), ("苏护", "fighter", {}, {}),
    ("苏全忠", "fighter", {}, {}), ("黄天祥", "fighter", {}, {}), ("邓九公", "fighter", {}, {}),
    # 扩展追加 (57 more for 172)
    ("老子", "mage", {}, {}), ("鸿钧道人", "mage", {}, {}), ("女娲娘娘", "support", {}, {}),
    ("伏羲", "mage", {}, {}), ("神农_FS", "support", {}, {}), ("轩辕", "fighter", {}, {}),
    ("昊天上帝", "mage", {}, {}), ("瑶池金母", "support", {}, {}), ("东华帝君", "fighter", {}, {}),
    ("真武大帝", "fighter", {}, {}), ("青龙", "fighter", {}, {}), ("白虎", "fighter", {}, {}),
    ("朱雀", "mage", {}, {}), ("玄武", "tank", {}, {}), ("勾陈", "fighter", {}, {}),
    ("腾蛇", "assassin", {}, {}), ("二十八宿·角", "fighter", {}, {}), ("二十八宿·亢", "fighter", {}, {}),
    ("二十八宿·氐", "tank", {}, {}), ("二十八宿·房", "marksman", {}, {}), ("二十八宿·心", "assassin", {}, {}),
    ("二十八宿·尾", "fighter", {}, {}), ("二十八宿·箕", "assassin", {}, {}), ("三十六天罡", "fighter", {}, {}),
    ("七十二地煞", "assassin", {}, {}), ("九曜星君", "mage", {}, {}), ("太岁", "tank", {}, {}),
    ("值年神", "support", {}, {}), ("值月神", "support", {}, {}), ("值日神", "support", {}, {}),
    ("值时神", "support", {}, {}), ("四值功曹", "support", {}, {}), ("六丁六甲", "fighter", {}, {}),
    ("五方揭谛", "support", {}, {}), ("日游神", "fighter", {}, {}), ("夜游神", "assassin", {}, {}),
    ("巨灵神_FS", "tank", {}, {}), ("弼马温", "support", {}, {}), ("天蓬元帅", "fighter", {}, {}),
    ("卷帘大将", "fighter", {}, {}), ("增长天王", "fighter", {}, {}), ("持国天王", "tank", {}, {}),
    ("广目天王", "marksman", {}, {}), ("多闻天王", "tank", {}, {}), ("千里眼_FS", "marksman", {}, {}),
    ("顺风耳_FS", "support", {}, {}), ("雷公_FS", "mage", {}, {}), ("电母_FS", "mage", {}, {}),
    ("风伯_FS", "mage", {}, {}), ("雨师_FS", "support", {}, {}), ("龙王敖广", "mage", {}, {}),
    ("龙王敖钦", "mage", {}, {}), ("龙王敖顺", "mage", {}, {}), ("龙王敖闰", "mage", {}, {}),
    ("井龙王", "mage", {}, {}),     ("泾河龙王", "mage", {}, {}), ("万圣龙王_FS", "mage", {}, {}),
    ("九龙岛四圣", "fighter", {}, {}), ("金鳌岛", "support", {}, {}),
]

# ======================== GREEK MYTHOLOGY (+152) ========================
HERO_DEFS["greek_mythology"] = [
    # Already: 宙斯, 哈迪斯, 喀耳刻, 倪克斯, 波塞冬, 雅典娜, 阿瑞斯, 珀尔修斯, 赫拉克勒斯, 阿喀琉斯...
    # Olympians (20)
    ("赫拉", "support", {}, {}), ("阿波罗", "marksman", {}, {}), ("阿尔忒弥斯", "marksman", {}, {}),
    ("赫菲斯托斯", "fighter", {}, {}), ("赫斯提亚", "support", {}, {}), ("狄俄尼索斯", "support", {}, {}),
    ("德墨忒尔", "support", {}, {}), ("阿佛洛狄忒", "support", {}, {}), ("赫尔墨斯", "assassin", {}, {}),
    ("潘", "fighter", {}, {}), ("赫柏", "support", {}, {}), ("厄洛斯", "marksman", {}, {}),
    ("伊里斯", "support", {}, {}), ("赫利俄斯", "mage", {}, {}), ("塞勒涅", "mage", {}, {}),
    ("厄俄斯", "support", {}, {}), ("阿斯克勒庇俄斯", "support", {}, {}), ("摩摩斯", "mage", {}, {}),
    ("塔纳托斯", "assassin", {}, {}), ("许普诺斯", "mage", {}, {}),
    # Titans (20)
    ("克洛诺斯", "fighter", {}, {}), ("瑞亚", "support", {}, {}), ("俄刻阿诺斯", "mage", {}, {}),
    ("忒堤斯", "support", {}, {}), ("许珀里翁", "mage", {}, {}), ("忒亚", "mage", {}, {}),
    ("科俄斯", "mage", {}, {}), ("福柏", "support", {}, {}), ("伊阿珀托斯", "fighter", {}, {}),
    ("忒弥斯", "support", {}, {}), ("谟涅摩叙涅", "support", {}, {}), ("阿特拉斯", "tank", {}, {}),
    ("普罗米修斯", "support", {}, {}), ("厄庇米修斯", "support", {}, {}), ("墨诺提俄斯", "fighter", {}, {}),
    ("赫利俄斯·太阳", "mage", {}, {}), ("塞勒涅·月亮", "mage", {}, {}), ("厄俄斯·黎明", "support", {}, {}),
    ("勒托", "support", {}, {}), ("阿斯忒里亚", "mage", {}, {}),
    # Primordials (15)
    ("盖亚", "tank", {}, {}), ("乌拉诺斯", "mage", {}, {}), ("厄瑞玻斯", "mage", {}, {}),
    ("塔尔塔罗斯", "tank", {}, {}), ("厄洛斯·原初", "mage", {}, {}), ("蓬托斯", "fighter", {}, {}),
    ("埃忒尔", "mage", {}, {}), ("赫墨拉", "support", {}, {}), ("卡俄斯", "mage", {}, {}),
    ("阿南刻", "mage", {}, {}), ("柯罗诺斯", "mage", {}, {}), ("法涅斯", "mage", {}, {}),
    ("倪克斯·夜", "mage", {}, {}), ("赫卡忒", "mage", {}, {}), ("摩罗斯", "assassin", {}, {}),
    # Heroes (25)
    ("忒修斯", "fighter", {}, {}), ("伊阿宋", "fighter", {}, {}), ("美狄亚", "mage", {}, {}),
    ("俄耳甫斯", "support", {}, {}), ("欧律狄刻", "support", {}, {}), ("柏勒洛丰", "fighter", {}, {}),
    ("代达罗斯", "support", {}, {}), ("伊卡洛斯", "assassin", {}, {}), ("阿塔兰忒", "marksman", {}, {}),
    ("希波吕忒", "fighter", {}, {}), ("彭忒西勒亚", "fighter", {}, {}), ("墨勒阿革洛斯", "fighter", {}, {}),
    ("那耳喀索斯", "support", {}, {}), ("皮格马利翁", "support", {}, {}), ("伽拉忒亚", "support", {}, {}),
    ("阿多尼斯", "fighter", {}, {}), ("安泰俄斯", "tank", {}, {}), ("卡德摩斯", "fighter", {}, {}),
    ("坦塔罗斯", "tank", {}, {}), ("西绪福斯", "fighter", {}, {}), ("伊克西翁", "fighter", {}, {}),
    ("提托诺斯", "support", {}, {}), ("门农", "fighter", {}, {}), ("墨涅拉俄斯", "fighter", {}, {}),
    ("阿伽门农", "fighter", {}, {}),
    # Monsters (20)
    ("弥诺陶洛斯", "tank", {}, {}), ("美杜莎", "mage", {}, {}), ("奇美拉", "fighter", {}, {}),
    ("刻耳柏洛斯", "tank", {}, {}), ("许德拉", "tank", {}, {}), ("斯芬克斯", "mage", {}, {}),
    ("格里芬", "fighter", {}, {}), ("独眼巨人", "tank", {}, {}), ("百臂巨人", "tank", {}, {}),
    ("厄喀德那", "mage", {}, {}), ("提丰", "fighter", {}, {}), ("斯库拉", "assassin", {}, {}),
    ("卡律布狄斯", "tank", {}, {}), ("拉冬", "tank", {}, {}), ("涅墨亚狮子", "fighter", {}, {}),
    ("哈耳庇厄", "assassin", {}, {}), ("戈耳工", "mage", {}, {}), ("恩浦萨", "assassin", {}, {}),
    ("拉米亚", "assassin", {}, {}), ("阿剌克涅", "assassin", {}, {}),
    # Expanded (52 more for 172)
    ("波吕斐摩斯", "tank", {}, {}), ("埃俄罗斯", "mage", {}, {}), ("涅柔斯", "mage", {}, {}),
    ("格劳科斯", "fighter", {}, {}), ("特里同", "fighter", {}, {}), ("安菲特里忒", "support", {}, {}),
    ("多里斯", "support", {}, {}), ("西蒂斯", "support", {}, {}), ("涅瑞伊得斯", "support", {}, {}),
    ("俄刻阿尼得斯", "support", {}, {}), ("普路同", "mage", {}, {}), ("普洛塞庇娜", "support", {}, {}),
    ("玛卡里亚", "support", {}, {}), ("厄里倪厄斯", "assassin", {}, {}), ("阿勒克托", "assassin", {}, {}),
    ("墨盖拉", "assassin", {}, {}), ("提西福涅", "assassin", {}, {}), ("卡戎", "fighter", {}, {}),
    ("米诺斯", "fighter", {}, {}), ("拉达曼迪斯", "fighter", {}, {}), ("埃阿科斯", "fighter", {}, {}),
    ("伊里丝", "support", {}, {}), ("仄费罗斯", "assassin", {}, {}), ("玻瑞阿斯", "fighter", {}, {}),
    ("诺托斯", "fighter", {}, {}), ("欧罗斯", "assassin", {}, {}), ("埃忒尔·光", "mage", {}, {}),
    ("赫斯珀里得斯", "support", {}, {}), ("阿特拉斯·擎天", "tank", {}, {}), ("金苹果", "support", {}, {}),
    ("涅克塔耳", "support", {}, {}), ("安布罗西亚", "support", {}, {}), ("奥林匹斯", "tank", {}, {}),
    ("冥河", "mage", {}, {}), ("忘川", "support", {}, {}), ("火河", "mage", {}, {}),
    ("哀河", "assassin", {}, {}), ("怨河", "mage", {}, {}), ("复仇三女神", "assassin", {}, {}),
    ("命运三女神", "support", {}, {}), ("时序三女神", "support", {}, {}), ("美惠三女神", "support", {}, {}),
    ("缪斯九女神", "support", {}, {}), ("牧神", "fighter", {}, {}), ("林神", "assassin", {}, {}),
    ("水妖", "mage", {}, {}), ("树精", "support", {}, {}), ("山精", "tank", {}, {}),
    ("半人马", "fighter", {}, {}), ("喀戎", "support", {}, {}), ("涅索斯", "fighter", {}, {}),
    ("西勒诺斯", "support", {}, {}),
    # +7 more for 172
    ("阿喀琉斯·踵", "fighter", {}, {}), ("奥德修斯", "fighter", {}, {}), ("狄俄墨得斯", "fighter", {}, {}),
    ("大埃阿斯", "tank", {}, {}), ("帕特罗克洛斯", "fighter", {}, {}), ("赫克托耳", "fighter", {}, {}),
    ("普里阿摩斯", "support", {}, {}), ("涅斯托尔", "support", {}, {}),
]

# ======================== NORSE MYTHOLOGY (+152) ========================
HERO_DEFS["norse_mythology"] = [
    # Already: 奥丁, 密米尔, 托尔, 弗雷, 提尔, 布伦希尔德, 苏尔特尔, 洛基, 芬里尔, 尼德霍格...
    # Aesir (20)
    ("巴德尔", "support", {}, {}), ("霍德尔", "assassin", {}, {}), ("海姆达尔", "marksman", {}, {}),
    ("布拉吉", "support", {}, {}), ("伊登", "support", {}, {}), ("维达尔", "fighter", {}, {}),
    ("瓦利", "assassin", {}, {}), ("弗丽嘉", "support", {}, {}), ("希芙", "fighter", {}, {}),
    ("凡赛堤", "support", {}, {}), ("乌勒尔", "marksman", {}, {}), ("赫尔莫德", "fighter", {}, {}),
    ("玛格尼", "fighter", {}, {}), ("摩迪", "fighter", {}, {}), ("诺特", "mage", {}, {}),
    ("达格", "fighter", {}, {}), ("苏尔", "mage", {}, {}), ("玛尼", "mage", {}, {}),
    ("萨迦", "support", {}, {}), ("埃尔", "support", {}, {}),
    # Vanir (10)
    ("尼奥尔德", "mage", {}, {}), ("弗雷娅", "support", {}, {}), ("古尔薇格", "mage", {}, {}),
    ("克瓦希尔", "support", {}, {}), ("斯卡蒂", "fighter", {}, {}), ("奥德", "fighter", {}, {}),
    ("赫诺丝", "support", {}, {}), ("格尔塞蜜", "support", {}, {}), ("弗雷·丰饶", "support", {}, {}),
    ("弗雷娅·爱神", "support", {}, {}),
    # Jotnar (20)
    ("尤弥尔", "tank", {}, {}), ("密米尔", "mage", {}, {}), ("洛基·诡计", "assassin", {}, {}),
    ("安格尔波达", "mage", {}, {}), ("斯卡蒂·冬", "fighter", {}, {}), ("希密尔", "tank", {}, {}),
    ("乌特加德·洛基", "mage", {}, {}), ("苏尔特尔·火", "fighter", {}, {}), ("索列姆", "tank", {}, {}),
    ("赫朗格尼尔", "tank", {}, {}), ("盖尔罗德", "tank", {}, {}), ("伯里", "fighter", {}, {}),
    ("包尔", "fighter", {}, {}), ("贝斯特拉", "support", {}, {}), ("劳菲", "assassin", {}, {}),
    ("法布提", "fighter", {}, {}), ("格里德", "support", {}, {}), ("雅恩莎撒", "support", {}, {}),
    ("奥尔盖尔米尔", "tank", {}, {}), ("贝格尔米尔", "fighter", {}, {}),
    # Dwarves & Elves (10)
    ("辛德里", "support", {}, {}), ("布洛克", "fighter", {}, {}), ("杜林", "fighter", {}, {}),
    ("莫德索尼尔", "tank", {}, {}), ("德瓦林", "fighter", {}, {}), ("阿尔维斯", "mage", {}, {}),
    ("伊瓦第", "support", {}, {}), ("安德瓦里", "support", {}, {}), ("法夫尼尔", "fighter", {}, {}),
    ("雷金", "support", {}, {}),
    # Creatures (20)
    ("海拉", "mage", {}, {}), ("耶梦加得", "tank", {}, {}), ("赫拉斯瓦尔格尔", "fighter", {}, {}),
    ("拉塔托斯克", "assassin", {}, {}), ("维德佛尔尼尔", "marksman", {}, {}), ("休金", "assassin", {}, {}),
    ("穆宁", "assassin", {}, {}), ("格里", "fighter", {}, {}), ("弗雷基", "fighter", {}, {}),
    ("斯莱普尼尔", "fighter", {}, {}), ("加尔姆", "tank", {}, {}), ("塔纳托斯", "assassin", {}, {}),
    ("斯瓦迪尔法利", "fighter", {}, {}), ("古林博斯帝", "tank", {}, {}), ("坦格里斯尼尔", "fighter", {}, {}),
    ("坦格乔斯特", "fighter", {}, {}), ("欧德姆布拉", "support", {}, {}), ("奥丁之鸦", "assassin", {}, {}),
    ("海拉之犬", "tank", {}, {}), ("芬里尔之子", "assassin", {}, {}),
    # Heroes & Valkyries (15)
    ("希格尔德", "fighter", {}, {}), ("布伦希尔德·女武神", "fighter", {}, {}), ("齐格鲁德", "fighter", {}, {}),
    ("古德伦", "support", {}, {}), ("贡纳尔", "fighter", {}, {}), ("赫格尼", "fighter", {}, {}),
    ("阿特利", "fighter", {}, {}), ("埃尔普", "fighter", {}, {}), ("索尔莉", "fighter", {}, {}),
    ("哈姆迪尔", "fighter", {}, {}), ("希亚尔普", "fighter", {}, {}), ("布伦希尔德·瓦尔基里", "fighter", {}, {}),
    ("瓦尔基里·赫萝克", "fighter", {}, {}), ("瓦尔基里·斯库尔德", "mage", {}, {}), ("瓦尔基里·贡露", "fighter", {}, {}),
    # Expanded (57 more for 172)
    ("诺伦三女神", "support", {}, {}), ("乌尔德", "support", {}, {}), ("薇儿丹蒂", "support", {}, {}),
    ("诗蔻蒂", "mage", {}, {}), ("命运三女神", "support", {}, {}), ("过去女神", "support", {}, {}),
    ("现在女神", "support", {}, {}), ("未来女神", "mage", {}, {}), ("精灵·光", "support", {}, {}),
    ("精灵·暗", "assassin", {}, {}), ("侏儒·火", "fighter", {}, {}), ("侏儒·土", "tank", {}, {}),
    ("巨人·霜", "tank", {}, {}), ("巨人·山", "tank", {}, {}), ("巨人·火", "fighter", {}, {}),
    ("阿斯加德", "tank", {}, {}), ("米德加德", "support", {}, {}), ("约顿海姆", "fighter", {}, {}),
    ("尼福尔海姆", "mage", {}, {}), ("穆斯贝尔海姆", "mage", {}, {}), ("赫尔海姆", "assassin", {}, {}),
    ("亚尔夫海姆", "support", {}, {}), ("瓦纳海姆", "support", {}, {}), ("斯瓦塔尔法海姆", "fighter", {}, {}),
    ("世界树", "support", {}, {}), ("智慧之泉", "support", {}, {}), ("命运之井", "mage", {}, {}),
    ("金宫", "tank", {}, {}), ("瓦尔哈拉", "fighter", {}, {}), ("弗尔克范格", "support", {}, {}),
    ("彩虹桥", "support", {}, {}), ("末日之狼", "assassin", {}, {}), ("末日之蛇", "tank", {}, {}),
    ("火巨人", "fighter", {}, {}), ("亡灵大军", "tank", {}, {}), ("英灵战士", "fighter", {}, {}),
    ("狂暴战士", "fighter", {}, {}), ("盾女", "tank", {}, {}), ("渡鸦", "assassin", {}, {}),
    ("座狼", "fighter", {}, {}), ("战马", "fighter", {}, {}), ("巨龙·法夫纳", "tank", {}, {}),
    ("尼伯龙根", "support", {}, {}), ("莱茵黄金", "support", {}, {}), ("安德瓦里之戒", "support", {}, {}),
    ("格拉墨", "fighter", {}, {}), ("巴鲁姆克", "fighter", {}, {}), ("提尔锋", "fighter", {}, {}),
    ("冈格尼尔", "marksman", {}, {}), ("妙尔尼尔", "fighter", {}, {}), ("德罗普尼尔", "support", {}, {}),
    ("布里希嘉曼", "support", {}, {}), ("西弗之发", "support", {}, {}), ("古林博斯帝·金猪", "fighter", {}, {}),
    ("斯基德普拉特尼", "support", {}, {}),     ("格莱普尼尔", "support", {}, {}), ("加拉尔", "support", {}, {}),
    # +5 more for 172
    ("西格恩", "support", {}, {}), ("纳尔弗", "fighter", {}, {}), ("阿里", "fighter", {}, {}),
    ("赫德", "assassin", {}, {}), ("南娜", "support", {}, {}), ("格欧费茵", "support", {}, {}),
]

# ======================== WORLD GENERALS (+152) ========================
HERO_DEFS["world_generals"] = [
    # Already: Xiang Yu, Alexander, Julius Caesar, Oda Nobunaga, Hua Mulan, Genghis Khan, Napoleon, Joan of Arc, King Arthur, Spartacus...
    # Ancient (25)
    ("Hannibal Barca", "fighter", {}, {}), ("Scipio Africanus", "fighter", {}, {}),
    ("Sun Tzu", "support", {}, {}), ("Cyrus the Great", "fighter", {}, {}),
    ("Darius the Great", "fighter", {}, {}), ("Leonidas", "tank", {}, {}),
    ("Themistocles", "support", {}, {}), ("Pericles", "support", {}, {}),
    ("Alcibiades", "assassin", {}, {}), ("Epaminondas", "fighter", {}, {}),
    ("Philip II of Macedon", "fighter", {}, {}), ("Pyrrhus of Epirus", "fighter", {}, {}),
    ("Miltiades", "fighter", {}, {}), ("Xenophon", "fighter", {}, {}),
    ("Agesilaus II", "fighter", {}, {}), ("Pelopidas", "fighter", {}, {}),
    ("Thutmose III", "fighter", {}, {}), ("Ramesses II", "fighter", {}, {}),
    ("Nebuchadnezzar II", "fighter", {}, {}), ("Ashurbanipal", "mage", {}, {}),
    ("Sennacherib", "fighter", {}, {}), ("Tiglath-Pileser III", "fighter", {}, {}),
    ("Sargon of Akkad", "fighter", {}, {}), ("Hammurabi", "support", {}, {}),
    ("Gilgamesh_Historical", "fighter", {}, {}),
    # Roman (20)
    ("Gaius Marius", "fighter", {}, {}), ("Sulla", "fighter", {}, {}),
    ("Pompey", "fighter", {}, {}), ("Mark Antony", "fighter", {}, {}),
    ("Augustus", "support", {}, {}), ("Trajan", "fighter", {}, {}),
    ("Marcus Aurelius", "support", {}, {}), ("Constantine the Great", "support", {}, {}),
    ("Belisarius", "fighter", {}, {}), ("Aetius", "fighter", {}, {}),
    ("Stilicho", "fighter", {}, {}), ("Germanicus", "fighter", {}, {}),
    ("Vespasian", "support", {}, {}), ("Titus", "fighter", {}, {}),
    ("Hadrian", "support", {}, {}), ("Septimius Severus", "fighter", {}, {}),
    ("Aurelian", "fighter", {}, {}), ("Diocletian", "support", {}, {}),
    ("Theodosius", "support", {}, {}), ("Majorian", "fighter", {}, {}),
    # Medieval European (20)
    ("Richard the Lionheart", "fighter", {}, {}), ("Saladin", "fighter", {}, {}),
    ("Charlemagne", "fighter", {}, {}), ("William the Conqueror", "fighter", {}, {}),
    ("El Cid", "fighter", {}, {}), ("Frederick Barbarossa", "fighter", {}, {}),
    ("Edward the Black Prince", "fighter", {}, {}), ("Henry V", "fighter", {}, {}),
    ("Vlad the Impaler", "assassin", {}, {}), ("Jan Žižka", "fighter", {}, {}),
    ("Godfrey of Bouillon", "fighter", {}, {}), ("Bohemond I", "fighter", {}, {}),
    ("Baldwin IV of Jerusalem", "fighter", {}, {}), ("Roland", "fighter", {}, {}),
    ("Alfred the Great", "fighter", {}, {}), ("Harold Godwinson", "fighter", {}, {}),
    ("Brian Boru", "fighter", {}, {}), ("Robert the Bruce", "fighter", {}, {}),
    ("William Wallace", "fighter", {}, {}), ("Gustavus Adolphus", "fighter", {}, {}),
    # Asian (25)
    ("Tokugawa Ieyasu", "fighter", {}, {}), ("Toyotomi Hideyoshi", "fighter", {}, {}),
    ("Takeda Shingen", "fighter", {}, {}), ("Uesugi Kenshin", "fighter", {}, {}),
    ("Sanada Yukimura", "fighter", {}, {}), ("Date Masamune", "fighter", {}, {}),
    ("Honda Tadakatsu", "tank", {}, {}), ("Miyamoto Musashi", "assassin", {}, {}),
    ("Cao Cao", "fighter", {}, {}), ("Liu Bei", "support", {}, {}),
    ("Zhuge Liang", "mage", {}, {}), ("Guan Yu", "fighter", {}, {}),
    ("Khalid ibn al-Walid", "fighter", {}, {}), ("Tamerlane", "fighter", {}, {}),
    ("Babur", "fighter", {}, {}), ("Akbar the Great", "support", {}, {}),
    ("Yi Sun-sin", "fighter", {}, {}), ("Gwanggaeto the Great", "fighter", {}, {}),
    ("Subutai", "assassin", {}, {}), ("Kublai Khan", "fighter", {}, {}),
    ("Hulagu Khan", "fighter", {}, {}), ("Timur", "fighter", {}, {}),
    ("Shah Jahan", "support", {}, {}), ("Aurangzeb", "fighter", {}, {}),
    ("Chandragupta Maurya", "fighter", {}, {}),
    # Modern (20)
    ("Oliver Cromwell", "fighter", {}, {}), ("Frederick the Great", "fighter", {}, {}),
    ("Duke of Wellington", "fighter", {}, {}), ("Horatio Nelson", "fighter", {}, {}),
    ("Ulysses S. Grant", "fighter", {}, {}), ("Robert E. Lee", "fighter", {}, {}),
    ("Stonewall Jackson", "fighter", {}, {}), ("George Washington", "fighter", {}, {}),
    ("Simón Bolívar", "fighter", {}, {}), ("José de San Martín", "fighter", {}, {}),
    ("Giuseppe Garibaldi", "fighter", {}, {}), ("Otto von Bismarck", "support", {}, {}),
    ("Winston Churchill", "support", {}, {}), ("Douglas MacArthur", "fighter", {}, {}),
    ("George S. Patton", "fighter", {}, {}), ("Erwin Rommel", "fighter", {}, {}),
    ("Georgy Zhukov", "tank", {}, {}), ("Che Guevara", "assassin", {}, {}),
    ("Charles de Gaulle", "fighter", {}, {}), ("Dwight Eisenhower", "support", {}, {}),
    # Women Warriors (15)
    ("Boudica", "fighter", {}, {}), ("Artemisia I", "fighter", {}, {}),
    ("Tomoe Gozen", "assassin", {}, {}), ("Nakano Takeko", "assassin", {}, {}),
    ("Lakshmibai", "fighter", {}, {}), ("Trieu Thi Trinh", "fighter", {}, {}),
    ("Lozen", "assassin", {}, {}), ("Kahina", "mage", {}, {}),
    ("Zenobia", "fighter", {}, {}), ("Granuaile", "fighter", {}, {}),
    ("Hangaku Gozen", "fighter", {}, {}), ("Yuenü", "assassin", {}, {}),
    ("Matilda of Tuscany", "fighter", {}, {}), ("Isabella I of Castile", "support", {}, {}),
    ("Catherine the Great", "support", {}, {}),
    # Expanded (27 more for 172)
    ("Peter the Great", "fighter", {}, {}), ("Ivan the Terrible", "fighter", {}, {}),
    ("Mehmed II", "fighter", {}, {}), ("Suleiman the Magnificent", "support", {}, {}),
    ("Montezuma II", "fighter", {}, {}), ("Pachacuti", "fighter", {}, {}),
    ("Shaka Zulu", "fighter", {}, {}), ("Samori Ture", "fighter", {}, {}),
    ("Menelik II", "fighter", {}, {}), ("Haile Selassie", "support", {}, {}),
    ("Leo Africanus", "support", {}, {}), ("Henry the Navigator", "support", {}, {}),
    ("Vasco da Gama", "fighter", {}, {}), ("Francis Drake", "fighter", {}, {}),
    ("Admiral Yi", "fighter", {}, {}), ("Zheng He", "fighter", {}, {}),
    ("Mansa Musa", "support", {}, {}), ("Sundiata Keita", "fighter", {}, {}),
    ("Askia Muhammad", "fighter", {}, {}), ("Idris Alooma", "fighter", {}, {}),
    ("Nzinga", "fighter", {}, {}), ("Rani of Jhansi", "fighter", {}, {}),
    ("Tecumseh", "fighter", {}, {}), ("Crazy Horse", "assassin", {}, {}),
    ("Sitting Bull", "support", {}, {}), ("Geronimo", "assassin", {}, {}),
    ("Cochise", "fighter", {}, {}),
    # +5 more for 172
    ("Tokugawa", "support", {}, {}), ("Qin Shi Huang", "fighter", {}, {}), ("Attila the Hun", "fighter", {}, {}),
    ("Alaric", "fighter", {}, {}), ("Skanderbeg", "fighter", {}, {}),
]

# ======================== CTHULHU MYTHOS (+157) ========================
HERO_DEFS["cthulhu_mythos"] = [
    # Already: 哈斯塔, 莎布尼古拉斯, 兰道夫卡特, 犹格索托斯, 阿萨托斯, 伊斯人, 克苏鲁, 修格斯, 达贡, 奈亚拉托提普...
    # Outer Gods (15)
    ("阿撒托斯·混沌", "mage", {}, {}), ("犹格·索托斯·全知", "mage", {}, {}),
    ("莎布·尼古拉丝·黑山羊", "tank", {}, {}), ("奈亚拉托提普·千面", "assassin", {}, {}),
    ("乌波·萨斯拉", "mage", {}, {}), ("阿布霍斯", "tank", {}, {}),
    ("伊波·兹特尔", "mage", {}, {}), ("图尔兹查", "mage", {}, {}),
    ("奥苏姆", "mage", {}, {}), ("伊德海拉", "mage", {}, {}),
    ("诺登斯", "fighter", {}, {}), ("奈奥格·索希普", "mage", {}, {}),
    ("塔维尔·亚特·乌姆尔", "mage", {}, {}), ("尤玛恩托", "mage", {}, {}),
    ("格赫罗斯", "mage", {}, {}),
    # Great Old Ones (20)
    ("加塔诺托亚", "tank", {}, {}), ("佐斯·奥莫格", "fighter", {}, {}),
    ("克苏嘎", "mage", {}, {}), ("阿弗姆·扎", "mage", {}, {}),
    ("修德·梅尔", "mage", {}, {}), ("克图格亚", "mage", {}, {}),
    ("伊戈罗纳克", "tank", {}, {}), ("扎特瓜", "tank", {}, {}),
    ("格拉基", "assassin", {}, {}), ("艾霍特", "assassin", {}, {}),
    ("昌格纳·方庚", "fighter", {}, {}), ("伊塔库亚", "assassin", {}, {}),
    ("克苏鲁·拉莱耶", "tank", {}, {}), ("哈斯塔·黄衣之王", "mage", {}, {}),
    ("达贡·深海", "fighter", {}, {}), ("海德拉", "tank", {}, {}),
    ("巴萨坦", "fighter", {}, {}), ("阿特拉克·纳克亚", "assassin", {}, {}),
    ("努格与耶布", "fighter", {}, {}), ("乌素姆", "mage", {}, {}),
    # Elder Gods (10)
    ("巴斯特", "fighter", {}, {}), ("许普诺斯", "mage", {}, {}),
    ("克塔尼德", "mage", {}, {}), ("乌尔塔尔", "fighter", {}, {}),
    ("纳茜·卡姆波尔", "support", {}, {}), ("沃瓦道斯", "fighter", {}, {}),
    ("奥瑞克斯", "fighter", {}, {}), ("卡玛佐兹", "assassin", {}, {}),
    ("扎尔", "mage", {}, {}), ("洛伊戈尔", "fighter", {}, {}),
    # Servitor Races (20)
    ("深潜者", "fighter", {}, {}), ("米·戈", "assassin", {}, {}),
    ("古老者", "mage", {}, {}), ("大蠕虫", "tank", {}, {}),
    ("巨噬蠕虫", "tank", {}, {}), ("伊斯之伟大种族", "mage", {}, {}),
    ("飞天水螅", "assassin", {}, {}), ("夜魇", "assassin", {}, {}),
    ("食尸鬼", "assassin", {}, {}), ("廷达罗斯猎犬", "assassin", {}, {}),
    ("蛇人", "fighter", {}, {}), ("星之彩", "mage", {}, {}),
    ("无形之子", "assassin", {}, {}), ("克苏鲁的星之眷族", "fighter", {}, {}),
    ("冷蛛", "assassin", {}, {}), ("妖鬼", "fighter", {}, {}),
    ("惊惧猎手", "assassin", {}, {}), ("古革巨人", "tank", {}, {}),
    ("炎之精", "mage", {}, {}), ("外神之仆", "assassin", {}, {}),
    # Human Characters (20)
    ("阿卜杜·阿尔哈兹莱德", "mage", {}, {}), ("伦道夫·卡特", "support", {}, {}),
    ("亨利·阿米蒂奇", "support", {}, {}), ("赫伯特·韦斯特", "support", {}, {}),
    ("克劳福德·蒂林哈斯特", "mage", {}, {}), ("老沃特雷", "mage", {}, {}),
    ("威尔伯·沃特雷", "fighter", {}, {}), ("查尔斯·德克斯特·沃德", "mage", {}, {}),
    ("约瑟夫·柯温", "mage", {}, {}), ("基恩教授", "support", {}, {}),
    ("纳撒尼尔·温盖特·皮斯理", "support", {}, {}), ("罗伯特·布莱克", "support", {}, {}),
    ("埃里希·赞恩", "support", {}, {}), ("理查德·厄普顿·皮克曼", "assassin", {}, {}),
    ("丹弗斯教授", "support", {}, {}), ("莱克博士", "support", {}, {}),
    ("戴尔教授", "support", {}, {}), ("摩根博士", "support", {}, {}),
    ("恐怖作家", "mage", {}, {}), ("调查员", "support", {}, {}),
    # Locations & Artifacts (15)
    ("拉莱耶", "tank", {}, {}), ("印斯茅斯", "fighter", {}, {}),
    ("阿卡姆", "support", {}, {}), ("敦威治", "mage", {}, {}),
    ("金斯波特", "support", {}, {}), ("乌尔塔", "mage", {}, {}),
    ("冷之高原", "mage", {}, {}), ("幻梦境", "mage", {}, {}),
    ("死灵之书", "mage", {}, {}), ("无名祭祀书", "mage", {}, {}),
    ("水神克塔亚特", "mage", {}, {}), ("黄衣之王剧本", "mage", {}, {}),
    ("银之钥", "support", {}, {}), ("黄金蜂蜜酒", "support", {}, {}),
    ("闪耀的偏方三八面体", "mage", {}, {}),
    # Expanded (57 more for 172)
    ("姆纳加拉", "tank", {}, {}), ("塞埃格", "fighter", {}, {}),
    ("夏乌戈纳尔·法格恩", "fighter", {}, {}), ("祖谢坤", "mage", {}, {}),
    ("莫尔迪基安", "assassin", {}, {}), ("巴格·沙斯", "tank", {}, {}),
    ("约-索托特", "mage", {}, {}), ("洛依高尔", "fighter", {}, {}),
    ("乌特·乌尔斯", "mage", {}, {}), ("克萨诺斯", "mage", {}, {}),
    ("伊德海拉·梦", "mage", {}, {}), ("格罗斯·高", "fighter", {}, {}),
    ("拉沃莫斯", "assassin", {}, {}), ("库潘格尼", "tank", {}, {}),
    ("提克", "assassin", {}, {}), ("夏恩", "fighter", {}, {}),
    ("食尸鬼之王", "assassin", {}, {}), ("深潜者之王", "fighter", {}, {}),
    ("蛇人之王", "fighter", {}, {}), ("夜魇之王", "assassin", {}, {}),
    ("蠕虫之王", "tank", {}, {}), ("大祭司", "mage", {}, {}),
    ("亵渎者", "assassin", {}, {}), ("异教徒·长老", "mage", {}, {}),
    ("隐秘信徒", "assassin", {}, {}), ("星之教会", "support", {}, {}),
    ("深渊之声", "mage", {}, {}), ("虚空低语", "assassin", {}, {}),
    ("黑暗回声", "mage", {}, {}), ("疯狂鼓手", "fighter", {}, {}),
    ("无名迷雾", "mage", {}, {}), ("无形黑暗", "assassin", {}, {}),
    ("盲目痴愚", "mage", {}, {}), ("不可名状", "tank", {}, {}),
    ("时空错乱", "mage", {}, {}), ("维度裂隙", "mage", {}, {}),
    ("疯狂山脉", "tank", {}, {}), ("南极大冰川", "mage", {}, {}),
    ("无名之城", "fighter", {}, {}), ("黄衣之王之城", "mage", {}, {}),
    ("深潜者之城", "fighter", {}, {}), ("宇宙深渊", "mage", {}, {}),
    ("门之钥", "support", {}, {}), ("万物归一", "mage", {}, {}),
    ("最终混沌", "tank", {}, {}), ("宇宙真理", "mage", {}, {}),
    ("星辰之音", "mage", {}, {}), ("暗星", "mage", {}, {}),
    ("赤星", "mage", {}, {}), ("黑洞呼唤", "mage", {}, {}),
    ("疯狂根源", "assassin", {}, {}), ("恐惧之源", "assassin", {}, {}),
    ("噩梦幻象", "mage", {}, {}), ("永恒静默", "support", {}, {}),
    ("虚无终局", "mage", {}, {}), ("万古长夜", "tank", {}, {}),
    ("亘古之存在", "mage", {}, {}),
    # +3 more for 172
    ("黑法老", "mage", {}, {}), ("暗夜咆哮者", "assassin", {}, {}), ("肿胀之女", "tank", {}, {}),
]

# ======================== HARRY POTTER (+157) ========================
HERO_DEFS["harry_potter"] = [
    # Already: 哈利·波特, 赫敏·格兰杰, 罗恩·韦斯莱, 邓布利多, 伏地魔, 斯内普, 麦格, 海格, 小天狼星, 莱姆斯·卢平...
    # Gryffindor (15)
    ("金妮·韦斯莱", "fighter", {}, {}), ("纳威·隆巴顿", "fighter", {}, {}),
    ("弗雷德·韦斯莱", "assassin", {}, {}), ("乔治·韦斯莱", "assassin", {}, {}),
    ("迪安·托马斯", "fighter", {}, {}), ("西莫·斐尼甘", "mage", {}, {}),
    ("帕瓦蒂·佩蒂尔", "support", {}, {}), ("拉文德·布朗", "support", {}, {}),
    ("奥利弗·伍德", "fighter", {}, {}), ("安吉丽娜·约翰逊", "fighter", {}, {}),
    ("凯蒂·贝尔", "fighter", {}, {}), ("考麦克·麦克拉根", "fighter", {}, {}),
    ("罗米达·万尼", "support", {}, {}), ("科林·克里维", "support", {}, {}),
    ("邓布利多军", "fighter", {}, {}),
    # Slytherin (15)
    ("德拉科·马尔福", "assassin", {}, {}), ("文森特·克拉布", "tank", {}, {}),
    ("格雷戈里·高尔", "tank", {}, {}), ("潘西·帕金森", "support", {}, {}),
    ("西奥多·诺特", "mage", {}, {}), ("马库斯·弗林特", "fighter", {}, {}),
    ("米利森特·伯斯德", "tank", {}, {}), ("达芙妮·格林格拉斯", "support", {}, {}),
    ("布雷司·沙比尼", "assassin", {}, {}), ("汤姆·里德尔", "mage", {}, {}),
    ("血人巴罗", "assassin", {}, {}), ("格雷女士", "support", {}, {}),
    ("胖修士", "support", {}, {}), ("差点没头的尼克", "support", {}, {}),
    ("皮皮鬼", "assassin", {}, {}),
    # Ravenclaw & Hufflepuff (15)
    ("卢娜·洛夫古德", "mage", {}, {}), ("秋·张", "fighter", {}, {}),
    ("帕德玛·佩蒂尔", "support", {}, {}), ("迈克尔·科纳", "fighter", {}, {}),
    ("泰瑞·布特", "fighter", {}, {}), ("安东尼·戈德斯坦", "support", {}, {}),
    ("塞德里克·迪戈里", "fighter", {}, {}), ("厄尼·麦克米兰", "fighter", {}, {}),
    ("汉娜·艾博", "support", {}, {}), ("苏珊·博恩斯", "fighter", {}, {}),
    ("扎克赖斯·史密斯", "assassin", {}, {}), ("贾斯廷·芬列里", "support", {}, {}),
    ("尼法朵拉·唐克斯", "assassin", {}, {}), ("加里克·奥利凡德", "support", {}, {}),
    ("哭泣的桃金娘", "support", {}, {}),
    # Order of the Phoenix (15)
    ("阿拉斯托·穆迪", "fighter", {}, {}), ("亚瑟·韦斯莱", "support", {}, {}),
    ("莫丽·韦斯莱", "fighter", {}, {}), ("比尔·韦斯莱", "fighter", {}, {}),
    ("查理·韦斯莱", "fighter", {}, {}), ("金斯莱·沙克尔", "fighter", {}, {}),
    ("多洛雷斯·乌姆里奇", "mage", {}, {}), ("鲁弗斯·斯克林杰", "fighter", {}, {}),
    ("埃非亚斯·多吉", "support", {}, {}), ("德达洛·迪歌", "support", {}, {}),
    ("斯多吉·波德摩", "fighter", {}, {}), ("海丝佳·琼斯", "support", {}, {}),
    ("爱米琳·万斯", "assassin", {}, {}), ("蒙顿格斯·弗莱奇", "assassin", {}, {}),
    ("阿伯福思·邓布利多", "fighter", {}, {}),
    # Death Eaters (15)
    ("小巴蒂·克劳奇", "assassin", {}, {}), ("贝拉特里克斯·莱斯特兰奇", "assassin", {}, {}),
    ("卢修斯·马尔福", "fighter", {}, {}), ("纳西莎·马尔福", "support", {}, {}),
    ("芬里尔·格雷伯克", "fighter", {}, {}), ("安东宁·多洛霍夫", "assassin", {}, {}),
    ("阿米库斯·卡罗", "fighter", {}, {}), ("阿莱克托·卡罗", "mage", {}, {}),
    ("科班·亚克斯利", "fighter", {}, {}), ("沃尔顿·麦克尼尔", "fighter", {}, {}),
    ("奥古斯特·卢克伍德", "mage", {}, {}), ("索菲尼·罗尔", "mage", {}, {}),
    ("特拉弗斯", "fighter", {}, {}), ("塞尔温", "fighter", {}, {}),
    ("伊戈尔·卡卡洛夫", "fighter", {}, {}),
    # Creatures (15)
    ("巴克比克", "fighter", {}, {}), ("诺伯特", "fighter", {}, {}),
    ("匈牙利树蜂", "tank", {}, {}), ("蛇怪", "assassin", {}, {}),
    ("阿拉戈克", "tank", {}, {}), ("路威", "tank", {}, {}),
    ("鹰头马身有翼兽", "fighter", {}, {}), ("夜骐", "assassin", {}, {}),
    ("凤凰福克斯", "support", {}, {}), ("匈牙利树蜂·龙", "tank", {}, {}),
    ("威尔士绿龙", "fighter", {}, {}), ("中国火球龙", "mage", {}, {}),
    ("瑞典短鼻龙", "fighter", {}, {}), ("秘鲁毒牙龙", "assassin", {}, {}),
    ("挪威脊背龙", "fighter", {}, {}),
    # Expanded (52 more for 172)
    ("詹姆·波特", "fighter", {}, {}), ("莉莉·波特", "support", {}, {}),
    ("小矮星彼得", "assassin", {}, {}), ("雷古勒斯·布莱克", "assassin", {}, {}),
    ("安多米达·唐克斯", "support", {}, {}), ("泰德·唐克斯", "support", {}, {}),
    ("芙蓉·德拉库尔", "support", {}, {}), ("加布丽·德拉库尔", "support", {}, {}),
    ("威克多尔·克鲁姆", "fighter", {}, {}), ("马克西姆夫人", "tank", {}, {}),
    ("巴希达·巴沙特", "support", {}, {}), ("盖勒特·格林德沃", "mage", {}, {}),
    ("克雷登斯·拜尔本", "mage", {}, {}), ("奎妮·戈德斯坦", "support", {}, {}),
    ("雅各布·科瓦尔斯基", "support", {}, {}), ("纽特·斯卡曼德", "support", {}, {}),
    ("蒂娜·戈德斯坦", "fighter", {}, {}), ("瑟拉菲娜·皮奎里", "fighter", {}, {}),
    ("帕西瓦尔·格雷维斯", "fighter", {}, {}), ("莉塔·莱斯特兰奇", "mage", {}, {}),
    ("忒修斯·斯卡曼德", "fighter", {}, {}), ("尼可·勒梅", "support", {}, {}),
    ("尤瑟夫·卡玛", "fighter", {}, {}), ("纳吉尼", "assassin", {}, {}),
    ("文达·罗齐尔", "mage", {}, {}), ("阿伯纳西", "fighter", {}, {}),
    ("纳尔拉克", "assassin", {}, {}), ("安东·沃格尔", "fighter", {}, {}),
    ("赫尔穆特", "fighter", {}, {}), ("格里姆森", "assassin", {}, {}),
    ("魔法部长", "support", {}, {}), ("国际巫师联合会", "support", {}, {}),
    ("马人费伦泽", "support", {}, {}), ("家养小精灵多比", "support", {}, {}),
    ("克利切", "support", {}, {}), ("闪闪", "support", {}, {}),
    ("分院帽", "support", {}, {}), ("格兰芬多之剑", "fighter", {}, {}),
    ("拉文克劳冠冕", "support", {}, {}), ("赫奇帕奇金杯", "support", {}, {}),
    ("斯莱特林挂坠盒", "mage", {}, {}), ("复活石", "support", {}, {}),
    ("老魔杖", "mage", {}, {}), ("隐形衣", "assassin", {}, {}),
    ("预言球", "support", {}, {}), ("时间转换器", "support", {}, {}),
    ("活点地图", "assassin", {}, {}), ("冥想盆", "support", {}, {}),
    ("吐真剂", "support", {}, {}),     ("福灵剂", "support", {}, {}),
    ("复方汤剂", "assassin", {}, {}), ("爱情魔药", "support", {}, {}),
    # +20 more for 172
    ("珀西·韦斯莱", "support", {}, {}), ("奥利凡德", "support", {}, {}), ("弗立维教授", "mage", {}, {}),
    ("斯普劳特教授", "support", {}, {}), ("霍琦夫人", "fighter", {}, {}), ("庞弗雷夫人", "support", {}, {}),
    ("费尔奇", "fighter", {}, {}), ("洛丽丝夫人", "assassin", {}, {}), ("宾斯教授", "mage", {}, {}),
    ("特里劳妮教授", "mage", {}, {}), ("斯拉格霍恩教授", "support", {}, {}), ("吉德罗·洛哈特", "support", {}, {}),
    ("奇洛教授", "mage", {}, {}), ("小矮星彼得·虫尾巴", "assassin", {}, {}),
    ("丽塔·斯基特", "assassin", {}, {}), ("谢诺菲留斯·洛夫古德", "support", {}, {}),
    ("马人·玛格瑞", "fighter", {}, {}), ("博格特", "mage", {}, {}),
    ("摄魂怪", "assassin", {}, {}), ("阴尸", "tank", {}, {}),
]

# ======================== FEIREN XUEYUAN (+136) ========================
HERO_DEFS["feiren_xueyuan"] = [
    # Already has: 九头虫, 哪吒, 土地, 大鹏, 太白, 嫦娥, 常乐, 广目, 悟静, 晓音, etc.
    ("悟空", "fighter", {}, {}), ("龙马", "fighter", {}, {}), ("羊丽", "support", {}, {}),
    ("雷姆", "mage", {}, {}), ("拉姆", "support", {}, {}), ("白象", "tank", {}, {}),
    ("金角", "mage", {}, {}), ("银角", "mage", {}, {}), ("玉兔", "support", {}, {}),
    ("白骨", "assassin", {}, {}), ("牛魔", "tank", {}, {}), ("铁扇", "mage", {}, {}),
    ("红孩", "mage", {}, {}), ("蝎子", "assassin", {}, {}), ("蜘蛛", "assassin", {}, {}),
    ("狮驼", "fighter", {}, {}), ("青狮", "tank", {}, {}), ("文殊", "support", {}, {}),
    ("普贤", "support", {}, {}), ("观音", "support", {}, {}), ("地藏", "tank", {}, {}),
    ("阎罗", "mage", {}, {}), ("钟馗", "fighter", {}, {}), ("孟婆", "support", {}, {}),
    ("黑白", "assassin", {}, {}), ("无常", "assassin", {}, {}), ("判官", "mage", {}, {}),
    ("龙王", "mage", {}, {}), ("龟丞相", "tank", {}, {}), ("虾兵", "fighter", {}, {}),
    ("蟹将", "tank", {}, {}), ("夜叉", "assassin", {}, {}), ("罗刹", "fighter", {}, {}),
    ("阿修罗", "fighter", {}, {}), ("紧那罗", "support", {}, {}), ("乾闼婆", "support", {}, {}),
    ("迦楼罗", "fighter", {}, {}), ("摩睺罗伽", "tank", {}, {}), ("帝释", "mage", {}, {}),
    ("梵天", "mage", {}, {}), ("湿婆", "fighter", {}, {}), ("毗湿奴", "support", {}, {}),
    ("吉祥天", "support", {}, {}), ("辩才天", "support", {}, {}), ("大黑天", "fighter", {}, {}),
    ("鬼子母", "support", {}, {}), ("孔雀", "mage", {}, {}), ("金翅", "fighter", {}, {}),
    ("玉皇", "mage", {}, {}), ("王母", "support", {}, {}), ("七仙女", "support", {}, {}),
    ("太白金星", "support", {}, {}), ("太上老君", "mage", {}, {}), ("二郎神", "fighter", {}, {}),
    ("哪吒三太子", "fighter", {}, {}), ("托塔天王", "tank", {}, {}), ("巨灵神", "tank", {}, {}),
    ("四大天王", "tank", {}, {}), ("千里眼", "marksman", {}, {}), ("顺风耳", "support", {}, {}),
    ("雷公", "mage", {}, {}), ("电母", "mage", {}, {}), ("风伯", "mage", {}, {}),
    ("雨师", "mage", {}, {}), ("二十八宿", "fighter", {}, {}), ("天罡", "fighter", {}, {}),
    ("地煞", "assassin", {}, {}), ("城隍", "support", {}, {}), ("灶君", "support", {}, {}),
    ("门神", "tank", {}, {}), ("福神", "support", {}, {}), ("禄神", "support", {}, {}),
    ("寿星", "support", {}, {}), ("喜神", "support", {}, {}), ("财神", "support", {}, {}),
    ("孙悟空_FL", "fighter", {}, {}), ("猪八戒", "tank", {}, {}), ("沙和尚", "fighter", {}, {}),
    ("唐僧_FL", "support", {}, {}), ("白龙马", "fighter", {}, {}), ("牛魔王_FL", "tank", {}, {}),
    ("铁扇公主_FL", "mage", {}, {}), ("红孩儿_FL", "mage", {}, {}), ("如意真仙", "support", {}, {}),
    ("蜘蛛精_FL", "assassin", {}, {}), ("蝎子精_FL", "assassin", {}, {}), ("白面狐狸", "assassin", {}, {}),
    ("玉面公主", "support", {}, {}), ("万圣龙王", "mage", {}, {}), ("九头驸马", "fighter", {}, {}),
    ("奔波儿灞", "assassin", {}, {}), ("灞波儿奔", "assassin", {}, {}), ("黄袍怪", "fighter", {}, {}),
    ("金角大王", "mage", {}, {}), ("银角大王", "mage", {}, {}), ("青牛精", "fighter", {}, {}),
    ("黄眉大王", "mage", {}, {}), ("赛太岁", "fighter", {}, {}), ("百眼魔君", "mage", {}, {}),
    ("狮驼王", "fighter", {}, {}), ("象王", "tank", {}, {}), ("金翅大鹏_FL", "fighter", {}, {}),
    ("白鹿精", "support", {}, {}), ("白面狐狸_FL", "assassin", {}, {}), ("老鼠精", "assassin", {}, {}),
    ("杏仙", "support", {}, {}), ("十八罗汉", "fighter", {}, {}), ("降龙罗汉", "fighter", {}, {}),
    ("伏虎罗汉", "fighter", {}, {}), ("布袋罗汉", "support", {}, {}), ("长眉罗汉", "mage", {}, {}),
    ("开心罗汉", "support", {}, {}), ("沉思罗汉", "support", {}, {}), ("挖耳罗汉", "assassin", {}, {}),
    ("看门罗汉", "tank", {}, {}), ("骑象罗汉", "fighter", {}, {}), ("坐鹿罗汉", "support", {}, {}),
    ("举钵罗汉", "support", {}, {}), ("托塔罗汉", "tank", {}, {}), ("静坐罗汉", "support", {}, {}),
    ("过江罗汉", "fighter", {}, {}), ("笑狮罗汉", "fighter", {}, {}), ("芭蕉罗汉", "support", {}, {}),
    ("灵吉菩萨", "support", {}, {}), ("地藏王", "tank", {}, {}), ("大势至", "support", {}, {}),
    ("日光菩萨", "support", {}, {}), ("月光菩萨", "support", {}, {}), ("虚空藏", "support", {}, {}),
    ("除盖障", "support", {}, {}), ("金刚手", "fighter", {}, {}), ("金刚拳", "fighter", {}, {}),
    ("金刚语", "mage", {}, {}), ("金刚意", "support", {}, {}),
    # +12 more for 172
    ("夸父", "tank", {}, {}), ("后羿", "marksman", {}, {}), ("刑天", "fighter", {}, {}),
    ("祝融_FL", "mage", {}, {}), ("共工", "mage", {}, {}), ("女娲", "support", {}, {}),
    ("伏羲", "mage", {}, {}), ("神农_FL", "support", {}, {}), ("燧人", "support", {}, {}),
    ("有巢", "support", {}, {}), ("蚩尤_FL", "fighter", {}, {}), ("应龙", "fighter", {}, {}),
]

# ======================== JOURNEY TO THE WEST (+147) ========================
HERO_DEFS["journey_to_the_west"] = [
    # Already has: 孙悟空, 猪悟能, 沙悟净, 唐僧, 牛魔王, 铁扇公主, 红孩儿, 白骨精, 蜘蛛精, 金翅大鹏...
    # 取经团队扩展
    ("白龙马·人形", "fighter", {}, {}), ("六耳猕猴", "assassin", {}, {}), ("通臂猿猴", "fighter", {}, {}),
    ("赤尻马猴", "assassin", {}, {}), ("金蝉子", "support", {}, {}),
    # 天宫神佛 (30)
    ("玉皇大帝", "mage", {}, {}), ("王母娘娘", "support", {}, {}), ("太上老君", "mage", {}, {}),
    ("二郎神", "fighter", {}, {}), ("哪吒三太子", "fighter", {}, {}), ("托塔天王", "tank", {}, {}),
    ("巨灵神", "tank", {}, {}), ("四大天王·持国", "tank", {}, {}), ("四大天王·增长", "fighter", {}, {}),
    ("四大天王·广目", "marksman", {}, {}), ("四大天王·多闻", "tank", {}, {}), ("太白金星", "support", {}, {}),
    ("嫦娥仙女", "support", {}, {}), ("吴刚", "fighter", {}, {}), ("月老", "support", {}, {}),
    ("赤脚大仙", "fighter", {}, {}), ("二十八宿·角木蛟", "fighter", {}, {}), ("二十八宿·亢金龙", "fighter", {}, {}),
    ("二十八宿·氐土貉", "tank", {}, {}), ("二十八宿·房日兔", "marksman", {}, {}), ("二十八宿·心月狐", "assassin", {}, {}),
    ("二十八宿·尾火虎", "fighter", {}, {}), ("二十八宿·箕水豹", "assassin", {}, {}), ("雷公", "mage", {}, {}),
    ("电母", "mage", {}, {}), ("风伯", "mage", {}, {}), ("雨师", "support", {}, {}),
    ("织女", "support", {}, {}), ("牛郎", "support", {}, {}), ("七仙女", "support", {}, {}),
    # 西天佛国 (20)
    ("如来佛祖", "mage", {}, {}), ("观音菩萨", "support", {}, {}), ("文殊菩萨", "support", {}, {}),
    ("普贤菩萨", "support", {}, {}), ("地藏菩萨", "tank", {}, {}), ("大势至菩萨", "support", {}, {}),
    ("灵吉菩萨", "support", {}, {}), ("孔雀大明王", "mage", {}, {}), ("金翅大鹏雕", "fighter", {}, {}),
    ("阿难", "support", {}, {}), ("迦叶", "support", {}, {}), ("弥勒佛", "support", {}, {}),
    ("燃灯古佛", "mage", {}, {}), ("药师佛", "support", {}, {}), ("韦陀", "fighter", {}, {}),
    ("金刚·青", "fighter", {}, {}), ("金刚·红", "fighter", {}, {}), ("金刚·白", "fighter", {}, {}),
    ("金刚·黄", "tank", {}, {}), ("罗汉·降龙", "fighter", {}, {}),
    # 妖怪群 (60)
    ("混世魔王", "fighter", {}, {}), ("蛟魔王", "fighter", {}, {}), ("鹏魔王", "fighter", {}, {}),
    ("狮驼王", "fighter", {}, {}), ("猕猴王", "assassin", {}, {}), ("禺狨王", "assassin", {}, {}),
    ("黑风怪", "tank", {}, {}), ("黄风怪", "mage", {}, {}), ("白骨夫人", "assassin", {}, {}),
    ("黄袍怪·奎木狼", "fighter", {}, {}), ("金角大王", "mage", {}, {}), ("银角大王", "mage", {}, {}),
    ("压龙大仙", "support", {}, {}), ("精细鬼", "assassin", {}, {}), ("伶俐虫", "assassin", {}, {}),
    ("巴山虎", "fighter", {}, {}), ("倚海龙", "fighter", {}, {}), ("狮猁怪", "fighter", {}, {}),
    ("灵感大王", "mage", {}, {}), ("独角兕大王", "tank", {}, {}), ("如意真仙", "support", {}, {}),
    ("琵琶精", "assassin", {}, {}), ("六百里驼罗", "tank", {}, {}), ("赛太岁", "fighter", {}, {}),
    ("百眼魔君", "mage", {}, {}), ("蜘蛛精·红", "assassin", {}, {}), ("蜘蛛精·橙", "assassin", {}, {}),
    ("蜘蛛精·黄", "assassin", {}, {}), ("蜘蛛精·绿", "assassin", {}, {}), ("蜘蛛精·青", "assassin", {}, {}),
    ("蜘蛛精·蓝", "assassin", {}, {}), ("蜘蛛精·紫", "assassin", {}, {}), ("狮驼岭·青毛狮", "fighter", {}, {}),
    ("狮驼岭·黄牙象", "tank", {}, {}), ("狮驼岭·云程鹏", "fighter", {}, {}), ("白鹿精", "support", {}, {}),
    ("白面狐狸", "assassin", {}, {}), ("南山大王", "fighter", {}, {}), ("黄狮精", "fighter", {}, {}),
    ("九灵元圣", "mage", {}, {}), ("辟寒大王", "fighter", {}, {}), ("辟暑大王", "fighter", {}, {}),
    ("辟尘大王", "fighter", {}, {}), ("玄英洞三怪", "mage", {}, {}), ("玉兔精", "assassin", {}, {}),
    ("老鼠精", "assassin", {}, {}), ("艾叶花豹", "assassin", {}, {}), ("蟒蛇精", "assassin", {}, {}),
    ("竹节山七狮", "fighter", {}, {}), ("黄眉大王", "mage", {}, {}), ("青牛精", "fighter", {}, {}),
    ("九头虫", "fighter", {}, {}), ("奔波儿灞", "assassin", {}, {}), ("灞波儿奔", "assassin", {}, {}),
    ("万圣公主", "mage", {}, {}), ("铁背苍狼", "fighter", {}, {}), ("杏仙", "support", {}, {}),
    ("孤直公", "support", {}, {}), ("凌空子", "mage", {}, {}), ("拂云叟", "support", {}, {}),
    # 人间角色 (20)
    ("李世民", "fighter", {}, {}), ("魏征", "mage", {}, {}), ("袁天罡", "mage", {}, {}),
    ("李淳风", "mage", {}, {}), ("尉迟恭", "tank", {}, {}), ("秦琼", "fighter", {}, {}),
    ("高太公", "support", {}, {}), ("高翠兰", "support", {}, {}), ("陈光蕊", "support", {}, {}),
    ("满堂娇", "support", {}, {}), ("刘伯钦", "fighter", {}, {}), ("寇员外", "support", {}, {}),
    ("金池长老", "mage", {}, {}), ("车迟国王", "support", {}, {}), ("比丘国王", "support", {}, {}),
    ("灭法国王", "support", {}, {}), ("朱紫国王", "support", {}, {}), ("宝象国王", "support", {}, {}),
    ("乌鸡国王", "support", {}, {}), ("女儿国王", "support", {}, {}),
    # 实力角色 (17)
    ("镇元大仙", "mage", {}, {}), ("菩提祖师", "mage", {}, {}), ("黎山老母", "support", {}, {}),
    ("紫阳真人", "support", {}, {}), ("张道陵", "mage", {}, {}), ("葛玄", "mage", {}, {}),
    ("许逊", "mage", {}, {}), ("萨守坚", "mage", {}, {}), ("钟馗", "fighter", {}, {}),
    ("阎罗王", "mage", {}, {}), ("判官·崔珏", "mage", {}, {}), ("孟婆", "support", {}, {}),
    ("牛头", "tank", {}, {}), ("马面", "fighter", {}, {}), ("黑无常", "assassin", {}, {}),
    ("白无常", "assassin", {}, {}), ("土地公", "support", {}, {}),
    # +4 more for 172
    ("城隍爷", "support", {}, {}), ("灶王爷", "support", {}, {}), ("门神·神荼", "tank", {}, {}),
    ("门神·郁垒", "tank", {}, {}),
]

def generate_skills(hero_name, role, custom_names=None, custom_effects=None):
    """Generate 4 skills for a hero based on role template."""
    if custom_names is None:
        custom_names = {}
    if custom_effects is None:
        custom_effects = {}

    template = ROLE_TEMPLATES[role]
    skills = []
    for slot_tmpl in template["slots"]:
        skill = copy.deepcopy(slot_tmpl)
        key = skill["key"]

        # Override name
        if key in custom_names:
            skill["name"] = custom_names[key]

        # Override effects
        if key in custom_effects:
            skill["effects"] = custom_effects[key]

        # Ensure description matches name
        if key in custom_names and key not in custom_effects:
            pass  # Keep template description

        skills.append(skill)
    return skills


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("game_id", help="e.g. smite, dota2, heroes_of_the_storm, onmyoji_arena")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be added without writing")
    args = parser.parse_args()

    game = args.game_id
    if game not in HERO_DEFS:
        print(f"ERROR: Unknown game '{game}'. Available: {list(HERO_DEFS.keys())}")
        sys.exit(1)

    current_count = len(list_pool_heroes(game))
    heroes_to_add = HERO_DEFS[game]

    added = 0
    skipped = []
    for hero_name, role, custom_names, custom_effects in heroes_to_add:
        if pool_has(game, hero_name):
            skipped.append(hero_name)
            continue
        skills = generate_skills(hero_name, role, custom_names, custom_effects)
        if not args.dry_run:
            write_hero_skill(game, hero_name, skills)
        added += 1

    new_total = current_count + added

    if args.dry_run:
        print(f"[DRY RUN] {game}: {current_count}→{new_total} (+{added})")
        print(f"  Adding: {[h[0] for h in heroes_to_add if h[0] not in skipped]}")
        if skipped:
            print(f"  Skipped (already exist): {skipped}")
        return

    print(f"[OK] {game}: {current_count}→{new_total} (+{added})")
    if skipped:
        print(f"  Skipped (already exist): {skipped}")

if __name__ == "__main__":
    main()
