---
id: zp-infra-010
difficulty: L3
category: ai-harness
subcategory: 工程化
tags:
- 智谱
- 面经
- MFU
- 性能诊断
- 训练优化
feynman:
  essence: 定位MFU低效、OOM根源和死锁点以恢复训练
  analogy: 像修车，看转速（MFU）、油箱（OOM）和塞车（Hang）分别修
  first_principle: 为什么硬件资源没有充分利用或为什么进程停止响应？
  key_points:
  - 低MFU通常源于通信重叠不足或IO瓶颈
  - OOM通过ZeRO、Checkpoint和混合精度解决
  - Hang通常由NCCL死锁或数据加载卡顿引起
  - 利用Profiler和NCCL日志是关键诊断手段
follow_up:
- MFU 怎么计算？ — — 实际 tokens/s × 每 token FLOPs(6N) / GPU 峰值 FLOPS
- Gradient Checkpoint 的重算开销？ — — 约 20-33%（多一次前向计算）
- NCCL All-Reduce 通信怎么调优？ — — 环形 vs 树形、NCCL_NET、overlap
memory_points:
- 低MFU诊断：用Profiler看Kernel耗时，Nsight看通信重叠，常见瓶颈是通信未Overlap或数据加载慢
- OOM解决：ZeRO-3分片参数、Checkpointing换激活显存、CPU Offload卸载冷数据
- Hang诊断：开启NCCL_DEBUG看通信死锁，CUDA_LAUNCH_BLOCKING同步定位错误，py-spy查堆栈
- 显存公式：总显存=权重+梯度+优化器+激活+KV，优化器状态占比最大
frequency: high
---

# 【智谱Infra面经】大模型训练低 MFU / OOM / hang 如何诊断？用哪些工具和指标？

**训练性能诊断三板斧：低 MFU / OOM / Hang**

**1. 低 MFU（Model FLOPs Utilization）诊断**

```
MFU = 实际 FLOPS / 峰值 FLOPS
目标: >50%（千卡集群），>60%（单机）
```

诊断流程：
1. **PyTorch Profiler** → 查看 GPU 利用率、kernel 耗时分布
2. **Nsight Systems** → 时间线分析（计算 vs 通信 vs IO 重叠情况）
3. **NCCL 日志** → All-Reduce/All-Gather 通信延迟
4. **常见原因**：
   - 通信未 overlap（计算等通信）
   - Gradient Checkpoint 重算开销
   - 数据加载瓶颈（CPU IO）
   - 小 kernel 太多（kernel launch 开销）

**2. OOM（Out of Memory）诊断**

显存组成：
```
总显存 = 模型权重 + 梯度 + 优化器状态 + 激活值 + KV Cache + 临时缓冲
  权重: P × bytes_per_param (BF16: 2P)
  梯度: P × 2 (BF16)
  优化器: P × 8 (Adam FP32 momentum+variance)
  激活值: L × batch × seq × hidden × layers
```

解决方案：
| 方案 | 节省 | 代价 |
|------|------|------|
| ZeRO-3 分片 | ~8x optimizer | 通信增加 |
| Gradient Checkpoint | ~60% 激活 | 重算开销 20% |
| CPU Offload | 灵活 | PCIe 带宽瓶颈 |
| 混合精度 BF16/FP8 | 2-4x | 精度损失 |
| Sequence Parallel | 长序列激活 | 通信增加 |

**3. Hang（训练卡死）诊断**

常见原因：
- NCCL 通信死锁（部分 GPU 崩溃）
- 数据加载卡住（NFS/网络存储慢）
- CUDA 错误（NaN/Inf 触发 device assert）
- 内存碎片（碎片化导致 alloc 失败）

诊断工具：
- `py-spy dump --pid <PID>` → 查看 Python 调用栈
- `NCCL_DEBUG=INFO` → NCCL 通信日志
- `CUDA_LAUNCH_BLOCKING=1` → 同步执行定位错误
- `nccl-tests` → 通信基准测试

**实战案例：**
训练 70B 模型时 Loss 突然变成 NaN 且卡死。开启 `CUDA_LAUNCH_BLOCKING=1` 后发现报错位置在 FlashAttention 的反向传播，排查发现是新版 NCCL + BF16 在特定通信拓扑下的数值溢出导致，回退 NCCL 版本解决。

**代码示例 (Python - Hook 定位 NaN):**
```python
import torch

# 注册 Hook 检测梯度/激活爆炸
def check_nan(module, inp, out):
    if torch.isnan(out).any():
        print(f"NaN detected in {module.__class__.__name__}")
        raise ValueError("Stop execution")

model.layer[-1].register_forward_hook(check_nan)
```

## 常见考点
1. **ZeRO-1, ZeRO-2, ZeRO-3 的切分粒度有什么区别？**（Optimizer States / Gradients / Parameters）
2. **如何区分是通信 Bound 还是计算 Bound？**（查看 Nsight Systems 的 gap，如果计算Kernel之间有长空闲等待 NCCL，则是通信未重叠）
3. **Gradient Checkpointing 为什么能节省显存？原理是什么？**（以计算换空间，前向不存所有中间激活，反向时重算）

```mermaid
flowchart TD
    classDef start fill:#4CAF50,color:#fff
    classDef process fill:#2196F3,color:#fff
    classDef decision fill:#FF9800,color:#fff
    classDef special fill:#9C27B0,color:#fff
    classDef error fill:#f44336,color:#fff
    classDef info fill:#607D8B,color:#fff
    class Checkpointing start
    class Fix process
    class Hang decision
    class Issue special
    class NCCL error
    class NCCL_DEBUG info
    class Nsight start
    class OOM process
    class Offload decision
    class Train special
    class ZeRO error
    class py info
    class spy start
    Train[训练任务] --> Issue{问题}
    Issue -->|低MFU| Nsight[Nsight看通信重叠]
    Issue -->|OOM| ZeRO[ZeRO-3/Checkpointing/Offload]
    Issue -->|Hang| NCCL[NCCL_DEBUG/py-spy]
    Nsight --> Fix[算子融合/通信Overlap]
    subgraph Legend["图例"]
        L1["🟢 开始/成功"]:::start
        L2["🔵 主流程"]:::process
        L3["🟠 判断/中间态"]:::decision
        L4["🔴 失败/结束"]:::error
    end
```


## 记忆要点

- 低MFU诊断：用Profiler看Kernel耗时，Nsight看通信重叠，常见瓶颈是通信未Overlap或数据加载慢
- OOM解决：ZeRO-3分片参数、Checkpointing换激活显存、CPU Offload卸载冷数据
- Hang诊断：开启NCCL_DEBUG看通信死锁，CUDA_LAUNCH_BLOCKING同步定位错误，py-spy查堆栈
- 显存公式：总显存=权重+梯度+优化器+激活+KV，优化器状态占比最大


## 结构化回答

**30 秒电梯演讲：** 定位MFU低效、OOM根源和死锁点以恢复训练——打个比方，像修车，看转速（MFU）、油箱（OOM）和塞车（Hang）分别修

**展开框架：**
1. **低MFU诊断** — 用Profiler看Kernel耗时，Nsight看通信重叠，常见瓶颈是通信未Overlap或数据加载慢
2. **OOM解决** — ZeRO-3分片参数、Checkpointing换激活显存、CPU Offload卸载冷数据
3. **Hang诊断** — 开启NCCL_DEBUG看通信死锁，CUDA_LAUNCH_BLOCKING同步定位错误，py-spy查堆栈

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「MFU 怎么计算？ — — 实际 tokens/s × 每 token FLOPs(6N) / GPU 峰值 FLOPS」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "【智谱Infra面经】大模型训练低 MFU / OOM / hang 如何诊断，30 秒讲清楚。" | 开场钩子 |
| 0:36 | 概念定义动画 | "一句话：定位MFU低效、OOM根源和死锁点以恢复训练" | 核心定义 |
| 1:12 | 低MFU诊断图解 | "用Profiler看Kernel耗时，Nsight看通信重叠，常见瓶颈是通信未Overlap或数据加载慢" | 低MFU诊断 |
| 1:48 | OOM解决图解 | "ZeRO-3分片参数、Checkpointing换激活显存、CPU Offload卸载冷数据" | OOM解决 |
| 2:24 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
