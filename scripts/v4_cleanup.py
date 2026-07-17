#!/usr/bin/env python3
"""
v4 Cleanup: Final polish — fix titles, remove fragments, fix categories
"""

import json, os, re
from collections import defaultdict

DATA_DIR = "/opt/data/projects/java-interview/data"

# ============================================================
# 1. Title fixes: convert topic names → questions
# ============================================================
TITLE_OVERRIDES = {
    # Fix broken titles
    '、轻量级锁': '什么是轻量级锁？它的升级过程是什么？',
    '、对象头': '什么是Java对象头？它包含哪些信息？',
    '、作用': '',  # Remove - too vague
    '4种线程池': 'Java有哪4种内置线程池？各自的使用场景是什么？',
    'prototyoe': 'Spring Bean的prototype作用域是什么？',
    # Convert short topics to questions
    'CAP': '什么是CAP理论？为什么分布式系统不能同时满足三个？',
    'DNS': 'DNS是什么？它的查询过程是怎样的？',
    'HTTPS': 'HTTPS的工作原理是什么？',
    'LVS': '什么是LVS？它的工作模式有哪些？',
    'ELK': '什么是ELK技术栈？它的应用场景有哪些？',
    'ELK架构': '什么是ELK架构？它的核心组件有哪些？',
    'Throwable': 'Java中Throwable体系是怎样的？Error和Exception的区别？',
    'Set': 'Java中Set接口有哪些实现类？它们的区别是什么？',
    'IP基础': 'IP协议的基础知识有哪些？',
    '缓存穿透': '什么是缓存穿透？如何解决？',
    '缓存雪崩': '什么是缓存雪崩？如何解决？',
    '缓存击穿': '什么是缓存击穿？如何解决？',
    '内存中对象': 'Java对象在内存中是如何布局的？',
    '对象构造': 'Java中对象构造的过程是怎样的？',
    '抓抛模型': 'Java异常处理的抓抛模型是什么？',
    '热点代码': '什么是JVM热点代码？热点探测是如何工作的？',
    '共享数据区': 'JVM运行时数据区中哪些区域是线程共享的？',
    '初始化': 'JVM类加载的初始化阶段做了什么？',
    '互斥与同步': '进程同步和互斥的区别是什么？',
    '存储引擎': 'MySQL有哪些存储引擎？InnoDB和MyISAM的区别？',
    '执行引擎': 'MySQL的执行引擎有哪些？',
    'API管理': '微服务中API网关的作用是什么？',
    '柔性事务': '什么是柔性事务？它与刚性事务的区别？',
    '字符编码': '常见的字符编码有哪些？Unicode和UTF-8的关系？',
    '设计原则': '面向对象设计的基本原则（SOLID）有哪些？',
    '单例模式': '什么是单例模式？有哪些实现方式？',
    '观察者模式': '什么是观察者模式？它的应用场景有哪些？',
    '代理模式': '什么是代理模式？静态代理和动态代理的区别？',
    '备忘录模式': '什么是备忘录模式？它的应用场景有哪些？',
    '消费者设计': 'Kafka消费者是如何设计的？',
    '生产者设计': 'Kafka生产者是如何设计的？',
    '存储系统': '分布式存储系统的核心架构是什么？',
    '马尔可夫': '什么是马尔可夫链？它在计算机科学中的应用？',
    '集群架构': 'Redis集群的架构是怎样的？',
}

# Fix known typos
TYPO_FIXES = {
    'prototyoe': 'prototype',
    'Hashtabe': 'Hashtable',
    'ServivorFrom': 'SurvivorFrom',
    'ServivorTo': 'SurvivorTo',
    'ServicorFrom': 'SurvivorFrom',
}

def fix_title(title):
    """Apply all title fixes."""
    t = title.strip()
    
    # Remove leading special characters
    t = re.sub(r'^[、，,。\.]+', '', t).strip()
    
    # Apply typo fixes
    for wrong, right in TYPO_FIXES.items():
        t = t.replace(wrong, right)
    
    # Apply overrides
    if t in TITLE_OVERRIDES:
        override = TITLE_OVERRIDES[t]
        if override == '':
            return None  # Signal to remove
        return override
    
    # Remove trailing colons
    t = re.sub(r'[:：]\s*$', '', t)
    
    # If already has question mark, keep
    if t.endswith('？') or t.endswith('?'):
        return t
    
    # If starts with question words
    if any(t.startswith(w) for w in ['什么是', '为什么', '如何', '怎样', '说说', '谈谈', 
                                      '简述', '描述', '请说', '请谈', '介绍一下', '解释',
                                      '说一说', '谈一谈']):
        return t + '？'
    
    # If has "区别" or "对比"
    if '区别' in t or '对比' in t:
        return t + '有什么区别？' if not t.endswith('区别') else t + '是什么？'
    
    # If it's a very short concept (< 8 chars), add "什么是...？"
    if len(t) <= 10 and not any(w in t for w in '的是如何为什么过程原理'):
        return f'什么是{t}？'
    
    # Default
    return t + '？' if not t.endswith('。') else t

# ============================================================
# 2. Remove clearly bad questions
# ============================================================
REMOVE_QUESTIONS = {
    '、作用', '导图前言', '前言', '总述', 'Collection接口',
    'List接口', 'Set接口', 'Queue接口', 'Map接口',
    '前言', '使用场景', '注意事项', '概述', '总结',
    'NodeManager', 'YARN运行流程',  # Hadoop
    'Storm Streaming Grouping',  # Storm
    'RMI实现方式',  # Too vague
    '马尔可夫',  # Not Java
}

# ============================================================
# Main
# ============================================================
def main():
    all_items = []
    for fname in os.listdir(DATA_DIR):
        if not fname.endswith('.json'): continue
        with open(os.path.join(DATA_DIR, fname)) as f:
            items = json.load(f)
        all_items.extend(items)
    
    print(f"Loaded: {len(all_items)}")
    
    # Fix titles and remove bad ones
    cleaned = []
    removed = 0
    for item in all_items:
        q = item['question'].strip()
        
        if q in REMOVE_QUESTIONS:
            removed += 1
            continue
        
        new_title = fix_title(q)
        if new_title is None:
            removed += 1
            continue
        
        item['question'] = new_title
        cleaned.append(item)
    
    print(f"Removed: {removed}")
    print(f"Cleaned: {len(cleaned)}")
    
    # Re-sort and re-number within each category
    categories = defaultdict(list)
    for item in cleaned:
        categories[item['category']].append(item)
    
    prefixes = {'java-core': 'core', 'concurrent': 'conc', 'jvm': 'jvm', 
                'framework': 'fw', 'database': 'db', 'middleware': 'mw', 'distributed': 'dist'}
    
    total = 0
    for cat in ['java-core', 'concurrent', 'jvm', 'framework', 'database', 'middleware', 'distributed']:
        items = categories.get(cat, [])
        items.sort(key=lambda x: (x.get('difficulty', 'L3'), x['question']))
        
        for i, item in enumerate(items):
            item['id'] = f"{prefixes[cat]}-{i+1:03d}"
            item['category'] = cat
        
        with open(os.path.join(DATA_DIR, f"{cat}.json"), 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        
        total += len(items)
        print(f"  {cat}.json: {len(items)}")
    
    print(f"\n✅ TOTAL: {total}")

if __name__ == '__main__':
    main()
