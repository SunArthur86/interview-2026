---
id: conc-140
difficulty: L3
category: concurrent
subcategory: 锁
tags:
- ReentrantLock
- synchronized
- 对比
feynman:
  essence: ReentrantLock是synchronized的可定制化升级版，主打灵活控制。
  analogy: synchronized像自动挡汽车，简单省心但控制少；ReentrantLock像手动挡赛车，操作繁琐但能漂移、抢跑、精确控制引擎。
  first_principle: 如何在保证线程安全的前提下，对锁的获取、释放和等待机制进行更精细的底层控制？
  key_points:
  - synchronized简单自动，JDK1.6后性能已优化
  - ReentrantLock支持中断、超时、公平锁、多条件变量
  - 用ReentrantLock必须手动在finally中释放锁
follow_up:
- ReentrantLock 的公平锁为什么比非公平锁慢？性能差多少？
- 多个 Condition 如何实现生产者-消费者模型？
- ReentrantLock 和 ReadWriteLock/StampedLock 有什么区别？
memory_points:
- 对比 synchronized：ReentrantLock 基于 AQS，支持可中断、可超时、公平锁及多条件变量。
- 因为 tryLock 可设超时或非阻塞获取，所以适合防范死锁或实现轮询尝试。
- 因为 newCondition 能精细分组等待唤醒，所以适合复杂的生产者消费者模型。
- 注意区别：thenApply 同步转换，而 thenApplyAsync 异步转换。
- 必须牢记：必须在 finally 块中调用 unlock()，避免死锁。
---

# ReentrantLock 相比 synchronized 多了哪些高级功能？什么场景该用 ReentrantLock？

【synchronized：简单够用】
- **关键字**：JVM 层面实现，C++ 编写，内置锁。
- **自动管理**：加锁、解锁由 JVM 自动控制（基于字节码 `monitorenter`/`monitorexit` 或方法常量池标志），不会发生死锁（代码执行完或异常自动释放）。
- **优化**：JDK 1.6 后引入偏向锁、轻量级锁、重量级锁锁升级，减少 OS 悬挂开销。
- **限制**：非公平锁，不可中断，不可设置超时，只有一个条件队列（等待集）。

【ReentrantLock 多出的 4 大功能】
1. **可中断锁**：
   - `lockInterruptibly()`：允许线程在等待锁时响应 `interrupt()` 中断信号，抛出 `InterruptedException` 退出等待。
   - *场景*：用于消除死锁，两个线程互相等待时，外部中断其中一个使其释放锁。
2. **可超时锁**：
   - `tryLock(long time, TimeUnit unit)`：给定时间内获取不到锁则返回 false，不会无限阻塞。
   - *场景*：避免死锁，或者用于轮询尝试获取资源。
3. **公平锁选择**：
   - 构造函数 `new ReentrantLock(true)` 启用公平模式。
   - *原理*：基于 AQS 的 `CLH` 队列，严格按照请求顺序（FIFO）获取锁，避免线程饥饿。
   - *代价*：维护队列开销大，吞吐量通常低于非公平锁。
4. **多条件变量**：
   - `newCondition()`：创建多个 `Condition` 对象。
   - *场景*：生产者/消费者模型。用 `notFull` 等待队列不满，用 `notEmpty` 等待队列不空，比 `synchronized` 的 `wait/notify` 更精细（`notifyAll` 唤醒所有线程效率低）。

【额外功能】
- **非阻塞获取**：`tryLock()` 立即返回，获取不到直接失败，不阻塞线程。
- **锁状态查询**：
  - `isLocked()`：锁是否被持有。
  - `isHeldByCurrentThread()`：当前线程是否持有锁。
  - `getHoldCount()`：当前线程重入获取锁的次数。
  - `getQueueLength()`：正在等待获取此锁的线程估计数。

【实战案例】
在实现一个分布式锁客户端时，需要获取 Redis 锁并在本地执行业务。由于网络抖动导致锁获取时间不确定，使用 `synchronized` 可能会导致主线程长时间阻塞。改用 `ReentrantLock.tryLock(3, TimeUnit.SECONDS)`，若 3 秒内无法获取本地执行权限则直接返回失败，极大提升了系统的容错性和响应能力。

【代码示例】
```java
ReentrantLock lock = new ReentrantLock(true); // 公平锁
if (lock.tryLock(1, TimeUnit.SECONDS)) {
    try {
        // 业务逻辑
    } finally {
        lock.unlock();
    }
} else {
    // 获取锁超时处理
    log.warn("Failed to acquire lock, timeout");
}

// 多条件变量示例
Condition notEmpty = lock.newCondition();
Condition notFull = lock.newCondition();
```

【架构对比（AQS vs Monitor）】
```text
ReentrantLock 基于实现 (AQS)
┌─────────────────────┐
│   State (int: 0/1)  │ <--- volatile state 变量 (CAS 修改)
├─────────────────────┤
│  CLH Queue (Node)   │ <--- 等待队列 (双向链表)
├─────────────────────┤
│ ConditionObject[]   │ <--- 多个条件队列
└─────────────────────┘

synchronized 基于实现
┌─────────────────────┐
│    Object Monitor   │ <--- C++ ObjectMonitor
├─────────────────────┤
│ _EntryList (CXQ)    │ <--- 竞争队列
├─────────────────────┤
│  _WaitSet           │ <--- 调用 wait() 的线程集合
└─────────────────────┘
```

【选型建议】
- **默认 synchronized**：代码简洁，JVM 自动管理，JVM 锁优化极佳。
- **使用 ReentrantLock 的场景**：
  - 需要使用 `tryLock` 避免死锁或实现轮询锁。
  - 需要公平锁机制以保证业务顺序。
  - 需要精细化控制多组线程等待/唤醒（多 Condition）。
  - 需要中断正在等待锁的线程。

【注意】`ReentrantLock` 必须在 `finally` 块中调用 `unlock()`，且加锁解锁次数必须对应，否则会导致死锁或逻辑错误。

## 记忆要点

- 对比 synchronized：ReentrantLock 基于 AQS，支持可中断、可超时、公平锁及多条件变量。
- 因为 tryLock 可设超时或非阻塞获取，所以适合防范死锁或实现轮询尝试。
- 因为 newCondition 能精细分组等待唤醒，所以适合复杂的生产者消费者模型。
- 注意区别：thenApply 同步转换，而 thenApplyAsync 异步转换。
- 必须牢记：必须在 finally 块中调用 unlock()，避免死锁。

## 结构化回答

**30 秒电梯演讲：** synchronized像自动挡汽车，简单省心但控制少；ReentrantLock像手动挡赛车，操作繁琐但能漂移、抢跑、精确控制引擎。

**展开框架：**
1. **synchronized** — synchronized简单自动，JDK1.6后性能已优化
2. **ReentrantLock** — ReentrantLock支持中断、超时、公平锁、多条件变量
3. **用ReentrantLock** — 用ReentrantLock必须手动在finally中释放锁

**收尾：** 关于这个问题，我还可以展开聊——ReentrantLock 的公平锁为什么比非公平锁慢？您想从哪个角度深入？

## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：ReentrantLock 相比 synchronized 多了哪些高级功能？什么场景该用 ReentrantLock | 今天这道题：ReentrantLock 相比 synchronized 多了哪些高级功能？什么场景该用 ReentrantLock。30 秒先给你讲清楚。 | 开场钩子 |
| 0:20 | 核心概念动画/示意图 | synchronized像自动挡汽车，简单省心但控制少；ReentrantLock像手动挡赛车，操作繁琐但能漂移、抢跑、精确控制引擎。 | 核心概念 |
| 0:40 | synchronized示意图 | synchronized简单自动，JDK1.6后性能已优化 | synchronized |
| 1:10 | ReentrantLock示意图 | ReentrantLock支持中断、超时、公平锁、多条件变量 | ReentrantLock |
| 1:40 | 总结卡 + 下期预告 | 记住三个词就能答好这道题。下期追问：ReentrantLock 的公平锁为什么比非公平锁慢？性能差多少？ | 收尾 |
