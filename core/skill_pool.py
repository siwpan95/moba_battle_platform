#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""技能池（skill pool）读写 API。

技能池结构：data/skills/<ip>/<英雄key>.json
每个英雄的技能数据独立成文件，文件名即英雄标识（hero.name / hero.name_en）。

与 core/loader.py 的 _resolve_skill_pool 保持一致：
- 文件名使用原始 key，由 loader 做归一化容错匹配。
- 本模块提供安全的公共写入/读取接口，供 tools 生成技能时调用，
  避免工具直接向旧的 data/skills/<ip>.json 大文件写入（loader 已优先读池，
  写大文件会导致新数据不被加载）。
"""
import os
import json

from .paths import SKILLS_DIR, CARDS_DIR

_ILLEGAL = '/\\:*?"<>|'

# 英文名 -> 中文名 反查索引缓存：{ip: {归一化英文名: 中文名}}
_EN_TO_CN_CACHE: dict = {}


def _norm(name: str) -> str:
    """与 core.loader._norm_name 保持一致的归一化。"""
    s = (name or "").strip().lower()
    for ch in ("'", '"', "·", "•", "-", "_", " "):
        s = s.replace(ch, "")
    return s


def en_to_cn_index(ip: str) -> dict:
    """返回 {归一化英文名: 中文英雄名} 索引，基于该 IP 中文角色卡的 name_en 字段。

    用途：当技能池里同时存在中文名文件与英文名文件时，loader 可用
    角色卡的 name_en 反查命中对应的中文名技能文件，实现双向兼容。
    """
    if ip in _EN_TO_CN_CACHE:
        return _EN_TO_CN_CACHE[ip]
    idx = {}
    card_dir = os.path.join(CARDS_DIR, ip)
    if os.path.isdir(card_dir):
        for fn in os.listdir(card_dir):
            if not fn.endswith(".json"):
                continue
            try:
                with open(os.path.join(card_dir, fn), "r", encoding="utf-8") as f:
                    o = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
            h = o.get("hero", {})
            nm = h.get("name", "")
            ne = h.get("name_en", "")
            if nm and ne:
                idx[_norm(ne)] = nm
    _EN_TO_CN_CACHE[ip] = idx
    return idx


def resolve_pool_key(ip: str, name: str, name_en: str = None):
    """将候选英雄名解析为技能池中的真实文件名 stem。

    按优先级：
      1. 直接用 name（通常中文）在池中查找；
      2. 用 name_en 在池中查找（英文原名文件）；
      3. 通过 name_en 反查中文名后再查池（双向兼容）。
    返回命中文件的 stem，未命中返回 None。
    """
    def exists(key):
        return os.path.isfile(os.path.join(SKILLS_DIR, ip, safe_name(key) + ".json"))

    for cand in (name, name_en):
        if cand and exists(cand):
            return cand
    if name_en:
        cn = en_to_cn_index(ip).get(_norm(name_en))
        if cn and exists(cn):
            return cn
    return None


def safe_name(key: str) -> str:
    """将英雄 key 转为安全的文件名（去除文件系统非法字符）。"""
    s = (key or "").strip()
    for ch in _ILLEGAL:
        s = s.replace(ch, "_")
    return s or "unnamed"


def pool_dir(ip: str) -> str:
    """返回并创建（如不存在）技能池目录 data/skills/<ip>/。"""
    d = os.path.join(SKILLS_DIR, ip)
    os.makedirs(d, exist_ok=True)
    return d


def hero_skill_path(ip: str, key: str) -> str:
    return os.path.join(pool_dir(ip), safe_name(key) + ".json")


def pool_has(ip: str, key: str) -> bool:
    """技能池中是否已存在该英雄的技能文件。"""
    p = os.path.join(SKILLS_DIR, ip, safe_name(key) + ".json")
    return os.path.isfile(p)


def write_hero_skill(ip: str, key: str, skills) -> str:
    """写入单个英雄技能文件，返回文件路径。"""
    p = hero_skill_path(ip, key)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(skills, f, ensure_ascii=False, indent=2)
    return p


def read_hero_skill(ip: str, key: str):
    """从技能池读取单个英雄技能，不存在/解析失败返回 None。"""
    p = os.path.join(SKILLS_DIR, ip, safe_name(key) + ".json")
    if not os.path.isfile(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def list_pool_heroes(ip: str) -> list:
    """列出技能池中某 IP 下所有英雄 key（即文件名 stem）。"""
    d = os.path.join(SKILLS_DIR, ip)
    if not os.path.isdir(d):
        return []
    return [fn[:-5] for fn in os.listdir(d) if fn.endswith(".json")]
