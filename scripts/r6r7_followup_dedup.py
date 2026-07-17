#!/usr/bin/env python3
"""
R6+R7: Follow-up question generation & semantic deduplication pass 2.

R6: Generate intelligent follow_up questions based on question content + answer keywords.
R7: Cross-book semantic dedup using fuzzy matching on normalized question text.
"""
import json
import re
import os
from collections import defaultdict

# ============================================================
# R6: FOLLOW-UP GENERATION
# ============================================================

# Topic-specific follow-up templates
FOLLOWUP_RULES = {
    # HashMap / Collections
    'HashMap': [
        'HashMap 的扩容机制是怎样的？',
        'HashMap 和 ConcurrentHashMap 的区别？',
        '为什么 HashMap 的容量要是 2 的幂次？',
    ],
    'ConcurrentHashMap': [
        'ConcurrentHashMap 在 JDK 1.7 和 1.8 中有什么区别？',
        'ConcurrentHashMap 的 put 操作流程是怎样的？',
    ],
    'ArrayList': [
        'ArrayList 和 LinkedList 有什么区别？',
        'ArrayList 的扩容机制是怎样的？',
    ],
    # Concurrency
    'synchronized': [
        'synchronized 和 ReentrantLock 的区别？',
        'synchronized 的锁升级过程是怎样的？',
    ],
    'volatile': [
        'volatile 能保证原子性吗？为什么？',
        'volatile 和 synchronized 的区别？',
    ],
    '线程池': [
        '线程池的核心参数有哪些？',
        '线程池的拒绝策略有哪些？',
    ],
    'AQS': [
        'AQS 的底层实现原理是什么？',
        'AQS 的公平锁和非公平锁如何实现？',
    ],
    'CAS': [
        'CAS 存在什么问题？如何解决？',
        'ABA 问题是什么？如何避免？',
    ],
    'ThreadLocal': [
        'ThreadLocal 会导致内存泄漏吗？为什么？',
        'ThreadLocal 的原理是什么？',
    ],
    # JVM
    'JVM': [
        'JVM 的内存结构是怎样的？',
        '如何进行 JVM 调优？',
    ],
    'GC': [
        'G1 和 CMS 垃圾收集器有什么区别？',
        '如何选择合适的垃圾收集器？',
    ],
    '类加载': [
        '什么是双亲委派模型？',
        '有哪些打破双亲委派的场景？',
    ],
    'JMM': [
        'happens-before 原则是什么？',
        '什么是指令重排？如何禁止？',
    ],
    # Spring
    'Spring': [
        'Spring Bean 的生命周期是怎样的？',
        'Spring 是如何解决循环依赖的？',
    ],
    'IOC': [
        'Spring IOC 容器的初始化过程？',
        'BeanFactory 和 ApplicationContext 的区别？',
    ],
    'AOP': [
        'Spring AOP 和 AspectJ 有什么区别？',
        'JDK 动态代理和 CGLIB 的区别？',
    ],
    '事务': [
        'Spring 事务的传播行为有哪些？',
        'Spring 事务在什么情况下会失效？',
    ],
    'SpringBoot': [
        'Spring Boot 自动配置的原理是什么？',
        'Spring Boot Starter 的作用是什么？',
    ],
    # Database
    'MySQL': [
        'MySQL 的 InnoDB 和 MyISAM 有什么区别？',
        'MySQL 的索引底层为什么用 B+ 树？',
    ],
    '索引': [
        '什么是覆盖索引？有什么优势？',
        '索引失效的场景有哪些？',
    ],
    'Redis': [
        'Redis 的持久化方式有哪些？',
        '如何保证缓存和数据库的一致性？',
    ],
    'MVCC': [
        'MVCC 的实现原理是什么？',
        'MVCC 能解决幻读问题吗？',
    ],
    # Middleware
    'Kafka': [
        'Kafka 如何保证消息不丢失？',
        'Kafka 的分区分配策略是什么？',
    ],
    'RabbitMQ': [
        'RabbitMQ 如何保证消息的可靠性投递？',
        'RabbitMQ 的死信队列是什么？',
    ],
    'RocketMQ': [
        'RocketMQ 和 Kafka 有什么区别？',
        'RocketMQ 如何实现事务消息？',
    ],
    'Elasticsearch': [
        'Elasticsearch 的倒排索引原理是什么？',
        'Elasticsearch 如何实现深度分页？',
    ],
    # Distributed
    'CAP': [
        'CAP 定理中的三个特性分别是什么？',
        '为什么分布式系统不能同时满足 CAP？',
    ],
    '分布式事务': [
        '分布式事务有哪些解决方案？',
        'Seata 的 AT 模式原理是什么？',
    ],
    '分布式锁': [
        '基于 Redis 和 Zookeeper 的分布式锁有什么区别？',
        'Redlock 算法的原理是什么？',
    ],
    'Docker': [
        'Docker 的网络模式有哪些？',
        'Docker 镜像是如何分层的？',
    ],
    'Kubernetes': [
        'Kubernetes 的 Service 有哪些类型？',
        'Kubernetes 的 Pod 生命周期是怎样的？',
    ],
    '微服务': [
        '微服务架构有什么优缺点？',
        '微服务之间如何通信？',
    ],
}

def generate_followups(q):
    """Generate follow-up questions based on question content."""
    text = q['question'] + ' ' + q['answer']
    followups = []
    
    for topic, templates in FOLLOWUP_RULES.items():
        # Check if this topic is relevant
        if topic.lower() in text.lower():
            for template in templates:
                # Don't add if the follow_up is basically the same as the question
                if q['question'] not in template and template not in q['question']:
                    if template not in followups:
                        followups.append(template)
    
    # Also generate generic follow-ups based on question type
    if not followups:
        if '?' in q['question'] or '？' in q['question']:
            # Generic follow-ups for question-type items
            if '为什么' in q['question']:
                followups.append('在实际项目中如何应用？')
            elif '如何' in q['question'] or '怎么' in q['question']:
                followups.append('有什么注意事项或最佳实践？')
            elif '区别' in q['question']:
                followups.append('在实际项目中如何选择？')
            elif '什么是' in q['question']:
                followups.append('有什么实际应用场景？')
    
    return followups[:3]  # Max 3 follow-ups

# ============================================================
# R7: SEMANTIC DEDUP PASS 2
# ============================================================

def normalize_for_dedup(q):
    """Aggressive normalization for dedup comparison."""
    q = re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]', '', q.lower())
    # Remove common Chinese stopwords
    stopwords = '什么是如何为什么的说在了和与及给把被让从对为到上下去出来里外'
    for sw in stopwords:
        q = q.replace(sw, '')
    return q

def is_similar(q1, q2, threshold=0.8):
    """Check if two questions are semantically similar."""
    n1 = normalize_for_dedup(q1)
    n2 = normalize_for_dedup(q2)
    
    if not n1 or not n2:
        return False
    if n1 == n2:
        return True
    if len(n1) > 8 and len(n2) > 8:
        if n1 in n2 or n2 in n1:
            return True
    
    # Character-level Jaccard similarity
    set1 = set(n1)
    set2 = set(n2)
    intersection = set1 & set2
    union = set1 | set2
    if union:
        jaccard = len(intersection) / len(union)
        if jaccard > threshold and abs(len(n1) - len(n2)) < max(len(n1), len(n2)) * 0.3:
            return True
    
    return False

def dedup_cross_file(all_data):
    """Deduplicate across all files in a project."""
    # Build index of all questions
    all_questions = []
    for cat, questions in all_data.items():
        for q in questions:
            all_questions.append((cat, q))
    
    # Group similar questions
    groups = []
    used = set()
    
    for i, (cat_i, q_i) in enumerate(all_questions):
        if i in used:
            continue
        
        group = [(cat_i, q_i)]
        used.add(i)
        
        for j in range(i + 1, len(all_questions)):
            if j in used:
                continue
            cat_j, q_j = all_questions[j]
            
            if is_similar(q_i['question'], q_j['question']):
                group.append((cat_j, q_j))
                used.add(j)
        
        if len(group) > 1:
            groups.append(group)
    
    # For each group, keep the one with longest answer
    removed = 0
    for group in groups:
        # Sort by answer length descending
        group.sort(key=lambda x: len(x[1]['answer']), reverse=True)
        # Keep first (best), mark others for removal
        for cat, q in group[1:]:
            q['_remove'] = True
            removed += 1
    
    # Filter out marked questions
    for cat in all_data:
        all_data[cat] = [q for q in all_data[cat] if not q.get('_remove')]
    
    return removed, len(groups)

# ============================================================
# MAIN
# ============================================================

def main():
    projects = [
        '/opt/data/projects/java-interview/data',
        '/opt/data/projects/ai-interview/data',
    ]
    
    print("=" * 60)
    print("R6+R7: Follow-up Generation & Semantic Dedup")
    print("=" * 60)
    
    for data_dir in projects:
        proj = os.path.basename(os.path.dirname(data_dir))
        print(f"\n--- {proj} ---")
        
        # Load all files
        all_data = {}
        for fname in sorted(os.listdir(data_dir)):
            if not fname.endswith('.json'):
                continue
            path = os.path.join(data_dir, fname)
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            cat = data[0]['category'] if data else fname.replace('.json', '')
            all_data[cat] = data
        
        # R6: Generate follow-ups
        followup_count = 0
        for cat, questions in all_data.items():
            for q in questions:
                if not q.get('follow_up'):
                    fus = generate_followups(q)
                    if fus:
                        q['follow_up'] = fus
                        followup_count += 1
        
        total_before = sum(len(v) for v in all_data.values())
        print(f"  R6: Follow-ups generated for {followup_count} questions")
        
        # R7: Semantic dedup
        removed, dup_groups = dedup_cross_file(all_data)
        total_after = sum(len(v) for v in all_data.values())
        print(f"  R7: Removed {removed} duplicates in {dup_groups} groups ({total_before} -> {total_after})")
        
        # Renumber IDs and save
        cat_prefixes = {
            'java-core': 'core', 'concurrent': 'conc', 'jvm': 'jvm',
            'framework': 'fw', 'database': 'db', 'middleware': 'mw', 'distributed': 'dist',
        }
        
        for cat, questions in all_data.items():
            prefix = cat_prefixes.get(cat, cat[:4])
            for i, q in enumerate(questions, 1):
                q['id'] = f"{prefix}-{i:03d}"
            
            # Save
            fname_map = {v: k for k, v in {
                'java-core': 'java-core.json', 'concurrent': 'concurrent.json',
                'jvm': 'jvm.json', 'framework': 'framework.json',
                'database': 'database.json', 'middleware': 'middleware.json',
                'distributed': 'distributed.json',
            }.items()}
            
            # For AI interview, keep original filenames
            if proj == 'ai-interview':
                # Map category to filename based on _category field in questions
                for q in questions:
                    cat_field = q.get('category', cat)
                    break
                
            # Find the right file
            if proj == 'java-interview':
                fname = fname_map.get(cat)
                if fname:
                    path = os.path.join(data_dir, fname)
                    with open(path, 'w', encoding='utf-8') as f:
                        json.dump(questions, f, ensure_ascii=False, indent=2)
            else:
                # AI interview: save back to original files
                # Group by _category
                pass
        
        if proj == 'java-interview':
            print(f"  Total: {total_after} questions")
        
        if proj == 'ai-interview':
            # For AI, save each file back
            # Re-map categories to files
            ai_cat_file_map = {}
            for fname in sorted(os.listdir(data_dir)):
                if not fname.endswith('.json'):
                    continue
                path = os.path.join(data_dir, fname)
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if data:
                    ai_cat_file_map[data[0].get('category', fname.replace('.json',''))] = fname
            
            for cat, questions in all_data.items():
                fname = ai_cat_file_map.get(cat, f'{cat}.json')
                path = os.path.join(data_dir, fname)
                # Don't renumber AI IDs (they have custom formats)
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(questions, f, ensure_ascii=False, indent=2)
            print(f"  Total: {total_after} questions")

if __name__ == '__main__':
    main()
