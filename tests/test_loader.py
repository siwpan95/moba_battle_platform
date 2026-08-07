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
    """ADR-005: skills=None 为合法状态（技能分离存储），不应报'已归一'。"""
    card = {}
    out, was = HeroLoader._normalize_card(card)
    assert was is False
    assert "skills" not in out


def test_normalize_illegal_type_becomes_empty_list():
    card = {"skills": "some string"}
    out, was = HeroLoader._normalize_card(card)
    assert was is True
    assert out["skills"] == []


def test_build_hero_dict_no_collision():
    """无碰撞时 build_hero_dict 正常构建。"""
    heroes = [
        {"hero": {"name": "路飞"}, "game": {"name": "One Piece"}, "_game_dir": "one_piece", "_filename": "路飞"},
        {"hero": {"name": "索隆"}, "game": {"name": "One Piece"}, "_game_dir": "one_piece", "_filename": "索隆"},
    ]
    result = HeroLoader.build_hero_dict(heroes)
    assert len(result) == 2
    # 都正常插入
    assert any("路飞" in k for k in result.keys())
    assert any("索隆" in k for k in result.keys())


def test_build_hero_dict_collision_disambiguates():
    """显示名碰撞时 build_hero_dict 应消歧而非静默覆盖。"""
    heroes = [
        {"hero": {"name": "路飞"}, "game": {"name": "One Piece"}, "_game_dir": "one_piece", "_filename": "路飞"},
        {"hero": {"name": "路飞"}, "game": {"name": "One Piece"}, "_game_dir": "one_piece_v2", "_filename": "路飞_v2"},
    ]
    result = HeroLoader.build_hero_dict(heroes)
    # 两张卡都应保留（不丢卡）
    assert len(result) == 2
    keys = list(result.keys())
    # 第一个键为正常显示名，第二个键应包含消歧目录信息
    assert "[One Piece] 路飞" in keys[0] or "路飞" in keys[0]
    # 第二个键必须包含消歧目录
    assert any("one_piece" in k for k in keys)

