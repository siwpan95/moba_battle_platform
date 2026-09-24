#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""battle_platform —— MOBA 英雄大乱斗 1v1 对战平台工作流包。

本包是对战平台「技能流」的可独立运行入口/子包，部署在
<仓库根>/battle_platform/ 。它本身不实现战斗引擎，
而是**衔接上级已有的引擎**（core/ data/ tools/ 位于父目录，
即仓库根），把技能工作流（新增 IP / 模板改名 / effects 补全 /
英雄池扩充 / 验证）封装成可调用、可命令化的模块。

磁盘格式以「真实项目」为准（技能文档中单文件 {英雄:技能} 的写法已过期）：
  - 技能血肉：data/skills/<game_id>/<英雄>.json  →  4 个技能 dict 的 list
  - 角色卡骨头：data/character_cards/<game_id>/<英雄>.json（skills 字段可省略）
  - 源数据：  data/source/<game_id>/heroes.json  →  [{"name": "..."}]
  - 注入点：  core/loader.py _inject_skills() 按 hero.name / 文件名 stem / name_en 做 JOIN
"""

from . import paths  # noqa: F401  导入即完成 PROJECT_ROOT 的 sys.path 引导
# 2026-09-23 去本地化：本文档串中的部署/引擎路径改为通用写法（原路径 与
#   原路径已不存在，仓已迁移至 原路径）；运行时逻辑未变。

__all__ = ["paths"]
