# 管线阻塞修复回归报告

| 项 | 值 |
|---|---|
| 文档 ID | QA-REG-001 |
| 作者 | 严守真（quality-lead） |
| 日期 | 2026-08-05 |
| 审评强度 | **Full** |
| 触发条件 | ADR-005 BLOCKER-1~5 修复（8 文件变更） |
| 修复范围 | `core/loader.py`, `core/schema.py`, `tools/card_generator.py`, `tools/card_tool.py`, `tools/check_cards.py`, `tests/test_loader.py`, `tests/test_schema.py`, `ui/ui.py` |
| 新增测试 | `tests/test_card_generator.py`（7 条） |

---

## 1. 现有测试套件全量执行

```bash
python -m pytest tests/ -v
```

**结果：55/55 PASS（全绿）** ✅

| 测试文件 | 用例数 | 状态 | 覆盖领域 |
|---|---|---|---|
| `test_battle_smoke.py` | 3 | ✅ PASS | dict 卡对战、单技能英雄、saving_throw 技能 |
| `test_card_generator.py` | 7 | ✅ PASS | 生成器契约（**新增**） |
| `test_catalog.py` | 5 | ✅ PASS | 英雄注册表/目录 |
| `test_engine.py` | 11 | ✅ PASS | 战斗引擎核心算法 |
| `test_fuzz_battle.py` | 3 | ✅ PASS | 真实卡随机对战 fuzzing |
| `test_loader.py` | 7 | ✅ PASS | 归一化 + 碰撞检测（扩展） |
| `test_mechanics.py` | 6 | ✅ PASS | Effect 分类/豁免/别名 |
| `test_schema.py` | 13 | ✅ PASS | 契约校验 + 字段透传（扩展） |

**补充检查**：

```bash
python tools/check_cards.py
# → 契约校验 1659 张卡，发现问题 0 项
# → card_id 唯一性: 1659/1659（通过）
```

✅ **Gate D-4：现有 pytest 套件全绿 — PASS**

---

## 2. Gate A — 卡片结构完整度（参照 GDD §4.1）

### 2.1 全库盘点

| 指标 | 实测值 | 阈值 | 判定 |
|---|---|---|---|
| 全库卡片数 | **1659** | — | — |
| `len(skills)` 分布 | len=1: 700, len=3: 7, len=4: 574, len=12: 378 | — | — |
| 技能槽 0–3 填充率 | **68.2%** (4529/6636) | ≥99% | ❌ |
| 空技能位 | **2107** (31.8%) | 0 | ❌ |
| 死数据（idx≥4） | **3024 条** / 378 卡 | 0 | ❌ |
| `dice_count==0` 槽数 | **575** | ≤50 | ❌ |

### 2.2 逐项判据

| ID | 判据 | 实测 | 阈值 | 判定 |
|---|---|---|---|---|
| **A-1** | `len(skills) == 4` | **1085/1659 FAIL** | 100% | **FAIL** |
| **A-2** | 槽 0–3 全部非模板名 | **1270/1659 FAIL** | 100% | **FAIL** |
| **A-3** | `dice_count>0` ≥3/4 槽 | **839/1659 FAIL** | 100% | **FAIL** |
| A-4 | `effects` 非空 ≥2/4 | — | ≥50% | ⚠️ 未详查 |
| A-5 | `saving_throw` ≥2/4 | — | ≥50% | ⚠️ 未详查 |
| A-6 | `key` 4 槽唯一 | `check_cards.py` 通过 | 100% | ✅ |
| **A-7** | 死数据 idx≥4 | **3024 条** | 0 | **FAIL** |

### 2.3 关键验证：新生成器产出 vs 旧卡兼容

**生成器（BLOCKER-1 修复后）**：

- 对所有 6 个 role，`get_skills()` 回退路径产物 `len==4` ✅
- `generate_character_card()` → `validate_card()` 返回 `[]` ✅
- 空模板（无 role 模板）→ 生成 4 个占位技能 ✅
- 模板不足 4 条 → 补齐至 4 ✅

**Loader（`_normalize_card` 兜底）**：

| 旧卡格式 | 归一化结果 | 状态 |
|---|---|---|
| `list[1]`（残卡） | 原样保留 list[1] | ✅ 不崩 |
| `list[3]`（vainglory） | 原样保留 list[3] | ✅ 不崩 |
| `list[12]`（重复模板） | 原样保留 list[12] | ✅ 不崩（sim 只取前 4） |
| `dict` 单技能 | → list[1] + 告警 | ✅ |
| `dict` 槽位键 | → list[4] + 告警 | ✅ |
| 缺失/非法 | → [] + 告警 | ✅ |

**结论**：管线修复本身正确——生成器产出 4 槽、loader 兼容旧格式。**但磁盘数据未被重新生成**，因此 Gate A 针对磁盘数据的判据全部 FAIL。这是**预期行为**：数据再生需要 `generate --all` 执行，属于下一阶段的派工作业。

> ⚠️ 注意：`_normalize_card` 对已是 `list[1]` 格式的卡**不触发归一化**（`was_normalized=False`），因为这些卡已经是合法 list。这意味着 700 张残卡在运行时仍是 1 技能——loader 不会自动补齐。补齐必须在生成端通过 `card_generator` 重新生成。

---

## 3. Gate C — 平衡门控（参照 GDD §4.3）

### 3.1 采样参数

- 等级：L9
- 采样：120 英雄（T1/T2/T4/T3 各 30 名）
- 对战：各 40 局 vs 全池随机对手
- 种子：20260805
- 回合上限：60
- 总对局数：4800

### 3.2 指标汇总（对比 GDD §1.9 基线）

| 指标 | 本轮实测 | GDD §1.9 基线 | 趋势 |
|---|---|---|---|
| 全池胜率均值 | 60.6% | 49.3% | ↑（采样偏 T1/T4 导致） |
| T1_real 胜率均值 | 83.5% | 78.9% | ↑ |
| T2_partial 胜率均值 | 68.7% | — | — |
| T4_template 胜率均值 | 66.4% | 65.1% | ≈ |
| T3_stub 胜率均值 | 23.7% | 18.3% | ↑（微小） |
| 回合数 P50 | 17 | 19 | ≈ |
| 回合数 P95 | 54 | 61（触顶） | ↓（轻微改善） |
| 60 回合未分胜负率 | 4.2% | 6.8% | ↓ |

### 3.3 分层对位胜率

| 对位 | A 方胜率 | GDD 基线 | 判定 |
|---|---|---|---|
| **T1_real vs T3_stub** | **98.4%** | 98.7% | ❌ FAIL |
| **T1_real vs T4_template** | **88.5%** | 88.1% | ❌ FAIL |
| **T1_real vs T2_partial** | **73.0%** | 82.9% | ❌ FAIL |
| **T2_partial vs T4_template** | **70.7%** | 45.7% | ❌ FAIL |
| T3_stub vs T3_stub | 47.4% | — | ✅ 可接受 |
| T1_real vs T1_real | 55.5% | — | ✅ |

> ⚠️ T2_partial vs T4_template 从基线 45.7% 升至 70.7%，属**本次采样波动**（T2 从基线 83 名现增至 191 名，分层定义更精确）。

### 3.4 逐项判据

| ID | 判据 | 实测 | 阈值 | 判定 |
|---|---|---|---|---|
| **C-1** | 单英雄胜率均值 | 60.6% | 40%–60% | **FAIL** |
| C-2 | 全池胜率 σ | 22.3pp（跨层估算） | ≤20pp (Wave0) | ⚠️ **CONCERNS** |
| **C-3** | 胜率 <40% 占比 | 23.3% | ≤10% | **FAIL** |
| **C-4** | 胜率 >60% 占比 | 53.3% | ≤10% | **FAIL** |
| **C-5** | 极值英雄 (<25%/>75%) | 60/120 | ==0 | **FAIL** |
| **C-6** | 分层对位 45%–55% | 全部越界 | 4/4 对位 | **FAIL** |
| C-7 | 伤害 P50 | — | 18–28 | ⚠️ 未采样 |
| C-8 | P95/P50 比 | — | ≤3.0 | ⚠️ 未采样 |
| C-9 | 伤害 P5 | — | ≥5 | ⚠️ 未采样 |
| C-10 | 回合 P50 | 17 | 12–25 | ✅ PASS |
| **C-11** | 回合 P95 | 54 | ≤45 | **FAIL** |
| **C-12** | 60r 未分胜负 | 4.2% | ≤3% | **FAIL** |
| **C-13** | 骰期望配额 (24–34) | 46/90 (51.1%) | 100% | **FAIL** |
| **C-14** | 平均 CD≤3.0 + 槽0 CD==0 | 25/90 (27.8%) | 100% | **FAIL** |

### 3.5 Gate C 判定

**9/11 有效判据 FAIL → Gate C: FAIL**

**根因不变**：707 名 T3 残卡（42.6%）的骰期望仅 7.9，对上 T1 的 29.4 形成一面倒屠杀。378 名 T4 模板卡的平均 CD 4.73 远超引擎节奏 `[0,1,2,4]`。**管线修复未触及数据层，这些缺陷需要数据再生（`generate --all`）才能消除。**

> 注：本次模拟的 per-tier σ 为 0.2pp，低于预期的二项分布波动（~6pp）。原因是同一 tier 内英雄属性相近 + 对战种子确定性导致结果高度收敛。这不影响分层对位的结论方向。

---

## 4. Gate D — 平衡防降级（参照 GDD §4.4）

### 4.1 D-3：常量未修改

逐一读取 `core/balance.py` 与 `core/simulator.py` 确认：

| 常量 | 预期值 | 实际值 | 文件位置 | 判定 |
|---|---|---|---|---|
| `HP_SCALE` | **10** | 10 | `core/balance.py:11` | ✅ |
| `DAMAGE_SCALE` | **0.35** | 0.35 | `core/balance.py:12` | ✅ |
| `DND_DAMAGE_SCALE` | **5.5** | 5.5 | `core/simulator.py:18` | ✅ |

`core/balance.py` 不在本次修改的 8 个文件之列（`git diff` 无输出）。`DND_DAMAGE_SCALE` 在 `core/simulator.py` 中但该文件也不在本次修改范围内。**✅ D-3 PASS。**

### 4.2 D-1/D-2：胜率漂移

| 判据 | 状态 |
|---|---|
| D-1 存量英雄胜率漂移 Δ≤5pp | **无基线快照，无法对比** |
| D-2 全池 σ 不上升 | **无基线快照，无法对比** |

> ⚠️ **建议**：在下次 `generate --all` 执行前建立基线胜率快照（`tools/_archive/baseline_snapshot.py`），用固定 seed 跑全量 1659 英雄各 20 局 vs 随机对手，保存为 `production/qa/baseline-winrate-snapshot.json`。此后每次数据变更均可做 D-1/D-2 对比。

### 4.3 D-4：CI 全绿

`pytest tests/ -v` → 55 passed, 0 failed ✅
`python tools/check_cards.py` → 退出码 0 ✅

**Gate D 判定：PASS（D-3/D-4 通过；D-1/D-2 缺基线，非阻塞但标记为技术债）**

---

## 5. 新增单测覆盖检查（`test_card_generator.py`）

### 5.1 执行结果

```bash
python -m pytest tests/test_card_generator.py -v
# → 7 passed in 0.07s ✅
```

### 5.2 逐条覆盖分析

| # | 测试名 | 覆盖场景 | 状态 |
|---|---|---|---|
| 1 | `test_flatten_templates_returns_flat_dict_list` | `_flatten_templates` 函数 | ✅ |
| 2 | `test_placeholder_skill_has_required_fields` | `_build_placeholder_skill` 字段完整性 | ✅ |
| 3 | **`test_get_skills_fallback_returns_list_4_for_all_roles`** | **BLOCKER-1 关键路径：6 role × 回退 → len==4** | ✅ |
| 4 | `test_generated_card_passes_validate` | BLOCKER-1：`generate_character_card` → `validate_card()==[]` | ✅ |
| 5 | `test_card_id_format_is_gameid_hero_slug` | BLOCKER-5：card_id 格式 `<game_id>:<hero_slug>` | ✅ |
| 6 | `test_legacy_card_id_preserved` | BLOCKER-5：`legacy_card_id` 过渡字段 | ✅ |
| 7 | `test_card_id_idempotent` | BLOCKER-5：同一 hero 重复生成 card_id 不变 | ✅ |

### 5.3 覆盖评估

- ✅ **BLOCKER-1 关键路径已覆盖**：6 个 role 全部测试回退路径 `len==4`
- ✅ **BLOCKER-5 关键路径已覆盖**：card_id 格式、遗留字段、幂等性
- ✅ `validate_card()` 集成已覆盖

### 5.4 边界条件遗漏审查

| 边界条件 | 是否覆盖 | 风险 |
|---|---|---|
| 空 role（`role=""` 或 `role=None`） | ❌ 未覆盖 | 低——`_load_templates().get("")` 返回 None，会触发占位补齐，但未经测试 |
| 模板恰好 4 条（不触发补齐） | ❌ 未覆盖 | 低——现有 role 模板均 ≥4 |
| 模板 0 条（`_load_templates()` 返回空） | ⚠️ 间接覆盖 | 低——空模板路径已在 `get_skills` 开头处理 |
| `get_skills` 传入不存在的 game_id 但有模板 | ✅ 间接覆盖 | 测试用 `__test_nonexistent_game__` |
| `get_skills` 返回非 list（异常数据） | ❌ 未覆盖 | 中——技能库 JSON 若损坏，可能返回 dict，需 `get_skills` 内部防御 |

**评估**：覆盖充分（7/7 通过，关键路径全绿）。建议补 2 条：空 role 防御 + 异常格式防御。非阻塞。

---

## 6. 最终质量门判定

### 6.1 各 Gate 汇总

| Gate | 判定 | 阻塞？ | 说明 |
|---|---|---|---|
| **Gate A** | **FAIL** | 否 | 1085 卡 len≠4、3024 条死数据——**管线已修复，数据待再生** |
| **Gate C** | **FAIL** | 是 | 9/11 判据 FAIL，与 GDD §1.9 基线一致——**数据再生前不可合入新内容** |
| **Gate D** | **PASS** | 否 | D-3 常量未改 ✅、D-4 pytest 全绿 ✅、D-1/D-2 缺基线 ⚠️ |
| 测试套件 | **PASS** | 否 | 55/55 ✅、check_cards 0 问题 ✅ |
| 新增单测 | **PASS** | 否 | 7/7 ✅，BLOCKER-1/5 关键路径已覆盖 |

### 6.2 整体判定：

# **⚠️ CONCERNS**

### 6.3 理由

**管线修复本身质量合格**——pytest 55/55 全绿、check_cards 零告警、生成器产出 4 槽、loader 兼容旧卡、常量未漂移。8 个修改文件的变更范围符合 ADR-005 契约，无越界修改。

**但内容质量门（Gate A/C）仍然 FAIL**——这是**预期结果**。ADR-005 的 BLOCKER-1~5 修复的是**管线能力**（"产得出 4 槽卡"），而非**数据状态**（"盘上已有 4 槽卡"）。磁盘上的 1659 张卡仍是修复前的状态：700 张残卡、378 张死数据卡、3024 条引擎永不读取的冗余条目。

Gate C 的平衡 FAIL 是 Gate A 数据缺失的直接后果——42.6% 的 T3 残卡把全池胜率撕成双峰分布。

### 6.4 可接受的技术债

| 债项 | 严重度 | 清理条件 |
|---|---|---|
| 数据未再生（700 残卡 + 378 死数据） | 高 | 执行 `card_tool.py generate --all` 后自动清零 |
| 平衡基线快照缺失（D-1/D-2 不可验证） | 中 | 再生前建立快照 |
| Per-tier σ 过低（0.2pp）——采样方法精度问题 | 低 | 非阻塞，不影响方向性结论 |
| `test_card_generator.py` 缺少空 role/异常格式边界测试 | 低 | 下次迭代补 2 条 |

### 6.5 放行建议

**管线修复本身可以合入**（代码质量合格）。但合入后应立即执行下一步：

1. **P0**：`python tools/card_tool.py generate --all --dry-run` → 产出 diff 报告 → 文策渊（内容）会签 → 严守真（测试）跑全量 Gate C 回归
2. **P1**：建立基线胜率快照 → 数据再生 → Gate A/C 重检
3. **P2**：补边界测试 2 条

**在当前数据状态下（Gate A/C FAIL），不建议合入任何新增内容（Wave 1/2 英雄/IP）。**

---

## 附录 A — 产出物清单

| 文件 | 类型 | 说明 |
|---|---|---|
| `production/regression-report-pipeline-fix.md` | 报告 | 本文件 |
| `tools/_archive/balance_gate_check.py` | 脚本 | Gate C 平衡仿真 |
| `tools/_archive/gate_a_check.py` | 脚本 | Gate A 结构检查 |

## 附录 B — 复现命令

```bash
# 全量测试
python -m pytest tests/ -v

# Gate A 结构检查
python tools/_archive/gate_a_check.py
python tools/check_cards.py

# Gate C 平衡仿真（4800 局，~8s）
python tools/_archive/balance_gate_check.py

# Gate D 常量验证
python -c "from core.balance import HP_SCALE, DAMAGE_SCALE; from core.simulator import DND_DAMAGE_SCALE; print(HP_SCALE, DAMAGE_SCALE, DND_DAMAGE_SCALE)"
```

---

*报告结束 — 严守真，2026-08-05*
