---
id: ai-scen-035
difficulty: L2
category: ai-scenario
subcategory: AI评测与监控
tags:
- 质量门禁
- CI/CD
- 自动评测
- Diff分析
- 回归检测
- 发布阻断
feynman:
  essence: 在CI流程中自动运行评测集，阻断劣化代码上线。
  analogy: 像红绿灯，考试不达标就不许发布，防止带病上线。
  first_principle: 如何在自动化流程中客观判断AI改动是优化还是退化？
  key_points:
  - 触发：Prompt或模型变更是自动触发条件
  - 基准：对比新版本与Baseline的各项指标
  - 策略：通过、警告、失败三级判定
  - 报告：自动生成Diff报告，指出退化案例
follow_up:
- CI中的评测时间如何压缩？
- 如何处理「警告」级别的变更？
- 增量评测如何确定受影响的场景？
memory_points:
- 触发条件：Prompt/模型/参数变更触发自动评测，防止质量退化。
- 评测流程：Golden Set推理 → 规则+LLM评分 → 与Baseline对比。
- 门禁阈值：指标下降<5%通过，>10%失败，5-10%需人工确认。
- 成本控制：CI用Core Set(50条)，发布前用Full Set(500条)。
- 边界处理：Judge不稳定取n=3众数，空输出直接判0分阻断。
---

# 如何设计CI中的AI质量门禁？在代码提交和发布前自动检测质量退化。

【场景分析】
AI应用的质量门禁（Quality Gate）是CI/CD中的关键环节：自动检测Prompt/模型变更是否引入质量退化。

【质量门禁流程】
1. 触发条件：
   - Prompt模板变更
   - 模型版本变更（新模型/新量化版本）
   - 检索参数调整（chunk_size、top_k、rerank阈值）
   - 系统配置变更（temperature、max_tokens）
2. 自动评测Pipeline：
   - Step 1：拉取Core Golden Set（50条）
   - Step 2：新版本批量推理生成答案
   - Step 3：自动评分（规则 + LLM-as-Judge）
   - Step 4：与Baseline对比
   - Step 5：生成质量报告（通过/失败/警告）
3. 门禁判定：
   - 通过：所有指标 >= Baseline的95%
   - 警告：部分指标下降5-10%，需人工确认
   - 失败：任一关键指标下降>10%

【评测维度与阈值】
| 维度 | 指标 | 通过阈值 | 失败阈值 |
| 准确性 | 答案正确率 | >=90% | <80% |
| 忠实度 | Faithfulness | >=0.85 | <0.70 |
| 安全性 | 有害输出率 | <0.1% | >1% |
| 格式 | 结构化输出合规率 | >=99% | <95% |
| 延迟 | P95延迟 | <Baseline×1.2 | >Baseline×2 |

【成本与时间控制】
- Core Set（50条）评测成本：约$2-5/次（GPT-4o-mini Judge）
- 评测时间：5-10分钟（并行推理）
- Full Set（500条）：约$20-50/次，30-60分钟，仅发布前运行
- 增量评测：只评测受变更影响的场景

【Diff分析报告】
- 回退案例：列出新版本答错的案例（原版本答对）
- 改善案例：列出新版本改善的案例
- 无人区：新版本和旧版本都答错但错误不同的案例
- 决策建议：基于回归/改善比例给出发布建议

【边界情况处理】
- **Prompt重构导致答案长度激增**：增加Token成本指标监控，防止成本爆炸。
- **Judge模型不稳定**：对同一答案进行多次Judge（n=3），取众数结果，避免评分随机性。
- **空输出/异常输出处理**：捕获模型拒绝回答或抛出异常的情况，直接判为0分并阻断流程。
- **并发速率限制**：防止评测请求过于密集触发上游API的Rate Limit，需实现指数退避重试机制。

【实战案例】
某金融问答系统升级RAG检索策略（从Top-K改为Rerank），CI门禁触发告警：虽然整体准确率提升2%，但“理财风险等级”相关问题的准确性下降了15%（幻觉增加）。团队回滚并发现Rerank模型对专业术语权重过高，导致忽略了文档中的风险免责声明。

【关键代码实现】
```python
import concurrent.futures

def run_quality_gate(candidate_model, golden_dataset, baseline_metrics):
    # 并行推理加速评测
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(candidate_model.predict, golden_dataset))
    
    current_metrics = evaluator.calculate(results)
    
    # 门禁判定逻辑
    for metric, value in current_metrics.items():
        threshold = baseline_metrics[metric] * 0.95
        if value < threshold:
            return {"status": "FAIL", "reason": f"{metric} dropped: {value} vs {threshold}"}
            
    return {"status": "PASS", "metrics": current_metrics}
```

## 面试追问
1. **评测集过时怎么办**？如何防止Golden Set的“数据污染”（即模型在训练集见过答案导致虚高）？
2. **Judge模型偏见**：如果Judge模型（如GPT-4）本身对新版本模型（如Claude 3）有偏好，如何消除这种系统误差？
3. **长尾场景**：对于极少发生但后果严重的极端输入（如恶意Prompt注入），如何在CI中进行有效覆盖？

## 易错点
1. **误将中间指标当最终指标**：例如只关注检索召回率而忽略了最终答案的正确率，导致检索结果全了但生成质量下降。
2. **忽视统计显著性**：指标微小波动（如0.1%）可能是随机噪声造成的，错误的判定会导致频繁的无效回滚或发布。

## 流程图

```mermaid
flowchart TD
    A[Prompt/模型配置变更] --> B[触发CI/CD流水线]
    B --> C[拉取Core Golden Set基准集]
    C --> D[新版本批量推理生成结果]
    D --> E[LLM-as-Judge自动评分机制]
    E --> F[与Baseline核心指标对比]
    F --> G{质量退化检测判定}
    G -- 指标下降<5% --> H[通过门禁, 允许发布]
    G -- 指标下降5-10% --> I[触发警告, 等待人工确认]
    G -- 关键指标下降>10% --> J[门禁失败, 阻断并回滚]
```


## 记忆要点

- 触发条件：Prompt/模型/参数变更触发自动评测，防止质量退化。
- 评测流程：Golden Set推理 → 规则+LLM评分 → 与Baseline对比。
- 门禁阈值：指标下降<5%通过，>10%失败，5-10%需人工确认。
- 成本控制：CI用Core Set(50条)，发布前用Full Set(500条)。
- 边界处理：Judge不稳定取n=3众数，空输出直接判0分阻断。


## 结构化回答

**30 秒电梯演讲：** 在CI流程中自动运行评测集，阻断劣化代码上线。——打个比方，像红绿灯，考试不达标就不许发布，防止带病上线。

**展开框架：**
1. **触发条件** — Prompt/模型/参数变更触发自动评测，防止质量退化。
2. **评测流程** — Golden Set推理 → 规则+LLM评分 → 与Baseline对比。
3. **门禁阈值** — 指标下降<5%通过，>10%失败，5-10%需人工确认。

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「CI中的评测时间如何压缩」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "设计CI中的AI质量门禁，30 秒讲清楚。" | 开场钩子 |
| 0:30 | 概念定义动画 | "一句话：在CI流程中自动运行评测集，阻断劣化代码上线。" | 核心定义 |
| 1:00 | 触发条件图解 | "Prompt/模型/参数变更触发自动评测，防止质量退化。" | 触发条件 |
| 1:30 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
