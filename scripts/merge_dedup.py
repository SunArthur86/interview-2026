#!/usr/bin/env python3
"""
Merge all raw book extractions → deduplicate → classify → write final data/*.json

Steps:
1. Load all raw_book*.json files
2. Normalize question text for dedup
3. Group by similarity, keep best answer
4. Filter low-quality entries
5. Assign IDs, subcategories
6. Write to data/*.json by category
"""
import json
import re
import os
import sys
from collections import defaultdict

BOOKS_DIR = "/tmp"
OUTPUT_DIR = "/opt/data/projects/java-interview/data"

# ============================================================
# SUBCATEGORY KEYWORDS (maps to config.js subcatGroups)
# ============================================================
SUBCAT_MAP = {
    # Java基础
    'Java基础': ['Java基础', 'JavaSE', '概述', '数据类型', '变量', '方法', '包装类',
                '自动装箱', '自动拆箱', 'static', 'final', '值传递', '引用传递'],
    '集合框架': ['集合', 'Collection', 'HashMap', 'LinkedHashMap', 'TreeMap',
                'ArrayList', 'LinkedList', 'HashSet', 'TreeSet', 'ConcurrentHashMap',
                'HashTable', 'Iterator', 'Map', 'List', 'Set', 'Queue', 'Deque'],
    '面向对象': ['面向对象', 'OOP', '封装', '继承', '多态', '抽象类', '接口',
                '重写', '重载', 'override', 'overload', '构造器', '内部类'],
    '泛型': ['泛型', 'Generic', '类型擦除'],
    '反射': ['反射', 'Reflection', 'Class', '动态代理'],
    '注解': ['注解', 'Annotation'],
    'IO/NIO': ['IO', 'NIO', 'Buffer', 'Channel', 'Selector', '流', 'Stream', 'FileInputStream'],
    '异常处理': ['异常', 'Exception', 'Error', 'try', 'catch', 'finally', 'throw'],
    '字符串': ['String', 'StringBuilder', 'StringBuffer', '字符', 'CharSequence'],

    # 线程与锁
    '线程基础': ['线程', 'Thread', 'Runnable', 'Callable', '线程创建', '生命周期',
                '守护线程', 'sleep', 'wait', 'notify', 'join', 'yield'],
    '线程池': ['线程池', 'ThreadPool', 'ThreadPoolExecutor', 'Executor', 'Executors',
              'ForkJoin', 'newFixedThreadPool', 'newCachedThreadPool'],
    '锁机制': ['锁', 'Lock', 'synchronized', 'ReentrantLock', 'ReadWriteLock',
              '公平锁', '非公平锁', '乐观锁', '悲观锁', '死锁', '活锁',
              '偏向锁', '轻量级锁', '重量级锁', '自旋锁', 'mutex'],
    'volatile': ['volatile', '内存屏障', '内存可见性'],
    'AQS': ['AQS', 'AbstractQueuedSynchronizer', 'CLH', 'state'],
    'ThreadLocal': ['ThreadLocal', 'ThreadLocalMap', 'InheritableThreadLocal'],

    # 并发工具
    '并发工具': ['CountDownLatch', 'CyclicBarrier', 'Semaphore', 'Exchanger',
                'Phaser', '并发工具'],
    '原子类': ['Atomic', 'AtomicInteger', 'AtomicLong', 'AtomicReference',
              'LongAdder', 'LongAccumulator'],
    'CAS': ['CAS', 'CompareAndSwap', 'Unsafe', 'compareAndSet'],
    'ConcurrentHashMap': ['ConcurrentHashMap', '分段锁', 'Node', 'CAS'],
    'BlockingQueue': ['BlockingQueue', 'ArrayBlockingQueue', 'LinkedBlockingQueue',
                     'SynchronousQueue', 'PriorityBlockingQueue'],

    # JVM
    'JMM': ['JMM', 'Java内存模型', 'happens-before', '内存屏障', '主内存', '工作内存'],
    '内存区域': ['内存区域', '堆', '栈', '方法区', '元空间', 'Metaspace',
                '程序计数器', '运行时数据区', 'Eden', 'Survivor', '老年代'],
    'GC算法': ['GC', '垃圾回收', '垃圾收集', 'G1', 'CMS', 'ZGC', 'Serial',
              'ParNew', 'Parallel', '标记清除', '标记整理', '复制算法',
              '分代收集', 'GC Roots', '可达性分析', 'STW'],
    'GC调优': ['调优', 'JVM参数', 'Xmx', 'Xms', 'jstat', 'jmap', 'jstack',
              'arthas', '性能监控', 'OOM', 'OutOfMemory', '内存泄漏'],
    '类加载': ['类加载', 'ClassLoader', '双亲委派', '加载器', '类初始化',
              'clinit', 'init'],
    '字节码': ['字节码', 'bytecode', 'JIT', '编译优化', '逃逸分析'],

    # Spring
    'Spring核心': ['Spring', 'IOC', 'DI', 'Bean', 'ApplicationContext',
                  'BeanFactory', 'BeanPostProcessor', 'Bean生命周期',
                  '循环依赖', '三级缓存', 'Aware'],
    'Spring AOP': ['AOP', '切面', '切点', '通知', '代理', 'JDK动态代理',
                   'CGLIB', 'AspectJ', 'Pointcut', 'JoinPoint'],
    'Spring事务': ['事务', 'Transactional', '传播行为', '隔离级别',
                  '声明式事务', '编程式事务', '事务失效'],
    'Spring Boot': ['SpringBoot', 'Spring Boot', '自动配置', 'Starter',
                   '@EnableAutoConfiguration', '条件注解'],
    'Spring Cloud': ['SpringCloud', 'Spring Cloud', 'Eureka', 'Nacos',
                    'Feign', 'Ribbon', 'Gateway', 'Hystrix', 'Sentinel',
                    '服务注册', '配置中心', '熔断', '降级'],

    # MyBatis
    'MyBatis': ['MyBatis', 'Mapper', 'ORM', 'SqlSession', '一二级缓存',
               '动态SQL', 'resultMap', '#{}', '${}', '插件', 'Interceptor'],

    # MySQL
    'MySQL': ['MySQL', 'SQL', 'InnoDB', 'MyISAM', '存储引擎'],
    '索引': ['索引', 'Index', 'B+树', 'B树', 'Hash索引', '聚簇索引',
            '非聚簇索引', '覆盖索引', '联合索引', '最左匹配', 'explain'],
    'SQL优化': ['慢查询', '执行计划', 'SQL优化', '查询优化', '分页优化'],
    '事务隔离': ['ACID', '隔离级别', '脏读', '幻读', '不可重复读',
               'MVCC', 'undo log', 'redo log', 'binlog', '两阶段提交'],
    'MySQL锁': ['行锁', '表锁', '间隙锁', '意向锁', 'Next-Key Lock',
               '共享锁', '排他锁', 'MDL锁'],

    # Redis
    'Redis': ['Redis', '数据类型', 'String', 'Hash', 'List', 'Set', 'ZSet',
             'HyperLogLog', 'Geo', 'Stream'],
    'Redis持久化': ['RDB', 'AOF', '持久化', 'bgsave', '混合持久化'],
    'Redis集群': ['哨兵', 'Sentinel', 'Cluster', '主从复制', '槽位',
                 '脑裂', 'Redis Cluster'],
    'Redis缓存': ['缓存穿透', '缓存击穿', '缓存雪崩', '缓存一致性',
                 '缓存淘汰', 'LRU', 'LFU', '过期策略', '布隆过滤器'],

    # 消息队列
    'Kafka': ['Kafka', 'Producer', 'Consumer', 'Broker', 'Topic',
             'Partition', 'Offset', 'Consumer Group', 'ISR', 'Leader',
             'Follower', 'Replication', 'Zookeeper'],
    'RabbitMQ': ['RabbitMQ', 'Exchange', 'Queue', 'Binding', 'Channel',
                'Confirm', 'Return', '死信队列', '延迟队列'],
    'RocketMQ': ['RocketMQ', 'NameServer', 'Broker', 'Producer',
                'Consumer', 'MessageQueue', 'Tag', 'Group'],
    '消息队列': ['消息队列', 'MQ', '消息可靠性', '消息顺序', '消息积压',
               '消息丢失', '重复消费', '幂等性', '消费组'],

    # 搜索引擎
    'Elasticsearch': ['Elasticsearch', 'ES', '倒排索引', '分词', 'Mapping',
                     'Analysis', '聚合', '查询DSL', 'Score', 'TF-IDF'],

    # 分布式
    '分布式理论': ['CAP', 'BASE', '一致性', 'Consistency', '可用性',
                 '分区容错', '分布式系统'],
    '分布式事务': ['分布式事务', '2PC', '3PC', 'TCC', 'Saga', 'Seata',
                  'XA', '本地消息表', '最大努力通知'],
    '分布式锁': ['分布式锁', 'Redis分布式锁', 'Zookeeper分布式锁',
               'Redlock', 'Redisson'],
    '微服务': ['微服务', '服务治理', '服务拆分', '服务注册', '服务发现',
             'API网关', '链路追踪', 'SkyWalking', 'Zipkin'],
    '容器化': ['Docker', 'Kubernetes', 'K8s', '容器', 'Pod', 'Deployment',
             'Service', 'Ingress', '镜像', 'Dockerfile', 'CI/CD', 'DevOps'],
    '负载均衡': ['负载均衡', 'Nginx', 'Ribbon', '一致性哈希',
               '轮询', '加权', '最少连接', 'LVS'],
}

def get_subcategory(question, answer, category):
    """Determine subcategory based on keywords."""
    text = question + ' ' + answer
    best_match = None
    best_score = 0

    for subcat, keywords in SUBCAT_MAP.items():
        score = sum(2 if kw in question else 1 for kw in keywords if kw in text)
        if score > best_score:
            best_score = score
            best_match = subcat

    if best_match and best_score > 0:
        return best_match

    # Fallback by category
    fallbacks = {
        'java-core': 'Java基础',
        'concurrent': '线程基础',
        'jvm': 'GC算法',
        'framework': 'Spring核心',
        'database': 'MySQL',
        'middleware': '消息队列',
        'distributed': '分布式理论',
    }
    return fallbacks.get(category, 'Java基础')

# ============================================================
# NORMALIZATION FOR DEDUP
# ============================================================

def normalize_question(q):
    """Normalize question text for dedup comparison."""
    # Remove whitespace
    q = re.sub(r'\s+', '', q)
    # Remove common prefixes
    for prefix in ['问：', '答：', '问:', '答:', '面试题：', '面试题:',
                   'Q：', 'Q:', '请问', '简述', '简答', '题目：']:
        if q.startswith(prefix):
            q = q[len(prefix):]
    # Remove punctuation variations
    q = q.replace('？', '?').replace('，', '').replace('。', '')
    q = q.replace('（', '(').replace('）', ')')
    # Remove trailing ?
    q = q.rstrip('?')
    return q.lower()

def questions_are_similar(q1, q2):
    """Check if two questions are similar enough to be duplicates."""
    n1 = normalize_question(q1)
    n2 = normalize_question(q2)

    if n1 == n2:
        return True

    # Check if one contains the other (for truncated versions)
    if len(n1) > 10 and len(n2) > 10:
        if n1 in n2 or n2 in n1:
            return True

    # Check edit distance for short questions
    if len(n1) < 30 and len(n2) < 30:
        # Simple character overlap ratio
        common = sum(1 for c in n1 if c in n2)
        ratio = common / max(len(n1), len(n2))
        if ratio > 0.85:
            return True

    return False

# ============================================================
# QUALITY FILTERS
# ============================================================

def is_high_quality(q):
    """Check if a Q&A pair is high quality enough to include."""
    question = q.get('question', '')
    answer = q.get('answer', '')

    # Minimum lengths
    if len(question) < 5:
        return False
    if len(answer) < 30:
        return False

    # Skip code-only entries
    if answer.count('{') > 5 and answer.count('}') > 5 and len(answer) < 200:
        return False

    # Skip entries that are mostly noise
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', question))
    if chinese_chars < 2 and not re.search(r'[A-Za-z]{3,}', question):
        return False

    # Skip entries with too many special characters (likely parsing errors)
    if question.count('|') > 3 or question.count('#') > 3:
        return False

    # Skip very long questions (likely not real questions)
    if len(question) > 200:
        return False

    return True

def format_answer(answer):
    """Clean up and format the answer text."""
    # Remove excessive blank lines
    answer = re.sub(r'\n{3,}', '\n\n', answer)
    # Trim each line
    lines = [l.strip() for l in answer.split('\n')]
    answer = '\n'.join(lines)
    return answer.strip()

# ============================================================
# MAIN
# ============================================================

def main():
    # Load all raw books
    all_questions = []
    book_files = sorted([f for f in os.listdir(BOOKS_DIR) if f.startswith('raw_book') and f.endswith('.json')])

    print("=" * 60)
    print("MERGE & DEDUP PIPELINE")
    print("=" * 60)

    for bf in book_files:
        path = os.path.join(BOOKS_DIR, bf)
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"  {bf}: {len(data)} questions")
        all_questions.extend(data)

    print(f"\nTotal raw questions: {len(all_questions)}")

    # Filter low quality
    filtered = [q for q in all_questions if is_high_quality(q)]
    print(f"After quality filter: {len(filtered)}")

    # Deduplicate
    # Group by normalized question, keep best answer
    groups = defaultdict(list)
    for q in filtered:
        key = normalize_question(q['question'])
        groups[key].append(q)

    # For each group, pick the entry with the longest answer (most detailed)
    deduped = []
    for key, group in groups.items():
        # Sort by answer length descending
        group.sort(key=lambda x: len(x.get('answer', '')), reverse=True)
        best = group[0].copy()
        best['_dup_count'] = len(group)
        # Merge tags from all duplicates
        all_tags = set()
        for item in group:
            all_tags.update(item.get('_tags', []))
        best['_tags'] = list(all_tags)[:5]
        deduped.append(best)

    print(f"After dedup: {len(deduped)}")

    # Secondary dedup pass: check for similar (not exact) questions
    final = []
    used = set()
    for i, q in enumerate(deduped):
        if i in used:
            continue
        norm = normalize_question(q['question'])
        # Check against already-added questions
        is_dup = False
        for j, fq in enumerate(final):
            if questions_are_similar(q['question'], fq['question']):
                # Keep the one with longer answer
                if len(q.get('answer', '')) > len(fq.get('answer', '')):
                    final[j] = q
                is_dup = True
                used.add(i)
                break
        if not is_dup:
            final.append(q)

    print(f"After similarity dedup: {len(final)}")

    # Format and assign final fields
    category_counters = defaultdict(int)
    for q in final:
        category = q['_category']
        category_counters[category] += 1
        # Assign ID
        cat_prefix = {
            'java-core': 'core',
            'concurrent': 'conc',
            'jvm': 'jvm',
            'framework': 'fw',
            'database': 'db',
            'middleware': 'mw',
            'distributed': 'dist',
        }.get(category, 'misc')
        q['id'] = f"{cat_prefix}-{category_counters[category]:03d}"
        # Assign subcategory
        q['subcategory'] = get_subcategory(q['question'], q['answer'], category)
        # Format answer
        q['answer'] = format_answer(q['answer'])
        # Map fields to final format
        q['difficulty'] = q.pop('_difficulty', 'L2')
        q['tags'] = q.pop('_tags', [])
        q['category'] = category
        # Clean up internal fields
        q.pop('_category', None)
        q.pop('_subcategory', None)
        q.pop('_source', None)
        q.pop('_dup_count', None)
        # Add empty follow_up
        q['follow_up'] = []

    # Sort by category then difficulty
    diff_order = {'L1': 1, 'L2': 2, 'L3': 3, 'L4': 4, 'L5': 5}
    final.sort(key=lambda x: (x['category'], diff_order.get(x['difficulty'], 9), x['id']))

    # Write by category
    category_files = {
        'java-core': 'java-core.json',
        'concurrent': 'concurrent.json',
        'jvm': 'jvm.json',
        'framework': 'framework.json',
        'database': 'database.json',
        'middleware': 'middleware.json',
        'distributed': 'distributed.json',
    }

    print("\n" + "=" * 60)
    print("FINAL OUTPUT")
    print("=" * 60)

    for cat, filename in category_files.items():
        cat_questions = [q for q in final if q['category'] == cat]
        # Ensure proper field order
        formatted = []
        for q in cat_questions:
            formatted.append({
                'id': q['id'],
                'category': q['category'],
                'subcategory': q['subcategory'],
                'difficulty': q['difficulty'],
                'tags': q['tags'],
                'question': q['question'],
                'answer': q['answer'],
                'follow_up': q.get('follow_up', []),
            })

        output_path = os.path.join(OUTPUT_DIR, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(formatted, f, ensure_ascii=False, indent=2)

        # Subcategory distribution
        subcat_counts = defaultdict(int)
        for q in formatted:
            subcat_counts[q['subcategory']] += 1
        top_subcats = sorted(subcat_counts.items(), key=lambda x: -x[1])[:5]

        # Difficulty distribution
        diff_counts = defaultdict(int)
        for q in formatted:
            diff_counts[q['difficulty']] += 1

        print(f"\n  {filename}: {len(formatted)} questions")
        print(f"    Subcategories: {', '.join(f'{s}({c})' for s, c in top_subcats)}")
        print(f"    Difficulty: {dict(diff_counts)}")

    print(f"\n{'='*60}")
    print(f"TOTAL: {len(final)} unique questions across {len(category_files)} categories")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
