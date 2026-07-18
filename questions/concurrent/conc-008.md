---
id: conc-008
difficulty: L2
category: concurrent
feynman:
  essence: 设置中断标志位，请求线程协作停止，而非暴力终止。
  analogy: 不是拔电源，而是按暂停键让任务自己收拾东西走人。
  first_principle: 如何安全地停止一个正在运行的线程而不破坏数据一致性？
  key_points:
  - 调用 interrupt() 仅设置标志位，不立即停止线程。
  - 若线程处于阻塞状态，会抛出 InterruptedException。
  - 通过检查标志位或捕获异常来处理中断逻辑。
  - 必须避免使用已废弃的 stop() 方法。
  - interrupt() 仅设置中断标志位
  - 阻塞线程被中断会抛出 InterruptedException
  - 运行线程需检查 isInterrupted() 自行处理
  - 响应中断可实现线程优雅停止
memory_points:
- 本质定义：interrupt是协作式终止，仅设置标志位而不强制stop
- 两态响应：运行中仅设标志位需主动检查，阻塞中则抛异常清标志
- 避坑指南：因为catch异常时标志被清空，所以需重新interrupt()
- 废弃对比：stop强制释放锁致状态不一致，而interrupt安全可优雅退出
- 本质澄清：interrupt 只是设置中断标志位，而非强制停止线程
- 状态影响：运行态仅置标志位，而阻塞态(如sleep)会抛异常并清除标志
- 方法对比：静态 interrupted() 会清除标志位，而实例 isInterrupted() 不清除
- 最佳实践：catch 异常后必须再次调用 interrupt() 恢复中断状态以防丢失
follow_up: []
tags: []
---

# Interrupt方法结束线程是什么？

Thread.interrupt() 是 Java 推荐的「协作式」终止线程的方法，它不会强制停止线程，而是设置线程的中断标志位，由线程自己决定如何响应。

**interrupt() 的核心逻辑：**

```text
                  [调用 thread.interrupt()]
                            |
            +---------------+---------------+
            |                               |
    [线程状态：阻塞]                 [线程状态：运行中]
  (sleep/wait/join)              (非阻塞状态)
            |                               |
            v                               v
    [抛出 InterruptedException]   [设置中断标志位]
    [同时清除中断标志位]           (isInterrupted = true)
            |
            +---> 代码捕获异常，决定是否退出
```

**interrupt() 的作用细节：**
1. **如果线程在运行（非阻塞）**：只设置内部的 `interrupt` 标志位为 `true`。线程代码需通过 `Thread.currentThread().isInterrupted()` 或静态的 `Thread.interrupted()`（会清除标志）主动检查。
2. **如果线程在阻塞**：
   - 线程会立即从阻塞状态退出。
   - 抛出 `InterruptedException`。
   - **关键**：抛出异常的同时，JVM 会自动清除中断标志位（将其重置为 `false`）。

**正确响应中断的模板：**
```java
public void run() {
    while (!Thread.currentThread().isInterrupted()) {
        try {
            // 业务逻辑
            Thread.sleep(1000);
        } catch (InterruptedException e) {
            // 1. 阻塞时被中断会清除标志位，需重新设置以供上层判断
            Thread.currentThread().interrupt(); 
            // 2. 通常这里选择跳出循环，结束线程
            break; 
        }
    }
}
```

**为什么不用 stop()？** 
`stop()` 已废弃，因为它强制停止线程并立即释放所有锁。这可能导致对象处于不一致的状态（如转账扣了款还没到账就被强制停止）。`interrupt()` 让线程优雅地在安全点退出，保证数据一致性。

### 实战案例
在开发一个文件扫描工具时，用户点击“取消”按钮调用 `thread.interrupt()`。起初线程使用 `Thread.sleep(100)` 轮询，能立即停止。但后来改为 `ServerSocket.accept()` 阻塞等待连接，导致中断无效（因为 `accept()` 不响应中断），最后改为调用 `socket.close()` 才成功打破阻塞。

### 代码示例 (中断死循环)
```java
Thread t = new Thread(() -> {
    // 模拟耗时计算，没有阻塞方法
    while (!Thread.currentThread().isInterrupted()) {
        long x = 0;
        for (int i = 0; i < Long.MAX_VALUE; i++) { x++; }
    }
    System.out.println("Thread stopped gracefully.");
});
t.start();
Thread.sleep(1000);
t.interrupt(); // 设置标志位，让 while 循环退出
```

### 线程停止方式对比
| 方式 | 机制 | 优点 | 缺点 | 推荐度 |
| :--- | :--- | :--- | :--- | :---
| **stop()** | 强制终止线程，立即释放锁 | 立即生效 | 数据不一致，破坏对象状态，已废弃 | ❌ 禁止 |
| **suspend()** | 强制挂起线程，持有锁不释放 | 暂停执行 | 极易造成死锁，已废弃 | ❌ 禁止 |
| **interrupt()** | 协作式，设置标志位或抛出异常 | 安全，优雅，保证数据一致性 | 需编写响应代码，可能无法中断某些 I/O | ✅ **强烈推荐** |
| **volatile标志** | 自定义标志位变量 | 简单易懂 | 无法处理 `sleep/wait` 等阻塞状态 | ⚠️ 仅限非阻塞场景 |

## 常见考点
1. **标志位清除机制**：为什么 catch 到 `InterruptedException` 后要重新调用 `interrupt()`？（因为 JVM 抛出异常时已清除标志，重新设置是为了让循环条件或上层调用者知道发生了中断）。
2. **LockSupport.park() 的响应**：处于 `park` 状态的线程被 `interrupt` 后，会立即返回（不抛异常），可以通过 `Thread.interrupted()` 判断。
3. **不可中断的阻塞**：Java NIO 中的 `ServerSocketChannel.accept()` 或某些 IO 阻塞可能无法响应中断，需要关闭 Channel 来跳出阻塞。

## 核心知识点图

<img src="/interview-2026/images/diagram_concurrent_conc-008.svg" alt="Interrupt方法结束线程是什么？ 核心知识点图" style="max-width:100%;height:auto;border:1px solid var(--border);border-radius:8px;margin:1em 0;" />

## 记忆要点

- 本质定义：interrupt是协作式终止，仅设置标志位而不强制stop
- 两态响应：运行中仅设标志位需主动检查，阻塞中则抛异常清标志
- 避坑指南：因为catch异常时标志被清空，所以需重新interrupt()
- 废弃对比：stop强制释放锁致状态不一致，而interrupt安全可优雅退出

## 结构化回答



**30 秒电梯演讲：** 不是拔电源，而是按暂停键让任务自己收拾东西走人。

**展开框架：**
1. **调用 int** — 调用 interrupt() 仅设置标志位，不立即停止线程。
2. **若线程处于阻塞状态** — 若线程处于阻塞状态，会抛出 InterruptedException。
3. **通过检查标志** — 通过检查标志位或捕获异常来处理中断逻辑。

**收尾：** 这是我实战中的理解，您想深入哪一段？



## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：Interrupt方法结束线程是什么 | 今天这道题：Interrupt方法结束线程是什么。30 秒先给你讲清楚。 | 开场钩子 |
| 0:20 | 核心概念动画/示意图 | 不是拔电源，而是按暂停键让任务自己收拾东西走人。 | 核心概念 |
| 0:40 | 调用 interrupt()示意图 | 调用 interrupt() 仅设置标志位，不立即停止线程。 | 调用 interrupt() |
| 1:10 | 总结卡 + 下期预告 | 记住今天这几个关键词，面试一定用得上。下期见。 | 收尾 |

---

## 延伸：线程中断（interrupt）是什么？

> 合并自 `conc-036`（相似度 67%）

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
