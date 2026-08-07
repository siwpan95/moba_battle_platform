#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读探针：内容管线规模压测（ENG-PIPE-001 佐证脚本）。

用途：为《数据管线就绪评估》采集 loader 在 1x/2x/3x/5x 卡量下的
启动耗时与常驻内存，判断 registry 缓存 / loader 启动 / simulator 内存瓶颈。

只读保证：
  - 不修改 data/ 下任何文件；扩容副本全部落在系统临时目录，运行结束即删除
  - 仅 monkeypatch core.loader.CARDS_DIR（进程内），不改动管线源码

用法：python tools/_archive/_pipeline_scale_probe.py
"""

import gc
import io
import os
import shutil
import sys
import tempfile
import time
import tracemalloc

# tools/_archive/x.py -> tools/_archive -> tools -> <项目根>
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import core.loader as L  # noqa: E402

SRC = os.path.join(_ROOT, "data", "character_cards")


def bench(path, label):
    """加载一次并返回 (卡数, 耗时秒, 常驻MB)。loader 自身打印被吞掉。"""
    gc.collect()
    L.CARDS_DIR = path
    tracemalloc.start()
    t0 = time.perf_counter()
    old = sys.stdout
    sys.stdout = io.StringIO()
    try:
        heroes = L.HeroLoader.load_all_heroes()
        hero_dict = L.HeroLoader.build_hero_dict(heroes)
    finally:
        sys.stdout = old
    elapsed = time.perf_counter() - t0
    cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    n, nd = len(heroes), len(hero_dict)
    print(f"{label:<12} 卡数={n:>6}  UI键={nd:>6}  加载={elapsed:>6.3f}s  "
          f"常驻={cur/1048576:>6.1f}MB  峰值={peak/1048576:>6.1f}MB  "
          f"丢键={n - nd:>4}")
    del heroes, hero_dict
    gc.collect()
    return n, elapsed, cur / 1048576


def main():
    print("=" * 78)
    print("  内容管线规模探针 — core.loader.load_all_heroes / build_hero_dict")
    print("=" * 78)
    rows = [bench(SRC, "1x 现状")]

    tmp = tempfile.mkdtemp(prefix="pipe_probe_")
    try:
        for mult in (2, 3, 5):
            flat = os.path.join(tmp, f"flat{mult}")
            os.makedirs(flat, exist_ok=True)
            for i in range(1, mult + 1):
                for g in os.listdir(SRC):
                    p = os.path.join(SRC, g)
                    if not os.path.isdir(p):
                        continue
                    dst = os.path.join(flat, f"{g}__{i}")
                    if not os.path.exists(dst):
                        shutil.copytree(p, dst)
            rows.append(bench(flat, f"{mult}x 扩容"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("-" * 78)
    base_n, base_t, base_m = rows[0]
    print(f"  线性度：耗时 {rows[-1][1] / base_t:.2f}x / 卡量 {rows[-1][0] / base_n:.2f}x"
          f"  ；内存 {rows[-1][2] / base_m:.2f}x")
    print(f"  单卡成本：约 {base_t / base_n * 1000:.3f} ms/卡，"
          f"{base_m / base_n * 1024:.1f} KB/卡（tracemalloc 口径）")


if __name__ == "__main__":
    main()
