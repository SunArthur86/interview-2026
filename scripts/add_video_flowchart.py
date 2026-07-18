#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为 interview-2026 项目指定目录下每道面试题的「## 视频脚本」段表格之后，
追加一个 `### 视频流程图` 子段（含 mermaid flowchart LR）。

处理逻辑:
1. 定位每个 `## 视频脚本` 起始位置（行首严格匹配 `## 视频脚本`）。
2. 找到该段结束位置 = 下一个 `## ` 标题或文件末尾。
3. 若该结束位置之前紧邻处已经存在 `### 视频流程图`，则跳过（幂等）。
4. 否则在该段表格末尾之后插入 `### 视频流程图` + mermaid 代码块。
5. mermaid 节点标签尽量从文件中提取该题核心知识点：
   - 标题（第一个 # H1）
   - 记忆要点（## 记忆要点 / ## 核心要点 下的要点）
   - 核心流程图节点（## 核心流程图 / ## 流程图）
   - 视频脚本表格的「讲解要点」列
6. classDef 配色: 开场=橙、概念=蓝、深入=绿、实战=紫、总结=灰。
"""

import os
import re
import sys
import html
from collections import defaultdict

# === 配置 ===
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUESTIONS_DIR = os.path.join(BASE_DIR, 'questions')
TARGET_DIRS = [
    'java-core', 'concurrent', 'jvm', 'framework', 'database',
    'distributed', 'middleware', 'scenario', 'java', 'algorithm',
    'network', 'frontend', 'other', 'system-design',
]

# 视频脚本段表格的标题列关键字（用于过滤无意义占位）
HOOK_KEYS = ('开场钩子', '开场', '钩子')
CORE_KEYS = ('核心定义', '核心概念', '概念')
WRAP_KEYS = ('收尾', '总结', '总结卡')


# === 工具函数 ===

def safe_label(text, maxlen=24):
    """把任意文本清洗为 mermaid 节点标签里安全的字符串。"""
    if not text:
        return ''
    # 去掉前后空白和常见 markdown 标记
    t = text.strip()
    # 去掉结尾的句号/省略号，简化
    t = re.sub(r'[。.……\-—]+$', '', t).strip()
    # 替换 mermaid 中会引起问题的字符
    t = t.replace('"', "'").replace('[', '【').replace(']', '】')
    t = t.replace('(', '（').replace(')', '）')
    t = t.replace('{', '｛').replace('}', '｝')
    t = t.replace('|', '/').replace('<', '《').replace('>', '》')
    t = t.replace('#', '').replace('\n', ' ').replace('\r', '')
    # 多空白合并
    t = re.sub(r'\s+', ' ', t).strip()
    if len(t) > maxlen:
        t = t[:maxlen] + '…'
    return t


def extract_title(content):
    """提取第一个 H1 标题（去掉 # 号）。"""
    m = re.search(r'^#\s+(.+?)\s*$', content, re.MULTILINE)
    if m:
        return safe_label(m.group(1), maxlen=30)
    return ''


def extract_memory_points(content):
    """提取「## 记忆要点」/「## 核心要点」/「## 核心考点」下的要点列表（最多 3 条）。"""
    # 定位目标段
    pattern = re.compile(
        r'^## (?:记忆要点|核心要点|核心考点|要点)[^\n]*\n(.*?)(?=^##\s|\Z)',
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(content)
    if not m:
        return []
    section = m.group(1)
    points = []
    for line in section.splitlines():
        s = line.strip()
        if not s:
            continue
        # 去掉前导的列表符号 - * + 或 1. 之类
        s2 = re.sub(r'^[-*+]\s+', '', s)
        s2 = re.sub(r'^\d+\.\s+', '', s2)
        s2 = re.sub(r'^\*\*([^*]+)\*\*[：:—\-].*$', r'\1', s2).strip()
        if s2 and len(s2) >= 2:
            lbl = safe_label(s2, maxlen=26)
            if lbl:
                points.append(lbl)
        if len(points) >= 3:
            break
    return points


def extract_flow_nodes(content):
    """从 `## 核心流程图` / `## 流程图` / `## 核心架构图` 的 mermaid 节点定义中提取关键词。"""
    nodes = []
    pattern = re.compile(
        r'^## (?:核心流程图|流程图|核心架构图|架构图)[^\n]*\n(.*?)(?=^##\s|\Z)',
        re.MULTILINE | re.DOTALL,
    )
    for m in pattern.finditer(content):
        section = m.group(1)
        # 提取形如  ID["..."]  或  ID["...<br/>..."]  的节点标签
        for nm in re.finditer(r'\b([A-Za-z_][A-Za-z0-9_]*)\s*\[\s*"([^"]+)"', section):
            label = nm.group(2)
            label = re.sub(r'<br\s*/?>', ' ', label)
            label = safe_label(label, maxlen=24)
            if label and label not in nodes:
                nodes.append(label)
            if len(nodes) >= 6:
                return nodes
    return nodes


def extract_video_table_points(script_section):
    """从单个 `## 视频脚本` 段表格的「讲解要点」列提取要点。"""
    points = []
    # 找表格行: | ... | ... | ... | (讲解要点) |
    for line in script_section.splitlines():
        s = line.rstrip()
        if not s.startswith('|'):
            continue
        cells = [c.strip() for c in s.strip('|').split('|')]
        if len(cells) < 4:
            continue
        last = cells[-1]
        # 跳过分隔行 |---|---|
        if re.match(r'^[-:\s]+$', last):
            continue
        # 跳过表头
        if last in ('讲解要点',) or '讲解要点' == last:
            continue
        lbl = safe_label(last, maxlen=22)
        if lbl and lbl not in points:
            points.append(lbl)
    return points


def pick_concept_points(title, memory, flownodes, table_points):
    """
    综合各个来源，挑选 2 个「概念/深入」节点标签（不包含开场与收尾）。
    优先级: 记忆要点 > 流程图节点 > 视频脚本表格要点 > 标题切片。
    （记忆要点最贴近题目核心，表格要点常为通用占位如「要点1」「核心定义」。）
    """
    candidates = []
    seen = set()

    # 通用占位标签黑名单（来自视频脚本表格的讲解要点列）
    GENERIC_LABELS = {
        '核心定义', '核心概念', '概念', '要点1', '要点2', '要点3',
        '要点4', '机制', '原理', '机制原理', '要点', '知识点',
    }

    def add(src_list, limit, allow_generic=False):
        for x in src_list:
            if not x:
                continue
            # 过滤开场/收尾类标签
            if any(k in x for k in HOOK_KEYS + WRAP_KEYS):
                continue
            # 过滤通用占位标签（除非 allow_generic）
            if not allow_generic and x in GENERIC_LABELS:
                continue
            if x in seen:
                continue
            seen.add(x)
            candidates.append(x)
            if len(candidates) >= limit:
                return

    add(memory, 2)
    add(flownodes, 2)
    add(table_points, 2)
    # 兜底：若仍然不够，放宽通用标签限制
    if len(candidates) < 2:
        add(table_points, 2, allow_generic=True)
        add(memory, 2, allow_generic=True)
    if not candidates and title:
        candidates.append(title)
    return candidates[:2]


# === mermaid 生成 ===

CLASS_DEF_BLOCK = """    classDef intro fill:#FF9800,color:#fff,stroke:#F57C00,stroke-width:2px
    classDef core fill:#2196F3,color:#fff,stroke:#1976D2,stroke-width:2px
    classDef deep fill:#4CAF50,color:#fff,stroke:#388E3C,stroke-width:2px
    classDef practice fill:#9C27B0,color:#fff,stroke:#7B1FA2,stroke-width:2px
    classDef wrap fill:#607D8B,color:#fff,stroke:#455A64,stroke-width:2px"""


def build_video_flowchart(title, memory, flownodes, table_points):
    """根据素材生成一个 mermaid flowchart LR 字符串（含 ```mermaid 围栏）。"""
    # 开场：用标题或"开场钩子"
    intro_label = title if title else '开场钩子'

    # 概念/深入/实战 三个讲解节点
    pts = pick_concept_points(title, memory, flownodes, table_points)
    # 保证至少 3 个讲解节点
    defaults = ['核心概念', '原理机制', '代码实战']
    while len(pts) < 3:
        idx = len(pts)
        d = defaults[idx] if idx < len(defaults) else f'要点{idx+1}'
        if d not in pts:
            pts.append(d)
        else:
            break
    concept_label = pts[0]
    deep_label = pts[1]
    practice_label = pts[2]

    # 收尾
    wrap_label = '总结回顾'

    # mermaid 里节点 ID 必须是字母/数字/下划线
    # 直接用 A/B/C/D/E
    lines = []
    lines.append('```mermaid')
    lines.append('flowchart LR')
    lines.append('')
    lines.append('    subgraph Intro["引入"]')
    lines.append(f'        A["{intro_label}"]:::intro')
    lines.append('    end')
    lines.append('')
    lines.append('    subgraph Core["讲解"]')
    lines.append(f'        B["{concept_label}"]:::core')
    lines.append(f'        C["{deep_label}"]:::deep')
    lines.append('    end')
    lines.append('')
    lines.append('    subgraph Practice["实战"]')
    lines.append(f'        D["{practice_label}"]:::practice')
    lines.append('    end')
    lines.append('')
    lines.append('    subgraph Wrap["收尾"]')
    lines.append(f'        E["{wrap_label}"]:::wrap')
    lines.append('    end')
    lines.append('')
    lines.append('    A --> B --> C --> D --> E')
    lines.append('')
    lines.append(CLASS_DEF_BLOCK)
    lines.append('```')
    return '\n'.join(lines)


# === 插入逻辑 ===

HEADER_RE = re.compile(r'^## ', re.MULTILINE)
SCRIPT_HEADER_RE = re.compile(r'^## 视频脚本\s*$', re.MULTILINE)


def find_script_section_end(content, header_start):
    """给定一个 `## 视频脚本` 的起始位置，返回该段的结束位置（下一个 ## 或 EOF）。

    从 header_start+1 开始搜索，避免匹配到本行的 `## 视频脚本` 标题。
    """
    m = HEADER_RE.search(content, header_start + 1)
    end = m.start() if m else len(content)
    return end


def has_existing_flowchart(content, header_start, section_end):
    """检查该 `## 视频脚本` 段内是否已经存在 `### 视频流程图`。

    通过扫描从 header_start 到 section_end 的整段内容来判断。
    """
    section = content[header_start:section_end]
    return '### 视频流程图' in section


def trim_trailing_ws(text):
    """去掉尾部空白行，返回 (body, trailing_ws_str)。"""
    m = re.search(r'(\s*)$', text)
    if m:
        return text[:m.start()], m.group(1)
    return text, ''


def process_file(path, dry_run=False):
    """处理单个文件，返回 (status, message)。status: done / skipped / error。"""
    with open(path, encoding='utf-8') as f:
        content = f.read()

    # 全文素材（用于第一个脚本段；多段文件共享，可接受）
    title = extract_title(content)
    memory = extract_memory_points(content)
    flownodes = extract_flow_nodes(content)

    # 找所有 `## 视频脚本` 段
    matches = list(SCRIPT_HEADER_RE.finditer(content))
    if not matches:
        return 'skipped', 'no 视频脚本 section'

    # 从后往前插入，避免位置偏移
    inserts = []  # (insert_pos, block_text)
    stats_per_file = {'sections': 0, 'skipped_existing': 0}

    for m in matches:
        section_end = find_script_section_end(content, m.start())
        # 定位插入点：段尾最后一个非空白位置之后
        # 找该段最后一段内容（去掉尾部纯空白）
        body = content[:section_end]
        # body 的末尾可能是空白，我们要在最后非空白处之后插入
        # 计算需要插入的锚点
        # 先看该段内是否已有 视频流程图
        if has_existing_flowchart(content, m.start(), section_end):
            stats_per_file['skipped_existing'] += 1
            continue

        # 提取该段表格要点
        section_body = content[m.end():section_end]
        table_points = extract_video_table_points(section_body)

        block = build_video_flowchart(title, memory, flownodes, table_points)
        full_block = '\n\n### 视频流程图\n\n' + block + '\n'

        inserts.append((section_end, full_block))
        stats_per_file['sections'] += 1

    if not inserts:
        return 'skipped', 'all sections already have 视频流程图'

    # 从后往前应用插入（保持位置有效）
    inserts.sort(key=lambda x: x[0], reverse=True)
    new_content = content
    # 插入策略：
    #   - 在 section_end 之前找到「最后一个非空行」的行尾位置 anchor。
    #   - 在 anchor 之后插入 block（block 自带前导 \n\n 形成空行、结尾 \n）。
    #   - anchor 与 section_end 之间原有的空白行（通常是下一个 ## 标题前的分隔空行）
    #     会被原样保留在 block 之后，从而保证 block 与后续 ## 标题之间仍有空行。
    for pos, block in inserts:
        before = new_content[:pos]
        after = new_content[pos:]
        # 找 before 中最后一个非空、非纯空白行的位置（行尾之后）
        # 即倒着找第一个非空白字符，然后定位到该行末尾（含换行符）。
        stripped = before.rstrip()
        if not stripped:
            # 整段都是空白（罕见），直接在 pos 处插入
            anchor = pos
        else:
            anchor = len(stripped)
        # 去掉 block 自身前导换行，由我们显式控制
        insert_text = '\n\n' + block.lstrip('\n')
        new_content = new_content[:anchor] + insert_text + new_content[anchor:]

    if new_content != content:
        if not dry_run:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
        return 'done', f'inserted {len(inserts)} block(s)'
    return 'skipped', 'no change'


def main():
    dry = '--dry-run' in sys.argv
    target_only = None
    for arg in sys.argv[1:]:
        if arg.startswith('--dir='):
            target_only = arg.split('=', 1)[1]

    dirs = [target_only] if target_only else TARGET_DIRS

    stats = defaultdict(int)
    files_per_dir = defaultdict(int)
    details = defaultdict(lambda: defaultdict(int))

    for d in dirs:
        base = os.path.join(QUESTIONS_DIR, d)
        if not os.path.isdir(base):
            print(f'[warn] 目录不存在: {base}')
            continue
        for fn in sorted(os.listdir(base)):
            if not fn.endswith('.md'):
                continue
            path = os.path.join(base, fn)
            files_per_dir[d] += 1
            try:
                status, msg = process_file(path, dry_run=dry)
            except Exception as e:
                status, msg = 'error', f'{type(e).__name__}: {e}'
            stats[status] += 1
            details[d][status] += 1

    # 打印统计
    prefix = '[DRY-RUN] ' if dry else ''
    print(f'\n{prefix}===== 处理统计 =====')
    total_files = sum(files_per_dir.values())
    print(f'扫描文件总数: {total_files}')
    for status in ['done', 'skipped', 'error']:
        print(f'  {status}: {stats[status]}')
    print(f'\n{prefix}===== 分目录统计 =====')
    print(f'{"目录":<16}{"文件":>6}{"done":>8}{"skipped":>10}{"error":>8}')
    for d in dirs:
        det = details[d]
        print(f'{d:<16}{files_per_dir[d]:>6}'
              f'{det.get("done",0):>8}{det.get("skipped",0):>10}{det.get("error",0):>8}')


if __name__ == '__main__':
    main()
