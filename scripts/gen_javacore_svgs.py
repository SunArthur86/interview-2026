#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为 questions/java-core/ 下每道面试题生成核心知识点 SVG 静态精绘图。
- 读取每题 frontmatter（title/h1, essence, key_points）
- 基于关键词路由到 25+ 种主题模板（JVM/GC/线程/集合/网络/Spring/并发/IO/事务/算法...）
- 模板未命中时走通用流程/对比/层级兜底
- SVG 规范：viewBox=0 0 800 500，标题 + 节点 + 箭头 + 6 色系
- md 在 `## 记忆要点` 前插入/替换 `## 核心知识点图` 段
- 输出：public/images/diagram_java-core_<filename>.svg

用法:
  python3 scripts/gen_javacore_svgs.py            # 全量
  python3 scripts/gen_javacore_svgs.py core-002   # 指定文件（可多个）
"""
import os
import re
import sys
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QDIR = ROOT / 'questions' / 'java-core'
IMG_DIR = ROOT / 'public' / 'images'

# 6 色系（题目要求）
GREEN = '#4CAF50'
ORANGE = '#FF9800'
PURPLE = '#9C27B0'
RED = '#f44336'
BLUE = '#2196F3'
GRAY = '#607D8B'

PALETTE = [GREEN, ORANGE, PURPLE, RED, BLUE, GRAY]

# ---------- helpers ----------

def esc(s):
    """HTML-escape text for SVG, preserve CJK."""
    if s is None:
        return ''
    return html.escape(str(s), quote=True)

def wrap_text(text, max_chars):
    """按字符宽度（中文=2，西文=1）做换行；支持显式 \\n 软换行。"""
    if not text:
        return ['']
    result = []
    # 先按显式换行切段
    for segment in str(text).split('\n'):
        if not segment:
            result.append('')
            continue
        # 再按宽度切分
        cur = ''
        cnt = 0
        for ch in segment:
            w = 2 if ord(ch) > 127 else 1
            if cnt + w > max_chars and cur:
                result.append(cur)
                cur = ch
                cnt = w
            else:
                cur += ch
                cnt += w
        if cur:
            result.append(cur)
    return result or ['']

def svg_header(title, subtitle=''):
    """SVG 公共头：背景、标题、副标题。"""
    parts = []
    parts.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500" '
                 'font-family="-apple-system, BlinkMacSystemFont, \'PingFang SC\', \'Microsoft YaHei\', sans-serif">')
    # 背景
    parts.append('<rect width="800" height="500" fill="#FAFBFC"/>')
    # 标题条
    parts.append(f'<rect x="0" y="0" width="800" height="64" fill="{BLUE}"/>')
    # 左色块强调
    parts.append(f'<rect x="0" y="0" width="8" height="64" fill="{ORANGE}"/>')
    title_short = title[:38] + ('…' if len(title) > 38 else '')
    parts.append(f'<text x="28" y="40" font-size="22" font-weight="700" fill="#FFFFFF" '
                 f'text-rendering="geometricPrecision">{esc(title_short)}</text>')
    if subtitle:
        parts.append(f'<text x="28" y="552" font-size="0"></text>')  # placeholder
    # 副标题（essence）放在标题下方
    if subtitle:
        sub_short = subtitle[:60] + ('…' if len(subtitle) > 60 else '')
        parts.append(f'<text x="28" y="92" font-size="14" fill="#37474F" font-style="italic">'
                     f'核心：{esc(sub_short)}</text>')
        body_top = 110
    else:
        body_top = 86
    parts.append(f'<!-- BODY_TOP={body_top} -->')
    return '\n'.join(parts), body_top

def svg_footer():
    return '</svg>'

# arrow marker definition (use once per svg)
ARROW_DEFS = '''<defs>
<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
  <path d="M0,0 L10,5 L0,10 z" fill="#455A64"/>
</marker>
<marker id="arrowG" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
  <path d="M0,0 L10,5 L0,10 z" fill="{green}"/>
</marker>
</defs>'''.format(green=GREEN)

def box(x, y, w, h, text, fill='#FFFFFF', stroke=BLUE, text_color='#263238',
        font_size=14, radius=8, weight=600, line_max=14):
    """绘制一个圆角矩形节点。"""
    parts = [f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" rx="{radius}" '
             f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>']
    lines = wrap_text(text, line_max)
    cy = y + h / 2 - (len(lines) - 1) * (font_size * 0.6)
    for ln in lines:
        parts.append(f'<text x="{x + w/2:.0f}" y="{cy:.0f}" font-size="{font_size}" '
                     f'fill="{text_color}" text-anchor="middle" dominant-baseline="middle" '
                     f'font-weight="{weight}">{esc(ln)}</text>')
        cy += font_size * 1.2
    return '\n'.join(parts)

def diamond(cx, cy, w, h, text, fill='#FFF8E1', stroke=ORANGE, font_size=13):
    """菱形判断节点。"""
    pts = f'{cx},{cy-h/2} {cx+w/2},{cy} {cx},{cy+h/2} {cx-w/2},{cy}'
    parts = [f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>']
    lines = wrap_text(text, 12)
    ty = cy - (len(lines) - 1) * (font_size * 0.6)
    for ln in lines:
        parts.append(f'<text x="{cx:.0f}" y="{ty:.0f}" font-size="{font_size}" fill="#263238" '
                     f'text-anchor="middle" dominant-baseline="middle">{esc(ln)}</text>')
        ty += font_size * 1.15
    return '\n'.join(parts)

def arrow(x1, y1, x2, y2, color='#455A64', dashed=False, label='', marker='arrow'):
    dash = ' stroke-dasharray="6,4"' if dashed else ''
    parts = [f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" '
             f'stroke="{color}" stroke-width="2"{dash} marker-end="url(#{marker})"/>']
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        parts.append(f'<text x="{mx:.0f}" y="{my - 6:.0f}" font-size="11" fill="{color}" '
                     f'text-anchor="middle" font-weight="600">{esc(label)}</text>')
    return '\n'.join(parts)

def section_label(x, y, text, color=GRAY):
    return (f'<text x="{x:.0f}" y="{y:.0f}" font-size="13" fill="{color}" '
            f'font-weight="700" letter-spacing="0.5">{esc(text)}</text>')

def legend(items, x=520, y=120):
    """items: list of (color, label)。右上图例。"""
    parts = []
    bx = x
    by = y
    width = 16
    for i, (c, lab) in enumerate(items):
        yy = by + i * 22
        parts.append(f'<rect x="{bx}" y="{yy}" width="14" height="14" rx="3" fill="{c}"/>')
        parts.append(f'<text x="{bx + 20}" y="{yy + 11}" font-size="12" fill="#37474F">{esc(lab)}</text>')
    return '\n'.join(parts)

# ---------- SVG 主题模板 ----------

def tpl_flow_vertical(title, essence, steps, body_top=110,
                      colors=None, decision=None):
    """通用竖向流程图。steps: list of str。可选 decision 插在第 N 步后。"""
    if colors is None:
        colors = [BLUE, GREEN, ORANGE, PURPLE, RED, GRAY]
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    n = len(steps)
    avail_h = 500 - body_top - 30
    box_h = min(56, max(40, (avail_h - 30 * (n - 1)) // n))
    box_w = 320
    x = (800 - box_w) // 2
    gap = (avail_h - box_h * n) // max(n - 1, 1)
    gap = min(gap, 36)
    y = body_top + 6
    centers = []
    for i, s in enumerate(steps):
        c = colors[i % len(colors)]
        parts.append(box(x, y, box_w, box_h, s, fill='#FFFFFF', stroke=c,
                         text_color='#263238', font_size=15, weight=600, line_max=20))
        centers.append((x + box_w / 2, y, y + box_h))
        y += box_h + gap
    # 箭头
    for i in range(n - 1):
        _, _, y_top = centers[i]
        _, y_next_bot, _ = centers[i + 1]
        cx = x + box_w / 2
        parts.append(arrow(cx, y_top, cx, y_next_bot))
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_layers(title, essence, layers, body_top=110, colors=None, vertical=False):
    """层级图：layers = [(label, [items...]), ...]。"""
    if colors is None:
        colors = [BLUE, GREEN, ORANGE, PURPLE, RED, GRAY]
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    n = len(layers)
    avail_h = 500 - body_top - 30
    layer_h = min(80, max(50, (avail_h - 16 * (n - 1)) // n))
    gap = 16
    y = body_top + 4
    for i, (label, items) in enumerate(layers):
        c = colors[i % len(colors)]
        # 整层背景
        parts.append(f'<rect x="40" y="{y:.0f}" width="720" height="{layer_h:.0f}" rx="8" '
                     f'fill="{c}22" stroke="{c}" stroke-width="2"/>')
        # 左侧 label
        parts.append(f'<text x="56" y="{y + layer_h/2:.0f}" font-size="15" fill="{c}" '
                     f'font-weight="700" dominant-baseline="middle">{esc(label)}</text>')
        # 右侧 items
        items_text = '  ·  '.join(items) if isinstance(items, list) else str(items)
        lines = wrap_text(items_text, 50)
        iy = y + layer_h / 2 - (len(lines) - 1) * 9
        for ln in lines:
            parts.append(f'<text x="170" y="{iy:.0f}" font-size="13" fill="#263238" '
                         f'dominant="middle">{esc(ln)}</text>')
            iy += 16
        y += layer_h + gap
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_compare(title, essence, cols, body_top=110):
    """对比图：cols = [(name, [features...]), ...]。2~4 列。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    n = len(cols)
    avail_w = 720
    gap = 16
    col_w = (avail_w - gap * (n - 1)) / n
    x0 = 40
    colors = [BLUE, ORANGE, GREEN, PURPLE][:n]
    y_top = body_top + 4
    col_h = 360
    # 表头
    for i, (name, _) in enumerate(cols):
        x = x0 + i * (col_w + gap)
        parts.append(f'<rect x="{x:.0f}" y="{y_top:.0f}" width="{col_w:.0f}" height="44" rx="8" '
                     f'fill="{colors[i]}"/>')
        parts.append(f'<text x="{x + col_w/2:.0f}" y="{y_top + 28:.0f}" font-size="16" '
                     f'fill="#FFFFFF" text-anchor="middle" font-weight="700">{esc(name)}</text>')
    # 内容
    yy = y_top + 60
    max_rows = max(len(c[1]) for c in cols)
    row_h = (col_h - 60) // max(max_rows, 1)
    for r in range(max_rows):
        for i, (name, feats) in enumerate(cols):
            x = x0 + i * (col_w + gap)
            feat = feats[r] if r < len(feats) else ''
            bg = '#FFFFFF' if r % 2 == 0 else '#F5F5F5'
            parts.append(f'<rect x="{x:.0f}" y="{yy:.0f}" width="{col_w:.0f}" height="{row_h:.0f}" '
                         f'fill="{bg}" stroke="#E0E0E0" stroke-width="1"/>')
            lines = wrap_text(feat, int(col_w / 7.5))
            ly = yy + row_h / 2 - (len(lines) - 1) * 8
            for ln in lines:
                parts.append(f'<text x="{x + col_w/2:.0f}" y="{ly:.0f}" font-size="12" '
                             f'fill="#37474F" text-anchor="middle" dominant-baseline="middle">{esc(ln)}</text>')
                ly += 15
        yy += row_h
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_mindmap(title, essence, center, branches, body_top=110):
    """中心放射图：center: str；branches: list of (label, color)。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    cx, cy = 400, (body_top + 500) // 2
    r = 240
    # 中心
    parts.append(f'<ellipse cx="{cx}" cy="{cy}" rx="110" ry="46" fill="{BLUE}" '
                 f'stroke="{ORANGE}" stroke-width="3"/>')
    for ln in wrap_text(center, 12):
        pass
    lines = wrap_text(center, 12)
    ly = cy - (len(lines) - 1) * 9
    for ln in lines:
        parts.append(f'<text x="{cx}" y="{ly}" font-size="15" fill="#FFFFFF" '
                     f'text-anchor="middle" dominant-baseline="middle" font-weight="700">{esc(ln)}</text>')
        ly += 17
    # 分支
    n = len(branches)
    import math
    for i, (label, color) in enumerate(branches):
        angle = -math.pi / 2 + 2 * math.pi * i / n
        bx = cx + r * math.cos(angle)
        by = cy + r * 0.62 * math.sin(angle)
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{bx:.0f}" y2="{by:.0f}" '
                     f'stroke="{color}" stroke-width="2" stroke-dasharray="4,3"/>')
        parts.append(f'<ellipse cx="{bx:.0f}" cy="{by:.0f}" rx="86" ry="36" '
                     f'fill="#FFFFFF" stroke="{color}" stroke-width="2"/>')
        blines = wrap_text(label, 12)
        byy = by - (len(blines) - 1) * 8
        for ln in blines:
            parts.append(f'<text x="{bx:.0f}" y="{byy:.0f}" font-size="12" fill="{color}" '
                         f'text-anchor="middle" dominant-baseline="middle" font-weight="600">{esc(ln)}</text>')
            byy += 14
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_pipeline(title, essence, stages, body_top=110, colors=None):
    """横向流水线：stages = list of str。"""
    if colors is None:
        colors = [BLUE, GREEN, ORANGE, PURPLE, RED, GRAY]
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    n = len(stages)
    avail_w = 720
    gap = 18
    box_w = (avail_w - gap * (n - 1)) / n
    box_h = 90
    y = body_top + 90
    x = 40
    centers = []
    for i, s in enumerate(stages):
        c = colors[i % len(colors)]
        parts.append(box(x, y, box_w, box_h, s, fill=c + '22', stroke=c,
                         text_color='#263238', font_size=13, weight=600, line_max=int(box_w / 8)))
        # 步骤序号
        parts.append(f'<circle cx="{x + 18}" cy="{y + 18}" r="13" fill="{c}"/>')
        parts.append(f'<text x="{x + 18}" y="{y + 23}" font-size="13" fill="#FFFFFF" '
                     f'text-anchor="middle" font-weight="700">{i + 1}</text>')
        centers.append((x, x + box_w, y + box_h / 2))
        x += box_w + gap
    for i in range(n - 1):
        _, x_right, yc = centers[i]
        x_left, _, _ = centers[i + 1]
        parts.append(arrow(x_right, yc, x_left, yc))
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_two_phase(title, essence, left_title, left_items, right_title, right_items,
                  body_top=110):
    """两栏对照图（如 慢启动 vs 拥塞避免 / 强一致性 vs 最终一致）。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    # 左
    parts.append(f'<rect x="40" y="{body_top}" width="340" height="360" rx="12" '
                 f'fill="{BLUE}11" stroke="{BLUE}" stroke-width="2"/>')
    parts.append(f'<text x="210" y="{body_top + 32}" font-size="17" fill="{BLUE}" '
                 f'text-anchor="middle" font-weight="700">{esc(left_title)}</text>')
    yy = body_top + 60
    for it in left_items:
        parts.append(f'<circle cx="64" cy="{yy + 8}" r="5" fill="{BLUE}"/>')
        for j, ln in enumerate(wrap_text(it, 38)):
            parts.append(f'<text x="78" y="{yy + 12 + j * 17}" font-size="13" fill="#263238">{esc(ln)}</text>')
        yy += 22 + len(wrap_text(it, 38)) * 4
    # 右
    parts.append(f'<rect x="420" y="{body_top}" width="340" height="360" rx="12" '
                 f'fill="{ORANGE}11" stroke="{ORANGE}" stroke-width="2"/>')
    parts.append(f'<text x="590" y="{body_top + 32}" font-size="17" fill="{ORANGE}" '
                 f'text-anchor="middle" font-weight="700">{esc(right_title)}</text>')
    yy = body_top + 60
    for it in right_items:
        parts.append(f'<circle cx="444" cy="{yy + 8}" r="5" fill="{ORANGE}"/>')
        for j, ln in enumerate(wrap_text(it, 38)):
            parts.append(f'<text x="458" y="{yy + 12 + j * 17}" font-size="13" fill="#263238">{esc(ln)}</text>')
        yy += 22 + len(wrap_text(it, 38)) * 4
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_decision_tree(title, essence, root, branches, body_top=110):
    """决策树：root -> 多个分支，每个分支带条件。branches = [(cond, result, color)]。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    # 根
    parts.append(f'<rect x="320" y="{body_top}" width="160" height="56" rx="10" '
                 f'fill="{BLUE}" stroke="{ORANGE}" stroke-width="2"/>')
    for j, ln in enumerate(wrap_text(root, 12)):
        parts.append(f'<text x="400" y="{body_top + 32 + j * 17}" font-size="14" fill="#FFFFFF" '
                     f'text-anchor="middle" font-weight="700">{esc(ln)}</text>')
    n = len(branches)
    by_top = body_top + 100
    bw = (720 - 24 * (n - 1)) / n
    for i, (cond, result, color) in enumerate(branches):
        x = 40 + i * (bw + 24)
        # 连线
        parts.append(arrow(400, body_top + 56, x + bw / 2, by_top + 30, color=color))
        # 条件小标签
        parts.append(f'<text x="{x + bw/2:.0f}" y="{by_top + 14}" font-size="12" fill="{color}" '
                     f'text-anchor="middle" font-weight="700">{esc(cond)}</text>')
        # 结果盒
        parts.append(f'<rect x="{x:.0f}" y="{by_top + 24}" width="{bw:.0f}" height="90" rx="8" '
                     f'fill="{color}22" stroke="{color}" stroke-width="2"/>')
        for j, ln in enumerate(wrap_text(result, int(bw / 8.5))):
            parts.append(f'<text x="{x + bw/2:.0f}" y="{by_top + 50 + j * 18}" font-size="13" '
                         f'fill="#263238" text-anchor="middle" font-weight="600">{esc(ln)}</text>')
        # 备注：可在结果下补充细节
        parts.append(f'<rect x="{x:.0f}" y="{by_top + 130}" width="{bw:.0f}" height="120" rx="8" '
                     f'fill="#FFFFFF" stroke="#E0E0E0" stroke-width="1" stroke-dasharray="4,3"/>')
        parts.append(f'<text x="{x + bw/2:.0f}" y="{by_top + 156}" font-size="11" fill="{color}" '
                     f'text-anchor="middle" font-weight="600">说明</text>')
        for j, ln in enumerate(wrap_text(result, int(bw / 7))[:4]):
            parts.append(f'<text x="{x + bw/2:.0f}" y="{by_top + 180 + j * 16}" font-size="11" '
                         f'fill="#546E7A" text-anchor="middle">{esc(ln)}</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

# ---------- 高级专用模板 ----------

def tpl_jvm_memory(title, essence, body_top=110):
    """JVM 内存结构图。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(f'<rect x="40" y="{body_top}" width="720" height="340" rx="10" '
                 f'fill="#FFFFFF" stroke="{BLUE}" stroke-width="2"/>')
    parts.append(f'<text x="56" y="{body_top + 26}" font-size="15" fill="{BLUE}" font-weight="700">JVM 运行时数据区</text>')
    # 堆（左大）
    parts.append(f'<rect x="60" y="{body_top + 44}" width="380" height="280" rx="8" '
                 f'fill="{ORANGE}22" stroke="{ORANGE}" stroke-width="2"/>')
    parts.append(f'<text x="250" y="{body_top + 68}" font-size="14" fill="{ORANGE}" '
                 f'text-anchor="middle" font-weight="700">堆 Heap（线程共享）</text>')
    # 堆内分区
    for i, (n, c) in enumerate([('新生代 Eden', GREEN), ('Survivor 0/1', BLUE), ('老年代 Old', RED)]):
        y = body_top + 84 + i * 76
        parts.append(f'<rect x="80" y="{y}" width="340" height="62" rx="6" fill="{c}22" stroke="{c}"/>')
        parts.append(f'<text x="250" y="{y + 36}" font-size="13" fill="{c}" text-anchor="middle" '
                     f'font-weight="700">{esc(n)}</text>')
    # 非堆（右）
    parts.append(f'<rect x="460" y="{body_top + 44}" width="285" height="280" rx="8" '
                 f'fill="{PURPLE}22" stroke="{PURPLE}" stroke-width="2"/>')
    parts.append(f'<text x="602" y="{body_top + 68}" font-size="14" fill="{PURPLE}" '
                 f'text-anchor="middle" font-weight="700">非堆 / 线程私有</text>')
    for i, (n, c) in enumerate([('方法区/元空间', PURPLE), ('虚拟机栈 / 本地方法栈', BLUE), ('程序计数器 PC', GREEN)]):
        y = body_top + 84 + i * 76
        parts.append(f'<rect x="478" y="{y}" width="249" height="62" rx="6" fill="{c}22" stroke="{c}"/>')
        parts.append(f'<text x="602" y="{y + 36}" font-size="12" fill="{c}" text-anchor="middle" '
                     f'font-weight="700">{esc(n)}</text>')
    parts.append(f'<text x="400" y="{body_top + 410}" font-size="12" fill="{GRAY}" text-anchor="middle">'
                 f'GC 主战场：新生代用复制算法，老年代用标记-整理</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_gc_flow(title, essence, body_top=110):
    """GC 流程：对象分配 → Minor GC → Major GC → Full GC。"""
    return tpl_pipeline(title, essence, [
        '新对象分配\n→ Eden 区',
        'Eden 满\n触发 Minor GC',
        '存活对象\n→ Survivor 复制',
        'Survivor 满 / 年龄≥15\n晋升老年代',
        '老年代满\n触发 Full GC',
        '回收 / Stop-The-World',
    ], body_top=body_top)

def tpl_thread_states(title, essence, body_top=110):
    """Java 线程状态机。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    # 6 个状态
    states = [
        ('NEW', '新建\n(start())', BLUE, 80, 200),
        ('RUNNABLE', '就绪+运行\n(OS 调度)', GREEN, 280, 130),
        ('BLOCKED', '阻塞\n(等 synchronized)', RED, 480, 200),
        ('WAITING', '等待\n(wait/join)', ORANGE, 620, 130),
        ('TIMED_WAITING', '限时等待\n(sleep/wait(t))', PURPLE, 480, 320),
        ('TERMINATED', '终止\n(run 退出)', GRAY, 280, 360),
    ]
    for key, label, c, x, y in states:
        parts.append(f'<rect x="{x}" y="{y}" width="140" height="58" rx="10" '
                     f'fill="{c}22" stroke="{c}" stroke-width="2"/>')
        parts.append(f'<text x="{x + 70}" y="{y + 22}" font-size="13" fill="{c}" '
                     f'text-anchor="middle" font-weight="700">{esc(key)}</text>')
        parts.append(f'<text x="{x + 70}" y="{y + 42}" font-size="10" fill="#546E7A" '
                     f'text-anchor="middle">{esc(label)}</text>')
    # 状态迁移
    trans = [
        (220, 229, 280, 159, 'start()'),
        (420, 159, 480, 229, '等锁'),
        (620, 159, 620, 229, ''),
        (550, 258, 480, 320, 'sleep(t)'),
        (480, 320, 280, 360, 'run 结束'),
        (280, 360, 220, 320, ''),
        (350, 159, 350, 130, 'yield'),
    ]
    for (x1, y1, x2, y2, lab) in trans:
        parts.append(arrow(x1, y1, x2, y2, label=lab, dashed=False))
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_thread_pool(title, essence, body_top=110):
    """线程池工作流。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    # 任务入口
    parts.append(box(60, body_top + 40, 130, 50, '提交任务\nexecute()', fill=GREEN + '22', stroke=GREEN, font_size=13))
    # 核心
    parts.append(box(240, body_top + 40, 130, 50, '核心线程\n(corePoolSize)', fill=BLUE + '22', stroke=BLUE, font_size=13))
    parts.append(arrow(190, body_top + 65, 240, body_top + 65, label='有空位'))
    # 队列
    parts.append(box(420, body_top + 40, 130, 50, '阻塞队列\nBlockingQueue', fill=ORANGE + '22', stroke=ORANGE, font_size=13))
    parts.append(arrow(370, body_top + 65, 420, body_top + 65, label='核心满'))
    # 最大线程
    parts.append(box(600, body_top + 40, 140, 50, '非核心线程\n(maxPoolSize)', fill=PURPLE + '22', stroke=PURPLE, font_size=13))
    parts.append(arrow(550, body_top + 65, 600, body_top + 65, label='队列满'))
    # 拒绝
    parts.append(box(600, body_top + 120, 140, 50, '拒绝策略\nRejectedHandler', fill=RED + '22', stroke=RED, font_size=13))
    parts.append(arrow(670, body_top + 90, 670, body_top + 120, label='都满'))
    # 底部参数说明
    parts.append(f'<rect x="60" y="{body_top + 200}" width="680" height="120" rx="8" '
                 f'fill="#FAFAFA" stroke="{GRAY}" stroke-width="1"/>')
    parts.append(f'<text x="80" y="{body_top + 224}" font-size="13" fill="{GRAY}" font-weight="700">7 大核心参数</text>')
    params = ['corePoolSize 核心线程数', 'maxPoolSize 最大线程数', 'keepAliveSeconds 空闲存活',
              'workQueue 工作队列', 'threadFactory 线程工厂', 'rejectedHandler 拒绝策略', 'unit 时间单位']
    for i, p in enumerate(params):
        col = i % 3
        row = i // 3
        x = 80 + col * 230
        y = body_top + 252 + row * 28
        parts.append(f'<circle cx="{x}" cy="{y - 4}" r="4" fill="{PALETTE[i]}"/>')
        parts.append(f'<text x="{x + 12}" y="{y}" font-size="12" fill="#37474F">{esc(p)}</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_hashmap(title, essence, body_top=110):
    """HashMap 数组+链表+红黑树。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    # 桶数组
    parts.append(section_label(60, body_top + 16, 'HashMap = 数组(桶) + 链表 + 红黑树', BLUE))
    bucket_x = 80
    for i in range(6):
        y = body_top + 40 + i * 56
        parts.append(f'<rect x="{bucket_x}" y="{y}" width="100" height="44" rx="6" '
                     f'fill="{BLUE}22" stroke="{BLUE}" stroke-width="1.5"/>')
        parts.append(f'<text x="{bucket_x + 50}" y="{y + 27}" font-size="13" fill="{BLUE}" '
                     f'text-anchor="middle" font-weight="700">桶[{i}]</text>')
    # 链表（第 2 个桶）
    chain_y = body_top + 40 + 1 * 56 + 22
    for k in range(3):
        x = 220 + k * 120
        parts.append(box(x, chain_y - 22, 110, 44, 'Node\nK=V', fill='#FFFFFF', stroke=GREEN, font_size=12))
        if k > 0:
            parts.append(arrow(x - 10, chain_y, x, chain_y))
    # 红黑树（第 5 个桶）
    tree_y = body_top + 40 + 4 * 56 + 22
    parts.append(box(220, tree_y - 22, 110, 44, '链表>8\n&amp; 总数≥64', fill=ORANGE + '22', stroke=ORANGE, font_size=12))
    parts.append(arrow(330, tree_y, 360, tree_y, label='树化'))
    parts.append(box(360, tree_y - 22, 130, 44, '红黑树\nO(logN)', fill=RED + '22', stroke=RED, font_size=12))
    # 右侧要点
    parts.append(f'<rect x="540" y="{body_top + 30}" width="220" height="320" rx="8" '
                 f'fill="#FFFFFF" stroke="{PURPLE}" stroke-width="1.5"/>')
    parts.append(f'<text x="650" y="{body_top + 56}" font-size="14" fill="{PURPLE}" '
                 f'text-anchor="middle" font-weight="700">核心要点</text>')
    notes = ['初始容量 16', '负载因子 0.75', '扩容：容量翻倍', '链表→树：>8 & ≥64', '树→链表：≤6',
             'hash = (h=key.hashCode())^h>>>16', '定位：(n-1) & hash', 'JDK8 起改为尾插法']
    for i, n in enumerate(notes):
        yy = body_top + 80 + i * 32
        parts.append(f'<circle cx="558" cy="{yy - 4}" r="4" fill="{PALETTE[i % 6]}"/>')
        for j, ln in enumerate(wrap_text(n, 22)):
            parts.append(f'<text x="568" y="{yy + j * 14}" font-size="12" fill="#37474F">{esc(ln)}</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_three_way_handshake(title, essence, body_top=110):
    """TCP 三次握手时序图。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    # 两条生命线
    parts.append(f'<line x1="200" y1="{body_top + 30}" x2="200" y2="450" stroke="{BLUE}" stroke-width="2" stroke-dasharray="4,3"/>')
    parts.append(f'<line x1="600" y1="{body_top + 30}" x2="600" y2="450" stroke="{ORANGE}" stroke-width="2" stroke-dasharray="4,3"/>')
    parts.append(f'<rect x="130" y="{body_top + 6}" width="140" height="38" rx="8" fill="{BLUE}"/>')
    parts.append(f'<text x="200" y="{body_top + 30}" font-size="14" fill="#FFFFFF" text-anchor="middle" font-weight="700">Client 客户端</text>')
    parts.append(f'<rect x="530" y="{body_top + 6}" width="140" height="38" rx="8" fill="{ORANGE}"/>')
    parts.append(f'<text x="600" y="{body_top + 30}" font-size="14" fill="#FFFFFF" text-anchor="middle" font-weight="700">Server 服务端</text>')
    # 三次握手
    msgs = [
        (body_top + 80, 600, 200, GREEN, 'SYN=1, seq=x', 'CLOSED → SYN_SENT'),
        (body_top + 160, 200, 600, ORANGE, 'SYN=1, ACK=1, seq=y, ack=x+1', 'LISTEN → SYN_RCVD'),
        (body_top + 240, 600, 200, BLUE, 'ACK=1, seq=x+1, ack=y+1', 'ESTABLISHED'),
    ]
    for y, x1, x2, c, label, state in msgs:
        parts.append(arrow(x1, y, x2, y, color=c))
        parts.append(f'<text x="400" y="{y - 8}" font-size="12" fill="{c}" text-anchor="middle" font-weight="700">{esc(label)}</text>')
        parts.append(f'<text x="400" y="{y + 18}" font-size="11" fill="{GRAY}" text-anchor="middle">{esc(state)}</text>')
    # 状态结果
    parts.append(f'<rect x="120" y="{body_top + 290}" width="160" height="38" rx="8" fill="{GREEN}22" stroke="{GREEN}"/>')
    parts.append(f'<text x="200" y="{body_top + 314}" font-size="13" fill="{GREEN}" text-anchor="middle" font-weight="700">ESTABLISHED</text>')
    parts.append(f'<rect x="520" y="{body_top + 290}" width="160" height="38" rx="8" fill="{GREEN}22" stroke="{GREEN}"/>')
    parts.append(f'<text x="600" y="{body_top + 314}" font-size="13" fill="{GREEN}" text-anchor="middle" font-weight="700">ESTABLISHED</text>')
    parts.append(f'<text x="400" y="{body_top + 360}" font-size="13" fill="{PURPLE}" text-anchor="middle" font-weight="700">'
                 f'三次握手 = 双方确认收发能力，防止历史连接</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_four_wave(title, essence, body_top=110):
    """TCP 四次挥手。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    parts.append(f'<line x1="200" y1="{body_top + 30}" x2="200" y2="450" stroke="{BLUE}" stroke-width="2" stroke-dasharray="4,3"/>')
    parts.append(f'<line x1="600" y1="{body_top + 30}" x2="600" y2="450" stroke="{ORANGE}" stroke-width="2" stroke-dasharray="4,3"/>')
    parts.append(f'<rect x="130" y="{body_top + 6}" width="140" height="38" rx="8" fill="{BLUE}"/>')
    parts.append(f'<text x="200" y="{body_top + 30}" font-size="14" fill="#FFFFFF" text-anchor="middle" font-weight="700">主动方</text>')
    parts.append(f'<rect x="530" y="{body_top + 6}" width="140" height="38" rx="8" fill="{ORANGE}"/>')
    parts.append(f'<text x="600" y="{body_top + 30}" font-size="14" fill="#FFFFFF" text-anchor="middle" font-weight="700">被动方</text>')
    msgs = [
        (body_top + 80, 200, 600, RED, 'FIN=1, seq=u'),
        (body_top + 150, 600, 200, ORANGE, 'ACK=1, ack=u+1  (被动方进入 CLOSE_WAIT)'),
        (body_top + 230, 600, 200, PURPLE, 'FIN=1, seq=w  (被动方处理完毕)'),
        (body_top + 300, 200, 600, BLUE, 'ACK=1, ack=w+1  (TIME_WAIT 2MSL 后关闭)'),
    ]
    for y, x1, x2, c, label in msgs:
        parts.append(arrow(x1, y, x2, y, color=c))
        parts.append(f'<text x="400" y="{y - 8}" font-size="12" fill="{c}" text-anchor="middle" font-weight="700">{esc(label)}</text>')
    parts.append(f'<text x="400" y="{body_top + 360}" font-size="13" fill="{GREEN}" text-anchor="middle" font-weight="700">'
                 f'四次挥手 = 全双工关闭，TIME_WAIT 防止报文滞留</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_https(title, essence, body_top=110):
    """HTTPS 握手 + 混合加密。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    # 两阶段
    parts.append(f'<rect x="40" y="{body_top}" width="350" height="350" rx="10" '
                 f'fill="{BLUE}11" stroke="{BLUE}" stroke-width="2"/>')
    parts.append(f'<text x="215" y="{body_top + 28}" font-size="15" fill="{BLUE}" '
                 f'text-anchor="middle" font-weight="700">① TLS 握手（非对称加密）</text>')
    handshake = ['ClientHello: SSL版本+随机数+加密套件',
                 'ServerHello: 选定套件+证书+随机数',
                 '客户端验证证书（CA 签名链）',
                 '客户端生成 pre-master，用公钥加密',
                 '双方基于 3 个随机数导出会话密钥']
    for i, h in enumerate(handshake):
        y = body_top + 56 + i * 50
        parts.append(f'<rect x="56" y="{y}" width="318" height="40" rx="6" '
                     f'fill="#FFFFFF" stroke="{BLUE}" stroke-width="1.5"/>')
        parts.append(f'<circle cx="74" cy="{y + 20}" r="11" fill="{BLUE}"/>')
        parts.append(f'<text x="74" y="{y + 24}" font-size="11" fill="#FFFFFF" text-anchor="middle" font-weight="700">{i+1}</text>')
        for j, ln in enumerate(wrap_text(h, 38)):
            parts.append(f'<text x="92" y="{y + 25 + j * 13}" font-size="11" fill="#263238">{esc(ln)}</text>')
    # 右侧：对称传输
    parts.append(f'<rect x="410" y="{body_top}" width="350" height="350" rx="10" '
                 f'fill="{GREEN}11" stroke="{GREEN}" stroke-width="2"/>')
    parts.append(f'<text x="585" y="{body_top + 28}" font-size="15" fill="{GREEN}" '
                 f'text-anchor="middle" font-weight="700">② 数据传输（对称加密）</text>')
    parts.append(box(450, body_top + 60, 130, 50, '客户端', fill=GREEN + '22', stroke=GREEN, font_size=14))
    parts.append(box(620, body_top + 60, 130, 50, '服务器', fill=ORANGE + '22', stroke=ORANGE, font_size=14))
    parts.append(arrow(580, body_top + 95, 620, body_top + 95, label='密文 AES'))
    parts.append(arrow(620, body_top + 120, 580, body_top + 120, label='密文 AES'))
    parts.append(f'<rect x="430" y="{body_top + 170}" width="310" height="160" rx="8" '
                 f'fill="#FFFFFF" stroke="{PURPLE}" stroke-width="1.5"/>')
    parts.append(f'<text x="585" y="{body_top + 195}" font-size="13" fill="{PURPLE}" '
                 f'text-anchor="middle" font-weight="700">三大特性</text>')
    for i, (n, c) in enumerate([('机密性：加密防窃听', BLUE), ('完整性：MAC 防篡改', GREEN),
                                 ('真实性：证书防冒充', ORANGE), ('默认端口：443', PURPLE)]):
        y = body_top + 220 + i * 28
        parts.append(f'<circle cx="450" cy="{y - 4}" r="5" fill="{c}"/>')
        parts.append(f'<text x="464" y="{y}" font-size="12" fill="#37474F">{esc(n)}</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_concurrence(title, essence, body_top=110):
    """并发基础：进程 vs 线程 vs 协程 对比。"""
    return tpl_compare(title, essence, [
        ('进程 Process', ['系统资源分配单位', '独立内存空间', '切换成本高', '通信：管道/消息队列', '健壮：一进程崩不影响其他']),
        ('线程 Thread', ['CPU 调度单位', '共享进程内存', '切换中等', '通信：共享变量+同步', '需加锁防竞态']),
        ('协程 Coroutine', ['用户态轻量级线程', '单线程内多任务', '切换成本极低', '通信：Channel/共享', '需主动 yield 让出']),
    ], body_top=body_top)

def tpl_lock(title, essence, body_top=110):
    """锁分类树。"""
    return tpl_layers(title, essence, [
        ('乐观 vs 悲观', ['乐观锁：CAS / 版本号（适合读多）   悲观锁：synchronized / ReentrantLock（适合写多）']),
        ('公平 vs 非公平', ['公平锁：FIFO 排队，无饥饿   非公平锁：可插队，吞吐量高']),
        ('独占 vs 共享', ['独占锁：ReentrantLock / synchronized   共享锁：ReadWriteLock / Semaphore']),
        ('可重入 vs 不可重入', ['可重入锁：同线程可多次获取，避免死锁   不可重入：再次获取会自死锁']),
        ('自旋锁', ['忙等待不阻塞，适合临界区短   自适应自旋：JVM 根据历史决定时长']),
    ], body_top=body_top)

def tpl_synchronized(title, essence, body_top=110):
    """synchronized 锁升级。"""
    return tpl_pipeline(title, essence, [
        '无锁状态\nnew',
        '偏向锁\n单线程访问',
        '轻量级锁\nCAS 自旋\n多线程交替',
        '重量级锁\nOS Mutex\n竞争激烈',
    ], body_top=body_top, colors=[GREEN, BLUE, ORANGE, RED])

def tpl_aqs(title, essence, body_top=110):
    """AQS 同步器框架。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(f'<rect x="60" y="{body_top}" width="680" height="60" rx="8" fill="{BLUE}" />')
    parts.append(f'<text x="400" y="{body_top + 38}" font-size="17" fill="#FFFFFF" '
                 f'text-anchor="middle" font-weight="700">AQS = state + CLH 双向 FIFO 队列</text>')
    # state
    parts.append(box(80, body_top + 90, 240, 70, 'volatile int state\n(同步状态)', fill=ORANGE + '22', stroke=ORANGE, font_size=14))
    # CAS
    parts.append(box(360, body_top + 90, 240, 70, 'CAS 修改 state\n(compareAndSet)', fill=GREEN + '22', stroke=GREEN, font_size=14))
    parts.append(arrow(320, body_top + 125, 360, body_top + 125))
    # CLH 队列
    parts.append(f'<rect x="60" y="{body_top + 190}" width="680" height="170" rx="10" '
                 f'fill="#FFFFFF" stroke="{PURPLE}" stroke-width="2"/>')
    parts.append(f'<text x="80" y="{body_top + 214}" font-size="14" fill="{PURPLE}" font-weight="700">CLH 等待队列（双向链表，FIFO）</text>')
    for i, (n, c, st) in enumerate([('head\n(哨兵)', GRAY, ''), ('Node 1\n线程A', BLUE, '前驱唤醒'),
                                     ('Node 2\n线程B', ORANGE, 'park 阻塞'), ('Node 3\n线程C', RED, 'park 阻塞')]):
        x = 100 + i * 160
        parts.append(box(x, body_top + 240, 140, 70, n, fill=c + '22', stroke=c, font_size=13))
        if st:
            parts.append(f'<text x="{x + 70}" y="{body_top + 332}" font-size="10" fill="{c}" '
                         f'text-anchor="middle">{esc(st)}</text>')
        if i > 0:
            parts.append(arrow(x - 20, body_top + 275, x, body_top + 275))
            parts.append(arrow(x, body_top + 285, x - 20, body_top + 285, color=GRAY, dashed=True))
    parts.append(f'<text x="400" y="{body_top + 384}" font-size="12" fill="{GRAY}" text-anchor="middle">'
                 f'实现：ReentrantLock / Semaphore / CountDownLatch / ReentrantReadWriteLock</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_volatile(title, essence, body_top=110):
    """volatile 内存语义。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(f'<rect x="60" y="{body_top}" width="680" height="60" rx="8" fill="{RED}"/>')
    parts.append(f'<text x="400" y="{body_top + 38}" font-size="16" fill="#FFFFFF" text-anchor="middle" font-weight="700">'
                 f'volatile 两大大语义：可见性 + 禁止指令重排（不保证原子性）</text>')
    # 三特性
    parts.append(box(60, body_top + 90, 220, 90, '可见性\n写后立刻刷主存\n读强制从主存读',
                     fill=GREEN + '22', stroke=GREEN, font_size=13))
    parts.append(box(290, body_top + 90, 220, 90, '禁止重排序\nMemory Barrier\nLoadLoad/StoreStore',
                     fill=BLUE + '22', stroke=BLUE, font_size=13))
    parts.append(box(520, body_top + 90, 220, 90, '不保证原子\ni++ 仍非原子\n需 AtomicXxx',
                     fill=ORANGE + '22', stroke=ORANGE, font_size=13))
    # JMM
    parts.append(f'<rect x="60" y="{body_top + 210}" width="680" height="160" rx="10" '
                 f'fill="#FFFFFF" stroke="{PURPLE}" stroke-width="2"/>')
    parts.append(f'<text x="400" y="{body_top + 234}" font-size="14" fill="{PURPLE}" '
                 f'text-anchor="middle" font-weight="700">JMM 内存模型视角</text>')
    # 线程A 工作内存
    parts.append(box(80, body_top + 250, 200, 50, '线程A 工作内存', fill='#FFFFFF', stroke=BLUE, font_size=12))
    parts.append(box(520, body_top + 250, 200, 50, '线程B 工作内存', fill='#FFFFFF', stroke=ORANGE, font_size=12))
    parts.append(box(300, body_top + 320, 200, 40, '主内存\nvolatile 变量',
                     fill=RED + '22', stroke=RED, font_size=12))
    parts.append(arrow(280, body_top + 275, 320, body_top + 340, color=GREEN, label='write 刷主存'))
    parts.append(arrow(480, body_top + 340, 520, body_top + 275, color=GREEN, label='read 读主存'))
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_spring_ioc(title, essence, body_top=110):
    """Spring IOC 容器。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    # 容器中心
    parts.append(f'<rect x="280" y="{body_top + 80}" width="240" height="100" rx="12" fill="{GREEN}"/>')
    parts.append(f'<text x="400" y="{body_top + 120}" font-size="18" fill="#FFFFFF" text-anchor="middle" font-weight="700">Spring IOC 容器</text>')
    parts.append(f'<text x="400" y="{body_top + 148}" font-size="13" fill="#FFFFFF" text-anchor="middle">ApplicationContext</text>')
    # 上游：组件
    for i, (n, c) in enumerate([('@Controller', BLUE), ('@Service', ORANGE), ('@Repository', PURPLE), ('@Component', RED)]):
        x = 60 + i * 175
        parts.append(box(x, body_top + 10, 160, 50, n, fill=c + '22', stroke=c, font_size=13))
        parts.append(arrow(x + 80, body_top + 60, 400, body_top + 80, color=c, dashed=True))
        parts.append(f'<text x="{x + 80}" y="{body_top + 76}" font-size="10" fill="{c}" text-anchor="middle">注册</text>')
    # 下游：使用方
    parts.append(box(310, body_top + 220, 180, 50, '调用方\n@Inject/@Autowired',
                     fill=GRAY + '22', stroke=GRAY, font_size=13))
    parts.append(arrow(400, body_top + 180, 400, body_top + 220, label='注入'))
    # 流程
    parts.append(f'<text x="400" y="{body_top + 304}" font-size="13" fill="{PURPLE}" text-anchor="middle" font-weight="700">'
                 f'IOC = Inversion of Control：对象创建权交容器</text>')
    flow = ['① 启动扫描 @Component', '② 反射创建 Bean', '③ 依赖注入', '④ 初始化（@PostConstruct）', '⑤ 就绪可注入']
    for i, f in enumerate(flow):
        x = 60 + i * 142
        parts.append(box(x, body_top + 320, 132, 50, f, fill='#FFFFFF', stroke=PALETTE[i % 6], font_size=11))
        if i > 0:
            parts.append(arrow(x - 10, body_top + 345, x, body_top + 345, color=GRAY))
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_spring_aop(title, essence, body_top=110):
    """Spring AOP 切面。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    # 业务方法
    parts.append(box(300, body_top + 60, 200, 60, '目标方法\nUserService.addUser()',
                     fill=BLUE + '22', stroke=BLUE, font_size=13))
    # 五种通知
    advices = [
        ('@Before\n前置通知', GREEN, 60, body_top + 180),
        ('@Around\n环绕通知', PURPLE, 230, body_top + 180),
        ('@AfterReturning\n返回通知', ORANGE, 400, body_top + 180),
        ('@AfterThrowing\n异常通知', RED, 570, body_top + 180),
        ('@After\n后置通知(终)', GRAY, 60, body_top + 280),
    ]
    for n, c, x, y in advices:
        parts.append(box(x, y, 170, 70, n, fill=c + '22', stroke=c, font_size=12))
        parts.append(arrow(x + 85, y + 70, 400, body_top + 122, color=c, dashed=True, label=''))
    # 底部术语
    parts.append(f'<rect x="60" y="{body_top + 280}" width="680" height="110" rx="10" '
                 f'fill="#FFFFFF" stroke="{GRAY}" stroke-width="1.5"/>')
    parts.append(f'<text x="80" y="{body_top + 304}" font-size="13" fill="{GRAY}" font-weight="700">核心术语</text>')
    terms = ['Aspect 切面 = 通知+切入点', 'Pointcut 切入点 = 哪些方法',
             'JoinPoint 连接点 = 方法执行点', 'Weaving 织入 = 编译/类加载/运行期',
             '底层：JDK 动态代理(接口) / CGLIB(类)']
    for i, t in enumerate(terms):
        col = i % 2
        row = i // 2
        x = 80 + col * 340
        y = body_top + 326 + row * 24
        parts.append(f'<circle cx="{x}" cy="{y - 4}" r="4" fill="{PALETTE[i]}"/>')
        parts.append(f'<text x="{x + 12}" y="{y}" font-size="12" fill="#37474F">{esc(t)}</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_spring_bean(title, essence, body_top=110):
    """Spring Bean 生命周期。"""
    return tpl_pipeline(title, essence, [
        '实例化\nInstantiationException',
        '属性赋值\npopulateBean\n(DI 注入)',
        'Aware 回调\nBeanNameAware\nBeanFactoryAware',
        'BeanPostProcessor\nbefore',
        '初始化\n@PostConstruct\ninit-method',
        'BeanPostProcessor\nafter (AOP 代理)',
        '使用',
        '销毁\n@PreDestroy\ndestroy-method',
    ], body_top=body_top)

def tpl_spring_boot(title, essence, body_top=110):
    """SpringBoot 自动装配。"""
    return tpl_pipeline(title, essence, [
        '@SpringBootApplication\n启动',
        '@EnableAutoConfiguration\n@Import(AutoConfigurationImportSelector)',
        '读取 META-INF/spring.factories\n(spring-boot 3: AutoConfiguration.imports)',
        '过滤 @Conditional\n条件装配',
        '满足条件 → 注册 Bean\n到容器',
        '用户配置优先\n(@ConditionalOnMissingBean)',
    ], body_top=body_top)

def tpl_transaction(title, essence, body_top=110):
    """事务 ACID + 隔离级别。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    # ACID
    parts.append(section_label(60, body_top + 16, 'ACID 四大特性', BLUE))
    acids = [
        ('A 原子性', '全部成功或全部回滚', GREEN),
        ('C 一致性', '数据约束不被破坏', BLUE),
        ('I 隔离性', '并发事务互不干扰', ORANGE),
        ('D 持久性', '提交后永久保存', PURPLE),
    ]
    for i, (n, d, c) in enumerate(acids):
        x = 60 + i * 175
        parts.append(f'<rect x="{x}" y="{body_top + 36}" width="160" height="80" rx="8" '
                     f'fill="{c}22" stroke="{c}" stroke-width="2"/>')
        parts.append(f'<text x="{x + 80}" y="{body_top + 64}" font-size="15" fill="{c}" '
                     f'text-anchor="middle" font-weight="700">{esc(n)}</text>')
        parts.append(f'<text x="{x + 80}" y="{body_top + 90}" font-size="11" fill="#37474F" '
                     f'text-anchor="middle">{esc(d)}</text>')
    # 隔离级别
    parts.append(section_label(60, body_top + 156, '四种隔离级别（→ 隔离性递增，性能递减）', PURPLE))
    isolations = [
        ('READ UNCOMMITTED', '读未提交', '脏读 / 不可重复读 / 幻读', RED),
        ('READ COMMITTED', '读已提交', '不可重复读 / 幻读', ORANGE),
        ('REPEATABLE READ', '可重复读\nMySQL 默认', '幻读', BLUE),
        ('SERIALIZABLE', '串行化', '无（性能最差）', GREEN),
    ]
    for i, (n, d, p, c) in enumerate(isolations):
        x = 60 + i * 175
        parts.append(f'<rect x="{x}" y="{body_top + 176}" width="160" height="100" rx="8" '
                     f'fill="{c}22" stroke="{c}" stroke-width="2"/>')
        parts.append(f'<text x="{x + 80}" y="{body_top + 198}" font-size="11" fill="{c}" '
                     f'text-anchor="middle" font-weight="700">{esc(n)}</text>')
        parts.append(f'<text x="{x + 80}" y="{body_top + 222}" font-size="13" fill="#263238" '
                     f'text-anchor="middle" font-weight="700">{esc(d)}</text>')
        parts.append(f'<text x="{x + 80}" y="{body_top + 248}" font-size="10" fill="#546E7A" '
                     f'text-anchor="middle">{esc(p)}</text>')
    # 传播行为
    parts.append(f'<text x="60" y="{body_top + 312}" font-size="13" fill="{GREEN}" font-weight="700">'
                 f'7 大传播行为：REQUIRED(默认) / REQUIRES_NEW / NESTED / SUPPORTS / NOT_SUPPORTED / NEVER / MANDATORY</text>')
    parts.append(f'<text x="60" y="{body_top + 338}" font-size="12" fill="{GRAY}">'
                 f'@Transactional 失效场景：非 public / 自调用 / 异常被吞 / 默认只回滚 RuntimeException</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_mybatis(title, essence, body_top=110):
    """MyBatis 流程。"""
    return tpl_pipeline(title, essence, [
        'SqlSessionFactory\nbuild(xml/注解)',
        'openSession()\n获取 SqlSession',
        'getMapper()\n动态代理 JDK',
        'MapperProxy.invoke()\n→ SqlSession',
        'Executor 执行\n(Batch/Reuse/Simple)',
        'StatementHandler\n处理 SQL 参数',
        'ResultSetHandler\n映射结果集 → POJO',
    ], body_top=body_top)

def tpl_redis_data_structure(title, essence, body_top=110):
    """Redis 5+ 数据结构。"""
    return tpl_layers(title, essence, [
        ('String 字符串', ['SDS 实现；set/get/incr；缓存/计数器/分布式锁']),
        ('Hash 哈希', ['field-value 表；hset/hget；存对象（用户信息）']),
        ('List 列表', ['双向链表/压缩列表；lpush/rpop；消息队列/最新 N 条']),
        ('Set 集合', ['元素唯一；sadd/sinter；标签/共同好友']),
        ('ZSet 有序集合', ['跳表+字典；zadd/zrange；排行榜/延时队列']),
        ('特殊：HyperLogLog/Bitmap/Geo/Stream', ['基数统计/位图/地理位置/消息流']),
    ], body_top=body_top)

def tpl_cache_pattern(title, essence, body_top=110):
    """缓存模式：Cache Aside / Read Through / Write Through / Write Behind。"""
    return tpl_compare(title, essence, [
        ('Cache Aside 旁路', ['最常用', '读：先查缓存，miss 查 DB 回填', '写：更新 DB，再删缓存', '问题：并发下短暂不一致']),
        ('Read/Write Through', ['缓存主导', '应用只操作缓存', '缓存同步写回 DB', '对应用透明']),
        ('Write Behind', ['异步回写', '写：只更新缓存', '后台批量刷 DB', '性能最高，可能丢数据']),
    ], body_top=body_top)

def tpl_mq(title, essence, body_top=110):
    """消息队列核心模型。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    # 生产者
    parts.append(box(50, body_top + 90, 130, 60, 'Producer\n生产者', fill=GREEN + '22', stroke=GREEN, font_size=14))
    # 交换器
    parts.append(box(260, body_top + 90, 130, 60, 'Exchange\n交换器', fill=BLUE + '22', stroke=BLUE, font_size=14))
    parts.append(arrow(180, body_top + 120, 260, body_top + 120, label='publish'))
    # 队列
    parts.append(box(470, body_top + 50, 110, 40, 'Queue 1', fill=ORANGE + '22', stroke=ORANGE, font_size=12))
    parts.append(box(470, body_top + 110, 110, 40, 'Queue 2', fill=ORANGE + '22', stroke=ORANGE, font_size=12))
    parts.append(box(470, body_top + 170, 110, 40, 'Queue 3', fill=ORANGE + '22', stroke=ORANGE, font_size=12))
    for yy in [70, 130, 190]:
        parts.append(arrow(390, body_top + 120, 470, body_top + yy, color=ORANGE, dashed=True, label=''))
    # 消费者
    parts.append(box(640, body_top + 90, 130, 60, 'Consumer\n消费者', fill=PURPLE + '22', stroke=PURPLE, font_size=14))
    for yy in [70, 130, 190]:
        parts.append(arrow(580, body_top + yy, 640, body_top + 120, color=PURPLE, dashed=True, label=''))
    # 4 种交换器
    parts.append(f'<rect x="50" y="{body_top + 250}" width="720" height="160" rx="10" '
                 f'fill="#FFFFFF" stroke="{GRAY}" stroke-width="1.5"/>')
    parts.append(f'<text x="70" y="{body_top + 274}" font-size="13" fill="{GRAY}" font-weight="700">4 种 Exchange 类型</text>')
    types = [
        ('Direct', '精确匹配 routing key', GREEN),
        ('Topic', '* 单词 / # 多单词', BLUE),
        ('Fanout', '广播所有队列', ORANGE),
        ('Headers', '匹配 header 键值', PURPLE),
    ]
    for i, (n, d, c) in enumerate(types):
        x = 70 + i * 175
        parts.append(f'<rect x="{x}" y="{body_top + 290}" width="160" height="100" rx="6" '
                     f'fill="{c}22" stroke="{c}" stroke-width="1.5"/>')
        parts.append(f'<text x="{x + 80}" y="{body_top + 318}" font-size="14" fill="{c}" '
                     f'text-anchor="middle" font-weight="700">{esc(n)}</text>')
        for j, ln in enumerate(wrap_text(d, 18)):
            parts.append(f'<text x="{x + 80}" y="{body_top + 348 + j * 16}" font-size="11" fill="#37474F" '
                         f'text-anchor="middle">{esc(ln)}</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_design_pattern(title, essence, body_top=110):
    """设计模式分类树。"""
    return tpl_layers(title, essence, [
        ('创建型（5 种）', ['单例 / 工厂方法 / 抽象工厂 / 建造者 / 原型']),
        ('结构型（7 种）', ['适配器 / 装饰器 / 代理 / 外观 / 桥接 / 组合 / 享元']),
        ('行为型（11 种）', ['策略 / 模板方法 / 观察者 / 责任链 / 命令 / 状态 / 迭代器 / 中介者 / 备忘录 / 访问者 / 解释器']),
        ('6 大原则', ['单一职责 / 里氏替换 / 依赖倒置 / 接口隔离 / 迪米特 / 开闭原则']),
    ], body_top=body_top)

def tpl_singleton(title, essence, body_top=110):
    """单例模式 5 种写法。"""
    return tpl_compare(title, essence, [
        ('饿汉式', ['类加载即创建', '天然线程安全', '无法延迟加载', '可能浪费资源']),
        ('懒汉式(DCL)', ['双重检查锁', 'volatile 防指令重排', '延迟加载', '推荐写法']),
        ('静态内部类', ['利用类加载机制', '天然线程安全', '延迟加载', '推荐写法']),
        ('枚举', ['Effective Java 推荐', '天然防反射', '天然防序列化', '最简洁安全']),
    ], body_top=body_top)

def tpl_io_model(title, essence, body_top=110):
    """IO 模型 4 种。"""
    return tpl_compare(title, essence, [
        ('BIO 同步阻塞', ['一连接一线程', 'accept()/read() 阻塞', '连接数少', 'JDK 1.4 前']),
        ('NIO 同步非阻塞', ['多路复用 Selector', 'Channel + Buffer', '一个线程管多连接', 'JDK 1.4']),
        ('IO 多路复用', ['epoll/kqueue (OS 级)', '事件驱动', 'Redis/Nginx 用', '高性能首选']),
        ('AIO 异步', ['真正的异步回调', 'Windows IOCP', 'Linux 伪 AIO', 'JDK 1.7+']),
    ], body_top=body_top)

def tpl_class_loader(title, essence, body_top=110):
    """类加载器层级 + 双亲委派。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    # 层级
    layers = [
        ('Bootstrap ClassLoader', '加载 rt.jar (JAVA_HOME/lib)', GRAY, 320),
        ('Extension ClassLoader', '加载 ext/*.jar (JAVA_HOME/lib/ext)', PURPLE, 280),
        ('Application ClassLoader', '加载 classpath / 用户类', BLUE, 240),
        ('Custom ClassLoader', '自定义 (tomcat/热部署)', ORANGE, 200),
    ]
    for i, (n, d, c, w) in enumerate(layers):
        x = (800 - w) // 2
        y = body_top + 20 + i * 56
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="46" rx="6" fill="{c}22" stroke="{c}" stroke-width="2"/>')
        parts.append(f'<text x="400" y="{y + 20}" font-size="14" fill="{c}" text-anchor="middle" font-weight="700">{esc(n)}</text>')
        parts.append(f'<text x="400" y="{y + 38}" font-size="11" fill="#546E7A" text-anchor="middle">{esc(d)}</text>')
    # 右侧：双亲委派
    parts.append(f'<rect x="540" y="{body_top + 250}" width="220" height="160" rx="8" '
                 f'fill="#FFFFFF" stroke="{GREEN}" stroke-width="1.5"/>')
    parts.append(f'<text x="650" y="{body_top + 276}" font-size="13" fill="{GREEN}" '
                 f'text-anchor="middle" font-weight="700">双亲委派模型</text>')
    for i, t in enumerate(['① 自底向上询问', '② 父加载器先加载', '③ 父加载不到才自己加载', '④ 防止核心类被篡改', '⑤ Tomcat 打破此模型']):
        y = body_top + 300 + i * 22
        parts.append(f'<circle cx="558" cy="{y - 4}" r="4" fill="{GREEN}"/>')
        parts.append(f'<text x="572" y="{y}" font-size="12" fill="#37474F">{esc(t)}</text>')
    # 类加载过程
    parts.append(section_label(60, body_top + 270, '类加载过程', BLUE))
    for i, n in enumerate(['加载', '验证', '准备', '解析', '初始化']):
        x = 60 + i * 90
        parts.append(box(x, body_top + 290, 80, 50, n, fill=PALETTE[i] + '22', stroke=PALETTE[i], font_size=12))
        if i > 0:
            parts.append(arrow(x - 10, body_top + 315, x, body_top + 315, color=GRAY))
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_concurrence_map(title, essence, body_top=110):
    """ConcurrentHashMap 分段/Node。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(f'<rect x="50" y="{body_top}" width="700" height="50" rx="8" fill="{BLUE}"/>')
    parts.append(f'<text x="400" y="{body_top + 32}" font-size="15" fill="#FFFFFF" text-anchor="middle" font-weight="700">'
                 f'JDK 7: Segment 分段锁  |  JDK 8: Node 数组 + CAS + synchronized 锁桶</text>')
    # JDK7
    parts.append(f'<rect x="50" y="{body_top + 70}" width="340" height="180" rx="8" '
                 f'fill="{ORANGE}11" stroke="{ORANGE}" stroke-width="2"/>')
    parts.append(f'<text x="220" y="{body_top + 96}" font-size="14" fill="{ORANGE}" '
                 f'text-anchor="middle" font-weight="700">JDK 7：Segment[]</text>')
    parts.append(f'<text x="220" y="{body_top + 122}" font-size="11" fill="#546E7A" text-anchor="middle">'
                 f'默认 16 段，每段独立锁（并发度=段数）</text>')
    for i in range(4):
        x = 70 + i * 78
        parts.append(box(x, body_top + 140, 70, 50, f'Seg{i}\nReentrantLock', fill='#FFFFFF', stroke=ORANGE, font_size=10))
        parts.append(box(x, body_top + 200, 70, 36, 'HashEntry[]', fill=ORANGE + '22', stroke=ORANGE, font_size=10))
    # JDK8
    parts.append(f'<rect x="410" y="{body_top + 70}" width="340" height="180" rx="8" '
                 f'fill="{GREEN}11" stroke="{GREEN}" stroke-width="2"/>')
    parts.append(f'<text x="580" y="{body_top + 96}" font-size="14" fill="{GREEN}" '
                 f'text-anchor="middle" font-weight="700">JDK 8：Node[]</text>')
    parts.append(f'<text x="580" y="{body_top + 122}" font-size="11" fill="#546E7A" text-anchor="middle">'
                 f'锁粒度细化到桶；CAS 写入 + synchronized 锁头节点</text>')
    for i in range(6):
        x = 430 + i * 50
        parts.append(box(x, body_top + 140, 42, 36, f'[{i}]', fill=GREEN + '22', stroke=GREEN, font_size=9))
    parts.append(f'<text x="580" y="{body_top + 200}" font-size="11" fill="{GREEN}" text-anchor="middle">'
                 f'链表>8 &amp; 数组≥64 → 红黑树 (TreeBin)</text>')
    parts.append(f'<text x="580" y="{body_top + 222}" font-size="11" fill="{GREEN}" text-anchor="middle">'
                 f'sizeCtl 控制；transfer 多线程辅助扩容</text>')
    # 底部要点
    parts.append(f'<text x="60" y="{body_top + 280}" font-size="13" fill="{PURPLE}" font-weight="700">'
                 f'核心 API：putIfAbsent / computeIfAbsent / sizeCtl / ForwardingNode</text>')
    parts.append(f'<text x="60" y="{body_top + 304}" font-size="12" fill="{GRAY}">'
                 f'读操作无锁(volatile Node) / 写 CAS+sync / 扩容并发迁移 / size 弱一致</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_jvm_class_exec(title, essence, body_top=110):
    """Java 代码执行流程：.java -> bytecode -> JVM -> 机器码。"""
    return tpl_pipeline(title, essence, [
        '源码\nHello.java',
        'javac 编译\n→ Hello.class\n(字节码)',
        'ClassLoader\n加载到内存',
        '字节码校验\n+ 链接',
        '解释器\n逐条解释执行',
        'JIT (HotSpot)\n热点代码编译\n为机器码',
        'OS 执行\n机器码',
    ], body_top=body_top)

def tpl_cas(title, essence, body_top=110):
    """CAS 原理 + ABA 问题。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    parts.append(box(280, body_top + 20, 240, 60, 'CAS(V, Expected, New)\nCompare And Swap', fill=BLUE, stroke=ORANGE, font_size=15))
    # 三步
    steps = [
        ('① 读取 V\n当前内存值', GREEN, 60),
        ('② 比较 V == Expected?', ORANGE, 280),
        ('③ 相等 → 写入 New\n不等 → 重试/放弃', RED, 500),
    ]
    for n, c, x in steps:
        parts.append(box(x, body_top + 110, 200, 80, n, fill=c + '22', stroke=c, font_size=13))
    parts.append(arrow(260, body_top + 150, 280, body_top + 150))
    parts.append(arrow(480, body_top + 150, 500, body_top + 150))
    # ABA
    parts.append(f'<rect x="60" y="{body_top + 230}" width="680" height="200" rx="10" '
                 f'fill="{RED}11" stroke="{RED}" stroke-width="2"/>')
    parts.append(f'<text x="400" y="{body_top + 256}" font-size="15" fill="{RED}" '
                 f'text-anchor="middle" font-weight="700">ABA 问题与解决</text>')
    flow = ['A', 'B', 'A', 'CAS 仍成功\n(虽经历变化)', 'AtomicStampedReference\n加版本号解决']
    for i, t in enumerate(flow):
        x = 80 + i * 130
        c = PALETTE[i % 6]
        parts.append(box(x, body_top + 280, 120, 56, t, fill=c + '22', stroke=c, font_size=12))
        if i > 0:
            parts.append(arrow(x - 10, body_top + 308, x, body_top + 308, color=RED))
    parts.append(f'<text x="400" y="{body_top + 400}" font-size="12" fill="{GRAY}" text-anchor="middle">'
                 f'底层：Unsafe.compareAndSwap*  |  应用：AtomicInteger/Long/Reference</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_threadlocal(title, essence, body_top=110):
    """ThreadLocal 内存模型。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    # 两个 Thread
    for ti, (tn, c) in enumerate([('Thread A', BLUE), ('Thread B', ORANGE)]):
        x = 60 + ti * 360
        parts.append(f'<rect x="{x}" y="{body_top}" width="320" height="180" rx="10" '
                     f'fill="{c}11" stroke="{c}" stroke-width="2"/>')
        parts.append(f'<text x="{x + 160}" y="{body_top + 28}" font-size="15" fill="{c}" '
                     f'text-anchor="middle" font-weight="700">{esc(tn)}</text>')
        # ThreadLocalMap
        parts.append(box(x + 30, body_top + 50, 260, 50, 'ThreadLocalMap\n(每个线程独有)',
                         fill='#FFFFFF', stroke=c, font_size=12))
        # Entry[]
        for i in range(3):
            ex = x + 30 + i * 80
            parts.append(box(ex, body_top + 120, 75, 50, f'Entry\nkey=TL_{i+1}\nvalue=V', fill=c + '22', stroke=c, font_size=10))
    # 关键说明
    parts.append(f'<rect x="60" y="{body_top + 210}" width="680" height="220" rx="10" '
                 f'fill="#FFFFFF" stroke="{PURPLE}" stroke-width="1.5"/>')
    parts.append(f'<text x="400" y="{body_top + 236}" font-size="14" fill="{PURPLE}" '
                 f'text-anchor="middle" font-weight="700">关键特性</text>')
    feats = [
        ('数据隔离', GREEN, '每个线程独立副本，无并发问题'),
        ('Entry 弱引用 Key', BLUE, 'ThreadLocal 被 GC 后 key=null'),
        ('内存泄漏风险', RED, 'value 强引用，需 remove() 释放'),
        ('InheritableThreadLocal', ORANGE, '父子线程可继承值'),
        ('典型应用', PURPLE, 'SimpleDateFormat / 数据库连接 / 用户上下文'),
    ]
    for i, (n, c, d) in enumerate(feats):
        col = i % 2
        row = i // 2
        x = 80 + col * 340
        y = body_top + 260 + row * 56
        parts.append(f'<rect x="{x}" y="{y - 16}" width="320" height="44" rx="6" fill="{c}22" stroke="{c}" stroke-width="1.5"/>')
        parts.append(f'<text x="{x + 14}" y="{y + 2}" font-size="12" fill="{c}" font-weight="700">{esc(n)}</text>')
        parts.append(f'<text x="{x + 14}" y="{y + 20}" font-size="11" fill="#37474F">{esc(d)}</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_generic(title, essence, body_top=110):
    """泛型：类型擦除。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(f'<rect x="60" y="{body_top}" width="680" height="50" rx="8" fill="{BLUE}"/>')
    parts.append(f'<text x="400" y="{body_top + 32}" font-size="15" fill="#FFFFFF" text-anchor="middle" font-weight="700">'
                 f'Java 泛型 = 编译期类型检查 + 运行期类型擦除（擦除到 Object / 边界）</text>')
    # 流程
    parts.append(box(80, body_top + 80, 200, 80, 'List<String>\nList<Integer>\n(源码)', fill=GREEN + '22', stroke=GREEN, font_size=14))
    parts.append(arrow(280, body_top + 120, 320, body_top + 120, label='javac'))
    parts.append(box(320, body_top + 80, 200, 80, '编译期检查\n保证类型安全', fill=ORANGE + '22', stroke=ORANGE, font_size=14))
    parts.append(arrow(520, body_top + 120, 560, body_top + 120, label='擦除'))
    parts.append(box(560, body_top + 80, 180, 80, '字节码 List\nT→Object\n(运行时)', fill=RED + '22', stroke=RED, font_size=14))
    # 通配符
    parts.append(section_label(60, body_top + 200, '三种通配符', PURPLE))
    cards = [
        ('<? extends T>', '上界：只能读\n(生产者 Producer)', GREEN),
        ('<? super T>', '下界：只能写\n(消费者 Consumer)', ORANGE),
        ('<?>', '无界：不确定类型\n只读 Object', BLUE),
    ]
    for i, (n, d, c) in enumerate(cards):
        x = 60 + i * 230
        parts.append(f'<rect x="{x}" y="{body_top + 220}" width="210" height="100" rx="8" '
                     f'fill="{c}22" stroke="{c}" stroke-width="2"/>')
        parts.append(f'<text x="{x + 105}" y="{body_top + 250}" font-size="14" fill="{c}" '
                     f'text-anchor="middle" font-weight="700">{esc(n)}</text>')
        for j, ln in enumerate(wrap_text(d, 22)):
            parts.append(f'<text x="{x + 105}" y="{body_top + 282 + j * 16}" font-size="11" fill="#37474F" '
                         f'text-anchor="middle">{esc(ln)}</text>')
    # PECS
    parts.append(f'<text x="400" y="{body_top + 360}" font-size="14" fill="{RED}" text-anchor="middle" font-weight="700">'
                 f'PECS 原则：Producer Extends, Consumer Super</text>')
    parts.append(f'<text x="400" y="{body_top + 388}" font-size="12" fill="{GRAY}" text-anchor="middle">'
                 f'类型擦除影响：无法 new T() / 无法 instanceof T / 静态字段不能是泛型 / 不支持基本类型泛型</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_reflection(title, essence, body_top=110):
    """反射 API 体系。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(f'<rect x="60" y="{body_top}" width="680" height="50" rx="8" fill="{PURPLE}"/>')
    parts.append(f'<text x="400" y="{body_top + 32}" font-size="15" fill="#FFFFFF" text-anchor="middle" font-weight="700">'
                 f'反射：运行期动态获取类信息 + 操作对象（Spring/MyBatis/JSON 序列化基石）</text>')
    # Class 入口
    parts.append(box(310, body_top + 70, 180, 60, 'Class<?>\n类对象入口', fill=BLUE + '22', stroke=BLUE, font_size=14))
    # 4 大方向
    targets = [
        ('获取 Field\ngetDeclaredField()', GREEN, 60, body_top + 170),
        ('获取 Method\ngetDeclaredMethod()', ORANGE, 230, body_top + 170),
        ('获取 Constructor\ngetConstructor()', RED, 400, body_top + 170),
        ('创建实例\nnewInstance()', PURPLE, 570, body_top + 170),
    ]
    for n, c, x, y in targets:
        parts.append(box(x, y, 170, 70, n, fill=c + '22', stroke=c, font_size=12))
        parts.append(arrow(400, body_top + 130, x + 85, y, color=c))
    # setAccessible
    parts.append(box(280, body_top + 280, 240, 60, 'setAccessible(true)\n突破 private 访问限制',
                     fill=RED + '22', stroke=RED, font_size=13))
    # 优劣
    parts.append(f'<rect x="60" y="{body_top + 360}" width="320" height="80" rx="8" '
                 f'fill="{GREEN}11" stroke="{GREEN}" stroke-width="1.5"/>')
    parts.append(f'<text x="80" y="{body_top + 384}" font-size="13" fill="{GREEN}" font-weight="700">优势</text>')
    parts.append(f'<text x="80" y="{body_top + 404}" font-size="11" fill="#37474F">动态 / 灵活 / 框架基石</text>')
    parts.append(f'<text x="80" y="{body_top + 422}" font-size="11" fill="#37474F">运行期扩展（插件机制）</text>')
    parts.append(f'<rect x="420" y="{body_top + 360}" width="320" height="80" rx="8" '
                 f'fill="{RED}11" stroke="{RED}" stroke-width="1.5"/>')
    parts.append(f'<text x="440" y="{body_top + 384}" font-size="13" fill="{RED}" font-weight="700">劣势</text>')
    parts.append(f'<text x="440" y="{body_top + 404}" font-size="11" fill="#37474F">性能差（JIT 后仍 1.5x）</text>')
    parts.append(f'<text x="440" y="{body_top + 422}" font-size="11" fill="#37474F">破坏封装 / 安全风险</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_exception(title, essence, body_top=110):
    """异常体系树。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    # Throwable
    parts.append(box(330, body_top + 10, 140, 50, 'Throwable', fill=GRAY, stroke=RED, font_size=15, text_color='#FFFFFF'))
    # Error / Exception
    parts.append(box(140, body_top + 90, 160, 50, 'Error\n(JVM 错误)', fill=RED + '22', stroke=RED, font_size=13))
    parts.append(box(500, body_top + 90, 160, 50, 'Exception', fill=ORANGE + '22', stroke=ORANGE, font_size=14))
    parts.append(arrow(380, body_top + 60, 220, body_top + 90, color=GRAY))
    parts.append(arrow(420, body_top + 60, 580, body_top + 90, color=GRAY))
    # Error 子类
    err_children = ['OutOfMemoryError', 'StackOverflowError', 'NoClassDefFoundError']
    for i, n in enumerate(err_children):
        x = 50 + i * 100
        parts.append(box(x, body_top + 170, 90, 50, n, fill=RED + '11', stroke=RED, font_size=9))
        parts.append(arrow(220, body_top + 140, x + 45, body_top + 170, color=RED, dashed=True))
    # Exception 子类：RuntimeException (unchecked) / 其他 (checked)
    parts.append(box(380, body_top + 170, 180, 50, 'RuntimeException\n(运行期 非受检)', fill=PURPLE + '22', stroke=PURPLE, font_size=12))
    parts.append(box(600, body_top + 170, 160, 50, 'IOException 等\n(编译期 受检)', fill=BLUE + '22', stroke=BLUE, font_size=12))
    parts.append(arrow(580, body_top + 140, 470, body_top + 170, color=GRAY))
    parts.append(arrow(620, body_top + 140, 680, body_top + 170, color=GRAY))
    # RuntimeException 子类
    rc = ['NullPointerException', 'ClassCastException', 'ArrayIndexOutOfBounds', 'ArithmeticException']
    for i, n in enumerate(rc):
        x = 60 + i * 175
        parts.append(box(x, body_top + 250, 165, 44, n, fill=PURPLE + '11', stroke=PURPLE, font_size=10))
        parts.append(arrow(470, body_top + 220, x + 82, body_top + 250, color=PURPLE, dashed=True))
    # 总结
    parts.append(f'<text x="400" y="{body_top + 330}" font-size="13" fill="{BLUE}" text-anchor="middle" font-weight="700">'
                 f'Checked 必须捕获/声明 throws；Unchecked 可不处理</text>')
    parts.append(f'<text x="400" y="{body_top + 358}" font-size="12" fill="{GRAY}" text-anchor="middle">'
                 f'finally 一定执行(System.exit 前)；try-with-resources 自动关闭</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_string_pool(title, essence, body_top=110):
    """String 常量池。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    parts.append(f'<rect x="60" y="{body_top}" width="680" height="60" rx="8" fill="{BLUE}"/>')
    parts.append(f'<text x="400" y="{body_top + 28}" font-size="14" fill="#FFFFFF" text-anchor="middle" font-weight="700">'
                 f'String 不可变（final char[]/byte[]）→ 可常量池共享 → 线程安全 → hashCode 缓存</text>')
    parts.append(f'<text x="400" y="{body_top + 50}" font-size="11" fill="#FFFFFF" text-anchor="middle">'
                 f'JDK 7+ 字符串常量池移到堆中</text>')
    # 三种创建
    parts.append(section_label(60, body_top + 90, '三种创建方式对比', PURPLE))
    cards = [
        ('字面量\n"abc"', '常量池引用\n相同字面量共享', GREEN, 60),
        ('new String("abc")', '堆 new + 常量池\n创建 1~2 个对象', ORANGE, 290),
        ('intern()', 'native 方法\n池有则返回池对象\n池无则 JDK7+ 入堆引用', RED, 520),
    ]
    for n, d, c, x in cards:
        parts.append(f'<rect x="{x}" y="{body_top + 110}" width="220" height="100" rx="8" '
                     f'fill="{c}22" stroke="{c}" stroke-width="2"/>')
        parts.append(f'<text x="{x + 110}" y="{body_top + 138}" font-size="13" fill="{c}" '
                     f'text-anchor="middle" font-weight="700">{esc(n)}</text>')
        for j, ln in enumerate(wrap_text(d, 26)):
            parts.append(f'<text x="{x + 110}" y="{body_top + 168 + j * 14}" font-size="11" fill="#37404F" '
                         f'text-anchor="middle">{esc(ln)}</text>')
    # 经典题
    parts.append(f'<rect x="60" y="{body_top + 240}" width="680" height="180" rx="10" '
                 f'fill="#FFFFFF" stroke="{GREEN}" stroke-width="1.5"/>')
    parts.append(f'<text x="80" y="{body_top + 264}" font-size="13" fill="{GREEN}" font-weight="700">经典面试题</text>')
    qa = [
        's1="ab"; s2="a"+"b";  s1==s2  →  true (编译期常量折叠)',
        's1="ab"; s3="a"; s4=s3+"b";  s1==s4  →  false (变量拼接→堆)',
        's5 = new String("a")+new String("b"); s5.intern()==s1  →  true (JDK7+)',
        'StringBuilder.append() 在循环中优于 + 拼接（避免中间对象）',
    ]
    for i, q in enumerate(qa):
        y = body_top + 290 + i * 30
        parts.append(f'<circle cx="78" cy="{y - 4}" r="4" fill="{PALETTE[i]}"/>')
        for j, ln in enumerate(wrap_text(q, 60)):
            parts.append(f'<text x="92" y="{y + j * 14}" font-size="11" fill="#37474F">{esc(ln)}</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_annotation(title, essence, body_top=110):
    """注解元注解+生命周期。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    # 元注解
    parts.append(section_label(60, body_top + 10, '5 大元注解', BLUE))
    metas = [
        ('@Target', '作用位置\nTYPE/METHOD/FIELD', GREEN),
        ('@Retention', '保留策略\nSOURCE/CLASS/RUNTIME', BLUE),
        ('@Documented', 'Javadoc 包含', ORANGE),
        ('@Inherited', '子类可继承', PURPLE),
        ('@Repeatable', '可重复使用', RED),
    ]
    for i, (n, d, c) in enumerate(metas):
        x = 60 + i * 140
        parts.append(f'<rect x="{x}" y="{body_top + 30}" width="130" height="80" rx="6" '
                     f'fill="{c}22" stroke="{c}" stroke-width="1.5"/>')
        parts.append(f'<text x="{x + 65}" y="{body_top + 56}" font-size="12" fill="{c}" '
                     f'text-anchor="middle" font-weight="700">{esc(n)}</text>')
        for j, ln in enumerate(wrap_text(d, 14)):
            parts.append(f'<text x="{x + 65}" y="{body_top + 78 + j * 14}" font-size="10" fill="#37404F" '
                         f'text-anchor="middle">{esc(ln)}</text>')
    # Retention 三阶段
    parts.append(section_label(60, body_top + 150, 'RetentionPolicy 三阶段', PURPLE))
    phases = [
        ('SOURCE', '源码期\n如 @Override', GREEN, 60),
        ('CLASS', '字节码期(默认)\n几乎不用', ORANGE, 290),
        ('RUNTIME', '运行期可反射读取\n框架基石', BLUE, 520),
    ]
    for i, (n, d, c, x) in enumerate(phases):
        parts.append(f'<rect x="{x}" y="{body_top + 170}" width="220" height="80" rx="8" '
                     f'fill="{c}22" stroke="{c}" stroke-width="2"/>')
        parts.append(f'<text x="{x + 110}" y="{body_top + 198}" font-size="14" fill="{c}" '
                     f'text-anchor="middle" font-weight="700">{esc(n)}</text>')
        for j, ln in enumerate(wrap_text(d, 26)):
            parts.append(f'<text x="{x + 110}" y="{body_top + 224 + j * 14}" font-size="11" fill="#37404F" '
                         f'text-anchor="middle">{esc(ln)}</text>')
        if i < 2:
            x_next = 60 + (i + 1) * 230
            parts.append(arrow(x + 220, body_top + 210, x_next, body_top + 210, color=GRAY, label='衰减'))
    # 自定义
    parts.append(f'<rect x="60" y="{body_top + 280}" width="680" height="160" rx="10" '
                 f'fill="#FFFFFF" stroke="{RED}" stroke-width="1.5"/>')
    parts.append(f'<text x="80" y="{body_top + 304}" font-size="13" fill="{RED}" font-weight="700">自定义注解 + 处理</text>')
    steps = ['@interface 定义', '元注解标注\n(RUNTIME)', '反射 isAnnotationPresent', 'getAnnotation', '业务处理']
    for i, s in enumerate(steps):
        x = 80 + i * 130
        c = PALETTE[i % 6]
        parts.append(box(x, body_top + 320, 120, 60, s, fill=c + '22', stroke=c, font_size=11))
        if i > 0:
            parts.append(arrow(x - 10, body_top + 350, x, body_top + 350, color=GRAY))
    parts.append(f'<text x="400" y="{body_top + 416}" font-size="12" fill="{GRAY}" text-anchor="middle">'
                 f'框架应用：Spring(@Component/@Autowired)  MyBatis  Lombok  编译期 apt</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_lambda(title, essence, body_top=110):
    """Lambda + 函数式接口。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(f'<rect x="60" y="{body_top}" width="680" height="50" rx="8" fill="{PURPLE}"/>')
    parts.append(f'<text x="400" y="{body_top + 32}" font-size="15" fill="#FFFFFF" text-anchor="middle" font-weight="700">'
                 f'Lambda = 语法糖  →  运行期生成 invokedynamic + LambdaMetafactory</text>')
    # 函数式接口
    parts.append(section_label(60, body_top + 80, 'JDK 内置函数式接口（java.util.function）', BLUE))
    fis = [
        ('Function<T,R>', 'apply(T)→R\n转换', GREEN),
        ('Predicate<T>', 'test(T)→boolean\n断言', ORANGE),
        ('Consumer<T>', 'accept(T)→void\n消费', BLUE),
        ('Supplier<T>', 'get()→T\n供给', PURPLE),
        ('BiFunction<T,U,R>', '双参转换', RED),
    ]
    for i, (n, d, c) in enumerate(fis):
        x = 60 + i * 140
        parts.append(f'<rect x="{x}" y="{body_top + 100}" width="130" height="80" rx="6" '
                     f'fill="{c}22" stroke="{c}" stroke-width="1.5"/>')
        parts.append(f'<text x="{x + 65}" y="{body_top + 124}" font-size="11" fill="{c}" '
                     f'text-anchor="middle" font-weight="700">{esc(n)}</text>')
        for j, ln in enumerate(wrap_text(d, 14)):
            parts.append(f'<text x="{x + 65}" y="{body_top + 146 + j * 14}" font-size="10" fill="#37404F" '
                         f'text-anchor="middle">{esc(ln)}</text>')
    # 方法引用
    parts.append(section_label(60, body_top + 210, '方法引用 4 种形式', PURPLE))
    mrefs = [
        ('类::静态方法', 'Integer::parseInt', GREEN),
        ('对象::实例方法', 'System.out::println', BLUE),
        ('类::实例方法', 'String::length', ORANGE),
        ('类::new', 'User::new', PURPLE),
    ]
    for i, (n, d, c) in enumerate(mrefs):
        x = 60 + i * 175
        parts.append(f'<rect x="{x}" y="{body_top + 230}" width="165" height="70" rx="6" '
                     f'fill="{c}22" stroke="{c}" stroke-width="1.5"/>')
        parts.append(f'<text x="{x + 82}" y="{body_top + 256}" font-size="11" fill="{c}" '
                     f'text-anchor="middle" font-weight="700">{esc(n)}</text>')
        parts.append(f'<text x="{x + 82}" y="{body_top + 282}" font-size="11" fill="#263238" '
                     f'text-anchor="middle">{esc(d)}</text>')
    # Stream API
    parts.append(f'<text x="400" y="{body_top + 340}" font-size="14" fill="{GREEN}" text-anchor="middle" font-weight="700">'
                 f'Stream API 流水线：source → 中间操作(惰性) → 终止操作</text>')
    parts.append(f'<text x="400" y="{body_top + 368}" font-size="12" fill="{GRAY}" text-anchor="middle">'
                 f'filter / map / flatMap / sorted / distinct  |  collect / reduce / forEach / count</text>')
    parts.append(f'<text x="400" y="{body_top + 392}" font-size="12" fill="{GRAY}" text-anchor="middle">'
                 f'并行流 parallelStream：ForkJoinPool.commonPool()，注意线程安全与顺序</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_stream(title, essence, body_top=110):
    """Stream API 流程。"""
    return tpl_pipeline(title, essence, [
        '源\nlist.stream()',
        'filter\n中间(惰性)',
        'map\n中间(惰性)',
        'sorted\n中间(惰性)',
        'distinct\n中间(惰性)',
        'collect/reduce\n终止操作',
        '结果',
    ], body_top=body_top)

def tpl_sql_index(title, essence, body_top=110):
    """B+ 树索引。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    parts.append(f'<rect x="60" y="{body_top}" width="680" height="50" rx="8" fill="{BLUE}"/>')
    parts.append(f'<text x="400" y="{body_top + 32}" font-size="15" fill="#FFFFFF" text-anchor="middle" font-weight="700">'
                 f'InnoDB B+ 树索引：非叶子节点存索引键，叶子节点存数据(聚簇) / 主键(二级)</text>')
    # B+ 树结构（简化）
    # 根
    parts.append(box(340, body_top + 70, 120, 40, '根节点\n10 | 20 | 30', fill=ORANGE + '22', stroke=ORANGE, font_size=11))
    # 中间
    for i, v in enumerate(['<10', '10-20', '20-30', '>30']):
        x = 80 + i * 175
        parts.append(box(x, body_top + 140, 150, 40, f'中间节点\n{v}', fill=BLUE + '22', stroke=BLUE, font_size=11))
        parts.append(arrow(400, body_top + 110, x + 75, body_top + 140, color=GRAY))
    # 叶子
    parts.append(f'<text x="400" y="{body_top + 215}" font-size="12" fill="{GREEN}" text-anchor="middle" font-weight="700">'
                 f'叶子节点（双向链表，范围查询友好）</text>')
    leaves = ['1,4,7', '10,13,17', '20,23,27', '30,35,40']
    for i, v in enumerate(leaves):
        x = 80 + i * 175
        parts.append(box(x, body_top + 230, 150, 50, f'叶子\n{v}\n+ 主键 ID', fill=GREEN + '22', stroke=GREEN, font_size=10))
        if i > 0:
            parts.append(arrow(x - 10, body_top + 255, x - 30, body_top + 255, color=GREEN))
            parts.append(arrow(x - 30, body_top + 265, x - 10, body_top + 265, color=GREEN, dashed=True))
    # 聚簇 vs 二级
    parts.append(f'<rect x="60" y="{body_top + 310}" width="340" height="130" rx="8" '
                 f'fill="{PURPLE}11" stroke="{PURPLE}" stroke-width="2"/>')
    parts.append(f'<text x="230" y="{body_top + 336}" font-size="14" fill="{PURPLE}" '
                 f'text-anchor="middle" font-weight="700">聚簇索引 (Clustered)</text>')
    for j, t in enumerate(['叶子节点存整行数据', '一张表只有一个', '默认主键 / 第一个 NOT NULL UNIQUE', '查询主键快']):
        y = body_top + 360 + j * 20
        parts.append(f'<circle cx="80" cy="{y - 4}" r="4" fill="{PURPLE}"/>')
        parts.append(f'<text x="94" y="{y}" font-size="11" fill="#37474F">{esc(t)}</text>')
    parts.append(f'<rect x="420" y="{body_top + 310}" width="320" height="130" rx="8" '
                 f'fill="{ORANGE}11" stroke="{ORANGE}" stroke-width="2"/>')
    parts.append(f'<text x="580" y="{body_top + 336}" font-size="14" fill="{ORANGE}" '
                 f'text-anchor="middle" font-weight="700">二级索引 (Secondary)</text>')
    for j, t in enumerate(['叶子节点存索引列+主键', '可有多个', '查询需"回表"再到聚簇查', '覆盖索引避免回表']):
        y = body_top + 360 + j * 20
        parts.append(f'<circle cx="440" cy="{y - 4}" r="4" fill="{ORANGE}"/>')
        parts.append(f'<text x="454" y="{y}" font-size="11" fill="#37404F">{esc(t)}</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_lock_deadlock(title, essence, body_top=110):
    """死锁 4 条件 + 排查。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(f'<rect x="60" y="{body_top}" width="680" height="50" rx="8" fill="{RED}"/>')
    parts.append(f'<text x="400" y="{body_top + 32}" font-size="15" fill="#FFFFFF" text-anchor="middle" font-weight="700">'
                 f'死锁 = 两个或多个线程互相等待对方释放资源</text>')
    # 4 必要条件
    parts.append(section_label(60, body_top + 80, '4 大必要条件（缺一不可）', BLUE))
    conds = [
        ('互斥', '资源独占', GREEN),
        ('占有并等待', '持锁再申请', BLUE),
        ('不剥夺', '不能强行夺走', ORANGE),
        ('循环等待', '环路依赖', PURPLE),
    ]
    for i, (n, d, c) in enumerate(conds):
        x = 60 + i * 175
        parts.append(f'<rect x="{x}" y="{body_top + 100}" width="160" height="80" rx="8" '
                     f'fill="{c}22" stroke="{c}" stroke-width="2"/>')
        parts.append(f'<text x="{x + 80}" y="{body_top + 128}" font-size="14" fill="{c}" '
                     f'text-anchor="middle" font-weight="700">{esc(n)}</text>')
        parts.append(f'<text x="{x + 80}" y="{body_top + 156}" font-size="11" fill="#37404F" '
                     f'text-anchor="middle">{esc(d)}</text>')
    # 经典示意
    parts.append(f'<text x="400" y="{body_top + 210}" font-size="13" fill="{RED}" text-anchor="middle" font-weight="700">'
                 f'经典示意：线程A 持锁1 等锁2；线程B 持锁2 等锁1</text>')
    parts.append(box(140, body_top + 230, 180, 50, '线程A\n持 Lock1 → 等 Lock2', fill=BLUE + '22', stroke=BLUE, font_size=12))
    parts.append(box(480, body_top + 230, 180, 50, '线程B\n持 Lock2 → 等 Lock1', fill=ORANGE + '22', stroke=ORANGE, font_size=12))
    parts.append(arrow(320, body_top + 245, 480, body_top + 245, color=RED, label='等待'))
    parts.append(arrow(480, body_top + 265, 320, body_top + 265, color=RED, label='等待'))
    # 解决
    parts.append(f'<rect x="60" y="{body_top + 310}" width="680" height="130" rx="10" '
                 f'fill="#FFFFFF" stroke="{GREEN}" stroke-width="1.5"/>')
    parts.append(f'<text x="80" y="{body_top + 334}" font-size="13" fill="{GREEN}" font-weight="700">解决方法</text>')
    sols = [
        ('破坏循环等待', '固定锁顺序', GREEN),
        ('超时放弃', 'tryLock(timeout)', BLUE),
        ('死锁检测', 'JStack / Arthas', ORANGE),
        ('避免', '一次性申请所有锁', PURPLE),
    ]
    for i, (n, d, c) in enumerate(sols):
        x = 80 + i * 165
        parts.append(f'<rect x="{x}" y="{body_top + 350}" width="155" height="76" rx="6" '
                     f'fill="{c}22" stroke="{c}" stroke-width="1.5"/>')
        parts.append(f'<text x="{x + 78}" y="{body_top + 376}" font-size="12" fill="{c}" '
                     f'text-anchor="middle" font-weight="700">{esc(n)}</text>')
        parts.append(f'<text x="{x + 78}" y="{body_top + 402}" font-size="10" fill="#37404F" '
                     f'text-anchor="middle">{esc(d)}</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_tomcat(title, essence, body_top=110):
    """Tomcat 架构。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    parts.append(box(300, body_top, 200, 50, 'Server (整个 Tomcat)', fill=GRAY + '22', stroke=GRAY, font_size=14))
    parts.append(box(300, body_top + 70, 200, 50, 'Service (≥1 Connector+1 Engine)', fill=BLUE + '22', stroke=BLUE, font_size=12))
    parts.append(arrow(400, body_top + 50, 400, body_top + 70))
    # Connector / Engine 并列
    parts.append(box(100, body_top + 150, 200, 60, 'Connector\n(HTTP/AJP/NIO)\n接收请求解析协议', fill=GREEN + '22', stroke=GREEN, font_size=12))
    parts.append(box(500, body_top + 150, 200, 60, 'Engine\n(Catalina 引擎)\n处理所有 Host', fill=ORANGE + '22', stroke=ORANGE, font_size=12))
    parts.append(arrow(400, body_top + 95, 200, body_top + 150))
    parts.append(arrow(400, body_top + 95, 600, body_top + 150))
    # Host/Context
    parts.append(box(500, body_top + 240, 200, 50, 'Host (虚拟主机)\nlocalhost 等', fill=PURPLE + '22', stroke=PURPLE, font_size=12))
    parts.append(arrow(600, body_top + 210, 600, body_top + 240))
    parts.append(box(500, body_top + 310, 200, 50, 'Context (单个 WebApp)', fill=RED + '22', stroke=RED, font_size=12))
    parts.append(arrow(600, body_top + 290, 600, body_top + 310))
    parts.append(box(500, body_top + 380, 200, 50, 'Wrapper (单个 Servlet)', fill=BLUE + '22', stroke=BLUE, font_size=12))
    parts.append(arrow(600, body_top + 360, 600, body_top + 380))
    # 左：线程模型
    parts.append(f'<rect x="60" y="{body_top + 240}" width="380" height="190" rx="8" '
                 f'fill="#FFFFFF" stroke="{GRAY}" stroke-width="1.5"/>')
    parts.append(f'<text x="80" y="{body_top + 264}" font-size="13" fill="{GRAY}" font-weight="700">线程模型 &amp; 类加载</text>')
    notes = ['Connector → Executor (线程池)', '每个请求一个 Worker 线程',
             'WebAppClassLoader 打破双亲委派', '每个 Context 独立 ClassLoader',
             '热部署原理：替换 ClassLoader']
    for i, n in enumerate(notes):
        y = body_top + 288 + i * 26
        parts.append(f'<circle cx="78" cy="{y - 4}" r="4" fill="{PALETTE[i]}"/>')
        parts.append(f'<text x="92" y="{y}" font-size="12" fill="#37474F">{esc(n)}</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_dubbo(title, essence, body_top=110):
    """Dubbo RPC 调用流程。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    # Consumer 侧
    parts.append(box(50, body_top + 40, 160, 60, 'Consumer\n业务调用方', fill=BLUE + '22', stroke=BLUE, font_size=13))
    parts.append(box(230, body_top + 40, 160, 60, 'Proxy\n动态代理\n(屏蔽远程细节)', fill=GREEN + '22', stroke=GREEN, font_size=11))
    parts.append(arrow(210, body_top + 70, 230, body_top + 70, label='调用'))
    parts.append(box(410, body_top + 40, 160, 60, 'Cluster\n容错(_failover_)\n负载均衡', fill=ORANGE + '22', stroke=ORANGE, font_size=11))
    parts.append(arrow(390, body_top + 70, 410, body_top + 70, label='路由'))
    parts.append(box(590, body_top + 40, 170, 60, 'Protocol/Codec\nDubbo 协议编码\n(默认 TCP+Hessian)', fill=PURPLE + '22', stroke=PURPLE, font_size=11))
    parts.append(arrow(570, body_top + 70, 590, body_top + 70, label='发送'))
    # 注册中心
    parts.append(box(330, body_top + 150, 140, 50, 'Registry\n(Zookeeper/Nacos)\n订阅/通知', fill=RED + '22', stroke=RED, font_size=11))
    parts.append(arrow(490, body_top + 100, 400, body_top + 150, color=RED, dashed=True, label='订阅'))
    parts.append(arrow(400, body_top + 150, 670, body_top + 220, color=RED, dashed=True, label='推送'))
    # Provider 侧
    parts.append(box(590, body_top + 220, 170, 60, 'Protocol\n解码\n→ Invoker', fill=PURPLE + '22', stroke=PURPLE, font_size=11))
    parts.append(box(590, body_top + 290, 170, 60, 'Filter 链\n(日志/限流/监控)', fill=ORANGE + '22', stroke=ORANGE, font_size=11))
    parts.append(arrow(670, body_top + 280, 670, body_top + 290))
    parts.append(box(590, body_top + 360, 170, 60, '真实 Service\n业务实现', fill=GREEN + '22', stroke=GREEN, font_size=13))
    parts.append(arrow(670, body_top + 350, 670, body_top + 360))
    # 注册
    parts.append(arrow(620, body_top + 200, 470, body_top + 175, color=RED, dashed=True, label='注册'))
    # 左下：要点
    parts.append(f'<text x="80" y="{body_top + 240}" font-size="13" fill="{BLUE}" font-weight="700">核心特性</text>')
    feats = ['服务发现：注册中心订阅', '负载均衡：RR/Random/ConsistentHash', '容错策略：Failover/Failfast/Forking',
             'SPI 扩展机制：自适应扩展点', '异步调用：CompletableFuture', 'Telnet 协议：在线调测']
    for i, f in enumerate(feats):
        col = i % 2
        row = i // 2
        x = 80 + col * 250
        y = body_top + 264 + row * 24
        parts.append(f'<circle cx="{x}" cy="{y - 4}" r="4" fill="{PALETTE[i]}"/>')
        parts.append(f'<text x="{x + 12}" y="{y}" font-size="11" fill="#37404F">{esc(f)}</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_distributed_lock(title, essence, body_top=110):
    """分布式锁三种实现。"""
    return tpl_compare(title, essence, [
        ('数据库', ['唯一索引', 'for update 行锁', '实现简单', '性能差', '需定时清理']),
        ('Redis (SETNX)', ['SET NX PX', 'Redlock 算法', '性能高', '需守护线程续期', 'AP 模型有风险']),
        ('Zookeeper', ['临时顺序节点', 'Curator InterProcessMutex', 'CP 强一致', '性能中等', '可靠性最高']),
    ], body_top=body_top)

def tpl_design_principle(title, essence, body_top=110):
    """设计模式六大原则。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(f'<rect x="60" y="{body_top}" width="680" height="50" rx="8" fill="{BLUE}"/>')
    parts.append(f'<text x="400" y="{body_top + 32}" font-size="15" fill="#FFFFFF" text-anchor="middle" font-weight="700">'
                 f'SOLID + 迪米特 + 合成复用 → 高内聚、低耦合</text>')
    principles = [
        ('S', '单一职责', 'Single Responsibility', '一个类只做一件事', GREEN),
        ('O', '开闭原则', 'Open-Closed', '对扩展开放，对修改关闭', BLUE),
        ('L', '里氏替换', 'Liskov Substitution', '子类能完整替换父类', ORANGE),
        ('I', '接口隔离', 'Interface Segregation', '不依赖不需要的接口', PURPLE),
        ('D', '依赖倒置', 'Dependency Inversion', '依赖抽象，不依赖具体', RED),
        ('LoD', '迪米特法则', 'Law of Demeter', '最少知道原则', GRAY),
        ('CARP', '合成复用', 'Composite Reuse', '多用组合，少用继承', GREEN),
    ]
    for i, (k, n, en, d, c) in enumerate(principles):
        col = i % 4
        row = i // 4
        x = 60 + col * 175
        y = body_top + 70 + row * 160
        parts.append(f'<rect x="{x}" y="{y}" width="160" height="140" rx="8" '
                     f'fill="{c}22" stroke="{c}" stroke-width="2"/>')
        parts.append(f'<circle cx="{x + 30}" cy="{y + 30}" r="20" fill="{c}"/>')
        parts.append(f'<text x="{x + 30}" y="{y + 36}" font-size="14" fill="#FFFFFF" '
                     f'text-anchor="middle" font-weight="700">{esc(k)}</text>')
        parts.append(f'<text x="{x + 80}" y="{y + 28}" font-size="13" fill="{c}" font-weight="700">{esc(n)}</text>')
        parts.append(f'<text x="{x + 80}" y="{y + 46}" font-size="9" fill="#546E7A">{esc(en)}</text>')
        for j, ln in enumerate(wrap_text(d, 16)):
            parts.append(f'<text x="{x + 80}" y="{y + 76 + j * 14}" font-size="10" fill="#37404F" '
                         f'text-anchor="middle">{esc(ln)}</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_proxy_pattern(title, essence, body_top=110):
    """代理模式：静态 vs JDK vs CGLIB。"""
    return tpl_compare(title, essence, [
        ('静态代理', ['编译期确定', '实现相同接口', '需手写代理类', '一个代理一个主题']),
        ('JDK 动态代理', ['基于接口', 'Proxy.newProxyInstance', 'InvocationHandler', 'Spring AOP 默认(有接口)']),
        ('CGLIB 动态代理', ['基于继承', 'Enhancer.create', 'MethodInterceptor', '不能代理 final 类/方法']),
    ], body_top=body_top)

def tpl_factory_pattern(title, essence, body_top=110):
    """工厂模式三种。"""
    return tpl_compare(title, essence, [
        ('简单工厂', ['一个工厂方法', 'if/switch 判断', '违反开闭原则', '场景：少量产品']),
        ('工厂方法', ['每产品一工厂', '符合开闭原则', '类爆炸', '场景：产品族扩展']),
        ('抽象工厂', ['工厂创建产品族', '多维度产品', '加新产品需改接口', '场景：跨平台 UI']),
    ], body_top=body_top)

def tpl_observer_pattern(title, essence, body_top=110):
    """观察者模式。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    # Subject 中心
    parts.append(box(330, body_top + 20, 180, 60, 'Subject 主题\n维护 observers 列表', fill=BLUE + '22', stroke=BLUE, font_size=13))
    # 3 个 Observer
    for i, (n, c) in enumerate([('Observer A\n(UI 更新)', GREEN), ('Observer B\n(日志记录)', ORANGE), ('Observer C\n(消息推送)', PURPLE)]):
        y = body_top + 130 + i * 60
        parts.append(box(60, y, 180, 50, n, fill=c + '22', stroke=c, font_size=11))
        parts.append(arrow(240, y + 25, 330, body_top + 60, color=c, dashed=True, label='注册'))
        parts.append(arrow(330, body_top + 60, 240, y + 25, color=RED, label='notify'))
    # 右侧：MQ 应用
    parts.append(f'<rect x="540" y="{body_top + 130}" width="220" height="190" rx="8" '
                 f'fill="#FFFFFF" stroke="{GREEN}" stroke-width="1.5"/>')
    parts.append(f'<text x="650" y="{body_top + 156}" font-size="13" fill="{GREEN}" '
                 f'text-anchor="middle" font-weight="700">实际应用</text>')
    apps = ['事件总线 EventBus', 'Spring ApplicationEvent', 'RxJava/Reactor 响应式',
            'Vue/React 数据绑定', 'MQ 发布订阅模型']
    for i, a in enumerate(apps):
        y = body_top + 180 + i * 24
        parts.append(f'<circle cx="558" cy="{y - 4}" r="4" fill="{PALETTE[i]}"/>')
        parts.append(f'<text x="572" y="{y}" font-size="11" fill="#37404F">{esc(a)}</text>')
    # 变体
    parts.append(f'<text x="400" y="{body_top + 360}" font-size="13" fill="{PURPLE}" text-anchor="middle" font-weight="700">'
                 f'推模式 vs 拉模式  |  同步通知 vs 异步事件</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_strategy_pattern(title, essence, body_top=110):
    """策略模式 + 消除 if/else。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    # Context
    parts.append(box(330, body_top + 20, 180, 60, 'Context\n持 Strategy 引用', fill=BLUE + '22', stroke=BLUE, font_size=13))
    # Interface
    parts.append(box(330, body_top + 110, 180, 50, '<<interface>>\nStrategy', fill=ORANGE + '22', stroke=ORANGE, font_size=13))
    parts.append(arrow(420, body_top + 80, 420, body_top + 110, label='聚合'))
    # 实现
    for i, (n, c) in enumerate([('ConcreteStrategyA', GREEN), ('ConcreteStrategyB', PURPLE), ('ConcreteStrategyC', RED)]):
        x = 60 + i * 250
        parts.append(box(x, body_top + 190, 220, 60, n, fill=c + '22', stroke=c, font_size=12))
        parts.append(arrow(x + 110, body_top + 190, 420, body_top + 160, color=c, dashed=True))
    # 优势
    parts.append(f'<rect x="60" y="{body_top + 280}" width="680" height="160" rx="10" '
                 f'fill="#FFFFFF" stroke="{GREEN}" stroke-width="1.5"/>')
    parts.append(f'<text x="80" y="{body_top + 304}" font-size="13" fill="{GREEN}" font-weight="700">优势 / Spring 应用</text>')
    items = [
        ('消除 if/else', '每个分支独立类', GREEN),
        ('开闭原则', '新增策略不改原代码', BLUE),
        ('Spring 注入', '@Autowired Map<String,Strategy>', ORANGE),
        ('典型场景', '支付/折扣/排序/路由', PURPLE),
        ('Java 应用', 'Comparator / ThreadPoolExecutor 拒绝策略', RED),
        ('替代方案', '枚举 + 函数式接口', GRAY),
    ]
    for i, (n, d, c) in enumerate(items):
        col = i % 3
        row = i // 3
        x = 80 + col * 225
        y = body_top + 326 + row * 60
        parts.append(f'<rect x="{x}" y="{y - 16}" width="210" height="48" rx="6" fill="{c}22" stroke="{c}" stroke-width="1.5"/>')
        parts.append(f'<text x="{x + 12}" y="{y + 2}" font-size="12" fill="{c}" font-weight="700">{esc(n)}</text>')
        parts.append(f'<text x="{x + 12}" y="{y + 22}" font-size="10" fill="#37404F">{esc(d)}</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_oop(title, essence, body_top=110):
    """OOP 四大特性。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(f'<rect x="60" y="{body_top}" width="680" height="50" rx="8" fill="{PURPLE}"/>')
    parts.append(f'<text x="400" y="{body_top + 32}" font-size="15" fill="#FFFFFF" text-anchor="middle" font-weight="700">'
                 f'面向对象四大特性：封装 / 继承 / 多态 / 抽象</text>')
    cards = [
        ('封装 Encapsulation', ['隐藏实现细节', 'private + getter/setter', '降低耦合', '保护数据完整性'], GREEN),
        ('继承 Inheritance', ['代码复用', 'extends 关键字', '单继承(类)/多实现(接口)', 'is-a 关系'], BLUE),
        ('多态 Polymorphism', ['同一接口不同表现', '重写 Override + 向上转型', '动态分派(invokevirtual)', '运行期确定'], ORANGE),
        ('抽象 Abstraction', ['抓住核心忽略细节', 'abstract class / interface', '定义契约', '面向接口编程'], PURPLE),
    ]
    for i, (n, feats, c) in enumerate(cards):
        x = 60 + i * 175
        parts.append(f'<rect x="{x}" y="{body_top + 70}" width="160" height="200" rx="8" '
                     f'fill="{c}22" stroke="{c}" stroke-width="2"/>')
        parts.append(f'<text x="{x + 80}" y="{body_top + 96}" font-size="13" fill="{c}" '
                     f'text-anchor="middle" font-weight="700">{esc(n)}</text>')
        for j, f in enumerate(feats):
            yy = body_top + 124 + j * 36
            parts.append(f'<text x="{x + 14}" y="{yy}" font-size="11" fill="#37404F">• {esc(f)}</text>')
    # 关键点
    parts.append(f'<text x="400" y="{body_top + 320}" font-size="13" fill="{BLUE}" text-anchor="middle" font-weight="700">'
                 f'底层：多态 = 运行期根据实际对象类型分派（invokevirtual）</text>')
    parts.append(f'<text x="400" y="{body_top + 350}" font-size="12" fill="{GRAY}" text-anchor="middle">'
                 f'重载 Overload (静态分派，编译期) ≠ 重写 Override (动态分派，运行期)</text>')
    parts.append(f'<text x="400" y="{body_top + 376}" font-size="12" fill="{GRAY}" text-anchor="middle">'
                 f'JDK 8: 接口支持 default / static 方法；JDK 9+: private 方法</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_collection_hierarchy(title, essence, body_top=110):
    """Java 集合框架层级。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    # 顶层
    parts.append(box(330, body_top + 10, 140, 40, 'Collection', fill=GRAY + '22', stroke=GRAY, font_size=14))
    parts.append(box(80, body_top + 10, 140, 40, 'Map', fill=PURPLE + '22', stroke=PURPLE, font_size=14))
    # 三大接口
    parts.append(box(60, body_top + 80, 130, 40, 'List', fill=BLUE + '22', stroke=BLUE, font_size=13))
    parts.append(box(220, body_top + 80, 130, 40, 'Set', fill=GREEN + '22', stroke=GREEN, font_size=13))
    parts.append(box(380, body_top + 80, 130, 40, 'Queue', fill=ORANGE + '22', stroke=ORANGE, font_size=13))
    parts.append(arrow(380, body_top + 50, 120, body_top + 80, color=GRAY))
    parts.append(arrow(400, body_top + 50, 280, body_top + 80, color=GRAY))
    parts.append(arrow(420, body_top + 50, 440, body_top + 80, color=GRAY))
    # List 实现
    list_impls = [('ArrayList\n(数组)', GREEN), ('LinkedList\n(双向链表)', BLUE), ('Vector\n(线程安全)', RED)]
    for i, (n, c) in enumerate(list_impls):
        x = 30 + i * 110
        parts.append(box(x, body_top + 150, 100, 50, n, fill=c + '22', stroke=c, font_size=10))
        parts.append(arrow(110, body_top + 120, x + 50, body_top + 150, color=GRAY))
    # Set 实现
    set_impls = [('HashSet\n(HashMap)', PURPLE), ('LinkedHashSet\n(链表+哈希)', BLUE), ('TreeSet\n(红黑树)', RED)]
    for i, (n, c) in enumerate(set_impls):
        x = 190 + i * 110
        parts.append(box(x, body_top + 150, 100, 50, n, fill=c + '22', stroke=c, font_size=10))
        parts.append(arrow(280, body_top + 120, x + 50, body_top + 150, color=GRAY))
    # Queue 实现
    q_impls = [('PriorityQueue\n(堆)', BLUE), ('ArrayDeque\n(双端数组)', GREEN), ('LinkedList', ORANGE)]
    for i, (n, c) in enumerate(q_impls):
        x = 350 + i * 110
        parts.append(box(x, body_top + 150, 100, 50, n, fill=c + '22', stroke=c, font_size=10))
        parts.append(arrow(440, body_top + 120, x + 50, body_top + 150, color=GRAY))
    # Map 实现
    map_impls = [('HashMap\n(数组+链表+树)', BLUE), ('LinkedHashMap\n(链表)', GREEN), ('TreeMap\n(红黑树)', RED), ('ConcurrentHashMap\n(线程安全)', PURPLE)]
    for i, (n, c) in enumerate(map_impls):
        x = 540 + (i % 2) * 130
        y = body_top + 80 + (i // 2) * 70
        parts.append(box(x, y, 120, 50, n, fill=c + '22', stroke=c, font_size=9))
        parts.append(arrow(150, body_top + 35, x + 60, y, color=PURPLE, dashed=True))
    # 底部要点
    parts.append(f'<text x="400" y="{body_top + 240}" font-size="13" fill="{BLUE}" text-anchor="middle" font-weight="700">'
                 f'选型：查多用 HashMap，有序用 Linked，排序用 Tree，并发用 Concurrent</text>')
    parts.append(f'<text x="400" y="{body_top + 268}" font-size="12" fill="{GRAY}" text-anchor="middle">'
                 f'fail-fast：迭代时 modCount 校验，抛 ConcurrentModificationException</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_docker_k8s(title, essence, body_top=110):
    """容器化 + K8s 编排。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    # Docker 部分
    parts.append(f'<rect x="60" y="{body_top}" width="320" height="170" rx="8" '
                 f'fill="{BLUE}11" stroke="{BLUE}" stroke-width="2"/>')
    parts.append(f'<text x="220" y="{body_top + 26}" font-size="15" fill="{BLUE}" '
                 f'text-anchor="middle" font-weight="700">Docker（容器化）</text>')
    parts.append(box(80, body_top + 40, 280, 36, 'App + Libs + Runtime → 镜像', fill='#FFFFFF', stroke=BLUE, font_size=12))
    parts.append(box(80, body_top + 84, 280, 36, 'Namespace + Cgroups 隔离', fill='#FFFFFF', stroke=BLUE, font_size=12))
    parts.append(box(80, body_top + 128, 280, 32, '比 VM 轻：共享内核，秒级启动', fill='#FFFFFF', stroke=GREEN, font_size=11))
    # K8s 部分
    parts.append(f'<rect x="420" y="{body_top}" width="320" height="380" rx="8" '
                 f'fill="{GREEN}11" stroke="{GREEN}" stroke-width="2"/>')
    parts.append(f'<text x="580" y="{body_top + 26}" font-size="15" fill="{GREEN}" '
                 f'text-anchor="middle" font-weight="700">Kubernetes（编排）</text>')
    # Master
    parts.append(f'<rect x="440" y="{body_top + 44}" width="280" height="100" rx="6" '
                 f'fill="{PURPLE}22" stroke="{PURPLE}" stroke-width="1.5"/>')
    parts.append(f'<text x="580" y="{body_top + 64}" font-size="12" fill="{PURPLE}" text-anchor="middle" font-weight="700">Master 控制面</text>')
    masters = ['kube-apiserver', 'etcd', 'kube-scheduler', 'kube-controller-manager']
    for i, m in enumerate(masters):
        col = i % 2
        row = i // 2
        x = 450 + col * 140
        y = body_top + 78 + row * 28
        parts.append(f'<rect x="{x}" y="{y - 14}" width="130" height="22" rx="3" fill="#FFFFFF" stroke="{PURPLE}"/>')
        parts.append(f'<text x="{x + 65}" y="{y + 2}" font-size="10" fill="{PURPLE}" text-anchor="middle">{esc(m)}</text>')
    # Worker
    parts.append(f'<rect x="440" y="{body_top + 154}" width="280" height="120" rx="6" '
                 f'fill="{ORANGE}22" stroke="{ORANGE}" stroke-width="1.5"/>')
    parts.append(f'<text x="580" y="{body_top + 174}" font-size="12" fill="{ORANGE}" text-anchor="middle" font-weight="700">Worker Node</text>')
    workers = ['kubelet', 'kube-proxy', 'Pod × N', 'Container Runtime']
    for i, w in enumerate(workers):
        col = i % 2
        row = i // 2
        x = 450 + col * 140
        y = body_top + 188 + row * 28
        parts.append(f'<rect x="{x}" y="{y - 14}" width="130" height="22" rx="3" fill="#FFFFFF" stroke="{ORANGE}"/>')
        parts.append(f'<text x="{x + 65}" y="{y + 2}" font-size="10" fill="{ORANGE}" text-anchor="middle">{esc(w)}</text>')
    # 核心概念
    parts.append(f'<text x="580" y="{body_top + 300}" font-size="12" fill="{GREEN}" text-anchor="middle" font-weight="700">核心概念</text>')
    concepts = ['Pod 最小调度单位', 'Deployment 副本控制', 'Service 服务发现', 'Ingress 七层路由', 'ConfigMap 配置']
    for i, c in enumerate(concepts):
        y = body_top + 320 + i * 18
        parts.append(f'<circle cx="450" cy="{y - 4}" r="4" fill="{GREEN}"/>')
        parts.append(f'<text x="464" y="{y}" font-size="11" fill="#37404F">{esc(c)}</text>')
    # Docker 优势
    parts.append(f'<text x="220" y="{body_top + 200}" font-size="13" fill="{BLUE}" text-anchor="middle" font-weight="700">Dockerfile 指令</text>')
    df = ['FROM 基础镜像', 'RUN 构建期执行', 'COPY/ADD 拷贝', 'CMD/ENTRYPOINT 启动', 'EXPOSE 暴露端口']
    for i, d in enumerate(df):
        y = body_top + 220 + i * 22
        parts.append(f'<circle cx="80" cy="{y - 4}" r="4" fill="{BLUE}"/>')
        parts.append(f'<text x="94" y="{y}" font-size="11" fill="#37404F">{esc(d)}</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_consistency(title, essence, body_top=110):
    """CAP / BASE / 一致性。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    # CAP 三角
    parts.append(f'<text x="400" y="{body_top + 16}" font-size="14" fill="{BLUE}" text-anchor="middle" font-weight="700">CAP 定理</text>')
    cx, cy, r = 200, body_top + 130, 80
    # C
    parts.append(f'<circle cx="{cx}" cy="{cy - r}" r="36" fill="{BLUE}22" stroke="{BLUE}" stroke-width="2"/>')
    parts.append(f'<text x="{cx}" y="{cy - r - 6}" font-size="14" fill="{BLUE}" text-anchor="middle" font-weight="700">C</text>')
    parts.append(f'<text x="{cx}" y="{cy - r + 12}" font-size="10" fill="#37404F" text-anchor="middle">一致性</text>')
    # A
    parts.append(f'<circle cx="{cx - r}" cy="{cy + r * 0.6}" r="36" fill="{GREEN}22" stroke="{GREEN}" stroke-width="2"/>')
    parts.append(f'<text x="{cx - r}" y="{cy + r * 0.6 - 6}" font-size="14" fill="{GREEN}" text-anchor="middle" font-weight="700">A</text>')
    parts.append(f'<text x="{cx - r}" y="{cy + r * 0.6 + 12}" font-size="10" fill="#37404F" text-anchor="middle">可用性</text>')
    # P
    parts.append(f'<circle cx="{cx + r}" cy="{cy + r * 0.6}" r="36" fill="{ORANGE}22" stroke="{ORANGE}" stroke-width="2"/>')
    parts.append(f'<text x="{cx + r}" y="{cy + r * 0.6 - 6}" font-size="14" fill="{ORANGE}" text-anchor="middle" font-weight="700">P</text>')
    parts.append(f'<text x="{cx + r}" y="{cy + r * 0.6 + 12}" font-size="10" fill="#37404F" text-anchor="middle">分区容错</text>')
    # 连线
    parts.append(f'<line x1="{cx}" y1="{cy - r + 36}" x2="{cx - r + 25}" y2="{cy + r * 0.6 - 25}" stroke="{GRAY}" stroke-width="1.5"/>')
    parts.append(f'<line x1="{cx}" y1="{cy - r + 36}" x2="{cx + r - 25}" y2="{cy + r * 0.6 - 25}" stroke="{GRAY}" stroke-width="1.5"/>')
    parts.append(f'<line x1="{cx - r + 36}" y1="{cy + r * 0.6}" x2="{cx + r - 36}" y2="{cy + r * 0.6}" stroke="{GRAY}" stroke-width="1.5"/>')
    parts.append(f'<text x="200" y="{body_top + 270}" font-size="11" fill="{RED}" text-anchor="middle" font-weight="700">三选二（网络分区必选 P）</text>')
    # BASE
    parts.append(f'<rect x="400" y="{body_top + 40}" width="340" height="170" rx="8" '
                 f'fill="{PURPLE}11" stroke="{PURPLE}" stroke-width="2"/>')
    parts.append(f'<text x="570" y="{body_top + 66}" font-size="14" fill="{PURPLE}" '
                 f'text-anchor="middle" font-weight="700">BASE (AP 系统妥协)</text>')
    base = [
        ('BA', 'Basically Available 基本可用'),
        ('S', 'Soft State 软状态'),
        ('E', 'Eventually Consistent 最终一致'),
    ]
    for i, (k, d) in enumerate(base):
        y = body_top + 92 + i * 36
        parts.append(f'<circle cx="420" cy="{y}" r="14" fill="{PURPLE}"/>')
        parts.append(f'<text x="420" y="{y + 5}" font-size="12" fill="#FFFFFF" text-anchor="middle" font-weight="700">{esc(k)}</text>')
        parts.append(f'<text x="445" y="{y + 5}" font-size="12" fill="#37404F">{esc(d)}</text>')
    # 一致性级别
    parts.append(f'<text x="570" y="{body_top + 240}" font-size="13" fill="{BLUE}" text-anchor="middle" font-weight="700">一致性级别（弱→强）</text>')
    levels = ['弱一致', '最终一致', '强一致', '线性一致']
    colors = [GREEN, BLUE, ORANGE, RED]
    for i, (l, c) in enumerate(zip(levels, colors)):
        x = 410 + i * 80
        parts.append(f'<rect x="{x}" y="{body_top + 260}" width="70" height="40" rx="6" fill="{c}22" stroke="{c}"/>')
        parts.append(f'<text x="{x + 35}" y="{body_top + 285}" font-size="11" fill="{c}" text-anchor="middle" font-weight="700">{esc(l)}</text>')
        if i > 0:
            parts.append(arrow(x - 6, body_top + 280, x, body_top + 280, color=GRAY))
    # 分布式协议
    parts.append(f'<text x="400" y="{body_top + 340}" font-size="13" fill="{GREEN}" text-anchor="middle" font-weight="700">'
                 f'一致性协议：Paxos / Raft (CP)  |  Gossip (AP)  |  2PC/3PC/TCC/Saga 分布式事务</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_microservice(title, essence, body_top=110):
    """微服务架构。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    # 网关
    parts.append(box(330, body_top + 10, 140, 40, 'API Gateway\n(Nginx/Spring Gateway)', fill=BLUE + '22', stroke=BLUE, font_size=12))
    # 4 业务服务
    services = [('用户服务', GREEN), ('订单服务', ORANGE), ('商品服务', PURPLE), ('支付服务', RED)]
    for i, (n, c) in enumerate(services):
        x = 60 + i * 175
        parts.append(box(x, body_top + 90, 160, 50, n, fill=c + '22', stroke=c, font_size=12))
        parts.append(arrow(400, body_top + 50, x + 80, body_top + 90, color=GRAY, dashed=True))
    # 中间件
    mws = [('注册中心\nNacos/Eureka', BLUE), ('配置中心\nApollo/Nacos', ORANGE),
           ('消息队列\nKafka/RabbitMQ', PURPLE), ('链路追踪\nSkyWalking/Zipkin', GREEN)]
    for i, (n, c) in enumerate(mws):
        x = 60 + i * 175
        parts.append(box(x, body_top + 180, 160, 50, n, fill=c + '22', stroke=c, font_size=11))
    # 数据层
    parts.append(f'<rect x="60" y="{body_top + 260}" width="680" height="60" rx="8" '
                 f'fill="{RED}11" stroke="{RED}" stroke-width="2"/>')
    parts.append(f'<text x="400" y="{body_top + 296}" font-size="13" fill="{RED}" text-anchor="middle" font-weight="700">'
                 f'数据隔离：每服务独立 DB（MySQL）+ Cache（Redis Cluster）+ ES</text>')
    # 优缺点
    parts.append(f'<rect x="60" y="{body_top + 340}" width="680" height="100" rx="8" '
                 f'fill="#FFFFFF" stroke="{GRAY}" stroke-width="1.5"/>')
    parts.append(f'<text x="80" y="{body_top + 364}" font-size="12" fill="{GREEN}" font-weight="700">优势</text>')
    parts.append(f'<text x="80" y="{body_top + 384}" font-size="11" fill="#37404F">独立部署 / 技术栈灵活 / 故障隔离 / 弹性伸缩</text>')
    parts.append(f'<text x="80" y="{body_top + 404}" font-size="11" fill="#37404F">团队边界清晰 / 单服务易维护</text>')
    parts.append(f'<text x="420" y="{body_top + 364}" font-size="12" fill="{RED}" font-weight="700">挑战</text>')
    parts.append(f'<text x="420" y="{body_top + 384}" font-size="11" fill="#37404F">分布式事务 / 服务发现 / 链路追踪</text>')
    parts.append(f'<text x="420" y="{body_top + 404}" font-size="11" fill="#37404F">数据一致性 / 运维复杂度 / 网络延迟</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)

def tpl_garbage_collector(title, essence, body_top=110):
    """GC 算法对比。"""
    return tpl_compare(title, essence, [
        ('标记-清除', ['Mark-Sweep', '产生内存碎片', '老年代早期', '效率中等']),
        ('复制', ['Copying', '无碎片 / 空间减半', '新生代主流', 'Survivor 用此']),
        ('标记-整理', ['Mark-Compact', '无碎片 / 慢', '老年代', 'Serial Old / Parallel Old']),
        ('分代收集', ['Generational', '新生代复制+老年代标记', '现代 JVM 默认', '适配对象生命周期']),
    ], body_top=body_top)

def tpl_generic_collection_or_core(title, essence, key_points, body_top=110):
    """通用兜底：竖向流程 + 关键要点（按 key_points 内容生成）。"""
    steps = []
    if key_points:
        steps = key_points[:6]
    else:
        steps = ['输入', '处理', '输出']
    # 控制每步不要太长
    return tpl_flow_vertical(title, essence, steps, body_top=body_top)


# ---------- 关键词 → 模板 路由 ----------

def select_template(id_, title, essence, key_points):
    """根据 id/title/essence/key_points 关键词选择最佳模板。返回 (tpl_func, kwargs)。"""
    text = ' '.join([
        id_, title or '', essence or '',
        ' '.join(key_points) if key_points else ''
    ]).lower()

    # 用 normalized 全角/中文
    cn_text = ' '.join([
        id_, title or '', essence or '',
        ' '.join(key_points) if key_points else ''
    ])

    # ===== 高优先级专用模板 =====

    # JVM 内存
    if any(k in cn_text for k in ['运行时数据', 'JVM内存', 'jvm 内存', '内存结构', '内存区域', '元空间', '方法区']) \
            or (any(k in text for k in ['jvm memory', 'jvm runtime']) and 'gc' not in text):
        return tpl_jvm_memory, {}

    # GC 流程
    if any(k in cn_text for k in ['垃圾回收', 'GC', 'minor gc', 'full gc', 'major gc', '新生代', '老年代回收']) \
            or any(k in text for k in ['garbage collect', 'minor gc', 'full gc']):
        if '算法' in cn_text or 'algorithm' in text or '比较' in cn_text:
            return tpl_garbage_collector, {}
        return tpl_gc_flow, {}

    # 线程状态
    if any(k in cn_text for k in ['线程状态', '线程的生命周期', '线程生命周期', '线程状态机']):
        return tpl_thread_states, {}

    # 线程池
    if any(k in cn_text for k in ['线程池', 'ThreadPoolExecutor', 'threadpool', '线程池工作', '线程池原理']):
        return tpl_thread_pool, {}

    # HashMap / HashSet
    if any(k in cn_text for k in ['HashMap', 'HashSet', '哈希表', '哈希冲突', '链表树化']):
        if 'concurrent' in text or 'ConcurrentHashMap' in cn_text:
            return tpl_concurrence_map, {}
        return tpl_hashmap, {}

    if 'ConcurrentHashMap' in cn_text or 'concurrenthashmap' in text:
        return tpl_concurrence_map, {}

    # TCP 三次握手
    if any(k in cn_text for k in ['三次握手', 'three-way', 'three way', 'tcp 连接', 'tcp连接']):
        return tpl_three_way_handshake, {}

    # 四次挥手
    if any(k in cn_text for k in ['四次挥手', 'four-way', 'tcp 断开', 'tcp断开', 'tcp 关闭']):
        return tpl_four_wave, {}

    # HTTPS / SSL
    if any(k in cn_text for k in ['HTTPS', 'SSL', 'TLS', '证书', '混合加密']):
        return tpl_https, {}

    # 进程 vs 线程
    if ('进程' in cn_text and '线程' in cn_text) and any(k in cn_text for k in ['区别', '对比', '比较']):
        return tpl_concurrence, {}

    # 锁分类
    if any(k in cn_text for k in ['锁的分类', 'java 锁', 'java锁', '锁类型', '乐观锁悲观锁', '公平锁']):
        return tpl_lock, {}

    # synchronized 锁升级
    if any(k in cn_text for k in ['synchronized', '锁升级', '偏向锁', '轻量级锁', '重量级锁']):
        return tpl_synchronized, {}

    # AQS
    if any(k in cn_text for k in ['AQS', 'AbstractQueuedSynchronizer', '同步器']):
        return tpl_aqs, {}

    # volatile
    if any(k in cn_text for k in ['volatile', '可见性', '内存屏障', '指令重排']):
        return tpl_volatle if False else tpl_volatile, {}

    # 死锁
    if any(k in cn_text for k in ['死锁', 'deadlock', '循环等待']):
        return tpl_lock_deadlock, {}

    # CAS / Atomic
    if any(k in cn_text for k in ['CAS', 'ABA', 'AtomicInteger', '原子操作', 'compareandswap']):
        return tpl_cas, {}

    # ThreadLocal
    if any(k in cn_text for k in ['ThreadLocal', 'threadlocal']):
        return tpl_threadlocal, {}

    # Spring IOC
    if any(k in cn_text for k in ['IOC', '控制反转', '依赖注入', 'ApplicationContext']):
        return tpl_spring_ioc, {}

    # Spring AOP
    if any(k in cn_text for k in ['AOP', '切面', '动态代理', 'aspectj', '切点']):
        return tpl_spring_aop, {}

    # Spring Bean 生命周期
    if any(k in cn_text for k in ['Bean 生命周期', 'Bean生命周期', 'Bean life']):
        return tpl_spring_bean, {}

    # SpringBoot
    if any(k in cn_text for k in ['SpringBoot', 'spring boot', '自动装配', 'SpringBootApplication']):
        return tpl_spring_boot, {}

    # 事务
    if any(k in cn_text for k in ['事务', 'ACID', '隔离级别', '传播行为', 'Transactional']):
        return tpl_transaction, {}

    # MyBatis
    if any(k in cn_text for k in ['MyBatis', 'mybatis', 'mapper', 'SqlSession']):
        return tpl_mybatis, {}

    # Redis 数据结构
    if any(k in cn_text for k in ['Redis', 'redis', 'ZSet', '跳表', 'sds']) and any(k in cn_text for k in ['数据结构', '类型', '数据类型', 'string', 'list', 'hash']):
        return tpl_redis_data_structure, {}

    # 缓存模式
    if any(k in cn_text for k in ['缓存一致', 'Cache Aside', '旁路缓存', '读写策略', '缓存模式']):
        return tpl_cache_pattern, {}

    # 消息队列
    if any(k in cn_text for k in ['RabbitMQ', 'Kafka', 'RocketMQ', '交换器', 'Exchange', '消息队列', '消息中间件']):
        return tpl_mq, {}

    # 单例模式
    if any(k in cn_text for k in ['单例模式', '单例', 'singleton', '饿汉', '懒汉', '双重检查']):
        return tpl_singleton, {}

    # 工厂模式
    if any(k in cn_text for k in ['工厂模式', 'Factory', '简单工厂', '抽象工厂']):
        return tpl_factory_pattern, {}

    # 观察者模式
    if any(k in cn_text for k in ['观察者模式', 'Observer', '发布订阅', '监听器']):
        return tpl_observer_pattern, {}

    # 策略模式
    if any(k in cn_text for k in ['策略模式', 'Strategy', 'if-else', 'if/else 消除']):
        return tpl_strategy_pattern, {}

    # 代理模式
    if any(k in cn_text for k in ['代理模式', 'Proxy', '静态代理', '动态代理']):
        if 'cglib' in text or 'JDK' in cn_text:
            return tpl_proxy_pattern, {}
        return tpl_proxy_pattern, {}

    # 设计模式总览 / 原则
    if any(k in cn_text for k in ['设计模式', '六大原则', 'solid', '开闭原则', '单一职责', '设计原则']):
        if any(k in cn_text for k in ['原则', 'principle', 'solid']):
            return tpl_design_principle, {}
        return tpl_design_pattern, {}

    # IO 模型
    if any(k in cn_text for k in ['BIO', 'NIO', 'AIO', 'IO 模型', '多路复用', 'epoll', 'Selector']):
        return tpl_io_model, {}

    # 类加载
    if any(k in cn_text for k in ['类加载', 'ClassLoader', '双亲委派', '类加载器']):
        return tpl_class_loader, {}

    # 字节码 / 执行流程
    if any(k in cn_text for k in ['字节码', 'javac', 'JIT', '解释执行', '编译执行', '跨平台', '一次编写']):
        return tpl_jvm_class_exec, {}

    # 泛型
    if any(k in cn_text for k in ['泛型', '类型擦除', '通配符', 'Type Erasure']):
        return tpl_generic, {}

    # 反射
    if any(k in cn_text for k in ['反射', 'Reflection', 'Class<?>', 'getDeclaredField']):
        return tpl_reflection, {}

    # 异常
    if any(k in cn_text for k in ['异常', 'Exception', 'Throwable', '受检', 'RuntimeException']):
        return tpl_exception, {}

    # String / 字符串常量池
    if any(k in cn_text for k in ['String 不可变', '字符串常量池', 'intern', 'StringBuilder', 'StringBuffer']):
        return tpl_string_pool, {}

    # 注解
    if any(k in cn_text for k in ['注解', 'Annotation', '元注解', 'Retention']):
        return tpl_annotation, {}

    # Lambda / 函数式
    if any(k in cn_text for k in ['Lambda', '函数式', 'Stream', '方法引用']):
        if 'Stream' in cn_text and 'API' in cn_text:
            return tpl_stream, {}
        return tpl_lambda, {}

    # SQL 索引
    if any(k in cn_text for k in ['B+ 树', 'B+树', 'B+tree', '索引', '聚簇索引', '二级索引', '回表']):
        return tpl_sql_index, {}

    # Tomcat
    if any(k in cn_text for k in ['Tomcat', 'tomcat', 'Catalina', 'Servlet 容器']):
        return tpl_tomcat, {}

    # Dubbo / RPC
    if any(k in cn_text for k in ['Dubbo', 'dubbo', 'RPC', 'rpc', '远程调用']):
        return tpl_dubbo, {}

    # 分布式锁
    if any(k in cn_text for k in ['分布式锁', 'Redlock', 'setnx', 'Redission']):
        return tpl_distributed_lock, {}

    # CAP / 一致性
    if any(k in cn_text for k in ['CAP', 'BASE', '一致性', 'Paxos', 'Raft', 'Gossip']):
        return tpl_consistency, {}

    # 微服务
    if any(k in cn_text for k in ['微服务', 'MicroService', '服务治理', 'Spring Cloud']):
        return tpl_microservice, {}

    # Docker / K8s
    if any(k in cn_text for k in ['Docker', 'Kubernetes', 'k8s', '容器', '镜像']):
        return tpl_docker_k8s, {}

    # OOP 四大特性
    if any(k in cn_text for k in ['面向对象', 'OOP', '封装继承多态', '多态', '四大特性']):
        return tpl_oop, {}

    # 集合框架层级
    if any(k in cn_text for k in ['Collection', '集合框架', 'List Set Map', 'Java 集合']):
        return tpl_collection_hierarchy, {}

    # ===== 中等优先级（基于语义形态） =====

    # 多步骤流程
    if any(k in cn_text for k in ['流程', '过程', '步骤', '生命周期', '工作原理', '原理']):
        return tpl_flow_vertical, {}

    # 对比 / 区别
    if any(k in cn_text for k in ['区别', '对比', '比较', '选型', 'VS', 'vs']):
        return tpl_two_phase, {}

    # 层级 / 分类
    if any(k in cn_text for k in ['分类', '类型', '层级', '层次', '包含', '组成', '结构']):
        return tpl_layers, {}

    return None  # 走通用兜底

# ---------- md / frontmatter 解析 ----------

FM_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)

def parse_frontmatter(raw):
    """简易解析 frontmatter（不依赖 PyYAML），返回 dict：id/essence/key_points/title。"""
    m = FM_RE.match(raw)
    if not m:
        return {}
    fm_text = m.group(1)
    data = {'key_points': []}
    cur_key = None
    for line in fm_text.split('\n'):
        if not line.strip() or line.strip().startswith('#'):
            continue
        # 顶层 key
        m1 = re.match(r'^([a-zA-Z_]+):\s*(.*)$', line)
        if m1 and not line.startswith(' '):
            key, val = m1.group(1), m1.group(2).strip()
            cur_key = key
            if val:
                data[key] = val.strip('"\'')
            else:
                data.setdefault(key, [] if key in ('key_points', 'memory_points', 'tags', 'follow_up') else '')
            continue
        # 嵌套子项
        if line.startswith(' '):
            stripped = line.strip()
            if stripped.startswith('- '):
                item = stripped[2:].strip()
                if cur_key in ('key_points', 'memory_points', 'tags', 'follow_up'):
                    data.setdefault(cur_key, []).append(item)
            elif ':' in stripped and cur_key == 'feynman':
                k, v = stripped.split(':', 1)
                data[k.strip()] = v.strip().strip('"\'')
    return data

def parse_title(raw):
    """提取第一个 H1。"""
    for line in raw.split('\n'):
        if line.startswith('# '):
            return line[2:].strip()
    return ''

def inject_svg_reference(raw, filename):
    """在 `## 记忆要点` 前插入/替换 `## 核心知识点图` 段。"""
    # 构造段
    section = (
        '\n## 核心知识点图\n\n'
        f'<img src="/interview-2026/images/diagram_java-core_{filename}.svg" '
        f'alt="核心知识点图" style="max-width:100%;height:auto;border:1px solid var(--border);'
        f'border-radius:8px;margin:1em 0;" />\n'
    )

    # 已存在 → 替换
    pattern = re.compile(
        r'\n?## 核心知识点图\s*\n.*?(?=\n## 记忆要点\b)',
        re.DOTALL
    )
    if pattern.search(raw):
        return pattern.sub(section, raw)

    # 不存在 → 在 `## 记忆要点` 前插入
    mem_pattern = re.compile(r'\n## 记忆要点\b')
    if mem_pattern.search(raw):
        return mem_pattern.sub(section + '\\n## 记忆要点', raw, count=1)

    # 兜底：附加在末尾
    return raw.rstrip() + '\n' + section

# ---------- 主流程 ----------

def process_file(md_path, write_md=True):
    raw = md_path.read_text(encoding='utf-8')
    fm = parse_frontmatter(raw)
    title = parse_title(raw)
    if not title:
        title = fm.get('id', md_path.stem)
    essence = fm.get('essence', '')
    key_points = fm.get('key_points', [])

    sel = select_template(fm.get('id', ''), title, essence, key_points)
    if sel is None:
        svg = tpl_generic_collection_or_core(title, essence, key_points)
    else:
        fn, kw = sel
        try:
            svg = fn(title, essence, **kw)
        except Exception as e:
            svg = tpl_generic_collection_or_core(title, essence, key_points)

    # 写 SVG
    svg_path = IMG_DIR / f'diagram_java-core_{md_path.stem}.svg'
    svg_path.write_text(svg, encoding='utf-8')

    # 写 md
    if write_md:
        new_raw = inject_svg_reference(raw, md_path.stem)
        if new_raw != raw:
            md_path.write_text(new_raw, encoding='utf-8')

    return svg_path.name

def main():
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    argv = sys.argv[1:]
    if argv:
        files = []
        for a in argv:
            p = QDIR / (a if a.endswith('.md') else a + '.md')
            if p.exists():
                files.append(p)
            else:
                print(f'[WARN] not found: {p}')
    else:
        files = sorted(QDIR.glob('*.md'))

    total = len(files)
    print(f'[INFO] processing {total} files')
    ok = 0
    fallback = 0
    for i, p in enumerate(files, 1):
        try:
            name = process_file(p)
            ok += 1
            if i % 30 == 0 or i == total:
                print(f'  [{i}/{total}] done')
        except Exception as e:
            print(f'[ERR] {p.name}: {e}')
    print(f'[DONE] success={ok}/{total}, fallback to generic={fallback}')

if __name__ == '__main__':
    main()
