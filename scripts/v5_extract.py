#!/usr/bin/env python3
"""
v5 Multi-Level Extractor — Maximum coverage, no fragmentation
==============================================================
Strategy:
- Book 1: Extract L2 + L3 (specific topics like "CMS收集器", "G1收集器")
- Book 2: Extract L4 (with AND without children) + L5, from Java篇 + 速记版 + 计算机基础篇
- Skip: 前端篇(p685+), Go篇(p964+), algorithm篇(p618-684)
- Smart dedup: if L3's content is a subset of its parent L2, keep only L3
"""

import fitz
import re
import json
import os
from collections import defaultdict

MIN_ANSWER_LEN = 100

SKIP_PATTERNS = [
    r'^前言$', r'^总述$', r'^总结$', r'^概述$',
    r'^目录$', r'^导图', r'^细节$', r'^作用$', r'^语法$',
    r'^使用场景$', r'^注意事项$',
    # Frontend/Go/non-Java
    r'goroutine', r'gmp\s*模型',
    r'^docker', r'^kubernetes',
    r'^css\b', r'^react\b', r'^vue\b', r'^angular\b',
    r'^flex\s*布局', r'^lua\b', r'^python\b', r'^rust\b',
    r'^gin\b', r'^webstorage', r'^webpack',
    r'^node\.js', r'^typescript',
    r'^小程序', r'^electron',
    r'^three\.js', r'^d3\.js',
    r'^jquery', r'^bootstrap',
    r'^sass\b', r'^less\b',
    r'^html\s',
    r'^link标签',
    r'^关于\s*this',
    r'^组件生命周期',
    # Vague
    r'^Collection接口$', r'^List接口$', r'^Set接口$', r'^Queue接口$', r'^Map接口$',
    r'^导图前言$',
]

def should_skip(title):
    t = title.strip().lower()
    for p in SKIP_PATTERNS:
        if re.search(p, t):
            return True
    if len(title.strip()) < 3:
        return True
    return False

def clean_title(title):
    t = title.strip()
    # Remove leading numbering: "2.2.1.", "10．", "1. ", etc
    t = re.sub(r'^\d+(\.\d+)*[\.\s]*', '', t)
    t = re.sub(r'^\d+[\s．、丨]+', '', t)
    # Remove 【常问】 etc
    t = re.sub(r'\s*【.*?】\s*', ' ', t)
    # Clean trailing markers
    t = re.sub(r'[:：]\s*$', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def extract_text(doc, start, end):
    parts = []
    for pno in range(start - 1, min(end, len(doc))):
        text = doc[pno].get_text("text")
        if text.strip():
            parts.append(text.strip())
    return "\n\n".join(parts)[:5000]

def extract_imgs(doc, start, end, prefix, idx, img_dir, max_n=3):
    seen = set()
    paths = []
    for pno in range(start - 1, min(end, len(doc))):
        for img in doc[pno].get_images(full=True):
            xref = img[0]
            if xref in seen:
                continue
            seen.add(xref)
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.n - pix.alpha > 3:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                if pix.width < 80 or pix.height < 60:
                    pix.close(); continue
                fname = f"{prefix}_{idx:04d}_{len(paths)+1}.png"
                pix.save(os.path.join(img_dir, fname))
                pix.close()
                paths.append(f"images/{fname}")
                if len(paths) >= max_n:
                    return paths
            except:
                pass
    return paths

def build_entries(toc, doc_len):
    """Build entries with computed end pages."""
    entries = []
    for i, (level, title, page) in enumerate(toc):
        end = doc_len
        for j in range(i + 1, len(toc)):
            if toc[j][0] <= level:
                end = toc[j][2] - 1
                break
        entries.append({
            'level': level, 'title': title, 'page': page, 'end': end, 'idx': i
        })
    return entries

def has_children(entries, idx, target_level=None):
    """Check if entry at idx has children of target_level (or any deeper level)."""
    base = entries[idx]
    for j in range(idx + 1, len(entries)):
        e = entries[j]
        if e['level'] <= base['level']:
            break
        if target_level is None or e['level'] == target_level:
            return True
    return False

# ============================================================
# Book 1: JAVA核心知识点整理 — L2 + L3
# ============================================================
def extract_book1(doc, img_dir):
    toc = doc.get_toc()
    entries = build_entries(toc, len(doc))
    questions = []

    # Chapter ranges for intelligent level selection
    # Chapters 1-6 (p1-139): Java core/concurrent/jvm/spring → L3 (specific topics)
    # Chapters 7+ (p140+): middleware/distributed/network → L2 (topic-level, not fragmented L3)
    for e in entries:
        if e['page'] <= 139:
            # Java core chapters: extract L3
            if e['level'] != 3:
                continue
        else:
            # Middleware/distributed chapters: extract L2 (L3 is too fragmented here)
            if e['level'] != 2:
                continue

        q_title = clean_title(e['title'])
        if should_skip(q_title) or len(q_title) < 4:
            continue

        answer = extract_text(doc, e['page'], e['end'])
        if len(answer) < MIN_ANSWER_LEN:
            continue

        # For L3 entries: if the answer is mostly the same as parent L2, skip
        # (We'll dedup later by content overlap)

        imgs = extract_imgs(doc, e['page'], e['end'], 'b1', len(questions)+1, img_dir)
        questions.append({
            'question': q_title,
            'answer': answer,
            'images': imgs,
            '_level': e['level'],
            '_page': e['page'],
        })

    return questions

# ============================================================
# Book 2: 代码随想录-八股文 — L4 + L5 from relevant sections
# ============================================================
def extract_book2(doc, img_dir):
    toc = doc.get_toc()
    entries = build_entries(toc, len(doc))
    questions = []

    for i, e in enumerate(entries):
        page = e['page']
        # SKIP frontend (p685+) and Go (p964+) and algorithm (p618-684)
        if page >= 618:
            continue

        q_title = clean_title(e['title'])
        if should_skip(q_title) or len(q_title) < 3:
            continue

        level = e['level']

        # Java篇 (p1-222): Extract L4 AND L5
        if page <= 222:
            if level == 4:
                # L4 is a topic — extract it as a question
                pass
            elif level == 5:
                # L5 is a specific question
                pass
            else:
                continue

        # 速记版 (p223-261): Extract L2 (they ARE questions)
        elif page <= 261:
            if level != 2:
                continue

        # 计算机基础篇 (p262-617): Extract L4 AND L5
        elif page <= 617:
            if level not in (4, 5):
                continue

        else:
            continue

        answer = extract_text(doc, e['page'], e['end'])
        if len(answer) < MIN_ANSWER_LEN:
            continue

        imgs = extract_imgs(doc, e['page'], e['end'], 'b2', len(questions)+1, img_dir)
        questions.append({
            'question': q_title,
            'answer': answer,
            'images': imgs,
            '_level': level,
            '_page': page,
        })

    return questions

# ============================================================
# Smart Dedup: remove L3 if content is 90%+ subset of its L2 parent
# ============================================================
def smart_dedup(questions):
    """Remove questions whose answer is mostly contained in a larger answer."""
    # Sort by answer length descending — keep larger answers
    questions.sort(key=lambda x: len(x['answer']), reverse=True)

    kept = []
    for q in questions:
        is_duplicate = False
        q_answer = q['answer']

        for k in kept:
            k_answer = k['answer']
            # If this question's answer is 80%+ contained in a kept answer
            # AND this is the shorter one
            if len(q_answer) < len(k_answer):
                # Check overlap
                overlap = 0
                # Simple check: does the first 200 chars of q appear in k?
                if q_answer[:200] in k_answer:
                    is_duplicate = True
                    break
                # Also check if titles are very similar
                if q['question'][:8] == k['question'][:8] and len(q_answer) < len(k_answer) * 0.5:
                    is_duplicate = True
                    break

        if not is_duplicate:
            kept.append(q)

    return kept

# ============================================================
# Title polishing
# ============================================================
def polish_title(title):
    t = title.strip()

    # Fix known issues
    fixes = {
        'prototyoe': 'Spring Bean的prototype作用域是什么？',
        'Hashtabe': 'Hashtable',
        'Servivor': 'Survivor',
    }
    for wrong, right in fixes.items():
        t = t.replace(wrong, right)

    # Remove leading special chars
    t = re.sub(r'^[、，,。\.]+', '', t).strip()

    # Already has question mark
    if t.endswith('？') or t.endswith('?'):
        return t

    # Starts with question words
    if any(t.startswith(w) for w in ['什么是', '为什么', '如何', '怎样', '说说',
                                      '谈谈', '简述', '描述', '介绍一下', '解释',
                                      '说一说', '谈一谈', '请说', '请谈']):
        return t + '？'

    # Contains 区别/对比
    if '区别' in t or '对比' in t:
        return t + '有什么区别？' if not t.endswith('区别') else t.replace('区别', '') + '有什么区别？'

    # Very short concept → "什么是...？"
    if len(t) <= 10 and not any(w in t for w in '的是如何为什么过程原理特点流程生命周期'):
        return f'什么是{t}？'

    return t + '？'

# ============================================================
# Classification
# ============================================================
CATEGORY_RULES = [
    ('concurrent', [
        '线程', '并发', '多线程', '锁', 'synchronized', 'volatile', 'aqs',
        'threadlocal', 'cas', '线程池', 'juc', 'lock', 'condition',
        '死锁', '线程安全', '并发容器', 'blockingqueue', 'concurrenthashmap',
        'happens-before', 'reentrantlock', 'atomic', 'fork/join',
        'callable', 'runnable', 'thread', 'executor', 'daemon',
        '偏向锁', '轻量级锁', '重量级锁', '自旋锁', '乐观锁', '悲观锁',
        '读写锁', '公平锁', '管程', 'monitor',
    ]),
    ('jvm', [
        'jvm', 'java虚拟机', '内存区域', '内存模型', '垃圾回收', '垃圾收集',
        'gc', '堆', '栈', '方法区', '元空间', '程序计数器',
        '类加载', '双亲委派', '字节码', '即时编译', 'jit',
        '新生代', '老年代', 'eden', 'survivor',
        '引用类型', '强引用', '软引用', '弱引用', '虚引用',
        'oom', '内存溢出', '内存泄漏', '逃逸分析', '热点代码', '执行引擎',
        '收集器', 'cms', 'g1', 'serial', 'parnew', 'parallel',
    ]),
    ('framework', [
        'spring', 'springboot', 'springmvc', 'mybatis', 'spring cloud',
        'ioc', 'aop', 'bean', '依赖注入', '控制反转', '切面',
        '事务', 'transactional', '拦截器', 'dispatcherservlet',
        'autowired', 'resource', 'starter', '自动装配', '循环依赖',
        'dubbo', 'rpc', 'factorybean',
    ]),
    ('database', [
        'mysql', 'sql', '索引', 'b+树', 'acid', '隔离级别', 'mvcc',
        'undo log', 'redo log', 'binlog', '分库分表', '读写分离',
        'innodb', 'myisam', '聚簇索引', '覆盖索引', '回表', '最左匹配',
        'redis', 'rdb', 'aof', '哨兵', '缓存穿透', '缓存雪崩',
        '缓存击穿', '持久化', 'redis集群', '跳表',
    ]),
    ('middleware', [
        'rabbitmq', 'kafka', 'rocketmq', '消息队列', '消息积压',
        'zookeeper', 'nacos', 'eureka', 'elasticsearch',
        'mongodb', 'amqp', 'exchange', 'broker',
    ]),
    ('distributed', [
        '分布式', '微服务', 'cap', 'base', 'consistency', '一致性',
        '分布式事务', '分布式锁', '分布式id',
        '注册中心', '配置中心', '网关', '熔断', '降级', '限流',
        '负载均衡', 'raft', 'paxos', '一致性哈希',
        '服务发现', 'hystrix', 'ribbon', 'feign',
        'sso', 'oauth', 'jwt', '鉴权',
    ]),
    ('java-core', [
        'java', '集合', 'list', 'map', 'set', 'queue', 'hashmap',
        '泛型', '注解', '反射', '异常', 'io流', 'nio', '序列化',
        'string', 'equal', 'hashcode', '面向对象', '多态', '继承',
        '接口', '抽象类', '重载', '重写', 'static', 'final',
        'lambda', 'stream', 'optional', '枚举', '内部类',
    ]),
]

def classify(q, a):
    text = (q + ' ' + a[:800]).lower()
    best = 'java-core'
    best_score = 0
    for cat, kws in CATEGORY_RULES:
        s = sum(1 for kw in kws if kw in text)
        if s > best_score:
            best_score = s
            best = cat
    return best

def difficulty(q, a):
    if len(a) > 1500:
        return 'L3'
    if any(kw in (q + a[:300]).lower() for kw in ['源码', '底层', '原理', '实现', 'aqs', 'gc', '调优', '分布式', 'mvcc', 'volatile', 'synchronized', '锁升级']):
        return 'L3'
    if len(a) > 600:
        return 'L2'
    return 'L1'

# ============================================================
# Main
# ============================================================
def main():
    books = "/opt/data/projects/java-interview/books"
    data = "/opt/data/projects/java-interview/data"
    imgs = "/opt/data/projects/java-interview/images"
    os.makedirs(imgs, exist_ok=True)

    all_qs = []

    print("Book 1: JAVA核心知识点整理")
    doc1 = fitz.open(os.path.join(books, "JAVA核心知识点整理.pdf"))
    b1 = extract_book1(doc1, imgs)
    print(f"  → {len(b1)} raw questions")
    doc1.close()
    all_qs.extend(b1)

    print("Book 2: 代码随想录-八股文")
    doc2 = fitz.open(os.path.join(books, "代码随想录-八股文（第五版）.pdf"))
    b2 = extract_book2(doc2, imgs)
    print(f"  → {len(b2)} raw questions")
    doc2.close()
    all_qs.extend(b2)

    # Title dedup
    print(f"\nBefore dedup: {len(all_qs)}")
    seen = {}
    for q in all_qs:
        key = q['question'].lower().strip()
        if key in seen:
            if len(q['answer']) > len(seen[key]['answer']):
                seen[key] = q
        else:
            seen[key] = q
    deduped = list(seen.values())
    print(f"After title dedup: {len(deduped)}")

    # Smart content dedup — DISABLED (too aggressive, removes valid L3 sub-questions)
    # deduped = smart_dedup(deduped)
    # print(f"After smart dedup: {len(deduped)}")
    print(f"Total: {len(deduped)}")

    # Polish titles
    for q in deduped:
        q['question'] = polish_title(q['question'])

    # Classify & save
    cats = defaultdict(list)
    for q in deduped:
        cat = classify(q['question'], q['answer'])
        cats[cat].append({
            'question': q['question'],
            'answer': q['answer'],
            'images': q.get('images', []),
            'difficulty': difficulty(q['question'], q['answer']),
        })

    # Clear old
    for f in os.listdir(data):
        if f.endswith('.json'):
            os.remove(os.path.join(data, f))

    order = ['java-core', 'concurrent', 'jvm', 'framework', 'database', 'middleware', 'distributed']
    prefs = {'java-core': 'core', 'concurrent': 'conc', 'jvm': 'jvm',
             'framework': 'fw', 'database': 'db', 'middleware': 'mw', 'distributed': 'dist'}

    total = 0
    for cat in order:
        items = cats.get(cat, [])
        items.sort(key=lambda x: (x['difficulty'], x['question']))
        for i, item in enumerate(items):
            item['id'] = f"{prefs[cat]}-{i+1:03d}"
            item['category'] = cat
            item['subcategory'] = ''
            item.setdefault('tags', [])
            item.setdefault('follow_up', [])

        with open(os.path.join(data, f"{cat}.json"), 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        total += len(items)
        print(f"  {cat}: {len(items)}")

    print(f"\n✅ TOTAL: {total}")

if __name__ == '__main__':
    main()
