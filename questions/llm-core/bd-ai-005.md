---
id: bd-ai-005
difficulty: L3
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
- 最佳实践
- 踩坑
feynman:
  essence: 不盲信，强约束，重测试，防幻觉，守安全。
  analogy: 像带实习生：指令要写死，代码要复查，权限要管好。
  first_principle: 如何在利用AI效率的同时保障代码质量与安全？
  key_points:
  - AI生成的代码必须人工Review和测试
  - 用.cursorrules固化代码规范与约束
  - 提供准确文档上下文防止幻觉
  - 严禁AI处理硬编码密钥
  - 先确认业务理解再写代码
follow_up:
- 如何评估AI生成代码的质量？—— 用Code Coverage + 静态分析 + Code Review三重保障
- .cursorrules怎么写最有效？—— 分模块写：技术栈/命名规范/架构模式/禁止事项
- 团队中如何推广AI编程最佳实践？—— 建立AI代码Review Checklist + 定期分享踩坑案例
memory_points:
- 坑1：过度信任AI代码，必须写测试验证，关键路径人工审查。
- 坑2：上下文不足致幻觉API，用@docs引用文档，注明版本号。
- 坑3：代码风格不一致，用.cursorrules定义规范，统一格式。
- 坑4：长对话失忆，关键约束写进配置文件，定期重复或拆分任务。
- 黄金法则：AI是副驾驶，测试是信任基础，约束显式化，保持人类审查闭环。
frequency: low
---

# 【字节面经】AI编程中有哪些踩坑经验？分享你的最佳实践。

在深度使用AI编程工具超过6个月后，我总结了以下核心踩坑经验和最佳实践。

**坑1：过度信任AI生成的代码**
- **现象：** AI生成的代码看起来合理，但存在隐蔽Bug（如竞态条件、空指针、边界遗漏）。
- **根因：** AI擅长"语法正确"但不保证"语义正确"，尤其是业务逻辑。且模型存在"幻觉"，可能编造不存在的库方法。
- **实战案例**：在电商大促前夕，AI生成的并发扣减库存代码未处理数据库死锁重试逻辑，导致压测时服务雪崩。
- **最佳实践：**
  - AI生成后必须写测试验证，不能"看着对就用"。
  - 用`// AI generated, needs review`标记，Code Review时重点检查。
  - 对关键路径代码（支付/认证/并发），人工逐行审查。

**坑2：上下文不足导致幻觉API**
- **现象：** AI调用了不存在的函数、用了已废弃的API、import了不存在的包。
- **根因：** 训练数据有时效性，且对非主流库覆盖差。
- **实战案例**：升级Next.js版本后，AI仍频繁调用已废弃的`getInitialProps`，导致页面SSR渲染失效。
- **最佳实践：**
  - 在Cursor中用`@file`或`@docs`引用最新的API文档。
  - 对关键依赖，在CLAUDE.md/.cursorrules中注明版本号。
  - 让AI先`npm install`/`pip install`确认包存在再使用。

**坑3：AI生成的代码风格不一致**
- **现象：** 不同AI（甚至同一AI不同轮次）生成的命名风格、错误处理方式、架构模式不一致。
- **实战案例**：多轮对话中，混用了`Promise.then`链式调用和`async/await`，导致代码回调和异常处理逻辑混乱。
- **最佳实践：**
  - 在`.cursorrules`或`CLAUDE.md`中定义代码规范。
```text
# .cursorrules 示例
- 使用 TypeScript strict mode
- 错误处理用 Result<T, E> 模式，不用 try-catch
- 命名：camelCase 函数，PascalCase 类型
- 所有函数必须有 JSDoc 注释
```
  - 用Prettier/ESLint做后处理统一格式。

**坑4：长对话后AI"忘记"早期约束**
- **现象：** 30轮对话后，AI开始违反开头定义的架构规范。
- **根因：** 上下文窗口有限，早期信息被压缩或丢弃，导致注意力机制"失忆"。
- **最佳实践：**
  - 关键约束写进`.cursorrules`（每轮都会注入）。
  - 定期在对话中重复关键约束（"再次提醒：用Repository模式"）。
  - 拆分长任务为多个短会话。

**坑5：安全风险——AI泄露敏感信息**
- **现象：** AI可能会把API Key、数据库密码等写进代码或日志。
- **实战案例**：AI在生成Demo代码时，为了"方便运行"，直接将真实的数据库连接字符串硬编码在Python脚本中并提交到仓库。
- **最佳实践：**
  - 在`.cursorrules`中明确「永远不要硬编码密钥，使用环境变量」。
  - 用`.gitignore` + pre-commit hook扫描密钥泄露。
  - 敏感项目不在云端AI工具中处理。

**坑6：复杂业务逻辑AI理解偏差**
- **现象：** AI生成的业务逻辑"看起来对"但实际不满足业务需求。
- **最佳实践：**
  - 先让AI写"业务理解文档"（用自然语言复述需求），人工确认后再写代码。
  - 用BDD（行为驱动开发）——先写场景描述，再让AI实现。
  - 复杂逻辑拆解为小函数，逐个验证。

**坑7：性能优化建议的盲目采纳**
- **现象：** AI建议的"优化"可能引入更复杂的问题（如过早优化、过度抽象）。
- **最佳实践：**
  - 先profile找到真实瓶颈，再让AI优化。
  - 优化前后必须做Benchmark对比。

**AI编程的提效漏斗模型（建议流程）：**
```text
需求澄清 
     ↓
架构设计 (AI辅助 + Human决策) 
     ↓
代码生成 (AI主导) 
     ↓
单元测试 (AI生成) 
     ↓
Code Review (Human重点检查逻辑/安全) 
     ↓
集成部署 (AI编写脚本 + Human执行)
```

**总结——AI编程的黄金法则：**
1. **AI是副驾驶不是自动驾驶** — 最终决策权和责任在人。
2. **测试是信任的基础** — 没有测试的AI代码不应该进生产。
3. **约束要显式化** — 不要假设AI知道你的项目规范。
4. **拆分任务粒度** — 小而明确的任务比大而模糊的任务效果好10倍。
5. **保持人类审查闭环** — Code Review不能因为AI写了就跳过。

## 常见考点
1. **Prompt Engineering 在代码生成中的具体技巧**：如Few-Shot Prompting如何通过提供示例来规范代码风格？
2. **如何检测AI代码中的潜在安全漏洞**：除了SAST工具，如何训练AI进行自审计？

## 流程图

```mermaid
flowchart TD
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
    class D start
    class D1 process
    class E decision
    class E1 special
    class F error
    class F1 info
    class Prompt start
    class Review process
    A[AI 编程最佳实践] --> B[不盲信]
    A --> C[强约束]
    A --> D[重测试]
    A --> E[防幻觉]
    A --> F[守安全]
    B --> B1[AI 生成代码需 Review]
    C --> C1[明确 Prompt 与规范]
    D --> D1[补全单元测试]
    E --> E1[关键逻辑人工校验]
    F --> F1[敏感信息脱敏]
```

## 记忆要点

- 坑1：过度信任AI代码，必须写测试验证，关键路径人工审查。
- 坑2：上下文不足致幻觉API，用@docs引用文档，注明版本号。
- 坑3：代码风格不一致，用.cursorrules定义规范，统一格式。
- 坑4：长对话失忆，关键约束写进配置文件，定期重复或拆分任务。
- 黄金法则：AI是副驾驶，测试是信任基础，约束显式化，保持人类审查闭环。

## 结构化回答

**30 秒电梯演讲：** 不盲信，强约束，重测试，防幻觉，守安全。——打个比方，像带实习生：指令要写死，代码要复查，权限要管好。

**展开框架：**
1. **坑1** — 过度信任AI代码，必须写测试验证，关键路径人工审查。
2. **坑2** — 上下文不足致幻觉API，用@docs引用文档，注明版本号。
3. **坑3** — 代码风格不一致，用.cursorrules定义规范，统一格式。

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「如何评估AI生成代码的质量？—— 用Code Coverage + 静态分析 + Code Review三重保障」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "【字节面经】AI编程中有哪些踩坑经验，30 秒讲清楚。" | 开场钩子 |
| 0:36 | 概念定义动画 | "一句话：不盲信，强约束，重测试，防幻觉，守安全。" | 核心定义 |
| 1:12 | 坑1图解 | "过度信任AI代码，必须写测试验证，关键路径人工审查。" | 坑1 |
| 1:48 | 坑2图解 | "上下文不足致幻觉API，用@docs引用文档，注明版本号。" | 坑2 |
| 2:24 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |

### 视频流程图

```mermaid
flowchart LR

    subgraph Intro["🎥 引入"]
        N0["【字节面经】AI编程中有哪些踩坑经验<br/>0:00"]:::intro
    end

    subgraph Core["📖 核心讲解"]
        N1["不盲信，强约束，重测试，防幻觉，守安全。<br/>0:36"]:::core
        N2["坑1图解<br/>1:12"]:::deep
    end

    subgraph Practice["🔧 实战"]
        N3["坑2图解<br/>1:48"]:::practice
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


