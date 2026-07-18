---
id: bd-ai-012
difficulty: L3
category: llm-core
categories:
- ai-agent
- eng-practice
- llm-core
subcategory: Prompt工程
tags:
- 字节
- 面经
- Function Calling
- RAG
- Embedding
feynman:
  essence: Function Calling获取实时结构化数据，RAG检索离线非结构化知识。
  analogy: Function Calling是打电话问实时信息，RAG是去图书馆翻阅历史档案。
  first_principle: 如何将外部世界的实时数据与静态知识高效注入模型上下文？
  key_points:
  - Function Calling适合实时交互和工具执行
  - RAG适合私有知识库和文档问答
  - 向量检索基于语义而非关键词匹配
  - 常用混合检索与重排序提升精度
follow_up:
- Function Calling和RAG能同时用吗？——可以，Agent自主决定调哪个
- RAG的检索效果怎么评估？——Recall@K + MRR + 人工标注准确率
- 向量数据库选型？——Milvus(大规模)/Qdrant(轻量)/Pinecone(托管)
memory_points:
- 核心区别：FC调API获实时/结构化数据，RAG检索文档获离线/非结构化知识
- 选型标准：需实时数据/执行操作(查库发邮件)用FC；需领域知识/私有文档用RAG
- 数据流：FC是Query→API→JSON→LLM；RAG是Query→向量检索→Context→LLM
- RAG关键：Embedding转向量，向量库做语义检索，非关键词匹配
- 实战：静态知识(公积金)用RAG，个性化鉴权数据(年假)必须用FC
frequency: high
---

# 【字节面经】Function Calling与RAG的区别和联系是什么？什么时候用Function Calling，什么时候用RAG？

**两者都是让模型基于真实数据回答，但方式完全不同。**

**Function Calling：** 让模型调用外部接口获取实时数据（天气/股票/数据库查询）。特点是数据实时的、结构化的，模型拿到就能用。

**RAG：** 把私有文档检索出来塞进上下文（公司文档/产品手册/会议纪要）。特点是数据离线的、非结构化的，需要先切片→Embedding→存向量数据库。

**实战案例：** 开发企业知识库助手时，对于“公司公积金比例是多少”这种静态知识用RAG；对于“我的剩余年假是多少”这种个性化、需鉴权查询的数据，必须用Function Calling调用内部HR系统，绝不能把工资表索引到RAG库里。

**代码示例 (OpenAI Tools)：**
```python
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "获取指定城市的实时天气",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"]
        }
    }
}]
# 模型会自主判断是否需要调用 get_weather，而不是生成文本猜测天气
```

**什么时候用哪个？**
- 需要实时数据或需要执行操作 → Function Calling
- 需要领域知识或私有文档 → RAG
- 实际项目中经常两者结合：RAG提供知识背景，Function Calling提供实时数据和执行能力

**Function Calling 与 RAG 对比表：**

| 维度 | Function Calling (工具调用) | RAG (检索增强生成) |
| :--- | :--- | :--- |
| **数据来源** | 外部 API/数据库 (SQL, HTTP) | 向量数据库/文档索引 |
| **数据时效性** | 实时 | 取决于索引更新频率 (通常有延迟) |
| **数据结构** | 高度结构化 (JSON/SQL结果) | 非结构化 (文本片段) |
| **适用场景** | 查库存、发邮件、算数、私有数据查询 | 知识问答、文档总结、合规建议 |
| **Token消耗** | 低 (仅传递参数和结果) | 高 (需要把长文本塞入Context) |

**Embedding/向量数据库在RAG中的作用：**
- Embedding是RAG的翻译官，把文本转成向量，语义相近的向量距离就近
- 向量数据库是存这些向量的专用仓库（Milvus/Pinecone/Qdrant），核心能力是快速做相似度检索
- RAG的检索不是关键词匹配而是算向量距离

**Function Calling 与 RAG 流程对比：**
```text
Function Calling 流程:          RAG 流程:
User Query                       User Query
    ↓                                ↓
┌─────────────┐                ┌───────────────────┐
│   Intent    │                │   Query Rewrite   │
│Classification│               └─────────┬─────────┘
└──────┬──────┘                          │
       │                                 ↓
       ↓                         ┌───────────────────┐
┌─────────────┐                │  Vector Retrieval │ (Semantic Search)
│   External  │                └─────────┬─────────┘
│   API Call  │                          │
└──────┬──────┘                          ↓
       │                         ┌───────────────────┐
       ↓                         │  Context (Chunks) │
┌─────────────┐                └─────────┬─────────┘
│ Structured  │                          │
│    Data     │                          ↓
└──────┬──────┘                    ┌───────────────────┐
       │                           │   LLM Generation │
       └───────────┬───────────────┴─────────┬─────────┘
                   ↓                           ↓
              Final Answer (Fact+Reasoning)
```

**检索策略设计关键点：**
1. 混合检索（向量+关键词，用RRF融合）
2. Chunk大小要调（512-1024 Token，带重叠）
3. HyDE（先生成假答案再检索）
4. Rerank（Cross-Encoder重排提升精度）

## 常见考点
1. **参数缺失**：如果Function Call需要的参数用户没给，是直接报错还是反问用户？（策略：反问用户补充信息，不要自己瞎编参数）
2. **多跳查询**：RAG中遇到复杂问题需要多次检索才能回答，如何设计？（Agent推理链路：Answer A -> Question B -> Retrieve B -> Synthesize）
3. **时效性差异**：RAG适合解决时效性问题吗？（不适合，除非向量库更新频率极高，否则实时数据还是得靠Function Calling）

## 核心流程图

```mermaid
flowchart LR
    TASK["用户任务<br/>'翻译这段话'"] --> PROMPT["Prompt 构造"]
    PROMPT --> ZERO["Zero-shot<br/>直接提问"]
    PROMPT --> FEW["Few-shot<br/>附带示例"]
    PROMPT --> COT["Chain-of-Thought<br/>'让我们一步步思考'"]
    ZERO --> LLM["LLM 推理"]
    FEW --> LLM
    COT --> LLM
    LLM --> OUTPUT["输出结果"]
    GUARD["Guardrails<br/>注入检测/越狱防护"] --> PROMPT
    style FEW fill:#2196F3,color:#fff
    style COT fill:#4CAF50,color:#fff
    style GUARD fill:#f44336,color:#fff

```

## 记忆要点

- 核心区别：FC调API获实时/结构化数据，RAG检索文档获离线/非结构化知识
- 选型标准：需实时数据/执行操作(查库发邮件)用FC；需领域知识/私有文档用RAG
- 数据流：FC是Query→API→JSON→LLM；RAG是Query→向量检索→Context→LLM
- RAG关键：Embedding转向量，向量库做语义检索，非关键词匹配
- 实战：静态知识(公积金)用RAG，个性化鉴权数据(年假)必须用FC

## 结构化回答

**30 秒电梯演讲：** Function Calling获取实时结构化数据，RAG检索离线非结构化知识。——打个比方，Function Calling是打电话问实时信息，RAG是去图书馆翻阅历史档案。

**展开框架：**
1. **核心区别** — FC调API获实时/结构化数据，RAG检索文档获离线/非结构化知识
2. **选型标准** — 需实时数据/执行操作(查库发邮件)用FC；需领域知识/私有文档用RAG
3. **数据流** — FC是Query→API→JSON→LLM；RAG是Query→向量检索→Context→LLM

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「Function Calling和RAG能同时用吗？——可以，Agent自主决定调哪个」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "【字节面经】Function Calling与RAG的区别和联系是什么，30 秒讲清楚。" | 开场钩子 |
| 0:36 | 概念定义动画 | "一句话：Function Calling获取实时结构化数据，RAG检索离线非结构化知识。" | 核心定义 |
| 1:12 | 核心区别图解 | "FC调API获实时/结构化数据，RAG检索文档获离线/非结构化知识" | 核心区别 |
| 1:48 | 选型标准图解 | "需实时数据/执行操作(查库发邮件)用FC；需领域知识/私有文档用RAG" | 选型标准 |
| 2:24 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |

### 视频流程图

```mermaid
flowchart LR

    subgraph Intro["🎥 引入"]
        N0["【字节面经】Function Ca…<br/>0:00"]:::intro
    end

    subgraph Core["📖 核心讲解"]
        N1["Function Calling获取实时结构化数<br/>0:36"]:::core
        N2["核心区别图解<br/>1:12"]:::core
    end

    subgraph Practice["🔧 实战"]
        N3["选型标准图解<br/>1:48"]:::practice
    end

    subgraph Wrap["🎬 收尾"]
        N4["总结回顾 & 下期预告<br/>2:24"]:::wrap
    end

    N0 --> N1 --> N2 --> N3 --> N4

    classDef intro fill:#FF9800,color:#fff
    classDef core fill:#2196F3,color:#fff
    classDef deep fill:#4CAF50,color:#fff
    classDef practice fill:#9C27B0,color:#fff
    classDef wrap fill:#607D8B,color:#fff
```


