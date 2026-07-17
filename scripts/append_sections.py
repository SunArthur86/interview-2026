#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为 distributed/ 和 scenario/ 目录下未处理的 .md 面试题文件追加
`## 结构化回答` 和 `## 视频脚本` 两个段落。

内容从已有 frontmatter (feynman.key_points / memory_points / essence / analogy / follow_up)
和正文小节标题中提炼，不编造。
"""

import os
import re
import sys
import yaml

ROOT = '/Users/sunqingguang/hermes/opt/projects/interview-java'
TARGET_DIRS = ('questions/distributed', 'questions/scenario')

# 难度对应：视频时长 + 表格行数（参考 interview-ai 语料分布 + 用户规范）
DIFF_CONFIG = {
    'L1': {'duration': '1 分 30 秒', 'rows': 4},
    'L2': {'duration': '2 分钟',      'rows': 4},
    'L3': {'duration': '3 分钟',      'rows': 5},
    'L4': {'duration': '4 分钟',      'rows': 6},
    'L5': {'duration': '4 分钟',      'rows': 6},
}
DEFAULT_DIFF = 'L2'


def clean_inline(text):
    """把单个要点清洗成可直接念的一行口语化文字。"""
    if not text:
        return ''
    t = text.strip().strip('-').strip()
    # 去掉行内 markdown 粗体/反引号，便于口播
    t = re.sub(r'\*\*([^*]+)\*\*', r'\1', t)
    t = re.sub(r'`([^`]+)`', r'\1', t)
    # 括号统一为半角
    t = t.replace('（', '(').replace('）', ')')
    # 多空格合并
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def extract_title(content):
    m = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return ''


def extract_h3_headings(content):
    """从正文中提取 ### 小节标题（去掉 frontmatter 区块和已知公共小节）。"""
    body = content
    if body.startswith('---'):
        parts = body.split('---', 2)
        body = parts[2] if len(parts) >= 3 else body
    headings = re.findall(r'^###\s+(.+)$', body, re.MULTILINE)
    skip_pat = re.compile(
        r'^(常见考点|记忆要点|架构图|核心流程|性能优化|实战案例|扩展功能|'
        r'整体架构|场景分析|关键代码|代码示例|状态流转|对比表)'
    )
    out = []
    for h in headings:
        c = clean_inline(h)
        if c and not skip_pat.match(c):
            out.append(c)
    return out[:4]


def short_essence(essence, title):
    base = clean_inline(essence) or title
    base = re.sub(r'[。\.]+$', '', base)
    return base


def pick_key_points(feynman, memory_points, h3_headings):
    """整合 key_points / memory_points / h3 三类素材，返回最多 3 个 (标题, 描述) 对。"""
    raw_points = []
    kp = feynman.get('key_points') if feynman else None
    if kp:
        raw_points.extend(kp)

    if memory_points:
        existing = set(clean_inline(p) for p in raw_points)
        for mp in memory_points:
            c = clean_inline(mp)
            if c and c not in existing:
                raw_points.append(mp)

    if h3_headings and len(raw_points) < 3:
        existing = set(clean_inline(p) for p in raw_points)
        for h in h3_headings:
            if h and h not in existing:
                raw_points.append(h)
            if len(raw_points) >= 5:
                break

    result = []
    seen = set()
    for p in raw_points:
        c = clean_inline(p)
        if not c or c in seen:
            continue
        seen.add(c)
        result.append(split_title_desc(c))
        if len(result) >= 5:
            break
    return result[:3]


def split_title_desc(point):
    """拆为 (短标题 2-12字, 描述)。"""
    p = point
    for sep in ['：', ':']:
        if sep in p:
            left, right = p.split(sep, 1)
            left = left.strip()
            right = right.strip().strip('。.')
            title = compress_title(left)
            desc = right if right else left
            return title, desc
    title = extract_leading_subject(p)
    return title, p


# 常见中文动词/虚词，用于切分前置主语
_SUBJECT_STOP = re.compile(
    r'(是为|用于|保证|防止|避免|支持|实现|通过|采用|利用|基于|根据|当|若|如果|'
    r'因为|所以|主要|核心|关键|为了|让|使|将|并|且|，|,|的|是|有|能|会|可|'
    r'指|代表|包含|包括|分为|属于|对应|类似|帮助|确保|完成|处理|解决)'
)


def extract_leading_subject(text):
    """从一句话里提取前置主语/核心名词短语作为短标题。"""
    t = text.strip()
    t = re.sub(r'^(因为|所以|如果|当|核心|关键|主要|要点)[：:]*', '', t)
    t = re.sub(r'[，,。.；;]+$', '', t)
    m = _SUBJECT_STOP.search(t)
    if m and m.start() >= 2:
        head = t[:m.start()].strip()
        head = re.sub(r'^的+|的+$', '', head).strip()
        if 2 <= len(head) <= 12:
            return head
        if len(head) > 12:
            return truncate_safe(head, 10)
    # 停用词在句首或没匹配：去掉句首动词前缀，取剩下的核心短语
    stripped = _SUBJECT_STOP.sub('|', t, count=1)
    if '|' in stripped:
        after = stripped.split('|', 1)[1].strip()
        after = re.sub(r'^的+|的+$', '', after).strip()
        if 2 <= len(after) <= 12:
            return after
        if len(after) > 12:
            return truncate_safe(after, 10)
    if len(t) <= 12:
        return t
    # 硬截断到 10 字，但避免把英文单词劈开：在 ASCII 边界往前回退
    return truncate_safe(t, 10)


def truncate_safe(text, max_len):
    """硬截断到 max_len 字符；若末尾落在 ASCII 单词中间，回退到单词起点。"""
    if len(text) <= max_len:
        return text
    cut = text[:max_len]
    # 若最后一个字符是 ASCII 字母/数字，回退到最后一个非 ASCII 边界
    if cut and re.match(r'[A-Za-z0-9]', cut[-1]):
        # 找最后一段连续 ASCII 的起点
        m = re.search(r'[A-Za-z0-9]+$', cut)
        if m and m.start() >= 4:  # 至少保留 4 个中文字符再回退
            cut = cut[:m.start()].rstrip()
        # 如果回退后太短，就保留整段 ASCII 直到下一个分隔符
        elif m:
            ext = re.search(r'^[A-Za-z0-9]+', text[max_len:])
            if ext:
                cut = cut + ext.group(0)
    return cut


def compress_title(s):
    """把任意短语压成 4-12 字的精炼标题。"""
    s = s.strip().strip('。.，,；;')
    s = re.sub(r'^(因为|所以|如果|当|核心|关键|主要|核心要点|要点|根因)[：:]*', '', s)
    s = re.sub(r'[，,。.；;]+$', '', s)
    if len(s) <= 10:
        return s
    for sep in ['、', '，', ',', ' ']:
        if sep in s:
            head = s.split(sep)[0].strip()
            if 2 <= len(head) <= 12:
                return head
    if len(s) > 10:
        return s[:8]
    return s


def build_elevator(essence, analogy, title, key_pairs):
    """30 秒电梯演讲整段。"""
    base = short_essence(essence, title)
    parts = [base + '。']

    a = clean_inline(analogy)
    if a:
        a = re.sub(r'[。\.]+$', '', a)
        parts.append('打比方——' + a + '。')

    if key_pairs:
        first_desc = key_pairs[0][1]
        first_desc = re.sub(r'[。\.]+$', '', first_desc)
        parts.append('落到工程上，' + first_desc + '。')

    text = ''.join(parts)
    if len(text) > 150:
        text = text[:147] + '...'
    return text


def build_followup_hook(follow_up):
    """收尾的追问钩子，口语化。"""
    if not follow_up:
        return '以上三点都能配合实战聊。我可以展开任一要点，您想先深入哪一块？'
    fu = []
    for q in follow_up[:2]:
        c = clean_inline(q)
        if not c:
            continue
        # 去掉「——答案」之类自带答复的部分，只保留问题
        for sep in ['——', '—']:
            if sep in c:
                c = c.split(sep)[0].strip()
                break
        c = re.sub(r'[？?]+$', '', c).strip()
        if c:
            fu.append('「' + c + '」')
    if not fu:
        return '以上三点都能配合实战聊。我可以展开任一要点，您想先深入哪一块？'
    return '这几个点都能配合实战展开。您想继续聊哪个追问——比如 ' + ' 或者 '.join(fu) + '？'


def build_structured_answer(fm, title, h3_headings):
    feynman = fm.get('feynman') or {}
    essence = feynman.get('essence')
    analogy = feynman.get('analogy')
    memory_points = fm.get('memory_points') or []
    follow_up = fm.get('follow_up') or []

    key_pairs = pick_key_points(feynman, memory_points, h3_headings)
    while len(key_pairs) < 3 and memory_points:
        c = clean_inline(memory_points[len(key_pairs) % len(memory_points)])
        if c:
            key_pairs.append(split_title_desc(c))
        if len(key_pairs) >= 3:
            break
    while len(key_pairs) < 3:
        key_pairs.append(('核心要点', '见正文'))

    elevator = build_elevator(essence, analogy, title, key_pairs)
    hook = build_followup_hook(follow_up)

    lines = []
    lines.append('## 结构化回答')
    lines.append('')
    lines.append('**30 秒电梯演讲：** ' + elevator)
    lines.append('')
    lines.append('**展开框架：**')
    for i, (t, d) in enumerate(key_pairs[:3], 1):
        lines.append(f'{i}. **{t}** — {d}')
    lines.append('')
    lines.append('**收尾：** ' + hook)
    lines.append('')
    return '\n'.join(lines)


def compress_topic(title):
    """把 H1 标题压成画面字幕可用的短主题。"""
    t = title.strip()
    t = re.sub(r'^【[^】]*】\s*', '', t)
    t = re.sub(r'^(如何设计一个|如何设计|什么是|为什么|怎么|如何|讲一讲|说一下|聊一聊|请简述|简述)', '', t)
    qm = re.search(r'[？?]', t)
    if qm:
        head = t[:qm.start()].strip()
        if 4 <= len(head) <= 24:
            t = head
        else:
            t = t[:qm.start()].strip() or t
    t = re.sub(r'[？?。.！!]+$', '', t)
    t = re.sub(r'(是什么|怎么办|为什么)$', '', t)
    if len(t) > 20:
        t = t[:20]
    return t.strip()


def build_timestamps(rows, total_sec):
    stamps = ['0:00']
    if rows == 1:
        return stamps
    if rows <= 2:
        stamps.append(fmt_ts(total_sec - 10))
        return stamps
    body_sec = total_sec - 15
    for i in range(1, rows - 1):
        sec = int(body_sec * i / (rows - 1))
        stamps.append(fmt_ts(sec))
    stamps.append(fmt_ts(total_sec - 10))
    return stamps


def fmt_ts(sec):
    sec = max(0, int(sec))
    m = sec // 60
    s = sec % 60
    if m == 0:
        return f'0:{s:02d}'
    return f'{m}:{s:02d}'


def build_script_rows(title, essence, analogy, structured_pairs,
                      memory_points, h3_headings, rows, difficulty):
    topic = title or '本期主题'

    if difficulty in ('L4', 'L5'):
        opening_say = f'"{topic}，30 秒讲清楚核心。"'
    elif difficulty == 'L3':
        opening_say = f'"{topic}，这题我会分三步讲。"'
    else:
        opening_say = f'"{topic}，一分钟讲透。"'
    row_opening = (
        f'标题卡：{topic}',
        opening_say,
        '开场钩子'
    )

    e = clean_inline(essence) or topic
    e = re.sub(r'[。\.]+$', '', e)
    row_essence = (
        '概念定义动画',
        f'"一句话：{e}。"',
        '核心定义'
    )

    a = clean_inline(analogy)
    if a:
        a = re.sub(r'[。\.]+$', '', a)
        row_analogy = (
            '生活类比动画',
            f'"打个比方——{a}。"',
            '核心类比'
        )
    else:
        row_analogy = row_essence

    middle = []
    pool = []
    for (t, d) in structured_pairs:
        if d:
            pool.append((compress_title(t) or '要点', d))
    for mp in memory_points:
        c = clean_inline(mp)
        if c and c not in [p[1] for p in pool]:
            pool.append((compress_title(c), c))
    for h in h3_headings:
        if h and h not in [p[0] for p in pool] and h not in [p[1] for p in pool]:
            pool.append((compress_title(h), h))

    if rows <= 4:
        n_middle = 1
    elif rows == 5:
        n_middle = 2
    else:
        n_middle = 3

    for i in range(n_middle):
        if i < len(pool):
            t, d = pool[i]
            d_clean = re.sub(r'[。\.]+$', '', d)
            middle.append((
                f'{t} 图解',
                f'"{d_clean}。"',
                t
            ))
        else:
            middle.append((
                '要点图解',
                '"具体细节见正文展开。"',
                '要点补充'
            ))

    ending = (
        '总结卡',
        '"记好这几条，面试不慌。下期见。"',
        '收尾'
    )

    if rows == 5:
        return [row_opening, row_essence, row_analogy] + middle[:2] + [ending]
    elif rows == 6:
        return [row_opening, row_essence, row_analogy] + middle[:3] + [ending]
    elif rows <= 4:
        return [row_opening, row_analogy, row_essence] + middle[:1] + [ending]
    return [row_opening, row_essence, row_analogy] + middle + [ending]


def build_video_script(fm, title, h3_headings, structured_pairs):
    difficulty = fm.get('difficulty', DEFAULT_DIFF)
    cfg = DIFF_CONFIG.get(difficulty, DIFF_CONFIG[DEFAULT_DIFF])
    duration = cfg['duration']
    rows = cfg['rows']

    feynman = fm.get('feynman') or {}
    essence = feynman.get('essence')
    analogy = feynman.get('analogy')
    memory_points = fm.get('memory_points') or []

    short_topic = compress_topic(title)

    if duration == '1 分 30 秒':
        total_sec = 90
    elif duration == '2 分钟':
        total_sec = 120
    elif duration == '3 分钟':
        total_sec = 180
    else:
        total_sec = 240

    timestamps = build_timestamps(rows, total_sec)

    script_rows = build_script_rows(
        title=short_topic,
        essence=essence,
        analogy=analogy,
        structured_pairs=structured_pairs,
        memory_points=memory_points,
        h3_headings=h3_headings,
        rows=rows,
        difficulty=difficulty,
    )

    lines = []
    lines.append('## 视频脚本')
    lines.append('')
    lines.append(f'> 预计时长：{duration} | 由浅入深')
    lines.append('')
    lines.append('| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |')
    lines.append('|------|----------|----------|----------|')
    for ts, (vis, say, key) in zip(timestamps, script_rows):
        lines.append(f'| {ts} | {vis} | {say} | {key} |')
    lines.append('')
    return '\n'.join(lines)


def process_file(path, dry_run=False):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    if '## 结构化回答' in content:
        return ('skip', '已有结构化回答')

    if not content.startswith('---'):
        return ('skip', '无 frontmatter')
    parts = content.split('---', 2)
    if len(parts) < 3:
        return ('skip', 'frontmatter 损坏')
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except Exception as e:
        return ('skip', f'YAML 解析失败: {e}')

    title = extract_title(content)
    h3_headings = extract_h3_headings(content)

    sa_text = build_structured_answer(fm, title, h3_headings)

    feynman = fm.get('feynman') or {}
    memory_points = fm.get('memory_points') or []
    structured_pairs = pick_key_points(feynman, memory_points, h3_headings)

    vs_text = build_video_script(fm, title, h3_headings, structured_pairs)

    body = content.rstrip() + '\n\n'
    new_content = body + sa_text + '\n' + vs_text

    if dry_run:
        return ('dry', new_content)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    return ('ok', None)


def main():
    dry = '--dry' in sys.argv
    target_files = []
    for d in TARGET_DIRS:
        full = os.path.join(ROOT, d)
        for root, dirs, files in os.walk(full):
            for f in sorted(files):
                if f.endswith('.md'):
                    target_files.append(os.path.join(root, f))

    counts = {'ok': 0, 'skip': 0, 'dry': 0, 'err': 0}
    sample_outputs = []
    for i, path in enumerate(target_files):
        try:
            status, msg = process_file(path, dry_run=dry)
        except Exception as e:
            counts['err'] += 1
            print(f'ERR {path}: {e}')
            continue
        counts[status] = counts.get(status, 0) + 1
        if status == 'ok' and len(sample_outputs) < 3:
            with open(path) as f:
                sample_outputs.append((path, f.read()))
        if status == 'skip' and i < 5:
            print(f'SKIP {path}: {msg}')

    print('\n=== 处理统计 ===')
    for k, v in counts.items():
        print(f'  {k}: {v}')
    print(f'  total scanned: {len(target_files)}')

    if dry and counts.get('dry', 0) > 0:
        print('\n(dry-run 模式，未写文件)')

    return sample_outputs


if __name__ == '__main__':
    main()
