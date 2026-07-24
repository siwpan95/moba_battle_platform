#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""loader 归一化单元测试（A2 止血 + A5b 校验）。

注意：HeroLoader._normalize_card 现返回 (card, was_normalized) 元组。
"""

from core.loader import HeroLoader


def test_normalize_flat_single_skill_dict():
    card = {"skills": {"name": "火球术", "key": "Q", "type": "法术", "cooldown": 0}}
    out, was = HeroLoader._normalize_card(card)
    assert was is True
    assert isinstance(out["skills"], list)
    assert len(out["skills"]) == 1
    assert out["skills"][0]["name"] == "火球术"


def test_normalize_slot_key_dict():
    card = {"skills": {"0": {"name": "Q"}, "1": {"name": "W"}, "2": {"name": "E"}, "3": {"name": "R"}}}
    out, was = HeroLoader._normalize_card(card)
    assert was is True
    assert [s["name"] for s in out["skills"]] == ["Q", "W", "E", "R"]


def test_normalize_already_list_passthrough():
    card = {"skills": [{"name": "Q"}, {"name": "W"}, {"name": "E"}, {"name": "R"}]}
    out, was = HeroLoader._normalize_card(card)
    assert was is False
    assert out["skills"] == card["skills"]


def test_normalize_missing_becomes_empty_list():
    card = {}
    out, was = HeroLoader._normalize_card(card)
    assert was is True
    assert out["skills"] == []


def test_normalize_illegal_type_becomes_empty_list():
    card = {"skills": "some string"}
    out, was = HeroLoader._normalize_card(card)
    assert was is True
    assert out["skills"] == []
