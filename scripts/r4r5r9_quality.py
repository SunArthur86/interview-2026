#!/usr/bin/env python3
"""
R4+R5+R9: Difficulty rebalancing, subcategory fix, and tag enrichment.
These three passes share the same iteration pattern, so we run them together.
"""
import json
import re
import os
from collections import defaultdict

# ============================================================
# R4: DIFFICULTY REBALANCING
# ============================================================

# Advanced keywords that indicate higher difficulty
EXPERT_KEYWORDS = [
    '源码分析', '源码层面', '底层实现', '底层原理', '源码剖析',
    '性能调优', 'JVM调优', 'GC调优', '架构设计', '高可用', '高并发',
    '分布式架构', '一致性算法', 'Raft', 'Paxos', 'ZAB',
    '零拷贝', '内存屏障', ' happens-before',
]

ADVANCED_KEYWORDS = [
    'AQS', 'CAS', 'CLH', 'Unsafe', 'compareAndSet',
    'G1', 'ZGC', 'CMS', 'Shenandoah', 'RememberedSet',
    'MVCC', 'undo log', 'redo log', '两阶段提交', 'WAL',
    'B+树', '聚簇索引', '覆盖索引', '最左匹配',
    '2PC', '3PC', 'TCC', 'Saga', 'Seata',
    'CAP', 'BASE', '一致性哈希', 'Gossip',
    '类加载器', '双亲委派', '打破双亲',
    'JMM', 'happens-before', '指令重排', '内存屏障',
    'ThreadLocalMap', 'InheritableThreadLocal',
    '偏向锁', '轻量级锁', '重量级锁', '自旋锁', '自适应自旋',
    ' volatile', 'ReentrantLock', 'ReadWriteLock', 'StampedLock',
    'CompletableFuture', 'ForkJoin', 'Phaser',
    'Sentinel', 'Hystrix', '熔断', '降级', '限流',
    'Redlock', 'Redisson', '布隆过滤器',
    'Elasticsearch', '倒排索引', 'BM25',
    'Docker', 'Kubernetes', 'Service Mesh',
    '设计模式', '单例', '工厂', '观察者', '责任链', '策略模式',
]

INTERMEDIATE_KEYWORDS = [
    'synchronized', 'volatile', '线程池', 'ThreadPool',
    'HashMap', 'ConcurrentHashMap', 'ArrayList', 'LinkedList',
    'Spring', 'IOC', 'AOP', 'Bean', '事务', 'Transactional',
    'MyBatis', 'Mapper', '缓存',
    'Redis', 'RDB', 'AOF', '哨兵', 'Cluster',
    'MySQL', '索引', '隔离级别', '锁',
    'Kafka', 'RabbitMQ', 'RocketMQ', '消息队列',
    'Java', 'JVM', 'GC', '垃圾回收',
    '反射', '泛型', '注解', 'Lambda', 'Stream',
    'NIO', 'Netty', 'BIO',
    '接口', '抽象类', '多态', '继承', '封装',
    '异常', '集合', '并发', '锁',
]

def estimate_difficulty(question, answer):
    """Re-estimate difficulty based on content depth (not just answer length)."""
    text = question + ' ' + answer
    ans_len = len(answer)
    
    expert_count = sum(1 for kw in EXPERT_KEYWORDS if kw in text)
    advanced_count = sum(1 for kw in ADVANCED_KEYWORDS if kw in text)
    intermediate_count = sum(1 for kw in INTERMEDIATE_KEYWORDS if kw in text)
    
    # Check for code complexity
    has_code = '```' in answer or answer.count('{') > 3
    has_multilayer = answer.count('\n') > 15
    
    # Expert: source code, deep architecture, tuning
    if expert_count >= 2 or (expert_count >= 1 and ans_len > 2000):
        return 'L5'
    
    # Advanced: AQS/CAS/G1/MVCC/distributed concepts + substantial explanation
    if expert_count >= 1 or advanced_count >= 4 or (advanced_count >= 2 and ans_len > 1500):
        return 'L4'
    
    # Intermediate: common framework/concept questions with moderate depth
    if advanced_count >= 2 or (intermediate_count >= 3 and ans_len > 800) or (has_code and ans_len > 600):
        return 'L3'
    
    # Basic: basic concepts, short answers
    if intermediate_count >= 1 or ans_len > 300:
        return 'L2'
    
    # Entry: simple definitions
    return 'L1'

# ============================================================
# R5: SUBCATEGORY FIX
# ============================================================

SUBCAT_RULES = {
    'java-core': {
        '集合框架': ['集合', 'Collection', 'HashMap', 'LinkedHashMap', 'TreeMap', 'ArrayList',
                   'LinkedList', 'HashSet', 'TreeSet', 'HashTable', 'Iterator', 'Map', 'List', 'Set', 'Queue'],
        '面向对象': ['面向对象', 'OOP', '封装', '继承', '多态', '抽象类', '接口', '重写', '重载',
                   'override', 'overload', '构造器', '内部类', '代理'],
        '字符串': ['String', 'StringBuilder', 'StringBuffer', '字符'],
        'IO/NIO': ['IO', 'NIO', 'Buffer', 'Channel', 'Selector', '序列化', 'FileInputStream'],
        '异常处理': ['异常', 'Exception', 'Error', 'try-catch', 'throw', 'throws'],
        '泛型': ['泛型', 'Generic', '类型擦除'],
        '反射': ['反射', 'Reflection', 'Class对象', '动态代理'],
        '注解': ['注解', 'Annotation'],
        'Java基础': [],  # fallback
    },
    'concurrent': {
        '线程池': ['线程池', 'ThreadPool', 'Executor', 'ForkJoin', 'ThreadPoolExecutor'],
        '锁机制': ['synchronized', 'ReentrantLock', 'ReadWriteLock', '死锁', '公平锁', '偏向锁',
                  '轻量级锁', '自旋锁', '乐观锁', '悲观锁', 'Lock'],
        'volatile': ['volatile', '内存屏障', '可见性', '有序性'],
        'AQS': ['AQS', 'AbstractQueuedSynchronizer', 'CLH'],
        'ThreadLocal': ['ThreadLocal'],
        'CAS': ['CAS', 'CompareAndSwap', 'Unsafe'],
        'ConcurrentHashMap': ['ConcurrentHashMap', '分段锁'],
        'BlockingQueue': ['BlockingQueue', 'ArrayBlockingQueue', 'LinkedBlockingQueue'],
        '原子类': ['AtomicInteger', 'AtomicLong', 'AtomicReference', 'LongAdder'],
        '并发工具': ['CountDownLatch', 'CyclicBarrier', 'Semaphore', 'Exchanger', 'Phaser'],
        '线程基础': [],  # fallback
    },
    'jvm': {
        'GC算法': ['GC', '垃圾回收', '垃圾收集', 'G1', 'CMS', 'ZGC', '标记清除', '复制算法', '可达性分析'],
        'GC调优': ['调优', 'JVM参数', 'jstat', 'jmap', 'jstack', 'arthas', 'OOM', '内存泄漏', '监控'],
        '内存区域': ['内存', '堆', '栈', '方法区', '元空间', 'Eden', 'Survivor', '老年代', '运行时数据'],
        '类加载': ['类加载', 'ClassLoader', '双亲委派', '加载器', '类初始化'],
        'JMM': ['JMM', 'happens-before', 'Java内存模型', '主内存', '工作内存'],
        '字节码': ['字节码', 'bytecode', 'JIT', '逃逸分析', '编译优化'],
    },
    'framework': {
        'Spring AOP': ['AOP', '切面', '代理', 'JDK动态代理', 'CGLIB', 'AspectJ', 'Pointcut'],
        'Spring事务': ['事务', 'Transactional', '传播行为', '事务失效', '声明式事务'],
        'Spring Boot': ['SpringBoot', 'Spring Boot', '自动配置', 'Starter', 'EnableAutoConfiguration'],
        'Spring Cloud': ['SpringCloud', 'Spring Cloud', 'Eureka', 'Nacos', 'Feign', 'Gateway',
                        'Hystrix', 'Sentinel', '服务注册', '熔断', '降级'],
        'MyBatis': ['MyBatis', 'Mapper', 'ORM', 'SqlSession', '一二级缓存', '动态SQL', 'resultMap'],
        'Spring核心': [],  # fallback for Spring/IOC/DI/Bean
    },
    'database': {
        '索引': ['索引', 'Index', 'B+树', 'B树', '聚簇', '覆盖索引', '联合索引', '最左匹配', 'explain'],
        'SQL优化': ['慢查询', '执行计划', 'SQL优化', '查询优化', '分页优化'],
        '事务隔离': ['ACID', '隔离级别', '脏读', '幻读', '不可重复读', 'MVCC', 'undo', 'redo', 'binlog'],
        'MySQL锁': ['行锁', '表锁', '间隙锁', '意向锁', 'Next-Key', '共享锁', '排他锁', 'MDL'],
        'Redis': ['Redis', '数据类型', 'ZSet', 'HyperLogLog', 'Geo', 'Stream'],
        'Redis持久化': ['RDB', 'AOF', '持久化', 'bgsave', '混合持久化'],
        'Redis集群': ['哨兵', 'Sentinel', 'Cluster', '主从复制', '槽位', '脑裂'],
        'Redis缓存': ['缓存穿透', '缓存击穿', '缓存雪崩', '缓存一致性', 'LRU', 'LFU', '布隆过滤器'],
        'MySQL': [],  # fallback
    },
    'middleware': {
        'Kafka': ['Kafka', 'Producer', 'Consumer', 'Broker', 'Partition', 'Offset', 'ISR'],
        'RabbitMQ': ['RabbitMQ', 'Exchange', 'Queue', '死信', '延迟队列', 'Channel'],
        'RocketMQ': ['RocketMQ', 'NameServer', 'MessageQueue', 'Producer', 'Consumer'],
        '消息队列': ['消息队列', '消息可靠', '消息顺序', '消息积压', '消息丢失', '幂等', '重复消费'],
        'Elasticsearch': ['Elasticsearch', 'ES', '倒排索引', '分词', 'Mapping', '聚合'],
        '负载均衡': ['Nginx', '负载均衡', '反向代理', 'LVS', '一致性哈希'],
    },
    'distributed': {
        '分布式事务': ['分布式事务', '2PC', '3PC', 'TCC', 'Saga', 'Seata', 'XA', '本地消息表'],
        '分布式锁': ['分布式锁', 'Redlock', 'Redisson', 'Zookeeper分布式锁'],
        '微服务': ['微服务', '服务治理', '服务注册', '服务发现', 'API网关', '链路追踪', 'SkyWalking'],
        '容器化': ['Docker', 'Kubernetes', 'K8s', '容器', 'Pod', 'Deployment', '镜像', 'Dockerfile'],
        '负载均衡': ['负载均衡', 'Nginx', '一致性哈希', '轮询'],
        '分布式理论': [],  # fallback for CAP/BASE/一致性
    },
}

def reclassify_subcategory(q, category):
    """Reclassify subcategory using improved keyword matching."""
    if category not in SUBCAT_RULES:
        return q.get('subcategory', '')
    
    rules = SUBCAT_RULES[category]
    text = (q['question'] + ' ' + q['answer']).lower()
    q_lower = q['question'].lower()
    
    best_subcat = None
    best_score = 0
    
    for subcat, keywords in rules.items():
        if not keywords:  # fallback subcat, skip
            continue
        score = 0
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in q_lower:
                score += 3  # In question = strong signal
            elif kw_lower in text:
                score += 1
        if score > best_score:
            best_score = score
            best_subcat = subcat
    
    if best_subcat and best_score >= 2:
        return best_subcat
    
    # Fallback
    fallbacks = {
        'java-core': 'Java基础', 'concurrent': '线程基础', 'jvm': '内存区域',
        'framework': 'Spring核心', 'database': 'MySQL', 'middleware': '消息队列',
        'distributed': '分布式理论',
    }
    return fallbacks.get(category, q.get('subcategory', ''))

# ============================================================
# R9: TAG ENRICHMENT
# ============================================================

TAG_KEYWORDS = {
    # Java Core
    'HashMap': ['HashMap'], 'ConcurrentHashMap': ['ConcurrentHashMap'],
    'ArrayList': ['ArrayList'], 'LinkedList': ['LinkedList'],
    'HashSet': ['HashSet'], 'TreeMap': ['TreeMap'],
    'String': ['String'], 'StringBuilder': ['StringBuilder'],
    'Integer': ['Integer'], 'Object': ['Object类'],
    'equals': ['equals', 'hashCode'],
    'static': ['static'], 'final': ['final'],
    '泛型': ['泛型', 'Generic'], '反射': ['反射', 'Reflection'],
    '注解': ['注解', 'Annotation'], 'Lambda': ['Lambda'],
    'Stream': ['Stream API'], 'Optional': ['Optional'],
    'IO': ['IO', 'NIO'], '序列化': ['序列化', 'Serializable'],
    '异常': ['Exception', '异常处理'],
    # Concurrent
    'synchronized': ['synchronized'], 'volatile': ['volatile'],
    'ReentrantLock': ['ReentrantLock'], 'ThreadLocal': ['ThreadLocal'],
    'AQS': ['AQS'], 'CAS': ['CAS'],
    '线程池': ['线程池', 'ThreadPoolExecutor'],
    'CountDownLatch': ['CountDownLatch'], 'CompletableFuture': ['CompletableFuture'],
    'ConcurrentHashMap': ['ConcurrentHashMap'],
    # JVM
    'JVM': ['JVM'], 'GC': ['GC', '垃圾回收'],
    'G1': ['G1'], 'CMS': ['CMS'],
    '类加载': ['类加载', 'ClassLoader', '双亲委派'],
    'JMM': ['JMM', 'Java内存模型'],
    'OOM': ['OOM', 'OutOfMemory'],
    # Framework
    'Spring': ['Spring'], 'IOC': ['IOC', 'DI'],
    'AOP': ['AOP', '切面'], 'Bean': ['Bean'],
    'SpringBoot': ['SpringBoot', 'Spring Boot'],
    'SpringCloud': ['SpringCloud', 'Spring Cloud'],
    'MyBatis': ['MyBatis'],
    '事务': ['Transactional', '事务管理', 'Spring事务'],
    '循环依赖': ['循环依赖', '三级缓存'],
    # Database
    'MySQL': ['MySQL'], 'Redis': ['Redis'],
    '索引': ['索引', 'B+树', 'Index'],
    'MVCC': ['MVCC'], 'B+树': ['B+树'],
    'RDB': ['RDB'], 'AOF': ['AOF'],
    '缓存穿透': ['缓存穿透'], '缓存雪崩': ['缓存雪崩'],
    # Middleware
    'Kafka': ['Kafka'], 'RabbitMQ': ['RabbitMQ'], 'RocketMQ': ['RocketMQ'],
    'Elasticsearch': ['Elasticsearch', 'ES'],
    'Nginx': ['Nginx'], 'Netty': ['Netty'],
    'Zookeeper': ['Zookeeper', 'ZK'],
    # Distributed
    'CAP': ['CAP'], '分布式事务': ['分布式事务', '2PC', 'TCC', 'Seata'],
    'Docker': ['Docker'], 'Kubernetes': ['Kubernetes', 'K8s'],
    '微服务': ['微服务'], '分布式锁': ['分布式锁'],
    '熔断': ['Hystrix', 'Sentinel', '熔断'],
}

def enrich_tags(q):
    """Generate better tags from question + answer content."""
    text = q['question'] + ' ' + q['answer']
    tags = []
    
    for tag, keywords in TAG_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text.lower():
                if tag not in tags:
                    tags.append(tag)
                break
    
    return tags[:6]  # Max 6 tags

# ============================================================
# MAIN
# ============================================================

def process_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    changes = {'difficulty': 0, 'subcategory': 0, 'tags': 0}
    
    for q in data:
        # R4: Difficulty rebalance
        old_diff = q.get('difficulty', 'L2')
        new_diff = estimate_difficulty(q['question'], q['answer'])
        if old_diff != new_diff:
            changes['difficulty'] += 1
        q['difficulty'] = new_diff
        
        # R5: Subcategory fix
        old_sub = q.get('subcategory', '')
        new_sub = reclassify_subcategory(q, q['category'])
        if old_sub != new_sub:
            changes['subcategory'] += 1
        q['subcategory'] = new_sub
        
        # R9: Tag enrichment
        old_tags = set(q.get('tags', []))
        new_tags = enrich_tags(q)
        if set(new_tags) != old_tags:
            changes['tags'] += 1
        q['tags'] = new_tags
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return len(data), changes

def main():
    projects = [
        '/opt/data/projects/java-interview/data',
        '/opt/data/projects/ai-interview/data',
    ]
    
    print("=" * 60)
    print("R4+R5+R9: Difficulty / Subcategory / Tags")
    print("=" * 60)
    
    for data_dir in projects:
        proj = os.path.basename(os.path.dirname(data_dir))
        print(f"\n--- {proj} ---")
        for fname in sorted(os.listdir(data_dir)):
            if not fname.endswith('.json'):
                continue
            path = os.path.join(data_dir, fname)
            count, changes = process_file(path)
            
            # Print if notable changes
            if changes['difficulty'] > 0 or changes['subcategory'] > 0:
                print(f"  {fname}: {count} Q | diff:{changes['difficulty']} subcat:{changes['subcategory']} tags:{changes['tags']}")
        
        # Print difficulty distribution
        print(f"\n  Difficulty distribution:")
        all_diff = defaultdict(int)
        all_subcat = defaultdict(int)
        for fname in sorted(os.listdir(data_dir)):
            if not fname.endswith('.json'):
                continue
            with open(os.path.join(data_dir, fname), 'r') as f:
                data = json.load(f)
            for q in data:
                all_diff[q['difficulty']] += 1
                all_subcat[q['subcategory']] += 1
        for d in ['L1', 'L2', 'L3', 'L4', 'L5']:
            pct = all_diff[d] / max(sum(all_diff.values()), 1) * 100
            print(f"    {d}: {all_diff[d]} ({pct:.0f}%)")

if __name__ == '__main__':
    main()
