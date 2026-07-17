---
id: scen-089
difficulty: L3
category: scenario
subcategory: 稳定性与容灾
tags:
- 实时计算
- Flink
- 流处理
- 窗口
- Watermark
- CEP
- Checkpoint
- 状态管理
feynman:
  essence: 基于流处理的低延迟、高吞吐无界数据实时计算框架。
  analogy: 像自来水管，数据像水流一样源源不断流进来，经过过滤（算子）实时流出清水。
  first_principle: 如何对无限产生的数据进行低延迟、高准确度的实时统计与分析？
  key_points:
  - 流批一体：Flink处理无界流，支持事件时间和窗口
  - 状态管理：Keyed State记录中间结果，RocksDB持久化
  - 容错机制：Checkpoint定期快照，Exactly-Once语义
  - 时间语义：Watermark处理乱序数据，保证计算准确
follow_up:
- Flink如何保证Exactly-Once？
- Watermark如何处理乱序数据？
- 状态后端如何选择？
memory_points:
- Watermark防乱序：水位线=最大事件时间-延迟阈值，触发窗口计算且防阻塞。
- Exactly-Once端到端：依赖Checkpoint+Barrier对齐，结合Sink端两阶段提交(2PC)。
- State后端对比：Memory纯内存极快易OOM，RocksDB存磁盘安全支持TB级但较慢。
- 计算场景口诀：聚合用Window，去重用HLL，风控用CEP。
---

# 如何设计一个系统来处理海量数据的实时计算？Flink/Spark Streaming。

【场景分析】
实时计算需求：实时大屏、实时风控、实时推荐、实时监控告警。

【批处理 vs 流处理】
- 批处理：处理有界数据，吞吐量高，延迟分钟级
- 流处理：处理无界数据，延迟毫秒级
- Lambda架构：批+流并行，批修正流
- Kappa架构：只流处理（推荐）

【Flink核心概念】
1. Source：数据源（Kafka/Socket/File）
2. Transformation：算子（Map/Filter/KeyBy/Window）
3. Sink：输出（Redis/ES/Kafka/DB）
4. Window：窗口（滚动/滑动/会话）
5. State：状态管理（ValueState/ListState/MapState）
6. Time：事件时间/处理时间/注入时间
7. Watermark：处理乱序事件

【实时计算场景实例】

1. 实时GMV：
```java
orders
    .assignTimestampsAndWatermarks(...)
    .keyBy(Order::getCategory)
    .window(TumblingEventTimeWindows.of(Time.minutes(1)))
    .aggregate(new SumAggregator("amount"))
    .addSink(new RedisSink());
```

2. 实时UV（独立访客）：
```java
events
    .keyBy(e → e.getDate() + "_" + e.getPage())
    .flatMap(new HyperLogLogMapper())  // 用HLL去重
    .addSink(new RedisSink());
```

3. 实时TopN：
```java
products
    .keyBy(Product::getCategoryId)
    .window(SlidingEventTimeWindows.of(Time.hours(1), Time.minutes(5)))
    .aggregate(new CountAndTopN(10))
    .addSink(new RedisSink());
```

4. CEP（复杂事件处理）— 风控：
```java
// 10秒内连续3次登录失败 → 锁定
Pattern<LoginEvent, ?> pattern = Pattern
    .<LoginEvent>begin("fails")
    .where(e → !e.isSuccess())
    .timesOrMore(3)
    .within(Time.seconds(10));

CEP.pattern(loginStream, pattern)
    .select(events → new Alert("连续登录失败"))
    .addSink(new AlertSink());
```

【Flink State管理】
- State Backend：MemoryStateBackend / RocksDBStateBackend
- Checkpoint：定期快照状态到外部存储
- 精确一次语义：两阶段提交
- 状态TTL：自动清理过期状态

【容错机制】
- Checkpoint：周期性保存状态快照
- Savepoint：手动触发的完整快照
- 故障恢复：从Checkpoint恢复
- Flink Kafka Exactly-Once：事务性Sink

【性能优化】
- 并行度：根据数据量和集群资源调整
- 窗口大小：大窗口减少计算频率
- 异步IO：外部查询用AsyncFunction
- 背压：消费者跟不上时自动降速

## 常见考点
1. **Flink 如何保证 Exactly-Once 语义？**
   - **内部**：通过 Checkpoint 和 Barrier 对齐机制，确保状态的一致性快照。
   - **端到端**：需要外部系统支持（如 Kafka 的事务机制或幂等写入）。Flink 利用 Two-Phase Commit (2PC) 协议，数据预提交后再正式提交，配合 Checkpoint 实现端到端 Exactly-Once。
2. **Watermark 是如何解决乱序数据的？**
   - Watermark = 当前最大事件时间 - 最大允许乱序时间。
   - 窗口计算的触发条件是：Watermark 时间 >= 窗口结束时间。早到的数据正常缓存，迟到的数据（时间 < Watermark）默认丢弃或进入侧输出流。Watermark 确保了「迟到的数据」不会无限期阻塞窗口计算。
3. **RocksDB State Backend 为什么比 Memory State Backend 慢但更稳定？**
   - Memory State Backend 将状态存在 JVM 堆内存，存取极快但受限于 GC 和内存大小，状态过大容易 OOM。
   - RocksDB 将状态序列化后存于本地磁盘，支持海量状态（TB级），不受 JVM 限制，但涉及序列化/反序列化和磁盘 IO，性能较低，适合大状态场景。

## 记忆要点

- Watermark防乱序：水位线=最大事件时间-延迟阈值，触发窗口计算且防阻塞。
- Exactly-Once端到端：依赖Checkpoint+Barrier对齐，结合Sink端两阶段提交(2PC)。
- State后端对比：Memory纯内存极快易OOM，RocksDB存磁盘安全支持TB级但较慢。
- 计算场景口诀：聚合用Window，去重用HLL，风控用CEP。

## 结构化回答

**30 秒电梯演讲：** 基于流处理的低延迟、高吞吐无界数据实时计算框架。打比方——像自来水管，数据像水流一样源源不断流进来，经过过滤(算子)实时流出清水。落到工程上，Flink处理无界流，支持事件时间和窗口。

**展开框架：**
1. **流批一体** — Flink处理无界流，支持事件时间和窗口
2. **状态管理** — Keyed State记录中间结果，RocksDB持久化
3. **容错机制** — Checkpoint定期快照，Exactly-Once语义

**收尾：** 这几个点都能配合实战展开。您想继续聊哪个追问——比如 「Flink如何保证Exactly-Once」 或者 「Watermark如何处理乱序数据」？

## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：系统来处理海量数据的实时计算 | "系统来处理海量数据的实时计算，这题我会分三步讲。" | 开场钩子 |
| 0:41 | 概念定义动画 | "一句话：基于流处理的低延迟、高吞吐无界数据实时计算框架。" | 核心定义 |
| 1:22 | 生活类比动画 | "打个比方——像自来水管，数据像水流一样源源不断流进来，经过过滤(算子)实时流出清水。" | 核心类比 |
| 2:03 | 流批一体 图解 | "Flink处理无界流，支持事件时间和窗口。" | 流批一体 |
| 2:50 | 状态管理 图解 | "Keyed State记录中间结果，RocksDB持久化。" | 状态管理 |
