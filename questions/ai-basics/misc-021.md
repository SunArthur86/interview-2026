---
id: misc-021
difficulty: L2
category: ai-basics
subcategory: 推理优化
images:
- svg_beam_search.svg
feynman:
  essence: 调节随机性与确定性的平衡，控制生成内容的多样性与质量。
  analogy: 调温水龙头，温度低就是固定的冷水，温度高就是随机混搭的热水。
  first_principle: 如何在模型生成的确定性与创造性之间找到最佳平衡点？
  key_points:
  - Temperature控制输出随机平滑度
  - Top-k限制候选词数量
  - Top-p限制累积概率质量
  - 通常组合使用Temp+Top-p
follow_up:
- 为什么Temperature=0不等于确定性输出?
- repetition_penalty如何影响生成质量?
memory_points:
- Temperature：控制随机性，低T确定（代码），高T创意（写作）
- Top-k：截断低概率噪声，固定候选集大小（如k=40）
- Top-p：动态截断长尾，保证累积概率质量（如p=0.9）
- 组合建议：T+Top-p最常用，代码用T=0.1，创意用T=0.7
---

# Temperature、Top-p、Top-k采样策略各自的作用?如何组合使用

- **采样策略:**

| 策略 | 作用 | 推荐值 | 适用场景 |
|------|------|--------|---------|
| Temperature | 控制随机性,T越低越确定 | 代码0.1/创意0.7 | 逻辑任务 vs 创作任务 |
| Top-k | 只从概率最高的k个token中采样 | k=40 | 过滤极低概率噪声 |
| Top-p (Nucleus) | 从累积概率超过p的最小token集中采样 | p=0.9 | 动态截断长尾 |

- **原理深度解析:**
  - **Temperature (温度)**: 在 Softmax 之前对 Logits 进行缩放。公式：$Softmax(\frac{logits}{T})$。
    - $T \to 0$: 概率分布趋于尖锐（One-hot），接近贪婪搜索，确定性高。
    - $T > 1$: 概率分布趋于平坦，随机性增加，容易产生创造性但也容易产生幻觉。
  - **Top-k**: 将概率低于第 $k$ 大 token 的所有 token 概率强制置 0，然后重新归一化。限制了候选集的大小，防止低概率的"噪声"词被选中。
  - **Top-p**: 从概率高到低累加，一旦累加和超过 $p$，则截断，剩余 token 概率置 0 并重归一化。它保证了候选集的概率质量，动态调整候选数量（有时是 1 个，有时是 100 个）。

- **采样流程图:**

```
Raw Logits (Model Output)
      │
      ▼
[ Divide by Temperature ] ──> 调整分布平滑度
      │
      ▼
[ Softmax ] ──> 得到概率分布 P
      │
      ▼
[ Filter: Top-k & Top-p ] ──> 剔除低概率 Token
  (例如: 只保留累积概率 > 0.9 的最小集合)
      │
      ▼
[ Re-normalize ] ──> 重新归一化概率和为 1
      │
      ▼
[ Sample ] ──> 根据最终概率采样 Token
```

- **组合建议:** 
  - **Temperature + Top-p**: 工业界最常用组合。Temperature 负责整体风格，Top-p 负责截断长尾噪声。
  - **代码/数学**: T=0.1 (甚至 0), p=0.95 (截断轻微误差)。逻辑任务希望结果确定。
  - **创意写作**: T=0.7 (引入随机性), p=0.9 (允许一定的多样性)
  - **注意**: Top-k 和 Top-p 通常同时开启，起到"双重保险"作用。例如设置 Top-k=40, Top-p=0.9，意味着取两者较小的集合。

- **实战案例:**
在构建代码生成助手时，初始设置 Temperature=0.7 导致生成的代码片段语法错误率高且包含幻觉API。将 Temperature 调整至 0.1 并开启 Top-p=0.95 后，编译通过率从65%提升至92%，有效减少了非确定性输出带来的风险。

- **代码示例:**
```python
import torch
import torch.nn.functional as F

def sample_with_strategy(logits, temperature=0.7, top_k=40, top_p=0.9):
    # 1. Temperature Scaling
    logits = logits / temperature
    
    # 2. Softmax
    probs = F.softmax(logits, dim=-1)
    
    # 3. Top-k Filtering
    values, indices = torch.topk(probs, top_k)
    # 创建全零mask，只保留top_k位置
    probs_top_k = torch.zeros_like(probs)
    probs_top_k.scatter_(1, indices, values)
    
    # 4. Top-p (Nucleus) Filtering
    sorted_probs, sorted_indices = torch.sort(probs_top_k, descending=True)
    cumulative_probs = torch.cumsum(sorted_probs, dim=-1)
    
    # 移除超过top_p的token
    sorted_indices_to_remove = cumulative_probs > top_p
    # 保留第一个超过阈值的token（保证至少有一个token）
    sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
    sorted_indices_to_remove[..., 0] = 0
    
    # 应用mask
    indices_to_remove = sorted_indices_to_remove.scatter(1, sorted_indices, sorted_indices_to_remove)
    probs_top_k[indices_to_remove] = 0.0
    
    # 5. Re-normalize
    final_probs = probs_top_k / probs_top_k.sum(dim=-1, keepdim=True)
    
    # 6. Sample
    next_token = torch.multinomial(final_probs, num_samples=1)
    return next_token
```

- **## 边界情况**
  1. **全零分布**: 当Top-p截断后没有任何Token（极罕见，如Temperature极高且分布极平），应回退到均匀分布或贪婪搜索，防止程序崩溃。
  2. **重复生成**: 在Top-k较小（如<10）且Temperature极低时，模型极易陷入死循环重复同一个短语，需添加Repetition Penalty进行缓解。

- **## 易错点**
  1. **Temperature为零的处理**: 理论上T=0时Softmax会出现除以零或无穷大。实际工程中（如vLLM/Transformers）通常使用Argmax替代，或者增加极小epsilon（1e-5）而非直接设为0。
  2. **Top-k与Top-p的叠加顺序**: 必须先应用Top-k限定范围，再在限定范围内应用Top-p。若顺序颠倒，Top-p可能选中大量低概率噪声，导致Top-k失效。

- **## 面试追问**
  1. 为什么在代码生成或数学推理任务中，单纯的Greedy Search（Temperature=0）往往不如Temperature=0.1效果更好？
  2. Min-P采样是近年来提出的新策略，它与Top-p有何本质区别，为何在处理某些模型的“白板”问题时效果更好？
  3. 在Speculative Decoding（投机采样）场景下，Draft Model和Target Model的采样策略参数（如Temperature）是否必须保持一致，为什么？

## 流程图

```mermaid
flowchart TD
    A[复杂推理问题] --> B{是否提供范例?}

    B -- 否 --> C[Zero-shot CoT]
    C --> D[Prompt追加 Let's think step by step]

    B -- 是 --> E[Few-shot CoT]
    E --> F[提供 问题 -> 推理步骤 -> 答案 范例]

    D --> G[激活大模型预训练推理模式]
    F --> G

    G --> H[强制模型分步输出中间过程]
    H --> I[利用更多Token扩展计算量]
    I --> J[减少跳步错误 输出最终答案]
```


## 记忆要点

- Temperature：控制随机性，低T确定（代码），高T创意（写作）
- Top-k：截断低概率噪声，固定候选集大小（如k=40）
- Top-p：动态截断长尾，保证累积概率质量（如p=0.9）
- 组合建议：T+Top-p最常用，代码用T=0.1，创意用T=0.7

## 结构化回答

**30 秒电梯演讲：** 采样三件套控制生成的随机性。Temperature 像调温水龙头，低 T 出固定冷水，高 T 出随机热水；Top-k 固定候选集大小（比如 k=40）；Top-p 动态截断长尾，保证累积概率质量（比如 p=0.9）。实战最常用的是 T+Top-p 组合：代码用 T=0.1，创意写作用 T=0.7。

**展开框架：**
1. **Temperature** — 控制概率分布的平滑度，低 T 让大概率词更突出、输出确定（适合代码、事实问答），高 T 让分布更平坦、输出有创意（适合写作）。
2. **Top-k 与 Top-p** — Top-k 固定保留 k 个候选词（如 k=40），简单粗暴截断噪声；Top-p（Nucleus）动态保留累积概率达到 p 的候选集（如 p=0.9），自适应长尾。
3. **组合建议** — T + Top-p 是最常用组合，兼顾随机性控制与长尾截断；代码任务用 T=0.1、创意任务用 T=0.7。

**收尾：** 一句话，采样参数是确定性与创造性的水龙头。您想深入聊聊为什么 Temperature=0 不等于完全确定性输出，还是 repetition_penalty 怎么影响生成质量？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题《采样三件套》+ 水龙头调温漫画 | 采样参数像调温水龙头，温度低就是固定的冷水，温度高就是随机混搭的热水。 | 类比开场 |
| 0:25 | Temperature 曲线：低 T 尖锐 vs 高 T 平坦 | Temperature 控制概率分布的平滑度。低 T 输出确定，适合代码；高 T 输出有创意，适合写作。 | Temperature |
| 0:55 | Top-k 示意：固定 k=40 个候选 | Top-k 是固定候选集大小，比如 k 等于 40，简单粗暴截掉低概率噪声。 | Top-k |
| 1:20 | Top-p 示意：动态累积概率到 p=0.9 | Top-p 是动态截断长尾，保留累积概率达到 0.9 的候选集，自适应不同分布形状。 | Top-p |
| 1:50 | 组合表：代码 T=0.1 / 创意 T=0.7 | 实战最常用 T 加 Top-p 组合，代码用 T=0.1，创意写作用 T=0.7。 | 组合建议 |

