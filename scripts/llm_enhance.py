#!/usr/bin/env python3
# coding: utf-8
"""
R1/R2/R3 答案增强：为每题补充细节、ASCII架构图/流程图、常见考点等。
批量提交（每批N题），SAME优化避免重发长答案。支持断点续传、并发。
用法: llm_enhance.py <project> [--round 1] [--batch 10] [--workers 6] [--resume]
"""
import sys, os, re, json, time, argparse, urllib.request
import yaml
from concurrent.futures import ThreadPoolExecutor, as_completed

MODEL = 'glm-4.6'

# 每轮的增强策略
ROUND_STRATEGY = {
    1: {
        'focus': '补充答案细节、增加 ASCII 架构图/流程图、添加「常见考点」',
        'prompt': '''你是资深技术面试官。请增强以下面试题的答案，使其更适合面试复习。

## 增强要求（对每题）
1. **补充关键细节**：答案不够深入处补充原理细节、参数说明、边界条件
2. **增加 ASCII 架构图/流程图**：对适合的题（系统架构、数据流、调用链、状态转换等），用 ASCII 字符画（┌─┐│└┘├┬┴─ 等框线）画一个简洁的架构图或流程图，帮助理解。不适合的题跳过。
3. **添加「## 常见考点」小节**：列出 2-4 个面试官常追问的点
4. 保持原有正确内容，只增不删

## 输出格式（严格JSON数组，无代码块）
[{"id":"题目id","answer":"SAME（答案已足够丰富无需改动时）或 增强后的完整答案markdown"}]

## 注意
- 只输出JSON
- 答案已足够详细时 answer="SAME"，不要重复
- ASCII图用纯文本字符，不要用图片''',
    },
    2: {
        'focus': '深化答案：实战案例、代码示例、对比表格',
        'prompt': '''你是资深技术面试官。请深化以下面试题答案，增加实战性。

## 深化要求（对每题）
1. **实战案例**：补充一个真实的工程场景或踩坑经验（1-2句）
2. **代码示例**：对涉及实现的题，补充关键代码片段（5-15行，标注语言）
3. **对比表格**：对涉及"区别/选型/对比"的题，用 markdown 表格对比
4. 保持原有内容，只增不删

## 输出格式（严格JSON数组，无代码块）
[{"id":"题目id","answer":"SAME（已足够时）或 深化后的完整答案markdown"}]

## 注意
- 只输出JSON；答案已足够时 answer="SAME"''',
    },
    3: {
        'focus': '打磨：边界情况、面试追问、易错点',
        'prompt': '''你是资深技术面试官。请打磨以下面试题答案的应试性。

## 打磨要求（对每题）
1. **边界情况**：补充容易忽略的边界条件、极端场景
2. **面试追问**：在末尾添加「## 面试追问」小节，列 2-3 个深度追问
3. **易错点**：补充「## 易错点」小节，列 1-2 个常见错误认知
4. 保持原有内容，只增不删

## 输出格式（严格JSON数组，无代码块）
[{"id":"题目id","answer":"SAME（已足够时）或 打磨后的完整答案markdown"}]

## 注意
- 只输出JSON；答案已足够时 answer="SAME"''',
    },
}

def parse_md(path):
    with open(path, encoding='utf-8') as f: raw = f.read()
    parts = raw.split('---\n', 2)
    if len(parts) < 3: return None
    try: meta = yaml.safe_load(parts[1]) or {}
    except: meta = {}
    body = parts[2].strip()
    lines = body.split('\n')
    q = lines[0].replace('# ', '').strip() if lines else ''
    ans = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ''
    return meta, q, ans

def load_questions(proj):
    qs = []
    for cat in sorted(os.listdir(f'{proj}/questions')):
        d = f'{proj}/questions/{cat}'
        if not os.path.isdir(d): continue
        for f in sorted(os.listdir(d)):
            if not f.endswith('.md'): continue
            parsed = parse_md(f'{d}/{f}')
            if not parsed: continue
            meta, q, ans = parsed
            qs.append({'id': str(meta.get('id', f.replace('.md',''))), 'path': f'{d}/{f}',
                       'meta': meta, 'question': q, 'answer': ans})
    return qs

def build_prompt(batch, strategy):
    parts = []
    for i, q in enumerate(batch):
        ans = q['answer'][:2000] if len(q['answer']) > 2000 else q['answer']
        parts.append(f'### 题目 {i+1}（id: {q["id"]}）\n**问题**：{q["question"]}\n\n**当前答案**：\n{ans}')
    return strategy['prompt'] + f'\n\n## 题目\n\n' + '\n\n---\n\n'.join(parts)

def call_glm(prompt, max_retries=3):
    data = json.dumps({'model': MODEL, 'messages': [{'role':'user','content':prompt}],
        'temperature':0.4, 'max_tokens':6000, 'thinking':{'type':'disabled'}}).encode()
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(os.environ['GLM_BASE_URL'].rstrip('/')+'/chat/completions',
                data=data, headers={'Authorization':'Bearer '+os.environ['GLM_API_KEY'],'Content-Type':'application/json'})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read())['choices'][0]['message']['content']
        except Exception as e:
            if attempt < max_retries - 1: time.sleep(5*(attempt+1))
    return None

def parse_resp(text):
    if not text: return None
    text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip())
    try: return json.loads(text)
    except:
        s, e = text.find('['), text.rfind(']')
        if s >= 0 and e > s:
            try: return json.loads(text[s:e+1])
            except: pass
    return None

def apply(q, fix, strategy):
    ans_field = fix.get('answer', 'SAME')
    if ans_field == 'SAME' or not ans_field: return False  # 无改动
    meta = dict(q['meta'])
    fm = yaml.dump(meta, allow_unicode=True, default_flow_style=False, sort_keys=False, width=1000)
    with open(q['path'], 'w', encoding='utf-8') as f:
        f.write(f'---\n{fm}---\n\n# {q["question"]}\n\n{ans_field}\n')
    return True

def process_batch(batch, idx, strategy):
    resp = call_glm(build_prompt(batch, strategy))
    return idx, parse_resp(resp)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('--round', type=int, default=1, choices=[1,2,3])
    ap.add_argument('--batch', type=int, default=8)
    ap.add_argument('--workers', type=int, default=5)
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--limit', type=int, default=0)
    args = ap.parse_args()
    proj = os.path.abspath(args.project)
    strategy = ROUND_STRATEGY[args.round]
    print(f'=== R{args.round}: {strategy["focus"]} ===')

    qs = load_questions(proj)
    if args.limit: qs = qs[:args.limit]
    prog = f'/tmp/{os.path.basename(proj)}_enhance_r{args.round}.json'
    done = set(json.load(open(prog)) if args.resume and os.path.exists(prog) else [])
    print(f'共 {len(qs)} 题，已完成 {len(done)}，每批 {args.batch}，并发 {args.workers}')

    batches = []
    for s in range(0, len(qs), args.batch):
        b = [q for q in qs[s:s+args.batch] if q['id'] not in done]
        if b: batches.append(b)
    print(f'待处理批次: {len(batches)}')

    stats = {'total': 0, 'changed': 0, 'failed': 0, 'errors': 0}
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(process_batch, b, i, strategy): (i, b) for i, b in enumerate(batches)}
        for fut in as_completed(futs):
            i, batch = futs[fut]
            try: idx, fixes = fut.result()
            except Exception as e:
                print(f'  [批{i}] 异常: {e}'); stats['failed'] += len(batch); continue
            if not fixes:
                print(f'  [批{i}] ❌解析失败'); stats['failed'] += len(batch); continue
            fmap = {str(f.get('id','')): f for f in fixes}
            for q in batch:
                fix = fmap.get(q['id'])
                if not fix: stats['failed'] += 1; continue
                try:
                    changed = apply(q, fix, strategy)
                    done.add(q['id']); stats['total'] += 1
                    if changed: stats['changed'] += 1
                except Exception as e: stats['errors'] += 1
            json.dump(list(done), open(prog, 'w'))
            ok = len([q for q in batch if q['id'] in done])
            print(f'  [批{i}] ✅{ok}/{len(batch)} 累计{len(done)}/{len(qs)} 改动{stats["changed"]}')

    print(f'\n===== R{args.round}完成: 处理{stats["total"]} 改动{stats["changed"]} 失败{stats["failed"]} =====')

if __name__ == '__main__':
    main()
