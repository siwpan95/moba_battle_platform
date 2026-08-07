# -*- coding: utf-8 -*-
"""pytest 本地配置：fixture 与跨测试状态清理。"""
import pytest
from core.loader import HeroLoader


@pytest.fixture(autouse=True)
def clear_skills_cache():
    """每个测试前清理全局 skills DB 缓存，消除跨测试污染。

    注：loader 重构后将缓存更名为 HeroLoader._SKILL_POOL_CACHE（惰性初始化）。
    此处同步更正，并防御性处理缓存尚未创建的情况。
    """
    cache = getattr(HeroLoader, "_SKILL_POOL_CACHE", None)
    if cache is not None:
        cache.clear()
    yield
