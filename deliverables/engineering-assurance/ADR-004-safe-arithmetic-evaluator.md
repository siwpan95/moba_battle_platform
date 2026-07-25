# ADR-004: 骰子/DC 公式求值改用 AST 安全求值器（消除 eval）

- **状态**：Accepted
- **日期**：2026-07-25
- **作者**：工程保障团队

## 背景

`core/mechanics.py` 的 `roll_dice_expr`（解析 `"1d8+WIS"`）与 `parse_dc`（解析 `"8+PROF+STR"`）
原先用 `eval()` 计算属性名替换后的算式字符串。虽有两层防护：

1. 上游 `re.fullmatch(r"[0-9+\-*/\s]+", s)` 白名单约束输入仅含数字与四则运算符
2. `try/except` 兜底异常

但 `eval` 仍是 OWASP Top 10 直接禁用 API，且：

- 正则白名单一旦写错（如漏转义、未来扩展允许括号），`eval` 立刻成为任意代码执行漏洞
- `eval` 有编译开销，热路径频繁调用影响性能
- 静态扫描工具（bandit / SemGrep）会持续告警，淹没真实问题

## 决策

改用基于 `ast` 模块的节点白名单求值器 `_safe_arith`：

```python
def _safe_arith(expr: str) -> int:
    tree = ast.parse(expr, mode="eval")
    # 仅允许 ast.Constant / ast.BinOp(+,-,*,/) / ast.UnaryOp(+,-)
    # 任何 Call / Attribute / Name / 复杂节点直接抛 ValueError
```

两处 `int(eval(s))` 替换为 `_safe_arith(s)`。

## 备选方案

- **A. `ast.literal_eval`**：拒绝——`literal_eval` 只支持字面量（数字/字符串/元组），
  **不支持运算符**（`1+2` 会抛异常），无法满足需求。
- **B. 自写 tokenizer + shunting-yard 求值器**：可行但过度工程——
  四则运算用 AST 遍历 20 行就能搞定，且 `ast.parse` 是标准库，经过充分验证。
- **C. 引入 `numexpr` / `simpleeval` 第三方库**：拒绝——本项目零运行时依赖是核心优势
  （见评估报告），不应为一个 20 行函数引入依赖。

## 后果

正向：
- 消除 `eval`，静态扫描告警清零，OWASP 合规。
- AST 节点白名单比正则白名单更鲁棒：即使上游正则放宽，`_safe_arith` 仍拒绝危险节点。
- 零新增依赖，零回归（17 个 mechanics/engine 测试全通过）。

需警惕：
- `_safe_arith` 的节点白名单需与未来算式语法同步——若需支持 `()` 括号或 `**` 幂运算，
  需在 `_SAFE_BIN_OPS` 补 `ast.Pow`，并在 `ast.parse` 后允许 `ast.BinOp` 嵌套（已天然支持）。
- 当前仅返回 `int`（`int(_ev(tree))` 截断小数）；若未来 DC/骰子需浮点，调整返回类型。
