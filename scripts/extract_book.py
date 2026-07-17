#!/usr/bin/env python3
"""
Book → Q&A JSON extractor for Java interview project.
Extracts question-answer pairs from PDF/EPUB books, classifies, and formats.

Usage: python3 extract_book.py <book_path> <output_json> [format_hint]
  format_hint: 'qa' (explicit Q&A), 'topic' (topic + explanation), 'auto'
"""
import fitz
import json
import re
import os
import sys
from pathlib import Path

# ============================================================
# TEXT EXTRACTION
# ============================================================

def extract_pdf(pdf_path):
    """Extract text from PDF, return list of (page_num, text)."""
    doc = fitz.open(pdf_path)
    pages = []
    for i in range(len(doc)):
        text = doc[i].get_text()
        if text.strip():
            pages.append((i + 1, text))
    doc.close()
    return pages

def extract_epub(epub_path):
    """Extract text from EPUB, return list of (chapter_title, text)."""
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup
    
    book = epub.read_epub(epub_path, options={'ignore_ncx': True})
    chapters = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), 'html.parser')
        text = soup.get_text(separator='\n')
        # Clean up
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        text = '\n'.join(lines)
        if len(text) > 100:
            title = item.get_name()
            chapters.append((title, text))
    return chapters

# ============================================================
# Q&A PARSING HEURISTICS
# ============================================================

# Question indicator patterns
QUESTION_PATTERNS = [
    # Explicit question markers
    r'^(.{5,80}[？?])$',
    r'^(什么是|什么叫|如何|为什么|怎么|哪些|哪个|怎样|什么是)',
    r'^(说一下|说一说|谈谈|简述|描述一下|介绍一下|解释一下|列举)',
    r'^(.{4,60}(的区别|的原理|的作用|的特点|的优势|的缺点|的过程|的流程))$',
    r'^(.{4,60}(是什么|有(哪些|什么)|是指|用法))$',
    r'^(.{2,40}(和|与).{2,40}(的区别|比较|对比|异同))$',
    r'^(为什么要|为何要|为什么不)',
    r'^(.{4,50}(如何实现|如何保证|如何解决|如何处理|如何优化))$',
    r'^(面试题[：:])',
    r'^(第[一二三四五六七八九十\d]+[题道])',
    # Topic-style (short line followed by detailed explanation)
    r'^([A-Za-z][A-Za-z\s/]{2,50})$',  # English terms like "ThreadLocal"
    r'^([A-Z][a-zA-Z]+(?:[A-Z][a-zA-Z]+)+)$',  # CamelCase terms
]

# Compile patterns
COMPILED_PATTERNS = [re.compile(p) for p in QUESTION_PATTERNS]

# Section header patterns (act as category indicators)
SECTION_PATTERNS = [
    r'^(JavaSE|Java基础|Java核心|集合框架|并发编程|多线程|JVM|Spring|SpringBoot|Spring Boot|SpringCloud|Spring Cloud|MyBatis|MySQL|Redis|Kafka|RabbitMQ|RocketMQ|分布式|微服务|Docker|Kubernetes|设计模式|计算机网络|操作系统|数据结构|算法|消息队列)$',
    r'^(Java\s*[篇章]|并发\s*[篇章]|JVM\s*[篇章]|Spring\s*[篇章]|数据库\s*[篇章]|中间件\s*[篇章]|分布式\s*[篇章])',
]

COMPILED_SECTION = [re.compile(p) for p in SECTION_PATTERNS]

# Lines to skip (not questions, not answers)
SKIP_PATTERNS = [
    r'^\d+$',  # page numbers
    r'^Page\s+\d+',
    r'^第\d+页',
    r'^https?://',
    r'^公众号',
    r'^关注',
    r'^扫码',
    r'^代码随想录',
    r'^Copyright',
    r'^\s*$',
]
COMPILED_SKIP = [re.compile(p) for p in SKIP_PATTERNS]

def should_skip(line):
    for p in COMPILED_SKIP:
        if p.match(line.strip()):
            return True
    return False

def is_question(line, prev_line=None, next_line=None):
    """Check if a line looks like a question/topic header."""
    line = line.strip()
    if len(line) < 3 or len(line) > 120:
        return False
    if should_skip(line):
        return False
    # Check explicit patterns
    for p in COMPILED_PATTERNS:
        if p.search(line):
            return True

    # Heuristic: short Chinese line that looks like a topic (not ending with period)
    # and is followed by a longer explanation line
    has_chinese = bool(re.search(r'[\u4e00-\u9fff]', line))
    if has_chinese and len(line) <= 60:
        # Must not end with sentence-ending punctuation (it's a header, not a statement)
        if line[-1] not in '。.；;！!，,':
            # Check for topic-indicating suffixes
            topic_suffixes = ['关系', '区别', '原理', '作用', '特点', '概念', '机制',
                            '特性', '场景', '问题', '方式', '方法', '条件', '规则',
                            '含义', '定义', '理解', '认识', '总结', '对比', '比较',
                            '概述', '简介', '说明', '分析', '实现', '优化', '应用',
                            '使用', '创建', '执行', '运行', '加载', '初始化',
                            '生命周期', '流程', '步骤', '架构', '设计', '模式']
            for suffix in topic_suffixes:
                if line.endswith(suffix):
                    return True
            # Lines with common Java interview question starters
            starters = ['为什么', '如何', '怎么', '什么是', '什么叫', '什么是',
                       '说一下', '谈谈', '简述', '介绍', '解释', '描述',
                       '列举', '说明', '分析', '比较', '对比', '判断',
                       '给定', '假设', '考虑', '关于', '对于', '针对']
            for starter in starters:
                if line.startswith(starter):
                    return True
            # Lines ending with ? or ？
            if line.endswith('?') or line.endswith('？'):
                return True
            # Topic-style: short line, next line is much longer (explanation)
            if next_line and len(next_line.strip()) > len(line) * 2 and len(line) >= 5:
                # Additional check: contains Chinese and looks like a topic
                if has_chinese and not line.startswith('public') and not line.startswith('private'):
                    # Don't treat code as questions
                    if not any(code_kw in line for code_kw in ['public ', 'private ', 'protected ', 'class ', 'import ', 'package ', 'return ', 'void ', '@']):
                        return True
    return False

def is_section_header(line):
    """Check if line is a section header (used for classification context)."""
    line = line.strip()
    for p in COMPILED_SECTION:
        if p.match(line) or p.search(line):
            return True
    return False

# ============================================================
# CLASSIFICATION
# ============================================================

CATEGORY_KEYWORDS = {
    'java-core': [
        'Java基础', 'JavaSE', '集合', 'Collection', 'HashMap', 'List', 'Set', 'Map',
        '泛型', '反射', '注解', 'Annotation', 'IO', 'NIO', '异常', 'Exception',
        'String', 'StringBuilder', 'StringBuffer', 'Object', 'equals', 'hashCode',
        '面向对象', 'OOP', '封装', '继承', '多态', '抽象类', '接口', 'interface',
        '包装类', 'Integer', '自动装箱', '自动拆箱', 'static', 'final', '变量',
        '方法重写', '方法重载', 'override', 'overload', '内部类', 'Lambda',
        'Stream', 'Optional', '数据类型', '值传递', '引用传递',
    ],
    'concurrent': [
        '线程', 'Thread', '并发', 'Concurrent', '锁', 'Lock', 'synchronized',
        'volatile', 'AQS', 'ThreadLocal', 'CAS', '线程池', 'ThreadPool',
        'Runnable', 'Callable', 'Future', 'CompletableFuture', 'CountDownLatch',
        'CyclicBarrier', 'Semaphore', '原子类', 'Atomic', 'BlockingQueue',
        'ConcurrentHashMap', '死锁', '活锁', '饥饿', '守护线程', 'volatile',
        '内存屏障', 'happens-before', '指令重排', '读写锁', 'ReentrantLock',
        'Condition', '公平锁', '非公平锁', '乐观锁', '悲观锁',
    ],
    'jvm': [
        'JVM', '内存模型', 'JMM', '内存区域', '堆', '栈', '方法区', '元空间',
        'GC', '垃圾回收', '垃圾收集', 'G1', 'CMS', 'ZGC', 'Serial', 'ParNew',
        '类加载', 'ClassLoader', '双亲委派', '字节码', 'bytecode', 'JIT',
        '编译器', 'JVM参数', 'Xmx', 'Xms', '调优', 'OOM', 'OutOfMemory',
        '内存泄漏', '内存溢出', '强引用', '软引用', '弱引用', '幻象引用',
        'GC Roots', '可达性分析', '标记清除', '标记整理', '复制算法',
        '分代收集', '安全点', 'STW', 'Stop The World',
    ],
    'framework': [
        'Spring', 'Bean', 'IOC', 'DI', 'AOP', '事务', 'Transactional',
        'SpringBoot', 'Spring Boot', '自动配置', 'Starter',
        'SpringCloud', 'Spring Cloud', '服务注册', 'Eureka', 'Nacos',
        'Feign', 'Ribbon', 'Gateway', '熔断', 'Hystrix', 'Sentinel',
        'MyBatis', 'Mybatis-plus', 'Mapper', 'ORM',
        'MVC', 'DispatcherServlet', 'RequestMapping',
        'Bean生命周期', '循环依赖', '三级缓存', 'EventListener',
    ],
    'database': [
        'MySQL', 'SQL', '索引', 'Index', 'B+树', 'B树', '事务', 'ACID',
        '隔离级别', 'MVCC', '锁', '行锁', '表锁', '间隙锁', '意向锁',
        '主从复制', 'binlog', 'redo log', 'undo log', '慢查询', '执行计划',
        'explain', '分库分表', 'ShardingSphere', '连接池', 'HikariCP',
        'Redis', '缓存', 'Cache', '持久化', 'RDB', 'AOF', '集群',
        '哨兵', 'Sentinel', '数据类型', '过期策略', '淘汰策略',
        '缓存穿透', '缓存击穿', '缓存雪崩', '分布式锁', 'Redisson',
    ],
    'middleware': [
        'Kafka', 'RabbitMQ', 'RocketMQ', '消息队列', 'MQ', 'ActiveMQ',
        'Elasticsearch', 'ES', '搜索', '倒排索引', 'Zookeeper', 'ZK',
        'Nginx', '负载均衡', 'Tomcat', 'Netty', '序列化', 'Protobuf',
        '消息可靠性', '消息顺序', '消息积压', '消息丢失', '重复消费',
        '消费组', '分区', 'Partition', 'Topic', 'Broker', 'Producer',
        'Consumer', 'Offset', 'ISR', 'Leader', 'Follower',
    ],
    'distributed': [
        '分布式', 'CAP', 'BASE', '一致性', 'Consistency', '共识算法',
        'Raft', 'Paxos', '分布式事务', '分布式锁', '2PC', '3PC',
        'TCC', 'Saga', 'Seata', '微服务', '服务治理', '限流', '熔断',
        '降级', '链路追踪', 'Docker', 'Kubernetes', 'K8s', '容器',
        'DevOps', 'CI/CD', 'Jenkins', '注册中心', '配置中心', '网关',
        '负载均衡', '一致性哈希', 'Gossip', '脑裂', '服务发现',
        '幂等性', '分布式ID', '雪花算法', 'Snowflake',
    ],
}

def classify_question(question, answer, context=''):
    """Classify a Q&A pair into a category based on keywords."""
    text = (question + ' ' + answer + ' ' + context).lower()
    
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in text:
                # Exact match gets higher score
                score += 2 if kw in (question + context) else 1
        scores[cat] = score
    
    # Return category with highest score
    best_cat = max(scores, key=scores.get)
    if scores[best_cat] > 0:
        return best_cat
    return 'java-core'  # default

def estimate_difficulty(question, answer):
    """Estimate difficulty L1-L5 based on answer length and complexity."""
    ans_len = len(answer)
    q_len = len(question)
    
    # Check for advanced keywords
    advanced_kw = ['源码', '底层', 'AQS', 'CAS', 'G1', 'ZGC', 'Paxos', 'Raft', 
                   '一致性', '分布式事务', '内存模型', 'JMM', 'MVCC', 'B+树']
    expert_kw = ['源码分析', '调优', '性能优化', '架构设计', '高可用', '高并发']
    
    advanced_count = sum(1 for kw in advanced_kw if kw in answer)
    expert_count = sum(1 for kw in expert_kw if kw in answer)
    
    if expert_count >= 2 or ans_len > 3000:
        return 'L5'
    elif expert_count >= 1 or advanced_count >= 3 or ans_len > 2000:
        return 'L4'
    elif advanced_count >= 1 or ans_len > 1000:
        return 'L3'
    elif ans_len > 400:
        return 'L2'
    else:
        return 'L1'

# ============================================================
# MAIN PARSER
# ============================================================

def parse_qa_from_text(full_text, book_name=''):
    """Parse Q&A pairs from full text. Returns list of {question, answer}."""
    lines = full_text.split('\n')
    qa_pairs = []
    current_question = None
    current_answer_lines = []
    current_section = ''  # for classification context
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # Track section headers for context
        if is_section_header(line_stripped):
            current_section = line_stripped
            continue

        if should_skip(line_stripped):
            continue

        # Get next non-empty line for context
        next_line = None
        for j in range(i + 1, min(i + 5, len(lines))):
            nl = lines[j].strip()
            if nl:
                next_line = nl
                break

        if is_question(line_stripped, None, next_line):
            # Save previous Q&A
            if current_question and current_answer_lines:
                answer = '\n'.join(current_answer_lines).strip()
                if len(answer) > 20:  # meaningful answer
                    qa_pairs.append({
                        'question': current_question,
                        'answer': answer,
                        'section': current_section,
                    })
            
            current_question = line_stripped.rstrip('？?：: ')
            # Clean common prefixes
            for prefix in ['问：', '答：', '问:', '答:', '面试题：', '面试题:', 'Q：', 'Q:', 'Q1：', 'Q2：', 'Q3：']:
                if current_question.startswith(prefix):
                    current_question = current_question[len(prefix):].strip()
            current_answer_lines = []
        else:
            if current_question:
                current_answer_lines.append(line_stripped)
    
    # Don't forget the last one
    if current_question and current_answer_lines:
        answer = '\n'.join(current_answer_lines).strip()
        if len(answer) > 20:
            qa_pairs.append({
                'question': current_question,
                'answer': answer,
                'section': current_section,
            })
    
    return qa_pairs

def extract_tags(question, answer):
    """Extract relevant tags from question and answer."""
    text = question + ' ' + answer
    tags = []
    
    # Common Java interview tags
    tag_keywords = [
        'HashMap', 'ConcurrentHashMap', 'ArrayList', 'LinkedList', 'HashSet',
        'synchronized', 'volatile', 'ReentrantLock', 'ThreadLocal', 'AQS',
        'CAS', '线程池', 'ThreadPoolExecutor', 'CountDownLatch',
        'Spring', 'SpringBoot', 'Spring Cloud', 'MyBatis', 'Bean', 'IOC', 'AOP',
        'MySQL', 'Redis', 'Kafka', 'RabbitMQ', 'RocketMQ', 'Elasticsearch',
        'Docker', 'Kubernetes', 'Nginx', 'Netty', 'Zookeeper',
        'JVM', 'GC', 'G1', 'CMS', 'ZGC', '类加载', '双亲委派',
        'Thread', 'Runnable', 'Future', 'CompletableFuture',
        'String', 'StringBuilder', 'Integer', 'Object',
        '事务', '索引', 'B+树', 'MVCC', '锁',
        'CAP', 'BASE', 'Raft', 'Paxos', '分布式事务',
        '泛型', '反射', '注解', 'Lambda', 'Stream',
        '设计模式', '单例', '工厂', '观察者', '代理',
        '内存模型', 'JMM', 'happens-before',
        '序列化', 'JSON', 'Protobuf',
    ]
    
    for kw in tag_keywords:
        if kw.lower() in text.lower():
            tags.append(kw)
    
    # Limit to 5 tags
    return tags[:5]

def process_book(book_path, output_path):
    """Process a single book and output JSON."""
    book_name = os.path.basename(book_path)
    print(f"\n{'='*60}")
    print(f"Processing: {book_name}")
    print(f"{'='*60}")
    
    # Extract text
    if book_path.endswith('.pdf'):
        pages = extract_pdf(book_path)
        print(f"  Extracted {len(pages)} pages")
        full_text = '\n'.join(text for _, text in pages)
    elif book_path.endswith('.epub'):
        chapters = extract_epub(book_path)
        print(f"  Extracted {len(chapters)} chapters")
        full_text = '\n'.join(text for _, text in chapters)
    else:
        print(f"  Unsupported format: {book_path}")
        return 0
    
    text_len = len(full_text)
    print(f"  Total text: {text_len:,} chars")
    
    # Parse Q&A
    qa_pairs = parse_qa_from_text(full_text, book_name)
    print(f"  Found {len(qa_pairs)} Q&A pairs")
    
    if not qa_pairs:
        print(f"  WARNING: No Q&A pairs found!")
        return 0
    
    # Format into interview JSON
    questions = []
    for qa in qa_pairs:
        category = classify_question(qa['question'], qa['answer'], qa.get('section', ''))
        difficulty = estimate_difficulty(qa['question'], qa['answer'])
        tags = extract_tags(qa['question'], qa['answer'])
        
        questions.append({
            'question': qa['question'],
            'answer': qa['answer'],
            '_category': category,
            '_subcategory': qa.get('section', ''),
            '_difficulty': difficulty,
            '_tags': tags,
            '_source': book_name,
        })
    
    # Save
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    
    print(f"  Output: {output_path} ({len(questions)} questions)")
    
    # Category distribution
    cat_counts = {}
    for q in questions:
        cat_counts[q['_category']] = cat_counts.get(q['_category'], 0) + 1
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"    {cat}: {count}")
    
    return len(questions)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 extract_book.py <book_path> <output_json>")
        sys.exit(1)
    
    process_book(sys.argv[1], sys.argv[2])
