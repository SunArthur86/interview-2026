---
id: biopharm-011
difficulty: L4
category: biopharm
subcategory: 企业级 AI 平台架构
tags:
- 生物医药
- AI 全栈
- 企业级 AI 平台架构
- 多租户
- 分层架构
- 可观测
feynman:
  essence: 企业级 AI Agent 平台架构是'分层解耦 + 能力沉淀'——接入层（网关）、编排层（Agent/Workflow）、能力层（RAG/工具/模型）、数据层（知识库/向量库）、基础设施层（GPU/监控），让
    AI 能力像中台一样被复用。
  analogy: 像大型医院体系——前台挂号（网关）、专科分诊（编排）、各科室能力（RAG/工具/模型）、病案室药房（数据层）、水电后勤（基础设施）。每层各司其职，新开科室复用底层能力，不用从零建。
  first_principle: 企业有多个 AI 场景（问答/检索/Agent/报表），若每个场景独立建一套，会重复造轮子、数据孤岛、运维爆炸。平台架构的本质是'把公共能力下沉成共享中台'，让上层场景快速组装复用。
  key_points:
  - 五层架构：接入层 / 编排层 / 能力层 / 数据层 / 基础设施层
  - 多租户隔离：数据/模型/配额按租户隔离，逻辑隔离为主
  - 能力中台：RAG、工具市场、模型路由、Workflow 引擎沉淀为共享服务
  - 统一网关：鉴权限流计量 + 模型路由 + 流式 + 审计的统一入口
  - 可观测与治理：监控/计量/审计/成本贯穿全链路
  socratic:
  - 药企有文献检索、用药咨询、临床辅助三个 AI 场景，要不要各建各的？
  - 每个业务线都自己接 LLM、自己建向量库，会带来什么重复和混乱？
  - 平台要支持多个客户（多家药企），数据怎么保证不串？
  - 接入层、编排层、能力层各自负责什么？为什么要分开？
  - 平台怎么让新 AI 场景两周上线而不是两个月？
first_principle:
  problem: 如何让企业多个 AI 场景共享能力、数据隔离、快速复用、统一治理？
  axioms:
  - 企业有多个 AI 场景，独立建设会重复+孤岛
  - 公共能力（RAG/工具/模型路由/Workflow）可复用
  - 多租户要求数据隔离和统一治理
  rebuild: 分层解耦——接入层统一入口、编排层组装 Agent/Workflow、能力层沉淀可复用服务、数据层管知识/向量、基础设施层管 GPU/监控，让上层场景快速组装，公共能力共享复用。
follow_up:
- 多租户怎么隔离？——逻辑隔离（共享集群+tenant_id 隔离）成本低、物理隔离（独立库/集群）安全高；医药敏感数据可核心物理隔离+边缘逻辑隔离。
- 能力中台怎么沉淀？——把 RAG、工具市场、模型路由、Workflow 做成标准服务+API，业务方按需调用；新场景=编排已有能力。
- 平台和单场景怎么演进？——先单场景验证，抽取共性沉淀中台，再支撑多场景；避免一上来就过度抽象。
memory_points:
- 五层架构：接入/编排/能力/数据/基础设施
- 多租户隔离 + 统一网关
- 能力中台：RAG/工具/路由/Workflow 共享
- 分层解耦，新场景快速组装
frequency: medium
---

# 【生物医药 AI】企业级 AI Agent 平台整体架构怎么设计？

> JD 依据："负责 AI Agent 系统架构设计、开发与优化；负责企业级 AI Agent 产品的架构设计、研发落地。"

## 一、为什么要平台化

```
单场景建设（重复造轮子）：
  文献检索系统：自己接 LLM + 自己建库 + 自己运维
  用药咨询系统：自己接 LLM + 自己建库 + 自己运维
  → 数据孤岛、重复投入、运维爆炸

平台化（能力复用）：
  统一平台 → 新场景只编排已有能力，快速上线
```

## 二、五层架构

```
┌─────────────────────────────────────────┐
│  接入层    API 网关 / Web / SDK / 审批台  │
├─────────────────────────────────────────┤
│  编排层    Agent 引擎 / Workflow 引擎     │
├─────────────────────────────────────────┤
│  能力层    RAG / 工具市场 / 模型路由 / Prompt │
├─────────────────────────────────────────┤
│  数据层    知识库 / 向量库 / 元数据 / 业务库 │
├─────────────────────────────────────────┤
│  基础设施  GPU 池 / 监控 / 日志 / 队列      │
└─────────────────────────────────────────┘
              横切：多租户 / 安全 / 计量 / 审计
```

### 1. 接入层（网关）
- 统一入口：API/Web/SDK/审批台。
- 鉴权（API Key/OAuth）、限流、计量、流式、审计。
- 模型路由（见005）的承载点。

### 2. 编排层
- **Agent 引擎**：规划+工具+校验闭环（见001）。
- **Workflow 引擎**：DAG+状态机+人工审批（见004）。
- 场景 = 编排能力的组合，新场景快速搭建。

### 3. 能力层（中台）
- **RAG 服务**：检索+重排+引用回溯（见002）。
- **工具市场**：工具/MCP server 注册、发现、调用（见003/028）。
- **模型路由**：多模型多供应商路由+fallback（见005）。
- **Prompt 管理**：版本化、A/B、模板复用。
- 这些能力对上层场景共享复用。

### 4. 数据层
- 知识库（文档治理，见008）、向量库（见006）、业务库（PG/MySQL）。
- 元数据治理、版本、权限。

### 5. 基础设施层
- GPU 池与推理服务（vLLM）、队列（Kafka/RabbitMQ）、监控（Prometheus）、日志（ELK）。

## 三、横切关注点（贯穿所有层）

- **多租户**：数据隔离 + 配额 + 计量。
- **安全合规**：脱敏 + 审计 + 权限（见034）。
- **可观测**：trace/metrics/log（见033）。
- **成本**：计量 + 预算 + 降级（见010）。

## 四、多租户隔离

```
租户A ─┐
租户B ─┤→ 共享平台，tenant_id 贯穿各层强制隔离
租户C ─┘

隔离强度：
  逻辑隔离（共享集群+tenant_id）→ 成本低，多数场景够
  物理隔离（独立库/独立集群）→ 安全高，敏感数据
```
- 医药场景：患者数据可物理隔离，通用知识库逻辑隔离。

## 五、新场景如何快速上线（平台价值）

```
新需求"药物相互作用查询"：
  ① 接入工具市场已有 drug_interaction 工具
  ② 接入 RAG（药品说明书库）
  ③ 用编排层拖拽 Agent（意图→调工具→检索→生成→校验）
  ④ 网关暴露 API
  → 两周上线（不用从零建）
```

## 六、演进路径（避免过度设计）

```
阶段1：单场景验证（先做文献检索，跑通价值）
阶段2：抽共性（把 RAG/工具沉淀成服务）
阶段3：多场景复用（平台化）
阶段4：开放（让业务方自助编排）
```
不要一上来就建大平台，先单场景验证再抽中台。

## 七、底层本质

企业级 AI 平台本质是**"把 AI 能力分层解耦、公共下沉、上层复用"**。五层架构各司其职，能力中台沉淀复用，新场景快速组装，多租户统一治理。

**这是'AI 项目'到'AI 平台'的跨越** —— 单个 AI 应用谁都能做，但能让企业多个场景低成本复用的平台，才是资深架构师的价值。

## 常见考点

1. **平台和单场景如何权衡？**——先单场景跑通价值，再抽共性沉淀，避免一开始过度抽象（YAGNI）；平台要服务于"让新场景更快上线"这个目标。
2. **能力中台怎么做版本兼容？**——服务 API 版本化、灰度发布、向下游保证契约稳定；破坏性变更走 v2 并行。
3. **怎么度量平台价值？**——新场景上线周期缩短、公共能力复用率、单位场景成本下降、租户数和调用量增长。


## 核心流程图

```mermaid
flowchart TD
    Start([🚀 客户端发起请求]):::start
    Producer[Producer 生产者<br/>发送消息]:::client
    DecideSync{发送模式?<br/>同步/异步/单向}:::decision
    Sync[同步发送<br/>阻塞等待 ACK]:::process
    Async[异步发送<br/>回调通知]:::process
    Oneway[单向发送<br/>不等响应]:::warn
    RetryQ{是否收到 ACK?}:::decision
    Retry[重试 N 次<br/>+ 幂等去重]:::process
    DLQ[多次失败 → 死信队列 DLQ]:::danger
    Broker[Broker 主节点<br/>写 PageCache]:::broker
    FlushQ{刷盘策略?}:::decision
    SyncFlush[同步刷盘 SYNC_FLUSH<br/>落盘后才返回]:::process
    AsyncFlush[异步刷盘<br/>后台异步落盘]:::warn
    ReplicaQ{复制策略?}:::decision
    SyncRep[同步复制 SYNC_MASTER<br/>等 Slave 落盘]:::process
    AsyncRep[异步复制<br/>Master 立即返回]:::warn
    Persist[(磁盘 + 多副本<br/>持久化存储)]:::store
    Consumer[Consumer 消费者<br/>拉取消息]:::client
    OffsetQ{Offset 提交方式?}:::decision
    AutoCommit[自动提交<br/>风险:业务异常也消费]:::warn
    ManualCommit[手动提交<br/>业务成功后再 ACK]:::process
    Business[执行业务逻辑]:::process
    BizQ{业务是否成功?}:::decision
    Reconsume[消费失败 → 重试<br/>RECONSUME_LATER]:::process
    Final([✅ 消息消费完成]):::start

    Start --> Producer --> DecideSync
    DecideSync -->|高可靠| Sync --> Broker
    DecideSync -->|高吞吐| Async --> Broker
    DecideSync -->|日志类| Oneway --> Broker
    Broker --> FlushQ
    FlushQ -->|金融级| SyncFlush --> ReplicaQ
    FlushQ -->|性能优先| AsyncFlush --> ReplicaQ
    ReplicaQ -->|强一致| SyncRep --> Persist
    ReplicaQ -->|弱一致| AsyncRep --> Persist
    Persist --> Consumer --> OffsetQ
    OffsetQ -->|不推荐| AutoCommit --> Business
    OffsetQ -->|推荐| ManualCommit --> Business
    Business --> BizQ
    BizQ -->|成功| ManualCommit --> Final
    BizQ -->|失败| Reconsume --> Consumer
    Producer -.ACK 超时/失败.-> RetryQ
    RetryQ -->|<N 次| Retry --> Producer
    RetryQ -->|>=N 次| DLQ

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef client fill:#10b981,stroke:#047857,color:#fff;
    classDef broker fill:#f59e0b,stroke:#b45309,color:#fff;
    classDef store fill:#8b5cf6,stroke:#6d28d9,color:#fff;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef warn fill:#fee2e2,stroke:#ef4444,color:#7f1d1d;
    classDef danger fill:#b91c1c,stroke:#7f1d1d,color:#fff,stroke-width:2px;

```

## 结构化回答

**30 秒电梯演讲：** 聊到企业级 AI Agent 平台整体架构怎么设计，我的理解是——企业级 AI Agent 平台架构是'分层解耦 + 能力沉淀'——接入层（网关）、编排层（Agent/Workflow）、能力层（RAG/工具/模型）、数据层（知识库/向量库）、基础设施层（GPU/监控），让 AI 能力像中台一样被复用。打个比方，像大型医院体系——前台挂号（网关）、专科分诊（编排）、各科室能力（RAG/工具/模型）、病案室药房（数据层）、水电后勤（基础设施）。每层各司其职，新开科室复用底层能力，不用从零建。

**展开框架：**
1. **五层架构** — 接入层 / 编排层 / 能力层 / 数据层 / 基础设施层
2. **多租户隔离** — 数据/模型/配额按租户隔离，逻辑隔离为主
3. **能力中台** — RAG、工具市场、模型路由、Workflow 引擎沉淀为共享服务

**收尾：** 这块我在项目里也踩过坑——想深入的话，可以接着聊：多租户怎么隔离？您更想看哪个方向？

## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "企业级 AI Agent 平台整体架构怎么设计——这道题面试官到底想考什么？我用 30 秒给你讲透。" | 开场钩子 |
| 0:15 | Agent 感知-思考-行动闭环图 | 先说核心：企业级 AI Agent 平台架构是'分层解耦 + 能力沉淀'——接入层（网关）、编排层（Agent/Workflow）、能力层（RAG/工具/模型）、数据层（知识库/向量库）。 | 核心定义 |
| 0:50 | 概念结构示意图 | 数据/模型/配额按租户隔离，逻辑隔离为主。 | 多租户隔离 |
| 1:20 | 流程图 | RAG、工具市场、模型路由、Workflow 引擎沉淀为共享服务。 | 能力中台 |
| 1:50 | API 网关架构图 | 鉴权限流计量 + 模型路由 + 流式 + 审计的统一入口。 | 统一网关 |
| 3:30 | 总结卡 | 一句话记忆：五层架构：接入/编排/能力/数据/基础设施。 下期可以接着聊：多租户怎么隔离。 | 收尾总结 |

### 视频流程图

```mermaid
flowchart LR
  subgraph Intro["🎬 引入"]
    N1["0:00<br/>开场钩子"]:::open
  end
  subgraph Body["📚 讲解"]
    N2["0:15<br/>Agent 感知-思考-行动闭环"]:::concept
    N3["0:50<br/>多租户隔离"]:::concept
    N4["1:20<br/>能力中台"]:::deep
    N5["1:50<br/>统一网关"]:::deep
  end
  subgraph Outro["🎯 收尾"]
    N6["3:30<br/>收尾总结"]:::summary
  end
  N1 --> N2
  N2 --> N3
  N3 --> N4
  N4 --> N5
  N5 --> N6
  classDef open fill:#f59e0b,stroke:#b45309,color:#fff,stroke-width:2px;
  classDef concept fill:#3b82f6,stroke:#1e3a8a,color:#fff;
  classDef deep fill:#10b981,stroke:#047857,color:#fff;
  classDef practice fill:#8b5cf6,stroke:#6d28d9,color:#fff;
  classDef summary fill:#6b7280,stroke:#374151,color:#fff,stroke-width:2px;
```

