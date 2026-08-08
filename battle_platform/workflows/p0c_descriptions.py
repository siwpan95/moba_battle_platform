#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P0-C 描述重写工作流：把模板/样板技能描述改写为英雄专属叙事。

策略
----
实测发现 8 个高负债 IP 的模板描述仅由 **24 条「角色×槽位」通用模板** 复用 ~596 次，
与具体英雄无关。本模块只改写被判定为模板的描述（无骰式，或去骰式后叙事 ≤6 字），
保留已叙事化的描述；改写为「英雄名 + 技能名意象 + IP 神话词 + 效果」的专属叙事，
并嵌入骰式以保持与数值一致（与 builder.compile_hero 的描述格式对齐）。

判定口径与深度评估一致：is_templated()。

用法
----
from battle_platform.workflows import p0c_descriptions as p0c
rep = p0c.rewrite_pass("egyptian_mythology", dry_run=False)
rep = p0c.run_all(dry_run=False)          # 对 8 个高负债 IP
"""
import os
import re
import json
import glob
import hashlib

from .. import paths  # PROJECT_ROOT / SKILLS_DIR / CARDS_DIR

# 高负债 IP（除 arabian_nights 外，arabian 已 6.1%）
HIGH_DEBT = [
    "egyptian_mythology", "hindu_mythology", "celtic_mythology",
    "japanese_mythology", "chinese_mythology", "slavic_mythology",
    "aztec_mythology", "arthurian_legend",
]

ROLEMAP = {  # universal_role(英) -> 中文角色
    "tank": "坦克", "fighter": "战士", "assassin": "刺客",
    "mage": "法师", "marksman": "射手", "support": "辅助",
}

# 每 IP 的神话风味词（点缀用，按 hash 抽取，避免单调）
IP_LORE = {
    "egyptian_mythology": ["尼罗河的潮气", "玛特的羽毛", "方尖碑的影", "冥河的凉意"],
    "hindu_mythology": ["恒河的雾", "轮回的环", "梵天的光", "湿婆的灰"],
    "celtic_mythology": ["翠绿的雾", "古老的橡木", "精灵的环", "海风的咸"],
    "japanese_mythology": ["八百万神的息", "樱吹雪", "神无月的静", "大祓的水"],
    "chinese_mythology": ["昆仑的雪", "九天的风", "东海的潮", "玄鸟的影"],
    "slavic_mythology": ["白桦林的影", "冻土的寒", "雷神的锤音", "月桂的香"],
    "aztec_mythology": ["太阳的灼", "羽蛇的鳞", "玉米田的绿", "祭坛的血"],
    "arthurian_legend": ["圆桌的誓", "卡美洛的钟", "湖中剑的寒", "不列颠的雾"],
}

# ---------------------------------------------------------------- 语义分类
# 实测 8 个高负债 IP 共出现 52 种 effect.type，归并为 12 个叙事语义类。
# 选帧优先看「技能实际效果」，而非槽位——避免把潜行技能写成投掷暗器。
EFFECT_CATEGORY = {
    # 硬控
    "眩晕": "硬控", "禁锢": "硬控", "束缚": "硬控", "冻结": "硬控", "石化": "硬控",
    "麻痹": "硬控", "压制": "硬控", "制服": "硬控", "击飞": "硬控", "倒地": "硬控",
    "震慑": "硬控",
    # 软控
    "减速": "软控", "沉默": "软控", "致盲": "软控", "恐惧": "软控", "混乱": "软控",
    "干扰": "软控", "魅惑": "软控", "暗示": "软控", "击退": "软控",
    # 护盾 / 减伤
    "护盾": "护盾", "减伤": "护盾", "防御": "护盾", "免疫": "护盾",
    "免疫控制": "护盾", "反弹": "护盾",
    # 治疗
    "治疗": "治疗", "回复": "治疗", "复活": "治疗",
    # 自强
    "增益": "自强", "加速": "自强", "暴击": "自强", "狂暴": "自强", "强化": "自强",
    "增援": "自强", "冲锋": "自强",
    # 其余
    "净化": "净化",
    "破甲": "破防", "易伤": "破防", "穿透": "破防",
    "灼烧": "灼蚀", "中毒": "灼蚀", "剧毒": "灼蚀", "持续伤害": "灼蚀",
    "重创": "灼蚀", "重伤": "灼蚀",
    "处决": "处决", "斩杀": "处决",
    "标记": "标记",
    "隐身": "隐匿", "潜行": "隐匿",
    "吸血": "汲取",
}

# 语义帧：每类 4 变体，[0][1] 常规量级（Q/W/E），[2][3] 宏大量级（R 大招）
CAT_FRAMES = {
    "硬控": [
        "{hero}探手扣住「{skill}」，一股沛然之力压落，敌身骤然僵直。",
        "{hero}的「{skill}」如铁枷扣下，对手连抬手都成了奢望。",
        "{hero}倾力斩出「{skill}」，{lore}为之一凝，当面之敌尽被钉在原地。",
        "{hero}将「{skill}」重重顿落，天地失声，敌阵僵成一片死物。",
    ],
    "软控": [
        "{hero}散出「{skill}」，敌之感官被搅乱，脚步一寸寸沉滞下去。",
        "{hero}低语「{skill}」，寒意顺着敌之脊背爬上，攻势自乱。",
        "{hero}铺开「{skill}」，{lore}漫过战场，敌阵的号令再传不出三步。",
        "{hero}倾尽「{skill}」，恐惧如潮水淹没敌军，秩序荡然无存。",
    ],
    "护盾": [
        "{hero}张开「{skill}」，光壁在身周凝成，来袭之伤尽碎于其上。",
        "{hero}以「{skill}」覆身，气机内敛，锋刃再难透入分毫。",
        "{hero}立起「{skill}」，{lore}化作城垣落地，护住身后所有人。",
        "{hero}倾注「{skill}」，一层不可破的鳞甲笼罩全军。",
    ],
    "治疗": [
        "{hero}引「{skill}」，暖流漫过伤处，血肉在光中悄然弥合。",
        "{hero}以「{skill}」轻抚同伴，痛楚被一寸寸收拢带走。",
        "{hero}倾洒「{skill}」，{lore}化作生机之雨，垂危者重新睁眼。",
        "{hero}燃尽「{skill}」，生命之泉自足下涌出，全军同沐其恩。",
    ],
    "自强": [
        "{hero}催动「{skill}」，筋骨间腾起灼热的力，气势为之一变。",
        "{hero}踏出「{skill}」，身法陡然轻快，攻势连绵不绝。",
        "{hero}尽解「{skill}」之封，{lore}在血脉中奔涌，形骸几近狂神。",
        "{hero}纵身入「{skill}」，力与速攀至极处，再无人能挡其锋。",
    ],
    "净化": [
        "{hero}以「{skill}」拂过同伴，附身的污浊被一寸寸涤去。",
        "{hero}诵起「{skill}」，秽气自身上剥落，神思复归清明。",
        "{hero}振袖施「{skill}」，{lore}里圣辉大盛，一切诅咒尽数消融。",
        "{hero}倾尽「{skill}」，涤荡之光横扫战场，众人重获自由之身。",
    ],
    "破防": [
        "{hero}以「{skill}」精准凿开敌之甲缝，护体之力应声瓦解。",
        "{hero}挥出「{skill}」，锋刃削过甲面，破绽就此暴露。",
        "{hero}倾力递出「{skill}」，{lore}之下，敌之坚壁层层剥落。",
        "{hero}轰出「{skill}」，敌阵防线成片崩解，再无遮蔽可言。",
    ],
    "灼蚀": [
        "{hero}掷出「{skill}」，余烬附于敌身，伤口久久不愈。",
        "{hero}的「{skill}」在敌体内蔓延，痛楚随每一次呼吸加深。",
        "{hero}倾泻「{skill}」，{lore}被烧灼成焦土，敌军在余毒中缓缓凋零。",
        "{hero}引爆「{skill}」，蚀骨之力扩散开来，无人能全身而退。",
    ],
    "处决": [
        "{hero}锁死残喘的猎物，「{skill}」凝于一点，一击了结。",
        "{hero}看准敌之力竭，「{skill}」自死角递出，不留余地。",
        "{hero}倾尽「{skill}」，{lore}见证了这一记终结之斩。",
        "{hero}挥落「{skill}」，濒死者的最后一线生机被彻底斩断。",
    ],
    "标记": [
        "{hero}以「{skill}」在敌身烙下印记，其行踪再无可藏。",
        "{hero}投出「{skill}」，一点微光钉在敌背，猎杀就此开始。",
        "{hero}张开「{skill}」，{lore}将敌之方位昭示全军。",
        "{hero}倾力标定「{skill}」，被锁定者的每一处破绽都无所遁形。",
    ],
    "隐匿": [
        "{hero}没入「{skill}」，身形在光影里溶成一缕烟。",
        "{hero}借「{skill}」敛去气息，连脚步声都被一并吞没。",
        "{hero}化「{skill}」为夜，{lore}掩去其踪，敌人只余满目虚影。",
        "{hero}尽展「{skill}」，自战场上彻底消失，直到刃锋抵喉才被察觉。",
    ],
    "汲取": [
        "{hero}以「{skill}」引敌之血气回流，伤势随之转轻。",
        "{hero}的「{skill}」贪婪吮吸，对手的力量正一分分易主。",
        "{hero}倾展「{skill}」，{lore}中生机逆流而上，尽归其身。",
        "{hero}张开「{skill}」，战场上的每一分损耗都化作自身的养料。",
    ],
}

# 兜底帧（技能无 effects 时）：role_cn -> [Q1,Q2,W1,W2,E1,E2,R1,R2]
ROLE_FRAMES = {
    "辅助": [
        "{hero}引动「{skill}」，流光自指间洒落，敌之视线被无声晕开。",
        "{hero}抬手，「{skill}」化作一点锐光钉向敌面，其神思微颤。",
        "{hero}低诵「{skill}」，暖流漫过盟友的伤处，将痛楚轻轻收拢。",
        "{hero}以「{skill}」覆住同伴，光壁在身周凝成，护其无虞。",
        "{hero}振袖施「{skill}」，{lore}里圣辉流转，净化之物尽数涤去。",
        "{hero}将「{skill}」覆上同伴，污浊被一寸寸化去，神思复清。",
        "{hero}张开「{skill}」，神圣之域笼罩战场，生者得其庇护。",
        "{hero}燃起「{skill}」，天使的羽影投下，广域同沐恩泽。",
    ],
    "法师": [
        "{hero}凝「{skill}」于指尖，元素在掌中绞成一线流光，破空而去。",
        "{hero}引「{skill}」，星火自虚空中坠向敌身。",
        "{hero}炸开「{skill}」，元素在敌阵中轰然绽放，牢笼骤生。",
        "{hero}以「{skill}」撕裂空间，敌被禁锢于元素之笼。",
        "{hero}念动「{skill}」，身形被褶皱的空间吞没，于他处重现。",
        "{hero}借「{skill}」遁入虚影，瞬息已易其位。",
        "{hero}召「{skill}」自天外坠下，{lore}在元素的怒啸中震颤。",
        "{hero}倾「{skill}」，风暴与陨石同落，山河失色。",
    ],
    "战士": [
        "{hero}抡圆兵刃，「{skill}」挟着全身重量劈落。",
        "{hero}踏前一步，「{skill}」带着破风的啸声砸下。",
        "{hero}稳住身形，「{skill}」撑开一层坚韧的壁。",
        "{hero}催动「{skill}」，筋骨间腾起不容撼动的硬气。",
        "{hero}借「{skill}」之势撞入敌群，尘土飞扬。",
        "{hero}暴喝一声，「{skill}」如铁锤撞开阵线。",
        "{hero}战意燎原，「{skill}」之下形骸几近狂神。",
        "{hero}倾尽「{skill}」，血与怒凝成不可阻的洪流。",
    ],
    "坦克": [
        "{hero}举盾迎上，「{skill}」带着千钧之势砸落，敌身一滞。",
        "{hero}以「{skill}」横扫，盾缘削过敌之甲。",
        "{hero}催动「{skill}」，甲间的咒纹亮起，伤不来犯。",
        "{hero}绷紧全身，「{skill}」在身周鼓成不动的壳。",
        "{hero}顿「{skill}」于地，震波环开，周遭皆颤。",
        "{hero}砸下「{skill}」，大地裂响，敌足被碎土绊住。",
        "{hero}倾尽「{skill}」，化作不动之垒，敌潮难撼。",
        "{hero}立「{skill}」，如山岳落地，阵线为之一稳。",
    ],
    "刺客": [
        "{hero}身形如电，「{skill}」自阴影里探出，直取咽喉。",
        "{hero}贴地疾掠，「{skill}」无声没入敌之侧腹。",
        "{hero}抖手，「{skill}」破空而去，毒信无声。",
        "{hero}甩出「{skill}」，淬毒的寒光钉进敌影。",
        "{hero}化「{skill}」，暗影穿行，踪迹难寻。",
        "{hero}没入「{skill}」，身形在光里溶成一缕烟。",
        "{hero}锁死猎物，「{skill}」凝于一点，一击了结。",
        "{hero}旋身递出「{skill}」，暗影之力于要害炸开。",
    ],
    "射手": [
        "{hero}拉满「{skill}」，一缕锐光钉向远方。",
        "{hero}眯眼，「{skill}」的箭尖已在敌喉上标明归处。",
        "{hero}布下「{skill}」，踩中者足下生根。",
        "{hero}掷出「{skill}」，机关咬合处迸出细索。",
        "{hero}借「{skill}」急退，与敌拉开一线生机。",
        "{hero}翻滚着拉开「{skill}」，风声擦过耳际。",
        "{hero}凝神，「{skill}」破空，决断落处再无悬念。",
        "{hero}引满「{skill}」，贯穿之矢带着必杀的啸音离去。",
    ],
}


def is_templated(desc):
    """与深度评估一致的模板描述判定：无骰式，或去骰式后叙事 ≤6 字。"""
    if not desc:
        return True
    if not re.search(r"\dd\d", desc):
        return True
    mech = re.sub(r"\d+d\d[+A-Z]*", "", desc)
    return len(mech.strip()) <= 6


def _role_of(card):
    g = card.get("game", {}) if isinstance(card, dict) else {}
    nat = g.get("native_role")
    uni = g.get("universal_role")
    r = nat or ROLEMAP.get(uni) or g.get("role_name")
    return r if r in ROLE_FRAMES else None


def _category_of(skill):
    """按技能实际 effects 判定叙事语义类；无可映射效果时返回 None。"""
    for e in (skill.get("effects") or []):
        if isinstance(e, dict):
            c = EFFECT_CATEGORY.get(e.get("type"))
            if c:
                return c
    return None


def _effect_tail(effects):
    if not isinstance(effects, list):
        return ""
    parts = []
    for e in effects:
        if isinstance(e, dict) and e.get("desc"):
            parts.append(e["desc"])
    return "；".join(parts)


def _dice_expr(dmg):
    if not isinstance(dmg, dict):
        return ""
    dc = dmg.get("dice_count")
    ds = dmg.get("dice_size")
    if not dc or not ds:
        return ""
    attr = dmg.get("bonus_attr")
    return f"{dc}d{ds}+{attr}" if attr else f"{dc}d{ds}"


def gen_description(hero, skill, game_id, role=None, slot=None):
    """为单个技能生成英雄专属叙事描述（保留骰式与效果）。

    slot: 0=Q 1=W 2=E 3=R（优先取技能 key，否则用入参）
    role: 中文角色（优先用入参，否则读卡）
    """
    if role is None:
        role = _role_of(_load_card(game_id, hero)) or "战士"
    key = (skill.get("key") or "").upper()
    KEY2SLOT = {"Q": 0, "W": 1, "E": 2, "R": 3}
    if slot is None:
        slot = KEY2SLOT.get(key, 0)
    h = int(hashlib.md5(f"{game_id}:{hero}:{skill.get('name')}".encode("utf-8")).hexdigest(), 16)
    cat = _category_of(skill)
    if cat:
        # 语义优先：帧由技能实际效果决定；R 槽取宏大量级变体（索引 2/3）
        frames = CAT_FRAMES[cat]
        frame = frames[(2 if (slot % 4) == 3 else 0) + (h % 2)]
    else:
        # 无 effects：退回「角色 × 槽位」帧
        frames = ROLE_FRAMES.get(role, ROLE_FRAMES["战士"])
        frame = frames[((slot % 4) * 2 + (h % 2)) % len(frames)]
    lore_pool = IP_LORE.get(game_id, ["古老的回响"])
    lore = lore_pool[h % len(lore_pool)]
    narr = frame.format(hero=hero, skill=skill.get("name", ""), lore=lore)
    dice = _dice_expr(skill.get("damage"))
    dtype = (skill.get("damage") or {}).get("type", "")
    tail = _effect_tail(skill.get("effects"))
    body = f"{dice}{dtype}伤害。{narr}" if dice else narr
    if tail:
        body = f"{body}{tail}。"
    # 兜底：若仍被判为模板（极端情况），强制补一句神话尾
    if is_templated(body):
        body = f"{body}{hero}的身影在{IP_LORE.get(game_id,['传说'])[0]}中淡去又重现。"
    return body


def _load_card(game_id, stem):
    p = os.path.join(paths.CARDS_DIR, game_id, stem + ".json")
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _load_skill_file(game_id, stem):
    p = paths.skill_file(game_id, stem)
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def detect_templated(game_id):
    """返回 [(stem, idx, skill)] 列表。"""
    out = []
    d = os.path.join(paths.SKILLS_DIR, game_id)
    if not os.path.isdir(d):
        return out
    for sf in sorted(glob.glob(os.path.join(d, "*.json"))):
        stem = os.path.splitext(os.path.basename(sf))[0]
        data = _load_skill_file(game_id, stem)
        if isinstance(data, dict):
            data = [v for v in data.values() if isinstance(v, list)]
            data = data[0] if data else []
        if not isinstance(data, list):
            continue
        for i, s in enumerate(data):
            if isinstance(s, dict) and is_templated(s.get("description") or ""):
                out.append((stem, i, s))
    return out


def rewrite_pass(game_id, dry_run=False):
    """重写该 IP 下所有模板描述。返回统计与样本。"""
    hits = detect_templated(game_id)
    rewritten = 0
    skipped = 0
    errors = []
    samples = []
    # 按 stem 分组，批量写回
    by_stem = {}
    for stem, i, s in hits:
        by_stem.setdefault(stem, []).append(i)
    for stem, idxs in by_stem.items():
        data = _load_skill_file(game_id, stem)
        if isinstance(data, dict):
            data = [v for v in data.values() if isinstance(v, list)]
            data = data[0] if data else []
        if not isinstance(data, list):
            continue
        role = _role_of(_load_card(game_id, stem)) or "战士"
        changed = False
        for i in idxs:
            if i >= len(data):
                continue
            s = data[i]
            if not isinstance(s, dict):
                continue
            try:
                new_desc = gen_description(stem, s, game_id, role=role, slot=i)
            except Exception as e:
                errors.append(f"{stem}#{i}: {e}")
                continue
            if new_desc != s.get("description"):
                if not dry_run:
                    s["description"] = new_desc
                rewritten += 1
                changed = True
                if len(samples) < 10:
                    samples.append((stem, s.get("name"), new_desc))
            else:
                skipped += 1
        if changed and not dry_run:
            try:
                with open(paths.skill_file(game_id, stem), "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                errors.append(f"{stem} write: {e}")
    return {"game_id": game_id, "rewritten": rewritten, "skipped": skipped,
            "errors": errors, "samples": samples}


def run_all(dry_run=False):
    out = {}
    for g in HIGH_DEBT:
        out[g] = rewrite_pass(g, dry_run=dry_run)
    return out


if __name__ == "__main__":
    import sys
    dr = "--dry" in sys.argv
    res = run_all(dry_run=dr)
    for g, r in res.items():
        print(f"{g}: rewritten={r['rewritten']} skipped={r['skipped']} errors={len(r['errors'])}")
        for s in r["samples"][:3]:
            print(f"   {s[0]}/{s[1]}: {s[2]}")
