---
id: mt-ai-007
difficulty: L2
category: llm-core
categories:
- eng-practice
- llm-core
subcategory: 推理优化
tags:
- 美团
- 面经
- 解码策略
- 采样
feynman:
  essence: 从概率分布中选择token的策略，平衡确定性与多样性。
  analogy: 像写作文，是每次只选最顺口的词（Greedy），还是在候选词里随机抽（Sampling），取决于你想要标准答案还是创意。
  first_principle: 如何将模型输出的概率分布转化为高质量的文本序列？
  key_points:
  - Greedy：最稳但死板，适合做题
  - Sampling：引入随机性，适合创作
  - Top-K/Top-P：过滤掉低概率的胡言乱语
  - Temperature：控制随机程度的旋钮
follow_up:
- Top-K 和 Top-P 怎么选？—— Top-P 更自适应，通常优先
- 为什么 Temperature=0 时结果不一定完全一致？—— 浮点精度 + batch padding 影响
- Speculative Decoding 怎么加速？—— 小模型快速生成候选，大模型批量验证
memory_points:
- 两大流派：Greedy/Beam重确定易重复，Top-K/Top-P重多样防尾巴
- 因为T控制整体随机性，所以T越低越确定(代码T<0.3)，T越高越发散(创意T>0.7)
- Top-P核基选：动态截断累积概率(常设0.9)，比Top-K固定截断更自然
- 进阶加速：投机采样用小模型草拟+大模型验证，实现2-3倍无损加速
---

# 【美团面经】了解大模型的解码策略吗？简要说一说

**大模型解码策略总结：**

| 策略 | 原理 | 特点 |
|------|------|------|
| **Greedy** | 每步选概率最高的 token | 确定性、易重复 |
| **Beam Search** | 维护 top-k 候选序列 | 平衡质量与多样性 |
| **Temperature Sampling** | 按温度缩放概率后采样 | T↑多样性↑，T↓确定性↑ |
| **Top-K Sampling** | 只从概率最高的 K 个中采样 | 截断尾部噪声 |
| **Top-P (Nucleus)** | 从累积概率≥P的最小集合中采样 | 动态截断，更自然 |
| **Contrastive Search** | 结合概率 + 惩罚重复 | 减少重复，保持连贯 |

**关键参数：**
- **Temperature (T)**：T=0 等价 Greedy；T=1 标准采样；T>1 更随机
  - 公式：p_i' = softmax(logit_i / T)
- **Top-P**：通常设 0.9~0.95
- **Repetition Penalty**：对已出现 token 降权，减少重复
- **Frequency Penalty**：按出现次数惩罚

**解码流程架构图：**
```text
      Input Prompt
           │
           ▼
┌───────────────────────┐
│   Model Forward Pass  │  ◄── Hidden States
│   (计算 Logits)       │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│   Logits Processing   │
│ 1. Temperature Scale  │
│ 2. Repetition Penalty │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│   Sampling Strategy   │─────► Greedy / Beam / Top-K / Top-P
└───────────┬───────────┘
            │
            ▼
      Selected Token
            │
            ▼ (Append to Input)
      Next Step ...
```

**实用建议：**
- 代码/数学：T=0~0.3（确定性优先）
- 创意写作：T=0.7~1.0（多样性优先）
- 对话：T=0.5~0.7 + Top-P=0.9

**进阶：**
- **Speculative Decoding** — 小模型草拟+大模型验证，加速 2-3×
- **Medusa** — 多头并行预测多个 token

### 实战案例
在电商客服 RAG 场景中，使用 Top-P 采样偶尔会生成“亲、这边建议您...”等不符合公司风格的用语。**实战中**：我们结合 `Repetition Penalty=1.05` 和严格的 `stop_tokens`（如停用词“再见”），并强制输出 JSON 字段，避免了模型无休止的唠叨和格式错误。

### 代码示例
```python
import torch

def top_k_top_p_filtering(logits, top_k=0, top_p=0.0, filter_value=-float('Inf')):
    # Top-K 截断
    if top_k > 0:
        indices_to_remove = logits < torch.topk(logits, top_k)[0][..., -1, None]
        logits[indices_to_remove] = filter_value
    
    # Top-P (Nucleus) 截断
    if top_p > 0.0:
        sorted_logits, sorted_indices = torch.sort(logits, descending=True)
        cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)
        
        # 移除累积概率超过 P 的 token
        sorted_indices_to_remove = cumulative_probs > top_p
        sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
        sorted_indices_to_remove[..., 0] = 0
        
        indices_to_remove = sorted_indices_to_remove.scatter(1, sorted_indices, sorted_indices_to_remove)
        logits[indices_to_remove] = filter_value
    
    return logits
```

### 对比表格
| 策略 | 适用场景 | 缺点 | 对话推荐参数 |
| :--- | :--- | :--- | :--- |
| **Greedy Search** | 代码生成、数学解题 | 极易陷入死循环，语气机械 | T=0 (或 1e-5) |
| **Beam Search** | 翻译、摘要任务 | 生成文本生硬，缺乏随机性 | Beam Size=4 (少用) |
| **Top-K Sampling** | 创意写作 | K 较小时会切断有效低概率词 | K=40~50 |
| **Top-P (Nucleus)** | 通用对话 (推荐) | 概率分布极平时可能截断过多 | P=0.9, T=0.7 |
| **Contrastive Search** | 长文本生成 | 实现稍复杂，需调节 deg_penalty | penalty=0.5~1.0 |


## 记忆要点

- 两大流派：Greedy/Beam重确定易重复，Top-K/Top-P重多样防尾巴
- 因为T控制整体随机性，所以T越低越确定(代码T<0.3)，T越高越发散(创意T>0.7)
- Top-P核基选：动态截断累积概率(常设0.9)，比Top-K固定截断更自然
- 进阶加速：投机采样用小模型草拟+大模型验证，实现2-3倍无损加速


## 结构化回答

**30 秒电梯演讲：** 从概率分布中选择token的策略，平衡确定性与多样性。——打个比方，像写作文，是每次只选最顺口的词（Greedy），还是在候选词里随机抽（Sampling），取决于你想要标准答案还是创意。

**展开框架：**
1. **两大流派** — Greedy/Beam重确定易重复，Top-K/Top-P重多样防尾巴
2. **因为T控制整体随** — 因为T控制整体随机性，所以T越低越确定(代码T<0.3)，T越高越发散(创意T>0.7)
3. **Top-P核基选** — 动态截断累积概率(常设0.9)，比Top-K固定截断更自然

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「Top-K 和 Top-P 怎么选？—— Top-P 更自适应，通常优先」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "【美团面经】了解大模型的解码策略吗，30 秒讲清楚。" | 开场钩子 |
| 0:30 | 概念定义动画 | "一句话：从概率分布中选择token的策略，平衡确定性与多样性。" | 核心定义 |
| 1:00 | 两大流派图解 | "Greedy/Beam重确定易重复，Top-K/Top-P重多样防尾巴" | 两大流派 |
| 1:30 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
