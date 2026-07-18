---
id: ai-harness-s003
difficulty: L3
category: ai-harness
subcategory: 推理优化
images:
- svg_transformer.svg
feynman:
  essence: 通过拆分模型层、权重矩阵或数据序列，突破单卡显存限制。
  analogy: 大象装冰箱：把象切开分装(层并行)，或几个人一起抬(张量并行)，或多冰箱放不同象(数据并行)。
  first_principle: 如何将一个巨大的模型拆解，使其能分布式地运行在多个有限的硬件资源上？
  key_points:
  - TP切分层内权重，通信频繁适合单机内互联
  - PP切分层间堆叠，减少通信气泡适合跨机
  - DP处理不同数据配合ZeRO节省显存
  - SP和EP分别针对长序列和MoE架构优化
memory_points:
- 切分维度对比：TP切层内权重（需高频通信），PP切层（跨机低频通信），DP切数据。
- 通信依赖对比：TP极依赖单机NVLink带宽做All-Reduce，PP靠跨机IB网络做点对点激活通信。
- 选型口诀：单机多卡用TP，跨机超长模型用PP，数据规模大用DP（含ZeRO分片）。
- 推理避坑：流式推理Batch=1时PP会有严重流水线气泡，推理应首选TP避免高延迟。
---

# 模型并行有哪些方案？

大模型超过单GPU显存时需要并行：

1. **张量并行**：
- 将每一层的权重矩阵按行/列切分到多GPU
- 每层需要All-Reduce通信
- 适合单机多卡（NVLink高速互联）

2. **流水线并行**：
- 将模型的不同层分到不同GPU
- 微批次处理（Micro-batching）减少气泡
- 适合跨机多卡

3. **数据并行**：
- 每个GPU有完整模型副本
- 处理不同batch
- ZeRO优化：将优化器状态/梯度/参数分片到不同GPU

4. **序列并行**：
- 将长序列切分到多GPU处理
- Ring Attention、DeepSpeed Ulysses

5. **专家并行**：
- MoE模型的专家分布到不同GPU
- All-to-All通信

Megatron-LM + DeepSpeed通常组合使用TP+PP+DP。

- **补充：通信开销与拓扑结构**
- **TP 通信**: 使用 All-Reduce，必须在层间完成，延迟敏感，极其依赖 NVLink 带宽（通常仅限单机内）。
- **PP 通信**: 点对点通信，仅需传递激活值，对带宽要求相对较低，适合跨机（以太网/InfiniBand）。
- **3D 并行**: 结合 DP(数据) + PP(层) + TP(模型切分)，用于训练千亿参数模型；推理中常用 TP + PP。

- **并行策略对比图**

```text
[张量并行 TP]       [流水线并行 PP]       [数据并行 DP]
Layer 1 (Part A)    GPU 0: Layer 1-10    GPU 0: Full Model
Layer 1 (Part B)    GPU 1: Layer 11-20   GPU 1: Full Model
    │  (All-Reduce)      │ (P2P Send)        │ (All-Reduce)
Layer 2 (Part A)    GPU 2: Layer 21-30   GPU 2: Full Model
Layer 2 (Part B)                        GPU 3: Full Model
```

### 实战案例
在训练 70B 参数模型时，若强行在单机 8 卡上使用 PP，会因为跨层通信频繁导致 NVLink 带宽拥塞；实战中通常将 TP 限制在单机内（利用 NVLink），而将 PP 扩展到多机间（利用 InfiniBand），以平衡计算与通信。

### 并行策略选型对比
| 维度 | 张量并行 (TP) | 流水线并行 (PP) | 数据并行 (DP/ZeRO) | 序列并行 (SP) |
| :--- | :--- | :--- | :--- | :--- |
| **切分粒度** | 层内权重矩阵切分 | 模型层切分 | 数据批次切分 | 输入序列切分 |
| **通信频率** | 极高（每层） | 低（阶段边界） | 低（Step 结束） | 高（Attention 内）
| **显存节省** | 中（仅权重分片） | 高（每卡仅存部分层） | 低（需存完整副本，ZeRO除外）| 高（KV Cache 分片）
| **适用场景** | 单机多卡、强带宽 | 跨机部署、超长模型 | 数据规模大、模型适中 | 超长上下文文本 |
| **主要缺点** | 通信瓶颈明显 | 存在气泡，调度复杂 | 显存占用大（非 ZeRO）| 实现复杂，依赖特定算子 |

### 代码示例 (PyTorch - TP 切分列示例)
```python
import torch.distributed as dist
# Column Parallel Linear: Y = XA (A is split by column)
class ColumnParallelLinear(torch.nn.Module):
    def __init__(self, in_features, out_features):
        super().__init__()
        self.weight = torch.nn.Parameter(torch.randn(out_features // world_size, in_features))
    
    def forward(self, x):
        # All-Reduce to sum partial results from all GPUs
        output = torch.nn.functional.linear(x, self.weight)
        dist.all_reduce(output, op=dist.ReduceOp.SUM)
        return output
```

- **边界情况**：
  - **推理中的 PP 气泡**：在推理（尤其是流式输出）阶段，如果 Batch Size 为 1，流水线并行的“气泡”开销占比极高，导致 TTFT 增加显著。通常需要拆分 Batch（Interleaved PP）或改用 TP。
  - **显存不均衡**：在 MoE 模型的专家并行中，如果某些 Token 极其倾向于特定的专家（热点问题），会导致对应 GPU 显存溢出，而其他 GPU 处于空闲状态（负载不均衡）。

## 面试追问
1. **追问 1**：在进行模型并行推理时，为什么通常优先选择张量并行（TP）而不是流水线并行（PP）？（引导：TP 避免了 PP 的 bubble，且单机 NVLink 延迟极低；PP 在低并发场景下延迟不仅没优势反而可能劣势）
2. **追问 2**：ZeRO-3 将参数切分到了不同卡，那在做推理前向传播时，All-Gather 的通信时机应该如何选择才能最小化延迟？（引导： prefetching，在计算第 i 层时异步获取第 i+1 层的参数）

## 易错点
1. **误区**：数据并行（DP）是显存效率最高的并行方式。
   **纠正**：普通 DP 每个卡都需要存储完整的模型参数、梯度和优化器状态，显存效率极低。只有结合 ZeRO（ZeRO-1/2/3）后，通过状态分片才能降低显存占用。
2. **误区**：流水线并行（PP）的阶段划分越多越好。
   **纠正**：PP 阶段划分越多，虽然每张卡的显存压力越小，但产生的通信边界和 Bubble 也会越多，导致 GPU 利用率下降和 latency 增加。

## 核心知识点图

<img src="/interview-2026/images/diagram_ai-harness_ai-harness-s003.svg" alt="模型并行有哪些方案？ - 核心知识点图" style="max-width:100%;height:auto;border:1px solid var(--border);border-radius:8px;margin:1em 0;" />

## 记忆要点

- 切分维度对比：TP切层内权重（需高频通信），PP切层（跨机低频通信），DP切数据。
- 通信依赖对比：TP极依赖单机NVLink带宽做All-Reduce，PP靠跨机IB网络做点对点激活通信。
- 选型口诀：单机多卡用TP，跨机超长模型用PP，数据规模大用DP（含ZeRO分片）。
- 推理避坑：流式推理Batch=1时PP会有严重流水线气泡，推理应首选TP避免高延迟。


## 结构化回答

**30 秒电梯演讲：** 通过拆分模型层、权重矩阵或数据序列，突破单卡显存限制。——打个比方，大象装冰箱：把象切开分装(层并行)，或几个人一起抬(张量并行)，或多冰箱放不同象(数据并行)。

**展开框架：**
1. **切分维度对比** — TP切层内权重（需高频通信），PP切层（跨机低频通信），DP切数据。
2. **通信依赖对比** — TP极依赖单机NVLink带宽做All-Reduce，PP靠跨机IB网络做点对点激活通信。
3. **选型口诀** — 单机多卡用TP，跨机超长模型用PP，数据规模大用DP（含ZeRO分片）。

**收尾：** 以上三点都能配合实战聊。您想深入聊哪一块？

## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "模型并行有哪些方案，30 秒讲清楚。" | 开场钩子 |
| 0:36 | 概念定义动画 | "一句话：通过拆分模型层、权重矩阵或数据序列，突破单卡显存限制。" | 核心定义 |
| 1:12 | 切分维度对比图解 | "TP切层内权重（需高频通信），PP切层（跨机低频通信），DP切数据。" | 切分维度对比 |
| 1:48 | 通信依赖对比图解 | "TP极依赖单机NVLink带宽做All-Reduce，PP靠跨机IB网络做点对点激活通信。" | 通信依赖对比 |
| 2:24 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
