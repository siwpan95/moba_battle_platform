# battle_platform —— 对战平台技能流工作流包

部署位置：`<仓库根>/battle_platform/`

本包是对战平台「技能流」的**可独立运行入口/子包**。它不重写战斗引擎，而是衔接
父目录（仓库根）已有的引擎（`core/` `data/` `tools/`），把技能工作流
封装成可调用、可命令化的模块。

> ⚠️ 格式约定：技能文档中「单文件 `data/skills/<game_id>.json` = {英雄:技能}」的写法已过期。
> 真实项目为**每英雄一个文件**：`data/skills/<game_id>/<英雄>.json`（4 个技能 dict 的 list）。
> 本包全部按真实格式实现。

## 目录结构

```
battle_platform/
├── __init__.py          # 包标识 + 触发 paths 引导
├── paths.py             # PROJECT_ROOT/sys.path 引导 + 路径助手
├── engine.py            # 引擎外观层（core.loader/registry/mechanics）
├── cli.py               # argparse 命令行入口
├── __main__.py          # python -m battle_platform 支持
├── workflows/
│   ├── add_ip.py        # 工作流一：新增 IP（注册 + 建目录 + 空 source）
│   ├── p0a_rename.py    # 工作流二：P0-A 模板技能名检测 / 改名
│   ├── p0b_effects.py   # 工作流三：P0-B effects 关键词补全
│   ├── p1_expand.py     # 工作流四：P1 英雄池扩充（追加英雄）
│   └── verify.py        # 验证管道（check_cards / pytest / smoke）
└── README.md
```

## 命令行用法

```bash
# 工作流一：新增 IP
python -m battle_platform add-ip --game foo_myth --display "Foo Myth" --cn "福神话"

# 工作流二：P0-A 模板名检测 / 改名
python -m battle_platform p0a detect --game arabian_nights
python -m battle_platform p0a apply --game arabian_nights --map '{"战士·旋风斩":"真旋风斩"}'

# 工作流三：P0-B 缺 effects 统计 / 补全
python -m battle_platform p0b missing --game arabian_nights
python -m battle_platform p0b complete --game arabian_nights --dry-run
python -m battle_platform p0b complete --game arabian_nights

# 工作流四：P1 英雄池扩充
python -m battle_platform p1 expand --game foo_myth --json heroes.json

# 验证管道
python -m battle_platform verify --pytest --smoke
```

## Python 内调用

```python
from battle_platform.workflows import add_ip, p0a_rename, p0b_effects, p1_expand, verify

add_ip.add_ip("foo_myth", "Foo Myth", "福神话")
p0a_rename.detect_template_skills("arabian_nights")
p0b_effects.complete_effects("arabian_nights", dry_run=True)
p1_expand.add_heroes("foo_myth", [{"name": "英雄A", "skills": [<4 dict>]}])
rep = verify.verify(run_pytest=False, smoke=True)
```

## 硬约束（与引擎一致）

- CD = `[0,1,2,4]`（Q/W/E/R）
- 骰期望入 GDD §3.2 配额带（tank 24-27 / fighter 27-30 / assassin 32-34 /
  mage 30-33 / marksman 29-32 / support 24-27）
- `effects[].type` 必须命中 `core/mechanics.py` 别名表（中文受控词）
- 描述 D&D 风味；商业 IP 禁止逐字复制 wiki
- 验证必须在每批入库后立即跑，不积累
