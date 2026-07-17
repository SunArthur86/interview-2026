---
id: bd-ai-004
difficulty: L4
category: llm-core
categories:
- ai-agent
- eng-practice
- llm-core
subcategory: AI编程
tags:
- 字节跳动
- 面经
- Agent框架
- OpenClaw
- Hermes
- Claude Code
- 上下文管理
feynman:
  essence: Claude Code重集成易用，Hermes重技能封装，OpenClaw重可定制审计。
  analogy: 像办公软件：Claude是Mac（生态好开箱用），Hermes是瑞士军刀（功能全），OpenClaw是工作站（可折腾）。
  first_principle: 如何在有限的上下文窗口内高效管理记忆与工具？
  key_points:
  - Claude Code：自动压缩上下文，MCP集成最深
  - Hermes：结构化记忆与Skill能力包
  - OpenClaw：事件溯源，Plugin灵活
  - 编程选Claude，复杂业务流程选Hermes
follow_up:
- Agent的上下文压缩会丢失信息，怎么缓解？—— 用结构化记忆（如Hermes的memories/）保存关键事实，不依赖对话窗口
- 多Agent系统如何共享记忆？—— 用共享Memory Store（如向量数据库）或MCP Memory Server
- Claude Code的自动摘要质量如何保证？—— 用专门的summarization prompt + 保留关键代码块和决策点
memory_points:
- 记忆：Claude Code自动摘要压缩，Hermes结构化JSON记忆，OpenClaw事件溯源。
- 工具：Claude Code MCP集成最深，Hermes Skill编排最强，OpenClaw Plugin最灵活。
- 上下文：Claude Code自动去重压缩，Hermes检索注入，OpenClaw全量日志。
- 差异：Claude Code无缝但细节丢失，Hermes精确检索适合回溯，OpenClaw适合审计。
- 策略：长任务需注意上下文窗口限制，利用Resume或Profile隔离管理会话。
---

# 【字节面经】对比OpenClaw/Hermes/Claude Code等Agent框架，从记忆机制、工具调用、上下文管理三个维度分析。

以下从三个核心维度深度对比当前主流的Agent框架。这里的"OpenClaw"指的是开源通用Agent框架（如OpenHands/类似项目），Hermes是Nous Research的Agent框架，Claude Code是Anthropic的CLI Agent。

**维度一：记忆机制**

| 框架 | 短期记忆 | 长期记忆 | 跨会话记忆 | 存储介质 |
|------|---------|---------|-----------|----------|
| Claude Code | 对话窗口 + 自动摘要压缩 | CLAUDE.md（项目级） | --resume 恢复会话 | 本地文件系统 |
| Hermes | 对话窗口 + Skills记忆体 | Memories目录（JSON持久化） | Profile隔离的多Profile记忆 | JSON/向量DB |
| OpenClaw | 对话窗口 + 事件流 | Workspace状态持久化 | 可选向量数据库集成 | Docker/沙箱 FS |

**关键差异：**
- **Claude Code** 采用"对话窗口+自动压缩"——超过上下文窗口时自动对早期对话做摘要，保留最近N轮原文。优点是无缝，缺点是早期细节可能丢失。压缩算法通常基于LLM自身的Summary能力，关键参数是`--max-tokens`阈值。
- **Hermes** 采用"结构化记忆"——把重要事实存为memories/*.json，可以精确检索和修改。适合需要精确回溯的场景。支持语义检索，记忆体包含`content`, `importance_score`, `timestamp`等元数据。
- **OpenClaw** 采用"事件溯源"——记录所有Action/Observation对，可以replay。适合需要审计和debug的场景。其工作区状态（如文件修改）是记忆的一部分，通过Docker Volume持久化。

**维度二：工具调用**

| 框架 | 工具定义方式 | 工具发现 | 并行调用 | 安全沙箱 |
|------|------------|---------|---------|----------|
| Claude Code | 内置Shell/FS + MCP Client | MCP Server自动发现 | 支持 | 本地权限受限 |
| Hermes | Tools + Skills + MCP | 配置文件声明 + MCP | 支持 | 依赖运行环境 |
| OpenClaw | Plugin系统 | 注册式 | 有限支持 | Docker强隔离 |

**关键差异：**
- **Claude Code** 的MCP集成最深——启动时自动加载~/.claude/下的MCP配置，工具发现是零配置的。Tool调用通过stdio流传输，支持Tool Timeout设置。
- **Hermes** 的Skill系统最强——Skill=Prompt+工具+流程+记忆体，是最完整的能力封装。一个Skill可以包含多个子工具的编排逻辑。
- **OpenClaw** 的Plugin最灵活——支持热加载，但配置较复杂。其通过Runtime动态加载代码，危险操作（如`rm -rf`）通常在容器内执行以保护宿主机。

**维度三：上下文管理**

| 框架 | 窗口策略 | 上下文注入 | 分支/并行 | Token利用率 |
|------|---------|-----------|----------|------------|
| Claude Code | 自动摘要压缩 | CLAUDE.md + 文件引用 | --resume多会话 | 高（自动去重） |
| Hermes | Token计数 + 智能裁剪 | Skills注入 + Memories检索 | Profile隔离 | 中（检索开销）|
| OpenClaw | 可配置窗口管理 | Workspace注入 | Agent分支 | 低（全量日志）|

**上下文管理深度分析：**

Claude Code的上下文压缩策略：
```text
原始对话: [msg1, msg2, ..., msg50]  # 超出窗口 (假设Limit=200k)
压缩后:   [summary(msg1-30), msg31, ..., msg50]
          └── 摘要替代原文(消耗Token少) ──┘  └── 保留近期原文(高保真) ──┘
```

Hermes的上下文注入策略：
```text
系统Prompt = 固定指令
          + Skills定义（按需注入相关Skills的Prompt部分）
          + 检索到的Memories (Top-K)
          + 用户Query
```

OpenClaw的上下文策略：
```text
Context = User Prompt 
        + Recent N Events (Event Sourcing)
        + Workspace State Snapshot (Diff)
```

**实战案例：**
- **Hermes 记忆失效**：在处理长文档分析任务时，Hermes 的向量检索将不相关的旧记忆注入到了 Context 中，导致模型产生幻觉。**解决**：调整了 Memories 的 `importance_score` 衰减算法，并限制单次 Session 注入的 Memory 数量不超过 3 条。

**代码示例：**
```python
# 模拟 Hermes 风格的动态上下文构建
def build_context(query: str, session_id: str):
    # 1. 检索长期记忆
    memories = vector_db.search(query, top_k=3)
    
    # 2. 获取短期对话历史 (Token预算管理)
    history = session_store.get_history(session_id)
    history = trim_by_tokens(history, max_tokens=4000) 
    
    # 3. 动态注入 Skill Prompt
    active_skill = detect_skill(query)
    skill_prompt = skill_registry.get(active_skill).template
    
    return {
        "system": f"{BASE_SYS}\n{skill_prompt}",
        "memories": "\n".join([m.text for m in memories]),
        "history": history
    }
```

## 记忆要点

- 记忆：Claude Code自动摘要压缩，Hermes结构化JSON记忆，OpenClaw事件溯源。
- 工具：Claude Code MCP集成最深，Hermes Skill编排最强，OpenClaw Plugin最灵活。
- 上下文：Claude Code自动去重压缩，Hermes检索注入，OpenClaw全量日志。
- 差异：Claude Code无缝但细节丢失，Hermes精确检索适合回溯，OpenClaw适合审计。
- 策略：长任务需注意上下文窗口限制，利用Resume或Profile隔离管理会话。


## 结构化回答

**30 秒电梯演讲：** Claude Code重集成易用，Hermes重技能封装，OpenClaw重可定制审计。——打个比方，像办公软件：Claude是Mac（生态好开箱用），Hermes是瑞士军刀（功能全），OpenClaw是工作站（可折腾）。

**展开框架：**
1. **记忆** — Claude Code自动摘要压缩，Hermes结构化JSON记忆，OpenClaw事件溯源。
2. **工具** — Claude Code MCP集成最深，Hermes Skill编排最强，OpenClaw Plugin最灵活。
3. **上下文** — Claude Code自动去重压缩，Hermes检索注入，OpenClaw全量日志。

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「Agent的上下文压缩会丢失信息，怎么缓解？—— 用结构化记忆（如Hermes的memories/）保存关键事实，不依赖对话窗口」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "【字节面经】对比OpenClaw/Hermes/Claude Code等Agen，30 秒讲清楚。" | 开场钩子 |
| 0:40 | 概念定义动画 | "一句话：Claude Code重集成易用，Hermes重技能封装，OpenClaw重可定制审计。" | 核心定义 |
| 1:20 | 记忆图解 | "Claude Code自动摘要压缩，Hermes结构化JSON记忆，OpenClaw事件溯源。" | 记忆 |
| 2:00 | 工具图解 | "Claude Code MCP集成最深，Hermes Skill编排最强，OpenClaw Plugin最灵活。" | 工具 |
| 2:40 | 上下文图解 | "Claude Code自动去重压缩，Hermes检索注入，OpenClaw全量日志。" | 上下文 |
| 3:20 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
