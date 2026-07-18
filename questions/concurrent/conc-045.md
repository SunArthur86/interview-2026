---
id: conc-045
difficulty: L3
category: concurrent
feynman:
  essence: 预定义四种线程池满足常见需求，但底层均基于ThreadPoolExecutor。
  analogy: Fixed像固定出租车队，Cached像临时叫车（随叫随走），Single像专线司机（一次只拉一人），Scheduled像闹钟服务。
  first_principle: 如何复用线程并有效管理任务执行？
  key_points:
  - Fixed：固定线程数，队列无限，防OOM需自定义
  - Cached：线程数无限，队列空，适合短任务
  - Single：单线程串行，队列无限
  - Scheduled：支持定时和周期性任务
  - 生产环境建议使用ThreadPoolExecutor控制参数
memory_points:
- 四大线程池：Fixed(固定)、Cached(缓存无界)、Single(单串行)、Scheduled(定时)
- 生产禁忌：禁用 Executors 工厂，因为无界队列和无限线程极易导致 OOM
- 正确姿势：必须用 ThreadPoolExecutor 自定义，强制使用有界队列防内存溢出
- 参数配置：CPU密集型设核心数为 N+1，而 IO 密集型设为 2N 并配合有界队列
---

# Java 提供了哪几种线程池？各自的特点和适用场景？

Java 通过 Executors 工厂类提供 4 种预定义线程池（生产环境推荐用 ThreadPoolExecutor 自定义）：

**1. newFixedThreadPool：固定大小线程池**
- 核心线程数 = 最大线程数 = n，无空闲回收。
- 队列：无界 LinkedBlockingQueue（可能 OOM！）。
- 适用：负载较重、任务量稳定的场景。

**2. newCachedThreadPool：缓存线程池**
- 核心线程数 0，最大线程数 Integer.MAX_VALUE（可能创建大量线程 OOM！）。
- 队列：SynchronousQueue（不存储，直接交接）。
- 空闲线程 60 秒回收。
- 适用：大量短任务、负载轻的场景。

**3. newSingleThreadExecutor：单线程线程池**
- 核心线程数 = 最大线程数 = 1，串行执行。
- 队列：无界 LinkedBlockingQueue。
- 适用：需要保证顺序执行的任务。

**4. newScheduledThreadPool：定时/周期任务线程池**
- 支持延迟执行和周期执行（scheduleAtFixedRate/scheduleWithFixedDelay）。
- 适用：定时任务、心跳检测。

### 线程池参数对比表

| 线程池类型 | corePoolSize | maximumPoolSize | keepAliveTime | WorkQueue | 风险点 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| FixedThreadPool | n | n | 0 | LinkedBlockingQueue (无界) | 队列堆积 OOM |
| CachedThreadPool | 0 | MAX_VALUE | 60s | SynchronousQueue | 线程数爆炸 OOM |
| SingleThreadExecutor | 1 | 1 | 0 | LinkedBlockingQueue (无界) | 队列堆积 OOM |
| ScheduledThreadPool | n | MAX_VALUE | 0 | DelayedWorkQueue | 线程数爆炸 OOM |

**⚠️ 阿里巴巴规范**：不推荐用 Executors 的 4 种（FixedThreadPool/SingleThread 用无界队列易 OOM，CachedThreadPool 最大线程数无界易 OOM），推荐用 ThreadPoolExecutor 显式指定参数。

### 5. 边界情况
- **任务提交拒绝**：当队列满且线程数达到最大值时，会触发拒绝策略（默认 AbortPolicy 抛异常）。
- **线程创建时机**：核心线程是懒加载的（任务提交后才创建），除非调用 `prestartAllCoreThreads`。
- **OOM 恢复**：线程池一旦因 OOM 崩溃，内部状态可能损坏，通常建议创建新的线程池实例，而非复用旧实例。
- **shutdown 行为**：调用 `shutdown()` 后，不再接收新任务，但会执行完队列中已存在的任务；`shutdownNow()` 则尝试中断正在执行的任务并清空队列。

### 实战与深化

- **实战案例**：在生产环境日志处理服务中，曾直接使用 `newFixedThreadPool` 处理解析任务，某日上游日志量激增，任务积压在无界队列中导致堆内存溢出（OOM），服务宕机；后改用 `ThreadPoolExecutor` 自定义有界队列（`ArrayBlockingQueue`）并配合拒绝策略（记录并降级），成功隔离了故障。
- **代码示例**：
```java
// 生产环境推荐自定义线程池
ThreadPoolExecutor executor = new ThreadPoolExecutor(
    10,  // corePoolSize
    20,  // maximumPoolSize
    60L, TimeUnit.SECONDS,
    new ArrayBlockingQueue<>(200), // 有界队列防止 OOM
    new ThreadFactoryBuilder().setNameFormat("log-pool-%d").build(),
    new ThreadPoolExecutor.CallerRunsPolicy() // 拒绝策略：由调用线程执行
);
```
- **对比表格**：Executors 工厂方法 vs ThreadPoolExecutor 自定义

| 特性 | Executors 工厂方法 | ThreadPoolExecutor 自定义 | 生产建议 |
| :--- | :--- | :--- | :--- |
| **队列类型** | 多数为无界队列 (容易 OOM) | 通常指定有界队列 | **强烈建议有界** |
| **线程数控制** | Cached 线程数无界 | 自定义 core/max | **根据 CPU 密集/IO 密集设置** |
| **拒绝策略** | 默认 AbortPolicy (抛异常) | 可灵活配置 (如降级) | **根据业务容忍度选择** |
| **线程命名** | 无法自定义 | 可自定义 (利于排查日志) | **必须自定义命名格式** |

## 面试追问
1. 线程池的核心线程数（corePoolSize）是如何被初始化的？是随着任务提交创建，还是一开始就创建？如何让它在启动时就创建好？
2. 如果不设置 `RejectedExecutionHandler`，默认的拒绝策略是什么？请介绍另外几种常见的拒绝策略及其适用场景。
3. `allowCoreThreadTimeOut` 参数设置为 true 后，线程池的行为会发生什么变化？

## 易错点
1. **混淆 IO 密集型和 CPU 密集型线程数设置**：IO 密集型通常设置为 2N 或 2N+1（N为CPU核数），CPU 密集型设置为 N+1，而不是越大越好。
2. **使用无界队列**：误以为 `LinkedBlockingQueue` 不传参数是“有界”的，其实默认容量是 `Integer.MAX_VALUE`，极易造成内存溢出。


## 记忆要点

- 四大线程池：Fixed(固定)、Cached(缓存无界)、Single(单串行)、Scheduled(定时)
- 生产禁忌：禁用 Executors 工厂，因为无界队列和无限线程极易导致 OOM
- 正确姿势：必须用 ThreadPoolExecutor 自定义，强制使用有界队列防内存溢出
- 参数配置：CPU密集型设核心数为 N+1，而 IO 密集型设为 2N 并配合有界队列

## 结构化回答

**30 秒电梯演讲：** Fixed像固定出租车队，Cached像临时叫车（随叫随走），Single像专线司机（一次只拉一人），Scheduled像闹钟服务。

**展开框架：**
1. **Fixed** — Fixed：固定线程数，队列无限，防OOM需自定义
2. **Cached** — Cached：线程数无限，队列空，适合短任务
3. **Single** — Single：单线程串行，队列无限

**收尾：** 这块我踩过一些坑，您想深入聊哪一段——原理细节、实战案例还是常见踩坑？

## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：Java 提供了哪几种线程池？各自的特点和适用场景 | 今天这道题：Java 提供了哪几种线程池？各自的特点和适用场景。30 秒先给你讲清楚。 | 开场钩子 |
| 0:20 | 核心概念动画/示意图 | Fixed像固定出租车队，Cached像临时叫车（随叫随走），Single像专线司机（一次只拉一人），Scheduled像闹钟服务。 | 核心概念 |
| 0:40 | Fixed示意图 | Fixed：固定线程数，队列无限，防OOM需自定义 | Fixed |
| 1:10 | Cached示意图 | Cached：线程数无限，队列空，适合短任务 | Cached |
| 1:40 | 总结卡 + 下期预告 | 记住今天这几个关键词，面试一定用得上。下期见。 | 收尾 |
