---
id: conc-128
difficulty: L2
category: concurrent
feynman:
  essence: 定义线程池的扩容规则、任务缓冲机制及拒绝策略。
  analogy: 就像开公司，定几个正式工，满员了把简历放进人才库，实在忙不过头再招临时工，人都招不进去了就拒简历。
  first_principle: 如何定义任务分配的优先级和资源上限以保证系统稳定？
  key_points:
  - corePoolSize为核心常备线程
  - maximumPoolSize为最大承载量
  - workQueue为任务缓冲区
  - handler为过载时的兜底策略
memory_points:
- 7参数口诀：核心、最大、存活时、计时单位、任务队列、线程工厂、拒绝策略
- 核心(core)默认不回收，最大(max)限定上限，存活时间针对非核心线程
- 任务队列与拒绝策略是限流与兜底关键
- 配置策略：CPU密集型设为 N+1，IO密集型设为 2N (N为CPU核心数)
---

# 线程池的7个核心参数是什么？

ThreadPoolExecutor的7个参数：

1. **corePoolSize**：核心线程数，即使空闲也不会被回收（除非设置allowCoreThreadTimeOut）。
2. **maximumPoolSize**：最大线程数。
3. **keepAliveTime**：非核心线程的空闲存活时间。
4. **unit**：keepAliveTime的时间单位。
5. **workQueue**：任务队列，如LinkedBlockingQueue、ArrayBlockingQueue、SynchronousQueue。
6. **threadFactory**：线程工厂，用于创建线程（可自定义线程名，便于排查监控，如使用 Guava 的 ThreadFactoryBuilder）。
7. **handler**：拒绝策略，任务无法执行时的处理方式。

阿里巴巴规范建议：不要使用Executors创建线程池（FixedThreadPool和CachedThreadPool的队列/线程数无限制可能导致OOM），应该手动创建ThreadPoolExecutor。

#### 参数配置策略补充
- **CPU 密集型**：`corePoolSize = CPU 核心数 + 1`（减少上下文切换）。
- **IO 密集型**：`corePoolSize = CPU 核心数 * 2`（通常建议设置更大，因为大部分时间线程在等待 IO，利用 CPU 并行处理其他线程）。

## 常见考点
1. **核心线程数设置为0会发生什么？**（任务来了会先入队，如果队列为 SynchronousQueue 则直接走拒绝策略或创建非核心线程）
2. **线程池的线程数如何根据业务类型（IO密集/CPU密集）进行调优？**
3. **`allowCoreThreadTimeOut` 设置为 true 后，线程池的行为会有什么变化？**
4. **使用不同类型的 `workQueue` 对线程池的运行有什么影响？**（考察有界/无界队列对流量控制和 OOM 的影响）

## 记忆要点

- 7参数口诀：核心、最大、存活时、计时单位、任务队列、线程工厂、拒绝策略
- 核心(core)默认不回收，最大(max)限定上限，存活时间针对非核心线程
- 任务队列与拒绝策略是限流与兜底关键
- 配置策略：CPU密集型设为 N+1，IO密集型设为 2N (N为CPU核心数)

## 结构化回答


**30 秒电梯演讲：** 就像开公司，定几个正式工，满员了把简历放进人才库，实在忙不过头再招临时工，人都招不进去了就拒简历。

**展开框架：**
1. **corePool** — Size为核心常备线程
2. **maximumP** — oolSize为最大承载量
3. **workQueu** — workQueue为任务缓冲区

**收尾：** 这是我实战中的理解，您想深入哪一段？


## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：线程池的7个核心参数是什么 | 今天这道题：线程池的7个核心参数是什么。30 秒先给你讲清楚。 | 开场钩子 |
| 0:20 | 核心概念动画/示意图 | 就像开公司，定几个正式工，满员了把简历放进人才库，实在忙不过头再招临时工，人都招不进去了就拒简历。 | 核心概念 |
| 0:40 | corePoolSize示意图 | corePoolSize为核心常备线程 | corePoolSize |
| 1:10 | 总结卡 + 下期预告 | 记住今天这几个关键词，面试一定用得上。下期见。 | 收尾 |
