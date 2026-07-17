#!/usr/bin/env python3
"""
V3 Extractor: TOC-driven extraction for two core Java PDFs.

Strategy:
- Use the PDF's built-in Table of Contents (bookmarks) to identify questions
- For each TOC entry (leaf level), extract the corresponding page text as the answer
- Extract images from those pages and associate them
- This gives us MUCH better coverage than line-by-line text parsing
"""
import fitz
import json
import re
import os
from collections import defaultdict

CJK_FIX_MAP = {
    '⽅': '方', '⼩': '小', '⽬': '目', '⽇': '日', '⽉': '月', '⽔': '水', '⽕': '火',
    '⼤': '大', '⼈': '人', '⼼': '心', '⼿': '手', '⼒': '力', '⼥': '女',
    '⼀': '一', '⼆': '二', '⼟': '土', '⽊': '木', '⽤': '用', '⽥': '田',
    '⽩': '白', '⽚': '片', '⽛': '牙', '⽜': '牛', '⽪': '皮', '⽭': '矛',
    '⽮': '矢', '⽯': '石', '⽰': '示', '⽲': '禾', '⽳': '穴', '⽴': '立',
    '⽵': '竹', '⽶': '米', '⽷': '糸', '⽸': '缶', '⽹': '网', '⽺': '羊',
    '⽻': '羽', '⽼': '老', '⽽': '而', '⽾': '耒', '⽿': '耳', '⾀': '聿',
    '⾁': '肉', '⾂': '臣', '⾃': '自', '⾄': '至', '⾅': '臼', '⾆': '舌',
    '⾇': '舟', '⾈': '色', '⾉': '艸', '⾊': '虍', '⾋': '虫', '⾌': '血',
    '⾍': '行', '⾎': '衣', '⾏': '行', '⾐': '衣', '⾟': '辛', '⾠': '辰',
    '⾡': '辶', '⾢': '邑', '⾣': '酉', '⾤': '采', '⾥': '里', '⾦': '金',
    '⾧': '长', '⾨': '门', '⾩': '阜', '⾪': '隶', '⾫': '隹', '⾬': '雨',
    '⾭': '青', '⾮': '非', '⾯': '面', '⾰': '革', '⾱': '韦', '⾲': '韭',
    '⾳': '音', '⾴': '页', '⾵': '风', '⾶': '飞', '⾷': '食', '⾸': '首',
    '⾹': '香', '⾺': '马', '⾻': '骨', '⾼': '高', '⾽': '髟', '⾾': '斗',
    '⾿': '鬯', '⿀': '鬲', '⿁': '鬼', '⿂': '鱼', '⿃': '鸟', '⿄': '卤',
    '⿅': '鹿', '⿆': '麦', '⿇': '麻', '⿈': '黄', '⿉': '黍', '⿊': '黑',
    '⿋': '黹', '⿌': '黽', '⿍': '鼎', '⿎': '鼓', '⿏': '鼠', '⿐': '鼻',
    '⿑': '齐', '⿒': '齿', '⿓': '龙', '⿔': '龟', '⿕': '龠',
    '⼊': '入',
}
def fix_cjk(text):
    for bad, good in CJK_FIX_MAP.items():
        text = text.replace(bad, good)
    return text

def clean_title(title):
    """Clean a TOC title into a proper question."""
    t = title.strip()
    # Remove numbering like "2.1.3." at the start
    t = re.sub(r'^[\d]+([.、][\d]+)*[.、]\s*', '', t)
    t = re.sub(r'^[（(][\d]+[）)]\s*', '', t)
    return t.strip()

def is_leaf_question(title, level):
    """Check if a TOC entry is a leaf question (not a section header)."""
    t = clean_title(title)
    if len(t) < 4:
        return False
    # Skip pure section headers like "JVM", "Spring", chapter names
    if level <= 1:
        return False
    # Skip "目录", page references
    if '目录' in t or '..........' in t:
        return False
    return True

def is_real_java_question(title):
    """Filter out non-Java-backend questions from titles."""
    t = title.strip()
    
    # Frontend
    frontend = ['CSS', 'HTML', 'JSX', 'React', 'Vue', 'webpack', 'npm', '小程序']
    for kw in frontend:
        if kw in t:
            return False
    
    return True


def extract_images_from_page(doc, page_num, book_prefix):
    """Extract images from a page, return list of saved filenames."""
    page = doc[page_num]
    image_files = []
    
    for img_info in page.get_images():
        xref = img_info[0]
        try:
            pix = fitz.Pixmap(doc, xref)
            # Skip tiny images (icons, spacers)
            if pix.width < 50 or pix.height < 30:
                pix = None
                continue
            
            # Convert to RGB if needed
            if pix.n - pix.alpha > 3:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            
            # Generate filename
            img_name = f"{book_prefix}_p{page_num+1:04d}_img{xref}.png"
            img_path = f"/opt/data/projects/java-interview/images/{img_name}"
            
            # Only save if not already exists
            if not os.path.exists(img_path):
                pix.save(img_path)
            
            image_files.append(img_name)
            pix = None
        except Exception as e:
            pass
    
    return image_files


def get_page_range_for_toc_entry(toc_entries, idx):
    """Get the page range for a TOC entry (from its page to the next sibling/parent's page)."""
    entry = toc_entries[idx]
    level, title, start_page = entry
    start_page = start_page - 1  # Convert to 0-indexed
    
    # Find end page: next entry at same or higher (lower number) level
    end_page = start_page + 1
    for j in range(idx + 1, len(toc_entries)):
        next_level = toc_entries[j][0]
        if next_level <= level:
            break
        end_page = toc_entries[j][2] - 1  # 0-indexed
        # Don't let it go beyond
        end_page = max(end_page, start_page + 1)
    
    # Also cap at the next sibling at same level
    for j in range(idx + 1, len(toc_entries)):
        if toc_entries[j][0] <= level:
            end_page = min(end_page, toc_entries[j][2] - 1)
            break
    
    return start_page, min(end_page, start_page + 5)  # Max 5 pages per question


def process_pdf(pdf_path, book_prefix):
    """Process a PDF using TOC-driven extraction."""
    doc = fitz.open(pdf_path)
    toc = doc.get_toc()
    book_name = os.path.basename(pdf_path)
    
    print(f"\n{'='*60}")
    print(f"Processing: {book_name}")
    print(f"  Pages: {len(doc)}, TOC entries: {len(toc)}")
    
    if not toc:
        print("  WARNING: No TOC found, falling back to text parsing")
        doc.close()
        return []
    
    qa_pairs = []
    current_chapter = ''
    
    for i, (level, title, page_num) in enumerate(toc):
        title_clean = fix_cjk(title)
        
        # Track chapter context
        if level <= 2:
            current_chapter = clean_title(title_clean)
            continue
        
        # Check if this is a leaf question
        if not is_leaf_question(title_clean, level):
            continue
        
        question = clean_title(title_clean)
        if not is_real_java_question(question):
            continue
        
        # Get page range
        start_page, end_page = get_page_range_for_toc_entry(toc, i)
        start_page = max(0, min(start_page, len(doc) - 1))
        end_page = max(start_page + 1, min(end_page, len(doc)))
        
        # Extract text from page range
        answer_parts = []
        for p in range(start_page, end_page):
            text = fix_cjk(doc[p].get_text())
            # Clean up page headers/footers
            text = re.sub(r'\d{2}/\d{2}/\d{4}', '', text)
            text = re.sub(r'Page \d+ of \d+', '', text)
            text = re.sub(r'代码随想录.*', '', text)
            answer_parts.append(text)
        
        answer = '\n'.join(answer_parts).strip()
        
        # Extract images from these pages
        images = []
        for p in range(start_page, end_page):
            imgs = extract_images_from_page(doc, p, book_prefix)
            images.extend(imgs)
        
        # Quality filter
        if len(answer) < 100:
            continue
        if len(question) < 4:
            continue
        
        # Deduplicate the answer (remove repeated content)
        # Trim answer to reasonable length
        if len(answer) > 10000:
            answer = answer[:10000] + '\n\n...(内容过长已截断)'
        
        qa_pairs.append({
            'question': question,
            'answer': answer,
            'chapter': current_chapter,
            'images': images,
            '_source': book_name,
            '_page': page_num,
        })
    
    doc.close()
    print(f"  Extracted: {len(qa_pairs)} Q&A pairs")
    return qa_pairs


# ============================================================
# CLASSIFICATION (reused from previous scripts)
# ============================================================

CATEGORY_KEYWORDS = {
    'java-core': [
        'Java基础', '集合', 'HashMap', 'List', 'Set', 'Map', '泛型', '反射', '注解',
        'IO', 'NIO', '异常', 'Exception', 'String', 'StringBuilder', 'Object',
        '面向对象', 'OOP', '封装', '继承', '多态', '抽象类', '接口', 'Integer',
        'static', 'final', '重写', '重载', '内部类', 'Lambda', 'Stream', '序列化',
        '数据类型', '变量', '方法', '构造器', '值传递', '包装类',
    ],
    'concurrent': [
        '线程', 'Thread', '并发', '锁', 'Lock', 'synchronized', 'volatile',
        'AQS', 'ThreadLocal', 'CAS', '线程池', 'ThreadPool', 'Runnable',
        'Callable', 'Future', 'CompletableFuture', 'CountDownLatch',
        'CyclicBarrier', 'Semaphore', 'Atomic', 'BlockingQueue',
        'ConcurrentHashMap', '死锁', 'ReentrantLock', 'happens-before',
        '乐观锁', '悲观锁', '读写锁',
    ],
    'jvm': [
        'JVM', '内存模型', 'JMM', '内存区域', '堆', '栈', '方法区', '元空间',
        'GC', '垃圾回收', 'G1', 'CMS', 'ZGC', '类加载', 'ClassLoader',
        '双亲委派', '字节码', 'JIT', 'OOM', '内存泄漏', '调优',
        'GC Roots', '可达性分析', 'Eden', 'Survivor',
    ],
    'framework': [
        'Spring', 'Bean', 'IOC', 'DI', 'AOP', '事务', 'Transactional',
        'SpringBoot', '自动配置', 'Starter', 'SpringCloud', 'Eureka',
        'Nacos', 'Feign', 'Gateway', 'Hystrix', 'Sentinel', 'MyBatis',
        'Mapper', 'ORM', '循环依赖', '三级缓存', 'Bean生命周期',
    ],
    'database': [
        'MySQL', 'SQL', '索引', 'B+树', 'ACID', '隔离级别', 'MVCC',
        '行锁', '表锁', '间隙锁', 'binlog', 'redo log', 'undo log',
        'Redis', '缓存', 'RDB', 'AOF', '哨兵', 'Cluster',
        '缓存穿透', '缓存击穿', '缓存雪崩', 'LRU', '分库分表',
    ],
    'middleware': [
        'Kafka', 'RabbitMQ', 'RocketMQ', '消息队列', 'MQ',
        'Elasticsearch', 'ES', '倒排索引', 'Zookeeper', 'Nginx',
        'Netty', 'Tomcat', '消息可靠', '消息顺序', '消息积压', '幂等',
        'Producer', 'Consumer', 'Broker', 'Topic', 'Partition',
    ],
    'distributed': [
        '分布式', 'CAP', 'BASE', '一致性', 'Raft', 'Paxos',
        '分布式事务', '分布式锁', '2PC', '3PC', 'TCC', 'Saga', 'Seata',
        '微服务', '服务治理', '限流', '链路追踪', 'Docker', 'Kubernetes',
        'K8s', '容器', '一致性哈希', '脑裂', '幂等性',
    ],
}

SUBCAT_KEYWORDS = {
    'java-core': {
        '集合框架': ['集合', 'HashMap', 'LinkedHashMap', 'TreeMap', 'ArrayList', 'LinkedList', 'HashSet', 'HashTable', 'Map', 'List', 'Set', 'Queue'],
        '面向对象': ['面向对象', 'OOP', '封装', '继承', '多态', '抽象类', '接口', '重写', '重载', '构造器', '内部类'],
        '字符串': ['String', 'StringBuilder', 'StringBuffer'],
        'IO/NIO': ['IO', 'NIO', 'Buffer', 'Channel', '序列化', '反序列化'],
        '异常处理': ['异常', 'Exception', 'Error', 'throw'],
        '泛型': ['泛型', 'Generic'],
        '反射': ['反射', 'Reflection', '动态代理'],
        '注解': ['注解', 'Annotation'],
        'Java基础': [],
    },
    'concurrent': {
        '线程池': ['线程池', 'ThreadPool', 'Executor', 'ForkJoin'],
        '锁机制': ['synchronized', 'ReentrantLock', '死锁', '公平锁', '偏向锁', '乐观锁', '悲观锁'],
        'volatile': ['volatile', '内存屏障', '可见性'],
        'AQS': ['AQS', 'AbstractQueuedSynchronizer'],
        'ThreadLocal': ['ThreadLocal'],
        'CAS': ['CAS', 'CompareAndSwap'],
        'ConcurrentHashMap': ['ConcurrentHashMap'],
        'BlockingQueue': ['BlockingQueue', 'ArrayBlockingQueue'],
        '原子类': ['Atomic'],
        '并发工具': ['CountDownLatch', 'CyclicBarrier', 'Semaphore'],
        '线程基础': [],
    },
    'jvm': {
        'GC算法': ['GC', '垃圾回收', 'G1', 'CMS', 'ZGC', '标记清除', '复制算法'],
        'GC调优': ['调优', 'OOM', '内存泄漏', 'jstat', 'jmap'],
        '内存区域': ['内存', '堆', '栈', '方法区', '元空间', 'Eden', 'Survivor'],
        '类加载': ['类加载', 'ClassLoader', '双亲委派'],
        'JMM': ['JMM', 'happens-before', 'Java内存模型'],
        '字节码': ['字节码', 'bytecode', 'JIT'],
    },
    'framework': {
        'Spring AOP': ['AOP', '切面', '代理', 'CGLIB'],
        'Spring事务': ['事务', 'Transactional', '传播行为'],
        'Spring Boot': ['SpringBoot', '自动配置', 'Starter'],
        'Spring Cloud': ['SpringCloud', 'Eureka', 'Nacos', 'Feign', 'Sentinel', '熔断'],
        'MyBatis': ['MyBatis', 'Mapper', 'ORM', 'SqlSession'],
        'Spring核心': [],
    },
    'database': {
        '索引': ['索引', 'B+树', '聚簇', '覆盖索引', '联合索引'],
        'SQL优化': ['慢查询', '执行计划', 'SQL优化'],
        '事务隔离': ['ACID', '隔离级别', '脏读', '幻读', 'MVCC', 'undo', 'redo', 'binlog'],
        'MySQL锁': ['行锁', '表锁', '间隙锁', 'Next-Key'],
        'Redis': ['Redis', '数据类型', 'ZSet'],
        'Redis持久化': ['RDB', 'AOF', '持久化'],
        'Redis集群': ['哨兵', 'Sentinel', 'Cluster', '主从复制'],
        'Redis缓存': ['缓存穿透', '缓存击穿', '缓存雪崩', 'LRU'],
        'MySQL': [],
    },
    'middleware': {
        'Kafka': ['Kafka', 'Producer', 'Consumer', 'Broker', 'Partition'],
        'RabbitMQ': ['RabbitMQ', 'Exchange', 'Queue', '死信'],
        'RocketMQ': ['RocketMQ', 'NameServer'],
        '消息队列': ['消息队列', '消息可靠', '消息顺序', '消息积压'],
        'Elasticsearch': ['Elasticsearch', 'ES', '倒排索引'],
        '负载均衡': ['Nginx', '负载均衡', '反向代理'],
    },
    'distributed': {
        '分布式事务': ['分布式事务', '2PC', '3PC', 'TCC', 'Saga', 'Seata'],
        '分布式锁': ['分布式锁', 'Redlock', 'Redisson'],
        '微服务': ['微服务', '服务治理', '服务注册', '链路追踪'],
        '容器化': ['Docker', 'Kubernetes', 'K8s', '容器', 'Pod'],
        '负载均衡': ['负载均衡', '一致性哈希'],
        '分布式理论': [],
    },
}

def classify(q_text, a_text, chapter=''):
    text = q_text + ' ' + a_text + ' ' + chapter
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = sum(2 if kw in q_text else 1 for kw in keywords if kw in text)
        scores[cat] = score
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else 'java-core'

def get_subcat(q_text, a_text, cat):
    rules = SUBCAT_KEYWORDS.get(cat, {})
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
    return defaults.get(cat, 'Java基础')

EXPERT_KW = ['源码', '底层实现', '性能调优', '架构设计', '高可用', 'Raft', 'Paxos']
ADVANCED_KW = ['AQS', 'CAS', 'G1', 'ZGC', 'CMS', 'MVCC', 'B+树', '2PC', 'TCC', 'CAP',
               'happens-before', '双亲委派', '偏向锁', 'ReentrantLock']
INTERMEDIATE_KW = ['synchronized', 'volatile', '线程池', 'HashMap', 'Spring', 'IOC', 'AOP',
                   '事务', 'MyBatis', 'Redis', 'MySQL', '索引', 'Kafka', 'GC', '反射', '泛型']

def estimate_difficulty(q_text, a_text):
    text = q_text + ' ' + a_text
    al = len(a_text)
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

TAG_MAP = {
    'HashMap': ['HashMap'], 'ConcurrentHashMap': ['ConcurrentHashMap'],
    'ArrayList': ['ArrayList'], 'synchronized': ['synchronized'],
    'volatile': ['volatile'], 'ReentrantLock': ['ReentrantLock'],
    'ThreadLocal': ['ThreadLocal'], 'AQS': ['AQS'], 'CAS': ['CAS'],
    '线程池': ['线程池', 'ThreadPoolExecutor'], 'JVM': ['JVM'],
    'GC': ['GC', '垃圾回收'], 'G1': ['G1'],
    '类加载': ['类加载', 'ClassLoader', '双亲委派'],
    'Spring': ['Spring'], 'IOC': ['IOC', 'DI'], 'AOP': ['AOP'],
    'SpringBoot': ['SpringBoot', 'Spring Boot'],
    'MyBatis': ['MyBatis'], '事务': ['Transactional', '事务'],
    'MySQL': ['MySQL'], 'Redis': ['Redis'], '索引': ['索引', 'B+树'],
    'MVCC': ['MVCC'], 'Kafka': ['Kafka'], 'RabbitMQ': ['RabbitMQ'],
    'RocketMQ': ['RocketMQ'], 'Docker': ['Docker'],
    'CAP': ['CAP'], '分布式事务': ['分布式事务', '2PC', 'TCC', 'Seata'],
    '微服务': ['微服务'], '分布式锁': ['分布式锁'],
    '死锁': ['死锁'], '循环依赖': ['循环依赖'],
}

def gen_tags(q_text, a_text):
    text = q_text + ' ' + a_text
    tags = []
    for tag, keywords in TAG_MAP.items():
        for kw in keywords:
            if kw.lower() in text.lower():
                if tag not in tags:
                    tags.append(tag)
                break
    return tags[:6]

FOLLOWUP_RULES = {
    'HashMap': ['HashMap 的扩容机制是怎样的？', 'HashMap 和 ConcurrentHashMap 的区别？'],
    'synchronized': ['synchronized 和 ReentrantLock 的区别？', 'synchronized 的锁升级过程是怎样的？'],
    'volatile': ['volatile 能保证原子性吗？'],
    '线程池': ['线程池的核心参数有哪些？', '线程池的拒绝策略有哪些？'],
    'GC': ['G1 和 CMS 有什么区别？'],
    'Spring': ['Spring Bean 的生命周期是怎样的？'],
    '事务': ['Spring 事务的传播行为有哪些？'],
    '索引': ['什么是覆盖索引？', '索引失效的场景有哪些？'],
    'Redis': ['Redis 持久化方式有哪些？'],
    'Kafka': ['Kafka 如何保证消息不丢失？'],
    '分布式事务': ['分布式事务有哪些解决方案？'],
}

def gen_followups(q_text, a_text):
    text = q_text + ' ' + a_text
    fus = []
    for topic, templates in FOLLOWUP_RULES.items():
        if topic.lower() in text.lower():
            for t in templates:
                if q_text not in t and t not in q_text and t not in fus:
                    fus.append(t)
    return fus[:3]

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
    return len(set(n1) & set(n2)) / max(len(set(n1) | set(n2)), 1) > 0.8


# ============================================================
# MAIN
# ============================================================

def main():
    books = [
        ("/opt/data/projects/java-interview/books/JAVA核心知识点整理.pdf", "corenotes"),
        ("/opt/data/projects/java-interview/books/代码随想录-八股文（第五版）.pdf", "baguwen"),
    ]
    
    print("=" * 60)
    print("V3 TOC-DRIVEN EXTRACTION WITH IMAGES")
    print("=" * 60)
    
    os.makedirs("/opt/data/projects/java-interview/images", exist_ok=True)
    
    all_qa = []
    for pdf_path, book_prefix in books:
        qa = process_pdf(pdf_path, book_prefix)
        all_qa.extend(qa)
    
    print(f"\nTotal extracted: {len(all_qa)}")
    
    # Dedup within new set
    groups = defaultdict(list)
    for qa in all_qa:
        key = normalize_q(qa['question'])
        groups[key].append(qa)
    
    deduped = []
    for key, group in groups.items():
        group.sort(key=lambda x: len(x['answer']), reverse=True)
        deduped.append(group[0])
    
    print(f"After internal dedup: {len(deduped)}")
    
    # Load existing questions for cross-dedup
    data_dir = '/opt/data/projects/java-interview/data'
    existing_titles = set()
    existing_data = {}
    for fname in os.listdir(data_dir):
        if not fname.endswith('.json'):
            continue
        with open(os.path.join(data_dir, fname)) as f:
            data = json.load(f)
        for q in data:
            existing_titles.add(normalize_q(q['question']))
        existing_data[fname.replace('.json', '')] = data
    
    # Remove duplicates against existing
    new_questions = []
    for qa in deduped:
        norm = normalize_q(qa['question'])
        is_existing = False
        for et in existing_titles:
            if is_dup(qa['question'], et):
                is_existing = True
                break
        if not is_existing:
            new_questions.append(qa)
    
    print(f"After cross-dedup with existing: {len(new_questions)} new questions")
    
    # Classify and format
    cat_data = defaultdict(list)
    for qa in new_questions:
        cat = classify(qa['question'], qa['answer'], qa.get('chapter', ''))
        subcat = get_subcat(qa['question'], qa['answer'], cat)
        diff = estimate_difficulty(qa['question'], qa['answer'])
        tags = gen_tags(qa['question'], qa['answer'])
        fus = gen_followups(qa['question'], qa['answer'])
        
        formatted = {
            'question': qa['question'],
            'answer': qa['answer'],
            'category': cat,
            'subcategory': subcat,
            'difficulty': diff,
            'tags': tags,
            'follow_up': fus,
            'images': qa.get('images', []),
        }
        cat_data[cat].append(formatted)
    
    # Merge into existing data files
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
    
    print(f"\n{'='*60}")
    print("MERGING INTO EXISTING DATA")
    print("=" * 60)
    
    total_existing = 0
    total_new = 0
    
    for cat, new_qs in sorted(cat_data.items()):
        fname = cat_files.get(cat)
        if not fname:
            continue
        
        path = os.path.join(data_dir, fname)
        with open(path) as f:
            existing = json.load(f)
        
        total_existing += len(existing)
        
        # Merge: add new questions to existing
        merged = existing + new_qs
        
        # Sort by difficulty then question
        diff_order = {'L1': 1, 'L2': 2, 'L3': 3, 'L4': 4, 'L5': 5}
        merged.sort(key=lambda x: (diff_order.get(x['difficulty'], 9), x['question']))
        
        # Renumber
        prefix = cat_prefixes.get(cat, 'misc')
        for i, q in enumerate(merged, 1):
            q['id'] = f"{prefix}-{i:03d}"
        
        # Ensure images field exists for old questions
        for q in merged:
            if 'images' not in q:
                q['images'] = []
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        
        total_new += len(new_qs)
        
        # Stats
        with_images = sum(1 for q in new_qs if q.get('images'))
        total_images = sum(len(q.get('images', [])) for q in new_qs)
        
        print(f"  {fname}: {len(existing)} + {len(new_qs)} new = {len(merged)} total ({with_images} with images, {total_images} images)")
    
    print(f"\n{'='*60}")
    print(f"SUMMARY: {total_existing} existing + {total_new} new = {total_existing + total_new} total")
    print(f"{'='*60}")
    
    # Count total images
    img_count = len(os.listdir("/opt/data/projects/java-interview/images"))
    print(f"Images in images/ directory: {img_count}")

if __name__ == '__main__':
    main()
