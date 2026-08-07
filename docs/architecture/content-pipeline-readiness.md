# 数据管线就绪评估（Content Pipeline Readiness Assessment）

> **⚠️ 状态更新（2026-08）**：本文档为 2026-08-05 的历史评估。文档中描述的 BLOCKER-1~5 已在后续工作中全部修复，ADR-005 已实施。评估结论（READY-WITH-CHANGES）中的阻断项现已解除。详见 §7 ADR-005 状态及各 BLOCKER 节的状态标注。

- **任务编号**：ENG-PIPE-001（P0）
- **评估人**：程基岩（engineering-lead）
- **调度人**：游承峰（studio-director）
- **日期**：2026-08-05
- **评估对象**：`G:\moba_battle_platform` — MOBA 英雄大乱斗 1v1 对战平台（Python 3.10+ / tkinter / D&D 5e 数值框架）
- **评估目标**：判定现有内容生产管线能否接纳本轮工作室目标「内容扩充（content expansion）」
- **评审强度**：Full
- **技术栈约束**：维持现状（Python + tkinter，零运行时依赖）

---

## 0. 执行摘要

### 就绪度判定：**READY-WITH-CHANGES**

管线的**骨架是健康的**：`core/` 已完成三次收敛重构（ADR-001 契约、ADR-002 taxonomy、ADR-003 消费路线、ADR-004 安全求值），单一真相清晰，loader 对新 IP 目录**零配置自动扫描**，规模特性**严格线性**，simulator 内存**不构成瓶颈**。

但管线的**内容生产端（tools/）落后于 core/ 的契约演进**，存在 1 个 P0 阻塞项与 3 个 P1 阻塞项。其中最严重的是：

> **`tools/card_generator.py:248-252` 的技能回退路径仍在生产违反 ADR-001 契约的 `skills: dict` 卡片** ——
> 即 SEV-2 事故（42% 英雄开战即崩）的**根因代码从未被修复**，当年只迁移了磁盘数据（`tools/migrate_skills_format.py`），没修生成器。
> 今天只要新增任何一个 IP，或为既有 IP 补任何一个技能库未覆盖的英雄，**CI 门禁 `tools/check_cards.py` 立刻转红**，且该英雄退化为 1 个技能。

这条路径当前的命中面高达 **65%**：全库 1659 张卡中仅 **581 张（35%）** 在 `data/skills/<game_id>.json` 中有真实技能数据，其余 1078 张全部走回退。技能数分布证实了这一点——**只有 574 张卡（34.6%）拥有完整 4 技能**，700 张仅 1 技能，378 张为 QWER×3 的 12 条冗余。

**结论**：内容扩充在**修复 5 项 P0/P1 改动后可以放行**；不修则每扩一个 IP 都在放大既有 65% 的内容债，且 CI 无法通过。

### 三个评估维度的结论速览

| 维度 | 结论 | 是否阻断扩充 |
|---|---|---|
| **新增 IP 目录扫描** | loader **可**零配置扫描新目录，但**只扫两层**，且与 CI 门禁的递归 glob **不对称**（假绿）；registry 未登记时中文名/目录名双双降级 | **部分阻断**（BLOCKER-2、BLOCKER-3） |
| **字段扩展** | 技能维度可扩但 `_to_skill_dict` 白名单**静默丢弃**未知字段；经济系统等新顶层维度**无槽位**，schema/simulator 均需改；新 effects 类型静默退化为 `flavor` | **部分阻断**（BLOCKER-4） |
| **规模增长** | **不构成瓶颈**。加载 O(n) 线性，0.67 ms/卡、16.4 KB/卡；simulator 5.1 KB/场（卡片按引用）；唯一风险是 UI 启动同步阻塞 | **不阻断**（P2 优化项） |

---

## 1. 评估范围、方法与复现环境

### 1.1 实地通读的文件（全部经 Read 逐行阅读）

| 文件 | 行数 | 角色 |
|---|---|---|
| `tools/card_generator.py` | 546 | 角色卡生成器（管线入口） |
| `tools/hero_calculator.py` | 504 | D&D 数值计算台 / 离线实验台 |
| `tools/skill_mechanics.py` | 527 | MOBA→D&D 技能机制映射引擎 |
| `tools/card_tool.py` | 708 | 管线 CLI（status/generate/validate/add-game…） |
| `core/loader.py` | 88 | 角色卡扫描加载 |
| `core/schema.py` | 111 | 数据契约单一真相（ADR-001） |
| `core/registry.py` | 121 | 游戏/角色/属性注册表（ADR-002） |
| `core/mechanics.py` | 193 | D&D 5e 机制处理器（ADR-003/004） |
| `core/config.py` | 19 | 兼容外观层（再导出） |
| `core/balance.py` | 13 | 战斗平衡参数 |

**补充通读**（判定管线闭环所必需）：`core/paths.py`、`core/catalog.py`、`core/simulator.py`、`tools/check_cards.py`、`tools/migrate_skills_format.py`、`tools/hero_name_mapping.py`、`ui/ui.py`（加载段）、`.github/workflows/ci.yml`、`pytest.ini`、`conftest.py`。

### 1.2 方法

只读分析为主，辅以**沙箱实证**：所有扩容副本与新 IP 模拟数据均落在系统临时目录，进程内 monkeypatch `core.loader.CARDS_DIR`，**未改动 `data/` 与现有管线源码任何一个字节**。

唯一写入：佐证脚本 `tools/_archive/_pipeline_scale_probe.py`（符合任务约束的最小原型，位于归档区，不参与运行时）。

### 1.3 复现环境与基线

```
Python 3.13.14 (Windows) — 注：CI 矩阵为 3.10/3.11/3.12/3.13
卡库规模：1659 张卡 / 24 个 IP 目录 / data/character_cards
契约门禁：python tools/check_cards.py  ->  契约校验 1659 张卡，发现问题 0 项（当前全绿）
索引一致性：_index.json total_cards=1659, total_games=24 —— 与磁盘一致
```

> **知识缺口（须回报）**：本机 `python -m pytest` 报 `No module named pytest`，**无法在本地复跑 7 个测试文件**
> （`tests/test_battle_smoke.py`、`test_catalog.py`、`test_engine.py`、`test_fuzz_battle.py`、`test_loader.py`、
> `test_mechanics.py`、`test_schema.py`）。CI（`.github/workflows/ci.yml:26`）会 `pip install pytest` 后执行，
> 故远端应有覆盖，但**本评估未能取得本地测试证据**。建议主理人确认是否需要为工作室环境预装 pytest。

---

## 2. 管线全景

```
                     ┌───────────────────────── 内容生产端 (tools/) ─────────────────────────┐
data/source/<game_id>/heroes.json          data/skills/<game_id>.json      data/skills/_templates.json
        │  (人工/爬取录入)                        │ (结构化D&D技能)                │ (6职业通用模板)
        ▼                                        │                                │
data/analysis/all_heroes_unified.json            │                                │
        │  (1659 条 unified hero)                 │                                │
        ▼                                        ▼                                ▼
   card_generator.generate_character_card() ── get_skills() ──三级回退──────────────┘
        │   · D&D 车卡：标准数组+种族加值 (:386-389)      ①精确命中 skills db (:244-246)
        │   · 战斗数值：calc_combat_stats (:255-294)      ②游戏名模糊匹配   (:236-241)
        │   · card_id = game[:3].upper()-seed (:403)      ③通用模板 random.choice (:248-252) ◀── BLOCKER-1
        ▼
data/character_cards/<game_id>/<hero>.json  +  _index.json
        │
        ├──► tools/check_cards.py  (CI 门禁, glob 递归)  ──► schema.validate_card
        ├──► tools/card_tool.py validate (第二套契约)
        │
                     └───────────────────────── 消费端 (core/ + ui/) ────────────────────────┐
        ▼
   core/loader.HeroLoader.load_all_heroes()   ◀── 两层 os.listdir（非递归）
        │   · _normalize_card 防御性归一 (:56-67)
        │   · schema.validate_card 仅告警不阻断 (:39-43)
        ▼
   build_hero_dict() -> OrderedDict{"[中文游戏名] 英雄名": card}   ◀── 键碰撞静默覆盖
        │
        ├──► ui/ui.py:120-127  (启动同步加载 + available_games 动态派生)
        ├──► core/catalog.filter_cards  (每次筛选 O(N) 全扫)
        └──► core/simulator.BattleSimulator  (消费 damage/effects/saving_throw)
```

### 2.1 架构健康面（应予保留的资产）

1. **单一真相已收敛**：`core/registry.py:28-53` 的 `GAME_REGISTRY` 是 24 个 IP 的唯一台账；`GAME_NAME_CN`（`:79`）由其派生而非独立维护；`core/config.py:16-18` 仅做再导出，调用方零改动。
2. **契约 as-code**：`core/schema.py` 不依赖 core 内其他模块（`:15` 明示），可被 loader / 迁移脚本 / CI 三方独立导入——这是内容扩充最重要的地基。
3. **防御性归一**：`core/loader.py:56-67` 对异常 skills 形状兜底，使得即使生产端产出脏数据，UI 也不崩（SEV-2 止血仍然有效）。
4. **CI 门禁已存在**：`.github/workflows/ci.yml:28-32` 在 4 个 Python 版本上跑单测 + 卡契约校验。
5. **安全求值**：`core/mechanics.py:114-136` 的 `_safe_arith` 已消除 `eval`（ADR-004），新增 IP 的 `dc_formula` / `value_formula` 走同一安全通道。

---

## 3. 维度一：新增 IP 目录扫描

### 3.1 loader 是否递归扫描 `data/character_cards/` 下的新子目录？

**答：能自动发现新目录，但只扫固定两层，不递归。**

`core/loader.py:25-31` 的实现：

```python
for game_dir in os.listdir(CARDS_DIR):              # 第 1 层：IP 目录
    game_path = os.path.join(CARDS_DIR, game_dir)
    if not os.path.isdir(game_path) or game_dir.startswith("_"):
        continue                                     # 跳过文件与 _ 前缀目录
    for filename in os.listdir(game_path):           # 第 2 层：卡片文件
        if filename.endswith(".json"):
```

沙箱实证（三种目录形态同时投放）：

```
扫描到卡数 = 1
英雄       = ['平铺英雄']
_game_dir  = ['new_ip_flat']
UI显示键   = ['[New IP Flat] 平铺英雄']
loader stdout: (无)
```

| 目录形态 | loader 行为 | 评价 |
|---|---|---|
| `new_ip_flat/a.json`（平铺） | ✅ 自动加载，**无需任何注册** | 符合内容扩充需要 |
| `new_ip_nested/season1/b.json`（三层） | ❌ **静默丢弃，零日志零告警** | **BLOCKER-2** |
| `_staging/c.json`（下划线前缀） | ⏭️ 跳过（`:27` 设计如此） | 符合预期，但见 BLOCKER-3 |

**结论**：按 IP 平铺一层，新增 IP **无需改 loader、无需改 registry 即可被加载**。这是管线对内容扩充最友好的一点。
但一旦内容团队按"IP/赛季"或"IP/系列"分子目录组织（内容扩充场景下极其自然的诉求），**卡片会无声消失**。

### 3.2 loader 与 CI 门禁的扫描不对称（假绿风险）

`tools/check_cards.py:25` 用的是**递归 glob**，`:29` 只跳过**文件名** `_` 前缀，**不跳过目录**：

```python
files = glob.glob(os.path.join(CARDS_DIR, "**", "*.json"), recursive=True)
...
if os.path.basename(f).startswith("_"):
    continue
```

同一份数据、两套扫描口径，实证结果：

```
=== loader（os.listdir 两层）vs check_cards（glob 递归）对同一份数据 ===
  loader      加载 0 张 -> []
  check_cards 校验 2 张 -> ['b.json', 'c.json']
  >> CI 门禁校验了 loader 根本加载不到的卡（假绿）
```

**影响**：内容团队提交嵌套目录或 `_staging/` 下的卡片，CI 会**校验通过并报告"已覆盖"**，但玩家在客户端里**根本看不到这些英雄**。这是内容扩充阶段最危险的一类缺陷——质量信号说谎。

### 3.3 新增 IP 是否需要额外映射？

需要，但**分两级**：加载不需要，**体验需要**。

`tools/hero_name_mapping.py` 是**英雄名**中文化表（528 条映射，覆盖 6 款游戏），由 `card_generator.py:18-21` 以 `try/except ImportError` 软引入（`:372` 使用）。它与"新增 IP"的关系是**可选增强**：不加映射，英雄名保留原始英/拼音形式。

真正影响体验的是 `core/registry.py:28-53` 的 `GAME_REGISTRY`。未登记时的降级链实证：

```
=== 新 IP 未登记 registry 时的降级表现 ===
  game='One Piece'    中文名->'海贼王'          卡目录->'one_piece'    技能文件->skills/one_piece.json
  game='My New IP'    中文名->'My New IP'    卡目录->'My_New_IP'    技能文件->skills/my_new_ip.json
```

暴露出**目录命名口径分裂**：

- `card_generator.py:38-40` 的 `_slugify()` **不做小写化** → 卡目录写成 `My_New_IP`
- `card_generator.py:187-192` 的 `_skill_file_stem()` 做了 `.lower()` → 技能文件找 `my_new_ip.json`
- 而 `core/registry.py:25-26` 注释明确规定 game_id 是**小写 snake_case**

结果：未登记 IP 的卡目录违反项目约定，且在**大小写敏感的 Linux CI** 与**不敏感的 Windows 开发机**之间行为分叉。

**新增一个 IP 的完整必做清单**（当前状态）：

| # | 动作 | 文件 | 不做的后果 |
|---|---|---|---|
| 1 | 登记 game_id 条目 | `core/registry.py:28-53` | 中文名回退英文；目录名变 `Mixed_Case`；`card_tool` 反查失败 |
| 2 | 补 `hero_file` 候选名 | `core/registry.py:61-63` | `detect_hero_file()`（`:66-75`）回退 `heroes.json` |
| 3 | 建 `data/source/<game_id>/heroes.json` | — | 无源数据 |
| 4 | 并入 `data/analysis/all_heroes_unified.json` | — | 生成器读不到（`card_generator.py:34`） |
| 5 | **建 `data/skills/<game_id>.json`** | — | **触发 BLOCKER-1，产出违约卡片** |
| 6 | （可选）补英雄名中文化 | `tools/hero_name_mapping.py` | 英雄名保留原文 |

> `tools/card_tool.py:530-594` 的 `add-game` 子命令**只完成了第 3 步**（建 `data/source/` 模板 + 说明.md），
> 且 `:542` 使用 `input()` 交互式取中文名，**无法在 CI/脚本中自动化**。第 1、2、4、5 步全靠人工记忆——
> 这是新增 IP 最容易出错的环节。

---

## 4. 维度二：字段扩展

### 4.1 当前 schema 的字段全集（实测自 1659 张卡）

```
顶层字段： attributes, card_id, difficulty, game, growth_per_level, hero, hit_die,
          playstyle_tags, primary_abilities, skills, source, stats_lv1, stats_lv18
          （+ loader 注入的运行时字段 _game_dir / _filename，见 loader.py:44-45）

技能字段： name(7553) key(7553) type(7553) action(7553) range(7553) target(7553)
          damage(7553) effects(7553) cooldown(7553) description(7553)
          saving_throw(4833) aoe_radius(405) approx(612)
```

**注意 `approx`（612 处）**：这是一个真实存在于数据中、但**不在 `core/schema.py:33-45` 白名单内**的字段。它是下一节问题的活体样本。

### 4.2 硬伤：`_to_skill_dict` 是白名单，静默丢弃未知字段

`core/schema.py:29-46` 返回的是**字面量字典**，只保留 12 个键：

```python
return {
    "name": ..., "key": ..., "type": ..., "cooldown": ..., "description": ...,
    "damage": ..., "effects": ..., "aoe_radius": ..., "saving_throw": ...,
    "action": ..., "range": ..., "target": ...,
}
```

实证——投喂内容扩充可能引入的新维度字段：

```
=== normalize_skills 字段白名单丢弃验证 ===
输入字段: ['approx','charges','cooldown','damage','description','effects','key','mana_cost','name','scaling','type']
输出字段: ['action','aoe_radius','cooldown','damage','description','effects','key','name','range','saving_throw','target','type']
被丢弃  : ['approx', 'charges', 'mana_cost', 'scaling']
```

**触发条件**：`core/loader.py:62-64` 有短路——已是 `list[dict]` 的卡不走归一化，所以**今天不会掉字段**。
但两条路径会引爆它：

1. `tools/migrate_skills_format.py:51` 对任何非 list 的卡调用 `normalize_skills` 并**写回磁盘**（`:57-59`）——**永久数据丢失**
2. BLOCKER-1 产出的 `skills: dict` 卡在 loader 处被归一（`loader.py:65-66`）——新字段在内存中即刻蒸发

**这是一颗定时炸弹**：内容团队新增 `mana_cost` / `charges` / `scaling`（经济系统与技能成长的自然载体），
在 99% 的卡上正常，在走归一化的卡上无声消失，且**没有任何告警**。

### 4.3 新 effects 类型：静默退化为 `flavor`

`core/mechanics.py:33-66` 用 20 张别名表把 effect.type 收敛到受控类别，`:73-84` 的 `categorize_effect` 对未识别项**兜底返回 `flavor`**，`core/simulator.py:494-495` 对 flavor **只打日志、不产生任何战斗效果**。

现网实测（约 5000 个 effect 实例）：

```
effect_categories = {control:801, dot:575, shield:446, aoe:426, buff:429, slow:365,
                     accel:319, heal:274, crit:224, vuln:202, sunder:152, immune:134,
                     reflect:132, invis:116, true_dmg:111, execute:105, cleanse:103,
                     revive:100, reduce:28, lifesteal:1, flavor:657}

flavor_top = [('None',352), ('force',164), ('confuse',100), ('位移',19), ('闪避',5),
              ('变身',3), ('分身',2), ('连击',2), ('钩拽',2), ('额外行动',1), ('换位',1), ('信念',1)]
```

**657 个 effect（约 13%）当前是哑弹**。其中三类值得单独点名：

- `type: None`（352 处）——`categorize_effect` 在 `:77-78` 直接返回 flavor，数据本身残缺
- `'confuse'`（100 处）——`_CONTROL` 集合里有中文 `"混乱"`（`mechanics.py:35`）却**没有英文 `confuse`**，纯粹的别名表遗漏
- `'位移'`（19 处）+ `'换位'`/`'钩拽'`——位移类机制**在 1v1 回合制模型里根本没有实现槽位**

**对内容扩充的含义**：新 IP 若引入新机制词（尤其英文别名），会**静默无效化**。管线不会报错，测试不会失败，
只有玩家发现"这个技能好像没用"。别名表必须与内容扩充同步扩展，且**需要一个"未识别 effect 类型"的可见性出口**。

### 4.4 新技能 `type`：会直接撞 CI 门禁

`core/schema.py:26` 的 `_VALID_TYPES = ("物理", "法术", "混合", "真实")` 是硬白名单，`:101-102` 校验。实证：

```
type='物理'   -> []                                    type='治疗'   -> ["skills[0].type 非法: '治疗'"]
type='法术'   -> []                                    type='增益'   -> ["skills[0].type 非法: '增益'"]
type='混合'   -> []                                    type='真实'   -> []
```

同时 `core/simulator.py:293-298` 只对 `法术` / `物理` 二分，`混合`(588 处) 与 `真实`(396 处) 落入 else 分支
按 `role == "mage"` 猜测——**已登记为合法的两个类型，消费端其实没有专属实现**。

### 4.5 新顶层维度（经济系统等）：schema 完全无槽位

```
顶层新增 economy/items -> []  (空=通过, 即 schema 不拦截也不认识)
```

`core/schema.py:78-110` 的 `validate_card` 只检查 skills / 六维 / hero.name 三件事，
对新增顶层字段**既不拦截也不认识**——意味着经济系统数据可以"塞进去"，但：

- 无契约保障（写错拼写不会被发现）
- `tools/card_tool.py:321-327` 的**第二套 required_fields 清单**不认识它，`validate` 子命令会漏检
- `core/simulator.py` 无任何消费路径
- `core/catalog.describe_card`（`catalog.py:46-95`）不展示

**需要改动的 schema 清单**见 §6。

### 4.6 双份数值定义已经漂移（内容扩充会放大）

`tools/card_generator.py:55-62` 的 `CLASS_DEF` 与 `tools/hero_calculator.py:45-94` 的 `CLASS_DEFS`
（叠加 `:199` 内联的 `armor_base`）是**两份独立的职业定义**。实测比对：

```
  role        hit_die   hp/lvl   armor(cg) armor(hc)  漂移
  tank        12/12      7/7             2         2
  fighter     10/10      6/6             3         3
  assassin     8/8       5/5             1         1
  mage         6/6       4/4             0         0
  marksman    10/10      6/6             3         2  <<< 不一致
  support      8/8       5/5             2         2
```

**射手的护甲基础值已经分叉**：生成器写卡用 `AC = 10 + DEX + 3`，数值实验台算的是 `10 + DEX + 2`。
同类重复还有 `POINT_BUY_COST`（`card_generator.py:73` vs `hero_calculator.py:29`）、
`ROLE_TEMPLATES`（`card_generator.py:101` vs `hero_calculator.py:328-335`）、
`RACIAL_BONUS`（`card_generator.py:91` vs `hero_calculator.py:338-345`）。

内容扩充期间平衡师会频繁使用数值台核对新英雄——**台账与产线不一致，会产出错误的平衡结论**。

---

## 5. 维度三：规模增长（1659 → 更大规模）

### 5.1 实测数据

佐证脚本：`tools/_archive/_pipeline_scale_probe.py`（复制真实卡库到临时目录，1x/2x/3x/5x 压测）

```
1x 现状        卡数=  1659  UI键=  1659  加载= 1.109s  常驻=  26.6MB  峰值=  26.6MB  丢键=   0
2x 扩容        卡数=  3318  UI键=  1659  加载= 2.438s  常驻=  52.8MB  峰值=  52.8MB  丢键=1659
3x 扩容        卡数=  4977  UI键=  1659  加载= 4.118s  常驻=  79.0MB  峰值=  79.0MB  丢键=3318
5x 扩容        卡数=  8295  UI键=  1659  加载= 5.733s  常驻= 131.3MB  峰值= 131.6MB  丢键=6636
```

**单卡成本：0.67 ms / 16.4 KB（tracemalloc 口径）。耗时 5.17x / 卡量 5.00x，内存 4.94x / 卡量 5.00x —— 严格线性，无超线性劣化。**

### 5.2 逐组件判定

#### (a) registry 缓存 —— 无瓶颈

`core/registry.py:28-53` 的 `GAME_REGISTRY` 是模块级常量字典，`:56` 与 `:79` 的派生表在 import 时一次性构建，
条目数等于 IP 数（24），即使扩到 100 个 IP 也是 O(100) 的静态结构。**不是瓶颈。**

`tools/card_generator.py:183-184` 的 `_skill_cache` / `_template_cache` 按 game 惰性缓存（`:195-207`、`:210-221`），
上限等于 IP 数，**无界增长风险不存在**。

唯一的小瑕疵：`core/registry.py:103-105` 的 `role_cn_to_en` **每次调用都重建反查字典**：

```python
def role_cn_to_en(role_cn: str):
    return {v: k for k, v in ROLE_NAME_CN.items()}.get(role_cn)
```

它被 `core/catalog.py:23` 在**每次筛选**时调用。虽然只有 6 个条目（绝对开销可忽略），但属于该模块自身
文档所称"消解重复逻辑"的反例，建议提为模块级常量。**P3，不阻断。**

#### (b) loader 启动耗时 —— 唯一需要关注的点，但仍非阻塞

**瓶颈定位**：`core/loader.py:29-34` 对每张卡执行一次 `open()` + `json.load()`。1659 次独立文件 I/O 是
Windows 文件系统上的主要成本。无任何缓存层——**每次应用启动都完整重读全库**，`_index.json` 存在但
loader 完全不消费它（`data/character_cards/_index.json` 仅由 `card_tool.rebuild_index` 写、给人看）。

**用户可感知的影响**在 UI 层：`ui/ui.py:118-127` 的 `_load_heroes()` 在主线程**同步**执行，无 splash、无进度条。

| 规模 | 加载耗时 | tkinter 窗口冻结时长 | 体验判定 |
|---|---|---|---|
| 1659（现状） | 1.11 s | ~1.1 s | 可接受 |
| 3318（2x） | 2.44 s | ~2.4 s | 临界 |
| 4977（3x） | 4.12 s | ~4.1 s | **明显卡顿，疑似无响应** |
| 8295（5x） | 5.73 s | ~5.7 s | Windows 可能弹"程序未响应" |

**建议阈值：卡量超过 ~3000（约 2 秒）即需引入缓存或异步加载。** 详见 §6 的 P2-1。

#### (c) simulator 内存 —— 明确不是瓶颈

```
100 场并存: 509 KB 总计 -> 5.1 KB/场 (卡片为引用,不复制)
单场 11 回合耗时 1.2 ms
```

`core/simulator.py:30-49` 的 `__init__` 只持有 `card1`/`card2` 的**引用**，不做深拷贝；
自有状态是 `cd1`/`cd2`（4 元素定长，`:51-53`）、`timed1`/`timed2`、`logs`。
本平台是 **1v1 单场**对战，同时只存在一个 `BattleSimulator` 实例。

**结论：simulator 内存与卡库规模解耦，扩到 10000 张卡也无影响。**

唯一的隐性上限：`self.logs`（`:56`）随回合无界增长，但单场 11 回合、日志条目量级为几十，可忽略。

#### (d) UI 筛选路径 —— 线性，可接受

`core/catalog.py:17-43` 的 `filter_cards` 对全量 dict 做 O(N) 遍历，UI 每次按键/切筛选都会调用：

```
query=''      命中=1659  单次=0.48 ms
query='亚'     命中=  38  单次=1.85 ms
query='亚索'    命中=   1  单次=1.90 ms
query='a'     命中=1164  单次=1.58 ms
```

外推到 8295 张卡约 9.5 ms/次——仍在人眼无感范围（<16 ms 一帧）。**不阻断。**

### 5.3 压测暴露的真实缺陷：`build_hero_dict` 显示名碰撞静默丢卡

压测表的 `丢键` 列不是测试假象，而是**实证了一个真实缺陷**。

`core/loader.py:70-82` 用**卡片内容**（而非目录）构造 UI 键：

```python
game_name = card.get("game", {}).get("name", "?")
game_cn = GAME_NAME_CN.get(game_name, game_name)
hero_name = card.get("hero", {}).get("name", "?")
display = f"[{game_cn}] {hero_name}"
result[display] = card          # ← OrderedDict 直接覆盖，无碰撞检测、无日志
```

压测中副本目录名不同（`league_of_legends__1` / `__2`），但卡内 `game.name` 相同 → 键相同 → **8295 张卡只剩 1659 个 UI 条目，6636 张静默蒸发**。

**内容扩充场景下的真实触发路径**（都不是臆测）：

1. 把一个大 IP 拆成多个目录（`mcu_phase1/` + `mcu_phase2/`），两边卡内 `game.name` 都是 `"Marvel Cinematic Universe"` → **后加载的目录覆盖先加载的，一半英雄消失**
2. 同一 IP 内英雄重名（不同形态/皮肤/时间线版本，如"路飞"与"路飞(四档)"若命名不慎重复）→ 静默覆盖
3. 未登记 IP 的英文 `game.name` 恰好与另一个未登记 IP 相同

当前 1659 张卡碰撞数为 0（已实测 `display_key_collisions= 0`），**是运气而非设计保障**。

---

## 6. 阻塞项与必改接口/字段

### BLOCKER-1（P0，硬阻断）✅ 已修复：生成器回退路径产出违反 ADR-001 契约的 `skills: dict`

**位置**：`tools/card_generator.py:248-252`

```python
    # 回退到通用模板（占位游戏 skills={} 也会落到这里，属预期，不报错）
    templates = _load_templates().get(role, [])          # -> list[6]，元素是【单个技能 dict】
    if not templates:
        templates = [["Q:普攻", "W:技能一", "E:技能二", "R:大招"]]
    return random.choice(templates)                       # -> 返回【1 个技能 dict】，而非 list[4]
```

`data/skills/_templates.json` 的形状是 `{role: [skill_dict × 6]}`，因此 `random.choice` 取出的是**单个技能字典**。
该返回值在 `card_generator.py:438` 被直接写进 `card["skills"]`。

**端到端实证**：

```
=== _templates.json[role] 的形状 ===
  t["fighter"] 类型= list 长度= 6
  t["fighter"][0] 类型= dict -> 是单个技能dict: ['name','key','type','action']

=== get_skills 回退路径实测（模拟新 IP，无 skills/<id>.json）===
  role=fighter  返回类型=dict  长度=11    !! 返回单个技能 dict
  role=mage     返回类型=dict  长度=10    !! 返回单个技能 dict

=== 生成整张卡并跑契约校验（新 IP 英雄）===
  card["skills"] 类型 = dict
  schema.validate_card -> ['skills 不是 list（契约要求 list[Skill]）']

=== 该卡进 simulator（core/simulator.py:180-186 _get_skill）===
  _get_skill(card,0) = None   <- dict 型 skills 直接返回 None
```

**这正是 ADR-001 / SEV-2 事故的根因**。当年的处置（`tools/migrate_skills_format.py`）只迁移了**磁盘数据**，
`core/loader.py:56-67` 加了**运行时防御**，但**生成器本身从未修复**。

**血迹仍在全库中清晰可见**：

```
=== 现网卡片技能数分布（4=完整）===
   1 个技能:   700 张  ← 与 ADR-001 记载的 "42.2%（700/1659）" 完全吻合：dict 被归一为 list[1]
   3 个技能:     7 张
   4 个技能:   574 张  ← 仅 34.6% 完整
  12 个技能:   378 张  ← QWER×3 冗余，simulator 只用索引 0-3（:51-53, :312-321），后 8 条是死数据
```

**与技能库覆盖率完全相关**（35% 覆盖 ↔ 65% 退化）：

```
   IP目录                          卡数     技能库条目     命中     覆盖率
   300_heroes                   149       149    149    100%      ← 4技能齐全
   dc / demon_slayer / genshin / harry_potter / mcu / one_piece
   overwatch2 / three_body / feiren_xueyuan / hong_kong_comics
   shuguang_heroes                                      100%      ← 4技能齐全
   ---------------------------------------------------------------
   arena_of_valor               115        10     10      9%      ← {1:63, 4:10, 12:42}
   smite                        130        12     12      9%      ← {1:79, 4:12, 12:39}
   yinghunzhiren                112        10     10      9%
   dota2                        126        15     12     10%
   marvel_super_war              65         7      7     11%
   onmyoji_arena                 83        10     10     12%
   vainglory                     54         7      7     13%      ← {1:25, 3:7, 12:22}
   pokemon_unite                 69        10     10     14%
   mobile_legends_bang_bang     132        20     20     15%
   heroes_of_the_storm           90        18     18     20%
   league_of_legends            172        50     38     22%      ← {1:82, 4:38, 12:52}
   honor_of_kings               116        32     32     28%
   ---------------------------------------------------------------
   合计                        1659              581     35%
```

**12 个覆盖率 100% 的 IP 全部是纯 4 技能；12 个低覆盖 IP 全部混有 1/3/12 技能卡。相关性为 1，因果链闭合。**

**对内容扩充的阻断性**：
- 新增任意 IP（技能库必然从空开始）→ 所有卡 `skills: dict` → **`tools/check_cards.py` 非零退出 → CI 红 → 无法合并**
- 为既有 IP 补录英雄，只要不在 `skills/<game_id>.json` 中 → 同上
- 即使绕过 CI，该英雄在客户端只有 **1 个技能**，且 `random.choice` 使其**不可复现**（虽有 `random.seed(rng_seed)` 于 `:366`，但模板选择随之绑定到 seed，语义上仍是"随机抽一个技能当全部技能"）

**必改**：`get_skills()` 的返回类型契约必须锁死为 `list[Skill]`（长度 4）。

---

### BLOCKER-2（P1，阻断嵌套目录组织）✅ 已修复：loader 只扫两层且静默丢弃

**位置**：`core/loader.py:25-31`

**必改**：改为递归遍历（`os.walk`），或**显式拒绝并告警**——但绝不能像现在这样静默。
考虑到 `card_tool.py:104-117` 的 `load_existing_cards` 是**同样的两层实现**，两处需同步。

---

### BLOCKER-3（P1，质量信号失真）✅ 已修复：CI 门禁与 loader 扫描口径不一致

**位置**：`tools/check_cards.py:25`（递归 glob，不跳目录）vs `core/loader.py:25-31`（两层，跳 `_` 目录）

**必改**：门禁必须**复用 loader 的扫描函数**，保证"CI 校验的集合 == 运行时加载的集合"。
这是所有内容质量保障的前提——口径不一致时，绿色 CI 没有意义。

---

### BLOCKER-4（P1，新维度落地即丢数据）✅ 已修复：`_to_skill_dict` 白名单静默丢弃未知字段

**位置**：`core/schema.py:29-46`

**必改**：改为"保留未知字段 + 补齐已知默认值"（`{**raw, **defaults}` 语义），
或至少在丢弃时产出 warning 并由 `migrate_skills_format.py` 拒绝写回。
经济系统、技能资源消耗、技能成长曲线等新维度全部依赖这一点。

---

### BLOCKER-5（P1，身份不稳定）✅ 已修复：`card_id` 在局部生成时被重写，且前缀会碰撞

**位置**：`tools/card_generator.py:403`（`card_id = f"{game[:3].upper()}-{rng_seed:04d}"`）
+ `tools/card_tool.py:291` / `card_generator.py:475`（`rng_seed = total + idx + 1000`，`total` 是**本次运行内**的累计计数）

实证：

```
现有 one_piece card_id 前5 = ['ONE-2262','ONE-2276','ONE-2265','ONE-2261','ONE-2263']

=== 模拟 generate --game "One Piece" 局部重生成（不写盘）===
局部生成将得到 = ['ONE-1000','ONE-1001','ONE-1002','ONE-1003','ONE-1004'] ...共 22
原 One Piece ID 会被改写 = ['ONE-2259','ONE-2260',...] -> 变为上面这批
```

**`card_id` 不是稳定标识，而是"全量生成时的位置序号"。** 内容扩充的标准动作
（`python card_tool.py generate --game <IP>`，正是 `card_tool.py:583,594` 与 `add-game` 引导用户执行的命令）
会把该 IP 下**所有既有卡的 ID 全部重写**。

同时前缀空间已经拥挤（`game[:3].upper()`）：

```
前缀号段： 300:1000..1148  ARE:1149..1263  DC :1264..1285  DAW:1286..1336
          DEM:1337..1350  HER:1550..1751  MAR:2040..2126  ONE:2259..2280
```

- `HER` = Heroes of the Storm(90) + Heroes Evolved(112) **已经共用前缀**
- `MAR` = Marvel Super War(65) + Marvel Cinematic Universe(22) **已经共用前缀**
- `DC ` **带一个尾随空格**（`"DC Universe"[:3]`）——card_id 里含空格，属数据卫生缺陷
- 新 IP 若前缀撞上低号段（如新增"300 Legends" → `300-1000..`），与现有 `300-1000..1148` **全量冲突**

当前全库 1659 个 ID 唯一（已实测），**靠的是全量生成的连续计数器，而非任何唯一性保证**。

**必改**：`card_id` 改为内容无关的稳定标识（如 `<game_id>:<hero_slug>` 或全量生成时持久化的 ID 台账），
并在 `check_cards.py` 增加全局唯一性断言。

---

### 次级问题清单（不阻断，但内容扩充期会持续放大）

| # | 位置 | 问题 | 影响 |
|---|---|---|---|
| N-1 | `tools/card_generator.py:55-62` vs `tools/hero_calculator.py:45-94,199` | 双份职业定义，**射手 armor 已漂移 3 vs 2** | 平衡结论错误 |
| N-2 | `tools/card_tool.py:254-256` | `--game` 过滤器条件含 `game_filter in h["name"]`。实测 `--game 亚` 命中 25 位英雄、跨 11 款游戏 | 误触发跨 IP 批量重写 |
| N-3 | `tools/card_tool.py:226` | 硬编码 `{len(detailed)}/16`，实际已 24 个 IP | 状态报告失真 |
| N-4 | `tools/card_generator.py:6` | docstring 仍写"16 款游戏 1503 位英雄" | 文档失真 |
| N-5 | `tools/card_tool.py:321-327` | 与 `core/schema.py` 并存的**第二套 required_fields 契约** | 双真相，扩字段需改两处 |
| N-6 | `tools/skill_mechanics.py` | **全项目无任何运行时引用**（仅 `core/engine.py:14` 注释提及）。新 IP 的"技能描述串 → 结构化 D&D 技能"缺自动化通路 | 新 IP 技能只能手工写 JSON |
| N-7 | `tools/skill_mechanics.py:464,480` | f-string 缺 `d`：产出 `"28+STR 伤害"` 而非 `"2d8+STR"`（已实测） | 描述文案错误 |
| N-8 | `tools/skill_mechanics.py:86`(键`回复`)、`:148`(键`冰冻`) | 字典重复键（AST 检测确认） | 静默覆盖，lint 异味 |
| N-9 | `tools/card_generator.py:297-324` | `assign_difficulty` 硬编码约 60 个英雄名 | 新 IP 难度全部走 role 默认值 |
| N-10 | `core/mechanics.py:35` | `_CONTROL` 有中文"混乱"无英文 `confuse`（100 处命中 flavor） | 机制哑火 |
| N-11 | `core/registry.py:103-105` | `role_cn_to_en` 每次调用重建反查字典 | 微小浪费，反自身设计意图 |
| N-12 | `core/loader.py:47-48` | 加载异常仅 print，无计数、无非零退出 | 批量损坏文件可能被忽略 |
| N-13 | `tools/card_tool.py:542` | `add-game` 用 `input()` 交互取中文名 | 无法 CI 自动化 |

---

## 7. ADR-005 草案

> 下文为草案条目，沿用 `deliverables/engineering-assurance/` 现有 ADR 风格（标题 / 状态 / 背景 / 决策 / 备选方案 / 后果）。
> **建议落盘路径**：`deliverables/engineering-assurance/ADR-005-content-expansion-pipeline-contract.md`
> **状态需主理人与用户审批后方可置为 Accepted。**

---

### ADR-005: 内容扩充管线契约化（生成端对齐 schema + 稳定卡标识 + 统一扫描口径）

- **状态**：Implemented
- **日期**：2026-08-05
- **作者**：程基岩（engineering-lead）
- **关联**：ADR-001（skills 契约归一）、ADR-002（taxonomy 收敛）、ADR-003（D&D 消费路线）

#### 背景

ADR-001 把 `skills` 的规范表示定为 `list[Skill]`，并在 `core/schema.py` 建立 as-code 契约、
在 `core/loader.py` 建立运行时防御、用 `tools/migrate_skills_format.py` 迁移了磁盘数据。
但**生产端从未纳入该契约**：`tools/card_generator.py:248-252` 的通用模板回退路径至今返回**单个技能 dict**，
即 SEV-2 的根因代码。全库现状证实其影响面——仅 574/1659（34.6%）的卡拥有完整 4 技能，
700 张为 `list[1]`（迁移残留），378 张为 QWER×3 冗余；`data/skills/` 对卡库的真实覆盖率仅 **35%**。

本轮工作室目标是内容扩充。新增 IP 的技能库必然从空开始，届时**每一张新卡都会命中该回退路径**，
导致 CI 门禁 `tools/check_cards.py` 非零退出，内容无法合入。

同时，评估发现三项与扩充直接冲突的设计缺陷：
(a) `card_id`（`card_generator.py:403`）由全量生成时的位置序号派生，局部生成 `--game <IP>` 会重写既有 ID；
(b) `core/loader.py:25-31` 两层扫描与 `tools/check_cards.py:25` 递归 glob 口径不一致，产生"CI 假绿"；
(c) `core/schema.py:29-46` 的 `_to_skill_dict` 是字段白名单，静默丢弃 `mana_cost` / `scaling` 等新维度字段
（现网 `approx` 字段 612 处已处于该风险敞口下）。

#### 决策

将内容管线的**生产端纳入与消费端同一套契约**，具体四条：

1. **生成端类型契约**：`get_skills()` 的返回类型锁定为 `list[Skill]`（长度恒为 4）。
   通用模板回退改为 `_load_templates()[role][:4]`（或按槽位补齐），并在 `card_generator` 出口处
   调用 `core.schema.validate_card`，**校验失败即拒绝写盘**（fail-fast，而非交给下游防御）。
   新增单测：对每个 role、对"技能库未命中"路径断言 `len(skills) == 4` 且 `validate_card() == []`。

2. **稳定卡标识**：`card_id` 语义从"生成序号"改为"内容标识"，采用 `<game_id>:<hero_slug>`
   （例：`one_piece:蒙奇·D·路飞`）。理由：与 `data/character_cards/<game_id>/<hero>.json` 的物理路径同构，
   天然唯一、局部生成幂等、无需台账。旧 `card_id` 保留为 `legacy_card_id` 字段一个版本周期。
   `tools/check_cards.py` 增加**全局唯一性断言**。

3. **统一扫描口径**：把目录遍历下沉为 `core/loader.py` 的单一实现 `iter_card_files(root)`（递归 `os.walk`，
   跳过 `_` 前缀的文件与目录），由 `HeroLoader.load_all_heroes`、`tools/check_cards.py`、
   `tools/card_tool.load_existing_cards` 三方共同复用。同时 `build_hero_dict` 增加
   **显示名碰撞检测**：碰撞时告警并以 `<game_id>/<filename>` 消歧，禁止静默覆盖。

4. **字段开放性**：`_to_skill_dict` 由"白名单重建"改为"已知字段补默认 + 未知字段透传"
   （`{**defaults, **raw}` 语义）。`validate_card` 保持只校验已知契约字段，
   对未知字段不拦截但由新增的 `report_unknown_fields()` 汇总输出，作为 schema 演进的观测入口。
   `_VALID_TYPES` 与 `core/mechanics.py` 的 effect 别名表纳入同一份"机制词表"文档，
   新增机制词必须同时登记别名与 simulator 消费分支，否则 CI 告警。

#### 备选方案

- **A. 只修生成器回退，不动 card_id / 扫描口径**：拒绝。能解 CI 红，但 BLOCKER-2/3/5 会在内容扩充
  中途以"英雄莫名消失""ID 对不上"的形态爆发，届时已有大量新内容落盘，修复成本远高于现在。
- **B. 放弃通用模板回退，强制每个英雄手写技能 JSON**：拒绝。当前 65% 的卡依赖回退，
  强制手写等于要求先补 1078 个英雄的技能数据才能动内容扩充，与本轮目标冲突。
  正确做法是让回退**产出合约内的 4 技能占位**，并用 `approx: true` 标记待人工精修。
- **C. 用 pydantic / jsonschema 做契约**：拒绝。项目核心优势是**零运行时依赖**（ADR-004 已确立此原则），
  且 `core/schema.py` 现有 111 行纯函数实现已满足需要。
- **D. 在 loader 侧继续加防御，不动生成端**：拒绝。这正是 SEV-2 之后采取的策略，
  三个月后的今天证明它只止住了崩溃，没有阻止 65% 的内容退化——**防御层掩盖了生产端缺陷**。

#### 后果

正向：
- 新增 IP 从"必然 CI 红"变为"开箱即通过"，内容扩充解锁。
- `card_id` 幂等后，局部生成 `--game <IP>` 成为安全的日常操作，支持增量补录英雄。
- CI 校验集合 == 运行时加载集合，质量信号恢复可信。
- 经济系统等新维度可以先落数据、后接消费，不再有静默丢字段风险。

需警惕：
- **`card_id` 变更是破坏性改动**。需确认无外部系统（存档、平衡表、UI 收藏）以旧 ID 为键；
  必须提供一次性迁移脚本并保留 `legacy_card_id` 过渡期。**此项须用户明确审批后执行。**
- 递归扫描会把 `data/character_cards/` 下**任何**深度的 JSON 纳入加载，需确保备份/草稿文件
  统一放在 `_` 前缀目录内，否则会被误加载。
- 修复回退路径后，`generate --all` 会改写 700 张 `list[1]` 卡为 4 技能占位——
  这是内容层面的**大规模变更**，须先 `--dry-run` 出 diff 报告并经文策渊（内容）与严守真（测试）会签。
- 未知字段透传后，脏字段也会被保留，需依赖 `report_unknown_fields()` 的观测输出做定期清理。

---

## 8. 就绪度判定与改动清单

### 8.1 判定

# **READY-WITH-CHANGES**

**可以启动内容扩充，但必须先完成 P0 + P1 共 5 项改动。**

**判定依据**：
- ✅ **架构地基合格**：单一真相已收敛，契约 as-code，CI 门禁存在，安全求值到位
- ✅ **规模无瓶颈**：线性 O(n)，simulator 与卡量解耦，扩到 5x 仍在可控范围
- ✅ **新 IP 可零配置加载**：平铺目录即被扫描，不需要改 loader
- ❌ **生产端未纳入契约**：BLOCKER-1 使"新增 IP"这一核心动作**必然导致 CI 失败**
- ❌ **身份与扫描口径不稳**：BLOCKER-2/3/5 会在扩充中途以数据丢失形态爆发
- ⚠️ **既有内容债 65%**：管线在修复前每扩一个 IP 都在放大这一债务

### 8.2 改动清单（按优先级排序）

| 优先级 | ID | 改动 | 位置 | **是否阻断内容扩充** | 预估 |
|---|---|---|---|---|---|
| **P0** | C-1 | `get_skills()` 回退返回 `list[Skill]`（len=4）；生成器出口接 `validate_card` fail-fast；补 role×回退路径单测 | `tools/card_generator.py:229-252,438` | **是 — 硬阻断，不修则 CI 必红** | S |
| **P1** | C-2 | 统一扫描口径：下沉 `iter_card_files()` 到 `core/loader.py`，三方复用 | `core/loader.py:25-31`、`tools/check_cards.py:25`、`tools/card_tool.py:104-117` | **是 — 嵌套目录静默丢卡 + CI 假绿** | S |
| **P1** | C-3 | `build_hero_dict` 增加显示名碰撞检测与消歧，禁止静默覆盖 | `core/loader.py:70-82` | **是 — 多目录同 IP 场景静默丢一半英雄** | XS |
| **P1** | C-4 | `_to_skill_dict` 改为未知字段透传；新增 `report_unknown_fields()` | `core/schema.py:29-46` | **是 — 新维度（经济/资源/成长）落地即丢数据** | XS |
| **P1** | C-5 | `card_id` 改为 `<game_id>:<hero_slug>`；保留 `legacy_card_id`；CI 加唯一性断言 | `tools/card_generator.py:403,475`、`tools/card_tool.py:291`、`tools/check_cards.py` | **是 — 局部生成重写既有 ID（须用户审批）** | M |
| **P2** | C-6 | 新增 IP 登记检查：`registry` 未登记时**告警**而非静默降级；`_slugify` 补 `.lower()` 对齐 game_id 约定 | `core/registry.py`、`tools/card_generator.py:38-40` | 否 — 降级可用，但目录命名违约 + Linux/Windows 分叉 | XS |
| **P2** | C-7 | loader 引入 `_index.json` 缓存或 mtime 增量加载；UI 改异步/带 splash | `core/loader.py`、`ui/ui.py:118-127` | 否 — **卡量 >3000 时转为 P1** | M |
| **P2** | C-8 | 合并双份职业定义为单一真相（修复射手 armor 3 vs 2 漂移） | `tools/card_generator.py:55-62`、`tools/hero_calculator.py:45-94,199` | 否 — 但会导致平衡结论错误 | S |
| **P2** | C-9 | `--game` 过滤器移除 `in h["name"]` 条件，改精确匹配 game_id / 显示名 / 中文名 | `tools/card_tool.py:254-256` | 否 — 但误操作会跨 11 个 IP 批量重写 | XS |
| **P2** | C-10 | `card_tool.py:321-327` 第二套契约并入 `core/schema.py` | `tools/card_tool.py:310-411` | 否 — 双真相，扩字段需改两处 | S |
| **P2** | C-11 | effect 别名表补 `confuse` 等英文别名；新增"未识别 effect 类型"统计出口 | `core/mechanics.py:33-66,73-84` | 否 — 但新机制会静默哑火（现存 657 处） | XS |
| **P3** | C-12 | 修 `skill_mechanics.py` f-string 缺 `d`（`:464,480`）与重复字典键（`:86,:148`）；决定该模块**接线或归档** | `tools/skill_mechanics.py` | 否 — 当前无运行时引用 | S |
| **P3** | C-13 | `add-game` 补全 registry 登记 + skills 骨架，移除 `input()` 改 CLI 参数 | `tools/card_tool.py:530-594` | 否 — 但新增 IP 的 6 步清单全靠人工记忆 | S |
| **P3** | C-14 | 清理陈旧文案：`card_tool.py:226` 硬编码 `/16`、`card_generator.py:6` "16 款 1503 位" | 同左 | 否 | XS |
| **P3** | C-15 | `role_cn_to_en` 反查表提为模块级常量 | `core/registry.py:103-105` | 否 | XS |

### 8.3 建议的执行顺序

```
第 1 批（解除阻断，可并行）  C-1 ─┬─ C-2 ─ C-3        ← 完成后「新增 IP」端到端跑通、CI 转绿
                              └─ C-4
第 2 批（须用户审批）        C-5                      ← 破坏性 ID 变更，需迁移脚本 + 会签
第 3 批（扩充期护栏）        C-6, C-8, C-9, C-11
第 4 批（规模触发）          C-7                      ← 卡量逼近 3000 时提为 P1
第 5 批（卫生）              C-10, C-12 ~ C-15
```

### 8.4 内容扩充放行的验收条件（建议交严守真固化为测试）

1. 新建一个空 IP 目录 + 空 `skills/<id>.json`，跑 `generate --game <新IP>` → `check_cards.py` 退出码为 0
2. 全部新卡 `len(skills) == 4` 且 `schema.validate_card() == []`
3. 对同一 IP 连续跑两次 `generate --game <IP>`，`card_id` 与文件内容**逐字节一致**（幂等）
4. 嵌套目录 `<ip>/<season>/x.json` 要么被加载，要么产出明确告警——不得静默
5. 构造两个 `game.name` 相同的目录 → `build_hero_dict` 产出告警且**不丢卡**
6. 技能新增 `mana_cost` 字段 → 经 loader 往返后字段仍在
7. `loader.load_all_heroes()` 在目标卡量下耗时 < 2s，或 UI 已异步化

---

## 附录 A：佐证脚本与复现命令

**规模压测脚本**（本次评估唯一写入，位于归档区，不参与运行时）：

```
tools/_archive/_pipeline_scale_probe.py
```

只读保证：不修改 `data/` 任何文件；扩容副本落在系统临时目录，运行结束即删除；
仅进程内 monkeypatch `core.loader.CARDS_DIR`，不改动管线源码。

```bash
# 规模压测（1x/2x/3x/5x）
python -u tools/_archive/_pipeline_scale_probe.py

# 当前契约门禁状态
python tools/check_cards.py

# 管线状态总览
python tools/card_tool.py status
```

## 附录 B：本评估未覆盖 / 待补事项

1. **本地无 pytest**，7 个测试文件未能本地复跑（见 §1.3）。CI 有覆盖，但本评估缺本地测试证据。
2. `data/source/` 的录入规范与 `data/analysis/all_heroes_unified.json` 的**生成脚本未在仓库中定位到**
   （`card_tool.py:593` 提示"重新运行数据分析"，但未指明脚本）。这是新增 IP 第 4 步的缺口，**建议回问主理人**。
3. `battle_platform/` 顶层目录未纳入本次评估范围（与 `core/paths.py:15-18` 的注释所述路径语义存在出入，
   注释写 `battle_platform/core` 而实际 `PROJECT_ROOT` 解析为仓库根）。
4. 经济系统的**具体字段设计**属策划域，本文只给出 schema 侧的承载改造点，
   具体维度定义待文策渊（design-strategist）的 GDD 产出后再做契约细化。
5. 未评估 `assets/`、`ui/` 的资源侧扩充成本（新 IP 是否需要头像/图标等资产）——属林绘澄（美术）域。
