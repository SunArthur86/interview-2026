---
id: zp-infra-009
difficulty: L3
category: ai-harness
subcategory: 推理优化
tags:
- 智谱
- 面经
- vLLM
- SGLang
- 推理引擎
feynman:
  essence: PagedAttention解决显存碎片，RadixAttention解决计算冗余
  analogy: vLLM像高效图书馆管理员管理书架，SGLang像聪明的读书会自动识别共读章节
  first_principle: 如何在高并发服务中同时兼顾显存效率和计算复用？
  key_points:
  - vLLM通过PagedAttention优化显存管理
  - SGLang利用Radix Tree共享前缀计算
  - SGLang原生支持结构化输出约束
  - vLLM生态更成熟，SGLang在特定场景吞吐更高
follow_up:
- RadixAttention 和 PagedAttention 能一起用吗？—— 可以，SGLang 底层也用分页管理
- 结构化生成怎么做？ — — 在 logits 上加 mask，只允许符合约束的 token
- TGI 和 TensorRT-LLM 呢？ — — TGI（HuggingFace）注重易用性，TensorRT-LLM（NVIDIA）注重极致性能
memory_points:
- vLLM核心：PagedAttention分页管理KV，解决显存碎片，生态成熟适合通用推理
- SGLang核心：RadixAttention树状结构，自动共享前缀，适合多轮对话与Agent
- 结构化输出：SGLang原生支持Regex/JSON约束解码，vLLM通常需后处理
- 场景选择：通用单轮选vLLM，多轮/长前缀/结构化输出选SGLang
---

# 【智谱Infra面经】vLLM 和 SGLang 有什么区别？各自的优势和适用场景？

**vLLM vs SGLang 对比：**

| 维度 | vLLM | SGLang |
|------|------|--------|
| **核心创新** | PagedAttention | RadixAttention + 结构化生成 |
| **KV 管理** | 分页块表 | Radix Tree 前缀复用 |
| **批处理** | Continuous Batching | Continuous Batching + 结构化约束 |
| **多轮对话** | 前缀复用有限 | Radix Tree 自动复用（优势大） |
| **结构化输出** | 需后处理 | 原生支持（JSON/Regex/选择）|
| **吞吐** | 高（通用场景） | 更高（多轮/前缀共享场景）|
| **生态** | 更成熟，社区大 | 新兴，增长快 |

**vLLM 核心优势：**
1. **PagedAttention** — 分页管理 KV Cache，消除碎片
2. **连续批处理** — 动态进出请求，最大化 GPU 利用率
3. **广泛模型支持** — HuggingFace 模型零适配
4. **成熟生态** — 最大开源推理社区

**SGLang 核心优势：**
1. **RadixAttention** — Radix Tree 自动识别并共享相同前缀
   - 多轮对话：system prompt 的 KV 自动复用
   - Agent 场景：工具描述的 KV 复用
   - Few-shot：示例前缀复用
2. **结构化生成** — 原生 JSON/Regex 约束解码
   - 直接约束 token 采样，无需后处理
   - 比 outlines/guidance 更高效
3. **前端 DSL** — Python DSL 编排复杂生成流程

**适用场景：**
- **vLLM**：通用推理、单轮对话、API 服务
- **SGLang**：多轮对话、Agent、结构化输出、Few-shot 大量前缀共享

**实战案例：**
在同一个 System Prompt 下服务 1000 个并发用户时，vLLM 会为每个请求重复缓存相同的 KV（显存压力大），而 SGLang 利用 RadixTree 仅缓存一份，显存占用仅为 vLLM 的 20% 左右。

**代码示例 (Python - SGLang 结构化输出):**
```python
import sglang as sgl

# 定义正则约束（例如提取手机号）
regex_pattern = r"1[3-9]\d{9}"

@sgl.function
def phone_extraction(s):
    s += "Please extract the phone number: "
    s += sgl.gen("answer", regex=regex_pattern)

# 运行时强制输出符合格式的 token，无后处理重试成本
state = phone_extraction.run("Call me at 13812345678.")
```

## 常见考点
1. **Radix Tree 相比 vLLM 的 Block Manager 在前缀共享上有何本质不同？**（Block Manager 主要解决碎片，Radix Tree 逻辑上更高效地处理了树状结构的共享引用）
2. **vLLM 的 PagedAttention 在实现计算时是如何处理非连续物理 Block 的？**（通过 paged_kernel 索引映射）
3. **结构化输出的正则约束通常如何集成到 Decoding 过程中？**（通常构建一个 Finite State Machine (FSM) 动态屏蔽无效 Token）

## 记忆要点

- vLLM核心：PagedAttention分页管理KV，解决显存碎片，生态成熟适合通用推理
- SGLang核心：RadixAttention树状结构，自动共享前缀，适合多轮对话与Agent
- 结构化输出：SGLang原生支持Regex/JSON约束解码，vLLM通常需后处理
- 场景选择：通用单轮选vLLM，多轮/长前缀/结构化输出选SGLang


## 结构化回答

**30 秒电梯演讲：** PagedAttention解决显存碎片，RadixAttention解决计算冗余——打个比方，vLLM像高效图书馆管理员管理书架，SGLang像聪明的读书会自动识别共读章节

**展开框架：**
1. **vLLM核心** — PagedAttention分页管理KV，解决显存碎片，生态成熟适合通用推理
2. **SGLang核心** — RadixAttention树状结构，自动共享前缀，适合多轮对话与Agent
3. **结构化输出** — SGLang原生支持Regex/JSON约束解码，vLLM通常需后处理

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「RadixAttention 和 PagedAttention 能一起用吗？—— 可以，SGLang 底层也用分页管理」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "【智谱Infra面经】vLLM 和 SGLang 有什么区别，30 秒讲清楚。" | 开场钩子 |
| 0:36 | 概念定义动画 | "一句话：PagedAttention解决显存碎片，RadixAttention解决计算冗余" | 核心定义 |
| 1:12 | vLLM核心图解 | "PagedAttention分页管理KV，解决显存碎片，生态成熟适合通用推理" | vLLM核心 |
| 1:48 | SGLang核心图解 | "RadixAttention树状结构，自动共享前缀，适合多轮对话与Agent" | SGLang核心 |
| 2:24 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
