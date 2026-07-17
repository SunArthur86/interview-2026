---
id: xhs-infra-005
difficulty: L4
category: ai-harness
subcategory: 推理与部署
tags:
- 量化
- GPTQ
- AWQ
- FP8
- INT4
- 小红书
feynman:
  essence: 将模型参数从高精度压缩到低精度，减少显存和计算开销。
  analogy: 把高清照片压缩成标清，虽然细节少一点，但省空间且传得快。
  first_principle: 如何在保持模型精度的前提下，极小化参数的存储位宽？
  key_points:
  - GPTQ基于Hessian二阶信息进行权重量化
  - AWQ基于激活值保留1%重要权重不被量化
  - SmoothQuant把激活值的难量化特征迁移到权重上
  - FP8依赖特定硬件（如H100）支持，精度损失最小
follow_up:
- INT4量化对生成质量影响有多大？
- AWQ如何确定哪些权重是「重要」的？
- QAT和PTQ在实际中如何选择？
memory_points:
- GPTQ：基于二阶信息的 PTQ，INT4 精度好，通用性强，但推理有解码开销。
- AWQ：激活感知量化，保留 1% 关键通道为 FP16，推理速度优于 GPTQ。
- SmoothQuant：将激活难度迁移至权重，解决异常值问题，适合 INT8。
- FP8：H100 原生支持，无需软件模拟，量化误差最小，依赖硬件。
---

# 模型量化方法对比：GPTQ vs AWQ vs FP8 vs SmoothQuant，各有什么优缺点？

## 主流量化方案对比

| 方法 | 类型 | 精度 | 加速 | 适用场景 | 校准数据 |
|------|------|------|------|----------|----------|
| **GPTQ** | 后训练(PTQ) | INT4/8 | 2-3x | 通用，精度损失小 | 需少量（~128样本） |
| **AWQ** | 后训练(PTQ) | INT4/8 | 2-3x | 激活感知，更稳健 | 需少量（~128样本） |
| **SmoothQuant** | 后训练(PTQ) | INT8 | 1.5-2x | 激活值异常值处理 | 需少量（~256样本） |
| **FP8** | 后训练/混合 | FP8(E4M3) | 1.5-2x | H100原生支持 | 无需校准或仅做Scaling计算 |
| **QAT** | 量化感知训练 | 任意 | 2-3x | 精度最高但需训练 | 需全量微调 |

## 核心区别与原理

### 1. GPTQ (Approximate Second-Order Quantization)
- **原理**：基于 Hessian 二阶信息的近似，通过"懒更新"在每一层权重更新中只量化一部分权重，反向更新剩余权重以保持误差最小。
- **优点**：对通用大模型（如 LLaMA）效果稳定，INT4 精度损失小。
- **缺点**：推理时需要解码操作， slight decode overhead；极低比特（INT3）下性能下降快。

### 2. AWQ (Activation-aware Weight Quantization)
- **原理**：基于观察：只有约 1% 的权重对输出贡献巨大。保留部分通道（如 0.5%-1%）为 FP16，其余量化为 INT4。
  - 公式简述：$X \cdot (W_{scale} + W_{clip}) \approx X \cdot W_{scale}$，通过缩放减少误差。
- **优点**：无需反量化，推理速度比 GPTQ 快；能有效处理 LLM 中的异常激活值。
- **缺点**：需要保留一小部分高精度权重，显存节省略少于纯 INT4。

### 3. SmoothQuant
- **原理**：通过数学等价变换，将激活值的难度"迁移"到权重上。
  - 公式：$Y = (X/s) \cdot (W \cdot s) = X' \cdot W'$
  - 引入平滑因子 $\alpha$（通常 0.5）：$s = max(|X|)^\alpha / max(|W|)^{1-\alpha}$
- **优点**：解决 Transformer 中激活值动态范围大（出现异常大值）导致难以量化的问题，仅需 INT8 即可保持较好精度。
- **缺点**：通常仅限 INT8，难以压榨到 INT4 的显存收益。

### 4. FP8 (Floating Point 8)
- **格式**：
  - **E4M3** (1 sign, 4 exponent, 3 mantissa)：用于权重/激活输入，范围小但精度高，适合 Transformer 前向。
  - **E5M2** (1 sign, 5 exponent, 2 mantissa)：用于梯度更新，范围大但精度低（类似 BF16 范围）。
- **优点**：H100/H200 原生 Tensor Core 支持（Transformer Engine），无需软件模拟；量化误差最小。
- **缺点**：硬件依赖性强，老显卡需模拟极慢；Scaling Factor 计算较复杂（Per-tensor vs Per-channel）。

```text
量化误差分布示意图

GPTQ: 均匀分布误差 [=====|=====]
AWQ: 保留关键通道 [#####|.....] (跳过重要权重)
SmoothQuant: 激活压缩 [==|========] -> 权重膨胀 [======|==]
FP8: 误差极小且非线性 [#######|]
```

## 小红书实践
- Diffusion/VLM模型量化需注意生成质量（UNet 量化常导致细节丢失）。
- 推荐场景：INT8 通用性最佳，复杂Prompt下 AWQ 优于 GPTQ。
- AIGC 生成：FP8 是未来趋势（特别是 H100 集群），不仅省显存还能提升 Throughput。

### 1. 实战案例
- **场景**：在某70B模型部署中，INT4 GPTQ在长文本生成中出现逻辑混乱（PPL突然升高），而AWQ通过保留关键线性层的1%通道，解决了该问题且推理速度提升20%。
- **踩坑**：SmoothQuant迁移到新模型时，若平滑因子`alpha`未根据层数调整（如深层设为0.7），会导致量化溢出。

### 2. 代码示例 (AWQ 核心激活缩放)
```python
# AWQ: 基于激活幅度 scaling 权重
def scale_weights(layer, activation_scale):
    # 获取每层的权重 (out_features, in_features)
    weight = layer.weight.data
    
    # 计算每个输出通道的重要性（基于激活统计）
    # 通常取 activation_scale 的 X% 分位数作为 clip 阈值
    clip_threshold = torch.quantile(activation_scale, 0.99)
    scale = activation_scale.clamp(max=clip_threshold)
    
    # 将 scale 除入权重 (模拟 X * (W/s) * s 的等价变换)
    # 实际工程中通常只 scale 权重，保留 scale 为常数用于反量化
    layer.weight.data = weight / scale.unsqueeze(1)
    return scale
```

### 3. 对比表格
| 维度 | GPTQ | AWQ | SmoothQuant | FP8 |
| :--- | :--- | :--- | :--- | :--- |
| **核心思想** | 权重误差最小化 | 激活感知/保留关键权重 | 激活-权重难度迁移 | 硬件原生低精度 |
| **硬件需求** | 通用 (需支持INT4 Gemm) | 通用 (需支持INT4 Gemm) | 通用 (INT8 Tensor Core) | H100+ (Hopper架构) |
| **校准集** | 需校准 (~128 seq) | 需校准 (~128 seq) | 需校准 (~256 seq) | 无需/仅计算Scale |
| **显存占用 (70B)** | ~40GB (INT4) | ~42GB (INT4 mix FP16) | ~80GB (INT8) | ~45GB (FP8) |
| **推理速度** | 中 (需Dequant) | 快 (Simulated Group Gemm) | 快 (Native INT8) | 最快 (Native FP8) |
| **抗异常值能力** | 弱 (容易 outliers) | 强 (Scale化解) | 强 (Smooth迁移) | 强 (FP8动态范围) |

## 记忆要点

- GPTQ：基于二阶信息的 PTQ，INT4 精度好，通用性强，但推理有解码开销。
- AWQ：激活感知量化，保留 1% 关键通道为 FP16，推理速度优于 GPTQ。
- SmoothQuant：将激活难度迁移至权重，解决异常值问题，适合 INT8。
- FP8：H100 原生支持，无需软件模拟，量化误差最小，依赖硬件。


## 结构化回答

**30 秒电梯演讲：** 将模型参数从高精度压缩到低精度，减少显存和计算开销。——打个比方，把高清照片压缩成标清，虽然细节少一点，但省空间且传得快。

**展开框架：**
1. **GPTQ** — 基于二阶信息的 PTQ，INT4 精度好，通用性强，但推理有解码开销。
2. **AWQ** — 激活感知量化，保留 1% 关键通道为 FP16，推理速度优于 GPTQ。
3. **SmoothQu** — SmoothQuant：将激活难度迁移至权重，解决异常值问题，适合 INT8。

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「INT4量化对生成质量影响有多大」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "模型量化方法对比：GPTQ vs AWQ vs FP8 vs SmoothQua，30 秒讲清楚。" | 开场钩子 |
| 0:40 | 概念定义动画 | "一句话：将模型参数从高精度压缩到低精度，减少显存和计算开销。" | 核心定义 |
| 1:20 | GPTQ图解 | "基于二阶信息的 PTQ，INT4 精度好，通用性强，但推理有解码开销。" | GPTQ |
| 2:00 | AWQ图解 | "激活感知量化，保留 1% 关键通道为 FP16，推理速度优于 GPTQ。" | AWQ |
| 2:40 | SmoothQuant图解 | "将激活难度迁移至权重，解决异常值问题，适合 INT8。" | SmoothQuant |
| 3:20 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
