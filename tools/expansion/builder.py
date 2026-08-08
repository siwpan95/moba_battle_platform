#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IP 英雄池 / 技能池扩充 —— 共享构建引擎。

职责单一：把「手写的神话素材」（英雄 + 4 段技能叙事）编译成符合
core/schema.py 契约、且数值落在 GDD 配额带内的技能 JSON。

设计原则
--------
1. **血肉手写，骨架自动**：技能名 / 叙事描述 / 效果选择由各 IP 数据模块手写
   （保证 IP 原生风味、零模板复制）；骰型 / CD / 豁免 / 射程等数值骨架由本
   模块按 role+slot 统一推导（保证平衡性可验证）。
2. **effects.type 必须命中 core/mechanics.py 别名表**，否则归为 flavor 不生效。
   本模块在编译期做白名单校验，未命中直接抛错 —— fail fast，不写盘。
3. 骰期望总和落入 GDD §3.2 配额带（见 ROLE_BAND）。

技能素材格式（各 IP 数据模块提供）::

    hero(
        "阿蒙", "Amun", "隐秘之主", "mage", dmg="力场",
        skills=[
            ("底比斯圣言", "阿蒙以无形之名低语，被点名者神智受缚。", ["沉默"]),
            ("隐者之风",   "...", [("加速", "乘无形之风疾行")]),
            ...
        ],
    )
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.mechanics import categorize_effect  # noqa: E402

SKILLS_DIR = os.path.join(PROJECT_ROOT, "data", "skills")
SOURCE_DIR = os.path.join(PROJECT_ROOT, "data", "source")
ANALYSIS_JSON = os.path.join(PROJECT_ROOT, "data", "analysis", "all_heroes_unified.json")

SLOT_KEYS = ["Q", "W", "E", "R"]
SLOT_CD = [0, 1, 2, 4]

# ── 角色定位 → 主属性 / 伤害学派 ──────────────────────────────
ROLE_ATTR = {
    "fighter": "STR", "tank": "STR", "assassin": "DEX",
    "marksman": "DEX", "mage": "INT", "support": "WIS",
}
ROLE_SCHOOL = {
    "fighter": "物理", "tank": "物理", "assassin": "物理",
    "marksman": "物理", "mage": "法术", "support": "法术",
}
ROLE_CN = {
    "fighter": "战士", "tank": "坦克", "assassin": "刺客",
    "marksman": "射手", "mage": "法师", "support": "辅助",
}

# ── 骰型骨架：(dice_count, dice_size)，期望 = c*(s+1)/2 ────────
# 合计期望须落入 ROLE_BAND，见模块自检 _assert_bands()
ROLE_DICE = {
    "fighter":  [(1, 10), (2, 8), (1, 8), (2, 10)],   # 5.5+9+4.5+11   = 30.0
    "tank":     [(1, 8),  (2, 6), (1, 6), (2, 10)],   # 4.5+7+3.5+11   = 26.0
    "assassin": [(1, 8),  (2, 8), (1, 10), (3, 8)],   # 4.5+9+5.5+13.5 = 32.5
    "marksman": [(1, 10), (2, 6), (1, 8), (3, 8)],    # 5.5+7+4.5+13.5 = 30.5
    "mage":     [(1, 8),  (2, 6), (2, 6), (4, 6)],    # 4.5+7+7+14     = 32.5
    "support":  [(1, 6),  (2, 6), (1, 8), (3, 6)],    # 3.5+7+4.5+10.5 = 25.5
}
# GDD §3.2 四技能骰期望配额带
ROLE_BAND = {
    "tank": (24, 27), "fighter": (27, 30), "assassin": (32, 34),
    "mage": (30, 33), "marksman": (29, 32), "support": (24, 27),
}

# ── 槽位形态：(range, target, action) ─────────────────────────
ROLE_SHAPE = {
    "fighter":  [("近战", "单体", "动作"), ("近战", "单体", "动作"),
                 ("近战", "范围", "动作"), ("近战", "单体", "动作")],
    "tank":     [("近战", "单体", "动作"), ("近战", "范围", "动作"),
                 ("自身", "自身", "附赠动作"), ("近战", "范围", "动作")],
    "assassin": [("近战", "单体", "动作"), ("近战", "单体", "动作"),
                 ("近战", "单体", "附赠动作"), ("近战", "单体", "动作")],
    "marksman": [("远程", "单体", "动作"), ("远程", "单体", "动作"),
                 ("远程", "范围", "附赠动作"), ("远程", "单体", "动作")],
    "mage":     [("远程", "单体", "动作"), ("远程", "范围", "动作"),
                 ("远程", "范围", "附赠动作"), ("远程", "范围", "动作")],
    "support":  [("远程", "单体", "动作"), ("远程", "友方", "动作"),
                 ("自身", "自身", "附赠动作"), ("远程", "范围", "动作")],
}
AOE_RADIUS = [0, 8, 10, 15]

# ── effects 白名单（须与 core/mechanics.py 别名表一致，中文优先）──
EFFECT_CATEGORY = {
    # control
    "眩晕": "control", "束缚": "control", "禁锢": "control", "倒地": "control",
    "击飞": "control", "麻痹": "control", "石化": "control", "震慑": "control",
    "沉默": "control", "魅惑": "control", "恐惧": "control", "混乱": "control",
    "暗示": "control", "制服": "control", "冻结": "control", "击退": "control",
    "干扰": "control", "压制": "control",
    # 其余
    "减速": "slow", "致盲": "slow",
    "护盾": "shield", "减伤": "reduce", "防御": "reduce",
    "治疗": "heal", "回复": "heal", "回血": "heal",
    "吸血": "lifesteal",
    "灼烧": "dot", "中毒": "dot", "持续伤害": "dot", "痛苦": "dot",
    "重伤": "dot", "剧毒": "dot", "重创": "dot",
    "处决": "execute", "斩杀": "execute",
    "真实伤害": "true_dmg", "穿透": "true_dmg",
    "增益": "buff", "强化": "buff", "附魔": "buff", "攻击增益": "buff",
    "狂暴": "buff", "增援": "buff",
    "加速": "accel", "冲锋": "accel", "攻速强化": "accel",
    "破甲": "sunder", "标记": "vuln", "易伤": "vuln",
    "暴击": "crit", "暴击强化": "crit", "反弹": "reflect",
    "免疫": "immune", "免疫控制": "immune",
    "隐身": "invis", "隐形": "invis", "潜行": "invis",
    "净化": "cleanse", "驱散": "cleanse", "复活": "revive",
}
# 效果默认持续回合（0 = 瞬发，不写 duration 文案）
EFFECT_DURATION = {
    "control": 1, "slow": 2, "shield": 2, "reduce": 2, "heal": 0,
    "lifesteal": 2, "dot": 2, "execute": 0, "true_dmg": 0, "buff": 2,
    "accel": 1, "sunder": 2, "vuln": 2, "crit": 2, "reflect": 2,
    "immune": 1, "invis": 1, "cleanse": 0, "revive": 0,
}
# 作用对象：自身增益 vs 敌方减益
_SELF_CATEGORIES = {"shield", "reduce", "heal", "lifesteal", "buff", "accel",
                    "crit", "reflect", "immune", "invis", "cleanse", "revive"}

# 效果兜底文案 —— 作者未写 desc 时使用，避免 desc 为空串（对战日志会显示这段）
DEFAULT_FX_DESC = {
    "眩晕": "失去行动能力", "束缚": "无法移动", "禁锢": "被困于原地",
    "倒地": "被击倒在地", "击飞": "被抛向空中", "麻痹": "肢体僵直",
    "石化": "躯体化为顽石", "震慑": "神智短暂空白", "沉默": "无法施放技能",
    "魅惑": "神智被夺", "恐惧": "陷入恐慌", "混乱": "行动失去章法",
    "暗示": "被植入指令", "制服": "被压制在地", "冻结": "被冰封",
    "击退": "被推离原位", "干扰": "行动被打断", "压制": "被强行压制",
    "减速": "移动速度降低", "致盲": "视野被夺",
    "护盾": "获得吸收伤害的护盾", "减伤": "受到的伤害降低",
    "防御": "防御姿态", "治疗": "恢复生命值", "回复": "持续恢复生命",
    "回血": "恢复生命值", "吸血": "造成的伤害转化为生命",
    "灼烧": "持续受到火焰伤害", "中毒": "毒素持续侵蚀",
    "持续伤害": "伤口持续流失生命", "痛苦": "剧痛持续", "重伤": "伤势持续恶化",
    "剧毒": "剧毒持续侵蚀", "重创": "创伤持续加深",
    "处决": "对残血目标造成额外伤害", "斩杀": "对低生命目标造成致命一击",
    "真实伤害": "无视护甲与护盾", "穿透": "无视目标防御",
    "增益": "属性获得提升", "强化": "能力被强化", "附魔": "武器被附魔",
    "攻击增益": "攻击力提升", "狂暴": "进入狂暴状态", "增援": "获得增援之力",
    "加速": "移动速度提升", "冲锋": "向前突进", "攻速强化": "攻击速度提升",
    "破甲": "护甲被削弱", "标记": "被标记，受到的伤害提升",
    "易伤": "防御破绽暴露", "暴击": "暴击率提升", "暴击强化": "暴击威力提升",
    "反弹": "反弹部分近战伤害", "免疫": "免疫控制效果",
    "免疫控制": "不受控制效果影响", "隐身": "脱离视野", "隐形": "身形消失",
    "潜行": "无声潜行", "净化": "移除负面状态", "驱散": "驱散敌方增益",
    "复活": "重返战场",
}

# 豁免属性：按效果类别挑选最贴合的检定
_SAVE_ATTR = {
    "control": "CON", "slow": "DEX", "dot": "CON",
    "sunder": "CON", "vuln": "DEX", "execute": "CON", "true_dmg": "DEX",
}
_MIND_EFFECTS = {"魅惑", "恐惧", "混乱", "暗示", "沉默", "震慑"}


# ══════════════════════════════════════════════════════════════
# 素材声明
# ══════════════════════════════════════════════════════════════
FxSpec = Union[str, Tuple[str, str]]
SkillSpec = Union[
    Tuple[str, str, Sequence[FxSpec]],
    Tuple[str, str, Sequence[FxSpec], Dict[str, Any]],
]


def hero(
    name: str,
    name_en: str,
    title: str,
    role: str,
    skills: Sequence[SkillSpec],
    dmg: str = "",
    attr: str = "",
    school: str = "",
) -> Dict[str, Any]:
    """声明一位英雄及其 4 段技能素材。"""
    if role not in ROLE_ATTR:
        raise ValueError(f"{name}: 非法 role {role!r}")
    if len(skills) != 4:
        raise ValueError(f"{name}: 必须恰好 4 个技能，实得 {len(skills)}")
    return {
        "name": name, "name_en": name_en, "title": title, "role": role,
        "dmg": dmg, "attr": attr, "school": school, "skills": list(skills),
    }


# ══════════════════════════════════════════════════════════════
# 编译
# ══════════════════════════════════════════════════════════════
def _norm_fx(fx: FxSpec) -> Tuple[str, str]:
    if isinstance(fx, str):
        return fx, ""
    return fx[0], (fx[1] if len(fx) > 1 else "")


def _default_dmg_type(school: str, role: str) -> str:
    if school == "法术":
        return "力场"
    return "钝击" if role == "tank" else ("穿刺" if role in ("assassin", "marksman") else "挥砍")


def _effect_suffix(effs: List[Dict[str, Any]]) -> str:
    """把 effects 编成中文尾注，如 '眩晕1回合+破甲2回合。'"""
    parts = []
    for e in effs:
        dur = e.get("duration", 0)
        parts.append(f"{e['type']}{dur}回合" if dur else e["type"])
    return ("" if not parts else "".join(["", "+".join(parts), "。"]))


def compile_hero(h: Dict[str, Any]) -> List[Dict[str, Any]]:
    """把英雄素材编译成 4 个技能 dict（可直接写入 data/skills/<ip>/<hero>.json）。"""
    role = h["role"]
    school = h["school"] or ROLE_SCHOOL[role]
    attr = h["attr"] or ROLE_ATTR[role]
    dmg_type = h["dmg"] or _default_dmg_type(school, role)
    dice = ROLE_DICE[role]
    shape = ROLE_SHAPE[role]

    out: List[Dict[str, Any]] = []
    for i, spec in enumerate(h["skills"]):
        sname, sdesc, fxs = spec[0], spec[1], spec[2]
        over: Dict[str, Any] = spec[3] if len(spec) > 3 else {}

        dc, ds = over.get("dice", dice[i])
        rng, tgt, act = shape[i]
        rng = over.get("range", rng)
        tgt = over.get("target", tgt)
        act = over.get("action", act)
        sk_school = over.get("type", school)
        sk_attr = over.get("attr", attr)
        sk_dmg = over.get("dmg", dmg_type)

        # ── effects ──
        effs: List[Dict[str, Any]] = []
        cats: List[str] = []
        for fx in fxs:
            etype, edesc = _norm_fx(fx)
            cat = EFFECT_CATEGORY.get(etype)
            if cat is None:
                raise ValueError(
                    f"{h['name']}/{sname}: effect '{etype}' 不在 mechanics 别名表内，"
                    f"会被降级为 flavor（不生效）")
            if categorize_effect({"type": etype}) == "flavor":
                raise ValueError(f"{h['name']}/{sname}: effect '{etype}' 运行期归类为 flavor")
            cats.append(cat)
            entry = {
                "type": etype,
                "target": "自身" if cat in _SELF_CATEGORIES else "敌方",
                "duration": EFFECT_DURATION[cat],
                "desc": edesc or DEFAULT_FX_DESC.get(etype, ""),
            }
            if entry["duration"] == 0:
                entry.pop("duration")
            effs.append(entry)

        skill: Dict[str, Any] = {
            "name": sname,
            "key": SLOT_KEYS[i],
            "type": sk_school,
            "action": act,
            "range": rng,
            "target": tgt,
            "damage": {"dice_count": dc, "dice_size": ds,
                       "bonus_attr": sk_attr, "type": sk_dmg},
            "effects": effs,
            "cooldown": SLOT_CD[i],
            "description": (f"{dc}d{ds}+{sk_attr} {sk_dmg}伤害。{sdesc}"
                            f"{_effect_suffix(effs)}"),
        }

        # ── 豁免检定：对敌减益 or 范围技 ──
        debuffs = [c for c in cats if c not in _SELF_CATEGORIES]
        if debuffs or tgt in ("范围", "区域"):
            if any(_norm_fx(f)[0] in _MIND_EFFECTS for f in fxs):
                sattr = "WIS"
            elif debuffs:
                sattr = _SAVE_ATTR.get(debuffs[0], "DEX")
            else:
                sattr = "DEX"
            skill["saving_throw"] = {
                "attr": sattr,
                "dc_formula": f"8+PROF+{sk_attr}",
                "on_save": "半伤",
            }
        if tgt in ("范围", "区域") and AOE_RADIUS[i]:
            skill["aoe_radius"] = over.get("aoe_radius", AOE_RADIUS[i])
        out.append(skill)
    return out


def dice_expectation(skills: Sequence[Dict[str, Any]]) -> float:
    tot = 0.0
    for s in skills:
        d = s.get("damage") or {}
        tot += (d.get("dice_count") or 0) * ((d.get("dice_size") or 0) + 1) / 2
    return tot


def _assert_bands() -> None:
    for role, dice in ROLE_DICE.items():
        exp = sum(c * (s + 1) / 2 for c, s in dice)
        lo, hi = ROLE_BAND[role]
        assert lo <= exp <= hi, f"{role} 骰期望 {exp} 越界 [{lo},{hi}]"


_assert_bands()


# ══════════════════════════════════════════════════════════════
# 落盘
# ══════════════════════════════════════════════════════════════
def _safe_filename(name: str) -> str:
    return name.replace("/", "_").replace(" ", "_").replace(":", "").replace("\\", "_")


def write_ip(game_id: str, display: str, source_cn: str,
             heroes: Sequence[Dict[str, Any]], dry_run: bool = False) -> Dict[str, Any]:
    """把一个 IP 的新增英雄写入 skills 池 + source + unified 清单。

    幂等：同名英雄覆盖技能文件，unified 内按 (game, name) 去重。
    """
    # 1. 编译 + 校验（全部通过才写盘）
    compiled: Dict[str, List[Dict[str, Any]]] = {}
    for h in heroes:
        sk = compile_hero(h)
        exp = dice_expectation(sk)
        lo, hi = ROLE_BAND[h["role"]]
        if not (lo <= exp <= hi):
            raise ValueError(f"{h['name']}({h['role']}) 骰期望 {exp} 越界 [{lo},{hi}]")
        cds = [s["cooldown"] for s in sk]
        if cds != SLOT_CD:
            raise ValueError(f"{h['name']} CD 序列异常 {cds}")
        compiled[h["name"]] = sk

    names = [h["name"] for h in heroes]
    if len(set(names)) != len(names):
        dup = [n for n in set(names) if names.count(n) > 1]
        raise ValueError(f"{game_id} 英雄重名: {dup}")

    if dry_run:
        return {"game_id": game_id, "new": len(heroes), "written": False}

    # 2. 技能池
    pool_dir = os.path.join(SKILLS_DIR, game_id)
    os.makedirs(pool_dir, exist_ok=True)
    for name, sk in compiled.items():
        with open(os.path.join(pool_dir, f"{_safe_filename(name)}.json"), "w",
                  encoding="utf-8") as f:
            json.dump(sk, f, ensure_ascii=False, indent=2)

    # 3. data/source/<game_id>/heroes.json
    src_dir = os.path.join(SOURCE_DIR, game_id)
    os.makedirs(src_dir, exist_ok=True)
    src_path = os.path.join(src_dir, "heroes.json")
    src: List[Dict[str, Any]] = []
    if os.path.exists(src_path):
        with open(src_path, encoding="utf-8") as f:
            src = json.load(f)
    have = {e.get("name") for e in src}
    for h in heroes:
        if h["name"] not in have:
            src.append({"name": h["name"]})
    with open(src_path, "w", encoding="utf-8") as f:
        json.dump(src, f, ensure_ascii=False, indent=2)

    # 4. all_heroes_unified.json
    with open(ANALYSIS_JSON, encoding="utf-8") as f:
        uni = json.load(f)
    idx = {(e.get("game"), e.get("name")): e for e in uni["heroes"]}
    added = 0
    for h in heroes:
        key = (display, h["name"])
        entry = {
            "game": display, "name": h["name"], "name_en": h["name_en"],
            "alias": h["title"], "native_role": ROLE_CN[h["role"]],
            "universal_role": h["role"], "source": source_cn,
        }
        if key in idx:
            idx[key].update(entry)
        else:
            uni["heroes"].append(entry)
            added += 1
    uni["total_heroes"] = len(uni["heroes"])
    uni["total_games"] = len(set(e["game"] for e in uni["heroes"]))
    with open(ANALYSIS_JSON, "w", encoding="utf-8") as f:
        json.dump(uni, f, ensure_ascii=False, indent=2)

    return {"game_id": game_id, "new": added, "skills": len(compiled),
            "total_source": len(src), "written": True}
