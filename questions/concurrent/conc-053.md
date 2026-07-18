---
id: conc-053
difficulty: L3
category: concurrent
feynman:
  essence: 基于AQS（队列同步器）利用CAS和状态变量控制并发。
  analogy: 像排队办业务，非公平是直接插队看运气，公平是严格按先来后到。
  first_principle: 如何高效管理锁的获取、释放以及等待线程的排队？
  key_points:
  - 核心依赖AQS，维护state状态和CLH等待队列。
  - 加锁失败则入队阻塞，释放锁则唤醒头节点。
  - 支持公平与非公平策略选择。
memory_points:
- 核心骨架：ReentrantLock基于AQS实现，核心是volatile int state和CLH双向队列
- 加锁流程：CAS改state(0变1)成功则获锁，失败入队并LockSupport.park阻塞
- 重入机制：判断当前线程是否持锁，若是则state加1，释放时减至0才唤醒后继节点
- 公平差异：非公平锁直接CAS抢占，而公平锁先检查队列前驱(遵循FIFO)
---

# ReentrantLock的实现原理是什么？

### ReentrantLock 实现原理

#### 1. 基础
`ReentrantLock` 基于 **AQS (AbstractQueuedSynchronizer)** 实现。它内部维护了一个 `Sync` 抽象类（继承自 AQS），并派生出 `NonfairSync`（非公平锁）和 `FairSync`（公平锁）。

#### 2. 核心机制 (AQS)
AQS 核心是一个 **volatile int state** 变量（表示锁状态，0表示空闲，>=1表示被重入占用）和一个 **CLH 队列**（双向链表，管理阻塞等待的线程）。

#### 3. 加锁流程
*   线程尝试通过 CAS 修改 `state` 从 0 -> 1。如果成功，获得锁，并设置 `exclusiveOwnerThread` 为当前线程。
*   如果失败，判断当前线程是否已持有锁（可重入）。若是，`state + 1`。
*   若非重入且未获取到锁，当前线程被封装为 Node 加入 AQS 的 CLH 队列尾部，并阻塞（`LockSupport.park`）。

#### 4. 解锁流程
*   线程尝试修改 `state`（减 1）。
*   若 `state` 减为 0，表示锁完全释放，清空 `exclusiveOwnerThread`。
*   释放后，唤醒 CLH 队列中的下一个节点线程（`LockSupport.unpark`）。

#### 5. AQS 架构图
```text
       ReentrantLock
            │
            ▼
      ┌───────────────┐
      │  Sync (AQS)   │
      └───────┬───────┘
              │ state (volatile int)
              ▼
      ┌───────────────┐      ┌───────────────────┐
      │   Head Node   │ <─── │  Tail Node (New)  │
      │ (dummy/virtual)│      │   (Thread A)      │
      └───────────────┘      └───────────────────┘
              ▲                       │
              │                       ▼
              │                 Waiting...
      ┌───────┴───────┐
      │  Condition   │ (等待通知机制)
      └───────────────┘
```

#### 6. 公平性选择
*   **非公平锁**：获取锁时直接抢占（CAS），不检查队列中是否有等待线程（默认，性能高，减少上下文切换）。
*   **公平锁**：获取锁时先检查 `hasQueuedPredecessors()`（队列是否有前驱节点），严格遵循 FIFO（性能略低，避免线程饥饿）。

#### ## 常见考点
1.  **公平锁与非公平锁的实现代码差异**：非公平锁在 `lock` 时会先尝试 CAS 抢占一次，失败了才走 `acquire` 逻辑；公平锁直接调用 `acquire`。
2.  **AQS 的 `state` 含义**：在 ReentrantLock 中表示重入次数；在 CountdownLatch 中表示计数器；在 Semaphore 中表示剩余许可数。
3.  **Condition 实现原理**：AQS 内部维护了一个 ConditionObject，也是单向链表，配合 `await/signal` 实现线程间协作。

#### 实战案例
在实现一个简单的分布式锁客户端时，曾遇到因为业务异常导致 `lock()` 后未执行 `unlock()`，最终死锁的坑。**最佳实践**是必须在 `try...finally` 代码块中释放锁，且使用 `lock.isHeldByCurrentThread()` 进行防御性检查，防止出现嵌套锁调用时意外释放外部锁。

#### 代码示例
```java
ReentrantLock lock = new ReentrantLock(true); // true 表示公平锁

lock.lock();
try {
    // 1. 检查重入情况（调试用）
    // System.out.println("Hold count: " + lock.getHoldCount());
    
    // 2. 业务逻辑
    criticalSection();
} finally {
    // 3. 即使发生异常也必须释放
    // 只有持有锁的线程才能解锁，避免非法监视器状态异常
    if (lock.isHeldByCurrentThread()) {
        lock.unlock();
    }
}
```

#### 对比表格
| 维度 | ReentrantLock | Synchronized |
| :--- | :--- | :--- |
| **实现方式** | 基于 AQS (API 层面) | 基于 JVM Monitor (字节码层面) |
| **锁释放** | 必须手动在 `finally` 中释放 | 自动释放 (代码块执行完或异常) |
| **公平性** | 支持公平/非公平可选 | 仅支持非公平锁 |
| **等待中断** | `lockInterruptibly()` 支持响应中断 | 不可中断，必须等待锁释放 |
| **条件变量** | 支持多个 `Condition` (精细唤醒) | 仅一个 (wait/notify) |
| **性能** | JDK 6 后优化好，竞争激烈时更有优势 | JDK 6 后优化极好 (锁升级)，普通场景推荐 |


## 记忆要点

- 核心骨架：ReentrantLock基于AQS实现，核心是volatile int state和CLH双向队列
- 加锁流程：CAS改state(0变1)成功则获锁，失败入队并LockSupport.park阻塞
- 重入机制：判断当前线程是否持锁，若是则state加1，释放时减至0才唤醒后继节点
- 公平差异：非公平锁直接CAS抢占，而公平锁先检查队列前驱(遵循FIFO)

## 结构化回答


**30 秒电梯演讲：** 像排队办业务，非公平是直接插队看运气，公平是严格按先来后到。

**展开框架：**
1. **核心依赖AQS** — 维护state状态和CLH等待队列。
2. **加锁失败则入队阻塞** — 释放锁则唤醒头节点。
3. **支持公平与非公平** — 支持公平与非公平策略选择。

**收尾：** 这是我实战中的理解，您想深入哪一段？


## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：ReentrantLock的实现原理是什么 | 今天这道题：ReentrantLock的实现原理是什么。30 秒先给你讲清楚。 | 开场钩子 |
| 0:20 | 核心概念动画/示意图 | 像排队办业务，非公平是直接插队看运气，公平是严格按先来后到。 | 核心概念 |
| 0:40 | 核心依赖AQS示意图 | 核心依赖AQS，维护state状态和CLH等待队列。 | 核心依赖AQS |
| 1:10 | 加锁失败则入队阻塞示意图 | 加锁失败则入队阻塞，释放锁则唤醒头节点。 | 加锁失败则入队阻塞 |
| 1:40 | 总结卡 + 下期预告 | 记住今天这几个关键词，面试一定用得上。下期见。 | 收尾 |
