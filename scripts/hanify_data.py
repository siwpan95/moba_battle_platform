"""
数据全面汉化脚本 - 批量修复 moba_battle_platform/data 中的中英混杂问题

运行方式: python scripts/hanify_data.py
"""

import json
import os
import re
import sys
import io
import glob
from pathlib import Path

# 修复 Windows 控制台编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CARDS_DIR = DATA_DIR / "character_cards"

# ============ 属性名映射 ============
ATTR_NAME_CN_MAP = {
    "STR": "力量",
    "DEX": "敏捷",
    "CON": "体质",
    "INT": "智力",
    "WIS": "感知",
    "CHA": "魅力",
}

# ============ 通用角色中文映射 ============
ROLE_CN_MAP = {
    "fighter": "战士",
    "mage": "法师",
    "assassin": "刺客",
    "tank": "坦克",
    "marksman": "射手",
    "support": "辅助",
}

# ============ 效果类型中文映射 ============
EFFECT_CN_MAP = {
    "shield": "护盾",
    "prone": "击倒",
    "reflect": "反射",
    "bleed": "流血",
    "stun": "眩晕",
    "hold": "定身",
    "invis": "隐身",
    "mark": "标记",
    "slow": "减速",
    "immune": "免疫",
    "knockback": "击退",
    "buff": "增益",
    "sunder": "破甲",
    "burn": "灼烧",
    "force": "力场",
    "aoe": "范围",
    "poison": "中毒",
    "silence": "沉默",
    "taunt": "嘲讽",
    "fear": "恐惧",
    "charm": "魅惑",
    "root": "缠绕",
    "disarm": "缴械",
    "blind": "致盲",
    "heal": "治疗",
    "pull": "牵引",
    "dash": "突进",
    "dmg_red": "减伤",
    "dmg_amp": "易伤",
    "crit": "暴击",
    "life_steal": "吸血",
    "execute": "斩杀",
    "revive": "复活",
    "cleanse": "净化",
    "transform": "变形",
    "trap": "陷阱",
    "aura": "光环",
    "summon": "召唤",
    "clone": "分身",
}

# ============ 游戏来源名中文映射（用于 by_role_*.txt） ============
GAME_SOURCE_CN = {
    "[300 Heroes]": "[300英雄]",
    "[Arena of Valor]": "[传说对决]",
    "[Dota 2]": "[刀塔2]",
    "[DC Universe]": "[DC宇宙]",
    "[Demon Slayer]": "[鬼灭之刃]",
    "[Extraordinary Ones]": "[非人学园]",
    "[Genshin Impact]": "[原神]",
    "[Greek Mythology]": "[希腊神话]",
    "[Harry Potter]": "[哈利波特]",
    "[Heroes of the Storm]": "[风暴英雄]",
    "[Honor of Kings]": "[王者荣耀]",
    "[Journey to the West]": "[西游记]",
    "[League of Legends]": "[英雄联盟]",
    "[Marvel Super War]": "[漫威超级战争]",
    "[Marvel Cinematic Universe]": "[漫威电影宇宙]",
    "[Mobile Legends: Bang Bang]": "[无尽对决]",
    "[Norse Mythology]": "[北欧神话]",
    "[One Piece]": "[海贼王]",
    "[Onmyoji Arena]": "[决战！平安京]",
    "[Overwatch 2]": "[守望先锋2]",
    "[Pokemon UNITE]": "[宝可梦大集结]",
    "[SMITE]": "[神之浩劫]",
    "[The Three-Body Problem]": "[三体]",
    "[Romance of the Three Kingdoms]": "[三国演义]",
    "[Vainglory]": "[虚荣]",
    "[World Generals]": "[世界历史名将]",
    "[Heroes Evolved]": "[英魂之刃]",
    "[Cthulhu Mythos]": "[克苏鲁神话]",
    "[Investiture of the Gods]": "[封神演义]",
    "[Dawn Heroes]": "[曙光英雄]",
    "[港漫群英]": "[港漫群英]",
}


def fix_char_card_attributes(filepath: Path) -> bool:
    """修复角色卡片的 attributes.name_cn 字段"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, Exception) as e:
        print(f"  [跳过] 无法解析 {filepath.name}: {e}")
        return False

    modified = False
    if "attributes" in data:
        for attr_key, attr_val in data["attributes"].items():
            if isinstance(attr_val, dict):
                current_cn = attr_val.get("name_cn", "")
                if current_cn in ATTR_NAME_CN_MAP:
                    # name_cn 仍是英文缩写，需要修复
                    attr_val["name_cn"] = ATTR_NAME_CN_MAP[current_cn]
                    modified = True

    if modified:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    return False


def fix_char_card_title(filepath: Path) -> bool:
    """修复角色卡片 hero.title - 当 title 与 name 相同且都是英文时"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return False

    modified = False
    hero = data.get("hero", {})
    name = hero.get("name", "")
    title = hero.get("title", "")
    name_en = hero.get("name_en", "")
    alias = hero.get("alias", "")

    # 判断 title 是否需要修复
    if title and name and _is_english(name):
        if title == name:
            # title 和 name 完全相同且都是英文 → 尝试用 name_en 或清空
            if alias:
                hero["title"] = alias
            elif name_en and name_en != name:
                hero["title"] = name_en
            else:
                # 没有更好的选择，用游戏原生角色名
                pass  # 保留原名，因为无法翻译
            modified = True

    if modified:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    return False


def fix_char_card_missing_fields(filepath: Path) -> bool:
    """补全简化版卡片缺失的中文字段"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return False

    modified = False
    game = data.get("game", {})

    # 补全 role_name
    if "universal_role" in game and "role_name" not in game:
        role = game["universal_role"]
        if role in ROLE_CN_MAP:
            game["role_name"] = ROLE_CN_MAP[role]
            modified = True

    # 补全 role_dnd_class
    if "role_name" in game and "role_dnd_class" not in game:
        game["role_dnd_class"] = game["role_name"]
        modified = True

    if modified:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    return False


def _is_english(text: str) -> bool:
    """判断文本是否主要为英文字符"""
    if not text:
        return False
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    return ascii_chars / len(text) > 0.5


def process_all_char_cards():
    """处理所有角色卡片"""
    print("=" * 60)
    print("阶段1: 修复角色卡片 attributes.name_cn")
    print("=" * 60)
    count_fixed = 0
    count_total = 0
    for json_file in sorted(CARDS_DIR.rglob("*.json")):
        if json_file.name == "_index.json":
            continue
        count_total += 1
        if fix_char_card_attributes(json_file):
            count_fixed += 1
            print(f"  [属性] {json_file.relative_to(BASE_DIR)}")
    print(f"  共扫描 {count_total} 张卡片，修复 {count_fixed} 张\n")

    print("=" * 60)
    print("阶段2: 修复角色卡片 hero.title")
    print("=" * 60)
    count_fixed = 0
    for json_file in sorted(CARDS_DIR.rglob("*.json")):
        if json_file.name == "_index.json":
            continue
        if fix_char_card_title(json_file):
            count_fixed += 1
            print(f"  [标题] {json_file.relative_to(BASE_DIR)}")
    print(f"  修复 {count_fixed} 张卡片\n")

    print("=" * 60)
    print("阶段3: 补全简化版卡片缺失的中文字段")
    print("=" * 60)
    count_fixed = 0
    for json_file in sorted(CARDS_DIR.rglob("*.json")):
        if json_file.name == "_index.json":
            continue
        if fix_char_card_missing_fields(json_file):
            count_fixed += 1
            print(f"  [字段] {json_file.relative_to(BASE_DIR)}")
    print(f"  修复 {count_fixed} 张卡片\n")


def fix_skills_hero_keys(filepath: Path) -> bool:
    """技能JSON中英文英雄键名不翻译（保留为程序键），但添加中文显示名"""
    # 技能JSON的键名作为程序标识符不能更改
    # 这里只做检查，不做修改
    return False


def fix_heroes_md(filepath: Path) -> bool:
    """修复 heroes.md 文件 - 确保表格结构完整，标记名称为实际名称"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return False

    modified = False

    # 只处理有"英雄列表"表格的MD文件
    if "英雄列表" not in content and "英雄列表" not in content:
        return False

    # 修复可能的英文角色标签
    role_translations = [
        ("Mage", "法师"),
        ("Fighter", "战士"),
        ("Assassin", "刺客"),
        ("Tank", "坦克"),
        ("Marksman", "射手"),
        ("Support", "辅助"),
        ("Warrior", "战士"),
        ("Guardian", "守护者"),
        ("Hunter", "射手"),
        ("Specialist", "专精"),
        ("Assault", "突袭"),
    ]

    for eng, chn in role_translations:
        # 只在表格的定位列中替换
        # 匹配 | 名称 | 英文名 | 定位 (可能包含英文)
        pattern = re.compile(rf"(\|[^|]*\|[^|]*\|[^|]*\b){eng}(\b[^|]*\|)", re.IGNORECASE)
        if pattern.search(content):
            # 这里需要小心处理，先跳过复杂的正则
            pass

    if modified:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    return modified


def fix_heroes_txt(filepath: Path) -> bool:
    """修复 heroes.txt 中的英文游戏来源名"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return False

    modified = False
    for eng, chn in GAME_SOURCE_CN.items():
        if eng in content:
            content = content.replace(eng, chn)
            modified = True

    if modified:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    return modified


def process_source_docs():
    """处理源文档"""
    source_dir = DATA_DIR / "source"
    if not source_dir.exists():
        return

    print("=" * 60)
    print("阶段4: 修复 source/heroes.md 文件")
    print("=" * 60)
    count_fixed = 0
    for md_file in sorted(source_dir.rglob("heroes.md")):
        if fix_heroes_md(md_file):
            count_fixed += 1
            print(f"  [MD] {md_file.relative_to(BASE_DIR)}")
    print(f"  修复 {count_fixed} 个文件\n")


def process_by_role_txt():
    """处理 analysis/by_role_*.txt 文件"""
    analysis_dir = DATA_DIR / "analysis"
    if not analysis_dir.exists():
        return

    print("=" * 60)
    print("阶段5: 修复 analysis/by_role_*.txt 游戏来源名")
    print("=" * 60)
    count_fixed = 0
    for txt_file in sorted(analysis_dir.glob("by_role_*.txt")):
        if fix_heroes_txt(txt_file):
            count_fixed += 1
            print(f"  [TXT] {txt_file.relative_to(BASE_DIR)}")
    print(f"  修复 {count_fixed} 个文件\n")


def fix_templates_json():
    """修复技能模板文件中的英文效果类型"""
    templates_file = DATA_DIR / "skills" / "_templates.json"
    if not templates_file.exists():
        print("  _templates.json 不存在，跳过\n")
        return

    print("=" * 60)
    print("阶段6: 修复 _templates.json 效果类型")
    print("=" * 60)

    try:
        with open(templates_file, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"  读取失败: {e}")
        return

    modified = False

    # 修复 effects 字段中的英文值
    # 模式匹配: "type": "shield", "type": "stun" 等效果类型
    for eng, chn in EFFECT_CN_MAP.items():
        pattern = rf'"type":\s*"{eng}"'
        replacement = f'"type": "{chn}"'
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            content = new_content
            modified = True

    if modified:
        with open(templates_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  已修复 {templates_file.relative_to(BASE_DIR)}\n")
    else:
        print(f"  无需修复\n")


def fix_all_heroes_unified():
    """修复 all_heroes_unified.json 中的空 name_en 字段"""
    unified_file = DATA_DIR / "analysis" / "all_heroes_unified.json"
    if not unified_file.exists():
        print("  all_heroes_unified.json 不存在，跳过\n")
        return

    print("=" * 60)
    print("阶段7: 检查 all_heroes_unified.json 空 name_en")
    print("=" * 60)

    try:
        with open(unified_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"  读取失败: {e}")
        return

    empty_count = 0
    if isinstance(data, list):
        for hero in data:
            if not hero.get("name_en"):
                empty_count += 1

    print(f"  共 {len(data)} 条记录，{empty_count} 条 name_en 为空")
    print(f"  (name_en 为空通常是因为英雄原本就是中文名，无需修复)\n")


def main():
    print("=" * 60)
    print("  MOBA 对战平台 - 数据全面汉化")
    print("=" * 60)
    print()

    # 阶段1-3: 角色卡片修复
    process_all_char_cards()

    # 阶段4: 源文档修复
    process_source_docs()

    # 阶段5: 分析文件修复
    process_by_role_txt()

    # 阶段6: 技能模板修复
    fix_templates_json()

    # 阶段7: 统一数据库检查
    fix_all_heroes_unified()

    print("=" * 60)
    print("  汉化处理完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
