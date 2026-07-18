---
id: ai-scen-023
difficulty: L2
category: ai-scenario
subcategory: LLM推理与部署
tags:
- 推理缓存
- 语义缓存
- Prefix Cache
- GPTCache
- KV Cache
- 成本优化
feynman:
  essence: 通过复用计算结果或中间状态，减少重复推理以降低延迟和Token消耗。
  analogy: 像考试时的记忆库，完全一样直接抄答案，意思相似稍作修改，开头一样直接接续写。
  first_principle: 如何在保证生成结果一致性的前提下，通过复用历史计算来最大化节省算力？
  key_points:
  - 精确缓存保正确，语义缓存提覆盖，Prefix缓存加速首字
  - 语义缓存需警惕否定词陷阱与阈值设定
  - 分层存储与多级淘汰策略平衡命中与成本
  - LLM推理引擎内部复用KV Cache是终极加速手段
follow_up:
- 语义缓存的相似度阈值如何确定？
- 如何处理缓存失效后的雪崩问题？
- Prefix缓存对不同长度的Prompt效果如何？
memory_points:
- 三级缓存：精确匹配（Redis）→ 语义匹配（向量）→ Prefix匹配（KV Cache）。
- 语义缓存：Embedding检索，相似度>0.95命中，需防否定词误判。
- Prefix缓存：复用公共前缀计算结果，不影响质量，仅加速推理。
- 风险控制：Hash Key包含Temperature参数，模型更新自动失效旧缓存。
- 实战效果：语义缓存命中率达30%，延迟从800ms降至15ms，大幅降本。
---

# 如何设计LLM推理的缓存策略？通过精确缓存、语义缓存和Prefix缓存降低成本和延迟。

【场景分析】
LLM推理缓存可大幅降低成本和延迟。缓存策略需要平衡命中率、正确性、新鲜度。

**【实战案例】**
某电商大促期间，客服机器人80%的问题集中在“物流查询”和“退改政策”。引入语义缓存后，RPM（每分钟请求数）峰值期间，直接命中缓存的响应时间从800ms降至15ms，且节省了约$2000/天的API调用成本。但在初期，因阈值设置过低（0.85），导致用户问“退货地址”时错误返回了“发货地址”的缓存，后引入“否定词检测”逻辑解决。

【缓存层次】
1. 精确缓存：
   - Key：hash(model + prompt + params)
   - 命中率：低（<5%），但100%正确
   - 适用：FAQ类固定问答、系统Prompt
   - 实现：Redis，TTL=24h
2. 语义缓存：
   - Key：prompt的Embedding向量
   - 命中：新Query与缓存Query的余弦相似度 > 阈值（0.95）
   - 命中率：20-40%（取决于场景）
   - 风险：语义相似但意图不同 → 误命中
   - 实现：GPTCache / 自建向量缓存
3. Prefix缓存：
   - Key：Prompt的公共前缀（系统Prompt、Few-shot示例）
   - 命中方式：复用已计算的KV Cache
   - 优势：不影响生成质量，仅加速推理
   - 实现：vLLM Automatic Prefix Caching

【缓存策略设计】
- 写入策略：Write-through（同步写）或 Write-behind（异步写）
- 淘汰策略：LRU + TTL + 主动失效
- 失效条件：模型版本变更、Prompt模板更新、用户反馈差评
- 分层存储：热数据Redis，温数据SSD，冷数据归档

【语义缓存的风险控制】
- 阈值调优：相似度阈值越高越安全但命中率越低
- 上下文验证：缓存的答案中引用的上下文是否仍有效
- 用户确认：命中缓存时标注「相似问题历史回答」
- 否定词检测：「北京天气」vs「北京不是晴天」语义相似但含义相反

【效果评估】
| 缓存类型 | 命中率 | 延迟降低 | 成本降低 |
| --- | --- | --- | --- |
| 精确缓存 | 5% | 99% | 5% |
| 语义缓存 | 30% | 95% | 30% |
| Prefix缓存 | 80%（前缀） | 40% | 无直接成本降低 |

【缓存工作流程】
```text
Request
   │
   ├──> 1. Exact Match Check (Redis Key Lookup)
   │        └── Hit? ──> Return Cached Response
   │
   ├──> 2. Prefix Match Check (KV Cache Block)
   │        └── Hit? ──> Load Shared KV Blocks ──> Continue Generation
   │
   └──> 3. Semantic Match Check (Vector Search)
            └── Score > Threshold?
                 ├── Yes ──> Return (Optional: User Confirmation)
                 └── No  ──> LLM Inference ──> Write to Cache ──> Return
```

**【代码示例：语义缓存检索逻辑】**
```python
async def get_semantic_cache(query: str, threshold=0.95):
    # 1. 计算Query向量
    query_embedding = await embed_model.embed_query(query)
    
    # 2. 向量检索（Redis Vector Search或Milvus）
    results = await vector_store.search(
        vector=query_embedding, 
        top_k=1, 
        score_threshold=threshold
    )
    
    if results:
        cached_item = results[0]
        # 3. 否定词安全检查（防止语义相近但意图相反）
        if not has_negation_overlap(query, cached_item.question):
            return cached_item.answer
    return None
```

## 常见考点
1. **缓存的一致性问题如何处理？**
   - 系统Prompt更新时，需基于版本号（Hash）自动使旧前缀缓存失效；对于知识库问答，知识库内容变更时需触发相关缓存的定向清除。
2. **向量数据库检索速度不够快怎么办？**
   - 使用HNSW索引提升检索速度；或者先进行精确匹配和关键词过滤，减少进入向量检索的流量。
3. **Temperature 参数对缓存的影响？**
   - 不同的Temperature会导致输出完全不同，因此Hash Key必须包含Temperature等参数。通常建议对Temperature=0（确定性输出）的场景启用强缓存。
4. **流式输出与缓存的冲突？**
   - 命中缓存时，若原始结果已完整生成，服务端需模拟流式发送（将缓存结果切片发送），保持客户端接口一致性。

## 核心知识点图

<img src="/interview-2026/images/diagram_ai-scenario_ai-scen-023.svg" alt="如何设计LLM推理的缓存策略？通过精确缓存、语义缓存和Prefix缓存降低成本和延迟。 - 核心知识点图" style="max-width:100%;height:auto;border:1px solid var(--border);border-radius:8px;margin:1em 0;" />

## 记忆要点

- 三级缓存：精确匹配（Redis）→ 语义匹配（向量）→ Prefix匹配（KV Cache）。
- 语义缓存：Embedding检索，相似度>0.95命中，需防否定词误判。
- Prefix缓存：复用公共前缀计算结果，不影响质量，仅加速推理。
- 风险控制：Hash Key包含Temperature参数，模型更新自动失效旧缓存。
- 实战效果：语义缓存命中率达30%，延迟从800ms降至15ms，大幅降本。


## 结构化回答

**30 秒电梯演讲：** 通过复用计算结果或中间状态，减少重复推理以降低延迟和Token消耗。——打个比方，像考试时的记忆库，完全一样直接抄答案，意思相似稍作修改，开头一样直接接续写。

**展开框架：**
1. **三级缓存** — 精确匹配（Redis）→ 语义匹配（向量）→ Prefix匹配（KV Cache）。
2. **语义缓存** — Embedding检索，相似度>0.95命中，需防否定词误判。
3. **Prefix缓存** — 复用公共前缀计算结果，不影响质量，仅加速推理。

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「语义缓存的相似度阈值如何确定」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "设计LLM推理的缓存策略，30 秒讲清楚。" | 开场钩子 |
| 0:30 | 概念定义动画 | "一句话：通过复用计算结果或中间状态，减少重复推理以降低延迟和Token消耗。" | 核心定义 |
| 1:00 | 三级缓存图解 | "精确匹配（Redis）→ 语义匹配（向量）→ Prefix匹配（KV Cache）。" | 三级缓存 |
| 1:30 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
