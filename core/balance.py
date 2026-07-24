#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""战斗平衡参数 —— 单一真相（ADR-002 拆分自 core.config）。

注意：simulator 内另有 DND_DAMAGE_SCALE（A3 消费路线专用的数据骰缩放），
与下面的全局 DAMAGE_SCALE 是两个独立旋钮，不要混淆。
"""

__all__ = ["HP_SCALE", "DAMAGE_SCALE"]

HP_SCALE = 10          # HP 倍率（D&D血量 × 10 = MOBA血量）
DAMAGE_SCALE = 0.35    # 伤害倍率（降低伤害，延长战斗回合数）
