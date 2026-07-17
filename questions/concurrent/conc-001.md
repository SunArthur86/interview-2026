---
id: conc-001
difficulty: L1
category: concurrent
feynman:
  essence: 固定数量线程，任务无限排队，线程永驻。
  analogy: 开设固定数量的窗口柜台，所有人取号排队，窗口不关。
  first_principle: 如何限制资源消耗以避免无限制创建线程导致的资源耗尽？
  key_points:
  - 核心线程数等于最大线程数，固定不变。
  - 使用无界队列存储多余任务，可能导致OOM。
  - 线程空闲时不会被回收，响应快但资源占用恒定。
  - 适用于负载稳定、已知并发量的场景。
memory_points:
- 特性口诀：核心等于最大，默认不超时回收
- 致命风险：因为用无界队列，所以任务堆积会导致OOM
- 核心源码：实际调用了ThreadPoolExecutor，keepAliveTime为0
- 生产建议：弃用该内置池，改用有界队列配合拒绝策略
---

# newFixedThreadPool是什么？

**newFixedThreadPool**

创建一个可重用固定线程数的线程池。核心特点如下：

1. **固定线程数**：池中始终维持指定数量的线程，这些线程即为核心线程数（`corePoolSize`），也等于最大线程数（`maximumPoolSize`）。
2. **无界队列**：使用共享的无界队列（`LinkedBlockingQueue`，默认容量为 `Integer.MAX_VALUE`）来存放待执行的任务。
3. **任务处理机制**：如果所有线程都处于活动状态，新提交的任务会在队列中等待，直到有线程可用。
4. **线程生命周期**：除非线程池显式关闭，否则池中的线程会一直存在（`allowCoreThreadTimeOut` 默认为 false），即使处于空闲状态也不会被回收。
5. **异常处理**：如果线程在执行任务期间因异常终止，线程池会创建一个新的线程来替代它。

**底层原理细节**：
- **源码实现**：实际调用的 `ThreadPoolExecutor` 构造函数如下：
  ```java
  new ThreadPoolExecutor(nThreads, nThreads, 0L, TimeUnit.MILLISECONDS, new LinkedBlockingQueue<Runnable>());
  ```
  由于 `keepAliveTime` 设置为 0，且核心线程默认不超时，多余的非核心线程不会被创建（因为 `core` == `max`），所以线程池大小恒定。
- **潜在风险**：由于使用了 `LinkedBlockingQueue`，如果任务提交速度远大于处理速度，队列可能会无限膨胀，导致 `OOM`（Out Of Memory）。

**任务提交流程图**：
```
新任务提交
   │
   ▼
当前线程数 < nThreads ?
   ├── Yes ──> 创建新线程执行任务
   │
   └── No ──> 加入 LinkedBlockingQueue (无界等待)
                  │
                  ▼
             (队列无限存储，直到有线程空闲取出)
```

**实战案例**：在某个高并发报表导出服务中，由于使用 `newFixedThreadPool` 处理导出任务，下游数据库响应变慢导致任务堆积，最终 `LinkedBlockingQueue` 撑满堆内存引发 OOM，导致整个服务节点不可用。**改进建议**：生产环境强烈建议使用自定义的 `ThreadPoolExecutor`，并指定 `LinkedBlockingQueue` 的具体容量（如 1000），配合拒绝策略（如 `CallerRunsPolicy`）进行降级保护。

**代码示例**：
```java
// 推荐的实战写法：自定义有界队列
ThreadPoolExecutor safePool = new ThreadPoolExecutor(
    10, 10, 0L, TimeUnit.MILLISECONDS,
    new LinkedBlockingQueue<Runnable>(1000), // 限制队列长度
    new ThreadPoolExecutor.CallerRunsPolicy() // 队列满时由调用线程执行，起到背压作用
);
```

**## 常见考点**
1. **OOM 风险**：为什么说 `newFixedThreadPool` 有可能导致内存溢出？
2. **参数对比**：它与 `newCachedThreadPool` 的核心区别（线程数量限制与队列类型）是什么？
3. **线程复用**：池中的线程是如何实现复用的（即 `runWorker` 方法中的循环逻辑）？

## 记忆要点

- 特性口诀：核心等于最大，默认不超时回收
- 致命风险：因为用无界队列，所以任务堆积会导致OOM
- 核心源码：实际调用了ThreadPoolExecutor，keepAliveTime为0
- 生产建议：弃用该内置池，改用有界队列配合拒绝策略

## 结构化回答

**30 秒电梯演讲：** 开设固定数量的窗口柜台，所有人取号排队，窗口不关。

**展开框架：**
1. **核心线程数** — 核心线程数等于最大线程数，固定不变。
2. **无界队列** — 使用无界队列存储多余任务，可能导致OOM。
3. **线程空闲时** — 线程空闲时不会被回收，响应快但资源占用恒定。

**收尾：** 这块我踩过一些坑，您想深入聊哪一段——原理细节、实战案例还是常见踩坑？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：newFixedThreadPool是什么 | 今天这道题：newFixedThreadPool是什么。30 秒先给你讲清楚。 | 开场钩子 |
| 0:20 | 核心概念动画/示意图 | 开设固定数量的窗口柜台，所有人取号排队，窗口不关。 | 核心概念 |
| 0:40 | 核心线程数示意图 | 核心线程数等于最大线程数，固定不变。 | 核心线程数 |
| 1:10 | 总结卡 + 下期预告 | 记住今天这几个关键词，面试一定用得上。下期见。 | 收尾 |
