---
id: conc-138
difficulty: L4
category: concurrent
subcategory: AQS
tags:
- AQS
- CLH队列
- JUC
feynman:
  essence: 基于state变量和CLH队列实现的并发基础框架，用于构建锁和同步器。
  analogy: 就像办证大厅，state叫号器，CLH是排队的人龙，抢到了state就去窗口办业务，没抢到就睡觉。
  first_principle: 如何统一管理多线程竞争资源时的排队、阻塞与唤醒机制？
  key_points:
  - volatile int state标识状态
  - CLH双向队列管理阻塞线程
  - CAS修改state保证原子性
  - 支持独占（锁）和共享（计数/信号量）模式
follow_up:
- AQS 的 CLH 队列和原始 CLH 队列有什么区别？为什么改成双向？
- 公平锁和非公平锁的性能差异有多大？为什么默认非公平？
- ReentrantLock 的 condition 是如何基于 AQS 实现的？
memory_points:
- 核心基础：volatile int state表示同步状态，配合CAS实现原子修改
- 核心队列：CLH变种双向链表，FIFO管理获取锁失败的阻塞线程
- 独占模式获取：tryAcquire失败 -> 尾插法入队 -> 前驱为头再自旋抢 -> park挂起
- 公平非公平对比：公平锁先查队列有无前驱；非公平锁直接CAS插队抢锁
---

# AQS（AbstractQueuedSynchronizer）的底层实现原理是什么？CLH 队列是如何工作的？

### AQS 核心思想
AQS 是一个用来构建锁和同步器的**基础框架**。它维护了一个 `volatile int state`（同步状态）和一个 **CLH (Craig, Landin, and Hagersten) 队列**（变种的双向链表）。

### 关键组件
1. **state 状态**：
   - 0：无锁 / 未占用。
   - >0：重入次数（独占）或剩余许可数（共享）。
   - 通过 `CAS` (CompareAndSet) 原子修改。

2. **CLH 队列**：
   - 这是一个 FIFO 双向队列，管理所有获取锁失败的线程。
   - 节点类型：`SHARED`（共享，如 Semaphore）和 `EXCLUSIVE`（独占，如 ReentrantLock）。
   - 节点状态 `waitStatus`：
     - `SIGNAL (-1)`：后继节点需要唤醒。
     - `CANCELLED (1)`：节点超时或被中断，需清理。
     - `CONDITION (-2)`：节点在 Condition 队列中。
     - `PROPAGATE (-3)`：共享模式头节点可能传播唤醒。

### CLH 队列工作流程图
```text
       Head (Dummy Node)                     Tail
        | waitStatus=SIGNAL                     |
        +---- prev ----+---- next ----> +---- prev ----+
        |              |               |              |
        |   (Thread A) |               |   (Thread B) |
        |   (Running)  |               |   (Blocked)  |
        |              |               |              |
        +--------------+               +--------------+
            ^ 释放锁 unpark(next)          ^ park() 阻塞在此
```

### 独占锁获取流程
1. **tryAcquire**：子类实现（如 ReentrantLock 的 nonfairTryAcquire），尝试 CAS 修改 state。
   - 成功：设置 exclusiveOwnerThread，直接返回。
   - 失败：进入队列。
2. **addWaiter**：将当前线程封装成 `Node.EXCLUSIVE` 节点，通过 CAS 尾插法加入队列。
3. **acquireQueued**：在队列中自旋死循环。
   - 检查前驱节点是否为 Head（即自己是老二）：若是，再次尝试 tryAcquire。
   - 若前驱不是 Head 或 抢锁失败：检查前驱 waitStatus 是否为 SIGNAL。若不是，则 CAS 改为 SIGNAL，表示“我睡了，记得叫我”。然后调用 `LockSupport.park(this)` 挂起线程。

### 释放锁流程
1. **tryRelease**：子类实现，修改 state（通常减 1）。若 state 为 0，清空持有线程。
2. **unparkSuccessor**：若头节点的 waitStatus 不为 0，CAS 重置为 0。
   - 找到头节点的下一个有效节点（waitStatus <= 0）。
   - 调用 `LockSupport.unpark(node.thread)` 唤醒后继线程。

### 公平锁 vs 非公平锁
- **公平锁**：在 `tryAcquire` 时，**先检查** CLH 队列中是否有前驱节点。如果有，直接放弃竞争，去排队。
- **非公平锁**：直接尝试 CAS 抢锁（插队）。抢不到再去排队。吞吐量通常高于公平锁，但可能导致线程饥饿。

### 💡 实战案例
排查高并发服务 CPU 飙高问题时，发现大量线程阻塞在 AQS 的 `acquireQueued` 方法中，且堆栈显示不断自旋。原因是持有锁的线程在临界区内执行了耗时的 RPC 调用（违背了锁的快进快出原则），导致后续线程在 CLH 队列中自旋空转。优化后将 RPC 调用移出同步块，问题解决。

### 💻 代码示例
```java
// 基于 AQS 实现一个简单的互斥锁
class SimpleLock extends AbstractQueuedSynchronizer {
    @Override
    protected boolean tryAcquire(int arg) {
        // CAS 抢占 state：0 -> 1
        if (compareAndSetState(0, 1)) {
            setExclusiveOwnerThread(Thread.currentThread());
            return true;
        }
        return false;
    }

    @Override
    protected boolean tryRelease(int arg) {
        setExclusiveOwnerThread(null);
        setState(0); // volatile 写，保证可见性
        return true;
    }
    
    public void lock() { acquire(1); }
    public void unlock() { release(1); }
}
```

### 🆚 公平锁 vs 非公平锁
| 维度 | 公平锁 | 非公平锁 |
| :--- | :--- | :--- |
| **获取策略** | 严格按队列 FIFO 顺序获取 | 允许插队（新线程直接 CAS 抢） |
| **吞吐量** | 较低（需频繁切换上下文，无并发竞争） | 较高（减少了挂起/唤醒的开销） |
| **饥饿现象** | 无 | 可能（高并发下后继线程一直抢不过新来的） |
| **实现差异** | `tryAcquire` 中需判断 `hasQueuedPredecessors()` | 直接 CAS 尝试修改 state |

## 常见考点
1. **为什么头节点是虚拟节点**？头节点不代表任何线程，它是“已持有锁”状态的占位符，方便统一处理唤醒逻辑。
2. **自旋为什么放弃**：为了避免 CPU 空转浪费资源，在自旋一定次数或检查到前驱状态非 SIGNAL 时，会主动 park 挂起。
3. **Condition 实现**：AQS 的 ConditionObject 是如何利用等待队列的？（Condition 内部维护了一个单向队列，await 时将节点从 AQS 同步队列移至 Condition 队列，signal 时再转移回去）。

## 记忆要点

- 核心基础：volatile int state表示同步状态，配合CAS实现原子修改
- 核心队列：CLH变种双向链表，FIFO管理获取锁失败的阻塞线程
- 独占模式获取：tryAcquire失败 -> 尾插法入队 -> 前驱为头再自旋抢 -> park挂起
- 公平非公平对比：公平锁先查队列有无前驱；非公平锁直接CAS插队抢锁

## 结构化回答


**30 秒电梯演讲：** 就像办证大厅，state叫号器，CLH是排队的人龙，抢到了state就去窗口办业务，没抢到就睡觉。

**展开框架：**
1. **volatile** — int state标识状态
2. **CLH双向队列管** — CLH双向队列管理阻塞线程
3. **CAS修改sta** — CAS修改state保证原子性

**收尾：** AQS 的 CLH 队列和原始 CLH 队列有什么区别？


## 视频脚本

> 预计时长：5 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：AQS（AbstractQueuedSynchronizer）的底层实现原理是什么？CLH 队列是如何工作的 | 今天这道题：AQS（AbstractQueuedSynchronizer）的底层实现原理是什么？CLH 队列是如何工作的。30 秒先给你讲清楚。 | 开场钩子 |
| 0:20 | 核心概念动画/示意图 | 就像办证大厅，state叫号器，CLH是排队的人龙，抢到了state就去窗口办业务，没抢到就睡觉。 | 核心概念 |
| 0:40 | volatile int示意图 | volatile int state标识状态 | volatile int |
| 1:10 | CLH双向队列示意图 | CLH双向队列管理阻塞线程 | CLH双向队列 |
| 1:40 | CAS修改state示意图 | CAS修改state保证原子性 | CAS修改state |
| 2:10 | 总结卡 + 下期预告 | 记住三个词就能答好这道题。下期追问：AQS 的 CLH 队列和原始 CLH 队列有什么区别？为什么改成双向？ | 收尾 |
