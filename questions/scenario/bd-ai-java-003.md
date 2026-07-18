---
id: bd-ai-java-003
difficulty: L4
category: scenario
subcategory: 系统设计
tags:
- 字节
- 面经
- Agent
- 架构
- 多Agent
- 系统设计
feynman:
  essence: 从确定性的逻辑执行转变为概率性的目标拆解。
  analogy: Web应用是流水线（按图纸生产），Agent是外包团队（听指令交付）。
  first_principle: 如何构建能够自主规划并执行任务的软件系统？
  key_points:
  - Web应用逻辑确定，Agent决策概率性
  - Agent通过循环调用工具逐步达成目标
  - 需关注Token成本、Trace追踪和非确定性测试
follow_up:
- Agent 应用怎么做监控？——Trace 追踪（类似 Jaeger）+ Token 消费统计 + 完成率指标
- Agent 的延迟怎么优化？——模型路由（简单走小模型）+ 缓存 + Speculative Decoding
- Java 生态做 Agent 有什么优势？——企业级稳定性 + 丰富中间件生态 + 强类型安全
memory_points:
- 核心对比：传统Web是确定性请求响应，AI Agent是概率性循环执行
- 因为Token按次消费，所以Agent需通过限流+缓存+模型路由控制成本
- 状态隔离：传统Web用ThreadLocal，Agent须用ChatMemory+Redis防上下文串扰
- 测试差异：传统Web靠断点分支，Agent靠准确率指标与Bad Case分析
---

# 【字节面经】传统 Web 应用和 AI Agent 应用有什么不同？结合你的开发经历谈谈。

**传统 Web 应用 vs AI Agent 应用核心对比：**

| 维度 | 传统 Web 应用 | AI Agent 应用 |
|------|-------------|---------------|
| **确定性** | 确定性（输入A则输出B） | 概率性（同样输入可能不同输出） |
| **执行模式** | 请求-响应（一次返回） | 循环执行（多轮工具调用） |
| **错误处理** | 明确错误码（404/500） | 模糊错误（幻觉/规划出错/工具失败） |
| **成本模型** | 服务器+带宽 | Token 消费（每次推理都花钱） |
| **测试方式** | 单元测试覆盖所有分支 | 评估指标 + Bad Case 分析 |
| **状态管理** | Session/Redis | KV Cache + 对话历史 + Checkpoint |
| **调试方式** | 断点调试 | 日志分析 + Trace 追踪 |
| **延迟特征** | 稳定低延迟 | 变长延迟（几秒到几分钟） |

**架构对比图：**

```text
传统 Web 架构:
[Client] ──(HTTP)──> [Controller] ──> [Service] ──> [DAO/DB]
   │                      │              │             │
   └──────────────────────┴──────────────┴─────────────┘
   确定性逻辑，同步/异步响应

Agent 应用架构:
[Client] ──(HTTP)──> [Controller] ──> [Agent Orchestrator]
                                   │
            ┌──────────────────────┼──────────────────────┐
            │                      │                      │
            ▼                      ▼                      ▼
      [LLM 思维链]           [RAG 检索]           [Tool 执行]
      (概率决策)           (向量库 PG/Milvus)     (Function Call)
            │                      │                      │
            └──────────────────────┴──────────────────────┘
                                   │
                         <循环判断：任务是否完成?>
                                   │
                              [最终响应]
```

**Java 后端架构差异：**

传统 Web 架构: Controller → Service → DAO → DB，同步/异步(MQ) → 确定性响应

Agent 应用架构: Controller → Agent Orchestrator → LLM 调用(概率性决策) → Tool 执行(Function Calling) → RAG 检索(向量数据库) → 循环判断(是否完成任务) → 结果汇总 → 响应

**Java 技术栈适配：**
- Spring AI / Spring AI Alibaba — Java 生态的 AI 集成框架
- LangChain4j — LangChain 的 Java 实现
- 向量数据库 — Milvus/Qdrant + Java SDK
- 消息队列 — Kafka 处理异步 Agent 任务
- 状态管理 — Redis 存对话历史 + Checkpoint

**实战案例：**
我们在开发客服 Agent 时，曾遇到用户并发提问导致 Agent 将 A 用户的状态误更新给 B 用户。传统 Web 的 `ThreadLocal` 完全失效，改为使用 LangChain4j 的 `ChatMemory` 结合 Redis 的 `Key-Id` 隔离机制，才解决了上下文串扰问题。

**异步状态管理代码示例（Spring Boot + WebFlux）：**
```java
// Agent 任务通常是异步的，直接返回 HTTP 202
@PostMapping("/agent/run")
public Mono<ResponseEntity<TaskId>> runAgent(@RequestBody AgentRequest req) {
    String taskId = UUID.randomUUID().toString();
    // 将任务提交到消息队列或异步线程池，避免阻塞 Tomcat 线程
    agentOrchestrator.submitAsync(taskId, req);
    // 立即返回任务ID，前端轮询或WebSocket获取结果
    return Mono.just(ResponseEntity.accepted().body(new TaskId(taskId)));
}
```

**工程挑战：**
1. 非确定性测试 — 无法写 assertEquals，需用准确率/完成率
2. 成本控制 — Token 计费需限流+缓存+模型路由
3. 长任务管理 — Agent 可能跑几分钟，需异步+进度追踪
4. 安全边界 — Prompt 注入防护 + 工具调用权限控制
5. 可观测性 — Trace 追踪每一步决策链路

## 常见考点
1. **非确定性处理**：如何保证 Agent 输出的稳定性？答案：通过设定严格的 System Prompt、使用温度参数低的模型、以及引入“人工确认”机制来减少随机性。


## 记忆要点

- 核心对比：传统Web是确定性请求响应，AI Agent是概率性循环执行
- 因为Token按次消费，所以Agent需通过限流+缓存+模型路由控制成本
- 状态隔离：传统Web用ThreadLocal，Agent须用ChatMemory+Redis防上下文串扰
- 测试差异：传统Web靠断点分支，Agent靠准确率指标与Bad Case分析

## 结构化回答

**30 秒电梯演讲：** 从确定性的逻辑执行转变为概率性的目标拆解。打比方——Web应用是流水线(按图纸生产)，Agent是外包团队(听指令交付)。落到工程上，Web应用逻辑确定，Agent决策概率性。

**展开框架：**
1. **Web应用逻辑确定** — Web应用逻辑确定，Agent决策概率性
2. **Agent** — Agent通过循环调用工具逐步达成目标
3. **需关注Token成本** — 需关注Token成本、Trace追踪和非确定性测试

**收尾：** 这几个点都能配合实战展开。您想继续聊哪个追问——比如 「Agent 应用怎么做监控」 或者 「Agent 的延迟怎么优化」？

## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：传统 Web 应用和 AI Agent | "传统 Web 应用和 AI Agent，30 秒讲清楚核心。" | 开场钩子 |
| 0:45 | 概念定义动画 | "一句话：从确定性的逻辑执行转变为概率性的目标拆解。" | 核心定义 |
| 1:30 | 生活类比动画 | "打个比方——Web应用是流水线(按图纸生产)，Agent是外包团队(听指令交付)。" | 核心类比 |
| 2:15 | Web应用逻辑确定 图解 | "Web应用逻辑确定，Agent决策概率性。" | Web应用逻辑确定 |
| 3:00 | Agent 图解 | "Agent通过循环调用工具逐步达成目标。" | Agent |
| 3:50 | 需关注Token成本 图解 | "需关注Token成本、Trace追踪和非确定性测试。" | 需关注Token成本 |
