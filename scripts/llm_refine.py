#!/usr/bin/env python3
# coding: utf-8
"""
用 GLM 大模型批量校验题目、修正答案、简化费曼（合并第一性原理）。
分批提交（每批 N 题），减少 prompt 次数。支持断点续传。
用法: llm_refine.py <project> [--batch 30] [--resume] [--limit N]
需在 venv(pyyaml) 下运行，或系统装了 pyyaml。
"""
import sys, os, re, json, time, argparse, urllib.request, urllib.error
import yaml
from concurrent.futures import ThreadPoolExecutor, as_completed

MODEL = 'glm-4.6'

def parse_md(path):
    """解析 markdown：返回 (meta_dict, question, answer)"""
    with open(path, encoding='utf-8') as f:
        raw = f.read()
    m = re.match(r'^---\n(.*?)\n---\n(.*)', raw, re.S)
    if not m:
        return None
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        meta = {}
    body = m.group(2).strip()
    qm = re.match(r'^# (.+?)\n\n?(.*)', body, re.S)
    if qm:
        return meta, qm.group(1).strip(), qm.group(2).strip()
    return meta, '', body

def load_questions(proj):
    qs = []
    qdir = os.path.join(proj, 'questions')
    for cat in sorted(os.listdir(qdir)):
        d = os.path.join(qdir, cat)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.endswith('.md'):
                continue
            path = os.path.join(d, f)
            parsed = parse_md(path)
            if not parsed:
                continue
            meta, question, answer = parsed
            qs.append({
                'id': str(meta.get('id', f.replace('.md', ''))),
                'path': path,
                'meta': meta,
                'question': question,
                'answer': answer,
            })
    return qs

PROMPT_TEMPLATE = """你是技术面试题库的质量审校专家。下面有 {n} 道题目，请逐一检查并优化。

## 任务（对每道题）
1. **校验答案**：检查事实错误、过时信息、明显谬误。有错则修正；**答案本身正确时 answer 字段填 "SAME"**（不要重发原答案，节省篇幅）。
2. **简化费曼（feynman）**：将原"第一性原理"精华融入费曼，输出精炼版：
   - essence：一句话本质（10-30字）
   - analogy：大白话类比（10-40字）
   - key_points：3-5 条记忆要点（每条一句）
   - first_principle：根本问题一句话（这到底在解决什么根本问题）

## 输出格式（严格 JSON 数组，无 markdown 代码块、无解释）
[
  {{
    "id": "题目id",
    "answer": "SAME" 或 "修正后的答案（仅在需要修正时输出完整内容）",
    "feynman": {{
      "essence": "一句话本质",
      "analogy": "大白话类比",
      "key_points": ["要点1","要点2"],
      "first_principle": "根本问题一句话"
    }}
  }}
]

## 注意
- 只输出 JSON 数组
- 答案本身正确时 answer 填 "SAME"，不要重复原答案
- feynman 各字段必须精炼，禁止塞大段答案

## 题目

{questions}
"""

def build_prompt(batch):
    parts = []
    for i, q in enumerate(batch):
        ans = q['answer'][:1500] if len(q['answer']) > 1500 else q['answer']
        parts.append(f'### 题目 {i+1}（id: {q["id"]}）\n**问题**：{q["question"]}\n\n**答案**：\n{ans}')
    return PROMPT_TEMPLATE.format(n=len(batch), questions='\n\n---\n\n'.join(parts))

def call_glm(prompt, max_retries=3):
    data = json.dumps({
        'model': MODEL,
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': 0.3,
        'max_tokens': 8000,
        # 关闭深度推理，加速；精炼任务不需要长思维链
        'thinking': {'type': 'disabled'},
    }).encode('utf-8')
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                os.environ['GLM_BASE_URL'].rstrip('/') + '/chat/completions',
                data=data,
                headers={'Authorization': 'Bearer ' + os.environ['GLM_API_KEY'], 'Content-Type': 'application/json'},
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read())['choices'][0]['message']['content']
        except Exception as e:
            print(f'    [重试 {attempt+1}/{max_retries}] {e}')
            time.sleep(4 * (attempt + 1))
    return None

def parse_response(text):
    if not text:
        return None
    text = re.sub(r'^```(?:json)?\s*', '', text.strip())
    text = re.sub(r'\s*```$', '', text.strip())
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        s, e = text.find('['), text.rfind(']')
        if s >= 0 and e > s:
            try:
                return json.loads(text[s:e+1])
            except json.JSONDecodeError:
                pass
    return None

def apply_fix(q, fix):
    """用 yaml 安全重写：更新 meta 的 feynman，删除 first_principle，写 answer"""
    meta = dict(q['meta'])  # 浅拷贝
    # 删除独立的 first_principle（已合并进 feynman）
    meta.pop('first_principle', None)
    # 设置新 feynman
    fey = fix.get('feynman') or {}
    new_fey = {}
    if fey.get('essence'):
        new_fey['essence'] = str(fey['essence']).strip()
    if fey.get('analogy'):
        new_fey['analogy'] = str(fey['analogy']).strip()
    if fey.get('first_principle'):
        new_fey['first_principle'] = str(fey['first_principle']).strip()
    if fey.get('key_points'):
        new_fey['key_points'] = [str(k).strip() for k in fey['key_points'] if str(k).strip()]
    if new_fey:
        meta['feynman'] = new_fey
    # answer: "SAME" 表示保留原答案
    ans_field = fix.get('answer', 'SAME')
    if ans_field == 'SAME' or not ans_field:
        answer = q['answer']
    else:
        answer = ans_field
    # 用 yaml dump frontmatter
    fm = yaml.dump(meta, allow_unicode=True, default_flow_style=False, sort_keys=False, width=1000)
    content = f'---\n{fm}---\n\n# {q["question"]}\n\n{answer}\n'
    with open(q['path'], 'w', encoding='utf-8') as f:
        f.write(content)

def process_batch(batch, batch_idx):
    """处理单个批次，返回 (batch_idx, fixes_or_None)"""
    resp = call_glm(build_prompt(batch))
    return batch_idx, parse_response(resp)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('--batch', type=int, default=30)
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--workers', type=int, default=4, help='并发批次数')
    args = ap.parse_args()
    proj = os.path.abspath(args.project)

    qs = load_questions(proj)
    if args.limit:
        qs = qs[:args.limit]
    print(f'共 {len(qs)} 题，每批 {args.batch} 题，并发 {args.workers}')

    prog_file = f'/tmp/{os.path.basename(proj)}_refine_progress.json'
    done_ids = set()
    if args.resume and os.path.exists(prog_file):
        done_ids = set(json.load(open(prog_file)))
        print(f'断点续传：已完成 {len(done_ids)} 题')

    # 构建待处理批次
    all_batches = []
    for start in range(0, len(qs), args.batch):
        batch = [q for q in qs[start:start + args.batch] if q['id'] not in done_ids]
        if batch:
            all_batches.append(batch)
    print(f'待处理批次: {len(all_batches)}')

    stats = {'total': 0, 'fixed': 0, 'failed': 0, 'errors': 0}

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(process_batch, b, i): (i, b) for i, b in enumerate(all_batches)}
        for fut in as_completed(futures):
            i, batch = futures[fut]
            try:
                bi, fixes = fut.result()
            except Exception as e:
                print(f'  [批{i}] 异常: {e}')
                stats['failed'] += len(batch)
                continue
            if not fixes:
                print(f'  [批{i}] ❌ 解析失败 ({batch[0]["id"]}...)')
                stats['failed'] += len(batch)
                continue
            fix_map = {str(f.get('id', '')): f for f in fixes}
            for q in batch:
                fix = fix_map.get(q['id'])
                if not fix:
                    stats['failed'] += 1
                    continue
                try:
                    apply_fix(q, fix)
                    done_ids.add(q['id'])
                    stats['total'] += 1
                except Exception as e:
                    stats['errors'] += 1
            json.dump(list(done_ids), open(prog_file, 'w'))
            ok = len([q for q in batch if q['id'] in done_ids])
            print(f'  [批{i}] ✅ {ok}/{len(batch)} | 累计 {len(done_ids)}/{len(qs)}')

    print(f'\n===== 完成: 处理{stats["total"]} 修正{stats["fixed"]} 失败{stats["failed"]} 错误{stats["errors"]} =====')

if __name__ == '__main__':
    main()
