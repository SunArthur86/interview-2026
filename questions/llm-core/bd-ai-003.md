---
id: bd-ai-003
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
- MCP
- Skills
- Tools
- Function Calling
feynman:
  essence: 三层抽象：Tools是原子函数，MCP是连接协议，Skills是业务封装。
  analogy: 像玩乐高：Tools是积木块，MCP是积木接口标准，Skills是拼好的模型。
  first_principle: 如何高效标准化地连接大模型与外部数据/工具？
  key_points:
  - Tools是函数定义，是基础
  - Skills是工具+流程的封装，解决业务复用
  - MCP是通信协议，解耦Agent与Server
  - 自建服务推荐MCP以兼容生态
follow_up:
- MCP和传统的API有什么区别？—— MCP是专为LLM设计的协议，包含语义描述和上下文管理，API只管数据传输
- 一个MCP Server怎么开发？—— 用TypeScript/Python SDK，实现tools/resources/prompts三个handler，stdio或SSE传输
- Skill能跨Agent平台使用吗？—— 目前不行，各平台Skill格式不同，MCP正在尝试标准化Skill层
memory_points:
- Tools：原子函数，JSON Schema定义，抽象层级最低，粒度细管理开销大。
- Skills：高阶能力包，封装Prompt+工具链+流程，可复用可分享，抽象层级最高。
- MCP：标准化传输协议，解耦Agent和工具，一次开发多端接入，抽象层级居中。
- 关系：Skills编排Tools，MCP传输Tools/数据，实现真正的插件化。
- 选型：简单调用用Tools，复用能力用Skills，通用服务接入选MCP。
---

# 【字节面经】Skills、Tools、MCP三者的区别是什么？如果自己实现工具服务，选哪种方案？

- **Skills、Tools、MCP 三者区别与选型**

这三个概念是当前AI Agent生态中最核心的工具能力抽象，但经常被混淆。以下从定义、抽象层级、适用场景三个维度深度拆解。

**1. Tools（工具/Function Calling）**
- **定义：** Agent可直接调用的原子函数，通过JSON Schema声明参数
- **抽象层级：** 最低层——一个函数定义就是一个Tool
- **标准：** OpenAI Function Calling、Anthropic Tool Use
```python
# Tool 定义示例
tools = [{
    "name": "get_weather",
    "description": "获取指定城市的天气",
    "input_schema": {
        "type": "object",
        "properties": {
            "city": {"type": "string"}
        },
        "required": ["city"]
    }
}]
```
- **特点：** 每次调用需要LLM推理选择工具+参数，粒度细，灵活但管理开销大

**2. Skills（技能）**
- **定义：** 封装了Prompt模板+工具链+执行流程的高阶能力包
- **抽象层级：** 最高层——一个Skill可能内部编排多个Tools
- **代表：** Claude Code Skills、Hermes Skills、Semantic Kernel
```
# Skill = Prompt模板 + 工具编排 + 约束
Skill: "代码审查"
  Prompt: "审查以下代码的安全性、性能、可读性..."
  Tools: [read_file, search_code, run_linter]
  Flow: 读代码 → 静态分析 → 生成报告
```
- **特点：** 可复用、可分享、可组合，面向"能力"而非"函数"

**3. MCP (Model Context Protocol)**
- **定义：** Anthropic提出的开放协议，标准化Agent与外部数据/工具服务之间的通信
- **抽象层级：** 中间层——是"传输协议+服务发现"标准
- **核心能力：** Tools（工具调用）、Resources（数据读取）、Prompts（提示模板）
- **特点：** 解耦Agent和工具——一次开发MCP Server，所有支持MCP的Agent都能用

**实战案例：**
- **MCP 踩坑**：初期开发一个 PostgreSQL 查询工具时，直接裸写 Function Calling，发现每次 Prompt 变动都需要重新部署模型服务。改用 MCP Server 后，只需升级本地 Server 端，所有接入的 Agent（如 Claude Desktop, Cursor）自动获得新功能，实现了真正的“插件化”解耦。

**代码示例：**
```python
# 实现一个简单的 MCP Server (使用 mcp-python-sdk)
from mcp.server import Server
from mcp.types import Tool, TextContent

app = Server("my-server")

@app.tool(
    name="get_system_status",
    description="Get current server health status"
)
async def handle_get_status() -> list[TextContent]:
    # 业务逻辑：调用监控系统API
    status = monitoring_api.check_health()
    return [TextContent(type="text", text=f"Status: {status}")]
```

**三者架构关系图：**
```text

  ┌───────────────────────────────────────────────────────────────┐
  │                     Skills (技能编排层)                         │
  │             (Prompt Template + Workflow + Logic)               │
  └─────────────────────────────┬─────────────────────────────────┘
                                │
                                │ 依赖 / 编排
                                ▼
  ┌───────────────────────────────────────────────────────────────┐
  │            MCP Protocol (标准化传输/发现协议)                   │
  │         (JSON-RPC / stdio / SSE over local/network)            │
  └───────┬───────────────────────────────────────────┬───────────┘
          │                                           │
    ┌─────▼─────┐                               ┌─────▼─────┐
    │ MCP Host  │                               │ MCP Host  │
    │ (Client)  │


## 记忆要点

- Tools：原子函数，JSON Schema定义，抽象层级最低，粒度细管理开销大。
- Skills：高阶能力包，封装Prompt+工具链+流程，可复用可分享，抽象层级最高。
- MCP：标准化传输协议，解耦Agent和工具，一次开发多端接入，抽象层级居中。
- 关系：Skills编排Tools，MCP传输Tools/数据，实现真正的插件化。
- 选型：简单调用用Tools，复用能力用Skills，通用服务接入选MCP。


## 结构化回答

**30 秒电梯演讲：** 三层抽象：Tools是原子函数，MCP是连接协议，Skills是业务封装。——打个比方，像玩乐高：Tools是积木块，MCP是积木接口标准，Skills是拼好的模型。

**展开框架：**
1. **Tools** — 原子函数，JSON Schema定义，抽象层级最低，粒度细管理开销大。
2. **Skills** — 高阶能力包，封装Prompt+工具链+流程，可复用可分享，抽象层级最高。
3. **MCP** — 标准化传输协议，解耦Agent和工具，一次开发多端接入，抽象层级居中。

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「MCP和传统的API有什么区别？—— MCP是专为LLM设计的协议，包含语义描述和上下文管理，API只管数据传输」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "【字节面经】Skills、Tools、MCP三者的区别是什么，30 秒讲清楚。" | 开场钩子 |
| 0:40 | 概念定义动画 | "一句话：三层抽象：Tools是原子函数，MCP是连接协议，Skills是业务封装。" | 核心定义 |
| 1:20 | Tools图解 | "原子函数，JSON Schema定义，抽象层级最低，粒度细管理开销大。" | Tools |
| 2:00 | Skills图解 | "高阶能力包，封装Prompt+工具链+流程，可复用可分享，抽象层级最高。" | Skills |
| 2:40 | MCP图解 | "标准化传输协议，解耦Agent和工具，一次开发多端接入，抽象层级居中。" | MCP |
| 3:20 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
