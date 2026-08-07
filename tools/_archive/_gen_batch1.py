"""Batch 1 (26 heroes) skill generator.
Uses role templates from tools/_archive/role_dnd_templates.json.
Generates D&D 5e flavored skill descriptions.
"""
import json, sys, os

# ── Role templates (inlined for script portability) ──
T = {
    "fighter": {
        "attr": "STR", "dmg_type": "挥砍",
        "Q": {"dc":1,"ds":10,"cd":0,"rng":"近战","tgt":"单体"},
        "W": {"dc":2,"ds":8,"cd":1,"rng":"近战","tgt":"单体"},
        "E": {"dc":1,"ds":8,"cd":2,"rng":"近战","tgt":"单体"},
        "R": {"dc":2,"ds":10,"cd":4,"rng":"近战","tgt":"单体"},
    },
    "assassin": {
        "attr": "DEX", "dmg_type": "挥砍",
        "Q": {"dc":1,"ds":10,"cd":0,"rng":"近战","tgt":"单体"},
        "W": {"dc":2,"ds":8,"cd":1,"rng":"远程","tgt":"单体"},
        "E": {"dc":1,"ds":8,"cd":2,"rng":"远程","tgt":"单体"},
        "R": {"dc":4,"ds":6,"cd":4,"rng":"近战","tgt":"单体"},
    },
    "mage": {
        "attr": "INT", "dmg_type": "力场",
        "Q": {"dc":1,"ds":8,"cd":0,"rng":"远程","tgt":"单体"},
        "W": {"dc":2,"ds":6,"cd":1,"rng":"远程","tgt":"范围"},
        "E": {"dc":2,"ds":6,"cd":2,"rng":"远程","tgt":"范围"},
        "R": {"dc":4,"ds":6,"cd":4,"rng":"远程","tgt":"范围"},
    },
    "marksman": {
        "attr": "DEX", "dmg_type": "穿刺",
        "Q": {"dc":1,"ds":8,"cd":0,"rng":"远程","tgt":"单体"},
        "W": {"dc":2,"ds":6,"cd":1,"rng":"远程","tgt":"单体"},
        "E": {"dc":1,"ds":8,"cd":2,"rng":"远程","tgt":"单体"},
        "R": {"dc":3,"ds":8,"cd":4,"rng":"远程","tgt":"单体"},
    },
    "tank": {
        "attr": "STR", "dmg_type": "钝击",
        "Q": {"dc":1,"ds":10,"cd":0,"rng":"近战","tgt":"单体"},
        "W": {"dc":2,"ds":6,"cd":1,"rng":"自身","tgt":"自身"},
        "E": {"dc":1,"ds":8,"cd":2,"rng":"近战","tgt":"范围"},
        "R": {"dc":2,"ds":8,"cd":4,"rng":"近战","tgt":"范围"},
    },
    "support": {
        "attr": "WIS", "dmg_type": "光耀",
        "Q": {"dc":1,"ds":6,"cd":0,"rng":"远程","tgt":"单体"},
        "W": {"dc":2,"ds":6,"cd":1,"rng":"远程","tgt":"单体"},
        "E": {"dc":1,"ds":6,"cd":2,"rng":"远程","tgt":"单体"},
        "R": {"dc":3,"ds":6,"cd":4,"rng":"远程","tgt":"范围"},
    },
}

def mk_skill(name, key, role, damage_type_override=None, effects=None, 
             saving_throw=None, desc="", aoe_radius=None, action="动作",
             range_override=None, target_override=None):
    """Build one skill dict."""
    t = T[role][key]
    dmg_type = damage_type_override or T[role]["dmg_type"]
    sk = {
        "name": name,
        "key": key,
        "type": "物理" if role in ("fighter","assassin","marksman","tank") else "法术",
        "action": action,
        "range": range_override or t["rng"],
        "target": target_override or t["tgt"],
        "damage": {
            "dice_count": t["dc"],
            "dice_size": t["ds"],
            "bonus_attr": T[role]["attr"],
            "type": dmg_type
        },
        "effects": effects or [],
        "cooldown": t["cd"],
        "description": desc
    }
    if saving_throw:
        sk["saving_throw"] = saving_throw
    if aoe_radius:
        sk["aoe_radius"] = aoe_radius
    return sk

# ═══════════════════════════════════════════════════════════
# BATCH 1 HEROES (26)
# ═══════════════════════════════════════════════════════════

HEROES = {}

# ── FIGHTERS (6) ──
HEROES["亚托克斯"] = [
    mk_skill("暗裔利刃", "Q", "fighter",
        effects=[{"type":"heal","desc":"造成伤害的30%转化为自身生命","target":"自身"}],
        desc="挥舞巨剑发动三连斩，剑锋边缘造成额外伤害。造成1d10+STR挥砍伤害，伤害的30%转化为自身生命值。每次斩击范围逐渐收窄，剑锋命中伤害提升50%。"),
    mk_skill("恶火束链", "W", "fighter",
        effects=[{"type":"slow","desc":"被锁链拖拽减速","duration":2,"target":"敌方"}],
        saving_throw={"attr":"STR","dc_formula":"8+PROF+STR","on_save":"无效"},
        desc="向前方挥出一道恶火锁链，命中首个敌人后嵌入其体内。造成2d8+STR挥砍伤害。若目标在2回合内未能脱离锁链范围，则被拖拽回原位并再次受到伤害。STR豁免成功则挣脱锁链。"),
    mk_skill("暗影冲决", "E", "fighter",
        effects=[{"type":"accel","desc":"向目标方向突进15尺","target":"自身"}],
        desc="化为暗影向前突进15尺，同时挥剑横扫路径上的敌人。造成1d8+STR挥砍伤害。被动：对敌方英雄造成伤害时回复少量生命值。"),
    mk_skill("大灭", "R", "fighter",
        damage_type_override="黯蚀",
        effects=[{"type":"buff","desc":"体型增大，攻击力+50%，获得飞行能力","duration":3,"target":"自身"},
                 {"type":"heal","desc":"受到致命伤害时回复50%生命（限一次）","target":"自身"}],
        desc="释放暗裔真身，体型暴增并展开恶魔双翼。造成2d10+STR黯蚀伤害。攻击力+50%，获得飞行能力，持续3回合。持续期间若受到致命伤害，原地复活并回复50%生命值（限一次）。"),
]

HEROES["贾克斯"] = [
    mk_skill("跳斩", "Q", "fighter",
        effects=[{"type":"accel","desc":"跃向目标，跨越地形与敌人","target":"自身"}],
        desc="纵身跃向一名可见的敌人，以武器重击其头部。造成1d10+STR挥砍伤害。可对友方单位施放以作位移。"),
    mk_skill("蓄力一击", "W", "fighter",
        damage_type_override="闪电",
        effects=[{"type":"buff","desc":"下次普通攻击附加额外闪电伤害","target":"自身"}],
        desc="将内息注入武器，下一击附带雷霆之威。造成2d8+STR闪电伤害，并使下一次普通攻击附加额外1d6闪电伤害。"),
    mk_skill("反击风暴", "E", "fighter",
        effects=[{"type":"control","desc":"眩晕周围所有敌人","duration":1,"target":"敌方"},
                 {"type":"reduce","desc":"闪避所有普通攻击","duration":1,"target":"自身"}],
        saving_throw={"attr":"CON","dc_formula":"8+PROF+STR","on_save":"无效"},
        desc="进入防御姿态，旋转灯柱弹开所有来袭的普通攻击，持续1回合。结束时猛击地面，对周围敌人造成1d8+STR挥砍伤害并眩晕1回合。每闪避一次攻击，反击伤害+20%。CON豁免成功则免疫眩晕。",
        aoe_radius=15),
    mk_skill("宗师之威", "R", "fighter",
        effects=[{"type":"buff","desc":"护甲与魔抗大幅提升","duration":3,"target":"自身"}],
        desc="释放灯柱中蕴藏的远古力量。造成2d10+STR挥砍伤害。护甲与魔法抗性大幅提升，持续3回合。被动：每第三次攻击附加额外1d8闪电伤害。"),
]

HEROES["泰达米尔"] = [
    mk_skill("嗜血杀戮", "Q", "fighter",
        effects=[{"type":"heal","desc":"消耗怒气回复生命","target":"自身"},
                 {"type":"buff","desc":"每损失5%生命+1物理攻击","target":"自身"}],
        desc="将沸腾的战意转化为生命力，消耗全部怒气回复生命。造成1d10+STR挥砍伤害。被动：每损失5%最大生命值，物理攻击力+1。"),
    mk_skill("蔑视", "W", "fighter",
        effects=[{"type":"slow","desc":"转身逃跑的敌人移动速度减半","duration":2,"target":"敌方"},
                 {"type":"sunder","desc":"转身逃跑的敌人攻击力下降","duration":2,"target":"敌方"}],
        saving_throw={"attr":"WIS","dc_formula":"8+PROF+STR","on_save":"无效"},
        desc="发出一声蛮族战吼，令周围敌人心生畏惧。造成2d8+STR挥砍伤害。背对你的敌人移动速度减半、攻击力下降，持续2回合。WIS豁免成功则免疫减益。"),
    mk_skill("旋风斩", "E", "fighter",
        effects=[{"type":"accel","desc":"旋转冲锋穿越战场30尺","target":"自身"}],
        desc="化身旋风旋转冲锋30尺，所过之处利刃翻飞。造成1d8+STR挥砍伤害。暴击时此技能冷却减少1回合。"),
    mk_skill("无尽怒火", "R", "fighter",
        effects=[{"type":"immune","desc":"生命值不会降至1以下，免疫一切伤害","duration":2,"target":"自身"}],
        desc="释放蛮王的终极战意——即使死神也无法夺走他的怒火。造成2d10+STR挥砍伤害。生命值不会降至1以下，免疫一切伤害和控制效果，持续2回合。可在被控制时激活。"),
]

HEROES["莫德凯撒"] = [
    mk_skill("破灭之锤", "Q", "fighter",
        damage_type_override="黯蚀",
        effects=[{"type":"execute","desc":"命中单体敌人时伤害+50%","target":"敌方"}],
        desc="将夜陨巨锤砸向地面，迸发黯蚀能量。造成1d10+STR黯蚀伤害。若只命中一个目标，伤害提升50%。"),
    mk_skill("不坏之身", "W", "fighter",
        effects=[{"type":"shield","desc":"获得伤害吸收护盾","duration":2,"value_formula":"2*LVL+STR","target":"自身"},
                 {"type":"heal","desc":"护盾剩余量转化为生命值","target":"自身"}],
        desc="将所受伤害的40%储存为亡灵护盾。造成2d8+STR挥砍伤害。激活护盾吸收伤害，持续2回合；再次激活可将剩余护盾量转化为生命值。"),
    mk_skill("断魂一扼", "E", "fighter",
        damage_type_override="黯蚀",
        effects=[{"type":"control","desc":"将敌人拖向自己15尺","target":"敌方"}],
        saving_throw={"attr":"STR","dc_formula":"8+PROF+STR","on_save":"无效"},
        desc="从地底伸出幽冥铁爪，将范围内敌人拖向自己。造成1d8+STR黯蚀伤害。无视地形与护甲。STR豁免成功则不被拖拽。"),
    mk_skill("轮回绝境", "R", "fighter",
        damage_type_override="黯蚀",
        effects=[{"type":"control","desc":"将目标拖入死亡领域孤立1v1","duration":3,"target":"敌方"},
                 {"type":"buff","desc":"窃取目标10%核心属性","duration":3,"target":"自身"}],
        desc="将一名敌人放逐至死亡领域，与外界完全隔绝。造成2d10+STR黯蚀伤害。领域内只有你与目标可以互相影响，持续3回合。领域持续期间窃取目标10%的核心属性。若在领域内击杀目标，永久保留窃取的属性。"),
]

HEROES["奥拉夫"] = [
    mk_skill("逆流投掷", "Q", "fighter",
        range_override="远程",
        effects=[{"type":"slow","desc":"移动速度减半","duration":2,"target":"敌方"}],
        saving_throw={"attr":"DEX","dc_formula":"8+PROF+STR","on_save":"无效"},
        desc="奋力掷出一柄飞斧，对命中敌人造成1d10+STR挥砍伤害并减速2回合。拾起地上的飞斧可使此技能冷却减少2回合。DEX豁免成功则免疫减速。"),
    mk_skill("残暴打击", "W", "fighter",
        effects=[{"type":"accel","desc":"攻击速度+50%","duration":2,"target":"自身"},
                 {"type":"lifesteal","desc":"获得20%生命偷取","duration":2,"target":"自身"}],
        desc="进入狂战士之怒，攻击速度+50%，并获得20%生命偷取。造成2d8+STR挥砍伤害。每损失2.5%生命值，治疗效果额外+1%。持续2回合。"),
    mk_skill("鲁莽挥击", "E", "fighter",
        damage_type_override="闪电",
        effects=[{"type":"true_dmg","desc":"此伤害无视减伤与护盾","target":"敌方"}],
        desc="以狂野之力劈出一道不可阻挡的闪电斩击。造成1d8+STR闪电伤害。此伤害为真实伤害，无视一切减伤与护盾效果。施放时自身消耗少量生命值，但若击杀目标则返还消耗。"),
    mk_skill("诸神黄昏", "R", "fighter",
        effects=[{"type":"immune","desc":"免疫一切控制效果","duration":3,"target":"自身"},
                 {"type":"buff","desc":"攻击力+30%，移动速度+20尺","duration":3,"target":"自身"}],
        desc="呼唤弗雷尔卓德的远古诸神之力，化身不可阻挡的毁灭风暴。造成2d10+STR挥砍伤害。免疫一切控制效果，攻击力+30%，移动速度+20尺，持续3回合。激活时被动护甲与魔抗翻倍。"),
]

HEROES["蔚"] = [
    mk_skill("强能冲拳", "Q", "fighter",
        effects=[{"type":"accel","desc":"蓄力后向前冲刺20尺","target":"自身"},
                 {"type":"control","desc":"击退命中的第一个敌人","target":"敌方"}],
        desc="蓄力后向前猛冲20尺，以海克斯铁拳轰击路径上的敌人。造成1d10+STR挥砍伤害并击退首个命中的目标。蓄力越长，伤害与冲刺距离越高（最多翻倍）。"),
    mk_skill("爆弹重拳", "W", "fighter",
        effects=[{"type":"sunder","desc":"目标护甲降低20%","duration":2,"target":"敌方"},
                 {"type":"accel","desc":"攻击速度+30%","duration":2,"target":"自身"}],
        desc="连续的铁拳轰击撕裂目标的防御。造成2d8+STR挥砍伤害。每第三次对同一目标的攻击触发爆弹效果：目标护甲降低20%，自身攻击速度+30%，持续2回合。"),
    mk_skill("透体之劲", "E", "fighter",
        range_override="远程",
        effects=[{"type":"aoe","desc":"冲击波穿透目标对后方敌人造成半额伤害","target":"敌方"}],
        desc="拳力透体而出，释放一道锥形冲击波穿透目标。造成1d8+STR挥砍伤害，并对目标身后15尺锥形范围内的敌人造成半额伤害。最多储存2层充能。"),
    mk_skill("天霸横空烈轰", "R", "fighter",
        effects=[{"type":"control","desc":"将目标击飞至空中并压制","duration":1,"target":"敌方"},
                 {"type":"accel","desc":"不可阻挡地冲向目标","target":"自身"}],
        desc="锁定一名敌人，不可阻挡地冲破一切阻拦冲向目标——击飞路径上所有敌人。造成2d10+STR挥砍伤害，并将主目标压制于地面1回合。沿途被撞到的敌人受到半额伤害并被击退。"),
]

# ── ASSASSINS (6) ──
HEROES["卡特琳娜"] = [
    mk_skill("弹射之刃", "Q", "assassin",
        damage_type_override="穿刺",
        effects=[{"type":"vuln","desc":"标记目标2回合，攻击被标记目标造成额外伤害","duration":2,"target":"敌方"}],
        desc="投掷一柄淬毒匕首，在敌人之间弹射。造成1d10+DEX穿刺伤害并标记目标。匕首每次弹射伤害递减10%，最多弹射3次。攻击被标记目标消耗标记并造成额外1d6伤害。"),
    mk_skill("伺机待发", "W", "assassin",
        effects=[{"type":"accel","desc":"向空中抛出一柄匕首，移动速度+30尺","duration":2,"target":"自身"}],
        desc="向空中抛出一柄匕首，获得短暂爆发性移速加成。造成2d8+DEX挥砍伤害。匕首2回合后掉落至地面，对周围敌人造成伤害。拾起匕首可刷新此技能冷却。"),
    mk_skill("瞬步", "E", "assassin",
        effects=[{"type":"accel","desc":"瞬间闪现到目标身旁","target":"自身"}],
        desc="化为一道残影，瞬间闪现到目标身旁发动突刺。造成1d8+DEX挥砍伤害。若目标是敌方匕首，拾起匕首并对此技能冷却减半。"),
    mk_skill("死亡莲华", "R", "assassin",
        effects=[{"type":"aoe","desc":"高速旋转向周围所有敌人投掷匕首","target":"敌方"}],
        desc="化身死亡旋风，以不可思议的速度向周围所有敌人投掷淬毒匕首。造成4d6+DEX挥砍伤害，持续2回合。每回合最多命中3个目标。施放期间无法移动，但可随时中断。"),
]

HEROES["泰隆"] = [
    mk_skill("诺克萨斯式外交", "Q", "assassin",
        damage_type_override="穿刺",
        effects=[{"type":"execute","desc":"近战距离时暴击率+50%","target":"敌方"},
                 {"type":"heal","desc":"击杀目标时回复少量生命","target":"自身"}],
        desc="跃向敌人发动一记精准的刺杀突刺。造成1d10+DEX穿刺伤害。若在近战距离施放，暴击率+50%。以此技能击杀目标时回复1d8生命值。"),
    mk_skill("斩草除根", "W", "assassin",
        damage_type_override="穿刺",
        effects=[{"type":"slow","desc":"移动速度减半","duration":1,"target":"敌方"}],
        saving_throw={"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"无效"},
        desc="掷出一排扇形的刺客飞刀，短暂延迟后收回。造成2d8+DEX穿刺伤害。飞刀命中减速1回合；收回时再次造成伤害。DEX豁免成功则无视减速效果。"),
    mk_skill("刺客之道", "E", "assassin",
        action="附赠动作",
        range_override="自身",
        target_override="自身",
        effects=[{"type":"accel","desc":"翻越地形障碍，移动速度+20尺","duration":1,"target":"自身"}],
        desc="以超凡的身手翻越地形障碍物。造成1d8+DEX挥砍伤害（落地时对周围敌人）。同一地形在3回合内不可再次翻越。翻越后移动速度+20尺，持续1回合。"),
    mk_skill("暗影突袭", "R", "assassin",
        effects=[{"type":"invis","desc":"进入隐形状态并获得移动速度加成","duration":2,"target":"自身"},
                 {"type":"accel","desc":"移动速度+40尺","duration":2,"value":40,"target":"自身"}],
        desc="散开一圈环形飞刀并进入隐形状态，移动速度+40尺，持续2回合。飞刀收回时穿过所有被击中的敌人，造成4d6+DEX挥砍伤害。隐形状态下首次攻击或施法会提前显形。"),
]

HEROES["乐芙兰"] = [
    mk_skill("恶意魔印", "Q", "assassin",
        damage_type_override="力场",
        effects=[{"type":"vuln","desc":"标记目标，下次技能消耗标记造成额外伤害","target":"敌方"}],
        desc="向目标投射一枚恶意魔印，造成1d10+DEX力场伤害并施加标记。若目标身上已有标记，消耗标记造成双倍伤害并使目标沉默1回合。"),
    mk_skill("魔影迷踪", "W", "assassin",
        damage_type_override="力场",
        effects=[{"type":"accel","desc":"冲刺至目标位置，可在2回合内再次激活返回原位","target":"自身"}],
        desc="化为一道魔影向前冲刺，对落点周围敌人造成2d8+DEX力场伤害。2回合内可再次激活此技能，瞬间返回起始位置。"),
    mk_skill("幻影锁链", "E", "assassin",
        damage_type_override="力场",
        effects=[{"type":"control","desc":"锁链束缚目标，无法移动","duration":1,"target":"敌方"}],
        saving_throw={"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"无效"},
        desc="掷出一道以太锁链链接目标。造成1d8+DEX力场伤害。若目标在下一回合结束时仍未脱离锁链范围，则被束缚1回合并再次受到伤害。DEX豁免成功则挣脱锁链。"),
    mk_skill("故技重施", "R", "assassin",
        damage_type_override="力场",
        effects=[{"type":"buff","desc":"复制上一个施放的技能，伤害与效果翻倍","target":"自身"}],
        desc="完美复现上一个施放的技能——但威力更盛。造成4d6+DEX力场伤害（若复制恶意魔印）或对应技能翻倍效果。复制的魔影迷踪可用于返回更远的原位。"),
]

HEROES["雷恩加尔"] = [
    mk_skill("残忍无情", "Q", "assassin",
        effects=[{"type":"buff","desc":"下次攻击必定暴击","target":"自身"},
                 {"type":"accel","desc":"攻击速度+40%","duration":2,"target":"自身"}],
        desc="以野兽般的狂暴猛击目标。造成1d10+DEX挥砍伤害。强化时：下次攻击必定暴击，且攻击速度+40%持续2回合。"),
    mk_skill("战争咆哮", "W", "assassin",
        effects=[{"type":"heal","desc":"回复最近2回合所受伤害的50%","target":"自身"},
                 {"type":"cleanse","desc":"移除所有控制效果","target":"自身"}],
        desc="发出震耳欲聋的战吼，造成2d8+DEX挥砍伤害。回复最近2回合内所受伤害的50%。强化时：额外移除所有控制与负面效果。"),
    mk_skill("套索打击", "E", "assassin",
        range_override="远程",
        effects=[{"type":"slow","desc":"移动速度减半","duration":2,"target":"敌方"}],
        saving_throw={"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"无效"},
        desc="投掷一记浸毒的流星索。造成1d8+DEX挥砍伤害并减速2回合。强化时：改为束缚目标，使其完全无法移动。DEX豁免成功则免疫束缚/减速。"),
    mk_skill("狩猎律动", "R", "assassin",
        effects=[{"type":"invis","desc":"进入伪装状态","duration":3,"target":"自身"},
                 {"type":"accel","desc":"移动速度+40尺","duration":3,"value":40,"target":"自身"},
                 {"type":"vuln","desc":"获得最近敌人的真实视野","target":"敌方"}],
        desc="进入终极狩猎姿态——伪装潜行、感知周围所有敌人的位置。造成4d6+DEX挥砍伤害（跃向目标的破隐一击）。持续3回合或发动攻击后显形。自动标记距离最近的敌人。"),
]

HEROES["伊芙琳"] = [
    mk_skill("憎恨之刺", "Q", "assassin",
        damage_type_override="黯蚀",
        effects=[{"type":"vuln","desc":"被尖刺命中的目标受到后续技能额外伤害","duration":2,"target":"敌方"}],
        desc="从地底召唤三根憎恨尖刺，穿刺路径上的敌人。造成1d10+DEX黯蚀伤害并标记目标。接下来3次对标记目标的攻击或技能造成额外1d4黯蚀伤害。"),
    mk_skill("引诱", "W", "assassin",
        effects=[{"type":"control","desc":"诅咒目标，攻击后魅惑使其走向你","duration":2,"target":"敌方"},
                 {"type":"sunder","desc":"被诅咒目标魔抗降低","duration":2,"target":"敌方"}],
        saving_throw={"attr":"WIS","dc_formula":"8+PROF+DEX","on_save":"无效"},
        desc="对一名敌人降下诅咒魔印。造成2d8+DEX挥砍伤害。2回合后魔印成熟，攻击或技能命中目标将魅惑其走向你，持续1回合，同时降低魔抗。WIS豁免成功则无视魅惑与降抗。"),
    mk_skill("鞭笞", "E", "assassin",
        effects=[{"type":"accel","desc":"向前突刺15尺","target":"自身"}],
        desc="挥动恶魔之尾向前猛击。造成1d8+DEX挥砍伤害。强化时：向前突刺15尺，对路径上所有敌人造成伤害。"),
    mk_skill("最终抚慰", "R", "assassin",
        damage_type_override="黯蚀",
        effects=[{"type":"execute","desc":"目标生命<30%时伤害翻倍","target":"敌方"},
                 {"type":"accel","desc":"施放后向后闪烁30尺并进入隐身","target":"自身"}],
        desc="化为不可选取的恶魔形态，对前方扇形区域降下死亡裁决。造成4d6+DEX黯蚀伤害。目标生命低于30%时伤害翻倍。施放后向后闪烁30尺并进入隐身状态，持续2回合。"),
]

HEROES["菲兹"] = [
    mk_skill("淘气打击", "Q", "assassin",
        damage_type_override="穿刺",
        effects=[{"type":"accel","desc":"穿过目标出现在其身后","target":"自身"}],
        desc="以三叉戟为锋刃，穿过目标的身体出现在其身后。造成1d10+DEX穿刺伤害。此攻击附带所有武器特效。"),
    mk_skill("海石三叉戟", "W", "assassin",
        effects=[{"type":"dot","desc":"目标流血，每回合受到1d4额外伤害","duration":2,"target":"敌方"},
                 {"type":"execute","desc":"对生命低于20%的目标伤害+50%","target":"敌方"}],
        desc="以蕴含海洋魔力的三叉戟撕裂目标。造成2d8+DEX挥砍伤害，并使目标流血2回合。攻击生命低于20%的目标时伤害+50%。击杀目标后此技能冷却归零。"),
    mk_skill("古灵精怪", "E", "assassin",
        effects=[{"type":"accel","desc":"跳跃至空中免疫一切伤害与效果","duration":1,"target":"自身"}],
        desc="以三叉戟撑地跃至空中，在此期间免疫一切伤害与效果。再次激活可提前落下，对周围敌人造成1d8+DEX挥砍伤害并减速1回合。"),
    mk_skill("巨鲨强袭", "R", "assassin",
        damage_type_override="穿刺",
        effects=[{"type":"control","desc":"巨鲨吞噬目标，击飞并眩晕","duration":1,"target":"敌方"},
                 {"type":"slow","desc":"鲨鱼游过的区域使敌人减速","duration":2,"target":"敌方"}],
        saving_throw={"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"半伤"},
        desc="投掷一只深海小鱼引诱巨鲨破土而出——鱼饵飞行距离越远，召唤的巨鲨越庞大。造成4d6+DEX穿刺伤害，击飞范围内所有敌人并眩晕1回合，随后鲨鱼游过的区域减速2回合。DEX豁免成功则伤害减半且免疫击飞。",
        aoe_radius=20),
]

# ── MAGES (6) ──
HEROES["瑞兹"] = [
    mk_skill("超负荷", "Q", "mage",
        damage_type_override="闪电",
        effects=[{"type":"buff","desc":"消耗全部符文充能，每层+1d4伤害","target":"自身"}],
        saving_throw={"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"},
        desc="发射一道纯粹的奥术脉冲，造成1d8+INT闪电伤害。消耗所有符文充能层数，每层额外+1d4伤害。符文充能由W/E技能叠加，最多2层。DEX豁免成功则伤害减半。"),
    mk_skill("符文禁锢", "W", "mage",
        damage_type_override="闪电",
        effects=[{"type":"control","desc":"禁锢目标，无法移动","duration":1,"target":"敌方"},
                 {"type":"buff","desc":"获得一层符文充能","target":"自身"}],
        saving_throw={"attr":"CON","dc_formula":"8+PROF+INT","on_save":"无效"},
        desc="以奥术符文瞬间禁锢一名敌人。造成2d6+INT闪电伤害，目标无法移动1回合。获得一层符文充能。CON豁免成功则免疫禁锢。"),
    mk_skill("法术涌动", "E", "mage",
        damage_type_override="闪电",
        effects=[{"type":"vuln","desc":"标记目标，使其受到的下次技能伤害翻倍","duration":1,"target":"敌方"},
                 {"type":"buff","desc":"获得一层符文充能","target":"自身"}],
        saving_throw={"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"},
        desc="释放一道弹射的奥术能量球，在敌人之间传播。造成2d6+INT闪电伤害。获得一层符文充能。被标记的目标受到的下一个技能伤害翻倍并扩散法术涌动至周围敌人。DEX豁免成功则伤害减半。"),
    mk_skill("曲境折跃", "R", "mage",
        range_override="自身",
        target_override="自身",
        effects=[{"type":"accel","desc":"开启传送门，将自身及周围友军传送至远处","target":"自身"}],
        desc="展开一道通往远方的奥术传送门，引导1回合后将自身及15尺内所有友军传送至目标位置。造成4d6+INT闪电伤害（对传送落点周围敌人）。引导期间受硬控即中断。"),
]

HEROES["弗拉基米尔"] = [
    mk_skill("鲜血转换", "Q", "mage",
        damage_type_override="黯蚀",
        effects=[{"type":"heal","desc":"吸取目标生命力回复自身","target":"自身"},
                 {"type":"buff","desc":"强化：下一次鲜血转换伤害+50%且治疗翻倍","duration":1,"target":"自身"}],
        desc="从目标体内抽取鲜血精华，造成1d8+INT黯蚀伤害并回复等量生命值。每施放两次后，第三次进入猩红冲刺：伤害+50%且治疗翻倍，移动速度短暂提升。"),
    mk_skill("血红之池", "W", "mage",
        range_override="自身",
        target_override="自身",
        effects=[{"type":"invis","desc":"化为血池，无法被选中","duration":1,"target":"自身"},
                 {"type":"slow","desc":"血池中的敌人被减速","duration":1,"target":"敌方"}],
        desc="将自己溶解为一滩不可被选中（免疫一切攻击与技能）的血池，持续1回合。站在血池中的敌人受到2d6+INT黯蚀伤害并被减速。血池结束时弗拉基米尔重新凝聚。"),
    mk_skill("血之潮汐", "E", "mage",
        damage_type_override="黯蚀",
        effects=[{"type":"slow","desc":"所有被击中的敌人减速","duration":2,"target":"敌方"}],
        saving_throw={"attr":"CON","dc_formula":"8+PROF+INT","on_save":"半伤"},
        desc="持续蓄力——消耗自身生命来凝聚一颗血球，释放时对周围所有敌人造成2d6+INT黯蚀伤害。蓄力越久伤害越高（最高翻倍），但自身消耗也越大。被命中的敌人减速2回合。CON豁免成功则伤害减半。",
        aoe_radius=15),
    mk_skill("血之瘟疫", "R", "mage",
        damage_type_override="黯蚀",
        effects=[{"type":"dot","desc":"被瘟疫感染的敌人受到持续伤害","duration":2,"target":"敌方"},
                 {"type":"heal","desc":"每个被感染的敌人为你回复生命","target":"自身"}],
        saving_throw={"attr":"CON","dc_formula":"8+PROF+INT","on_save":"半伤"},
        desc="在目标区域引爆一场猩红瘟疫，感染范围内的所有敌人。造成4d6+INT黯蚀伤害。受感染的敌人在2回合内每回合受到额外1d6黯蚀伤害，每个被感染的敌人为你回复1d4生命值。CON豁免成功则伤害减半。",
        aoe_radius=20),
]

HEROES["卡西奥佩娅"] = [
    mk_skill("瘟毒爆炸", "Q", "mage",
        damage_type_override="毒素",
        effects=[{"type":"dot","desc":"中毒，每回合受到1d4毒素伤害","duration":2,"target":"敌方"},
                 {"type":"accel","desc":"命中英雄时移动速度+20尺","duration":1,"target":"自身"}],
        saving_throw={"attr":"CON","dc_formula":"8+PROF+INT","on_save":"半伤"},
        desc="在目标脚下引爆一滩剧毒泥沼，造成1d8+INT毒素伤害。中毒目标每回合受到1d4毒素伤害，持续2回合。命中敌方英雄时自身移动速度+20尺，持续1回合。CON豁免成功则伤害减半。"),
    mk_skill("剧毒迷雾", "W", "mage",
        damage_type_override="毒素",
        effects=[{"type":"slow","desc":"站在毒雾中的敌人移动速度减半且无法使用位移","duration":2,"target":"敌方"},
                 {"type":"dot","desc":"每回合受到1d4毒素伤害","duration":2,"target":"敌方"}],
        saving_throw={"attr":"CON","dc_formula":"8+PROF+INT","on_save":"无效"},
        desc="喷吐一大片剧毒瘴气笼罩战场。造成2d6+INT毒素伤害。毒雾持续3回合，站在其中的敌人减速且被缚地（无法使用位移能力），每回合受到1d4毒素伤害。CON豁免成功则无视缚地效果。",
        aoe_radius=20),
    mk_skill("双生毒牙", "E", "mage",
        damage_type_override="毒素",
        effects=[{"type":"execute","desc":"攻击中毒目标时伤害+50%并回复生命","target":"敌方"},
                 {"type":"heal","desc":"命中中毒目标时回复1d6生命","target":"自身"}],
        desc="以闪电般的速度咬向目标，注入蛇毒。造成2d6+INT毒素伤害。若目标正处于中毒状态，伤害+50%并为你回复1d6生命值。击杀目标后返还法力消耗。"),
    mk_skill("石化凝视", "R", "mage",
        damage_type_override="毒素",
        effects=[{"type":"control","desc":"面向你的敌人被石化眩晕","duration":2,"target":"敌方"},
                 {"type":"slow","desc":"背对你的敌人被减速","duration":2,"target":"敌方"}],
        saving_throw={"attr":"CON","dc_formula":"8+PROF+INT","on_save":"无效"},
        desc="睁开通往异界的蛇瞳，释放一道锥形的石化魔光。造成4d6+INT毒素伤害。面向你的敌人被石化（完全无法行动）2回合；背对你的敌人减速2回合。CON豁免成功则免疫石化但仍被减速。",
        aoe_radius=30),
]

HEROES["布兰德"] = [
    mk_skill("火焰烙印", "Q", "mage",
        damage_type_override="火焰",
        effects=[{"type":"control","desc":"命中已点燃的目标时眩晕","duration":1,"target":"敌方"}],
        saving_throw={"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"},
        desc="射出一发浓缩的火焰飞弹，造成1d8+INT火焰伤害。若目标已被布兰德的技能点燃，则额外眩晕1回合。DEX豁免成功则伤害减半。"),
    mk_skill("烈焰之柱", "W", "mage",
        damage_type_override="火焰",
        effects=[{"type":"dot","desc":"点燃目标，每回合受1d4火焰伤害","duration":2,"target":"敌方"}],
        saving_throw={"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"},
        desc="在目标脚下召唤一道冲天火柱，造成2d6+INT火焰伤害。点燃目标2回合。已点燃的目标受到额外25%伤害。DEX豁免成功则伤害减半。",
        aoe_radius=10),
    mk_skill("烈火燃烧", "E", "mage",
        damage_type_override="火焰",
        effects=[{"type":"aoe","desc":"火焰扩散至目标周围所有敌人","target":"敌方"},
                 {"type":"dot","desc":"点燃所有被扩散命中的目标","duration":2,"target":"敌方"}],
        desc="对一名敌人释放纯粹的烈火冲击。造成2d6+INT火焰伤害。若目标已被点燃，火焰扩散至其周围15尺所有敌人，造成等量伤害并点燃。"),
    mk_skill("烈焰风暴", "R", "mage",
        damage_type_override="火焰",
        effects=[{"type":"dot","desc":"火焰在敌人之间反复弹跳","duration":2,"target":"敌方"}],
        saving_throw={"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"},
        desc="释放一颗在敌人之间疯狂弹跳的烈焰火种。造成4d6+INT火焰伤害，并在敌人之间弹跳最多5次。每次弹跳优先命中未被点燃的目标。同一目标可被多次弹跳命中（后续伤害递减30%）。DEX豁免成功则伤害减半。"),
]

HEROES["维克托"] = [
    mk_skill("虹吸能量", "Q", "mage",
        damage_type_override="闪电",
        effects=[{"type":"shield","desc":"获得护盾","duration":1,"value_formula":"2*LVL+INT","target":"自身"},
                 {"type":"buff","desc":"下次普通攻击附加额外闪电伤害","target":"自身"}],
        desc="以机械臂发射一道能量虹吸射线，造成1d8+INT闪电伤害。获得护盾，持续1回合。强化：护盾量+60%，之后获得移动速度加成。"),
    mk_skill("重力场", "W", "mage",
        range_override="远程",
        target_override="范围",
        effects=[{"type":"slow","desc":"力场内的敌人持续减速","duration":1,"target":"敌方"},
                 {"type":"control","desc":"在力场内停留1回合以上的敌人被眩晕","duration":1,"target":"敌方"}],
        saving_throw={"attr":"CON","dc_formula":"8+PROF+INT","on_save":"无效"},
        desc="部署一个持续3回合的重力禁锢装置，对进入区域的敌人造成2d6+INT闪电伤害并减速。区域内停留超过1回合的敌人被眩晕1回合。CON豁免成功则免疫眩晕。",
        aoe_radius=15),
    mk_skill("死亡射线", "E", "mage",
        damage_type_override="火焰",
        effects=[{"type":"dot","desc":"射线经过的地面灼烧2回合","duration":2,"target":"敌方"}],
        saving_throw={"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"},
        desc="从第三只机械臂发射一道可自由调整角度的毁灭射线，切割战场。造成2d6+INT火焰伤害。强化：射线在地面留下灼烧轨迹，站在上面的敌人每回合受到1d4火焰伤害。DEX豁免成功则伤害减半。"),
    mk_skill("混乱风暴", "R", "mage",
        damage_type_override="闪电",
        effects=[{"type":"dot","desc":"风暴持续3回合，每回合对范围内敌人造成伤害","duration":3,"target":"敌方"}],
        saving_throw={"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"},
        desc="召唤一团由纯粹奥术能量构成的奇异点雷暴。造成4d6+INT闪电伤害。风暴持续3回合，每回合对范围内敌人造成2d6闪电伤害。维克托可用附赠动作移动风暴位置。DEX豁免成功则伤害减半。",
        aoe_radius=20),
]

HEROES["卡尔萨斯"] = [
    mk_skill("荒芜", "Q", "mage",
        damage_type_override="黯蚀",
        effects=[{"type":"execute","desc":"命中单体敌人时伤害翻倍","target":"敌方"}],
        saving_throw={"attr":"DEX","dc_formula":"8+PROF+INT","on_save":"半伤"},
        desc="在目标脚下引爆一枚亡灵地雷。造成1d8+INT黯蚀伤害。若只命中一个敌人，伤害翻倍。DEX豁免成功则伤害减半。"),
    mk_skill("痛苦之墙", "W", "mage",
        damage_type_override="黯蚀",
        range_override="远程",
        target_override="范围",
        effects=[{"type":"slow","desc":"穿越墙体的敌人移动速度减半","duration":2,"target":"敌方"},
                 {"type":"sunder","desc":"穿越墙体的敌人魔抗降低","duration":2,"target":"敌方"}],
        desc="竖起一道幽魂哀嚎之墙，穿过墙体的敌人受到2d6+INT黯蚀伤害，移动速度减半且魔抗降低，持续2回合。墙体持续3回合。"),
    mk_skill("污染", "E", "mage",
        damage_type_override="黯蚀",
        range_override="自身",
        target_override="范围",
        effects=[{"type":"dot","desc":"周围的敌人每回合受到黯蚀伤害","duration":3,"target":"敌方"}],
        desc="开启亡灵光环——以自身为中心散发亵渎能量场。造成2d6+INT黯蚀伤害，且每回合对范围内敌人造成1d6黯蚀伤害。关闭污染时返还部分法力。",
        aoe_radius=15),
    mk_skill("安魂曲", "R", "mage",
        damage_type_override="黯蚀",
        range_override="远程",
        target_override="范围",
        effects=[{"type":"true_dmg","desc":"无视距离，对场上所有敌方英雄降下死亡","target":"敌方"}],
        saving_throw={"attr":"WIS","dc_formula":"8+PROF+INT","on_save":"半伤"},
        desc="吟唱死亡颂歌——3回合引导后，对战场上所有敌方英雄同时降下死亡裁决。造成4d6+INT黯蚀伤害。无视距离与视野限制。WIS豁免成功则伤害减半。引导期间可被硬控打断。",
        aoe_radius=999),
]

# ── MARKSMEN (3) ──
HEROES["德莱文"] = [
    mk_skill("旋转飞斧", "Q", "marksman",
        effects=[{"type":"buff","desc":"下次攻击伤害+50%，斧头弹回空中可接住刷新","target":"自身"}],
        desc="开始旋转一柄双手飞斧——荣耀行刑官的招牌技艺。造成1d8+DEX穿刺伤害，但下一击伤害+50%。斧头命中后弹向空中，移动至落点可接住飞斧，刷新此效果。最多同时持有2柄旋转飞斧。"),
    mk_skill("血性冲刺", "W", "marksman",
        effects=[{"type":"accel","desc":"移动速度+30尺，攻击速度+40%","duration":2,"target":"自身"}],
        desc="肾上腺素飙升——移动速度+30尺，攻击速度+40%，持续2回合。造成2d6+DEX穿刺伤害。接住一柄旋转飞斧时刷新此技能冷却。"),
    mk_skill("开道利斧", "E", "marksman",
        effects=[{"type":"control","desc":"击退目标15尺并减速","duration":2,"target":"敌方"}],
        saving_throw={"attr":"STR","dc_formula":"8+PROF+DEX","on_save":"无效"},
        desc="用力掷出两柄飞斧，将路径上的敌人推向两侧。造成1d8+DEX穿刺伤害，击退15尺并减速2回合。STR豁免成功则不被击退但仍被减速。"),
    mk_skill("冷血追命", "R", "marksman",
        range_override="远程",
        target_override="范围",
        effects=[{"type":"execute","desc":"斧头命中低生命目标时伤害提升","target":"敌方"}],
        saving_throw={"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"半伤"},
        desc="全力掷出两柄巨型回旋利斧，横跨整个战场。造成3d8+DEX穿刺伤害。利斧抵达地图尽头后折返，返程再次造成伤害。命中越多的敌人伤害越高。DEX豁免成功则伤害减半。"),
]

HEROES["烬"] = [
    mk_skill("曼舞手雷", "Q", "marksman",
        damage_type_override="火焰",
        effects=[{"type":"aoe","desc":"手雷在敌人之间弹跳，每次弹跳伤害+35%","target":"敌方"}],
        desc="投掷一颗精密计算弹道的手雷，在敌人之间优雅弹跳。造成1d8+DEX火焰伤害。最多弹跳4次，每次弹跳伤害+35%。若手雷击杀目标，后续弹跳伤害翻倍。"),
    mk_skill("致命华彩", "W", "marksman",
        range_override="远程",
        effects=[{"type":"control","desc":"禁锢被标记的敌人","duration":1,"target":"敌方"}],
        saving_throw={"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"无效"},
        desc="射出一发超远程的精准弹丸。造成2d6+DEX穿刺伤害。若目标已被烬或友军的攻击标记，则额外禁锢1回合。DEX豁免成功则免疫禁锢。"),
    mk_skill("万众倾倒", "E", "marksman",
        damage_type_override="火焰",
        effects=[{"type":"slow","desc":"踩中陷阱的敌人减速","duration":2,"target":"敌方"},
                 {"type":"dot","desc":"陷阱爆炸后绽放莲花持续造成伤害","target":"敌方"}],
        saving_throw={"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"半伤"},
        desc="放置一朵隐形的莲花陷阱，敌人踩中后减速2回合并在短暂延迟后爆炸，对周围敌人造成1d8+DEX火焰伤害。击杀敌方英雄后，在其尸体上自动绽放一朵莲花陷阱。DEX豁免成功则伤害减半。"),
    mk_skill("完美谢幕", "R", "marksman",
        range_override="远程",
        target_override="范围",
        effects=[{"type":"slow","desc":"被子弹命中的敌人减速","duration":1,"target":"敌方"},
                 {"type":"execute","desc":"第四发子弹必定暴击且对低生命目标伤害翻倍","target":"敌方"}],
        saving_throw={"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"半伤"},
        desc="架起名为「低语」的传奇狙击步枪，展开一张扇形杀戮地带。共4发子弹，每发造成3d8+DEX穿刺伤害，命中的敌人减速1回合。第四发——也是最后一发——必定暴击，且目标生命越低伤害越高（最高翻倍）。DEX豁免成功则伤害减半（第四发不减半）。"),
]

HEROES["厄运小姐"] = [
    mk_skill("一箭双雕", "Q", "marksman",
        effects=[{"type":"aoe","desc":"子弹穿透首个目标后弹射至后方敌人","target":"敌方"}],
        desc="射出一发跳弹——命中首个敌人后弹射至其身后的目标。造成1d8+DEX穿刺伤害。若首段击杀目标，弹射伤害翻倍。弹射优先命中英雄。"),
    mk_skill("大步流星", "W", "marksman",
        effects=[{"type":"accel","desc":"移动速度+30尺，攻击速度+60%","duration":2,"target":"自身"}],
        desc="赏金猎人的脚步从不停歇。造成2d6+DEX穿刺伤害。被动：若5回合内未受到伤害，获得移动速度+30尺。主动激活：攻击速度+60%，持续2回合。"),
    mk_skill("枪林弹雨", "E", "marksman",
        range_override="远程",
        target_override="范围",
        effects=[{"type":"slow","desc":"弹幕区域内的敌人移动速度减半","duration":2,"target":"敌方"}],
        saving_throw={"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"半伤"},
        desc="呼叫海盗船炮火覆盖目标区域。造成1d8+DEX穿刺伤害。弹幕持续3回合，每回合对区域内的敌人造成伤害并减速。DEX豁免成功则伤害减半。",
        aoe_radius=20),
    mk_skill("弹幕时间", "R", "marksman",
        range_override="远程",
        target_override="范围",
        effects=[{"type":"aoe","desc":"向前方锥形区域倾泻毁灭性弹幕","target":"敌方"}],
        saving_throw={"attr":"DEX","dc_formula":"8+PROF+DEX","on_save":"半伤"},
        desc="莎拉双枪齐鸣，向前方锥形区域倾泻数百发子弹的毁灭弹幕。造成3d8+DEX穿刺伤害。弹幕共12波，持续2回合，每波可触发暴击。DEX豁免成功则伤害减半。施放期间无法移动但可随时中断。",
        aoe_radius=30),
]

# ── SUPPORTS (3) ──
HEROES["索拉卡"] = [
    mk_skill("流星坠落", "Q", "support",
        effects=[{"type":"heal","desc":"命中敌方英雄时回复自身生命","target":"自身"},
                 {"type":"slow","desc":"被流星击中的敌人减速","duration":1,"target":"敌方"}],
        saving_throw={"attr":"DEX","dc_formula":"8+PROF+WIS","on_save":"半伤"},
        desc="召唤星辰碎片坠落于目标区域。造成1d6+WIS光耀伤害并减速1回合。命中敌方英雄时自身回复1d8生命值。DEX豁免成功则伤害减半。"),
    mk_skill("星之灌注", "W", "support",
        effects=[{"type":"heal","desc":"为友方目标回复大量生命","target":"自身"}],
        desc="引导星辰之力灌注一名友方单位，为其回复2d6+WIS生命值。索拉卡自身消耗少量生命值施放此技能。若自身处于流星坠落回复状态，则消耗减半。"),
    mk_skill("星体结界", "E", "support",
        range_override="远程",
        target_override="范围",
        effects=[{"type":"silence","desc":"结界内的敌人无法施法","duration":1,"target":"敌方"},
                 {"type":"control","desc":"结界消失时仍在其中的敌人被禁锢","duration":1,"target":"敌方"}],
        saving_throw={"attr":"WIS","dc_formula":"8+PROF+WIS","on_save":"无效"},
        desc="在目标区域布下一片星辰结界。造成1d6+WIS光耀伤害。结界持续2回合，区域内的敌人被沉默（无法使用法术技能）。结界消失时仍在其中的敌人被禁锢1回合。WIS豁免成功则无视禁锢效果。",
        aoe_radius=15),
    mk_skill("祈愿", "R", "support",
        range_override="远程",
        target_override="范围",
        effects=[{"type":"heal","desc":"为战场上所有友方英雄回复大量生命","target":"自身"},
                 {"type":"cleanse","desc":"移除所有友方英雄的重伤效果","target":"自身"}],
        desc="向星空发出最虔诚的祈祷——战场上所有友方英雄回复3d6+WIS生命值。友方生命低于40%时治疗效果+50%。同时移除所有友方英雄身上的重伤效果。无视距离与视野。"),
]

HEROES["娑娜"] = [
    mk_skill("英勇赞美诗", "Q", "support",
        effects=[{"type":"buff","desc":"自身与周围友方下次攻击附加额外光耀伤害","duration":1,"target":"自身"}],
        desc="弹奏激昂的旋律，对最近的两个敌人造成1d6+WIS光耀伤害。自身与周围友方获得光环：下次攻击附加额外1d4光耀伤害，持续1回合。"),
    mk_skill("坚毅咏叹调", "W", "support",
        effects=[{"type":"heal","desc":"治疗自身与伤势最重的友方","target":"自身"},
                 {"type":"shield","desc":"为周围友方提供护盾","duration":2,"value_formula":"2*LVL+WIS","target":"自身"}],
        desc="演奏抚慰的旋律，治疗自身与一名伤势最重的友方2d6+WIS生命值。周围友方获得护盾，持续2回合。"),
    mk_skill("迅捷奏鸣曲", "E", "support",
        effects=[{"type":"accel","desc":"自身与周围友方移动速度+20尺","duration":2,"target":"自身"}],
        desc="演绎轻快的旋律，造成1d6+WIS光耀伤害。自身与周围友方移动速度+20尺，持续2回合。"),
    mk_skill("狂舞终乐章", "R", "support",
        range_override="远程",
        target_override="范围",
        effects=[{"type":"control","desc":"强迫前方锥形区域内敌人起舞（眩晕）","duration":1,"target":"敌方"}],
        saving_throw={"attr":"WIS","dc_formula":"8+PROF+WIS","on_save":"无效"},
        desc="奏响不可抗拒的终极乐章——前方锥形区域内所有敌人被迫起舞，完全丧失行动能力。造成3d6+WIS光耀伤害并眩晕1回合。WIS豁免成功则免疫眩晕但仍受伤害。",
        aoe_radius=25),
]

HEROES["娜美"] = [
    mk_skill("碧波之牢", "Q", "support",
        range_override="远程",
        target_override="范围",
        effects=[{"type":"control","desc":"将敌人困在水泡中，无法移动或行动","duration":1,"target":"敌方"}],
        saving_throw={"attr":"DEX","dc_formula":"8+PROF+WIS","on_save":"无效"},
        desc="向目标区域掷出一个巨大的气泡水牢。造成1d6+WIS光耀伤害，命中的敌人被囚禁在水泡中1回合。DEX豁免成功则免疫囚禁。"),
    mk_skill("冲击之潮", "W", "support",
        effects=[{"type":"heal","desc":"治疗友方或伤害敌方，在目标之间弹跳","target":"自身"}],
        desc="释放一道潮汐能量流，在友方与敌方之间交替弹跳。对友方回复2d6+WIS生命值，对敌方造成等量光耀伤害。每次弹跳效果递减15%。最多弹跳3次。"),
    mk_skill("唤潮之佑", "E", "support",
        effects=[{"type":"buff","desc":"强化友方：接下来3次攻击附加额外光耀伤害与减速","duration":2,"target":"自身"}],
        desc="召唤潮汐之力祝福一名友方英雄。造成1d6+WIS光耀伤害。目标的接下来3次攻击附加额外1d4光耀伤害并使目标减速1回合。持续2回合。"),
    mk_skill("怒涛之啸", "R", "support",
        range_override="远程",
        target_override="范围",
        effects=[{"type":"control","desc":"巨浪击飞路径上所有敌人","duration":1,"target":"敌方"},
                 {"type":"slow","desc":"被巨浪波及的敌人减速","duration":2,"target":"敌方"}],
        saving_throw={"attr":"STR","dc_formula":"8+PROF+WIS","on_save":"无效"},
        desc="召唤一道横跨战场的滔天巨浪，击飞路径上所有敌人并造成3d6+WIS光耀伤害。友方被巨浪触及则获得双倍唤潮之佑效果。巨浪距离越远速度越快。STR豁免成功则不被击飞但仍被减速。"),
]

# ── TANKS (2) ──
HEROES["蕾欧娜"] = [
    mk_skill("破晓之盾", "Q", "tank",
        effects=[{"type":"control","desc":"下次攻击眩晕目标","duration":1,"target":"敌方"}],
        saving_throw={"attr":"CON","dc_formula":"8+PROF+STR","on_save":"无效"},
        desc="以曙光圣盾猛击目标，造成1d10+STR钝击伤害并眩晕1回合。此攻击重置普通攻击计时。CON豁免成功则免疫眩晕。"),
    mk_skill("日蚀", "W", "tank",
        effects=[{"type":"reduce","desc":"护甲与魔抗翻倍","duration":2,"target":"自身"},
                 {"type":"dot","desc":"护盾爆炸对周围敌人造成伤害","target":"敌方"}],
        desc="以太阳之力包裹自身，护甲与魔抗翻倍，持续2回合。造成2d6+STR钝击伤害。持续时间结束后圣盾爆炸，对周围敌人造成额外伤害。"),
    mk_skill("天顶之刃", "E", "tank",
        effects=[{"type":"control","desc":"突进至最后一个命中的敌人身旁并将其禁锢","duration":1,"target":"敌方"}],
        saving_throw={"attr":"DEX","dc_formula":"8+PROF+STR","on_save":"无效"},
        desc="以曙光之刃刺出一道日光束，造成1d8+STR钝击伤害。蕾欧娜突进至最后一个被命中的敌人身旁，并将其短暂禁锢0.5回合。DEX豁免成功则不被禁锢。"),
    mk_skill("日炎耀斑", "R", "tank",
        range_override="远程",
        target_override="范围",
        damage_type_override="光耀",
        effects=[{"type":"control","desc":"中心区域敌人眩晕，外围敌人减速","duration":2,"target":"敌方"}],
        saving_throw={"attr":"CON","dc_formula":"8+PROF+STR","on_save":"无效"},
        desc="召唤一道太阳耀斑轰击战场。中心区域敌人受到2d8+STR光耀伤害并眩晕2回合；外围敌人受到半额伤害并减速2回合。CON豁免成功则免疫眩晕但减速照常。",
        aoe_radius=25),
]

HEROES["布隆"] = [
    mk_skill("寒冬之咬", "Q", "tank",
        damage_type_override="寒冷",
        effects=[{"type":"slow","desc":"移动速度减半","duration":2,"target":"敌方"},
                 {"type":"vuln","desc":"施加一层震荡冰封标记","target":"敌方"}],
        saving_throw={"attr":"CON","dc_formula":"8+PROF+STR","on_save":"无效"},
        desc="从盾牌中喷出一股弗雷尔卓德冻气。造成1d10+STR寒冷伤害，减速2回合并施加一层震荡冰封。任何友方的攻击可叠加此标记；叠满4层后目标被冻结1回合。CON豁免成功则免疫减速。"),
    mk_skill("挺身而出", "W", "tank",
        effects=[{"type":"shield","desc":"跃向友方，为双方提供护甲与魔抗加成","duration":2,"target":"自身"},
                 {"type":"reduce","desc":"自身与目标友方护甲+魔抗提升","duration":2,"target":"自身"}],
        desc="跃向一名友方英雄，以巨盾庇护彼此。造成2d6+STR钝击伤害。自身与目标友方护甲与魔抗提升，持续2回合。"),
    mk_skill("坚不可摧", "E", "tank",
        range_override="自身",
        target_override="自身",
        effects=[{"type":"reduce","desc":"举盾方向受到的伤害减少80%","duration":2,"target":"自身"},
                 {"type":"immune","desc":"完全格挡首个命中盾牌的飞行技能","target":"自身"}],
        desc="举起不可摧毁的远古冰盾，朝向指定方向。造成1d8+STR钝击伤害。来自举盾方向的所有伤害减少80%，且首个命中盾牌的投射物技能被完全格挡。持续2回合。举盾期间可缓慢移动。"),
    mk_skill("冰川裂隙", "R", "tank",
        damage_type_override="寒冷",
        effects=[{"type":"control","desc":"击飞路径上所有敌人","duration":1,"target":"敌方"},
                 {"type":"slow","desc":"裂隙区域持续减速","duration":2,"target":"敌方"}],
        saving_throw={"attr":"STR","dc_formula":"8+PROF+STR","on_save":"无效"},
        desc="以巨盾猛击地面，撕开一道深不见底的冰川裂隙。造成2d8+STR寒冷伤害，击飞路径上所有敌人。裂隙持续3回合，站在上面的敌人减速。首个被击中的敌人被击飞最高。STR豁免成功则不被击飞。",
        aoe_radius=30),
]

# ═══════════════════════════════════════════════════════════
# OUTPUT
# ═══════════════════════════════════════════════════════════

# Validate dice expectancy
def calc_E(hero_skills):
    E = 0
    for sk in hero_skills:
        d = sk["damage"]
        E += d["dice_count"] * (d["dice_size"] + 1) / 2
    return round(E, 1)

ROLE_BANDS = {
    "fighter": (27, 30), "assassin": (32, 34), "mage": (30, 33),
    "marksman": (29, 32), "tank": (24, 27), "support": (24, 27),
}

role_of = {
    "亚托克斯":"fighter","贾克斯":"fighter","泰达米尔":"fighter","莫德凯撒":"fighter",
    "奥拉夫":"fighter","蔚":"fighter",
    "卡特琳娜":"assassin","泰隆":"assassin","乐芙兰":"assassin","雷恩加尔":"assassin",
    "伊芙琳":"assassin","菲兹":"assassin",
    "瑞兹":"mage","弗拉基米尔":"mage","卡西奥佩娅":"mage","布兰德":"mage",
    "维克托":"mage","卡尔萨斯":"mage",
    "德莱文":"marksman","烬":"marksman","厄运小姐":"marksman",
    "索拉卡":"support","娑娜":"support","娜美":"support",
    "蕾欧娜":"tank","布隆":"tank",
}

# EFFECTS VALIDATION
VALID_EFFECTS = {
    "眩晕","控制","束缚","禁锢","击飞","击退","冻结","石化","麻痹",
    "魅惑","恐惧","沉默","震慑","混乱","暗示","制服","干扰","压制",
    "stun","hold","prone","knockback",
    "slow","减速","致盲","目盲",
    "shield","护盾",
    "减伤","防御",
    "heal","治疗","回复","回血",
    "lifesteal","吸血",
    "dot","灼烧","中毒","bleed","burn","poison","持续伤害","痛苦","重伤","剧毒","重创",
    "execute","斩杀","处决",
    "true_dmg","真实伤害","穿透","pierce","true_damage",
    "buff","增益","强化","附魔","攻击增益","狂暴","增援",
    "accel","加速","haste","dash","攻速强化","冲锋",
    "sunder","破甲",
    "vuln","标记","mark","易伤",
    "crit","暴击","暴击强化",
    "reflect","反弹",
    "immune","免疫","免疫控制",
    "invis","隐身","隐形","潜行",
    "cleanse","净化","驱散",
    "revive","复活",
    "aoe","范围攻击",
}

print(f"Generated {len(HEROES)} heroes")
issues = []
for name, skills in HEROES.items():
    E = calc_E(skills)
    role = role_of[name]
    lo, hi = ROLE_BANDS[role]
    if not (lo <= E <= hi):
        issues.append(f"  {name} [{role}] E={E} (band {lo}-{hi}) ***OUT OF BAND***")
    
    # Check effects
    for sk in skills:
        for eff in sk.get("effects", []):
            t = eff.get("type","").strip().lower()
            if t not in VALID_EFFECTS:
                issues.append(f"  {name}/{sk['key']}: effect.type='{eff['type']}' NOT IN ALIAS TABLE")
    
    # Check CD
    cds = [sk["cooldown"] for sk in skills]
    avg_cd = sum(cds)/len(cds)
    if cds[0] != 0:
        issues.append(f"  {name}: slot 0 CD={cds[0]} (must be 0)")
    if avg_cd > 3.0:
        issues.append(f"  {name}: avg CD={avg_cd:.1f} > 3.0")
    if max(cds) > 5:
        issues.append(f"  {name}: max CD={max(cds)} > 5")
    
    # effects count
    total_eff = sum(len(sk.get("effects",[])) for sk in skills)
    if total_eff > 8:
        issues.append(f"  {name}: total effects={total_eff} > 8")
    for sk in skills:
        if len(sk.get("effects",[])) > 3:
            issues.append(f"  {name}/{sk['key']}: effects count={len(sk['effects'])} > 3")

if issues:
    print(f"\n*** {len(issues)} ISSUES ***")
    for i in issues:
        print(i)
else:
    print("\nAll validations PASSED!")

# Print dice expectancy summary
print("\n=== Dice Expectancy Summary ===")
for name, skills in HEROES.items():
    E = calc_E(skills)
    role = role_of[name]
    lo, hi = ROLE_BANDS[role]
    ok = "OK" if lo <= E <= hi else "FAIL"
    print(f"  {name:8s} [{role:9s}] E={E:5.1f} ({lo}-{hi}) {ok}")

# Write output
out_path = "tools/_archive/batch1_skills.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(HEROES, f, ensure_ascii=False, indent=2)
print(f"\nWritten to {out_path}")
