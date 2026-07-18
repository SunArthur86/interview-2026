---
id: agmu-017
difficulty: L2
category: ai-agent
subcategory: 多智能体系统
tags:
- IO
feynman:
  essence: 分层评估结合人工黄金集，避免模型评估偏差。
  analogy: 像考核员工，既要考试（单元），也要看项目成果（端到端）。
  first_principle: 如何全方位量化多智能体系统的性能表现？
  key_points:
  - 单元：单Agent输入输出
  - 集成：交互逻辑测试
  - 端到端：整体任务成功率
  - 防偏：LLM-as-judge需黄金集校准
memory_points:
- 评估分层进行：单元测单 Agent，集成测交互，E2E 测任务成功率。
- 配合 LLM-as-a-judge 和 Golden Set，防偏见。
- Tracing 可视化全链路，定位 Token 消耗与中间状态。
---

# 多 Agent 的评估怎么做

多 Agent 的评估必须**分层**进行，单看最终结果往往难以定位问题。
- **单元**：单 Agent I/O。测试单个 Agent 是否根据特定 Input 给出了合理的 Output 或 Tool Call。
- **集成**：两两交互。测试 Agent A 的输出是否能被 Agent B 正确解析并执行。
- **端到端（E2E）**：任务成功率。给定一个用户 Goal，整个系统是否能以合理的成本和时间给出正确结果。

辅助手段：LLM-as-judge（用 GPT-4 当裁判），但需防偏见，最好配黄金集与人审。

**评估流程与代码示例**：
```text
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Dataset   │ ───▶ │   System     │ ───▶ │   Metrics   │
│ (Goals)     │      │   (Agents)   │      │ (Success/   │
└─────────────┘      └──────────────┘      │  Cost/Latency│
                           │               └─────────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │  LLM-as-a-Judge  │
                  │  (Score 1-10)    │
                  └──────────────────┘
```

**实战案例**：
在开发客服 Agent 时，单纯看最终回复准确率高达 95%，但通过 Trace 评估发现，Agent A（意图识别）多次将「退款」误判为「咨询」，导致 Agent B 不得不进行多轮反问。通过优化 Agent A 的单元评估指标，将系统平均交互轮次从 5.2 轮降至 3.1 轮，大幅降低了 Token 成本。

**代码示例**：
```python
# 防止多 Agent 评估时的死循环
import hashlib

def run_eval_with_guard(agent_step, max_steps=10):
    seen_states = set()
    for i in range(max_steps):
        action = agent_step()
        # 对 Action 指纹哈希，防止陷入死循环（如 A->B->A）
        state_hash = hashlib.md5(str(action).encode()).hexdigest()
        if state_hash in seen_states:
            return {"status": "failed", "reason": "loop_detected"}
        seen_states.add(state_hash)
    return {"status": "completed", "steps": i}
```

**评估维度对比**：

| 维度 | 单元测试 | 集成测试 | E2E (Golden Set) |
| :--- | :--- | :--- | :--- |
| **评估对象** | 单个 Agent | Agent 交互对 | 完整工作流 |
| **核心指标** | Function Call 正确率 | 消息解析成功率 | 任务完成率 / 总耗时 |
| **故障定位** | 极快 | 中等 | 慢 (需 Trace) |
| **成本** | 低 | 中 | 高 (消耗大量 Token) |

**关键细节补充**：
- **Tracing**：必须使用分布式追踪（如 LangSmith, Arize），可视化每一步的 Token 消耗和中间状态。
- **Golden Set**：构建高质量的标准问题集，覆盖常见路径和边界情况。
- **Hallucination Rate**：专门检测 Agent 是否虚构了工具或参数。
- **Cost-aware Evaluation**：不仅评估结果对错，还要评估达成结果的路径是否最经济（如避免不必要的工具调用）。

**增强后的代码逻辑（去重与熔断）**：
```python
from typing import Callable, Any, Set, List
import hashlib

def run_with_timeout_and_loop_check(step_func: Callable, max_steps: int = 20) -> Any:
    history: Set[str] = set()
    for _ in range(max_steps):
        result = step_func()
        # 指纹计算：只取关键字段或哈希，避免内容微变导致判空失败
        state_sig = hashlib.md5(str(result).encode()).hexdigest()
        
        if state_sig in history:
            raise RuntimeError("Agent陷入了状态循环")
        history.add(state_sig)
        
        if result.get("done", False):
            return result
    raise TimeoutError("超过最大评估步数")
```

## 易错点
1. **过度依赖 LLM-as-Judge**：认为 GPT-4 的打分就是绝对真理。实际上对于特定领域的逻辑（如数学计算、代码语法），传统的规则测试往往比 LLM 裁判更准且成本更低。
2. **忽视数据分布偏移**：评估集只覆盖“ happy path”（正常流程），一旦用户输入偏离预期，Agent 表现崩塌。必须引入 Adversarial Examples（对抗样本）进行鲁棒性测试。

## 面试追问
1. 如果 E2E 评估显示成功率下降，但单元测试都通过了，你会怎么排查？（提示：关注 Agent 间的交互损耗和上下文传递噪声）。
2. 如何构建高质量的 Golden Set？除了人工标注，有没有自动化生成并清洗测试数据的方法？
3. 在资源受限的情况下（如只有 GPT-3.5 可用做裁判），如何保证评估的客观性？


## 记忆要点

- 评估分层进行：单元测单 Agent，集成测交互，E2E 测任务成功率。
- 配合 LLM-as-a-judge 和 Golden Set，防偏见。
- Tracing 可视化全链路，定位 Token 消耗与中间状态。


## 结构化回答

**30 秒电梯演讲：** 多 Agent 评估必须分层进行，单看最终结果难定位问题。三层：单元测单 Agent 输入输出（Function Call 正确率）、集成测两两交互（消息解析成功率）、E2E 测任务成功率（整体 Goal 完成率）。辅助手段是 LLM-as-Judge（GPT-4 当裁判）但要防偏见配黄金集与人审。必须用 Tracing（LangSmith、Arize）可视化全链路定位 Token 消耗和中间状态。

**展开框架：**
1. **三层评估** — 单元测单 Agent I/O（Function Call 正确率）、集成测 Agent 交互对（消息解析成功率）、E2E 测完整工作流（任务完成率总耗时）。
2. **辅助手段** — LLM-as-Judge 用 GPT-4 打分但要防偏见配 Golden Set；Hallucination Rate 专门检测虚构工具或参数；Cost-aware 评估路径是否最经济。
3. **Tracing 与避坑** — 分布式追踪（LangSmith、Arize）可视化每步 Token 消耗；评估集别只覆盖 happy path 要引对抗样本测鲁棒性。

**收尾：** 做客服 Agent 时踩过坑——最终回复准确率 95% 但 Trace 发现意图识别 Agent 把退款误判为咨询导致多轮反问，优化 Agent A 单元指标后交互轮次从 5.2 降到 3.1。您想聊哪块，Golden Set 构建还是 Tracing 工具选型？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：多 Agent 评估怎么做 | "像考核员工，既要考试（单元），也要看项目成果（端到端）。" | 类比开场 |
| 0:15 | 三层评估图 | "单元测单 Agent，集成测交互，E2E 测任务成功率。" | 分层评估 |
| 0:45 | LLM-as-Judge 警示 | "GPT-4 当裁判要防偏见，配黄金集和人审校准。" | 辅助手段 |
| 1:10 | Tracing 可视化 | "LangSmith、Arize 可视化全链路，定位 Token 消耗。" | 工具支持 |
| 1:35 | 意图误判案例 | "实战：准确率 95% 但意图误判导致多轮，Trace 定位优化。" | 实战教训 |
| 1:50 | 总结卡 | "记住：分层评估 + LLM 裁判 + Tracing。下期讲人机在环。" | 收尾 |
