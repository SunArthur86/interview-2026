#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为 concurrent / database 分类的每道面试题生成核心知识点 SVG 静态精绘图。
- 通过 coding plan 额度（Anthropic 协议，GLM-5.2）批量调用 LLM 设计专属 SVG。
- SVG 保存到 public/images/diagram_<category>_<filename>.svg
- 在 md 中 `## 记忆要点` 前插入 `## 核心知识点图` 小节（如缺失则回退到下一个章节标题，再不行追加末尾）
- 支持断点续传：进度保存在 /tmp/<proj>_svgs_<cat>.json
用法: gen_svgs.py <project> [--cat concurrent,database] [--batch 3] [--workers 4] [--resume]
环境变量: CP_API_KEY (优先) 或 GLM_API_KEY。
"""
import os, re, sys, json, time, argparse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

MODEL = 'GLM-5.2'
BASE_URL = os.environ.get('CP_BASE_URL', 'https://open.bigmodel.cn/api/anthropic')

CATEGORIES = ['concurrent', 'database']

PROMPT = '''你是一名技术架构图设计师 + 大模型内容分析师。为下方每道面试题的核心知识点设计一张专属 SVG 静态精绘图。

## SVG 硬性规范（必须严格遵守）
1. `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500">`，不要写死 width/height
2. 必须包含：标题（顶部居中）、流程节点、箭头连线、颜色分组标注
3. 调色板（严格使用）：
   - 绿 #4CAF50（成功/正常路径，浅底 #E8F5E9）
   - 橙 #FF9800（判断/重试/警告，浅底 #FFF3E0）
   - 紫 #9C27B0（关键概念/抽象层，浅底 #F3E5F5）
   - 红 #f44336（失败/风险/异常，浅底 #FFEBEE）
   - 蓝 #2196F3（数据/流程主路径，浅底 #E3F2FD）
   - 灰 #607D8B（次要/注释，浅底 #ECEFF1）
4. 在 `<defs>` 内定义箭头 marker（id="arr"），所有连线使用 marker-end="url(#arr)"
5. 背景使用浅灰 `<rect width="800" height="500" fill="#fafafa"/>`
6. 节点形状约定：
   - 矩形 rx="8"（流程/数据节点）
   - 菱形 polygon（判断节点）
   - 椭圆 ellipse（开始/结束）
7. 字体：`font-family="system-ui,-apple-system,sans-serif"`，标题 font-size="18" font-weight="700"
8. 文本必须 text-anchor="middle"，中文标签清晰可读（节点字号 12-13，标题 18）
9. 图例 legend 放底部（可选但推荐，帮助理解颜色含义）
10. 坐标必须合理布局，节点之间不能重叠，箭头方向清晰

## 设计原则
1. **专属化**：每道题的图必须紧扣该题的 essence 和 key_points，不能套通用模板
2. **信息密度**：节点数 5-12 个，每个节点标签要具体（避免"模块""组件"这种空泛词）
3. **可视化手段**：
   - 流程/时序 → 纵向流程图 + 判断分支
   - 层级/分类 → 树状/分组（subgraph 风格用 rect 圈起）
   - 对比/选型 → 左右两列对照
   - 数据结构 → 直接画出结构示意（如 B+ 树、链表、栈堆）
   - 状态转换 → 状态机节点 + 转换箭头
4. **核心要点高亮**：题目的"致命风险""关键限制"用红色标注；"优势"用绿色
5. 标签里如需换行用 `<tspan x="..." dy="14">第二行</tspan>`

## 输出格式（严格 JSON 数组，每题一个对象）
[{"id":"题目id","svg":"<svg xmlns=\\"http://www.w3.org/2000/svg\\" viewBox=\\"0 0 800 500\\">...</svg>"}]

注意：
- `svg` 字段是完整 SVG 源码（含 `<svg>` 开标签和 `</svg>` 闭标签）
- 不要输出任何解释性文字、不要 markdown 代码块包裹
- SVG 中的双引号在 JSON 字符串里要转义为 `\\"`
- 只输出 JSON 数组，不要任何前后缀
- 每题一张图，不要遗漏'''


def parse_md(path):
    """解析 frontmatter，返回 (qid, meta, raw)。"""
    with open(path, encoding='utf-8') as f:
        raw = f.read()
    parts = raw.split('---\n', 2)
    if len(parts) < 3:
        return None, {}, raw
    fm = parts[1]
    body = parts[2].lstrip('\n')
    lines = body.split('\n')
    title = lines[0].replace('# ', '').strip() if lines else ''
    qid = os.path.basename(path).replace('.md', '')
    m = re.search(r'^id:\s*(\S+)\s*$', fm, re.MULTILINE)
    if m:
        qid = m.group(1).strip()
    # 提取 essence / analogy / key_points
    meta = {'title': title}
    em = re.search(r'essence:\s*(.+?)(?:\n\s*\w+:|$)', fm, re.DOTALL)
    if em:
        meta['essence'] = em.group(1).strip().split('\n')[0].strip()
    am = re.search(r'analogy:\s*(.+?)(?:\n\s*\w+:|$)', fm, re.DOTALL)
    if am:
        meta['analogy'] = am.group(1).strip().split('\n')[0].strip()
    # key_points（YAML 列表项 - xxx）
    kp_match = re.search(r'key_points:\s*\n((?:\s+-\s+.+\n?)+)', fm)
    if kp_match:
        kps = re.findall(r'-\s+(.+)', kp_match.group(1))
        meta['key_points'] = [k.strip().strip("'\"") for k in kps][:5]
    return qid, meta, raw


def truncate_for_prompt(raw, max_chars=2500):
    """只保留 frontmatter 关键字段 + 标题 + 前若干正文。"""
    parts = raw.split('---\n', 2)
    body = parts[2] if len(parts) >= 3 else raw
    body = body.strip()
    # 去除 ```代码块```（节省 token）
    body = re.sub(r'```[\s\S]*?```', '（代码块省略）', body)
    # 去除 | 表格 |（节流）
    body = re.sub(r'^\|.*\|\s*$', '（表格行）', body, flags=re.MULTILINE)
    if len(body) > max_chars:
        body = body[:max_chars] + '\n…（截断）'
    return body


def build_prompt(batch):
    parts = []
    for i, q in enumerate(batch):
        body = truncate_for_prompt(q['raw'])
        m = q['meta']
        kp_str = '\n'.join(f'  - {k}' for k in m.get('key_points', [])) or '  - (无)'
        parts.append(
            f'### 题目 {i+1}（id: {q["id"]}, 分类: {q["cat"]}）\n'
            f'**问题（title）**：{m.get("title","")}\n'
            f'**核心本质（essence）**：{m.get("essence","")}\n'
            f'**类比（analogy）**：{m.get("analogy","")}\n'
            f'**核心要点（key_points）**：\n{kp_str}\n\n'
            f'**正文摘要**：\n{body}'
        )
    return PROMPT + '\n\n## 题目\n\n' + '\n\n---\n\n'.join(parts)


def call_llm(prompt, max_retries=5):
    data = json.dumps({
        'model': MODEL,
        'max_tokens': 16000,
        'messages': [{'role': 'user', 'content': prompt}],
    }).encode()
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                BASE_URL.rstrip('/') + '/v1/messages',
                data=data,
                headers={
                    'x-api-key': os.environ['CP_API_KEY'],
                    'anthropic-version': '2023-06-01',
                    'Content-Type': 'application/json',
                },
            )
            with urllib.request.urlopen(req, timeout=300) as r:
                resp = json.loads(r.read())
                for b in resp.get('content', []):
                    if b.get('type') == 'text':
                        return b.get('text', '')
                return ''
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_retries - 1:
                wait = min(10 * (attempt + 1), 60)
                time.sleep(wait)
                continue
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))
    return None


def parse_resp(text):
    if not text:
        return None
    text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip())
    try:
        return json.loads(text)
    except Exception:
        s, e = text.find('['), text.rfind(']')
        if s >= 0 and e > s:
            try:
                return json.loads(text[s:e+1])
            except Exception:
                pass
    return None


SVG_VIEWBOX_RE = re.compile(r'viewBox\s*=\s*["\']0\s+0\s+800\s+500["\']', re.IGNORECASE)
SVG_TAG_RE = re.compile(r'<svg[\s>]', re.IGNORECASE)
SVG_CLOSE_RE = re.compile(r'</svg>\s*$', re.IGNORECASE)


def validate_svg(svg):
    """基础校验：含 <svg>、viewBox 800x500、节点数合理。"""
    if not svg or not isinstance(svg, str):
        return False, '空 svg'
    s = svg.strip()
    if not SVG_TAG_RE.search(s):
        return False, '缺 <svg> 标签'
    if not SVG_VIEWBOX_RE.search(s):
        return False, 'viewBox 不是 0 0 800 500'
    if not SVG_CLOSE_RE.search(s):
        return False, '缺 </svg> 闭合'
    # 节点数过少判定：至少有 5 个 rect/polygon/ellipse/circle
    node_count = sum(len(re.findall(p, s)) for p in [r'<rect\b', r'<polygon\b', r'<ellipse\b', r'<circle\b'])
    if node_count < 3:
        return False, f'节点数过少({node_count})'
    return True, 'ok'


INSERT_BEFORE_HEADERS = [
    '## 记忆要点',
    '## 结构化回答',
    '## 视频脚本',
    '## 苏格拉底',
    '## 常见考点',
    '## 总结',
]


def find_insert_point(raw):
    """返回 (idx, header)。优先在 ## 记忆要点 之前插入，否则按 INSERT_BEFORE_HEADERS 顺序找。"""
    for h in INSERT_BEFORE_HEADERS:
        m = re.search(r'^' + re.escape(h) + r'\b[^\n]*\s*$', raw, re.MULTILINE)
        if m:
            return m.start(), h
    return len(raw.rstrip()) + 1, None


def apply_svg_to_md(q, svg_content):
    """将 ## 核心知识点图 小节插入 md 文件。返回 (changed, msg)。"""
    raw = q['raw']
    path = q['path']
    cat = q['cat']
    fname = os.path.basename(path).replace('.md', '')
    img_filename = f'diagram_{cat}_{fname}.svg'
    img_path = os.path.join(q['proj'], 'public', 'images', img_filename)
    section = (
        f'## 核心知识点图\n\n'
        f'<img src="/interview-2026/images/{img_filename}" '
        f'alt="{q["meta"].get("title", "")} 核心知识点图" '
        f'style="max-width:100%;height:auto;border:1px solid var(--border);'
        f'border-radius:8px;margin:1em 0;" />\n\n'
    )
    # 如果已有 ## 核心知识点图，替换；否则插入
    if '## 核心知识点图' in raw:
        # 替换已有 section（直到下一个 ## 标题）
        pattern = re.compile(r'## 核心知识点图\b.*?(?=\n##\s|\Z)', re.DOTALL)
        new = pattern.sub(section.rstrip(), raw, count=1)
        # 保留段落分隔
        new = new.rstrip() + '\n'
    else:
        idx, header = find_insert_point(raw)
        if header is None:
            new = raw.rstrip() + '\n\n' + section
        else:
            prefix = raw[:idx].rstrip('\n')
            new = prefix + '\n\n' + section + raw[idx:].lstrip('\n')
    # 写回 md
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new if new.endswith('\n') else new + '\n')
    # 写 svg 文件
    os.makedirs(os.path.dirname(img_path), exist_ok=True)
    with open(img_path, 'w', encoding='utf-8') as f:
        f.write(svg_content.strip() + '\n')
    return True, img_filename


def load_candidates(proj, cat_filter):
    out = []
    for cat in CATEGORIES:
        if cat_filter and cat not in cat_filter:
            continue
        d = os.path.join(proj, 'questions', cat)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.endswith('.md'):
                continue
            path = os.path.join(d, f)
            try:
                qid, meta, raw = parse_md(path)
            except Exception as e:
                print(f'  解析失败 {f}: {e}')
                continue
            if qid is None:
                continue
            out.append({
                'id': qid,
                'cat': cat,
                'path': path,
                'proj': proj,
                'meta': meta,
                'raw': raw,
            })
    return out


def process_batch(batch, idx):
    resp = call_llm(build_prompt(batch))
    return idx, parse_resp(resp)


def main():
    ap = argparse.ArgumentParser(description='为面试题批量生成核心知识点 SVG 图（GLM-5.2）')
    ap.add_argument('project', help='项目目录路径')
    ap.add_argument('--cat', default='concurrent,database', help='分类，逗号分隔（默认全部）')
    ap.add_argument('--batch', type=int, default=3, help='每批题目数（默认3）')
    ap.add_argument('--workers', type=int, default=4, help='并发数（默认4）')
    ap.add_argument('--resume', action='store_true', help='断点续传')
    ap.add_argument('--limit', type=int, default=0, help='只处理前N题（测试）')
    ap.add_argument('--ids', default='', help='只处理指定 id（逗号分隔）')
    args = ap.parse_args()

    if 'CP_API_KEY' not in os.environ:
        if 'GLM_API_KEY' in os.environ:
            os.environ['CP_API_KEY'] = os.environ['GLM_API_KEY']
        else:
            sys.exit('未设置 CP_API_KEY / GLM_API_KEY')

    proj = os.path.abspath(args.project)
    cat_filter = set(c.strip() for c in args.cat.split(',') if c.strip())
    print(f'=== SVG 核心知识点图批量生成（GLM-5.2）: {proj} ===')
    print(f'分类: {sorted(cat_filter)}')

    qs = load_candidates(proj, cat_filter)
    if args.ids:
        wanted = set(i.strip() for i in args.ids.split(','))
        qs = [q for q in qs if q['id'] in wanted]
    if args.limit:
        qs = qs[:args.limit]

    # 进度文件按分类组合
    prog = f'/tmp/{os.path.basename(proj)}_svgs_{"-".join(sorted(cat_filter))}.json'
    done = set(json.load(open(prog)) if args.resume and os.path.exists(prog) else [])
    # 启动时再次过滤已写入的（md 已含 ## 核心知识点图）
    qs_left = []
    for q in qs:
        if q['id'] in done:
            continue
        if '## 核心知识点图' in q['raw']:
            done.add(q['id'])
            continue
        qs_left.append(q)
    json.dump(list(done), open(prog, 'w'))
    qs = qs_left

    print(f'待处理: {len(qs)} 题 | 每批 {args.batch} | 并发 {args.workers} | 进度: {prog}')

    batches = [qs[s:s+args.batch] for s in range(0, len(qs), args.batch)]
    print(f'共 {len(batches)} 批')

    stats = {'total': 0, 'changed': 0, 'failed': 0, 'errors': 0}
    by_cat = {}
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(process_batch, b, i): (i, b) for i, b in enumerate(batches)}
        for fut in as_completed(futs):
            i, batch = futs[fut]
            try:
                idx, fixes = fut.result()
            except Exception as e:
                print(f'  [批{i}] 异常: {e}')
                stats['failed'] += len(batch)
                continue
            if not fixes:
                print(f'  [批{i}] 解析失败')
                stats['failed'] += len(batch)
                continue
            fmap = {str(f.get('id', '')): f for f in fixes}
            for q in batch:
                fix = fmap.get(q['id'])
                stats['total'] += 1
                if not fix:
                    stats['failed'] += 1
                    print(f'    [{q["id"]}] 未返回结果')
                    continue
                svg = fix.get('svg') or fix.get('diagram') or fix.get('code')
                ok, msg = validate_svg(svg)
                if not ok:
                    stats['failed'] += 1
                    print(f'    [{q["id"]}] SVG 校验失败: {msg}')
                    continue
                try:
                    changed, info = apply_svg_to_md(q, svg)
                    if changed:
                        stats['changed'] += 1
                        done.add(q['id'])
                        by_cat[q['cat']] = by_cat.get(q['cat'], 0) + 1
                except Exception as e:
                    stats['errors'] += 1
                    print(f'    [{q["id"]}] 写入异常: {e}')
            json.dump(list(done), open(prog, 'w'))
            ok = len([q for q in batch if q['id'] in done])
            elapsed = int(time.time() - t0)
            print(f'  [批{i}] ok={ok}/{len(batch)} 累计写入={stats["changed"]} 失败={stats["failed"]} {elapsed}s')

    print(f'\n===== 完成: 处理{stats["total"]} 写入{stats["changed"]} 失败{stats["failed"]} 异常{stats["errors"]} =====')
    for c, n in sorted(by_cat.items(), key=lambda x: -x[1]):
        print(f'  {c:<18} +{n}')
    leftover = [q['id'] for q in qs if q['id'] not in done]
    if leftover:
        print(f'\n剩余未完成: {len(leftover)} 题')
        print('  ' + ', '.join(leftover[:30]))


if __name__ == '__main__':
    main()
