#!/usr/bin/env python3
"""Batch 2: Generate 30 heroes (fighter 16 + assassin 5 + mage 9) for LoL."""
import json, sys, os

TEMPLATES = json.load(open(os.path.join(os.path.dirname(__file__), 'role_dnd_templates.json'), 'r', encoding='utf-8'))
SKILLS_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'skills', 'league_of_legends.json')

def make_skill(key, name, role_tmpl, custom=None):
    """Apply role template for slot, then overlay custom."""
    c = custom or {}
    slot = role_tmpl['slots'][key]
    
    # Merge damage overrides: custom["damage"] dict takes precedence over top-level keys
    dmg_override = {}
    if "damage" in c:
        dmg_override = c["damage"]
    # Top-level keys override merged dict
    for k in ("dice_count", "dice_size", "bonus_attr", "damage_type"):
        if k in c:
            if k == "damage_type":
                dmg_override["type"] = c[k]
            else:
                dmg_override[k] = c[k]
    
    damage = {
        "dice_count": dmg_override.get("dice_count", slot['damage']['dice_count']),
        "dice_size": dmg_override.get("dice_size", slot['damage']['dice_size']),
        "bonus_attr": dmg_override.get("bonus_attr", slot['damage']['bonus_attr']),
        "type": dmg_override.get("type", slot['damage']['type'])
    }
    
    # Generate description dynamically
    dc, ds, ba, dt = damage["dice_count"], damage["dice_size"], damage["bonus_attr"], damage["type"]
    if dc == 0:
        desc_base = "无直接伤害。"
    else:
        desc_base = f"{dc}d{ds}+{ba} {dt}伤害。"
    
    skill = {
        "name": c.get("name", f"{key}技能"),
        "key": key,
        "type": c.get("type", "物理" if role_tmpl['primary_attr'] in ('STR','DEX') else "法术"),
        "action": c.get("action", role_tmpl.get('action_default', '动作')),
        "range": c.get("range", slot['range']),
        "target": c.get("target", slot['target']),
        "damage": damage,
        "effects": c.get("effects", []),
        "cooldown": c.get("cooldown", slot['cooldown']),
        "description": c.get("description", desc_base)
    }
    if c.get("aoe_radius"):
        skill["aoe_radius"] = c["aoe_radius"]
    if c.get("saving_throw"):
        skill["saving_throw"] = c["saving_throw"]
    elif 'saving_throw_hint' in slot and '无' not in str(slot.get('saving_throw_hint','')):
        st = {
            "attr": c.get("st_attr", role_tmpl.get('saving_throw_attr_default', 'CON')),
            "dc_formula": f"8+PROF+{damage['bonus_attr']}",
            "on_save": c.get("on_save", "半伤")
        }
        skill["saving_throw"] = st
    return skill

# ── BATCH 2 HERO DEFINITIONS ──
# Format: (hero_name, role, [Q_custom, W_custom, E_custom, R_custom])
# Each custom dict overrides template defaults

BATCH2 = [
    # ═══ FIGHTERS (16) ═══
    ("安蓓萨", "fighter", [
        {"name":"狡黠横扫", "effects":[{"type":"sunder","desc":"龙犬刀刃命中降低目标护甲","duration":1,"target":"敌方"}]},
        {"name":"拒斥", "effects":[{"type":"shield","desc":"获得临时护盾吸收伤害","duration":1,"value":50,"target":"自身"},{"type":"reduce","desc":"格挡期间受伤减半","duration":1,"target":"自身"}], "range":"自身", "target":"自身"},
        {"name":"撕裂", "effects":[{"type":"slow","desc":"锁链拖拽减速","duration":1,"target":"敌方"},{"type":"accel","desc":"施放后可短距冲刺","target":"自身"}], "damage_type":"挥砍"},
        {"name":"公开处刑", "effects":[{"type":"control","desc":"压制目标并眩晕","duration":1,"target":"敌方"},{"type":"accel","desc":"闪现至目标身后","target":"自身"}], "dice_count":2, "dice_size":10, "saving_throw":{"attr":"CON","dc_formula":"8+PROF+STR","on_save":"半伤"}},
    ]),
    ("卑尔维斯", "fighter", [
        {"name":"虚空激流", "effects":[{"type":"accel","desc":"四向冲刺穿过敌人","target":"自身"}], "damage_type":"挥砍"},
        {"name":"上觐沉渊", "effects":[{"type":"control","desc":"尾击击飞敌人","duration":1,"target":"敌方"},{"type":"slow","desc":"落地后减速","duration":1,"target":"敌方"}], "target":"范围", "saving_throw":{"attr":"CON","dc_formula":"8+PROF+STR","on_save":"无效"}, "aoe_radius":15},
        {"name":"搠面皇锋", "effects":[{"type":"lifesteal","desc":"风暴切割回复生命","duration":1,"target":"自身"},{"type":"reduce","desc":"引导期间受到伤害减半","duration":1,"target":"自身"}], "range":"近战", "target":"范围", "aoe_radius":10},
        {"name":"万载豪筵", "effects":[{"type":"buff","desc":"真身形态，攻击范围与速度提升","duration":3,"target":"自身"},{"type":"execute","desc":"吞噬虚空珊瑚引爆真实伤害","threshold":25,"target":"敌方"}], "dice_count":3, "dice_size":8},
    ]),
    ("布蕾尔", "fighter", [
        {"name":"冲颅", "effects":[{"type":"accel","desc":"跃向目标并击退","target":"自身"},{"type":"sunder","desc":"击碎护甲","duration":1,"target":"敌方"}], "range":"近战"},
        {"name":"血莽", "effects":[{"type":"buff","desc":"进入狂暴，攻速与移速大幅提升","duration":2,"target":"自身"},{"type":"lifesteal","desc":"攻击回复生命","duration":2,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"挥砍"},
        {"name":"恐吓尖啸", "effects":[{"type":"control","desc":"恐惧周围敌人","duration":1,"target":"敌方"},{"type":"reduce","desc":"尖啸期间受到伤害减半","duration":1,"target":"自身"}], "range":"近战", "target":"范围", "aoe_radius":15, "saving_throw":{"attr":"WIS","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"必死无疑", "effects":[{"type":"accel","desc":"全图冲锋飞踢","target":"自身"},{"type":"control","desc":"命中后恐惧周围敌人","duration":1,"target":"敌方"}], "dice_count":3, "dice_size":8, "range":"远程", "saving_throw":{"attr":"WIS","dc_formula":"8+PROF+STR","on_save":"无效"}},
    ]),
    ("黛安娜", "fighter", [
        {"name":"新月打击", "effects":[{"type":"dot","desc":"月光灼烧标记","duration":2,"target":"敌方"}], "range":"远程", "damage_type":"力场", "bonus_attr":"INT", "damage":{"dice_count":1,"dice_size":10,"bonus_attr":"INT","type":"力场"}},
        {"name":"苍白之瀑", "effects":[{"type":"shield","desc":"三颗法球环绕获得护盾","duration":2,"value":30,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"力场", "bonus_attr":"INT"},
        {"name":"月之降临", "effects":[{"type":"control","desc":"将周围敌人拉向自身","duration":1,"target":"敌方"},{"type":"slow","desc":"拉拽后减速","duration":1,"target":"敌方"}], "target":"范围", "aoe_radius":20, "damage_type":"力场", "bonus_attr":"INT", "saving_throw":{"attr":"STR","dc_formula":"8+PROF+INT","on_save":"无效"}},
        {"name":"月神冲刺", "effects":[{"type":"accel","desc":"突进至标记目标身旁","target":"自身"},{"type":"buff","desc":"月银之力强化下次攻击","duration":1,"target":"自身"}], "dice_count":2,"dice_size":10,"damage_type":"力场","bonus_attr":"INT"},
    ]),
    ("普朗克", "fighter", [
        {"name":"枪火谈判", "effects":[{"type":"execute","desc":"暴击时附带额外真实伤害","threshold":30,"target":"敌方"}], "range":"远程", "damage_type":"穿刺"},
        {"name":"坏血病疗法", "effects":[{"type":"heal","desc":"吃橘子清除负面状态并回复生命","value":20,"target":"自身"},{"type":"cleanse","desc":"移除所有负面效果","target":"自身"}], "range":"自身", "target":"自身", "damage_type":"挥砍"},
        {"name":"火药桶", "effects":[{"type":"sunder","desc":"连环爆炸破甲","duration":1,"target":"敌方"},{"type":"slow","desc":"爆炸减速","duration":1,"target":"敌方"}], "target":"范围", "aoe_radius":15, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+STR","on_save":"半伤"}},
        {"name":"加农炮幕", "effects":[{"type":"slow","desc":"炮火覆盖区域减速","duration":2,"target":"敌方"},{"type":"dot","desc":"持续炮击灼烧","duration":2,"target":"敌方"}], "dice_count":3,"dice_size":8, "range":"远程", "target":"范围", "aoe_radius":25, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+STR","on_save":"半伤"}},
    ]),
    ("古拉加斯", "fighter", [
        {"name":"滚动酒桶", "effects":[{"type":"slow","desc":"酒桶发酵后伤害提升并减速","duration":1,"target":"敌方"}], "range":"远程", "damage_type":"钝击", "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+STR","on_save":"半伤"}},
        {"name":"醉酒狂暴", "effects":[{"type":"reduce","desc":"饮酒减伤","duration":1,"target":"自身"},{"type":"buff","desc":"下次攻击伤害提升","duration":1,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"钝击"},
        {"name":"肉弹冲击", "effects":[{"type":"accel","desc":"肚皮冲撞穿越战场","target":"自身"},{"type":"control","desc":"撞击眩晕","duration":1,"target":"敌方"}], "saving_throw":{"attr":"CON","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"爆破酒桶", "effects":[{"type":"control","desc":"巨型酒桶炸飞所有敌人","duration":1,"target":"敌方"}], "dice_count":2,"dice_size":10, "target":"范围", "aoe_radius":20, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+STR","on_save":"半伤"}},
    ]),
    ("格温", "fighter", [
        {"name":"快刀乱剪", "effects":[{"type":"execute","desc":"中心区真实伤害","threshold":50,"target":"敌方"},{"type":"sunder","desc":"剪刀撕裂护甲","duration":1,"target":"敌方"}], "range":"近战", "damage_type":"挥砍"},
        {"name":"圣霭", "effects":[{"type":"immune","desc":"霭外敌人无法选中格温","duration":2,"target":"自身"},{"type":"shield","desc":"圣霭护体","duration":2,"value":30,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"力场", "bonus_attr":"INT"},
        {"name":"断续疾走", "effects":[{"type":"accel","desc":"短距冲刺并提升攻速","duration":1,"target":"自身"}], "damage_type":"挥砍"},
        {"name":"穿针引线", "effects":[{"type":"dot","desc":"圣针穿透持续伤害","duration":2,"target":"敌方"},{"type":"heal","desc":"针线回收治疗","value":15,"target":"自身"}], "dice_count":3,"dice_size":8, "damage_type":"力场", "bonus_attr":"INT", "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"}},
    ]),
    ("赫卡里姆", "fighter", [
        {"name":"暴走", "effects":[{"type":"buff","desc":"连续使用伤害叠加","duration":2,"target":"自身"}], "range":"近战", "target":"范围", "aoe_radius":10},
        {"name":"恐惧之灵", "effects":[{"type":"dot","desc":"灵焰光环灼烧周围敌人","duration":2,"target":"敌方"},{"type":"heal","desc":"吸取生命回复自身","value":10,"target":"自身"}], "range":"近战", "target":"范围", "aoe_radius":15, "damage_type":"力场", "bonus_attr":"INT"},
        {"name":"毁灭冲锋", "effects":[{"type":"accel","desc":"蓄力冲锋速度飙升","target":"自身"},{"type":"control","desc":"撞击击退敌人","duration":1,"target":"敌方"}], "saving_throw":{"attr":"STR","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"暗影冲击", "effects":[{"type":"control","desc":"幽灵骑兵冲锋恐惧所有路径敌人","duration":1,"target":"敌方"},{"type":"accel","desc":"率领幽灵骑兵长距离冲锋","target":"自身"}], "dice_count":2,"dice_size":10, "target":"范围", "range":"远程", "aoe_radius":30, "saving_throw":{"attr":"WIS","dc_formula":"8+PROF+STR","on_save":"无效"}},
    ]),
    ("俄洛伊", "fighter", [
        {"name":"触手猛击", "effects":[{"type":"heal","desc":"触手命中回复生命","value":10,"target":"自身"}], "range":"近战", "target":"范围", "aoe_radius":15},
        {"name":"严苛惩戒", "effects":[{"type":"buff","desc":"下次攻击命令所有触手拍击","duration":1,"target":"自身"}], "damage_type":"钝击"},
        {"name":"灵魂试炼", "effects":[{"type":"vuln","desc":"抽出灵魂，对灵魂的伤害传递至本体","duration":2,"target":"敌方"},{"type":"slow","desc":"灵魂被抽出后减速","duration":1,"target":"敌方"}], "range":"远程", "saving_throw":{"attr":"WIS","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"信仰之跃", "effects":[{"type":"buff","desc":"召唤大量触手环绕","duration":3,"target":"自身"},{"type":"heal","desc":"触手攻击回复生命","duration":3,"value":10,"target":"自身"}], "dice_count":3,"dice_size":8, "target":"范围", "aoe_radius":20, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+STR","on_save":"半伤"}},
    ]),
    ("嘉文四世", "fighter", [
        {"name":"巨龙撞击", "effects":[{"type":"sunder","desc":"长枪穿透降低护甲","duration":1,"target":"敌方"}], "range":"远程", "damage_type":"穿刺"},
        {"name":"黄金圣盾", "effects":[{"type":"shield","desc":"圣盾光环护体","duration":2,"value":30,"target":"自身"},{"type":"slow","desc":"光环减速周围敌人","duration":1,"target":"敌方"}], "range":"自身", "target":"范围", "aoe_radius":15, "damage_type":"力场", "bonus_attr":"INT"},
        {"name":"德邦军旗", "effects":[{"type":"accel","desc":"掷出军旗，可再次激活突进军旗处","target":"自身"},{"type":"buff","desc":"军旗光环提升友军攻速","duration":2,"target":"自身"}], "range":"远程", "damage_type":"穿刺"},
        {"name":"天崩地裂", "effects":[{"type":"control","desc":"跃起砸地形成环形壁垒困住敌人","duration":2,"target":"敌方"}], "dice_count":2,"dice_size":10, "target":"范围", "aoe_radius":20, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+STR","on_save":"半伤"}},
    ]),
    ("凯尔", "fighter", [
        {"name":"耀焰冲击", "effects":[{"type":"sunder","desc":"圣焰撕裂护甲与魔抗","duration":1,"target":"敌方"},{"type":"slow","desc":"圣焰减速","duration":1,"target":"敌方"}], "range":"远程", "damage_type":"光耀", "bonus_attr":"INT"},
        {"name":"星降恩典", "effects":[{"type":"heal","desc":"圣光治疗自身与附近友军","value":15,"target":"自身"},{"type":"accel","desc":"治疗附带移速加成","duration":1,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"光耀", "bonus_attr":"INT"},
        {"name":"星火符刃", "effects":[{"type":"execute","desc":"星火处决低血量目标","threshold":20,"target":"敌方"}], "damage_type":"光耀", "bonus_attr":"INT"},
        {"name":"圣裁之刻", "effects":[{"type":"immune","desc":"神圣审判使目标无敌","duration":2,"target":"自身"},{"type":"buff","desc":"圣剑降临造成范围神圣伤害","duration":1,"target":"自身"}], "dice_count":3,"dice_size":8, "damage_type":"光耀", "bonus_attr":"INT", "target":"范围", "aoe_radius":20},
    ]),
    ("克烈", "fighter", [
        {"name":"飞索捕熊", "effects":[{"type":"control","desc":"捕熊夹拖拽目标","duration":1,"target":"敌方"},{"type":"dot","desc":"拖拽持续伤害","duration":1,"target":"敌方"}], "range":"远程", "saving_throw":{"attr":"STR","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"暴烈秉性", "effects":[{"type":"buff","desc":"第四击狂暴连斩伤害翻倍","duration":1,"target":"自身"}], "damage_type":"挥砍"},
        {"name":"比武", "effects":[{"type":"accel","desc":"短距冲刺","target":"自身"},{"type":"shield","desc":"冲刺获得护盾","duration":1,"value":20,"target":"自身"}], "range":"近战", "damage_type":"挥砍"},
        {"name":"冲啊啊啊", "effects":[{"type":"accel","desc":"全队冲锋加速","duration":2,"target":"自身"},{"type":"shield","desc":"冲锋形成护盾","duration":2,"value":40,"target":"自身"},{"type":"control","desc":"撞击首个敌人击退","duration":1,"target":"敌方"}], "dice_count":2,"dice_size":10, "range":"远程", "target":"范围"},
    ]),
    ("莉莉娅", "fighter", [
        {"name":"飞花挞", "effects":[{"type":"dot","desc":"梦境花粉持续伤害","duration":2,"target":"敌方"},{"type":"accel","desc":"命中后移速提升","duration":1,"target":"自身"}], "range":"近战", "target":"范围", "aoe_radius":15, "damage_type":"力场", "bonus_attr":"INT", "damage":{"dice_count":1,"dice_size":10,"bonus_attr":"INT","type":"力场"}},
        {"name":"流涡种", "effects":[{"type":"slow","desc":"种子爆炸减速","duration":1,"target":"敌方"}], "range":"远程", "damage_type":"力场", "bonus_attr":"INT", "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"}},
        {"name":"惊惶木", "effects":[{"type":"slow","desc":"投掷树枝减速","duration":1,"target":"敌方"},{"type":"dot","desc":"梦境粉尘标记","duration":2,"target":"敌方"}], "range":"远程", "damage_type":"力场", "bonus_attr":"INT"},
        {"name":"夜阑谣", "effects":[{"type":"control","desc":"催眠花粉使梦境标记目标沉睡","duration":1,"target":"敌方"}], "dice_count":3,"dice_size":8, "damage_type":"力场", "bonus_attr":"INT", "target":"范围", "range":"远程", "aoe_radius":25, "saving_throw":{"attr":"WIS","dc_formula":"8+PROF+INT","on_save":"无效"}},
    ]),
    ("魔腾", "fighter", [
        {"name":"黄沙之影", "effects":[{"type":"accel","desc":"影径上移速提升","duration":1,"target":"自身"},{"type":"buff","desc":"影径上攻击力提升","duration":1,"target":"自身"}], "range":"远程", "damage_type":"挥砍"},
        {"name":"黑暗庇护", "effects":[{"type":"shield","desc":"暗影护盾格挡一次技能","duration":1,"value":30,"target":"自身"},{"type":"buff","desc":"成功格挡后攻速翻倍","duration":2,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"力场", "bonus_attr":"INT"},
        {"name":"无言恐惧", "effects":[{"type":"control","desc":"噩梦锁链触发恐惧","duration":1,"target":"敌方"}], "range":"近战", "saving_throw":{"attr":"WIS","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"鬼影重重", "effects":[{"type":"accel","desc":"全图暗影冲锋","target":"自身"},{"type":"control","desc":"天昏地暗，剥夺所有敌人视野","duration":1,"target":"敌方"}], "dice_count":3,"dice_size":8, "range":"远程"},
    ]),
    ("雷克塞", "fighter", [
        {"name":"女王之怒", "effects":[{"type":"buff","desc":"三次撕咬攻速递增","duration":1,"target":"自身"}], "range":"近战", "target":"范围", "aoe_radius":10},
        {"name":"遁地/破土", "effects":[{"type":"invis","desc":"遁入地下潜行","target":"自身"},{"type":"control","desc":"破土而出击飞敌人","duration":1,"target":"敌方"}], "range":"自身", "target":"自身", "damage_type":"钝击"},
        {"name":"狂野之噬", "effects":[{"type":"execute","desc":"满怒时真实伤害翻倍","threshold":40,"target":"敌方"}], "damage_type":"穿刺"},
        {"name":"虚空猛冲", "effects":[{"type":"accel","desc":"锁定受伤目标远程突袭","target":"自身"},{"type":"execute","desc":"冲刺处决低血量目标","threshold":25,"target":"敌方"}], "dice_count":3,"dice_size":8, "range":"远程"},
    ]),
    ("兰博", "fighter", [
        {"name":"火焰喷射", "effects":[{"type":"dot","desc":"烈焰锥形灼烧","duration":1,"target":"敌方"}], "range":"近战", "target":"范围", "aoe_radius":15, "damage_type":"力场", "bonus_attr":"INT", "damage":{"dice_count":1,"dice_size":10,"bonus_attr":"INT","type":"力场"}},
        {"name":"破碎护盾", "effects":[{"type":"shield","desc":"机械护盾吸收伤害","duration":1,"value":30,"target":"自身"},{"type":"accel","desc":"护盾开启移速提升","duration":1,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"力场", "bonus_attr":"INT"},
        {"name":"电子鱼叉", "effects":[{"type":"slow","desc":"双发鱼叉减速叠加","duration":1,"target":"敌方"}], "range":"远程", "damage_type":"力场", "bonus_attr":"INT", "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"无效"}},
        {"name":"恒温灼烧", "effects":[{"type":"dot","desc":"火箭弹幕铺设火焰路径持续灼烧","duration":2,"target":"敌方"},{"type":"slow","desc":"火焰路径减速","duration":2,"target":"敌方"}], "dice_count":3,"dice_size":8, "damage_type":"力场", "bonus_attr":"INT", "range":"远程", "target":"范围", "aoe_radius":30, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"}},
    ]),
    # ═══ ASSASSINS (5) ═══
    ("卡萨丁", "assassin", [
        {"name":"虚无法球", "effects":[{"type":"shield","desc":"法球提供法术护盾","duration":1,"value":20,"target":"自身"},{"type":"control","desc":"打断目标施法","duration":1,"target":"敌方"}], "range":"远程", "damage_type":"力场", "damage":{"dice_count":1,"dice_size":10,"bonus_attr":"INT","type":"力场"}, "bonus_attr":"INT"},
        {"name":"虚空之刃", "effects":[{"type":"buff","desc":"下次普攻附带额外力场伤害","duration":1,"target":"自身"}], "damage_type":"力场", "bonus_attr":"INT"},
        {"name":"能量脉冲", "effects":[{"type":"slow","desc":"虚空能量锥形减速","duration":1,"target":"敌方"}], "range":"近战", "target":"范围", "aoe_radius":15, "damage_type":"力场", "bonus_attr":"INT", "saving_throw":{"attr":"CON","dc_formula":"8+PROF+INT","on_save":"半伤"}},
        {"name":"虚空行走", "effects":[{"type":"accel","desc":"短距闪烁位移","target":"自身"},{"type":"buff","desc":"连续使用伤害翻倍但消耗递增","duration":1,"target":"自身"}], "dice_count":3,"dice_size":6, "damage_type":"力场", "bonus_attr":"INT", "range":"远程", "target":"范围", "aoe_radius":15},
    ]),
    ("易大师", "assassin", [
        {"name":"阿尔法突袭", "effects":[{"type":"invis","desc":"化为不可选中状态斩击多名敌人","duration":1,"target":"自身"}], "target":"范围", "aoe_radius":20, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"半伤"}},
        {"name":"冥想", "effects":[{"type":"heal","desc":"引导回复大量生命","duration":1,"value":30,"target":"自身"},{"type":"reduce","desc":"引导期间受到伤害减半","duration":1,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"挥砍"},
        {"name":"无极剑道", "effects":[{"type":"buff","desc":"每次攻击附带额外真实伤害","duration":2,"target":"自身"}], "damage_type":"挥砍"},
        {"name":"高原血统", "effects":[{"type":"accel","desc":"移速攻速大幅提升","duration":3,"target":"自身"},{"type":"immune","desc":"免疫减速效果","duration":3,"target":"自身"}], "dice_count":3,"dice_size":6, "range":"自身", "target":"自身"},
    ]),
    ("娜菲芮", "assassin", [
        {"name":"暗裔匕首", "effects":[{"type":"dot","desc":"匕首投掷流血","duration":2,"target":"敌方"}], "range":"远程", "damage_type":"穿刺"},
        {"name":"血之追寻", "effects":[{"type":"accel","desc":"追踪血迹冲刺","target":"自身"},{"type":"vuln","desc":"标记目标","duration":1,"target":"敌方"}], "range":"远程", "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"半伤"}},
        {"name":"剔骨", "effects":[{"type":"accel","desc":"短距冲刺撕咬","target":"自身"}], "damage_type":"穿刺"},
        {"name":"群嗥", "effects":[{"type":"buff","desc":"召唤犬群协同攻击","duration":3,"target":"自身"},{"type":"shield","desc":"犬群提供护盾","duration":3,"value":40,"target":"自身"}], "dice_count":3,"dice_size":6},
    ]),
    ("奇亚娜", "assassin", [
        {"name":"伊克斯塔尔之刃", "effects":[{"type":"execute","desc":"边缘命中伤害翻倍","threshold":50,"target":"敌方"}], "range":"远程", "damage_type":"挥砍", "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"半伤"}},
        {"name":"方圆之器", "effects":[{"type":"buff","desc":"附魔武器：河流=束缚、墙壁=处决、草丛=隐身","duration":2,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"挥砍"},
        {"name":"勇往直前", "effects":[{"type":"accel","desc":"指定元素冲刺","target":"自身"}], "damage_type":"挥砍"},
        {"name":"大显身手", "effects":[{"type":"control","desc":"元素冲击波沿地形爆炸并眩晕","duration":1,"target":"敌方"},{"type":"dot","desc":"冲击波持续伤害","duration":1,"target":"敌方"}], "dice_count":4,"dice_size":6, "target":"范围", "range":"远程", "aoe_radius":25, "saving_throw":{"attr":"CON","dc_formula":"8+PROF+DEX","on_save":"半伤"}},
    ]),
    ("萨科", "assassin", [
        {"name":"欺诈魔术", "effects":[{"type":"invis","desc":"闪现隐身","duration":1,"target":"自身"},{"type":"buff","desc":"隐身期间下次攻击暴击","duration":1,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"穿刺"},
        {"name":"惊吓魔盒", "effects":[{"type":"control","desc":"魔盒恐惧周围敌人","duration":1,"target":"敌方"},{"type":"dot","desc":"魔盒持续射击","duration":2,"target":"敌方"}], "range":"远程", "saving_throw":{"attr":"WIS","dc_formula":"8+PROF+DEX","on_save":"无效"}},
        {"name":"双面毒刃", "effects":[{"type":"slow","desc":"飞刀减速","duration":1,"target":"敌方"},{"type":"execute","desc":"背刺时额外伤害","threshold":30,"target":"敌方"}], "range":"远程", "damage_type":"穿刺"},
        {"name":"幻象", "effects":[{"type":"invis","desc":"短暂消失后制造可控分身","duration":1,"target":"自身"},{"type":"buff","desc":"分身复制攻击并爆炸","duration":2,"target":"自身"}], "dice_count":3,"dice_size":6, "range":"自身", "target":"自身"},
    ]),
    # ═══ MAGES (9) ═══
    ("艾尼维亚", "mage", [
        {"name":"寒冰闪耀", "effects":[{"type":"control","desc":"冰晶飞行中再次激活可引爆眩晕","duration":1,"target":"敌方"},{"type":"slow","desc":"穿透减速","duration":1,"target":"敌方"}], "saving_throw":{"attr":"CON","dc_formula":"8+PROF+INT","on_save":"无效"}},
        {"name":"寒冰屏障", "effects":[{"type":"control","desc":"召唤不可通行的冰墙阻挡敌人","duration":2,"target":"敌方"}], "damage_type":"寒冷", "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"}},
        {"name":"霜寒刺骨", "effects":[{"type":"execute","desc":"对被冰冻目标伤害翻倍","threshold":0,"target":"敌方"}], "target":"单体"},
        {"name":"冰川风暴", "effects":[{"type":"dot","desc":"暴风雪持续造成寒冷伤害","duration":3,"target":"敌方"},{"type":"slow","desc":"暴风雪中移速攻速减半","duration":3,"target":"敌方"}], "dice_count":4,"dice_size":6, "target":"范围", "aoe_radius":25, "saving_throw":{"attr":"CON","dc_formula":"8+PROF+INT","on_save":"半伤"}},
    ]),
    ("奥瑞利安索尔", "mage", [
        {"name":"星穹流瀑", "effects":[{"type":"dot","desc":"星火持续喷吐，随引导时间伤害递增","duration":2,"target":"敌方"}], "target":"范围", "aoe_radius":20, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"}},
        {"name":"星界飞行", "effects":[{"type":"accel","desc":"腾空飞行穿越地形","duration":1,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"力场"},
        {"name":"奇点", "effects":[{"type":"control","desc":"黑洞吸引并拖拽敌人","duration":1,"target":"敌方"},{"type":"execute","desc":"黑洞中心处决低血量目标","threshold":15,"target":"敌方"}], "range":"远程", "saving_throw":{"attr":"STR","dc_formula":"8+PROF+INT","on_save":"无效"}},
        {"name":"星弦高落", "effects":[{"type":"control","desc":"陨星冲击波击退并眩晕","duration":1,"target":"敌方"},{"type":"dot","desc":"冲击波余震灼烧","duration":1,"target":"敌方"}], "dice_count":4,"dice_size":6, "target":"范围", "aoe_radius":30, "saving_throw":{"attr":"CON","dc_formula":"8+PROF+INT","on_save":"半伤"}},
    ]),
    ("奥罗拉", "mage", [
        {"name":"双重诅咒", "effects":[{"type":"dot","desc":"诅咒飞弹往返造成两次伤害","duration":1,"target":"敌方"},{"type":"heal","desc":"驱灵治疗自身","value":10,"target":"自身"}], "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"}},
        {"name":"穿越帷幕", "effects":[{"type":"invis","desc":"跃入灵界隐身","duration":1,"target":"自身"},{"type":"accel","desc":"灵界中移速提升","duration":1,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"力场"},
        {"name":"怪异术", "effects":[{"type":"slow","desc":"灵能冲击减速","duration":1,"target":"敌方"},{"type":"accel","desc":"施放后向后跳跃","target":"自身"}], "saving_throw":{"attr":"WIS","dc_formula":"8+PROF+INT","on_save":"半伤"}},
        {"name":"间界穿梭", "effects":[{"type":"control","desc":"灵界领域困住敌人","duration":2,"target":"敌方"},{"type":"accel","desc":"可在领域两端传送","duration":2,"target":"自身"}], "dice_count":4,"dice_size":6, "target":"范围", "aoe_radius":25, "saving_throw":{"attr":"WIS","dc_formula":"8+PROF+INT","on_save":"半伤"}},
    ]),
    ("阿兹尔", "mage", [
        {"name":"征服沙场", "effects":[{"type":"accel","desc":"命令所有沙兵冲锋","target":"自身"},{"type":"slow","desc":"沙兵冲锋减速","duration":1,"target":"敌方"}], "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"}},
        {"name":"沙兵现身", "effects":[{"type":"buff","desc":"召唤沙兵替代普攻进行远程穿刺","duration":3,"target":"自身"}], "damage_type":"穿刺", "range":"远程", "target":"单体"},
        {"name":"流沙移形", "effects":[{"type":"accel","desc":"位移至沙兵身旁","target":"自身"},{"type":"shield","desc":"位移获得护盾","duration":1,"value":25,"target":"自身"}], "damage_type":"力场"},
        {"name":"禁军之墙", "effects":[{"type":"control","desc":"召唤沙兵墙击退并阻挡所有敌人","duration":2,"target":"敌方"}], "dice_count":4,"dice_size":6, "target":"范围", "aoe_radius":25, "saving_throw":{"attr":"STR","dc_formula":"8+PROF+INT","on_save":"无效"}},
    ]),
    ("费德提克", "mage", [
        {"name":"恐惧", "effects":[{"type":"control","desc":"恐惧目标使其逃跑","duration":1,"target":"敌方"}], "target":"单体", "saving_throw":{"attr":"WIS","dc_formula":"8+PROF+INT","on_save":"无效"}},
        {"name":"生命吸取", "effects":[{"type":"lifesteal","desc":"持续吸取目标生命","duration":2,"value":15,"target":"自身"},{"type":"dot","desc":"吸取造成持续伤害","duration":2,"target":"敌方"}], "target":"单体", "saving_throw":{"attr":"CON","dc_formula":"8+PROF+INT","on_save":"半伤"}},
        {"name":"黑暗之风", "effects":[{"type":"control","desc":"沉默弹射多个目标","duration":1,"target":"敌方"}], "target":"范围", "saving_throw":{"attr":"WIS","dc_formula":"8+PROF+INT","on_save":"无效"}},
        {"name":"群鸦风暴", "effects":[{"type":"dot","desc":"乌鸦风暴环绕持续造成伤害","duration":3,"target":"敌方"},{"type":"accel","desc":"闪现引导乌鸦风暴","target":"自身"}], "dice_count":4,"dice_size":6, "target":"范围", "aoe_radius":25, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"}},
    ]),
    ("黑默丁格", "mage", [
        {"name":"炮台", "effects":[{"type":"dot","desc":"部署自动炮台持续射击","duration":3,"target":"敌方"}], "range":"远程", "target":"单体"},
        {"name":"海克斯科技火箭", "effects":[{"type":"dot","desc":"多枚火箭弹齐射","duration":1,"target":"敌方"}], "target":"范围", "aoe_radius":15, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"}},
        {"name":"手雷", "effects":[{"type":"control","desc":"震荡手雷中心区眩晕","duration":1,"target":"敌方"},{"type":"slow","desc":"手雷边缘减速","duration":1,"target":"敌方"}], "range":"远程", "saving_throw":{"attr":"CON","dc_formula":"8+PROF+INT","on_save":"无效"}},
        {"name":"升级", "effects":[{"type":"buff","desc":"强化下一个基础技能","duration":1,"target":"自身"}], "dice_count":0,"dice_size":0, "damage_type":"力场", "range":"自身", "target":"自身"},
    ]),
    ("彗", "mage", [
        {"name":"灾", "effects":[{"type":"dot","desc":"灾厄绘笔画出的火焰或闪电持续伤害","duration":1,"target":"敌方"}], "target":"范围", "aoe_radius":15, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"}},
        {"name":"靖", "effects":[{"type":"shield","desc":"静谧绘笔给予护盾","duration":1,"value":25,"target":"自身"},{"type":"accel","desc":"静谧绘笔提升移速","duration":1,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"力场"},
        {"name":"悚", "effects":[{"type":"control","desc":"恐惧绘笔造成恐惧或拉拽","duration":1,"target":"敌方"}], "range":"远程", "saving_throw":{"attr":"WIS","dc_formula":"8+PROF+INT","on_save":"无效"}},
        {"name":"焚心绚华绘", "effects":[{"type":"dot","desc":"绝望之种扩散持续伤害","duration":3,"target":"敌方"},{"type":"slow","desc":"绝望领域减速叠加","duration":3,"target":"敌方"}], "dice_count":4,"dice_size":6, "target":"范围", "aoe_radius":30, "saving_throw":{"attr":"WIS","dc_formula":"8+PROF+INT","on_save":"半伤"}},
    ]),
    ("卡尔玛", "mage", [
        {"name":"心灵烈焰", "effects":[{"type":"slow","desc":"灵能冲击减速","duration":1,"target":"敌方"}], "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"}},
        {"name":"坚定不移", "effects":[{"type":"control","desc":"灵链束缚目标","duration":1,"target":"敌方"},{"type":"heal","desc":"梵咒强化时治疗自身","value":15,"target":"自身"}], "target":"单体", "saving_throw":{"attr":"WIS","dc_formula":"8+PROF+INT","on_save":"无效"}},
        {"name":"鼓舞", "effects":[{"type":"shield","desc":"灵能护盾","duration":1,"value":25,"target":"自身"},{"type":"accel","desc":"护盾提供移速","duration":1,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"力场"},
        {"name":"梵咒", "effects":[{"type":"buff","desc":"强化下一个技能效果翻倍","duration":1,"target":"自身"}], "dice_count":0,"dice_size":0, "range":"自身", "target":"自身", "damage_type":"力场"},
    ]),
    ("凯南", "mage", [
        {"name":"雷缚印", "effects":[{"type":"vuln","desc":"手里剑施加雷缚标记","duration":2,"target":"敌方"}], "range":"远程", "damage_type":"力场", "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"}},
        {"name":"电子脉冲", "effects":[{"type":"dot","desc":"释放雷电脉冲打击标记目标","duration":1,"target":"敌方"}], "target":"范围", "aoe_radius":20, "damage_type":"力场"},
        {"name":"雷铠", "effects":[{"type":"accel","desc":"化身闪电获得极速","duration":1,"target":"自身"},{"type":"shield","desc":"闪电护甲","duration":1,"value":20,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"力场"},
        {"name":"秘奥义!万雷天牢引", "effects":[{"type":"dot","desc":"召唤雷暴环绕持续雷击","duration":3,"target":"敌方"},{"type":"control","desc":"三层雷缚触发眩晕","duration":1,"target":"敌方"}], "dice_count":4,"dice_size":6, "target":"范围", "aoe_radius":25, "saving_throw":{"attr":"CON","dc_formula":"8+PROF+INT","on_save":"半伤"}},
    ]),
]

def generate():
    output = {}
    for hero_name, role, customs in BATCH2:
        tmpl = TEMPLATES[role]
        skills = []
        for i, key in enumerate(["Q", "W", "E", "R"]):
            cust = customs[i] if i < len(customs) else {}
            # Handle bonus_attr override at hero level
            if "bonus_attr" in cust:
                # Move bonus_attr into damage
                pass  # handled in make_skill via custom
            skills.append(make_skill(key, hero_name, tmpl, cust))
        output[hero_name] = skills
    
    # Append to main JSON
    with open(SKILLS_PATH, 'r', encoding='utf-8') as f:
        main = json.load(f)
    
    for name, skills in output.items():
        main[name] = skills
    
    with open(SKILLS_PATH, 'w', encoding='utf-8') as f:
        json.dump(main, f, ensure_ascii=False, indent=2)
    
    print(f"Batch 2: Generated {len(output)} heroes ({sum(len(v) for v in output.values())} skills)")
    print(f"Heroes: {', '.join(output.keys())}")
    return output

if __name__ == '__main__':
    generate()
