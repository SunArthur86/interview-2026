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
memory_points:
- 本质定义：interrupt是协作式终止，仅设置标志位而不强制stop
- 两态响应：运行中仅设标志位需主动检查，阻塞中则抛异常清标志
- 避坑指南：因为catch异常时标志被清空，所以需重新interrupt()
- 废弃对比：stop强制释放锁致状态不一致，而interrupt安全可优雅退出
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
