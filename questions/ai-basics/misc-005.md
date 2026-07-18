---
id: misc-005
difficulty: L2
category: ai-basics
subcategory: 大模型原理
tags:
- IO
feynman:
  essence: 通过多头共享K/V矩阵,大幅缩减显存占用并提升推理速度。
  analogy: 多个人(Q)共用同一套参考书(K/V),不用每人买一套,省钱又省地方。
  first_principle: 如何在保持注意力表达能力的前提下,极大压缩KV Cache显存?
  key_points:
  - MHA:独立KV,质量好但慢
  - MQA:所有头共用一个KV,极快但伤质量
  - GQA:分组共享,兼顾速度与质量
follow_up:
- GQA的分组数如何选择?
- MQA在什么场景下值得质量折中?
memory_points:
- MHA各头独立K/V，MQA全头共享一对K/V，GQA分组共享K/V
- 权衡：K/V头越少，显存和带宽占用越小，推理越快，但表达能力略降
- 大模型选GQA：兼顾MHA的质量和MQA的速度，KV Cache减至1/G
- 注意：训练和推理架构必须一致，MHA不能直接切GQA，需Uptraining
frequency: medium
---

# MHA、MQA、GQA三者有什么区别?为什么大模型倾向用GQA

MHA、MQA、GQA三者是Key/Value在不同head间的共享策略:

| 方案 | K/V头数 | KV Cache | 质量 | 速度 |
|------|---------|----------|------|------|
| MHA | = Q头数 | 大 | 最好 | 慢 |
| MQA | 1 | **最小** | 下降 | **最快** |
| GQA | 分组共享 | 中等 | **接近MHA** | **快** |

- **核心权衡:** K/V头越少→KV Cache越小→推理越快,但质量可能下降

**补充细节：**
- **MHA (Multi-Head Attention)**: 每个头都有独立的 $W_Q, W_K, W_V$。表达能力最强，但解码时访存开销巨大，因为每个头都要加载对应的 Key/Value 向量。
- **MQA (Multi-Query Attention)**: 所有头共享同一组 $W_K, W_V$。KV Cache 仅需一份，极大减少显存占用和 HBM 带宽（带宽通常是推理瓶颈），但可能导致模型表达能力的“坍缩”。
- **GQA (Grouped-Query Attention)**: 折中方案。将 $N$ 个 Query 头分为 $G$ 组，每组共享一个 $K$ 和 $V$ 头。当 $G=1$ 时退化为 MQA，当 $G=N$ 时退化为 MHA。

**计算影响**：在推理阶段，Attention 计算受限于内存带宽。GQA 减少了读取 Key/Value 的数据量，从而显著提升推理吞吐量（TPS），而不仅仅是显存静态占用的减少。

**实战案例：**
在将 PaLM (MHA架构) 迁移到生产环境推理时，发现延迟极高。改用 **MQA/GQA** 后，虽然训练损失略有上升（需进行少量步数的 uptraining），但推理 TPS (Tokens Per Second) 提升了 3 倍以上，因为瓶颈从计算转为了显存带宽。

**代码示例 (PyTorch - GQA KV重复逻辑)：**
```python
# inputs: q [bs, seq, n_heads, d], k [bs, seq, n_kv_heads, d]
# n_kv_heads 必须能整除 n_heads

def repeat_kv(hidden_states, n_rep):
    batch, seq_len, n_kv_heads, head_dim = hidden_states.shape
    if n_rep == 1:
        return hidden_states
    return hidden_states[:, :, :, None, :].expand(batch, seq_len, n_kv_heads, n_rep, head_dim).reshape(batch, seq_len, n_kv_heads * n_rep, head_dim)
```

- **GQA (Grouped-Query Attention):**
- 将Q头分为G组,每组共享一对K/V
- 例如32个Q头分为8组,每组4个Q头共享K/V
- KV Cache减少为MHA的1/4

- **实际应用:**
- LLaMA-2 70B: GQA (8组)
- LLaMA-3: GQA
- Mistral: GQA
- GLM-4: GQA

**ASCII 结构图（Head 共享模式）：**
```
MHA (标准模式):
  Q_head1 ───┐
  Q_head2 ───┤
  Q_head3 ───┼──► Attention ──► Output
  Q_head4 ───┤      (各算各的 K/V)
              │
  K_head1 ───┤
  K_head2 ───┤
  K_head3 ───┘
  K_head4 ───┘  (V 同理)

MQA (极致共享):
  Q_head1 ───┐
  Q_head2 ───┼──► Attention ──► Output
  Q_head3 ───┤      (共用同一个 K_head)
  Q_head4 ───┘
              │
  K_shared ───┘

GQA (分组共享 - G=2):
  Q_head1 ───┐
  Q_head2 ───┼──► Attention (Group 1)
              │       (共用 K_group1)
  Q_head3 ───┼──► Attention (Group 2)
  Q_head4 ───┘       (共用 K_group2)
```

## 常见考点
1. **训练与推理一致性**：如果模型在训练时使用 MHA，推理时能否直接切换到 GQA/MQA？(不能，权重结构不同；需使用 Uptraining / Knowledge Distillation 进行对齐训练)。
2. **性能瓶颈**：为什么减少 KV Cache 能提速？(解释 Compute-bound vs Memory-bound，大模型推理通常是 Memory-bound，减少访存量比减少计算量更关键)。
3. **分组策略选择**：GQA 的分组数量 G 如何选取？(通常根据模型大小和 KV Cache 压缩率需求折中，如 40B 模型常用 G=8)。

## 核心流程图

```mermaid
flowchart TD
    Start([🚀 应用发起读请求]):::start
    App[应用层<br/>查询数据]:::client
    CacheHitQ{{缓存命中?}}:::decision
    ReturnCache["直接返回缓存数据<br/>O(1) 低延迟"]:::process
    MissDB{缓存未命中}:::decision
    QueryDB[查询数据库<br/>执行 SQL]:::process
    PenetrateQ{{是否为恶意请求?<br/>查询不存在的 key}}:::decision
    BloomFilter[布隆过滤器拦截<br/>+ 缓存空值]:::process
    BreakDownQ{{热点 key 失效?<br/>缓存击穿}}:::decision
    Mutex[加互斥锁<br/>单线程回源]:::process
    AvalancheQ{{大批 key 同时过期?<br/>缓存雪崩}}:::decision
    TTLJitter[随机 TTL<br/>+ 多级缓存]:::process
    WriteBackQ{{是否回写缓存?}}:::decision
    WriteCache[写入 Redis<br/>设置 TTL]:::process
    BigKeyCheck{{大 Key / 热 Key?}}:::decision
    SplitKey[拆分大 Key<br/>本地缓存热 Key]:::process
    DB[(MySQL 主从<br/>持久化数据)]:::store
    Cache[(Redis Cluster<br/>分片缓存)]:::store
    Final([✅ 返回结果]):::start
    Alarm[告警 + 限流降级]:::danger

    Start --> App --> CacheHitQ
    CacheHitQ -->|命中| ReturnCache --> BigKeyCheck
    BigKeyCheck -->|是| SplitKey --> Final
    BigKeyCheck -->|否| Final
    CacheHitQ -->|未命中| MissDB --> PenetrateQ
    PenetrateQ -->|是| BloomFilter --> Alarm
    PenetrateQ -->|否| BreakDownQ
    BreakDownQ -->|是| Mutex --> QueryDB
    BreakDownQ -->|否| AvalancheQ
    AvalancheQ -->|是| TTLJitter --> QueryDB
    AvalancheQ -->|否| QueryDB
    QueryDB --> DB --> WriteBackQ
    WriteBackQ -->|是| WriteCache --> Cache --> ReturnCache
    WriteBackQ -->|否| ReturnCache

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef client fill:#10b981,stroke:#047857,color:#fff;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef store fill:#8b5cf6,stroke:#6d28d9,color:#fff;
    classDef danger fill:#b91c1c,stroke:#7f1d1d,color:#fff,stroke-width:2px;

```

## 记忆要点

- MHA各头独立K/V，MQA全头共享一对K/V，GQA分组共享K/V
- 权衡：K/V头越少，显存和带宽占用越小，推理越快，但表达能力略降
- 大模型选GQA：兼顾MHA的质量和MQA的速度，KV Cache减至1/G
- 注意：训练和推理架构必须一致，MHA不能直接切GQA，需Uptraining

## 结构化回答

**30 秒电梯演讲：** MHA、MQA、GQA 是 K/V 在不同 head 间的共享策略：MHA 各头独立 K/V 质量好但慢，MQA 全头共享一对 K/V 极快但伤质量，GQA 分组共享兼顾两者。大模型倾向 GQA 因为它平衡了 MHA 的质量和 MQA 的速度，把 KV Cache 压到 1/G。

**展开框架：**
1. **三种共享策略** — MHA 各头独立 K/V（质量好显存大）、MQA 全头共享一对 K/V（极快伤质量）、GQA 分组共享（中间路线）。
2. **权衡逻辑** — K/V 头越少，显存和带宽占用越小推理越快，但表达能力略降；大模型推理是 Memory-bound，减少访存比减计算更关键。
3. **为什么选 GQA** — 兼顾 MHA 质量和 MQA 速度，KV Cache 减至 1/G；但训练推理架构必须一致，MHA 不能直接切 GQA 需 Uptraining。

**收尾：** GQA 分组数 G 通常按模型大小折中，40B 模型常用 G=8。您想深入聊 GQA 分组数怎么选，还是 MQA 在什么场景值得质量折中？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：MHA/MQA/GQA | "KV Cache 太占显存？三种共享策略压缩它，大模型都选 GQA。" | 开场钩子 |
| 0:15 | 多人共用参考书类比 | "像多人（Q）共用同一套参考书（K/V），不用每人买一套，省钱省地方。" | 核心类比 |
| 0:40 | 三种策略 K/V 头数对比图 | "MHA 各头独立，MQA 全头共享一对，GQA 分组共享。" | 三种策略 |
| 1:10 | 质量 vs 速度权衡图 | "权衡：K/V 头越少推理越快但质量降，大模型推理 Memory-bound 减访存最关键。" | 权衡逻辑 |
| 1:35 | GQA 为啥是甜点 | "GQA 兼顾 MHA 质量和 MQA 速度，KV Cache 压到 1/G，是大模型标配。" | 选型结论 |
| 1:55 | 总结卡 | "口诀：MHA 质好，MQA 极快，GQA 兼顾。下期讲分词。" | 收尾 |

### 视频流程图

```mermaid
flowchart LR

    subgraph Intro["🎥 引入"]
        N0["MHA/MQA/GQA<br/>0:00"]:::intro
    end

    subgraph Core["📖 核心讲解"]
        N1["多人共用参考书类比<br/>0:15"]:::core
        N2["三种策略 K/V 头数对比图<br/>0:40"]:::core
        N3["质量 vs 速度权衡图<br/>1:10"]:::deep
    end

    subgraph Practice["🔧 实战"]
        N4["GQA 为啥是甜点<br/>1:35"]:::practice
    end

    subgraph Wrap["🎬 收尾"]
        N5["口诀：MHA 质好，MQA 极快，GQA 兼顾。<br/>1:55"]:::wrap
    end

    N0 --> N1 --> N2 --> N3 --> N4 --> N5

    classDef intro fill:#FF9800,color:#fff
    classDef core fill:#2196F3,color:#fff
    classDef deep fill:#4CAF50,color:#fff
    classDef practice fill:#9C27B0,color:#fff
    classDef wrap fill:#607D8B,color:#fff
```


