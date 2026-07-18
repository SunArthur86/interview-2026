---
id: sarg-001
difficulty: L1
category: ai-agent
subcategory: RAG技术
images:
- svg_rag.svg
feynman:
  essence: 给LLM外挂知识库，通过检索增强生成答案的准确性。
  analogy: 像考试时允许翻书，遇到不懂的问题查资料再作答。
  first_principle: 如何在不重新训练模型的情况下，让LLM掌握外部知识？
  key_points:
  - 离线索引文档，在线检索增强
  - 解决知识时效性和私有化问题
  - 显著减少幻觉并提供来源
  - 无需训练，落地成本低
memory_points:
- 核心定义：检索+生成，解决大模型知识时效性差和无法访问私有数据问题
- 基本流程：离线文档切片向量化 -> 在线查询检索 -> Prompt构建 -> LLM生成
- 核心价值：降低幻觉（基于事实）、可解释性（引用来源）、低成本更新知识
- 对比微调：RAG适合动态知识库，微调适合调整风格和推理模式
---

# RAG的基本架构是什么？为什么需要RAG？

RAG（Retrieval-Augmented Generation）= 检索 + 生成。旨在解决大模型知识时效性差和私有数据无法利用的问题。

### 基本架构流程
```text
离线阶段:
┌──────────┐    ┌──────────┐    ┌──────────────┐
│ 原始文档  │───>│ 文档切分 │───>│ 向量化+索引  │
└──────────┘    └──────────┘    └──────┬───────┘
                                      │
                                      v
                              ┌──────────────┐
                              │  向量数据库   │
                              └──────┬───────┘

在线阶段:
┌──────────┐    ┌──────────┐    ┌──────────────┐    ┌──────────┐
│ 用户问题  │───>│ 向量化   │───>│ 语义向量检索  │───>│ Prompt构建│
└──────────┘    └──────────┘    └──────┬───────┘    └─────┬────┘
                                       │                  │
                                       v                  v
                              ┌──────────────┐    ┌──────────┐
                              │ Top-K 文档   │───>│  LLM生成  │───> 最终答案
                              └──────────────┘    └──────────┘
```

### 为什么需要RAG（核心痛点）
1.  **知识时效性**：预训练模型有时间截止，无法获取训练后发生的新信息（如最新新闻、股价）。RAG通过外挂数据库实时更新。
2.  **私有数据访问**：模型无法训练企业内部的私有文档（合同、API文档、代码库）。RAG可以将其纳入检索范围。
3.  **降低幻觉**：模型生成受限于检索到的上下文，相比纯生成模式，减少了“一本正经胡说八道”的概率。
4.  **可解释性与溯源**：答案可以附带引用来源（Document ID），用户可点击原文验证，增强信任度。
5.  **成本与效率**：相比于频繁微调模型以更新知识，更新向量数据库的成本极低。

### RAG vs 微调
*   **RAG**：适合知识密集型、动态变化的数据。无需训练，部署快。
*   **微调**：适合调整模型风格、格式或特定领域的推理能力。需要大量算力和数据。

### 实战案例
*   **金融研报生成**：某投行构建 RAG 系统读取每日 500+ 份研报。曾遇到模型将“2023年数据”与“2024年预测”混淆。解决方案：在 Prompt 中强制要求“仅根据检索到的 [2024] 标签文档作答”，并在 Metadata 中过滤时间，时效性提升 40%。
*   **企业知识库“漂移”**：公司政策更新后，旧文档未及时下架。RAG 检索到旧政策导致回答错误。实战中需引入“时间加权排序”或 Rerank 模块优先展示最新版本。

### 代码示例 (Python - 简易 RAG 流程)
```python
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI

# 1. 离线/在线初始化
embeddings = OpenAIEmbeddings()
db = FAISS.load_local("faiss_index", embeddings)
llm = ChatOpenAI(model="gpt-4")

# 2. 检索
docs = db.similarity_search("公司差旅报销政策是什么？", k=3)

# 3. 生成
context = "\n".join([d.page_content for d in docs])
prompt = f"基于以下上下文回答问题：\n{context}\n问题：公司差旅报销政策是什么？"
answer = llm.predict(prompt)
```

### 架构优化对比 (进阶)
| 优化方向 | 基础 RAG | 优化后方案 (如 Advanced RAG) | 优势 |
|---------|---------|--------------------------|------|
| **检索质量** | 单次向量检索 | 混合检索 + Rerank (重排序) | 解决语义模糊，精准度提升 |
| **查询理解** | 直接检索用户问题 | Query Rewriting (查询改写/分解) | 处理复杂问题，指代消解 |
| **上下文窗口** | 直接拼接 Top-K | 长上下文压缩/摘要 | 降低 Token 消耗，减少噪声 |

## 常见考点
1.  **RAG 如何缓解幻觉？**
    通过将检索到的高置信度上下文放入 Prompt，限制模型生成范围，强制模型基于事实回答，而非依赖内部概率记忆。
2.  **RAG 的主要延迟瓶颈在哪里？**
    通常在 LLM 生成的推理阶段，其次是向量检索阶段（如果数据量巨大且未优化）。
3.  **如果检索到的文档是错误的，RAG 会如何表现？**
    模型会产生“误导性幻觉”，即基于错误的事实生成逻辑自洽但内容错误的答案。因此检索质量和 Rerank 至关重要。


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

- 核心定义：检索+生成，解决大模型知识时效性差和无法访问私有数据问题
- 基本流程：离线文档切片向量化 -> 在线查询检索 -> Prompt构建 -> LLM生成
- 核心价值：降低幻觉（基于事实）、可解释性（引用来源）、低成本更新知识
- 对比微调：RAG适合动态知识库，微调适合调整风格和推理模式

## 结构化回答

**30 秒电梯演讲：** RAG 就是检索 + 生成——给大模型外挂一个知识库，让它答题前先查资料再开口。它解决三个核心痛点：模型知识过时、访问不了私有数据、容易一本正经胡说八道。因为答案基于检索到的事实，还能附带引用来源。

**展开框架：**
1. **基本流程** — 离线把文档切片、向量化、存进向量库；在线把用户问题向量化检索 Top-K，拼进 Prompt 让 LLM 生成。
2. **核心价值** — 降低幻觉（基于事实）、可解释（带引用）、低成本更新知识（加文档即可，不用重训）。
3. **对比微调** — RAG 适合动态知识库和时效性场景，微调适合调整风格和推理模式，两者互补。

**收尾：** 我做过金融研报 RAG，遇到模型混淆 2023 实际数据和 2024 预测，靠在 Prompt 里强制按时间标签作答 + Metadata 过滤，时效性提升 40%。您想聊检索质量怎么优化，还是幻觉怎么进一步压？

## 视频脚本

> 预计时长：1 分 30 秒 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：什么是 RAG | "大模型老记错新知识？RAG 给它外挂个知识库，先查再答。" | 开场钩子 |
| 0:15 | RAG 离线+在线流程图 | "离线：文档切片向量化存库；在线：问题向量化检索 Top-K，拼 Prompt 让 LLM 答。" | 基本流程 |
| 0:40 | 四大核心痛点图 | "解决四个问题：知识过时、私有数据、幻觉、不可溯源。" | 核心价值 |
| 1:05 | 金融研报时间过滤案例 | "实战：研报 RAG 混淆年份，Prompt 强制按时间标签答 + Metadata 过滤，提 40%。" | 实战案例 |
| 1:25 | 总结卡 | "一句话：检索加生成，外挂知识降幻觉。下期讲怎么切文档。" | 收尾 |

