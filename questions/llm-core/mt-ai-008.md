---
id: mt-ai-008
difficulty: L3
category: llm-core
categories:
- eng-practice
- llm-core
subcategory: 模型结构
tags:
- 美团
- 面经
- Qwen
- 模型演进
feynman:
  essence: 阿里通义千问系列的开源演进史，核心是架构标准化与数据规模扩展。
  analogy: 像汽车迭代，从普通轿车（Qwen-1）升级到超跑（Qwen-2.5），引擎架构优化且燃料更多。
  first_principle: 如何在保持开源领先的同时，平衡模型性能、长上下文能力与推理成本？
  key_points:
  - Qwen-1 奠定双语基础架构
  - Qwen-1.5 引入 GQA 推理加速
  - Qwen-2 实现长文本与多语言突破
  - Qwen-2.5 数据堆至 18T 达到 SOTA
follow_up:
- Qwen 和 LLaMA 架构有什么区别？—— Qwen 用 GQA（1.5起），LLaMA-2 用 MHA，LLaMA-3 才用 GQA
- Qwen 的训练数据有多大？—— Qwen-2.5 约 18T tokens
- Qwen-VL 是怎么做多模态的？—— ViT 编码图像 + 适配层对齐到语言空间
memory_points:
- Qwen1筑基(双语强)，1.5换代GQA(省显存)，2代破壁128K(多语言)，2.5全能成SOTA
- 架构演进：MHA转GQA减少KV Cache，通信效率提升30%
- 长度演进：32K外推 -> YaRN+DCA算法外推128K -> 原生全长训练128K
- Qwen2.5质变核心：喂入18T海量Token，并衍生Coder/Math专精垂直版本
---

# 【美团面经】串一下 Qwen 系列，几版模型都做了哪些贡献？

**Qwen（通义千问）系列演进路线：**

**Qwen-1（2023.8）：**
- 参数：1.8B ~ 72B
- 架构：标准 Decoder-only + RoPE + SwiGLU
- 贡献：中英双语强、代码能力强、开源完整

**Qwen-1.5（2024.2）：**
- 参数：0.5B ~ 110B
- 改进：GQA（Grouped Query Attention）减少 KV Cache
- 训练：更大规模数据 + 更长上下文（32K）
- 贡献：性能接近 LLaMA-2，部分超越

**Qwen-2（2024.6）：**
- 参数：0.5B ~ 72B
- 改进：
  - 支持 128K 上下文（YaRN + DCA）
  - 多语言（29 种语言）
  - 更强的代码和数学能力
- 贡献：开源 SOTA，72B 接近 GPT-4 水平

**Qwen-2.5（2024.11）：**
- 参数：0.5B ~ 72B
- 改进：
  - 训练数据 18T tokens（大规模扩展）
  - 原生 128K 上下文
  - 代码能力接近专精模型（Qwen2.5-Coder）
  - 数学能力大幅提升（Qwen2.5-Math）
- 贡献：全面开源 SOTA，多个垂直版本

**核心技术架构演进：**
```text
┌─────────────┐    ┌───────────────────────┐    ┌───────────────────────┐
│  Qwen-1     │    │     Qwen-1.5          │    │    Qwen-2 / 2.5       │
│─────────────│    │───────────────────────│    │───────────────────────│
│ MHA / MQA   │───►│ GQA (Grouped Query)   │───►│ GQA + Rope Scaling     │
│ SwiGLU      │    │ SwiGLU                │    │ SwiGLU                │
│ 8K Context  │    │ 32K Context           │    │ 128K (YaRN/DCA)       │
└─────────────┘    └───────────────────────┘    └───────────────────────┘
       │                    │                            │
       ▼                    ▼                            ▼
  Base Release      Cache Effort Up         Long Context & Multilingual
```

**核心技术贡献汇总：**
| 方面 | 贡献 |
|------|------|
| 架构 | GQA + RoPE + SwiGLU 标准化 |
| 训练 | 大规模数据 + 课程学习 |
| 长度 | YaRN 长度外推 → 原生 128K |
| 多语言 | 29 种语言支持 |
| 对齐 | DPO + 多轮 RLHF |
| 生态 | Coder/Math/VL 多模态全家桶 |

### 实战案例
在 Qwen-7B 转向 Qwen-1.5-7B 的迁移中，显存占用显著下降。**实战经验**：在 vLLM 推理框架下，Qwen-1.5-14B 的 GQA 优化使得单张 A10 (24G) 显卡在 Batch Size=16 时比 Qwen-1 版本吞吐量提升了 40%，非常适合高并发中文客服场景。

### 代码示例
```python
# 使用 vLLM 部署 Qwen2.5-72B，利用 GQA 和 FlashAttention 加速
from vllm import LLM, SamplingParams

# 初始化模型 (自动识别 GQA 架构，开启张量并行)
llm = LLM(
    model="Qwen/Qwen2.5-72B-Instruct",
    tensor_parallel_size=4,      # 4卡 A100 跑 72B
    max_model_len=32768,         # 限制显存常用长度
    trust_remote_code=True,
    enforce_eager=True           # 若遇 CUDA 核心兼容问题可开启
)

sampling_params = SamplingParams(temperature=0.7, top_p=0.9, max_tokens=512)
outputs = llm.generate(["你好，请介绍一下北京的景点。"], sampling_params)
```

### 对比表格
| 版本 | 注意力机制 | 最大上下文 | 推理显存优化 (相比上代) | 主要亮点 |
| :--- | :--- | :--- | :--- | :--- |
| **Qwen-1** | MHA / MQA | 8K | 基准 | 中英双语基石，代码强 |
| **Qwen-1.5** | **GQA** | 32K | ↓ ~30% (KV Cache) | 通信效率大幅提升，推理快 |
| **Qwen-2** | GQA | 128K | 持平 (但在长文本下更优) | 多语言，YaRN 外推算法 |
| **Qwen-2.5** | GQA | 128K | 微调 (FP8/量化支持更好) | 数学/代码全能，18T 数据训练 |



## 核心流程图

```mermaid
flowchart TD
    N0["Qwen-1 奠定双语基础架构"]
    N1["Qwen-1.5 引入 GQA 推理加速"]
    N2["Qwen-2 实现长文本与多语言突破"]
    N3["Qwen-2.5 数据堆至 18T 达到"]
    N0 --> N1
    N1 --> N2
    N2 --> N3
    style N0 fill:#2196F3,color:#fff
    style N1 fill:#FF9800,color:#fff
    style N2 fill:#4CAF50,color:#fff
    style N3 fill:#9C27B0,color:#fff
```

## 记忆要点

- Qwen1筑基(双语强)，1.5换代GQA(省显存)，2代破壁128K(多语言)，2.5全能成SOTA
- 架构演进：MHA转GQA减少KV Cache，通信效率提升30%
- 长度演进：32K外推 -> YaRN+DCA算法外推128K -> 原生全长训练128K
- Qwen2.5质变核心：喂入18T海量Token，并衍生Coder/Math专精垂直版本


## 结构化回答

**30 秒电梯演讲：** 阿里通义千问系列的开源演进史，核心是架构标准化与数据规模扩展。——打个比方，像汽车迭代，从普通轿车（Qwen-1）升级到超跑（Qwen-2.5），引擎架构优化且燃料更多。

**展开框架：**
1. **Qwen1筑基(** — Qwen1筑基(双语强)，1.5换代GQA(省显存)，2代破壁128K(多语言)，2.5全能成SOTA
2. **架构演进** — MHA转GQA减少KV Cache，通信效率提升30%
3. **长度演进** — 32K外推 -> YaRN+DCA算法外推128K -> 原生全长训练128K

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「Qwen 和 LLaMA 架构有什么区别？—— Qwen 用 GQA（1.5起），LLaMA-2 用 MHA，LLaMA-3 才用 GQA」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "【美团面经】串一下 Qwen 系列，几版模型都做了哪些贡献，30 秒讲清楚。" | 开场钩子 |
| 0:36 | 概念定义动画 | "一句话：阿里通义千问系列的开源演进史，核心是架构标准化与数据规模扩展。" | 核心定义 |
| 1:12 | 要点图解 | "Qwen1筑基(双语强)，1.5换代GQA(省显存)，2代破壁128K(多语言)，2.5全能成SOTA" | 要点 |
| 1:48 | 架构演进图解 | "MHA转GQA减少KV Cache，通信效率提升30%" | 架构演进 |
| 2:24 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
