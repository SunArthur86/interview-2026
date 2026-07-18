---
id: sarg-003
difficulty: L2
category: ai-agent
subcategory: RAG技术
images:
- svg_rag.svg
feynman:
  essence: 选择能精准捕捉语义且匹配场景需求的高质量向量化模型。
  analogy: 像选翻译，既要懂语言（中文），又要懂专业（领域）。
  first_principle: 如何将文本转化为能准确表达语义且高效的向量表示？
  key_points:
  - 优先考虑语言支持和MTEB排名
  - 权衡维度大小与存储/检索成本
  - 根据算力选择API或本地部署
  - 长文档场景注意Context Window长度
memory_points:
- 选型维度：语言支持（中文选BGE）、维度权衡（精度vs速度）、上下文长度
- 混合检索：Dense（向量语义）+ Sparse（关键词BM25）互补，效果最佳
- 评估标准：参考MTEB排行榜Retrieval任务，而非总榜
- 实战建议：通用选OpenAI，中文选BGE系列，长文档选支持8k长度的模型
frequency: medium
---

# 如何选择Embedding模型？

Embedding 模型决定了 RAG 检索的“天花板”，直接影响了语义匹配的准确度。

### 选择维度与细节

1.  **多语言与领域支持**
    *   **通用英文**：OpenAI `text-embedding-3-small/large`（性能强，维度可选）。
    *   **中文场景**：BAAI `bge-large-zh` 或 `bge-small-zh`（目前中文社区公认效果较好）。
    *   **多语言**：BAAI `bge-m3`（支持 100+ 种语言，且支持长文本）。

2.  **维度与性能权衡**
    *   **高维 (1024/1536)**：信息量大，精度高，但存储成本高、检索计算慢。如 `bge-large`, `OpenAI ada-002`。
    *   **低维 (384/512)**：速度快，存储省，适合海量数据或低延迟场景。如 `bge-small`。
    *   **Matryoshka (嵌套维度)**：OpenAI `text-embedding-3` 支持动态截断维度，无需重新训练即可在精度和速度间灵活切换。

3.  **检索类型**
    *   **Dense Retrieval (稠密检索)**：传统向量检索，适合语义匹配。
    *   **Sparse Retrieval (稀疏检索)**：如 BM25、Splade，适合精确关键词匹配（如人名、型号）。
    *   **混合检索**：最佳实践通常是 `Dense (向量) + Sparse (关键词)` 结合，互补长短。`bge-m3` 同时支持这两种能力。

4.  **上下文长度**
    *   传统模型通常限制在 **512 tokens**。超过长度的文本需切分，会导致上下文割裂。
    *   新一代模型如 `bge-m3` 或 `jina-embeddings-v2` 支持 **8192 tokens**，可以直接对长段落进行编码，保持语义完整性。

### 评估指标
参考 **MTEB (Massive Text Embedding Benchmark)** 排行榜，重点关注 **Retrieval** 类目的数据集表现，而非总榜（因为总榜包含分类、聚类等任务，不完全代表 RAG 检索能力）。

### 实战案例
*   **专有名词检索失效**：某医疗项目使用通用 `text-embedding-ada-002`，搜“心梗”无法匹配到“心肌梗死”的文档。后微调 BGE 模型注入医疗术语同义词对，召回率提升 30%。
*   **性能降级踩坑**：在 1000 万级数据量下，使用 1536 维向量导致检索延迟超过 500ms。切换为 `bge-small-zh` (512维) 并开启 PQ 量化，延迟降至 50ms 且精度损失极小。

### 代码示例 (Python - 混合检索配置)
```python
from langchain.retrievers import BM25Retriever, EnsembleRetriever
from langchain.vectorstores import FAISS

# 1. 初始化两个检索器
vectorstore = FAISS.from_texts(texts, embedding=embeddings)
vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

bm25_retriever = BM25Retriever.from_texts(texts)
bm25_retriever.k = 5

# 2. 集成混合检索 (加权融合)
ensemble_retriever = EnsembleRetriever(
    retrievers=[bm25_retriever, vector_retriever],
    weights=[0.5, 0.5] # 关键词与向量各占一半权重
)
```

### 主流 Embedding 模型对比
| 模型 | 维度 | 优势 | 劣势 | 推荐场景 |
|------|------|------|------|----------|
| **OpenAI text-embedding-3** | 1536/3072 (可缩放) | 综合能力强，支持 Matryoshka | 需付费，需代理访问 | 通用商业项目，追求效果 |
| **BAAI bge-m3** | 1024 | 多语言，支持 8192 长文本，支持稠密+稀疏 | 推理速度较慢 | 多语言混合，长文档检索 |
| **BAAI bge-large-zh** | 1024 | 中文语义理解极强 | 显存占用较高 | 纯中文高精度场景 |
| **Jina Embeddings v2** | 768 | 支持 8192 长度，开源友好 | 细粒度匹配略逊于 BGE | 英文为主的长上下文 |

## 常见考点
1.  **微调过的 Embedding 模型比通用模型好在哪里？**
    在特定领域（如医疗、法律）的数据上微调后，模型能学会该领域的“行话”和语义距离，解决通用模型对专业术语理解偏差的问题。
2.  **向量归一化的作用是什么？**
    将向量模长变为 1，使得相似度计算简化为点积，且便于使用余弦相似度进行空间度量，消除文本长度对相似度分数的影响。
3.  **如何评估 Embedding 是否适合我的数据？**
    构造一个包含“Query-正文档-负文档”的小规模测试集，计算 Recall@k 或 MRR 指标进行实测。

## 核心流程图

```mermaid
flowchart TB
    classDef start fill:#4CAF50,color:#fff
    classDef process fill:#2196F3,color:#fff
    classDef decision fill:#FF9800,color:#fff
    classDef special fill:#9C27B0,color:#fff
    classDef error fill:#f44336,color:#fff
    classDef info fill:#607D8B,color:#fff
    class BGE start
    class Benchmark process
    class Choose decision
    class Code special
    class Code2 error
    class Cost info
    class Dim start
    class Domain process
    class E5 decision
    class Embedding special
    class Factors error
    class GTE info
    class Lang start
    class MTEB process
    class MaxLen decision
    class Models special
    class OpenAI error
    class Voyage info
    class code start
    class embedding process
    class text decision
    Choose["选 Embedding 模型"] --> Factors["考量因素"]
    Factors --> Lang["语言: 中/英/多语言"]
    Factors --> Dim["维度: 768/1024/1536"]
    Factors --> Domain["领域: 通用/代码/医疗"]
    Factors --> MaxLen["最大长度"]
    Factors --> Cost["成本/部署"]
    Lang --> Models["主流模型"]
    Models --> BGE["BGE (中/多语言)"]
    Models --> OpenAI["OpenAI text-embedding"]
    Models --> E5["E5 / GTE"]
    Models --> Code2["Code: Voyage/code-"]
    Choose --> Benchmark["基准: MTEB 排行榜"]
```

## 记忆要点

- 选型维度：语言支持（中文选BGE）、维度权衡（精度vs速度）、上下文长度
- 混合检索：Dense（向量语义）+ Sparse（关键词BM25）互补，效果最佳
- 评估标准：参考MTEB排行榜Retrieval任务，而非总榜
- 实战建议：通用选OpenAI，中文选BGE系列，长文档选支持8k长度的模型

## 结构化回答

**30 秒电梯演讲：** Embedding 模型决定了 RAG 检索的天花板。选型盯三个维度：语言（中文优先 BGE）、维度（高维精度高但慢，低维省成本）、上下文长度（长文档选支持 8k 的）。别迷信总榜，要看 MTEB 的 Retrieval 任务排名。最佳实践是 Dense 向量 + Sparse 关键词的混合检索。

**展开框架：**
1. **三大选型维度** — 语言支持（中文选 BGE-large-zh，多语言选 bge-m3）、维度权衡（1024/1536 精度高但贵，384/512 快且省）、上下文长度（传统 512，新一代 bge-m3/jina 支持 8192）。
2. **混合检索** — Dense 向量抓语义 + Sparse（BM25/Splade）抓精确关键词，互补长短，bge-m3 一站式支持两种。
3. **评估标准** — 看 MTEB 排行榜的 Retrieval 类目，不是总榜；通用选 OpenAI，中文选 BGE，长文档选 8k 长度模型。

**收尾：** 我在医疗项目用通用 ada-002 搜"心梗"匹配不到"心肌梗死"，微调 BGE 注入术语同义词对后召回率提 30%。您想聊混合检索的权重怎么配，还是 Embedding 微调怎么做？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：Embedding 怎么选 | "Embedding 选错，RAG 检索天花板就定了。三个维度盯死。" | 开场钩子 |
| 0:15 | 三大选型维度图 | "语言：中文选 BGE；维度：高维精度高低维省成本；长度：长文档选支持 8k 的。" | 选型维度 |
| 0:45 | 主流模型对比表 | "OpenAI 通用强，bge-large-zh 中文最准，bge-m3 多语言加长文本，jina 长上下文。" | 模型对比 |
| 1:10 | Dense + Sparse 混合检索图 | "最佳实践：Dense 向量抓语义 + BM25 抓关键词，混合互补，效果最好。" | 混合检索 |
| 1:35 | 医疗术语召回案例 | "实战：通用模型搜心梗匹配不到心肌梗死，微调 BGE 注入同义词对，召回提 30%。" | 实战案例 |
| 1:55 | 总结卡 | "口诀：看 MTEB Retrieval 榜，中文 BGE，混合检索最稳。下期讲 Rerank。" | 收尾 |

### 视频流程图

```mermaid
flowchart LR

    subgraph Intro["🎥 引入"]
        N0["Embedding 怎么选<br/>0:00"]:::intro
    end

    subgraph Core["📖 核心讲解"]
        N1["三大选型维度图<br/>0:15"]:::core
        N3["Dense + Sparse 混合检索图<br/>1:10"]:::deep
    end

    subgraph Practice["🔧 实战"]
        N2["主流模型对比表<br/>0:45"]:::practice
        N4["医疗术语召回案例<br/>1:35"]:::practice
    end

    subgraph Wrap["🎬 收尾"]
        N5["口诀：看 MTEB Retrieval 榜，中文<br/>1:55"]:::wrap
    end

    N0 --> N1 --> N2 --> N3 --> N4 --> N5

    classDef intro fill:#FF9800,color:#fff
    classDef core fill:#2196F3,color:#fff
    classDef deep fill:#4CAF50,color:#fff
    classDef practice fill:#9C27B0,color:#fff
    classDef wrap fill:#607D8B,color:#fff
```


