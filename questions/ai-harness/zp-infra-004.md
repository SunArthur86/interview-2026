---
id: zp-infra-004
difficulty: L4
category: ai-harness
subcategory: 推理优化
tags:
- 智谱
- 面经
- KV Cache
- PagedAttention
- vLLM
feynman:
  essence: 通过分页管理、动态批处理和前缀复用优化显存
  analogy: 像餐厅管理桌子，有人走立刻收台（Paged），拼桌坐人（CB），同点一份菜（Prefix）
  first_principle: 如何在高并发下最小化显存占用并最大化吞吐？
  key_points:
  - PagedAttention解决内存碎片和浪费问题
  - Continuous Batching提升GPU利用率
  - 前缀复用避免重复计算相同Prompt
  - 量化（INT8/FP8）和GQA直接压缩KV体积
follow_up:
- PagedAttention 的 block size 怎么选？—— 通常 16，太小则块表开销大，太大则碎片多
- Continuous Batching 和 Static Batching 区别？—— Static 等最慢请求完成，Continuous 动态进出
- KV Cache 量化会影响精度吗？—— INT8 几乎不影响，INT4 可能损失 1-3%
memory_points:
- 诊断：显存碎片、预分配浪费(短请求占长空间)、前缀无法共享。
- 修复：PagedAttention分页管理(利用率40%→96%)，Continuous Batching动态调度。
- 其他：Radix Tree复用前缀，KV量化(FP8/INT8)，GQA减少头数。
frequency: high
---

# 【智谱Infra面经】KV Cache 导致推理成本远高于预期，如何诊断和修复？

**KV Cache 是大模型推理的核心瓶颈。**

**问题诊断：**

1. **内存碎片**
   - 传统预分配：每个请求预留 max_seq_len 的 KV 空间
   - 实际只用一部分 → 大量浪费
   - 诊断：监控 GPU 内存利用率 vs 实际 KV 使用率

2. **预分配浪费**
   - 短请求（如 50 token）却分配了 2048 token 的空间
   - 诊断：比较实际生成长度 vs 预分配长度

3. **无法共享前缀**
   - 多轮对话中相同 system prompt 的 KV Cache 重复计算
   - 诊断：分析请求的前缀重复率

**修复方案（组合使用）：**

1. **PagedAttention（vLLM 核心创新）**
   - 类似操作系统虚拟内存分页
   - KV Cache 分成固定大小 block（如 16 token/block）
   - 块表（Block Table）映射逻辑序列 → 物理块
   - 非连续存储、动态分配/释放
   - **内存利用率从 ~40% → ~96%**

2. **连续批处理**
   - 动态加入/移除请求
   - 不需要等待同一 batch 的所有请求完成
   - **吞吐提升 2-8x**

3. **Radix Tree 前缀复用**
   - 识别相同前缀的请求
   - 共享前缀部分的 KV Cache
   - 多轮对话/Agent 场景效果显著

4. **KV Cache 量化**
   - INT8/FP8 量化 KV
   - 内存减半，精度损失 <1%

5. **GQA/MQA 减少 KV 头数**
   - GLM-4 用 GQA（4-8 组）→ KV Cache 减少 4-8x

---

**实战案例**：
曾遇某内部 RAG 服务上线后 OOM，排查发现因不同用户 Prompt 长方差大（30-2000 token），传统 OrcaStaticBatching 按 4096 预分配导致 80% 显存闲置。切换至 vLLM 的 PagedAttention 后，相同显卡并发数提升 3 倍，P99 延迟降低 40%。

**代码示例（Python - PagedAttention 核心逻辑模拟）**：
```python
class BlockTable:
    def __init__(self, block_size=16):
        self.block_size = block_size
        self.free_blocks = [] # 物理显存块池
        self.logical_to_phys = {} # 逻辑seq -> 物理block映射

    def allocate(self, seq_len):
        # 计算需要的block数，向上取整
        num_blocks_needed = (seq_len + self.block_size - 1) // self.block_size
        blocks = [self.free_blocks.pop() for _ in range(num_blocks_needed)]
        return blocks
```

## 常见考点
1. **PagedAttention 中 Block Table 的维护开销在哪里？**（CPU 管理开销与 GPU 内存碎片消除的权衡）
2. **Continuous Batching 和 Static Batching 在调度策略上的本质区别？**（基于 Step vs 基于 Token 的时间片）
3. **KV Cache 量化（INT8）对推理精度的具体影响在哪些场景最明显？**（通常在长文本、复杂推理任务中）

```mermaid
flowchart TD
    classDef start fill:#4CAF50,color:#fff
    classDef process fill:#2196F3,color:#fff
    classDef decision fill:#FF9800,color:#fff
    classDef special fill:#9C27B0,color:#fff
    classDef error fill:#f44336,color:#fff
    classDef info fill:#607D8B,color:#fff
    class Diagnose start
    class GQA process
    class INT8 decision
    class Issue special
    class PA error
    class PagedAttention info
    class Quant start
    class Radix process
    class br decision
    Issue[推理成本高] --> Diagnose{诊断}
    Diagnose -->|显存碎片| PA[PagedAttention<br/>40%到96%]
    Diagnose -->|前缀无法共享| Radix[Radix Tree复用]
    Diagnose -->|带宽瓶颈| Quant[KV量化FP8/INT8]
    Diagnose -->|头数过多| GQA[GQA减少头数]
    subgraph Legend["图例"]
        L1["🟢 开始/成功"]:::start
        L2["🔵 主流程"]:::process
        L3["🟠 判断/中间态"]:::decision
        L4["🔴 失败/结束"]:::error
    end
```


## 记忆要点

- 诊断：显存碎片、预分配浪费(短请求占长空间)、前缀无法共享。
- 修复：PagedAttention分页管理(利用率40%→96%)，Continuous Batching动态调度。
- 其他：Radix Tree复用前缀，KV量化(FP8/INT8)，GQA减少头数。


## 结构化回答

**30 秒电梯演讲：** 通过分页管理、动态批处理和前缀复用优化显存——打个比方，像餐厅管理桌子，有人走立刻收台（Paged），拼桌坐人（CB），同点一份菜（Prefix）

**展开框架：**
1. **诊断** — 显存碎片、预分配浪费(短请求占长空间)、前缀无法共享。
2. **修复** — PagedAttention分页管理(利用率40%→96%)，Continuous Batching动态调度。
3. **其他** — Radix Tree复用前缀，KV量化(FP8/INT8)，GQA减少头数。

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「PagedAttention 的 block size 怎么选？—— 通常 16，太小则块表开销大，太大则碎片多」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "【智谱Infra面经】KV Cache 导致推理成本远高于预期，如何诊断和修复，30 秒讲清楚。" | 开场钩子 |
| 0:40 | 概念定义动画 | "一句话：通过分页管理、动态批处理和前缀复用优化显存" | 核心定义 |
| 1:20 | 诊断图解 | "显存碎片、预分配浪费(短请求占长空间)、前缀无法共享。" | 诊断 |
| 2:00 | 修复图解 | "PagedAttention分页管理(利用率40%→96%)，Continuous Batching动态调度。" | 修复 |
| 2:40 | 其他图解 | "Radix Tree复用前缀，KV量化(FP8/INT8)，GQA减少头数。" | 其他 |
| 3:20 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
