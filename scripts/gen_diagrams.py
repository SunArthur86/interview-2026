#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为剩余分类下「>50行 且 无 mermaid / 无 ASCII 框图」的面试题生成 mermaid 流程图/架构图。
- 通过 coding plan 额度（Anthropic 协议，GLM-5.2）批量调用。
- 在 `## 记忆要点` / `## 视频脚本`（取先出现者）之前插入「## 流程图」小节。
- 支持断点续传：进度保存在 /tmp/<proj>_diagrams.json。
用法: gen_diagrams.py <project> [--batch 4] [--workers 4] [--resume]
环境变量: CP_API_KEY (优先) 或 GLM_API_KEY。
"""
import os, re, sys, json, time, argparse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

MODEL = 'GLM-5.2'
BASE_URL = os.environ.get('CP_BASE_URL', 'https://open.bigmodel.cn/api/anthropic')

CATEGORIES = [
    'ai', 'java-architect', 'eng-practice', 'ai-scenario', 'ai-basics',
    'framework', 'pdd-scm', 'biopharm', 'pdd-content', 'pdd-trade',
    'ant-risk', 'pdd-ai', 'boss-ai', 'fde', 'system-design',
    'algorithm', 'frontend', 'multi-agent', 'java', 'network',
]

BOX_CHARS = set('┌┐└┘├┤┬┴┼│─━═┃║╔╗╚╝╠╣╦╩╬')

PROMPT = '''你是一名技术架构图设计师。为下方每道面试题设计一张 mermaid 流程图/架构图。

## 图表类型选择
- 架构 / 数据流 / 处理流程 → `flowchart TD`（自上而下）
- 时序 / 多方交互 / RPC 调用 → `sequenceDiagram`
- 层级 / 分类 / 组件包含 → `graph TD`
- 方案对比 / 选型 → `flowchart LR` + subgraph

## 质量要求
1. mermaid 语法必须严格正确：英文 ID（如 A1/B2/C3）+ 中文节点标签
2. 节点数量 5-15 个，箭头方向清晰
3. 标签要和题目强相关，避免空泛词如"模块"、"组件"
4. 复杂关系用 subgraph 分组（如客户端 / 服务端 / 存储层）
5. 标签内如有特殊字符需用引号包裹，如 `A["模型<br/>训练"]`
6. 不要输出任何解释性文字，不要 markdown 代码块包裹——直接输出 mermaid 源码
7. 图表不要重复题目已有的图（题目里已经有 mermaid 或 ASCII 框图就跳过）

## 输出格式（严格 JSON 数组）
为每道题输出一个对象，`id` 与输入一致，`diagram` 字段是完整 mermaid 源码（不含 ```mermaid 包裹）：

[{"id":"题目id","diagram":"flowchart TD\\n    A[...] --> B[...]"}]

只输出 JSON 数组，不要任何前后缀。每题一张图，不要遗漏。'''

def has_mermaid(content):
    return '```mermaid' in content

def has_box_diagram(content):
    chars = set(content) & BOX_CHARS
    total = sum(content.count(c) for c in BOX_CHARS)
    return len(chars) >= 3 and total >= 10

def parse_md(path):
    with open(path, encoding='utf-8') as f:
        raw = f.read()
    parts = raw.split('---\n', 2)
    if len(parts) < 3:
        return None, raw
    body = parts[2].lstrip('\n')  # 去掉开头多余空行
    lines = body.split('\n')
    q = lines[0].replace('# ', '').strip() if lines else ''
    # extract id from frontmatter
    qid = os.path.basename(path).replace('.md', '')
    m = re.search(r'^id:\s*(\S+)\s*$', parts[1], re.MULTILINE)
    if m:
        qid = m.group(1).strip()
    return qid, q, body

def load_candidates(proj):
    """扫描所有目标分类，返回需要处理题目列表。"""
    out = []
    for cat in CATEGORIES:
        d = os.path.join(proj, 'questions', cat)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.endswith('.md'):
                continue
            path = os.path.join(d, f)
            try:
                raw = open(path, encoding='utf-8').read()
            except Exception:
                continue
            lines = raw.count('\n')
            if lines < 50:
                continue
            if has_mermaid(raw) or has_box_diagram(raw):
                continue
            qid, q, body = parse_md(path)
            out.append({
                'id': qid,
                'cat': cat,
                'path': path,
                'question': q,
                'raw': raw,
            })
    return out

def truncate_for_prompt(raw, max_chars=3500):
    """只保留标题 + 前若干正文，省 token。"""
    # 去除 frontmatter
    parts = raw.split('---\n', 2)
    body = parts[2] if len(parts) >= 3 else raw
    body = body.strip()
    # 去除 ```代码块```（节省 token 且不必要看实现细节）
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
        parts.append(f'### 题目 {i+1}（id: {q["id"]}, 分类: {q["cat"]}）\n**问题**：{q["question"]}\n\n**答案摘要**：\n{body}')
    return PROMPT + '\n\n## 题目\n\n' + '\n\n---\n\n'.join(parts)

def call_llm(prompt, max_retries=5):
    data = json.dumps({
        'model': MODEL,
        'max_tokens': 8000,
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
            with urllib.request.urlopen(req, timeout=240) as r:
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

def validate_mermaid(code):
    """基础校验：必须含图表类型关键字且不少于3行。"""
    if not code or not isinstance(code, str):
        return False
    code = code.strip()
    head = code.split('\n', 1)[0].strip().lower()
    if not (head.startswith('flowchart') or head.startswith('graph')
           or head.startswith('sequencediagram') or head.startswith('stateDiagram')
           or head.startswith('statediagram') or head.startswith('classdiagram')
           or head.startswith('erdiagram') or head.startswith('pie')
           or head.startswith('gantt') or head.startswith('mindmap')):
        return False
    if code.count('\n') < 3:
        return False
    return True

INSERT_HEADERS = ('## 记忆要点', '## 视频脚本', '## 视频脚本/记忆要点')

def find_insert_point(raw):
    """返回插入位置（行起始 idx）和后续保留文本。"""
    # 找最先出现的可识别「结尾段」标题
    for h in INSERT_HEADERS:
        m = re.search(r'^' + re.escape(h) + r'\b[^\n]*\s*$', raw, re.MULTILINE)
        if m:
            return m.start(), h
    # 没找到 → 追加末尾
    return len(raw.rstrip()) + 1, None

def apply_diagram(q, code):
    raw = q['raw']
    # 不重复插入
    if '```mermaid' in raw:
        return False, '已有 mermaid'
    if has_box_diagram(raw):
        return False, '已有 ASCII 框图'
    code = code.strip()
    # 去除模型可能误包的代码围栏
    code = re.sub(r'^```mermaid\s*', '', code)
    code = re.sub(r'\s*```$', '', code).strip()
    if not validate_mermaid(code):
        return False, 'mermaid 校验失败'
    # 注意：保持双换行间距，且与下一段标题之间也留双换行
    section = f'## 流程图\n\n```mermaid\n{code}\n```\n\n'

    idx, header = find_insert_point(raw)
    if header is None:
        # 末尾追加：前面补双换行
        new = raw.rstrip() + '\n\n' + section
    else:
        # 强制让标题前刚好是 \n\n（避免源文件里已有的多余空行）
        prefix = raw[:idx].rstrip('\n')
        new = prefix + '\n\n' + section + raw[idx:].lstrip('\n')
    # 写回（保持原编码 + 末尾换行）
    with open(q['path'], 'w', encoding='utf-8') as f:
        f.write(new if new.endswith('\n') else new + '\n')
    return True, f'插入于 {header or "末尾"}'

def process_batch(batch, idx):
    resp = call_llm(build_prompt(batch))
    return idx, parse_resp(resp)

def main():
    ap = argparse.ArgumentParser(description='为面试题批量生成 mermaid 流程图（GLM-5.2）')
    ap.add_argument('project', help='项目目录路径')
    ap.add_argument('--batch', type=int, default=4, help='每批题目数（默认4）')
    ap.add_argument('--workers', type=int, default=4, help='并发数（默认4）')
    ap.add_argument('--resume', action='store_true', help='断点续传')
    ap.add_argument('--limit', type=int, default=0, help='只处理前N题（测试）')
    ap.add_argument('--cat', default='', help='只处理指定分类（如 ai）')
    args = ap.parse_args()

    if 'CP_API_KEY' not in os.environ:
        if 'GLM_API_KEY' in os.environ:
            os.environ['CP_API_KEY'] = os.environ['GLM_API_KEY']
        else:
            sys.exit('未设置 CP_API_KEY / GLM_API_KEY')

    proj = os.path.abspath(args.project)
    print(f'=== mermaid 流程图批量生成（GLM-5.2）: {proj} ===')

    qs = load_candidates(proj)
    if args.cat:
        qs = [q for q in qs if q['cat'] == args.cat]
    if args.limit:
        qs = qs[:args.limit]
    prog = f'/tmp/{os.path.basename(proj)}_diagrams.json'
    done = set(json.load(open(prog)) if args.resume and os.path.exists(prog) else [])
    # 启动时再次过滤已写入的（防止脏数据）
    qs = [q for q in qs if q['id'] not in done]
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
                    continue
                code = fix.get('diagram') or fix.get('mermaid') or fix.get('code')
                try:
                    changed, msg = apply_diagram(q, code)
                    if changed:
                        stats['changed'] += 1
                        done.add(q['id'])
                        by_cat[q['cat']] = by_cat.get(q['cat'], 0) + 1
                    else:
                        stats['failed'] += 1
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

if __name__ == '__main__':
    main()
