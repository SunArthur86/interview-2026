---
id: ai-harness-s004
difficulty: L2
category: ai-harness
subcategory: 推理优化
images:
- svg_quantization.svg
feynman:
  essence: 根据吞吐、延迟和硬件资源匹配最优推理框架。
  analogy: 跑车拉货选卡车(TensorRT)，买菜选代步车，不想买车就打车。
  first_principle: 如何在不同的硬件环境和业务需求下，选择成本最低且体验最好的模型运行方式？
  key_points:
  - 生产环境高吞吐首选vLLM，追求极致性能选TensorRT-LLM
  - 个人和边缘设备轻量化部署推荐Ollama或llama.cpp
  - API方案适合无算力需求的快速接入
  - 部署需权衡显存容量、并发量和响应延迟
memory_points:
- KV Cache是显存大头，可达总显存80%以上。
- PagedAttention：类OS虚拟内存分页，消除内部碎片，按需分配。
- GQA/MQA：减少KV头数，推理侧透明(Llama3用8个KV头vs32个Q头)。
- 量化收益：FP16→INT8省50%，→INT4省75%(需配SmoothQuant)。
- 易错点：KV越大≠效果越好；Prefix Caching共享率低反成负担。
---

# 大模型部署有哪些方案？

KV Cache是LLM推理的主要显存开销（可达总显存的80%+）：

1. **PagedAttention**：
- 分块管理KV Cache
- 消除内部碎片
- 按需分配

2. **GQA/MQA**：
- 减少KV的头数
- MQA极端减少（1个KV头）
- GQA折中（如Llama3-8B用8个KV头vs32个Q头）

3. **KV Cache量化**：
- FP16 → INT8：减少50%内存
- KV Cache INT4量化：减少75%

4. **Sliding Window Attention**：
- 只保留最近W个token的KV Cache
- 超出窗口的丢弃（如Mistral用4096窗口）

5. **KV Cache Offloading**：
- 将不活跃的KV Cache移到CPU内存
- 需要时再加载回GPU

6. **Prefix Sharing**：
- 多请求共享相同system prompt的KV Cache

- **补充：量化与精度权衡**
- **静态量化**: 校准集确定量化参数，部署简单。
- **动态量化**: 运行时计算量化参数，精度略高但计算开销增加。
- **INT4 KV 陷阱**: 极低比特可能导致注意力计算出现显著的精度损失，通常需要配合 SmoothQuant 或类似的激活值平滑技术。

- **KV Cache 数据流示意图**

```text
输入 Token (T_i)
   │
   ▼
┌──────────────┐
│  QKV Projection │
└───┬──────┬────┘
    │      │
    │      ▼
    │  [Store K_i, V_i] ────> KV Cache (Memory)
    │      ▲
    │      │ (Load History K_0...K_{i-1})
    │      │
    ▼      │
┌──────────────┐
│ Attention Calc │ (Score = Q * K^T)
└──────────────┘
```

### 实战案例
在 128K 长文本推理中，使用 FP16 存储 KV Cache 导致 80GB 显存仅能容纳 2 个并发请求。通过开启 vLLM 的 **INT8 KV Cache** 并结合 **GQA**（若模型支持），显存占用降低约 60%，成功将并发数提升至 6 个，且 Perplexity 几乎无损失。

### KV Cache 优化技术对比
| 优化技术 | 核心机制 | 显存节省 | 性能影响 | 实施难度 | 适用场景 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **PagedAttention** | 类似操作系统虚拟内存分页 | 消除内部碎片 | 增加少许管理开销 | 高（需修改内核） | 高并发、变长请求 |
| **GQA/MQA** | 多个 Query 头共享一组 KV | 高 (取决于分组比) | 减少内存带宽瓶颈 | 低（推理侧透明） | Llama3, Mistral 等现代模型 |
| **INT4/INT8 量化** | 降低 KV 数据类型位宽 | 高 (50%-75%) | 可能增加 Dequantize 开销 | 中（需校准） | 显存极度受限场景 |
| **Sliding Window** | 仅保留窗口内 KV | 极高 (固定上限) | 长距离上下文丢失 | 低 | 生成任务、局部依赖强 |
| **Prefix Caching** | 共享 System Prompt KV | 间接节省 | 加速 TTFT | 高（需框架支持） | 多轮对话、Prompt 固定 |

### 代码示例 (简单的 KV Cache 伪代码)
```python
class KVCache:
    def __init__(self, max_len, head_dim, dtype=torch.float16):
        self.k_cache = torch.zeros((max_len, head_dim), dtype=dtype, device='cuda')
        self.v_cache = torch.zeros((max_len, head_dim), dtype=dtype, device='cuda')
        self.seq_len = 0

    def update(self, k_new, v_new):
        # 简单拼接，实际中需考虑预分配内存池避免频繁 malloc
        self.k_cache[self.seq_len:self.seq_len+k_new.shape[1]] = k_new
        self.v_cache[self.seq_len:self.seq_len+v_new.shape[1]] = v_new
        self.seq_len += k_new.shape[1]
```

- **边界情况**：
  - **输入长度超过 KV Cache 预分配上限**：如果不进行扩容处理（如 vLLM 的 Block 分配失败），推理会直接报错 OOM，而非自动降级。
  - **Beam Search**：在生成多个候选分支时，KV Cache 的显存占用会随 Beam Size 线性倍增，极易导致显存爆炸。
  - **多轮对话 Context 复用**：如果系统 Prompt 极长，而用户 Query 很短，每次都重新计算 System Prompt 的 KV 会极其浪费，Prefix Caching 在此场景收益巨大。

## 面试追问
1. **追问 1**：使用 PagedAttention 固然能解决碎片化问题，但它引入了额外的 Kernel 开销和元数据管理。在 Batch Size 较小（如 < 4）的场景下，PagedAttention 可能不如连续内存分配快，你会如何做动态权衡？（引导：根据 Batch Size 或碎片率切换 Allocator）
2. **追问 2**：INT4 KV Cache 虽然节省显存，但会导致 Attention Score 计算精度下降。除了 SmoothQuant，还有什么技术可以在不恢复高精度计算的前提下缓解这个问题？（引导：Per-Token Quantization, 权重量化配合 KV 量化）

## 易错点
1. **误区**：KV Cache 越大，模型效果越好。
   **纠正**：对于某些局部依赖性强的任务，过长的 KV Cache 可能会引入噪声（Distractor Attention），反而在推理时导致注意力分散。Sliding Window 或 kv-compression 在某些情况下反而能提升效果。
2. **误区**：开启了 Prefix Caching 就一定能节省显存。
   **纠正**：Prefix Caching 共享的是物理 Block。如果请求的并发度不够高，或者 System Prompt 之间的差异导致无法完全匹配，共享率会很低，此时缓存本身占用的显存反而可能成为负担。


## 记忆要点

- KV Cache是显存大头，可达总显存80%以上。
- PagedAttention：类OS虚拟内存分页，消除内部碎片，按需分配。
- GQA/MQA：减少KV头数，推理侧透明(Llama3用8个KV头vs32个Q头)。
- 量化收益：FP16→INT8省50%，→INT4省75%(需配SmoothQuant)。
- 易错点：KV越大≠效果越好；Prefix Caching共享率低反成负担。


## 结构化回答

**30 秒电梯演讲：** 根据吞吐、延迟和硬件资源匹配最优推理框架。——打个比方，跑车拉货选卡车(TensorRT)，买菜选代步车，不想买车就打车。

**展开框架：**
1. **KV Cache** — KV Cache是显存大头，可达总显存80%以上。
2. **PagedAtt** — PagedAttention：类OS虚拟内存分页，消除内部碎片，按需分配。
3. **GQA/MQA** — 减少KV头数，推理侧透明(Llama3用8个KV头vs32个Q头)。

**收尾：** 以上三点都能配合实战聊。您想深入聊哪一块？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "大模型部署有哪些方案，30 秒讲清楚。" | 开场钩子 |
| 0:30 | 概念定义动画 | "一句话：根据吞吐、延迟和硬件资源匹配最优推理框架。" | 核心定义 |
| 1:00 | 要点图解 | "KV Cache是显存大头，可达总显存80%以上。" | 要点 |
| 1:30 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
