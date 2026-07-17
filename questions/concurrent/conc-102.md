---
id: conc-102
difficulty: L3
category: concurrent
feynman:
  essence: 控制多线程并发访问共享资源的同步机制。
  analogy: 厕所门锁：synchronized是自动门，ReentrantLock是手动锁，Semaphore是限流闸机。
  first_principle: 如何在多线程环境下保证数据的一致性和安全性？
  key_points:
  - synchronized自动管理，代码简洁
  - ReentrantLock功能丰富(中断、超时、公平)
  - Semaphore控制并发数量
  - AtomicInteger利用CAS实现高性能无锁
memory_points:
- synchronized：JVM内置锁，自动释放。锁升级不可逆：偏向锁->轻量级锁(自旋)->重量级锁
- ReentrantLock：基于AQS，需手动unlock。支持响应中断、超时尝试、公平锁及多条件变量
- Semaphore：信号量，基于AQS共享模式，用于控制同时访问特定资源的并发线程数（限流）
- CAS乐观锁：基于硬件指令，无阻塞性能高，但存在ABA问题（可加版本号解决）
- 选型口诀：限流选Semaphore，简单计数选Atomic，高级特性选Reentrant，其余选synchronized
---

# 什么是线程锁总结？

### 线程锁总结

**1. synchronized (内置锁)**
- **特点**：Java 语言内置的关键字，基于对象的 Monitor 实现。JVM 负责加锁和解锁，代码简洁，自动释放锁。
- **实现原理**：
  - 对象头中的 Mark Word 存储锁状态（无锁、偏向锁、轻量级锁、重量级锁）。
  - 随着竞争加剧，锁会升级：偏向锁 -> 轻量级锁（自旋锁） -> 重量级锁（内核态互斥量）。锁升级不可逆。
- **适用场景**：资源竞争不激烈，代码块逻辑简单，不需要高级特性。
- **缺点**：
  - 不可中断，等待锁的线程无法响应中断。
  - 不支持超时获取锁。
  - 无法实现公平锁（非公平锁）。

**2. ReentrantLock (可重入锁)**
- **特点**：基于 JDK (`java.util.concurrent.locks` 包) 实现，依赖于 AQS (`AbstractQueuedSynchronizer`)。
- **优势**：
  - **可中断**：支持 `lockInterruptibly()`，等待锁的线程可以响应中断。
  - **支持超时**：`tryLock(time)` 可在指定时间内尝试获取锁，非阻塞或超时返回。
  - **公平性选择**：构造函数可传入 `true` 实现公平锁（按请求顺序获取），默认为非公平锁（性能更高）。
  - **多条件变量**：支持绑定多个 `Condition` 对象，可以精细控制线程等待和唤醒（分组唤醒），比 `wait/notify` 更灵活。
- **使用注意**：必须手动在 `finally` 块中调用 `unlock()` 释放锁，否则可能导致死锁。
- **性能**：在 JDK 1.6 之后，synchronized 性能大幅优化。低竞争下两者差距小，高激烈竞争下 ReentrantLock 因支持中断和自选策略通常表现更稳定。

**3. Semaphore (信号量)**
- **特点**：用于控制同时访问特定资源的线程数量。本质上是一个计数器，通过 AQS 共享模式实现。
- **核心方法**：
  - `acquire()`：获取一个许可，若无许可则阻塞，直到有许可或线程被中断。
  - `release()`：释放一个许可，唤醒阻塞线程。
- **适用场景**：限流（如数据库连接池）、资源池管理。
- **注意**：需在 `finally` 中释放，且 `acquire` 和 `release` 必须成对出现，否则会导致信号量泄露。

**4. AtomicInteger (原子类)**
- **特点**：基于 CAS (Compare And Swap) 硬件指令实现的原子操作类，属于乐观锁机制。
- **实现原理**：
  - 利用 `Unsafe` 类直接操作内存。
  - 核心方法 `compareAndSwapInt(expected, update)`：如果内存值等于预期值，则更新为新值，否则重试（自旋）。
- **适用场景**：高并发下的计数器、序列号生成等简单原子操作。
- **优势**：无锁，不会导致线程上下文切换，性能通常远高于 `ReentrantLock` 或 `synchronized`。
- **局限**：
  - 只能保证单个共享变量的原子性。
  - ABA 问题（通过版本号解决，如 `AtomicStampedReference`）。
  - 高并发下自旋失败会消耗大量 CPU 资源。

**锁机制对比选择流程图：**
```
         [开始]
            |
            v
     +------+------+
     | 是否需要控制 |
     | 并发访问数量? |
     +------+------+
       | Yes        | No
       v            v
   [Semaphore] +---+--------------+
               | 是否是简单计数? |
               +---+--------------+
                  | Yes           | No
                  v               v
           [AtomicInteger] +------+------+
                           | 需要高级特性? |
                           | (中断/公平/多Condition) |
                           +------+------+
                              | Yes      | No
                              v          v
                        [ReentrantLock] [synchronized]
```

## 常见考点
1. **synchronized 的锁升级过程？**
   无锁 -> 偏向锁（线程ID重偏向） -> 轻量级锁（CAS自旋替换MarkWord到栈锁记录） -> 重量级锁（膨胀为Monitor，用户态->内核态）。
2. **ReentrantLock 的公平锁和非公平锁的实现区别？**
   非公平锁在获取锁时直接尝试 CAS 抢占，失败再加入队列；公平锁在获取锁时先检查队列中是否有前驱节点，有则排队。
3. **CAS 的 ABA 问题及解决方案？**
   问题：变量值从 A 变为 B 又变回 A，CAS 无法感知。解决：加版本号或时间戳（`AtomicStampedReference`）。

## 记忆要点

- synchronized：JVM内置锁，自动释放。锁升级不可逆：偏向锁->轻量级锁(自旋)->重量级锁
- ReentrantLock：基于AQS，需手动unlock。支持响应中断、超时尝试、公平锁及多条件变量
- Semaphore：信号量，基于AQS共享模式，用于控制同时访问特定资源的并发线程数（限流）
- CAS乐观锁：基于硬件指令，无阻塞性能高，但存在ABA问题（可加版本号解决）
- 选型口诀：限流选Semaphore，简单计数选Atomic，高级特性选Reentrant，其余选synchronized

## 结构化回答


**30 秒电梯演讲：** 厕所门锁：synchronized是自动门，ReentrantLock是手动锁，Semaphore是限流闸机。

**展开框架：**
1. **synchronized自…** — synchronized自动管理，代码简洁
2. **Reentran** — tLock功能丰富(中断、超时、公平)
3. **Semaphor** — Semaphore控制并发数量

**收尾：** 这是我实战中的理解，您想深入哪一段？


## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：什么是线程锁总结 | 今天这道题：什么是线程锁总结。30 秒先给你讲清楚。 | 开场钩子 |
| 0:20 | 核心概念动画/示意图 | 厕所门锁：synchronized是自动门，ReentrantLock是手动锁，Semaphore是限流闸机。 | 核心概念 |
| 0:40 | synchronized自动示意图 | synchronized自动管理，代码简洁 | synchronized自动 |
| 1:10 | ReentrantLock示意图 | ReentrantLock功能丰富(中断、超时、公平) | ReentrantLock |
| 1:40 | 总结卡 + 下期预告 | 记住今天这几个关键词，面试一定用得上。下期见。 | 收尾 |
