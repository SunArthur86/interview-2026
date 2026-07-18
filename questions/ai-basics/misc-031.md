---
id: misc-031
difficulty: L2
category: ai-basics
subcategory: RAG与向量检索
tags:
- IO
- IOC
- 索引
- Elasticsearch
feynman:
  essence: 利用LLM作为裁判，自动量化检索和生成的质量。
  analogy: 像老师批改作业，不只看答案对不对，还要检查是不是抄的书（来源）以及有没有跑题。
  first_principle: 在没有人工标注标准答案的情况下，如何科学、自动化地衡量RAG系统的好坏？
  key_points:
  - 检索看精准率和召回率
  - 生成看忠实度和相关性
  - Ragas利用LLM实现自动化评估
follow_up:
- 如何减少RAG的幻觉?
- Faithfulness如何自动计算?
memory_points:
- Ragas核心指标：Context Precision(查准)、Context Recall(查全)、Faithfulness(忠实度)、Answer Relevancy(相关)。
- Faithfulness：答案陈述是否被Context支持，防幻觉。
- Context Recall：标准答案信息是否在Context中找到，防漏检。
- 评估流程：RAG输出 -> LLM-as-a-Judge -> 打分。无需人工标注但需注意评估模型偏见。
---

# 如何评估RAG系统的质量?Ragas框架的核心指标有哪些

- **RAG评估维度:**

- **检索质量(Retrieval):**
- **Context Precision** - 检索到的文档中有多少是相关的
- **Context Recall** - 所有相关文档中有多少被检索到

- **生成质量(Generation):**
- **Faithfulness** - 答案是否忠于检索到的文档(无幻觉)
- **Answer Relevancy** - 答案是否回应了用户问题

- **Ragas框架:**
- 开源RAG评估工具
- 无需人工标注,用LLM自动评估
- 支持 grounding(忠实度) / relevance(相关性) / recall(召回)

- **评估流程架构:**

```text
Question + Ground Truth (Optional)
      │
      ▼
┌──────────────────┐
│   RAG System     │
└────┬────────┬─────┘
     │        │
     ▼        ▼
Context   Answer
     │        │
     ▼        ▼
┌─────────────────────────┐
│   LLM-as-a-Judge        │
│ (Ragas Evaluation)      │
└────────┬────────────────┘
         │
         ▼
   Metrics Scores
```

- **其他评估工具:** TruLens、LlamaIndex Evaluation、LangSmith

- **实战案例:** 在某客服RAG上线前，使用Ragas进行批量评估。发现Faithfulness分数仅为0.6，经分析发现模型常利用预训练知识回答而非基于检索内容。通过调整Prompt增加“请仅根据上下文回答”的强约束后，Faithfulness提升至0.92。

- **代码示例:**
```python
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision
from datasets import Dataset

# 准备评估数据
data_samples = {
    'question': ['用户如何重置密码？'],
    'answer': ['用户可以在设置页面点击重置...'],
    'contexts' [['设置页面的重置指引...']],
    'ground_truth': ['在设置页面点击忘记密码...'] # 可选
}
dataset = Dataset.from_dict(data_samples)

# 运行评估
result = evaluate(
    dataset=dataset,
    metrics=[context_precision, faithfulness, answer_relevancy]
)

print(result.to_pandas())
```

- **对比表格:**

| 指标 | 评估维度 | 理想分数 | 计算原理 (Ragas) | 关注点 |
| :--- | :--- | :--- | :--- | :--- |
| **Context Precision** | 检索 | 高 (1.0) | 检索结果中相关文档的排序权重 | 是否把垃圾信息排在前面？ |
| **Context Recall** | 检索 | 高 (1.0) | 标准答案中的句子能否在Context中找到 | 是否遗漏了关键信息？ |
| **Faithfulness** | 生成 | 高 (1.0) | 答案中的陈述是否被Context支持 | 是否在“胡编乱造”？(幻觉) |
| **Answer Relevancy** | 生成 | 高 (1.0) | 答案反推的问题与原问题的Embedding相似度 | 是否“答非所问”？ |

## 常见考点
1. **Context Recall 和 Context Precision 的计算逻辑是什么？**
   - **Precision** = 检索到的文档中，被标注为相关的比例（不查错）。
   - **Recall** = 标注为相关的文档中，被成功检索到的比例（不漏查）。

2. **Faithfulness 和 Answer Relevancy 评分的原理？**
   - **Faithfulness**：将答案拆解为多个原子陈述，逐一判断是否能在Context中找到依据。
   - **Answer Relevancy**：基于生成的答案反生成一个问题，计算反生成问题与原问题的相似度。

- **## 易错点**
1. **忽视Ground Truth的必要性**：虽然Ragas支持无Ground Truth评估（如Context Recall），但在严格的生产验收中，没有Ground Truth很难准确衡量“漏检”情况。
2. **评估模型的偏见**：用LLM（如GPT-4）作为评估者时，评估结果可能会受到评估模型自身偏好或知识的影响（例如，如果答案超出了评估模型的认知范围，即使符合事实，Faithfulness也可能被误判为低）。

- **## 面试追问**
1. 在没有Ground Truth的情况下，如何计算Context Recall？（Ragas使用一种基于“上下文充分性”的启发式方法，让LLM判断Context是否足够回答问题，但这不是标准的Recall；或者利用LLM生成参考答案来模拟GT）
2. 如果RAG系统的上下文窗口有限，导致Context被截断，会主要影响哪个指标？（主要影响Context Recall，因为相关文档可能被截断；同时也可能影响Faithfulness，因为依据缺失导致模型被迫幻觉）
3. 除了Ragas，如何进行端到端的用户满意度评估？（引入人工反馈RLHF，或根据用户点击率、点赞率等隐性指标构建Human Preference Metrics）


## 记忆要点

- Ragas核心指标：Context Precision(查准)、Context Recall(查全)、Faithfulness(忠实度)、Answer Relevancy(相关)。
- Faithfulness：答案陈述是否被Context支持，防幻觉。
- Context Recall：标准答案信息是否在Context中找到，防漏检。
- 评估流程：RAG输出 -> LLM-as-a-Judge -> 打分。无需人工标注但需注意评估模型偏见。

## 结构化回答

**30 秒电梯演讲：** Ragas 用 LLM 当裁判，自动量化 RAG 的检索和生成质量。四个核心指标：Context Precision 查准、Context Recall 查全、Faithfulness 忠实度（防幻觉）、Answer Relevancy 相关性。流程是 RAG 输出交给 LLM-as-a-Judge 打分，无需人工标注，但要注意评估模型自身的偏见。

**展开框架：**
1. **检索侧指标** — Context Precision 衡量召回的上下文里有多少真正相关（查准）；Context Recall 衡量标准答案所需信息是否都在召回的上下文里（查全，防漏检）。
2. **生成侧指标** — Faithfulness 检查答案的每条陈述是否被上下文支持，防止幻觉；Answer Relevancy 衡量答案是否切题、没有跑偏。
3. **评估流程与注意点** — RAG 输出 → LLM-as-a-Judge → 自动打分，无需人工标注标准答案；但要注意评估模型自身有偏见，关键场景仍需抽检校准。

**收尾：** 一句话，Ragas 让 RAG 评估从"拍脑袋"变成"可量化"。您想深入聊聊怎么减少 RAG 幻觉，还是 Faithfulness 具体怎么自动计算？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题《Ragas 评估》+ 老师批改作业漫画 | Ragas 像老师批改作业，不只看答案对不对，还要检查是不是抄的书、有没有跑题，用 LLM 当裁判自动打分。 | 类比开场 |
| 0:25 | 检索侧两指标：Precision / Recall | 检索侧看两个指标：Context Precision 查准，看召回里有多少相关；Context Recall 查全，看标准答案信息是不是都在上下文里。 | 检索指标 |
| 0:55 | 生成侧两指标：Faithfulness / Relevancy | 生成侧看两个：Faithfulness 看答案陈述是否被上下文支持，防幻觉；Answer Relevancy 看答案是否切题。 | 生成指标 |
| 1:25 | 评估流程图：RAG 输出 → LLM-as-a-Judge → 打分 | 流程是 RAG 输出交给 LLM-as-a-Judge 自动打分，不需要人工标注标准答案。 | 评估流程 |
| 1:50 | 注意点提示：评估模型偏见 | 注意评估模型自身也有偏见，关键场景还是要抽样人工校准一下。 | 注意事项 |

