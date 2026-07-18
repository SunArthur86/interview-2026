---
id: conc-030
difficulty: L2
category: concurrent
feynman:
  essence: 线程生命周期的终点，任务执行完毕或被迫终止。
  analogy: 员工下班离职，工牌注销，不能再回来工作。
  first_principle: 如何标记并清理一个已完成执行或因错误无法继续执行的线程？
  key_points:
  - run() 方法执行完成正常结束
  - 抛出未捕获异常导致意外终止
  - 死亡的线程不能被再次 start
  - stop() 方法已被废弃不推荐使用
memory_points:
- 定义：线程 run() 方法执行完毕的终止状态，生命周期彻底结束。
- 触发条件：正常执行结束，或抛出未捕获的异常导致意外退出。
- 因为 stop() 极易导致数据不一致，所以废弃 stop()，推荐用 interrupt 标志位优雅停止。
- 死亡即终局：一旦进入 TERMINATED 状态，不能再次 start()，否则抛 IllegalThreadStateException。
---

# 什么是线程死亡（DEAD）？

### 线程死亡（TERMINATED/DEAD）

**定义**：
线程的**终止状态**，表示线程的生命周期已经结束。

**进入死亡状态的几种方式：**
1. **正常结束**：线程执行完 `run()` 方法的最后一条指令，正常退出。
2. **异常结束**：线程在执行过程中抛出了一个未捕获的 `Exception` 或 `Error`，导致线程意外终止。
3. **强制停止（不推荐）**：调用已废弃的 `stop()` 方法强制结束线程（容易导致数据不一致，已被淘汰）。

**注意事项**：
- 一旦线程进入死亡状态，就**不能再次启动**。调用 `start()` 会抛出 `IllegalThreadStateException`。
- 此时线程对象可能仍作为实体对象存在于内存中，但不再拥有执行栈和执行资源。

**状态流转图**：
```text
  ┌──────────────┐
  │   NEW/       │ ────────[调用 start()]───────▶ ┌─────────────┐
  │   RUNNABLE   │                                   │   RUNNING   │
  └──────────────┘                                   └──────┬──────┘
        ▲                                                   │
        │                                                   │
        │           ┌───────────────────────────────────────┘
        │           │
        │           │ (run()正常返回 / 抛出未捕获异常 / stop())
        │           ▼
        │    ┌───────────────┐
        └────│  TERMINATED   │
             │    (DEAD)     │
             └───────────────┘
```

**实战案例**：在生产环境中，曾遇到因线程池任务执行逻辑没有 `try-catch`，导致子线程抛出未捕获异常（如 NPE）而静默死亡，任务丢失且主线程无感知，排查困难。最终通过实现 `Thread.UncaughtExceptionHandler` 并在线程工厂中设置，统一捕获异常并报警解决。

**代码示例**：
```java
// 优雅停止线程：使用中断标志位
Thread thread = new Thread(() -> {
    while (!Thread.currentThread().isInterrupted()) { // 检查中断状态
        // 执行任务
        try {
            TimeUnit.SECONDS.sleep(1);
        } catch (InterruptedException e) {
            // 捕获中断异常，JVM会自动清除中断标志，需手动再次中断以退出循环
            Thread.currentThread().interrupt(); 
        }
    }
    System.out.println("线程已停止");
});
thread.start();
// thread.interrupt(); // 发送停止信号
```

## 常见考点
1. 如何正确优雅地停止一个线程？（考察 interrupt() 与 isInterrupted() 配合使用）
2. 线程池中的线程复用机制是如何处理线程死亡后的任务重新分配的？
3. 为什么不推荐使用 `Thread.stop()`？
4. `run()` 方法抛出异常后，线程处于什么状态？主线程能捕获到吗？

## 核心知识点图

<img src="/interview-2026/images/diagram_concurrent_conc-030.svg" alt="什么是线程死亡（DEAD）？ 核心知识点图" style="max-width:100%;height:auto;border:1px solid var(--border);border-radius:8px;margin:1em 0;" />

## 记忆要点

- 定义：线程 run() 方法执行完毕的终止状态，生命周期彻底结束。
- 触发条件：正常执行结束，或抛出未捕获的异常导致意外退出。
- 因为 stop() 极易导致数据不一致，所以废弃 stop()，推荐用 interrupt 标志位优雅停止。
- 死亡即终局：一旦进入 TERMINATED 状态，不能再次 start()，否则抛 IllegalThreadStateException。

## 结构化回答




**30 秒电梯演讲：** 员工下班离职，工牌注销，不能再回来工作。

**展开框架：**
1. **run()** — run() 方法执行完成正常结束
2. **抛出未捕获异** — 抛出未捕获异常导致意外终止
3. **死亡的线程不** — 死亡的线程不能被再次 start

**收尾：** 这是我实战中的理解，您想深入哪一段？




## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：什么是线程死亡（DEAD） | 今天这道题：什么是线程死亡（DEAD）。30 秒先给你讲清楚。 | 开场钩子 |
| 0:20 | 核心概念动画/示意图 | 员工下班离职，工牌注销，不能再回来工作。 | 核心概念 |
| 0:40 | run()示意图 | run() 方法执行完成正常结束 | run() |
| 1:10 | 总结卡 + 下期预告 | 记住今天这几个关键词，面试一定用得上。下期见。 | 收尾 |
