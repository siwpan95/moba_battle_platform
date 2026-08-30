# Changelog

本项目所有值得注意的变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added

- UI 新增「🔑 密钥」设置弹窗：可在界面内输入 DeepSeek API Key（掩码显示、可切换明文）与模型名，保存到本地 `私人令牌.txt`（已 .gitignore，不入库不上传）；未配置 key 时点「日志润色」自动弹出引导（2026-08-29）。
- tools/log_polish.py 新增 `save_token_file()`：写入/更新凭据时保留无关行（如 gitee 令牌），仅在存在旧 key 时才移除旧 key/model 行；配套单测 tests/test_log_polish_credentials.py。

### Security

- 移除 tools/log_polish.py 中硬编码的 DeepSeek API Key（改为环境变量 DEEPSEEK_API_KEY 注入）。原密钥已公开泄露，请立即在 DeepSeek 平台轮换（2026-08-27 深度审核 R0）。

### Changed

- R2 规则内核接入（2026-08-27）：core/mechanics.py 的 roll_dice/d20 豁免改 alloy.trpg.dice（D&D 5e 同构原语，rng 注入语义不变；表达式 DSL 与数据骰缩放保留仓内）；恢复被局部回退的 R0 安全修复（环境变量注入 + .gitignore 凭据段 + LICENSE）。

## [1.0.0] - 2026-08-27

### Added

- 首个发行版：Windows 可执行程序（PyInstaller，Python 3.14）。
- 发布面：gitee [siwpan/moba_battle_platform](https://gitee.com/siwpan/moba_battle_platform) release `v1.0.0`（MOBA 英雄大乱斗 v1.0.0）。