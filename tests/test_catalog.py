#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""core.catalog 测试：从 ui 下沉的过滤 / 摘要逻辑（ADR-002 Phase3）。"""

import pytest

from core.loader import HeroLoader
from core.catalog import filter_cards, describe_card
from core.registry import ROLE_NAME_CN, game_cn


@pytest.fixture(scope="module")
def heroes_dict():
    heroes = HeroLoader.load_all_heroes()
    return HeroLoader.build_hero_dict(heroes)


def test_filter_empty_query_returns_all(heroes_dict):
    res = filter_cards(heroes_dict)
    assert len(res) == len(heroes_dict)


def test_filter_by_game(heroes_dict):
    first = next(iter(heroes_dict.values()))
    gcn = game_cn(first)
    res = filter_cards(heroes_dict, game_filter=gcn)
    assert res, "按存在游戏过滤应非空"
    assert all(game_cn(c) == gcn for c in res.values())


def test_filter_by_role(heroes_dict):
    first = next(iter(heroes_dict.values()))
    role_en = first.get("game", {}).get("universal_role", "")
    role_cn = ROLE_NAME_CN.get(role_en, role_en)
    res = filter_cards(heroes_dict, role_filter=role_cn)
    assert res, "按存在位置过滤应非空"
    assert all(c.get("game", {}).get("universal_role", "") == role_en
                 for c in res.values())


def test_filter_search(heroes_dict):
    first_key = next(iter(heroes_dict.keys()))
    name = heroes_dict[first_key]["hero"]["name"]
    res = filter_cards(heroes_dict, search_query=name)
    assert first_key in res


def test_describe_card_level_scaling(heroes_dict):
    first = next(iter(heroes_dict.values()))
    low = describe_card(first, 1)
    high = describe_card(first, 18)
    assert "Lv.1" in low and "Lv.18" in high
    assert "生命" in low
    assert "属性" in low
