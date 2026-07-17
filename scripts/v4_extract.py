#!/usr/bin/env python3
"""
v4 Smart Extractor — Section-Aware, Fragment-Free
==================================================
Key fixes:
1. Skip 前端篇 (p685+) and Go篇 (p964+) entirely
2. Extract at the right level per section
3. Only keep entries that are real interview questions
4. No title mangling — keep original question phrasing from the book
"""

import fitz
import re
import json
import os
from collections import defaultdict

MIN_ANSWER_LEN = 100

# ============================================================
# Patterns to SKIP (not real interview questions)
# ============================================================
SKIP_PATTERNS = [
    # Textbook section markers
    r'^\d+[\.\s、]',           # "1. xxx", "2、 xxx"
    r'^前言$', r'^总述$', r'^总结$', r'^概述$',
    r'^目录$', r'^导图',
    r'^细节$', r'^作用$', r'^语法$',
    # Frontend/Go/non-Java
    r'goroutine', r'gmp\s*模型',
    r'^docker', r'^kubernetes',
    r'^css\b', r'^react\b', r'^vue\b', r'^angular\b',
    r'^flex\s*布局', r'^lua\b', r'^python\b', r'^rust\b',
    r'^gin\b', r'^webstorage', r'^webpack',
    r'^node\.js', r'^typescript',
    r'^小程序', r'^uni-app',
    r'^electron', r'^three\.js', r'^d3\.js',
    r'^jquery', r'^bootstrap',
    r'^sass\b', r'^less\b',
    r'^html\s',
    r'^link标签',
    r'^浏览器.*(渲染|事件|同源)',
    r'^关于\s*this',
    r'^组件生命周期',
    r'^对称加密$', r'^非对称加密$',
    r'^混合加密',
    r'^数字证书', r'^数字签名', r'^消息摘要',
    # Pure topic fragments (will be converted)
    r'^收发流程$', r'^问题引出$',
]

def should_skip(title):
    """Check if a TOC entry should be skipped."""
    t = title.strip().lower()
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, t):
            return True
    # Skip if title is just a number or very short fragment
    if len(title.strip()) < 3:
        return True
    return False

def clean_title(title):
    """Clean TOC numbering but preserve the question text."""
    t = title.strip()
    # Remove leading numbering like "2.1.3.", "2.2.", "10．"
    t = re.sub(r'^\d+(\.\d+)*[\.\s]*', '', t)
    t = re.sub(r'^\d+[\s．、丨]+', '', t)
    # Remove trailing markers
    t = re.sub(r'\s*【.*?】\s*', '', t)  # 【常问】 etc
    t = t.strip()
    return t

def extract_page_text(doc, start_page, end_page):
    """Extract text from page range (0-indexed)."""
    parts = []
    for pno in range(start_page, min(end_page, len(doc))):
        text = doc[pno].get_text("text")
        if text.strip():
            parts.append(text.strip())
    return "\n\n".join(parts)[:4000]  # Cap at 4000 chars

def extract_images_from_pages(doc, start_page, end_page, max_imgs=3):
    """Extract and save images from page range."""
    images = []
    for pno in range(start_page, min(end_page, len(doc))):
        for img in doc[pno].get_images(full=True):
            xref = img[0]
            if xref not in [i[0] for i in images]:
                images.append((xref, pno))
    return images[:max_imgs]

def save_images(doc, images, prefix, idx, output_dir):
    """Save images and return relative paths."""
    paths = []
    for i, (xref, pno) in enumerate(images):
        try:
            pix = fitz.Pixmap(doc, xref)
            if pix.n - pix.alpha > 3:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            if pix.width < 80 or pix.height < 60:
                pix.close()
                continue
            fname = f"{prefix}_{idx:04d}_{i+1}.png"
            pix.save(os.path.join(output_dir, fname))
            pix.close()
            paths.append(f"images/{fname}")
        except:
            pass
    return paths


# ============================================================
# Book 1: JAVA核心知识点整理 — L2 level extraction
# ============================================================
def extract_book1(doc, img_dir):
    toc = doc.get_toc()
    questions = []
    
    # Build entries with end pages
    entries = []
    for i, (level, title, page) in enumerate(toc):
        end = len(doc)
        for j in range(i + 1, len(toc)):
            if toc[j][0] <= level:
                end = toc[j][2] - 1
                break
        entries.append((level, title, page, end, i))
    
    for level, title, start_page, end_page, idx in entries:
        if level != 2:
            continue
        
        q_title = clean_title(title)
        if should_skip(q_title):
            continue
        
        answer = extract_page_text(doc, start_page - 1, end_page)
        if len(answer) < MIN_ANSWER_LEN:
            continue
        
        imgs = extract_images_from_pages(doc, start_page - 1, end_page)
        img_paths = save_images(doc, imgs, 'b1', len(questions) + 1, img_dir)
        
        questions.append({
            'question': q_title,
            'answer': answer,
            'images': img_paths,
            'source_book': 'JAVA核心知识点整理',
            'source_section': '',
        })
    
    return questions


# ============================================================
# Book 2: 代码随想录-八股文 — Section-aware extraction
# ============================================================
def extract_book2(doc, img_dir):
    toc = doc.get_toc()
    questions = []
    
    # Build entries with end pages
    entries = []
    for i, (level, title, page) in enumerate(toc):
        end = len(doc)
        for j in range(i + 1, len(toc)):
            if toc[j][0] <= level:
                end = toc[j][2] - 1
                break
        entries.append((level, title, page, end, i))
    
    # Process each entry based on which section it's in
    for level, title, start_page, end_page, idx in entries:
        # SKIP frontend and Go sections entirely
        if start_page >= 685:
            continue
        
        q_title = clean_title(title)
        if should_skip(q_title):
            continue
        
        # Determine extraction level based on page range
        if start_page <= 222:
            # Java篇: extract L4 (leaf, no children) and L5 entries
            if level == 4:
                # Check if has L5 children
                has_children = any(e[0] == 5 and e[2] >= start_page and e[2] <= end_page 
                                   for e in entries)
                if has_children:
                    continue  # Skip parent, children will be extracted
                # L4 leaf node → question
            elif level == 5:
                pass  # L5 entries are questions
            elif level == 3 and '总结' not in q_title and '基础' not in q_title:
                # Some L3 entries under Java篇 are good standalone topics
                # But skip generic ones
                continue
            else:
                continue
        elif 223 <= start_page <= 261:
            # 八股文速记版: extract L2 entries (they ARE questions)
            if level != 2:
                continue
        elif 262 <= start_page <= 617:
            # 计算机基础篇: extract L4 entries under "面试题" sections
            if level != 4:
                continue
        elif 618 <= start_page <= 684:
            # 算法篇: skip for now (different format)
            continue
        else:
            continue
        
        answer = extract_page_text(doc, start_page - 1, end_page)
        if len(answer) < MIN_ANSWER_LEN:
            continue
        
        imgs = extract_images_from_pages(doc, start_page - 1, end_page)
        img_paths = save_images(doc, imgs, 'b2', len(questions) + 1, img_dir)
        
        questions.append({
            'question': q_title,
            'answer': answer,
            'images': img_paths,
            'source_book': '代码随想录-八股文',
            'source_section': '',
        })
    
    return questions


# ============================================================
# Category Classification
# ============================================================
CATEGORY_RULES = [
    ('concurrent', [
        '线程', '并发', '多线程', '锁', 'synchronized', 'volatile', 'aqs',
        'threadlocal', 'cas', '线程池', 'juc', 'countdownlatch',
        'cyclicbarrier', 'semaphore', 'lock', 'condition', '公平锁',
        '非公平锁', '读写锁', '死锁', '线程安全', '并发容器',
        'blockingqueue', 'concurrenthashmap', 'copyonwrite',
        'future', 'completablefuture', 'happens-before', '内存屏障',
        '上下文切换', '管程', 'monitor', 'reentrantlock', 'atomic',
        'fork/join', 'forkjoin', '工作窃取', '生产者消费者',
        'callable', 'runnable', 'thread', 'executor',
        '守护线程', 'daemon', '偏向锁', '轻量级锁', '重量级锁',
        '自旋锁', '乐观锁', '悲观锁', '分段锁',
    ]),
    ('jvm', [
        'jvm', 'java虚拟机', '内存区域', '内存模型', '垃圾回收', '垃圾收集',
        'gc', '堆', '栈', '方法区', '元空间', '程序计数器', '本地方法',
        '类加载', '双亲委派', '字节码', '即时编译', 'jit',
        '运行时数据', '新生代', '老年代', 'eden', 'survivor', 'minor gc',
        'major gc', 'full gc', '引用类型', '强引用', '软引用', '弱引用', '虚引用',
        'jmm', '内存可见性', '指令重排', '对象头', 'mark word',
        '调优', 'jstat', 'jmap', 'jstack', 'oom', '内存溢出', '内存泄漏',
        '编译优化', '逃逸分析', '热点代码', '执行引擎',
    ]),
    ('framework', [
        'spring', 'springboot', 'springmvc', 'mybatis', 'spring cloud',
        'ioc', 'aop', 'bean', '依赖注入', '控制反转', '切面', '代理',
        '事务', 'transactional', '拦截器', '过滤器',
        'dispatcherservlet', 'autowired', 'resource',
        'starter', '自动装配', '循环依赖',
        'dubbo', 'rpc', 'rpc框架',
    ]),
    ('database', [
        'mysql', 'sql', '索引', 'b+树', 'b树', 'acid',
        '隔离级别', 'mvcc', 'undo log', 'redo log', 'binlog',
        '主从', '分库分表', '读写分离', '慢查询', '执行计划',
        'innodb', 'myisam', '聚簇索引', '覆盖索引', '回表', '最左匹配',
        'redis', 'rdb', 'aof', '哨兵', '缓存穿透', '缓存雪崩',
        '缓存击穿', '分布式锁', '持久化',
        '事务隔离', '数据库锁', '死锁',
    ]),
    ('middleware', [
        'rabbitmq', 'kafka', 'rocketmq', '消息队列', '消息积压',
        'zookeeper', 'nacos', 'eureka',
        'elasticsearch', 'mongodb',
        'amqp', 'exchange', 'producer', 'consumer', 'broker',
    ]),
    ('distributed', [
        '分布式', '微服务', 'cap', 'base', 'consistency',
        '分布式事务', '分布式id', '分布式缓存',
        '注册中心', '配置中心', '网关', '熔断', '降级', '限流',
        '负载均衡', 'raft', 'paxos', '一致性哈希', '分片',
        '服务发现', '服务治理', '链路追踪',
        'sso', 'oauth', 'jwt', '鉴权', '认证',
        'hystrix', 'ribbon', 'feign',
    ]),
    ('java-core', [  # Default fallback
        'java', '集合', 'list', 'map', 'set', 'queue', 'hashmap',
        '泛型', '注解', '反射', '异常', 'io流', 'nio', '序列化',
        'string', 'stringbuilder', 'equal', 'hashcode',
        '面向对象', '多态', '继承', '封装', '接口', '抽象类',
        '重载', '重写', 'static', 'final',
        'lambda', 'stream', 'optional', '枚举',
        'object类', '值传递', '内部类',
    ]),
]

def classify(question, answer):
    text = (question + ' ' + answer[:800]).lower()
    best_cat = 'java-core'
    best_score = 0
    for cat, keywords in CATEGORY_RULES:
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best_score = score
            best_cat = cat
    return best_cat

def assign_difficulty(question, answer):
    ans_len = len(answer)
    q_lower = question.lower()
    
    advanced = ['源码', '底层', '原理', '实现', 'aqs', 'cas',
                'classloader', 'gc', '调优', '分布式', '一致性',
                'raft', 'mvcc', 'b+树', 'happens-before', 'volatile',
                'synchronized', '锁升级', '内存模型']
    if any(kw in q_lower or kw in answer[:500].lower() for kw in advanced):
        return 'L3'
    if ans_len > 800:
        return 'L2'
    return 'L1'

# ============================================================
# Main
# ============================================================
def main():
    books_dir = "/opt/data/projects/java-interview/books"
    data_dir = "/opt/data/projects/java-interview/data"
    img_dir = "/opt/data/projects/java-interview/images"
    
    os.makedirs(img_dir, exist_ok=True)
    
    all_qs = []
    
    # Book 1
    print("Book 1: JAVA核心知识点整理.pdf")
    doc1 = fitz.open(os.path.join(books_dir, "JAVA核心知识点整理.pdf"))
    b1 = extract_book1(doc1, img_dir)
    print(f"  → {len(b1)} questions")
    doc1.close()
    all_qs.extend(b1)
    
    # Book 2
    print("Book 2: 代码随想录-八股文（第五版）.pdf")
    doc2 = fitz.open(os.path.join(books_dir, "代码随想录-八股文（第五版）.pdf"))
    b2 = extract_book2(doc2, img_dir)
    print(f"  → {len(b2)} questions")
    doc2.close()
    all_qs.extend(b2)
    
    # Dedup
    print(f"\nBefore dedup: {len(all_qs)}")
    seen = {}
    for q in all_qs:
        key = q['question'].lower().strip()
        if key in seen:
            # Keep longer answer
            if len(q['answer']) > len(seen[key]['answer']):
                seen[key] = q
        else:
            seen[key] = q
    deduped = list(seen.values())
    print(f"After dedup: {len(deduped)}")
    
    # Classify
    categories = defaultdict(list)
    for q in deduped:
        cat = classify(q['question'], q['answer'])
        diff = assign_difficulty(q['question'], q['answer'])
        categories[cat].append({
            'question': q['question'],
            'answer': q['answer'],
            'images': q.get('images', []),
            'difficulty': diff,
        })
    
    # Clear old files
    for f in os.listdir(data_dir):
        if f.endswith('.json'):
            os.remove(os.path.join(data_dir, f))
    
    # Save
    cat_order = ['java-core', 'concurrent', 'jvm', 'framework', 'database', 'middleware', 'distributed']
    prefixes = {'java-core': 'core', 'concurrent': 'conc', 'jvm': 'jvm', 
                'framework': 'fw', 'database': 'db', 'middleware': 'mw', 'distributed': 'dist'}
    
    total = 0
    for cat in cat_order:
        items = categories.get(cat, [])
        items.sort(key=lambda x: (x['difficulty'], x['question']))
        
        for i, item in enumerate(items):
            item['id'] = f"{prefixes[cat]}-{i+1:03d}"
            item['category'] = cat
            item['subcategory'] = ''
            item.setdefault('tags', [])
            item.setdefault('follow_up', [])
        
        with open(os.path.join(data_dir, f"{cat}.json"), 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        
        total += len(items)
        print(f"  {cat}.json: {len(items)}")
    
    print(f"\n✅ TOTAL: {total}")

if __name__ == '__main__':
    main()
