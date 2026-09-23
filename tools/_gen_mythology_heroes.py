#!/usr/bin/env python3
"""Add 55 mythology heroes to all_heroes_unified.json."""
# 2026-09-28 去本地化：数据路径改为仓内推导（原 G:/moba_battle_platform/data/analysis/all_heroes_unified.json 已不存在，仓已迁移至 G:\repos\moba_battle_platform）
# 解析优先级：环境变量 MOBA_BATTLE_PLATFORM_ROOT → 仓根推导（tools/ 上溯 1 层，复用 core.paths 单一真相）→ fail-loud 点名该设哪个变量
import json
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from core.paths import PROJECT_ROOT  # noqa: E402  仓内路径单一真相（ADR-002），本身由 __file__ 推导

path = os.path.join(
    os.environ.get("MOBA_BATTLE_PLATFORM_ROOT") or PROJECT_ROOT,
    "data", "analysis", "all_heroes_unified.json",
)
if not os.path.exists(path):
    raise SystemExit(
        "[_gen_mythology_heroes] 找不到英雄池统一数据：%s\n"
        "  该文件应位于 <仓库根>/data/analysis/all_heroes_unified.json。\n"
        "  如仓库根不在推导位置，请设置环境变量 MOBA_BATTLE_PLATFORM_ROOT 指向本仓根目录后重试。" % path
    )

with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

norse = [
    ('奥丁','Odin','','法师','mage','北欧神话'),
    ('托尔','Thor','','战士','fighter','北欧神话'),
    ('洛基','Loki','','刺客','assassin','北欧神话'),
    ('芙蕾雅','Freya','','辅助','support','北欧神话'),
    ('海姆达尔','Heimdall','','坦克','tank','北欧神话'),
    ('弗雷','Freyr','','战士','fighter','北欧神话'),
    ('巴德尔','Baldr','','辅助','support','北欧神话'),
    ('提尔','Tyr','','战士','fighter','北欧神话'),
    ('赫尔','Hel','','辅助','support','北欧神话'),
    ('芬里尔','Fenrir','','刺客','assassin','北欧神话'),
    ('希芙','Sif','','辅助','support','北欧神话'),
    ('布伦希尔德','Brynhildr','','战士','fighter','北欧神话'),
    ('西格恩','Sigyn','','辅助','support','北欧神话'),
    ('苏尔特尔','Surtr','','战士','fighter','北欧神话'),
    ('尼德霍格','Nidhogg','','刺客','assassin','北欧神话'),
    ('密米尔','Mimir','','法师','mage','北欧神话'),
    ('弗丽嘉','Frigg','','辅助','support','北欧神话'),
    ('瓦尔基里','Valkyrie','','刺客','assassin','北欧神话'),
    ('斯库尔','Skoll','','射手','marksman','北欧神话'),
    ('哈提','Hati','','射手','marksman','北欧神话'),
]

greek = [
    ('宙斯','Zeus','','法师','mage','希腊神话'),
    ('波塞冬','Poseidon','','战士','fighter','希腊神话'),
    ('哈迪斯','Hades','','法师','mage','希腊神话'),
    ('雅典娜','Athena','','战士','fighter','希腊神话'),
    ('阿瑞斯','Ares','','战士','fighter','希腊神话'),
    ('阿波罗','Apollo','','射手','marksman','希腊神话'),
    ('阿尔忒弥斯','Artemis','','射手','marksman','希腊神话'),
    ('赫菲斯托斯','Hephaestus','','坦克','tank','希腊神话'),
    ('赫尔墨斯','Hermes','','刺客','assassin','希腊神话'),
    ('美杜莎','Medusa','','刺客','assassin','希腊神话'),
    ('珀尔修斯','Perseus','','战士','fighter','希腊神话'),
    ('赫拉克勒斯','Heracles','','战士','fighter','希腊神话'),
    ('阿喀琉斯','Achilles','','战士','fighter','希腊神话'),
    ('奥德修斯','Odysseus','','射手','marksman','希腊神话'),
    ('喀耳刻','Circe','','法师','mage','希腊神话'),
    ('潘多拉','Pandora','','辅助','support','希腊神话'),
    ('厄里斯','Eris','','刺客','assassin','希腊神话'),
    ('塔纳托斯','Thanatos','','刺客','assassin','希腊神话'),
    ('倪克斯','Nyx','','法师','mage','希腊神话'),
    ('赫斯提亚','Hestia','','辅助','support','希腊神话'),
]

cthulhu = [
    ('克苏鲁','Cthulhu','','坦克','tank','克苏鲁神话'),
    ('奈亚拉托提普','Nyarlathotep','','刺客','assassin','克苏鲁神话'),
    ('达贡','Dagon','','战士','fighter','克苏鲁神话'),
    ('深潜者','Deep One','','刺客','assassin','克苏鲁神话'),
    ('修格斯','Shoggoth','','坦克','tank','克苏鲁神话'),
    ('哈斯塔','Hastur','','法师','mage','克苏鲁神话'),
    ('莎布尼古拉斯','Shub-Niggurath','','法师','mage','克苏鲁神话'),
    ('兰道夫卡特','Randolph Carter','','法师','mage','克苏鲁神话'),
    ('埃里奇赞','Erich Zann','','射手','marksman','克苏鲁神话'),
    ('犹格索托斯','Yog-Sothoth','','法师','mage','克苏鲁神话'),
    ('阿萨托斯','Azathoth','','法师','mage','克苏鲁神话'),
    ('诺登斯','Nodens','','辅助','support','克苏鲁神话'),
    ('蛇人','Serpent Man','','刺客','assassin','克苏鲁神话'),
    ('伊斯人','Yithian','','法师','mage','克苏鲁神话'),
    ('米戈','Mi-Go','','刺客','assassin','克苏鲁神话'),
]

for name, name_en, alias, native_role, role, source in norse:
    data['heroes'].append({
        'game': 'Norse Mythology',
        'name': name, 'name_en': name_en, 'alias': alias,
        'native_role': native_role, 'universal_role': role, 'source': source
    })

for name, name_en, alias, native_role, role, source in greek:
    data['heroes'].append({
        'game': 'Greek Mythology',
        'name': name, 'name_en': name_en, 'alias': alias,
        'native_role': native_role, 'universal_role': role, 'source': source
    })

for name, name_en, alias, native_role, role, source in cthulhu:
    data['heroes'].append({
        'game': 'Cthulhu Mythos',
        'name': name, 'name_en': name_en, 'alias': alias,
        'native_role': native_role, 'universal_role': role, 'source': source
    })

data['total_heroes'] = len(data['heroes'])
data['total_games'] = len(set(h['game'] for h in data['heroes']))

with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f'Total heroes: {data["total_heroes"]}, Total games: {data["total_games"]}')
for g in ['Norse Mythology','Greek Mythology','Cthulhu Mythos']:
    cnt = sum(1 for h in data['heroes'] if h['game']==g)
    print(f'{g}: {cnt} heroes')
