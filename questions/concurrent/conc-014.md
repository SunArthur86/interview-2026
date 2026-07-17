---
id: conc-014
difficulty: L2
category: concurrent
feynman:
  essence: sleep是暂停不释放锁，wait是等待并释放锁。
  analogy: sleep是眯一会手还扶着方向盘；wait是停车熄火把钥匙给别人，等通知再上车。
  first_principle: 线程在挂起时，是否需要让出临界资源的控制权以允许其他线程工作？
  key_points:
  - 所属类：sleep属Thread，wait属Object。
  - 锁行为：sleep不释放锁，wait释放锁。
  - 使用限制：wait必须在同步块中使用，sleep不需要。
  - 唤醒机制：sleep超时醒，wait需notify或超时。
memory_points:
- 类不同：sleep 来自 Thread，wait 来自 Object
- 锁机制：sleep 睡觉不释放锁，wait 等待必须释放锁
- 位置要求：wait 必须在 synchronized 块内，sleep 随处可用
- 唤醒方式：sleep 超时自动醒，wait 需 notify 或超时
---

# sleep与wait 区别？

`sleep()` 和 `wait()` 是 Java 多线程中非常容易混淆的两个方法，它们的区别主要体现在以下几个方面：

**1. 所属类不同**
- `sleep()`：属于 `Thread` 类的方法。
- `wait()`：属于 `Object` 类的方法。

**2. 锁的释放机制不同（核心区别）**
- `sleep()`：**不会释放锁**。如果线程在持有锁的状态下调用 `sleep()`，其他线程无法获得该锁，只能等待。
- `wait()`：**会释放锁**。当线程调用 `wait()` 时，它会释放当前持有的对象锁，进入等待队列，直到被 `notify()` 或 `notifyAll()` 唤醒或超时。

**3. 使用场景不同**
- `sleep()`：通常用于暂停线程的执行，不涉及线程间通信（同步）。
- `wait()`：必须用于同步代码块或同步方法中（即必须先获取锁），主要用于线程间的通信和协调。

**4. 唤醒方式不同**
- `sleep()`：睡眠时间结束后自动唤醒。
- `wait()`：需要等待其他线程调用 `notify()` 或 `notifyAll()` 唤醒，或者 `wait(long timeout)` 超时后自动唤醒。

**实战案例**：
在高并发抢购场景中，若在 `synchronized(lock)` 代码块内误用 `Thread.sleep(1000)` 而非 `lock.wait(1000)`，会导致锁被占用1秒不释放，系统吞吐量跌至个位数。

**代码示例（Wait 使用）**：
```java
synchronized (obj) {
    while (conditionNotMet) {
        try {
            obj.wait(200); // 释放锁，等待唤醒或超时
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
    // 执行业务逻辑
}
```

**对比表格**：

| 维度 | Thread.sleep() | Object.wait() |
| :--- | :--- | :--- |
| **锁释放** | 不释放锁 | 释放锁 |
| **作用位置** | 任何地方 | 必须在 synchronized 块内 |
| **所属类** | Thread | Object |
| **唤醒机制** | 超时自动唤醒 | notify/notifyAll 或超时 |
| **CPU占用** | 占用时间片（不释放CPU） | 不占用CPU，释放CPU资源 |
| **异常捕获** | 必须捕获 InterruptedException | 必须捕获 InterruptedException |

**补充细节：**
- **CPU 占用**：`sleep()` 时线程不释放 CPU 时间片（取决于操作系统调度），但处于 TIMED_WAITING 状态；`wait()` 释放锁后，线程进入 WAITING 状态，不占用 CPU，也不竞争锁直到被唤醒。
- **异常处理**：`sleep()` 必须捕获 `InterruptedException`，表示线程可能在休眠期间被中断；`wait()` 同样需要捕获 `InterruptedException`。

**执行流程对比图：**

```text
Thread.sleep() 流程：
┌─────────────┐     持有锁      ┌──────────────┐
│  线程 A 运行  │ ────────────> │ 进入 Sleep   │
└─────────────┘                 └──────┬───────┘
                                      │
                         睡眠中 (不释放锁) │
                                      ▼
                               ┌──────────────┐
                               │ 自动唤醒     │
                               └──────┬───────┘
                                      │
                           恢复运行 (继续持有锁)

Object.wait() 流程：
┌─────────────┐     持有锁      ┌──────────────┐     释放锁     ┌─────────────┐
│  线程 A 运行  │ ────────────> │ 调用 wait()  │ ──────────> │ 等待队列     │
└─────────────┘                 └──────────────┘               └──────┬──────┘
                                                                      │
                                               其他线程 B 调用 notify │
                                                                      ▼
                                                               ┌──────────────┐
                                                               │ 尝试重新获取锁 │
                                                               └──────┬───────┘
```

## 记忆要点

- 类不同：sleep 来自 Thread，wait 来自 Object
- 锁机制：sleep 睡觉不释放锁，wait 等待必须释放锁
- 位置要求：wait 必须在 synchronized 块内，sleep 随处可用
- 唤醒方式：sleep 超时自动醒，wait 需 notify 或超时

## 结构化回答

**30 秒电梯演讲：** sleep是眯一会手还扶着方向盘；wait是停车熄火把钥匙给别人，等通知再上车。

**展开框架：**
1. **所属类** — 所属类：sleep属Thread，wait属Object。
2. **锁行** — 锁行为：sleep不释放锁，wait释放锁。
3. **限制** — 使用限制：wait必须在同步块中使用，sleep不需要。

**收尾：** 这块我踩过一些坑，您想深入聊哪一段——原理细节、实战案例还是常见踩坑？

## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：sleep与wait 区别 | 今天这道题：sleep与wait 区别。30 秒先给你讲清楚。 | 开场钩子 |
| 0:20 | 核心概念动画/示意图 | sleep是眯一会手还扶着方向盘；wait是停车熄火把钥匙给别人，等通知再上车。 | 核心概念 |
| 0:40 | 所属类示意图 | 所属类：sleep属Thread，wait属Object。 | 所属类 |
| 1:10 | 总结卡 + 下期预告 | 记住今天这几个关键词，面试一定用得上。下期见。 | 收尾 |
