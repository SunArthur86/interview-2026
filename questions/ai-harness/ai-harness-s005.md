---
id: ai-harness-s005
difficulty: L3
category: ai-harness
subcategory: 推理优化
images:
- svg_kvcache.svg
feynman:
  essence: 通过分块、量化、共享和裁剪手段压缩KV Cache显存占用。
  analogy: 做笔记：只记重点(GQA)、用缩写(量化)、撕掉旧页、共用开头。
  first_principle: 如何在不显著影响模型效果的前提下，最大程度减少推理过程中的显存占用？
  key_points:
  - PagedAttention解决显存碎片和浪费问题
  - GQA/MQA通过减少KV头数大幅降低显存占用
  - 量化将FP16降至INT8/4，显著节省内存
  - 滑动窗口和Offloading进一步处理长序列低频数据
memory_points:
- 核心认知：KV Cache是LLM推理显存大头（占比超80%），优化的本质是省显存提并发。
- 显存降维打击：GQA/MQA减KV头数，INT8/INT4量化直接减半或削减75%存储。
- 系统级调度：vLLM的PagedAttention按页分配消灭碎片，Prefix Sharing复用系统提示词。
- 架构级拓展：Sliding Window限长丢弃旧Token，Offloading时间换空间卸载至CPU内存。
---

# LLM中的KV Cache如何优化？

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
        # 将新生成的 K, V 追加到缓存中
        batch_size, new_tokens, _, _ = k_new.shape
        self.k_cache[self.seq_len : self.seq_len + new_tokens] = k_new.squeeze(1)
        self.v_cache[self.seq_len : self.seq_len + new_tokens] = v_new.squeeze(1)
        self.seq_len += new_tokens
        # 返回当前全部历史用于 Attention 计算
        return self.k_cache[:self.seq_len], self.v_cache[:self.seq_len]
```

## 常见考点
1. **GQA 相比 MHA 能节省多少显存？**
   - 假设 Attention 头数为 H，GQA 的 KV 头数为 G，显存节省比例约为 $(1 - G/H)$，同时显著提升 Decode 阶段带宽利用率。
2. **KV Cache Offloading 为什么会导致性能骤降？**
   - PCIe 带宽远小于 GPU 显存带宽，每次换入换出 KV Cache 的延迟会极大拖慢 TPOT。
3. **FlashAttention 对 KV Cache 有影响吗？**
   - FlashAttention 优化的是计算过程（减少 HBM 访问），不改变 KV Cache 的存储机制，但通常与其配套使用。

## 记忆要点

- 核心认知：KV Cache是LLM推理显存大头（占比超80%），优化的本质是省显存提并发。
- 显存降维打击：GQA/MQA减KV头数，INT8/INT4量化直接减半或削减75%存储。
- 系统级调度：vLLM的PagedAttention按页分配消灭碎片，Prefix Sharing复用系统提示词。
- 架构级拓展：Sliding Window限长丢弃旧Token，Offloading时间换空间卸载至CPU内存。


## 结构化回答

**30 秒电梯演讲：** 通过分块、量化、共享和裁剪手段压缩KV Cache显存占用。——打个比方，做笔记：只记重点(GQA)、用缩写(量化)、撕掉旧页、共用开头。

**展开框架：**
1. **核心认知** — KV Cache是LLM推理显存大头（占比超80%），优化的本质是省显存提并发。
2. **显存降维打击** — GQA/MQA减KV头数，INT8/INT4量化直接减半或削减75%存储。
3. **系统级调度** — vLLM的PagedAttention按页分配消灭碎片，Prefix Sharing复用系统提示词。

**收尾：** 以上三点都能配合实战聊。您想深入聊哪一块？

## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "LLM中的KV Cache如何优化，30 秒讲清楚。" | 开场钩子 |
| 0:36 | 概念定义动画 | "一句话：通过分块、量化、共享和裁剪手段压缩KV Cache显存占用。" | 核心定义 |
| 1:12 | 核心认知图解 | "KV Cache是LLM推理显存大头（占比超80%），优化的本质是省显存提并发。" | 核心认知 |
| 1:48 | 显存降维打击图解 | "GQA/MQA减KV头数，INT8/INT4量化直接减半或削减75%存储。" | 显存降维打击 |
| 2:24 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
