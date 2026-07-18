---
id: misc-027
difficulty: L2
category: ai-basics
subcategory: RAG与向量检索
tags:
- IO
- GC
feynman:
  essence: 结合关键词的精确匹配和向量检索的语义理解。
  analogy: 像查字典，既看目录索引（关键词）又看内容理解（语义），两头都不误。
  first_principle: 如何同时满足精确查找（如人名）和模糊理解（如同义词）的检索需求？
  key_points:
  - BM25精准匹配专有名词，弱在语义
  - 向量检索擅长模糊匹配，弱在精确字符
  - RRF是混合排序的主流算法
follow_up:
- RRF为什么比加权平均更常用?
- 如何确定alpha参数?
memory_points:
- 混合检索=BM25(精确匹配)+向量(语义匹配)，互补短板。
- 融合方法：RRF(倒数排名融合，无需归一化，最常用) 或 加权平均(需归一化)。
- RRF公式：sum(1/(k+rank))，k通常取60。
- 适用场景：专业术语多(医疗/法律)、包含缩写或需同时处理语义和拼写错误。
frequency: high
---

# 什么是混合检索(Hybrid Search)?BM25和向量检索如何融合

- **为什么需要混合检索:**

- **BM25(关键词检索):** 擅长精确匹配(产品名、人名、术语),但不理解语义
- **向量检索(语义检索):** 擅长语义相似,但精确匹配弱
- **混合 = 两者优势互补**

- **融合方法:**

1. **RRF (Reciprocal Rank Fusion):**
score = sum(1 / (k + rank_i))
- k通常取60
- 简单有效,不需要分数归一化
- **最常用**

2. **加权平均:**
score = alpha * norm(bm25_score) + (1-alpha) * norm(vector_score)
- 需要将两种分数归一化到[0,1]
- alpha通常0.5-0.7

- **架构流程:**

```text
┌─────────────┐
│   User Query│
└──────┬──────┘
       │
       ├──────────────────┐
       │                  │
       ▼                  ▼
┌──────────────┐   ┌──────────────┐
│ BM25 Search  │   │ Vector Search│
│ (Sparse)     │   │ (Dense)      │
└──────┬───────┘   └──────┬───────┘
       │                  │
       │     Top-K Docs    │
       ▼                  ▼
       └────────┬─────────┘
                │
                ▼
       ┌──────────────────┐
       │ Score Fusion     │
       │ (RRF / Weighted) │
       └────────┬─────────┘
                │
                ▼
       ┌──────────────────┐
       │ Final Ranked List│
       └──────────────────┘
```

- **实践:**
- Weaviate/Qdrant原生支持混合检索
- LangChain的EnsembleRetriever封装了RRF

- **实战案例:** 在某医疗问答项目中，用户查询“阿司匹林”。纯向量检索可能召回“止痛药”等语义相关但泛化的内容，混合检索通过BM25的强匹配能力，精准召回说明书中包含“阿司匹林”关键词的段落，解决了专业名词召回不准的问题。

- **代码示例:**
```python
from rank_bm25 import BM25Okapi
from sklearn.preprocessing import MinMaxScaler
import numpy as np

# 假设 bm25_scores 和 vector_scores 已获取
# 1. 归一化 (Min-Max)
scaler = MinMaxScaler()
bm25_norm = scaler.fit_transform(np.array(bm25_scores).reshape(-1, 1)).flatten()
vector_norm = scaler.fit_transform(np.array(vector_scores).reshape(-1, 1)).flatten()

# 2. 加权融合 (alpha=0.7偏向BM25)
alpha = 0.7
final_scores = alpha * bm25_norm + (1 - alpha) * vector_norm
```

- **对比表格:**

| 特性 | RRF (倒数排名融合) | 加权平均 | 纯向量/纯BM25 |
| :--- | :--- | :--- | :--- |
| **核心逻辑** | 基于排名倒数的求和 | 基于分数的线性加权 | 单一信号源 |
| **分数归一化** | **不需要** (对数值不敏感) | **必须** (需对齐量纲) | 不适用 |
| **鲁棒性** | 高 (抗分数波动) | 中 (受归一化参数影响) | 低 (单一短板) |
| **实现复杂度** | 低 | 中 (需调参alpha) | 最低 |
| **适用场景** | 通用型，分数分布不一致时 | 分数分布已知且可信时 | 数据特征极其单一时 |

## 常见考点
1. **为什么分数需要归一化？**
   - BM25分数范围通常在0-20+，向量余弦相似度在-1到1。直接加权会导致向量检索权重被淹没，必须归一化（如Min-Max或Sigmoid）。

2. **RRF中的参数k起什么作用？**
   - k控制排名对分数的影响程度。k越大，低排名的结果贡献越小。通常取值为60，是一个经验常数。

3. **混合检索在哪些场景下效果提升最明显？**
   - 专业术语多（如医疗、法律）、用户查询包含缩写、或需要同时处理语义和拼写错误的场景。


## 核心流程图

```mermaid
flowchart TD
    Start([🚀 SQL 请求到达]):::start
    Parser[解析器 Parser<br/>词法/语法分析]:::process
    AST[生成抽象语法树 AST]:::process
    Preproc[预处理器<br/>语义检查 + 权限]:::process
    Optimizer[优化器 Optimizer]:::process
    CostQ{{基于代价选择?<br/>CBO}}:::decision
    IdxScan[索引扫描<br/>range/ref]:::process
    FullScan[全表扫描<br/>ALL]:::warn
    Execute[执行器 Executor<br/>调用存储引擎接口]:::process
    EngineQ{{存储引擎?<br/>InnoDB/MyISAM}}:::decision
    InnoDB[InnoDB 引擎]:::process
    BufferPool[Buffer Pool<br/>内存缓冲池]:::store
    HitQ{{页命中 Buffer Pool?}}:::decision
    ReadDisk[从磁盘读取页<br/>随机 IO]:::warn
    RedoLog[(redo log<br/>WAL 先写日志)]:::store
    BinLog[(binlog<br/>主从复制)]:::store
    UndoLog[(undo log<br/>事务回滚/MVCC)]:::store
    CommitQ{{是否提交事务?<br/>2PC}}:::decision
    TwoPhase[Prepare → 写 redo<br/>→ 写 binlog → Commit]:::process
    Crash[宕机崩溃恢复<br/>redo 重放 + binlog 校验]:::danger
    Final([✅ 返回结果集]):::start

    Start --> Parser --> AST --> Preproc --> Optimizer
    Optimizer --> CostQ
    CostQ -->|有合适索引| IdxScan --> Execute
    CostQ -->|无索引/全表| FullScan --> Execute
    Execute --> EngineQ
    EngineQ -->|默认| InnoDB --> BufferPool
    EngineQ -->|旧版| FullScan
    BufferPool --> HitQ
    HitQ -->|命中| Execute
    HitQ -->|未命中| ReadDisk --> BufferPool
    InnoDB -.修改.-> UndoLog
    InnoDB -.修改.-> RedoLog
    InnoDB -.提交.-> BinLog
    Execute --> CommitQ
    CommitQ -->|是| TwoPhase --> Final
    CommitQ -->|崩溃| Crash --> RedoLog

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef store fill:#8b5cf6,stroke:#6d28d9,color:#fff;
    classDef warn fill:#fee2e2,stroke:#ef4444,color:#7f1d1d;
    classDef danger fill:#b91c1c,stroke:#7f1d1d,color:#fff,stroke-width:2px;

```

## 记忆要点

- 混合检索=BM25(精确匹配)+向量(语义匹配)，互补短板。
- 融合方法：RRF(倒数排名融合，无需归一化，最常用) 或 加权平均(需归一化)。
- RRF公式：sum(1/(k+rank))，k通常取60。
- 适用场景：专业术语多(医疗/法律)、包含缩写或需同时处理语义和拼写错误。

## 结构化回答

**30 秒电梯演讲：** 混合检索是 BM25 加向量检索，互补短板。BM25 擅长精确匹配专有名词，向量检索擅长语义理解。融合方法主流是 RRF（倒数排名融合），公式是对 1 除以 k 加 rank 求和，k 通常取 60，它的好处是无需对分数归一化。适合专业术语多、有缩写、或要同时处理语义和拼写错误的场景。

**展开框架：**
1. **互补逻辑** — BM25 基于词频做精确字符匹配，强在人名、术语、缩写；向量检索基于语义相似度，强在同义、改写；两者互补，单用任一个都有盲区。
2. **融合方法** — RRF（倒数排名融合）按排名而非分数融合，公式 sum(1/(k+rank))，k 常取 60，无需归一化、对分数尺度不敏感，所以最常用；加权平均需要归一化，调参更麻烦。
3. **适用场景** — 医疗法律等专业术语多、包含缩写、需同时处理语义理解和拼写错误的场景，混合检索明显优于单一方式。

**收尾：** 一句话，混合检索是 RAG 召回质量的标配。您想深入聊聊 RRF 为什么比加权平均更常用，还是 alpha 参数怎么定？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题《混合检索》+ 查字典漫画：目录索引 + 内容理解 | 混合检索像查字典，既看目录索引做关键词匹配，又看内容做语义理解，两头都不误。 | 类比开场 |
| 0:25 | BM25 vs 向量检索 对比图 | BM25 基于词频做精确匹配，强在人名、术语、缩写；向量检索基于语义相似度，强在同义改写。两者互补。 | 互补逻辑 |
| 0:55 | RRF 公式：sum(1/(k+rank))，k=60 | 融合方法主流是 RRF，倒数排名融合，公式是对 1 除以 k 加 rank 求和，k 通常取 60，好处是无需归一化分数。 | RRF 融合 |
| 1:25 | RRF vs 加权平均 对比 | 相比加权平均需要归一化、调参麻烦，RRF 按排名融合对分数尺度不敏感，所以最常用。 | 方法对比 |
| 1:50 | 适用场景图标：医疗/法律/缩写/拼写错误 | 适合专业术语多、有缩写、或要同时处理语义和拼写错误的场景，比如医疗、法律。 | 适用场景 |

