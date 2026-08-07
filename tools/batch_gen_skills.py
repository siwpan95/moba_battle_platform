#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量 D&D 技能生成器。
根据英雄名 + role 从 role_dnd_templates.json 模板生成 4 技能 JSON。
确保：骰入配额带、effects 命中 mechanics.py 别名、CD=[0,1,2,4]、D&D 风味描述。
"""

import json
import random
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.skill_pool import write_hero_skill, pool_has

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), '_archive', 'role_dnd_templates.json')

# ── 技能名生成（D&D 风味） ──
SKILL_NAMES = {
    "assassin": {
        "Q": ["影袭", "暗杀突刺", "致命投掷", "毒刃", "暗影打击", "淬毒匕首", "割喉", "暗影步袭"],
        "W": ["暗影飞刀", "毒镖连射", "影缝", "暗器连掷", "暗影穿刺", "飞镰掷", "投刃"],
        "E": ["影遁", "暗影位移", "烟雾弹", "暗影步", "潜行突进", "幻影闪避", "暗影疾走"],
        "R": ["死亡印记", "暗杀绝技", "暗影裁决", "绝命一击", "暗影处决", "死神之舞", "暗影灭绝"],
    },
    "mage": {
        "Q": ["奥术飞弹", "火焰箭", "冰霜弹", "魔法弹", "元素射击", "秘法冲击", "闪电矢", "暗影弹"],
        "W": ["冰霜新星", "烈焰风暴", "重力场", "时间冻结", "暗影束缚", "奥术禁锢", "元素牢笼"],
        "E": ["闪现术", "火焰路径", "冰霜护甲", "魔力涌动", "相位转移", "元素位移", "奥术疾走"],
        "R": ["陨石术", "暴风雪", "奥术风暴", "元素浩劫", "时间扭曲", "暗影轰炸", "星陨"],
    },
    "marksman": {
        "Q": ["精准射击", "穿刺箭", "连珠箭", "瞄准射击", "致命一箭", "狙击", "破甲弹"],
        "W": ["陷阱布置", "捕兽夹", "束缚箭", "减速陷阱", "粘性炸弹", "冰霜陷阱", "缠绕弹"],
        "E": ["后跳射击", "翻滚闪避", "疾风步", "闪避突进", "滑步射击", "翻滚换弹", "疾跑"],
        "R": ["致命狙杀", "弹幕射击", "终极瞄准", "穿心箭", "毁灭射击", "全弹发射", "狙击绝杀"],
    },
    "fighter": {
        "Q": ["重击", "猛击", "旋风斩", "顺劈斩", "力量打击", "碎甲击", "雷霆一击"],
        "W": ["战斗怒吼", "防御姿态", "格挡反击", "钢铁意志", "战争践踏", "不屈战吼", "坚韧壁垒"],
        "E": ["冲锋", "英勇飞跃", "狂暴突进", "战意冲锋", "嗜血冲刺", "无畏突进", "战士跃击"],
        "R": ["狂暴", "战神降临", "决斗挑战", "不屈之魂", "终极战吼", "毁灭打击", "战神附体"],
    },
    "tank": {
        "Q": ["盾击", "嘲讽打击", "钩镰", "粉碎打击", "震荡波", "锁链拖拽", "巨力撞击"],
        "W": ["铁壁", "不坏金身", "坚韧护盾", "石肤术", "钢铁之躯", "防御壁垒", "不屈之盾"],
        "E": ["地震践踏", "裂地猛击", "震荡冲击", "巨石投掷", "范围嘲讽", "粉碎震荡", "雷霆践踏"],
        "R": ["不动如山", "大地之怒", "巨像降临", "终极守护", "山崩地裂", "钢铁要塞", "宏伟屏障"],
    },
    "support": {
        "Q": ["圣光弹", "治愈之光", "信仰之矢", "神圣射击", "光明冲击", "星光弹", "祈福弹"],
        "W": ["治愈祷言", "神圣庇护", "生命之泉", "圣疗术", "群体治疗", "守护之光", "神圣护盾"],
        "E": ["祝福术", "净化光环", "信仰之盾", "神圣强化", "驱魔仪式", "光辉祝福", "圣洁光环"],
        "R": ["神圣降临", "天使之翼", "奇迹之光", "终极守护", "圣域", "救赎之光", "神圣结界"],
    },
}

# ── D&D 风味描述模板 ──
DESC_TEMPLATES = {
    "assassin": {
        "Q": "以迅雷之势发动近战打击。在阴影中淬炼的利刃直取要害。",
        "W": "投掷淬毒暗器，精准命中远方目标。暗杀者的远程绝技。",
        "E": "身形一闪，化作暗影穿行于战场。刺客赖以生存的位移身法。",
        "R": "锁定猎物，释放致命连击。暗影之力凝于一点，一击必杀。",
    },
    "mage": {
        "Q": "凝聚元素之力，向前方发射魔法弹幕。基础但致命的法术攻击。",
        "W": "在目标区域引发元素爆发，将敌人禁锢于魔法牢笼之中。",
        "E": "以魔力扭曲空间，瞬间转移自身位置。法师的保命位移法术。",
        "R": "召唤天外陨石/暴风雪/元素风暴，对广大区域造成毁灭性打击。",
    },
    "marksman": {
        "Q": "拉满弓弦/瞄准镜，射出一发精准的远距离打击。射手的核心输出技。",
        "W": "在脚下布置陷阱/束缚装置。踩中的敌人将寸步难行。",
        "E": "快速后撤/翻滚，与敌人拉开距离。射手赖以生存的保命位移。",
        "R": "锁定目标，射出决定性的一击/弹幕。射手的最强终结技。",
    },
    "fighter": {
        "Q": "挥舞武器发动沉重打击。战士的近身搏杀之本。",
        "W": "摆出防御姿态，提升自身韧性。战斗中的生存之道。",
        "E": "向目标发起冲锋/跳跃。战士切入战场的突进技。",
        "R": "激发全部战意，进入狂暴/强化状态。战士的终极战斗形态。",
    },
    "tank": {
        "Q": "以盾牌/重武器猛击敌人，附加控制效果。坦克的控场起手式。",
        "W": "激活防御技能，大幅提升伤害减免/生成护盾。坦克的生存核心。",
        "E": "猛击地面造成范围冲击，削弱周围敌人。坦克的群体压制技。",
        "R": "释放全部防御/控制潜能，化身不可撼动的堡垒。坦克的终极团战技。",
    },
    "support": {
        "Q": "发射圣光弹幕攻击敌人。辅助的基础远程骚扰手段。",
        "W": "吟唱治疗祷言/释放护盾，为盟友提供生命恢复或伤害吸收。",
        "E": "施加祝福/净化，强化盟友属性或清除负面效果。辅助的增益核心。",
        "R": "召唤神圣领域/天使庇护，为大范围盟友提供强力保护与治疗。",
    },
}


def load_template():
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def pick_skill_name(role: str, slot: str, seed: int) -> str:
    names = SKILL_NAMES.get(role, {}).get(slot, ["技能"])
    return names[seed % len(names)]


def gen_skills_for_hero(hero_name: str, role: str, seed: int = 0,
                        signature_effects: dict = None) -> list:
    """为一个英雄生成 4 技能列表。
    
    Args:
        hero_name: 英雄名
        role: assassin/mage/marksman/fighter/tank/support
        seed: 确定性随机种子
        signature_effects: {slot: [effects]} 自定义效果，如 {"Q": ["dot"], "R": ["execute"]}
    """
    tmpl = load_template()
    if role not in tmpl:
        raise ValueError(f"Unknown role: {role}. Must be one of {list(tmpl.keys())}")

    role_tmpl = tmpl[role]
    slots_order = ["Q", "W", "E", "R"]
    signature = signature_effects or {}

    skills = []
    for i, slot in enumerate(slots_order):
        slot_tmpl = role_tmpl["slots"][slot]
        rng = random.Random(f"{hero_name}_{slot}_{seed}")

        # 基础数据
        skill = {
            "name": pick_skill_name(role, slot, seed + i),
            "key": slot,
            "type": "物理" if role in ("assassin", "marksman", "fighter", "tank") else "法术",
            "damage": dict(slot_tmpl["damage"]),
            "cooldown": slot_tmpl["cooldown"],
            "description": DESC_TEMPLATES[role][slot],
            "range": slot_tmpl["range"],
            "target": slot_tmpl["target"],
            "action": role_tmpl.get("action_default", "动作"),
        }

        # 添加 effects
        effects = []
        if slot in signature:
            for eff_type in signature[slot]:
                effects.append(make_effect(eff_type, role, slot))
        elif slot_tmpl.get("effects_hint"):
            # 从 hints 中选 1 个
            hints = slot_tmpl["effects_hint"]
            if "必选" in str(hints):
                # 解析必选项
                if "control" in str(hints) and role in ("mage", "tank"):
                    effects.append(make_effect("control", role, slot))
                elif "heal" in str(hints) or "shield" in str(hints):
                    if "heal" in str(hints):
                        effects.append(make_effect("heal", role, slot))
                    if "shield" in str(hints):
                        effects.append(make_effect("shield", role, slot))
                elif "accel" in str(hints):
                    effects.append(make_effect("accel", role, slot))
                elif "reduce" in str(hints) or "shield" in str(hints):
                    effects.append(make_effect("shield" if "shield" in str(hints) else "reduce", role, slot))
                elif "vuln" in str(hints):
                    effects.append(make_effect("vuln", role, slot))
                elif "invis" in str(hints):
                    effects.append(make_effect("invis", role, slot))
                elif "buff" in str(hints):
                    effects.append(make_effect("buff", role, slot))
                elif "execute" in str(hints):
                    effects.append(make_effect("execute", role, slot))
        if not effects and role_tmpl.get("common_effects"):
            # 随机选一个 common effect
            common = role_tmpl["common_effects"]
            chosen = common[(seed + i) % len(common)]
            effects.append(make_effect(chosen, role, slot))

        if effects:
            skill["effects"] = effects

        # 添加 saving_throw
        if slot_tmpl.get("saving_throw_hint") and "通常无" not in str(slot_tmpl["saving_throw_hint"]):
            st_attr = role_tmpl.get("saving_throw_attr_default", "DEX")
            st_primary = role_tmpl.get("primary_attr", "STR")
            skill["saving_throw"] = {
                "attr": st_attr,
                "dc_formula": f"8+PROF+{st_primary}",
                "on_save": "半伤"
            }

        skills.append(skill)

    return skills


def make_effect(eff_type: str, role: str, slot: str) -> dict:
    """根据 effects 类型生成规范 effect dict。"""
    effect_map = {
        "control": {"type": "眩晕", "desc": "使目标眩晕，失去行动能力", "duration": 1, "target": "敌方"},
        "slow": {"type": "减速", "desc": "降低目标移动速度", "duration": 2, "target": "敌方"},
        "shield": {"type": "护盾", "desc": "生成临时伤害吸收护盾", "duration": 2, "target": "自身"},
        "reduce": {"type": "减伤", "desc": "减少受到的伤害", "duration": 2, "target": "自身"},
        "heal": {"type": "治疗", "desc": "恢复生命值", "duration": 0, "target": "自身"},
        "dot": {"type": "灼烧", "desc": "持续受到火焰伤害", "duration": 2, "target": "敌方"},
        "execute": {"type": "处决", "desc": "对低血量目标造成额外伤害", "duration": 0, "target": "敌方"},
        "buff": {"type": "增益", "desc": "提升自身攻击力", "duration": 2, "target": "自身"},
        "accel": {"type": "加速", "desc": "提升移动和攻击速度", "duration": 2, "target": "自身"},
        "sunder": {"type": "破甲", "desc": "降低目标防御力", "duration": 2, "target": "敌方"},
        "vuln": {"type": "标记", "desc": "标记目标，使其受到额外伤害", "duration": 2, "target": "敌方"},
        "invis": {"type": "隐身", "desc": "进入隐身状态", "duration": 1, "target": "自身"},
        "reflect": {"type": "反弹", "desc": "反弹部分受到的伤害", "duration": 2, "target": "自身"},
        "immune": {"type": "免疫控制", "desc": "免疫控制效果", "duration": 1, "target": "自身"},
        "cleanse": {"type": "净化", "desc": "清除负面效果", "duration": 0, "target": "自身"},
        "lifesteal": {"type": "吸血", "desc": "攻击时回复生命", "duration": 2, "target": "自身"},
    }
    return effect_map.get(eff_type, {"type": eff_type, "desc": f"{eff_type}效果", "duration": 1, "target": "敌方"})


def append_heroes(game_id: str, heroes: dict, dry_run: bool = False):
    """追加英雄技能到技能池。

    Args:
        game_id: 如 'honor_of_kings'
        heroes: {英雄名: role} 或 {英雄名: {"role": ..., "signature": {...}}}

    每个英雄独立写入 data/skills/<game_id>/<英雄名>.json（技能池模式）。
    """
    added = []
    for name, info in heroes.items():
        if pool_has(game_id, name):
            print(f"  SKIP: {name} (技能池已存在)")
            continue

        if isinstance(info, str):
            role = info
            sig = None
        else:
            role = info.get("role", "fighter")
            sig = info.get("signature", None)

        seed = hash(name) % 10000
        skills = gen_skills_for_hero(name, role, seed=seed, signature_effects=sig)
        if not dry_run:
            write_hero_skill(game_id, name, skills)
        added.append(name)
        print(f"  ADD: {name} ({role}) -> 技能池")

    if not dry_run and added:
        print(f"\n  写入 {len(added)} 新英雄到技能池 data/skills/{game_id}/")

    return added


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python batch_gen_skills.py <game_id> <heroes_json_file>")
        print("  heroes_json_file: {英雄名: role, ...}")
        sys.exit(1)

    game_id = sys.argv[1]
    heroes_file = sys.argv[2]

    with open(heroes_file, 'r', encoding='utf-8') as f:
        heroes = json.load(f)

    dry = "--dry-run" in sys.argv
    append_heroes(game_id, heroes, dry_run=dry)
