---
id: scen-099
difficulty: L2
category: scenario
subcategory: 存储架构设计
tags:
- 存储选型
- MySQL
- MongoDB
- HBase
- Elasticsearch
- ClickHouse
- Redis
- 选型决策
feynman:
  essence: 根据数据结构、一致性要求及查询模式，匹配最擅长的存储引擎。
  analogy: 像工匠干活，锯木头用电锯，拧螺丝用起子，没有万能工具，只有最合适的工具。
  first_principle: 如何在CAP（一致性、可用性、分区容错性）和读写性能之间找到最佳平衡点？
  key_points:
  - MySQL强事务适合核心业务
  - ES擅长全文检索和聚合分析
  - HBase/ClickHouse搞定海量数据分析
  - Redis负责高性能缓存与计数
follow_up:
- MongoDB和MySQL如何选择？
- 什么场景用HBase？
- ClickHouse适合什么场景？
memory_points:
- 选型决策：强事务选MySQL，模糊搜索选ES，百亿级写选HBase，海量分析选ClickHouse
- DB严禁存大文件/图片，只需存URL，避免Buffer Pool被占满拖垮性能
- 多引擎混合架构：MySQL为主数据源，同步ES做搜索，Flink写CK做BI分析
- MongoDB胜在Schema灵活，HBase基于LSM写入极高但只适合RowKey查询
---

# 如何设计一个海量数据的存储选型方案？MySQL/MongoDB/HBase/ES如何选择？

【场景分析】
海量数据存储选型没有银弹，必须根据业务场景（读写比例、数据量、一致性要求、查询类型）进行权衡。

【数据库特性深度对比】

| 特性 | MySQL | MongoDB | HBase | Elasticsearch | ClickHouse |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **类型** | OLTP (关系型) | OLTP (文档型) | NoSQL (列族) | 搜索引擎 | OLAP (列式) |
| **核心优势** | ACID 事务、复杂查询 | Schema 灵活、水平扩展易 | 写入吞吐量极高、海量存储 | 全文检索、复杂聚合分析 | 极速聚合查询、压缩率高 |
| **写入性能** | 中 (TPS 千级) | 高 (TPS 万级) | 极高 (TPS 十万级+) | 中 (索引构建重) | 高 (批量写入) |
| **查询能力** | SQL、Join、事务 | 灵活 JSON 查询 | RowKey 范围查询 | 全文、Agg、模糊 | SQL (分析类) |
| **数据量级** | 单表 5000万 (需分库分表) | 亿级 (分片) | 千亿/万亿级 | 亿级 | PB 级 |
| **典型场景** | 订单、支付、用户资产 | 日志、评论、CMS、物联网 | 监控日志、轨迹数据、历史流水 | 商品搜索、站内搜索、日志分析 | BI 报表、用户行为分析、大屏 |

【选型决策树】
```
Start: 存储需求
│
├─ 是否有强事务需求 (ACID)?
│  ├─ Yes ──> MySQL / PostgreSQL / OceanBase
│  └─ No ──> 继续判断
│     │
     ├─ 查询模式：模糊搜索 / 全文检索?
     │  ├─ Yes ──> Elasticsearch
     │  └─ No ──> 继续判断
     │     │
          ├─ 数据量级 > 100亿 且 写入量巨大?
          │  ├─ Yes ──> 需要复杂分析?
          │  │           ├─ Yes ──> ClickHouse / Doris
     │     │           └─ No (KV查询) ──> HBase / Cassandra
     │     │
          │  └─ No (数据量中等) ──> Schema 是否频繁变动?
                              ├─ Yes ──> MongoDB
                              └─ No ──> MySQL (无需分库分表) 或 PostgreSQL
```

【架构模式：多引擎组合】
现代互联网架构通常是 "HTAP"（混合事务/分析处理）或 "Polyglot Persistence"（混合存储）架构。

**典型电商架构**：
```
┌─────────────┐   写入   ┌──────────┐   同步   ┌──────────────┐
│   用户下单  │ ───────> │  MySQL   │ ──────> │ Elasticsearch │
│  (OLTP)     │          │ (主数据) │         │  (商品搜索)   │
└─────────────┘          └──────────┘         └──────────────┘
      │                                                │
      │                                                ▼
      │                                        ┌──────────────┐
      │                                        │   用户查询   │
      └────────────────────────────────────────> │  (前端/APP)  │
                                               └──────────────┘

另有一条支流：
用户行为日志 ──> Kafka ──> Flink清洗 ──> ClickHouse/HBase (分析/报表)
```

## 常见考点
1. **MySQL 能存图片/大文件吗？**
   - 技术上可以（BLOB/TEXT），但**严禁**这样做。
   - 原因：严重影响查询性能，占用大量 Buffer Pool，备份恢复极慢。
   - 正确做法：存对象存储（OSS/S3），数据库只存 URL。
2. **MongoDB 和 MySQL 谁更适合做社交关系存储？**
   - 如果关系复杂（如好友的好友，多度查询），图数据库 更好。
   - 如果只是简单的用户资料存储，MongoDB（Schema 灵活）优于 MySQL。
3. **HBase 为什么不适合做随机读？**
   - HBase 是 LSM-Tree 架构，写入是追加顺序写，性能极高；但读取可能需要合并 MemStore 和磁盘上的 HFile，且不支持多列索引，只能通过 RowKey 查询，随机范围查询性能不如 B+ 树结构的 MySQL。


## 记忆要点

- 选型决策：强事务选MySQL，模糊搜索选ES，百亿级写选HBase，海量分析选ClickHouse
- DB严禁存大文件/图片，只需存URL，避免Buffer Pool被占满拖垮性能
- 多引擎混合架构：MySQL为主数据源，同步ES做搜索，Flink写CK做BI分析
- MongoDB胜在Schema灵活，HBase基于LSM写入极高但只适合RowKey查询

## 结构化回答


**30 秒电梯演讲：** 像工匠干活，锯木头用电锯，拧螺丝用起子，没有万能工具，只有最合适的工具。

**展开框架：**
1. **MySQL强事务** — MySQL强事务适合核心业务
2. **ES擅长全文检索** — ES擅长全文检索和聚合分析
3. **HBase/Cl** — ickHouse搞定海量数据分析

**收尾：** MongoDB和MySQL如何选择？


## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：海量数据的存储选型方案 | "海量数据的存储选型方案，一分钟讲透。" | 开场钩子 |
| 0:35 | 生活类比动画 | "打个比方——像工匠干活，锯木头用电锯，拧螺丝用起子，没有万能工具，只有最合适的工具。" | 核心类比 |
| 1:10 | 概念定义动画 | "一句话：根据数据结构、一致性要求及查询模式，匹配最擅长的存储引擎。" | 核心定义 |
| 1:50 | MySQL强事务适合 图解 | "MySQL强事务适合核心业务。" | MySQL强事务适合 |
