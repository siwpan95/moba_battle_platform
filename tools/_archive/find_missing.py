import json
import os
import sys

# 2026-09-23 去本地化：技能数据路径改为仓内推导（原路径已不存在，仓已迁移至 原路径）
# 解析优先级：环境变量 MOBA_BATTLE_PLATFORM_ROOT → 仓根推导（tools/_archive/ 上溯 2 层，复用 core.paths 单一真相）→ fail-loud 点名该设哪个变量
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from core.paths import PROJECT_ROOT  # noqa: E402  仓内路径单一真相（ADR-002），本身由 __file__ 推导

_SKILLS_JSON = os.path.join(
    os.environ.get("MOBA_BATTLE_PLATFORM_ROOT") or PROJECT_ROOT,
    "data", "skills", "league_of_legends.json",
)
if not os.path.exists(_SKILLS_JSON):
    raise SystemExit(
        "[find_missing] 找不到技能数据文件：%s\n"
        "  注：本仓技能数据现为「每英雄一文件」格式 <仓库根>/data/skills/league_of_legends/<英雄>.json，\n"
        "  本脚本依赖的旧「单文件 {英雄: 技能}」JSON 已不在仓内。\n"
        "  如该单文件数据位于他处，请设置环境变量 MOBA_BATTLE_PLATFORM_ROOT 指向本仓根目录后重试。" % _SKILLS_JSON
    )

all_champs = {
    '阿卡丽': 'assassin', '艾克': 'assassin', '伊芙琳': 'assassin', '菲兹': 'assassin',
    '卡萨丁': 'assassin', '卡特琳娜': 'assassin', '卡兹克': 'assassin', '乐芙兰': 'assassin',
    '易大师': 'assassin', '娜菲芮': 'assassin', '奈德丽': 'assassin', '奇亚娜': 'assassin',
    '雷恩加尔': 'assassin', '萨科': 'assassin', '泰隆': 'assassin', '劫': 'assassin',
    
    '亚托克斯': 'fighter', '安蓓萨': 'fighter', '卑尔维斯': 'fighter', '布蕾尔': 'fighter',
    '卡蜜尔': 'fighter', '德莱厄斯': 'fighter', '黛安娜': 'fighter', '菲奥娜': 'fighter',
    '普朗克': 'fighter', '盖伦': 'fighter', '纳尔': 'fighter', '古拉加斯': 'fighter',
    '格温': 'fighter', '赫卡里姆': 'fighter', '俄洛伊': 'fighter', '艾瑞莉娅': 'fighter',
    '嘉文四世': 'fighter', '贾克斯': 'fighter', '杰斯': 'fighter', '凯尔': 'fighter',
    '凯隐': 'fighter', '克烈': 'fighter', '李青': 'fighter', '莉莉娅': 'fighter',
    '莫德凯撒': 'fighter', '内瑟斯': 'fighter', '魔腾': 'fighter', '奥拉夫': 'fighter',
    '潘森': 'fighter', '雷克塞': 'fighter', '雷克顿': 'fighter', '锐雯': 'fighter',
    '兰博': 'fighter', '瑟提': 'fighter', '希瓦娜': 'fighter', '特朗德尔': 'fighter',
    '泰达米尔': 'fighter', '乌迪尔': 'fighter', '厄加特': 'fighter', '蔚': 'fighter',
    '佛耶戈': 'fighter', '沃利贝尔': 'fighter', '沃里克': 'fighter', '孙悟空': 'fighter',
    '赵信': 'fighter', '亚索': 'fighter', '永恩': 'fighter', '约里克': 'fighter',
    
    '阿狸': 'mage', '艾尼维亚': 'mage', '安妮': 'mage', '奥瑞利安索尔': 'mage',
    '奥罗拉': 'mage', '阿兹尔': 'mage', '布兰德': 'mage', '卡西奥佩娅': 'mage',
    '伊莉丝': 'mage', '费德提克': 'mage', '黑默丁格': 'mage', '彗': 'mage',
    '卡尔玛': 'mage', '卡尔萨斯': 'mage', '凯南': 'mage', '丽桑卓': 'mage',
    '拉克丝': 'mage', '玛尔扎哈': 'mage', '莫甘娜': 'mage', '妮蔻': 'mage',
    '奥莉安娜': 'mage', '瑞兹': 'mage', '萨勒芬妮': 'mage', '斯维因': 'mage',
    '塞拉斯': 'mage', '辛德拉': 'mage', '塔莉垭': 'mage', '崔斯特': 'mage',
    '维迦': 'mage', '维克兹': 'mage', '薇古丝': 'mage', '维克托': 'mage',
    '弗拉基米尔': 'mage', '泽拉斯': 'mage', '吉格斯': 'mage', '佐伊': 'mage', '婕拉': 'mage',
    
    '阿克尚': 'marksman', '厄斐琉斯': 'marksman', '艾希': 'marksman', '凯特琳': 'marksman',
    '库奇': 'marksman', '德莱文': 'marksman', '伊泽瑞尔': 'marksman', '格雷福斯': 'marksman',
    '烬': 'marksman', '金克丝': 'marksman', '卡莎': 'marksman', '卡莉丝塔': 'marksman',
    '千珏': 'marksman', '克格莫': 'marksman', '卢锡安': 'marksman', '厄运小姐': 'marksman',
    '尼菈': 'marksman', '奎因': 'marksman', '莎弥拉': 'marksman', '赛娜': 'marksman',
    '希维尔': 'marksman', '斯莫德': 'marksman', '提莫': 'marksman', '崔丝塔娜': 'marksman',
    '图奇': 'marksman', '韦鲁斯': 'marksman', '薇恩': 'marksman', '霞': 'marksman', '泽丽': 'marksman',
    
    '巴德': 'support', '布隆': 'support', '艾翁': 'support', '迦娜': 'support',
    '璐璐': 'support', '米利欧': 'support', '娜美': 'support', '派克': 'support',
    '洛': 'support', '烈娜塔': 'support', '娑娜': 'support', '索拉卡': 'support',
    '塔姆': 'support', '塔里克': 'support', '锤石': 'support', '悠米': 'support', '基兰': 'support',
    
    '阿利斯塔': 'tank', '阿木木': 'tank', '布里茨': 'tank', '科加斯': 'tank',
    '蒙多医生': 'tank', '加里奥': 'tank', '奎桑提': 'tank', '蕾欧娜': 'tank',
    '墨菲特': 'tank', '茂凯': 'tank', '诺提勒斯': 'tank', '努努': 'tank',
    '奥恩': 'tank', '波比': 'tank', '拉莫斯': 'tank', '芮尔': 'tank',
    '瑟庄妮': 'tank', '慎': 'tank', '辛吉德': 'tank', '赛恩': 'tank',
    '斯卡纳': 'tank', '扎克': 'tank',
}

with open(_SKILLS_JSON, 'r', encoding='utf-8') as f:
    existing = json.load(f)
existing_names = [k for k in existing if not k.startswith('_')]

alias_map = {
    '刀妹': '艾瑞莉娅', '剑姬': '菲奥娜', '诺手': '德莱厄斯', '盲僧': '李青',
    '蜘蛛': '伊莉丝', '豹女': '奈德丽', '发条': '奥莉安娜', '牛头': '阿利斯塔',
    '石头人': '墨菲特', '龙龟': '拉莫斯', '鳄鱼': '雷克顿',
}

canonical_existing = set()
for name in existing_names:
    canonical_existing.add(alias_map.get(name, name))

missing = []
for name, role in all_champs.items():
    if name not in canonical_existing:
        missing.append((name, role))

print(f"Total champions: {len(all_champs)}")
print(f"Existing (canonical): {len(canonical_existing)}")
print(f"Missing: {len(missing)}")
print()

for r in ['assassin', 'fighter', 'mage', 'marksman', 'support', 'tank']:
    champs = [(n, ro) for n, ro in missing if ro == r]
    print(f"=== {r} ({len(champs)}) ===")
    for n, _ in champs:
        print(f"  {n}")
