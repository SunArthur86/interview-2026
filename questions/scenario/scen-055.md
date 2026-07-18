---
id: scen-055
difficulty: L2
category: scenario
subcategory: 架构演进
tags:
- 链路追踪
- SkyWalking
- Jaeger
- OpenTelemetry
- TraceId
- Span
- 自动埋点
feynman:
  essence: 给请求打全局标签，追踪其在各服务间的调用路径。
  analogy: 像快递面单，记录包裹经过的每一个中转站和时间。
  first_principle: 如何快速定位跨多个微服务的请求延迟或故障根源？
  key_points:
  - TraceId串联全链路日志
  - Span记录每个环节耗时
  - 字节码增强无侵入埋点
  - 异步上报与采样优化
follow_up:
- TraceId如何在线程池中传播？
- SkyWalking的采样策略有哪些？
- 如何减少链路追踪的性能开销？
memory_points:
- 核心模型：一次完整的分布式请求为一个Trace，具体操作为Span，通过ParentID串联。
- 上下文传播：跨进程靠透传Header（如HTTP的X-B3-TraceId），跨线程靠TTL传递。
- 选型对比：SkyWalking靠Java Agent字节码增强实现零侵入，Jaeger更契合云原生多语言。
- 性能优化：通过动态采样率、异步批量上报机制，避免链路追踪拖垮业务主流程。
frequency: high
---

# 如何设计微服务的链路追踪系统？快速定位跨服务调用问题。

【场景分析】
微服务调用链复杂：一个请求经过10+服务，出问题时难以定位是哪个环节。

【实战案例】
某核心接口RT突增，通过SkyWalking追踪发现瓶颈在于下游服务的数据库慢查询。在Trace日志中，虽然HTTP调用耗时正常，但深层的JDBC Span显示某次Update执行了5秒，进一步关联DB日志发现是锁等待，从而快速定位并解决了死锁问题。

【OpenTracing/OpenTelemetry标准】
核心概念：
- Trace：一次完整的分布式请求
- Span：一个操作（如一次HTTP调用或DB查询）
- SpanContext：跨进程传播的上下文（traceId + spanId）

【数据模型】
```
Trace: traceId = abc123
  ├─ Span 1: Gateway接收 (spanId=1, 5ms)
  │   └─ Span 2: 调用UserService (spanId=2, parent=1, 10ms)
  │       └─ Span 3: DB查询 (spanId=3, parent=2, 3ms)
  └─ Span 4: 调用OrderService (spanId=4, parent=1, 50ms)
      └─ Span 5: 调用Redis (spanId=5, parent=4, 2ms)
      └─ Span 6: 调用PaymentService (spanId=6, parent=4, 30ms)
```

【TraceId传播】
- HTTP：通过Header `X-B3-TraceId` / `X-B3-SpanId`
- gRPC：通过Metadata
- MQ：通过Message Header
- 线程池：通过ThreadLocal + TaskDecorator

【主流方案对比】

| 方案 | 采集方式 | 优势 | 劣势 | 适用场景 |
| :--- | :--- | :--- | :--- | :--- |
| **SkyWalking** | Java Agent (字节码增强) | 对代码零侵入，UI丰富，支持JVM监控 | 主要支持Java生态 (虽有多语言探针) | Java为主的微服务，运维友好 |
| **Jaeger** | SDK/Agent | CNCF毕业项目，云原生亲和，支持OTel | UI相对简单，需手动埋点或配置 | K8s环境，多语言异构系统 |
| **Zipkin** | SDK | 轻量级，Spring Cloud Sleuth集成度高 | 功能简单，存储扩展性一般 | 简单架构，学习原理 |
| **Pinpoint** | Agent | 追踪粒度极细（到字节码级别） | 资源消耗较大，HBase存储重 | 需要深度代码级性能分析 |

【SkyWalking Agent原理】
- 启动参数：`-javaagent:skywalking-agent.jar`
- 在JVM启动时拦截类加载
- 对常见框架（Spring/MyBatis/HTTP）自动埋点
- 无需修改业务代码
- 异步上报Span数据到OAP Server

【关键功能】
1. 调用拓扑：自动发现服务依赖关系
2. 慢链路分析：按耗时排序TopN链路
3. 错误链路：自动捕获异常链路
4. 服务依赖：可视化服务调用关系
5. JVM监控：CPU/内存/GC/线程
6. 告警：RT/QPS/错误率告警

【性能优化】
- 采样率：不是所有请求都上报（1%-100%可调）
- 异步上报：不阻塞业务线程
- 批量上报：减少网络开销
- 数据降采样：老数据降低精度

【链路追踪上下文传播图】
```
进程 A: Client 进程                      进程 B: Server 进程
  │                                          │
  │ 1. 构建 Span Context                    │
  │    TraceID: X, SpanID: A                │
  │                                          │
  │ 2. HTTP Request                         │
  │    Header: {                            │
  │      "trace-id": "X",
  │      "span-id": "A",
  │      "baggage": "user=123"             │
  │    }                                    │
  ├─────────────────────────────────────►   │
  │                                          │ 3. 提取 Context
  │                                          │    TraceID: X, ParentID: A
```

【代码示例：手动传递 TraceContext (跨线程/异步)】
```java
// 使用 TransmittableThreadLocal (TTL) 解决线程池上下文丢失
ExecutorService executor = TtlExecutors.getTtlExecutorService(Executors.newFixedThreadPool(10));

public void asyncProcess() {
    // 主线程已注入 TraceContext
    executor.submit(() -> {
        // 子线程自动继承 TraceContext
        Span span = tracer.nextSpan().name("async-operation");
        try (Tracer.SpanInScope ws = tracer.withSpanInScope(span)) {
            // 业务逻辑
            doWork();
        } finally {
            span.end();
        }
    });
}
```



## 核心流程图

```mermaid
flowchart TD
    REQ([用户请求]):::start --> DNS[DNS解析 多IP轮询]
    DNS --> LB["负载均衡 LVS/F5<br/>四层流量分发"]
    LB --> NGINX[Nginx 七层反向代理<br/>健康检查 故障剔除]
    NGINX --> SVC[服务集群<br/>多实例部署]
    SVC --> MASTER{主从模式?}:::decision
    MASTER -->|是 主备| MS[主节点写 备节点同步<br/>主挂自动切换VIP]
    MASTER -->|否 多活| MA[多节点同时服务<br/>无单点]
    SVC --> FAIL{实例故障?}:::decision
    FAIL -->|是| HEALTH[健康检查探针<br/>剔除故障实例]
    FAIL -->|否| NORMAL[正常处理]:::success
    HEALTH --> REROUTE[流量转移到健康实例]
    REROUTE --> NORMAL
    MS --> DOWN{主节点宕机?}:::decision
    DOWN -->|是| FAILOVER[Keepalived VIP漂移<br/>Sentinel选主]
    DOWN -->|否| NORMAL
    FAILOVER --> ALERT[告警通知 运维介入]:::async
    NORMAL --> METRIC{SLA指标}:::decision
    METRIC -->|可用性 99.99%| SLA[年停机<53分钟<br/>核心系统目标]
    METRIC -->|RTO 恢复时间| RTO[灾难到恢复服务<br/>分钟级]
    METRIC -->|RPO 数据丢失| RPO[灾难到数据丢失量<br/>秒级 同步复制]
        classDef start fill:#e3f2fd,stroke:#1976d2,stroke-width:2px,color:#0d47a1
    classDef decision fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#e65100
    classDef success fill:#e8f5e9,stroke:#388e3c,stroke-width:2px,color:#1b5e20
    classDef error fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#b71c1c
    classDef storage fill:#eceff1,stroke:#455a64,stroke-width:2px,color:#263238
    classDef async fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#4a148c

```
## 记忆要点

- 核心模型：一次完整的分布式请求为一个Trace，具体操作为Span，通过ParentID串联。
- 上下文传播：跨进程靠透传Header（如HTTP的X-B3-TraceId），跨线程靠TTL传递。
- 选型对比：SkyWalking靠Java Agent字节码增强实现零侵入，Jaeger更契合云原生多语言。
- 性能优化：通过动态采样率、异步批量上报机制，避免链路追踪拖垮业务主流程。

## 结构化回答


**30 秒电梯演讲：** 像快递面单，记录包裹经过的每一个中转站和时间。

**展开框架：**
1. **TraceId** — TraceId串联全链路日志
2. **Span** — Span记录每个环节耗时
3. **字节码增强无** — 字节码增强无侵入埋点

**收尾：** TraceId如何在线程池中传播？


## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：微服务的链路追踪系统 | "微服务的链路追踪系统，一分钟讲透。" | 开场钩子 |
| 0:35 | 生活类比动画 | "打个比方——像快递面单，记录包裹经过的每一个中转站和时间。" | 核心类比 |
| 1:10 | 概念定义动画 | "一句话：给请求打全局标签，追踪其在各服务间的调用路径。" | 核心定义 |
| 1:50 | TraceId串联全 图解 | "TraceId串联全链路日志。" | TraceId串联全 |

### 视频流程图

```mermaid
flowchart LR

    subgraph Intro["引入"]
        A["如何设计微服务的链路追踪系统？快速定位跨服务调用问题"]:::intro
    end

    subgraph Core["讲解"]
        B["核心模型：一次完整的分布式请求为一个Trace，具体…"]:::core
        C["上下文传播：跨进程靠透传Header（如HTTP的X…"]:::deep
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

