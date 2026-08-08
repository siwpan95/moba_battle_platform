#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工作流子包：对战平台技能流的四个标准流程 + 验证。

  - add_ip   工作流一：新增 IP（注册 registry + 建目录 + 空 source）
  - p0a_rename 工作流二：P0-A 模板技能名改写（检测 + 应用改名映射）
  - p0b_effects 工作流三：P0-B effects 补全（按技能名关键词推断）
  - p0c_descriptions 工作流四：P0-C 模板描述重写（按效果语义生成专属叙事）
  - p0d_dice_rebalance 工作流五：P0-D 骰骨架回调（拉回 GDD §3.2 配额带）
  - p1_expand 工作流六：P1 英雄池扩充（追加英雄到技能池与 source）
  - verify    验证管道（check_cards + 可选 pytest + 可选烟雾对战）
"""

from . import add_ip
from . import p0a_rename
from . import p0b_effects
from . import p0c_descriptions
from . import p0d_dice_rebalance
from . import p1_expand
from . import verify

__all__ = ["add_ip", "p0a_rename", "p0b_effects", "p0c_descriptions",
           "p0d_dice_rebalance", "p1_expand", "verify"]
