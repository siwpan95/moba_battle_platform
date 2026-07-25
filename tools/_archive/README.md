# tools/_archive

一次性临时脚本归档。这些脚本在数据治理阶段用于排查特定问题（如英文名残留、
遗漏英雄），功能已被 `tools/card_tool.py` 的 `status` / `search` / `validate`
命令覆盖，保留仅供历史追溯，不再维护。

| 脚本 | 原用途 |
|------|--------|
| `_check_missing.py` | 查找 13 个指定英文名英雄所在文件并打印 name/game |
| `_check_names.py` | 统计仍为 ASCII 英文名的角色卡 |
| `_final_check.py` | 最终校验英文名残留（与 _check_names 重复） |

如需类似排查，请用：
```bash
python tools/card_tool.py status     # 查看角色卡状态
python tools/card_tool.py search 亚索  # 搜索英雄
python tools/card_tool.py validate   # 校验合法性
```
