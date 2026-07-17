---
id: core-298
difficulty: L3
category: java-core
feynman:
  essence: 区分集合在并发环境下是否需要外部同步才能安全操作。
  analogy: 单行道（线程安全，一次只能一个车）和多车道（不安全，会撞车）。
  first_principle: 多线程同时读写数据时，如何保证数据一致性与性能？
  key_points:
  - 旧类Vector/HashTable是线程安全但性能低
  - 常用类ArrayList/HashMap是线程不安全
  - 不安全集合可用Collections工具类包装
  - 并发包（JUC）中有更高效的并发集合
memory_points:
- 老牌安全：Vector/Hashtable方法全锁（性能差淘汰），Collections包装类迭代需手动加锁
- 并发推荐：JUC包下首选，ConcurrentHashMap（分段锁/CAS+syn）和CopyOnWriteList（读多写少）
- 底层特性：HashMap底层是数组+链表/红黑树，ArrayDeque底层是循环数组
- 不安全风险：HashMap多线程扩容易导致数据丢失或死循环（JDK1.7头插法成环）
---

# 有哪些集合是线程安全和线程不安全的？

### 集合框架底层数据结构

#### 1. List接口的实现
- **ArrayList**：基于动态数组实现。底层使用 `Object[]` 数组存储，默认容量为 10，扩容时通常按 `newCapacity = oldCapacity + (oldCapacity >> 1)`（即 1.5 倍）增长。
- **LinkedList**：基于双向链表实现。底层通过内部类 `Node` 包含 `prev`, `item`, `next` 指针连接。
- **Vector**：类似于 ArrayList，但是是线程安全的。底层也是使用数组实现，方法使用 `synchronized` 修饰，扩容默认为 2 倍（可通过 `capacityIncrement` 修改）。

#### 2. Set接口
- **HashSet**：基于哈希表实现。底层实际上是 `HashMap`，元素作为 Key，Value 是一个固定的 `PRESENT` 对象。JDK 1.8 后，当链表长度超过 8 且数组长度超过 64 时，链表转为红黑树。
- **LinkedHashSet**：继承自 `HashSet`，底层使用 `LinkedHashMap`，通过维护一个双向链表来记录插入顺序（或访问顺序）。
- **TreeSet**：基于红黑树实现。底层使用 `TreeMap`，元素有序（自然排序或自定义 Comparator）。

#### 3. Queue接口
- **LinkedList**：同时实现了 List、Queue 和 Deque 接口，可作为双端队列使用。
- **ArrayDeque**：基于动态数组的双端队列。底层使用循环数组（利用 head 和 tail 指针实现），效率高于 LinkedList（在队列操作时减少了对象创建开销）。
- **PriorityQueue**：基于优先级堆实现的队列。底层使用数组表示的**小顶堆**（二叉堆），不允许 null 元素，非线程安全。

#### 4. Map接口
- **HashMap**：基于哈希表实现。JDK 1.8 结构为：`数组 + 链表/红黑树`。初始容量 16，负载因子 0.75。线程不安全。
- **LinkedHashMap**：在 HashMap 的基础上加入双向链表，可以保持插入顺序或 LRU 顺序（通过 `accessOrder` 参数控制）。
- **TreeMap**：基于红黑树实现。Key 必须实现 Comparable 或传入 Comparator，按键有序。
- **Hashtable**：古老的哈希表实现，类似 HashMap，但方法都是 `synchronized` 修饰的，不允许 key 或 value 为 null。不推荐使用。

---

### 线程安全 vs 线程不安全

#### 线程安全

1. **Vector / Hashtable**：
   - **原理**：直接在方法上加 `synchronized` 锁，锁的粒度大（对象级锁），并发性能较差。
   - **现状**：属于遗留类，现在极少使用。

2. **Collections.synchronizedXxx**：
   - **原理**：通过包装器模式，返回一个所有迭代方法都加锁的集合类。
   - **注意**：**迭代时必须手动加锁**，否则可能抛出 `ConcurrentModificationException`。例如：
     ```java
     List list = Collections.synchronizedList(new ArrayList());
     synchronized(list) { // 必须手动同步
         Iterator i = list.iterator();
         while (i.hasNext())
             foo(i.next());
     }
     ```

3. **`java.util.concurrent` 包下的并发集合（推荐）**：
   - **ConcurrentHashMap**：JDK 1.7 使用分段锁，JDK 1.8 使用 CAS + `synchronized` 锁数组节点，粒度更细，效率高。
   - **CopyOnWriteArrayList / CopyOnWriteArraySet**：写时复制。适用于读多写少的场景。通过在修改时复制底层数组来实现无锁读。
   - **BlockingQueue**（如 ArrayBlockingQueue, LinkedBlockingQueue）：内部使用 ReentrantLock 或 Condition 实现生产者-消费者模型。
   - **ConcurrentSkipListMap / ConcurrentSkipListSet**：基于跳表实现的并发有序集合。

#### 线程不安全

1. **ArrayList, LinkedList, HashSet, HashMap**：
   - **风险**：在多线程扩容或插入时，可能导致数据覆盖、数组越界（在 JDK 1.7 的 HashMap 扩容中）或死循环（JDK 1.7 链表环）。

2. **TreeMap, TreeSet**：
   - 同样非线程安全。多线程下破坏树结构会导致遍历异常或数据丢失。

---

### ## 常见考点

1. **HashMap 在多线程下扩容导致死循环的问题（JDK 1.7 特有）**：
   - 解释 1.7 头插法导致链表成环的原理，以及 1.8 改为尾插法如何解决了这个问题（但仍非线程安全）。

2. **ConcurrentHashMap 在 JDK 1.7 和 1.8 的实现区别**：
   - 1.7 分段锁 vs 1.8 CAS + synchronized。
   - 为什么 1.8 放弃了分段锁？（为了减少内存占用，提高扩容性能）。

3. **CopyOnWriteArrayList 的迭代器为什么是弱一致性的？**
   - 理解它迭代的是创建迭代器那一刻的数组快照，迭代过程中如果有修改，迭代器感知不到。

4. **ArrayList 扩容机制细节**：
   - 默认容量、扩容倍数、`Arrays.copyOf` 的性能损耗。

## 记忆要点

- 老牌安全：Vector/Hashtable方法全锁（性能差淘汰），Collections包装类迭代需手动加锁
- 并发推荐：JUC包下首选，ConcurrentHashMap（分段锁/CAS+syn）和CopyOnWriteList（读多写少）
- 底层特性：HashMap底层是数组+链表/红黑树，ArrayDeque底层是循环数组
- 不安全风险：HashMap多线程扩容易导致数据丢失或死循环（JDK1.7头插法成环）

## 结构化回答

**30 秒电梯演讲：** 区分集合在并发环境下是否需要外部同步才能安全操作。打个比方，单行道（线程安全，一次只能一个车）和多车道（不安全，会撞车）。

**展开框架：**
1. **老牌安全** — Vector/Hashtable方法全锁（性能差淘汰），Collections包装类迭代需手动加锁
2. **并发推荐** — JUC包下首选，ConcurrentHashMap（分段锁/CAS+syn）和CopyOnWriteList（读多写少）
3. **底层特性** — HashMap底层是数组+链表/红黑树，ArrayDeque底层是循环数组

**收尾：** 这三点都能配合实战聊。您想深入聊原理、对比还是避坑？

## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：有哪些集合是线程安全和线程不安全的 | "有哪些集合是线程安全和线程不安全的？一句话——单行道（线程安全，一次只能一个车）和多车道（不安全，会撞车）。" | 开场钩子 |
| 0:45 | 概念动画/示意图 | "区分集合在并发环境下是否需要外部同步才能安全操作——单行道（线程安全，一次只能一个车）和多车道（不安全，会撞车）" | 核心定义 |
| 1:30 | 老牌安全示意 | "Vector/Hashtable方法全锁（性能差淘汰），Collections包装类迭代需手动加锁" | 要点1 |
| 2:15 | 并发推荐示意 | "JUC包下首选，ConcurrentHashMap（分段锁/CAS+syn）和CopyOnWriteList（读多写少）" | 要点2 |
| 3:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |
