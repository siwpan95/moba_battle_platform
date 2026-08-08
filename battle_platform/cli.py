#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""battle_platform 工作流命令行入口。

用法示例：
  python -m battle_platform add-ip --game foo_myth --display "Foo Myth" --cn "福神话"
  python -m battle_platform p0a detect --game arabian_nights
  python -m battle_platform p0a apply --game arabian_nights --map '{"战士·旋风斩":"真旋风"}'
  python -m battle_platform p0b complete --game arabian_nights --dry-run
  python -m battle_platform p1 expand --game foo_myth --json heroes.json
  python -m battle_platform verify --pytest --smoke
"""

import argparse
import json
import os
import sys

from battle_platform import paths
from battle_platform.workflows import add_ip, p0a_rename, p0b_effects, p1_expand, verify


def _cmd_add_ip(a):
    r = add_ip.add_ip(a.game, a.display, a.cn, a.hero_file)
    print("add-ip:", json.dumps(r, ensure_ascii=False))


def _cmd_p0a(a):
    if a.action == "detect":
        hits = p0a_rename.detect_template_skills(a.game)
        t, tot = p0a_rename.template_ratio(a.game)
        print(f"[{a.game}] 模板技能 {t}/{tot}；命中 {len(hits)} 条")
        for h in hits[:20]:
            print(f"  - {h['hero']}#{h['index']}  {h['name']}")
        if len(hits) > 20:
            print(f"  … 其余 {len(hits) - 20} 条省略")
    elif a.action == "apply":
        mapping = json.loads(a.map)
        n = p0a_rename.apply_renames(a.game, mapping)
        print(f"apply: 改名 {n} 条")


def _cmd_p0b(a):
    if a.action == "missing":
        m, tot = p0b_effects.missing_count(a.game)
        print(f"[{a.game}] 缺 effects 技能 {m}/{tot}")
    elif a.action == "complete":
        r = p0b_effects.complete_effects(a.game, dry_run=a.dry_run)
        print("complete:", json.dumps(r, ensure_ascii=False))


def _cmd_p1(a):
    specs = json.load(open(a.json, encoding="utf-8"))
    heroes = specs if isinstance(specs, list) else specs.get("heroes", [])
    if a.spec and hasattr(p1_expand, "build_from_spec"):
        # specs 为 builder.hero() 产物时无法直接跨进程传；此处提示用 build_from_spec 走代码
        print("p1 expand (spec 模式) 请在 Python 中调用 p1_expand.build_from_spec()")
        return
    r = p1_expand.add_heroes(a.game, heroes)
    print("p1 expand:", json.dumps(r, ensure_ascii=False))


def _cmd_verify(a):
    rep = verify.verify(run_pytest=a.pytest, smoke=a.smoke)
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    sys.exit(0 if rep["ok"] else 1)


def main(argv=None):
    p = argparse.ArgumentParser(prog="battle_platform", description="MOBA 对战平台技能流工作流包")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("add-ip", help="新增 IP")
    sp.add_argument("--game", required=True)
    sp.add_argument("--display", required=True)
    sp.add_argument("--cn", required=True)
    sp.add_argument("--hero-file", default="heroes.json")
    sp.set_defaults(func=_cmd_add_ip)

    sp = sub.add_parser("p0a", help="P0-A 模板技能名改写")
    sp.add_argument("action", choices=["detect", "apply"])
    sp.add_argument("--game", required=True)
    sp.add_argument("--map", help="JSON 改名映射 {旧:新}")
    sp.set_defaults(func=_cmd_p0a)

    sp = sub.add_parser("p0b", help="P0-B effects 补全")
    sp.add_argument("action", choices=["missing", "complete"])
    sp.add_argument("--game", required=True)
    sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(func=_cmd_p0b)

    sp = sub.add_parser("p1", help="P1 英雄池扩充")
    sp.add_argument("action", choices=["expand"])
    sp.add_argument("--game", required=True)
    sp.add_argument("--json", required=True, help="英雄清单 JSON（[{name,skills:[4 dict]}]）")
    sp.add_argument("--spec", action="store_true", help="spec 模式（builder.hero 产物，走代码调用）")
    sp.set_defaults(func=_cmd_p1)

    sp = sub.add_parser("verify", help="验证管道")
    sp.add_argument("--pytest", action="store_true")
    sp.add_argument("--smoke", action="store_true")
    sp.set_defaults(func=_cmd_verify)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
