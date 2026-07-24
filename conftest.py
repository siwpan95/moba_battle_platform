# -*- coding: utf-8 -*-
"""pytest 根配置：保证项目根目录在 sys.path，便于 `from core...` 绝对导入。

与 tools/*.py 各自的 `PROJECT_ROOT` 引导一致，作为 CI 兜底；
同时让 tests/ 下的用例无需手动 sys.path 注入即可 import core / tools。
"""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
