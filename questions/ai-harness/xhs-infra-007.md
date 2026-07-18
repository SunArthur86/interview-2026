---
id: xhs-infra-007
difficulty: L4
category: ai-harness
subcategory: 训练框架
tags:
- 分布式训练
- OOM
- MFU
- Profiler
- 小红书
feynman:
  essence: 利用Profiler工具分析算力、显存和通信瓶颈。
  analogy: 像医生看CT一样，用监控工具定位训练过程堵在哪里。
  first_principle: 如何精准定位并解决分布式训练中的资源瓶颈与异常？
  key_points:
  - OOM通常由大Batch、长序列或未开启Gradient Checkpoint引起
  - 低MFU需区分是Compute Bound、Memory Bound还是Communication Bound
  - Hang常见于网络通信故障或Rank间死锁
  - 核心工具：PyTorch Profiler, Nsight Systems/Compute, NCCL Log
follow_up:
- 如何计算训练的理论MFU？
- 通信-计算overlap具体怎么实现？
- Gradient Checkpoint的代价是什么？
memory_points:
- OOM诊断：显存=模型+优化器(2x)+梯度+激活+KV。解法用ZeRO-3切片、Checkpoint换显存、SP切分序列。
- 低MFU诊断：算力Bound查Kernel利用率，内存Bound查HBM带宽。解法通信Overlap、算子融合、IO加速。
- Hang诊断：设NCCL_DEBUG=INFO查通信，用py-spy抓堆栈。常见死锁或IB网卡MTU不一致。
frequency: high
---

# 大模型训练中如何诊断OOM、低MFU和hang？常用的Profiler工具有哪些？

## OOM 诊断

### 显存占用公式
$$Total Memory = Model + Optimizer + Gradients + Activations + KV Cache + Temporary$$

1. **Model Weights (模型参数)**：FP16 时，70B 模型约 140GB。
2. **Optimizer States (优化器状态)**：AdamW 通常需要 FP32 权重备份 + Momentum + Variance（2倍模型大小）。
3. **Gradients (梯度)**：FP16 存储梯度（1倍模型大小）。
4. **Activations (激活值)**：与 Batch Size、Sequence Length、隐藏层维度成正比。

**常见原因 & 解决方案**：
- **原因**：Batch Size 过大、Context Window 过长（KV Cache 爆炸）、未使用 Activation Checkpointing。
- **方案**：
  - **ZeRO-3** (DeepSpeed)：将优化器、梯度、参数切片分布到不同 GPU。
  - **Gradient Checkpointing (Activation Recomputation)**：以计算换显存，前向时不存所有激活，反向时重算。
  - **Sequence Parallel (TP + SP)**：将 Sequence 维度切分，减少单卡 KV Cache 压力。
  - **CPU Offload**：将优化器状态卸载到 CPU（增加通信开销，换显存）。

**实战案例**：
在某次 70B 模型长文本微调中，设置 `max_length=8192` 时 OOM。排查发现 KV Cache 占用了 40%+ 显存。解决方案是将 Attention 机制替换为 FlashAttention-2 并开启 Sequence Parallel（SP），将 Ring-Attention 结合使用，成功在 8x A100 (80G) 上训练。

## 低 MFU 诊断
MFU (Model FLOPs Utilization) = 实际 TFLOPS / 理论峰值 TFLOPS

### 诊断流程与工具
```text
[PyTorch Profiler / Nsight Systems]
         |
   +-----+-----+
   |           |
Compute     Memory
Bound        Bound
   |           |
[检查Kernel] [检查访问]
   |           |
Tensor Core  HBM BW
利用率?      利用率?
```

**常见低 MFU 原因**：
- **通信未 Overlap**：计算与通信未重叠（例如 `torch.nn.parallel.DistributedDataParallel` 梯度同步是阻塞的）。应使用 `torch.distributed.all_reduce` 在反向传播时异步执行，或启用 ZeRO-1/2 的梯度预取。
- **IO 瓶颈**：数据加载慢，GPU 等待 CPU。需设置 `num_workers`、`prefetch_factor`，或使用 WebDataset。
- **Kernel Launch Overhead**：大量小 Kernel 发射。算子融合 可解决。
- **非 MatMul 操作占比高**：LayerNorm、Softmax、Element-wise 操作占比过高，未利用 Tensor Core。

**代码示例**：
```python
# 使用 torch.distributed.barrier 确保同步，并优化 Dataloader
torch.distributed.barrier() # 确保所有进程同时开始

# 针对 IO Bound 优化的 DataLoader 设置
train_loader = DataLoader(
    dataset,
    batch_size=per_gpu_batch,
    num_workers=8,           # 根据 CPU 核心数调整
    prefetch_factor=4,       # 预取批次
    pin_memory=True,         # 加速 CPU -> GPU 传输
    persistent_workers=True  # 保持 worker 进程避免重复初始化
)
```

## Hang 诊断
1. **NCCL 调试**：设置环境变量 `NCCL_DEBUG=INFO`，查看通信是否卡在某个 All-Reduce 步骤。
2. **死锁检测**：
   - 检查 `torch.distributed.barrier()` 是否在所有 Rank 一致调用。
   - 避免在一个进程中使用多个 NCCL 通信流导致的资源竞争。
3. **网络拓扑**：检查 InfiniBand (IB) 或 RoCE 的丢包情况（`ibstat`, `perf top`）。
4. **Stack Trace 抓取**：使用 `py-spy dump --pid <pid>` 或 `gdb -p <pid>` 查看进程卡在哪个 Python/C++ 函数（通常卡在 NCCL Kernel 或 GPU Kernel 中）。

**实战案例**：
多机训练中 Rank 0 经常 Hang 住，其他进程等待。通过 `NCCL_DEBUG=INFO` 发现 Rank 0 的网卡 `TX` 队列满。排查发现是某节点的 IB 网卡 MTU 设置不一致（2048 vs 4096），导致包分片异常，修正后 Hang 消失。

## 工具链
| 工具 | 核心用途 | 关键指标 |
|------|----------|----------|
| **PyTorch Profiler** | 整体性能瓶颈分析 | CPU Time, CUDA Time, Memory Usage |
| **Nsight Systems (nsys)** | 系统级时间线可视化 | Kernel Stream, CUDA memcpy, NCCL Call gap |
| **Nsight Compute (ncu)** | Kernel 级别深度分析 | Tensor Core Utilization, Memory Throughput |

```mermaid
flowchart TD
    classDef start fill:#4CAF50,color:#fff
    classDef process fill:#2196F3,color:#fff
    classDef decision fill:#FF9800,color:#fff
    classDef special fill:#9C27B0,color:#fff
    classDef error fill:#f44336,color:#fff
    classDef info fill:#607D8B,color:#fff
    class Fix start
    class Hang process
    class Issue decision
    class NCCL special
    class OOM error
    class Profile info
    class Stack start
    class Training process
    class ZeRO decision
    class br special
    class py error
    Training[训练任务] --> Issue{问题诊断}
    Issue -->|OOM| ZeRO[ZeRO-3切片<br/>Checkpointing换显存]
    Issue -->|低MFU| Profile[Profiler查Kernel]
    Issue -->|Hang| NCCL[NCCL_DEBUG查通信]
    Profile --> Fix[算子融合/通信Overlap]
    NCCL --> Stack[py-spy抓堆栈]
```


## 记忆要点

- OOM诊断：显存=模型+优化器(2x)+梯度+激活+KV。解法用ZeRO-3切片、Checkpoint换显存、SP切分序列。
- 低MFU诊断：算力Bound查Kernel利用率，内存Bound查HBM带宽。解法通信Overlap、算子融合、IO加速。
- Hang诊断：设NCCL_DEBUG=INFO查通信，用py-spy抓堆栈。常见死锁或IB网卡MTU不一致。


## 结构化回答

**30 秒电梯演讲：** 利用Profiler工具分析算力、显存和通信瓶颈。——打个比方，像医生看CT一样，用监控工具定位训练过程堵在哪里。

**展开框架：**
1. **OOM诊断** — 显存=模型+优化器(2x)+梯度+激活+KV。解法用ZeRO-3切片、Checkpoint换显存、SP切分序列。
2. **低MFU诊断** — 算力Bound查Kernel利用率，内存Bound查HBM带宽。解法通信Overlap、算子融合、IO加速。
3. **Hang诊断** — 设NCCL_DEBUG=INFO查通信，用py-spy抓堆栈。常见死锁或IB网卡MTU不一致。

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「如何计算训练的理论MFU」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "大模型训练中如何诊断OOM、低MFU和hang，30 秒讲清楚。" | 开场钩子 |
| 0:40 | 概念定义动画 | "一句话：利用Profiler工具分析算力、显存和通信瓶颈。" | 核心定义 |
| 1:20 | OOM诊断图解 | "显存=模型+优化器(2x)+梯度+激活+KV。解法用ZeRO-3切片、Checkpoint换显存、SP切分序列。" | OOM诊断 |
| 2:00 | 低MFU诊断图解 | "算力Bound查Kernel利用率，内存Bound查HBM带宽。解法通信Overlap、算子融合、IO加速。" | 低MFU诊断 |
| 2:40 | Hang诊断图解 | "设NCCL_DEBUG=INFO查通信，用py-spy抓堆栈。常见死锁或IB网卡MTU不一致。" | Hang诊断 |
| 3:20 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
