---
id: eng-practice-s001
difficulty: L2
category: eng-practice
subcategory: 工程化实战
images:
- svg_react.svg
feynman:
  essence: 通过精准的语言指令引导大模型输出高质量结果的技巧。
  analogy: 像给新员工写SOP，不仅要告诉他做什么，还要给他看几个优秀范例，并规定好输出格式。
  first_principle: 如何通过自然语言指令最大化激发模型预训练知识的潜力并控制其输出？
  key_points:
  - 明确角色设定和任务目标
  - 提供Few-shot示例引导模型模仿
  - 使用思维链(CoT)提升复杂推理能力
  - 加入负面约束防止模型幻觉
memory_points:
- 基础技巧：角色设定、任务分解、Few-shot（示例多样性）、输出格式约束、CoT。
- 高级技巧：Self-Consistency（多数投票）、ToT（树状探索）、ReAct（推理+行动）。
- 工程实践：Prompt 模板化管理（Git），A/B 测试，结构化输出（JSON Mode/Pydantic）。
- 注意事项：CoT 适合复杂推理但增加延迟，简单任务慎用；Few-shot 样本需动态检索。
---

# LLM应用的Prompt工程有哪些最佳实践？

### 基础技巧
1. **角色设定**: '你是一个经验丰富的XX专家'
2. **任务分解**: 复杂任务拆成步骤（复杂推理任务表现提升显著）
3. **Few-shot**: 提供2-5个示例（示例多样性比数量更重要，需涵盖不同场景边界）
4. **输出格式约束**: '请以JSON格式输出，包含字段：xxx'
5. **Chain-of-Thought (CoT)**: '请一步一步思考'（注意：CoT 在简单任务上可能降低准确率并增加 Latency）
6. **负面约束**: '不要编造数据，如果不确定请说不知道'

### 高级技巧
- **Self-Consistency**: 对同一问题多次采样，对推理路径进行多数投票（适用于数学/逻辑推理，成本较高）
- **CoT-SC**: CoT + Self-Consistency 结合
- **Tree-of-Thoughts (ToT)**: 树状思维探索，允许模型回溯和自我修正（适合规划类任务）
- **ReAct**: 结合推理与行动，循环执行 Thought -> Action -> Observation

### 实际工程中
1. **模板化管理Prompt**：使用 LangChain/Jinja2 模板，纳入 Git 版本控制
2. **A/B测试不同Prompt**：基于生产流量进行离线或在线评估
3. **使用Prompt框架**：LangChain、LlamaIndex（处理 prompt 组装和记忆模块）
4. **结构化输出**：JSON Mode（强制格式）、Outlines（正则约束）、Guidance（Token级别控制）
5. **多轮对话管理**：基于 Sliding Window 或 Token Limit 动态截断，使用 Summary 累积历史信息

> **💡 实战案例**：在做结构化数据抽取时，直接要求输出JSON经常遇到字段缺失或格式错误（如注释干扰）。改用**Type Hints（类型提示）配合 Pydantic 定义**，并要求模型仅输出纯JSON字符串，解析成功率从 85% 提升至 99%。

> **🧱 代码示例（Python - 动态 Few-shot 检索）**
> ```python
> from langchain.embeddings import OpenAIEmbeddings
> from langchain.vectorstore import FAISS
>
> def get_dynamic_examples(query, example_pool, k=3):
>     # 从向量库中检索与当前Query最相似的示例
>     embeddings = OpenAIEmbeddings()
>     vectorstore = FAISS.from_texts(
>         [ex['input'] for ex in example_pool], 
>         embeddings, 
>         metadatas=example_pool
>     )
>     retrieved = vectorstore.similarity_search(query, k=k)
>     return [item.metadata for item in retrieved]
> ```

### 对比不同Prompt技术的适用性

| 技术 | 核心思想 | 适用场景 | 成本/延迟 | 实战注意事项 |
|------|----------|----------|-----------|--------------|
| Zero-shot | 直接指令 | 简单任务、格式转换 | 最低 | 指令需极度清晰，避免歧义 |
| Few-shot | 给出示例 | 模式匹配、风格模仿 | 低 | 示例必须具有代表性，避免模型过拟合示例细节 |
| CoT | 思维链 | 数学、逻辑推理、复杂QA | 中 | 简单任务慎用，模型可能“过度思考”出错 |
| ReAct | 推理+行动 | 工具调用、Agent 任务 | 高（多轮交互） | 必须限制Action步数，防止死循环 |

## 常见考点
1. **如何处理 Prompt 越界问题？**：System Prompt 和 User Prompt 的优先级是如何处理的（通常 System 优先级最高，但部分模型可通过特定 Prompt 注入覆盖）。
2. **Few-shot 学习的样本选择策略？**：如何通过 Embedding 相似度从向量库中动态检索最相关的 Examples，而不是静态写死。
3. **CoT 的局限性？**：在闭集任务中显式推理有时反而会引入噪音，如何判断何时该用 CoT。

## 流程图

```mermaid
flowchart TD
    A[用户输入 Query] --> B{任务复杂度判断}
    B -->|简单任务| C[基础Prompt: 角色设定/Few-shot]
    B -->|复杂推理| D[CoT: 逐步分解思考]
    B -->|工具调用| E[ReAct: 推理与行动循环]
    C --> F[格式约束输出: JSON/Pydantic]
    D --> G[Self-Consistency: 多次采样投票]
    E --> H[外部API/数据库环境交互]
    F --> I(结构化解析结果)
    G --> I
    H --> E
    I --> J[LangChain/Git 模板化管理]
```


## 记忆要点

- 基础技巧：角色设定、任务分解、Few-shot（示例多样性）、输出格式约束、CoT。
- 高级技巧：Self-Consistency（多数投票）、ToT（树状探索）、ReAct（推理+行动）。
- 工程实践：Prompt 模板化管理（Git），A/B 测试，结构化输出（JSON Mode/Pydantic）。
- 注意事项：CoT 适合复杂推理但增加延迟，简单任务慎用；Few-shot 样本需动态检索。


## 结构化回答

**30 秒电梯演讲：** 通过精准的语言指令引导大模型输出高质量结果的技巧。——打个比方，像给新员工写SOP，不仅要告诉他做什么，还要给他看几个优秀范例，并规定好输出格式。

**展开框架：**
1. **基础技巧** — 角色设定、任务分解、Few-shot（示例多样性）、输出格式约束、CoT。
2. **高级技巧** — Self-Consistency（多数投票）、ToT（树状探索）、ReAct（推理+行动）。
3. **工程实践** — Prompt 模板化管理（Git），A/B 测试，结构化输出（JSON Mode/Pydantic）。

**收尾：** 以上三点都能配合实战聊。您想深入聊哪一块？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "LLM应用的Prompt工程有哪些最佳实践，30 秒讲清楚。" | 开场钩子 |
| 0:30 | 概念定义动画 | "一句话：通过精准的语言指令引导大模型输出高质量结果的技巧。" | 核心定义 |
| 1:00 | 基础技巧图解 | "角色设定、任务分解、Few-shot（示例多样性）、输出格式约束、CoT。" | 基础技巧 |
| 1:30 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
