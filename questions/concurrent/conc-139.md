---
id: conc-139
difficulty: L4
category: concurrent
subcategory: 线程池
tags:
- 线程池
- 调优
- 拒绝策略
feynman:
  essence: 根据任务类型平衡 CPU 利用与资源等待，通过有界队列防止资源耗尽。
  analogy: 线程池就像银行柜台：核心员工（核心线程）一直在办业务；人多了叫号排队（队列）；排满了雇临时工（最大线程）；挤爆了就保安拦人（拒绝策略）。
  first_principle: 如何平衡有限的 CPU 资源与不确定的任务量，以实现最大吞吐量且不导致系统崩溃？
  key_points:
  - CPU 密集型设 N+1，IO 密集型设 2N 或公式计算
  - 拒绝 Executors，使用有界队列防止 OOM
  - 通过监控指标进行动态参数调整
follow_up:
- 线程池的队列为什么不用无界？newFixedThreadPool 的坑是什么？
- CallerRunsPolicy 拒绝策略为什么能起到「降速」效果？
- 如何动态调整线程池参数？有什么工具？
memory_points:
- 任务提交流程：核心满 -> 入队列 -> 队列满 -> 最大线程满 -> 拒绝策略。
- 因为 CPU 密集型需减少切换，所以线程数设为 N+1；而 IO 密集型需利用等待，设为 2N。
- 实战避坑：核心数极小而无界队列极大，会导致任务堆积拖垮 RT，建议用有界队列防 OOM。
- 拒绝策略选型：限流降级用 CallerRunsPolicy，快速失败用 AbortPolicy，容忍丢失用 DiscardPolicy。
---

# 线程池如何调优？核心线程数、最大线程数、队列大小应该怎么设置？

【线程池参数】
ThreadPoolExecutor 7 个参数：
- corePoolSize（核心线程数）：常驻核心线程数，即使空闲也不会被回收（除非 allowCoreThreadTimeOut 设置为 true）。
- maximumPoolSize（最大线程数）：线程池允许创建的最大线程数。
- keepAliveTime（空闲存活时间）：非核心线程空闲时的存活时间。
- unit（时间单位）：keepAliveTime 的时间单位（纳秒、毫秒等）。
- workQueue（任务队列）：用于保存等待执行任务的阻塞队列。
- threadFactory（线程工厂）：创建新线程，用于设置线程名、是否守护线程等。
- rejectedExecutionHandler（拒绝策略）：当队列满且线程数达到最大值时的处理策略。

【任务提交流程与架构】
```text
      提交任务
         │
         ▼
┌─────────────────────┐
│ 核心线程数 < core?   │──Yes──> 创建核心线程执行
└─────────────────────┘
         │ No
         ▼
┌─────────────────────┐
│ 队列已满?            │──No──> 入队等待
└─────────────────────┘
         │ Yes
         ▼
┌─────────────────────┐
│ 线程数 < maximum?    │──Yes──> 创建非核心线程执行
└─────────────────────┘
         │ No
         ▼
┌─────────────────────┐
│ 执行拒绝策略         │
└─────────────────────┘
```

【线程数设置公式】
- **CPU 密集型**：N + 1（N = CPU 核数，Runtime.getRuntime().availableProcessors()）。
  - *原理*：CPU 一直处于计算状态，多一个线程是为了处理因页面错误或其他原因导致的偶发暂停，保证 CPU 时钟利用率。
- **IO 密集型**：2N 或 N * (1 + IO耗时/CPU耗时)。
  - *原理*：IO 操作（网络、磁盘）不占用 CPU，线程处于阻塞状态。通过增加线程数充分利用 CPU 切换执行其他任务。
- **混合型**：拆分任务，使用不同线程池（CPU 密集池小，IO 密集池大），避免相互影响。

【实战案例】
在电商大促期间，订单服务曾因将核心线程数设置得过小（仅为 8），而队列容量设置得过大（10000），导致在流量洪峰时任务大量堆积在队列中，下游数据库虽然空闲但无法处理，RT（响应时间）飙升至 10s+。改为线程数 50、队列 500 后，任务被快速拒绝或消费，系统吞吐量提升了 3 倍。

【代码示例】
```java
int cpuCore = Runtime.getRuntime().availableProcessors();
// IO 密集型动态计算线程数 (假设 IO 等待占比 70%)
double blockingCoefficient = 0.7;
int threadCount = (int) (cpuCore / (1 - blockingCoefficient)); 

ThreadPoolExecutor executor = new ThreadPoolExecutor(
    threadCount, // corePoolSize
    threadCount * 2, // maximumPoolSize
    60L, TimeUnit.SECONDS,
    new LinkedBlockingQueue<>(500), // 有界队列防 OOM
    new ThreadFactoryBuilder().setNameFormat("order-pool-%d").build(),
    new ThreadPoolExecutor.CallerRunsPolicy() // 兜底背压
);
```

【队列选择】
- **有界队列**（如 `ArrayBlockingQueue`）：
  - *优点*：防止资源耗尽（OOM），系统可控。
  - *缺点*：队列满时触发创建非核心线程或拒绝策略，需权衡队列大小和 `maxPoolSize`。
- **无界队列**（如 `LinkedBlockingQueue`）:
  - *优点*：任务缓冲能力强，不会立即触发拒绝。
  - *缺点*：当任务堆积速度 > 消费速度时，极易导致 OOM（`newFixedThreadPool` 的坑）。
- **同步移交队列**（`SynchronousQueue`）：
  - *特点*：不存储元素，每个插入操作必须等待另一个线程的移除操作。
  - *场景*：`newCachedThreadPool`，追求高响应速度，传递任务直接给线程，无缓冲。

【拒绝策略对比】
| 策略 | 行为 | 适用场景 |
| :--- | :--- | :--- |
| **AbortPolicy** (默认) | 抛出 RejectedExecutionException | 需快速感知异常、开发测试环境 |
| **CallerRunsPolicy** | 由调用线程（主线程）执行任务 | 需要降级限流、允许短暂延迟的生产环境 |
| **DiscardPolicy** | 静默丢弃，不报错 | 非关键数据、可容忍丢失（如日志统计） |
| **DiscardOldestPolicy** | 丢弃队列最老任务，尝试重新提交 | 愿意牺牲旧任务以执行新任务 |

【调优建议】
1. **禁止使用 Executors**：直接使用 `ThreadPoolExecutor`，明确参数含义，避免隐式 OOM 风险。
2. **核心线程数**：
   - 动态计算：根据压测结果调整。一般 IO 密集型设为 `2 * CPU` 或 `CPU / (1 - 阻塞系数)`。
3. **队列设置**：推荐有界队列。大小设置需结合任务执行耗时与系统容忍的最大延迟。
4. **拒绝策略**：核心业务推荐 `CallerRunsPolicy` 实现平滑降级，非核心业务可用 Discard 或记录日志持久化。

## 记忆要点

- 任务提交流程：核心满 -> 入队列 -> 队列满 -> 最大线程满 -> 拒绝策略。
- 因为 CPU 密集型需减少切换，所以线程数设为 N+1；而 IO 密集型需利用等待，设为 2N。
- 实战避坑：核心数极小而无界队列极大，会导致任务堆积拖垮 RT，建议用有界队列防 OOM。
- 拒绝策略选型：限流降级用 CallerRunsPolicy，快速失败用 AbortPolicy，容忍丢失用 DiscardPolicy。

## 结构化回答

**30 秒电梯演讲：** 线程池就像银行柜台：核心员工（核心线程）一直在办业务；人多了叫号排队（队列）；排满了雇临时工（最大线程）；挤爆了就保安拦人（拒绝策略）。

**展开框架：**
1. **CPU 密集型设 N+1** — CPU 密集型设 N+1，IO 密集型设 2N 或公式计算
2. **拒绝 Executors** — 拒绝 Executors，使用有界队列防止 OOM
3. **监控指标进行动态参数调整** — 通过监控指标进行动态参数调整

**收尾：** 关于这个问题，我还可以展开聊——线程池的队列为什么不用无界？您想从哪个角度深入？

## 视频脚本

> 预计时长：5 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：线程池如何调优？核心线程数、最大线程数、队列大小应该怎么设置 | 今天这道题：线程池如何调优？核心线程数、最大线程数、队列大小应该怎么设置。30 秒先给你讲清楚。 | 开场钩子 |
| 0:20 | 核心概念动画/示意图 | 线程池就像银行柜台：核心员工（核心线程）一直在办业务；人多了叫号排队（队列）；排满了雇临时工（最大线程）；挤爆了就保安拦人（拒绝策略）。 | 核心概念 |
| 0:40 | CPU 密集型设 N+1示意图 | CPU 密集型设 N+1，IO 密集型设 2N 或公式计算 | CPU 密集型设 N+1 |
| 1:10 | 拒绝 Executors示意图 | 拒绝 Executors，使用有界队列防止 OOM | 拒绝 Executors |
| 1:40 | 监控指标进行动态参数调整示意图 | 通过监控指标进行动态参数调整 | 监控指标进行动态参数调整 |
| 2:10 | 总结卡 + 下期预告 | 记住三个词就能答好这道题。下期追问：线程池的队列为什么不用无界？newFixedThreadPool 的坑是什么？ | 收尾 |
