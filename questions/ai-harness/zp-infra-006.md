---
id: zp-infra-006
difficulty: L3
category: ai-harness
subcategory: 推理优化
tags:
- 智谱
- 面经
- GQA
- KV Cache
- 注意力机制
feynman:
  essence: 通过分组共享Key/Value头减少显存并提升吞吐
  analogy: 像多个人（Q头）查阅几本参考书（KV头），不用人手一本，分组轮流看就行
  first_principle: 如何在减少KV Cache显存占用和保持注意力表达能力之间平衡？
  key_points:
  - GQA分组共享KV头，减少显存占用
  - 相比MQA，GQA保留了更多表达能力
  - 解决了推理时的显存带宽瓶颈
  - GLM-4等大模型支持超长上下文的关键
follow_up:
- GQA 的分组数怎么选？—— 通常 h/4 ~ h/8，需要实验验证
- GQA 训练时和 MHA 有什么区别？—— K/V 投影矩阵更小，其他不变
- MLA 和 GQA 有什么区别？—— MLA 是低秩压缩（动态恢复），GQA 是离散共享
memory_points:
- GQA优势：KV头数减少g倍(如8倍)，显存和带宽压力骤降，质量接近MHA远超MQA。
- 头数权衡：Q头数h不变，KV头数h/g。通过Repeat扩展KV匹配Q计算。
- 实战收益：长文本场景显存瓶颈显著缓解，吞吐提升，PPL几乎无损。
frequency: high
---

# 【智谱Infra面经】GLM-4 为什么选择 GQA？GQA vs MHA/MQA 的头数/维度权衡？KV Cache 节省多少？

**注意力机制演进：MHA → MQA → GQA**

| 机制 | Q 头数 | K/V 头数 | KV Cache | 质量 |
|------|--------|---------|----------|------|
| **MHA** | h | h | 1×（基准） | 最好 |
| **MQA** | h | 1 | h× | 差 |
| **GQA** | h | h/g（g组） | g× | 接近MHA |

**GLM-4 选择 GQA 的原因：**
1. **KV Cache 减少**：GLM-4 用 GQA（典型 4-8 组），KV Cache 减少 4-8x
2. **推理吞吐提升**：KV 读写量减少 → memory-bound 缓解 → 吞吐提升
3. **质量保持**：GQA 在 4-8 组时质量接近 MHA，远好于 MQA
4. **长上下文友好**：KV Cache 减少后，128K~1M 上下文推理可行

**KV Cache 计算示例：**
```
假设 32 层 × 32 Q头 × 128 维 × seq_len

MHA: KV Cache = 2 × 32 × 32 × 128 × seq
GQA(g=8): KV Cache = 2 × 32 × 4 × 128 × seq  (减少 8x)
MQA: KV Cache = 2 × 32 × 1 × 128 × seq      (减少 32x)
```

**为什么不用 MQA？**
- MQA 所有 Q 头共享 1 组 KV → 表达能力损失大
- GQA 是 MHA 和 MQA 的折中：分组共享既减少 KV 又保持质量
- 实验表明 GQA g=8 时几乎所有 benchmark 都接近 MHA

---

**实战案例**：
Llama-2-7B 量化推理时，显存正好卡在 24G 显存边界。通过手动修改模型配置将 MHA 转为 GQA（group_size=8），推理显存占用从 24GB 降至 18GB，成功在单卡 V100 上部署 128K 上下文，且困惑度（PPL）仅上升 0.05，几乎无损。

**代码示例（PyTorch - GQA 实现逻辑）**：
```python
import torch
import torch.nn.functional as F

def gqa_forward(q, k, v, n_rep):
    # q: [batch, seq, heads, dim]
    # k, v: [batch, seq, kv_heads, dim], kv_heads = heads / n_rep
    
    # 1. 重复 KV 头以匹配 Q 头数
    k = k.repeat_interleave(n_rep, dim=2) 
    v = v.repeat_interleave(n_rep, dim=2)
    
    # 2. 执行标准 Attention
    attn = (q @ k.transpose(-2, -1)) * (1.0 / torch.sqrt(q.size(-1)))
    attn = F.softmax(attn, dim=-1)
    output = attn @ v
    return output
```

## 常见考点
1. **GQA 在实现上如何做 Split 和 Concat？**（Q 维度不变，K/V 维度减少后通过 Repeat 扩展以匹配 Q 计算）
2. **GQA 对训练和推理速度的影响是否相同？**（主要收益在推理显存，训练速度收益相对较小，主要受限于 Memory Bound）
3. **除了减少显存，GQA 对 Attention Kernel 计算还有哪些优化点？**（减少了 HBM 读取 K/V 的次数）

```mermaid
flowchart TD
    classDef start fill:#4CAF50,color:#fff
    classDef process fill:#2196F3,color:#fff
    classDef decision fill:#FF9800,color:#fff
    classDef special fill:#9C27B0,color:#fff
    classDef error fill:#f44336,color:#fff
    classDef info fill:#607D8B,color:#fff
    class GQA start
    class K process
    class MHA decision
    class MQA special
    class Match error
    class Repeat info
    class Save start
    class br process
    class h decision
    MHA[MHA<br/>h个Q/K/V头] --> MQA[MQA<br/>h个Q头 1个KV]
    MHA --> GQA[GQA<br/>h个Q头 h/g个KV]
    GQA --> Repeat[Repeat扩展KV匹配Q]
    Repeat --> Match[计算Attention]
    Match --> Save[显存带宽节省g倍]
```

## 记忆要点

- GQA优势：KV头数减少g倍(如8倍)，显存和带宽压力骤降，质量接近MHA远超MQA。
- 头数权衡：Q头数h不变，KV头数h/g。通过Repeat扩展KV匹配Q计算。
- 实战收益：长文本场景显存瓶颈显著缓解，吞吐提升，PPL几乎无损。

## 结构化回答

**30 秒电梯演讲：** 通过分组共享Key/Value头减少显存并提升吞吐——打个比方，像多个人（Q头）查阅几本参考书（KV头），不用人手一本，分组轮流看就行

**展开框架：**
1. **GQA优势** — KV头数减少g倍(如8倍)，显存和带宽压力骤降，质量接近MHA远超MQA。
2. **头数权衡** — Q头数h不变，KV头数h/g。通过Repeat扩展KV匹配Q计算。
3. **实战收益** — 长文本场景显存瓶颈显著缓解，吞吐提升，PPL几乎无损。

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「GQA 的分组数怎么选？—— 通常 h/4 ~ h/8，需要实验验证」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "【智谱Infra面经】GLM-4 为什么选择 GQA，30 秒讲清楚。" | 开场钩子 |
| 0:36 | 概念定义动画 | "一句话：通过分组共享Key/Value头减少显存并提升吞吐" | 核心定义 |
| 1:12 | GQA优势图解 | "KV头数减少g倍(如8倍)，显存和带宽压力骤降，质量接近MHA远超MQA。" | GQA优势 |
| 1:48 | 头数权衡图解 | "Q头数h不变，KV头数h/g。通过Repeat扩展KV匹配Q计算。" | 头数权衡 |
| 2:24 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |

### 视频流程图

```mermaid
flowchart LR

    subgraph Intro["🎥 引入"]
        N0["【智谱Infra面经】GLM-4 …<br/>0:00"]:::intro
    end

    subgraph Core["📖 核心讲解"]
        N1["通过分组共享Key/Value头减少显存并提升吞<br/>0:36"]:::core
        N2["GQA优势图解<br/>1:12"]:::core
    end

    subgraph Practice["🔧 实战"]
        N3["头数权衡图解<br/>1:48"]:::practice
    end

    subgraph Wrap["🎬 收尾"]
        N4["总结回顾 & 下期预告<br/>2:24"]:::wrap
    end

    N0 --> N1 --> N2 --> N3 --> N4

    classDef intro fill:#FF9800,color:#fff
    classDef core fill:#2196F3,color:#fff
    classDef deep fill:#4CAF50,color:#fff
    classDef practice fill:#9C27B0,color:#fff
    classDef wrap fill:#607D8B,color:#fff
```


