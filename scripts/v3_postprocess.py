#!/usr/bin/env python3
"""
v3 Post-Process: Clean, fix categories, convert titles, filter non-Java
"""

import json, os, re
from collections import defaultdict

DATA_DIR = "/opt/data/projects/java-interview/data"

# ============================================================
# 1. Hard filter: remove these topics entirely
# ============================================================
HARD_REMOVE_PATTERNS = [
    r'goroutine', r'gmp\s*模型', r'spark\s*rdd', r'hadoop',
    r'chrome.*文字', r'函数柯里化', r'树的遍历', r'数据复制$',
    r'webpack', r'^babel', r'^typescript', r'^node\.js',
    r'^express\b', r'^koa\b', r'^前端性能',
    r'组件生命周期', r'^vue', r'^react', r'^angular',
    r'^css\s', r'^less\b', r'^sass\b',
    r'^jquery', r'^bootstrap',
    r'^小程序', r'^uni-app', r'^taro',
    r'webpack|gulp|rollup',
    r'^electron',
    r'^three\.js', r'^d3\.js',
    r'websocket.*(实现|原理)',  # network, not java
    r'^消息摘要', r'^数字证书', r'^数字签名',
    r'^对称加密$', r'^非对称加密$',
    r'^混合加密', r'^http.*报文', r'^http\s*2',
    r'^浏览器.*tcp', r'^http.*过程$',
    r'^tcp.*握手', r'^tcp.*挥手',
    r'^dns', r'^cdn\b',
    r'^从输入.*到页面', r'^浏览器.*渲染',
    r'^spa.*优化', r'^首屏',
    r'^pwa\b', r'^service\s*worker',
]

# ============================================================
# 2. Title fixup: convert fragment to question
# ============================================================
def fix_title(title):
    """Convert fragmentary titles into proper question format."""
    t = title.strip()
    
    # Remove leading numbers
    t = re.sub(r'^\d+[\.\s、]*', '', t)
    
    # Remove trailing colons, dashes
    t = re.sub(r'[:：]\s*$', '', t)
    
    # Skip if already a question
    if t.endswith('？') or t.endswith('?'):
        return t
    
    # If starts with question words, keep as-is
    if any(t.startswith(w) for w in ['什么是', '什么是', '为什么', '如何', '怎样', '说说', '谈谈', '简述', '描述', '请说', '请谈']):
        return t + '？'
    
    # If contains "区别" or "对比"
    if '区别' in t or '对比' in t:
        return t + '有什么区别？'
    
    # If it's a concept name (< 8 chars, no verb)
    if len(t) <= 12 and not any(w in t for w in '的是如何为什么'):
        return f'什么是{t}？'
    
    # Default: add "？" 
    if not t.endswith('。'):
        return t + '？'
    return t

# ============================================================
# 3. Split concurrent from java-core
# ============================================================
CONCURRENT_KEYWORDS = [
    '线程', '并发', '多线程', '锁', 'synchronized', 'volatile', 'aqs',
    'threadlocal', 'cas', '线程池', 'juc', 'countdownlatch',
    'cyclicbarrier', 'semaphore', 'lock', 'condition', '公平锁',
    '非公平锁', '读写锁', '死锁', '线程安全', '并发容器',
    'blockingqueue', 'concurrenthashmap', 'copyonwrite',
    'future', 'completablefuture', 'happens-before', '内存屏障',
    '上下文切换', '管程', 'monitor', 'reentrantlock', 'atomic',
    'parallel', 'fork/join', 'forkjoin', '工作窃取', '生产者消费者',
    '消费者设计', '线程锁', 'callable', 'runnable', 'thread',
    'executor', 'executors', '线程组', '守护线程', 'daemon',
]

def is_concurrent(question, answer):
    text = (question + ' ' + answer[:500]).lower()
    return sum(1 for kw in CONCURRENT_KEYWORDS if kw in text) >= 2

# ============================================================
# Main processing
# ============================================================
def main():
    # Load all questions
    all_items = []
    for fname in os.listdir(DATA_DIR):
        if not fname.endswith('.json'): continue
        with open(os.path.join(DATA_DIR, fname)) as f:
            items = json.load(f)
        for item in items:
            item['_source_file'] = fname
            all_items.append(item)
    
    print(f"Loaded: {len(all_items)} questions")
    
    # Step 1: Hard filter
    filtered = []
    removed_count = 0
    for item in all_items:
        q = item.get('question', '')
        should_remove = False
        for pattern in HARD_REMOVE_PATTERNS:
            if re.search(pattern, q.lower().strip()):
                should_remove = True
                break
        if should_remove:
            removed_count += 1
        else:
            filtered.append(item)
    print(f"Hard filtered: -{removed_count} → {len(filtered)}")
    
    # Step 2: Remove items with too-short titles AND too-short answers
    quality = []
    for item in filtered:
        q = item.get('question', '').strip()
        a = item.get('answer', '')
        if len(q) < 3 or len(a) < 100:
            continue
        quality.append(item)
    print(f"Quality filter: {len(filtered)} → {len(quality)}")
    
    # Step 3: Fix titles
    for item in quality:
        item['question'] = fix_title(item['question'])
    
    # Step 4: Re-classify — split concurrent from java-core
    categories = defaultdict(list)
    for item in quality:
        cat = item.get('category', 'java-core')
        if cat == 'java-core' and is_concurrent(item['question'], item['answer']):
            cat = 'concurrent'
        categories[cat].append(item)
    
    # Step 5: Re-number IDs and format
    cat_order = ['java-core', 'concurrent', 'jvm', 'framework', 'database', 'middleware', 'distributed']
    cat_prefix = {'java-core': 'core', 'concurrent': 'conc', 'jvm': 'jvm', 'framework': 'fw',
                  'database': 'db', 'middleware': 'mw', 'distributed': 'dist'}
    
    total = 0
    for cat in cat_order:
        items = categories.get(cat, [])
        # Sort by difficulty then alphabetically
        items.sort(key=lambda x: (x.get('difficulty', 'L3'), x['question']))
        
        for i, item in enumerate(items):
            item['id'] = f"{cat_prefix[cat]}-{i+1:03d}"
            item['category'] = cat
            # Ensure required fields
            if 'subcategory' not in item:
                item['subcategory'] = ''
            if 'tags' not in item:
                item['tags'] = []
            if 'follow_up' not in item:
                item['follow_up'] = []
            if 'images' not in item:
                item['images'] = []
        
        fname = f"{cat}.json"
        with open(os.path.join(DATA_DIR, fname), 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        
        total += len(items)
        print(f"  {fname}: {len(items)} questions")
    
    # Clean up any extra files
    expected_files = {f"{c}.json" for c in cat_order}
    for fname in os.listdir(DATA_DIR):
        if fname.endswith('.json') and fname not in expected_files:
            os.remove(os.path.join(DATA_DIR, fname))
            print(f"  Removed extra: {fname}")
    
    print(f"\n✅ TOTAL: {total} questions")

if __name__ == '__main__':
    main()
