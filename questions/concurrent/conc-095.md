---
id: conc-095
difficulty: L3
category: concurrent
feynman:
  essence: 控制多线程对共享资源的互斥访问机制。
  analogy: 就像厕所的锁，有人进去（加锁）就关上门，其他人只能在门口等。
  first_principle: 如何在多线程环境下保证同一时刻只有一个线程能访问临界区？
  key_points:
  - synchronized：JVM内置关键字，自动加锁解锁
  - ReentrantLock：JDK提供的类，需手动lock/unlock
  - 可重入性：同一线程可多次获取同一把锁
  - 公平性：支持公平锁与非公平锁策略
  - 高性能场景下优先选择ReentrantLock
  - synchronized自动管理，代码简洁
  - ReentrantLock功能丰富(中断、超时、公平)
  - Semaphore控制并发数量
memory_points:
- 核心对比：synchronized是JVM关键字自动释放锁，ReentrantLock是API层需手动释放。
- 特性差异：ReentrantLock支持公平锁、可中断(lockInterruptibly)及多条件变量。
- synchronized锁升级：无竞争偏向锁 -> 少竞争轻量级锁(CAS自旋) -> 高竞争重量级锁。
- 实战必记：ReentrantLock的unlock操作必须放在finally块中执行以防死锁。
- synchronized：JVM内置锁，自动释放。锁升级不可逆：偏向锁->轻量级锁(自旋)->重量级锁
- ReentrantLock：基于AQS，需手动unlock。支持响应中断、超时尝试、公平锁及多条件变量
- Semaphore：信号量，基于AQS共享模式，用于控制同时访问特定资源的并发线程数（限流）
- CAS乐观锁：基于硬件指令，无阻塞性能高，但存在ABA问题（可加版本号解决）
follow_up: []
tags: []
---

# 什么是种线程锁？

在 Java 中，锁机制主要用于解决多线程并发访问共享资源时的数据一致性问题。常见的锁主要分为 `synchronized` 关键字和 `java.util.concurrent.locks` 包下的 `Lock` 接口实现类（如 ReentrantLock）。

### 一、synchronized

#### 1. 基本概念
`synchronized` 是 Java 内置的关键字，基于 JVM 层面实现。它修饰的代码块或方法，在同一时刻最多只有一个线程能执行，保证了原子性和可见性。

#### 2. 实现原理与锁升级
`synchronized` 的实现基于对象的 **Monitor**（监视器锁）。在 JDK 1.6 之后，为了减少获得锁和释放锁带来的性能消耗，引入了**偏向锁、轻量级锁、重量级锁**，锁会随着竞争情况逐渐升级，但不能降级。

```text
锁升级流程（简化版）：

线程A访问同步块
     │
     ├─> 检查 Mark Word 中的 Thread ID
     │       │
     │       └─> 是 A 吗? ─(是)─> 偏向锁 (Biased Lock) (无竞争, 直接执行)
     │               │
     │              (否)
     │               │
     │               ▼
     ├─> 尝试获取轻量级锁 (CAS 替换 Mark Word)
     │       │
     │      (CAS 成功) ─> 轻量级锁 (Lightweight Lock) (当前线程持有)
     │       │
     │      (CAS 失败 - 存在竞争)
     │       │
     │       ▼
     ├─> 自旋锁
     │       │ (自旋一定次数仍未获取到锁)
     │       │
     │       ▼
     └─> 重量级锁 (Heavyweight Lock) (OS Mutex, 线程挂起/唤醒, 开销大)
```

#### 3. 特点
*   **自动加锁/解锁**：代码块执行完或抛出异常时，JVM 会自动释放锁，不易出现死锁（但也无法中断）。
*   **不可中断**：等待 `synchronized` 锁的线程无法被 `interrupt()` 中断，必须一直等到拿到锁。

### 二、ReentrantLock (可重入锁)

#### 1. 基本概念
`ReentrantLock` 是 JDK 提供的基于 AQS (AbstractQueuedSynchronizer) 实现的类，位于 `java.util.concurrent.locks` 包下。

#### 2. 核心特性
*   **可重入性**：同一个线程可以多次获取同一把锁，不会自己把自己锁死。
*   **可中断**：使用 `lockInterruptibly()` 可以在等待锁的过程中响应中断，解决死锁僵局。
*   **公平锁/非公平锁**：
    *   **公平锁**：严格按照请求锁的顺序来获取锁（性能较低）。
    *   **非公平锁**：允许插队，性能通常高于公平锁（默认是非公平锁）。
*   **支持超时**：`tryLock(time)` 可以在指定时间内尝试获取锁，超时则放弃。
*   **条件绑定**：支持多个 `Condition` 对象，可以精细控制线程的等待和唤醒分组（`synchronized` 只有隐式的一个 wait/notify）。

#### 3. 使用规范
使用 `ReentrantLock` 必须在 `finally` 块中手动释放锁 `unlock()`，否则可能导致死锁。

```java
ReentrantLock lock = new ReentrantLock();
try {
    lock.lock();
    // 业务逻辑
} finally {
    lock.unlock(); // 必须手动释放
}
```

### 三、总结对比

| 特性 | synchronized | ReentrantLock |
| :--- | :--- | :--- |
| **实现层面** | JVM 关键字，C++ 实现 | JDK API，Java 实现 (基于 AQS) |
| **释放锁** | 自动释放 | 必须 `finally` 手动释放 |
| **锁类型** | 非公平（不可配置） | 可配置公平/非公平 |
| **响应中断** | 不可中断 | 可中断 (`lockInterruptibly`) |
| **等待超时** | 不支持 | 支持 (`tryLock`) |
| **条件变量** | 单个 (`wait/notify`) | 多个 (`Condition`) |
| **性能** | JDK 1.6 后优化很好，两者差距不大 | 极高并发下略占优（自旋优化更多） |

---

## ## 常见考点
1.  **synchronized 的锁升级过程是怎样的？**
    *   回答要点：偏向锁（无竞争）-> 轻量级锁（CAS自旋）-> 重量级锁（OS互斥量）。目的是在无竞争和少竞争时减少内核态切换的开销。
2.  **ReentrantLock 和 synchronized 的区别？**
    *   回答要点：ReentrantLock 需手动释放锁，支持公平性选择、可中断、多条件变量，是 API 层面的；synchronized 是关键字，自动释放锁，更简单。
3.  **什么是 AQS (AbstractQueuedSynchronizer)？**
    *   回答要点：它是 Java 并发包中构建锁和同步器的基础框架（如 ReentrantLock, CountDownLatch 都是基于它实现的），核心是一个 volatile int state 变量和一个 CLH 队列。

## 记忆要点

- 核心对比：synchronized是JVM关键字自动释放锁，ReentrantLock是API层需手动释放。
- 特性差异：ReentrantLock支持公平锁、可中断(lockInterruptibly)及多条件变量。
- synchronized锁升级：无竞争偏向锁 -> 少竞争轻量级锁(CAS自旋) -> 高竞争重量级锁。
- 实战必记：ReentrantLock的unlock操作必须放在finally块中执行以防死锁。

## 结构化回答

**30 秒电梯演讲：** 就像厕所的锁，有人进去（加锁）就关上门，其他人只能在门口等。

**展开框架：**
1. **synchronized** — synchronized：JVM内置关键字，自动加锁解锁
2. **ReentrantLock** — ReentrantLock：JDK提供的类，需手动lock/unlock
3. **重入性** — 可重入性：同一线程可多次获取同一把锁

**收尾：** 这块我踩过一些坑，您想深入聊哪一段——原理细节、实战案例还是常见踩坑？

## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：什么是种线程锁 | 今天这道题：什么是种线程锁。30 秒先给你讲清楚。 | 开场钩子 |
| 0:20 | 核心概念动画/示意图 | 就像厕所的锁，有人进去（加锁）就关上门，其他人只能在门口等。 | 核心概念 |
| 0:40 | synchronized示意图 | synchronized：JVM内置关键字，自动加锁解锁 | synchronized |
| 1:10 | ReentrantLock示意图 | ReentrantLock：JDK提供的类，需手动lock/unlock | ReentrantLock |
| 1:40 | 总结卡 + 下期预告 | 记住今天这几个关键词，面试一定用得上。下期见。 | 收尾 |

---

## 延伸：什么是线程锁总结？

> 合并自 `conc-102`（相似度 73%）

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
