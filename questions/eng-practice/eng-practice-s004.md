---
id: eng-practice-s004
difficulty: L2
category: eng-practice
subcategory: 工程化实战
images:
- svg_quantization.svg
feynman:
  essence: 通过模型路由、缓存和上下文压缩等手段降低AI运行开销。
  analogy: 像省油驾驶：市区用小排量车（小模型），走熟路不查地图（缓存），少带不必要的行李（精简Prompt）。
  first_principle: 如何在保证模型效果的前提下，最大化降低推理与交互的计算资源成本？
  key_points:
  - 根据任务难度路由选择不同大小的模型
  - 利用语义缓存避免重复计算
  - 压缩历史上下文减少Token输入
  - 高频场景考虑自建或量化部署
memory_points:
- 模型路由：小模型处理简单任务，大模型处理复杂任务，先判后分。
- Prompt优化：精简System Prompt，历史对话做摘要或滑动窗口截断。
- 缓存策略：语义缓存防重复计算，Prompt Caching缓存长上下文前缀。
- RAG优化：提高检索精度减少无关Token，动态截断保留最相关片段。
- 自建部署：Token量极大时，自建vLLM加量化比API更划算。
---

# LLM应用的token成本如何优化？

Token成本是LLM应用的主要运营成本，优化需从模型、Prompt、架构三个层面入手。

### 1. 模型选择与路由
- **小模型处理简单任务**：如 GPT-3.5/Claude Haiku/GLM-4-Flash 用于意图识别、简单摘要
- **大模型处理复杂任务**：如 GPT-4/Claude Opus 用于复杂推理、代码生成
- **模型路由策略**：
  - 先用小模型判断问题难度/类别，再分发到对应模型
  - 设置兜底机制：小模型失败时升级到大模型

### 2. Prompt 优化
- **精简 System Prompt**：移除冗余的角色描述，保留核心指令
- **历史对话压缩**：
  - 滑动窗口：仅保留最近 N 轮对话
  - 摘要机制：对旧对话进行摘要，保留摘要而非原文
- **Token 省略技巧**：用 '...' 或占位符替换重复出现的常量文本，在发送前替换回来（需注意 API 计费点）

### 3. 缓存策略
- **语义缓存**：使用 Redis + Embedding，对相似问题直接返回历史答案
- **Prompt Caching（API层）**：利用 OpenAI/Anthropic 等厂商的 Prefix Cache 功能，缓存重复的 System Prompt（如长篇文档）

### 4. 批量处理
- **Batch API**：OpenAI Batch API 提供 50% 折扣，适合离线任务（如夜间批量处理数据），但延迟较高（24h内）

### 5. 上下文管理
- **RAG 优化**：提高检索精度，减少检索回来的无关文档 Token
- **动态截断**：根据 `max_tokens` 限制，动态裁剪检索结果，保留最相关的片段（如 Rerank 后取 Top K）

### 6. 自建部署
- **成本临界点**：当高频调用 Token 量极大时，API 费用可能超过 GPU 租赁+运维成本
- **推理优化**：使用 vLLM + 量化 (AWQ/GPTQ) + 显存优化 (PagedAttention)

### 💡 实战案例
在构建企业知识库助手时，我们发现每次请求都会将长达 50k 的公司规章制度作为 System Prompt 上下文发送，导致每月成本激增。**实战优化**：我们启用了 Prompt Caching 并结合了动态 RAG 检索，仅在必要时将具体规则切片注入，使得单次请求成本降低了 85%。

### 💻 代码示例 (Python - 语义缓存实现)
```python
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

def semantic_cache_check(query, cache_dict, embed_model, threshold=0.95):
    query_vec = embed_model.embed(query)
    for cached_q, cached_vec in cache_dict.items():
        score = cosine_similarity([query_vec], [cached_vec])[0][0]
        if score >= threshold:
            return cache_dict[cached_q]["answer"] # 命中缓存
    return None
```

### 📊 成本优化策略对比
| 策略维度 | 手段 | 成本降低幅度 | 延迟影响 | 适用场景 |
| :--- | :--- | :--- | :--- | :--- |
| **模型层** | 模型路由/降级 | 30%-90% | 降低 | 逻辑分层明确的业务 |
| **传输层** | Prompt Caching | 50%-90% (重复部分) | 显著降低 | 长上下文/多轮对话 |
| **计算层** | 语义缓存 | ~100% (命中时) | 极低 | 高频重复问题 |
| **输入层** | RAG 精简/截断 | 20%-40% | 略降 | 知识库检索场景 |

## 常见考点
1. **模型路由的具体实现逻辑？**：讨论基于规则的路由和基于 LLM 的路由的优劣。
2. **Semantic Cache 的相似度阈值如何设定？**：阈值过高导致缓存命中率低，过低可能导致答非所问，需结合业务场景调优。
3. **Prompt Caching 的生效条件？**：通常要求前缀完全一致，因此设计中需将静态 System Prompt 放在最前面，动态变量放在最后面。

## 记忆要点

- 模型路由：小模型处理简单任务，大模型处理复杂任务，先判后分。
- Prompt优化：精简System Prompt，历史对话做摘要或滑动窗口截断。
- 缓存策略：语义缓存防重复计算，Prompt Caching缓存长上下文前缀。
- RAG优化：提高检索精度减少无关Token，动态截断保留最相关片段。
- 自建部署：Token量极大时，自建vLLM加量化比API更划算。


## 结构化回答

**30 秒电梯演讲：** 通过模型路由、缓存和上下文压缩等手段降低AI运行开销。——打个比方，像省油驾驶：市区用小排量车（小模型），走熟路不查地图（缓存），少带不必要的行李（精简Prompt）。

**展开框架：**
1. **模型路由** — 小模型处理简单任务，大模型处理复杂任务，先判后分。
2. **Prompt优化** — 精简System Prompt，历史对话做摘要或滑动窗口截断。
3. **缓存策略** — 语义缓存防重复计算，Prompt Caching缓存长上下文前缀。

**收尾：** 以上三点都能配合实战聊。您想深入聊哪一块？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "LLM应用的token成本如何优化，30 秒讲清楚。" | 开场钩子 |
| 0:30 | 概念定义动画 | "一句话：通过模型路由、缓存和上下文压缩等手段降低AI运行开销。" | 核心定义 |
| 1:00 | 模型路由图解 | "小模型处理简单任务，大模型处理复杂任务，先判后分。" | 模型路由 |
| 1:30 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
