---
id: scen-103
difficulty: L3
category: scenario
subcategory: 高并发系统设计
tags:
- 限流
- 高并发
- 网关
feynman:
  essence: 漏斗式分级限流，本地拦底，分布控全局。
  analogy: 像游园验票：门口保安粗筛，入口闸机细查，场馆内区控。
  first_principle: 如何以最小开销精准控制全局流量峰值？
  key_points:
  - 本地限流抗高频，无网延迟
  - 分布式限流用Lua，保原子性
  - 网关层拦截最优，成本最低
  - 多层兜底防雪崩，逐级降级
follow_up:
- 令牌桶和漏桶的核心区别是什么？分别适合什么场景？
- Redis 分布式限流如果 Redis 挂了怎么办？降级策略是什么？
- 集群限流模式下，Token Server 成为单点怎么解决？
memory_points:
- 千万并发需分层限流：CDN/Nginx层(L3)拦截恶意流量，网关层(L4)做精确业务限流
- 单机用滑动窗口更精准，分布式用Redis+Lua(保证原子性)或令牌桶
- 高并发绝不全走Redis：先过本地限流，仅秒杀等核心资源才申请分布式Token
- Redis挂掉要优雅降级为单机限流，宁可局部超载，绝不能阻断全局服务
frequency: high
---

# 如何设计一个支撑千万级并发的网关限流系统？对比单机限流与分布式限流的方案。

【场景分析】
千万级并发限流的核心矛盾：既要精准控制全局流量，又要保证网关本身不成为瓶颈。

【单机限流（适合中小流量）】
1. **令牌桶**：
   - 原理：以恒定速率向桶中放入令牌，请求消耗令牌。
   - 特性：允许突发流量（桶的大小决定突发上限），平滑流量。
   - 实现：Guava RateLimiter, Sentinel。
2. **漏桶**：
   - 原理：请求先入桶，桶以恒定速率流出（处理请求）。
   - 特性：强制匀速，拒绝溢出请求。保护下游能力极强，但无法应对突发。
3. **滑动窗口**：
   - 原理：将时间分为多个小格，统计当前窗口内的总请求数。
   - 特性：精度高于固定窗口（"临界突变"问题）。

【分布式限流（适合千万级并发）】
1. **Redis + Lua 脚本**：
   - 核心：将 "读取当前计数-判断是否超限-自增" 逻辑封装在 Lua 脚本中，保证原子性。
   - 优化：Redis 集群部署，避免单点瓶颈；使用 `pexpire` 设置 key 过期时间自动滚动窗口。
2. **网关层限流**：
   - 核心：利用 Nginx/OpenResty 的高性能特性，在流量进入应用层前拦截。
   - 优势：C 语言实现，内存操作，性能极高（百万级 QPS）。
3. **Sentinel 集群流控**：
   - 架构：独立的 Token Server 服务负责计算全局限流阈值，多个 Token Client（网关节点）向 Server 申请令牌。

【推荐架构（分层限流）】
```text
用户请求
   │
   ▼
[CDN/HTTP-DNS]           (L1: DNS 封禁/区域限流)
   │
   ▼
[OS/TCP Kernel]          (L2: Syn Cookie 防护)
   │
   ▼
[Nginx/OpenResty]        (L3: IP/QPS 限流，拒绝恶意流量)
   │
   ▼
[API Gateway Cluster]    (L4: 业务接口限流，用户维度限流)
   │   ├─ 本地限流
   │   └─ Redis 分布式限流 (精确控制)
   │
   ▼
[Microservices]          (L5: 自我保护 Sentinel)
```

【性能要点】
- **本地限流优先**：请求先过本地限流，拦截大部分正常流量，减少 Redis 压力。仅对需要精确全局控制的资源（如秒杀库存）才调用 Redis。
- **Lua 原子性**：避免多次 RTT (Round-Trip Time)。
- **优雅降级**：Redis 挂了时，自动降级为单机限流，宁可稍微超卖/超载，也不能让整个系统不可用。

【## 常见考点】
1. **固定窗口 vs 滑动窗口**：为何固定窗口在边界处会出现"两倍流量"问题？（例如 00:01 的 100 请求和 00:02 的 100 请求在 00:01:59 扫描时可能被同时统计）。
2. **Redis 性能瓶颈**：千万并发下，所有请求都去 Redis `incr` 会不会压垮 Redis？（会的，因此需要分层，且核心接口才走 Redis，普通接口走本地限流）。
3. **Sentinel 集群限流**：Token Server 挂了怎么办？（Client 会自动切换到本地限流模式（降级）或连接备用 Token Server）。
4. **限流后的策略**：是直接拒绝 429，还是排队？（高并发场景建议直接拒绝，排队会堆积线程导致网关 OOM）。



## 核心流程图

```mermaid
flowchart TD
    REQ([请求到达]):::start --> ALG{限流算法}:::decision
    ALG -->|计数器固定窗口| CNT[单位时间内计数<br/>超阈值拒绝]
    ALG -->|滑动窗口| SW[细分窗口平滑统计<br/>解决临界问题]:::async
    ALG -->|漏桶| LB["固定速率漏水<br/>超出容量丢弃/排队"]
    ALG -->|令牌桶| TB[固定速率发令牌<br/>拿到才处理 允许突发]
    CNT --> CBUG{临界问题?}:::decision
    CBUG -->|是 窗口切换瞬间| SURGE[2倍流量冲击<br/>需滑动窗口补救]:::error
    CBUG -->|否| PASS1[放行]
    SW --> STAT[Redis ZSET统计<br/>score=时间戳]
    STAT --> CHK1{窗口内数量?}:::decision
    CHK1 -->|超阈值| DROP1[拒绝 429 Too Many]
    CHK1 -->|未超| PASS2[放行]
    LB --> QUEUE[请求入桶<br/>队列缓冲]
    QUEUE --> RATE[匀速消费<br/>超出容量溢出]
    RATE --> CHK2{桶满?}:::decision
    CHK2 -->|是| DROP2[拒绝]
    CHK2 -->|否| PASS3[排队处理]
    TB --> TOKEN[(令牌桶<br/>定时添加令牌)]:::storage
    TOKEN --> TAKE{有令牌?}:::decision
    TAKE -->|是| CONSUME[消耗1个令牌 放行]
    TAKE -->|否| DROP3["拒绝/等待"]:::error
    PASS1 --> DONE([请求被处理]):::success
    PASS2 --> DONE
    PASS3 --> DONE
    CONSUME --> DONE
    REQ --> LEV{限流层级}:::decision
    LEV -->|网关限流| GW["Nginx/Spring Cloud Gateway"]
    LEV -->|应用限流| APP["Sentinel/Resilience4j"]
    LEV -->|分布式限流| DIST[Redis+Lua 原子操作]
        classDef start fill:#e3f2fd,stroke:#1976d2,stroke-width:2px,color:#0d47a1
    classDef decision fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#e65100
    classDef success fill:#e8f5e9,stroke:#388e3c,stroke-width:2px,color:#1b5e20
    classDef error fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#b71c1c
    classDef storage fill:#eceff1,stroke:#455a64,stroke-width:2px,color:#263238
    classDef async fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#4a148c

```
## 记忆要点

- 千万并发需分层限流：CDN/Nginx层(L3)拦截恶意流量，网关层(L4)做精确业务限流
- 单机用滑动窗口更精准，分布式用Redis+Lua(保证原子性)或令牌桶
- 高并发绝不全走Redis：先过本地限流，仅秒杀等核心资源才申请分布式Token
- Redis挂掉要优雅降级为单机限流，宁可局部超载，绝不能阻断全局服务

## 结构化回答


**30 秒电梯演讲：** 像游园验票：门口保安粗筛，入口闸机细查，场馆内区控。

**展开框架：**
1. **本地限流抗高频** — 本地限流抗高频，无网延迟
2. **分布式限流用Lua** — 分布式限流用Lua，保原子性
3. **网关层拦截最优** — 网关层拦截最优，成本最低

**收尾：** 令牌桶和漏桶的核心区别是什么？


## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：支撑千万级并发的网关限流系统 | "支撑千万级并发的网关限流系统，这题我会分三步讲。" | 开场钩子 |
| 0:41 | 概念定义动画 | "一句话：漏斗式分级限流，本地拦底，分布控全局。" | 核心定义 |
| 1:22 | 生活类比动画 | "打个比方——像游园验票：门口保安粗筛，入口闸机细查，场馆内区控。" | 核心类比 |
| 2:03 | 本地限流抗高频 图解 | "本地限流抗高频，无网延迟。" | 本地限流抗高频 |
| 2:50 | 分布式限流用Lua 图解 | "分布式限流用Lua，保原子性。" | 分布式限流用Lua |

### 视频流程图

```mermaid
flowchart LR

    subgraph Intro["引入"]
        A["如何设计一个支撑千万级并发的网关限流系统？对比单机限流与分布…"]:::intro
    end

    subgraph Core["讲解"]
        B["千万并发需分层限流：CDN/Nginx层（L3）拦截…"]:::core
        C["单机用滑动窗口更精准，分布式用Redis+Lua（保…"]:::deep
    end

    subgraph Practice["实战"]
        D["代码实战"]:::practice
    end

    subgraph Wrap["收尾"]
        E["总结回顾"]:::wrap
    end

    A --> B --> C --> D --> E

    classDef intro fill:#FF9800,color:#fff,stroke:#F57C00,stroke-width:2px
    classDef core fill:#2196F3,color:#fff,stroke:#1976D2,stroke-width:2px
    classDef deep fill:#4CAF50,color:#fff,stroke:#388E3C,stroke-width:2px
    classDef practice fill:#9C27B0,color:#fff,stroke:#7B1FA2,stroke-width:2px
    classDef wrap fill:#607D8B,color:#fff,stroke:#455A64,stroke-width:2px
```

