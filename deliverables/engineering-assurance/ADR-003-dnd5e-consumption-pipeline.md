# ADR-003: D&D 5e 机制完整消费路线（坐实数值框架）

- **状态**：Accepted
- **日期**：2026-07-25
- **作者**：工程保障团队（Archi 设计 / WorkBuddy 落地）

## 背景

ADR-001 解决了 `skills` 字段的结构契约，但技能内部的 D&D 5e 机制数据
（`damage` 骰 / `effects` / `saving_throw`）此前并未被 simulator 真正消费：

- 伤害用写死的技能位倍率（普攻=1.0 / 技能一=1.3 / 大招=2.0），忽略技能自带的 `damage` 骰
- `effects`（控制/护盾/减伤/治疗/吸血/持续伤害/斩杀/真伤…）仅记日志，不生效
- `saving_throw`（豁免检定）完全未实现，带豁免的技能（占 63%）等同于自动命中

这意味着 `tools/skill_mechanics.py` 辛苦产出的结构化 D&D 数据被浪费，
战斗实质上是"披着 D&D 外皮的简单倍率结算"。README 宣称的"D&D 5e 数值框架"名不副实。

## 决策

采用「**纯函数机制模块 + 别名归一表 + simulator 状态消费**」三层：

| 层 | 模块 | 职责 |
|----|------|------|
| 机制归一 | `core/mechanics.py` | 纯函数：骰子、豁免、effect 类别归一；不依赖 simulator，可独立单测 |
| 状态消费 | `core/simulator.py` | 维护 timed 状态（控制/护盾/减伤/易伤/增益/DOT…），调用 mechanics 应用效果 |
| 公式底座 | `core/engine.py` | `skill_raw_damage`（骰+属性加值）、`apply_mitigation`（物理/法术减伤保底 30%） |

### effect 别名归一表

真实数据里 `effect.type` 中英混用、同义多词（`stun`/`眩晕`/`knockback`/`击退`…），
`mechanics.categorize_effect` 用 20 张别名表收敛到受控类别：

```
control / slow / shield / reduce / heal / lifesteal / dot /
execute / true_dmg / buff / accel / sunder / vuln / crit /
reflect / immune / invis / cleanse / revive / aoe
```

未识别的归为 `flavor`（仅记日志），保证未覆盖的 effect 类型不崩战斗。

### 伤害结算链（A3 路线）

```
skill.damage (dice_count d dice_size + bonus_attr modifier)
    ↓ BattleEngine.skill_raw_damage  (掷骰)
raw
    ↓ BattleEngine.apply_mitigation  (物理 AC×0.005 / 法术 WIS×0.03，保底 30%)
    ↓ 暴击 (calc_crit_chance × crit_damage_multiplier)
    ↓ × DAMAGE_SCALE (0.35) × active_damage_scale (等级成长) × DND_DAMAGE_SCALE (5.5)
    ↓ saving_throw (半伤/无效)
    ↓ 斩杀 (低血翻倍) / 真伤 (无视减伤护盾) / 减伤 / 易伤 / 增伤 / 护盾吸收
final dmg
```

### 两个独立缩钮（不要混淆）

| 常量 | 位置 | 作用 |
|------|------|------|
| `DAMAGE_SCALE = 0.35` | `core/balance.py` | 全局平衡旋钮，降低伤害延长回合 |
| `DND_DAMAGE_SCALE = 5.5` | `core/simulator.py` | A3 专用，把数据骰期望（~15）放大到与 HP 量级匹配 |

## 备选方案

- **A. 维持写死倍率**：拒绝——浪费 `skill_mechanics.py` 产出的结构化数据，
  且 D&D 风味全失，README 涉嫌虚假宣传。
- **B. 完整实现 D&D 5e SRD**：拒绝——MOBA 节奏与 TRPG 不同，
  完整 SRD（动作经济、法术位、长休息）会让单局对战过于复杂。
  故采用"受 D&D 5e 启发的简化 ARPG 模型"。
- **C. effects 用策略模式（每类一个 Effect 类）**：可行但过度设计——
  20 类效果逻辑都很轻（加状态/扣血/加盾），用 `if/elif` 分发更直观可读。
  若未来 effect 数量超 50 或逻辑变重，再重构为策略模式。

## 后果

正向：
- 战斗真正消费 D&D 数据，"D&D 5e 数值框架"名副其实。
- 63% 带豁免的技能、75% 带 effects 的技能、92% 带 damage 骰的技能全部生效。
- `mechanics.py` 纯函数 + 别名表，单测覆盖 6 用例，可独立演进。
- 新增 effect 类型只需在 `_CATEGORY_TABLES` 加一行别名，simulator 加一个 elif 分支。

需警惕（回滚方式）：
- `categorize_effect` 的别名表需与真实数据同步——发现未识别 effect 时应回填别名，
  避免"flavor 黑洞"（大量效果被静默丢弃）。
- `saving_throw` 的 DC 公式用 `eval` 解析（ADR-004 待处理：改 `ast.literal_eval`）。
- simulator 状态系统（`timed1/timed2`）用 list 存字典，回合衰减靠 `turns -= 1`；
  若未来需复杂状态（如层数堆叠、优先级覆盖），应改为结构化 buff 系统。
- `_hero_act` 方法因消费 20 类 effects 变长（~199 行），后续应拆分（见改进项 P1）。

## 实施阶段

- A3a：`mechanics.py` 别名归一表 + `categorize_effect` + 骰子/豁免纯函数。
- A3b：`simulator._hero_act` 消费 damage 骰 + effects + saving_throw。
- A3c：`engine.skill_raw_damage` / `apply_mitigation` 公式底座。
- A3d（本 ADR）：决策记录落盘。

## 验证

- `pytest tests/test_mechanics.py` —— 6 用例覆盖归一/骰子/DC/豁免
- `pytest tests/test_engine.py` —— 11 用例覆盖公式契约
- `pytest tests/test_battle_smoke.py::test_skill_with_dice_effects_and_saving_throw_no_crash` —— 端到端不崩
- 实测：1659 张卡随机两两对战 50 回合，0 崩溃，HP 不越界
