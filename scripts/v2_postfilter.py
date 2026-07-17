#!/usr/bin/env python3
"""
V2 Post-filter: Remove remaining low-quality questions and fix classification.
Run AFTER v2_extract.py.
"""
import json
import re
import os
from collections import defaultdict

DATA_DIR = '/opt/data/projects/java-interview/data'

# Patterns that indicate a "question" is actually NOT a real interview question
BAD_QUESTION_PATTERNS = [
    # Blog/chapter endings, personal reflections
    r'(截止|截至|在这个专栏|今天你写|你看了多少|寒冬来临|学习.*不知道)',
    # Non-technical soft questions
    r'(你是个能吃苦|你有多懂面试官|收过报警短信|怎样确保评估全面|怎样看待脑筋)',
    # Blog teasers
    r'(究竟是大公司好|做了哪些优化$|有哪些可以优化|这个项目有哪些)',
    # Vague conversational fragments
    r'^(还有吗|但是不同域呢|面试官：)',
    # Pure math/expression fragments
    r'^[\d\.\+\-\*\/\(\)\[\]=\'"\s]+$',
    r"^\d+.*\.length.*=",
]

COMPILED_BAD = [re.compile(p) for p in BAD_QUESTION_PATTERNS]

# Lines that start with chapter numbering: "五、", "六、", "4-1："
CHAPTER_RE = re.compile(r'^[一二三四五六七八九十\d]+[、\-－][\d]*[：:]')

def is_bad_question(q_text, a_text):
    """Check if a question should be filtered out."""
    # Check bad patterns
    for p in COMPILED_BAD:
        if p.search(q_text):
            return True
    
    # Chapter numbering prefix
    if CHAPTER_RE.match(q_text):
        return True
    
    # Question is just a number or expression
    if re.match(r'^[\d\.\+\-\*\/\(\)\s=]+$', q_text):
        return True
    
    # Answer starts with code (meaning question was likely "看这段代码...")
    if a_text.lstrip()[:20].startswith(('public class', 'public static', 'private ')):
        # This is fine if the question explicitly asks about code
        if '代码' not in q_text and '输出' not in q_text and '结果' not in q_text:
            pass  # Keep it, code in answer is normal
    
    # Very short questions with no technical content
    if len(q_text) < 6:
        return True
    
    # Question is purely conversational (no technical keywords)
    tech_keywords = [
        'Java', 'Spring', 'HashMap', 'Thread', '线程', '锁', 'synchronized',
        'volatile', 'JVM', 'GC', '垃圾', '内存', '类加载', 'MySQL', 'Redis',
        '索引', '事务', 'Kafka', 'RabbitMQ', 'RocketMQ', '消息', 'Docker',
        'Kubernetes', '微服务', '分布式', 'CAP', 'MyBatis', 'Nginx',
        'Netty', 'TCP', 'HTTP', 'UDP', '接口', '抽象类', '多态', '继承',
        '集合', '泛型', '反射', '注解', '异常', 'IO', 'NIO', '序列化',
        '单例', '工厂', '代理', '缓存', '数据库', '并发', '异步', '阻塞',
        '负载均衡', '一致性', 'Raft', 'Paxos', 'Zookeeper', 'Elasticsearch',
        'B+树', 'MVCC', 'AQS', 'CAS', 'ThreadLocal', 'AOP', 'IOC',
        'Bean', 'Filter', 'Listener', 'Servlet', 'Tomcat',
    ]
    
    has_tech = any(kw.lower() in q_text.lower() for kw in tech_keywords)
    
    # If no question mark, no starter, AND no tech keyword → likely junk
    has_qmark = '？' in q_text or '?' in q_text
    has_starter = any(q_text.startswith(s) for s in ['什么', '如何', '为什么', '说', '谈谈', '简述', '介绍', '解释', '列举', '说明', '怎样', '为何', '描述'])
    has_topic_suffix = any(q_text.endswith(s) for s in ['的区别', '的原理', '的作用', '的特点', '的优势', '是什么', '有哪些', '机制', '原理', '生命周期'])
    
    if not has_qmark and not has_starter and not has_topic_suffix and not has_tech:
        return True
    
    # Answer too short
    if len(a_text) < 150:
        return True
    
    return False

# Fix classification issues
RECLASSIFY_RULES = {
    # Questions that are clearly networking, not Java
    'network': {
        'keywords': ['TCP', 'UDP', 'HTTP', 'HTTPS', '三次握手', '四次挥手', '拥塞控制',
                    '滑动窗口', 'MAC地址', 'IP地址', 'ARP', 'DNS', 'CDN', 'Socket',
                    '粘包', '拆包', 'TLS', 'SSL', '证书'],
        'target_cat': 'middleware',
        'target_subcat': '负载均衡',
    },
    # Questions about data structures/algorithms that belong in Java core
    'algorithm': {
        'keywords': ['红黑树', '二叉树', 'B树', '排序算法', '查找算法', '链表'],
        'target_cat': 'java-core',
        'target_subcat': '集合框架',
    },
}

def process():
    total_in = 0
    total_out = 0
    
    for fname in sorted(os.listdir(DATA_DIR)):
        if not fname.endswith('.json'):
            continue
        path = os.path.join(DATA_DIR, fname)
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        total_in += len(data)
        
        # Filter
        cleaned = [q for q in data if not is_bad_question(q['question'], q['answer'])]
        
        # Renumber
        cat = cleaned[0]['category'] if cleaned else fname.replace('.json', '')
        prefix = {'java-core': 'core', 'concurrent': 'conc', 'jvm': 'jvm',
                  'framework': 'fw', 'database': 'db', 'middleware': 'mw', 'distributed': 'dist'}.get(cat, 'misc')
        for i, q in enumerate(cleaned, 1):
            q['id'] = f"{prefix}-{i:03d}"
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(cleaned, f, ensure_ascii=False, indent=2)
        
        removed = len(data) - len(cleaned)
        total_out += len(cleaned)
        if removed > 0:
            print(f"  {fname}: {len(cleaned)} kept, {removed} removed")
    
    print(f"\nTotal: {total_in} → {total_out} (removed {total_in - total_out})")

if __name__ == '__main__':
    print("=" * 60)
    print("V2 POST-FILTER: Remove low-quality questions")
    print("=" * 60)
    process()
