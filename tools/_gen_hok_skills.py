#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""王者荣耀 / 传说对决 技能批量生成器

基于 role_dnd_templates.json 的 6 角色模板，为英雄生成 D&D 5e 技能数据。

用法：
    python tools/_gen_hok_skills.py --game honor_of_kings --batch 1
    python tools/_gen_hok_skills.py --game arena_of_valor --batch 1

输出：追加到 data/skills/{game}.json
"""

import json
import os
import sys
import argparse
import random
from copy import deepcopy

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.skill_pool import write_hero_skill
from typing import Dict, List, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

TEMPLATE_PATH = os.path.join(PROJECT_ROOT, "tools", "_archive", "role_dnd_templates.json")

# ── 角色 → 模板映射 ──
ROLE_TO_TEMPLATE = {
    "tank": "tank", "坦克": "tank",
    "fighter": "fighter", "战士": "fighter",
    "assassin": "assassin", "刺客": "assassin",
    "mage": "mage", "法师": "mage",
    "marksman": "marksman", "射手": "marksman",
    "support": "support", "辅助": "support",
}

# 技能类型映射
ROLE_DMG_TYPE = {
    "tank": "钝击", "fighter": "挥砍", "assassin": "挥砍",
    "mage": "力场", "marksman": "穿刺", "support": "光耀",
}
ROLE_SKILL_TYPE = {
    "tank": "物理", "fighter": "物理", "assassin": "物理",
    "mage": "法术", "marksman": "物理", "support": "法术",
}
ROLE_PRIMARY_ATTR = {
    "tank": "STR", "fighter": "STR", "assassin": "DEX",
    "mage": "INT", "marksman": "DEX", "support": "WIS",
}
ROLE_RANGE = {
    "tank": "近战", "fighter": "近战", "assassin": "近战",
    "mage": "远程", "marksman": "远程", "support": "远程",
}

# ── effects 风味描述库 ──
EFFECT_FLAVOR = {
    "control": "使目标陷入{desc}状态（{save}豁免，DC=8+PROF+{attr}）",
    "slow": "使目标移动速度减半，持续{dur}轮",
    "shield": "获得{val}点临时护盾，持续{dur}轮",
    "reduce": "本回合受到伤害减半",
    "heal": "恢复{val}点生命值",
    "lifesteal": "造成伤害的50%转化为自身生命",
    "dot": "目标每回合受到{val}点{type}伤害，持续{dur}轮",
    "execute": "对生命值低于50%的目标额外造成2d6伤害",
    "true_dmg": "此伤害无视护盾与减伤",
    "buff": "攻击力+2，持续{dur}轮",
    "accel": "获得额外移动力，本回合可穿越敌人",
    "sunder": "目标AC-2，持续{dur}轮",
    "vuln": "标记目标：下次对该目标的攻击优势",
    "crit": "本回合攻击掷骰取优势",
    "reflect": "受击时反弹{dur}点伤害",
    "immune": "免疫下一次控制效果",
    "invis": "获得隐身，持续到攻击或回合结束",
    "cleanse": "移除自身所有负面状态",
    "revive": "死亡后以1HP复活（每场战斗1次）",
}

CONTROL_DESC = {
    "stun": "眩晕", "hold": "束缚", "prone": "倒地",
    "knockback": "击退", "freeze": "冻结", "fear": "恐惧",
    "silence": "沉默", "charm": "魅惑", "petrify": "石化",
}

# ── D&D 风味描述模板 ──
DND_FLAVOR_Q = {
    "tank": "沉重的钝击撕裂空气，{hero}挥动武器发起冲锋。{dice}+{attr} {dmg_type}伤害。{eff}",
    "fighter": "{hero}以战技之姿发起突刺，一击命中要害。{dice}+{attr} {dmg_type}伤害。{eff}",
    "assassin": "如暗影中的利刃，{hero}的突袭无声无息。{dice}+{attr} {dmg_type}伤害。{eff}",
    "mage": "奥术能量在指尖凝聚，{hero}释放出一枚魔法飞弹。{dice}+{attr} {dmg_type}伤害。{eff}",
    "marksman": "弓弦嗡鸣，一支利箭破空而出。{dice}+{attr} {dmg_type}伤害。{eff}",
    "support": "神圣的光芒如晨曦绽放，{hero}引导着治愈之力。{dice}+{attr} {dmg_type}伤害。{eff}",
}

DND_FLAVOR_W = {
    "tank": "{hero}架起防御姿态，以钢铁意志吸收伤害。{dice}+{attr} {dmg_type}伤害。{eff}",
    "fighter": "蓄力一击，{hero}的战吼响彻战场。{dice}+{attr} {dmg_type}伤害。{eff}",
    "assassin": "诡诈的战术——{hero}从阴影中掷出飞刃。{dice}+{attr} {dmg_type}伤害。{eff}",
    "mage": "咒语的符文在空中闪烁，一道魔法阵轰然展开。{dice}+{attr} {dmg_type}伤害。{eff}",
    "marksman": "{hero}设下致命的陷阱，猎物已无处可逃。{dice}+{attr} {dmg_type}伤害。{eff}",
    "support": "圣言诵出，{hero}的祝福化为护盾笼罩盟友。{dice}+{attr} {dmg_type}伤害。{eff}",
}

DND_FLAVOR_E = {
    "tank": "大地震颤，{hero}的重击碾碎敌阵。{dice}+{attr} {dmg_type}伤害。{eff}",
    "fighter": "疾风般的步伐——{hero}突进至敌人身前。{dice}+{attr} {dmg_type}伤害。{eff}",
    "assassin": "身形一闪，{hero}已出现在敌人身后。{dice}+{attr} {dmg_type}伤害。{eff}",
    "mage": "空间扭曲，{hero}的身影在奥术光辉中消失又重现。{dice}+{attr} {dmg_type}伤害。{eff}",
    "marksman": "轻盈的后跳拉开距离，{hero}的箭矢始终锁定目标。{dice}+{attr} {dmg_type}伤害。{eff}",
    "support": "纯净的祝福之光从{hero}手中流淌而出。{dice}+{attr} {dmg_type}伤害。{eff}",
}

DND_FLAVOR_R = {
    "tank": "「见证我的怒火！」{hero}化身不可阻挡的战争机器。{dice}+{attr} {dmg_type}伤害。{eff}",
    "fighter": "终极武技——{hero}释放全部力量的最强一击。{dice}+{attr} {dmg_type}伤害。{eff}",
    "assassin": "死亡的华尔兹开始——{hero}的终极暗杀术。{dice}+{attr} {dmg_type}伤害。{eff}",
    "mage": "禁忌的咒文被咏唱，{hero}释放出毁灭性的魔力洪流。{dice}+{attr} {dmg_type}伤害。{eff}",
    "marksman": "终极狙击——{hero}的箭矢如流星般贯穿战场。{dice}+{attr} {dmg_type}伤害。{eff}",
    "support": "神迹降临！{hero}呼唤至高之力庇佑全队。{dice}+{attr} {dmg_type}伤害。{eff}",
}

DND_FLAVOR = {
    "Q": DND_FLAVOR_Q, "W": DND_FLAVOR_W, "E": DND_FLAVOR_E, "R": DND_FLAVOR_R,
}


def load_templates() -> dict:
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_effect(eff_type: str, role_template: dict, slot_key: str) -> dict:
    """根据 effect 类型构建 effect dict。"""
    primary = role_template.get("primary_attr", "STR")
    save_attr = role_template.get("saving_throw_attr_default", "DEX")
    
    effect = {"type": eff_type}
    
    if eff_type == "control":
        ctrl_desc = random.choice(list(CONTROL_DESC.values()))
        effect["target"] = "敌方"
        effect["duration"] = 1
        if slot_key in ("W", "R"):
            effect["saving_throw"] = {"attr": save_attr, "dc_formula": f"8+PROF+{primary}", "on_save": "无效"}
            effect["desc"] = f"使目标{ctrl_desc}1轮（{save_attr}豁免 DC=8+PROF+{primary}，豁免无效）"
        else:
            effect["desc"] = f"使目标{ctrl_desc}1轮"
    elif eff_type == "slow":
        effect["target"] = "敌方"
        effect["duration"] = random.choice([1, 2])
        effect["desc"] = f"目标移动速度减半，持续{effect['duration']}轮"
    elif eff_type == "shield":
        effect["target"] = "自身"
        effect["duration"] = random.choice([1, 2])
        effect["value"] = random.choice([5, 8, 10])
        effect["desc"] = f"获得{effect['value']}点临时护盾，持续{effect['duration']}轮"
    elif eff_type == "reduce":
        effect["target"] = "自身"
        effect["duration"] = 1
        effect["desc"] = "本回合受到伤害减半"
    elif eff_type == "heal":
        effect["target"] = "自身"
        effect["value"] = random.choice([6, 8, 10, 12])
        effect["desc"] = f"恢复{effect['value']}点生命值"
    elif eff_type == "lifesteal":
        effect["target"] = "自身"
        effect["desc"] = "造成伤害的50%转化为自身生命"
    elif eff_type in ("dot", "bleed", "burn", "poison"):
        effect["target"] = "敌方"
        effect["duration"] = random.choice([1, 2, 3])
        effect["value"] = random.choice([3, 4, 6])
        dmg_desc = {"dot": "持续", "bleed": "流血", "burn": "灼烧", "poison": "毒素"}.get(eff_type, "持续")
        effect["desc"] = f"目标每回合{effect['value']}点{dmg_desc}伤害，持续{effect['duration']}轮"
    elif eff_type == "execute":
        effect["target"] = "敌方"
        effect["desc"] = "对HP<50%目标额外2d6伤害"
    elif eff_type == "true_dmg":
        effect["target"] = "敌方"
        effect["desc"] = "此伤害无视护盾与减伤"
    elif eff_type == "buff":
        effect["target"] = "自身"
        effect["duration"] = random.choice([1, 2])
        effect["desc"] = f"攻击力+2，持续{effect['duration']}轮"
    elif eff_type == "accel":
        effect["target"] = "自身"
        effect["desc"] = "获得额外移动力，本回合可穿越敌人"
    elif eff_type == "sunder":
        effect["target"] = "敌方"
        effect["duration"] = random.choice([1, 2])
        effect["desc"] = f"目标AC-2，持续{effect['duration']}轮"
    elif eff_type == "vuln":
        effect["target"] = "敌方"
        effect["duration"] = 1
        effect["desc"] = "标记目标，下次攻击优势"
    elif eff_type == "crit":
        effect["target"] = "自身"
        effect["desc"] = "本回合攻击掷骰取优势"
    elif eff_type == "reflect":
        effect["target"] = "自身"
        effect["duration"] = 1
        effect["value"] = 3
        effect["desc"] = f"受击反弹3点伤害，持续{effect['duration']}轮"
    elif eff_type == "immune":
        effect["target"] = "自身"
        effect["desc"] = "免疫下一次控制效果"
    elif eff_type == "invis":
        effect["target"] = "自身"
        effect["desc"] = "获得隐身，持续到攻击或回合结束"
    elif eff_type == "cleanse":
        effect["target"] = "自身"
        effect["desc"] = "移除自身所有负面状态"
    
    return effect


def format_dice(dmg: dict) -> str:
    """格式化骰子表达式如 '1d8' 或 '2d6'。"""
    return f"{dmg['dice_count']}d{dmg['dice_size']}"


def generate_skills(hero_name: str, role: str, skill_names: dict, templates: dict) -> list:
    """为一个英雄生成 4 技能 list[dict]。
    
    skill_names: {"Q": "技能名", "W": "技能名", "E": "技能名", "R": "技能名"}
    """
    template_key = ROLE_TO_TEMPLATE.get(role, "fighter")
    t = templates.get(template_key, templates["fighter"])
    slots_cfg = t["slots"]
    
    primary_attr = ROLE_PRIMARY_ATTR.get(role, "STR")
    dmg_type = ROLE_DMG_TYPE.get(role, "挥砍")
    skill_type = ROLE_SKILL_TYPE.get(role, "物理")
    range_val = ROLE_RANGE.get(role, "近战")
    
    slot_order = ["Q", "W", "E", "R"]
    slot_keys = ["1", "2", "3", "P"]
    slot_cds = [0, 1, 2, 4]
    
    # 各 slot 的默认 effects（基于模板 hints）
    slot_default_effects = {
        "Q": [],  # 通常无 effect 或简单
        "W": [],  # control / slow / shield
        "E": [],  # accel / heal / dash
        "R": [],  # 大招 effects
    }
    
    # 根据角色分配 effects
    common = t.get("common_effects", [])
    
    if template_key == "tank":
        slot_default_effects["Q"] = ["slow"] if random.random() > 0.5 else []
        slot_default_effects["W"] = [random.choice(["reduce", "shield"])]
        slot_default_effects["E"] = [random.choice(["sunder", "slow", "control"])]
        slot_default_effects["R"] = ["control"] + ([random.choice(["reduce", "shield"])] if random.random() > 0.5 else [])
    elif template_key == "fighter":
        slot_default_effects["Q"] = ["buff"] if random.random() > 0.5 else []
        slot_default_effects["W"] = [random.choice(["slow", "reduce", "sunder"])]
        slot_default_effects["E"] = [random.choice(["accel", "heal", "lifesteal"])]
        slot_default_effects["R"] = [random.choice(["buff", "execute"])] + ([random.choice(["slow", "control"])] if random.random() > 0.5 else [])
    elif template_key == "assassin":
        slot_default_effects["Q"] = ["execute"] if random.random() > 0.4 else []
        slot_default_effects["W"] = [random.choice(["slow", "dot"])]
        slot_default_effects["E"] = ["accel"]
        slot_default_effects["R"] = random.sample(["invis", "accel", "buff", "execute"], k=min(2, len(common)))
    elif template_key == "mage":
        slot_default_effects["Q"] = ["slow"] if random.random() > 0.5 else []
        slot_default_effects["W"] = ["control"]
        slot_default_effects["E"] = [random.choice(["accel", "slow", "dot"])]
        slot_default_effects["R"] = [random.choice(["control", "dot"])] + (["aoe"] if random.random() > 0.5 else [])
    elif template_key == "marksman":
        slot_default_effects["Q"] = []
        slot_default_effects["W"] = [random.choice(["control", "slow"])]
        slot_default_effects["E"] = ["accel"]
        slot_default_effects["R"] = [random.choice(["vuln", "slow"])]
    elif template_key == "support":
        slot_default_effects["Q"] = ["slow"] if random.random() > 0.5 else []
        slot_default_effects["W"] = [random.choice(["heal", "shield"])]
        slot_default_effects["E"] = [random.choice(["buff", "cleanse", "shield"])]
        slot_default_effects["R"] = [random.choice(["heal", "shield", "control"])] + ([random.choice(["buff", "cleanse"])] if random.random() > 0.5 else [])
    
    skills = []
    for idx, (slot_label, slot_key) in enumerate(zip(slot_order, slot_keys)):
        sc = slots_cfg[slot_label]
        dmg_cfg = deepcopy(sc["damage"])
        dmg_cfg["bonus_attr"] = primary_attr
        
        # 部分角色可微调 damage type
        if template_key == "mage" and slot_label == "R":
            dmg_cfg["type"] = random.choice(["力场", "火焰", "冰霜", "闪电", "光耀"])
        elif template_key == "mage":
            dmg_cfg["type"] = random.choice(["力场", "火焰", "冰霜", "闪电", "光耀", "暗蚀"]).replace("力场", "力场")  # 保留力场为主
            if random.random() < 0.3:
                dmg_cfg["type"] = random.choice(["火焰", "冰霜", "闪电"])
        
        effects = []
        eff_hints = slot_default_effects.get(slot_label, [])
        for eh in eff_hints:
            if eh in ("aoe",):  # aoe is flavor only
                continue
            eff = build_effect(eh, t, slot_label)
            if eff:
                effects.append(eff)
        
        # 最多 3 effects
        effects = effects[:3]
        
        dice_str = format_dice(dmg_cfg)
        eff_desc = ""
        if effects:
            eff_parts = []
            for e in effects:
                if e.get("desc"):
                    eff_parts.append(e["desc"])
                else:
                    eff_parts.append(e.get("type", ""))
            eff_desc = " " + "；".join(eff_parts) + "。"
        
        flavor_template = DND_FLAVOR[slot_label][template_key]
        desc = flavor_template.format(
            hero=hero_name,
            dice=dice_str,
            attr=primary_attr,
            dmg_type=dmg_cfg.get("type", dmg_type),
            eff=eff_desc,
        )
        
        skill = {
            "name": skill_names.get(slot_label, f"技能{slot_label}"),
            "key": slot_key,
            "type": skill_type,
            "action": "动作",
            "range": range_val,
            "target": "单体" if slot_label != "R" or template_key not in ("mage", "tank", "support") else ("范围" if random.random() > 0.4 else "单体"),
            "damage": dmg_cfg,
            "effects": effects,
            "cooldown": slot_cds[idx],
            "description": desc,
        }
        
        # W/R 技能加 saving_throw（按模板覆盖率）
        if slot_label in ("W", "R") and effects:
            has_control = any(e.get("type") in ("control", "眩晕", "stun", "hold") for e in effects)
            if has_control or (template_key in ("mage", "tank", "support") and random.random() > 0.3):
                save_attr = t.get("saving_throw_attr_default", "DEX")
                skill["saving_throw"] = {
                    "attr": save_attr,
                    "dc_formula": f"8+PROF+{primary_attr}",
                    "on_save": "半伤" if template_key == "mage" else "无效",
                }
        
        # 范围技能加 aoe_radius
        if skill["target"] == "范围":
            skill["aoe_radius"] = random.choice([10, 15, 20])
        
        skills.append(skill)
    
    return skills


def load_existing(game: str) -> dict:
    """加载已有技能数据（兼容旧大文件；新数据已迁移至技能池）。"""
    path = os.path.join(PROJECT_ROOT, "data", "skills", f"{game}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_skills(game: str, data: dict):
    """保存技能数据到技能池：data/skills/<game>/<英雄>.json（每英雄独立文件）。"""
    for name, skills in data.items():
        write_hero_skill(game, name, skills)
    print(f"已保存 {len(data)} 英雄到技能池 data/skills/{game}/")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", default="honor_of_kings", choices=["honor_of_kings", "arena_of_valor"])
    parser.add_argument("--batch", type=int, default=1)
    parser.add_argument("--hero-defs", help="JSON file with hero definitions")
    args = parser.parse_args()
    
    if not args.hero_defs:
        print("需要 --hero-defs 参数指定英雄定义文件")
        sys.exit(1)
    
    with open(args.hero_defs, "r", encoding="utf-8") as f:
        hero_defs = json.load(f)
    
    templates = load_templates()
    existing = load_existing(args.game)
    
    new_count = 0
    skip_count = 0
    
    for hero_def in hero_defs:
        name = hero_def["name"]
        if name in existing:
            print(f"  [跳过] {name} 已存在")
            skip_count += 1
            continue
        
        role = hero_def.get("role", "fighter")
        skill_names = hero_def.get("skills", {})
        
        skills = generate_skills(name, role, skill_names, templates)
        existing[name] = skills
        new_count += 1
        print(f"  [生成] {name} ({role}) - {[s['name'] for s in skills]}")
    
    save_skills(args.game, existing)
    print(f"\n批次 # 完成: 新增 {new_count}, 跳过 {skip_count}, 总计 {len(existing)}")
    
    # 校验输出
    errors = []
    for hero_name, hero_skills in existing.items():
        if not isinstance(hero_skills, list):
            errors.append(f"{hero_name}: skills 不是 list")
            continue
        if len(hero_skills) != 4:
            errors.append(f"{hero_name}: 技能数={len(hero_skills)}, 期望4")
        for i, s in enumerate(hero_skills):
            if not isinstance(s, dict):
                errors.append(f"{hero_name}[{i}]: 非 dict")
                continue
            for field in ["name", "key", "type", "cooldown"]:
                if field not in s:
                    errors.append(f"{hero_name}[{i}]: 缺少 {field}")
            if s.get("type") not in ("物理", "法术", "混合", "真实"):
                errors.append(f"{hero_name}[{i}]: 非法 type={s.get('type')}")
    
    if errors:
        print(f"\n⚠ 校验发现问题 {len(errors)} 项:")
        for e in errors[:20]:
            print(f"  - {e}")
    else:
        print("\n✓ 基础校验通过")


if __name__ == "__main__":
    main()
