---
id: conc-009
difficulty: L2
category: concurrent
feynman:
  essence: 针对不同负载特性，预设了固定、缓存、单线程、定时四种配置。
  analogy: 像交通工具选择：公交（固定）、出租车（缓存）、专车（单线程）、校车（定时）。
  first_principle: 如何通过预配置减少并发编程的复杂度，同时适应不同的任务特征？
  key_points:
  - Fixed：限制并发数，稳。
  - Cached：弹性扩容，适合小任务快处理。
  - Single：顺序执行，安全。
  - Scheduled：周期性任务，替代 Timer。
memory_points:
- Fixed特性：核心等于最大，因用无界队列易致OOM
- Cached特性：核心为0且最大无穷，因无限创线程易耗尽CPU
- 其他两种：Single串行执行保顺序，Scheduled支持定时周期任务
- 最佳实践：因内置池均有OOM或耗尽风险，所以生产禁用 Executors
---

# Java内置的4种线程池各自的特点和使用场景是什么？

Java 通过 `Executors` 工具类提供了 4 种常见的线程池，它们实际上是对 `ThreadPoolExecutor` 参数的不同封装。在生产代码中，建议直接使用 `ThreadPoolExecutor` 构造器，以便明确控制队列大小和拒绝策略，防止 OOM。

**1. newFixedThreadPool（固定大小线程池）**
- **参数配置**：`corePoolSize = n`, `maxPoolSize = n`, `keepAliveTime = 0`。
- **队列**：`LinkedBlockingQueue`（无界队列，容量为 `Integer.MAX_VALUE`）。
- **特点**：线程数固定，多余任务在队列中无限等待。
- **场景**：适用于负载较重、需要限制并发线程数的场景。
- **风险**：任务堆积过多可能导致 OOM。

**2. newCachedThreadPool（缓存线程池）**
- **参数配置**：`corePoolSize = 0`, `maxPoolSize = Integer.MAX_VALUE`, `keepAliveTime = 60s`。
- **队列**：`SynchronousQueue`（不存储元素的队列，直接传递给线程）。
- **特点**：无线程时可创建，空闲 60 秒回收。来多少任务创建多少线程（直到 Integer.MAX_VALUE）。
- **场景**：适用于大量短生命周期、异步的任务，并发突增。
- **风险**：高并发下可能因线程数暴涨导致 CPU 耗尽或 OOM。

**3. newSingleThreadExecutor（单线程线程池）**
- **参数配置**：`corePoolSize = 1`, `maxPoolSize = 1`。
- **队列**：`LinkedBlockingQueue`。
- **特点**：单线程串行执行，保证任务顺序（FIFO）。
- **场景**：需要保证任务执行顺序，且同一时间只有一个任务执行的场景。
- **风险**：同样存在无界队列 OOM 风险。

**4. newScheduledThreadPool（定时任务线程池）**
- **参数配置**：`corePoolSize = n`, `maxPoolSize = Integer.MAX_VALUE`。
- **队列**：`DelayedWorkQueue`（优先级队列，基于堆结构）。
- **特点**：支持 `schedule`（延迟执行）和 `scheduleAtFixedRate`（周期性执行）。
- **场景**：需要执行定时任务或周期性心跳检测。
- **风险**：最大线程数无界风险。

### 实战案例
某线上服务因下游响应变慢，`newFixedThreadPool` 的任务队列堆积了数百万个对象，直接导致 Full GC 频繁直至 OOM 崩溃。修复后改用有界队列 `ArrayBlockingQueue` 并自定义拒绝策略（记录日志+降级处理），成功将故障限制在局部。

### 代码示例 (推荐的生产环境构造)
```java
ThreadPoolExecutor executor = new ThreadPoolExecutor(
    10, // corePoolSize
    20, // maxPoolSize
    60L, TimeUnit.SECONDS,
    new ArrayBlockingQueue<>(200), // 有界队列，防止OOM
    new ThreadFactoryBuilder().setNameFormat("biz-pool-%d").build(),
    new ThreadPoolExecutor.CallerRunsPolicy() // 拒绝策略：由调用线程执行
);
```

### 4种线程池对比
| 特性 | FixedThreadPool | CachedThreadPool | SingleThreadExecutor | ScheduledThreadPool |
| :--- | :--- | :--- | :--- | :--- |
| **核心线程数** | 固定 N | 0 | 1 | N |
| **最大线程数** | 固定 N | Integer.MAX_VALUE | 1 | Integer.MAX_VALUE |
| **工作队列** | LinkedBlockingQueue (无界) | SynchronousQueue | LinkedBlockingQueue (无界) | DelayedWorkQueue |
| **存活时间** | 0 | 60s | 0 | 0 |
| **主要风险** | 队列堆积 OOM | 线程数暴涨 OOM/CPU满 | 队列堆积 OOM | 线程数暴涨 OOM |
| **适用场景** | 稳定负载，限流 | 瞬时高并发，短任务 | 顺序执行，内存安全 | 定时/周期任务 |

## 常见考点
1. **OOM 风险**：为什么阿里规范禁止使用 Executors 创建线程池？（因为 Fixed/Single 使用默认无界 LinkedBlockingQueue，Cached 使用最大 Integer 线程数，高负载下均会导致内存溢出）。
2. **线程池参数含义**：`corePoolSize`（即使空闲也保留的线程数）、`maxPoolSize`（最大线程数）、`workQueue`（任务缓冲区）之间的协作逻辑（先 core -> 满 queue -> 满 max -> 拒绝）。
3. **如何创建合适的线程池**：IO 密集型任务建议 `corePoolSize = 2N + 1`（N 为 CPU 核数），CPU 密集型建议 `corePoolSize = N + 1`。

## 核心知识点图

<img src="/interview-2026/images/diagram_concurrent_conc-009.svg" alt="Java内置的4种线程池各自的特点和使用场景是什么？ 核心知识点图" style="max-width:100%;height:auto;border:1px solid var(--border);border-radius:8px;margin:1em 0;" />

## 记忆要点

- Fixed特性：核心等于最大，因用无界队列易致OOM
- Cached特性：核心为0且最大无穷，因无限创线程易耗尽CPU
- 其他两种：Single串行执行保顺序，Scheduled支持定时周期任务
- 最佳实践：因内置池均有OOM或耗尽风险，所以生产禁用 Executors

## 结构化回答




**30 秒电梯演讲：** 像交通工具选择：公交（固定）、出租车（缓存）、专车（单线程）、校车（定时）。

**展开框架：**
1. **Fixed** — 限制并发数，稳。
2. **Cached** — 弹性扩容，适合小任务快处理。
3. **Single** — 顺序执行，安全。

**收尾：** 这是我实战中的理解，您想深入哪一段？




## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：Java内置的4种线程池各自的特点和使用场景是什么 | 今天这道题：Java内置的4种线程池各自的特点和使用场景是什么。30 秒先给你讲清楚。 | 开场钩子 |
| 0:20 | 核心概念动画/示意图 | 像交通工具选择：公交（固定）、出租车（缓存）、专车（单线程）、校车（定时）。 | 核心概念 |
| 0:40 | Fixed示意图 | Fixed：限制并发数，稳。 | Fixed |
| 1:10 | 总结卡 + 下期预告 | 记住今天这几个关键词，面试一定用得上。下期见。 | 收尾 |
