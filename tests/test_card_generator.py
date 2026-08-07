"""card_generator 生成器契约测试（C-1: get_skills() 返回 list[4] + fail-fast validate_card）。"""
import sys
import os
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import schema

# 直接导入 card_generator 函数（tools/ 已在 sys.path）
from tools.card_generator import (
    get_skills,
    _flatten_templates,
    _build_placeholder_skill,
    _load_templates,
    generate_character_card,
)

ROLES = ["tank", "fighter", "assassin", "mage", "marksman", "support"]


def test_flatten_templates_returns_flat_dict_list():
    """展平函数应返回纯 skill dict 列表。"""
    templates = _load_templates()
    for role, tmpl in templates.items():
        flat = _flatten_templates(tmpl)
        assert isinstance(flat, list), f"{role}: flat 不是 list"
        assert len(flat) > 0, f"{role}: flat 为空"
        for item in flat:
            assert isinstance(item, dict), f"{role}: flat 中包含非 dict 元素 {type(item)}"


def test_placeholder_skill_has_required_fields():
    """占位技能应包含引擎消费所需的最小字段集。"""
    for i in range(4):
        skill = _build_placeholder_skill(i)
        assert isinstance(skill, dict)
        assert "name" in skill
        assert "key" in skill and skill["key"] == ["Q", "W", "E", "R"][i]
        assert "type" in skill
        assert skill.get("approx") is True


def test_get_skills_fallback_returns_list_4_for_all_roles():
    """对每个 role，技能库未命中（空库）时 get_skills 返回 list[4] 且通过 validate_card。"""
    for role in ROLES:
        skills = get_skills("不存在的英雄", "nonexistent", "__test_nonexistent_game__", role)
        assert isinstance(skills, list), f"{role}: 返回值类型={type(skills).__name__}，应为 list"
        assert len(skills) == 4, f"{role}: len(skills)={len(skills)}，应为 4"
        for i, s in enumerate(skills):
            assert isinstance(s, dict), f"{role}[{i}]: 非 dict"
            assert s.get("key") in ("Q", "W", "E", "R"), f"{role}[{i}]: key={s.get('key')!r}"


def test_generated_card_passes_validate():
    """通过 generate_character_card 产出的卡应通过 schema.validate_card()。"""
    hero_stub = {
        "name": "测试英雄",
        "name_en": "TestHero",
        "game": "__test_generated_card__",
        "universal_role": "fighter",
        "source": "test",
    }
    card = generate_character_card(hero_stub, 99999)
    problems = schema.validate_card(card)
    assert problems == [], f"校验失败: {problems}"
    skills = card.get("skills")
    assert isinstance(skills, list), f"skills 类型={type(skills).__name__}"
    assert len(skills) == 4, f"skills 长度={len(skills)}"


def test_card_id_format_is_gameid_hero_slug():
    """ADR-005: card_id 应为 <game_id>:<hero_slug> 格式。"""
    hero_stub = {
        "name": "路飞",
        "name_en": "Luffy",
        "game": "One Piece",
        "universal_role": "fighter",
        "source": "test",
    }
    card = generate_character_card(hero_stub, 11111)
    cid = card["card_id"]
    # 格式: game_id:hero_slug
    assert ":" in cid, f"card_id 缺少冒号分隔符: {cid}"
    parts = cid.split(":")
    assert len(parts) == 2, f"card_id 应有两段: {cid}"
    # 第一段应为 game_id (小写)
    assert parts[0] == "one_piece", f"game_id 应为 one_piece 而非 {parts[0]}"
    # 第二段应为 hero_slug (不含空格和斜杠)
    assert " " not in parts[1], f"hero_slug 含空格: {parts[1]}"
    assert "/" not in parts[1], f"hero_slug 含斜杠: {parts[1]}"


def test_legacy_card_id_preserved():
    """旧 card_id 保留为 legacy_card_id 过渡字段。"""
    hero_stub = {
        "name": "路飞",
        "name_en": "Luffy",
        "game": "One Piece",
        "universal_role": "fighter",
        "source": "test",
    }
    card = generate_character_card(hero_stub, 11111)
    assert "legacy_card_id" in card, "缺少 legacy_card_id 字段"
    legacy = card["legacy_card_id"]
    # 旧格式: GAM-XXXX (game[:3].upper()-seed)
    assert legacy.startswith("ONE-"), f"legacy_card_id 前缀不符: {legacy}"
    assert legacy != card["card_id"], "legacy_card_id 不应与新 card_id 相同"


def test_card_id_idempotent():
    """对同一 hero 重复生成应产出相同的 card_id（幂等）。"""
    hero_stub = {
        "name": "索隆",
        "name_en": "Zoro",
        "game": "One Piece",
        "universal_role": "fighter",
        "source": "test",
    }
    card1 = generate_character_card(hero_stub, 22222)
    card2 = generate_character_card(hero_stub, 33333)
    assert card1["card_id"] == card2["card_id"], \
        f"card_id 不幂等: {card1['card_id']} vs {card2['card_id']}"

