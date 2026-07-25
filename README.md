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

- 1659 张角色卡，来自 24 款 MOBA / 泛娱乐 IP（实测，2026-07-25）
- 7553 条结构化技能（平均 4.55/英雄）
- 技能数据完整度：92% 带 damage 骰 / 75% 带 effects / 63% 带 saving_throw
- 300+ 知名英雄使用真实技能数据，其余使用角色定位模板自动填充

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

## 依赖

- Python 3.10+（实测 3.10 / 3.11 / 3.12 / 3.13 / 3.14 均通过）
- tkinter (内置)
- pytest（仅测试需要）
- 字体: simhei.ttf (黑体), simkai.ttf (楷体) — assets/fonts/
