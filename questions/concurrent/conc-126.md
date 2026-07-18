---
id: conc-126
difficulty: L3
category: concurrent
feynman:
  essence: 支持插入/获取阻塞操作的线程安全队列，用于生产者-消费者模式。
  analogy: 像肯德基的点餐窗口，厨师做好放进窗口（队列），没菜了顾客就等，满了厨师就等。
  first_principle: 如何让多线程之间高效且安全地进行数据传递与缓冲？
  key_points:
  - put/take 支持阻塞
  - offer/poll 支持超时
  - 常用于生产者消费者模式
  - 主要实现类有 Array、Linked、Synchronous
memory_points:
- 一句话定义：满则阻塞写，空则阻塞读，专用于多线程安全传递数据
- 核心四方法对比：抛异常(add/remove)、返特殊(offer/poll)、阻塞(put/take)、超时退
- 底层实现：ReentrantLock 配合两个 Condition (notEmpty/notFull) 实现阻塞唤醒
- 两大主力对比：Array必须设容量且单锁；Linked默认无界且读写双锁分离吞吐高
---

# 说一说你对BlockingQueue的了解？

### BlockingQueue（阻塞队列）详解

#### 概念
`BlockingQueue` 主要用于多线程环境下线程间安全地传递数据。它继承自 `Queue`，提供了阻塞操作：当队列为空时，获取元素的操作会阻塞；当队列满时，添加元素的操作会阻塞。

#### 核心特性
1. **阻塞操作**：
   - `put(e)`：插入元素，如果队列满则阻塞，直到有空间。
   - `take()`：获取元素，如果队列空则阻塞，直到有元素。

2. **超时操作**：
   - `offer(e, time, unit)`：插入元素，如果队列满则等待指定时间，超时返回 false。
   - `poll(time, unit)`：获取元素，如果队列空则等待指定时间，超时返回 null。

3. **容量限制**：
   - 阻塞队列通常是有界的（如 `ArrayBlockingQueue`），防止内存溢出；
   - 也有无界队列（如 `LinkedBlockingQueue` 默认 `Integer.MAX_VALUE`），生产环境需谨慎。

#### 常见实现类
- **ArrayBlockingQueue**：基于数组的有界阻塞队列，FIFO。**必须指定容量**，内部通过 ReentrantLock 和 Condition 实现。
- **LinkedBlockingQueue**：基于链表的可选有界阻塞队列（默认无界 `Integer.MAX_VALUE`）。读写采用两把锁（takeLock 和 putLock），从而实现读写操作不互斥，吞吐量通常高于 ArrayBlockingQueue。
- **SynchronousQueue**：不存储元素的阻塞队列，每个插入操作必须等待另一个线程的移除操作，否则一直阻塞。吞吐量极高，用于传递性场景（如 `Executors.newCachedThreadPool`）。
- **PriorityBlockingQueue**：支持优先级的无界阻塞队列。使用堆结构实现，要求元素实现 Comparable 或提供 Comparator。
- **DelayQueue**：支持延时获取元素的无界阻塞队列。使用 PriorityQueue 实现，元素需实现 Delayed 接口。

#### 实现原理简述
```text
Producer Thread          Consumer Thread
     │                        │
     │   put(e)               │   take()
     ├───────────────────────▶│
     │   (Lock notFull)       │   (Lock notEmpty)
     │                        ▼
     │                   ┌─────────┐
     │                   │  Queue  │
     │                   │  Buffer │
     │                   └─────────┘
     │                        ▲
     │                        │
     │◀───────────────────────┤
     │   signal()             │   await()
```
底层通常使用 `ReentrantLock` 保证线程安全，配合 `Condition` 的 `await/signal` 机制进行线程间通知（类似于 Object 的 wait/notify）。例如 ArrayBlockingQueue 维护两个 Condition：`notEmpty`（取元素时若空则阻塞）和 `notFull`（放元素时若满则阻塞）。

## 常见考点
1. **ArrayBlockingQueue 和 LinkedBlockingQueue 的区别？**（锁机制、初始容量、链表vs数组）
2. **SynchronousQueue 的实现原理及应用场景？**（考察公平/非公平策略，CAS 或栈实现）
3. **BlockingQueue 为什么不需要显式加锁即可保证线程安全？**（考察内部已封装的锁机制）
4. **生产环境中如何选择合适的阻塞队列？**


## 记忆要点

- 一句话定义：满则阻塞写，空则阻塞读，专用于多线程安全传递数据
- 核心四方法对比：抛异常(add/remove)、返特殊(offer/poll)、阻塞(put/take)、超时退
- 底层实现：ReentrantLock 配合两个 Condition (notEmpty/notFull) 实现阻塞唤醒
- 两大主力对比：Array必须设容量且单锁；Linked默认无界且读写双锁分离吞吐高

## 结构化回答


**30 秒电梯演讲：** 像肯德基的点餐窗口，厨师做好放进窗口（队列），没菜了顾客就等，满了厨师就等。

**展开框架：**
1. **put/ta** — put/take 支持阻塞
2. **offer/** — offer/poll 支持超时
3. **常用于生产者** — 常用于生产者消费者模式

**收尾：** 这是我实战中的理解，您想深入哪一段？


## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：说一说你对BlockingQueue的了解 | 今天这道题：说一说你对BlockingQueue的了解。30 秒先给你讲清楚。 | 开场钩子 |
| 0:20 | 核心概念动画/示意图 | 像肯德基的点餐窗口，厨师做好放进窗口（队列），没菜了顾客就等，满了厨师就等。 | 核心概念 |
| 0:40 | put/take示意图 | put/take 支持阻塞 | put/take |
| 1:10 | offer/poll示意图 | offer/poll 支持超时 | offer/poll |
| 1:40 | 总结卡 + 下期预告 | 记住今天这几个关键词，面试一定用得上。下期见。 | 收尾 |
