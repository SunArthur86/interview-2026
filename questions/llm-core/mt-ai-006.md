---
id: mt-ai-006
difficulty: L4
category: llm-core
categories:
- eng-practice
- llm-core
subcategory: 位置编码
tags:
- 美团
- 面经
- Qwen
- 长度外推
feynman:
  essence: 利用YaRN等插值技术，动态调整RoPE频率以适应更长文本。
  analogy: 像拉伸皮筋，不同部位拉伸力度不同（频率相关），保证拉长后不断裂也不变形。
  first_principle: 如何让基于短文本训练的位置编码，平滑地扩展到长文本而不产生崩塌？
  key_points:
  - 早期：NTK-aware RoPE 插值
  - Qwen2：引入YaRN，分频率插值
  - Qwen2.5：直接增加长文本训练数据
  - 核心：平衡高频局部信息和低频全局信息
follow_up:
- NTK-aware 和 YaRN 的区别？—— NTK 统一缩放所有维度，YaRN 分频段处理
- 长度外推会损失质量吗？—— 会，特别是长序列的精确召回任务（如 needle-in-haystack）
- 为什么不直接训练更长的序列？—— 训练成本随序列长度平方增长（Attention 复杂度）
memory_points:
- 演进口诀：初代非线插、二代上YaRN、2.5暴力练全长
- 因为高频保局部细节不缩放，低频管全局结构做拉伸，所以YaRN成外推首选
- Qwen2靠YaRN+DCA辅切分外推128K，Qwen2.5直接原生喂入真实长文数据
- 实战配置：transformers中rope_scaling参数指定yarn及factor缩放倍数
---

# 【美团面经】Qwen 是怎么做长度外推的？

**Qwen 系列在长度外推上的方案演进：**

**1. 早期 Qwen（7B/14B）：**
- **策略**：基础训练长度 2K/8K，推理时通过 **NTK-aware 插值** 支持 32K。
- **原理**：对 RoPE 的 base 频率进行非线性缩放，使得模型在未见过的长位置上，相对位置关系依然保持合理。

**2. Qwen2（2024）：**
- **策略**：引入 **YaRN (Yet another RoPE extensioN)**，直接支持训练 32K，推理外推至 128K。
- **YaRN 核心机制**：
  - 将 RoPE 的频率维度分为高频（局部细节）、中频、低频（全局结构）。
  - **高频**（高频词、局部句法）：保持高分辨率，不做或微弱插值，保证近距离精度。
  - **低频**（全局语义）：线性缩放，防止位置索引溢出导致的错位。
  - **平滑过渡**：中间频率使用平滑曲线插值，避免突变。
- **Dual Chunk Attention (DCA)**：辅助训练策略，将长序列切分为 Chunk，Chunk 内和 Chunk 间分别计算注意力，缓解长距离注意力衰减。

**3. Qwen2.5（2024末）：**
- **策略**：**暴力美学**。直接在预训练和 SFT 阶段混入大量 32K~128K 的真实长文本数据。
- **原理**：相比于外推算法，“内插”（在训练时就见过）效果最稳。配合 GQA 减少显存，使得全长训练成为可能。

**核心技术细节：YaRN 的数学原理**
```n原始 RoPE 频率: θ_i = base^(-2i/d)
YaRN 缩放后:     θ_i' = θ_i / s(λ_i)

其中 s(λ_i) 是缩放因子，取决于该维度属于高频还是低频：
- λ → 1 (高频): s ≈ 1 (不缩放，保留局部精度)
- λ → 0 (低频): s = scale_factor (线性缩放，适配全长)
```

### 实战案例
在 Qwen2-72B 推理中，直接启用 128K 上下文处理财报分析时，显存经常 OOM。**实战优化**：开启 HuggingFace 的 `sdpa` (Scaled Dot Product Attention) 和 `flash_attention_2`，并使用 `use_cache=True`，能将显存占用降低约 40%，使得单卡 A100 (80G) 可跑通 128K 批次大小为 1 的推理。

### 代码示例
```python
# transformers 中使用 YaRN 配置加载 Qwen2 进行长度外推
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2-7B-Instruct",
    rope_scaling={
        "type": "yarn",  # 指定使用 YaRN 缩放
        "factor": 16.0,   # 缩放因子 (例如从 8K 拉伸到 128K)
        "original_max_position_embeddings": 32768
    },
    torch_dtype="auto",
    device_map="auto"
)
```

### 对比表格
| 策略 | NTK-Aware Scaling | YaRN | 暴力训练 (Full Length Training) |
| :--- | :--- | :--- | :--- |
| **原理** | 修改 base 进行非线性插值 | 分频段插值 (高频保持+低频拉伸) | 训练阶段直接包含长序列数据 |
| **额外训练** | 不需要 | 不需要 (或微调) | 需要 (预训练/SFT 阶段) |
| **短文本性能** | 有一定退化 | 几乎无退化 (保留高频分辨率) | 最优 (原生长度) |
| **资源消耗** | 低 (推理时配置) | 低 | 高 (需更多显存和算力) |
| **适用场景** | 快速验证、资源受限 | 生产环境外推首选 (Qwen2/GPT-4) | 追求极致长文效果 (Qwen2.5) |

## 流程图

```mermaid
flowchart TD
    A[训练长度 8K] --> B[扩展到 32K/128K]
    B --> C{Qwen 长度外推}
    C --> C1[YaRN: NTK 插值]
    C --> C2[动态 NTK 分段]
    C --> C3[ABF 调整基频]
    C1 & C2 & C3 --> D[缩放 RoPE 频率]
    D --> E[适配更长序列]
    E --> F[少量微调恢复性能]
```


## 记忆要点

- 演进口诀：初代非线插、二代上YaRN、2.5暴力练全长
- 因为高频保局部细节不缩放，低频管全局结构做拉伸，所以YaRN成外推首选
- Qwen2靠YaRN+DCA辅切分外推128K，Qwen2.5直接原生喂入真实长文数据
- 实战配置：transformers中rope_scaling参数指定yarn及factor缩放倍数


## 结构化回答

**30 秒电梯演讲：** 利用YaRN等插值技术，动态调整RoPE频率以适应更长文本。——打个比方，像拉伸皮筋，不同部位拉伸力度不同（频率相关），保证拉长后不断裂也不变形。

**展开框架：**
1. **演进口诀** — 初代非线插、二代上YaRN、2.5暴力练全长
2. **因为高频保局部细** — 因为高频保局部细节不缩放，低频管全局结构做拉伸，所以YaRN成外推首选
3. **Qwen2靠Ya** — Qwen2靠YaRN+DCA辅切分外推128K，Qwen2.5直接原生喂入真实长文数据

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「NTK-aware 和 YaRN 的区别？—— NTK 统一缩放所有维度，YaRN 分频段处理」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "【美团面经】Qwen 是怎么做长度外推的，30 秒讲清楚。" | 开场钩子 |
| 0:40 | 概念定义动画 | "一句话：利用YaRN等插值技术，动态调整RoPE频率以适应更长文本。" | 核心定义 |
| 1:20 | 演进口诀图解 | "初代非线插、二代上YaRN、2.5暴力练全长" | 演进口诀 |
| 2:00 | 要点图解 | "因为高频保局部细节不缩放，低频管全局结构做拉伸，所以YaRN成外推首选" | 要点 |
| 2:40 | 要点图解 | "Qwen2靠YaRN+DCA辅切分外推128K，Qwen2.5直接原生喂入真实长文数据" | 要点 |
| 3:20 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
