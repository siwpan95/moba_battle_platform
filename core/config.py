#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全局常量与汉化映射表 —— 兼容外观层（ADR-002）。

原 core.config 是「上帝模块」，现按职责拆分为三个单一真相模块：
  - core.paths    : 项目路径常量
  - core.registry  : 游戏/角色/属性 注册表与汉化映射 + 辅助函数
  - core.balance   : 战斗平衡参数（HP_SCALE / DAMAGE_SCALE）

本文件只做再导出，确保既有调用方
    from core.config import GAME_NAME_CN, CARDS_DIR, HP_SCALE, ROLE_NAME_CN, ...
零改动即可继续工作。新增代码请直接 `from core.registry / core.paths / core.balance import ...`。
"""

# 顺序：paths -> registry -> balance（无循环依赖）
from .paths import *        # 路径常量
from .registry import *     # 游戏/角色/属性 taxonomy + role_cn_to_en / game_cn
from .balance import *      # 战斗平衡参数
