---
id: core-155
difficulty: L3
category: java-core
feynman:
  essence: 利用锁和条件变量实现生产者-消费者模型的阻塞容器。
  analogy: 像传送带，没货了工人等着（阻塞），货满了搬运工等着，自动协调生产和消费。
  first_principle: 如何让多个线程自动协作，当资源不足时等待，资源可用时被唤醒，从而避免无效的轮询？
  key_points:
  - 由ReentrantLock和Condition实现线程挂起和唤醒
  - 常用方法包括put/take（阻塞）和offer/poll（非阻塞）
  - ArrayBlockingQueue有界，LinkedBlockingQueue默认无界
  - 广泛应用于生产者-消费者场景
memory_points:
- 一句话定义：支持阻塞的队列，空时取等待，满时存等待
- 底层机制：依赖Reentrant锁，配合notEmpty和notFull两个Condition实现挂起与唤醒
- 生产者存：获取锁，若满则await挂起；成功存入后signal唤醒消费者
- 消费者取：获取锁，若空则await挂起；成功取出后signal唤醒生产者
- 模型应用：天然解决生产者-消费者问题，解耦并实现异步削峰
---

# JAVA阻塞队列原理是什么？

阻塞队列（BlockingQueue）是一个支持两个附加操作的队列：
1. 当队列为空时，获取元素的线程会**等待**队列变为非空。
2. 当队列满时，存储元素的线程会**等待**队列出现可用空间。

### 核心原理
主要使用 `ReentrantLock` 和 `Condition`（条件变量）来实现线程的阻塞和唤醒。它利用经典的“生产者-消费者”模型。

**阻塞队列工作流程图：**
```text
    生产者线程                       阻列队列                         消费者线程
       │                             │                                  │
       ├──── put(e) ────────────────>│                                  │
       │                             │  lock.lock()                    │
       │                             │  if (count == capacity)         │
       │                             │      notFull.await()  ◄─────────┤ (挂起)
       │                             │                                  │
       │                             │  enqueue(e)                     │
       │                             │  count++                        │
       │                             │  notEmpty.signal() ─────────────>┤ (唤醒)
       │                             │  lock.unlock()                  │
       │                             │                                  │
       │<──── (返回) ◄────────────────│                                  │
       │                             │                                  │
       │                             │<───── take() ◄──────────────────┤
       │◄──── notFull.signal() ──────│  lock.lock()                    │
       │ (唤醒生产者)                 │  if (count == 0)                │
       │                             │      notEmpty.await() ◄────────┤ (挂起)
       │                             │  dequeue()                      │
       │                             │  count--                        │
       │                             │  lock.unlock()                  │
       │                             ├─────────── e ───────────────────>┤
```

- **生产者**：调用 `put` 时获取锁，如果队列满，调用 `notFull.await()` 释放锁并挂起；插入成功后调用 `notEmpty.signal()` 唤醒消费者。
- **消费者**：调用 `take` 时获取锁，如果队列空，调用 `notEmpty.await()` 释放锁并挂起；取出成功后调用 `notFull.signal()` 唤醒生产者。

### 代码示例 (ArrayBlockingQueue 核心逻辑)
```java
public void put(E e) throws InterruptedException {
    final ReentrantLock lock = this.lock;
    lock.lockInterruptibly();
    try {
        while (count == items.length)
            notFull.await(); // 队列满，挂起当前线程
        enqueue(e);
    } finally {
        lock.unlock();
    }
}

private void enqueue(E x) {
    items[putIndex] = x;
    if (++putIndex == items.length) putIndex = 0;
    count++;
    notEmpty.signal(); // 唤醒消费者
}
```

### 实战案例
在异步日志打印框架中，使用 `LinkedBlockingQueue` 作为日志缓冲区。当后台线程处理过慢导致队列满时，`put` 操作会阻塞业务线程，起到“背压”作用，防止系统 OOM，但也需注意设置合理的容量以避免阻塞太久。

## 记忆要点

- 一句话定义：支持阻塞的队列，空时取等待，满时存等待
- 底层机制：依赖Reentrant锁，配合notEmpty和notFull两个Condition实现挂起与唤醒
- 生产者存：获取锁，若满则await挂起；成功存入后signal唤醒消费者
- 消费者取：获取锁，若空则await挂起；成功取出后signal唤醒生产者
- 模型应用：天然解决生产者-消费者问题，解耦并实现异步削峰

## 结构化回答

**30 秒电梯演讲：** 利用锁和条件变量实现生产者-消费者模型的阻塞容器。打个比方，像传送带，没货了工人等着（阻塞），货满了搬运工等着，自动协调生产和消费。

**展开框架：**
1. **一句话定义** — 支持阻塞的队列，空时取等待，满时存等待
2. **底层机制** — 依赖Reentrant锁，配合notEmpty和notFull两个Condition实现挂起与唤醒
3. **生产者存** — 获取锁，若满则await挂起；成功存入后signal唤醒消费者

**收尾：** 我在项目里踩过坑——在异步日志打印框架中，使用 `LinkedBlockingQueue` 作为日志缓冲区。您想深入聊哪一段：原理、避坑还是对比选型？

## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：JAVA阻塞队列原理是什么 | "JAVA阻塞队列原理是什么？一句话——像传送带，没货了工人等着（阻塞），货满了搬运工等着，自动协调生产和消费。" | 开场钩子 |
| 0:45 | 概念动画/示意图 | "利用锁和条件变量实现生产者-消费者模型的阻塞容器——像传送带，没货了工人等着（阻塞），货满了搬运工等着，自动协调生产和消费" | 核心定义 |
| 1:30 | 一句话定义示意 | "支持阻塞的队列，空时取等待，满时存等待" | 要点1 |
| 2:15 | 底层机制示意 | "依赖Reentrant锁，配合notEmpty和notFull两个Condition实现挂起与唤醒" | 要点2 |
| 3:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |
