#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════╗
║        MOBA 英雄角色卡制作流程工具                  ║
║   统一管理：生成 / 验证 / 统计 / 新增内容           ║
╚══════════════════════════════════════════════════════╝

用法：
  python card_tool.py status              查看当前角色卡状态
  python card_tool.py generate --all      全量重新生成
  python card_tool.py generate --game 王者荣耀  仅生成指定游戏
  python card_tool.py validate            校验所有角色卡合法性
  python card_tool.py add-game --name 新游戏名 --heroes hero_data.json  新增游戏
  python card_tool.py search 亚索         搜索英雄
  python card_tool.py info 亚索           查看单个英雄详情
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from typing import Dict, List, Optional

# 修复 Windows 控制台编码问题
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 将 card_generator 的核心函数导入
from card_generator import (
    generate_character_card, get_skills, GAME_NAME_CN,
    ABILITY_NAMES, ABILITY_CN, CLASS_DEF, ROLE_CN, ROLE_DND,
    ROLE_TEMPLATES, RACIAL_BONUS, validate_point_buy
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 让 tools 脚本能导入 core 包（与 main.py / hero_calculator.py 一致）
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# 游戏注册表 / 共享工具（单一真相）从 core.config 导入
from core.config import REGISTRY_BY_ID, REGISTRY_BY_DISPLAY, detect_hero_file

INPUT_JSON = os.path.join(PROJECT_ROOT, "data", "analysis", "all_heroes_unified.json")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "character_cards")
INDEX_PATH = os.path.join(OUTPUT_DIR, "_index.json")
SKILLS_DIR = os.path.join(PROJECT_ROOT, "data", "skills")


# ==========================================
# 工具函数
# ==========================================

def safe_filename(name: str) -> str:
    """将名称转为安全文件名"""
    return name.replace("/", "_").replace(" ", "_").replace(":", "").replace("\\", "_")


def _skill_entry_count(game_id: str) -> int:
    """返回 skills/<game_id>.json 的英雄技能条目数；无文件/解析失败返回 -1。

    占位游戏技能文件为 {}（空），返回 0 —— 运行时回退通用模板，属预期。
    """
    p = os.path.join(SKILLS_DIR, f"{game_id}.json")
    if not os.path.exists(p):
        return -1
    try:
        with open(p, encoding="utf-8") as f:
            return len(json.load(f))
    except Exception:
        return -1


def _game_dir_for_display(game_name: str) -> str:
    """显示名 -> 角色卡目录（game_id）；未登记游戏回退 safe_filename。"""
    return REGISTRY_BY_DISPLAY.get(game_name, safe_filename(game_name))


def _display_for_dir(dir_name: str) -> str:
    """目录名(game_id) -> 显示名；未知则按旧规则反推。"""
    entry = REGISTRY_BY_ID.get(dir_name)
    return entry["display"] if entry else dir_name.replace("_", " ")


def load_unified_heroes() -> list:
    """加载统一英雄数据"""
    if not os.path.exists(INPUT_JSON):
        print(f"[错误] 未找到数据文件: {INPUT_JSON}")
        sys.exit(1)
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("heroes", [])


def load_existing_cards() -> Dict[str, list]:
    """加载已有角色卡，按游戏分组返回"""
    cards_by_game = defaultdict(list)
    if not os.path.isdir(OUTPUT_DIR):
        return cards_by_game
    for game_dir in os.listdir(OUTPUT_DIR):
        game_path = os.path.join(OUTPUT_DIR, game_dir)
        if not os.path.isdir(game_path) or game_dir.startswith("_"):
            continue
        for filename in os.listdir(game_path):
            if filename.endswith(".json"):
                filepath = os.path.join(game_path, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        card = json.load(f)
                    cards_by_game[game_dir].append(card)
                except Exception:
                    continue
    return cards_by_game


def rebuild_index(cards_by_game: Dict[str, list]):
    """重建索引文件。games 键统一为 game_id（小写 slug），并保留 display/cn。"""
    game_counts = {}
    for dir_name, cards in sorted(cards_by_game.items()):
        # dir_name 现在即 game_id；反查显示名/中文名（大小写正确）
        entry = REGISTRY_BY_ID.get(dir_name)
        if entry:
            game_name = entry["display"]
            game_cn = entry["cn"]
        else:
            game_name = dir_name.replace("_", " ")
            game_cn = GAME_NAME_CN.get(game_name, game_name)
        # 以卡片内 game.name 兜底（双保险）
        if cards:
            card_name = cards[0].get("game", {}).get("name")
            if card_name:
                game_name = card_name
        game_counts[dir_name] = {
            "display": game_name,
            "cn": game_cn,
            "count": len(cards),
            "directory": dir_name,
        }

    total = sum(c["count"] for c in game_counts.values())
    index = {
        "project": "MOBA英雄角色卡",
        "framework": "基于D&D 5e规则的数值体系",
        "total_cards": total,
        "total_games": len(game_counts),
        "games": game_counts,
        "card_schema": {
            "attributes": "六维属性(STR/DEX/CON/INT/WIS/CHA)，含属性值和调整值",
            "stats": "1级和18级战斗数值(生命/护甲/攻击/法强/冷却/暴击率/暴击伤害/攻速/豁免)",
            "skills": "4个技能(3个基础 + 1个大招)，含中文描述",
            "difficulty": "1-5星难度评级",
            "playstyle_tags": "最多8个玩法标签，支持搜索筛选",
        }
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    return index


# ==========================================
# 命令实现
# ==========================================

def cmd_status():
    """查看角色卡状态"""
    print("=" * 60)
    print("  角色卡状态总览")
    print("=" * 60)

    heroes = load_unified_heroes()
    print(f"\n  原始英雄数据: {len(heroes)} 位")

    cards_by_game = load_existing_cards()
    total_cards = sum(len(c) for c in cards_by_game.values())

    if total_cards == 0:
        print(f"  已有角色卡: 0 张 (尚未生成)")
        print(f"\n  运行 'python card_tool.py generate --all' 开始生成")
        return

    print(f"  已有角色卡: {total_cards} 张")

    # 按游戏统计
    print(f"\n  ┌─ 按游戏分布 ─────────────────────────────────┐")
    print(f"  │ {'游戏':<20} {'原始':>5} {'卡片':>5} {'状态':>6} │")
    print(f"  ├{'─'*50}┤")

    hero_count_by_game = defaultdict(int)
    for h in heroes:
        hero_count_by_game[h["game"]] += 1

    for dir_name, cards in sorted(cards_by_game.items()):
        entry = REGISTRY_BY_ID.get(dir_name)
        if entry:
            game_name = entry["display"]
            game_cn = entry["cn"]
        else:
            game_name = dir_name.replace("_", " ")
            game_cn = GAME_NAME_CN.get(game_name, game_name)
        if cards:
            card_name = cards[0].get("game", {}).get("name")
            if card_name:
                game_name = card_name
        hero_count = hero_count_by_game.get(game_name, 0)
        card_count = len(cards)
        if hero_count == card_count:
            status = "✓ 完整"
        elif hero_count > card_count:
            status = f"⚠缺{hero_count - card_count}"
        else:
            status = "?"
        print(f"  │ {game_cn:<18} {hero_count:>5} {card_count:>5} {status:>6} │")
    print(f"  └{'─'*50}┘")

    # 技能文件覆盖情况（占位游戏 skills={} 回退通用模板，属预期，不报错）
    detailed, placeholder = [], []
    for d in sorted(cards_by_game):
        (detailed if _skill_entry_count(d) > 0 else placeholder).append(d)
    print(f"\n  技能文件覆盖: {len(detailed)}/16 详细, {len(placeholder)}/16 占位(运行时回退通用模板)")
    if placeholder:
        names = ", ".join(REGISTRY_BY_ID.get(d, {}).get("display", d) for d in placeholder)
        print(f"    占位游戏(技能缺失, 属预期): {names}")

    # 角色定位分布
    role_count = defaultdict(int)
    for cards in cards_by_game.values():
        for card in cards:
            role = card.get("game", {}).get("universal_role", "?")
            role_count[role] += 1

    print(f"\n  ┌─ 按角色定位分布 ────────────────────────────┐")
    role_order = ["tank", "fighter", "assassin", "mage", "marksman", "support"]
    for role in role_order:
        if role in role_count:
            role_cn = ROLE_CN.get(role, role)
            bar = "█" * (role_count[role] // 30)
            print(f"  │ {role_cn:<6} {role_count[role]:>5}  {bar} │")
    print(f"  └{'─'*50}┘")


def cmd_generate(game_filter: Optional[str] = None):
    """生成角色卡"""
    heroes = load_unified_heroes()

    # 筛选
    if game_filter:
        matched = [h for h in heroes if game_filter in h.get("game", "")
                   or game_filter in GAME_NAME_CN.get(h.get("game", ""), "")
                   or game_filter in h.get("name", "")]
        if not matched:
            # 尝试中文名匹配
            for h in heroes:
                game_cn = GAME_NAME_CN.get(h.get("game", ""), "")
                if game_filter in game_cn or game_filter in h.get("name", ""):
                    matched.append(h)
        if matched:
            heroes = matched
            # 从卡片中取游戏名
            game_names = set(h.get("game", "") for h in heroes)
            print(f"筛选出 {len(heroes)} 位英雄 (来自: {', '.join(GAME_NAME_CN.get(g, g) for g in game_names)})")
        else:
            print(f"[错误] 没有匹配 '{game_filter}' 的英雄")
            print(f"可用游戏: {', '.join(GAME_NAME_CN.values())}")
            return

    print("=" * 60)
    print(f"  生成角色卡 (共 {len(heroes)} 位)")
    print("=" * 60)

    by_game = defaultdict(list)
    for h in heroes:
        by_game[h["game"]].append(h)

    total = 0
    game_counts = {}

    for game_name, game_heroes in sorted(by_game.items()):
        safe_name = _game_dir_for_display(game_name)
        game_dir = os.path.join(OUTPUT_DIR, safe_name)
        os.makedirs(game_dir, exist_ok=True)

        count = 0
        for idx, hero in enumerate(game_heroes):
            card = generate_character_card(hero, total + idx + 1000)
            hero_filename = safe_filename(hero.get("name", f"hero_{idx}"))
            filepath = os.path.join(game_dir, f"{hero_filename}.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(card, f, ensure_ascii=False, indent=2)
            count += 1

        game_counts[game_name] = count
        total += count
        game_cn = GAME_NAME_CN.get(game_name, game_name)
        print(f"  ✓ {game_cn}: {count} 张角色卡")

    # 重建索引
    cards_by_game = load_existing_cards()
    rebuild_index(cards_by_game)

    print(f"\n  完成！共生成 {total} 张角色卡")


def cmd_validate():
    """校验角色卡合法性"""
    print("=" * 60)
    print("  角色卡校验")
    print("=" * 60)

    cards_by_game = load_existing_cards()
    if not cards_by_game:
        print("  未找到角色卡，请先运行 generate --all")
        return

    required_fields = ["card_id", "hero", "game", "source", "difficulty",
                       "playstyle_tags", "attributes", "primary_abilities",
                       "hit_die", "stats_lv1", "stats_lv18", "growth_per_level", "skills"]
    attr_keys = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
    stat_keys = ["level", "hp", "ac", "physical_atk", "magic_power",
                 "prof_bonus", "atk_speed_pct", "crit_chance", "crit_damage",
                 "cdr_pct", "heal_bonus_pct", "cc_resist_pct", "save_bonuses"]

    errors = []
    warnings = []
    total = 0
    valid = 0

    for dir_name, cards in cards_by_game.items():
        for card in cards:
            total += 1
            card_id = card.get("card_id", "?")

            # 检查必填字段
            missing = [f for f in required_fields if f not in card]
            if missing:
                errors.append(f"[{card_id}] 缺少字段: {missing}")
                continue

            # 检查属性
            attrs = card.get("attributes", {})
            for attr in attr_keys:
                if attr not in attrs:
                    errors.append(f"[{card_id}] 缺少属性: {attr}")
                else:
                    a = attrs[attr]
                    if "score" not in a or "modifier" not in a:
                        errors.append(f"[{card_id}] 属性 {attr} 结构不完整")

            # 检查统计
            for stat_key in stat_keys[:-1]:  # 除了 save_bonuses
                if stat_key not in card["stats_lv1"]:
                    errors.append(f"[{card_id}] stats_lv1 缺少: {stat_key}")
                if stat_key not in card["stats_lv18"]:
                    errors.append(f"[{card_id}] stats_lv18 缺少: {stat_key}")

            # 检查技能数
            skills = card.get("skills", [])
            if len(skills) != 4:
                warnings.append(f"[{card_id}] 技能数={len(skills)} (预期4)")

            # 检查难度范围
            diff = card.get("difficulty", 0)
            if not (1 <= diff <= 5):
                errors.append(f"[{card_id}] 难度={diff} (应为1-5)")

            # 检查生命骰
            hit_die = card.get("hit_die", 0)
            if hit_die not in (6, 8, 10, 12):
                errors.append(f"[{card_id}] 生命骰={hit_die} (应为6/8/10/12)")

            # D&D 购点合法性
            scores = {attr: attrs[attr]["score"] for attr in attr_keys if attr in attrs}
            racial_role = card.get("game", {}).get("universal_role", "fighter")
            racial = RACIAL_BONUS.get(racial_role, {})
            base_scores = {attr: scores[attr] - racial.get(attr, 0) for attr in attr_keys}
            cost, legal, violations = validate_point_buy(base_scores)
            if not legal:
                warnings.append(f"[{card_id}] 购点违规: {', '.join(violations)}  (花费={cost})")

            valid += 1

    print(f"\n  总计: {total} 张卡")
    print(f"  有效: {valid} 张卡")
    print(f"  错误: {len(errors)} 项")
    print(f"  警告: {len(warnings)} 项")

    if errors:
        print(f"\n  ┌─ 错误详情 ──────────────────────────────────┐")
        for e in errors[:20]:
            print(f"  │ {e}")
        if len(errors) > 20:
            print(f"  │ ... 还有 {len(errors) - 20} 项错误")
        print(f"  └{'─'*50}┘")

    if warnings:
        print(f"\n  ┌─ 警告详情 ──────────────────────────────────┐")
        for w in warnings[:10]:
            print(f"  │ {w}")
        if len(warnings) > 10:
            print(f"  │ ... 还有 {len(warnings) - 10} 项警告")
        print(f"  └{'─'*50}┘")

    if not errors and not warnings:
        print("\n  ✓ 所有角色卡校验通过！")


def cmd_search(query: str):
    """搜索英雄"""
    heroes = load_unified_heroes()
    query_lower = query.lower().strip()

    matched = []
    for h in heroes:
        name = h.get("name", "").lower()
        name_en = h.get("name_en", "").lower()
        game = h.get("game", "").lower()
        alias = h.get("alias", "").lower()
        role = h.get("universal_role", "").lower()
        role_cn = ROLE_CN.get(role, "").lower()

        if (query_lower in name or query_lower in name_en or
                query_lower in game or query_lower in alias or
                query_lower in role_cn):
            matched.append(h)

    if not matched:
        print(f"未找到匹配 '{query}' 的英雄")
        return

    print("=" * 60)
    print(f"  搜索 '{query}' — 找到 {len(matched)} 位英雄")
    print("=" * 60)
    print(f"\n  {'英雄名':<16} {'游戏':<16} {'定位':<8} {'别名':<12}")
    print(f"  {'-'*55}")
    for h in matched[:30]:
        name = h.get("name", "?")
        game = GAME_NAME_CN.get(h.get("game", ""), h.get("game", "?"))
        role = ROLE_CN.get(h.get("universal_role", ""), "?")
        alias = h.get("alias", "")[:10]
        print(f"  {name:<14} {game:<14} {role:<6} {alias:<12}")
    if len(matched) > 30:
        print(f"  ... 还有 {len(matched) - 30} 位")


def cmd_info(hero_name: str):
    """查看单个英雄详情"""
    heroes = load_unified_heroes()
    hero_name_lower = hero_name.lower().strip()

    # 精确匹配优先
    matched = None
    for h in heroes:
        if h.get("name", "").lower() == hero_name_lower:
            matched = h
            break

    if not matched:
        # 模糊匹配
        for h in heroes:
            if hero_name_lower in h.get("name", "").lower():
                matched = h
                break

    if not matched:
        print(f"未找到英雄 '{hero_name}'")
        return

    print("=" * 60)
    print(f"  英雄详情: {matched['name']}")
    print("=" * 60)
    print(f"  英文名: {matched.get('name_en', '-')}")
    print(f"  别名: {matched.get('alias', '-')}")
    print(f"  来源游戏: {GAME_NAME_CN.get(matched['game'], matched['game'])} ({matched['game']})")
    print(f"  原始定位: {matched.get('native_role', '-')}")
    print(f"  通用定位: {ROLE_CN.get(matched.get('universal_role', ''), '-')}")
    print(f"  IP来源: {matched.get('source', '-')}")

    # 尝试加载对应角色卡
    game_safe = _game_dir_for_display(matched["game"])
    hero_safe = safe_filename(matched["name"])
    card_path = os.path.join(OUTPUT_DIR, game_safe, f"{hero_safe}.json")

    if os.path.exists(card_path):
        with open(card_path, "r", encoding="utf-8") as f:
            card = json.load(f)

        print(f"\n  ┌─ D&D 5e 角色卡 ─────────────────────────────┐")
        print(f"  │ 卡片ID: {card['card_id']}")
        print(f"  │ 难度: {'★'*card['difficulty']}{'☆'*(5-card['difficulty'])}")
        print(f"  │ 生命骰: d{card['hit_die']}")
        print(f"  │")
        print(f"  │ 六维属性:")
        for attr in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]:
            a = card["attributes"][attr]
            cn = ABILITY_CN[attr]
            print(f"  │   {cn:<4} 值:{a['score']:>2}  调整:{a['modifier']:+>3}")
        print(f"  │")
        print(f"  │ 战斗数值 (Lv1):")
        s = card["stats_lv1"]
        print(f"  │   生命:{s['hp']}  护甲:{s['ac']}  攻击:{s['physical_atk']}  法强:{s['magic_power']}")
        print(f"  │   攻速:{s.get('atk_speed_pct',0)}%  暴击率:{s.get('crit_chance',s.get('crit_pct',0))}%")
        print(f"  │   暴击伤害:{s.get('crit_damage',150)}%  冷却:{s.get('cdr_pct',0)}%")
        print(f"  │")
        print(f"  │ 技能:")
        for sk in card.get("skills", []):
            if isinstance(sk, dict):
                # 结构化 D&D 技能
                dmg = sk.get("damage", {})
                dmg_str = f"{dmg.get('dice_count',0)}d{dmg.get('dice_size',0)}+{dmg.get('bonus_attr','?')}"
                line = f"  [{sk.get('key','?')}] {sk.get('name','?')} | {dmg_str} {dmg.get('type','')}"
                if sk.get("saving_throw"):
                    line += f" | {sk['saving_throw']['attr']}豁免 DC={sk['saving_throw']['dc_formula']}"
                line += f" | CD:{sk.get('cooldown',0)}"
                print(f"  │   {line}")
            else:
                print(f"  │   {sk}")
        print(f"  │")
        print(f"  │ 玩法标签: {', '.join(card.get('playstyle_tags', []))}")
        print(f"  └{'─'*50}┘")
    else:
        print(f"\n  (尚未生成角色卡)")


def cmd_add_game(name: str, heroes_file: Optional[str] = None):
    """新增游戏到项目（交互式引导）"""
    print("=" * 60)
    print(f"  新增游戏: {name}")
    print("=" * 60)

    game_dir = os.path.join(PROJECT_ROOT, "data", "source", safe_filename(name))
    os.makedirs(game_dir, exist_ok=True)

    # 创建模板文件
    heroes_template = {
        "game": name,
        "game_name_cn": input("请输入游戏中文名: ").strip(),
        "heroes": []
    }
    heroes_template["heroes"].append({
        "name": "示例英雄",
        "name_en": "示例英雄",
        "alias": "",
        "native_role": "战士/刺客/法师/射手/辅助/坦克",
        "universal_role": "fighter",
        "source": name
    })

    # 写模板
    json_path = os.path.join(game_dir, detect_hero_file(game_dir))
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(heroes_template, f, ensure_ascii=False, indent=2)

    # 写说明
    readme_path = os.path.join(game_dir, "说明.md")
    readme_content = f"""# {name} 英雄数据

## 目录结构
- `heroes.json` — 英雄数据（按模板格式填写）
- `heroes.md` — 可选的人类可读格式
- `heroes.txt` — 可选简单列表

## 数据格式
每个英雄需包含以下字段：
```json
{{
  "name": "英雄中文名",
  "name_en": "英雄英文名",
  "alias": "别名/称号（可选）",
  "native_role": "游戏内定位",
  "universal_role": "fighter|assassin|mage|marksman|support|tank",
  "source": "IP来源/游戏名"
}}
```

## 后续步骤
1. 编辑 `heroes.json`，按模板格式添加英雄数据
2. 运行 `python tools/card_tool.py generate --game {name}` 生成角色卡
"""
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)

    print(f"\n  ✓ 已创建游戏目录: {game_dir}")
    print(f"  ✓ 模板文件: {json_path}")
    print(f"  ✓ 说明文件: {readme_path}")
    print(f"\n  后续步骤:")
    print(f"  1. 编辑 heroes.json 添加英雄数据")
    print(f"  2. 重新运行数据分析")
    print(f"  3. 运行 'python card_tool.py generate --game {name}' 生成角色卡")


def cmd_list_games():
    """列出所有游戏"""
    heroes = load_unified_heroes()
    by_game = defaultdict(list)
    for h in heroes:
        by_game[h["game"]].append(h)

    cards_by_game = load_existing_cards()

    print("=" * 60)
    print("  游戏列表")
    print("=" * 60)
    print(f"\n  {'游戏名':<22} {'英雄数':>6} {'卡片数':>6} {'角色卡目录':<25}")
    print(f"  {'-'*65}")

    for game_name, game_heroes in sorted(by_game.items()):
        game_cn = GAME_NAME_CN.get(game_name, game_name)
        hero_count = len(game_heroes)
        safe_name = _game_dir_for_display(game_name)
        cards = cards_by_game.get(safe_name, [])
        card_count = len(cards)
        print(f"  {game_cn:<20} {hero_count:>6} {card_count:>6} {safe_name:<25}")


# ==========================================
# 命令行入口
# ==========================================

def main():
    parser = argparse.ArgumentParser(
        description="MOBA 英雄角色卡制作流程工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python card_tool.py status                    查看当前状态
  python card_tool.py generate --all           全量生成角色卡
  python card_tool.py generate --game 王者荣耀  仅生成指定游戏
  python card_tool.py validate                 校验所有角色卡
  python card_tool.py search 亚索              搜索英雄
  python card_tool.py info 亚索                查看详情
  python card_tool.py list-games              列出所有游戏
  python card_tool.py add-game --name 新游戏    新增游戏模板
  python card_tool.py rebuild-index            重建索引文件
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # status
    subparsers.add_parser("status", help="查看角色卡状态")

    # generate
    gen_parser = subparsers.add_parser("generate", help="生成角色卡")
    gen_group = gen_parser.add_mutually_exclusive_group()
    gen_group.add_argument("--all", action="store_true", help="生成全部游戏")
    gen_group.add_argument("--game", type=str, help="仅生成指定游戏")

    # validate
    subparsers.add_parser("validate", help="校验角色卡合法性")

    # search
    search_parser = subparsers.add_parser("search", help="搜索英雄")
    search_parser.add_argument("query", type=str, help="搜索关键词")

    # info
    info_parser = subparsers.add_parser("info", help="查看英雄详情")
    info_parser.add_argument("hero", type=str, help="英雄名")

    # list-games
    subparsers.add_parser("list-games", help="列出所有游戏")

    # add-game
    add_parser = subparsers.add_parser("add-game", help="新增游戏")
    add_parser.add_argument("--name", type=str, required=True, help="游戏名")
    add_parser.add_argument("--heroes", type=str, help="英雄数据JSON文件路径（可选）")

    # rebuild-index
    subparsers.add_parser("rebuild-index", help="重建索引文件")

    args = parser.parse_args()

    if args.command == "status" or args.command is None:
        cmd_status()
    elif args.command == "generate":
        if args.game:
            cmd_generate(game_filter=args.game)
        elif args.all:
            cmd_generate(game_filter=None)
        else:
            print("请指定 --all 或 --game")
            parser.print_help()
    elif args.command == "validate":
        cmd_validate()
    elif args.command == "search":
        cmd_search(args.query)
    elif args.command == "info":
        cmd_info(args.hero)
    elif args.command == "list-games":
        cmd_list_games()
    elif args.command == "add-game":
        cmd_add_game(args.name, args.heroes)
    elif args.command == "rebuild-index":
        cards = load_existing_cards()
        rebuild_index(cards)
        print("索引文件已重建")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
