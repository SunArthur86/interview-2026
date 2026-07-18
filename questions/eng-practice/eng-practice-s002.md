---
id: eng-practice-s002
difficulty: L2
category: eng-practice
subcategory: 工程化实战
feynman:
  essence: 建立多维度体系判断模型表现是否满足业务需求。
  analogy: 像体检，既要做常规检查（基准测试），也要看主观感受（人工评估），还要关注日常工作状态（在线指标）。
  first_principle: 如何全面、客观地衡量一个复杂AI系统在实际应用中的真实效果？
  key_points:
  - 结合离线基准测试与在线业务指标
  - 利用LLM-as-Judge实现低成本自动评估
  - 针对RAG场景关注忠实度与上下文召回
  - 评估标准需与具体业务目标对齐
memory_points:
- 离线评估：基准测试（MMLU/GSM8K），自动评估（RAGAS/LLM-as-Judge），人工评估。
- 在线评估：用户反馈（点赞/点踩），业务指标（任务完成率/交互轮数）。
- RAGAS 核心：Faithfulness（忠实度）、Relevancy（相关性）、Context Recall（召回）。
- 评估策略：逻辑用 LLM-as-Judge，语气用用户指标；离线测选型，在线测价值。
frequency: low
---

# 如何评估LLM应用的效果？

LLM应用评估是多维度的，通常分为离线评估和在线评估两个阶段：

### 1. 离线基准测试
- **通用能力**: MMLU (多任务理解), GSM8K (数学推理), HumanEval (代码生成), C-Eval/CMMLU (中文评测)
- **局限性**: 基准测试分数与实际业务表现往往相关度不高，仅作为模型选型参考

### 2. 自动评估
- **基础指标**: Exact Match / F1 Score (适用于事实性问答)
- **生成质量**: BLEU / ROUGE (传统NLP指标，对LLM相关性判断较弱)
- **LLM-as-Judge**: 使用 GPT-4 等强模型对回答进行打分（需设计好评分Rubric，解决偏好性问题和位置偏差）
- **RAGAS**: RAG专用评估框架
  - **Faithfulness** (忠实度): 答案是否完全源于上下文
  - **Relevancy** (相关性): 答案是否解决了问题
  - **Context Recall**: 检索到的上下文是否包含了标准答案的所有信息

### 3. 人工评估
- **Elo Rating**: 类似棋手的等级分系统，基于对抗胜负更新分数
- **Pairwise Comparison**: 展示两个回答，人工选择更优的一个（比绝对打分更容易）
- **标注质量评估**: 计算标注员之间的一致性

### 4. 在线指标
- **用户反馈**: 点赞/点踩率
- **业务指标**: 任务完成率、平均交互轮数、重试率

> **💡 实战案例**：在某客服机器人评估中，GPT-4作为打分器给出的“逻辑正确性”分数与人类专家相关性极高（0.9），但在“语气亲和力”上相关性极低（0.3）。最终采用了**分层评估**：逻辑用LLM-as-Judge，语气用用户点赞指标。

> **🧱 代码示例（Python - 使用 RAGAS 计算忠实度）**
> ```python
> from ragas import evaluate
> from ragas.metrics import faithfulness
> from datasets import Dataset
>
> # 准备数据
data_samples = {
>     'question': ['纳斯达克指数是多少？'],
>     'answer': ['纳斯达克指数目前为13,000点。'],
>     'contexts': [['道琼斯指数是33,000点，标普500是4,100点。']] # 故意给错误的上下文
> }
> dataset = Dataset.from_dict(data_samples)
>
> # 运行评估
> score = evaluate(dataset, metrics=[faithfulness])
> print(score['faithfulness']) # 预期输出接近 0
> ```

### 评估方法对比

| 维度 | 离线评估 | 在线评估 |
|------|----------|----------|
| **目的** | 模型选型、版本对比、安全测试 | 验证业务价值、用户体验监控 |
| **数据来源** | 黄金测试集、生产日志采样 | 真实用户流量、A/B 测试分流 |
| **反馈速度** | 快，可即时迭代 | 慢，需积累一定流量才显著 |
| **核心指标** | 准确率、召回率、Ragas分数 | 转化率、留存率、用户满意度 |
| **成本** | Token 消耗（LLM-as-Judge） | 潜在的业务损失（如果Bad Case上线） |

### 评估流程架构
```text
┌─────────────┐
│  生产环境   │─────┐
└──────┬──────┘     │ (采样日志)
       │           │
       ▼           ▼
┌──────────────────────────┐
│      评估数据集         │
└──────┬───────────┬───────┘
       │           │
       ▼           ▼
┌──────────┐  ┌──────────┐
│ 规则匹配 │  │ LLM评测 │
│(F1/EM)   │  │(GPT-4)  │
└─────┬────┘  └─────┬────┘
      │            │
      └─────┬──────┘
            ▼
     ┌──────────────┐
     │  综合评分看板│
     └──────────────┘
```

## 常见考点
1. **LLM-as-Judge 的位置偏差如何解决？**：即模型倾向于认为排在前面的回答更好，需通过交换位置多次测试取平均来消除。
2. **RAG 评估中的 Faithfulness 和 Context Recall 的具体计算方式？**：通常是将答案切分成陈述句，然后分别验证其是否被上下文支持。
3. **如何构建高质量的黄金测试集？**：讨论生成式构建（用LLM生成Q&A）与人工校验的结合。


## 核心流程图

```mermaid
flowchart TD
    Start([🚀 多线程并发任务]):::start
    Submit[提交任务到线程池<br/>execute / submit]:::process
    CoreQ{{核心线程数满?<br/>corePoolSize}}:::decision
    NewCore[创建核心线程<br/>立即执行]:::process
    QueueQ{{工作队列满?<br/>workQueue}}:::decision
    Enqueue[任务入队<br/>LinkedBlockingQueue]:::process
    MaxQ{{达到最大线程数?<br/>maxPoolSize}}:::decision
    NewWorker[创建非核心线程]:::process
    RejectQ{{拒绝策略?<br/>RejectedHandler}}:::decision
    Abort[AbortPolicy<br/>抛异常]:::danger
    Caller[CallerRunsPolicy<br/>调用线程执行]:::process
    Discard[DiscardPolicy<br/>丢弃]:::warn
    Worker[Worker 线程<br/>循环 take 任务]:::process
    SyncQ{{是否需要同步?<br/>共享资源}}:::decision
    CAS[CAS 无锁操作<br/>compareAndSwap]:::process
    Lock[加锁 synchronized / AQS]:::process
    VolatileQ{{可见性需求?<br/>禁止指令重排}}:::decision
    Volatile[volatile 修饰<br/>内存屏障]:::process
    Final[业务执行完成]:::process
    WaitQ{{是否需要等待?<br/>Future/Condition}}:::decision
    Future[CompletableFuture<br/>异步编排]:::process
    Done([✅ 任务完成]):::start

    Start --> Submit --> CoreQ
    CoreQ -->|否| NewCore --> Worker
    CoreQ -->|是| QueueQ
    QueueQ -->|否| Enqueue --> Worker
    QueueQ -->|是| MaxQ
    MaxQ -->|否| NewWorker --> Worker
    MaxQ -->|是| RejectQ
    RejectQ -->|默认| Abort
    RejectQ -->|降级| Caller
    RejectQ -->|容忍| Discard
    Worker --> SyncQ
    SyncQ -->|无锁| CAS --> Final
    SyncQ -->|互斥| Lock --> VolatileQ
    VolatileQ -->|是| Volatile --> Final
    VolatileQ -->|否| Final
    Final --> WaitQ
    WaitQ -->|是| Future --> Done
    WaitQ -->|否| Done

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef warn fill:#fee2e2,stroke:#ef4444,color:#7f1d1d;
    classDef danger fill:#b91c1c,stroke:#7f1d1d,color:#fff,stroke-width:2px;

```

## 记忆要点

- 离线评估：基准测试（MMLU/GSM8K），自动评估（RAGAS/LLM-as-Judge），人工评估。
- 在线评估：用户反馈（点赞/点踩），业务指标（任务完成率/交互轮数）。
- RAGAS 核心：Faithfulness（忠实度）、Relevancy（相关性）、Context Recall（召回）。
- 评估策略：逻辑用 LLM-as-Judge，语气用用户指标；离线测选型，在线测价值。


## 结构化回答

**30 秒电梯演讲：** 建立多维度体系判断模型表现是否满足业务需求。——打个比方，像体检，既要做常规检查（基准测试），也要看主观感受（人工评估），还要关注日常工作状态（在线指标）。

**展开框架：**
1. **离线评估** — 基准测试（MMLU/GSM8K），自动评估（RAGAS/LLM-as-Judge），人工评估。
2. **在线评估** — 用户反馈（点赞/点踩），业务指标（任务完成率/交互轮数）。
3. **RAGAS 核心** — Faithfulness（忠实度）、Relevancy（相关性）、Context Recall（召回）。

**收尾：** 以上三点都能配合实战聊。您想深入聊哪一块？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "评估LLM应用的效果，30 秒讲清楚。" | 开场钩子 |
| 0:30 | 概念定义动画 | "一句话：建立多维度体系判断模型表现是否满足业务需求。" | 核心定义 |
| 1:00 | 离线评估图解 | "基准测试（MMLU/GSM8K），自动评估（RAGAS/LLM-as-Judge），人工评估。" | 离线评估 |
| 1:30 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
