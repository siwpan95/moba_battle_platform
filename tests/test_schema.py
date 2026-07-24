"""core.schema 数据契约单元测试（ADR-001 单一真相）。"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import schema


def test_normalize_none():
    out, warns = schema.normalize_skills(None)
    assert out == []
    assert warns  # 应有告警


def test_normalize_list_passthrough():
    raw = [{"name": "Q", "type": "物理"}]
    out, warns = schema.normalize_skills(raw)
    # list 元素会被规范化为契约字段（补齐 cooldown/description 等），但 name/type 不变
    assert isinstance(out, list) and len(out) == 1
    assert out[0]["name"] == "Q"
    assert out[0]["type"] == "物理"
    assert warns == []


def test_normalize_flat_dict_single_skill():
    flat = {"name": "Q", "key": "Q", "type": "spell", "cooldown": 4}
    out, warns = schema.normalize_skills(flat)
    assert isinstance(out, list) and len(out) == 1
    assert out[0]["name"] == "Q"
    assert out[0]["type"] == "spell"
    assert "扁平单技能" in warns[0]


def test_normalize_slot_key_dict():
    slot = {"0": {"name": "Q"}, "3": {"name": "R"}}
    out, warns = schema.normalize_skills(slot)
    assert len(out) == 4
    assert out[0]["name"] == "Q"
    assert out[3]["name"] == "R"
    assert "槽位键" in warns[0]


def test_normalize_invalid_type():
    out, warns = schema.normalize_skills("oops")
    assert out == []
    assert warns


def test_validate_card_ok():
    card = {
        "hero": {"name": "Hero"},
        "attributes": {a: {"modifier": 1} for a in ("STR", "DEX", "CON", "INT", "WIS", "CHA")},
        "skills": [{"name": "Q", "type": "物理"}],
    }
    assert schema.validate_card(card) == []


def test_validate_card_dict_skills_fails():
    card = {
        "hero": {"name": "Hero"},
        "attributes": {a: {"modifier": 1} for a in ("STR", "DEX", "CON", "INT", "WIS", "CHA")},
        "skills": {"name": "Q"},
    }
    problems = schema.validate_card(card)
    assert any("list" in p for p in problems)


def test_validate_card_missing_hero_and_attr():
    card = {"skills": []}
    problems = schema.validate_card(card)
    assert any("hero.name" in p for p in problems)
    assert any("modifier" in p for p in problems)
    assert any("skills" in p for p in problems)
