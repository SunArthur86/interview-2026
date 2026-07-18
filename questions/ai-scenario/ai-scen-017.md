---
id: ai-scen-017
difficulty: L3
category: ai-scenario
subcategory: AI对话系统设计
tags:
- AI客服
- 意图识别
- 智能转接
- 情绪检测
- RAG
- 自助率
feynman:
  essence: 结合意图识别、知识库检索和情绪检测，自动解答常见问题并智能转接人工。
  analogy: 像初级客服处理简单问题，遇到搞不定或客户生气时，立刻把电话转给主管。
  first_principle: 如何最大化自动化解决常见问题的比例，同时保证复杂问题能平滑过渡到人工服务？
  key_points:
  - 使用RAG检索知识库，结合意图分类精准回答。
  - 设置转人工阈值，基于置信度和情绪判断。
  - 提供智能坐席辅助，人工接管时自动总结前文。
  - 通过解决率和满意度指标持续优化模型。
follow_up:
- 如何平衡AI客服的效率和用户满意度？
- 如何设计合理的转人工策略？
- AI客服如何处理多轮追问中的上下文丢失？
memory_points:
- 核心流程：意图识别（BERT/LLM）→ RAG检索 → 置信度判断 → 低分转人工。
- 知识检索：混合检索（向量+关键词+Rerank），对接CRM实时查订单。
- 人机协作：转人工时自动生成对话摘要，情绪愤怒优先排队。
- 技术选型：首选RAG+LLM，维护成本低；传统FAQ仅用于极简单业务。
- 实战优化：接入结构化数据库，通过Function Calling直接判断退货规则。
---

# 如何设计一个AI智能客服系统？要求能处理80%的常见问题，复杂问题转人工。

【场景分析】
AI客服核心目标：准确理解用户意图、快速解决问题、智能路由人工、持续学习改进。

【系统架构】
1. **意图识别层**：
   - 分类器：Fine-tuned BERT / LLM zero-shot
   - 意图分类：咨询类（查订单/查物流）、操作类（退换货/修改）、投诉类、闲聊类
   - 置信度：低于阈值（0.7）→ 转人工
2. **知识检索层（RAG）**：
   - 产品FAQ库 + 政策文档 + 历史工单
   - 混合检索：向量 + 关键词 + Rerank
   - 实时查询：对接CRM/ERP系统获取用户订单信息
3. **对话管理**：
   - 多轮对话：追问必要信息（订单号、商品名）
   - 情绪检测：用户愤怒/焦虑 → 优先转人工
   - 上下文记忆：同一工单内保持上下文
4. **人工协作层**：
   - 智能转接：自动附带对话摘要和用户画像
   - 坐席辅助：AI实时给人工座席推荐回答
   - 质检：自动评估对话质量

【实战案例】
某电商客服在处理“退货”时，AI常因无法判断“是否拆封”而反复询问。我们在RAG中接入了**结构化商品数据库**，通过Function Calling直接读取商品属性，直接判断是否支持7天无理由，问题解决率提升了15%。

【关键代码】（人工转接与摘要生成）
```python
def escalate_to_human(session_id: str, reason: str):
    history = get_conversation_history(session_id)
    # 调用LLM生成摘要，包含用户诉求、已尝试方案
    summary = llm.invoke(f"请总结以下对话，供人工客服参考。重点包含用户诉求和失败尝试:\n{history}")
    
    ticket = {
        "session_id": session_id,
        "summary": summary.content,
        "user_intent": history.get("intent"),
        "priority": "HIGH" if history.get("sentiment") == "angry" else "NORMAL",
        "timestamp": datetime.now()
    }
    # 推送到人工客服队列
    human_service_queue.push(ticket)
```

【技术方案对比】
| 维度 | 传统FAQ/规则 | RAG + LLM | LLM Fine-tuning |
| :--- | :--- | :--- | :--- |
| **回答准确度** | 低（死板匹配） | 高（语义理解） | 极高（领域适配） |
| **维护成本** | 高（需穷举Q&A） | 中（更新文档库） | 高（需标注数据训练） |
| **幻觉风险** | 无 | 中（需检索校验） | 高（模型自带属性） |
| **启动速度** | 快 | 快 | 慢（需训练周期） |
| **推荐选型** | 极简单业务 | **通用AI客服首选** | 专业术语极多场景 |

```text
┌─────────────┐     1. 用户提问     ┌───────────────┐
│   用户端    │ ──────────────────► │  对话网关     │
└─────────────┘                     └───────┬───────┘
                                            │
                           ┌────────────────┼────────────────┐
                           ▼                ▼                ▼
                   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
                   │  意图识别    │  │  情绪分析    │  │   安全护栏   │
                   │ (BERT/LLM)   │  │  (规则/模型) │  │ (敏感词/注入)│
                   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
                          │                 │                 │
                          ▼                 │                 ▼
                   ┌──────────────┐         │         ┌──────────────┐
                   │ 路由决策     │◄────────┴────────►│  拦截/转接   │
                   │ (置信度判断) │                   └──────────────┘
                   └──┬───────┬───┘
           高置信度   │       │   低置信度/情绪异常
                      │       │
                      ▼       ▼
            ┌───────────────┐ ┌───────────────┐
            │   RAG 检索    │ │  人工客服路由 │
            │ (KB+CRM)      │ │ (生成摘要)    │
            └───────┬───────┘ └───────────────┘
                    │
                    ▼
            ┌───────────────┐
            │   回复生成    │
            │ (LLM Answer)  │
            └───────┬───────┘
                    │
                    ▼
            ┌───────────────┐
            │   人工确认    │
            │ (防幻觉兜底)  │
            └─────────


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

## 记忆要点

- 核心流程：意图识别（BERT/LLM）→ RAG检索 → 置信度判断 → 低分转人工。
- 知识检索：混合检索（向量+关键词+Rerank），对接CRM实时查订单。
- 人机协作：转人工时自动生成对话摘要，情绪愤怒优先排队。
- 技术选型：首选RAG+LLM，维护成本低；传统FAQ仅用于极简单业务。
- 实战优化：接入结构化数据库，通过Function Calling直接判断退货规则。


## 结构化回答

**30 秒电梯演讲：** 结合意图识别、知识库检索和情绪检测，自动解答常见问题并智能转接人工。——打个比方，像初级客服处理简单问题，遇到搞不定或客户生气时，立刻把电话转给主管。

**展开框架：**
1. **核心流程** — 意图识别（BERT/LLM）→ RAG检索 → 置信度判断 → 低分转人工。
2. **知识检索** — 混合检索（向量+关键词+Rerank），对接CRM实时查订单。
3. **人机协作** — 转人工时自动生成对话摘要，情绪愤怒优先排队。

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「如何平衡AI客服的效率和用户满意度」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "设计一个AI智能客服系统，30 秒讲清楚。" | 开场钩子 |
| 0:36 | 概念定义动画 | "一句话：结合意图识别、知识库检索和情绪检测，自动解答常见问题并智能转接人工。" | 核心定义 |
| 1:12 | 核心流程图解 | "意图识别（BERT/LLM）→ RAG检索 → 置信度判断 → 低分转人工。" | 核心流程 |
| 1:48 | 知识检索图解 | "混合检索（向量+关键词+Rerank），对接CRM实时查订单。" | 知识检索 |
| 2:24 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
