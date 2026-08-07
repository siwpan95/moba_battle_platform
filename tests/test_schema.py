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


# --- C-4: 未知字段透传测试 (ADR-005) ---

def test_to_skill_dict_preserves_unknown_fields():
    """_to_skill_dict 应透传未知字段，不丢弃（ADR-005）。"""
    raw = {
        "name": "火球术",
        "key": "Q",
        "type": "法术",
        "mana_cost": 50,      # 未知字段
        "scaling": "INT",     # 未知字段
        "charges": 3,         # 未知字段
        "approx": True,       # 已知存在于现网但非白名单
    }
    result = schema._to_skill_dict(raw, 0)
    # 已知字段保留
    assert result["name"] == "火球术"
    assert result["key"] == "Q"
    assert result["type"] == "法术"
    # 未知字段透传
    assert result.get("mana_cost") == 50
    assert result.get("scaling") == "INT"
    assert result.get("charges") == 3
    assert result.get("approx") is True


def test_to_skill_dict_adds_defaults_for_missing_known_fields():
    """_to_skill_dict 应对缺失的已知字段补默认值。"""
    raw = {"name": "Q"}  # 只有 name
    result = schema._to_skill_dict(raw, 0)
    assert result["key"] == "Q"
    assert result["type"] == "物理"  # 默认值
    assert result["cooldown"] == 0
    assert result["description"] == ""


def test_report_unknown_fields_detects_new_dimensions():
    """report_unknown_fields 应能发现 mana_cost / scaling / charges 等新维度字段。"""
    skills = [
        {"name": "Q", "mana_cost": 50, "scaling": "INT"},
        {"name": "W", "mana_cost": 30},
        {"name": "E", "charges": 3},
        {"name": "R", "approx": True},
    ]
    unknown = schema.report_unknown_fields(skills)
    assert unknown.get("mana_cost") == 2  # Q + W
    assert unknown.get("scaling") == 1
    assert unknown.get("charges") == 1
    assert unknown.get("approx") == 1
    # 已知字段不应出现在未知报告中
    assert "name" not in unknown


def test_report_unknown_fields_empty_for_known_only():
    """纯已知字段不应触发 unknown 报告。"""
    skills = [
        {"name": "Q", "key": "Q", "type": "物理", "cooldown": 0, "description": "desc"}
    ]
    unknown = schema.report_unknown_fields(skills)
    assert unknown == {}


def test_validate_card_still_accepts_unknown_fields():
    """validate_card 应接受携带未知字段的合法卡（行为不变）。"""
    card = {
        "hero": {"name": "Hero"},
        "attributes": {a: {"modifier": 1} for a in ("STR", "DEX", "CON", "INT", "WIS", "CHA")},
        "skills": [{"name": "Q", "type": "物理", "mana_cost": 50, "scaling": "INT"}],
    }
    problems = schema.validate_card(card)
    assert problems == []
