---
id: bd-ai-006
difficulty: L3
category: llm-core
categories:
- ai-agent
- eng-practice
- llm-core
subcategory: Agent核心框架
tags:
- 字节跳动
- 面经
- Agent
- 工具调用
- 规划
- ReAct
feynman:
  essence: 通过感知-规划-行动-观察的闭环，结合RAG和工具调用实现自主决策。
  analogy: 像人做任务：先看资料（感知），定计划（规划），动手做（行动），检查结果（观察）。
  first_principle: 如何让模型利用外部工具和知识，自主地解决复杂任务？
  key_points:
  - 核心是ReAct循环推理执行
  - 规划层分解复杂任务
  - RAG提供外部知识增强
  - 工具需原子化且鲁棒
  - 上下文需动态组装管理
follow_up:
- ReAct和Plan-and-Execute的区别？—— ReAct是边想边做（交错推理），Plan-and-Execute是先规划后执行（串行）
- Agent怎么知道任务完成了？—— LLM判断 + 终止条件（如产出包含最终答案格式/达到目标）
- 工具调用失败后怎么恢复？—— 错误信息返回给LLM，让其重新选择工具或调整参数
memory_points:
- 核心闭环：感知(组装上下文)→规划(任务分解)→行动(工具调用)→观察(结果解析)→决策
- 感知层：注入Prompt、对话历史、RAG检索知识及工具Schema，构建完整上下文
- 规划层：采用ReWOO先分解任务再执行，避免无效调用，复杂任务分步处理
- 行动层：ReAct循环，LLM选工具→执行→捕获异常→将错误反馈给LLM自我纠正
- 关键参数：设置最大迭代次数(如10次)防止死循环，异常信息需转化为自然语言
frequency: medium
---

# 【字节面经】Agent如何结合工具、知识、规划实现自主运行？请设计一个完整的执行链路。

Agent自主运行的核心是"感知→规划→行动→观察"的闭环。以下从架构设计到代码实现进行完整拆解。

**核心架构：ReAct + 工具增强**

```text
用户输入
    ↓
[感知层] 意图理解 + 上下文组装
    ↓
[规划层] 任务分解 → 子目标序列
    ↓
┌──→ [行动层] 选择工具 + 参数生成
│         ↓
│    [执行层] 工具调用 → 获取结果
│         ↓
│    [观察层] 结果解析 + 状态更新
│         ↓
│    [决策层] 是否完成？→ 否 → 回到行动层
│                  → 是 → 输出最终答案
└────────────────────────────────┘
```

**1. 感知层 — 上下文组装**
感知层的核心是将非结构化的用户输入转化为LLM可理解的Prompt，并注入必要的知识。
```python
def build_context(user_input, memory, knowledge_base):
    context = {
        "user_query": user_input,
        "conversation_history": memory.get_recent(n=10),  # 滑动窗口保留近期对话
        "relevant_knowledge": knowledge_base.retrieve(user_input, top_k=5),  # RAG检索
        "available_tools": get_tool_schemas(),  # 当前可用的工具定义
        "system_prompt": AGENT_SYSTEM_PROMPT
    }
    return context
```

**2. 规划层 — 任务分解**
对于复杂任务，先做ReWOO（Reasoning Without Observation）式的规划，避免在思维过程中产生无效的工具调用开销。
- **实战案例**：在自动化数据分析Agent中，直接让AI分析Excel常因数据量过大导致Token超限，通过先规划"采样分析->全量跑数"两步策略，将成功率从60%提升至95%。
```python
# 规划Prompt示例
planning_prompt = """
用户需求：{user_query}
可用工具：{tools}
请将任务分解为2-5个子步骤，每个步骤说明：
1. 使用哪个工具
2. 需要什么参数
3. 预期得到什么信息
不要执行，只规划。
"""
# 输出示例
plan = [
    {"step": 1, "tool": "search_api", "params": {"q": "竞品分析"}, "expect": "竞品列表"},
    {"step": 2, "tool": "web_scraper", "params": {"url": "..."}, "expect": "竞品详情"},
    {"step": 3, "tool": "data_analyzer", "params": {}, "expect": "对比分析"}
]
```

**3. 行动层 — 工具选择与调用（ReAct Loop）**
这是Agent的"大脑"与"手脚"连接的关键。
```python
def react_loop(query, tools, max_iterations=10):
    messages = [{"role": "user", "content": query}]
    
    for i in range(max_iterations):
        # LLM推理：选择工具 or 给出最终答案
        response = llm.chat(
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        
        # 助手回复加入历史
        messages.append({"role": "assistant", "content": response.content})
        
        # 如果LLM选择调用工具
        if response.tool_calls:
            for tool_call in response.tool_calls:
                # 执行工具 (关键：异常处理)
                try:
                    func = tools_map[tool_call.function.name]
                    args = json.loads(tool_call.function.arguments)
                    result = func(**args)
                    messages.append({"role": "tool", "content": str(result), "tool_call_id": tool_call.id})
                except Exception as e:
                    # 实战关键：将错误转化为LLM可理解的自我纠正指令
                    error_msg = f"Error: {str(e)}. Please fix arguments or try another tool."
                    messages.append({"role": "tool", "content": error_msg, "tool_call_id": tool_call.id})
        else:
            # 最终答案
            return response.content
    return "Maximum iterations reached."
```

## 核心流程图

```mermaid
flowchart TD
    N0["核心是ReAct循环推理执行"]
    N1["规划层分解复杂任务"]
    N2["RAG提供外部知识增强"]
    N3["工具需原子化且鲁棒"]
    N4["上下文需动态组装管理"]
    N0 --> N1
    N1 --> N2
    N2 --> N3
    N3 --> N4
    style N0 fill:#2196F3,color:#fff
    style N1 fill:#FF9800,color:#fff
    style N2 fill:#4CAF50,color:#fff
    style N3 fill:#9C27B0,color:#fff
    style N4 fill:#f44336,color:#fff
    subgraph Legend["图例"]
        L1["🟢 开始/成功"]:::start
        L2["🔵 主流程"]:::process
        L3["🟠 判断/中间态"]:::decision
        L4["🔴 失败/结束"]:::error
    end
```

## 记忆要点

- 核心闭环：感知(组装上下文)→规划(任务分解)→行动(工具调用)→观察(结果解析)→决策
- 感知层：注入Prompt、对话历史、RAG检索知识及工具Schema，构建完整上下文
- 规划层：采用ReWOO先分解任务再执行，避免无效调用，复杂任务分步处理
- 行动层：ReAct循环，LLM选工具→执行→捕获异常→将错误反馈给LLM自我纠正
- 关键参数：设置最大迭代次数(如10次)防止死循环，异常信息需转化为自然语言

## 结构化回答

**30 秒电梯演讲：** 通过感知-规划-行动-观察的闭环，结合RAG和工具调用实现自主决策。——打个比方，像人做任务：先看资料（感知），定计划（规划），动手做（行动），检查结果（观察）。

**展开框架：**
1. **核心闭环** — 感知(组装上下文)→规划(任务分解)→行动(工具调用)→观察(结果解析)→决策
2. **感知层** — 注入Prompt、对话历史、RAG检索知识及工具Schema，构建完整上下文
3. **规划层** — 采用ReWOO先分解任务再执行，避免无效调用，复杂任务分步处理

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「ReAct和Plan-and-Execute的区别？—— ReAct是边想边做（交错推理），Plan-and-Execute是先规划后执行（串行）」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "【字节面经】Agent如何结合工具、知识、规划实现自主运行，30 秒讲清楚。" | 开场钩子 |
| 0:36 | 概念定义动画 | "一句话：通过感知-规划-行动-观察的闭环，结合RAG和工具调用实现自主决策。" | 核心定义 |
| 1:12 | 核心闭环图解 | "感知(组装上下文)→规划(任务分解)→行动(工具调用)→观察(结果解析)→决策" | 核心闭环 |
| 1:48 | 感知层图解 | "注入Prompt、对话历史、RAG检索知识及工具Schema，构建完整上下文" | 感知层 |
| 2:24 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |

### 视频流程图

```mermaid
flowchart LR

    subgraph Intro["🎥 引入"]
        N0["【字节面经】Agent如何结合工具…<br/>0:00"]:::intro
    end

    subgraph Core["📖 核心讲解"]
        N1["通过感知-规划-行动-观察的闭环，结合RAG和工<br/>0:36"]:::core
        N2["核心闭环图解<br/>1:12"]:::core
    end

    subgraph Practice["🔧 实战"]
        N3["感知层图解<br/>1:48"]:::practice
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


