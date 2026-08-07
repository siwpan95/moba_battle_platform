# card_id 迁移 dry-run 报告

**日期**: 2026-08-05
**总卡数**: 1659
**card_id 将变更**: 1659 (100%)
**card_id 不变**: 0
**新 card_id 唯一性**: PASS (目录+文件名天然唯一)

## 旧 card_id 前缀碰撞现状

- `HER`: 202 cards across 2 games: ['heroes_of_the_storm', 'yinghunzhiren']
- `MAR`: 87 cards across 2 games: ['marvel_super_war', 'mcu']

## 变更样本（前15条）

- `300-1080` → `300_heroes:002`
  - 文件: G:\moba_battle_platform\data\character_cards\300_heroes\002.json
- `300-1027` → `300_heroes:Archer`
  - 文件: G:\moba_battle_platform\data\character_cards\300_heroes\Archer.json
- `300-1054` → `300_heroes:C.C.`
  - 文件: G:\moba_battle_platform\data\character_cards\300_heroes\C.C..json
- `300-1130` → `300_heroes:DIO`
  - 文件: G:\moba_battle_platform\data\character_cards\300_heroes\DIO.json
- `300-1026` → `300_heroes:Saber`
  - 文件: G:\moba_battle_platform\data\character_cards\300_heroes\Saber.json
- `300-1045` → `300_heroes:一方通行`
  - 文件: G:\moba_battle_platform\data\character_cards\300_heroes\一方通行.json
- `300-1023` → `300_heroes:三笠`
  - 文件: G:\moba_battle_platform\data\character_cards\300_heroes\三笠.json
- `300-1136` → `300_heroes:东方仗助`
  - 文件: G:\moba_battle_platform\data\character_cards\300_heroes\东方仗助.json
- `300-1009` → `300_heroes:东风谷早苗`
  - 文件: G:\moba_battle_platform\data\character_cards\300_heroes\东风谷早苗.json
- `300-1033` → `300_heroes:两仪式`
  - 文件: G:\moba_battle_platform\data\character_cards\300_heroes\两仪式.json
- `300-1115` → `300_heroes:中野梓`
  - 文件: G:\moba_battle_platform\data\character_cards\300_heroes\中野梓.json
- `300-1132` → `300_heroes:乔鲁诺·乔巴纳`
  - 文件: G:\moba_battle_platform\data\character_cards\300_heroes\乔鲁诺·乔巴纳.json
- `300-1037` → `300_heroes:五更琉璃`
  - 文件: G:\moba_battle_platform\data\character_cards\300_heroes\五更琉璃.json
- `300-1090` → `300_heroes:五条悟`
  - 文件: G:\moba_battle_platform\data\character_cards\300_heroes\五条悟.json
- `300-1041` → `300_heroes:五河琴里`
  - 文件: G:\moba_battle_platform\data\character_cards\300_heroes\五河琴里.json
- ... 共 1659 条变更

## 新 card_id 格式示例（每游戏1条）

- `300_heroes`: `300_heroes:002`
- `arena_of_valor`: `arena_of_valor:Airi`
- `dc`: `dc:丧钟`
- `demon_slayer`: `demon_slayer:伊黑小芭内`
- `dota2`: `dota2:上古巨神`
- `feiren_xueyuan`: `feiren_xueyuan:九头虫`
- `genshin`: `genshin:七七`
- `harry_potter`: `harry_potter:伏地魔`
- `heroes_of_the_storm`: `heroes_of_the_storm:Abathur`
- `hong_kong_comics`: `hong_kong_comics:华英雄`
- `honor_of_kings`: `honor_of_kings:上官婉儿`
- `league_of_legends`: `league_of_legends:丽桑卓`
- `marvel_super_war`: `marvel_super_war:万磁王`
- `mcu`: `mcu:冬兵`
- `mobile_legends_bang_bang`: `mobile_legends_bang_bang:Aamon`
- `one_piece`: `one_piece:乌索普`
- `onmyoji_arena`: `onmyoji_arena:一反木绵`
- `overwatch2`: `overwatch2:D.Va`
- `pokemon_unite`: `pokemon_unite:仙子伊布`
- `shuguang_heroes`: `shuguang_heroes:乌雅`
- `smite`: `smite:Achilles`
- `three_body`: `three_body:丁仪`
- `vainglory`: `vainglory:Adagio`
- `yinghunzhiren`: `yinghunzhiren:丛林之子`

## 迁移方案

- **新格式**: `<game_id>:<hero_slug>`（与物理路径同构）
- **旧 card_id**: 保留为 `legacy_card_id` 字段一个版本周期
- **迁移脚本**: `tools/_archive/migrate_card_ids.py`（一次性执行）
- **幂等性**: 新 ID 由目录+文件名派生，局部生成 `--game <IP>` 不再重写既有 ID