"""一次性脚本：对缺失英雄做 role 分类 + 选第 1 批"""
import json, os
from collections import Counter

cards_dir = 'data/character_cards/league_of_legends/'
d = json.load(open('data/skills/league_of_legends.json','r',encoding='utf-8'))
existing = set(d.keys())
nickname_map = {
    '德莱厄斯':'诺手','艾瑞莉娅':'刀妹','雷克顿':'鳄鱼',
    '奥莉安娜':'发条','墨菲特':'石头人','阿利斯塔':'牛头',
    '菲奥娜':'剑姬','嘉文四世':'皇子','奈德丽':'豹女',
    '伊莉丝':'蜘蛛','拉莫斯':'龙龟'
}

role_map = {
    '亚托克斯':'fighter','奥拉夫':'fighter','孙悟空':'fighter','贾克斯':'fighter',
    '泰达米尔':'fighter','莫德凯撒':'fighter','蔚':'fighter','沃里克':'fighter',
    '希瓦娜':'fighter','约里克':'fighter','特朗德尔':'fighter','普朗克':'fighter',
    '赫卡里姆':'fighter','雷克塞':'fighter','乌迪尔':'fighter','克烈':'fighter',
    '卑尔维斯':'fighter','格温':'fighter','贝蕾亚':'fighter','安蓓萨':'fighter',
    '尼菈':'fighter','兰博':'fighter','凯尔':'fighter','黛安娜':'fighter',
    '卡特琳娜':'assassin','泰隆':'assassin','乐芙兰':'assassin','雷恩加尔':'assassin',
    '伊芙琳':'assassin','萨科':'assassin','奇亚娜':'assassin','菲兹':'assassin',
    '卡萨丁':'assassin','派克':'assassin','魔腾':'assassin','纳亚菲利':'assassin',
    '阿克尚':'assassin','易':'assassin','奎因':'assassin',
    '瑞兹':'mage','弗拉基米尔':'mage','卡西奥佩娅':'mage','布兰德':'mage',
    '卡尔萨斯':'mage','维克托':'mage','玛尔扎哈':'mage','泽拉斯':'mage',
    '维迦':'mage','维克兹':'mage','妮蔻':'mage','斯维因':'mage',
    '费德提克':'mage','奥瑞利安·索尔':'mage','黑默丁格':'mage','艾尼维亚':'mage',
    '塔莉垭':'mage','婕拉':'mage','基兰':'mage','莫甘娜':'mage',
    '卡尔玛':'mage','薇古丝':'mage','奥萝拉':'mage','慧':'mage',
    '梅尔':'mage','莉莉娅':'mage','萨勒芬妮':'mage','凯南':'mage',
    '德莱文':'marksman','厄运小姐':'marksman','烬':'marksman','崔丝塔娜':'marksman',
    '希维尔':'marksman','图奇':'marksman','卡莉丝塔':'marksman','厄斐琉斯':'marksman',
    '克格莫':'marksman','泽丽':'marksman','莎弥拉':'marksman','霞':'marksman',
    '韦鲁斯':'marksman','赛娜':'marksman','斯莫德':'marksman','格雷福斯':'marksman',
    '库奇':'marksman','崔斯特':'marksman','阿兹尔':'marksman',
    '蕾欧娜':'tank','布隆':'tank','诺提勒斯':'tank','瑟庄妮':'tank',
    '扎克':'tank','茂凯':'tank','赛恩':'tank','科加斯':'tank',
    '蒙多医生':'tank','俄洛伊':'tank','厄加特':'tank','布里茨':'tank',
    '古拉加斯':'tank','芮尔':'tank','努努和威朗普':'tank','斯卡纳':'tank',
    '沃利贝尔':'tank','辛吉德':'tank','塔里克':'tank','奎桑提':'tank',
    '索拉卡':'support','娑娜':'support','娜美':'support','璐璐':'support',
    '悠米':'support','洛':'support','迦娜':'support','烈娜塔':'support',
    '艾翁':'support','米利欧':'support','尤娜拉':'support','扎亨':'support',
}

missing = []
for f in sorted(os.listdir(cards_dir)):
    if not f.endswith('.json'): continue
    name = f.replace('.json','')
    if name in existing or name in nickname_map:
        continue
    if name not in role_map:
        print(f'UNMAPPED: {name}')
        continue
    role = role_map[name]
    en = ''
    with open(os.path.join(cards_dir, f),'r',encoding='utf-8') as fh:
        card = json.load(fh)
        en = card.get('hero',{}).get('name_en','')
    missing.append((name, en, role))

print(f'Total missing: {len(missing)}')
print(f'Role counts: {Counter(r for _,_,r in missing)}')
print()

# Batch 1: top ~25 icons + role diversity
batch1 = [
    # Fighter (most covered role in existing 55 - highest ROI)
    ('亚托克斯','fighter'), ('贾克斯','fighter'), ('泰达米尔','fighter'),
    ('莫德凯撒','fighter'), ('奥拉夫','fighter'), ('蔚','fighter'),
    # Assassin (strong existing coverage with 劫/阿卡丽/卡兹克)
    ('卡特琳娜','assassin'), ('泰隆','assassin'), ('乐芙兰','assassin'),
    ('雷恩加尔','assassin'), ('伊芙琳','assassin'), ('菲兹','assassin'),
    # Mage (strong existing coverage with 阿狸/辛德拉/丽桑卓)
    ('瑞兹','mage'), ('弗拉基米尔','mage'), ('卡西奥佩娅','mage'),
    ('布兰德','mage'), ('维克托','mage'), ('卡尔萨斯','mage'),
    # Marksman (good existing: 凯特琳/金克丝/薇恩)
    ('德莱文','marksman'), ('烬','marksman'), ('厄运小姐','marksman'),
    # Support (least covered - boost now)
    ('索拉卡','support'), ('娑娜','support'), ('娜美','support'),
    # Tank (existing: 锤石/石头人/阿木木/牛头)
    ('蕾欧娜','tank'), ('布隆','tank'),
]

print(f'=== BATCH 1 ({len(batch1)} heroes) ===')
for i, (name, role) in enumerate(batch1):
    print(f'  {i+1}. {name} [{role}]')
