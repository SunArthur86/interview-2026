#!/usr/bin/env python3
"""
v3 Smart Extractor — TOC-Hierarchy-Aware Extraction
=====================================================
Key principle: Extract at the RIGHT level for each book, not blindly grab all TOC entries.

Book 1 (JAVA核心知识点整理): Extract at L2 level (226 sections).
  Each L2 = one question, answer = all text in its page range (includes L3/L4/L5 content).

Book 2 (代码随想录-八股文): Extract at L4/L5 level.
  - L4 with L5 children → each L5 = one question
  - L4 without L5 children → L4 itself = one question
  - Skip L6 (too granular)
"""

import fitz
import re
import json
import os
from collections import defaultdict

# ============================================================
# Configuration
# ============================================================
MIN_ANSWER_LEN = 120  # Skip questions with answers shorter than this

# Non-Java topics to filter out
NON_JAVA_PATTERNS = [
    r'^go\s*(语言|并发|web|中|的)',
    r'goroutine',
    r'gmp\s*模型',
    r'^docker',
    r'^kubernetes',
    r'^css\b',
    r'^react\b',
    r'^vue\b',
    r'^angular\b',
    r'^flex\s*布局',
    r'^nginx\s*配置',
    r'^lua\b',
    r'^python\b',
    r'^rust\b',
    r'^c\+\+',
    r'^前端',
    r'^epoll\s*(的|et|lt)',
    r'^select\s*(实现|的|/poll)',
    r'^spout\b',
    r'^bolt\b',
    r'^tuple\b',
    r'^fiber\b',
    r'^gin\b',
    r'^webstorage',
    r'^app.*(开屏|首页|渲染)',
    r'^浏览器同源',
    r'^降低.*渲染时间',
    r'^编译$',
    r'^关于.*编译',
    r'^操作系统有哪些锁',
]

def clean_title(title):
    """Remove TOC numbering and clean up title."""
    # Remove patterns like "2.1.3.", "2.2.", "10．", "3．", "01丨"
    title = re.sub(r'^\d+(\.\d+)*\.?\s*', '', title)
    title = re.sub(r'^\d+\s*[．.、丨]\s*', '', title)
    title = re.sub(r'^\d+\s+', '', title)
    # Remove trailing page numbers or artifacts
    title = re.sub(r'\s*\d+$', '', title)
    # Clean whitespace
    title = title.strip()
    return title

def is_valid_question(title, answer):
    """Check if a question is valid (meaningful title + sufficient answer)."""
    title = clean_title(title)
    
    # Skip if title too short (< 4 chars after cleaning)
    if len(title) < 4:
        return False
    
    # Skip single English words or abbreviations (likely not real questions)
    if re.match(r'^[A-Z][a-z]*$', title) and len(title) < 8:
        return False
    if re.match(r'^[A-Z]{2,8}$', title) and not any(c in title.lower() for c in 'aeiou'):
        return False
    
    # Skip if answer too short
    if len(answer) < MIN_ANSWER_LEN:
        return False
    
    # Skip non-Java topics
    title_lower = title.lower()
    for pattern in NON_JAVA_PATTERNS:
        if re.match(pattern, title_lower):
            return False
    
    return True

def extract_page_text(doc, start_page, end_page):
    """Extract text from a range of pages (0-indexed)."""
    text_parts = []
    for pno in range(start_page, min(end_page, len(doc))):
        page = doc[pno]
        text = page.get_text("text")
        if text.strip():
            text_parts.append(text.strip())
    return "\n\n".join(text_parts)

def extract_images_from_pages(doc, start_page, end_page):
    """Extract image references from a range of pages."""
    images = []
    for pno in range(start_page, min(end_page, len(doc))):
        page = doc[pno]
        img_list = page.get_images(full=True)
        for img in img_list:
            xref = img[0]
            if xref not in [i['xref'] for i in images]:
                images.append({'xref': xref, 'page': pno + 1})
    return images

def save_images(doc, images, question_id, book_prefix, output_dir):
    """Save images to disk and return relative paths."""
    paths = []
    for i, img_info in enumerate(images[:3]):  # Max 3 images per question
        try:
            xref = img_info['xref']
            pix = fitz.Pixmap(doc, xref)
            if pix.n - pix.alpha > 3:  # CMYK → RGB
                pix = fitz.Pixmap(fitz.csRGB, pix)
            
            # Skip tiny images (likely icons/logos)
            if pix.width < 80 or pix.height < 60:
                pix.close()
                continue
            
            img_filename = f"{book_prefix}_{question_id}_{i+1}.png"
            img_path = os.path.join(output_dir, img_filename)
            pix.save(img_path)
            pix.close()
            paths.append(f"images/{img_filename}")
        except Exception as e:
            pass
    return paths

# ============================================================
# Book 1: JAVA核心知识点整理 — Extract at L2 level
# ============================================================
def extract_book1(doc, output_dir):
    """Extract questions from JAVA核心知识点整理.pdf at L2 level."""
    toc = doc.get_toc()
    questions = []
    
    # Build a flat list of (level, title, page, index) for navigation
    entries = [(level, title, page, i) for i, (level, title, page) in enumerate(toc)]
    
    # Find all L2 entries
    for i, (level, title, page_num, toc_idx) in enumerate(entries):
        if level != 2:
            continue
        
        # Find the end page: next L1 or L2 entry
        end_page = len(doc)
        for j in range(toc_idx + 1, len(entries)):
            next_level, next_title, next_page, _ = entries[j]
            if next_level <= 2:
                end_page = next_page - 1
                break
        
        start_page = page_num - 1  # 0-indexed
        
        # Extract text
        answer = extract_page_text(doc, start_page, end_page)
        
        # Clean title
        q_title = clean_title(title)
        
        if not is_valid_question(q_title, answer):
            continue
        
        # Extract images
        images = extract_images_from_pages(doc, start_page, end_page)
        img_paths = save_images(doc, images, f"b1_{len(questions)+1:04d}", "b1", output_dir)
        
        questions.append({
            'question': q_title,
            'answer': answer[:3000],  # Cap at 3000 chars
            'images': img_paths,
            'source': 'JAVA核心知识点整理',
            'source_pages': f"p{page_num}-{end_page}"
        })
    
    return questions

# ============================================================
# Book 2: 代码随想录-八股文 — Extract at L4/L5 level
# ============================================================
def extract_book2(doc, output_dir):
    """Extract questions from 代码随想录-八股文.pdf at L4/L5 level."""
    toc = doc.get_toc()
    entries = [(level, title, page, i) for i, (level, title, page) in enumerate(toc)]
    
    # Build parent-child map: for each entry index, find its children
    children_map = defaultdict(list)  # parent_idx → [child_indices]
    for i, (level, title, page, toc_idx) in enumerate(entries):
        # Find parent (previous entry with level-1)
        for j in range(i - 1, -1, -1):
            if entries[j][0] == level - 1:
                children_map[j].append(i)
                break
    
    questions = []
    
    # Process L4 entries
    for i, (level, title, page_num, toc_idx) in enumerate(entries):
        if level != 4:
            continue
        
        has_l5_children = i in children_map and len(children_map[i]) > 0
        
        if has_l5_children:
            # Each L5 child is a question
            for child_idx in children_map[i]:
                child_level, child_title, child_page, child_toc_idx = entries[child_idx]
                
                # Find end page: next L5 sibling or next L4 entry
                end_page = len(doc)
                # Check next sibling
                siblings = children_map[i]
                sibling_pos = siblings.index(child_idx)
                if sibling_pos + 1 < len(siblings):
                    end_page = entries[siblings[sibling_pos + 1]][2] - 1
                else:
                    # Last child → find next L4 entry
                    for j in range(child_toc_idx + 1, len(entries)):
                        if entries[j][0] <= 4:
                            end_page = entries[j][2] - 1
                            break
                
                start_page = child_page - 1
                answer = extract_page_text(doc, start_page, end_page)
                q_title = clean_title(child_title)
                
                if not is_valid_question(q_title, answer):
                    continue
                
                images = extract_images_from_pages(doc, start_page, end_page)
                img_paths = save_images(doc, images, f"b2_{len(questions)+1:04d}", "b2", output_dir)
                
                questions.append({
                    'question': q_title,
                    'answer': answer[:3000],
                    'images': img_paths,
                    'source': '代码随想录-八股文',
                    'source_pages': f"p{child_page}-{end_page}",
                    'parent_topic': clean_title(title)  # L4 title as parent topic
                })
        else:
            # L4 without L5 children → L4 itself is the question
            # Find end page: next L4 entry
            end_page = len(doc)
            for j in range(toc_idx + 1, len(entries)):
                if entries[j][0] <= 4:
                    end_page = entries[j][2] - 1
                    break
            
            start_page = page_num - 1
            answer = extract_page_text(doc, start_page, end_page)
            q_title = clean_title(title)
            
            if not is_valid_question(q_title, answer):
                continue
            
            images = extract_images_from_pages(doc, start_page, end_page)
            img_paths = save_images(doc, images, f"b2_{len(questions)+1:04d}", "b2", output_dir)
            
            questions.append({
                'question': q_title,
                'answer': answer[:3000],
                'images': img_paths,
                'source': '代码随想录-八股文',
                'source_pages': f"p{page_num}-{end_page}"
            })
    
    return questions

# ============================================================
# Category Classification
# ============================================================
CATEGORY_RULES = [
    ('java-core', [
        'java基础', 'javase', '数据类型', '变量', '方法', '类和对象', '面向对象',
        '集合', 'list', 'map', 'set', 'queue', 'hashmap', 'treemap', 'arraylist',
        '泛型', '注解', '反射', '异常', 'io流', 'nio', '序列化', 'string', 'stringbuilder',
        'equal', 'hashcode', '包装类', '自动装箱', '深拷贝', '浅拷贝', '访问权限',
        'static', 'final', '接口', '抽象类', '多态', '继承', '封装', '重载', '重写',
        'java8', 'lambda', 'stream', 'optional', 'java概述', '枚举', '正则',
        'object类', '值传递', '引用传递', 'jdbc', '锁', 'volatile', 'synchronized',
        'aqs', 'threadlocal', 'cas', '线程池', '并发', '多线程', 'juc',
        'countdownlatch', 'cyclicbarrier', 'semaphore', 'lock', 'condition',
        '公平锁', '非公平锁', '读写锁', '死锁', '线程安全', '并发容器',
        'blockingqueue', 'concurrenthashmap', 'copyonwrite', 'future', 'completablefuture',
        '线程', '进程', '并行', '管程', 'happens-before', '内存屏障',
    ]),
    ('jvm', [
        'jvm', 'java虚拟机', '内存区域', '内存模型', '垃圾回收', '垃圾收集',
        'gc', '堆', '栈', '方法区', '元空间', '程序计数器', '本地方法',
        '类加载', '类加载器', '双亲委派', '字节码', '编译器', '即时编译',
        '运行时数据', '新生代', '老年代', 'eden', 'survivor', 'minor gc',
        'major gc', 'full gc', '引用类型', '强引用', '软引用', '弱引用', '虚引用',
        'jmm', 'java内存模型', '内存可见性', '指令重排', '对象头', 'mark word',
        '调优', 'jstat', 'jmap', 'jstack', 'arthas', 'oom', '内存溢出', '内存泄漏',
    ]),
    ('framework', [
        'spring', 'springboot', 'springmvc', 'mybatis', 'spring cloud',
        'ioc', 'aop', 'bean', '依赖注入', '控制反转', '切面', '代理',
        '事务', 'transactional', 'aspectj', '拦截器', '过滤器',
        'dispatcherservlet', 'handlermapping', 'redis', 'cache', '缓存',
        'rabbitmq', 'kafka', 'zookeeper', 'netty', 'tomcat',
        'swagger', 'jenkins', 'maven', 'gradle', 'junit', 'mockito',
    ]),
    ('database', [
        '数据库', 'mysql', 'sql', '索引', 'b+树', 'b树', '事务', 'acid',
        '隔离级别', '锁', 'mvcc', 'undo log', 'redo log', 'binlog',
        '主从', '分库分表', '读写分离', '慢查询', '执行计划', 'explain',
        'join', 'left join', 'inner join', '子查询', 'union',
        '范式', 'er图', '关系模型', '存储引擎', 'innodb', 'myisam',
        '聚簇索引', '非聚簇索引', '覆盖索引', '回表', '最左匹配',
        'redis', 'rdb', 'aof', '哨兵', '集群', '缓存穿透', '缓存雪崩',
        '缓存击穿', '分布式锁', '过期策略', '淘汰策略', '持久化',
    ]),
    ('middleware', [
        'rabbitmq', 'kafka', 'rocketmq', '消息队列', 'zookeeper',
        'nginx', 'elasticsearch', 'redis集群', 'nacos', 'eureka',
        'dubbo', 'grpc', 'netty', 'minio', 'mongodb',
        'amqp', '交换器', '队列绑定', '消费者', '生产者',
    ]),
    ('distributed', [
        '分布式', '微服务', 'cap', 'base', '一致性', 'consistency',
        '分布式锁', '分布式事务', '分布式id', '分布式缓存',
        '注册中心', '配置中心', '网关', '熔断', '降级', '限流',
        '负载均衡', 'raft', 'paxos', '一致性哈希', '分片',
        'rpc', '远程调用', '服务发现', '服务治理', '链路追踪',
        '分布式 session', 'sso', 'oauth', 'jwt', '鉴权', '认证',
    ]),
]

def classify_question(question, answer, parent_topic=''):
    """Classify a question into a category based on keywords."""
    text = (question + ' ' + answer[:500] + ' ' + parent_topic).lower()
    
    best_category = 'java-core'  # Default
    best_score = 0
    
    for category, keywords in CATEGORY_RULES:
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best_score = score
            best_category = category
    
    return best_category

# ============================================================
# Difficulty Assignment
# ============================================================
def assign_difficulty(question, answer, category):
    """Assign difficulty based on answer length and topic complexity."""
    ans_len = len(answer)
    q_lower = question.lower()
    
    # Advanced topics
    advanced_kw = ['源码', '底层', '原理', '实现', 'aqs', 'cas', 'memory',
                   'classloader', '字节码', 'gc', '调优', '分布式', '一致性',
                   'raft', 'paxos', 'mvcc', 'b+树', 'happens-before']
    is_advanced = any(kw in q_lower or kw in answer[:300].lower() for kw in advanced_kw)
    
    # Basic topics  
    basic_kw = ['什么是', '基本', '概述', '区别', '特征', '类型', '什么是']
    is_basic = any(kw in q_lower for kw in basic_kw)
    
    if is_advanced or ans_len > 1500:
        return 'L3'
    elif ans_len > 600 or not is_basic:
        return 'L2'
    else:
        return 'L1'

# ============================================================
# Main
# ============================================================
def main():
    books_dir = "/opt/data/projects/java-interview/books"
    output_dir = "/opt/data/projects/java-interview/data"
    images_dir = "/opt/data/projects/java-interview/images"
    
    os.makedirs(images_dir, exist_ok=True)
    
    all_questions = []
    
    # Book 1
    print("=" * 60)
    print("Extracting Book 1: JAVA核心知识点整理.pdf")
    print("=" * 60)
    doc1 = fitz.open(os.path.join(books_dir, "JAVA核心知识点整理.pdf"))
    book1_qs = extract_book1(doc1, images_dir)
    print(f"  Extracted: {len(book1_qs)} questions")
    doc1.close()
    all_questions.extend(book1_qs)
    
    # Book 2
    print("\n" + "=" * 60)
    print("Extracting Book 2: 代码随想录-八股文（第五版）.pdf")
    print("=" * 60)
    doc2 = fitz.open(os.path.join(books_dir, "代码随想录-八股文（第五版）.pdf"))
    book2_qs = extract_book2(doc2, images_dir)
    print(f"  Extracted: {len(book2_qs)} questions")
    doc2.close()
    all_questions.extend(book2_qs)
    
    # Deduplicate
    print(f"\nTotal before dedup: {len(all_questions)}")
    seen = set()
    deduped = []
    for q in all_questions:
        key = q['question'].lower().strip()
        if key in seen:
            # Merge answers if duplicate
            for existing in deduped:
                if existing['question'].lower().strip() == key:
                    if len(q['answer']) > len(existing['answer']):
                        existing['answer'] = q['answer']
                        existing['images'] = list(set(existing.get('images', []) + q.get('images', [])))
                    break
            continue
        seen.add(key)
        deduped.append(q)
    print(f"After dedup: {len(deduped)}")
    
    # Classify and format
    categories = defaultdict(list)
    for i, q in enumerate(deduped):
        cat = classify_question(q['question'], q['answer'], q.get('parent_topic', ''))
        difficulty = assign_difficulty(q['question'], q['answer'], cat)
        
        categories[cat].append({
            'id': f"{cat[:4]}-{len(categories[cat])+1:03d}",
            'category': cat,
            'difficulty': difficulty,
            'tags': [],
            'question': q['question'],
            'answer': q['answer'],
            'follow_up': [],
            'images': q.get('images', [])
        })
    
    # Clear old data files
    for old_file in os.listdir(output_dir):
        if old_file.endswith('.json'):
            os.remove(os.path.join(output_dir, old_file))
            print(f"  Cleared: {old_file}")
    
    # Save
    cat_names = {
        'java-core': 'java-core.json',
        'jvm': 'jvm.json',
        'concurrent': 'concurrent.json',
        'framework': 'framework.json',
        'database': 'database.json',
        'middleware': 'middleware.json',
        'distributed': 'distributed.json',
    }
    
    total = 0
    for cat, items in sorted(categories.items()):
        fname = cat_names.get(cat, f"{cat}.json")
        with open(os.path.join(output_dir, fname), 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        print(f"  {fname}: {len(items)} questions")
        total += len(items)
    
    print(f"\n✅ TOTAL: {total} questions")

if __name__ == '__main__':
    main()
