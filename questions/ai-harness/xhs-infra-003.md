---
id: xhs-infra-003
difficulty: L4
category: ai-harness
subcategory: 训练框架
tags:
- DeepSpeed
- ZeRO
- 分布式训练
- 3D Parallelism
- 小红书
feynman:
  essence: 将模型状态（优化器、梯度、参数）切片分散存储，消除冗余。
  analogy: 把大百科全书拆成几卷，每人只保管一部分，用的时候再互相借阅。
  first_principle: 如何在数据并行中突破单卡显存限制以训练超大模型？
  key_points:
  - ZeRO-1切分优化器状态，ZeRO-2切分梯度，ZeRO-3切分参数
  - ZeRO-3通信量最大，需配合Offload或3D并行
  - 通过通信与计算重叠掩盖通信延迟
  - 代价是增加了参数获取时的All-Gather通信
follow_up:
- ZeRO-3和FSDP有什么区别？
- 3D Parallelism中DP/TP/PP如何配比？
- 如何诊断训练中的通信瓶颈？
memory_points:
- ZeRO-1：分片 Optimizer States，节省 4 倍显存，通信开销同 DP。
- ZeRO-2：增加分片 Gradients，节省 8 倍显存，通信开销略增。
- ZeRO-3：增加分片 Parameters，节省 N 倍显存，通信开销大增。
- ZeRO-3 缓解：通信计算重叠、3D 并行组合、CPU Offload、NCCL 参数调优。
---

# DeepSpeed ZeRO-1/2/3的区别是什么？ZeRO-3的通信瓶颈如何缓解？

ZeRO（Zero Redundancy Optimizer）通过分片消除数据并行中的冗余。

## 三阶段分片
| 阶段 | 分片内容 | 内存节省 | 通信开销 |
|------|---------|---------|----------|
| ZeRO-1 | Optimizer States | ~4x | =DP |
| ZeRO-2 | + Gradients | ~8x | 略增 |
| ZeRO-3 | + Parameters | ~N倍(卡数) | 大增(All-Gather) |

## ZeRO-3通信瓶颈缓解
1. **通信-计算Overlap**：NCCL stream异步通信
2. **Sequence Parallel**：减少TP通信量
3. **3D Parallelism组合**：DP+TP+PP合理配比
4. **CPU/NVME Offload**：减少显存压力
5. **NCCL环境变量调优**：NCCL_IB_DISABLE=0, NCCL_P2P_DISABLE=1

## 实际经验
- ZeRO-3 + 3D Parallel + overlap 可实现高MFU
- 小红书场景：vLLM魔改适配私有模型

### 实战案例
- **ZeRO-3 训练卡顿**：在训练 175B 参数模型时，使用 ZeRO-3 遇到了迭代时间随节点数增加不降反升的问题。排查发现是 `bucket_size` 设置过小导致通信过于频繁。增大 `gradient_clipping` 的通信 bucket 大小并启用 `offload_optimizer` 后，训练速度提升 20%。
- **Checkpoint 恢复慢**：ZeRO-3 的模型参数分布在各张卡上，保存 Checkpoint 时需要所有-to-all 通信汇聚，非常耗时。改用 DeepSpeed 的 `async_save` 和分布式 Checkpoint 后，保存时间从 15 分钟缩短至 30 秒。

### 代码示例 (Python - DeepSpeed ZeRO-3 配置)
```python
# deepspeed_config.json
{
  "train_batch_size": 192,
  "gradient_accumulation_steps": 1,
  "optimizer": {
    "type": "AdamW",
    "params": {
      "lr": 1e-4
    }
  },
  "zero_optimization": {
    "stage": 3,  // 开启 ZeRO-3
    "overlap_comm": true,  // 通信计算重叠
    "contiguous_gradients": true,
    "reduce_bucket_size": 5e8,
    "stage3_prefetch_bucket_size": 5e7,
    "stage3_param_persistence_threshold": 1e5,
    "offload_optimizer": {   // 开启 CPU Offload 节省显存
      "device": "cpu"
    }
  },
  "fp16": {
    "enabled": true
  }
}
```

### ZeRO-3 vs FSDP 选型对比
| 特性 | DeepSpeed ZeRO-3 | Megatron-LM + TP | Hugging Face FSDP |
| :--- | :--- | :--- | :--- |
| **易用性** | 高（插件式，兼容 HF） | 中（需改模型代码） | 中（HF 原生支持） |
| **显存节省** | 极致（支持 CPU/NVME Offload） | 一般（依赖模型并行切分） | 高（支持 Offload） |
| **通信模式** | All-Gather / Reduce-Scatter | All-Reduce (TP内) | All-Gather / Reduce-Scatter |
| **适用场景** | 超大规模模型单卡/多卡训练 | 推理极致性能或特定训练架构 | PyTorch 生态原生迁移 |

## 记忆要点

- ZeRO-1：分片 Optimizer States，节省 4 倍显存，通信开销同 DP。
- ZeRO-2：增加分片 Gradients，节省 8 倍显存，通信开销略增。
- ZeRO-3：增加分片 Parameters，节省 N 倍显存，通信开销大增。
- ZeRO-3 缓解：通信计算重叠、3D 并行组合、CPU Offload、NCCL 参数调优。


## 结构化回答

**30 秒电梯演讲：** 将模型状态（优化器、梯度、参数）切片分散存储，消除冗余。——打个比方，把大百科全书拆成几卷，每人只保管一部分，用的时候再互相借阅。

**展开框架：**
1. **ZeRO-1** — 分片 Optimizer States，节省 4 倍显存，通信开销同 DP。
2. **ZeRO-2** — 增加分片 Gradients，节省 8 倍显存，通信开销略增。
3. **ZeRO-3** — 增加分片 Parameters，节省 N 倍显存，通信开销大增。

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「ZeRO-3和FSDP有什么区别」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "DeepSpeed ZeRO-1/2/3的区别是什么，30 秒讲清楚。" | 开场钩子 |
| 0:40 | 概念定义动画 | "一句话：将模型状态（优化器、梯度、参数）切片分散存储，消除冗余。" | 核心定义 |
| 1:20 | ZeRO-1图解 | "分片 Optimizer States，节省 4 倍显存，通信开销同 DP。" | ZeRO-1 |
| 2:00 | ZeRO-2图解 | "增加分片 Gradients，节省 8 倍显存，通信开销略增。" | ZeRO-2 |
| 2:40 | ZeRO-3图解 | "增加分片 Parameters，节省 N 倍显存，通信开销大增。" | ZeRO-3 |
| 3:20 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
