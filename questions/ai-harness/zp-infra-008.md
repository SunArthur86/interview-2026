---
id: zp-infra-008
difficulty: L4
category: ai-harness
subcategory: 推理优化
tags:
- 智谱
- 面经
- CUDA
- Kernel
- Roofline
- Nsight
feynman:
  essence: 利用Roofline模型和Nsight工具定位Kernel瓶颈
  analogy: 像体检看心率（计算）和供血（内存），哪边慢治哪边
  first_principle: 是计算能力不足还是数据传输太慢限制了Kernel性能？
  key_points:
  - 计算算术强度AI判断受限于计算还是显存
  - Nsight Compute分析Occupancy和Stall原因
  - Memory Bound优化合并读写，Compute Bound用Tensor Core
  - 通过Tiling减少全局内存访问
follow_up:
- Occupancy 是越高越好吗？—— 不一定，高 occupancy 可能意味着低 per-thread 资源
- 怎么判断 Kernel 是否已经最优？—— 与 cuBLAS/cuDNN 对比，看差距
- FlashAttention 的 Kernel 为什么快？—— 减少了 global memory 读写，在 SRAM 内完成分块计算
memory_points:
- 计算公式：算术强度AI = FLOPs / Bytes，对比转折点判断Bound类型
- Memory Bound：带宽瓶颈，优化方向是合并访问、Shared Memory分块、向量化读写
- Compute Bound：算力瓶颈，优化方向是Tensor Core利用、指令流水线、减少逻辑判断
- 工具定位：Nsight Compute看Stall原因，Nsight Systems看计算与通信重叠情况
---

# 【智谱Infra面经】如何评估一个 CUDA Kernel 的优化空间？怎么判断它是计算 bound 还是内存 bound？

**CUDA Kernel 优化评估流程：**

**1. Roofline 模型分析**
```
Arithmetic Intensity (AI) = FLOPs / Bytes

计算上限 = min(峰值算力, AI × 峰值带宽)

如果 AI > 转折点 → Compute Bound
如果 AI < 转折点 → Memory Bound

转折点 = 峰值算力 / 峰值带宽
  A100: 312 TFLOPS / 2TB/s ≈ 156 FLOPs/Byte
  H100: 989 TFLOPS / 3.35TB/s ≈ 295 FLOPs/Byte
```

**2. Nsight Compute 分析**
- **Occupancy**：活跃 warp 数 / 最大 warp 数
  - 低 occupancy → warp 不足以隐藏延迟
- **Memory Throughput**：实际带宽 / 峰值带宽
  - >80% → 接近 memory bound
- **Compute Throughput**：实际 FLOPS / 峰值 FLOPS
  - >80% → 接近 compute bound
- **Stall Reasons**：
  - `stall_long_scoreboard` → 等待内存
  - `stall_short_scoreboard` → 等待计算
- **Bank Conflict**：shared memory bank 冲突

**3. 具体优化方向**

| 瓶颈类型 | 优化方向 |
|----------|--------|
| **Memory Bound** | Coalesced access、shared mem tiling、减少冗余读写 |
| **Compute Bound** | Tensor Core (WMMA/MMA)、指令流水线、减少非 matmul 计算 |
| **Latency Bound** | 增加并行度（更多 warp/block）、prefetch |
| **Bank Conflict** | 调整 shared mem 布局、改变访问模式 |

**4. GEMM Kernel 优化示例**
```
朴素 GEMM: 每个元素从 global mem 读多次 → 严重 memory bound
优化: 
  1. Tiling: 把块加载到 shared mem（减少 global 读取）
  2. Register tiling: 每个 thread 负责小块，用寄存器累积
  3. Tensor Core: 用 WMMA/MMA 指令做矩阵乘
  4. Vectorized access: float4 一次读 4 个 float
```

---

**实战案例**：
优化一个自定义的 Element-wise Add+Scale Kernel，Nsight 分析显示 `dram__throughput` 仅 50GB/s（远低于 1.5TB/s 峰值），且存在大量 `stall_memory_dependency`。通过将计算逻辑从 `float` 转为 `float4` 向量化读写（一次加载 128bit），带宽利用率飙升至 450GB/s，整体速度提升 8 倍。

**代码示例（CUDA - Memory Coalescing 对比）**：
```cpp
// --- 优化前：Non-Coalesced Access (未对齐读取) ---
__global__ void bad_add(float* x, float* y, float* out, int n) {
    int idx = threadIdx.x + blockIdx.x * blockDim.x;
    // 假设 stride 奇数，导致 warp 内线程访问不连续的内存块
    int stride = 17; 
    if (idx < n) out[idx] = x[idx] + y[stride * idx];
}

// --- 优化后：Coalesced Access (向量化+对齐) ---
__global__ void good_add(float4* x, float4* y, float4* out, int n) {
    int idx = threadIdx.x + blockIdx.x * blockDim.x;
    // float4 一次读 16 bytes，且 warp 内线程连续访问
    if (idx < n) {
        float4 a = x[idx];
        float4 b = y[idx];
        // 简化的向量加法
        out[idx].x = a.x + b.x;
        out[idx].y = a.y + b.y;
        out[idx].z = a.z + b.z;
        out[idx].w = a.w + b.w;
    }
}
```

## 常见考点
1. **Occupancy 是不是越高越好？**（不是，有时牺牲 Occupancy 换取更多的 Register/Shared Memory 使用能减少全局内存访问）
2. **如何通过 Nsight Compute 的 `dram__throughput` 和 `dram__bytes_sum` 快速判断是否 Memory Bound？**（如果吞吐接近峰值或 Stall 主要在 Memory，即为 Memory Bound）
3. **Warp Divergence 对性能的影响有多大？如何检测？**（查看 `smsp__thread_branch_executed` 指标）

```mermaid
flowchart TD
    Kernel[CUDA Kernel] --> AI[算术强度AI<br/>FLOPs/Bytes]
    AI --> Compare{对比转折点}
    Compare -->|低于| Memory[Memory Bound<br/>合并访问/分块]
    Compare -->|高于| Compute[Compute Bound<br/>Tensor Core/流水线]
    Memory --> Tool[Nsight Compute]
    Compute --> Tool
```

## 记忆要点

- 计算公式：算术强度AI = FLOPs / Bytes，对比转折点判断Bound类型
- Memory Bound：带宽瓶颈，优化方向是合并访问、Shared Memory分块、向量化读写
- Compute Bound：算力瓶颈，优化方向是Tensor Core利用、指令流水线、减少逻辑判断
- 工具定位：Nsight Compute看Stall原因，Nsight Systems看计算与通信重叠情况


## 结构化回答

**30 秒电梯演讲：** 利用Roofline模型和Nsight工具定位Kernel瓶颈——打个比方，像体检看心率（计算）和供血（内存），哪边慢治哪边

**展开框架：**
1. **计算公式** — 算术强度AI = FLOPs / Bytes，对比转折点判断Bound类型
2. **Memory B** — Memory Bound：带宽瓶颈，优化方向是合并访问、Shared Memory分块、向量化读写
3. **Compute** — Compute Bound：算力瓶颈，优化方向是Tensor Core利用、指令流水线、减少逻辑判断

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「Occupancy 是越高越好吗？—— 不一定，高 occupancy 可能意味着低 per-thread 资源」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "【智谱Infra面经】如何评估一个 CUDA Kernel 的优化空间，30 秒讲清楚。" | 开场钩子 |
| 0:40 | 概念定义动画 | "一句话：利用Roofline模型和Nsight工具定位Kernel瓶颈" | 核心定义 |
| 1:20 | 计算公式图解 | "算术强度AI = FLOPs / Bytes，对比转折点判断Bound类型" | 计算公式 |
| 2:00 | Memory Bound图解 | "带宽瓶颈，优化方向是合并访问、Shared Memory分块、向量化读写" | Memory Bound |
| 2:40 | 要点图解 | "Compute Bound：算力瓶颈，优化方向是Tensor Core利用、指令流水线、减少逻辑判断" | 要点 |
| 3:20 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
