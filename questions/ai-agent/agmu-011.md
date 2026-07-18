---
id: agmu-011
difficulty: L1
category: ai-agent
subcategory: 多智能体系统
feynman:
  essence: 将协作结构显式化以降低 Prompt 编程的复杂度。
  analogy: 像把口头分工变成了可视化的组织架构图。
  first_principle: 如何将隐式的协作逻辑转化为可管理的显式结构？
  key_points:
  - 抽象：角色、任务、依赖为一等公民
  - 价值：结构可见可复用
  - 简化：降低Prompt负担
  - 局限：权限边界需手动把控
memory_points:
- Crew 抽象角色分工与任务依赖，降低 Prompt 心智负担。
- 支持 Sequential 顺序流和 Hierarchical 层级管理。
- Task 输出自动作为下个 Task 输入，实现上下文传递。
---

# CrewAI 的「Crew」抽象解决什么问题

CrewAI 的「Crew」抽象本质上是将 **「角色分工 + 任务依赖 + 执行顺序」** 从散乱的 Prompt 工程中抽离出来，变成一等公民。它定义了一组 Agent（角色）如何协作完成一组 Task（任务），降低了「写一大坨 system prompt」的心智负担，让协作结构可见、可复用。

**架构抽象图**：
```text
      [ Crew (Process Manager) ]
      /          |           \
   Agent1      Agent2       Agent3
   (Coder)   (Reviewer)   (Writer)
      |           |           |
      v           v           v
   Task1 <---- Task2 <---- Task3
 (Create)   (Review)    (Finalize)
      |           |           |
      └───────────┴───────────┘
                  │
           [ Sequential Process ]
           (Hierarchical also avail)
```

**关键细节补充**：
- **Process（流程）**：Crew 默认支持 `sequential`（顺序执行）和 `hierarchical`（层级管理，有一个 Manager Agent 分发任务）。
- **Task 属性**：每个 Task 可以指定 `description`（用于 LLM 理解）、`expected_output`（用于格式化输出）以及具体的 `agent`。通过 Context 机制，前一个任务的输出可以自动传递给下一个任务。
- **Tools 集成**：虽然结构化了，但工具权限还是挂载在具体的 Agent 实例上，Crew 本身不提供工具沙箱，依赖 Agent 自身的工具定义。

**实战案例**：曾在一个自动研报生成项目中使用 CrewAI，将研究员、数据分析师、写手三个 Agent 组成 Crew。踩坑点是当任务链过长时，中间 Task 输出的格式若稍有偏差（如 JSON 缺字段），下游 Agent 就会直接报错卡死，后来不得不在 Task 之间增加 Python 格式校验的「回调钩子」来清洗数据。

**代码示例**：
```python
from crewai import Agent, Task, Crew, Process

# 定义角色与工具绑定
researcher = Agent(
    role='Research Analyst',
    goal='Discover trending tech',
    tools=[search_tool, serper_dev_tool], # 绑定搜索工具
    llm='gpt-4'
)

# 定义任务上下文传递
task1 = Task(description='Search AI news', expected_output='Bullet points', agent=researcher)
task2 = Task(description='Write summary based on {task1.output}', agent=writer)

# 启动层级流程
crew = Crew(agents=[researcher, writer], tasks=[task1, task2], process=Process.hierarchical)
result = crew.kickoff()
```

**流程模式对比**：

| 特性 | Sequential (顺序) | Hierarchical (层级) |
| :--- | :--- | :--- |
| **执行逻辑** | 线性执行，Task 按列表顺序串行 | Manager Agent 动态规划并分发任务 |
| **并行能力** | 无 (强依赖顺序) | 理论支持并行分发 (受限于 Manager) |
| **适用场景** | 简单流水线、依赖明确的链条 | 复杂任务分解、需要动态决策的场景 |
| **成本消耗** | 较低 (固定次数 LLM 调用) | 较高 (Manager 持续参与规划) |

**追问应对**：若问缺点？答：抽象与真实权限/数据边界仍需自己把控；复杂分支可能要下沉到代码，Crew 的流程编排能力相比 LangGraph 的图结构较弱。

## 常见考点
1. **进程模式**：`Sequential` 和 `Hierarchical` 的适用场景？（答：简单流水线用 Sequential，需要动态调度或复杂分解用 Hierarchical）。
2. **内存共享**：不同 Agent 之间如何共享上下文？（答：主要通过 Task 的输出作为下一个 Task 的输入，或者共享短期记忆）。
3. **执行机制**：CrewAI 是并行的吗？（答：默认 Sequential 是串行的，Hierarchical 中 Manager 可以并发派发，但需注意 LLM API 调用的并发限制）。

## 核心知识点图

<img src="/interview-2026/images/diagram_ai-agent_agmu-011.svg" alt="CrewAI 的「Crew」抽象解决什么问题 - 核心知识点图" style="max-width:100%;height:auto;border:1px solid var(--border);border-radius:8px;margin:1em 0;" />

## 记忆要点

- Crew 抽象角色分工与任务依赖，降低 Prompt 心智负担。
- 支持 Sequential 顺序流和 Hierarchical 层级管理。
- Task 输出自动作为下个 Task 输入，实现上下文传递。


## 结构化回答

**30 秒电梯演讲：** Crew 抽象把"角色分工+任务依赖+执行顺序"从散乱 Prompt 工程中抽离成一等公民，像把口头分工变成可视化组织架构图。降低写一大坨 system prompt 的心智负担，让协作结构可见可复用。支持 Sequential 顺序流和 Hierarchical 层级管理，Task 输出自动作为下个 Task 输入。缺点是权限边界需自己把控，复杂分支编排能力弱于 LangGraph。

**展开框架：**
1. **核心抽象** — Agent（角色）、Task（任务）、Crew（管理器）三件套；Task 可指定 description、expected_output、agent，通过 Context 机制自动传递上下文。
2. **两种 Process** — Sequential 线性执行强依赖顺序适合简单流水线；Hierarchical 有 Manager Agent 动态分发任务适合复杂分解。
3. **局限与避坑** — 工具权限挂 Agent 实例上 Crew 不提供沙箱；任务链长时中间输出格式偏差会卡死下游，需加 Python 校验回调钩子。

**收尾：** 做自动研报生成时踩过坑——研究员、数据分析师、写手组 Crew，任务链长时中间 Task JSON 缺字段下游直接卡死，加了格式校验回调钩子清洗数据后解决。您想聊哪块，Sequential vs Hierarchical 选型还是上下文传递机制？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：CrewAI 的 Crew 抽象 | "像把口头分工变成了可视化的组织架构图。" | 类比开场 |
| 0:15 | 三件套抽象图 | "Agent 角色、Task 任务、Crew 管理器，三件套组合。" | 核心抽象 |
| 0:45 | 两种 Process 对比 | "Sequential 线性适合流水线，Hierarchical 层级适合复杂分解。" | 流程模式 |
| 1:10 | 上下文自动传递 | "Task 输出自动作为下个 Task 输入，Context 机制传递。" | 上下文机制 |
| 1:35 | 格式偏差卡死案例 | "实战：任务链长中间 JSON 缺字段卡死，加校验钩子解决。" | 实战教训 |
| 1:50 | 总结卡 | "记住：角色+任务+Crew 三件套，注意权限边界。下期讲 MetaGPT。" | 收尾 |
