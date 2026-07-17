---
id: core-123
difficulty: L2
category: java-core
feynman:
  essence: 生产、存储、消费三端全链路确认
  analogy: 快递发货要确认揽收、入仓、签收
  first_principle: 如何保证分布式系统中的数据可靠性
  key_points:
  - 生产端：发确认、重试、事务
  - Broker：多副本、持久化、刷盘
  - 消费端：手动提交、幂等处理
memory_points:
- 全局：保证不丢失必须死磕「生产者、Broker、消费者」全链路
- 生产端：开启 acks=all 确认机制并加重试，配合本地消息表兜底
- Broker端：Kafka靠多副本同步，RocketMQ靠同步刷盘防宕机丢数据
- 消费端：关闭自动提交，必须确保业务处理成功后再手动提交 offset
- 幂等性：重试机制会导致重复投递，所以消费端必须做幂等处理
---

# 如何保证消息队列（MQ）中的消息不丢失？

保证消息不丢失需覆盖「生产者 → Broker → 消费者」三个环节：

**1. 生产者端（发送丢失）：**
- **确认机制：** Kafka 用 `acks=all`（等所有 ISR 副本确认）；RabbitMQ 用 confirm 模式。
- **重试：** 发送失败自动重试（设 retries > 0）。
- **幂等：** 开启幂等（Kafka `enable.idempotence=true`）防止重试导致重复。
- **事务消息：** RocketMQ 支持事务消息，保证「本地事务 + 发送」原子。
- **异步回调：** 异步发送必须处理失败回调（重发或落库补偿）。

**2. Broker 端（存储丢失）：**
- **多副本：** Kafka `replication.factor ≥ 3`，`min.insync.replicas ≥ 2`。
- **禁止 unclean leader：** `unclean.leader.election.enable=false`，防止落后副本当 leader 丢数据。
- **刷盘策略：** RocketMQ 同步刷盘（SYNC_FLUSH）保证写入磁盘才返回；Kafka 依赖副本（比单机刷盘可靠）。
- **持久化：** 消息持久化到磁盘，非纯内存。

**3. 消费者端（消费丢失）：**
- **手动提交 offset：** 关闭自动提交（`enable.auto.commit=false`），业务处理完手动提交。
- **幂等消费：** 防止重试导致重复处理（业务唯一键去重）。
- **失败重试 + 死信队列：** 多次重试失败转 DLQ 人工处理。
- **同步消费：** 不要用自动 ack，确保业务成功后才 ack。

**实战案例**：某电商大促期间，由于生产者配置了 `acks=1`（仅 Leader 确认），Broker Leader 在同步给 Follower 前宕机，导致消息丢失，订单金额对不上。事后修正为 `acks=all` 并配合本地消息表做兜底，彻底解决数据一致性问题。

**代码示例**（Java - Kafka Producer 发送）:
```javanProperties props = new Properties();
props.put("bootstrap.servers", "localhost:9092");
props.put("acks", "all"); // 等待所有 ISR 副本确认
props.put("retries", 3); // 发送失败重试 3 次
props.put("enable.idempotence", true); // 开启幂等性

Producer<String, String> producer = new KafkaProducer<>(props);
try {
    // 异步发送带回调
    producer.send(new ProducerRecord<>("topic", "key", "value"), (metadata, exception) -> {
        if (exception != null) {
            // 记录日志或落库兜底，防止静默丢失
            System.err.println("Send failed: " + exception.getMessage());
        }
    });
} finally {
    producer.close();
}
```

**对比表格：**

| 环节 | 核心配置/策略 | 风险点 | 解决方案 |
| :--- | :--- | :--- | :--- |
| **生产者** | `acks=all`, Retries, 异步回调 | 网络抖动导致丢包 | 确认机制 + 本地消息表定时补发 |
| **Broker (Kafka)** | `replication.factor=3`, `min.insync.replicas=2` | 节点宕机未同步 | 禁止 unclean leader 选举 |
| **Broker (RocketMQ)** | 同步刷盘 (SYNC_FLUSH), 异步复制 | 断电丢失内存数据 | 同步刷盘牺牲性能换高可靠 |
| **消费者** | 手动 Commit (enable.auto.commit=false) | 业务报错但已提交 Offset | 业务逻辑处理成功后再提交 Offset |

**## 常见考点**
1.  **Kafka 的 `acks=0`, `acks=1`, `acks=-1/all` 的区别？**
    -   `0`：生产者发送后不等待 Broker 响应（最快，最易丢）。
    -   `1`：等待 Leader 写入成功（折中，Leader 挂了可能丢）。
    -   `all`：等待 Leader 和所有 ISR 中的 Follower 写入成功（最慢，最可靠）。
2.  **消息队列如何保证顺序消费？**
    -   发送端：通过 Partition Key 将有序消息发到同一分区。
    -   消费端：单线程消费同一分区（或者同一分区的消费线程池串行化），避免并发处理乱序。

## 记忆要点

- 全局：保证不丢失必须死磕「生产者、Broker、消费者」全链路
- 生产端：开启 acks=all 确认机制并加重试，配合本地消息表兜底
- Broker端：Kafka靠多副本同步，RocketMQ靠同步刷盘防宕机丢数据
- 消费端：关闭自动提交，必须确保业务处理成功后再手动提交 offset
- 幂等性：重试机制会导致重复投递，所以消费端必须做幂等处理

## 结构化回答

**30 秒电梯演讲：** 生产、存储、消费三端全链路确认。打个比方，快递发货要确认揽收、入仓、签收。

**展开框架：**
1. **全局** — 保证不丢失必须死磕「生产者、Broker、消费者」全链路
2. **生产端** — 开启 acks=all 确认机制并加重试，配合本地消息表兜底
3. **Broker端** — Kafka靠多副本同步，RocketMQ靠同步刷盘防宕机丢数据

**收尾：** 我在项目里踩过坑——某电商大促期间，由于生产者配置了 `acks=1`（仅 Leader 确认），Broker Leader 在同步给 Follower 前宕机，导致消息丢失，订单金额对不上。您想深入聊哪一段：原理、避坑还是对比选型？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：如何保证消息队列（MQ）中的消息不丢… | "如何保证消息队列（MQ）中的消息不丢失？一句话——快递发货要确认揽收、入仓、签收。" | 开场钩子 |
| 0:40 | 概念动画/示意图 | "生产、存储、消费三端全链路确认——快递发货要确认揽收、入仓、签收" | 核心定义 |
| 1:20 | 全局示意 | "保证不丢失必须死磕「生产者、Broker、消费者」全链路" | 要点1 |
| 2:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |
