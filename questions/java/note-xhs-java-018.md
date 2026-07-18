---
id: note-xhs-java-018
difficulty: L3
category: java
subcategory: 并发
tags:
- volatile
- 可见性
- 有序性
- 内存屏障
- JMM
- 并发
source: 拼多多Java三轮技术面一面
feynman:
  essence: volatile保证变量的可见性（修改立刻对其他线程可见）和有序性（禁止指令重排序），但不保证原子性。
  analogy: volatile就像办公室的白板——你写上去所有人立刻能看到（可见性），写的时候必须按顺序写（有序性），但两个人同时抢着写就会乱（不保证原子性）。
  key_points:
  - 保证可见性：修改后立即刷新到主内存，读取时强制从主内存加载
  - 保证有序性：通过内存屏障禁止指令重排序
  - 不保证原子性：volatile int的i++不是原子操作
  - 底层靠Store Barrier和Load Barrier实现
  - 典型应用：DCL单例、状态标志位
first_principle:
  problem: 多核CPU各有自己的高速缓存（L1/L2/L3），一个线程修改了变量的值，另一个线程可能还读到旧值。如何用最小代价保证数据可见？
  axioms:
  - 每个CPU核心有自己的L1/L2缓存，共享L3和主内存
  - 缓存一致性协议（MESI）保证缓存行级别的同步
  - 编译器和CPU为了优化性能会重排序指令
  - 重量级锁（synchronized）开销太大，需要轻量级方案
  rebuild: 在变量前加volatile修饰符 → 编译器在读写操作前后插入内存屏障 → CPU触发缓存一致性协议，使其他核心的缓存行失效 → 修改后的值对所有核心立即可见。同时屏障阻止指令重排序。
follow_up:
- volatile能替代synchronized吗？为什么？
- volatile的i++为什么不是原子操作？怎么修复？
- DCL单例模式中，volatile修饰实例变量的作用是什么？
- volatile和final有什么关系？final域的重排序规则是什么？
- 什么是伪共享（False Sharing）？volatile会导致伪共享吗？如何解决？
memory_points:
- volatile两保证一不保证：保证可见性+有序性，不保证原子性
- 底层：Store Barrier（写后插入）+ Load Barrier（读前插入）
- DCL单例必须用volatile——防止new对象时的指令重排序（分配内存→赋值引用→初始化，重排为分配→赋值→其他线程拿到未初始化对象）
- 替代方案：AtomicInteger保证原子性、synchronized保证互斥
frequency: high
---

# 【拼多多一面】volatile 关键字的作用和底层实现

## 🎯 一句话本质

volatile是Java提供的**最轻量级的同步机制**，保证变量的**可见性**（Visibility）和**有序性**（Ordering），但**不保证原子性**（Atomicity）。底层通过CPU**内存屏障**（Memory Barrier）实现。

## 🧒 费曼类比

```
没有volatile的世界：
  CPU核心1: 我把flag改成true了（写在自己的缓存里）
  CPU核心2: flag还是false啊？（读的是自己缓存的旧值）
  结果：核心2永远等不到flag变true 💀

有volatile的世界：
  CPU核心1: flag=true! → 白板通知所有核心 → 缓存失效
  CPU核心2: flag被改了？重新读主内存 → true!
  结果：核心2立刻看到变更 ✅
```

## 📊 可见性原理（JMM层面）

```
       Thread-1                    Main Memory                  Thread-2
    ┌──────────┐                ┌──────────────┐             ┌──────────┐
    │ 工作内存  │                │              │             │ 工作内存  │
    │ flag=true│─── Store ────→ │  flag = true │ ←─ Load ────│ flag=false│
    │ (本地缓存)│   Barrier      │  (主内存)     │   Barrier   │(缓存失效) │
    └──────────┘                └──────────────┘             └──────────┘
         │                                                        │
    volatile写操作:                                          volatile读操作:
    1. 写工作内存                                        1. 缓存行被标记为无效
    2. StoreStore屏障（前面普通写不能重排到后面）            2. LoadLoad屏障（后面的读不能重排到前面）
    3. 写主内存                                          3. 从主内存重新加载
    4. StoreLoad屏障（防止后面的读重排到前面）               4. 读主内存值
```

## 🔧 三大特性详解

### 1. 可见性

当一个线程修改了volatile变量，JMM会立刻将线程工作内存中的值刷新到主内存；其他线程读取时，JMM会将它们工作内存中的缓存置为无效，强制从主内存重新加载。

```java
// 没有volatile → 程序可能永远不停止
class NoVolatileDemo {
    private boolean running = true; // 加 volatile 才能正常退出

    void stop() { running = false; }

    void run() {
        while (running) {
            // JIT优化后可能永远读取寄存器中的缓存值
        }
        System.out.println("stopped");
    }
}
```

### 2. 有序性（禁止指令重排序）

编译器和CPU为了提高性能会对指令进行重排序。volatile通过插入**内存屏障**来禁止特定方向的重排序：

```
volatile写之前的普通读写  ←StoreStore屏障→  不能重排到volatile写之后
volatile写                                ←StoreLoad屏障→  后面的读写不能重排到写之前
volatile读                                ←LoadLoad屏障→  后面的读不能重排到读之前
volatile读                                ←LoadStore屏障→ 后面的写不能重排到读之前
```

### 3. 不保证原子性

```java
volatile int count = 0;

// 10个线程各执行1000次 count++
// 结果大概率不等于 10000
// 因为 count++ = 读 + 加1 + 写，三步之间可以被其他线程打断
```

**修复方案**：
```java
AtomicInteger count = new AtomicInteger(0);
count.incrementAndGet(); // CAS保证原子性

// 或者
synchronized void increment() { count++; }
```

## 💻 经典应用：DCL单例模式

```java
public class Singleton {
    // 必须加volatile！
    private static volatile Singleton instance;

    public static Singleton getInstance() {
        if (instance == null) {                   // 第一次检查（无锁）
            synchronized (Singleton.class) {
                if (instance == null) {            // 第二次检查
                    instance = new Singleton();    // 非原子操作！
                }
            }
        }
        return instance;
    }
}
```

**为什么必须加volatile？**

`instance = new Singleton()` 在字节码层面分三步：

```
1. 分配内存空间                  memory = allocate()
2. 初始化对象                    ctorInstance(memory)  
3. 将引用指向内存地址             instance = memory

如果步骤2和3被重排序 → 另一个线程在第一次检查时拿到未初始化的对象 → NPE！
volatile禁止2和3重排序，确保要么都没做，要么都做完了。
```

## 🔧 底层实现：内存屏障

JMM定义了4种内存屏障：

| 屏障类型 | 指令 | 作用 |
|---------|------|------|
| StoreStore | Store1; **StoreStore**; Store2 | Store1必须在Store2前刷新到内存 |
| StoreLoad | Store1; **StoreLoad**; Load2 | Store1刷新后才能执行Load2（开销最大） |
| LoadLoad | Load1; **LoadLoad**; Load2 | Load1必须在Load2前完成读取 |
| LoadStore | Load1; **LoadStore**; Store2 | Load1必须在Store2前完成读取 |

在x86架构上，volatile写最终会生成 `lock addl $0x0,(%rsp)` 指令，它有两个作用：
1. 锁定缓存行，将当前处理器缓存写回内存
2. 使其他CPU缓存中该地址无效（触发MESI协议）

## 📋 面试加分点

1. **volatile vs synchronized对比**：
   - volatile轻量级（无上下文切换），synchronized重量级（可能引起线程阻塞）
   - volatile只修饰变量，synchronized可修饰方法和代码块
   - volatile不保证原子性，synchronized保证原子性

2. **happens-before规则**：volatile变量的写操作 happens-before 后续的读操作

3. **x86的强内存模型**：x86是TSO（Total Store Order），只有StoreLoad需要显式屏障，其他三种自动保证。所以volatile在x86上几乎零开销。

4. **CAS操作自带volatile语义**：`AtomicInteger.incrementAndGet()` 底层是Unsafe.compareAndSwapInt，本身就有全屏障效果

## ❓ 苏格拉底式面试追问

1. **"volatile保证了可见性，那为什么i++还是不安全？你能拆解i++的底层操作来解释吗？"**
   → 引导分析i++的三步：读取→加1→写回，中间有间隙

2. **"你提到DCL单例需要volatile，那用静态内部类实现的懒加载需要volatile吗？为什么？"**
   → 测试对类加载机制的理解（静态内部类利用JVM类加载机制保证线程安全，不需要volatile）

3. **"在ARM架构上volatile的开销和在x86上一样吗？为什么？"**
   → 引导思考不同CPU内存模型的差异，ARM是弱内存模型需要更多屏障

4. **"如果把volatile数组中的某个元素修改了，其他线程能看到吗？"**
   → volatile修饰的是引用，不是数组元素。修改arr[i]对其他线程不可见

5. **"volatile的happens-before规则和synchronized的happens-before规则有什么区别？"**
   → volatile是变量级别的happens-before，synchronized是锁释放/获取的happens-before


## 核心流程图

```mermaid
flowchart TD
    Start([🚀 应用发起读请求]):::start
    App[应用层<br/>查询数据]:::client
    CacheHitQ{{缓存命中?}}:::decision
    ReturnCache["直接返回缓存数据<br/>O(1) 低延迟"]:::process
    MissDB{缓存未命中}:::decision
    QueryDB[查询数据库<br/>执行 SQL]:::process
    PenetrateQ{{是否为恶意请求?<br/>查询不存在的 key}}:::decision
    BloomFilter[布隆过滤器拦截<br/>+ 缓存空值]:::process
    BreakDownQ{{热点 key 失效?<br/>缓存击穿}}:::decision
    Mutex[加互斥锁<br/>单线程回源]:::process
    AvalancheQ{{大批 key 同时过期?<br/>缓存雪崩}}:::decision
    TTLJitter[随机 TTL<br/>+ 多级缓存]:::process
    WriteBackQ{{是否回写缓存?}}:::decision
    WriteCache[写入 Redis<br/>设置 TTL]:::process
    BigKeyCheck{{大 Key / 热 Key?}}:::decision
    SplitKey[拆分大 Key<br/>本地缓存热 Key]:::process
    DB[(MySQL 主从<br/>持久化数据)]:::store
    Cache[(Redis Cluster<br/>分片缓存)]:::store
    Final([✅ 返回结果]):::start
    Alarm[告警 + 限流降级]:::danger

    Start --> App --> CacheHitQ
    CacheHitQ -->|命中| ReturnCache --> BigKeyCheck
    BigKeyCheck -->|是| SplitKey --> Final
    BigKeyCheck -->|否| Final
    CacheHitQ -->|未命中| MissDB --> PenetrateQ
    PenetrateQ -->|是| BloomFilter --> Alarm
    PenetrateQ -->|否| BreakDownQ
    BreakDownQ -->|是| Mutex --> QueryDB
    BreakDownQ -->|否| AvalancheQ
    AvalancheQ -->|是| TTLJitter --> QueryDB
    AvalancheQ -->|否| QueryDB
    QueryDB --> DB --> WriteBackQ
    WriteBackQ -->|是| WriteCache --> Cache --> ReturnCache
    WriteBackQ -->|否| ReturnCache

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef client fill:#10b981,stroke:#047857,color:#fff;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef store fill:#8b5cf6,stroke:#6d28d9,color:#fff;
    classDef danger fill:#b91c1c,stroke:#7f1d1d,color:#fff,stroke-width:2px;

```

## 结构化回答

**30 秒电梯演讲：** volatile保证变量的可见性（修改立刻对其他线程可见）和有序性（禁止指令重排序），但不保证原子性。

**展开框架：**
1. **volatile两保证一** — 保证可见性+有序性，不保证原子性
2. **底层** — Store Barrier（写后插入）+ Load Barrier（读前插入）
3. **DCL单例必须用** — —防止new对象时的指令重排序（分配内存→赋值引用→初始化，重排为分配→赋值→其他线程拿到未初始化对象）

**收尾：** 这块我踩过坑——要不要深入聊：volatile能替代synchronized吗？为什么？

## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "并发一句话：volatile保证变量的可见性（修改立刻对其他线程可见）和有序性（禁止指令重排序），但不保证原子性。" | 开场钩子 |
| 0:15 | 排序算法柱状图动画 | "volatile两保证一不保证：保证可见性+有序性，不保证原子性" | volatile两保证一 |
| 1:06 | 排序算法柱状图动画分步演示 | "底层：Store Barrier（写后插入）+ Load Barrier（读前插入）" | 底层 |
| 1:57 | 关键代码/伪代码片段 | "DCL单例必须用volatile——防止new对象时的指令重排序（分配内存到赋值引用到初始化，重排为分配到赋值到其他…" | DCL单例必须用 |
| 2:50 | 总结卡 | "核心抓住这条主线，下期咱们接着聊：volatile能替代synchronized吗？为什么。" | 收尾 |

### 视频流程图

```mermaid
flowchart LR

    subgraph Intro["引入"]
        A["【拼多多一面】volatile 关键字的作用和底层实现"]:::intro
    end

    subgraph Core["讲解"]
        B["直接返回缓存数据 O（1） 低延迟"]:::core
        C["volatile两保证一"]:::deep
    end

    subgraph Practice["实战"]
        D["代码实战"]:::practice
    end

    subgraph Wrap["收尾"]
        E["总结回顾"]:::wrap
    end

    A --> B --> C --> D --> E

    classDef intro fill:#FF9800,color:#fff,stroke:#F57C00,stroke-width:2px
    classDef core fill:#2196F3,color:#fff,stroke:#1976D2,stroke-width:2px
    classDef deep fill:#4CAF50,color:#fff,stroke:#388E3C,stroke-width:2px
    classDef practice fill:#9C27B0,color:#fff,stroke:#7B1FA2,stroke-width:2px
    classDef wrap fill:#607D8B,color:#fff,stroke:#455A64,stroke-width:2px
```


