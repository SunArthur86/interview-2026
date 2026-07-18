---
id: conc-041
difficulty: L3
category: concurrent
feynman:
  essence: Latch是发令枪倒计时，Barrier是集合点，Semaphore是限流门卫。
  analogy: CountDownLatch像比赛发令（裁判等运动员）；CyclicBarrier像团建集合（人齐了才出发）；Semaphore像公厕（坑位有限，出来了才能进）。
  first_principle: 如何协调多个线程的执行顺序和并发数量？
  key_points:
  - CountDownLatch：一个或多个线程等待，计数归零唤醒，不可复用
  - CyclicBarrier：线程间相互等待，人齐执行，可复用
  - Semaphore：控制并发数，获取/释放许可
  - Latch用于任务汇总，Barrier用于并行协作
memory_points:
- CountDownLatch：一次性减法计数器，用于主线程等待 N 个子任务全部完成
- CyclicBarrier：可循环的同步屏障，用于一组线程互相等待至指定数量后齐发
- Semaphore：许可证限流器，用于控制同时访问特定资源的最大并发线程数
- 本质对比：前两者是等计数归零触发放行，而信号量是控制有限资源的并发抢占
---

# CyclicBarrier、CountDownLatch、Semaphore的区别和使用场景？

### 1. CountDownLatch（倒计时器）
- **功能**：允许一个或多个线程等待其他线程完成一组操作。
- **机制**：初始化设定计数器。线程调用 `await()` 阻塞，其他线程完成任务调用 `countDown()` 使计数减 1。当计数归零，所有阻塞线程被唤醒。
- **特点**：计数器只能用一次，不可重置。
- **场景**：应用程序启动（等待多个初始化服务完成）、并行计算汇总结果。

### 2. CyclicBarrier（回环栅栏）
- **功能**：让一组线程到达一个屏障（同步点）时被阻塞，直到最后一个线程到达，所有线程才同时继续执行。
- **机制**：线程调用 `await()` 表示已到达。所有线程都到达后，屏障打开，线程继续，并自动重置（可循环使用）。支持构造时传入 `Runnable` 在所有线程到达后执行。
- **特点**：可重复使用，侧重于线程间的相互等待。
- **场景**：多线程计算数据，最后合并结果（如 MapReduce）；多线程并发测试。

### 3. Semaphore（信号量）
- **功能**：控制同时访问特定资源的线程数量。
- **机制**：维护一组许可证。线程调用 `acquire()` 获取许可（若无则阻塞），使用完调用 `release()` 归还许可。
- **特点**：限流。
- **场景**：数据库连接池（限制连接数）、限制系统并发访问流量。

### 4. 边界情况
- **CountDownLatch**：如果 `await()` 线程被中断，会抛出 `InterruptedException`；计数器归零后，后续调用 `await()` 会立即返回，`countDown()` 调用无效。
- **CyclicBarrier**：如果某个调用 `await()` 的线程被中断或超时，屏障会被破坏（BrokenBarrierException），其他等待线程会收到该异常，无法重用，除非重置。
- **Semaphore**：`release()` 可以在 `acquire()` 之前调用，甚至可以增加超过初始值的许可数（需谨慎），可能导致并发量失控。

### 5. 架构/状态对比图

```text
+---------------------+     +-----------------------+     +----------------------+
|   CountDownLatch     |     |     CyclicBarrier      |     |     Semaphore         |
+---------------------+     +-----------------------+     +----------------------+
| One-shot (一次性)   |     | Reusable (可循环)      |     | Reusable (可循环)     |
|                     |     |                       |     |                      |
| [Main Thread]       |     | [Worker 1] [Worker 2] |     | [Resource Pool]       |
|      |              |     |      |         |       |     |   Permits: N          |
| await()             |     |   await()   await()   |     |                      |
|      x--------------x-----x---x---------x-------x     | acquire() <-- release()
|                     |     |   Barrier Action      |     |         |              |
| countDown() by      |     | (optional)            |     |         v              |
| Worker Threads      |     |                       |     |     Blocking          |
+---------------------+     +-----------------------+     +----------------------+
```

### 6. 实战与深化

- **实战案例**：在一个微服务多数据源初始化场景中，主线程使用 `CountDownLatch` 等待 5 个数据源连接健康检查完成；而在多线程报表导出中，每个线程处理 1/10 数据量后使用 `CyclicBarrier` 屏障等待，所有线程完成后由最后一个线程触发 Excel 文件合并上传。
- **代码示例**：
```java
// CyclicBarrier: 3个线程到达屏障后执行合并动作
CyclicBarrier barrier = new CyclicBarrier(3, () -> {
    System.out.println("所有子任务完成，执行合并逻辑...");
});

// Semaphore: 模拟限流，只允许 5 个并发下载
Semaphore semaphore = new Semaphore(5);
if (semaphore.tryAcquire()) { // 非阻塞尝试获取
    try {
        download();
    } finally {
        semaphore.release();
    }
}
```

## 面试追问
1. CountDownLatch 的计数器能否被重置？如果需要重置，有没有替代方案？
2. 使用 CyclicBarrier 时，如果其中一个线程在 `await()` 处挂掉（或抛出异常），其他线程会怎样？如何处理这种异常场景？
3. Semaphore 的公平锁（Fair）和非公平锁模式有什么区别？在高并发场景下如何选择？

## 易错点
1. **混淆 CountDownLatch 和 CyclicBarrier**：前者是外部线程等待内部线程完成（如裁判等运动员），后者是线程之间互相等待（如运动员互相等齐再出发）。
2. **忘记释放 Semaphore 许可**：如果在 `acquire()` 后的业务逻辑中抛出异常且未在 `finally` 中 `release()`，会导致许可证泄漏，最终导致线程池“假死”。


## 记忆要点

- CountDownLatch：一次性减法计数器，用于主线程等待 N 个子任务全部完成
- CyclicBarrier：可循环的同步屏障，用于一组线程互相等待至指定数量后齐发
- Semaphore：许可证限流器，用于控制同时访问特定资源的最大并发线程数
- 本质对比：前两者是等计数归零触发放行，而信号量是控制有限资源的并发抢占

## 结构化回答

**30 秒电梯演讲：** CountDownLatch像比赛发令（裁判等运动员）；CyclicBarrier像团建集合（人齐了才出发）；Semaphore像公厕（坑位有限，出来了才能进）。

**展开框架：**
1. **CountDownLatch** — CountDownLatch：一个或多个线程等待，计数归零唤醒，不可复用
2. **CyclicBarrier** — CyclicBarrier：线程间相互等待，人齐执行，可复用
3. **Semaphore** — Semaphore：控制并发数，获取/释放许可

**收尾：** 这块我踩过一些坑，您想深入聊哪一段——原理细节、实战案例还是常见踩坑？

## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：CyclicBarrier、CountDownLatch、Semaphore的区别和使用场景 | 今天这道题：CyclicBarrier、CountDownLatch、Semaphore的区别和使用场景。30 秒先给你讲清楚。 | 开场钩子 |
| 0:20 | 核心概念动画/示意图 | CountDownLatch像比赛发令（裁判等运动员）；CyclicBarrier像团建集合（人齐了才出发）；Semaphore像公厕（坑位有限，出来了才能进）。 | 核心概念 |
| 0:40 | CountDownLatch示意图 | CountDownLatch：一个或多个线程等待，计数归零唤醒，不可复用 | CountDownLatch |
| 1:10 | CyclicBarrier示意图 | CyclicBarrier：线程间相互等待，人齐执行，可复用 | CyclicBarrier |
| 1:40 | 总结卡 + 下期预告 | 记住今天这几个关键词，面试一定用得上。下期见。 | 收尾 |
