---
id: conc-063
difficulty: L3
category: concurrent
feynman:
  essence: synchronized是JVM内置锁，ReentrantLock是JDK实现的灵活API锁。
  analogy: synchronized是自动挡（自动开关），ReentrantLock是手动挡（手动控制，功能多）。
  first_principle: 如何提供更灵活的并发控制手段？
  key_points:
  - synchronized自动释放，ReentrantLock手动释放
  - ReentrantLock支持公平锁和中断等待
  - ReentrantLock支持多个Condition精细控制
memory_points:
- 实现层面：Synchronized 是 JVM 关键字自动释放，ReentrantLock 是 JDK API 需手动 unlock。
- 高级特性：ReentrantLock 支持公平锁、可中断、多条件变量。
- 条件变量对比：Synchronized 只有一个 WaitSet 随机唤醒，而 ReentrantLock 可绑定多个 Condition 精确唤醒。
- 核心依赖：ReentrantLock 底层基于 AQS 实现，通过 state 变量记录重入次数。
---

# synchronized和ReentrantLock的区别？

**synchronized 和 ReentrantLock 的区别**

**相同点：**
1. 都是用于协调多线程对共享资源的访问，保证线程安全。
2. 都是可重入锁（同一个线程可以多次获取同一把锁，避免死锁）。
3. 都保证了可见性和互斥性（基于 JMM 的 Happens-Before 原则）。

**不同点：**

| 特性 | synchronized | ReentrantLock |
| :--- | :--- | :--- |
| **实现层面** | JVM 层面，基于关键字，由 JVM 实现。 | JDK API 层面，基于 AQS (AbstractQueuedSynchronizer) 实现。 |
| **释放锁方式** | 自动释放锁（代码执行完或异常）。 | 必须在 `finally` 块中手动调用 `unlock()` 释放，否则可能导致死锁。 |
| **公平性** | 非公平锁。 | 可选，默认非公平，构造方法传入 `true` 可构造公平锁。 |
| **等待可中断** | 不可中断，死等（除非抛出异常或执行完毕）。 | 支持中断等待（`lockInterruptibly`），解决死锁更灵活。 |
| **绑定条件** | 只有一个 WaitSet，随机唤醒一个或全部 (`notify/notifyAll`)。 | 支持多个 `Condition`，可以精细控制唤醒特定线程（生产/消费模型常用）。 |
| **性能** | JDK 1.6 后优化极大（锁升级、偏向锁），性能与 ReentrantLock 持平。 | 在高竞争或复杂场景（如定时锁、轮询锁）下仍具一定优势。 |

**### 1. 实战案例**
在实现一个简单的阻塞队列时，如果使用 `synchronized`，我们无法区分“队列为空等待”和“队列已满等待”的线程，`notify` 可能会错误地唤醒空队列上的生产者。使用 `ReentrantLock` 配合两个 `Condition`（`notFull` 和 `notEmpty`），可以精确控制唤醒生产者或消费者，大大提高了调度效率。

**### 2. 代码示例**
```java
ReentrantLock lock = new ReentrantLock();
Condition notEmpty = lock.newCondition();
Condition notFull = lock.newCondition();

public void put(Object item) throws InterruptedException {
    lock.lock();
    try {
        while (count == items.length)
            notFull.await(); // 队列满，阻塞在 notFull 条件上
        items[putIndex] = item;
        notEmpty.signal(); // 唤醒消费者
    } finally {
        lock.unlock();
    }
}
```

**## 常见考点**
1. **AQS 原理简述**：ReentrantLock 是如何利用 AQS 的？（通过 state 变量（0 表示无锁，>0 表示重入次数）和 CLH 双向队列管理等待线程）。
2. **tryLock 与 lock**：tryLock 有什么用？（tryLock 会尝试获取锁，获取不到立即返回 false，不会阻塞，可用于避免死锁或轮询）。
3. **Condition 的实现**：Condition 的 await/signal 和 Object 的 wait/notify 有什么本质区别？（Condition 可以支持多路通知，更灵活；且必须持有对应的 Lock 才能调用）。
4. **选择建议**：一般如果没有特殊需求（如公平性、中断等），推荐使用 synchronized（写法简单，JVM 自动优化）。
5. **ReentrantLock 的可重入实现**：线程再次获取锁时，CAS 增加 state 变量的值；释放锁时，state 减为 0 才真正释放锁。

## 记忆要点

- 实现层面：Synchronized 是 JVM 关键字自动释放，ReentrantLock 是 JDK API 需手动 unlock。
- 高级特性：ReentrantLock 支持公平锁、可中断、多条件变量。
- 条件变量对比：Synchronized 只有一个 WaitSet 随机唤醒，而 ReentrantLock 可绑定多个 Condition 精确唤醒。
- 核心依赖：ReentrantLock 底层基于 AQS 实现，通过 state 变量记录重入次数。

## 结构化回答

**30 秒电梯演讲：** synchronized是自动挡（自动开关），ReentrantLock是手动挡（手动控制，功能多）。

**展开框架：**
1. **synchronized** — synchronized自动释放，ReentrantLock手动释放
2. **ReentrantLock** — ReentrantLock支持公平锁和中断等待
3. **ReentrantLock** — ReentrantLock支持多个Condition精细控制

**收尾：** 这块我踩过一些坑，您想深入聊哪一段——原理细节、实战案例还是常见踩坑？

## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：synchronized和ReentrantLock的区别 | 今天这道题：synchronized和ReentrantLock的区别。30 秒先给你讲清楚。 | 开场钩子 |
| 0:20 | 核心概念动画/示意图 | synchronized是自动挡（自动开关），ReentrantLock是手动挡（手动控制，功能多）。 | 核心概念 |
| 0:40 | synchronized示意图 | synchronized自动释放，ReentrantLock手动释放 | synchronized |
| 1:10 | ReentrantLock示意图 | ReentrantLock支持公平锁和中断等待 | ReentrantLock |
| 1:40 | 总结卡 + 下期预告 | 记住今天这几个关键词，面试一定用得上。下期见。 | 收尾 |
