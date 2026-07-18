---
id: conc-055
difficulty: L3
category: concurrent
feynman:
  essence: 基于计数的并发控制器，允许多个线程同时访问资源。
  analogy: 像车库只有5个车位，车来了拿通行证，走时归还。
  first_principle: 如何限制同时访问某个资源的并发线程数量？
  key_points:
  - 基于AQS共享模式实现。
  - acquire获取许可，release释放许可。
  - 常用于流量控制或资源池管理。
memory_points:
- 一句话原理：基于AQS共享模式，用state模拟许可，acquire减1而release加1
- 核心机制：许可数<=0时获取线程入队阻塞，释放许可时唤醒队列后继线程
- 核心场景：控制同时访问资源的线程数，如限流、数据库连接池管理
- 组件对比：Semaphore许可可循环用，而CountDownLatch是一次性不可重置
---

# Semaphore信号量的原理和使用场景是什么？

### Semaphore 信号量原理与使用场景

#### 1. 原理
`Semaphore` 也是基于 AQS 实现的（**共享模式**）。
*   它维护了一个 **许可数量**（即 AQS 中的 `state` 变量）。
*   **acquire()**：尝试获取许可（通过 CAS 操作将 `state - 1`）。如果 `state < 0`（即许可数为 0），线程进入 AQS 同步队列的共享模式阻塞等待。
*   **release()**：释放许可，通过 CAS 操作将 `state + 1`。若增加后 `state <= 0`（说明之前有线程在等待），则唤醒等待队列中的一个或多个线程。

#### 2. 核心流程图
```text
Thread A calls acquire()
        │
        ▼
   state > 0 ? ──No──▶ 入队阻塞 (AQS Shared Node)
        │ Yes                  │
        │                     LockSupport.park()
   CAS state--                  │
        │                      │ (Release时唤醒)
   获得许可执行                 ▼
        │              尝试 CAS state++
        │                      │
   业务逻辑...                 ▼
        │              唤醒后继线程竞争
   calls release() ◀────────────┘
```

#### 3. 使用场景
1.  **限流**：控制同时访问特定资源的线程数量。例如：数据库连接池（限制最大连接数）、API 接口限流（令牌桶算法变种）。
2.  **资源池**：管理有限的资源，如文件句柄、复杂的计算资源。
3.  **互斥锁**：当许可数初始化为 1 时，功能类似于二元互斥锁，但通常建议直接用 ReentrantLock。

#### 4. 示例
```java
// 允许 5 个线程同时访问
Semaphore semaphore = new Semaphore(5);
try {
    semaphore.acquire(); // 获取许可，若不足则阻塞
    // 执行业务逻辑
} catch (InterruptedException e) {
    e.printStackTrace();
} finally {
    semaphore.release(); // 释放许可，必须在 finally 中
}
```

#### ## 常见考点
1.  **公平性问题**：`Semaphore` 构造函数可传 `fair` 参数。默认为非公平，可能导致某些线程长时间获取不到许可（饥饿）。
2.  **与 CountDownLatch 的区别**：CountDownLatch 是一次性的，计数减到0后无法重置；Semaphore 的许可可以动态释放和获取，循环使用。
3.  **获取多个许可**：`acquire(int permits)` 一次性获取/释放多个资源，防止死锁（例如需要连接A和连接B才能工作，要么同时获取两个，要么都不获取）。

#### 实战案例
在旧系统中维护一个第三方图片处理服务时，该服务最大并发承载为 10。直接使用 `Semaphore(10)` 保护调用代码，成功防止了因并发过高导致的服务端 503 错误。但需注意，如果任务处理时间差异极大，非公平信号量可能导致长任务占用所有许可，短任务长时间饥饿。

#### 代码示例
```java
// 限制同时只有 3 个线程能执行下载操作
Semaphore downloadLimiter = new Semaphore(3);

public void downloadFile(String url) {
    if (downloadLimiter.tryAcquire()) { // 非阻塞尝试获取
        try {
            // 模拟耗时下载
            Thread.sleep(1000);
            System.out.println("Downloaded: " + url);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } finally {
            downloadLimiter.release(); // 归还许可
        }
    } else {
        System.out.println("系统繁忙，请稍后再试: " + url);
        // 降级逻辑：放入重试队列
    }
}
```

#### 对比表格
| 组件 | 工作模式 | State含义 | 重用性 | 典型场景 |
| :--- | :--- | :--- | :--- | :--- |
| **Semaphore** | 共享模式 | 剩余许可数 | 可循环增减 | 限流、资源池 |
| **CountDownLatch** | 共享模式 | 倒数计数器 | 一次性 (不可重置) | 并发统计、并行计算 |
| **CyclicBarrier** | 同步屏障 | 等待线程数 | 可循环 (reset) | 多线程数据汇总 |
| **ReentrantLock** | 独占模式 | 锁重入次数 (0/1+) | 可释放/重入 | 临界区保护 |

## 核心知识点图

<img src="/interview-2026/images/diagram_concurrent_conc-055.svg" alt="Semaphore信号量的原理和使用场景是什么？ - 核心知识点图" style="max-width:100%;height:auto;border:1px solid var(--border);border-radius:8px;margin:1em 0;" />

## 记忆要点

- 一句话原理：基于AQS共享模式，用state模拟许可，acquire减1而release加1
- 核心机制：许可数<=0时获取线程入队阻塞，释放许可时唤醒队列后继线程
- 核心场景：控制同时访问资源的线程数，如限流、数据库连接池管理
- 组件对比：Semaphore许可可循环用，而CountDownLatch是一次性不可重置

## 结构化回答




**30 秒电梯演讲：** 像车库只有5个车位，车来了拿通行证，走时归还。

**展开框架：**
1. **AQS** — 基于AQS共享模式实现。
2. **acquire获取许** — acquire获取许可，release释放许可。
3. **常用于流量控** — 常用于流量控制或资源池管理。

**收尾：** 这是我实战中的理解，您想深入哪一段？




## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：Semaphore信号量的原理和使用场景是什么 | 今天这道题：Semaphore信号量的原理和使用场景是什么。30 秒先给你讲清楚。 | 开场钩子 |
| 0:20 | 核心概念动画/示意图 | 像车库只有5个车位，车来了拿通行证，走时归还。 | 核心概念 |
| 0:40 | AQS共享模式示意图 | 基于AQS共享模式实现。 | AQS共享模式 |
| 1:10 | acquire获取许示意图 | acquire获取许可，release释放许可。 | acquire获取许 |
| 1:40 | 总结卡 + 下期预告 | 记住今天这几个关键词，面试一定用得上。下期见。 | 收尾 |
