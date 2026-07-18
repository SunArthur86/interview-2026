---
id: bd-ai-001
difficulty: L2
category: llm-core
categories:
- ai-agent
- eng-practice
- llm-core
subcategory: AI编程
tags:
- 字节跳动
- 面经
- AI编程
- Cursor
- Copilot
- Claude Code
feynman:
  essence: Copilot 补全行，Cursor 改全库，Claude Code 自主执行任务。
  analogy: 自动纠错、改全卷、请个助教代写作业。
  first_principle: 如何利用不同的自动化层级最大化编码效率？
  key_points:
  - Copilot 适合单行补全，低延迟流式编码
  - Cursor 适合跨文件重构，具备项目级上下文
  - Claude Code 可自主执行命令和测试，处理多步任务
  - Web 端适合架构设计和非编码思考任务
follow_up:
- Copilot的补全有时会"跑偏"，怎么提高准确率？—— 用注释引导意图、保持函数签名清晰、用@引用相关文件
- Cursor的Codebase索引和纯RAG有什么区别？—— Cursor结合AST+嵌入检索，能理解import关系和调用链
- 如何评估一个AI编程工具的ROI？—— 从编码效率提升、Bug率变化、Onboarding时间缩短三个维度量化
memory_points:
- Copilot：行级/函数级补全，IDE深度集成，适合写样板代码和API调用。
- Cursor：全文件/多文件编辑，支持Codebase索引，适合重构和理解代码库。
- Claude Code：CLI Agent，自主执行命令和测试，适合环境搭建和批量修复。
- Web Chat：适合架构设计、技术选型和Debug思路探讨，思考型任务。
- 选型：补全用Copilot，重构用Cursor，自主任务用Claude Code，设计用Web。
frequency: low
---

# 【字节面经】平常用什么AI编程工具？各自的特点和使用场景是什么？

在日常开发中，我根据不同场景组合使用多种AI编程工具，核心原则是"让工具匹配场景"。

**1. GitHub Copilot — 行级/函数级补全**
- **特点：** IDE深度集成（VS Code/JetBrains），实时单行/多行补全，延迟低（<200ms），基于Codex/GPT模型
- **场景：** 写样板代码（CRUD、DTO、测试用例）、补全已知API调用、快速生成正则/SQL
- **局限：** 上下文窗口短（~2048 tokens），无法跨文件理解项目结构

**2. Cursor — 全文件/多文件编辑**
- **特点：** Fork自VS Code，内置Claude/GPT-4，支持`@file`、`@codebase`引用，Cmd+K局部重写，Cmd+L全项目对话
- **场景：** 重构跨文件逻辑、生成新模块、Code Review、理解陌生代码库
- **优势：** Codebase Indexing用嵌入检索+AST分析，能"看到"整个项目

**3. Claude Code (CLI Agent) — 自主任务执行**
- **特点：** 终端运行，能自主读写文件、执行命令、运行测试，支持多轮自主迭代
- **场景：** 批量迁移代码（如Python 2→3）、搭建项目骨架、修复CI失败、做复杂的多步骤重构

**4. ChatGPT/Claude Web — 设计讨论/方案验证**
- **场景：** 架构设计讨论、技术选型对比、写文档/PR描述、debug思路探讨
- **优势：** 不受IDE限制，适合"思考型"任务而非"编码型"任务

**5. Windsurf/Continue — 开源替代**
- **特点：** Continue可接入任意模型（本地Ollama/远程API），Windsurf强调Cascade多步编辑

**工具选型决策树：**
```
需要写代码？
├─ 单行/函数补全 → Copilot
├─ 跨文件重构 → Cursor (Cmd+K/L)
├─ 自主完成多步任务 → Claude Code
└─ 只讨论不写 → ChatGPT/Claude Web
```

**实战案例：**
- **Cursor 踩坑**：在重构一个遗留的 Java 项目时，Cursor 因为 Gradle 依赖解析失败，生成了不存在的类名引用。**解决**：先用 `@Gradle` 引入构建文件上下文，再进行重构，确保 AI 理解依赖约束。
- **Claude Code 救场**：CI 流水线因为 Python 版本升级报错几百个 Flake8 警告。使用 Claude Code 执行“自动修复所有 Flake8 警告并验证”，它在沙箱中循环修正，直到测试通过，节省了半天的手动修复时间。

**代码示例：**
```python
# Cursor 的 .cursorrules 示例（项目级编码规范）
# 当使用 Cursor 进行多文件编辑时，遵循以下规则以确保风格统一

You are a senior Python engineer.
Tech Stack: FastAPI, Pydantic v2, SQLAlchemy 2.0.
Rules:
1. Always use type hinting.
2. Use AsyncSession for DB operations.
3. Route dependencies must be validated via Pydantic.
4. No `print()` statements, use `logger.info()`.
```

**工具对比矩阵：**

| 特性 | GitHub Copilot | Cursor | Claude Code | ChatGPT Web |
| :--- | :--- | :--- | :--- | :--- |
| **核心交互** | 自动补全 | 对话 + 编辑 | 命令行 Agent | 对话 |
| **上下文感知** | 当前文件 (~50行) | 全项目 | 文件系统 | 粘贴内容 |
| **执行能力** | 无 | 仅编辑文本 | 终端/文件操作 | 无 |
| **最佳场景** | 敲代码加速 | 代码重构/理解 | 环境搭建/批量修复 | 架构设计/学习 |
| **离线性** | 部分支持 | 否 | 否 | 否 |

**实践心得：** 工具不是越多越好。日常80%时间用Cursor（编辑+对话）+ Copilot（补全），遇到复杂批量任务才启动Claude Code。关键在于建立"AI工具肌肉记忆"——每个工具的快捷键、引用语法、上下文边界都要熟练，才能在编码心流中无缝切换。

## 流程图

```mermaid
flowchart LR
    classDef start fill:#4CAF50,color:#fff
    classDef process fill:#2196F3,color:#fff
    classDef decision fill:#FF9800,color:#fff
    classDef special fill:#9C27B0,color:#fff
    classDef error fill:#f44336,color:#fff
    classDef info fill:#607D8B,color:#fff
    class A start
    class AI process
    class B decision
    class B1 special
    class C error
    class C1 info
    class Claude start
    class Code process
    class Copilot decision
    class Cursor special
    class D error
    class D1 info
    class E start
    class F process
    class G decision
    class GitHub special
    class IDE error
    A[AI 编程工具] --> B[GitHub Copilot]
    A --> C[Cursor]
    A --> D[Claude Code]
    B --> B1[行级补全 IDE 插件]
    C --> C1[全库理解 多文件改]
    D --> D1[自主代理 读写执行闭环]
    B1 --> E[适合单点辅助]
    C1 --> F[适合重构/批量改]
    D1 --> G[适合端到端任务]
```


## 记忆要点

- Copilot：行级/函数级补全，IDE深度集成，适合写样板代码和API调用。
- Cursor：全文件/多文件编辑，支持Codebase索引，适合重构和理解代码库。
- Claude Code：CLI Agent，自主执行命令和测试，适合环境搭建和批量修复。
- Web Chat：适合架构设计、技术选型和Debug思路探讨，思考型任务。
- 选型：补全用Copilot，重构用Cursor，自主任务用Claude Code，设计用Web。


## 结构化回答

**30 秒电梯演讲：** Copilot 补全行，Cursor 改全库，Claude Code 自主执行任务。——打个比方，自动纠错、改全卷、请个助教代写作业。

**展开框架：**
1. **Copilot** — 行级/函数级补全，IDE深度集成，适合写样板代码和API调用。
2. **Cursor** — 全文件/多文件编辑，支持Codebase索引，适合重构和理解代码库。
3. **Claude C** — Claude Code：CLI Agent，自主执行命令和测试，适合环境搭建和批量修复。

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「Copilot的补全有时会"跑偏"，怎么提高准确率？—— 用注释引导意图、保持函数签名清晰、用@引用相关文件」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "【字节面经】平常用什么AI编程工具，30 秒讲清楚。" | 开场钩子 |
| 0:30 | 概念定义动画 | "一句话：Copilot 补全行，Cursor 改全库，Claude Code 自主执行任务。" | 核心定义 |
| 1:00 | Copilot图解 | "行级/函数级补全，IDE深度集成，适合写样板代码和API调用。" | Copilot |
| 1:30 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
