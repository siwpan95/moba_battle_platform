#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公版 IP 批量扩充生成器（2026-08-05）。

流程：
  1) 将 9 个公版 IP 的英雄名册追加到 data/analysis/all_heroes_unified.json（主名册）。
  2) 为每个 IP 生成 data/source/<id>/heroes.json（源树，保持一致）。
  3) 用 batch_gen_skills 的 role 模板生成 data/skills/<id>/<英雄>.json（血肉）。
  4) 用 generate_character_card 生成 data/character_cards/<id>/<英雄>.json（骨头，内嵌真实技能）。
  5) 契约校验（schema.validate_card）fail-fast，拒绝写盘。

汉化规则：名册中的 cn 名已按「官方译名→直译→保留英文」三档处理。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from core.registry import GAME_REGISTRY, ROLE_NAME_CN  # noqa: E402
from core.skill_pool import write_hero_skill, pool_has  # noqa: E402
from batch_gen_skills import gen_skills_for_hero  # noqa: E402
from card_generator import generate_character_card  # noqa: E402
from core import schema  # noqa: E402

# 稳定种子（避免 Python hash 随机化导致跨进程不一致）
def stable_seed(name: str) -> int:
    return sum(ord(c) for c in name) % 100000

# ==========================================================
# 公版 IP 名册（cn, en, alias, native_role_cn, role, source_cn）
# 英雄名已按汉化三档规则处理：官方译名优先，其次直译。
# ==========================================================
IPS = [
    {
        "id": "arthurian_legend", "display": "Arthurian Legend", "cn": "亚瑟王传说",
        "heroes": [
            ("亚瑟王", "Arthur", "", "战士", "fighter", "亚瑟王传说"),
            ("梅林", "Merlin", "", "法师", "mage", "亚瑟王传说"),
            ("桂妮维亚", "Guinevere", "", "辅助", "support", "亚瑟王传说"),
            ("兰斯洛特", "Lancelot", "", "战士", "fighter", "亚瑟王传说"),
            ("摩根勒菲", "Morgan le Fay", "", "法师", "mage", "亚瑟王传说"),
            ("高文", "Gawain", "", "战士", "fighter", "亚瑟王传说"),
            ("加拉哈德", "Galahad", "", "坦克", "tank", "亚瑟王传说"),
            ("珀西瓦尔", "Percival", "", "射手", "marksman", "亚瑟王传说"),
            ("莫德雷德", "Mordred", "", "刺客", "assassin", "亚瑟王传说"),
            ("崔斯坦", "Tristan", "", "射手", "marksman", "亚瑟王传说"),
            ("贝德维尔", "Bedivere", "", "战士", "fighter", "亚瑟王传说"),
            ("鲍斯", "Bors", "", "坦克", "tank", "亚瑟王传说"),
            ("加雷斯", "Gareth", "", "战士", "fighter", "亚瑟王传说"),
            ("凯", "Kay", "", "战士", "fighter", "亚瑟王传说"),
            ("尤瑟王", "Uther Pendragon", "", "战士", "fighter", "亚瑟王传说"),
            ("湖中女士", "Lady of the Lake", "", "辅助", "support", "亚瑟王传说"),
        ],
    },
    {
        "id": "egyptian_mythology", "display": "Egyptian Mythology", "cn": "埃及神话",
        "heroes": [
            ("拉", "Ra", "", "法师", "mage", "埃及神话"),
            ("奥西里斯", "Osiris", "", "坦克", "tank", "埃及神话"),
            ("伊西斯", "Isis", "", "辅助", "support", "埃及神话"),
            ("荷鲁斯", "Horus", "", "射手", "marksman", "埃及神话"),
            ("塞特", "Set", "", "刺客", "assassin", "埃及神话"),
            ("阿努比斯", "Anubis", "", "坦克", "tank", "埃及神话"),
            ("托特", "Thoth", "", "法师", "mage", "埃及神话"),
            ("哈托尔", "Hathor", "", "辅助", "support", "埃及神话"),
            ("普塔", "Ptah", "", "战士", "fighter", "埃及神话"),
            ("塞赫麦特", "Sekhmet", "", "战士", "fighter", "埃及神话"),
            ("巴斯特", "Bastet", "", "刺客", "assassin", "埃及神话"),
            ("奈芙蒂斯", "Nephthys", "", "辅助", "support", "埃及神话"),
            ("玛特", "Maat", "", "辅助", "support", "埃及神话"),
            ("舒", "Shu", "", "坦克", "tank", "埃及神话"),
            ("泰芙努特", "Tefnut", "", "法师", "mage", "埃及神话"),
            ("努特", "Nut", "", "法师", "mage", "埃及神话"),
            ("盖布", "Geb", "", "坦克", "tank", "埃及神话"),
            ("阿图姆", "Atum", "", "法师", "mage", "埃及神话"),
            ("孔苏", "Khonsu", "", "法师", "mage", "埃及神话"),
            ("索贝克", "Sobek", "", "战士", "fighter", "埃及神话"),
        ],
    },
    {
        "id": "hindu_mythology", "display": "Hindu Mythology", "cn": "印度神话",
        "heroes": [
            ("梵天", "Brahma", "", "法师", "mage", "印度神话"),
            ("毗湿奴", "Vishnu", "", "坦克", "tank", "印度神话"),
            ("湿婆", "Shiva", "", "刺客", "assassin", "印度神话"),
            ("萨拉斯瓦蒂", "Saraswati", "", "辅助", "support", "印度神话"),
            ("拉克希米", "Lakshmi", "", "辅助", "support", "印度神话"),
            ("帕尔瓦蒂", "Parvati", "", "辅助", "support", "印度神话"),
            ("杜尔迦", "Durga", "", "战士", "fighter", "印度神话"),
            ("迦利", "Kali", "", "刺客", "assassin", "印度神话"),
            ("罗摩", "Rama", "", "战士", "fighter", "印度神话"),
            ("克里希纳", "Krishna", "", "辅助", "support", "印度神话"),
            ("哈努曼", "Hanuman", "", "战士", "fighter", "印度神话"),
            ("伽内什", "Ganesha", "", "坦克", "tank", "印度神话"),
            ("卡尔提凯耶", "Kartikeya", "", "射手", "marksman", "印度神话"),
            ("苏利耶", "Surya", "", "法师", "mage", "印度神话"),
            ("因陀罗", "Indra", "", "法师", "mage", "印度神话"),
            ("阿耆尼", "Agni", "", "法师", "mage", "印度神话"),
            ("伐楼拿", "Varuna", "", "法师", "mage", "印度神话"),
            ("阎摩", "Yama", "", "坦克", "tank", "印度神话"),
            ("那罗辛哈", "Narasimha", "", "战士", "fighter", "印度神话"),
        ],
    },
    {
        "id": "chinese_mythology", "display": "Chinese Mythology", "cn": "中国神话",
        "heroes": [
            ("盘古", "Pangu", "", "战士", "fighter", "中国神话"),
            ("女娲", "Nüwa", "", "辅助", "support", "中国神话"),
            ("伏羲", "Fuxi", "", "法师", "mage", "中国神话"),
            ("神农", "Shennong", "", "辅助", "support", "中国神话"),
            ("黄帝", "Huangdi", "", "坦克", "tank", "中国神话"),
            ("祝融", "Zhurong", "", "战士", "fighter", "中国神话"),
            ("共工", "Gonggong", "", "坦克", "tank", "中国神话"),
            ("句芒", "Jumang", "", "辅助", "support", "中国神话"),
            ("蓐收", "Rushou", "", "战士", "fighter", "中国神话"),
            ("西王母", "Queen Mother of the West", "", "法师", "mage", "中国神话"),
            ("后土", "Hou Tu", "", "坦克", "tank", "中国神话"),
            ("羲和", "Xihe", "", "法师", "mage", "中国神话"),
            ("嫦娥", "Chang'e", "", "辅助", "support", "中国神话"),
            ("刑天", "Xingtian", "", "战士", "fighter", "中国神话"),
            ("蚩尤", "Chiyou", "", "战士", "fighter", "中国神话"),
            ("应龙", "Yinglong", "", "射手", "marksman", "中国神话"),
            ("雷公", "Leigong", "", "法师", "mage", "中国神话"),
            ("电母", "Dianmu", "", "法师", "mage", "中国神话"),
            ("二郎真君", "Erlang Shen", "", "战士", "fighter", "中国神话"),
            ("元始天尊", "Yuanshi Tianzun", "", "法师", "mage", "中国神话"),
            ("灵宝天尊", "Lingbao Tianzun", "", "法师", "mage", "中国神话"),
            ("道德天尊", "Daode Tianzun", "", "法师", "mage", "中国神话"),
        ],
    },
    {
        "id": "japanese_mythology", "display": "Japanese Mythology", "cn": "日本神话",
        "heroes": [
            ("天照大神", "Amaterasu", "", "法师", "mage", "日本神话"),
            ("月读", "Tsukuyomi", "", "法师", "mage", "日本神话"),
            ("素戋呜尊", "Susanoo", "", "战士", "fighter", "日本神话"),
            ("伊奘诺尊", "Izanagi", "", "坦克", "tank", "日本神话"),
            ("伊奘冉尊", "Izanami", "", "辅助", "support", "日本神话"),
            ("大国主", "Okuninushi", "", "坦克", "tank", "日本神话"),
            ("天宇受卖命", "Ame-no-Uzume", "", "辅助", "support", "日本神话"),
            ("风神", "Fujin", "", "法师", "mage", "日本神话"),
            ("雷神", "Raijin", "", "法师", "mage", "日本神话"),
            ("八幡神", "Hachiman", "", "战士", "fighter", "日本神话"),
            ("稻荷", "Inari", "", "辅助", "support", "日本神话"),
            ("龙神", "Ryujin", "", "坦克", "tank", "日本神话"),
            ("辉夜姬", "Kaguya", "", "辅助", "support", "日本神话"),
            ("桃太郎", "Momotaro", "", "战士", "fighter", "日本神话"),
            ("日本武尊", "Yamato Takeru", "", "战士", "fighter", "日本神话"),
            ("少彦名", "Sukunahikona", "", "辅助", "support", "日本神话"),
            ("迩迩艺命", "Ninigi", "", "射手", "marksman", "日本神话"),
        ],
    },
    {
        "id": "celtic_mythology", "display": "Celtic Mythology", "cn": "凯尔特神话",
        "heroes": [
            ("库丘林", "Cú Chulainn", "", "战士", "fighter", "凯尔特神话"),
            ("芬恩·麦克库尔", "Fionn mac Cumhaill", "", "战士", "fighter", "凯尔特神话"),
            ("摩根", "Morgan", "", "法师", "mage", "凯尔特神话"),
            ("卢", "Lugh", "", "射手", "marksman", "凯尔特神话"),
            ("布里吉特", "Brigid", "", "辅助", "support", "凯尔特神话"),
            ("塞努诺斯", "Cernunnos", "", "坦克", "tank", "凯尔特神话"),
            ("达格达", "Dagda", "", "坦克", "tank", "凯尔特神话"),
            ("丹努", "Danu", "", "辅助", "support", "凯尔特神话"),
            ("塔拉尼斯", "Taranis", "", "法师", "mage", "凯尔特神话"),
            ("奥西恩", "Oisín", "", "射手", "marksman", "凯尔特神话"),
            ("奥斯卡", "Oscar", "", "战士", "fighter", "凯尔特神话"),
            ("迪尔米德", "Diarmuid", "", "刺客", "assassin", "凯尔特神话"),
            ("梅芙", "Medb", "", "辅助", "support", "凯尔特神话"),
            ("斯卡哈", "Scáthach", "", "刺客", "assassin", "凯尔特神话"),
            ("玛纳南", "Manannán", "", "坦克", "tank", "凯尔特神话"),
            ("奥格玛", "Oghma", "", "战士", "fighter", "凯尔特神话"),
            ("努阿达", "Nuada", "", "坦克", "tank", "凯尔特神话"),
            ("里安农", "Rhiannon", "", "辅助", "support", "凯尔特神话"),
            ("皮瓦利格", "Pwyll", "", "战士", "fighter", "凯尔特神话"),
        ],
    },
    {
        "id": "slavic_mythology", "display": "Slavic Mythology", "cn": "斯拉夫神话",
        "heroes": [
            ("佩伦", "Perun", "", "战士", "fighter", "斯拉夫神话"),
            ("维列斯", "Veles", "", "刺客", "assassin", "斯拉夫神话"),
            ("莫科什", "Mokosh", "", "辅助", "support", "斯拉夫神话"),
            ("斯瓦罗格", "Svarog", "", "坦克", "tank", "斯拉夫神话"),
            ("达日博格", "Dazhbog", "", "法师", "mage", "斯拉夫神话"),
            ("霍尔", "Khors", "", "法师", "mage", "斯拉夫神话"),
            ("斯特里博格", "Stribog", "", "法师", "mage", "斯拉夫神话"),
            ("特里格拉夫", "Triglav", "", "坦克", "tank", "斯拉夫神话"),
            ("雅利洛", "Yarilo", "", "辅助", "support", "斯拉夫神话"),
            ("切尔诺伯格", "Chernobog", "", "刺客", "assassin", "斯拉夫神话"),
            ("白神", "Belobog", "", "辅助", "support", "斯拉夫神话"),
            ("芭芭雅嘎", "Baba Yaga", "", "法师", "mage", "斯拉夫神话"),
            ("科谢伊", "Koschei", "", "刺客", "assassin", "斯拉夫神话"),
            ("多莫沃伊", "Domovoi", "", "坦克", "tank", "斯拉夫神话"),
            ("莱斯", "Lesh", "", "战士", "fighter", "斯拉夫神话"),
            ("鲁萨尔卡", "Rusalka", "", "辅助", "support", "斯拉夫神话"),
            ("火鸟", "Firebird", "", "射手", "marksman", "斯拉夫神话"),
            ("伊利亚·穆罗梅茨", "Ilya Muromets", "", "战士", "fighter", "斯拉夫神话"),
            ("多布雷尼亚", "Dobrynya", "", "战士", "fighter", "斯拉夫神话"),
            ("阿廖沙", "Alyosha Popovich", "", "刺客", "assassin", "斯拉夫神话"),
        ],
    },
    {
        "id": "aztec_mythology", "display": "Aztec Mythology", "cn": "阿兹特克神话",
        "heroes": [
            ("羽蛇神", "Quetzalcoatl", "", "法师", "mage", "阿兹特克神话"),
            ("特斯卡特利波卡", "Tezcatlipoca", "", "刺客", "assassin", "阿兹特克神话"),
            ("维齐洛波奇特利", "Huitzilopochtli", "", "战士", "fighter", "阿兹特克神话"),
            ("特拉洛克", "Tlaloc", "", "坦克", "tank", "阿兹特克神话"),
            ("米克特兰特库特利", "Mictlantecuhtli", "", "坦克", "tank", "阿兹特克神话"),
            ("西佩·托特克", "Xipe Totec", "", "战士", "fighter", "阿兹特克神话"),
            ("修堤库特里", "Xiuhtecuhtli", "", "法师", "mage", "阿兹特克神话"),
            ("查尔奇乌特利奎", "Chalchiuhtlicue", "", "辅助", "support", "阿兹特克神话"),
            ("托纳蒂乌", "Tonatiuh", "", "法师", "mage", "阿兹特克神话"),
            ("森特奥特尔", "Centeotl", "", "辅助", "support", "阿兹特克神话"),
            ("埃赫卡特尔", "Ehecatl", "", "法师", "mage", "阿兹特克神话"),
            ("米克特卡西瓦特尔", "Mictecacihuatl", "", "辅助", "support", "阿兹特克神话"),
            ("索洛特尔", "Xolotl", "", "刺客", "assassin", "阿兹特克神话"),
            ("科阿特利奎", "Coatlicue", "", "坦克", "tank", "阿兹特克神话"),
            ("科约尔绍基", "Coyolxauhqui", "", "射手", "marksman", "阿兹特克神话"),
            ("梅茨利", "Metztli", "", "法师", "mage", "阿兹特克神话"),
        ],
    },
    {
        "id": "arabian_nights", "display": "One Thousand and One Nights", "cn": "一千零一夜",
        "heroes": [
            ("山鲁佐德", "Shahrazad", "", "辅助", "support", "一千零一夜"),
            ("山鲁亚尔", "Shahryar", "", "战士", "fighter", "一千零一夜"),
            ("敦亚佐德", "Dunyazad", "", "辅助", "support", "一千零一夜"),
            ("阿拉丁", "Aladdin", "", "刺客", "assassin", "一千零一夜"),
            ("辛巴达", "Sinbad", "", "战士", "fighter", "一千零一夜"),
            ("阿里巴巴", "Ali Baba", "", "刺客", "assassin", "一千零一夜"),
            ("马尔基娜", "Morgiana", "", "辅助", "support", "一千零一夜"),
            ("贾法尔", "Ja'far", "", "法师", "mage", "一千零一夜"),
            ("哈伦·拉希德", "Harun al-Rashid", "", "坦克", "tank", "一千零一夜"),
            ("卡西姆", "Cassim", "", "战士", "fighter", "一千零一夜"),
            ("神灯精灵", "Genie of the Lamp", "", "法师", "mage", "一千零一夜"),
            ("白都伦", "Badoura", "", "辅助", "support", "一千零一夜"),
            ("艾哈迈德", "Ahmad", "", "射手", "marksman", "一千零一夜"),
            ("珀里·巴努", "Peri Banu", "", "辅助", "support", "一千零一夜"),
            ("莎赫扎曼", "Shahzaman", "", "战士", "fighter", "一千零一夜"),
        ],
    },
]


def step1_append_unified():
    path = os.path.join(ROOT, "data", "analysis", "all_heroes_unified.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    existing = {(h.get("game"), h.get("name")) for h in data.get("heroes", [])}
    added = 0
    for ip in IPS:
        for (name, name_en, alias, native_role, role, source) in ip["heroes"]:
            if (ip["display"], name) in existing:
                print(f"  SKIP dup in unified: {ip['display']}/{name}")
                continue
            data["heroes"].append({
                "game": ip["display"], "name": name, "name_en": name_en,
                "alias": alias, "native_role": native_role,
                "universal_role": role, "source": source,
            })
            added += 1
    data["total_heroes"] = len(data["heroes"])
    data["total_games"] = len(set(h["game"] for h in data["heroes"]))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[1/3] 主名册追加完成：+{added} 英雄（现共 {data['total_heroes']}）")
    return added


def step2_source_trees():
    for ip in IPS:
        sdir = os.path.join(ROOT, "data", "source", ip["id"])
        os.makedirs(sdir, exist_ok=True)
        heroes = [{"name": name} for (name, *_rest) in ip["heroes"]]
        with open(os.path.join(sdir, "heroes.json"), "w", encoding="utf-8") as f:
            json.dump(heroes, f, ensure_ascii=False, indent=2)
    print(f"[2/3] 源树 data/source/<id>/heroes.json 已写入 {len(IPS)} 个 IP")


def step3_skills():
    total = 0
    for ip in IPS:
        gid = ip["id"]
        for (name, name_en, alias, native_role, role, source) in ip["heroes"]:
            if pool_has(gid, name):
                continue
            skills = gen_skills_for_hero(name, role, seed=stable_seed(name))
            write_hero_skill(gid, name, skills)
            total += 1
    print(f"[3a] 技能池写入完成：+{total} 个英雄技能文件")


def step4_cards():
    total = 0
    failed = 0
    for ip in IPS:
        gid = ip["id"]
        cdir = os.path.join(ROOT, "data", "character_cards", gid)
        os.makedirs(cdir, exist_ok=True)
        for (name, name_en, alias, native_role, role, source) in ip["heroes"]:
            hero = {
                "game": ip["display"], "name": name, "name_en": name_en,
                "alias": alias, "native_role": native_role,
                "universal_role": role, "source": source,
            }
            card = generate_character_card(hero, stable_seed(name))
            viol = schema.validate_card(card)
            if viol:
                failed += 1
                print(f"  ✗ 契约失败 [{gid}] {name}: {'; '.join(viol)}")
                continue
            fp = os.path.join(cdir, f"{name}.json")
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(card, f, ensure_ascii=False, indent=2)
            total += 1
    print(f"[3b] 角色卡生成完成：+{total} 张（失败 {failed}）")


if __name__ == "__main__":
    print("=" * 60)
    print("  公版 IP 批量扩充生成")
    print("=" * 60)
    step1_append_unified()
    step2_source_trees()
    step3_skills()
    step4_cards()
    print("\n完成。下一步：运行 check_cards.py + pytest + rebuild-index + 烟雾对战。")
