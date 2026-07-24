# ADR-002: Taxonomy 收敛与 config 上帝模块拆分

- **状态**：Accepted
- **日期**：2026-07-25
- **作者**：工程保障团队（Archi 设计 / WorkBuddy 落地）

## 背景

`core/config.py` 长期扮演「上帝模块」：路径常量、`GAME_REGISTRY` 游戏注册表、三套汉化映射
（`GAME_NAME_CN` / `ATTR_NAME_CN` / `STAT_NAME_CN` / `ROLE_NAME_CN`）、`detect_hero_file`、
以及战斗平衡常量（`HP_SCALE` / `DAMAGE_SCALE`）全部堆在一处（~104 行）。

由此引发的重复与漂移（事故响应复盘 + 代码审查发现）：

1. `ui/ui.py::_apply_filters` **内联** `role_cn_to_en = {v:k for k,v in ROLE_NAME_CN.items()}`
   与游戏名反查逻辑，与 `loader.py` 中的同名逻辑各写各的。
2. `tools/card_generator.py` **重新定义** `HP_SCALE = 10`，与 `config.balance` 的真相值重复，
   一旦调平衡两边不同步即悄悄分叉。
3. `tools/hero_calculator.py` 用 `_CORE_DIR`（直接把 `core/` 塞进 `sys.path`）+
   `from engine import ...`，与其余 4 个 tools 的 `PROJECT_ROOT` + `from core...` 风格不一致。

## 决策

采用「**单一真相模块 + 再导出兼容外观层**」：

| 新模块 | 职责 |
|--------|------|
| `core/paths.py`   | 所有路径常量（`PROJECT_ROOT` / `CARDS_DIR` / `SOURCE_DIR` …） |
| `core/registry.py` | 游戏/角色/属性 taxonomy 单一真相 + `role_cn_to_en()` / `game_cn()` 辅助函数 |
| `core/balance.py`  | `HP_SCALE` / `DAMAGE_SCALE` |
| `core/config.py`   | **仅再导出**（外观层），调用方 `from core.config import X` 零改动 |

辅助函数 `role_cn_to_en(中文定位)` 与 `game_cn(card|id, fallback)` 由 registry 统一提供，
消解 ui / loader 的内联反查。业务过滤与英雄摘要逻辑下沉至新建 `core/catalog.py`（见 Phase3）。

## 备选方案

- **A. 维持单文件 config**：拒绝——继续累积上帝模块，重复只会更多。
- **B. 直接改调用方 import 到子模块**：可行但改动面大（loader / simulator / ui / 多个 tools），
  与「事故后零回归」原则冲突；故采用兼容外观层，调用方分批迁移、按需 `from core.registry import ...`。

## 后果

正向：
- taxonomy 单一真相，新增游戏/角色只改 `registry.py` 一处。
- `config.py` 从 104 行降到 ~25 行纯外观，可读性提升。
- `card_generator` 的 `HP_SCALE` 重复被消除，平衡旋钮回归单点。

需警惕（回滚方式）：
- **循环导入**：`config` 只 `import *` 子模块，子模块互不依赖、均不回引 config。
  若未来某子模块需引用 config，须改为延迟导入或上移到更底层模块。
- **`import *` 泄漏**：每个子模块显式声明 `__all__`，避免把 `os` 等实现细节带到 config 命名空间。
- **tools 运行时路径**：tools 仍以 `PROJECT_ROOT` 注入 `sys.path` 后 `from core...` 绝对导入；
  pytest 侧新增根 `conftest.py` 兜底同一路径，CI（`python tools/check_cards.py`）行为不变。

## 实施阶段

- Phase1（本 ADR）：`paths` / `registry` / `balance` 拆分 + `config` 外观层 + 本决策记录。
- Phase2：tools 导入规范化（`hero_calculator` 对齐 `PROJECT_ROOT` 风格、`card_generator` 删 `HP_SCALE` 副本、根 `conftest.py`）。
- Phase3：UI 领域逻辑下沉 `core/catalog.py`，ui 仅保留视图。
- Phase4：接入 GitHub Actions（合法触发器 + Python 3.11/3.12 矩阵）。
