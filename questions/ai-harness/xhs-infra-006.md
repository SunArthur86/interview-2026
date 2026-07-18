---
id: xhs-infra-006
difficulty: L5
category: ai-harness
subcategory: 推理与部署
tags:
- CUDA
- Kernel
- GEMM
- Tensor Core
- 小红书
feynman:
  essence: 利用Shared Memory分块和Tensor Core硬件加速矩阵乘法。
  analogy: 像搬砖一样，先把砖（数据）搬到脚手架，再快速砌墙，减少来回跑。
  first_principle: 如何最大化利用GPU内存层级和专用计算单元（Tensor Core）？
  key_points:
  - 利用Tiling将数据块加载到Shared Memory复用
  - 合并访存以最大化利用显存带宽
  - 避免Bank Conflict保证Shared Memory并发效率
  - 调用Tensor Core（WMMA API）进行矩阵运算加速
follow_up:
- 如何判断一个Kernel是memory-bound还是compute-bound？
- shared memory tiling的大小如何选择？
- MoE模型的router kernel有什么特殊优化？
memory_points:
- 内存优化：Coalescing 合并访问，Shared Memory Tiling 分块复用，Padding 消除 Bank Conflict。
- Tensor Core：使用 WMMA API，要求 FP16/BF16 输入和 FP32 累加，数据布局需对齐。
- 流水线：Double Buffering 异步加载，隐藏内存延迟，掩盖数据传输时间。
- 性能分析：用 Roofline 模型判断是 Memory Bound 还是 Compute Bound，对症下药。
---

# CUDA Kernel优化：如何写一个高效的GEMM（矩阵乘法）？bank conflict和Tensor Core如何优化？

## GEMM 优化层次（从底到顶）

### 1. 内存访问优化
- **Coalescing（合并访问）**：保证 Warp 内 32 个线程访问连续的全局内存地址，合并为 1-2 个内存事务（128B）。
- **Shared Memory Tiling（分块）**：利用 Shared Memory 作为软件管理 Cache，将全局内存数据分块复用。
  - 原理：计算 $C = A \times B$，将 A 和 B 切分为 tile 存入 SM，每个线程计算多个元素，减少全局内存访问次数（$O(N^3) \to O(N^2)$）。
- **Bank Conflict 消除**：
  - Shared Memory 分为 32 个 Bank，32 位宽。如果 32 个线程访问同一个 Bank 的不同地址（Stride 为 32 的倍数）会导致冲突。
  - **解决方案**：Padding（维度加 1），或使用 `float4`/`ldg` 向量加载。

### 2. Tensor Core 利用
- **WMMA（Warp Matrix Multiply-Accumulate）API**：
  - 利用 Warp 级别的矩阵指令。
  - **输入**：FP16/BF16 (A, B矩阵)，**累加**：FP32 (C矩阵)。
  - **形状**：16x16x16 (MMA.16x16x16) 或 8x8x32 (早期 Volta)。
- **Hopper (H100) FP8 支持**：引入 FMA 指令，支持 E4M3/E5M2 格式，吞吐量翻倍。
- **数据布局转换**：Tensor Core 要求数据按行/列主序交错存储（如 TN, NN 布局），否则无法利用硬件加速。

### 3. Tiling 策略与流水线

```text
GEMM Tiling & Pipeline 逻辑图

Global Memory (DRAM)
   |      | 
   v      v
+---------------------+
| Shared Mem (Tile A) | <--- Block (32x32 threads)
| Shared Mem (Tile B) | <--- Warp 负责 Sub-C 的计算
+---------------------+
   |      | (Registers)
   v      v
Registers (Thread Fragment)
   |      |
   +--->[ Accumulate (Tensor Core) ]
```

- **Grid/Block 划分**：
  - Grid: `(M/BM, N/BN)`
  - Block: `(BM, BN, BK)`，通常使用 2D 线程块 `(32, 32)`。
- **Double Buffering / Pipeline**：
  - 在计算当前 Tile 的同时，异步加载下一个 Tile (`cp.async`)，隐藏内存延迟。

### 4. Roofline 模型分析
- **公式**：`Performance = min { Peak Compute, Bandwidth * Arithmetic Intensity }`
- **诊断**：
  - 用 `Nsight Compute` 查看 `Memory Throughput` 和 `Compute Throughput`。
  - 如果 **Mem bound**（内存受限，Stall Long）：优化 Shared Memory 读写、增加 Cache Reuse、使用 `__restrict__` 指针。
  - 如果 **Compute bound**（计算受限）：增大 Tile 尺寸、使用 Tensor Core、优化指令流水线。

### 关键指标
- **Occupancy（占用率）**：并非越高越好，足够掩盖延迟即可（通常 >50% 即可）。过高可能意味着 Register/Shared 使用不足。
- **IPC (Instructions Per Cycle)**：衡量指令发射效率。
- **FLOPs Utilization**：实际算力 / 理论峰值（A100 312 TFLOPS FP16 Tensor Core）。

## 常见考点
1. **Shared Memory Bank Conflict 的具体场景**：如果 `int array[32]`，线程 `tid` 访问 `array[tid * 32]`，会访问同一个 Bank，导致 32-way Serialize。如何通过 Padding 解决？

### 1. 实战案例
- **场景**：优化某推荐系统的Embedding Lookup与Dense Layer混合计算。原GEMM Kernel因Shared Memory配置过小（仅48KB），导致L1 Cache未充分利用，Roofline分析显示严重Memory Bound。调整Tile大小从128x128增至128x256后，吞吐量提升40%。
- **踩坑**：在使用Tensor Core时，若矩阵维度M/N/K不是16/8的倍数，未进行Padding会导致硬件无法对齐读取，造成Illegal Memory Access或结果错误。

### 2. 代码示例 (CUDA C++ - Tensor Core WMMA 简化版)
```cpp
#include <mma.h>
using namespace nvcuda::wmma;

__global__ void wmma_gemm(half *A, half *B, float *C, int M, int N, int K) {
    // 1. 定义矩阵片段 (16x16x16)
    fragment<matrix_a, 16, 16, 16, row_major> a_frag;
    fragment<matrix_b, 16, 16, 16, col_major> b_frag;
    fragment<accumulator, 16, 16, 16, float> c_frag;

    // 2. 加载矩阵到片段 (自动处理Shared Memory到Register)
    load_matrix_sync(a_frag, A + warpId * ...);
    load_matrix_sync(b_frag, B + ...);
    fill_fragment(c_frag, 0.0f);

    // 3. 计算 (Tensor Core指令)
    for (int k = 0; k < K; k += 16) {
        mma_sync(c_frag, a_frag, b_frag, c_frag);
        // 更新指针加载下一块...
    }

    // 4. 存储结果
    store_matrix_sync(C + ..., c_frag, mem_row_major);
}
```

### 3. 对比表格
| 优化维度 | 标准 CUDA Core | Shared Memory Tiling | Tensor Core (WMMA) |
| :--- | :--- | :--- | :--- |
| **计算单元** | FP32/FP16 ALU | FP32/FP16 ALU | 4x4x4 或 16x16x16 Matrix Units |
| **指令级** | FADD/FMUL | FADD/FMUL (Warp Shuffle) | HMMA (FP16) / MMA (INT8/FP8) |
| **数据吞吐** | 1x (Base) | 2-4x (由于Cache复用) | **8-16x** (硬件矩阵乘法) |
| **编程复杂度** | 低 | 中 (需手动Tiling/Unroll) | 高 (需特定数据布局/Alignment) |
| **主要瓶颈** | Latency | Shared Memory Bandwidth / Bank Conflict | Register File Bandwidth |
| **适用算子** | Element-wise, Reduction | 卷积, 小矩阵乘法 | 大矩阵乘法 (GEMM), Attention QKV |

```mermaid
flowchart TD
    Matrix[矩阵乘法GEMM] --> Tile[Shared Memory Tiling]
    Tile --> Coalescing[Coalescing合并访问]
    Coalescing --> Padding[Padding消Bank Conflict]
    Padding --> TC[Tensor Core<br/>WMMA API]
    TC --> Pipe[Double Buffering<br/>异步加载]
    Pipe --> Roofline[Roofline分析]
```


## 记忆要点

- 内存优化：Coalescing 合并访问，Shared Memory Tiling 分块复用，Padding 消除 Bank Conflict。
- Tensor Core：使用 WMMA API，要求 FP16/BF16 输入和 FP32 累加，数据布局需对齐。
- 流水线：Double Buffering 异步加载，隐藏内存延迟，掩盖数据传输时间。
- 性能分析：用 Roofline 模型判断是 Memory Bound 还是 Compute Bound，对症下药。


## 结构化回答

**30 秒电梯演讲：** 利用Shared Memory分块和Tensor Core硬件加速矩阵乘法。——打个比方，像搬砖一样，先把砖（数据）搬到脚手架，再快速砌墙，减少来回跑。

**展开框架：**
1. **内存优化** — Coalescing 合并访问，Shared Memory Tiling 分块复用，Padding 消除 Bank Conflict。
2. **Tensor C** — Tensor Core：使用 WMMA API，要求 FP16/BF16 输入和 FP32 累加，数据布局需对齐。
3. **流水线** — Double Buffering 异步加载，隐藏内存延迟，掩盖数据传输时间。

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「如何判断一个Kernel是memory-bound还是compute-bound」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "CUDA Kernel优化：如何写一个高效的GEMM（矩阵乘法），30 秒讲清楚。" | 开场钩子 |
| 0:40 | 概念定义动画 | "一句话：利用Shared Memory分块和Tensor Core硬件加速矩阵乘法。" | 核心定义 |
| 1:20 | 内存优化图解 | "Coalescing 合并访问，Shared Memory Tiling 分块复用" | 内存优化 |
| 2:00 | Tensor Core图解 | "使用 WMMA API，要求 FP16/BF16 输入和 FP32 累加，数据布局需对齐。" | Tensor Core |
| 2:40 | 流水线图解 | "Double Buffering 异步加载，隐藏内存延迟，掩盖数据传输时间。" | 流水线 |
| 3:20 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
