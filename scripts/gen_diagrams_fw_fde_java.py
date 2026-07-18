#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量生成 framework/fde/java 三个分类的核心知识点 SVG 静态精绘图。

输入: questions/<category>/<file>.md (含 frontmatter: title, essence, key_points)
输出:
  1. public/images/diagram_<category>_<filename>.svg
  2. 在 md 文件的 "## 记忆要点" 前插入/替换 "## 核心知识点图" 段
"""

import os
import re
import sys
import html
from pathlib import Path

try:
    import yaml  # PyYAML
except ImportError:
    yaml = None

ROOT = Path("/Users/sunqingguang/hermes/opt/projects/interview-2026")
Q_DIR = ROOT / "questions"
IMG_DIR = ROOT / "public" / "images"

CATEGORIES = ["framework", "fde", "java"]

# 色板
GREEN = "#4CAF50"
ORANGE = "#FF9800"
PURPLE = "#9C27B0"
RED = "#f44336"
BLUE = "#2196F3"
GRAY = "#607D8B"

PALETTE = [BLUE, PURPLE, GREEN, ORANGE, RED, GRAY]


# ----------------------- frontmatter 解析 -----------------------
FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(text):
    m = FM_RE.match(text)
    if not m:
        return {}
    body = m.group(1)
    if yaml:
        try:
            data = yaml.safe_load(body)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}


def get_title(text):
    m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return ""


def get_essence(text):
    fm = parse_frontmatter(text)
    fe = fm.get("feynman")
    if isinstance(fe, dict) and fe.get("essence"):
        return str(fe["essence"]).strip()
    if fm.get("essence"):
        return str(fm["essence"]).strip()
    return ""


def get_key_points(text):
    fm = parse_frontmatter(text)
    fe = fm.get("feynman")
    if isinstance(fe, dict):
        kp = fe.get("key_points")
        if isinstance(kp, list) and kp:
            return [str(x) for x in kp if x]
    kp = fm.get("key_points")
    if isinstance(kp, list) and kp:
        return [str(x) for x in kp if x]
    if isinstance(kp, str) and kp:
        return [kp]
    return []


# ----------------------- 文本工具 -----------------------
def short_label(s, max_len=22):
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"[（(][^）)]*[）)]", "", s).strip()
    if len(s) > max_len:
        for sep in ["——", "— ", "；", "，", "、", " - "]:
            if sep in s:
                head = s.split(sep)[0].strip()
                if 4 <= len(head) <= max_len:
                    s = head
                    break
    if len(s) > max_len:
        s = s[:max_len] + "…"
    return s


def wrap_text(s, max_chars=11):
    s = s.strip()
    if not s:
        return [""]
    tokens = []
    buf = ""
    for ch in s:
        if re.match(r"[A-Za-z0-9.+_/\-]", ch):
            buf += ch
        else:
            if buf:
                tokens.append(buf)
                buf = ""
            tokens.append(ch)
    if buf:
        tokens.append(buf)

    lines = []
    cur = ""
    cur_len = 0
    for tok in tokens:
        tok_len = len(tok)
        if tok_len > max_chars:
            if cur:
                lines.append(cur)
                cur = ""
                cur_len = 0
            for i in range(0, tok_len, max_chars):
                piece = tok[i:i + max_chars]
                if i + max_chars >= tok_len:
                    cur = piece
                    cur_len = len(piece)
                else:
                    lines.append(piece)
            continue
        if cur_len + tok_len <= max_chars:
            cur += tok
            cur_len += tok_len
        else:
            lines.append(cur)
            cur = tok
            cur_len = tok_len
    if cur:
        lines.append(cur)
    return lines


def escape_xml(s):
    return html.escape(s, quote=True)


def _lighten(hex_color, factor=0.88):
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return hex_color
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return f"#{r:02X}{g:02X}{b:02X}"


# ----------------------- SVG 生成 -----------------------
def build_svg(title, essence, key_points):
    kps = [short_label(k) for k in key_points if k and k.strip()]
    if not kps:
        kps = ["核心要点"]
    show_kps = kps[:6]

    W, H = 800, 500
    colors = [PALETTE[i % len(PALETTE)] for i in range(len(show_kps))]

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'style="max-width:100%;height:auto;font-family:\'PingFang SC\',\'Microsoft YaHei\',system-ui,sans-serif;background:#fafafa;">'
    )
    parts.append(
        '<defs>'
        '<marker id="arr" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto">'
        '<path d="M0,0 L10,4 L0,8 Z" fill="#90A4AE"/></marker>'
        '<filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">'
        '<feDropShadow dx="0" dy="2" stdDeviation="2" flood-opacity="0.12"/></filter>'
        '</defs>'
    )
    parts.append(f'<rect width="{W}" height="{H}" fill="#fafafa" rx="8"/>')
    parts.append(f'<rect x="0" y="0" width="{W}" height="6" fill="{BLUE}" rx="3"/>')

    disp_title = title
    m = re.search(r"【.+?】\s*(.+)", disp_title)
    if m:
        disp_title = m.group(1).strip()
    if len(disp_title) > 36:
        disp_title = disp_title[:36] + "…"

    parts.append(
        f'<text x="{W/2}" y="48" text-anchor="middle" '
        f'font-size="22" font-weight="700" fill="#263238">{escape_xml(disp_title)}</text>'
    )
    parts.append(f'<line x1="80" y1="68" x2="{W-80}" y2="68" stroke="#E0E0E0" stroke-width="1"/>')

    sub = essence.strip() if essence else ""
    if len(sub) > 64:
        sub = sub[:64] + "…"
    if sub:
        parts.append(
            f'<text x="{W/2}" y="92" text-anchor="middle" '
            f'font-size="13" fill="#546E7A" font-style="italic">{escape_xml(sub)}</text>'
        )

    n = len(show_kps)
    if n == 1:
        n = 2

    if n <= 3:
        rows = [show_kps]
        row_colors = [colors]
    else:
        half = (n + 1) // 2
        rows = [show_kps[:half], show_kps[half:]]
        row_colors = [colors[:half], colors[half:]]

    row_y = [210, 350]
    node_w = 180
    node_h = 80

    def row_xs(items):
        total_w = len(items) * node_w + (len(items) - 1) * 30
        start_x = (W - total_w) / 2
        return [start_x + i * (node_w + 30) for i in range(len(items))]

    for ri, row in enumerate(rows):
        xs = row_xs(row)
        y = row_y[ri]
        for i in range(len(row) - 1):
            x1 = xs[i] + node_w
            x2 = xs[i + 1]
            ym = y + node_h / 2
            parts.append(
                f'<line x1="{x1}" y1="{ym}" x2="{x2-4}" y2="{ym}" '
                f'stroke="#90A4AE" stroke-width="2" marker-end="url(#arr)"/>'
            )
        if ri > 0:
            prev_row = rows[ri - 1]
            prev_xs = row_xs(prev_row)
            last_x = prev_xs[-1] + node_w / 2
            last_y_bot = row_y[ri - 1] + node_h
            cur_first_x = xs[0] + node_w / 2
            cur_y_top = y
            mid_y = (last_y_bot + cur_y_top) / 2
            parts.append(
                f'<path d="M {last_x} {last_y_bot} L {last_x} {mid_y} '
                f'L {cur_first_x} {mid_y} L {cur_first_x} {cur_y_top-4}" '
                f'fill="none" stroke="#90A4AE" stroke-width="2" stroke-dasharray="5,3" '
                f'marker-end="url(#arr)"/>'
            )

    for ri, row in enumerate(rows):
        xs = row_xs(row)
        y = row_y[ri]
        for i, (label, x) in enumerate(zip(row, xs)):
            color = row_colors[ri][i]
            fill = _lighten(color)
            parts.append(
                f'<rect x="{x}" y="{y}" width="{node_w}" height="{node_h}" '
                f'rx="10" fill="{fill}" stroke="{color}" stroke-width="2" filter="url(#shadow)"/>'
            )
            parts.append(
                f'<rect x="{x}" y="{y}" width="6" height="{node_h}" rx="3" fill="{color}"/>'
            )
            seq = ri * (len(rows[0]) if len(rows) > 1 else 0) + i + 1
            parts.append(
                f'<circle cx="{x + node_w - 18}" cy="{y + 18}" r="11" fill="{color}"/>'
            )
            parts.append(
                f'<text x="{x + node_w - 18}" y="{y + 22}" text-anchor="middle" '
                f'font-size="12" font-weight="700" fill="#fff">{seq}</text>'
            )
            text_lines = wrap_text(label, max_chars=9)
            ty = y + node_h / 2 - (len(text_lines) - 1) * 9 + 2
            for tl in text_lines:
                parts.append(
                    f'<text x="{x + node_w / 2 + 3}" y="{ty}" text-anchor="middle" '
                    f'font-size="13" font-weight="600" fill="#263238">{escape_xml(tl)}</text>'
                )
                ty += 18

    legend_y = H - 36
    parts.append(
        f'<text x="40" y="{legend_y}" font-size="12" fill="#78909C" font-weight="600">核心知识点流程图</text>'
    )
    lx = 220
    for i, c in enumerate(PALETTE):
        parts.append(f'<rect x="{lx + i*70}" y="{legend_y-12}" width="14" height="14" rx="3" fill="{c}"/>')
        names = ["蓝", "紫", "绿", "橙", "红", "灰"]
        parts.append(
            f'<text x="{lx + i*70 + 20}" y="{legend_y-1}" font-size="11" fill="#546E7A">{names[i]}</text>'
        )
    parts.append(
        f'<text x="{W-40}" y="{legend_y}" text-anchor="end" font-size="11" fill="#90A4AE" font-style="italic">interview-2026</text>'
    )

    parts.append('</svg>')
    return "\n".join(parts)


# ----------------------- md 插入 -----------------------
SECTION_HEADER = "## 核心知识点图"
MEMORY_HEADER = "## 记忆要点"


def update_markdown(md_path, img_relative_path, title):
    text = md_path.read_text(encoding="utf-8")
    alt = (title or "核心知识点图") + " - 核心知识点图"
    new_section = (
        f"{SECTION_HEADER}\n\n"
        f'<img src="/interview-2026/images/{img_relative_path}" '
        f'alt="{escape_xml(alt)}" '
        f'style="max-width:100%;height:auto;border:1px solid var(--border);'
        f'border-radius:8px;margin:1em 0;" />\n'
    )

    pattern = re.compile(
        rf"{re.escape(SECTION_HEADER)}.*?(?=\n## |\Z)",
        re.DOTALL,
    )
    if SECTION_HEADER in text:
        text_new = pattern.sub(new_section + "\n", text, count=1)
    else:
        if MEMORY_HEADER in text:
            text_new = text.replace(
                MEMORY_HEADER,
                new_section + "\n" + MEMORY_HEADER,
                1,
            )
        else:
            text_new = text.rstrip() + "\n\n" + new_section

    md_path.write_text(text_new, encoding="utf-8")


# ----------------------- 主流程 -----------------------
def process_category(cat):
    cat_dir = Q_DIR / cat
    if not cat_dir.exists():
        print(f"[{cat}] 目录不存在，跳过")
        return 0, 0, 0, [f"目录不存在: {cat_dir}"]
    files = sorted(cat_dir.glob("*.md"))
    n_svg = 0
    n_md = 0
    errs = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
            title = get_title(text)
            essence = get_essence(text)
            kps = get_key_points(text)
            if not kps:
                kps = [title or "核心要点"]

            stem = f.stem
            svg_name = f"diagram_{cat}_{stem}.svg"
            svg_path = IMG_DIR / svg_name
            svg = build_svg(title, essence, kps)
            svg_path.write_text(svg, encoding="utf-8")
            n_svg += 1

            update_markdown(f, svg_name, title)
            n_md += 1
        except Exception as e:
            errs.append(f"{f.name}: {e}")
    return len(files), n_svg, n_md, errs


def main():
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    total_files = 0
    total_svg = 0
    total_md = 0
    all_errs = []
    print("=" * 60)
    print("批量生成核心知识点 SVG 图 (framework/fde/java)")
    print("=" * 60)
    for cat in CATEGORIES:
        nf, ns, nm, errs = process_category(cat)
        total_files += nf
        total_svg += ns
        total_md += nm
        all_errs.extend(errs)
        print(f"[{cat}] files={nf} svg={ns} md_updated={nm} errs={len(errs)}")
    print("-" * 60)
    print(f"TOTAL files={total_files} svg={total_svg} md_updated={total_md}")
    if all_errs:
        print("\nERRORS:")
        for e in all_errs:
            print(" -", e)
    return 0 if not all_errs else 1


if __name__ == "__main__":
    sys.exit(main())
