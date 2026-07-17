---
id: scen-018
difficulty: L2
category: scenario
subcategory: 缓存架构设计
tags:
- 多级缓存
- CDN
- Caffeine
- 缓存一致性
- Cache-Aside
- 延迟双删
feynman:
  essence: 在不同层级设置缓存防线，逐级拦截请求，最大限度减少穿透到数据库的流量。
  analogy: 像多层安检，村口挡一批、小区门口挡一批、楼门口再挡一批，最后才进屋查户口。
  first_principle: 如何利用存储介质的分层特性，在保证数据一致性的前提下最大化系统的吞吐量？
  key_points:
  - 本地缓存极快但容量小且易不一致，适合读多写少的配置或热点数据
  - CDN适合静态资源，离用户最近
  - Cache-Aside是读写策略的标准答案
  - 通过消息队列或Binlog解决多级缓存的一致性问题
follow_up:
- 如何保证多级缓存的一致性？
- 本地缓存如何选择Caffeine vs Guava？
- 缓存命中率如何监控和优化？
memory_points:
- 缓存链路口诀：CDN静态、Nginx响应、Caffeine本地、Redis分布式
- 性能对比：因本地缓存无网络开销极快（纳秒级），故可保护Redis免受高QPS冲击
- 读写策略：读多写少用Cache-Aside（旁路），更新DB后删缓存而非更新缓存
- 多级一致性保障：DB同步用Canal监听Binlog，Redis同步至本地用MQ广播删除指令
- 本地缓存防脏读：广播删除指令，或设极短TTL（如1分钟）自动过期兜底
---

# 如何设计一个多级缓存架构？包含本地缓存、分布式缓存、CDN。

【场景分析】
多级缓存目标：最大化缓存命中率、最小化请求延迟、减轻后端压力。

【缓存层级与架构图】
1. **浏览器/客户端缓存**：HTTP Cache-Control。
2. **CDN缓存**：静态资源（JS/CSS/图片）、HTML 页面。
3. **Nginx 本地缓存**：Proxy Cache，存放热点 API 响应。
4. **应用本地缓存**：Caffeine/Guava，JVM 堆内内存。
5. **分布式缓存**：Redis Cluster。
6. **数据库**：MySQL。

```text
Client Request
   │
   ▼
┌─────────┐ (1) Hit: Return Static Asset
│   CDN   │
└────┬────┘
     │ (2) Miss: Dynamic Request
     ▼
┌─────────┐ (3) Hit: Nginx Proxy Cache
│ Nginx   │
└────┬────┘
     │ (4) Miss
     ▼
┌─────────────┐ (5) Hit: Microservices Local Cache (Caffeine)
│ Application │
│  Instance   │◄─────┐ (7) Pub/Sub Invalidation Msg
└──────┬──────┘───────┘
       │ (6) Miss
       ▼
┌─────────────┐ (8) Hit: Distributed Cache (Redis)
│  Redis      │◄─────┐ (9) Write-Through/DB Sync
└──────┬──────┘───────┘
       │ (10) Miss
       ▼
┌─────────────┐
│  Database   │
└─────────────┘
```

【缓存读写策略】
1. **Cache-Aside (旁路缓存)**：
   - **读**：读 Cache -> Miss 则读 DB -> 写 Cache。
   - **写**：更新 DB -> 删除 Cache（Delay Double Delete）。
   - *适用*：读多写少。
2. **Write-Through**：
   - 写 Cache 时同步写 DB。
   - *适用*：一致性要求高，写性能要求不高。
3. **Write-Behind (Write-Back)**：
   - 只写 Cache，异步批量写 DB。
   - *风险*：Cache 宕机数据丢失。

【多级缓存一致性保障】
1. **Redis -> 本地缓存**：
   - **消息机制**：利用 Redis Pub/Sub 或 RocketMQ。当 Key 变更时，广播消息给所有应用实例，删除本地 Caffeine 缓存。
   - **版本号/Tag**：数据带上版本号，本地缓存校验版本。
2. **DB -> Redis**：
   - **Canal监听**：伪装 MySQL Slave，解析 Binlog，发送 MQ 更新/删除 Redis。
   - **延迟双删**：先删 Redis -> 更新 DB -> 休眠 500ms -> 再删 Redis（防止并发旧数据覆盖）。

【性能数据参考】
- **L1 Cache (Caffeine)**: 纳秒级 (~1,000,000 ops/s)，无网络开销。
- **L2 Cache (Redis)**: 毫秒级 (~1-5ms)，有网络开销。
- **L3 (DB)**: 10ms - 100ms+。

## 常见考点
1. **为什么需要本地缓存？直接查 Redis 不行吗？**
   - 本地缓存无网络序列化/反序列化开销，速度极快（纳秒级）；保护 Redis，降低 Redis QPS 峰值。
2. **本地缓存如何解决各实例间数据不一致的问题？**
   - 利用消息总线广播删除指令（而非更新，因为是弱一致），或者设置较短的 TTL（如1分钟）自动过期。
3. **Nginx 缓存和应用缓存冲突怎么办？**
   - 一般 Nginx 缓存 TTL 设置较长（如静态资源），应用缓存 TTL 较短。在动态 API 场景，通常不开启 Nginx 缓存或通过 `proxy_cache_bypass` 控制绕过。

## 记忆要点

- 缓存链路口诀：CDN静态、Nginx响应、Caffeine本地、Redis分布式
- 性能对比：因本地缓存无网络开销极快（纳秒级），故可保护Redis免受高QPS冲击
- 读写策略：读多写少用Cache-Aside（旁路），更新DB后删缓存而非更新缓存
- 多级一致性保障：DB同步用Canal监听Binlog，Redis同步至本地用MQ广播删除指令
- 本地缓存防脏读：广播删除指令，或设极短TTL（如1分钟）自动过期兜底

## 结构化回答


**30 秒电梯演讲：** 像多层安检，村口挡一批、小区门口挡一批、楼门口再挡一批，最后才进屋查户口。

**展开框架：**
1. **本地缓存极快但容量小且易不一致** — 适合读多写少的配置或热点数据
2. **CDN适合静态资源** — CDN适合静态资源，离用户最近
3. **Cache** — Aside是读写策略的标准答案

**收尾：** 如何保证多级缓存的一致性？


## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：多级缓存架构 | "多级缓存架构，一分钟讲透。" | 开场钩子 |
| 0:35 | 生活类比动画 | "打个比方——像多层安检，村口挡一批、小区门口挡一批、楼门口再挡一批，最后才进屋查户口。" | 核心类比 |
| 1:10 | 概念定义动画 | "一句话：在不同层级设置缓存防线，逐级拦截请求，最大限度减少穿透到数据库的流量。" | 核心定义 |
| 1:50 | 本地缓存极快但容量小 图解 | "本地缓存极快但容量小且易不一致，适合读多写少的配置或热点数据。" | 本地缓存极快但容量小 |
