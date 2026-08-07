# ADR-005: 内容扩充管线契约化（生成端对齐 schema + 稳定卡标识 + 统一扫描口径）

- **状态**：Proposed（待审批）
- **日期**：2026-08-05
- **作者**：程基岩（engineering-lead）
- **关联**：ADR-001（skills 契约归一）、ADR-002（taxonomy 收敛）、ADR-003（D&D 消费路线）、ADR-004（安全求值器）

## 背景

ADR-001 把 `skills` 的规范表示定为 `list[Skill]`，并在 `core/schema.py` 建立 as-code 契约、
在 `core/loader.py` 建立运行时防御、用 `tools/migrate_skills_format.py` 迁移了磁盘数据。
但**生产端从未纳入该契约**：`tools/card_generator.py:248-252` 的通用模板回退路径至今返回**单个技能 dict**，
即 SEV-2 的根因代码。

全库现状证实其影响面——仅 574/1659（34.6%）的卡拥有完整 4 技能，
700 张为 `list[1]`（迁移残留），378 张为 QWER×3 冗余；`data/skills/` 对卡库的真实覆盖率仅 **35%**。

本轮工作室目标是内容扩充。新增 IP 的技能库必然从空开始，届时**每一张新卡都会命中该回退路径**，
导致 CI 门禁 `tools/check_cards.py` 非零退出，内容无法合入。

同时，评估发现三项与扩充直接冲突的设计缺陷：
(a) `card_id`（`card_generator.py:403`）由全量生成时的位置序号派生，局部生成 `--game <IP>` 会重写既有 ID；
(b) `core/loader.py:25-31` 两层扫描与 `tools/check_cards.py:25` 递归 glob 口径不一致，产生"CI 假绿"；
(c) `core/schema.py:29-46` 的 `_to_skill_dict` 是字段白名单，静默丢弃 `mana_cost` / `scaling` 等新维度字段
（现网 `approx` 字段 612 处已处于该风险敞口下）。

## 决策

将内容管线的**生产端纳入与消费端同一套契约**，具体四条：

### 1. 生成端类型契约

`get_skills()` 的返回类型锁定为 `list[Skill]`（长度恒为 4）。
通用模板回退改为 `_load_templates()[role][:4]`（或按槽位补齐），并在 `card_generator` 出口处
调用 `core.schema.validate_card`，**校验失败即拒绝写盘**（fail-fast，而非交给下游防御）。

新增单测：对每个 role、对"技能库未命中"路径断言 `len(skills) == 4` 且 `validate_card() == []`。

### 2. 稳定卡标识

`card_id` 语义从"生成序号"改为"内容标识"，采用 `<game_id>:<hero_slug>`
（例：`one_piece:蒙奇·D·路飞`）。理由：与 `data/character_cards/<game_id>/<hero>.json` 的物理路径同构，
天然唯一、局部生成幂等、无需台账。旧 `card_id` 保留为 `legacy_card_id` 字段一个版本周期。

`tools/check_cards.py` 增加**全局唯一性断言**。

### 3. 统一扫描口径

把目录遍历下沉为 `core/loader.py` 的单一实现 `iter_card_files(root)`（递归 `os.walk`，
跳过 `_` 前缀的文件与目录），由 `HeroLoader.load_all_heroes`、`tools/check_cards.py`、
`tools/card_tool.load_existing_cards` 三方共同复用。

同时 `build_hero_dict` 增加**显示名碰撞检测**：碰撞时告警并以 `<game_id>/<filename>` 消歧，禁止静默覆盖。

### 4. 字段开放性

`_to_skill_dict` 由"白名单重建"改为"已知字段补默认 + 未知字段透传"
（`{**defaults, **raw}` 语义）。`validate_card` 保持只校验已知契约字段，
对未知字段不拦截但由新增的 `report_unknown_fields()` 汇总输出，作为 schema 演进的观测入口。

`_VALID_TYPES` 与 `core/mechanics.py` 的 effect 别名表纳入同一份"机制词表"文档，
新增机制词必须同时登记别名与 simulator 消费分支，否则 CI 告警。

## 备选方案

- **A. 只修生成器回退，不动 card_id / 扫描口径**：拒绝。能解 CI 红，但 BLOCKER-2/3/5 会在内容扩充
  中途以"英雄莫名消失""ID 对不上"的形态爆发，届时已有大量新内容落盘，修复成本远高于现在。

- **B. 放弃通用模板回退，强制每个英雄手写技能 JSON**：拒绝。当前 65% 的卡依赖回退，
  强制手写等于要求先补 1078 个英雄的技能数据才能动内容扩充，与本轮目标冲突。
  正确做法是让回退**产出合约内的 4 技能占位**，并用 `approx: true` 标记待人工精修。

- **C. 用 pydantic / jsonschema 做契约**：拒绝。项目核心优势是**零运行时依赖**（ADR-004 已确立此原则），
  且 `core/schema.py` 现有 111 行纯函数实现已满足需要。

- **D. 在 loader 侧继续加防御，不动生成端**：拒绝。这正是 SEV-2 之后采取的策略，
  三个月后的今天证明它只止住了崩溃，没有阻止 65% 的内容退化——**防御层掩盖了生产端缺陷**。

## 后果

### 正向

- 新增 IP 从"必然 CI 红"变为"开箱即通过"，内容扩充解锁
- `card_id` 幂等后，局部生成 `--game <IP>` 成为安全的日常操作，支持增量补录英雄
- CI 校验集合 == 运行时加载集合，质量信号恢复可信
- 经济系统等新维度可以先落数据、后接消费，不再有静默丢字段风险

### 需警惕

- **`card_id` 变更是破坏性改动**。需确认无外部系统（存档、平衡表、UI 收藏）以旧 ID 为键；
  必须提供一次性迁移脚本并保留 `legacy_card_id` 过渡期。**此项须用户明确审批后执行。**

- 递归扫描会把 `data/character_cards/` 下**任何**深度的 JSON 纳入加载，需确保备份/草稿文件
  统一放在 `_` 前缀目录内，否则会被误加载。

- 修复回退路径后，`generate --all` 会改写 700 张 `list[1]` 卡为 4 技能占位——
  这是内容层面的**大规模变更**，须先 `--dry-run` 出 diff 报告并经文策渊（内容）与严守真（测试）会签。

- 未知字段透传后，脏字段也会被保留，需依赖 `report_unknown_fields()` 的观测输出做定期清理。

## 实施阶段

- Phase 1（本 ADR）：决策记录落盘，待用户审批。
- Phase 2：BLOCKER-1 修复（生成器回退 → `list[Skill]`×4 + fail-fast 校验）
- Phase 3：BLOCKER-2/3 修复（统一扫描口径 → `iter_card_files` + 碰撞检测）
- Phase 4：BLOCKER-4 修复（`_to_skill_dict` 字段透传）
- Phase 5：BLOCKER-5 修复（`card_id` 语义变更 + 迁移脚本）—— 须单独审批

## 验证

- `pytest tests/test_card_generator.py` —— 新增：role×回退路径断言 `len==4` + `validate_card()==[]`
- `pytest tests/test_loader.py` —— 扩展：嵌套目录加载 + 显示名碰撞告警
- `pytest tests/test_schema.py` —— 扩展：未知字段透传 + `report_unknown_fields`
- `python tools/check_cards.py` —— 扩展：`card_id` 全局唯一性断言
- 端到端：新 IP 空技能库 → `generate --game` → `check_cards.py` 退出码 0
