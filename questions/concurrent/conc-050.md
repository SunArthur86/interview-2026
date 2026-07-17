---
id: conc-050
difficulty: L3
category: concurrent
feynman:
  essence: 线程从创建到销毁的过程，经历不同的状态调度。
  analogy: 像人的活动：出生(NEW)、醒着(RUNNABLE)、排队(BLOCKED)、发呆(WAITING)、睡觉(TIMED_WAITING)、离世(TERMINATED)。
  first_principle: 线程在 JVM 中是如何被调度和管理生命周期的？
  key_points:
  - RUNNABLE包含Ready和Running两种微观状态。
  - BLOCKED是等锁，WAITING是等信号，TIMED_WAITING是等时间。
  - BLOCKED只能转变为RUNNABLE，不能直接TERMINATED。
memory_points:
- 六大状态：NEW(新建) -> RUNNABLE(就绪/运行) -> TERMINATED(终止)
- 阻塞区分：BLOCKED是等Synchronized锁，而WAITING是等notify信号或join完成
- 触发条件：sleep/wait(timeout)触发TIMED_WAITING，wait/park触发WAITING
- 状态陷阱：Java的RUNNABLE包含了OS的就绪和运行，且IO阻塞在Java中也算RUNNABLE
---

# Java线程的生命周期和状态转换是怎样的？

### Java 线程生命周期

Java 线程在运行中会经历以下 6 种状态（`Thread.State` 枚举）:

#### 1. NEW（新建）
*   线程对象被创建，但尚未调用 `start()`。

#### 2. RUNNABLE（运行/就绪）
*   调用 `start()` 后，线程处于可运行状态。包含了 **Running**（正在运行）和 **Ready**（等待 CPU 调度）两种微观状态。

#### 3. BLOCKED（阻塞）
*   线程试图获取一个对象的监视器锁，但该锁正被其他线程持有。线程被阻塞在锁池中。

**实战案例**：生产环境出现死锁时，通过 `jstack` 导出堆栈，发现大量线程处于 `BLOCKED` 状态，且都在等待同一个锁对象地址。通过分析状态流转图，可以快速定位是持锁线程未释放导致后续线程堆积。

#### 4. WAITING（无限等待）
*   线程进入等待状态，直到被其他线程显式唤醒。
*   **触发方式**：`Object.wait()`, `Thread.join()`, `LockSupport.park()`。

#### 5. TIMED_WAITING（计时等待）
*   线程在指定时间内等待。
*   **触发方式**：`Thread.sleep()`, `Object.wait(long)`, `Thread.join(long)`。

**代码示例**：状态检查
```java
Thread t = new Thread(() -> {
    try { Thread.sleep(1000); } catch (Exception e) {}
});
t.start();
System.out.println(t.getState()); // 输出 RUNNABLE (可能)
// main 线程 join t
try { t.join(); } catch (Exception e) {}
System.out.println(t.getState()); // 输出 TERMINATED
```

#### 6. TERMINATED（终止）
*   线程执行完毕（`run()` 结束）或因异常退出了 `run()` 方法，生命周期结束。

#### 状态流转图示
```text
                 +---------->  TIMED_WAITING  <----------+
                 | (sleep, wait timeout)    |             |
                 |                           | (时间到)    |
+-------+   start()    +----------+          v             |    run() 结束
|  NEW  | --------->   |RUNNABLE  | <-------+-------+     |    +--------+
+-------+              +----+-----+         |       |     +---> |TERMINATED|
                            |               |       |          +--------+
                            | 竞争锁失败    | notify/notifyAll
                            |               |       |
                            v               |       v
                         +------+    unlock +------+   join 完成
                         |BLOCKED| <--------------+ | WAITING |
                         +------+                  +---------+
```

#### 状态对比详情

| 状态 | 触发条件 | 释放 CPU | 释放锁 | 唤醒条件 |
| :--- | :--- | :--- | :--- | :--- |
| **BLOCKED** | 等待进入 synchronized 块 | 是 | 否 | 获得锁 |
| **WAITING** | wait(), join(), park() | 是 | 是 (wait 时) | notify, join结束, unpark |
| **TIMED_WAITING** | sleep(n), wait(n) | 是 | 否 (sleep 时) | 超时, notify, interrupt |
| **RUNNABLE** | start(), yield/唤醒后 | 否 (Running) -> 是 (Ready) | - | 被调度器选中 |

**## 常见考点**
1.  **BLOCKED vs WAITING**：阻塞和等待的区别？（Blocked 是在等锁，Waiting 是在等信号）
2.  **线程如何终止**：不推荐使用 `stop()`，如何优雅地停止线程？（使用 `interrupt()` 配合状态检查）
3.  **Runnbale 状态细分**：Java 中 Runnable 包含 Ready 和 Running，这与操作系统状态有何不同？
4.  **yield 与状态转换**：调用 `yield()` 后线程会进入什么状态？（仍为 Runnable，但可能被调度器选中概率降低）

## 记忆要点

- 六大状态：NEW(新建) -> RUNNABLE(就绪/运行) -> TERMINATED(终止)
- 阻塞区分：BLOCKED是等Synchronized锁，而WAITING是等notify信号或join完成
- 触发条件：sleep/wait(timeout)触发TIMED_WAITING，wait/park触发WAITING
- 状态陷阱：Java的RUNNABLE包含了OS的就绪和运行，且IO阻塞在Java中也算RUNNABLE

## 结构化回答

**30 秒电梯演讲：** 像人的活动：出生(NEW)、醒着(RUNNABLE)、排队(BLOCKED)、发呆(WAITING)、睡觉(TIMED_WAITING)、离世(TERMINATED)。

**展开框架：**
1. **RUNNABLE** — RUNNABLE包含Ready和Running两种微观状态。
2. **BLOCKED** — BLOCKED是等锁，WAITING是等信号，TIMED_WAITING是等时间。
3. **BLOCKED只能转变** — BLOCKED只能转变为RUNNABLE，不能直接TERMINATED。

**收尾：** 这块我踩过一些坑，您想深入聊哪一段——原理细节、实战案例还是常见踩坑？

## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：Java线程的生命周期和状态转换是怎样的 | 今天这道题：Java线程的生命周期和状态转换是怎样的。30 秒先给你讲清楚。 | 开场钩子 |
| 0:20 | 核心概念动画/示意图 | 像人的活动：出生(NEW)、醒着(RUNNABLE)、排队(BLOCKED)、发呆(WAITING)、睡觉(TIMED_WAITING)、离世(TERMINATED)。 | 核心概念 |
| 0:40 | RUNNABLE示意图 | RUNNABLE包含Ready和Running两种微观状态。 | RUNNABLE |
| 1:10 | BLOCKED示意图 | BLOCKED是等锁，WAITING是等信号，TIMED_WAITING是等时间。 | BLOCKED |
| 1:40 | 总结卡 + 下期预告 | 记住今天这几个关键词，面试一定用得上。下期见。 | 收尾 |
