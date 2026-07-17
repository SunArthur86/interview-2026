#!/usr/bin/env python3
"""
V2 Extractor: Conservative Q&A extraction from PDF/EPUB books.
Only extract REAL interview questions, not section headers or list items.

Key rules:
- A question must contain Chinese text (>= 6 chars) or be a well-known English Java term
- Lines starting with code keywords (public/private/import/return) are NEVER questions
- Lines starting with numbers (1./2./3.) are list items, NOT questions
- Lines starting with // or # are comments, NOT questions
- Very short labels like "声明位置"/"生命周期" are sub-points, NOT standalone questions
- A question's answer must be >= 150 chars to be meaningful
"""
import fitz
import json
import re
import os
import sys
from collections import defaultdict

# ============================================================
# CJK FIX
# ============================================================
CJK_FIX_MAP = {
    '⽅': '方', '⼩': '小', '⽬': '目', '⽐': '比', '⽓': '气', '⽔': '水', '⽕': '火',
    '⽊': '木', '⽉': '月', '⽇': '日', '⼤': '大', '⼈': '人', '⼊': '入', '⼒': '力',
    '⼥': '女', '⼼': '心', '⼿': '手', '⽀': '支', '⽂': '文', '⼆': '二', '⼀': '一',
    '⼟': '土', '⽤': '用', '⽥': '田', '⽩': '白', '⽚': '片', '⽛': '牙', '⽜': '牛',
    '⽪': '皮', '⽬': '目', '⽭': '矛', '⽮': '矢', '⽯': '石', '⽰': '示', '⽱': '禸',
    '⽲': '禾', '⽳': '穴', '⽴': '立', '⽵': '竹', '⽶': '米', '⽷': '糸', '⽸': '缶',
    '⽹': '网', '⽺': '羊', '⽻': '羽', '⽼': '老', '⽽': '而', '⽾': '耒', '⽿': '耳',
    '⾀': '聿', '⾁': '肉', '⾂': '臣', '⾃': '自', '⾄': '至', '⾅': '臼', '⾆': '舌',
    '⾇': '舟', '⾈': '色', '⾉': '艸', '⾊': '虍', '⾋': '虫', '⾌': '血', '⾍': '行',
    '⾎': '衣', '⾏': '行', '⾐': '衣', '⾟': '辛', '⾠': '辰', '⾡': '辶', '⾢': '邑',
    '⾣': '酉', '⾤': '采', '⾥': '里', '⾦': '金', '⾧': '长', '⾨': '门', '⾩': '阜',
    '⾪': '隶', '⾫': '隹', '⾬': '雨', '⾭': '青', '⾮': '非', '⾯': '面', '⾰': '革',
    '⾱': '韦', '⾲': '韭', '⾳': '音', '⾴': '页', '⾵': '风', '⾶': '飞', '⾷': '食',
    '⾸': '首', '⾹': '香', '⾺': '马', '⾻': '骨', '⾼': '高', '⾽': '髟', '⾾': '斗',
    '⾿': '鬯', '⿀': '鬲', '⿁': '鬼', '⿂': '鱼', '⿃': '鸟', '⿄': '卤', '⿅': '鹿',
    '⿆': '麦', '⿇': '麻', '⿈': '黄', '⿉': '黍', '⿊': '黑', '⿋': '黹', '⿌': '黽',
    '⿍': '鼎', '⿎': '鼓', '⿏': '鼠', '⿐': '鼻', '⿑': '齐', '⿒': '齿', '⿓': '龙',
    '⿔': '龟', '⿕': '龠',
}

def fix_cjk(text):
    for bad, good in CJK_FIX_MAP.items():
        text = text.replace(bad, good)
    return text

# ============================================================
# QUESTION DETECTION (Conservative)
# ============================================================

# Lines that are DEFINITELY not questions
NEVER_QUESTION_PREFIXES = [
    '//', '#', 'public ', 'private ', 'protected ', 'import ', 'package ',
    'return ', 'class ', 'interface ', 'enum ', 'void ', 'static ',
    'if (', 'for (', 'while (', 'switch (', 'try ', 'catch ',
    'throw ', 'throws ', '@Override', '@Autowired', '@Bean', '@Component',
    '@Service', '@Controller', '@RestController', '@Repository',
    '@Configuration', '@RequestMapping', '@GetMapping', '@PostMapping',
    '@SpringBootApplication', '@Mapper', '@Test',
    'console.log', 'System.out', 'System.err',
    'SELECT ', 'INSERT ', 'UPDATE ', 'DELETE ', 'CREATE ', 'ALTER ',
    'DROP ', 'FROM ', 'WHERE ', 'http://', 'https://',
    '公众号', '关注', '扫码', '微信', 'B站',
]

# Question indicator patterns (MUST match to be a question)
QUESTION_STARTERS = [
    '什么是', '什么叫', '如何理解', '如何实现', '如何保证', '如何解决',
    '如何处理', '如何优化', '如何进行', '如何设计', '如何使用',
    '为什么', '为何', '怎么理解', '怎样',
    '说一下', '说一说', '谈谈', '简述', '描述一下', '介绍一下',
    '解释一下', '列举', '说明一下',
    '什么是', '是什么',
]

# Topic-style: lines that look like interview topics (not fragments)
# These are full phrases that make sense as standalone questions
TOPIC_PATTERNS = [
    # "XXX和YYY的区别" pattern
    r'^.{4,40}(和|与|和).{2,40}(的区别|对比|比较|异同)$',
    # "XXX的原理/作用/特点/优势" pattern  
    r'^.{4,40}(的原理|的作用|的特点|的优势|的缺点|的实现|的机制|的本质)$',
    # "XXX是什么/有哪些" pattern
    r'^.{3,40}(是什么|有哪些|有哪几种|有几种)$',
    # "XXX如何YYY" pattern
    r'^.{3,30}如何.{2,30}$',
    # "为什么XXX" pattern
    r'^为什么.{3,50}$',
    # "XXX生命周期"
    r'^.{2,20}生命周期$',
    # "什么是XXX"
    r'^什么是.{2,40}$',
]

COMPILED_TOPIC = [re.compile(p) for p in TOPIC_PATTERNS]

def is_real_question(line, text_lines, idx):
    """
    Conservative check: is this line a real interview question?
    
    Returns (is_question, confidence) tuple.
    """
    line = line.strip()
    if len(line) < 6 or len(line) > 150:
        return False, 0
    
    # Never questions
    for prefix in NEVER_QUESTION_PREFIXES:
        if line.startswith(prefix):
            return False, 0
    
    # Pure numbers / numbering
    if re.match(r'^[\d.、，,\s]+$', line):
        return False, 0
    
    # Numbered list items: "1.xxx" "2、xxx"
    if re.match(r'^[\d]+[、.)]\s', line):
        return False, 0
    
    # Has question mark
    if line.endswith('？') or line.endswith('?'):
        # But must have enough Chinese content
        chinese = len(re.findall(r'[\u4e00-\u9fff]', line))
        if chinese >= 3:
            return True, 3
        # English question with question mark
        if len(line) > 10 and re.search(r'[A-Za-z]{3,}', line):
            return True, 2
    
    # Starts with question starters
    for starter in QUESTION_STARTERS:
        if line.startswith(starter):
            chinese = len(re.findall(r'[\u4e00-\u9fff]', line))
            if chinese >= 3:
                return True, 3
    
    # Topic patterns (full phrases)
    for p in COMPILED_TOPIC:
        if p.match(line):
            chinese = len(re.findall(r'[\u4e00-\u9fff]', line))
            if chinese >= 3:
                return True, 2
    
    # Well-known Java interview topics (exact match or close)
    KNOWN_TOPICS = [
        '面向对象', '封装继承多态', '接口和抽象类', 'HashMap', 'ConcurrentHashMap',
        'ArrayList', 'LinkedList', 'HashSet', 'TreeMap', 'Hashtable',
        'synchronized', 'volatile', 'ReentrantLock', 'ThreadLocal',
        '线程池', 'CAS', 'AQS', 'CountDownLatch', 'CyclicBarrier',
        '死锁', '乐观锁', '悲观锁',
        'JVM内存模型', 'JMM', '垃圾回收', 'GC', 'G1', 'CMS',
        '类加载机制', '双亲委派', '内存溢出', 'OOM',
        'Spring', 'IOC', 'AOP', 'Bean', 'SpringBoot',
        '事务', '事务传播', '循环依赖',
        'MyBatis', 'MySQL', 'B+树', '索引', 'MVCC',
        'Redis', 'Kafka', 'RabbitMQ', 'RocketMQ',
        'Elasticsearch', 'Docker', 'Kubernetes',
        'CAP', 'BASE', '分布式事务', '分布式锁',
        '微服务', '负载均衡', '消息队列',
        'TCP', 'UDP', 'HTTP', 'HTTPS',
        '单例模式', '工厂模式', '观察者模式',
        '反射', '泛型', '注解', '异常处理',
        '序列化', '深拷贝', '浅拷贝',
    ]
    
    # Check if line is a known topic (possibly with "的XXX" suffix)
    for topic in KNOWN_TOPICS:
        if line == topic or line.startswith(topic + '的') or line == topic + '原理' \
           or line == topic + '机制' or line == topic + '面试题':
            return True, 2
    
    return False, 0

# ============================================================
# ANSWER QUALITY
# ============================================================

def is_meaningful_answer(answer):
    """Check if answer text is substantial enough."""
    if not answer or len(answer) < 150:
        return False
    # Must have some Chinese content
    chinese = len(re.findall(r'[\u4e00-\u9fff]', answer))
    if chinese < 20:
        return False
    return True

def clean_question(q):
    """Clean question text."""
    q = q.strip()
    # Remove numbering
    q = re.sub(r'^[\d]+[、.．)]\s*', '', q)
    q = re.sub(r'^[（(][\d]+[）)]\s*', '', q)
    # Remove prefixes
    for prefix in ['问：', '问:', '答：', '答:', '面试题：', '面试题:',
                   'Q：', 'Q:', 'Q1：', 'Q2：', '题目：', '题目:', '请问']:
        if q.startswith(prefix):
            q = q[len(prefix):].strip()
    # Remove residual numbering
    q = re.sub(r'^[\d]+[、.．)]\s*', '', q)
    # Strip noise
    q = q.strip('：:？?')
    q = q.replace('|', '')
    q = re.sub(r'\s{2,}', ' ', q)
    return q.strip()

# ============================================================
# CLASSIFICATION
# ============================================================

CATEGORY_KEYWORDS = {
    'java-core': [
        'Java基础', '集合', 'Collection', 'HashMap', 'List', 'Set', 'Map',
        '泛型', '反射', '注解', 'IO', 'NIO', '异常', 'Exception',
        'String', 'StringBuilder', 'Object', 'equals', 'hashCode',
        '面向对象', 'OOP', '封装', '继承', '多态', '抽象类', '接口',
        '包装类', 'Integer', 'static', 'final', '变量',
        '重写', '重载', '内部类', 'Lambda', 'Stream', 'Optional',
        '值传递', '引用传递', '序列化',
    ],
    'concurrent': [
        '线程', 'Thread', '并发', '锁', 'Lock', 'synchronized',
        'volatile', 'AQS', 'ThreadLocal', 'CAS', '线程池',
        'Runnable', 'Callable', 'Future', 'CompletableFuture',
        'CountDownLatch', 'CyclicBarrier', 'Semaphore', 'Atomic',
        'BlockingQueue', 'ConcurrentHashMap', '死锁', 'ReentrantLock',
        'happens-before', '读写锁', '乐观锁', '悲观锁',
    ],
    'jvm': [
        'JVM', '内存模型', 'JMM', '内存区域', '堆', '栈', '方法区', '元空间',
        'GC', '垃圾回收', 'G1', 'CMS', 'ZGC',
        '类加载', 'ClassLoader', '双亲委派', '字节码', 'JIT',
        'OOM', '内存泄漏', '调优', 'jstat', 'jmap',
        'GC Roots', '可达性分析', '分代',
    ],
    'framework': [
        'Spring', 'Bean', 'IOC', 'DI', 'AOP', '事务', 'Transactional',
        'SpringBoot', '自动配置', 'Starter',
        'SpringCloud', 'Eureka', 'Nacos', 'Feign', 'Gateway',
        'Hystrix', 'Sentinel', '熔断', '降级',
        'MyBatis', 'Mapper', 'ORM',
        '循环依赖', '三级缓存', 'Bean生命周期',
    ],
    'database': [
        'MySQL', 'SQL', '索引', 'B+树', 'ACID',
        '隔离级别', 'MVCC', '行锁', '表锁', '间隙锁',
        '主从复制', 'binlog', 'redo log', 'undo log', '慢查询',
        'Redis', '缓存', 'RDB', 'AOF', '哨兵', 'Cluster',
        '缓存穿透', '缓存击穿', '缓存雪崩', 'LRU',
        '分库分表',
    ],
    'middleware': [
        'Kafka', 'RabbitMQ', 'RocketMQ', '消息队列', 'MQ',
        'Elasticsearch', 'ES', '倒排索引',
        'Zookeeper', 'Nginx', 'Netty', 'Tomcat',
        '消息可靠', '消息顺序', '消息积压', '幂等',
        'Producer', 'Consumer', 'Broker', 'Topic', 'Partition',
    ],
    'distributed': [
        '分布式', 'CAP', 'BASE', '一致性', 'Raft', 'Paxos',
        '分布式事务', '分布式锁', '2PC', '3PC', 'TCC', 'Saga', 'Seata',
        '微服务', '服务治理', '限流', '链路追踪',
        'Docker', 'Kubernetes', 'K8s', '容器', 'DevOps',
        '一致性哈希', '脑裂', '幂等性', '雪花算法',
    ],
}

def classify(question, answer, section=''):
    text = (question + ' ' + answer + ' ' + section)
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = sum(2 if kw in question else 1 for kw in keywords if kw in text)
        scores[cat] = score
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else 'java-core'

SUBCAT_KEYWORDS = {
    'java-core': {
        '集合框架': ['集合', 'Collection', 'HashMap', 'LinkedHashMap', 'TreeMap', 'ArrayList', 'LinkedList', 'HashSet', 'HashTable', 'Iterator', 'Map', 'List', 'Set', 'Queue'],
        '面向对象': ['面向对象', 'OOP', '封装', '继承', '多态', '抽象类', '接口', '重写', '重载', '构造器', '内部类'],
        '字符串': ['String', 'StringBuilder', 'StringBuffer', '字符'],
        'IO/NIO': ['IO', 'NIO', 'Buffer', 'Channel', '序列化', '反序列化'],
        '异常处理': ['异常', 'Exception', 'Error', 'try-catch', 'throw'],
        '泛型': ['泛型', 'Generic', '类型擦除'],
        '反射': ['反射', 'Reflection', '动态代理'],
        '注解': ['注解', 'Annotation'],
        'Java基础': [],
    },
    'concurrent': {
        '线程池': ['线程池', 'ThreadPool', 'Executor', 'ForkJoin'],
        '锁机制': ['synchronized', 'ReentrantLock', 'ReadWriteLock', '死锁', '公平锁', '偏向锁', '乐观锁', '悲观锁'],
        'volatile': ['volatile', '内存屏障', '可见性'],
        'AQS': ['AQS', 'AbstractQueuedSynchronizer'],
        'ThreadLocal': ['ThreadLocal'],
        'CAS': ['CAS', 'CompareAndSwap', 'Unsafe'],
        'ConcurrentHashMap': ['ConcurrentHashMap'],
        'BlockingQueue': ['BlockingQueue', 'ArrayBlockingQueue', 'LinkedBlockingQueue'],
        '原子类': ['AtomicInteger', 'AtomicLong', 'AtomicReference', 'LongAdder'],
        '并发工具': ['CountDownLatch', 'CyclicBarrier', 'Semaphore'],
        '线程基础': [],
    },
    'jvm': {
        'GC算法': ['GC', '垃圾回收', 'G1', 'CMS', 'ZGC', '标记清除', '复制算法', '可达性分析'],
        'GC调优': ['调优', 'JVM参数', 'jstat', 'jmap', 'jstack', 'OOM', '内存泄漏'],
        '内存区域': ['内存', '堆', '栈', '方法区', '元空间', 'Eden', 'Survivor'],
        '类加载': ['类加载', 'ClassLoader', '双亲委派'],
        'JMM': ['JMM', 'happens-before', 'Java内存模型'],
        '字节码': ['字节码', 'bytecode', 'JIT', '逃逸分析'],
    },
    'framework': {
        'Spring AOP': ['AOP', '切面', '代理', 'CGLIB', 'AspectJ'],
        'Spring事务': ['事务', 'Transactional', '传播行为', '事务失效'],
        'Spring Boot': ['SpringBoot', 'Spring Boot', '自动配置', 'Starter'],
        'Spring Cloud': ['SpringCloud', 'Eureka', 'Nacos', 'Feign', 'Gateway', 'Hystrix', 'Sentinel', '熔断'],
        'MyBatis': ['MyBatis', 'Mapper', 'ORM', 'SqlSession', '缓存', '动态SQL'],
        'Spring核心': [],
    },
    'database': {
        '索引': ['索引', 'B+树', '聚簇', '覆盖索引', '联合索引', '最左匹配'],
        'SQL优化': ['慢查询', '执行计划', 'SQL优化', '查询优化'],
        '事务隔离': ['ACID', '隔离级别', '脏读', '幻读', 'MVCC', 'undo', 'redo', 'binlog'],
        'MySQL锁': ['行锁', '表锁', '间隙锁', 'Next-Key', '共享锁', '排他锁'],
        'Redis': ['Redis', '数据类型', 'ZSet', 'HyperLogLog'],
        'Redis持久化': ['RDB', 'AOF', '持久化', 'bgsave'],
        'Redis集群': ['哨兵', 'Sentinel', 'Cluster', '主从复制', '槽位', '脑裂'],
        'Redis缓存': ['缓存穿透', '缓存击穿', '缓存雪崩', 'LRU', 'LFU', '布隆'],
        'MySQL': [],
    },
    'middleware': {
        'Kafka': ['Kafka', 'Producer', 'Consumer', 'Broker', 'Partition', 'Offset'],
        'RabbitMQ': ['RabbitMQ', 'Exchange', 'Queue', '死信', '延迟队列'],
        'RocketMQ': ['RocketMQ', 'NameServer', 'MessageQueue'],
        '消息队列': ['消息队列', '消息可靠', '消息顺序', '消息积压', '消息丢失', '幂等'],
        'Elasticsearch': ['Elasticsearch', 'ES', '倒排索引', '分词', 'Mapping'],
        '负载均衡': ['Nginx', '负载均衡', '反向代理', 'LVS'],
    },
    'distributed': {
        '分布式事务': ['分布式事务', '2PC', '3PC', 'TCC', 'Saga', 'Seata', 'XA'],
        '分布式锁': ['分布式锁', 'Redlock', 'Redisson'],
        '微服务': ['微服务', '服务治理', '服务注册', '链路追踪', 'SkyWalking'],
        '容器化': ['Docker', 'Kubernetes', 'K8s', '容器', 'Pod', 'Deployment', '镜像', 'Dockerfile'],
        '负载均衡': ['负载均衡', '一致性哈希', '轮询'],
        '分布式理论': [],
    },
}

def get_subcat(q_text, a_text, category):
    rules = SUBCAT_KEYWORDS.get(category, {})
    text = q_text + ' ' + a_text
    best, best_score = None, 0
    for subcat, keywords in rules.items():
        if not keywords:
            continue
        score = sum(3 if kw in q_text else 1 for kw in keywords if kw in text)
        if score > best_score:
            best_score = score
            best = subcat
    if best and best_score >= 2:
        return best
    defaults = {'java-core': 'Java基础', 'concurrent': '线程基础', 'jvm': '内存区域',
                'framework': 'Spring核心', 'database': 'MySQL', 'middleware': '消息队列',
                'distributed': '分布式理论'}
    return defaults.get(category, 'Java基础')

# ============================================================
# DIFFICULTY
# ============================================================

EXPERT_KW = ['源码', '底层实现', '底层原理', '性能调优', '架构设计', '高可用', '高并发', 'Raft', 'Paxos']
ADVANCED_KW = ['AQS', 'CAS', 'G1', 'ZGC', 'CMS', 'MVCC', 'B+树', '2PC', 'TCC', 'CAP', 'BASE',
               'happens-before', '双亲委派', '偏向锁', 'ReentrantLock', 'Sentinel', 'Redlock']
INTERMEDIATE_KW = ['synchronized', 'volatile', '线程池', 'HashMap', 'Spring', 'IOC', 'AOP',
                   '事务', 'MyBatis', 'Redis', 'MySQL', '索引', 'Kafka', 'RabbitMQ', 'GC',
                   '反射', '泛型', 'NIO', '多态', '接口', '异常']

def estimate_difficulty(question, answer):
    text = question + ' ' + answer
    al = len(answer)
    expert = sum(1 for kw in EXPERT_KW if kw in text)
    advanced = sum(1 for kw in ADVANCED_KW if kw in text)
    intermediate = sum(1 for kw in INTERMEDIATE_KW if kw in text)
    
    if expert >= 2 or (expert >= 1 and al > 2000):
        return 'L5'
    if expert >= 1 or advanced >= 4 or (advanced >= 2 and al > 1500):
        return 'L4'
    if advanced >= 2 or (intermediate >= 3 and al > 800):
        return 'L3'
    if intermediate >= 1 or al > 300:
        return 'L2'
    return 'L1'

# ============================================================
# TAGS
# ============================================================

TAG_MAP = {
    'HashMap': ['HashMap'], 'ConcurrentHashMap': ['ConcurrentHashMap'],
    'ArrayList': ['ArrayList'], 'LinkedList': ['LinkedList'],
    'synchronized': ['synchronized'], 'volatile': ['volatile'],
    'ReentrantLock': ['ReentrantLock'], 'ThreadLocal': ['ThreadLocal'],
    'AQS': ['AQS'], 'CAS': ['CAS'], '线程池': ['线程池', 'ThreadPoolExecutor'],
    'JVM': ['JVM'], 'GC': ['GC', '垃圾回收'], 'G1': ['G1'], 'CMS': ['CMS'],
    '类加载': ['类加载', 'ClassLoader', '双亲委派'],
    'Spring': ['Spring'], 'IOC': ['IOC', 'DI'], 'AOP': ['AOP'],
    'SpringBoot': ['SpringBoot', 'Spring Boot'],
    'MyBatis': ['MyBatis'], '事务': ['Transactional', '事务'],
    'MySQL': ['MySQL'], 'Redis': ['Redis'], '索引': ['索引', 'B+树'],
    'MVCC': ['MVCC'], 'Kafka': ['Kafka'], 'RabbitMQ': ['RabbitMQ'],
    'RocketMQ': ['RocketMQ'], 'Elasticsearch': ['Elasticsearch', 'ES'],
    'Docker': ['Docker'], 'Kubernetes': ['Kubernetes', 'K8s'],
    'CAP': ['CAP'], '分布式事务': ['分布式事务', '2PC', 'TCC', 'Seata'],
    '微服务': ['微服务'], '分布式锁': ['分布式锁'],
    '死锁': ['死锁'], '循环依赖': ['循环依赖'],
    'Redis缓存': ['缓存穿透', '缓存雪崩', 'LRU'],
}

def gen_tags(q):
    text = q['question'] + ' ' + q['answer']
    tags = []
    for tag, keywords in TAG_MAP.items():
        for kw in keywords:
            if kw.lower() in text.lower():
                if tag not in tags:
                    tags.append(tag)
                break
    return tags[:6]

# ============================================================
# FOLLOW-UPS
# ============================================================

FOLLOWUP_RULES = {
    'HashMap': ['HashMap 的扩容机制是怎样的？', 'HashMap 和 ConcurrentHashMap 的区别？'],
    'synchronized': ['synchronized 和 ReentrantLock 的区别？', 'synchronized 的锁升级过程是怎样的？'],
    'volatile': ['volatile 能保证原子性吗？为什么？'],
    '线程池': ['线程池的核心参数有哪些？', '线程池的拒绝策略有哪些？'],
    'AQS': ['AQS 的底层实现原理是什么？'],
    'CAS': ['CAS 的 ABA 问题是什么？如何解决？'],
    'ThreadLocal': ['ThreadLocal 会导致内存泄漏吗？'],
    'GC': ['G1 和 CMS 有什么区别？', '如何选择垃圾收集器？'],
    'Spring': ['Spring Bean 的生命周期是怎样的？', 'Spring 如何解决循环依赖？'],
    'AOP': ['JDK 动态代理和 CGLIB 的区别？'],
    '事务': ['Spring 事务的传播行为有哪些？', 'Spring 事务在什么情况下会失效？'],
    '索引': ['什么是覆盖索引？', '索引失效的场景有哪些？'],
    'Redis': ['Redis 持久化方式有哪些？', '如何保证缓存和数据库一致性？'],
    'Kafka': ['Kafka 如何保证消息不丢失？'],
    'CAP': ['CAP 定理的三个特性分别是什么？'],
    '分布式事务': ['分布式事务有哪些解决方案？'],
    'Docker': ['Docker 的网络模式有哪些？'],
    '微服务': ['微服务架构有什么优缺点？'],
}

def gen_followups(q):
    text = q['question'] + ' ' + q['answer']
    fus = []
    for topic, templates in FOLLOWUP_RULES.items():
        if topic.lower() in text.lower():
            for t in templates:
                if q['question'] not in t and t not in q['question'] and t not in fus:
                    fus.append(t)
    return fus[:3]

# ============================================================
# TEXT EXTRACTION
# ============================================================

def extract_pdf(path):
    doc = fitz.open(path)
    pages = []
    for i in range(len(doc)):
        text = fix_cjk(doc[i].get_text())
        if text.strip():
            pages.append((i+1, text))
    doc.close()
    return pages

def extract_epub(path):
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup
    book = epub.read_epub(path, options={'ignore_ncx': True})
    chapters = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), 'html.parser')
        text = fix_cjk(soup.get_text(separator='\n'))
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        text = '\n'.join(lines)
        if len(text) > 100:
            chapters.append((item.get_name(), text))
    return chapters

# ============================================================
# SKIP PATTERNS
# ============================================================

SKIP_RE = [
    re.compile(r'^\d+$'),
    re.compile(r'^Page\s+\d+'),
    re.compile(r'^第\d+页'),
    re.compile(r'^https?://'),
    re.compile(r'^公众号'),
    re.compile(r'^关注'),
    re.compile(r'^扫码'),
    re.compile(r'^代码随想录'),
    re.compile(r'^Copyright'),
    re.compile(r'^\s*$'),
]

def should_skip(line):
    for p in SKIP_RE:
        if p.match(line.strip()):
            return True
    return False

# ============================================================
# DEDUP
# ============================================================

def normalize_q(q):
    q = re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]', '', q.lower())
    stopwords = '什么是如何为什么的说在了和与及给把被让从对为到上下去出来里外'
    for sw in stopwords:
        q = q.replace(sw, '')
    return q

def is_dup(q1, q2):
    n1, n2 = normalize_q(q1), normalize_q(q2)
    if not n1 or not n2:
        return False
    if n1 == n2:
        return True
    if len(n1) > 8 and len(n2) > 8 and (n1 in n2 or n2 in n1):
        return True
    s1, s2 = set(n1), set(n2)
    j = len(s1 & s2) / max(len(s1 | s2), 1)
    return j > 0.8 and abs(len(n1) - len(n2)) < max(len(n1), len(n2)) * 0.3

# ============================================================
# MAIN PIPELINE
# ============================================================

def process_book(path):
    """Extract real Q&A pairs from a book."""
    book_name = os.path.basename(path)
    
    if path.endswith('.pdf'):
        pages = extract_pdf(path)
        full_text = '\n'.join(text for _, text in pages)
    elif path.endswith('.epub'):
        chapters = extract_epub(path)
        full_text = '\n'.join(text for _, text in chapters)
    else:
        return []
    
    lines = full_text.split('\n')
    qa_pairs = []
    current_q = None
    current_a = []
    current_section = ''
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or should_skip(stripped):
            continue
        
        # Check if real question
        is_q, confidence = is_real_question(stripped, lines, i)
        
        if is_q:
            # Save previous
            if current_q and current_a:
                answer = '\n'.join(current_a).strip()
                if is_meaningful_answer(answer):
                    qa_pairs.append({
                        'question': current_q,
                        'answer': answer,
                        'section': current_section,
                        '_source': book_name,
                    })
            
            current_q = clean_question(stripped)
            current_a = []
        else:
            if current_q:
                current_a.append(stripped)
    
    # Last one
    if current_q and current_a:
        answer = '\n'.join(current_a).strip()
        if is_meaningful_answer(answer):
            qa_pairs.append({
                'question': current_q,
                'answer': answer,
                'section': current_section,
                '_source': book_name,
            })
    
    return qa_pairs

def format_answer(text):
    """Light markdown formatting."""
    if not text:
        return text
    lines = text.split('\n')
    formatted = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            formatted.append('')
            continue
        # Numbered list → proper markdown
        m = re.match(r'^([\d]+)[、.)]\s*(.*)', stripped)
        if m:
            formatted.append(f"{m.group(1)}. {m.group(2)}")
            continue
        # Bullet points
        if re.match(r'^[•●○▪◦\-*]\s*\S', stripped):
            formatted.append(f"- {re.sub(r'^[•●○▪◦\-*]\s*', '', stripped)}")
            continue
        # Label: "XXX：" → bold
        lm = re.match(r'^([^\s:：]{2,15})[：:]\s*(.*)', stripped)
        if lm and not any(stripped.startswith(p) for p in ['http', 'public', 'private', 'import']):
            label = lm.group(1)
            if not any(c in label for c in '=;{}()<>|'):
                formatted.append(f"**{label}：** {lm.group(2)}")
                continue
        formatted.append(stripped)
    
    result = '\n'.join(formatted)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()

def main():
    books_dir = '/opt/data/projects/java-interview/books'
    output_dir = '/opt/data/projects/java-interview/data'
    
    print("=" * 60)
    print("V2 CONSERVATIVE EXTRACTION")
    print("=" * 60)
    
    # Process all books
    all_qa = []
    for fname in sorted(os.listdir(books_dir)):
        path = os.path.join(books_dir, fname)
        if not os.path.isfile(path):
            continue
        if not (fname.endswith('.pdf') or fname.endswith('.epub')):
            continue
        
        qa = process_book(path)
        print(f"  {fname}: {len(qa)} real Q&A pairs")
        all_qa.extend(qa)
    
    print(f"\nTotal extracted: {len(all_qa)}")
    
    # Dedup
    groups = defaultdict(list)
    for qa in all_qa:
        key = normalize_q(qa['question'])
        groups[key].append(qa)
    
    deduped = []
    for key, group in groups.items():
        group.sort(key=lambda x: len(x['answer']), reverse=True)
        deduped.append(group[0])
    
    print(f"After exact dedup: {len(deduped)}")
    
    # Fuzzy dedup
    final = []
    for qa in deduped:
        is_dup_flag = False
        for fq in final:
            if is_dup(qa['question'], fq['question']):
                if len(qa['answer']) > len(fq['answer']):
                    final[final.index(fq)] = qa
                is_dup_flag = True
                break
        if not is_dup_flag:
            final.append(qa)
    
    print(f"After fuzzy dedup: {len(final)}")
    
    # Classify and format
    cat_data = defaultdict(list)
    for qa in final:
        cat = classify(qa['question'], qa['answer'], qa.get('section', ''))
        subcat = get_subcat(qa['question'], qa['answer'], cat)
        diff = estimate_difficulty(qa['question'], qa['answer'])
        
        formatted = {
            'question': clean_question(qa['question']),
            'answer': format_answer(qa['answer']),
            'category': cat,
            'subcategory': subcat,
            'difficulty': diff,
            'tags': [],
            'follow_up': [],
        }
        formatted['tags'] = gen_tags(formatted)
        formatted['follow_up'] = gen_followups(formatted)
        cat_data[cat].append(formatted)
    
    # Sort by difficulty then ID
    diff_order = {'L1': 1, 'L2': 2, 'L3': 3, 'L4': 4, 'L5': 5}
    
    cat_prefixes = {
        'java-core': 'core', 'concurrent': 'conc', 'jvm': 'jvm',
        'framework': 'fw', 'database': 'db', 'middleware': 'mw', 'distributed': 'dist',
    }
    cat_files = {
        'java-core': 'java-core.json', 'concurrent': 'concurrent.json',
        'jvm': 'jvm.json', 'framework': 'framework.json',
        'database': 'database.json', 'middleware': 'middleware.json',
        'distributed': 'distributed.json',
    }
    
    print("\n" + "=" * 60)
    print("FINAL OUTPUT")
    print("=" * 60)
    
    total = 0
    for cat, questions in sorted(cat_data.items()):
        questions.sort(key=lambda x: (diff_order.get(x['difficulty'], 9), x['question']))
        prefix = cat_prefixes.get(cat, 'misc')
        for i, q in enumerate(questions, 1):
            q['id'] = f"{prefix}-{i:03d}"
        
        path = os.path.join(output_dir, cat_files.get(cat, f'{cat}.json'))
        # Ensure proper field order
        output = []
        for q in questions:
            output.append({
                'id': q['id'],
                'category': q['category'],
                'subcategory': q['subcategory'],
                'difficulty': q['difficulty'],
                'tags': q['tags'],
                'question': q['question'],
                'answer': q['answer'],
                'follow_up': q['follow_up'],
            })
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        total += len(questions)
        
        # Stats
        diff_counts = defaultdict(int)
        subcat_counts = defaultdict(int)
        for q in questions:
            diff_counts[q['difficulty']] += 1
            subcat_counts[q['subcategory']] += 1
        top_subcats = sorted(subcat_counts.items(), key=lambda x: -x[1])[:5]
        
        print(f"\n  {cat_files[cat]}: {len(questions)} questions")
        print(f"    Subcats: {', '.join(f'{s}({c})' for s, c in top_subcats)}")
        print(f"    Difficulty: {dict(diff_counts)}")
    
    print(f"\n{'='*60}")
    print(f"TOTAL: {total} high-quality questions")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
