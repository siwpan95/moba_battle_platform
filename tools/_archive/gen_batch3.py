#!/usr/bin/env python3
"""Batch 3: Generate 30 heroes (mage 12 + marksman 17 + support 1) for LoL."""
import json, sys, os

TEMPLATES = json.load(open(os.path.join(os.path.dirname(__file__), 'role_dnd_templates.json'), 'r', encoding='utf-8'))
SKILLS_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'skills', 'league_of_legends.json')

def make_skill(key, name, role_tmpl, custom=None):
    c = custom or {}
    slot = role_tmpl['slots'][key]
    dmg_override = {}
    if "damage" in c:
        dmg_override = c["damage"]
    for k in ("dice_count", "dice_size", "bonus_attr", "damage_type"):
        if k in c:
            if k == "damage_type": dmg_override["type"] = c[k]
            else: dmg_override[k] = c[k]
    damage = {
        "dice_count": dmg_override.get("dice_count", slot['damage']['dice_count']),
        "dice_size": dmg_override.get("dice_size", slot['damage']['dice_size']),
        "bonus_attr": dmg_override.get("bonus_attr", slot['damage']['bonus_attr']),
        "type": dmg_override.get("type", slot['damage']['type'])
    }
    dc, ds, ba, dt = damage["dice_count"], damage["dice_size"], damage["bonus_attr"], damage["type"]
    desc_base = "无直接伤害。" if dc == 0 else f"{dc}d{ds}+{ba} {dt}伤害。"
    skill = {
        "name": c.get("name", f"{key}技能"), "key": key,
        "type": c.get("type", "物理" if role_tmpl['primary_attr'] in ('STR','DEX') else "法术"),
        "action": c.get("action", role_tmpl.get('action_default', '动作')),
        "range": c.get("range", slot['range']),
        "target": c.get("target", slot['target']),
        "damage": damage,
        "effects": c.get("effects", []),
        "cooldown": c.get("cooldown", slot['cooldown']),
        "description": c.get("description", desc_base)
    }
    if c.get("aoe_radius"): skill["aoe_radius"] = c["aoe_radius"]
    if c.get("saving_throw"):
        skill["saving_throw"] = c["saving_throw"]
    elif 'saving_throw_hint' in slot and '无' not in str(slot.get('saving_throw_hint','')):
        skill["saving_throw"] = {
            "attr": c.get("st_attr", role_tmpl.get('saving_throw_attr_default', 'CON')),
            "dc_formula": f"8+PROF+{damage['bonus_attr']}",
            "on_save": c.get("on_save", "半伤")
        }
    return skill

BATCH3 = [
    # ═══ MAGES (12) ═══
    ("玛尔扎哈", "mage", [
        {"name":"虚空召唤", "effects":[{"type":"control","desc":"虚空之门沉默路径敌人","duration":1,"target":"敌方"}], "saving_throw":{"attr":"CON","dc_formula":"8+PROF+INT","on_save":"无效"}},
        {"name":"虚无盲区", "effects":[{"type":"dot","desc":"虚空池百分比灼烧生命","duration":2,"target":"敌方"}], "target":"范围", "aoe_radius":15, "saving_throw":{"attr":"CON","dc_formula":"8+PROF+INT","on_save":"半伤"}},
        {"name":"煞星幻象", "effects":[{"type":"dot","desc":"瘟疫幻象持续感染，击杀后传播","duration":2,"target":"敌方"}], "saving_throw":{"attr":"CON","dc_formula":"8+PROF+INT","on_save":"半伤"}},
        {"name":"冥府之握", "effects":[{"type":"control","desc":"压制目标使其完全失去行动","duration":2,"target":"敌方"},{"type":"dot","desc":"虚空能量持续侵蚀","duration":2,"target":"敌方"}], "target":"单体", "saving_throw":{"attr":"WIS","dc_formula":"8+PROF+INT","on_save":"无效"}},
    ]),
    ("莫甘娜", "mage", [
        {"name":"暗之禁锢", "effects":[{"type":"control","desc":"暗影法球捆缚目标","duration":1,"target":"敌方"}], "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"无效"}},
        {"name":"痛苦腐蚀", "effects":[{"type":"dot","desc":"诅咒之地持续腐蚀","duration":2,"target":"敌方"}], "target":"范围", "aoe_radius":15, "saving_throw":{"attr":"CON","dc_formula":"8+PROF+INT","on_save":"半伤"}},
        {"name":"黑暗之盾", "effects":[{"type":"shield","desc":"黑盾吸收魔法伤害并免疫控制","duration":2,"value":30,"target":"自身"},{"type":"cleanse","desc":"免疫控制效果","duration":2,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"力场"},
        {"name":"灵魂镣铐", "effects":[{"type":"control","desc":"灵魂锁链链接周围敌人，延迟眩晕","duration":1,"target":"敌方"},{"type":"slow","desc":"锁链持续减速","duration":2,"target":"敌方"}], "target":"范围", "aoe_radius":25, "saving_throw":{"attr":"WIS","dc_formula":"8+PROF+INT","on_save":"半伤"}},
    ]),
    ("妮蔻", "mage", [
        {"name":"盛开花种", "effects":[{"type":"dot","desc":"花种绽放可重复触发","duration":1,"target":"敌方"}], "target":"范围", "aoe_radius":15, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"}},
        {"name":"两生花影", "effects":[{"type":"invis","desc":"短暂隐身并制造分身迷惑敌人","duration":1,"target":"自身"},{"type":"accel","desc":"分身期间移速提升","duration":1,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"力场"},
        {"name":"缠结倒刺", "effects":[{"type":"control","desc":"魔法漩涡禁锢路径敌人","duration":1,"target":"敌方"}], "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"无效"}},
        {"name":"怒放", "effects":[{"type":"shield","desc":"引导期间获得护盾","duration":1,"value":40,"target":"自身"},{"type":"control","desc":"跃起落地造成范围眩晕","duration":1,"target":"敌方"}], "dice_count":4,"dice_size":6, "target":"范围", "aoe_radius":25, "saving_throw":{"attr":"CON","dc_formula":"8+PROF+INT","on_save":"半伤"}},
    ]),
    ("萨勒芬妮", "mage", [
        {"name":"清籁穿云", "effects":[{"type":"execute","desc":"低血量目标额外伤害","threshold":25,"target":"敌方"}], "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"}},
        {"name":"聚和心声", "effects":[{"type":"shield","desc":"音波护盾保护友军","duration":1,"value":25,"target":"自身"},{"type":"heal","desc":"和声治疗附近友军","duration":1,"value":15,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"光耀"},
        {"name":"增幅节拍", "effects":[{"type":"slow","desc":"音波减速","duration":1,"target":"敌方"},{"type":"control","desc":"对已减速目标造成禁锢","duration":1,"target":"敌方"}], "saving_throw":{"attr":"WIS","dc_formula":"8+PROF+INT","on_save":"无效"}},
        {"name":"炫音返场", "effects":[{"type":"control","desc":"音浪魅惑路径上所有敌人","duration":1,"target":"敌方"},{"type":"buff","desc":"为路径友军提供增益","duration":2,"target":"自身"}], "dice_count":4,"dice_size":6, "target":"范围", "range":"远程", "aoe_radius":35, "saving_throw":{"attr":"WIS","dc_formula":"8+PROF+INT","on_save":"无效"}},
    ]),
    ("斯维因", "mage", [
        {"name":"死亡之手", "effects":[{"type":"dot","desc":"恶魔闪电链穿透","duration":1,"target":"敌方"}], "target":"范围", "aoe_radius":15, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"}},
        {"name":"帝国视界", "effects":[{"type":"slow","desc":"恶魔之眼远程减速并揭示","duration":1,"target":"敌方"}], "saving_throw":{"attr":"WIS","dc_formula":"8+PROF+INT","on_save":"无效"}},
        {"name":"永不复行", "effects":[{"type":"control","desc":"恶魔之手抓回并禁锢","duration":1,"target":"敌方"}], "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"无效"}},
        {"name":"恶魔升华", "effects":[{"type":"buff","desc":"变身为恶魔形态，持续吸取周围生命","duration":3,"target":"自身"},{"type":"lifesteal","desc":"吸取周围敌人生命","duration":3,"value":15,"target":"自身"}], "dice_count":4,"dice_size":6, "target":"范围", "aoe_radius":25, "saving_throw":{"attr":"CON","dc_formula":"8+PROF+INT","on_save":"半伤"}},
    ]),
    ("塔莉垭", "mage", [
        {"name":"石穿", "effects":[{"type":"dot","desc":"连续投掷五枚岩石","duration":1,"target":"敌方"}], "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"}},
        {"name":"岩突", "effects":[{"type":"control","desc":"隆起岩石抛掷敌人","duration":1,"target":"敌方"}], "target":"范围", "aoe_radius":10, "saving_throw":{"attr":"STR","dc_formula":"8+PROF+INT","on_save":"无效"}},
        {"name":"撒石阵", "effects":[{"type":"slow","desc":"碎石陷阱减速","duration":2,"target":"敌方"},{"type":"dot","desc":"位移触发碎石爆炸","duration":2,"target":"敌方"}], "target":"范围", "aoe_radius":20, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"}},
        {"name":"墙幔", "effects":[{"type":"control","desc":"召唤不可逾越的石墙分割战场","duration":3,"target":"敌方"},{"type":"accel","desc":"可乘石墙滑行","duration":3,"target":"自身"}], "dice_count":3,"dice_size":8, "range":"远程", "target":"范围", "aoe_radius":40},
    ]),
    ("崔斯特", "mage", [
        {"name":"万能牌", "effects":[{"type":"dot","desc":"三张魔法牌扇形飞散","duration":1,"target":"敌方"}], "target":"范围", "aoe_radius":15, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"}},
        {"name":"选牌", "effects":[{"type":"control","desc":"金牌眩晕/红牌减速/蓝牌回复","duration":1,"target":"敌方"}], "range":"远程"},
        {"name":"卡牌骗术", "effects":[{"type":"buff","desc":"每四次攻击附带额外伤害","duration":1,"target":"自身"}], "damage_type":"穿刺"},
        {"name":"命运", "effects":[{"type":"accel","desc":"揭示全图敌人并传送至任意位置","target":"自身"}], "dice_count":0,"dice_size":0, "range":"远程", "target":"自身", "damage_type":"力场", "cooldown":4},
    ]),
    ("维迦", "mage", [
        {"name":"黑暗祭祀", "effects":[{"type":"buff","desc":"击杀单位永久提升法强","duration":99,"target":"自身"}], "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"}},
        {"name":"黑暗物质", "effects":[{"type":"dot","desc":"陨星坠落延迟打击","duration":1,"target":"敌方"}], "target":"范围", "aoe_radius":15, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"}},
        {"name":"扭曲空间", "effects":[{"type":"control","desc":"魔法牢笼边缘眩晕触碰者","duration":1,"target":"敌方"}], "range":"远程", "target":"范围", "aoe_radius":20, "saving_throw":{"attr":"CON","dc_formula":"8+PROF+INT","on_save":"无效"}},
        {"name":"能量爆裂", "effects":[{"type":"execute","desc":"目标生命越低伤害越高","threshold":33,"target":"敌方"}], "dice_count":4,"dice_size":6, "target":"单体", "saving_throw":{"attr":"WIS","dc_formula":"8+PROF+INT","on_save":"半伤"}},
    ]),
    ("维克兹", "mage", [
        {"name":"等离子裂变", "effects":[{"type":"sunder","desc":"等离子分裂降低魔抗","duration":1,"target":"敌方"}], "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"}},
        {"name":"虚空裂隙", "effects":[{"type":"dot","desc":"裂隙延迟爆炸","duration":1,"target":"敌方"}], "target":"范围", "aoe_radius":10, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"}},
        {"name":"构造分解", "effects":[{"type":"control","desc":"击飞并推开","duration":1,"target":"敌方"},{"type":"sunder","desc":"分解目标研究护甲","duration":1,"target":"敌方"}], "saving_throw":{"attr":"CON","dc_formula":"8+PROF+INT","on_save":"无效"}},
        {"name":"生命形态瓦解射线", "effects":[{"type":"dot","desc":"持续解离射线造成毁灭伤害","duration":2,"target":"敌方"},{"type":"slow","desc":"射线减速","duration":2,"target":"敌方"}], "dice_count":4,"dice_size":6, "target":"范围", "range":"远程", "aoe_radius":30, "saving_throw":{"attr":"CON","dc_formula":"8+PROF+INT","on_save":"半伤"}},
    ]),
    ("薇古丝", "mage", [
        {"name":"寒心波云", "effects":[{"type":"slow","desc":"暗影波减速","duration":1,"target":"敌方"}], "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"}},
        {"name":"生人勿近", "effects":[{"type":"shield","desc":"暗影护盾","duration":1,"value":25,"target":"自身"},{"type":"control","desc":"恐惧近身敌人","duration":1,"target":"敌方"}], "range":"自身", "target":"范围", "aoe_radius":10, "saving_throw":{"attr":"WIS","dc_formula":"8+PROF+INT","on_save":"无效"}},
        {"name":"溟濛渐染", "effects":[{"type":"slow","desc":"暗影区域减速并标记","duration":2,"target":"敌方"}], "target":"范围", "aoe_radius":15},
        {"name":"愁云迷雾", "effects":[{"type":"accel","desc":"暗影冲刺追踪标记目标","target":"自身"},{"type":"control","desc":"命中恐惧周围敌人","duration":1,"target":"敌方"}], "dice_count":4,"dice_size":6, "range":"远程"},
    ]),
    ("泽拉斯", "mage", [
        {"name":"奥能脉冲", "effects":[{"type":"sunder","desc":"充能光束穿透降低魔抗","duration":1,"target":"敌方"}], "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"}},
        {"name":"毁灭之眼", "effects":[{"type":"slow","desc":"奥术轰击中心区减速","duration":1,"target":"敌方"}], "target":"范围", "aoe_radius":10, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"}},
        {"name":"冲击法球", "effects":[{"type":"control","desc":"奥术法球眩晕命中者","duration":1,"target":"敌方"}], "saving_throw":{"attr":"CON","dc_formula":"8+PROF+INT","on_save":"无效"}},
        {"name":"奥术仪式", "effects":[{"type":"dot","desc":"多轮奥术弹幕远程轰炸","duration":2,"target":"敌方"},{"type":"slow","desc":"弹幕减速","duration":2,"target":"敌方"}], "dice_count":4,"dice_size":6, "target":"范围", "range":"远程", "aoe_radius":30, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"}},
    ]),
    ("婕拉", "mage", [
        {"name":"致命荆棘", "effects":[{"type":"dot","desc":"荆棘藤蔓穿透","duration":1,"target":"敌方"}], "target":"范围", "aoe_radius":15, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"}},
        {"name":"迅猛生长", "effects":[{"type":"buff","desc":"播下种子，被技能激活后长成荆棘喷吐者","duration":3,"target":"自身"}], "range":"远程", "damage_type":"穿刺"},
        {"name":"缠绕之根", "effects":[{"type":"control","desc":"藤蔓缠绕禁锢","duration":1,"target":"敌方"}], "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"无效"}},
        {"name":"绞杀之藤", "effects":[{"type":"control","desc":"荆棘丛击飞范围内敌人","duration":1,"target":"敌方"},{"type":"dot","desc":"荆棘持续鞭笞","duration":2,"target":"敌方"}], "dice_count":4,"dice_size":6, "target":"范围", "aoe_radius":25, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"}},
    ]),
    # ═══ MARKSMEN (17) ═══
    ("阿克尚", "marksman", [
        {"name":"复仇回旋镖", "effects":[{"type":"vuln","desc":"回旋镖标记目标","duration":1,"target":"敌方"}], "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"半伤"}},
        {"name":"英雄入潜", "effects":[{"type":"invis","desc":"伪装潜行靠近标记目标","duration":2,"target":"自身"},{"type":"accel","desc":"追踪加速","duration":2,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"穿刺"},
        {"name":"荡索", "effects":[{"type":"accel","desc":"钩索荡击连续射击","duration":1,"target":"自身"}], "damage_type":"穿刺"},
        {"name":"因果报应", "effects":[{"type":"execute","desc":"充能狙击低血处决","threshold":25,"target":"敌方"}], "dice_count":3,"dice_size":8, "range":"远程", "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"半伤"}},
    ]),
    ("厄斐琉斯", "marksman", [
        {"name":"武器技能", "effects":[{"type":"vuln","desc":"狙击枪标记可远程引爆","duration":1,"target":"敌方"}], "range":"远程"},
        {"name":"月相轮转", "effects":[{"type":"buff","desc":"切换主副武器","duration":1,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"穿刺"},
        {"name":"武器队列", "effects":[{"type":"buff","desc":"弹药耗尽自动切换下一武器","duration":99,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"穿刺"},
        {"name":"月华祷言", "effects":[{"type":"heal","desc":"月光洗礼治疗自身","value":20,"target":"自身"},{"type":"slow","desc":"月光减速命中敌人","duration":1,"target":"敌方"}], "dice_count":3,"dice_size":8, "range":"远程", "target":"范围", "aoe_radius":25, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"半伤"}},
    ]),
    ("库奇", "marksman", [
        {"name":"磷光炸弹", "effects":[{"type":"vuln","desc":"炸弹照亮隐形目标","duration":2,"target":"敌方"}], "range":"远程", "target":"范围", "aoe_radius":10, "damage_type":"力场", "bonus_attr":"DEX", "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"半伤"}},
        {"name":"瓦尔基里俯冲", "effects":[{"type":"accel","desc":"长距离俯冲位移","target":"自身"},{"type":"dot","desc":"俯冲路径留下灼烧轨迹","duration":1,"target":"敌方"}], "range":"远程", "damage_type":"力场"},
        {"name":"格林机枪", "effects":[{"type":"sunder","desc":"机枪扫射降低护甲","duration":1,"target":"敌方"}], "target":"范围", "aoe_radius":15},
        {"name":"火箭轰击", "effects":[{"type":"dot","desc":"导弹舱持续发射火箭","duration":2,"target":"敌方"}], "dice_count":3,"dice_size":8, "range":"远程", "target":"范围", "aoe_radius":15, "damage_type":"力场"},
    ]),
    ("格雷福斯", "marksman", [
        {"name":"穷途末路", "effects":[{"type":"dot","desc":"火药弹墙壁反弹二次爆炸","duration":1,"target":"敌方"}], "range":"近战", "target":"范围", "aoe_radius":15, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"半伤"}},
        {"name":"烟幕弹", "effects":[{"type":"slow","desc":"烟幕中敌人视野受限","duration":2,"target":"敌方"}], "range":"远程", "damage_type":"力场"},
        {"name":"快速拔枪", "effects":[{"type":"accel","desc":"短距冲刺装填弹药","target":"自身"},{"type":"buff","desc":"获得额外护甲","duration":1,"target":"自身"}], "damage_type":"穿刺"},
        {"name":"终极爆弹", "effects":[{"type":"control","desc":"巨型爆弹击退目标","duration":1,"target":"敌方"},{"type":"accel","desc":"后坐力推开自身","target":"自身"}], "dice_count":3,"dice_size":8, "range":"远程", "target":"范围", "aoe_radius":20, "saving_throw":{"attr":"CON","dc_formula":"8+PROF+DEX","on_save":"半伤"}},
    ]),
    ("卡莉丝塔", "marksman", [
        {"name":"穿刺", "effects":[{"type":"dot","desc":"长矛刺入叠加","duration":3,"target":"敌方"},{"type":"accel","desc":"投掷后向指定方向跳跃","target":"自身"}], "damage_type":"穿刺"},
        {"name":"哨兵", "effects":[{"type":"vuln","desc":"哨兵巡逻标记目标","duration":2,"target":"敌方"}], "range":"远程", "damage_type":"穿刺"},
        {"name":"撕裂", "effects":[{"type":"execute","desc":"拔出所有矛，每根矛额外伤害","threshold":10,"target":"敌方"},{"type":"slow","desc":"撕裂减速","duration":1,"target":"敌方"}], "target":"范围", "aoe_radius":20, "saving_throw":{"attr":"CON","dc_formula":"8+PROF+DEX","on_save":"半伤"}},
        {"name":"命运的召唤", "effects":[{"type":"control","desc":"召回契约者并击飞路径敌人","duration":1,"target":"敌方"},{"type":"immune","desc":"契约者变为不可选中","duration":1,"target":"自身"}], "dice_count":2,"dice_size":10, "target":"范围", "range":"远程", "aoe_radius":25},
    ]),
    ("克格莫", "marksman", [
        {"name":"腐蚀唾液", "effects":[{"type":"sunder","desc":"腐蚀降低护甲魔抗","duration":1,"target":"敌方"}], "range":"远程", "damage_type":"力场"},
        {"name":"生化弹幕", "effects":[{"type":"buff","desc":"超远射程生化攻击","duration":2,"target":"自身"},{"type":"dot","desc":"弹幕附带百分比生命伤害","duration":2,"target":"敌方"}], "range":"自身", "target":"自身", "damage_type":"力场"},
        {"name":"虚空淤泥", "effects":[{"type":"slow","desc":"淤泥路径减速","duration":1,"target":"敌方"}], "range":"远程", "target":"范围", "aoe_radius":15, "damage_type":"力场"},
        {"name":"活体大炮", "effects":[{"type":"execute","desc":"远程炮击低血增伤","threshold":40,"target":"敌方"}], "dice_count":3,"dice_size":8, "range":"远程", "target":"范围", "aoe_radius":15, "damage_type":"力场", "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"半伤"}},
    ]),
    ("尼菈", "marksman", [
        {"name":"无形之刃", "effects":[{"type":"buff","desc":"水刃强化普攻","duration":1,"target":"自身"}], "range":"近战", "target":"范围", "aoe_radius":15},
        {"name":"雾纱障壁", "effects":[{"type":"reduce","desc":"雾纱减伤并免疫魔法","duration":1,"target":"自身"},{"type":"accel","desc":"雾纱移速提升","duration":1,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"力场"},
        {"name":"滑流", "effects":[{"type":"accel","desc":"水流冲刺穿过敌人","target":"自身"}], "damage_type":"挥砍"},
        {"name":"神化", "effects":[{"type":"control","desc":"水刃漩涡拖拽中心敌人","duration":1,"target":"敌方"},{"type":"heal","desc":"漩涡造成伤害治疗友军","duration":1,"value":20,"target":"自身"}], "dice_count":3,"dice_size":8, "target":"范围", "aoe_radius":25, "saving_throw":{"attr":"STR","dc_formula":"8+PROF+DEX","on_save":"无效"}},
    ]),
    ("奎因", "marksman", [
        {"name":"炫目攻势", "effects":[{"type":"slow","desc":"致盲标记","duration":1,"target":"敌方"}], "range":"远程", "target":"范围", "aoe_radius":10, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"半伤"}},
        {"name":"敏锐感知", "effects":[{"type":"vuln","desc":"揭示周围隐形单位并标记","duration":2,"target":"敌方"}], "range":"自身", "target":"范围", "aoe_radius":25, "damage_type":"穿刺"},
        {"name":"旋翔掠杀", "effects":[{"type":"accel","desc":"冲刺标记目标","target":"自身"},{"type":"slow","desc":"踢击减速","duration":1,"target":"敌方"}], "saving_throw":{"attr":"STR","dc_formula":"8+PROF+DEX","on_save":"无效"}},
        {"name":"深入敌后", "effects":[{"type":"accel","desc":"召唤华洛骑乘飞行，移速翻倍","duration":3,"target":"自身"},{"type":"buff","desc":"骑乘状态攻击附带额外伤害","duration":3,"target":"自身"}], "dice_count":2,"dice_size":10, "range":"自身", "target":"自身"},
    ]),
    ("莎弥拉", "marksman", [
        {"name":"天赋", "effects":[{"type":"vuln","desc":"近战挥砍/远程射击","duration":1,"target":"敌方"}], "range":"近战", "damage_type":"挥砍"},
        {"name":"锋旋", "effects":[{"type":"shield","desc":"剑刃旋风摧毁飞行道具","duration":1,"value":20,"target":"自身"}], "range":"自身", "target":"范围", "aoe_radius":10},
        {"name":"狂飙", "effects":[{"type":"accel","desc":"冲刺穿越目标","target":"自身"},{"type":"buff","desc":"击杀刷新冷却","duration":1,"target":"自身"}], "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"半伤"}},
        {"name":"炼狱扳机", "effects":[{"type":"dot","desc":"旋风式扫射周围所有敌人","duration":2,"target":"敌方"},{"type":"lifesteal","desc":"扫射附带吸血","duration":2,"value":10,"target":"自身"}], "dice_count":3,"dice_size":8, "target":"范围", "aoe_radius":20, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"半伤"}},
    ]),
    ("赛娜", "marksman", [
        {"name":"黑暗洞灭", "effects":[{"type":"heal","desc":"圣光穿透治疗友军","duration":1,"value":15,"target":"自身"},{"type":"slow","desc":"黑暗光束减速","duration":1,"target":"敌方"}], "range":"远程"},
        {"name":"无尽厮守", "effects":[{"type":"control","desc":"黑雾禁锢延迟触发","duration":1,"target":"敌方"}], "saving_throw":{"attr":"WIS","dc_formula":"8+PROF+DEX","on_save":"无效"}},
        {"name":"黑雾咒附", "effects":[{"type":"invis","desc":"黑雾伪装自身与附近友军","duration":2,"target":"自身"},{"type":"accel","desc":"雾中移速提升","duration":2,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"力场"},
        {"name":"暗影燎原", "effects":[{"type":"shield","desc":"全图光柱为友军提供护盾","duration":1,"value":40,"target":"自身"},{"type":"dot","desc":"光柱中心造成伤害","duration":1,"target":"敌方"}], "dice_count":3,"dice_size":8, "range":"远程", "target":"范围", "aoe_radius":40, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"半伤"}},
    ]),
    ("希维尔", "marksman", [
        {"name":"回旋之刃", "effects":[{"type":"sunder","desc":"十字刃穿透降低护甲","duration":1,"target":"敌方"}], "damage_type":"挥砍", "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"半伤"}},
        {"name":"弹射", "effects":[{"type":"buff","desc":"攻击弹射至多个目标","duration":1,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"穿刺"},
        {"name":"法术护盾", "effects":[{"type":"shield","desc":"护盾格挡一次技能并回复法力","duration":1,"value":15,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"力场"},
        {"name":"狩猎", "effects":[{"type":"accel","desc":"全队战斗怒吼大幅提升移速","duration":2,"target":"自身"},{"type":"buff","desc":"附近友军获得加速","duration":2,"target":"自身"}], "dice_count":2,"dice_size":10, "range":"自身", "target":"自身"},
    ]),
    ("斯莫德", "marksman", [
        {"name":"超级灼热龙息", "effects":[{"type":"execute","desc":"叠层进化，225层处决低血目标","threshold":10,"target":"敌方"},{"type":"dot","desc":"225层附带真实伤害灼烧","duration":2,"target":"敌方"}], "range":"远程"},
        {"name":"阿嚏!", "effects":[{"type":"slow","desc":"炽热喷嚏减速爆炸","duration":1,"target":"敌方"}], "range":"远程", "target":"范围", "aoe_radius":15, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"半伤"}},
        {"name":"扑棱扑棱扑棱!", "effects":[{"type":"accel","desc":"展翅飞行无视地形","duration":1,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"力场"},
        {"name":"妈——!", "effects":[{"type":"heal","desc":"龙母喷火治疗自身","duration":1,"value":25,"target":"自身"},{"type":"slow","desc":"中心区减速","duration":1,"target":"敌方"}], "dice_count":3,"dice_size":8, "range":"远程", "target":"范围", "aoe_radius":35, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"半伤"}},
    ]),
    ("崔丝塔娜", "marksman", [
        {"name":"急速射击", "effects":[{"type":"buff","desc":"攻速大幅提升","duration":2,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"穿刺"},
        {"name":"火箭跳跃", "effects":[{"type":"accel","desc":"火箭跳远距离位移","target":"自身"},{"type":"slow","desc":"落地减速","duration":1,"target":"敌方"}], "target":"范围", "aoe_radius":10, "damage_type":"力场"},
        {"name":"爆炸火花", "effects":[{"type":"dot","desc":"炸弹附着，攻击叠加引爆","duration":2,"target":"敌方"}], "damage_type":"力场", "bonus_attr":"DEX"},
        {"name":"毁灭射击", "effects":[{"type":"control","desc":"巨型加农炮击退目标","duration":1,"target":"敌方"}], "dice_count":3,"dice_size":8, "saving_throw":{"attr":"STR","dc_formula":"8+PROF+DEX","on_save":"无效"}},
    ]),
    ("图奇", "marksman", [
        {"name":"埋伏", "effects":[{"type":"invis","desc":"潜行进入伪装","duration":2,"target":"自身"},{"type":"buff","desc":"脱离伪装后攻速提升","duration":2,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"穿刺"},
        {"name":"剧毒之桶", "effects":[{"type":"slow","desc":"毒液减速并叠加毒素","duration":2,"target":"敌方"}], "range":"远程", "target":"范围", "aoe_radius":15, "damage_type":"力场", "saving_throw":{"attr":"CON","dc_formula":"8+PROF+DEX","on_save":"无效"}},
        {"name":"毒性爆发", "effects":[{"type":"execute","desc":"引爆毒素，层数越高伤害越高","threshold":20,"target":"敌方"}], "target":"范围", "aoe_radius":25, "saving_throw":{"attr":"CON","dc_formula":"8+PROF+DEX","on_save":"半伤"}},
        {"name":"火力全开", "effects":[{"type":"buff","desc":"毒弩穿透所有目标，射程提升","duration":2,"target":"自身"},{"type":"dot","desc":"穿透射击附加毒素","duration":2,"target":"敌方"}], "dice_count":3,"dice_size":8, "target":"范围", "aoe_radius":30},
    ]),
    ("韦鲁斯", "marksman", [
        {"name":"穿刺之箭", "effects":[{"type":"sunder","desc":"蓄力贯穿降低护甲","duration":1,"target":"敌方"}], "range":"远程", "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"半伤"}},
        {"name":"枯萎箭袋", "effects":[{"type":"dot","desc":"普攻附枯萎","duration":2,"target":"敌方"},{"type":"execute","desc":"技能引爆枯萎造成百分比伤害","threshold":10,"target":"敌方"}], "range":"自身", "target":"自身", "damage_type":"力场"},
        {"name":"恶灵箭雨", "effects":[{"type":"slow","desc":"箭雨减速并施加重伤","duration":2,"target":"敌方"},{"type":"dot","desc":"重伤降低治疗","duration":2,"target":"敌方"}], "target":"范围", "aoe_radius":15, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"半伤"}},
        {"name":"腐败锁链", "effects":[{"type":"control","desc":"腐败藤蔓禁锢并蔓延周围敌人","duration":1,"target":"敌方"}], "dice_count":3,"dice_size":8, "range":"远程", "saving_throw":{"attr":"CON","dc_formula":"8+PROF+DEX","on_save":"无效"}},
    ]),
    ("霞", "marksman", [
        {"name":"双刃", "effects":[{"type":"vuln","desc":"双刃投掷留下羽毛","duration":2,"target":"敌方"}], "range":"远程", "damage_type":"穿刺"},
        {"name":"致死羽衣", "effects":[{"type":"buff","desc":"羽刃风暴提升攻速移速","duration":2,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"穿刺"},
        {"name":"倒钩", "effects":[{"type":"control","desc":"召回所有羽毛，3根以上禁锢","duration":1,"target":"敌方"}], "target":"范围", "aoe_radius":25, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"无效"}},
        {"name":"暴风羽刃", "effects":[{"type":"immune","desc":"跃入空中变为不可选中","duration":1,"target":"自身"},{"type":"dot","desc":"羽刃暴雨覆盖区域","duration":1,"target":"敌方"}], "dice_count":3,"dice_size":8, "target":"范围", "aoe_radius":20, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"半伤"}},
    ]),
    ("泽丽", "marksman", [
        {"name":"电火进射", "effects":[{"type":"accel","desc":"电击后可短距冲刺","target":"自身"}], "range":"远程", "damage_type":"力场"},
        {"name":"强穿激光", "effects":[{"type":"slow","desc":"激光穿透减速","duration":1,"target":"敌方"}], "range":"远程", "damage_type":"力场", "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"半伤"}},
        {"name":"灿丽花火", "effects":[{"type":"accel","desc":"电光冲刺穿越地形","target":"自身"}], "range":"远程", "damage_type":"力场"},
        {"name":"超限爆闪", "effects":[{"type":"buff","desc":"超载状态攻速移速飙升","duration":3,"target":"自身"},{"type":"dot","desc":"连锁闪电弹射","duration":3,"target":"敌方"}], "dice_count":3,"dice_size":8, "target":"范围", "aoe_radius":25, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"半伤"}},
    ]),
    # ═══ SUPPORT/ASSASSIN (1) ═══
    ("派克", "assassin", [
        {"name":"透骨尖钉", "effects":[{"type":"control","desc":"鱼叉钩拽拉近目标","duration":1,"target":"敌方"},{"type":"slow","desc":"蓄力减速","duration":1,"target":"敌方"}], "range":"远程", "damage_type":"穿刺", "saving_throw":{"attr":"STR","dc_formula":"8+PROF+DEX","on_save":"无效"}},
        {"name":"幽潭潜行", "effects":[{"type":"invis","desc":"潜入幽潭隐身","duration":2,"target":"自身"},{"type":"accel","desc":"潜行中移速飙升","duration":2,"target":"自身"},{"type":"heal","desc":"潜行回复近期受伤生命","duration":2,"value":15,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"穿刺"},
        {"name":"魅影浪洄", "effects":[{"type":"accel","desc":"暗影冲刺","target":"自身"},{"type":"control","desc":"暗影返回时眩晕穿过敌人","duration":1,"target":"敌方"}], "saving_throw":{"attr":"CON","dc_formula":"8+PROF+DEX","on_save":"无效"}},
        {"name":"涌泉之恨", "effects":[{"type":"execute","desc":"X形处决低血量目标，击杀刷新","threshold":25,"target":"敌方"},{"type":"accel","desc":"处决成功可再次施放","target":"自身"}], "dice_count":4,"dice_size":6, "target":"范围", "aoe_radius":20, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"半伤"}},
    ]),
]

def generate():
    output = {}
    for hero_name, role, customs in BATCH3:
        tmpl = TEMPLATES[role]
        skills = [make_skill(key, hero_name, tmpl, customs[i] if i < len(customs) else {}) for i, key in enumerate(["Q","W","E","R"])]
        output[hero_name] = skills
    
    with open(SKILLS_PATH, 'r', encoding='utf-8') as f:
        main = json.load(f)
    for name, skills in output.items():
        main[name] = skills
    with open(SKILLS_PATH, 'w', encoding='utf-8') as f:
        json.dump(main, f, ensure_ascii=False, indent=2)
    
    print(f"Batch 3: Generated {len(output)} heroes ({sum(len(v) for v in output.values())} skills)")
    print(f"Heroes: {', '.join(output.keys())}")

if __name__ == '__main__':
    generate()
