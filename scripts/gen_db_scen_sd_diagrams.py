#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为 database / scenario / system-design 三大分类批量生成核心知识点 SVG 静态精绘图。

复用 gen_knowledge_diagrams.py 的解析与渲染逻辑，仅覆盖 CATEGORIES。
"""
import os
import sys
from pathlib import Path

# 让本脚本可被直接 python 运行 (将 scripts/ 加入 sys.path)
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import gen_knowledge_diagrams as gkd  # noqa: E402

# 覆盖目标分类
gkd.CATEGORIES = ["database", "scenario", "system-design"]


def main():
    gkd.IMG_DIR.mkdir(parents=True, exist_ok=True)
    total_files = 0
    total_svg = 0
    total_md = 0
    all_errs = []
    print("=" * 60)
    print("批量生成核心知识点 SVG 图 [database / scenario / system-design]")
    print("=" * 60)
    for cat in gkd.CATEGORIES:
        nf, ns, nm, errs = gkd.process_category(cat)
        total_files += nf
        total_svg += ns
        total_md += nm
        all_errs.extend(errs)
        print(f"[{cat}] files={nf} svg={ns} md_updated={nm} errs={len(errs)}")
    print("-" * 60)
    print(f"TOTAL files={total_files} svg={total_svg} md_updated={total_md}")
    if all_errs:
        print("\nERRORS (前 20 条):")
        for e in all_errs[:20]:
            print(" -", e)
        if len(all_errs) > 20:
            print(f" ... 共 {len(all_errs)} 条错误")
    return 0 if not all_errs else 1


if __name__ == "__main__":
    sys.exit(main())
