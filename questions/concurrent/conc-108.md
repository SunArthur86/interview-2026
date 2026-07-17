---
id: conc-108
difficulty: L3
category: concurrent
feynman:
  essence: 进程是资源容器，线程是执行实体，有多种创建和状态流转方式。
  analogy: 进程是项目组，线程是组员。项目组有资源，组员干活。
  first_principle: 程序如何在操作系统中被组织、调度和执行？
  key_points:
  - Java线程创建主要有三种方式
  - RUNNABLE包含OS的就绪和运行态
  - 线程状态流转涉及阻塞和等待
  - 线程崩溃会影响所属进程
memory_points:
- 创建方式：继承Thread、实现Runnable、实现Callable(带返回值)、使用线程池(推荐)
- 状态流转：NEW -> RUNNABLE -> (BLOCKED/WAITING/TIMED_WAITING) -> TERMINATED
- 注意区分：Java的RUNNABLE包含了OS层面的就绪和运行状态，BLOCKED专指等待内置锁
- sleep与wait：sleep不释放锁，wait释放锁且必须在同步块中调用
- 核心禁忌：生产环境严禁直接new Thread，因为无限制创建会导致内存溢出和CPU频繁上下文切换
---

# 什么是进程线程基础？

### 进程线程基础

**1. 什么是进程和线程**
- **进程**：系统运行程序的基本单位，拥有独立的内存空间和资源。在 Java 中启动 `main` 函数即启动了一个 JVM 进程。
- **线程**：进程中的执行单元，操作系统调度的最小单位。同一进程的线程共享内存空间，但独立执行流。

**2. Java 创建线程的方式**
1. **继承 Thread 类**：重写 `run()` 方法。
2. **实现 Runnable 接口**：实现 `run()` 方法，提交给 `Thread` 执行。
3. **使用 Callable/Future**：实现 `call()` 方法，支持返回值和抛出异常（配合 `FutureTask`）。
4. **使用 Executor 框架**：利用线程池（如 `ThreadPoolExecutor`）管理和复用线程，这是生产环境推荐方式。

**3. 实战案例**
在一次代码审查中，我发现同事在 `for` 循环里直接 `new Thread()` 处理异步日志写入。压测时由于线程数激增导致上下文切换频繁且 OOM。改为使用 `FixedThreadPool` 后，不仅限制了最大并发数，还通过复用线程将请求响应耗时降低了 40%。

**4. 代码示例（线程池与状态捕获）**
```java
// 推荐使用 ThreadPoolExecutor
ExecutorService executor = new ThreadPoolExecutor(
    10, 20, 60L, TimeUnit.SECONDS, new ArrayBlockingQueue<>(100));

// 提交任务并获取返回值
Future<String> future = executor.submit(() -> {
    Thread.sleep(1000); // 模拟耗时操作
    return "Task Completed";
});
```

**5. 线程的生命周期**
1. **NEW (新建)**：线程对象创建但未调用 `start()`。
2. **RUNNABLE (就绪/运行)**：调用 `start()` 后，处于就绪或运行状态。
3. **BLOCKED (阻塞)**：等待监视器锁（如 `synchronized` 竞争失败），在锁池中等待。
4. **WAITING (等待)**：无限期等待其他线程显式唤醒（如 `wait()`, `join()`, `LockSupport.park()`），在等待池中。
5. **TIMED_WAITING (超时等待)**：有限期等待（如 `sleep()`, `wait(timeout)`, `parkNanos()`）。
6. **TERMINATED (终止)**：执行完毕或异常退出。

**状态转换流程图：**
```text

          start()
    NEW ─────────────> RUNNABLE
                            │
                            │ sleep(t) / wait(t) / join(t)
                            ↓
               TIMED_WAITING (超时自动唤醒)
                            │
                            ▼
           ┌─────────────────────────────┐
           │                             │
    wait() / join()              竞争锁失败
    (需 notify/notifyAll)             │
           │                             │
           ▼                             ▼
    WAITING <────────────────── BLOCKED
     ▲      ▲ 获得锁                  │
     │      │                          │
     └──────┴──────────────────────────┘
                 run() 结束
                   │
                   ▼
             TERMINATED
```

**注意**：
- Java 的 `RUNNABLE` 状态涵盖了操作系统层面的 **Ready** 和 **Running** 状态。
- `BLOCKED` 仅指等待 `synchronized` 监视器锁，而 `WAITING/TIMED_WAITING` 可以指等待任意条件或显式锁（如 `ReentrantLock` 的 Condition）。

## 常见考点
1. `sleep()` 和 `wait()` 的区别？
   - `sleep()` 是 Thread 类静态方法，不释放锁；`wait()` 是 Object 类方法，释放锁并必须在同步块中调用。
2. 为什么不建议显式创建线程（`new Thread()`）？
   - 线程创建销毁开销大；无限制创建可能导致 OOM；缺乏统一的管理和监控。
3. 线程池中线程复用原理？
   - 线程池中的 Worker 线程在执行完一个任务后，不会退出，而是通过 `while (task != null || (task = getTask()) != null)` 循环不断从阻塞队列中获取新任务执行，从而实现复用。

## 记忆要点

- 创建方式：继承Thread、实现Runnable、实现Callable(带返回值)、使用线程池(推荐)
- 状态流转：NEW -> RUNNABLE -> (BLOCKED/WAITING/TIMED_WAITING) -> TERMINATED
- 注意区分：Java的RUNNABLE包含了OS层面的就绪和运行状态，BLOCKED专指等待内置锁
- sleep与wait：sleep不释放锁，wait释放锁且必须在同步块中调用
- 核心禁忌：生产环境严禁直接new Thread，因为无限制创建会导致内存溢出和CPU频繁上下文切换

## 结构化回答


**30 秒电梯演讲：** 进程是项目组，线程是组员。项目组有资源，组员干活。

**展开框架：**
1. **Java线程创建** — Java线程创建主要有三种方式
2. **RUNNABLE** — 包含OS的就绪和运行态
3. **线程状态流转涉及** — 线程状态流转涉及阻塞和等待

**收尾：** 这是我实战中的理解，您想深入哪一段？


## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：什么是进程线程基础 | 今天这道题：什么是进程线程基础。30 秒先给你讲清楚。 | 开场钩子 |
| 0:20 | 核心概念动画/示意图 | 进程是项目组，线程是组员。项目组有资源，组员干活。 | 核心概念 |
| 0:40 | Java示意图 | Java线程创建主要有三种方式 | Java |
| 1:10 | RUNNABLE示意图 | RUNNABLE包含OS的就绪和运行态 | RUNNABLE |
| 1:40 | 总结卡 + 下期预告 | 记住今天这几个关键词，面试一定用得上。下期见。 | 收尾 |
