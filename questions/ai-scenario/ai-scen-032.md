---
id: ai-scen-032
difficulty: L2
category: ai-scenario
subcategory: AI评测与监控
tags:
- Golden Set
- 评测集
- CI/CD
- 人工标注
- 回归测试
- 质量门禁
feynman:
  essence: 构建分层标准测试集，通过自动化评测守护模型质量。
  analogy: 像考试题库，每次改代码后都考一遍，防止考分倒退。
  first_principle: 如何在快速迭代中量化AI能力，确保不发生退化？
  key_points:
  - 构建：融合真实日志、人工构造和Bad Case
  - 分层：核心集CI快测，全集发布前深测
  - 执行：规则+LLM自动判分，人工双盲抽检
  - 门禁：分数下降即阻断发布，守住质量底线
follow_up:
- 如何保持Golden Set的时效性？
- 标注一致性如何保证？
- Core Set和Full Set的分配比例如何确定？
memory_points:
- 构建流程：来源（线上日志/人工构造/对抗样本）→ 标注（评分细则）→ 分层。
- 分层设计：Core Set（50条，CI必跑）+ Full Set（500条，发布前）。
- 评测执行：规则校验（必过）+ LLM-as-Judge（语义评分）+ 语义相似度。
- CI集成：Pre-merge通过率>95%，Pre-release>90%，下降>5%阻断发布。
- 对比：Golden Set离线快且无风险，A/B测试在线慢但看真实业务指标。
---

# 如何设计AI应用的Golden Set评测系统？构建高质量评测集，保障每次迭代不退化。

【场景分析】
Golden Set是AI应用质量保障的基础：没有评测集就无法量化迭代效果，也无法阻断质量退化。

**实战案例**：某电商客服助手在更新Prompt模板后，对“如何退货”的回答变得正确但语气冷漠，导致用户满意度下降。通过Golden Set中的“语气亲和力”检查点（包含人工评分样本），CI系统成功捕获了这一质量退化并阻断了发布。

【Golden Set构建流程】
1. 数据来源：
   - 线上真实日志：选取有代表性的用户交互
   - 人工构造：覆盖特定场景和边界条件
   - 对抗样本：红队测试生成的攻击样本
   - Bad Case回流：线上用户反馈的差评案例
2. 标注规范：
   - Query：用户问题
   - 期望答案：参考答案（允许有多重可接受答案）
   - 评分标准：1-5分评分细则（正确性、相关性、完整性、安全性）
   - 关键检查点：必须包含的关键信息、禁止包含的有害内容
   - 检索标注：相关文档ID（用于评测检索质量）
3. 分层设计：
   - Core Set（50条）：核心场景，每次CI运行
   - Full Set（500条）：完整覆盖，发布前运行
   - Regression Set（动态）：新发现的Bad Case

**代码示例（Python：使用LLM-as-Judge评测Golden Set）**
```python
def evaluate_golden_set(model_outputs, golden_data):
    scores = []
    for item in golden_data:
        output = model_outputs.get(item["query"])
        # 1. 关键信息规则校验（必过）
        if not all(k in output for k in item["must_have"]):
            return 0.0 # 直接判0分
        
        # 2. LLM 打分（语义评测）
        judge_prompt = f"Answer: {output}\nReference: {item['ref']}\nRate (1-5):"
        score = llm_client.generate(judge_prompt)
        scores.append(float(score))
    return np.mean(scores)
```

【覆盖维度】
- 功能维度：FAQ、多轮对话、工具调用、代码生成、文档处理
- 难度维度：简单40% + 中等40% + 困难20%
- 场景维度：正常路径60% + 边缘场景25% + 对抗样本15%
- 语言维度：中文、英文、混合
- 长度维度：短Query、长Query、超长上下文

【评测执行】
1. 自动评测：
   - 规则校验：格式检查、关键词检查、引用验证
   - LLM-as-Judge：GPT-4作为评审打分
   - 语义相似度：与参考答案的BERTScore
2. 人工评测：
   - 双盲评测：两个标注者独立打分
   - 仲裁机制：分数差异>1分时第三人仲裁
   - 定期重标：10%样本重新标注，检测标注一致性

【CI/CD集成】
- Pre-merge：Core Set通过率>95%
- Pre-release：Full Set通过率>90%
- 回滚阈值：通过率下降>5% → 阻断发布
- 成本控制：LLM-as-Judge用 cheaper model（GPT-4o-mini）

**对比表格：Golden Set vs 在线A/B测试**

| 维度 | Golden Set (离线评测) | 在线 A/B 测试 |
| :--- | :--- | :--- |
| **实施成本** | 低（仅算力成本） | 高（需要分流、埋点、用户流量） |
| **反馈速度** | 实时（分钟级） | 慢（通常需要数天收集样本） |
| **评估指标** | 准确率、安全性、幻觉率 | CTR、转化率、用户停留时长、满意度 |
| **风险性** | 无风险（沙盒环境） | 有风险（可能影响用户体验） |
| **覆盖范围** | 特定场景、边缘Case | 真实长尾流量、泛化能力 |

## 常见考点
1. **数据泄露风险**：在构建评测集时，如何防止评测集的数据被 inadvertently 包含在训练数据中？
   *答案要点*：严格的数据隔离策略。建立Canary Set（金丝雀集），这部分数据绝不参与训练。定期使用Canary Set测试模型，若模型异常高分，疑似过拟合或数据泄露。
2. **Golden Set的维护成本**：随着产品迭代，旧的问题不再适用，如何低成本维护Golden Set？
   *答案要点*：设置样本的生命周期管理；通过监控线上Query分布，自动识别低频/失效样本并标记待删除；利用LLM自动生成相似问题来扩充或替换过时样本，人工只需复核。
3. **主观题的评分一致性**：对于开放性问题，如何保证LLM-as-Judge或人工评分的稳定性？
   *答案要点*：细化评分Rubric（细则），将抽象标准转化为具体的检查项；使用CoT（Chain of Thought）让Judge先分析再打分；计算Cohen's Kappa系数监控一致性，低一致性样本需重新对齐标准。

## 流程图

```mermaid
flowchart TD
    A["数据来源池"] --> B["标注与规范设计"]
    subgraph A ["多源数据采集"]
        A1["线上真实日志"]
        A2["Bad Case回流"]
        A3["红队对抗样本"]
    end
    subgraph B ["精细化标注"]
        B1["参考答案标注"]
        B2["1-5分评分细则"]
        B3["关键检查点定义"]
    end
    B --> C{"Golden Set分层路由"}
    C -->|"核心场景"| D1["Core Set (50条)<br/>Pre-merge必跑"]
    C -->|"全量覆盖"| D2["Full Set (500条)<br/>Pre-release全量跑"]
    D1 --> E["自动评测引擎"]
    D2 --> E
    subgraph E ["自动化评测"]
        E1["规则校验<br/>(格式/关键词)"] --> E4["综合评分汇总"]
        E2["LLM-as-Judge<br/>(GPT-4o-mini语义)"] --> E4
        E3["语义相似度<br/>(BERTScore)"] --> E4
    end
    E4 --> F{"通过率检查"}
    F -- "下降>5%" --> G["阻断CI/CD发布"]
    F -- "Pre-merge>95%" --> H["允许代码合并"]
```

## 核心知识点图

<img src="/interview-2026/images/diagram_ai-scenario_ai-scen-032.svg" alt="如何设计AI应用的Golden Set评测系统？构建高质量评测集，保障每次迭代不退化。 - 核心知识点图" style="max-width:100%;height:auto;border:1px solid var(--border);border-radius:8px;margin:1em 0;" />

## 记忆要点

- 构建流程：来源（线上日志/人工构造/对抗样本）→ 标注（评分细则）→ 分层。
- 分层设计：Core Set（50条，CI必跑）+ Full Set（500条，发布前）。
- 评测执行：规则校验（必过）+ LLM-as-Judge（语义评分）+ 语义相似度。
- CI集成：Pre-merge通过率>95%，Pre-release>90%，下降>5%阻断发布。
- 对比：Golden Set离线快且无风险，A/B测试在线慢但看真实业务指标。


## 结构化回答

**30 秒电梯演讲：** 构建分层标准测试集，通过自动化评测守护模型质量。——打个比方，像考试题库，每次改代码后都考一遍，防止考分倒退。

**展开框架：**
1. **构建流程** — 来源（线上日志/人工构造/对抗样本）→ 标注（评分细则）→ 分层。
2. **分层设计** — Core Set（50条，CI必跑）+ Full Set（500条，发布前）。
3. **评测执行** — 规则校验（必过）+ LLM-as-Judge（语义评分）+ 语义相似度。

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「如何保持Golden Set的时效性」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "设计AI应用的Golden Set评测系统，30 秒讲清楚。" | 开场钩子 |
| 0:30 | 概念定义动画 | "一句话：构建分层标准测试集，通过自动化评测守护模型质量。" | 核心定义 |
| 1:00 | 构建流程图解 | "来源（线上日志/人工构造/对抗样本）→ 标注（评分细则）→ 分层。" | 构建流程 |
| 1:30 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
