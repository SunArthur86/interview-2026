---
id: conc-011
difficulty: L2
category: concurrent
feynman:
  essence: 通过标志位或中断信号请求线程停止，而非暴力终止。
  analogy: 想让同事停下来，是发个消息通知他（interrupt），而不是直接拔掉他电脑的电源（stop）。
  first_principle: 如何在不破坏共享资源一致性的前提下，安全地停止一个正在运行的线程？
  key_points:
  - 正常结束：run方法执行完毕。
  - 标志位退出：volatile变量控制循环。
  - interrupt()：抛异常唤醒阻塞或置位标志，需线程配合检查。
  - stop()废弃：强行释放锁导致数据不一致，极不安全。
memory_points:
- 终止线程推荐 interrupt 和 volatile 标志位，严禁使用 stop()
- 因为 stop() 会瞬间释放所有锁并破坏原子性，导致对象状态不一致
- interrupt 遇到阻塞会抛异常，遇到运行态仅置标志位需主动检查
- 两阶段终止模式：catch 异常后需再次调用 interrupt() 恢复中断状态
---

# Java终止线程有哪几种方式？为什么stop()被废弃？

Java 终止线程主要有以下几种方式：

**1. 正常运行结束**
线程执行完 `run()` 方法的所有代码，线程正常终止。

**2. 使用退出标志**
对于伺服线程（需要长时间运行的线程），通常定义一个 `volatile boolean` 类型的标志位来控制循环退出。
```java
public class ThreadSafe extends Thread {
    public volatile boolean exit = false;
    public void run() {
        while (!exit) {
            // do something
        }
    }
}
```
**注意**：`volatile` 关键字保证了 `exit` 变量的可见性，确保一个线程修改了值，其他线程能立即看到。

**3. 使用 interrupt() 方法中断线程**
这是 Java 推荐的标准中断方式。
- **如果线程处于阻塞状态**（如 `sleep`, `wait`, `join` 等）：调用 `interrupt()` 会使线程抛出 `InterruptedException`，从而跳出阻塞状态，应在 `catch` 块中处理退出逻辑。
- **如果线程处于运行状态**：调用 `interrupt()` 仅仅是将线程的中断标志位置为 `true`。线程内部需要通过 `isInterrupted()` 或 `Thread.interrupted()` 来检查标志位并主动停止执行。

**4. 使用 stop() 方法（已废弃，严禁使用）**
`Thread.stop()` 方法已经被废弃，因为它极其不安全。
- **原因**：调用 `stop()` 会立即终止线程，并释放该线程持有的所有锁。这会导致锁被突然释放，被锁保护的对象可能处于不一致的状态（“脏读”或写入一半），破坏了数据原子性，引发难以排查的程序错误。这就像“直接拔掉电脑电源”而不是“正常关机”。

**实战案例**：
在微服务调用中，若使用 `stop()` 强制终止正在处理订单支付的线程，可能导致支付状态已扣款但数据库订单未更新（锁释放导致其他线程读到中间状态）。正确的做法是设置线程中断标志，并在 `finally` 块中回滚事务。

**代码示例（两阶段终止模式）**：
```java
public void run() {
    while (!Thread.currentThread().isInterrupted()) {
        try {
            // 模拟阻塞操作
            TimeUnit.SECONDS.sleep(1);
        } catch (InterruptedException e) {
            // 捕获中断异常，再次设置中断标志以保持中断状态
            Thread.currentThread().interrupt();
            break;
        }
    }
    // 执行资源清理
    cleanup();
}
```

**对比表格**：

| 特性 | stop() | interrupt() | 标志位退出 |
| :--- | :--- | :--- | :--- |
| **安全性** | 极低（破坏原子性） | 高（响应式） | 高（依赖逻辑） |
| **锁处理** | 立即释放所有锁 | 不释放锁（需手动处理） | 不释放锁 |
| **适用场景** | 严禁使用 | 通用、标准方式 | 轮询任务（非阻塞） |
| **阻塞状态** | 强制终止 | 抛出异常唤醒 | 无法感知 |

**补充细节：**
关于 `interrupt()` 的最佳实践是“两阶段终止模式”。即捕获 `InterruptedException` 后，应该再次调用 `interrupt()` 恢复中断状态，以便上层调用栈也能感知到中断请求。此外，对于处于 I/O 阻塞（如 NIO 的 `InterruptibleChannel`）的线程，调用 `interrupt()` 会关闭 Channel 并抛出 `ClosedByInterruptException`。

```java
// 最佳实践示例
public void run() {
    try {
        while (!Thread.currentThread().isInterrupted()) {
            // do work
        }
    } catch (InterruptedException e) {
        // 线程在阻塞期间被中断
        Thread.currentThread().interrupt(); // 恢复中断状态
    } finally {
        cleanup(); // 清理资源
    }
}
```

## 常见考点
1. **如何处理不可中断的阻塞？**：对于传统的 I/O 流，`interrupt()` 往往无效，通常需要通过关闭底层的 Socket 来迫使线程抛出异常。
2. **停止线程时如何保证资源释放？**：无论使用标志位还是 interrupt，都应当在 finally 块或显式的清理逻辑中释放资源（文件句柄、数据库连接等）。
3. **`interrupt()` 与 `isInterrupted()` 的区别？**：`interrupt()` 是设置中断位（实例方法）；`isInterrupted()` 只是查询状态；`Thread.interrupted()` 是静态方法，查询并清除中断位。
4. **为什么废弃 `suspend()` 和 `resume()`？**：`suspend()` 调用后线程不释放锁，容易导致死锁；`stop()` 则破坏数据一致性。


## 记忆要点

- 终止线程推荐 interrupt 和 volatile 标志位，严禁使用 stop()
- 因为 stop() 会瞬间释放所有锁并破坏原子性，导致对象状态不一致
- interrupt 遇到阻塞会抛异常，遇到运行态仅置标志位需主动检查
- 两阶段终止模式：catch 异常后需再次调用 interrupt() 恢复中断状态

## 结构化回答


**30 秒电梯演讲：** 想让同事停下来，是发个消息通知他（interrupt），而不是直接拔掉他电脑的电源（stop）。

**展开框架：**
1. **正常结束** — run方法执行完毕。
2. **标志位退出** — volatile变量控制循环。
3. **interrupt()** — 抛异常唤醒阻塞或置位标志，需线程配合检查。

**收尾：** 这是我实战中的理解，您想深入哪一段？


## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：Java终止线程有哪几种方式？为什么stop()被废弃 | 今天这道题：Java终止线程有哪几种方式？为什么stop()被废弃。30 秒先给你讲清楚。 | 开场钩子 |
| 0:20 | 核心概念动画/示意图 | 想让同事停下来，是发个消息通知他（interrupt），而不是直接拔掉他电脑的电源（stop）。 | 核心概念 |
| 0:40 | 正常结束示意图 | 正常结束：run方法执行完毕。 | 正常结束 |
| 1:10 | 总结卡 + 下期预告 | 记住今天这几个关键词，面试一定用得上。下期见。 | 收尾 |
