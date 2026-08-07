#!/usr/bin/env python3
"""Batch 4: Generate 30 heroes (fighter 8 + support 9 + tank 13) for LoL."""
import json, os

TEMPLATES = json.load(open(os.path.join(os.path.dirname(__file__), 'role_dnd_templates.json'), 'r', encoding='utf-8'))
SKILLS_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'skills', 'league_of_legends.json')

def make_skill(key, name, role_tmpl, custom=None):
    c = custom or {}
    slot = role_tmpl['slots'][key]
    dmg_override = {}
    if "damage" in c: dmg_override = c["damage"]
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

BATCH4 = [
    # ═══ FIGHTERS (8) ═══
    ("希瓦娜", "fighter", [
        {"name":"龙牙突袭", "effects":[{"type":"buff","desc":"下次攻击附带额外伤害并施加标记","duration":1,"target":"自身"}], "damage_type":"挥砍"},
        {"name":"烈火燎原", "effects":[{"type":"dot","desc":"烈焰光环持续灼烧周围敌人","duration":2,"target":"敌方"},{"type":"accel","desc":"烈焰中移速提升","duration":2,"target":"自身"}], "range":"自身", "target":"范围", "aoe_radius":15, "damage_type":"力场", "bonus_attr":"INT"},
        {"name":"烈焰吐息", "effects":[{"type":"sunder","desc":"火球穿透降低护甲","duration":1,"target":"敌方"},{"type":"vuln","desc":"标记目标增伤","duration":1,"target":"敌方"}], "range":"远程", "damage_type":"力场", "bonus_attr":"INT", "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"}},
        {"name":"魔龙降世", "effects":[{"type":"buff","desc":"化身魔龙，体型增大属性飙升","duration":3,"target":"自身"},{"type":"control","desc":"龙翼冲击击退路径敌人","duration":1,"target":"敌方"}], "dice_count":3,"dice_size":8, "target":"范围", "range":"远程", "aoe_radius":30, "saving_throw":{"attr":"STR","dc_formula":"8+PROF+STR","on_save":"无效"}},
    ]),
    ("特朗德尔", "fighter", [
        {"name":"噬咬", "effects":[{"type":"buff","desc":"撕咬偷取攻击力","duration":1,"target":"自身"},{"type":"sunder","desc":"降低目标攻击力","duration":1,"target":"敌方"}], "damage_type":"穿刺"},
        {"name":"冰封领域", "effects":[{"type":"accel","desc":"极冰领域移速攻速提升","duration":2,"target":"自身"},{"type":"heal","desc":"领域内回复增强","duration":2,"value":10,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"寒冷"},
        {"name":"寒冰之柱", "effects":[{"type":"control","desc":"召唤冰柱阻挡并减速","duration":2,"target":"敌方"},{"type":"slow","desc":"冰柱周围大幅减速","duration":2,"target":"敌方"}], "range":"远程", "damage_type":"寒冷"},
        {"name":"强权至敌", "effects":[{"type":"sunder","desc":"吸取目标双抗与生命","duration":2,"target":"敌方"},{"type":"buff","desc":"偷取的防御与生命加于自身","duration":2,"target":"自身"}], "dice_count":2,"dice_size":10, "saving_throw":{"attr":"CON","dc_formula":"8+PROF+STR","on_save":"半伤"}},
    ]),
    ("乌迪尔", "fighter", [
        {"name":"虎爪姿态", "effects":[{"type":"buff","desc":"虎形态提高攻速与额外伤害","duration":2,"target":"自身"},{"type":"dot","desc":"虎爪撕裂持续流血","duration":1,"target":"敌方"}], "damage_type":"挥砍"},
        {"name":"龟壳姿态", "effects":[{"type":"shield","desc":"灵龟护盾吸收伤害","duration":2,"value":40,"target":"自身"},{"type":"lifesteal","desc":"攻击回复生命","duration":2,"value":10,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"钝击"},
        {"name":"熊力姿态", "effects":[{"type":"accel","desc":"巨熊冲锋移速飙升","duration":1,"target":"自身"},{"type":"control","desc":"熊掌拍击眩晕","duration":1,"target":"敌方"}], "saving_throw":{"attr":"CON","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"凤翼姿态", "effects":[{"type":"dot","desc":"凤凰烈焰锥形喷吐","duration":2,"target":"敌方"},{"type":"slow","desc":"烈焰减速","duration":2,"target":"敌方"}], "dice_count":3,"dice_size":8, "target":"范围", "aoe_radius":20, "damage_type":"力场", "bonus_attr":"INT", "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"}},
    ]),
    ("厄加特", "fighter", [
        {"name":"腐蚀电荷", "effects":[{"type":"dot","desc":"酸液爆炸持续腐蚀","duration":2,"target":"敌方"},{"type":"slow","desc":"酸液减速","duration":1,"target":"敌方"}], "range":"远程", "damage_type":"力场", "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+STR","on_save":"半伤"}},
        {"name":"净除", "effects":[{"type":"shield","desc":"机械护盾吸收伤害","duration":1,"value":30,"target":"自身"},{"type":"dot","desc":"六管机枪持续扫射","duration":1,"target":"敌方"}], "range":"自身", "target":"范围", "aoe_radius":15, "damage_type":"穿刺"},
        {"name":"鄙弃", "effects":[{"type":"accel","desc":"冲刺抓取目标","target":"自身"},{"type":"control","desc":"过肩摔将目标掷到身后并眩晕","duration":1,"target":"敌方"}], "saving_throw":{"attr":"STR","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"超越死亡的恐惧", "effects":[{"type":"execute","desc":"发射钻头处决低血量目标","threshold":25,"target":"敌方"},{"type":"control","desc":"处决成功恐惧周围敌人","duration":1,"target":"敌方"}], "dice_count":3,"dice_size":8, "range":"远程", "saving_throw":{"attr":"CON","dc_formula":"8+PROF+STR","on_save":"半伤"}},
    ]),
    ("沃利贝尔", "fighter", [
        {"name":"擂首一击", "effects":[{"type":"control","desc":"熊掌拍击眩晕","duration":1,"target":"敌方"},{"type":"accel","desc":"冲刺加速","target":"自身"}], "saving_throw":{"attr":"CON","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"暴怒撕咬", "effects":[{"type":"heal","desc":"撕咬伤口回复生命","duration":1,"value":15,"target":"自身"},{"type":"vuln","desc":"标记伤口增伤","duration":1,"target":"敌方"}], "damage_type":"穿刺"},
        {"name":"霹天雳地", "effects":[{"type":"slow","desc":"雷霆轰击减速","duration":1,"target":"敌方"},{"type":"shield","desc":"雷霆中自身获得护盾","duration":1,"value":30,"target":"自身"}], "target":"范围", "aoe_radius":15, "damage_type":"力场", "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+STR","on_save":"半伤"}},
        {"name":"天声震落", "effects":[{"type":"control","desc":"跃起化身巨熊砸地，范围内敌人眩晕","duration":1,"target":"敌方"},{"type":"buff","desc":"巨熊形态体型增大属性飙升","duration":3,"target":"自身"}], "dice_count":3,"dice_size":8, "target":"范围", "aoe_radius":25, "range":"远程", "saving_throw":{"attr":"CON","dc_formula":"8+PROF+STR","on_save":"无效"}},
    ]),
    ("沃里克", "fighter", [
        {"name":"野兽之口", "effects":[{"type":"lifesteal","desc":"撕咬吸血回复","duration":1,"value":20,"target":"自身"},{"type":"accel","desc":"可绕至目标身后","target":"自身"}], "damage_type":"穿刺"},
        {"name":"鲜血追猎", "effects":[{"type":"accel","desc":"追踪低血目标移速飙升","duration":2,"target":"自身"},{"type":"vuln","desc":"标记猎物","duration":2,"target":"敌方"}], "range":"自身", "target":"自身", "damage_type":"挥砍"},
        {"name":"远祖嗥叫", "effects":[{"type":"reduce","desc":"嗥叫期间受伤减半","duration":1,"target":"自身"},{"type":"control","desc":"嗥叫结束恐惧周围敌人","duration":1,"target":"敌方"}], "range":"自身", "target":"范围", "aoe_radius":15, "saving_throw":{"attr":"WIS","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"无尽束缚", "effects":[{"type":"control","desc":"跃起压制目标持续撕咬","duration":2,"target":"敌方"},{"type":"lifesteal","desc":"压制期间吸血回复","duration":2,"value":25,"target":"自身"}], "dice_count":3,"dice_size":8, "range":"远程", "saving_throw":{"attr":"STR","dc_formula":"8+PROF+STR","on_save":"无效"}},
    ]),
    ("孙悟空", "fighter", [
        {"name":"粉碎打击", "effects":[{"type":"sunder","desc":"金箍棒打击降低护甲","duration":1,"target":"敌方"},{"type":"buff","desc":"攻击距离提升","duration":1,"target":"自身"}], "damage_type":"钝击"},
        {"name":"真假猴王", "effects":[{"type":"invis","desc":"进入短暂隐身留下分身","duration":1,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"钝击"},
        {"name":"腾云突击", "effects":[{"type":"accel","desc":"筋斗云冲刺","target":"自身"},{"type":"buff","desc":"分身同步突击增伤","duration":1,"target":"自身"}], "damage_type":"钝击"},
        {"name":"大闹天宫", "effects":[{"type":"control","desc":"金箍棒旋转击飞所有敌人","duration":1,"target":"敌方"},{"type":"accel","desc":"旋转中移速递增","duration":2,"target":"自身"}], "dice_count":3,"dice_size":8, "target":"范围", "aoe_radius":20, "saving_throw":{"attr":"CON","dc_formula":"8+PROF+STR","on_save":"无效"}},
    ]),
    ("约里克", "fighter", [
        {"name":"临终仪式", "effects":[{"type":"heal","desc":"仪式回复生命","duration":1,"value":15,"target":"自身"},{"type":"buff","desc":"击杀单位留下坟墓召唤雾行者","duration":3,"target":"自身"}], "damage_type":"钝击"},
        {"name":"暗灵缠身", "effects":[{"type":"control","desc":"召唤亡灵之墙围困目标","duration":2,"target":"敌方"},{"type":"slow","desc":"墙内减速","duration":2,"target":"敌方"}], "range":"远程", "damage_type":"力场"},
        {"name":"哀伤之雾", "effects":[{"type":"vuln","desc":"迷雾标记增伤","duration":1,"target":"敌方"},{"type":"slow","desc":"迷雾减速","duration":1,"target":"敌方"}], "range":"远程", "damage_type":"力场"},
        {"name":"海屿悼词", "effects":[{"type":"buff","desc":"召唤迷雾室女持续推线作战","duration":4,"target":"自身"},{"type":"dot","desc":"室女攻击持续伤害","duration":4,"target":"敌方"}], "dice_count":3,"dice_size":8, "damage_type":"力场"},
    ]),
    # ═══ SUPPORTS (9) ═══
    ("艾翁", "support", [
        {"name":"根深敌固", "effects":[{"type":"control","desc":"藤蔓缠绕禁锢","duration":1,"target":"敌方"},{"type":"accel","desc":"友军可点击突进至目标","target":"自身"}], "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+WIS","on_save":"无效"}},
        {"name":"揠苗助长", "effects":[{"type":"buff","desc":"种下草丛创造视野遮蔽","duration":3,"target":"自身"}], "range":"远程", "damage_type":"光耀"},
        {"name":"种豆得瓜", "effects":[{"type":"shield","desc":"种子护盾保护友军","duration":2,"value":30,"target":"自身"},{"type":"slow","desc":"护盾到期爆炸减速","duration":1,"target":"敌方"}], "range":"远程"},
        {"name":"小菊!", "effects":[{"type":"buff","desc":"召唤石像哨兵黛西协同作战","duration":3,"target":"自身"},{"type":"control","desc":"黛西第三击击飞","duration":1,"target":"敌方"}], "dice_count":3,"dice_size":8, "target":"范围", "aoe_radius":15},
    ]),
    ("迦娜", "support", [
        {"name":"飓风呼啸", "effects":[{"type":"control","desc":"蓄力龙卷风击飞路径敌人","duration":1,"target":"敌方"}], "saving_throw":{"attr":"STR","dc_formula":"8+PROF+WIS","on_save":"无效"}},
        {"name":"和风守护", "effects":[{"type":"slow","desc":"风精灵减速目标","duration":1,"target":"敌方"},{"type":"accel","desc":"被动提升自身移速","duration":99,"target":"自身"}], "range":"远程", "damage_type":"光耀"},
        {"name":"风暴之眼", "effects":[{"type":"shield","desc":"风盾保护友军并提升攻击力","duration":2,"value":35,"target":"自身"},{"type":"buff","desc":"护盾提升攻击力","duration":2,"target":"自身"}], "range":"远程", "damage_type":"光耀"},
        {"name":"复苏季风", "effects":[{"type":"heal","desc":"季风持续治疗范围内友军","duration":2,"value":30,"target":"自身"},{"type":"control","desc":"击退周围敌人","duration":1,"target":"敌方"}], "dice_count":3,"dice_size":8, "target":"范围", "aoe_radius":25, "saving_throw":{"attr":"STR","dc_formula":"8+PROF+WIS","on_save":"无效"}},
    ]),
    ("璐璐", "support", [
        {"name":"闪耀长枪", "effects":[{"type":"slow","desc":"双枪减速叠加","duration":1,"target":"敌方"}], "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+WIS","on_save":"半伤"}},
        {"name":"奇思妙想", "effects":[{"type":"buff","desc":"友军体型增大攻速飙升","duration":2,"target":"自身"},{"type":"control","desc":"对敌人施放则变形为小动物","duration":1,"target":"敌方"}], "range":"远程", "saving_throw":{"attr":"WIS","dc_formula":"8+PROF+WIS","on_save":"无效"}},
        {"name":"帮忙皮克斯", "effects":[{"type":"shield","desc":"皮克斯护盾保护友军","duration":2,"value":30,"target":"自身"},{"type":"vuln","desc":"对敌人施放则标记并造成伤害","duration":2,"target":"敌方"}], "range":"远程"},
        {"name":"狂野生长", "effects":[{"type":"buff","desc":"友军体型暴增获得额外生命","duration":2,"target":"自身"},{"type":"control","desc":"击飞周围敌人","duration":1,"target":"敌方"}], "dice_count":3,"dice_size":8, "target":"范围", "range":"远程", "aoe_radius":10},
    ]),
    ("米利欧", "support", [
        {"name":"超级火焰球", "effects":[{"type":"control","desc":"火焰弹击退","duration":1,"target":"敌方"},{"type":"slow","desc":"火焰减速","duration":1,"target":"敌方"}], "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+WIS","on_save":"半伤"}},
        {"name":"温暖拥抱", "effects":[{"type":"heal","desc":"营火治疗友军","duration":1,"value":20,"target":"自身"},{"type":"buff","desc":"提升友军攻击范围","duration":2,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"光耀"},
        {"name":"活力充沛", "effects":[{"type":"shield","desc":"护盾保护友军并提供移速","duration":2,"value":25,"target":"自身"},{"type":"accel","desc":"移速提升","duration":2,"target":"自身"}], "range":"远程"},
        {"name":"生生不息", "effects":[{"type":"heal","desc":"生命之焰群体治疗","duration":1,"value":35,"target":"自身"},{"type":"cleanse","desc":"移除友军控制效果","target":"自身"}], "dice_count":3,"dice_size":8, "target":"范围", "range":"远程", "aoe_radius":25},
    ]),
    ("洛", "support", [
        {"name":"微光飞翎", "effects":[{"type":"heal","desc":"飞翎命中治疗自身与附近友军","duration":1,"value":15,"target":"自身"}], "range":"远程", "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+WIS","on_save":"半伤"}},
        {"name":"盛大登场", "effects":[{"type":"accel","desc":"华丽冲刺","target":"自身"},{"type":"control","desc":"跃起击飞周围敌人","duration":1,"target":"敌方"}], "target":"范围", "aoe_radius":15, "saving_throw":{"attr":"CON","dc_formula":"8+PROF+WIS","on_save":"无效"}},
        {"name":"轻舞成双", "effects":[{"type":"shield","desc":"飞向友军提供护盾","duration":2,"value":35,"target":"自身"}], "range":"远程", "damage_type":"光耀"},
        {"name":"惊鸿过隙", "effects":[{"type":"accel","desc":"魅惑冲刺移速飙升","duration":2,"target":"自身"},{"type":"control","desc":"触碰敌人造成魅惑","duration":1,"target":"敌方"}], "dice_count":3,"dice_size":8, "target":"范围", "saving_throw":{"attr":"WIS","dc_formula":"8+PROF+WIS","on_save":"无效"}},
    ]),
    ("烈娜塔", "support", [
        {"name":"握手言和", "effects":[{"type":"control","desc":"化学弹禁锢并拖拽","duration":1,"target":"敌方"}], "saving_throw":{"attr":"CON","dc_formula":"8+PROF+WIS","on_save":"无效"}},
        {"name":"紧急救助", "effects":[{"type":"buff","desc":"化学兴奋剂提升攻速移速","duration":2,"target":"自身"},{"type":"revive","desc":"持续期间若击杀回复满血，否则死亡","duration":2,"target":"自身"}], "range":"远程", "damage_type":"光耀"},
        {"name":"忠诚激励", "effects":[{"type":"shield","desc":"化学护盾保护友军","duration":2,"value":30,"target":"自身"},{"type":"slow","desc":"爆炸减速","duration":1,"target":"敌方"}], "range":"远程"},
        {"name":"恶意收购", "effects":[{"type":"control","desc":"化学云雾使敌人狂暴攻击友军","duration":1,"target":"敌方"}], "dice_count":3,"dice_size":8, "target":"范围", "aoe_radius":25, "saving_throw":{"attr":"WIS","dc_formula":"8+PROF+WIS","on_save":"无效"}},
    ]),
    ("塔里克", "support", [
        {"name":"星光之触", "effects":[{"type":"heal","desc":"星光治疗友军","duration":1,"value":20,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"光耀"},
        {"name":"坚毅壁垒", "effects":[{"type":"shield","desc":"链接友军共享护甲","duration":3,"value":25,"target":"自身"},{"type":"buff","desc":"链接友军的技能也会从塔里克位置施放","duration":3,"target":"自身"}], "range":"远程", "damage_type":"光耀"},
        {"name":"炫光", "effects":[{"type":"control","desc":"星光眩晕路径敌人","duration":1,"target":"敌方"}], "saving_throw":{"attr":"CON","dc_formula":"8+PROF+WIS","on_save":"无效"}},
        {"name":"宇宙之辉", "effects":[{"type":"immune","desc":"延迟后友军无敌","duration":2,"target":"自身"}], "dice_count":0,"dice_size":0, "range":"自身", "target":"范围", "aoe_radius":20, "damage_type":"光耀", "cooldown":4},
    ]),
    ("悠米", "support", [
        {"name":"摸鱼飞弹", "effects":[{"type":"slow","desc":"飞弹减速","duration":1,"target":"敌方"},{"type":"execute","desc":"飞弹飞行越久伤害越高","threshold":0,"target":"敌方"}], "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+WIS","on_save":"半伤"}},
        {"name":"悠米出动", "effects":[{"type":"buff","desc":"附身友军变为不可选中","duration":99,"target":"自身"},{"type":"heal","desc":"附身时治疗友军","duration":1,"value":15,"target":"自身"}], "range":"远程", "damage_type":"光耀"},
        {"name":"旺盛精力", "effects":[{"type":"heal","desc":"治疗自身或附身友军","duration":1,"value":20,"target":"自身"},{"type":"accel","desc":"附身友军移速攻速提升","duration":1,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"光耀"},
        {"name":"魔典终章", "effects":[{"type":"dot","desc":"魔典波纹持续伤害","duration":2,"target":"敌方"},{"type":"control","desc":"被多道波纹命中禁锢","duration":1,"target":"敌方"}], "dice_count":3,"dice_size":8, "target":"范围", "aoe_radius":25, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+WIS","on_save":"半伤"}},
    ]),
    ("基兰", "support", [
        {"name":"定时炸弹", "effects":[{"type":"dot","desc":"延迟炸弹附着爆炸","duration":1,"target":"敌方"},{"type":"control","desc":"双炸弹引爆眩晕","duration":1,"target":"敌方"}], "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+WIS","on_save":"半伤"}},
        {"name":"穿梭未来", "effects":[{"type":"buff","desc":"减少其他技能冷却","duration":1,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"光耀", "cooldown":1},
        {"name":"时间扭曲", "effects":[{"type":"accel","desc":"友军时间加速移速飙升","duration":1,"target":"自身"},{"type":"slow","desc":"敌人时间减速","duration":1,"target":"敌方"}], "range":"远程", "damage_type":"光耀"},
        {"name":"时光倒流", "effects":[{"type":"revive","desc":"守护友军，死亡时复活","duration":2,"target":"自身"}], "dice_count":0,"dice_size":0, "range":"远程", "target":"单体", "damage_type":"光耀", "cooldown":4},
    ]),
    # ═══ TANKS (13) ═══
    ("布里茨", "tank", [
        {"name":"机械飞爪", "effects":[{"type":"control","desc":"火箭飞爪将目标拖拽至面前","duration":1,"target":"敌方"}], "range":"远程", "damage_type":"钝击", "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"过载运转", "effects":[{"type":"accel","desc":"机械超载移速攻速飙升","duration":2,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"力场"},
        {"name":"能量铁拳", "effects":[{"type":"control","desc":"充能铁拳击飞目标","duration":1,"target":"敌方"}], "saving_throw":{"attr":"CON","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"静电力场", "effects":[{"type":"dot","desc":"静电场持续电击","duration":2,"target":"敌方"},{"type":"control","desc":"主动引爆沉默周围敌人","duration":1,"target":"敌方"}], "dice_count":2,"dice_size":8, "target":"范围", "aoe_radius":20, "saving_throw":{"attr":"CON","dc_formula":"8+PROF+STR","on_save":"半伤"}},
    ]),
    ("科加斯", "tank", [
        {"name":"破裂", "effects":[{"type":"control","desc":"地刺击飞","duration":1,"target":"敌方"},{"type":"slow","desc":"落地减速","duration":1,"target":"敌方"}], "target":"范围", "aoe_radius":15, "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"野性尖叫", "effects":[{"type":"control","desc":"锥形尖啸沉默","duration":1,"target":"敌方"}], "target":"范围", "aoe_radius":15, "damage_type":"力场", "saving_throw":{"attr":"CON","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"恐惧之刺", "effects":[{"type":"dot","desc":"虚空尖刺穿透减速","duration":1,"target":"敌方"},{"type":"slow","desc":"尖刺减速","duration":1,"target":"敌方"}], "target":"范围", "aoe_radius":15},
        {"name":"盛宴", "effects":[{"type":"execute","desc":"吞噬低血量目标造成真实伤害","threshold":20,"target":"敌方"},{"type":"buff","desc":"击杀永久提升最大生命值与体型","duration":99,"target":"自身"}], "dice_count":3,"dice_size":8, "saving_throw":{"attr":"CON","dc_formula":"8+PROF+STR","on_save":"半伤"}},
    ]),
    ("蒙多医生", "tank", [
        {"name":"病毒屠刀", "effects":[{"type":"slow","desc":"屠刀减速","duration":1,"target":"敌方"},{"type":"dot","desc":"病毒持续伤害","duration":1,"target":"敌方"}], "range":"远程", "damage_type":"穿刺", "saving_throw":{"attr":"CON","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"心脏电击", "effects":[{"type":"heal","desc":"电击回复大量生命","duration":1,"value":25,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"力场"},
        {"name":"大力行医", "effects":[{"type":"buff","desc":"医疗执照提升攻击力","duration":2,"target":"自身"},{"type":"accel","desc":"移速提升","duration":2,"target":"自身"}], "damage_type":"钝击"},
        {"name":"极限剂量", "effects":[{"type":"buff","desc":"注射超级血清，大幅回复生命并提升移速攻击力","duration":3,"target":"自身"},{"type":"heal","desc":"回复大量已损失生命","duration":1,"value":40,"target":"自身"}], "dice_count":2,"dice_size":8, "range":"自身", "target":"自身"},
    ]),
    ("奎桑提", "tank", [
        {"name":"恩托打击", "effects":[{"type":"slow","desc":"钝器重击减速","duration":1,"target":"敌方"}], "damage_type":"钝击"},
        {"name":"开路先锋", "effects":[{"type":"reduce","desc":"举盾防御姿态伤害减半","duration":1,"target":"自身"},{"type":"control","desc":"盾击击退","duration":1,"target":"敌方"}], "range":"自身", "target":"自身", "damage_type":"钝击", "saving_throw":{"attr":"STR","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"大步驰援", "effects":[{"type":"accel","desc":"冲锋至友军身旁提供护盾","target":"自身"},{"type":"shield","desc":"友军获得护盾","duration":1,"value":25,"target":"自身"}], "range":"远程"},
        {"name":"全力以赴", "effects":[{"type":"buff","desc":"全力形态：失去部分防御换取攻击力飙升","duration":3,"target":"自身"},{"type":"control","desc":"将目标撞过地形并眩晕","duration":1,"target":"敌方"}], "dice_count":3,"dice_size":8, "range":"远程", "saving_throw":{"attr":"STR","dc_formula":"8+PROF+STR","on_save":"无效"}},
    ]),
    ("茂凯", "tank", [
        {"name":"荆棘重击", "effects":[{"type":"slow","desc":"树根冲击减速","duration":1,"target":"敌方"},{"type":"control","desc":"近身目标被击退","duration":1,"target":"敌方"}], "target":"范围", "aoe_radius":10, "saving_throw":{"attr":"STR","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"扭曲突刺", "effects":[{"type":"accel","desc":"化为树根冲刺不可选中","target":"自身"},{"type":"control","desc":"缠绕禁锢目标","duration":1,"target":"敌方"}], "range":"远程", "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"树苗投掷", "effects":[{"type":"dot","desc":"树苗追踪爆炸","duration":1,"target":"敌方"},{"type":"slow","desc":"树苗爆炸减速","duration":2,"target":"敌方"}], "range":"远程", "damage_type":"力场"},
        {"name":"自然之握", "effects":[{"type":"control","desc":"荆棘巨墙缓慢推进禁锢所有敌人","duration":2,"target":"敌方"}], "dice_count":2,"dice_size":8, "target":"范围", "range":"远程", "aoe_radius":40, "saving_throw":{"attr":"STR","dc_formula":"8+PROF+STR","on_save":"无效"}},
    ]),
    ("诺提勒斯", "tank", [
        {"name":"疏通航道", "effects":[{"type":"control","desc":"船锚钩拽自身与目标相撞","duration":1,"target":"敌方"}], "range":"远程", "saving_throw":{"attr":"STR","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"泰坦之怒", "effects":[{"type":"shield","desc":"深海护盾吸收伤害","duration":2,"value":45,"target":"自身"},{"type":"dot","desc":"护盾周围冲击波伤害","duration":2,"target":"敌方"}], "range":"自身", "target":"自身", "aoe_radius":10, "damage_type":"力场"},
        {"name":"暗流涌动", "effects":[{"type":"slow","desc":"深海暗流环形减速","duration":1,"target":"敌方"}], "target":"范围", "aoe_radius":15, "damage_type":"力场", "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+STR","on_save":"半伤"}},
        {"name":"深海冲击", "effects":[{"type":"control","desc":"追踪冲击波沿途击飞","duration":1,"target":"敌方"},{"type":"control","desc":"主目标击飞眩晕","duration":1,"target":"敌方"}], "dice_count":2,"dice_size":8, "range":"远程", "saving_throw":{"attr":"CON","dc_formula":"8+PROF+STR","on_save":"无效"}},
    ]),
    ("努努", "tank", [
        {"name":"吞噬", "effects":[{"type":"heal","desc":"吞噬目标回复大量生命","duration":1,"value":30,"target":"自身"},{"type":"execute","desc":"对非英雄单位高额真实伤害","threshold":40,"target":"敌方"}], "damage_type":"钝击"},
        {"name":"史上最大雪球", "effects":[{"type":"accel","desc":"推动雪球越滚越大移速递增","duration":2,"target":"自身"},{"type":"control","desc":"雪球撞击击飞","duration":1,"target":"敌方"}], "target":"范围", "saving_throw":{"attr":"STR","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"雪球飞射", "effects":[{"type":"slow","desc":"雪球齐射减速","duration":1,"target":"敌方"},{"type":"control","desc":"被多次命中禁锢","duration":1,"target":"敌方"}], "target":"范围", "aoe_radius":15, "damage_type":"寒冷"},
        {"name":"绝对零度", "effects":[{"type":"dot","desc":"引导暴风雪持续伤害","duration":2,"target":"敌方"},{"type":"slow","desc":"暴风雪极寒减速","duration":2,"target":"敌方"},{"type":"shield","desc":"引导期间获得巨额护盾","duration":2,"value":50,"target":"自身"}], "dice_count":3,"dice_size":8, "target":"范围", "aoe_radius":25, "damage_type":"寒冷", "saving_throw":{"attr":"CON","dc_formula":"8+PROF+STR","on_save":"半伤"}},
    ]),
    ("芮尔", "tank", [
        {"name":"裂阵", "effects":[{"type":"sunder","desc":"长枪击碎护盾与护甲","duration":1,"target":"敌方"},{"type":"heal","desc":"命中回复生命","duration":1,"value":10,"target":"自身"}], "damage_type":"穿刺"},
        {"name":"驭铁术", "effects":[{"type":"accel","desc":"驭铁冲锋","target":"自身"},{"type":"control","desc":"铁马跃起击飞","duration":1,"target":"敌方"}], "target":"范围", "aoe_radius":15, "saving_throw":{"attr":"CON","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"招引", "effects":[{"type":"control","desc":"磁力牵引眩晕","duration":1,"target":"敌方"},{"type":"buff","desc":"链接友军共享防御","duration":3,"target":"自身"}], "range":"远程", "saving_throw":{"attr":"CON","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"磁力过载", "effects":[{"type":"control","desc":"磁力风暴拖拽周围敌人","duration":2,"target":"敌方"},{"type":"dot","desc":"磁力持续伤害","duration":2,"target":"敌方"}], "dice_count":2,"dice_size":8, "target":"范围", "aoe_radius":25, "saving_throw":{"attr":"STR","dc_formula":"8+PROF+STR","on_save":"无效"}},
    ]),
    ("瑟庄妮", "tank", [
        {"name":"极寒突袭", "effects":[{"type":"accel","desc":"骑猪冲锋","target":"自身"},{"type":"control","desc":"撞击击飞","duration":1,"target":"敌方"}], "saving_throw":{"attr":"CON","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"凛冬之怒", "effects":[{"type":"dot","desc":"连枷旋转两段横扫","duration":1,"target":"敌方"},{"type":"slow","desc":"第二段减速","duration":1,"target":"敌方"}], "target":"范围", "aoe_radius":15, "damage_type":"寒冷"},
        {"name":"永冻领域", "effects":[{"type":"control","desc":"冰冻标记叠加眩晕","duration":1,"target":"敌方"},{"type":"slow","desc":"永久冻土减速","duration":2,"target":"敌方"}], "target":"范围", "aoe_radius":20, "saving_throw":{"attr":"CON","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"极冰寒狱", "effects":[{"type":"control","desc":"投掷极冰套索远距离眩晕","duration":1,"target":"敌方"},{"type":"slow","desc":"冰狱风暴减速","duration":2,"target":"敌方"}], "dice_count":2,"dice_size":8, "range":"远程", "target":"范围", "aoe_radius":25, "damage_type":"寒冷", "saving_throw":{"attr":"CON","dc_formula":"8+PROF+STR","on_save":"无效"}},
    ]),
    ("辛吉德", "tank", [
        {"name":"剧毒踪迹", "effects":[{"type":"dot","desc":"身后留下毒雾持续伤害","duration":3,"target":"敌方"}], "range":"自身", "target":"范围", "aoe_radius":10, "damage_type":"力场"},
        {"name":"强力粘胶", "effects":[{"type":"control","desc":"粘胶区域禁锢","duration":1,"target":"敌方"},{"type":"slow","desc":"粘胶减速","duration":2,"target":"敌方"}], "range":"远程", "target":"范围", "aoe_radius":15, "damage_type":"力场", "saving_throw":{"attr":"DEX","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"过肩摔", "effects":[{"type":"control","desc":"将目标摔至身后并眩晕","duration":1,"target":"敌方"}], "saving_throw":{"attr":"STR","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"疯狂药剂", "effects":[{"type":"buff","desc":"注入疯狂药剂全属性飙升","duration":3,"target":"自身"},{"type":"heal","desc":"药剂持续回复","duration":3,"value":25,"target":"自身"}], "dice_count":2,"dice_size":8, "range":"自身", "target":"自身"},
    ]),
    ("赛恩", "tank", [
        {"name":"残虐猛击", "effects":[{"type":"control","desc":"蓄力巨斧击飞","duration":1,"target":"敌方"},{"type":"slow","desc":"未蓄满则减速","duration":1,"target":"敌方"}], "target":"范围", "aoe_radius":15, "saving_throw":{"attr":"CON","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"灵魂熔炉", "effects":[{"type":"shield","desc":"亡灵护盾吸收伤害","duration":2,"value":40,"target":"自身"},{"type":"dot","desc":"护盾到期爆炸","duration":1,"target":"敌方"}], "range":"自身", "target":"自身", "aoe_radius":10, "damage_type":"力场"},
        {"name":"杀手怒吼", "effects":[{"type":"sunder","desc":"怒吼破甲减速","duration":1,"target":"敌方"},{"type":"slow","desc":"音波减速","duration":1,"target":"敌方"}], "range":"远程", "damage_type":"力场", "saving_throw":{"attr":"CON","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"蛮横冲撞", "effects":[{"type":"accel","desc":"亡灵冲锋不可阻挡","duration":2,"target":"自身"},{"type":"control","desc":"撞击墙体眩晕","duration":1,"target":"敌方"}], "dice_count":2,"dice_size":8, "range":"远程", "target":"范围", "aoe_radius":30},
    ]),
    ("斯卡纳", "tank", [
        {"name":"水晶横扫", "effects":[{"type":"sunder","desc":"水晶能量撕裂护甲","duration":1,"target":"敌方"},{"type":"buff","desc":"命中减少其他技能冷却","duration":1,"target":"自身"}], "target":"范围", "aoe_radius":10, "damage_type":"力场"},
        {"name":"水晶蝎甲", "effects":[{"type":"shield","desc":"水晶甲壳护盾","duration":2,"value":35,"target":"自身"},{"type":"accel","desc":"护盾期间移速提升","duration":2,"target":"自身"}], "range":"自身", "target":"自身", "damage_type":"力场"},
        {"name":"伊克斯塔尔的冲击", "effects":[{"type":"control","desc":"投掷水晶石眩晕","duration":1,"target":"敌方"},{"type":"slow","desc":"冲击波减速","duration":1,"target":"敌方"}], "range":"远程", "saving_throw":{"attr":"CON","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"晶状毒刺", "effects":[{"type":"control","desc":"毒刺穿刺压制并拖拽目标","duration":2,"target":"敌方"}], "dice_count":2,"dice_size":8, "saving_throw":{"attr":"STR","dc_formula":"8+PROF+STR","on_save":"无效"}},
    ]),
    ("扎克", "tank", [
        {"name":"延伸打击", "effects":[{"type":"slow","desc":"橡胶手臂延伸减速","duration":1,"target":"敌方"},{"type":"control","desc":"抓取两个目标相撞","duration":1,"target":"敌方"}], "range":"远程", "saving_throw":{"attr":"STR","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"不稳定物质", "effects":[{"type":"dot","desc":"身体爆破","duration":1,"target":"敌方"},{"type":"heal","desc":"捡起碎片回复生命","duration":1,"value":10,"target":"自身"}], "target":"范围", "aoe_radius":10, "damage_type":"力场"},
        {"name":"橡筋弹弓", "effects":[{"type":"accel","desc":"蓄力弹射远距离位移","target":"自身"},{"type":"control","desc":"落地击飞","duration":1,"target":"敌方"}], "range":"远程", "saving_throw":{"attr":"CON","dc_formula":"8+PROF+STR","on_save":"无效"}},
        {"name":"动感弹球", "effects":[{"type":"control","desc":"弹跳四次击飞周围敌人","duration":1,"target":"敌方"},{"type":"accel","desc":"弹跳中移速提升","duration":2,"target":"自身"}], "dice_count":2,"dice_size":8, "target":"范围", "aoe_radius":20, "saving_throw":{"attr":"CON","dc_formula":"8+PROF+STR","on_save":"无效"}},
    ]),
]

def generate():
    output = {}
    for hero_name, role, customs in BATCH4:
        tmpl = TEMPLATES[role]
        skills = [make_skill(key, hero_name, tmpl, customs[i] if i < len(customs) else {}) for i, key in enumerate(["Q","W","E","R"])]
        output[hero_name] = skills
    
    with open(SKILLS_PATH, 'r', encoding='utf-8') as f:
        main = json.load(f)
    for name, skills in output.items():
        main[name] = skills
    with open(SKILLS_PATH, 'w', encoding='utf-8') as f:
        json.dump(main, f, ensure_ascii=False, indent=2)
    
    print(f"Batch 4: Generated {len(output)} heroes ({sum(len(v) for v in output.values())} skills)")
    print(f"Heroes: {', '.join(output.keys())}")

if __name__ == '__main__':
    generate()
