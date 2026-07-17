#!/usr/bin/env python3
"""
Post-process: clean question text, fix subcategories, filter low quality.
"""
import json
import re
import os
from collections import defaultdict

DATA_DIR = "/opt/data/projects/java-interview/data"

def clean_question(q):
    """Remove numbering prefixes and clean up question text."""
    q = q.strip()
    # Remove numbering: "1、", "2.", "3、", "1) ", "（1）", etc.
    q = re.sub(r'^[\d]+[、.．)]\s*', '', q)
    q = re.sub(r'^[（(][\d]+[）)]\s*', '', q)
    q = re.sub(r'^第[一二三四五六七八九十\d]+[题章节条步步]\s*[：:]*\s*', '', q)
    # Remove leading "问：" etc
    for prefix in ['问：', '问:', '答：', '答:', '面试题：', '面试题:', 'Q：', 'Q:', '题目：', '题目:']:
        if q.startswith(prefix):
            q = q[len(prefix):].strip()
    # Remove numbering after removal (e.g., "1、什么是..." → "什么是..." → already handled)
    q = re.sub(r'^[\d]+[、.．)]\s*', '', q)
    return q.strip()

def is_valid_question(q_text, a_text):
    """Additional quality filters."""
    # Too short
    if len(a_text) < 50:
        return False
    # Question too long (likely a paragraph, not a question)
    if len(q_text) > 150:
        return False
    # Pure code entries
    if q_text.count(';') > 3 and q_text.count('{') > 1:
        return False
    # Numbering-only (after cleanup, if it's just a number)
    if re.match(r'^[\d.、，,\s]+$', q_text):
        return False
    # Lines that are clearly NOT questions (too fragmentary)
    if len(q_text) < 4:
        return False
    # Skip lines that are clearly code snippets
    code_indicators = ['public class', 'private ', 'protected ', 'import ', 
                       'package ', '@Override', '@Autowired', '@Bean',
                       'return ', 'System.out', 'void ', 'static ']
    if any(q_text.startswith(ci) for ci in code_indicators):
        return False
    # Skip lines that are clearly answer fragments (start with these)
    answer_starts = ['1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.',
                     '首先', '具体的', '具体的⽅式', '具体⽅式']
    if any(q_text.startswith(af) for af in answer_starts) and len(q_text) < 30:
        return False
    
    return True

# Better subcategory mapping per category
CAT_SUBCAT_PRIORITY = {
    'java-core': ['集合框架', '面向对象', '泛型', '反射', '注解', 'IO/NIO', '异常处理', '字符串', 'Java基础'],
    'concurrent': ['线程基础', '线程池', '锁机制', 'volatile', 'AQS', 'ThreadLocal', 'CAS', 'ConcurrentHashMap', 'BlockingQueue', '并发工具', '原子类'],
    'jvm': ['JMM', '内存区域', 'GC算法', 'GC调优', '类加载', '字节码'],
    'framework': ['Spring核心', 'Spring AOP', 'Spring事务', 'Spring Boot', 'Spring Cloud', 'MyBatis'],
    'database': ['MySQL', '索引', 'SQL优化', '事务隔离', 'MySQL锁', 'Redis', 'Redis持久化', 'Redis集群', 'Redis缓存'],
    'middleware': ['Kafka', 'RabbitMQ', 'RocketMQ', '消息队列', 'Elasticsearch', '负载均衡'],
    'distributed': ['分布式理论', '分布式事务', '分布式锁', '微服务', '容器化', '负载均衡'],
}

def fix_subcategory(q, category):
    """Ensure subcategory is valid for the category."""
    valid_subcats = CAT_SUBCAT_PRIORITY.get(category, ['Java基础'])
    if q['subcategory'] not in valid_subcats:
        # Try to reclassify based on content
        text = q['question'] + ' ' + q['answer']
        for subcat in valid_subcats:
            # Check keywords for this subcat from SUBCAT_MAP
            # Simple fallback: use the first valid subcat as default
            pass
        # Default fallback
        defaults = {
            'java-core': 'Java基础',
            'concurrent': '线程基础',
            'jvm': '内存区域',
            'framework': 'Spring核心',
            'database': 'MySQL',
            'middleware': '消息队列',
            'distributed': '分布式理论',
        }
        return defaults.get(category, 'Java基础')
    return q['subcategory']

# Category-specific subcategory keyword matching
SUBCAT_KEYWORDS = {
    'concurrent': {
        '线程池': ['线程池', 'ThreadPool', 'Executor', 'ForkJoin', 'newFixed', 'newCached', 'newScheduled'],
        '锁机制': ['锁', 'Lock', 'synchronized', 'ReentrantLock', 'ReadWriteLock', '死锁', '偏向锁', '轻量级', '自旋'],
        'volatile': ['volatile', '内存屏障', '可见性'],
        'AQS': ['AQS', 'AbstractQueuedSynchronizer'],
        'ThreadLocal': ['ThreadLocal'],
        'CAS': ['CAS', 'CompareAndSwap', 'Unsafe'],
        'ConcurrentHashMap': ['ConcurrentHashMap'],
        'BlockingQueue': ['BlockingQueue', 'ArrayBlocking', 'LinkedBlocking'],
        '原子类': ['Atomic', 'AtomicInteger', 'AtomicLong', 'LongAdder'],
        '并发工具': ['CountDownLatch', 'CyclicBarrier', 'Semaphore'],
        '线程基础': ['线程', 'Thread', '进程', '并发', 'Runnable', 'Callable'],
    },
    'jvm': {
        'GC算法': ['GC', '垃圾回收', '垃圾收集', 'G1', 'CMS', 'ZGC', '标记清除', '复制算法', '可达性'],
        'GC调优': ['调优', 'JVM参数', 'jstat', 'jmap', 'jstack', 'OOM', '内存泄漏', 'arthas', '监控'],
        '内存区域': ['内存', '堆', '栈', '方法区', '元空间', 'Eden', 'Survivor', '老年代', '运行时'],
        '类加载': ['类加载', 'ClassLoader', '双亲委派', '加载器', '初始化'],
        'JMM': ['JMM', 'happens-before', '内存模型', '主内存', '工作内存'],
        '字节码': ['字节码', 'bytecode', 'JIT', '编译优化', '逃逸分析'],
    },
    'database': {
        '索引': ['索引', 'Index', 'B+树', 'B树', 'Hash索引', '聚簇', '覆盖索引', '联合索引', '最左匹配'],
        'SQL优化': ['慢查询', '执行计划', 'explain', 'SQL优化', '查询优化', '分页'],
        '事务隔离': ['ACID', '隔离级别', '脏读', '幻读', '不可重复读', 'MVCC', 'undo log', 'redo log', 'binlog'],
        'MySQL锁': ['行锁', '表锁', '间隙锁', '意向锁', 'Next-Key', '共享锁', '排他锁'],
        'Redis': ['Redis', '数据类型', 'String', 'Hash', 'ZSet', 'HyperLogLog'],
        'Redis持久化': ['RDB', 'AOF', '持久化', 'bgsave'],
        'Redis集群': ['哨兵', 'Sentinel', 'Cluster', '主从复制', '槽位', '脑裂'],
        'Redis缓存': ['缓存穿透', '缓存击穿', '缓存雪崩', '缓存一致性', '缓存淘汰', 'LRU', 'LFU', '布隆'],
        'MySQL': ['MySQL', 'SQL', 'InnoDB', 'MyISAM', '存储引擎', '数据库'],
    },
    'middleware': {
        'Kafka': ['Kafka', 'Producer', 'Consumer', 'Broker', 'Partition', 'Offset', 'ISR'],
        'RabbitMQ': ['RabbitMQ', 'Exchange', 'Queue', '死信', '延迟队列'],
        'RocketMQ': ['RocketMQ', 'NameServer', 'MessageQueue'],
        '消息队列': ['消息队列', 'MQ', '消息可靠', '消息顺序', '消息积压', '消息丢失', '幂等'],
        'Elasticsearch': ['Elasticsearch', 'ES', '倒排索引', '分词', 'Mapping'],
        '负载均衡': ['Nginx', '负载均衡', '负载', '反向代理', 'LVS'],
    },
    'distributed': {
        '分布式事务': ['分布式事务', '2PC', '3PC', 'TCC', 'Saga', 'Seata', 'XA'],
        '分布式锁': ['分布式锁', 'Redis分布式锁', 'Redlock', 'Redisson'],
        '微服务': ['微服务', '服务治理', '服务拆分', '服务注册', '服务发现', 'API网关', '链路追踪'],
        '容器化': ['Docker', 'Kubernetes', 'K8s', '容器', 'Pod', 'Deployment', '镜像', 'Dockerfile'],
        '负载均衡': ['负载均衡', 'Nginx', '一致性哈希', '轮询'],
        '分布式理论': ['CAP', 'BASE', '一致性', '分区容错', '分布式系统', '共识'],
    },
    'framework': {
        'Spring AOP': ['AOP', '切面', '切点', '代理', 'JDK动态代理', 'CGLIB', 'AspectJ'],
        'Spring事务': ['事务', 'Transactional', '传播行为', '事务失效'],
        'Spring Boot': ['SpringBoot', 'Spring Boot', '自动配置', 'Starter', 'EnableAutoConfiguration'],
        'Spring Cloud': ['SpringCloud', 'Spring Cloud', 'Eureka', 'Nacos', 'Feign', 'Ribbon', 'Gateway', 'Hystrix', 'Sentinel'],
        'MyBatis': ['MyBatis', 'Mapper', 'ORM', 'SqlSession', '缓存', '动态SQL', 'resultMap'],
        'Spring核心': ['Spring', 'IOC', 'DI', 'Bean', 'ApplicationContext', 'BeanFactory', '循环依赖', '三级缓存'],
    },
}

def reclassify_subcategory(q, category):
    """Reclassify subcategory based on category-specific keywords."""
    if category not in SUBCAT_KEYWORDS:
        return q['subcategory']
    
    text = q['question'] + ' ' + q['answer']
    best_subcat = None
    best_score = 0
    
    for subcat, keywords in SUBCAT_KEYWORDS[category].items():
        score = sum(3 if kw in q['question'] else 1 for kw in keywords if kw in text)
        if score > best_score:
            best_score = score
            best_subcat = subcat
    
    if best_subcat and best_score > 0:
        return best_subcat
    
    defaults = {
        'concurrent': '线程基础',
        'jvm': '内存区域',
        'database': 'MySQL',
        'middleware': '消息队列',
        'distributed': '分布式理论',
        'framework': 'Spring核心',
        'java-core': 'Java基础',
    }
    return defaults.get(category, 'Java基础')

def main():
    total_in = 0
    total_out = 0
    
    category_files = {
        'java-core': 'java-core.json',
        'concurrent': 'concurrent.json',
        'jvm': 'jvm.json',
        'framework': 'framework.json',
        'database': 'database.json',
        'middleware': 'middleware.json',
        'distributed': 'distributed.json',
    }
    
    for cat, filename in category_files.items():
        path = os.path.join(DATA_DIR, filename)
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        total_in += len(data)
        
        cleaned = []
        for q in data:
            q['question'] = clean_question(q['question'])
            q['answer'] = q['answer'].strip()
            
            if not is_valid_question(q['question'], q['answer']):
                continue
            
            # Reclassify subcategory
            q['subcategory'] = reclassify_subcategory(q, cat)
            
            cleaned.append(q)
        
        # Renumber IDs
        for i, q in enumerate(cleaned, 1):
            cat_prefix = {
                'java-core': 'core', 'concurrent': 'conc', 'jvm': 'jvm',
                'framework': 'fw', 'database': 'db', 'middleware': 'mw', 'distributed': 'dist',
            }.get(cat, 'misc')
            q['id'] = f"{cat_prefix}-{i:03d}"
        
        total_out += len(cleaned)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(cleaned, f, ensure_ascii=False, indent=2)
        
        # Stats
        subcat_counts = defaultdict(int)
        for q in cleaned:
            subcat_counts[q['subcategory']] += 1
        diff_counts = defaultdict(int)
        for q in cleaned:
            diff_counts[q['difficulty']] += 1
        
        print(f"\n{filename}: {len(cleaned)} (removed {len(data) - len(cleaned)})")
        print(f"  Subcats: {dict(subcat_counts)}")
        print(f"  Difficulty: {dict(diff_counts)}")
    
    print(f"\n{'='*60}")
    print(f"TOTAL: {total_in} → {total_out} (removed {total_in - total_out})")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
