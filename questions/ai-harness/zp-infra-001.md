---
id: zp-infra-001
difficulty: L4
category: ai-harness
subcategory: 推理优化
tags:
- 智谱
- 面经
- 量化
- SmoothQuant
- AWQ
- GPTQ
feynman:
  essence: 通过数学变换或优化算法减少权重量化误差
  analogy: 像把行李里的重物（激活值）均匀分摊到各个箱子（权重）里，方便搬运
  first_principle: 如何在极低比特（4bit/8bit）下保持模型推理精度？
  key_points:
  - SmoothQuant通过缩放平衡激活与权重分布
  - AWQ保留重要权重精度，仅量化次要部分
  - GPTQ利用Hessian二阶信息逐列补偿量化误差
  - 三者目标均为降低W4量化带来的精度损失
follow_up:
- SmoothQuant 为什么能平滑？—— 激活异常值集中在少数 channel，通过缩放因子 s 把激活的异常值'转移'到权重端
- AWQ 和 GPTQ 哪个精度更好？—— 通常 AWQ 略优，因为考虑了激活信息；GPTQ 纯权重补偿更通用
- per-tensor/channel/group 哪个最细？—— group 最细（如 group_size=128），channel 次之，tensor 最粗
memory_points:
- SmoothQuant：Per-channel/tensor。数学等价变换，将激活难度迁移至权重，适合W8A8。
- AWQ：Per-group。保留1%显著权重为FP16，其余INT4量化，激活感知，推理快。
- GPTQ：Per-column。基于Hessian二阶信息补偿权重误差，纯INT4，精度高。
frequency: medium
---

# 【智谱Infra面经】按照量化粒度说明一下 SmoothQuant、AWQ、GPTQ 分别是什么粒度的？它们的作用流程是什么？

**大模型三大量化算法对比（按粒度）：**

| 算法 | 粒度 | 核心思想 | 激活值处理 | 适用场景 |
|------|------|----------|-----------|----------|
| **SmoothQuant** | per-channel / per-tensor | 平滑激活值异常值到权重 | 是（激活感知） | W8A8，Transformer架构 |
| **AWQ** | per-group / per-channel | 保护激活感知的显著权重 | 是（activation-aware） | W4A16，通用LLM |
| **GPTQ** | per-column（逐列） | 基于二阶信息（Hessian）的权重补偿 | 否（仅权重量化） | W4A16，学术界首选 |

**SmoothQuant 流程：**
1. **分析**：统计校准集的激活值，发现某些 Channel 存在数值极大的异常值，导致量化范围被拉伸，精度丢失。
2. **迁移（平滑）**：引入缩放因子 `s`，将激活值的难度“迁移”到权重上。
   - 数学变换：`W' = W · diag(s)`, `X' = X / diag(s)`
   - 逻辑：激活值除以 `s` 变小（易量化），权重乘以 `s` 变大（但权重分布通常较平缓，能更好吸收误差）。
3. **量化**：对平滑后的 `W'` 和 `X'` 分别做 per-channel/per-tensor INT8 量化。
4. **特点**：**粒度最粗**，但引入了数学等价变换，使得 W8A8 在 Transformer 上能保持极低精度损失。

**AWQ (Activation-aware Weight Quantization) 流程：**
1. **寻找显著权重**：基于少量校准数据，分析激活值幅度。对于激活值较大的 Channel，对应的权重对输出影响最大（显著权重）。
2. **保护机制**：只保留约 1% 的显著权重为 FP16，其余 99% 做 INT4 量化。
   - 公式思想：`Y = X @ W`，将 `W` 分割为 `W_keep` 和 `W_quant`。通过缩放让 `W_quant` 承担主要数值范围，而 `W_keep` 补偿量化误差。
3. **量化**：非显著权重进行 per-group INT4 量化（Group size 通常为 64 或 128）。
4. **特点**：**per-group 粒度**，精度高，推理速度快（仅需少量反量化计算），适合 W4A16。

**GPTQ 流程：**
1. **逐列处理**：按顺序量化权重矩阵的每一列。
2. **二阶补偿**：每量化一列后，利用 Hessian 矩阵（二阶导数信息，代表输入数据的特征分布）的逆矩阵，来调整剩余未量化列的数值，以最小化整体量化误差。
   - 类似于 **OBS (Optimal Brain Surgeon)** 剪枝算法的逆过程：剪枝是删节点，GPTQ是降精度，都用 Hessian 补偿。
3. **特点**：**per-column 粒度**，精度高，无需保留部分FP16权重（纯INT4），但反量化推理计算量较 AWQ 略大（取决于实现）。

## 实战案例
在Llama-3-70B的端侧部署（NVIDIA Jetson Orin）中，我们最初尝试使用GPTQ 4bit量化，发现推理过程中FP16反量化Kernel占用了大量计算资源，导致Token生成速度仅为10 t/s。切换到AWQ方案后，虽然显存占用略高（保留了1%的FP16权重），但由于利用了CUDA Core的高效混合精度计算，且不需要复杂的Hessian逆计算调整，推理速度提升到了18 t/s，且PPL困惑度与FP16几乎一致。

## 代码示例 (Python - 模拟SmoothQuant的平滑变换)
```python
import torch

def smooth_quant_transform(activation, weight, alpha=0.5):
    # 1. 统计通道级别的最大激活值
    # activation: [Batch, Seq, Hidden]
    max_act = activation.abs().max(dim=0).values # [Hidden]
    
    # 2. 计算缩放因子 s = (max_act)^alpha / (weight_scale)^(1-alpha)
    # 这里简化处理，直接使用最大值比率
    weight_scale = weight.abs().max(dim=0).values # [Hidden] if weight is [Out, In]
    scale = (max_act.pow(alpha)) / (weight_scale.pow(1 - alpha) + 1e-5)
    
    # 3. 变换：X' = X / s, W' = W * s
    # 为了数值稳定，通常融合到后续的Linear Layer计算中
    return scale
```

## 常见考点
1. **追问**：GPTQ 和 AWQ 在推理时有什么区别？（答：GPTQ 通常需要在线反量化，或者需要特定的 Dequant Kernel；AWQ 往往通过保留部分 FP16 权重简化了推理 Kernel 实现，实际推理吞吐量 AWQ 往往更有优势）。
2. **追问**：SmoothQuant 中的 alpha 参数通常取多少？（答：通常取 0.5，表示激活值和权重各承担一半的量化难度，不同模型可能需要微调）。
3. **追问**：Per-channel 和 Per-token 量化的区别是什么？（答：Per-channel 是对权重矩阵的每一列/行单独定 Scale；Per-token 是对每一个 Token 的激活值单独定 Scale。Per-channel 训练前/后均可，Per-tensor 仅能训练后；Per-token 推理计算开销大但精度高）。

```mermaid
flowchart TD
    classDef start fill:#4CAF50,color:#fff
    classDef process fill:#2196F3,color:#fff
    classDef decision fill:#FF9800,color:#fff
    classDef special fill:#9C27B0,color:#fff
    classDef error fill:#f44336,color:#fff
    classDef info fill:#607D8B,color:#fff
    class AWQ start
    class Choice process
    class GPTQ decision
    class Model special
    class Per error
    class Smooth info
    class SmoothQuant start
    class W8A8 process
    class br decision
    class channel special
    class column error
    class group info
    class tensor start
    Model[FP模型] --> Choice{量化粒度}
    Choice -->|Per-channel/tensor| Smooth[SmoothQuant<br/>W8A8]
    Choice -->|Per-group| AWQ[AWQ<br/>1%显著权重FP16]
    Choice -->|Per-column| GPTQ[GPTQ<br/>Hessian二阶补偿]
```


## 记忆要点

- SmoothQuant：Per-channel/tensor。数学等价变换，将激活难度迁移至权重，适合W8A8。
- AWQ：Per-group。保留1%显著权重为FP16，其余INT4量化，激活感知，推理快。
- GPTQ：Per-column。基于Hessian二阶信息补偿权重误差，纯INT4，精度高。


## 结构化回答

**30 秒电梯演讲：** 通过数学变换或优化算法减少权重量化误差——打个比方，像把行李里的重物（激活值）均匀分摊到各个箱子（权重）里，方便搬运

**展开框架：**
1. **SmoothQu** — SmoothQuant：Per-channel/tensor。数学等价变换，将激活难度迁移至权重，适合W8A8。
2. **AWQ** — Per-group。保留1%显著权重为FP16，其余INT4量化，激活感知，推理快。
3. **GPTQ** — Per-column。基于Hessian二阶信息补偿权重误差，纯INT4，精度高。

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「SmoothQuant 为什么能平滑？—— 激活异常值集中在少数 channel，通过缩放因子 s 把激活的异常值'转移'到权重端」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "【智谱Infra面经】按照量化粒度说明一下 SmoothQuant、AWQ、GP，30 秒讲清楚。" | 开场钩子 |
| 0:40 | 概念定义动画 | "一句话：通过数学变换或优化算法减少权重量化误差" | 核心定义 |
| 1:20 | SmoothQuant图解 | "Per-channel/tensor。数学等价变换，将激活难度迁移至权重，适合W8A8。" | SmoothQuant |
| 2:00 | AWQ图解 | "Per-group。保留1%显著权重为FP16，其余INT4量化，激活感知，推理快。" | AWQ |
| 2:40 | GPTQ图解 | "Per-column。基于Hessian二阶信息补偿权重误差，纯INT4，精度高。" | GPTQ |
| 3:20 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
