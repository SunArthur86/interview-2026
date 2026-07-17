---
id: conc-066
difficulty: L3
category: concurrent
feynman:
  essence: 基于状态变量和CLH队列的同步器框架。
  analogy: 就像办证大厅的叫号系统，管排队(CLH队列)和当前办理人数(state)，具体业务由自定义窗口实现。
  first_principle: 如何标准化线程阻塞、排队和唤醒的底层逻辑？
  key_points:
  - 通过volatile int state管理资源状态
  - 使用CLH队列管理阻塞线程
  - 支持独占和共享两种资源获取模式
memory_points:
- 核心定义：JUC下构建锁和同步器的基础框架，如ReentrantLock和Semaphore均基于此。
- 双核心机制：volatile int state（配合CAS修改） + CLH变种双向等待队列。
- 两大模式：独占模式（如ReentrantLock）与共享模式（如Semaphore、CountDownLatch）。
- 模板方法设计：子类仅需重写tryAcquire/tryRelease管理state，入队与阻塞交由AQS负责。
---

# 什么是 AQS（抽象的队列同步器）？

**AQS (AbstractQueuedSynchronizer)**

AQS 是 JDK 提供的一个用来构建锁和同步器的框架。它位于 `java.util.concurrent.locks` 包下，许多 JUC 并发包中的类（如 `ReentrantLock`、`Semaphore`、`CountDownLatch`）都是基于 AQS 实现的。

**核心原理：**

1. **State 变量（同步状态）**
   - AQS 内部维护一个 `volatile int state` 变量，表示同步状态（如锁被重入的次数、剩余的信号量个数）。
   - **关键细节**：提供了 `getState`、`setState` 和 `compareAndSetState` (CAS) 方法进行修改。CAS 保证了修改 state 的原子性。

2. **CLH 队列（双向链表）**
   - AQS 内部维护了一个 FIFO（先进先出）的双向队列（CLH 变体）。
   - **节点结构**：`Node` 包含 `waitStatus`（状态：CANCELLED, SIGNAL, CONDITION, PROPAGATE）、`prev`、`next` 和 `thread`。
   - **流程**：多线程争抢资源失败时，会被封装成 Node 节点加入队列尾部阻塞。
   - **头节点**：通常表示当前持有锁的线程（或虚节点）。释放锁时，头节点唤醒后继节点。

3. **资源共享模式**
   - **独占模式**：一次只能一个线程持有资源（如 `ReentrantLock`）。需实现 `tryAcquire` 和 `tryRelease`。
   - **共享模式**：多个线程可同时持有资源（如 `Semaphore`、`CountDownLatch`）。需实现 `tryAcquireShared` 和 `tryReleaseShared`。

**## 实战案例**
在一个高性能网关项目中，我们需要实现一个限流器。直接使用 AQS 的共享模式自定义同步器，控制并发访问数。相比直接使用 `Semaphore`，自定义实现允许我们在获取许可失败时记录更详细的拦截日志，并集成到监控系统中，这是对 AQS 灵活性的典型应用。

**## 代码示例**
```java
// 基于 AQS 实现一个简单的互斥锁（非公平）
class MyLock implements Lock {
    private static class Sync extends AbstractQueuedSynchronizer {
        protected boolean tryAcquire(int acquires) {
            return compareAndSetState(0, 1); // CAS 尝试将 0 改为 1
        }
        protected boolean tryRelease(int releases) {
            setState(0);
            return true;
        }
    }
    private final Sync sync = new Sync();
    public void lock() { sync.acquire(1); }
    public void unlock() { sync.release(1); }
    // ... 其他接口实现
}
```

**## 对比表格**
| 特性 | 独占模式 | 共享模式 |
| :--- | :--- | :--- |
| **核心方法** | tryAcquire / tryRelease | tryAcquireShared / tryReleaseShared |
| **资源占用** | 同一时刻仅一个线程 | 同一时刻允许多个线程 |
| **典型实现** | ReentrantLock | Semaphore, CountDownLatch, ReentrantReadWriteLock.ReadLock |
| **Node 等待状态** | EXCLUSIVE (-1) | SHARED (1) |

**架构数据流图：**

```text
       线程 1            线程 2             线程 3
         |                |                  |
    TryAcquire()     TryAcquire()       TryAcquire()
         |                |                  |
    [成功: State=1]   [失败]             [失败]
         |                |                  |
    (执行业务)    -> Node(2)入尾  ->  Node(3)入尾
                           ^                  |
                           | (阻塞/LockSupport.park)
                      FIFO 等待队列
```

**## 面试追问**
1. AQS 中的 `Condition`（条件变量）是如何实现的？它和 `wait/notify` 有什么区别？（基于 Node 的单向链表，支持多条件队列）
2. 什么是 AQS 的“公平锁”和“非公平锁”实现上的区别？（非公平锁在尝试获取锁时直接 CAS 抢占，不检查队列前驱）
3. 如果一个线程在 AQS 队列中等待时被中断，它会立刻从队列中移除吗？（不，只是标记中断状态，通常在获取锁成功后或抛出 InterruptedException 时才处理取消逻辑）

**## 易错点**
1. **覆盖误区**：认为自定义 AQS 必须重写所有方法，实际上只需根据模式重写 `tryAcquire`/`tryRelease` 或 `tryAcquireShared`/`tryReleaseShared`，其余排队逻辑由父类实现。
2. **State 理解**：认为 `state` 只能是 0 或 1（是否上锁），实际上 `state` 是 int 类型，可用于计数（如重入次数、信号量剩余数）。

## 记忆要点

- 核心定义：JUC下构建锁和同步器的基础框架，如ReentrantLock和Semaphore均基于此。
- 双核心机制：volatile int state（配合CAS修改） + CLH变种双向等待队列。
- 两大模式：独占模式（如ReentrantLock）与共享模式（如Semaphore、CountDownLatch）。
- 模板方法设计：子类仅需重写tryAcquire/tryRelease管理state，入队与阻塞交由AQS负责。

## 结构化回答


**30 秒电梯演讲：** 就像办证大厅的叫号系统，管排队(CLH队列)和当前办理人数(state)，具体业务由自定义窗口实现。

**展开框架：**
1. **通过volati** — le int state管理资源状态
2. **使用CLH队列管** — 使用CLH队列管理阻塞线程
3. **支持独占和共享两** — 支持独占和共享两种资源获取模式

**收尾：** 这是我实战中的理解，您想深入哪一段？


## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：什么是 AQS（抽象的队列同步器） | 今天这道题：什么是 AQS（抽象的队列同步器）。30 秒先给你讲清楚。 | 开场钩子 |
| 0:20 | 核心概念动画/示意图 | 就像办证大厅的叫号系统，管排队(CLH队列)和当前办理人数(state)，具体业务由自定义窗口实现。 | 核心概念 |
| 0:40 | volatile int示意图 | 通过volatile int state管理资源状态 | volatile int |
| 1:10 | CLH队列示意图 | 使用CLH队列管理阻塞线程 | CLH队列 |
| 1:40 | 总结卡 + 下期预告 | 记住今天这几个关键词，面试一定用得上。下期见。 | 收尾 |
