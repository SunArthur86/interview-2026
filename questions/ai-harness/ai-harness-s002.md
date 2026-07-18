---
id: ai-harness-s002
difficulty: L3
category: ai-harness
subcategory: 推理优化
images:
- svg_kvcache.svg
feynman:
  essence: Prefill并行读题，Decode逐字答题，两者计算和访存瓶颈不同。
  analogy: 读题时大脑飞速运转，写字时手速受限而大脑等待。
  first_principle: 如何区分并优化LLM推理中"理解输入"和"生成输出"这两个不同性质的阶段？
  key_points:
  - Prefill阶段计算密集，并行处理Prompt生成KV Cache
  - Decode阶段访存密集，逐Token生成受限于显存带宽
  - Prefill决定首字延迟(TTFT)，Decode决定生成速度(TPOT)
  - 优化需针对不同阶段的瓶颈分别采取措施
memory_points:
- 两阶段对比：Prefill并行算KV密集（决定TTFT），Decode串行读KV受限（决定TPOT）。
- 计算瓶颈对比：Prefill吃算力做O(N^2)矩阵乘，Decode吃显存带宽做大Cache读取。
- 优化策略口诀：Pre用FlashAttn分块算，Dec靠量化投机采样，混批调靠vLLM连续批处理。
- 长上下文避坑：Prompt极长时Prefill耗时O(N^2)激增，TTFT可能远超Decode时间。
---

# LLM推理的Prefill和Decode阶段有什么区别？

LLM自回归推理分两个阶段：

**Prefill阶段（预填充）：**
- 处理输入prompt的所有token
- 一次性并行计算所有token的KV Cache
- 计算密集型：大量矩阵乘法
- GPU利用率高

**Decode阶段（解码）：**
- 逐个生成输出token
- 每步用之前所有token的KV Cache（从缓存读取）
- 内存密集型：瓶颈在KV Cache读取带宽
- GPU利用率低（大模型通常<10%）

- **阶段对比**

| 维度 | Prefill 阶段 | Decode 阶段 |
|------|-------------|-------------|
| 输入处理 | 一次处理所有 Prompt Token | 逐个生成 Output Token |
| 计算模式 | 并行计算 | 自回归串行计算 |
| 瓶颈资源 | GPU 算力 | 显存带宽 |
| 延迟特征 | 决定 TTFT (首字延迟) | 决定 TPOT (生成速度) |
| 优化手段 | FlashAttention, 分块预填充 | KV Cache 量化, Speculative Decoding |

- **实战案例**：在长文档总结任务中，Prefill 占用了总时间的 80%（由于 Prompt 极长）。通过采用分块 Prefill 策略，用户能在 1 秒内看到第一个生成的字，极大改善了“即时反馈”体验。踩坑：若 Decode 阶段显存带宽不足，即使显卡算力很强，生成速度也会被锁死在 20 tokens/s 以下。

- **代码示例**：
```python
# 伪代码：模拟 Prefill 和 Decode 的资源消耗差异
import torch

def profile_phase(stage, input_ids, past_kv=None):
    if stage == "prefill":
        # Prefill: 矩阵大，计算量 O(N^2)
        logits, kv_cache = model.forward(input_ids)
        print(f"Prefill: High FLOPs, GPU Compute Load: {torch.cuda.utilization()}%")
        return logits, kv_cache
    else:
        # Decode: 矩阵小，需加载巨大 KV Cache，带宽瓶颈 O(N)
        logits, kv_cache = model.forward(input_ids[-1:], past_kv)
        print(f"Decode: Low FLOPs, HBM Bandwidth Load: High")
        return logits, kv_cache
```

**优化策略：**
- Prefill优化：FlashAttention、Chunked Prefill（将长prompt分块处理）
- Decode优化：KV Cache量化、GQA/MQA、投机采样
- 调度优化：将Prefill和Decode请求混合批处理（vLLM的continuous batching）

**TTFT（Time To First Token）= Prefill时间**
**TPOT（Time Per Output Token）= Decode时间**

- **补充：计算与访存瓶颈的量化分析**
- **Prefill**: 算术强度高，FLOPs 随序列长度平方增长（$O(N^2)$），GPU 计算单元满载。
- **Decode**: 仅处理单个 Token，计算量小但需加载巨大的 KV Cache（$O(N)$），主要受限于 HBM 带宽。
- **混合调度**: 为了避免 Decode 阶段长请求阻塞短请求的 TTFT，vLLM 等框架会采用迭代级调度，优先保证新请求的 Prefill 资源。

- **边界情况**：
  - **Batch Size = 1**：此时 Decode 阶段不仅受限于显存带宽，Kernel Launch 的开销也可能成为瓶颈，导致 GPU 利用率极低（<2%）。
  - **空输入/极短 Prompt**：Prefill 阶段时间极短，几乎可忽略，系统总耗时完全取决于 Decode 阶段的步数。
  - **KV Cache 耗尽**：在长文本生成中，如果 KV Cache 超出预设显存上限，系统必须回退到重计算模式或截断上下文，导致 Decode 速度急剧下降。

## 面试追问
1. **追问 1**：在 Continuous Batching 调度中，如果有多个长文本的 Decode 请求占用显存，导致新请求的 Prefill 无法分配到足够的 KV Cache 空间，这种情况下通常有哪些缓解策略？（引导：Priority Scheduling, Preemption 机制，或 KV Cache Swap out）
2. **追问 2**：为什么投机采样（Speculative Decoding）通常主要加速 Decode 阶段，而在 Prefill 阶段效果不明显？（引导：Prefill 本身已经是高度并行的计算密集型操作，串行的 Draft 无法带来加速；且小模型处理长 Prompt 可能不如大模型快）

## 易错点
1. **误区**：Prefill 阶段总是比 Decode 阶段快。
   **纠正**：在极长上下文（如 1M tokens）场景下，Prefill 的计算量 $O(N^2)$ 会变得极其巨大，此时 TTFT 可能长达数十秒，甚至超过整个 Decode 阶段的时间。
2. **误区**：Batch Size 越大，推理吞吐量一定线性增加。
   **纠正**：在 Decode 阶段，过大的 Batch Size 可能导致 KV Cache 占用过多显存，触发 OOM 或者频繁的内存碎片整理；同时，如果 Batch 内各序列长度差异巨大，计算会受限于最长的序列，导致 Padding 浪费。

```mermaid
flowchart LR
    Prompt[输入Prompt] --> Prefill[Prefill阶段<br/>并行算KV]
    Prefill --> TTFT[决定TTFT]
    Prefill --> Decode[Decode阶段<br/>串行读KV]
    Decode --> TPOT[决定TPOT]
    Decode --> Output[输出Token]
    Prefill -.->|O(N^2)矩阵乘| Compute[吃算力]
    Decode -.->|大Cache读取| Memory[吃显存带宽]
```

## 记忆要点

- 两阶段对比：Prefill并行算KV密集（决定TTFT），Decode串行读KV受限（决定TPOT）。
- 计算瓶颈对比：Prefill吃算力做O(N^2)矩阵乘，Decode吃显存带宽做大Cache读取。
- 优化策略口诀：Pre用FlashAttn分块算，Dec靠量化投机采样，混批调靠vLLM连续批处理。
- 长上下文避坑：Prompt极长时Prefill耗时O(N^2)激增，TTFT可能远超Decode时间。


## 结构化回答

**30 秒电梯演讲：** Prefill并行读题，Decode逐字答题，两者计算和访存瓶颈不同。——打个比方，读题时大脑飞速运转，写字时手速受限而大脑等待。

**展开框架：**
1. **两阶段对比** — Prefill并行算KV密集（决定TTFT），Decode串行读KV受限（决定TPOT）。
2. **计算瓶颈对比** — Prefill吃算力做O(N^2)矩阵乘，Decode吃显存带宽做大Cache读取。
3. **优化策略口诀** — Pre用FlashAttn分块算，Dec靠量化投机采样，混批调靠vLLM连续批处理。

**收尾：** 以上三点都能配合实战聊。您想深入聊哪一块？

## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "LLM推理的Prefill和Decode阶段有什么区别，30 秒讲清楚。" | 开场钩子 |
| 0:36 | 概念定义动画 | "一句话：Prefill并行读题，Decode逐字答题，两者计算和访存瓶颈不同。" | 核心定义 |
| 1:12 | 两阶段对比图解 | "Prefill并行算KV密集（决定TTFT），Decode串行读KV受限（决定TPOT）。" | 两阶段对比 |
| 1:48 | 计算瓶颈对比图解 | "Prefill吃算力做O(N^2)矩阵乘，Decode吃显存带宽做大Cache读取。" | 计算瓶颈对比 |
| 2:24 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
