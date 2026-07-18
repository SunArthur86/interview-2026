---
id: conc-122
difficulty: L3
category: concurrent
feynman:
  essence: 专为多线程设计的安全集合，使用细粒度锁或无锁算法提升性能。
  analogy: 多窗口同时服务（并发容器）vs 单窗口排队（同步容器）。
  first_principle: 如何在多线程环境下安全高效地操作集合数据？
  key_points:
  - ConcurrentHashMap使用分段锁或CAS+Sync
  - CopyOnWriteArrayList适合读多写少，写时复制
  - 阻塞队列（BlockingQueue）用于线程池任务传递
  - 相比synchronized集合，并发容器迭代器弱一致且不抛异常
memory_points:
- 并发容器对比同步容器：细粒度锁或CAS替代整表锁，迭代具备弱一致性防报错
- ConcurrentHashMap：JDK 8抛弃Segment改用 Node数组+链表+红黑树
- CHM加锁本质：JDK 7分段锁，JDK 8细化为 CAS + synchronized锁头节点
- 典型场景：CopyOnWrite适合读多写少，阻塞队列常配合线程池消费
---

# 什么是并发容器？Java 有哪些并发容器？

并发容器是 `java.util.concurrent` 包中提供的、专门为多线程高并发场景设计的线程安全集合。它们相比于使用 `synchronized` 包装的早期「同步容器」（如 Vector、Hashtable），在并发性能和扩展性上有极大提升。

**核心原理差异：**
- **同步容器**：使用 `synchronized` 方法保证线程安全，锁粒度大（通常是锁住整个容器对象），导致在高并发下吞吐量低，且迭代器可能抛出 `ConcurrentModificationException`（Fail-Fast）。
- **并发容器**：采用更细粒度的锁（分段锁）、CAS（Compare-And-Swap）操作、或者写时复制（Copy-On-Write）策略，允许并发读写，迭代器通常具有弱一致性（Weakly Consistent），不会抛出 `ConcurrentModificationException`。

**主要并发容器分类：**

**1. List 接口**
- **CopyOnWriteArrayList**：
  - **原理**：写时复制。当执行修改操作（add, set, remove）时，会先复制一份底层数组，在新数组上进行修改，修改完成后将引用指向新数组。
  - **适用场景**：读多写少。因为写操作开销大（复制数组），读操作无锁，性能极高。

**2. Map 接口**
- **ConcurrentHashMap**：
  - **JDK 1.7**：分段锁。将数据分为多个 Segment（默认 16 个），每个 Segment 继承自 ReentrantLock，并发度等于 Segment 数量。
  - **JDK 1.8**：抛弃 Segment，采用 **Node 数组 + 链表 + 红黑树** 结构。使用 `CAS + synchronized` 锁数组节点，锁粒度更细（只锁住链表/红黑树的头节点），并发度更高。
  - **不允许 null 键/值**（与 HashMap 不同）。
- **ConcurrentSkipListMap**：
  - **原理**：基于跳表的有序 Map。利用跳表的多层索引结构实现快速查找（O(log N)），通过 CAS 和 volatile 保证并发安全。
  - **适用场景**：需要高并发且需要保持 Key 有序的场景。

**3. Set 接口**
- **CopyOnWriteArraySet**：基于 CopyOnWriteArrayList 实现，去重逻辑依赖于 add 时检查已存在元素。
- **ConcurrentSkipListSet**：基于 ConcurrentSkipListMap 实现，支持自然排序。

**4. Queue 接口（非阻塞队列）**
- **ConcurrentLinkedQueue**：
  - **原理**：基于链表的无界非阻塞队列，使用 CAS + Volatile 实现无锁并发。
  - **适用场景**：高并发场景下的生产消费模型，不阻塞线程。
- **ConcurrentLinkedDeque**：双向链表版本。

**5. BlockingQueue 接口（阻塞队列，常用于线程池）**
- **ArrayBlockingQueue**：基于数组的有界阻塞队列，必须指定容量，FIFO。
- **LinkedBlockingQueue**：基于链表的可选有界阻塞队列（默认 Integer.MAX_VALUE），吞吐量通常高于 ArrayBlockingQueue。
- **SynchronousQueue**：不存储元素的阻塞队列，每一个 put 必须等待一个 take，反之亦然。`Executors.newCachedThreadPool` 使用此队列。
- **PriorityBlockingQueue**：无界优先级阻塞队列，支持自然排序或比较器排序。
- **DelayQueue**：无界阻塞队列，只有当元素的延时时间到了才能从中取出。常用于定时任务。

## 常见考点
1. **ConcurrentHashMap JDK 7 vs 8 的区别**：7 是分段锁（Segment），8 是 CAS + synchronized 锁头节点。为什么 JDK 8 要摒弃 Segment？因为内存占用过大（Segment 继承 ReentrantLock，即使不竞争也占用对象头），且并发度受限于 Segment 数量。
2. **CopyOnWriteArrayList 的迭代器为什么不抛出 ConcurrentModificationException**：因为迭代器操作的是创建迭代器时刻的那个“快照”数组，即使原数组被修改，迭代器引用的旧数组不变，这就是弱一致性。
3. **ConcurrentHashMap 的 size() 方法如何实现**：JDK 7 是累加所有 Segment 的 size；JDK 8 使用 `baseCount` 和 `CounterCell` 数组，利用 CAS 累加，类似于 LongAdder 的实现，避免了热点竞争。


## 记忆要点

- 并发容器对比同步容器：细粒度锁或CAS替代整表锁，迭代具备弱一致性防报错
- ConcurrentHashMap：JDK 8抛弃Segment改用 Node数组+链表+红黑树
- CHM加锁本质：JDK 7分段锁，JDK 8细化为 CAS + synchronized锁头节点
- 典型场景：CopyOnWrite适合读多写少，阻塞队列常配合线程池消费

## 结构化回答

**30 秒电梯演讲：** 多窗口同时服务（并发容器）vs 单窗口排队（同步容器）。

**展开框架：**
1. **ConcurrentHash** — ConcurrentHashMap使用分段锁或CAS+Sync
2. **CopyOnWriteArr** — CopyOnWriteArrayList适合读多写少，写时复制
3. **阻塞队列（** — 阻塞队列（BlockingQueue）用于线程池任务传递

**收尾：** 这块我踩过一些坑，您想深入聊哪一段——原理细节、实战案例还是常见踩坑？

## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：什么是并发容器？Java 有哪些并发容器 | 今天这道题：什么是并发容器？Java 有哪些并发容器。30 秒先给你讲清楚。 | 开场钩子 |
| 0:20 | 核心概念动画/示意图 | 多窗口同时服务（并发容器）vs 单窗口排队（同步容器）。 | 核心概念 |
| 0:40 | ConcurrentHash示意图 | ConcurrentHashMap使用分段锁或CAS+Sync | ConcurrentHash |
| 1:10 | CopyOnWriteArr示意图 | CopyOnWriteArrayList适合读多写少，写时复制 | CopyOnWriteArr |
| 1:40 | 总结卡 + 下期预告 | 记住今天这几个关键词，面试一定用得上。下期见。 | 收尾 |
