---
id: ai-scen-020
difficulty: L2
category: ai-scenario
subcategory: AI对话系统设计
tags:
- AI销售
- SPIN提问
- 销售漏斗
- 异议处理
- CRM集成
- 推荐引擎
feynman:
  essence: 基于销售漏斗和客户画像，利用策略引擎引导对话并自动转化销售线索。
  analogy: 像随身携带金牌话术库和产品手册的顶级销售，一边聊天一边记笔记，精准推产品。
  first_principle: 如何将非标准化的客户沟通转化为结构化的销售机会并最大化成交率？
  key_points:
  - 利用SPIN挖掘深层痛点，构建动态客户画像
  - 基于漏斗阶段匹配销售策略，步步为营
  - 结构化知识库处理常见异议与竞品对比
  - 人机协作模式兼顾效率与复杂谈判能力
follow_up:
- AI销售助手如何避免过于机械化的对话？
- 如何衡量AI对销售转化率的实际贡献？
- 如何处理AI无法回答的专业技术问题？
memory_points:
- 核心能力：SPIN提问挖掘需求，销售漏斗阶段识别，异议处理促单。
- 系统架构：客户画像层（CRM+实时提取）+ 销售知识库 + 策略引擎。
- 策略路由：根据意图和对话历史判断阶段（开场/挖掘/谈判/促单）。
- 实战优化：Prompt增加“预算探询强制节点”，过滤无效线索提升转化。
- 推荐引擎：需求匹配产品矩阵，基于画像做个性化组合推荐。
---

# 如何设计一个AI销售助手？能理解客户需求、推荐产品、处理异议、引导成单。

【场景分析】
AI销售助手核心能力：需求挖掘（SPIN提问法）、产品推荐、异议处理、谈判引导、CRM集成。

【实战案例】
某B2B SaaS客户接入后，AI助手处理了40%的初级咨询，但初期因未识别到“预算锁死”的客户，导致人工销售介入后转化率低。后来在Prompt中增加了“预算探询强制节点”，将无效线索过滤率提升了15%。

【系统架构】
1. 客户画像层：
   - 数据来源：CRM历史 + 对话中提取的偏好 + 行为数据
   - 画像维度：行业、规模、预算、痛点、决策角色
   - 实时更新：对话中识别新信息自动更新画像
2. 销售知识层：
   - 产品知识库：产品规格、价格、对比、案例
   - 话术库：开场白、需求挖掘、异议处理、促单话术
   - 竞品分析：优势/劣势/差异化话术
3. 对话策略引擎：
   - 销售漏斗阶段识别：认知→兴趣→评估→决策→成交
   - 策略匹配：根据漏斗阶段选择对话策略
   - SPIN提问：Situation→Problem→Implication→Need-Payoff
4. 推荐引擎：
   - 需求匹配：客户需求 → 产品矩阵匹配
   - 个性化推荐：基于画像和历史的推荐排序
   - 组合推荐：主产品+配件+服务包

【代码示例：对话策略路由】
```python
def determine_conversation_stage(chat_history, user_intent):
    # 基于意图识别和对话历史判断当前处于销售漏斗哪个阶段
    if user_intent == "inquiry":
        return "opening" # 开场建立信任
    elif check_budget_mentioned(chat_history):
        return "negotiation" # 异议处理/谈判
    elif check_pain_points_confirmed(chat_history):
        return "proposal" # 产品推荐/促单
    else:
        return "discovery" # SPIN需求挖掘
```

## 技术原理

AI 销售助手的核心是**把非结构化的自然语言对话映射到结构化的销售漏斗状态机**，每一轮对话既要推进阶段，又要产出可落库的结构化数据。这本质是一个"对话状态跟踪 + 策略路由"的工程问题：

- **销售漏斗作为有限状态机（FSM）**：阶段定义为 认知→兴趣→评估→决策→成交，每个阶段有明确的进入条件和退出动作。LLM 本身不擅长维持长程状态，所以必须由外层的状态机记录"当前处于哪个阶段""已经收集了哪些槽位（slot）"。LLM 每轮只负责：意图识别（用户处于漏斗哪一阶）、槽位抽取（预算/决策人/痛点）、下一步策略生成。
- **SPIN 提问法的工程化拆解**：SPIN（Situation/Problem/Implication/Need-Payoff）不是让 LLM 自由发挥，而是拆成可校验的子任务——Situation 阶段必填槽位（公司规模、行业），Problem 阶段必填槽位（当前痛点），Implication 阶段做影响放大（量化损失），Need-Payoff 阶段引导客户自己说出价值。每个子任务配独立的 Prompt 和校验规则，避免 LLM 跑偏。
- **客户画像的实时增量更新**：画像不是静态的 CRM 快照，而是对话过程中持续抽取的增量。每轮对话用一个小模型（或函数调用）抽取"预算""决策角色""时间节点"等槽位，写入画像库。下一轮策略生成时把最新画像注入 Prompt，实现"边聊边记"。
- **人机协作的降级机制**：AI 识别到"超出能力边界"（技术深水区、强情绪、大客户战略谈判）时主动转人工，而不是硬聊。关键信号包括：用户连续 2 次表达不满、问题命中"转人工"意图分类器、预算超过阈值进入"高价值线索"队列。这是 AI 销售落地时转化率不崩盘的兜底。

## 代码示例

```python
# 1. 销售漏斗状态机 + 策略路由
from enum import Enum
from dataclasses import dataclass, field

class FunnelStage(Enum):
    OPENING = "opening"        # 开场建立信任
    DISCOVERY = "discovery"    # SPIN 需求挖掘
    PROPOSAL = "proposal"      # 产品推荐
    NEGOTIATION = "negotiation"  # 异议处理/谈判
    CLOSING = "closing"        # 促单

@dataclass
class CustomerProfile:
    industry: str = ""
    budget: str = ""           # 关键槽位：预算
    pain_points: list = field(default_factory=list)
    decision_role: str = ""    # 决策人/影响者/使用者
    timeline: str = ""

class SalesStrategyRouter:
    """根据意图 + 槽位填充度决定下一阶段和策略"""
    def route(self, intent: str, profile: CustomerProfile,
              history: list) -> tuple[FunnelStage, str]:
        # 强制节点：预算未探询不允许进入促单（实战踩坑总结）
        if intent == "closing_intent" and not profile.budget:
            return FunnelStage.DISCOVERY, "spin_budget_probe"
        if intent == "objection":
            return FunnelStage.NEGOTIATION, "objection_handler"
        if profile.pain_points and profile.budget:
            return FunnelStage.PROPOSAL, "product_recommend"
        return FunnelStage.DISCOVERY, "spin_problem_question"

# 2. 槽位抽取 + 画像增量更新（每轮调用）
def extract_slots(user_msg: str, profile: CustomerProfile) -> CustomerProfile:
    """用小模型/正则从用户消息抽取槽位，增量更新画像"""
    prompt = f"""从用户消息抽取销售关键信息，输出 JSON：
    {{'budget': '', 'pain_points': [], 'decision_role': '', 'timeline': ''}}
    用户消息：{user_msg}
    当前画像：{profile.__dict__}"""
    slots = llm_extract(prompt)   # 函数调用，输出结构化 JSON
    for k, v in slots.items():
        if v:
            setattr(profile, k, v)   # 只更新非空字段
    return profile

# 3. 异议处理：结构化知识库检索 + 话术模板
def handle_objection(objection: str, kb: vectorstore) -> str:
    """异议 → 检索知识库 → 填充话术模板"""
    docs = kb.similarity_search(objection, k=3)   # 竞品对比/案例/FAB
    return llm_generate(
        template="用户提出异议：{obj}\n参考话术：{ctx}\n生成自然回应",
        ctx="\n".join(d.content for d in docs), obj=objection)
```

```yaml
# 4. 人机协作降级规则（配置化，避免硬编码）
handoff_rules:
  - trigger: "intent == complain && sentiment_score < -0.5"
    action: transfer_to_human
    reason: "用户情绪负向，AI 继续会激化矛盾"
  - trigger: "turn_count > 15 && stage == discovery"
    action: transfer_to_human
    reason: "需求挖掘超 15 轮仍未收敛，可能高价值复杂客户"
  - trigger: "budget > 100000"
    action: transfer_to_human
    reason: "大额线索必须人工介入"
```

## 对比选型

| 维度 | 纯规则型销售机器人 | LLM 驱动销售助手（本方案） | 人工销售 |
| :--- | :--- | :--- | :--- |
| **对话自然度** | 低（关键词匹配，僵硬） | 高（上下文理解，拟人化） | 最高 |
| **覆盖咨询量** | 高（成本极低） | 中高（40%-70% 初级咨询） | 低（人力受限） |
| **复杂谈判** | 不支持 | 有限（需人机协作降级） | 强 |
| **画像积累** | 无（不沉淀数据） | 实时增量结构化 | 依赖销售手动录入 |
| **转化率** | 极低 | 中（过滤无效线索后提升 15%+） | 高 |
| **适用阶段** | 顶部漏斗筛选 | 中部漏斗培育 + 意向识别 | 底部漏斗成交 |

## 常见坑

- **不要让 LLM 自由发挥对话**：无状态机的自由对话会跑题、跳过预算探询、过早报价。必须用 FSM 强制阶段流转 + 槽位校验，把 LM 限制在"单轮策略生成"的边界内。
- **预算探询是必填节点**：实战踩坑——未探询预算就推高价产品，人工介入后发现预算锁死，转化率低。在 Prompt 增加强制节点后无效线索过滤率提升 15%。
- **异议处理不能靠 LLM 即兴**：竞品对比、价格异议这类问题必须检索结构化知识库（竞品分析表、FAB 话术），不能让模型瞎编，否则会出现幻觉性贬低竞品（合规风险）。
- **衡量 AI 贡献要设计 A/B 实验**：不能只看 AI 处理的线索转化率，因为 AI 接的多是低质量线索。必须做随机分流 A/B 测试，对比"有 AI 介入"vs"无 AI"的最终成交率，才能真实归因。
- **GDPR/个保法合规**：客户画像涉及个人信息，对话录音和画像存储要明确告知用户、提供退出机制，敏感字段（身份证、手机号）要脱敏后入库。

## 记忆要点

- 核心能力：SPIN提问挖掘需求，销售漏斗阶段识别，异议处理促单。
- 系统架构：客户画像层（CRM+实时提取）+ 销售知识库 + 策略引擎。
- 策略路由：根据意图和对话历史判断阶段（开场/挖掘/谈判/促单）。
- 实战优化：Prompt增加“预算探询强制节点”，过滤无效线索提升转化。
- 推荐引擎：需求匹配产品矩阵，基于画像做个性化组合推荐。


## 结构化回答

**30 秒电梯演讲：** 基于销售漏斗和客户画像，利用策略引擎引导对话并自动转化销售线索。——打个比方，像随身携带金牌话术库和产品手册的顶级销售，一边聊天一边记笔记，精准推产品。

**展开框架：**
1. **核心能力** — SPIN提问挖掘需求，销售漏斗阶段识别，异议处理促单。
2. **系统架构** — 客户画像层（CRM+实时提取）+ 销售知识库 + 策略引擎。
3. **策略路由** — 根据意图和对话历史判断阶段（开场/挖掘/谈判/促单）。

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「AI销售助手如何避免过于机械化的对话」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "设计一个AI销售助手，30 秒讲清楚。" | 开场钩子 |
| 0:30 | 概念定义动画 | "一句话：基于销售漏斗和客户画像，利用策略引擎引导对话并自动转化销售线索。" | 核心定义 |
| 1:00 | 核心能力图解 | "SPIN提问挖掘需求，销售漏斗阶段识别，异议处理促单。" | 核心能力 |
| 1:30 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
