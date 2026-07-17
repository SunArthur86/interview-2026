#!/usr/bin/env python3
# coding: utf-8
"""
基于 2026 面试趋势 + 现有题库，让 GLM 生成不重复的新面试题。
用法: gen_new_questions.py <project> <trend_context_file> --count 30
输出: /tmp/<project>_new_trend.json
"""
import sys, os, re, json, argparse, urllib.request, yaml

MODEL = 'glm-4.6'

def collect_existing_titles(proj):
    titles = []
    for cat in os.listdir(f'{proj}/questions'):
        d = f'{proj}/questions/{cat}'
        if not os.path.isdir(d): continue
        for f in os.listdir(d):
            if not f.endswith('.md'): continue
            with open(f'{d}/{f}', encoding='utf-8') as fh:
                m = re.search(r'^# (.+)$', fh.read(), re.M)
            if m: titles.append(m.group(1).strip())
    return titles

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('trend_file', help='搜索到的趋势上下文文件')
    ap.add_argument('--count', type=int, default=30)
    args = ap.parse_args()
    proj = os.path.abspath(args.project)

    existing = collect_existing_titles(proj)
    trend = open(args.trend_file, encoding='utf-8').read()[:4000]
    # 分类列表
    cats = [c for c in os.listdir(f'{proj}/questions') if os.path.isdir(f'{proj}/questions/{c}')]

    prompt = f'''你是技术面试题专家。根据以下 2026 面试趋势，生成 {args.count} 道【全新的、不与现有题库重复】的高质量面试题。

## 2026 面试趋势
{trend}

## 现有题库已有题目（避免重复，共{len(existing)}题，部分示例）
{chr(10).join(existing[:60])}

## 要求
1. 生成 {args.count} 道**现有题库没有**的新题
2. 覆盖趋势中不同方向
3. 每题：question（问题）、answer（答案 300-600字，精炼准确）、category（从 {cats} 选）、subcategory、difficulty(L1-L5)
4. answer 中不要用换行符或引号，用句号分隔，避免JSON转义问题
5. 答案要专业准确

## 输出格式（严格JSON数组，无代码块、无解释）
[{{"question":"题目","answer":"答案","category":"分类","subcategory":"子分类","difficulty":"L2"}}]'''

    data = json.dumps({'model': MODEL, 'messages':[{'role':'user','content':prompt}],
        'temperature':0.6, 'max_tokens':6000, 'thinking':{'type':'disabled'}}).encode()
    req = urllib.request.Request(os.environ['GLM_BASE_URL'].rstrip('/')+'/chat/completions',
        data=data, headers={'Authorization':'Bearer '+os.environ['GLM_API_KEY'],'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=240) as r:
        resp = json.loads(r.read())['choices'][0]['message']['content']

    # 解析（容错）
    resp = re.sub(r'^```(?:json)?\s*|\s*```$', '', resp.strip())
    qs = None
    try:
        qs = json.loads(resp)
    except:
        s, e = resp.find('['), resp.rfind(']')
        if s >= 0 and e > s:
            try: qs = json.loads(resp[s:e+1])
            except json.JSONDecodeError:
                # 逐对象提取
                import re as re2
                objs = re2.findall(r'\{[^{}]*"question"[^{}]*\}', resp[s:e+1], re2.S)
                qs = []
                for o in objs:
                    try: qs.append(json.loads(o))
                    except: pass
    if not qs:
        print('解析失败'); return

    # 去重：与现有题库比对
    def norm(t): return re.sub(r'[？?！!。，,、（）()\s的什么是一]', '', t).lower()
    existing_norm = set(norm(t) for t in existing)
    new = []
    for q in qs:
        if norm(q.get('question','')) not in existing_norm:
            new.append(q)
    print(f'生成 {len(qs)} 题，去重后 {len(new)} 题')
    out = f'/tmp/{os.path.basename(proj)}_new_trend.json'
    json.dump(new, open(out,'w'), ensure_ascii=False, indent=2)
    print(f'写入 {out}')

if __name__ == '__main__':
    main()
