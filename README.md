# MOBA 英雄大乱斗 — 1v1 对战平台

## 启动

```bash
python main.py
```

> 注：`main.py` 位于项目根目录，无需 `cd` 到子目录。

## 功能

| 功能 | 说明 |
|------|------|
| 🔍 搜索 | 按英雄名/游戏名搜索 |
| 🎲 随机英雄 | 一键随机双方英雄 |
| ⚔️ 开始对战 | 逐行动画播放战斗过程 |
| ⚡ 快速模拟 | 跳过动画，直接显示结果 |
| ⏩ 速度调节 | 0.1x~1.5x 动画速度滑块 |

## 战斗系统

- 战斗模型：D&D 5e 数值框架（技能骰伤害 / effects / 豁免已由引擎消费，见 ADR-003）
- 物理伤害 = ATK × 技能倍率 × (1 − 对方AC × 0.005)，最低保留30%
- 法术伤害 = AP × 技能倍率 × (1 − 对方WIS豁免 × 0.03)，最低保留30%
- 技能倍率（按技能位）：普攻=1.0 / 技能一=1.3 / 技能二=1.1 / 大招=2.0
- 最终伤害还会乘以 DAMAGE_SCALE=0.35（全局平衡旋钮，见 core/balance.py）与等级缩放（等级越高伤害越高）
- 暴击概率 = 基础10% + DEX调整×2%，最低5%
- 暴击伤害 = 基础150% + DEX调整×5%
- AI决策：优先大招(50%概率) → 技能一 → 技能二 → 技能三
- 技能冷却：技能一=0回合，技能二=1回合，技能三=2回合，大招=4回合

## 英雄池

- 5926 张角色卡，来自 31 款 MOBA / 泛娱乐 IP（实测）
- 4208 条技能数据，100% 带 damage 骰 / 90% 带 effects / 85% 带 saving_throw
- 技能数据由 `data/skills/` 目录下的结构化 JSON 驱动，部分 IP 使用通用模板回退

## 角色卡管理

```bash
cd tools
python card_tool.py status            # 查看角色卡状态
python card_tool.py generate --all    # 全量重新生成
python card_tool.py generate --game 王者荣耀   # 生成指定游戏
python card_tool.py validate          # 校验合法性
python card_tool.py search 亚索       # 搜索英雄
python card_tool.py info 亚索         # 查看详情
```

## 验证管线

```bash
python tools/check_cards.py    # 磁盘级契约校验（validate_card + card_id 唯一性 + skill 格式）
pytest                         # 单元测试（需安装 pytest）
```

> **注意**：`check_cards.py` 仅校验磁盘上的卡片数据是否符合 `core/schema.py` 契约（字段完整性、技能格式、card_id 唯一性等），**不覆盖 loader 注入后的运行时状态**（如 `_game_dir`、`_filename` 等运行时字段）。完整的行为验证请通过 `pytest` 测试套件覆盖。

## 依赖

- Python 3.10+（实测 3.10 / 3.11 / 3.12 / 3.13 / 3.14 均通过）
- tkinter (内置)
- pytest（仅测试需要）
- 字体: simhei.ttf (黑体), simkai.ttf (楷体) — assets/fonts/

## 文档索引

| 文档 | 位置 | 说明 |
|------|------|------|
| 架构决策记录（ADR） | `docs/architecture/content-pipeline-readiness.md` §7 | ADR-001~005，含内容管线契约化决策 |
| 质量审计报告 | `production/quality-audit-report.md` | 历史审计（数据已过期，仅供存档参考） |
| 角色卡索引 | `data/character_cards/_index.json` | 自动生成的卡片索引（可能滞后于实际磁盘数据） |

### 开发者快速入门

```bash
# 运行测试
pip install pytest && pytest

# 编辑/生成卡片
cd tools
python card_tool.py status                 # 查看卡片状态
python card_tool.py generate --all         # 全量重新生成（谨慎操作）
python card_tool.py validate               # 校验卡片合法性

# 契约门禁
python tools/check_cards.py                # CI 同款校验
```

### Runbook：常用诊断命令

```bash
python main.py                             # 启动游戏 UI
python tools/check_cards.py                # 磁盘契约校验（CI 门禁）
python -m pytest                           # 全量单元测试
python tools/card_tool.py status           # 管线状态总览
python tools/card_tool.py search <关键词>   # 搜索英雄
python tools/card_tool.py info <英雄名>    # 查看英雄详情
```
