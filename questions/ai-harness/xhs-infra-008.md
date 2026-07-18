---
id: xhs-infra-008
difficulty: L4
category: ai-harness
subcategory: 推理与部署
tags:
- 系统设计
- Serving
- 推荐系统
- LLM
- 小红书
feynman:
  essence: 分级调度与弹性异构资源组合，平衡高并发与成本。
  analogy: 像餐厅运营，大厨（大模型）做难菜，帮厨（小模型）做快餐，合理排队。
  first_principle: 如何在保证低延迟和高吞吐的前提下，最小化推理服务成本？
  key_points:
  - 动态批处理（Continuous Batching）提升吞吐
  - 请求路由实现大小模型分级处理
  - 会话亲和性复用KV Cache降低延迟
  - 利用混合异构GPU和Spot实例降低成本
follow_up:
- 模型路由器如何决策用大模型还是小模型？
- KV Cache在多轮对话中如何管理？
- 推荐场景的冷启动如何用LLM优化？
memory_points:
- 负载均衡：L7按内容/用户画像路由，长文本去高显存节点。会话亲和命中KV Cache。
- 调度优化：Continuous Batching动态剔除Padding。Prefill(算力)与Decode(带宽)分离调度。
- 成本优化：异构GPU池(A100算力/L40S带宽)。投机采样用小模型加速。前缀缓存共享Prompt。
---

# 设计一个支持百万QPS的大模型Serving系统（结合推荐场景）。如何做负载均衡和成本优化？

## 整体架构设计

```text
Client
  |
  v
+-----------------------+
|   API Gateway (L7)    | <--- 鉴权/限流/路由
+-----------+-----------+
            |
+-----------v-----------+    +-----------------------+
|   Request Router      |--->|  Load Balancer (L4)   |
| (Model/Session Logic) |    +-----------------------+
+-----------+-----------+              |
            |           +--------------v--------------+
            +----------->|   GPU Inference Cluster   |
                        | +------+   +------+   +----+||
                        | |vLLM  |   |TGI   |   |TRT-LLM||
                        | |(Paged|   |(Flash|   |(Tensor||
                        | |Attn)|   |Attn)|   |Core) ||
                        | +------+   +------+   +----+||
                        +------------------------------+
                        | KV Cache (GPU/CPUDisagg)    |
                        +------------------------------+
```

## 核心组件优化

### 1. 负载均衡与路由
- **L7 负载均衡**：
  - 基于请求内容路由：长文本 → 高显存节点；短文本 → 高吞吐节点。
  - 基于用户画像路由：VIP 用户优先独占或路由至低延迟节点。
- **会话亲和**：
  - 确保同一用户的连续请求（尤其是多轮对话）尽可能落在同一节点，直接命中 KV Cache，避免重新 Prefill。
  - 若节点负载过高，支持 KV Cache 的迁移或重建（Copy-on-write 机制）。

**实战案例**：
在推荐理由生成的场景中，高峰期尾部延迟 P99 飙升。排查发现 LB 轮询导致长 Context 请求堆积在少数节点上。改为加权最小连接数算法，并单独设立“长文本专用节点池”后，P99 降低了 40%。

### 2. 批处理与调度策略
- **Continuous Batching (vLLM/Orca)**：
  - 动态识别已完成的序列，立即插入新序列，剔除静态 Padding 的浪费。
- **迭代级调度**：
  - 不等到 Batch 中所有句子生成结束才处理下一波，而是每次迭代只处理当前未完成的 Token。
- **Prefill vs Decode 分离**：
  - 预填充阶段是 Compute Bound，解码阶段是 Memory Bound。
  - **分离架构**：将计算密集的 Prefill 卸载到专用 Compute 节点，Decode 留在 Memory 节点，最大化整体吞吐。

### 3. 成本优化
- **异构 GPU 池**：
  - A100/H100：用于 70B+ 模型或低延迟要求。
  - L40S/T4：用于 7B/13B 模型或离线生成任务。
  - **弹性伸缩**：利用 Spot 实例处理离线任务（如索引更新、Embedding 生成），降低 50%+ 成本。
- **Speculative Decoding (投机采样)**：
  - 使用小模型（如 70B 参数用 7B 做辅助）提前生成 N 个 Token，大模型并行验证。验证成功即输出，失败则回滚。
  - 加速比通常在 1.5x - 2.5x，显存几乎不增加。
- **前缀缓存**：
  - 系统提示词 或通用 Prompt 段只计算一次 KV Cache，所有请求共享。

### 4. 推荐场景特化
- **Refined Pipeline**：
  - **Rank 阶段**：传统双塔模型，CPU/GPU 快速召回。
  - **Rerank 阶段**：LLM 重排 Top-K 候选集（利用 LLM 的语义理解能力）。
- **Batch Rerank**：
  - 将多个 Item 拼接成一个 Prompt 送入 LLM，一次性重排，减少推理 Overhead。

**代码示例**：
```python
# 伪代码：推荐场景批量 Rerank Prompt 构建
def build_rerank_prompt(user_query, candidates):
    items_text = "\n".join([f"{i+1}. {item['title']}" for i, item in enumerate(candidates)])
    prompt = f"""User Query: {user_query}
Candidates:
{items_text}

Please rank the candidates by relevance to the query. Return only the sorted IDs."""
    return prompt
# 将多个 User 的 Rerank 任务拼接到一个大 Batch 中送入 vLLM
```

### 技术选型对比
| 组件 | 方案 A (vLLM) | 方案 B (TGI) | 方案 C (TRT-LLM) |
| :--- | :--- | :--- | :--- |
| **核心优势** | 开源活跃，PagedAttention 内存管理极佳，易部署 | HuggingFace 生态集成度高，Telemetry 完善 | 极致性能，利用 Tensor Core 深度优化，FP8 支持 |
| **适用场景** | 通用在线 Serving，快速迭代 | 需要模型库快速转换和监控的场景 | 对延迟极度敏感，主要使用 NVIDIA 硬件栈 |
| **调度能力** | Continuous Batching (非常成熟) | Continuous Batching (较好) | In-flight Batching (高性能) |
| **部署难度** | 低 (Python 为主) | 中 (容器化) | 高 (需编译 TensorRT 引擎) |
| **成本效益** | 高 (显存利用率高) | 中 | 极高 (吞吐量大，但开发维护成本高) |

```mermaid
flowchart TD
    Request[百万QPS请求] --> LB[L7负载均衡<br/>用户画像路由]
    LB --> Affinity[会话亲和<br/>命中KV Cache]
    Affinity --> Schedule[Continuous Batching<br/>剔除Padding]
    Schedule --> PD[Prefill/Decode分离调度]
    PD --> Hetero[异构GPU池<br/>A100算力/L40S带宽]
    Hetero --> Cost[前缀缓存+投机采样]
```


## 记忆要点

- 负载均衡：L7按内容/用户画像路由，长文本去高显存节点。会话亲和命中KV Cache。
- 调度优化：Continuous Batching动态剔除Padding。Prefill(算力)与Decode(带宽)分离调度。
- 成本优化：异构GPU池(A100算力/L40S带宽)。投机采样用小模型加速。前缀缓存共享Prompt。


## 结构化回答

**30 秒电梯演讲：** 分级调度与弹性异构资源组合，平衡高并发与成本。——打个比方，像餐厅运营，大厨（大模型）做难菜，帮厨（小模型）做快餐，合理排队。

**展开框架：**
1. **负载均衡** — L7按内容/用户画像路由，长文本去高显存节点。会话亲和命中KV Cache。
2. **调度优化** — Continuous Batching动态剔除Padding。Prefill(算力)与Decode(带宽)分离调度。
3. **成本优化** — 异构GPU池(A100算力/L40S带宽)。投机采样用小模型加速。前缀缓存共享Prompt。

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「模型路由器如何决策用大模型还是小模型」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "设计一个支持百万QPS的大模型Serving系统（结合推荐场景），30 秒讲清楚。" | 开场钩子 |
| 0:40 | 概念定义动画 | "一句话：分级调度与弹性异构资源组合，平衡高并发与成本。" | 核心定义 |
| 1:20 | 负载均衡图解 | "L7按内容/用户画像路由，长文本去高显存节点。会话亲和命中KV Cache。" | 负载均衡 |
| 2:00 | 调度优化图解 | "Continuous Batching动态剔除Padding。Prefill(算力)与Decode(带宽)分离调度。" | 调度优化 |
| 2:40 | 成本优化图解 | "异构GPU池(A100算力/L40S带宽)。投机采样用小模型加速。前缀缓存共享Prompt。" | 成本优化 |
| 3:20 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
