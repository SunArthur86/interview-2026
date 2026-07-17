---
id: conc-049
difficulty: L3
category: concurrent
feynman:
  essence: 控制线程的运行、阻塞、等待和唤醒状态。
  analogy: 像指挥交通，sleep是暂停，yield是让行，join是排队等。
  first_principle: 如何在线程之间进行协作与调度？
  key_points:
  - wait释放锁并等待，需notify唤醒；sleep休眠不释放锁。
  - interrupt仅设置标志位，结合异常机制优雅终止线程。
  - join用于等待子线程结束，保证执行顺序。
memory_points:
- 锁释放对比：wait()必在同步块且释放锁，而sleep()不释放锁仅让出CPU
- 中断机制：interrupt()仅设标志位，遇阻塞(如sleep)抛异常并清标志，需重新调interrupt()恢复
- 线程通信：wait/notify实现等待唤醒，必须持有相同对象的Monitor锁
- 其他方法：yield()让步不释放锁，join()等待目标线程执行完毕
---

# Java线程有哪些基本方法？各自的作用？

### Java 线程核心方法

#### 1. 线程等待
*   `wait()`：线程释放锁并进入等待队列，直到被 `notify()` 或 `notifyAll()` 唤醒。必须在同步块中调用。

#### 2. 线程睡眠
*   `sleep(long millis)`：线程休眠指定时间，**不释放锁**。让出 CPU 给其他线程，时间到后恢复就绪状态。

**实战案例**：在实现任务重试机制时，第一次请求失败后，通常调用 `Thread.sleep(2000)` 休眠 2 秒再重试，避免立即重试导致对下游服务造成“风暴”压力（这也是一种简单的熔断降级思路）。

#### 3. 线程让步
*   `yield()`：提示调度器当前线程愿意放弃当前 CPU 使用权。**不释放锁**，状态变回 Runnable。仅是建议，调度器可能忽略。

#### 4. 线程中断
*   `interrupt()`：设置线程的中断标志位。
*   **行为**：如果线程处于 `wait/sleep/join` 等阻塞状态，会抛出 `InterruptedException` 并清除标志位；如果是运行状态，仅设置标志，线程需自行检查 `isInterrupted()` 处理。

**代码示例**：
```java
// 优雅终止线程
while (!Thread.currentThread().isInterrupted()) {
    try {
        doWork();
    } catch (InterruptedException e) {
        // 捕获异常后，重新设置中断标志，以便上层逻辑处理
        Thread.currentThread().interrupt(); 
        break; // 退出循环
    }
}
```

#### 5. Join 等待
*   `join()`：当前线程等待调用 `join()` 的线程执行完毕（死亡）后才能继续执行。

#### 6. 线程唤醒
*   `notify()`：随机唤醒一个等待队列中的线程。
*   `notifyAll()`：唤醒等待队列中的所有线程。

#### 7. 其他常用方法
*   `isAlive()`：判断线程是否存活。
*   `setDaemon(true)`：设置为守护线程（当所有非守护线程结束时，JVM 退出）。
*   `currentThread()`：获取当前执行的线程对象。

#### wait() 与 sleep() 的核心区别
| 特性 | wait() | sleep() |
| :--- | :--- | :--- |
| **所属类** | Object (Java 根类) | Thread |
| **锁释放** | **释放锁** (释放 Monitor) | **不释放锁** (持有 Monitor) |
| **唤醒方式** | notify/notifyAll 或超时 | 时间结束自动唤醒 |
| **使用场景** | 线程间通信/协作 | 暂停执行，模拟延时 |

**## 常见考点**
1.  **InterruptedException 处理**：捕获中断异常后，为什么需要再次调用 `interrupt()` 恢复中断状态？
2.  **wait/notify 为什么必须在同步块**：底层原理？（防止“Lost Wake-Up”问题，即信号丢失）
3.  **join 的底层实现**：join() 底层是如何实现的？（实际上也是利用 wait() 方法）
4.  **yield 的实际效果**：在 Linux/Windows 下 yield 的行为差异（可能导致线程切换到其他 CPU 核）

## 记忆要点

- 锁释放对比：wait()必在同步块且释放锁，而sleep()不释放锁仅让出CPU
- 中断机制：interrupt()仅设标志位，遇阻塞(如sleep)抛异常并清标志，需重新调interrupt()恢复
- 线程通信：wait/notify实现等待唤醒，必须持有相同对象的Monitor锁
- 其他方法：yield()让步不释放锁，join()等待目标线程执行完毕

## 结构化回答

**30 秒电梯演讲：** 像指挥交通，sleep是暂停，yield是让行，join是排队等。

**展开框架：**
1. **wait释放锁并等待** — wait释放锁并等待，需notify唤醒；sleep休眠不释放锁。
2. **interrupt** — interrupt仅设置标志位，结合异常机制优雅终止线程。
3. **join用于等待子线程结束** — join用于等待子线程结束，保证执行顺序。

**收尾：** 这块我踩过一些坑，您想深入聊哪一段——原理细节、实战案例还是常见踩坑？

## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：Java线程有哪些基本方法？各自的作用 | 今天这道题：Java线程有哪些基本方法？各自的作用。30 秒先给你讲清楚。 | 开场钩子 |
| 0:20 | 核心概念动画/示意图 | 像指挥交通，sleep是暂停，yield是让行，join是排队等。 | 核心概念 |
| 0:40 | wait释放锁并等待示意图 | wait释放锁并等待，需notify唤醒；sleep休眠不释放锁。 | wait释放锁并等待 |
| 1:10 | interrupt示意图 | interrupt仅设置标志位，结合异常机制优雅终止线程。 | interrupt |
| 1:40 | 总结卡 + 下期预告 | 记住今天这几个关键词，面试一定用得上。下期见。 | 收尾 |
