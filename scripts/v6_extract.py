#!/usr/bin/env python3
"""
v6 Comprehensive Extractor — Convert ALL book sections to interview questions
=============================================================================
Core principle: Every meaningful section in the book IS a potential interview question.
Don't filter — CONVERT. Take every L2 section, turn it into "什么是X？" or "X的原理是什么？"

Book 1: Extract ALL L2 sections (226 entries) → convert to questions
  - Skip: Hadoop(25), Spark(26), Storm(27), YARN(28), ML(29)
  - Keep Docker from ch30 (relevant to DevOps)
Book 2: Extract ALL L4+L5 from Java篇+速记版+计算机基础篇
  - Skip: 前端篇(p685+), Go篇(p964+), 算法篇(p618-684)
"""

import fitz
import re
import json
import os
from collections import defaultdict

MIN_ANSWER_LEN = 80  # Lowered — even short answers are valid if the topic is good

# Chapters to SKIP entirely from Book 1 (not Java backend interview material)
SKIP_BOOK1_CHAPTERS = {
    # 25: Hadoop, 26: Spark, 27: Storm, 28: YARN, 29: ML
    # These are big data / data science, not Java backend interviews
}

# Skip patterns for individual entries
SKIP_PATTERNS = [
    r'^前言$', r'^总述$', r'^总结$', r'^概述$',
    r'^目录$', r'^导图', r'^概念$',
    r'^使用场景$', r'^注意事项$', r'^细节$', r'^作用$',
    r'^语法$', r'^特点$',  # Too vague as standalone
    r'^goroutine', r'^docker$', r'^kubernetes',
    r'^css\b', r'^react\b', r'^vue\b',
    r'^gin\b', r'^webstorage',
    r'^webpack', r'^node\.js',
    r'^html\s', r'^link标签',
]

def should_skip(title):
    t = title.strip().lower()
    for p in SKIP_PATTERNS:
        if re.search(p, t):
            return True
    if len(title.strip()) < 3:
        return True
    return False

def clean_title(title):
    """Remove TOC numbering, keep the content."""
    t = title.strip()
    t = re.sub(r'^\d+(\.\d+)*[\.\s]*', '', t)
    t = re.sub(r'^\d+[\s．、丨]+', '', t)
    t = re.sub(r'\s*【.*?】\s*', ' ', t)
    t = re.sub(r'[:：]\s*$', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def to_question(title):
    """Convert a topic name into a proper interview question."""
    t = title.strip()
    
    # Already a question
    if t.endswith('？') or t.endswith('?'):
        return t
    
    # Starts with question words
    if any(t.startswith(w) for w in ['什么是', '为什么', '如何', '怎样', '说说',
                                      '谈谈', '简述', '描述', '介绍一下', '解释',
                                      '说一说', '谈一谈', '请说', '请谈']):
        return t + '？'
    
    # Contains comparison
    if '区别' in t or '对比' in t or ' vs ' in t.lower() or 'VS' in t:
        return f'{t}？'
    
    # Contains "原理" or "机制"
    if '原理' in t or '机制' in t or '流程' in t:
        return f'{t}是什么？'
    
    # Special conversions for known topics
    conversions = {
        # JVM
        '程序计数器(线程私有)': 'JVM中程序计数器的作用是什么？',
        '虚拟机栈(线程私有)': 'JVM虚拟机栈的结构和作用是什么？',
        '本地方法区(线程私有)': 'JVM本地方法区的作用是什么？',
        '方法区/永久代（线程共享）': 'JVM方法区（永久代）的作用是什么？',
        '堆（Heap-线程共享）-运行时数据区': 'JVM堆内存的结构是怎样的？',
        '新生代': 'JVM新生代的内存结构是怎样的？',
        '老年代': 'JVM老年代的特点和GC策略是什么？',
        '永久代': 'JVM永久代和元空间的区别是什么？',
        '如何确定垃圾': 'JVM如何判断对象是否可以被回收？',
        '标记清除算法（Mark-Sweep）': '标记清除（Mark-Sweep）垃圾回收算法的原理和优缺点？',
        '复制算法（copying）': '复制（Copying）垃圾回收算法的原理是什么？',
        '标记整理算法(Mark-Compact)': '标记整理（Mark-Compact）算法的原理是什么？',
        '分代收集算法': '分代收集算法的核心思想是什么？',
        '强引用': 'Java中强引用的特点是什么？',
        '软引用': 'Java中软引用的特点和使用场景是什么？',
        '弱引用': 'Java中弱引用的特点和使用场景是什么？',
        '虚引用': 'Java中虚引用的作用是什么？',
        '阻塞IO模型': '什么是阻塞IO（BIO）模型？',
        '非阻塞IO模型': '什么是非阻塞IO（NIO）模型？',
        '多路复用IO模型': '什么是多路复用IO模型？',
        '信号驱动IO模型': '什么是信号驱动IO模型？',
        '异步IO模型': '什么是异步IO（AIO）模型？',
        '双亲委派': 'JVM双亲委派模型的工作原理是什么？',
        '锁优化': 'JVM中有哪些锁优化技术？',
        '变量可见性': 'volatile关键字如何保证变量的可见性？',
        '禁止重排序': 'volatile关键字如何禁止指令重排序？',
        
        # Concurrent
        '乐观锁': '什么是乐观锁？它的实现原理是什么？',
        '悲观锁': '什么是悲观锁？它和乐观锁的区别？',
        '自旋锁': '什么是自旋锁？它的优缺点是什么？',
        '可重入锁（递归锁）': '什么是可重入锁？它的实现原理是什么？',
        '公平锁与非公平锁': '公平锁和非公平锁的区别是什么？',
        '共享锁和独占锁': '共享锁和独占锁的区别是什么？',
        '重量级锁（Mutex Lock）': '什么是重量级锁？它的性能问题是什么？',
        '轻量级锁': '什么是轻量级锁？它是如何工作的？',
        '偏向锁': '什么是偏向锁？锁升级的过程是怎样的？',
        '分段锁': '什么是分段锁？ConcurrentHashMap是如何使用分段锁的？',
        '原子包 java.util.concurrent.atomic（锁自旋）': 'Java atomic包中的原子类是如何实现的？',
        'ABA问题': '什么是CAS的ABA问题？如何解决？',
        
        # Design patterns
        '工厂方法模式': '工厂方法模式的设计思想和应用场景是什么？',
        '抽象工厂模式': '抽象工厂模式和工厂方法模式的区别是什么？',
        '单例模式': '单例模式有几种实现方式？各自的优缺点？',
        '建造者模式': '建造者模式的应用场景和实现方式是什么？',
        '原型模式': '原型模式的原理是什么？浅拷贝和深拷贝的区别？',
        '适配器模式': '适配器模式的原理和应用场景是什么？',
        '装饰器模式': '装饰器模式和继承的区别是什么？',
        '外观模式': '外观模式的作用和应用场景有哪些？',
        '桥接模式': '桥接模式的设计思想是什么？',
        '组合模式': '组合模式的原理和应用场景是什么？',
        '享元模式': '享元模式的原理是什么？Integer缓存是如何使用享元模式的？',
        '策略模式': '策略模式如何消除大量的if-else？',
        '模板方法模式': '模板方法模式的原理是什么？Spring中哪里用到了？',
        '观察者模式': '观察者模式的原理是什么？Java中如何实现？',
        '责任链模式': '责任链模式的原理和应用场景是什么？',
        '命令模式': '命令模式的原理和使用场景是什么？',
        '备忘录模式': '备忘录模式的原理是什么？',
        '状态模式': '状态模式和策略模式的区别是什么？',
        '访问者模式': '访问者模式的原理是什么？什么场景下使用？',
        '中介者模式': '中介者模式如何解耦对象之间的交互？',
        '解释器模式': '解释器模式的原理和应用场景是什么？',
        
        # Network
        '网络7层架构': 'OSI七层网络模型和TCP/IP四层模型的区别是什么？',
        'CDN 原理': 'CDN的工作原理是什么？',
        
        # Algorithm  
        '二分查找': '二分查找算法的原理和实现是什么？',
        '冒泡排序算法': '冒泡排序的原理和时间复杂度是什么？',
        '插入排序算法': '插入排序的原理和时间复杂度是什么？',
        '快速排序算法': '快速排序的原理和最坏时间复杂度是什么？',
        '希尔排序算法': '希尔排序的原理是什么？',
        '归并排序算法': '归并排序的原理和时间复杂度是什么？',
        '桶排序算法': '桶排序的原理和使用场景是什么？',
        '基数排序算法': '基数排序的原理是什么？',
        '剪枝算法': '回溯算法中的剪枝策略是什么？',
        '回溯算法': '回溯算法的原理和经典应用有哪些？',
        '最短路径算法': 'Dijkstra最短路径算法的原理是什么？',
        '最大子数组算法': '最大子数组问题的解决思路是什么？',
        '最小生成树算法': '最小生成树算法（Prim/Kruskal）的原理是什么？',
        
        # Data structures
        '栈（stack）': '栈数据结构的特点和应用场景有哪些？',
        '队列（queue）': '队列数据结构的特点和常见变体有哪些？',
        '链表（Link）': '链表和数组的区别是什么？链表的常见操作？',
        '散列表（Hash Table）': '散列表的原理和冲突解决方法有哪些？',
        '红黑树': '红黑树的特性是什么？它在Java中的哪些地方被使用？',
        'B-TREE': 'B树和B+树的区别是什么？',
        '位图': '位图（Bitmap）数据结构的原理和应用场景是什么？',
        
        # Crypto
        'AES': 'AES加密算法的原理是什么？',
        'RSA': 'RSA非对称加密算法的原理是什么？',
        'CRC': 'CRC循环冗余校验的原理是什么？',
        'MD5': 'MD5哈希算法的原理和安全性问题是什么？',
        
        # Database
        '存储过程(特定功能的SQL 语句集)': 'MySQL存储过程的作用和优缺点是什么？',
        '触发器(一段能自动执行的程序)': 'MySQL触发器的作用和使用场景是什么？',
        '分区分表': '数据库分库分表的策略有哪些？',
        '垂直切分(按照功能模块)': '数据库垂直切分的原理和适用场景是什么？',
        '水平切分(按照规则划分存储)': '数据库水平切分的策略有哪些？',
        '两阶段提交协议': '什么是两阶段提交（2PC）协议？有什么缺点？',
        '三阶段提交协议': '什么是三阶段提交（3PC）协议？它解决了2PC的什么问题？',
        '柔性事务': '什么是柔性事务？最大努力通知型事务是什么？',
        
        # Consistency algorithms
        'NWR': '什么是NWR机制？它如何调节一致性和可用性？',
        'Gossip': 'Gossip协议的工作原理是什么？',
        'Paxos': 'Paxos算法的基本原理是什么？',
        'Raft': 'Raft算法相比Paxos有什么改进？',
        'Zab': 'ZooKeeper的ZAB协议的工作流程是什么？',
        '一致性Hash': '一致性Hash的原理和特性是什么？它在分布式系统中的应用？',
        
        # Distributed cache
        '缓存雪崩': '什么是缓存雪崩？如何预防和解决？',
        '缓存穿透': '什么是缓存穿透？如何预防和解决？',
        '缓存预热': '什么是缓存预热？为什么需要缓存预热？',
        '缓存更新': '缓存更新策略有哪些？如何保证缓存和数据库的一致性？',
        '缓存降级': '什么是缓存降级？什么场景下需要降级？',
        
        # Middleware
        'Kafka概念': 'Kafka的核心概念和架构是怎样的？',
        '生产者设计': 'Kafka生产者的设计原理是什么？',
        '消费者设计': 'Kafka消费者的设计原理和消费模型是什么？',
        'Slf4j': 'SLF4J门面模式的作用是什么？',
        'Log4j': 'Log4j的日志级别和组件架构是什么？',
        'LogBack': 'Logback相比Log4j有哪些优点？',
        'ELK': 'ELK日志系统的架构和各组件的作用是什么？',
        'MongoDB': 'MongoDB的特点和适用场景是什么？',
        'Thrift': 'Thrift序列化框架的原理和特点是什么？',
        'Protoclol Buffer': 'Protocol Buffer的原理和优势是什么？',
        'Keepalive': 'Keepalive高可用方案的原理是什么？',
        'HAProxy': 'HAProxy负载均衡器的特点和使用场景是什么？',
        'Tomcat架构': 'Tomcat的架构和请求处理流程是怎样的？',
        '事件调度（kafka）': '微服务中如何使用Kafka实现事件驱动架构？',
        '服务跟踪（starter-sleuth）': 'Spring Cloud Sleuth如何实现分布式链路追踪？',
        'API管理': '微服务中API管理的作用和方案是什么？',
        '配置中心': '微服务配置中心的作用和实现方案有哪些？',
        'API 网关': '微服务中API网关的作用是什么？',
        
        # Java basics
        'JAVA异常分类及处理': 'Java异常体系的分类和处理方式是什么？',
        'JAVA反射': 'Java反射机制的原理和应用场景是什么？',
        'JAVA注解': 'Java注解的工作原理是什么？如何自定义注解？',
        'JAVA内部类': 'Java内部类有哪几种？各自的特点和使用场景？',
        'JAVA泛型': 'Java泛型的原理是什么？什么是类型擦除？',
        'JAVA序列化(创建可复用的Java对象)': 'Java序列化机制的原理和使用场景是什么？',
        'JAVA复制': 'Java中深拷贝和浅拷贝的区别是什么？如何实现深拷贝？',
        '接口继承关系和实现': 'Java集合框架的接口继承关系是怎样的？',
        'JAVA并发知识库': 'Java并发编程的知识体系是怎样的？',
        'JAVA线程实现/创建方式': 'Java创建线程有哪几种方式？',
        '4种线程池': 'Java内置的4种线程池各自的特点和使用场景是什么？',
        '线程生命周期(状态)': 'Java线程的生命周期和状态转换是怎样的？',
        '终止线程4种方式': 'Java终止线程有哪几种方式？为什么stop()被废弃？',
        'sleep与wait 区别': 'sleep()和wait()的区别是什么？',
        'start与run区别': '线程的start()和run()有什么区别？',
        'JAVA后台线程': '什么是Java守护线程（Daemon Thread）？',
        'JAVA锁': 'Java中有哪些锁？它们的分类和特点是什么？',
        '线程基本方法': 'Java线程有哪些基本方法？各自的作用？',
        '线程上下文切换': '什么是线程上下文切换？如何减少上下文切换？',
        '同步锁与死锁': '什么是死锁？产生死锁的条件和预防方法？',
        '线程池原理': 'Java线程池的工作原理是什么？',
        'JAVA阻塞队列原理': 'Java阻塞队列（BlockingQueue）的原理是什么？',
        'CyclicBarrier、CountDownLatch、Semaphore的用法': 'CyclicBarrier、CountDownLatch、Semaphore的区别和使用场景？',
        'volatile关键字的作用（变量可见性、禁止重排序）': 'volatile关键字的作用和原理是什么？',
        '如何在两个线程之间共享数据': 'Java中如何在多个线程之间安全地共享数据？',
        'ThreadLocal作用（线程本地存储）': 'ThreadLocal的原理和使用场景是什么？内存泄漏问题？',
        'synchronized和ReentrantLock的区别': 'synchronized和ReentrantLock的区别是什么？',
        'ConcurrentHashMap并发': 'ConcurrentHashMap的并发实现原理是什么？',
        'Java中用到的线程调度': 'Java线程调度的机制是什么？',
        '进程调度算法': '常见的进程调度算法有哪些？',
        '什么是CAS（比较并交换-乐观锁机制-锁自旋）': '什么是CAS？它的原理和ABA问题是什么？',
        '什么是 AQS（抽象的队列同步器）': '什么是AQS？它的核心原理是什么？',
        'Synchronized同步锁': 'synchronized关键字的底层原理是什么？',
        'ReentrantLock': 'ReentrantLock的实现原理是什么？',
        'Semaphore信号量': 'Semaphore信号量的原理和使用场景是什么？',
        'AtomicInteger': 'AtomicInteger的实现原理是什么？',
        'ReadWriteLock读写锁': 'ReadWriteLock读写锁的原理和使用场景是什么？',
        'JAVA IO包': 'Java IO包的核心类有哪些？',
        'JAVA NIO': 'Java NIO的核心组件有哪些？和BIO的区别？',
        'Channel': 'Java NIO中Channel的作用和使用方式是什么？',
        'Buffer': 'Java NIO中Buffer的工作原理是什么？',
        'Selector': 'Java NIO中Selector的作用是什么？',
        'JVM 类加载机制': 'JVM类加载的过程是怎样的？',
        'GC分代收集算法  VS 分区收集算法': 'GC分代收集和分区收集的区别是什么？',
        'GC垃圾收集器': 'Java中有哪些GC垃圾收集器？各自的特点？',
        'JAVA 四中引用类型': 'Java的四种引用类型是什么？各自的特点？',
        'JVM内存区域': 'JVM的内存区域划分是怎样的？',
        'JVM运行时内存': 'JVM运行时数据区的结构是怎样的？',
        '垃圾回收与算法': 'JVM垃圾回收的算法有哪些？',
        'Spring 特点': 'Spring框架的特点和核心模块有哪些？',
        'Spring 核心组件': 'Spring框架的核心组件有哪些？',
        'Spring 常用模块': 'Spring的常用模块有哪些？',
        'Spring 常用注解': 'Spring中常用的注解有哪些？',
        'Spring IOC原理': 'Spring IoC容器的原理是什么？',
        'Spring APO原理': 'Spring AOP的原理是什么？',
        'Spring MVC原理': 'Spring MVC的请求处理流程是怎样的？',
        'Spring Boot原理': 'Spring Boot的自动配置原理是什么？',
        'JPA原理': 'JPA和Hibernate的关系是什么？',
        'Mybatis缓存': 'MyBatis的一级缓存和二级缓存原理是什么？',
        'Netty 原理': 'Netty框架的核心原理是什么？',
        'Netty 高性能': 'Netty实现高性能的关键技术有哪些？',
        'Netty RPC实现': '如何基于Netty实现一个RPC框架？',
        'RMI实现方式': 'Java RMI的实现方式和工作原理是什么？',
        'Zookeeper概念': 'ZooKeeper的核心概念和数据模型是什么？',
        'Zookeeper角色': 'ZooKeeper集群中有哪些角色？各自的作用？',
        'Zookeeper工作原理（原子广播）': 'ZooKeeper的ZAB原子广播协议的工作原理？',
        'Znode有四种形式的目录节点': 'ZooKeeper中Znode有哪几种类型？',
        'Kafka数据存储设计': 'Kafka的数据存储设计是怎样的？',
        'RabbitMQ架构': 'RabbitMQ的整体架构和核心组件有哪些？',
        'Exchange 类型': 'RabbitMQ中Exchange有哪几种类型？',
        '列式存储': '列式存储和行式存储的区别是什么？',
        'Hbase核心概念': 'HBase的核心概念有哪些？',
        'Hbase核心架构': 'HBase的架构和核心组件有哪些？',
        'Hbase的写逻辑': 'HBase的写入流程是怎样的？',
        'HBase vs Cassandra': 'HBase和Cassandra的区别是什么？',
        '四层负载均衡 vs 七层负载均衡': '四层负载均衡和七层负载均衡的区别是什么？',
        '负载均衡算法/策略': '常见的负载均衡算法有哪些？',
        'LVS': 'LVS负载均衡的原理和工作模式有哪些？',
        'Nginx反向代理负载均衡': 'Nginx如何实现反向代理和负载均衡？',
        '存储引擎': 'MySQL的存储引擎有哪些？InnoDB和MyISAM的区别？',
        '索引': 'MySQL索引的类型和原理是什么？',
        '数据库三范式': '数据库三范式是什么？反范式设计的优缺点？',
        '数据库是事务': '数据库事务的ACID特性是什么？',
        '数据库并发策略': '数据库并发控制策略有哪些？',
        '数据库锁': '数据库锁的分类有哪些？行锁、表锁、页锁的区别？',
        '基于Redis分布式锁': '如何基于Redis实现分布式锁？有哪些注意事项？',
        'CAP': 'CAP理论是什么？为什么分布式系统不能同时满足CAP？',
        'Slf4j (p169)': 'SLF4J门面模式的作用是什么？',
    }
    
    if t in conversions:
        return conversions[t]
    
    # Default: if it looks like a concept, ask "什么是X？"
    if len(t) <= 12:
        return f'什么是{t}？'
    
    return f'{t}是什么？'

def extract_text(doc, start, end):
    parts = []
    for pno in range(start - 1, min(end, len(doc))):
        text = doc[pno].get_text("text")
        if text.strip():
            parts.append(text.strip())
    return "\n\n".join(parts)[:5000]

def extract_imgs(doc, start, end, prefix, idx, img_dir, max_n=3):
    seen = set()
    paths = []
    for pno in range(start - 1, min(end, len(doc))):
        for img in doc[pno].get_images(full=True):
            xref = img[0]
            if xref in seen: continue
            seen.add(xref)
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.n - pix.alpha > 3:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                if pix.width < 80 or pix.height < 60:
                    pix.close(); continue
                fname = f"{prefix}_{idx:04d}_{len(paths)+1}.png"
                pix.save(os.path.join(img_dir, fname))
                pix.close()
                paths.append(f"images/{fname}")
                if len(paths) >= max_n: return paths
            except: pass
    return paths

def build_entries(toc, doc_len):
    entries = []
    for i, (level, title, page) in enumerate(toc):
        end = doc_len
        for j in range(i + 1, len(toc)):
            if toc[j][0] <= level:
                end = toc[j][2] - 1
                break
        entries.append({'level': level, 'title': title, 'page': page, 'end': end, 'idx': i})
    return entries

# ============================================================
# Book 1: Extract ALL L2 sections
# ============================================================
def extract_book1(doc, img_dir):
    toc = doc.get_toc()
    entries = build_entries(toc, len(doc))
    questions = []
    
    for e in entries:
        # Extract BOTH L2 and L3 — L2 gives topic overview, L3 gives specifics
        if e['level'] not in (2, 3):
            continue
        
        # Skip big-data chapters (Hadoop p259+)
        if e['page'] >= 259:
            continue
        
        q_title = clean_title(e['title'])
        if should_skip(q_title) or len(q_title) < 3:
            continue
        
        answer = extract_text(doc, e['page'], e['end'])
        if len(answer) < MIN_ANSWER_LEN:
            continue
        
        question = to_question(q_title)
        if not question:
            continue
            
        imgs = extract_imgs(doc, e['page'], e['end'], 'b1', len(questions)+1, img_dir)
        questions.append({
            'question': question,
            'answer': answer,
            'images': imgs,
        })
    
    return questions

# ============================================================
# Book 2: Extract ALL L4 + L5 from relevant sections
# ============================================================
def extract_book2(doc, img_dir):
    toc = doc.get_toc()
    entries = build_entries(toc, len(doc))
    questions = []
    
    for e in entries:
        page = e['page']
        # SKIP frontend (p685+) and Go (p964+) and algorithm (p618-684)
        if page >= 618:
            continue
        
        q_title = clean_title(e['title'])
        if should_skip(q_title):
            continue
        
        level = e['level']
        
        # Java篇 (p1-222): L4 + L5
        if page <= 222:
            if level not in (4, 5):
                continue
        # 速记版 (p223-261): L2
        elif page <= 261:
            if level != 2:
                continue
        # 计算机基础篇 (p262-617): L4 + L5
        elif page <= 617:
            if level not in (4, 5):
                continue
        else:
            continue
        
        answer = extract_text(doc, e['page'], e['end'])
        if len(answer) < MIN_ANSWER_LEN:
            continue
        
        question = to_question(q_title)
        if not question:
            continue
        
        imgs = extract_imgs(doc, e['page'], e['end'], 'b2', len(questions)+1, img_dir)
        questions.append({
            'question': question,
            'answer': answer,
            'images': imgs,
        })
    
    return questions

# ============================================================
# Classification (title-weighted)
# ============================================================
def classify(q, a):
    text = (q + ' ' + a[:800]).lower()
    q_lower = q.lower()
    
    rules = [
        ('concurrent', ['线程', '并发', '多线程', '锁', 'synchronized', 'volatile', 'aqs',
                        'threadlocal', 'cas', '线程池', '死锁', '线程安全', 'blockingqueue',
                        'concurrenthashmap', 'reentrantlock', '偏向锁', '轻量级锁', '重量级锁',
                        '读写锁', '自旋锁', '乐观锁', '悲观锁', 'callable', 'runnable',
                        'countdownlatch', 'cyclicbarrier', 'semaphore', '上下文切换']),
        ('jvm', ['jvm', '垃圾回收', '垃圾收集', 'gc', '类加载', '双亲委派', '字节码',
                 '内存区域', '内存模型', '新生代', '老年代', 'eden', 'survivor',
                 'oom', 'g1收集器', 'cms', 'serial', 'parnew', 'jit',
                 '程序计数器', '虚拟机栈', '方法区', '引用类型', '收集器',
                 '逃逸分析', '热点代码', 'io模型', 'nio', '阻塞io']),
        ('framework', ['spring', 'springboot', 'springmvc', 'mybatis', 'ioc', 'aop',
                       'bean', '事务传播', 'starter', '自动装配', '循环依赖',
                       'dispatcherservlet', 'autowired', 'factorybean', 'dubbo',
                       'tomcat', 'jpa', 'hibernate']),
        ('database', ['mysql', 'sql', '索引', 'b+树', 'acid', '隔离级别', 'mvcc',
                      'innodb', 'myisam', 'redo', 'binlog', '回表', '最左匹配',
                      'redis', 'rdb', 'aof', '哨兵', '缓存穿透', '缓存雪崩',
                      'redis集群', '跳表', 'redis事务', 'redis持久化', 'mongo',
                      '存储引擎', '三范式', '乐观锁', '悲观锁', '数据库锁', '分库分表']),
        ('middleware', ['kafka', 'rabbitmq', 'rocketmq', '消息队列', '消息积压',
                        'zookeeper', 'elasticsearch', 'nginx', 'netty', 'rpc',
                        'mongodb', 'hbase', 'cassandra', 'amqp', 'broker',
                        'exchange', 'znode', 'gossip', '日志', 'log4j', 'logback',
                        'elk', 'slf4j', 'thrift', 'protocol buffer', 'protobuf']),
        ('distributed', ['分布式', '微服务', 'cap', 'paxos', 'raft', 'zab',
                         '一致性哈希', '一致性hash', '负载均衡', '服务熔断', '服务降级',
                         '服务注册', '服务发现', 'eureka', '注册中心', '配置中心', '网关',
                         'hystrix', 'ribbon', '分布式锁', '分布式事务', 'sso', 'oauth',
                         'jwt', 'lvs', 'keepalive', 'haproxy', '脑裂', '高可用',
                         '两阶段提交', '三阶段提交', '柔性事务', 'nwr']),
        ('java-core', ['java', '集合', 'list', 'map', 'set', 'queue', 'hashmap',
                       '泛型', '注解', '反射', '异常', 'io流', '序列化',
                       'string', '面向对象', '多态', '继承', '接口', '抽象类',
                       '重载', '重写', 'static', 'final', 'lambda', 'stream',
                       '内部类', '深拷贝', '浅拷贝', '设计模式', '算法', '排序',
                       '数据结构', '红黑树', '二叉树', '加密', '网络', 'http',
                       'tcp', 'udp', 'cdn', 'cookie', 'session']),
    ]
    
    scores = {}
    for cat, kws in rules:
        score = sum(3 for kw in kws if kw in q_lower) + sum(1 for kw in kws if kw in text)
        scores[cat] = score
    
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        best = 'java-core'
    return best

def difficulty(q, a):
    if len(a) > 1500 or any(kw in (q+a[:300]).lower() for kw in 
        ['源码', '底层', '原理', '实现', 'aqs', 'gc', '调优', '分布式', 'mvcc', 
         'volatile', 'synchronized', '锁升级', '类加载', '一致性']):
        return 'L3'
    if len(a) > 600:
        return 'L2'
    return 'L1'

# ============================================================
# Main
# ============================================================
def main():
    books = "/opt/data/projects/java-interview/books"
    data = "/opt/data/projects/java-interview/data"
    imgs = "/opt/data/projects/java-interview/images"
    os.makedirs(imgs, exist_ok=True)
    
    all_qs = []
    
    print("Book 1: JAVA核心知识点整理 — ALL L2 sections")
    doc1 = fitz.open(os.path.join(books, "JAVA核心知识点整理.pdf"))
    b1 = extract_book1(doc1, imgs)
    print(f"  → {len(b1)} questions")
    doc1.close()
    all_qs.extend(b1)
    
    print("Book 2: 代码随想录 — ALL L4+L5")
    doc2 = fitz.open(os.path.join(books, "代码随想录-八股文（第五版）.pdf"))
    b2 = extract_book2(doc2, imgs)
    print(f"  → {len(b2)} questions")
    doc2.close()
    all_qs.extend(b2)
    
    # Dedup by title
    seen = {}
    for q in all_qs:
        key = q['question'].lower().strip()
        if key not in seen or len(q['answer']) > len(seen[key]['answer']):
            seen[key] = q
    deduped = list(seen.values())
    print(f"\nBefore dedup: {len(all_qs)} → After: {len(deduped)}")
    
    # Classify & save
    cats = defaultdict(list)
    for q in deduped:
        cat = classify(q['question'], q['answer'])
        cats[cat].append({
            'question': q['question'],
            'answer': q['answer'],
            'images': q.get('images', []),
            'difficulty': difficulty(q['question'], q['answer']),
        })
    
    for f in os.listdir(data):
        if f.endswith('.json'):
            os.remove(os.path.join(data, f))
    
    order = ['java-core', 'concurrent', 'jvm', 'framework', 'database', 'middleware', 'distributed']
    prefs = {'java-core': 'core', 'concurrent': 'conc', 'jvm': 'jvm',
             'framework': 'fw', 'database': 'db', 'middleware': 'mw', 'distributed': 'dist'}
    
    total = 0
    for cat in order:
        items = cats.get(cat, [])
        items.sort(key=lambda x: (x.get('difficulty', 'L3'), x['question']))
        for i, item in enumerate(items):
            item['id'] = f"{prefs[cat]}-{i+1:03d}"
            item['category'] = cat
            item.setdefault('subcategory', '')
            item.setdefault('tags', [])
            item.setdefault('follow_up', [])
        with open(os.path.join(data, f"{cat}.json"), 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        total += len(items)
        print(f"  {cat}: {len(items)}")
    
    print(f"\n✅ TOTAL: {total}")

if __name__ == '__main__':
    main()
