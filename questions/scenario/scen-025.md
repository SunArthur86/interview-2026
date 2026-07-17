---
id: scen-025
difficulty: L2
category: scenario
subcategory: 消息队列应用
tags:
- 顺序消费
- Kafka
- RocketMQ
- 分区有序
- MessageQueueSelector
- 状态机
feynman:
  essence: 将同一业务键的消息发往同一队列，单线程顺序处理。
  analogy: 像单车道排队过收费站，只有前一辆车通过，后一辆车才能进，保证先进先出。
  first_principle: 如何在分布式多线程环境中保证特定数据流的因果一致性？
  key_points:
  - 生产端按业务Key（如订单ID）分区
  - 同一Partition内消息天然有序
  - 消费端单线程绑定队列
  - 牺牲并发度换取顺序性
follow_up:
- 顺序消费如何处理积压？
- 全局顺序为什么性能差？
- 如何检测消息乱序？
memory_points:
- 生产端防丢：同步发送+acks=all（等所有副本确认）+开启幂等防重试重复
- Broker端防丢：多副本同步复制（factor≥3, min.insync≥2），严禁落后副本参与脏选举
- 消费端防丢：关闭自动提交Offset，业务逻辑处理完毕后再手动Ack
- 重试兜底：多次消费失败必须转入死信队列（DLQ）进行人工干预，切忌直接丢弃
- 全链路铁律：Producer重试落库表，Broker同步刷盘防断电，Consumer手动提交加幂等
---

# 如何保证消息的顺序消费？

保证消息队列消息不丢失的全链路方案（以 Kafka/RocketMQ 为例）：

**三个环节都可能丢消息：**

**1. 生产者端（发送丢失）：**
- 同步发送 + 重试：`acks=all`（等待所有 ISR 副本确认）+ `retries > 0`。
- 开启幂等：`enable.idempotence=true`，防止重试导致重复。
- 用事务保证「发送成功」和「业务操作」原子。
- 异步发送需处理回调失败（重发或落库补偿）。

**2. Broker 端（存储丢失）：**
- 副本数 ≥ 3：`replication.factor ≥ 3`，`min.insync.replicas ≥ 2`。
- 关闭_unclean leader 选举：`unclean.leader.election.enable=false`，禁止落后副本当 leader。
- 刷盘策略：RocketMQ 同步刷盘（ASYNC_FLUSH → SYNC_FLUSH），Kafka 依赖 OS PageCache（副本比单机刷盘更可靠）。

**3. 消费者端（消费丢失）：**
- 关闭自动提交 offset：`enable.auto.commit=false`，业务处理完手动提交。
- 消费失败重试 + 死信队列（DLQ）：多次重试失败转 DLQ 人工处理。
- 幂等消费：防止重试导致重复处理（用业务唯一键去重）。

【实战案例】
**异步回调的坑**：某项目使用异步发送Kafka消息，Callback仅打印日志未重试。当Kafka集群短暂抖动时，生产者虽已向用户返回“成功”，但消息实际未发送成功，导致资金对账平不了。改进：改为同步发送或异步失败后写入本地“发送失败表”，由定时任务兜底补偿。

【代码示例（Java Producer 最佳实践）】
```javanProperties props = new Properties();
// 1. 保证可靠性：等待所有ISR副本确认
props.put("acks", "all");
// 2. 开启幂等性，防止重试导致重复
props.put("enable.idempotence", "true");
// 3. 重试次数
props.put("retries", "3");

KafkaProducer<String, String> producer = new KafkaProducer<>(props);
// 发送消息
producer.send(new ProducerRecord<>("topic", "key", "value"));
```

【方案对比（可靠性 vs 性能）】
| 配置项 | 高可靠配置 | 高性能配置 | 说明 |
| :--- | :--- | :--- | :--- |
| **acks (Kafka)** | all (或 -1) | 1 或 0 | 0=不等待确认；1=只等Leader；all=等所有ISR |
| **retries** | Integer.MAX_VALUE | 0 或 3 | 高可靠模式无限重试直到成功 |
| **刷盘模式** | 同步刷盘 | 异步刷盘 | 同步刷盘性能较差但防断电丢数据 |
| **副本数** | 3 | 1 | 副本数越多，磁盘可用性越高 |

【全链路总结】
- 生产者：确认机制 + 重试 + 本地落库兜底
- Broker：多副本同步复制 + 防止脏选举
- 消费者：手动Ack + 业务幂等

## 记忆要点

- 生产端防丢：同步发送+acks=all（等所有副本确认）+开启幂等防重试重复
- Broker端防丢：多副本同步复制（factor≥3, min.insync≥2），严禁落后副本参与脏选举
- 消费端防丢：关闭自动提交Offset，业务逻辑处理完毕后再手动Ack
- 重试兜底：多次消费失败必须转入死信队列（DLQ）进行人工干预，切忌直接丢弃
- 全链路铁律：Producer重试落库表，Broker同步刷盘防断电，Consumer手动提交加幂等

## 结构化回答




**30 秒电梯演讲：** 像单车道排队过收费站，只有前一辆车通过，后一辆车才能进，保证先进先出。

**展开框架：**
1. **Key** — 生产端按业务Key（如订单ID）分区
2. **Partition** — 同一Partition内消息天然有序
3. **消费端单线程** — 消费端单线程绑定队列

**收尾：** 顺序消费如何处理积压？




## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：保证消息的顺序消费 | "保证消息的顺序消费，一分钟讲透。" | 开场钩子 |
| 0:35 | 生活类比动画 | "打个比方——像单车道排队过收费站，只有前一辆车通过，后一辆车才能进，保证先进先出。" | 核心类比 |
| 1:10 | 概念定义动画 | "一句话：将同一业务键的消息发往同一队列，单线程顺序处理。" | 核心定义 |
| 1:50 | 生产端按业务Key( 图解 | "生产端按业务Key(如订单ID)分区。" | 生产端按业务Key( |
