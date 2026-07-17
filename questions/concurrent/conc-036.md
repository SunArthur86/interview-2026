---
id: conc-036
difficulty: L2
category: concurrent
feynman:
  essence: 通过设置标志位通知线程停止，而非强制杀死线程。
  analogy: 你在睡觉（阻塞），别人把你叫醒（中断）；你在干活（运行），别人喊你停一下，具体停不停你自己决定。
  first_principle: 如何安全地请求一个线程停止运行而不造成资源泄露？
  key_points:
  - interrupt() 仅设置中断标志位
  - 阻塞线程被中断会抛出 InterruptedException
  - 运行线程需检查 isInterrupted() 自行处理
  - 响应中断可实现线程优雅停止
memory_points:
- 本质澄清：interrupt 只是设置中断标志位，而非强制停止线程
- 状态影响：运行态仅置标志位，而阻塞态(如sleep)会抛异常并清除标志
- 方法对比：静态 interrupted() 会清除标志位，而实例 isInterrupted() 不清除
- 最佳实践：catch 异常后必须再次调用 interrupt() 恢复中断状态以防丢失
---

# 线程中断（interrupt）是什么？

线程中断是 Java 提供的一种线程间协作机制，而不是强制终止线程。它是线程间“握手”的一种方式。

**核心机制：**
- **中断标识位**：每个线程都有一个布尔类型的中断标识。调用 `interrupt()` 方法仅仅是设置该标识为 `true`，并不会直接停止正在运行的线程。

**对线程状态的影响：**
1. **运行状态**：如果线程正在运行，调用 `interrupt()` 仅仅设置标志位。线程需要通过 `isInterrupted()` 或 `Thread.interrupted()` 自行检查并决定如何响应。
2. **阻塞状态**：如果线程处于 `Object.wait()`, `Thread.join()`, `Thread.sleep()` 等阻塞状态，调用 `interrupt()` 会使线程抛出 `InterruptedException`，同时**清除中断标志位**（即变回 `false`），线程提前退出阻塞状态。

**最佳实践：**
- 不要使用 `stop()` 方法（已废弃且不安全，可能导致数据不一致）。
- 使用 `interrupt()` 通知线程停止。**处理中断有两种方式**：
  1. **向上抛出 throws InterruptedException**，交由上层处理。
  2. **在 catch 中再次调用 interrupt()** 恢复中断状态，`Thread.currentThread().interrupt();`，以确保后续逻辑能感知到中断。

### 实战案例
在开发线程池批量处理任务时，如果应用关闭，仅仅调用 `shutdown()` 可能导致正在执行的长时任务无法及时停止，阻塞 JVM 退出。**实战经验**：在业务循环逻辑中必须检查 `Thread.currentThread().isInterrupted()`，或者捕获 `InterruptedException` 后立即终止循环，配合 `awaitTermination` 确保资源优雅释放。

### 代码示例
```java
// 正确的中断处理模式：恢复中断状态
try {
    Thread.sleep(1000); 
} catch (InterruptedException e) {
    // 捕获异常后，中断标志已被清除
    Thread.currentThread().interrupt(); // **关键：恢复中断状态**
    // 执行清理逻辑
    cleanUp();
    return; // 或者抛出异常
}
```

### 对比表格
| 方法 | 类型 | 作用 | 中断标志位变化 |
| :--- | :--- | :--- | :--- |
| **interrupt()** | 实例方法 | 请求中断目标线程 | false -> true |
| **isInterrupted()** | 实例方法 | 检查中断状态 | **不改变** |
| **interrupted()** | 静态方法 | 检查并**清除**中断状态 | true -> false (复位) |
| **Thread.stop()** | 实例方法 | 强制停止线程 (已废弃) | 无意义 ( unsafe ) |

**状态流转示意图：**

```text
      Thread A               Thread B
    (Running)             (Interrupt)
        |                      |
        |   t.interrupt()      |
        +--------------------->|
                               |
              Check Point      |
        (isInterrupted?)<------+  [状态1: 仅置位标志]
               |
               v
        [Running Code] (自行处理逻辑)
               |
               | sleep(1000)   |
               v               |
        [BLOCKED] <------------+
               |               | [状态2: 抛出异常, 清除标志]
   InterruptedException     |
               |               |
               v               |
      (Catch & Stop)-----------+
```

**## 常见考点**
1. **`interrupted()` 和 `isInterrupted()` 的区别？**
   - `interrupted()` 是静态方法，会检查并**清除**中断标志位。
   - `isInterrupted()` 是实例方法，仅检查**不清除**标志位。
2. **为什么抛出 `InterruptedException` 后标志位会被清除？**
   - Java 设计为了避免线程在处理异常时，如果异常处理不当导致无限循环，中断标志一直存在可能引发后续逻辑的混乱，通常建议在 catch 块中再次调用 `interrupt()` 恢复状态。
3. **LockSupport.park() 响应中断吗？**
   - 响应。`park()` 的线程被 `interrupt()` 后会立刻唤醒，但不会抛出异常，可以通过 `Thread.interrupted()` 判断唤醒原因。
4. **如何优雅停止一个线程？**
   - 使用 `volatile boolean` 标志位（适用于简单循环）+ `interrupt()`（适用于涉及阻塞操作如 sleep/wait 的场景）。

## 记忆要点

- 本质澄清：interrupt 只是设置中断标志位，而非强制停止线程
- 状态影响：运行态仅置标志位，而阻塞态(如sleep)会抛异常并清除标志
- 方法对比：静态 interrupted() 会清除标志位，而实例 isInterrupted() 不清除
- 最佳实践：catch 异常后必须再次调用 interrupt() 恢复中断状态以防丢失

## 结构化回答



**30 秒电梯演讲：** 你在睡觉（阻塞），别人把你叫醒（中断）；你在干活（运行），别人喊你停一下，具体停不停你自己决定。

**展开框架：**
1. **interr** — interrupt() 仅设置中断标志位
2. **阻塞线程被中断** — 阻塞线程被中断会抛出 InterruptedException
3. **Interrupted** — 运行线程需检查 isInterrupted() 自行处理

**收尾：** 这是我实战中的理解，您想深入哪一段？



## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：线程中断（interrupt）是什么 | 今天这道题：线程中断（interrupt）是什么。30 秒先给你讲清楚。 | 开场钩子 |
| 0:20 | 核心概念动画/示意图 | 你在睡觉（阻塞），别人把你叫醒（中断）；你在干活（运行），别人喊你停一下，具体停不停你自己决定。 | 核心概念 |
| 0:40 | interrupt()示意图 | interrupt() 仅设置中断标志位 | interrupt() |
| 1:10 | 总结卡 + 下期预告 | 记住今天这几个关键词，面试一定用得上。下期见。 | 收尾 |
