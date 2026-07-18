---
id: mt-ai-011
difficulty: L3
category: llm-core
categories:
- eng-practice
- llm-core
subcategory: 企业面试问答
tags:
- 美团
- 面经
- AI产品
- 项目管理
feynman:
  essence: 用结构化叙事展示发现问题、解决问题并创造价值的过程。
  analogy: 像讲一个精彩的英雄故事：遇到大反派（痛点），练绝世武功（技术方案），最终拯救世界（结果）。
  first_principle: 如何证明你的技术投入有效解决了业务痛点并带来了可量化的价值？
  key_points:
  - S-T 要明确背景和量化目标
  - A 要突出技术难点和解决方案
  - R 必须有数据支撑的量化结果
  - 强调 Trade-off 和反思过程
  - 体现数据驱动的迭代思维
follow_up:
- RAG 的准确率怎么评测？—— 人工标注 + LLM-as-Judge + RAGAS 指标
- 成本怎么控制？—— 模型路由（简单走小模型）、缓存、批处理
- 如果准确率不够怎么办？—— 加 Reranker / 混合检索 / Fine-tune Embedding / 调整分块
memory_points:
- STAR框架：S背景讲清痛点，T目标量化指标，A方案突出难点解决，R结果带数据复盘
- 行动环节三层讲：方案选型(为何选Qwen) -> 架构设计(含降级兜底) -> 迭代调优(Bad Case驱动)
- 量化结果模板：准确率/延迟(TP99) + 业务价值(降本增效DAU提升)
- 万能架构：Query改写 -> 意图路由 -> 混合检索 -> Rerank精排 -> LLM带溯源生成
frequency: low
---

# 【美团面经】请说说开发过的 AI 产品/功能是什么？用户需求是什么？最终结果如何？（STAR 回答框架）

**AI 产品面试回答框架（STAR 法）：**

**S（Situation）背景：**
- 业务痛点是什么？（如：信息过载、人工成本高、响应慢）
- 影响范围（用户量/收入/人力成本）？
- 为什么现在做？（时机判断、技术成熟度、竞品分析）

**T（Task）任务：**
- 你的角色和职责？（Owner、算法负责人、工程落地？）
- 目标是什么？（定量指标：准确率>90%、响应<1s、转化率+5%）
- 有什么约束？（预算有限、合规要求、延迟不能超过XX）

**A（Action）行动：**
- **技术方案选型**：为什么选这个模型/方案？（如：选 Qwen 而非 Llama 是因为中文语境好）
- **架构设计**：
  - 整体架构图（见下文）
  - 数据流/调用链
  - 降级策略（模型挂了怎么办？）
- **难点解决**：
  - 延迟优化：KV Cache、量化、投机采样
  - 幻觉抑制：RAG + 引用溯源、Self-Consistency
  - 成本控制：路由小模型 + 大模型复核
- **迭代过程**：v1（MVP）→ v2（优化）做了什么改进？（Bad Case 驱动）

**R（Result）结果：**
- 定量指标：准确率、召回、延迟（TP50/TP99）、Token 成本、DAU/留存率
- 用户反馈：NPS、满意度评分、典型用户评价
- 业务影响：节省人力工时、收入提升、转化率提高
- 学到了什么？（反思：如“数据清洗比模型选择更重要”）

**典型 RAG 系统架构（Action 部分可视化）：**

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │ Question
       ▼
┌───────────────────────────────────────────┐
│            Application Layer              │
├───────────────────────────────────────────┤
│  1. Query Rewrite (意图改写/扩展)          │
│  2. Router (意图路由: 知识库/闲聊/联网)    │
└───────┬───────────────────┬───────────────┘
        │                   │
        ▼                   ▼
┌───────────────┐   ┌──────────────────┐
│  Retriever    │   │  LLM Generation  │
├───────────────┤   └────────┬─────────┘
│ - Dense (ES)  │            │ Prompt + Docs
│ - Sparse (BM)│            │
│ - Vector     │            │
└───────┬───────┘            │
        │ Docs              │
        ▼                   │
┌───────────────┐            │
│   Reranker    │ (精排Top-K) │
└───────┬───────┘            │
        │                   │
        └─────────┬─────────┘
                  │
                  ▼
            ┌─────────┐
            │ Answer  │
            └─────────┘
```

**示例（RAG 知识库）：**
```
S: 公司内部文档分散在飞书/Wiki/共享盘，新员工查找效率低，平均耗时 15min/问题
T: 构建 AI 知识助手，目标：覆盖率 90%、准确率 85%、延迟 <3s
A: 
  - 方案：Embedding + 向量检索 + Reranker + LLM 生成
  - 模型：bge-large-zh（Embedding）+ Qwen2.5-72B（生成）
  - 优化：混合检索(向量+BM25)、查询改写、分块策略调优(512 tokens + overlap)
  - 降级：检索失败→兜底 ES 搜索，LLM 超时→返回热榜问题
R:
  - 准确率从 v1 的 62% → v2 的 88%
  - 平均响应时间 1.8s
  - 月活覆盖 80% 研发，节省 FAQ 人力约 20h/周
```

**代码示例（Hybrid Search with LangChain）：**
```python
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import FAISS

# 1. 稀疏检索
bm25_retriever = BM25Retriever.from_texts(splits)

# 2. 密集检索
vectorstore = FAISS.from_texts(splits, embedding)
faiss_retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

# 3. 加权融合
ensemble_retriever = EnsembleRetriever(
    retrievers=[bm25_retriever, faiss_retriever], 
    weights=[0.3, 0.7]  # 调优参数
)
```



## 核心流程图

```mermaid
flowchart TD
    N0["S-T 要明确背景和量化目标"]
    N1["A 要突出技术难点和解决方案"]
    N2["R 必须有数据支撑的量化结果"]
    N3["强调 Trade-off 和反思过程"]
    N4["体现数据驱动的迭代思维"]
    N0 --> N1
    N1 --> N2
    N2 --> N3
    N3 --> N4
    style N0 fill:#2196F3,color:#fff
    style N1 fill:#FF9800,color:#fff
    style N2 fill:#4CAF50,color:#fff
    style N3 fill:#9C27B0,color:#fff
    style N4 fill:#f44336,color:#fff
    subgraph Legend["图例"]
        L1["🟢 开始/成功"]:::start
        L2["🔵 主流程"]:::process
        L3["🟠 判断/中间态"]:::decision
        L4["🔴 失败/结束"]:::error
    end
```

## 记忆要点

- STAR框架：S背景讲清痛点，T目标量化指标，A方案突出难点解决，R结果带数据复盘
- 行动环节三层讲：方案选型(为何选Qwen) -> 架构设计(含降级兜底) -> 迭代调优(Bad Case驱动)
- 量化结果模板：准确率/延迟(TP99) + 业务价值(降本增效DAU提升)
- 万能架构：Query改写 -> 意图路由 -> 混合检索 -> Rerank精排 -> LLM带溯源生成


## 结构化回答

**30 秒电梯演讲：** 用结构化叙事展示发现问题、解决问题并创造价值的过程。——打个比方，像讲一个精彩的英雄故事：遇到大反派（痛点），练绝世武功（技术方案），最终拯救世界（结果）。

**展开框架：**
1. **STAR框架** — S背景讲清痛点，T目标量化指标，A方案突出难点解决，R结果带数据复盘
2. **行动环节三层讲** — 方案选型(为何选Qwen) -> 架构设计(含降级兜底) -> 迭代调优(Bad Case驱动)
3. **量化结果模板** — 准确率/延迟(TP99) + 业务价值(降本增效DAU提升)

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「RAG 的准确率怎么评测？—— 人工标注 + LLM-as-Judge + RAGAS 指标」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "【美团面经】请说说开发过的 AI 产品/功能是什么，30 秒讲清楚。" | 开场钩子 |
| 0:36 | 概念定义动画 | "一句话：用结构化叙事展示发现问题、解决问题并创造价值的过程。" | 核心定义 |
| 1:12 | STAR框架图解 | "S背景讲清痛点，T目标量化指标，A方案突出难点解决，R结果带数据复盘" | STAR框架 |
| 1:48 | 行动环节三层讲图解 | "方案选型(为何选Qwen) -> 架构设计(含降级兜底) -> 迭代调优(Bad Case驱动)" | 行动环节三层讲 |
| 2:24 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
