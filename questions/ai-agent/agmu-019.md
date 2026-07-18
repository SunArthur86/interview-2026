---
id: agmu-019
difficulty: L2
category: ai-agent
subcategory: 多智能体系统
tags:
- IO
- IOC
feynman:
  essence: 单 Agent 是工具调度器，多 Agent 是协作组织。
  analogy: 单 Agent 是瑞士军刀，多 Agent 是专家组。
  first_principle: 如何根据任务复杂度选择系统架构模式？
  key_points:
  - 单Agent：统一策略，简单工具调用
  - 多Agent：角色隔离、并行、对抗
  - 选择：任务简单用单Agent
  - 复杂：需组织流程用多Agent
memory_points:
- 单 Agent 适合简单任务，上下文连贯成本低。
- 多 Agent 适合需角色隔离、并行处理或对抗评审的复杂任务。
- 避免过度设计，简单任务勿增实体。
---

# 多 Agent 与「单 Agent + 多个工具」取舍

若任务只需统一策略按序调用不同 API，单 Agent + 工具调度即可，架构简单、上下文连贯、成本低；若任务复杂，需要角色隔离（如分别设程序员、产品经理、测试员）、并行处理（多线程执行子任务）、对抗评审（红蓝军对抗）或复杂的组织流程协作，多 Agent 架构更合适。

**架构对比**：
```text
【单 Agent + 工具模式】
┌─────────────┐
│   单 Agent  │◄────┐
│ (大脑+调度)  │     │ 上下文
└──────┬──────┘     │ 共享
       │           │
  ┌────┴────┬────┐   │
  ▼         ▼    ▼   ▼
 Tool1    Tool2 ToolN

【多 Agent 模式】
┌─────────┐  消息总线  ┌─────────┐
│ Agent A │◄────────►│ Agent B │
│(写代码)  │  (解耦/   │(测试员)  │
└─────────┘   异步)   └─────────┘
    │                       │
    ▼                       ▼
┌─────────┐            ┌─────────┐
│  Tool   │            │  Tool   │
└─────────┘            └─────────┘
```

**实战案例**：
初期构建文档生成器时使用单 Agent，它既能查 API 又能写 Markdown，但当文档篇幅超过 2000 tokens 时，它经常忘记开头定义的术语。改为多 Agent（Searcher 专注查资料，Writer 专注写作，Editor 专注校对）后，文档结构一致性提升明显，且查资料与写作可并行，耗时缩短 30%。

**代码示例**：
```python
# Pseudo-code for Multi-Agent dispatch
from typing import Literal

def dispatch_task(task_type: str) -> str:
    # 单 Agent 简单逻辑
    if task_type == "simple_query":
        return single_agent_with_tools.run(task_type)
    
    # 多 Agent 协作逻辑
    agents = {
        "coder": CodeAgent(),
        "reviewer": ReviewerAgent()
    }
    
    # 1. Coder generates code
    code_result = agents["coder"].run(task_type)
    
    # 2. Reviewer validates (并行或串行)
    review = agents["reviewer"].run(code_result)
    
    return review.final_output
```

**架构选型对比**：

| 维度 | 单 Agent + Tools | 多 Agent 系统 |
| :--- | :--- | :--- |
| **上下文连贯性** | 高 (单一 Memory) | 中 (需共享/同步 Memory) |
| **Token 成本** | 低 (一次 Prompt) | 高 (多次交互 + 解析) |
| **扩展性** | 低 (加工具需重训 Prompt) | 高 (加 Agent 无需改动现有) |
| **容错能力** | 差 (一处错全盘输) | 好 (单个 Agent 失败可重试/降级) |
| **适用场景** | FAQ、简单指令执行 | 软件开发、复杂流程审批 |

## 常见考点
1. **通信成本**：多 Agent 间消息传递会造成大量 Token 消耗，如何优化？（如消息摘要、共享记忆库）。
2. **环路控制**：多 Agent 容易陷入无限对话循环，如何设置终止条件？（如最大轮数、裁判 Agent 打分）。
3. **一致性**：多 Agent 对同一事实的理解不一致时，如何解决？（通过共享知识库或仲裁 Agent）。

## 易错点
1. **过度设计**：对于简单的“查询 + 格式化”任务引入多 Agent，导致延迟成倍增加且调试困难。应遵循“Occam's Razor”（如无必要，勿增实体）。
2. **消息传递噪声**：在多 Agent 对话中，过多冗余的寒暄或重复信息会挤占宝贵的 Context Window。应规定 Agent 间使用结构化数据（如 JSON）而非自然语言进行高效通信。

## 面试追问
1. 随着任务复杂度提升，如何动态决定是启用单 Agent 还是多 Agent？（提示：引入 Router Agent 评估任务复杂度）。
2. 在多 Agent 系统中，如何处理“慢速 Agent”拖垮整体响应速度的问题？（提示：设置超时机制、异步并行或热备份 Agent）。
3. 你提到了“角色隔离”，如何防止不同 Agent 的 Prompt 之间产生冲突或指令泄露？


## 记忆要点

- 单 Agent 适合简单任务，上下文连贯成本低。
- 多 Agent 适合需角色隔离、并行处理或对抗评审的复杂任务。
- 避免过度设计，简单任务勿增实体。


## 结构化回答

**30 秒电梯演讲：** 单 Agent 是瑞士军刀（统一策略按序调用 API），多 Agent 是专家组（角色隔离、并行处理、对抗评审）。任务只需统一策略按序调用不同 API 用单 Agent + 工具调度即可，架构简单上下文连贯成本低。需要角色隔离（程序员、PM、测试员）、并行处理、对抗评审或复杂组织流程才上多 Agent。遵循奥卡姆剃刀——如无必要勿增实体，简单任务别过度设计。

**展开框架：**
1. **单 Agent + 工具** — 统一策略按序调用 API；上下文连贯性高（单一 Memory）；Token 成本低（一次 Prompt）；扩展性低（加工具需重训 Prompt）。
2. **多 Agent 系统** — 角色隔离、并行处理、对抗评审；上下文中（需共享同步 Memory）；Token 成本高（多次交互解析）；扩展性高（加 Agent 无需改动现有）。
3. **选型与避坑** — 简单查询用单 Agent，软件开发复杂审批用多 Agent；过度设计会让延迟成倍增加调试困难；Agent 间通信用 JSON 结构化数据减少噪音。

**收尾：** 做文档生成器时踩过坑——单 Agent 超 2000 tokens 忘记开头术语，改多 Agent（Searcher 查资料、Writer 写作、Editor 校对）后结构一致性提升，查资料与写作并行耗时缩短 30%。您想聊哪块，Router Agent 动态决策还是慢速 Agent 拖垮处理？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：多 Agent vs 单 Agent+工具 | "单 Agent 是瑞士军刀，多 Agent 是专家组。" | 类比开场 |
| 0:15 | 架构对比图 | "单 Agent 统一调度工具，多 Agent 消息总线解耦协作。" | 架构对比 |
| 0:45 | 选型维度表 | "上下文连贯、Token 成本、扩展性、容错四维度对比。" | 选型维度 |
| 1:10 | 过度设计警示 | "坑：简单任务引入多 Agent 延迟成倍增加，遵循奥卡姆剃刀。" | 关键坑 |
| 1:35 | 文档生成案例 | "实战：单 Agent 忘术语，多 Agent 并行耗时缩短 30%。" | 实战收益 |
| 1:50 | 总结卡 | "记住：简单用单 Agent，复杂角色隔离才上多 Agent。" | 收尾 |
