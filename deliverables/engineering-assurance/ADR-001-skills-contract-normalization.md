# ADR-001: 角色卡 skills 数据契约归一（as-code 单一真相）

- **状态**：Accepted
- **日期**：2026-07-24
- **作者**：工程保障团队（Archi 设计 / WorkBuddy 落地）

## 背景

`data/character_cards/` 下 1659 张角色卡的 `skills` 字段历史上出现了三种表示：

1. **list[skill]** —— 规范表示，长度通常为 4（对应 Q/W/E/R）
2. **扁平单技能 dict** —— 字段名直接作为 key（如 `{"name":"火球术","key":"Q",...}`）
3. **槽位键 dict** —— 以 `"0"/"1"/"2"/"3"` 为 key 的 dict

三种表示并存导致 `core/simulator.py` 在消费时频繁 `KeyError` / `TypeError`，
**42% 英雄开战即崩**（事故 SEV-2，2026-07-24 触发）。根因是数据生产侧
（`tools/card_generator.py`）与消费侧（`simulator`）没有共享的契约定义，
每写一个新工具就重新解释一次 `skills` 的结构。

## 决策

采用「**as-code 单一真相模块 + 加载期归一 + CI 契约门禁**」三层防御：

| 层 | 模块 | 职责 |
|----|------|------|
| 契约定义 | `core/schema.py` | `normalize_skills()` 把任意历史表示归一为 `list[Skill]`；`validate_card()` 按契约校验 |
| 加载期归一 | `core/loader.py::_normalize_card` | 加载每张卡时调用 `schema.normalize_skills`，防御对战崩溃 |
| CI 门禁 | `tools/check_cards.py` | 扫描全部卡，发现 dict 格式 skills 或契约违规即非零退出，阻断合并 |

### 规范表示

```python
skills: list[Skill]   # 长度通常为 4（对应 Q/W/E/R）

# 每个 Skill dict 的契约字段（由 _to_skill_dict 规范化保证）：
{
    "name": str,           # 必填
    "key": "Q"|"W"|"E"|"R",
    "type": "物理"|"法术"|"混合"|"真实",  # 必填，simulator 据此选伤害公式
    "cooldown": int,
    "description": str,
    "damage": {dice_count, dice_size, bonus_attr, type} | {},
    "effects": list | None,
    "aoe_radius": number | None,
    "saving_throw": {attr, dc_formula, on_save} | None,
    "action": str,
    "range": str | None,
    "target": str | None,
}
```

### 归一规则（`schema.normalize_skills`）

| 输入 | 输出 | 告警 |
|------|------|------|
| `list[skill]` | 逐元素规范化后原样返回 | 无 |
| 扁平单技能 dict | 包成长度 1 的 list（保留真实字段） | "扁平单技能 dict，已包成 list[1]" |
| 槽位键 dict（`"0".."3"`） | 按槽位展开成 list[4] | "槽位键 dict，已按槽位展开" |
| 缺失 / 其它类型 | 空 list | "skills 缺失/类型异常" |

## 备选方案

- **A. 数据全量重生成**：拒绝——1659 张卡逐张返工成本高，且历史卡可能再次漂移。
- **B. 在 simulator 内到处写 `if isinstance(skills, dict)`**：拒绝——治标不治本，
  每个新消费点都要重写一遍防御，违反单一真相。
- **C. 用 JSON Schema 文件**：可行但增加运行时依赖（`jsonschema`），且无法表达归一逻辑。
  故采用 as-code 模块，零依赖且可被工具链直接 import。

## 后果

正向：
- 事故 SEV-2 止血：42% 英雄开战即崩 → 0 崩溃（`test_dict_skills_no_longer_crashes` 锁死回归）。
- 契约集中在 `core/schema.py` 一处，新增工具/消费点只需 import，不再重新解释。
- CI 门禁（`tools/check_cards.py`）让违规卡无法进入主干，**1659 张卡 0 契约违规**。

需警惕（回滚方式）：
- `normalize_skills` 的归一逻辑必须与 `_to_skill_dict` 字段集保持同步，
  新增契约字段时两处都要改（否则归一后的卡缺字段）。
- 加载期归一是兜底，**不应成为数据生产侧不规范的借口**；
  `tools/migrate_skills_format.py` 提供一次性迁移脚本，把历史 dict 卡转为 list 卡。
- `validate_card` 是告警级（加载期不阻断），CI 是阻断级；两者标准需对齐。

## 实施阶段

- A1（事故止血）：`loader._normalize_card` + `schema.normalize_skills`，消除开战崩溃。
- A2（契约校验）：`schema.validate_card` + 加载期告警。
- A5b（CI 门禁）：`tools/check_cards.py` 非零退出阻断合并。
- A7（本 ADR）：决策记录落盘。

## 验证

- `pytest tests/test_schema.py` —— 8 用例覆盖归一与校验
- `pytest tests/test_loader.py` —— 5 用例覆盖加载期归一
- `pytest tests/test_battle_smoke.py::test_dict_skills_no_longer_crashes` —— 回归锁死
- `python tools/check_cards.py` —— 1659 张卡 0 问题
