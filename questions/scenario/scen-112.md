---
id: scen-112
difficulty: L4
category: scenario
subcategory: 高并发系统设计
tags:
- 秒杀
- 超卖
- 高并发
feynman:
  essence: Redis 原子扣减，数据库异步落地。
  analogy: 像抢票：进场前先验票销票（Redis），进去后再登记身份（DB），票没了直接拦。
  first_principle: 如何在极高并发下保证库存数量绝对准确？
  key_points:
  - Redis Lua脚本保证扣减原子性
  - 乐观锁更新DB，强一致性但慢
  - 扣减成功发MQ，异步落库解耦
  - 超时未支付必须回滚库存
follow_up:
- Redis 扣减成功但 DB 扣减失败（MQ 消费失败）怎么办？库存如何回滚？
- 如果 Redis 宕机，库存数据丢失怎么恢复？
- 本地预扣减方案如何保证多实例不超卖？
memory_points:
- 超卖根因：查库存与扣减非原子操作，导致并发读旧值
- DB兜底层：UPDATE stock SET count=count-1 WHERE id=? AND count>0 利用了行锁
- 极致性能：用Redis Lua脚本做GET与DECR的原子扣减，承压10万+QPS
- 全链路架构：前置限流削峰，Redis Lua扣减，MQ异步落库，DB乐观锁兜底
---

# 秒杀系统如何做到「绝不超卖」？从缓存到数据库的全链路库存扣减方案。

【超卖根因】并发扣减时「查库存 → 判断 >0 → 扣减」非原子操作，多个线程同时读到库存=1。

【防超卖方案】
方案一：DB 乐观锁。UPDATE stock SET count = count - 1 WHERE id = ? AND count > 0。原子操作，count > 0 保证不超卖。优点：简单、绝对正确。缺点：DB 行锁瓶颈（单行约 2000-5000 QPS）。

方案二：Redis 原子扣减（推荐）。用 Lua 脚本：先 GET 库存，判断 >0 则 DECR，返回成功/失败。整个脚本由 Redis 保证原子性。优点：10万+ QPS。Redis 扣减成功后异步同步到 DB（MQ + 消费者更新 DB）。

方案三：Redis + 本地预扣减（极致性能）。应用本地 AtomicInteger 预扣减，定期从 Redis 拉取库存配额到本地。

【全链路防超卖架构】
```
┌─────────────┐     ┌──────────┐     ┌─────────────┐     ┌─────────┐     ┌───────────┐     ┌─────────────┐
│  用户请求   │ ──> │  Nginx   │ ──> │  API 网关   │ ──> │  秒杀   │ ──> │ Redis Lua │ ──> │  MQ 消息队列 │
│ (高频点击)  │     │(限流/静态)│     │ (鉴权/限流) │     │  服务   │     │ (原子扣减) │     │ (削峰填谷)  │
└─────────────┘     └──────────┘     └─────────────┘     └─────────┘     └───────────┘     └─────────────┘
                                                            │                │
                                                            │ 失败           │ 成功          │       ┌─────────────┐
                                                            ▼                ▼               │       │  数据库 DB   │
                                                     ┌──────────┐   ┌──────────┐          └──> │ (创建订单) │
                                                     │ 直接返回 │   │ 返回排队 │                  └─────────────┘
                                                     │ "售罄"  │   │ "排队中" │                         ▲
                                                     └──────────┘   └──────────┘                         │
                                                                                                  │
                                    ┌──────────────────────────────────────────────────────────────┘
                                    │
                         ┌──────────▼──────────┐
                         │    异步消费者       │
                         │ (消费MQ创建订单)    │
                         │ DB事务:             │
                         │ 1.INSERT order      │

---

**【实战案例】**
某次秒杀活动，Redis 库存扣减正常，但最终 DB 订单表出现了库存为 0 仍生成的订单（超卖）。排查发现是 MQ 消费者处理消息时，为了性能做了 `INSERT` 后再异步扣减 DB 库存，导致并发下 DB 层没守住。修正为先 `UPDATE stock` 扣减库存（带行锁），成功后再 `INSERT order`，利用 DB 事务 ACID 特性兜底。

**【代码示例：Redis Lua 原子扣减脚本】
Lua (Redis Script)
```lua
-- KEYS[1]: 库存Key, ARGV[1]: 扣减数量(通常为1)
local stock = tonumber(redis.call('GET', KEYS[1]))
if stock == nil then 
    return -1 -- 商品不存在
end
if stock >= tonumber(ARGV[1]) then
    return redis.call('DECRBY', KEYS[1], ARGV[1]) -- 扣减并返回剩余库存
else
    return 0 -- 库存不足
end
```
Java 调用片段:
```java
String script = "...上述Lua脚本...";
DefaultRedisScript<Long> redisScript = new DefaultRedisScript<>(script, Long.class);
Long remaining = stringRedisTemplate.execute(redisScript, Collections.singletonList("stock:1001"), "1");
if (remaining != null && remaining >= 0) {
    // 扣减成功，发消息到 MQ
} else {
    return "售罄";
}
```

**【对比表格：防超卖方案对比】

| 方案 | 核心逻辑 | QPS 承受能力 | 一致性保证 | 适用阶段 |
| :--- | :--- | :--- | :--- | :--- |
| **DB 乐观锁** | UPDATE ... WHERE count>0 | 低 (~2k) | 强一致性 | 低并发、数据兜底 |
| **Redis Lua** | 内存原子操作 | 高 (~10w+) | 最终一致 (异步回写DB) | 秒杀主流程 |
| **本地预扣减** | AtomicInteger | 极高 (~50w+) | 弱一致性 (可能少卖) | 极端瞬时洪峰 |

## 核心知识点图

<img src="/interview-2026/images/diagram_scenario_scen-112.svg" alt="秒杀系统如何做到「绝不超卖」？从缓存到数据库的全链路库存扣减方案。 - 核心知识点图" style="max-width:100%;height:auto;border:1px solid var(--border);border-radius:8px;margin:1em 0;" />

## 记忆要点

- 超卖根因：查库存与扣减非原子操作，导致并发读旧值
- DB兜底层：UPDATE stock SET count=count-1 WHERE id=? AND count>0 利用了行锁
- 极致性能：用Redis Lua脚本做GET与DECR的原子扣减，承压10万+QPS
- 全链路架构：前置限流削峰，Redis Lua扣减，MQ异步落库，DB乐观锁兜底

## 结构化回答


**30 秒电梯演讲：** 像抢票：进场前先验票销票（Redis），进去后再登记身份（DB），票没了直接拦。

**展开框架：**
1. **Redis Lu** — a脚本保证扣减原子性
2. **乐观锁更新DB** — 乐观锁更新DB，强一致性但慢
3. **扣减成功发MQ** — 扣减成功发MQ，异步落库解耦

**收尾：** Redis 扣减成功但 DB 扣减失败（MQ 消费失败）怎么办？


## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：秒杀系统如何做到「绝不超卖」 | "秒杀系统如何做到「绝不超卖」，30 秒讲清楚核心。" | 开场钩子 |
| 0:45 | 概念定义动画 | "一句话：Redis 原子扣减，数据库异步落地。" | 核心定义 |
| 1:30 | 生活类比动画 | "打个比方——像抢票：进场前先验票销票(Redis)，进去后再登记身份(DB)，票没了直接拦。" | 核心类比 |
| 2:15 | Redis 图解 | "Redis Lua脚本保证扣减原子性。" | Redis |
| 3:00 | 乐观锁更新DB 图解 | "乐观锁更新DB，强一致性但慢。" | 乐观锁更新DB |
| 3:50 | 扣减成功发MQ 图解 | "扣减成功发MQ，异步落库解耦。" | 扣减成功发MQ |
