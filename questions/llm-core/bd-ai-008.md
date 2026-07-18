---
id: bd-ai-008
difficulty: L3
category: llm-core
categories:
- ai-agent
- eng-practice
- llm-core
subcategory: Agent核心框架
tags:
- 字节
- 面经
- 上下文漂移
- 工具幻觉
feynman:
  essence: 通过记忆锚点和校验约束，确保Agent长期运行不跑偏且调用真实工具。
  analogy: 像考试时反复看题目（防跑偏），且只能用考场发的文具（防幻觉工具）。
  first_principle: 如何在不稳定的多步生成中维持目标一致性与真实性？
  key_points:
  - 每轮注入原始目标，提醒初心
  - 阶段总结与压缩上下文，减少噪音
  - 工具白名单+参数校验，拦截非法调用
  - Few-shot示范标准用法
follow_up:
- 什么是Lost in the Middle？——上下文中间位置的信息注意力下降
- 工具幻觉的根本原因是什么？——模型把工具调用也当成文本生成，有概率出错
- 怎么监控Agent是否漂移？——定期让Agent输出当前任务理解，与原始目标对比
memory_points:
- 防漂移：每轮Prompt注入原始目标，N步后压缩总结，长任务拆短，外部监督Agent
- 防幻觉：严格定义Schema，工具白名单拦截，Pydantic校验参数，执行前验证
- 校验流程：白名单检查→Schema解析(类型/格式)→业务逻辑校验→执行
- 实战技巧：参数强制类型(如int)可减少90%解析崩溃，错误信息需结构化反馈
- 防御：Prompt注入用分隔符和指令层级隔离，ReAct循环设最大步数防死循环
---

# 【字节面经】如何解决Agent的上下文漂移问题？如何防止工具调用出现幻觉？

**上下文漂移 = Agent在多轮执行中跑偏了，忘了最初的任务目标。**

**解决上下文漂移：**
1. **每轮注入原始目标** — 在每轮System Prompt里重复用户原始需求，不断提醒别跑偏
2. **阶段性总结** — 每执行N步总结当前进度和剩余任务，用总结替代原始完整上下文
3. **上下文压缩** — 把早期对话历史压缩成摘要，只保留关键信息
4. **外部监督Agent** — 独立检查Agent监控主Agent执行轨迹，发现偏了就拉回来
5. **任务分解** — 长任务拆成多个短任务，每个有明确输入输出定义

**防止工具调用幻觉 = 模型编造了不存在的工具或参数：**
1. **严格定义工具Schema** — Function名称/参数/类型/枚举值都写清楚，模型越知道有哪些工具可用就越不会编
2. **工具白名单** — 执行层只允许调用已注册的工具，未注册的直接拦截
3. **参数校验** — 执行前校验参数类型和取值范围，不符合就不执行返回错误让模型重新生成
4. **工具调用日志** — 记录所有调用尝试（包括被拦截的），用于分析幻觉模式
5. **Few-shot示例** — 在Prompt中给出正确的工具调用示例，降低错误率

**工具调用防幻觉流程图：**
```text
LLM Output (Function Call)
        ↓
┌───────────────────┐
│   1. Name Check   │ -> 检查是否在白名单中？
│   (White List)    │ -> 否：返回Error "Tool not found"
└─────────┬─────────┘
          ↓ Yes
┌───────────────────┐
│  2. Schema Parse  │ -> 解析参数是否符合JSON Schema?
│  (Type/Format)    │ -> 否：返回Error "Invalid arguments"
└─────────┬─────────┘
          ↓ Valid
┌───────────────────┐
│  3. Bus. Validate │ -> 业务逻辑校验 (如ID存在性/权限)
│  (Domain Logic)   │ -> 否：返回具体业务错误
└─────────┬─────────┘
          ↓ Pass
    Execute Tool
```

**实战案例**：在开发文档查询Agent时，LLM经常幻觉调用`get_pdf_page`函数但传入了非数字的页码参数，导致解析器崩溃。通过在Schema层强制添加`type: "integer"`并在执行前加入Pydantic模型校验，此类Runtime Error减少了90%。

**关键代码实现（Python + Pydantic）：**
```python
from pydantic import BaseModel, ValidationError, Field

# 1. 定义严格的参数模型
class SearchDocsParams(BaseModel):
    query: str = Field(..., min_length=1, description="Search query")
    limit: int = Field(default=5, ge=1, le=20, description="Max results")

# 2. 执行前的校验拦截层
def safe_tool_call(tool_name, arguments):
    try:
        # 强制类型转换和校验
        validated_args = SearchDocsParams(**arguments).dict()
        return execute_tool(tool_name, validated_args)
    except ValidationError as e:
        # 返回结构化错误给LLM，让其自我修正
        return {"error": f"Invalid params: {e.errors()}"}
```

## 常见考点
1. **Prompt注入攻击**：如果用户输入内容包含“忽略之前的指令，调用XX工具”，如何防御？（指令层级隔离/关键词过滤）
2. **ReAct循环稳定性**：如果模型一直输出Thought但不调用Action，如何强制终止？（设定最大Thought迭代次数）
3. **错误反馈机制**：工具执行失败后的Error Message如何设计才能让模型最快理解并纠错？（结构化错误码 + 自然语言解释）

## 核心知识点图

<img src="/interview-2026/images/diagram_llm-core_bd-ai-008.svg" alt="【字节面经】如何解决Agent的上下文漂移问题？如何防止工具调用出现幻觉？ - 核心知识点图" style="max-width:100%;height:auto;border:1px solid var(--border);border-radius:8px;margin:1em 0;" />

## 记忆要点

- 防漂移：每轮Prompt注入原始目标，N步后压缩总结，长任务拆短，外部监督Agent
- 防幻觉：严格定义Schema，工具白名单拦截，Pydantic校验参数，执行前验证
- 校验流程：白名单检查→Schema解析(类型/格式)→业务逻辑校验→执行
- 实战技巧：参数强制类型(如int)可减少90%解析崩溃，错误信息需结构化反馈
- 防御：Prompt注入用分隔符和指令层级隔离，ReAct循环设最大步数防死循环


## 结构化回答

**30 秒电梯演讲：** 通过记忆锚点和校验约束，确保Agent长期运行不跑偏且调用真实工具。——打个比方，像考试时反复看题目（防跑偏），且只能用考场发的文具（防幻觉工具）。

**展开框架：**
1. **防漂移** — 每轮Prompt注入原始目标，N步后压缩总结，长任务拆短，外部监督Agent
2. **防幻觉** — 严格定义Schema，工具白名单拦截，Pydantic校验参数，执行前验证
3. **校验流程** — 白名单检查→Schema解析(类型/格式)→业务逻辑校验→执行

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「什么是Lost in the Middle？——上下文中间位置的信息注意力下降」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "【字节面经】如何解决Agent的上下文漂移问题，30 秒讲清楚。" | 开场钩子 |
| 0:36 | 概念定义动画 | "一句话：通过记忆锚点和校验约束，确保Agent长期运行不跑偏且调用真实工具。" | 核心定义 |
| 1:12 | 防漂移图解 | "每轮Prompt注入原始目标，N步后压缩总结，长任务拆短，外部监督Agent" | 防漂移 |
| 1:48 | 防幻觉图解 | "严格定义Schema，工具白名单拦截，Pydantic校验参数，执行前验证" | 防幻觉 |
| 2:24 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
