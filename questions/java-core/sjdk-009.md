---
id: sjdk-009
difficulty: L3
category: java-core
feynman:
  essence: JVM管理的轻量级线程，实现“一请求一线程”
  analogy: 像Java线程一样写同步代码，像Node.js一样高效处理百万并发
  first_principle: 解决传统线程在高并发IO场景下阻塞成本过高和数量受限的问题
  key_points:
  - 由JVM管理的用户态线程
  - 数量几乎无限，创建销毁开销极小
  - 阻塞操作不阻塞底层操作系统线程
  - 适用于高并发IO场景，不适合CPU密集型
memory_points:
- 本质：通过虚拟线程实现同步代码风格高并发，替代复杂的Reactive异步链
- 核心原理：基于Continuation续体，遇阻塞IO则从载体线程Unmount卸载
- 避坑：synchronized或本地方法会导致Pinning(钉住)，高并发下耗尽载体线程
- 解决：摒弃synchronized改用ReentrantLock，且上下文传递改用ScopedValue
---

# 什么是Project Loom？虚拟线程如何改变Java并发编程模型？

🎯 本质：Project Loom（JDK 21正式发布）引入轻量级虚拟线程，允许用同步编程风格实现高并发IO。

🏗️ 线程模型架构对比：
```text
传统模型
┌─────────┐         ┌───────────────┐    ┌──────────────┐
│ Request │──spawn──│ Platform(OS)  │──M:N─│ CPU Core     │
│ (1:1)   │         │ Thread (Heavy)│    │ (Context Svc)│
└─────────┘         └───────────────┘    └──────────────┘
高成本：栈内存(~1MB)，上下文切换慢(微秒级)

虚拟线程模型
┌─────────┐         ┌───────────────┐    ┌──────────────┐
│ Request │──mount──│ Carrier (OS)  │    │ CPU Core     │
│ (Many)  │  <────> │   Thread      │    │ (Continuations)│
└─────────┘  unmount│ (ForkJoinPool)│    └──────────────┘
低成本：栈内存(~KB)，调度在用户态(纳秒级)
```

📊 编程模型与生命周期：
// 同步代码即可实现高并发，底层由 JVM 调度
Thread.startVirtualThread(() -> {
    var data = httpClient.get(url);  // IO操作：虚拟线程Unmount，让出Carrier
    db.save(data);                   // IO就绪：虚拟线程Mount，继续执行
});

// 使用 ExecutorService 批量管理
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    IntStream.range(0, 10_000).forEach(i -> {
        executor.submit(() -> processRequest(i));
    });
}

技术细节与原理：
1. **Continuation (续体)**：
   - 虚拟线程的实现基于 Continuation。它保存调用栈状态。
   - 在 JVM 层面，虚拟线程的任务被封装为 `Runnable`，运行在 Carrier Thread（平台线程，通常是 `ForkJoinPool` 的 Worker 线程）上。
2. **Mount / Unmount 机制**：
   - **Mount**：当虚拟线程运行时，它的栈帧被拷贝/映射到平台线程的栈上执行。
   - **Unmount**：遇到阻塞操作（如 Socket 读取、LockSupport.park）时，JVM 将虚拟线程的状态从平台线程栈移除（卸载），平台线程转而去处理队列中的其他虚拟线程。
3. **Pinning (载入钉住) 问题**：
   - 当虚拟线程执行到 `synchronized` 块或调用本地方法 时，它无法被 Unmount，会一直占用底层的 Carrier Thread。
   - **后果**：在高并发下，如果大量虚拟线程被钉住，Carrier Thread 会被耗尽，导致吞吐量下降，退化为传统线程池性能。
   - **解决**：尽量使用 `ReentrantLock` 替代 `synchronized`（因为 `ReentrantLock` 基于 `LockSupport`，支持 Unmount）。
4. **调度器**：默认使用 `ForkJoinPool`，工作线程数等于 CPU 核心数（力求最大化 CPU 利用率，减少上下文切换）。

对现有技术的影响：
1. **替代 CompletableFuture**：不再需要复杂的链式调用，直接写 `try-catch` 同步代码。
2. **部分替代 Reactive 编程**：Web 容器（如 Tomcat、Netty）适配虚拟线程后，不再需要 Reactive 堆栈即可实现高吞吐。
3. **内存与 CPU 开销**：虚拟线程对象分配在堆上，栈初始很小且按需增长。
4. **ThreadLocal 警告**：由于虚拟线程数量可能高达百万，每个线程都缓存 `ThreadLocal` 会导致严重的内存泄漏。应尽量使用 `ScopedValue`（JDK 21 预览特性）传递上下文。

⚔️ 传统线程 vs 虚拟线程 vs Reactive (WebFlux)
| 维度 | 传统线程 | 虚拟线程 | Reactive (WebFlux) |
| :--- | :--- | :--- | :--- |
| **编程模型** | 同步阻塞 (简单) | 同步阻塞 (简单) | 异步非阻塞 (复杂，学习曲线陡峭) |
| **内存占用** | 高 (~2MB/栈) | 极低 (~KB/栈) | 低 (无栈，仅对象) |
| **吞吐量** | 受限于线程数 (通常几百) | 受限于网络/DB (百万级并发) | 极高 (事件循环) |
| **调试难度** | 容易 (常规堆栈) | 容易 (堆栈逻辑清晰) | 困难 (Reactors 堆栈晦涩) |
| **适用场景** | CPU 密集型或旧系统 | IO 密集型 (微服务、网关) | 高流量的流式处理 |

💻 代码示例：ReentrantLock 避免钉住
```java
// ❌ 错误：synchronized 会导致虚拟线程钉住在 Carrier 上
public synchronized void wrongProcess() {
    blockingIOOperation(); // 阻塞期间占用 Carrier
}

// ✅ 正确：ReentrantLock 支持虚拟线程卸载
private final ReentrantLock lock = new ReentrantLock();
public void correctProcess() {
    lock.lock();
    try {
        blockingIOOperation(); // 阻塞期间虚拟线程 Unmount，释放 Carrier
    } finally {
        lock.unlock();
    }
}
```

🔥 实战案例：
在某电商大促活动中，我们将原有的 Tomcat 线程池（200线程）升级为支持虚拟线程的 Web 容器。原本在并发 2000 QPS 时出现的“RejectExecutionException”彻底消失，在 8C16G 机器上轻松支撑 10,000+ QPS，且延迟 P99 从 500ms 降低到 50ms。但上线初期曾因遗留代码中大量使用 `synchronized` 导致 Carrier Thread 被耗尽，监控发现 CPU 利用率极低但吞吐上不去，排查后定位到是 Pinning 问题，替换为 ReentrantLock 后恢复。

## 核心知识点图

<img src="/interview-2026/images/diagram_java-core_sjdk-009.svg" alt="核心知识点图" style="max-width:100%;height:auto;border:1px solid var(--border);border-radius:8px;margin:1em 0;" />

## 记忆要点

- 本质：通过虚拟线程实现同步代码风格高并发，替代复杂的Reactive异步链
- 核心原理：基于Continuation续体，遇阻塞IO则从载体线程Unmount卸载
- 避坑：synchronized或本地方法会导致Pinning(钉住)，高并发下耗尽载体线程
- 解决：摒弃synchronized改用ReentrantLock，且上下文传递改用ScopedValue

## 结构化回答

**30 秒电梯演讲：** JVM管理的轻量级线程，实现“一请求一线程”。打个比方，像Java线程一样写同步代码，像Node.js一样高效处理百万并发。

**展开框架：**
1. **本质** — 通过虚拟线程实现同步代码风格高并发，替代复杂的Reactive异步链
2. **核心原理** — 基于Continuation续体，遇阻塞IO则从载体线程Unmount卸载
3. **避坑** — synchronized或本地方法会导致Pinning(钉住)，高并发下耗尽载体线程

**收尾：** 这三点都能配合实战聊。您想深入聊原理、对比还是避坑？

## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：什么是Project Loom？虚拟… | "什么是Project Loom？虚拟线程如何改变Java并发编程模型？一句话——像Java线程一样写同步代码，像Node.js一样高效处理百万并发。" | 开场钩子 |
| 0:45 | 概念动画/示意图 | "JVM管理的轻量级线程，实现“一请求一线程”——像Java线程一样写同步代码，像Node.js一样高效处理百万并发" | 核心定义 |
| 1:30 | 本质示意 | "通过虚拟线程实现同步代码风格高并发，替代复杂的Reactive异步链" | 要点1 |
| 2:15 | 核心原理示意 | "基于Continuation续体，遇阻塞IO则从载体线程Unmount卸载" | 要点2 |
| 3:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |
