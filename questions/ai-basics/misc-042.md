---
id: misc-042
difficulty: L2
category: ai-basics
subcategory: 评估与安全
feynman:
  essence: 通过标准化数据集和指标量化模型的各项能力，衡量模型优劣。
  analogy: 像“高考”一样统一出题，给学生打分，但高分未必代表能干好工作。
  first_principle: 如何科学、客观地衡量大模型在特定任务或通用场景下的能力水平？
  key_points:
  - MMLU考知识广度，GSM8K/HumanEval考逻辑
  - MT-Bench侧重对话体验
  - 警惕数据污染，需结合人工评测
follow_up:
- 如何检测模型是否在benchmark上过拟合?
- LiveBench如何解决数据污染问题?
memory_points:
- 知识基准：MMLU（多学科）、C-Eval（中文），考察广度，多为选择题
- 能力基准：GSM8K（数学推理）、HumanEval（代码生成）、TruthfulQA（反幻觉）
- 对话基准：MT-Bench（多轮对话，GPT-4打分）、Arena-Hard（高难度，强区分度）
- 局限性：数据污染、过拟合、无法覆盖真实场景、多选题偏差
- 最佳实践：静态基准 + 模型裁判 + 真实业务A/B测试组合评估
---

# 大模型的主流评估基准有哪些?各自评估什么能力?有什么局限性

- **主流评估基准:**

| Benchmark | 评估能力 | 题目数 | 特点 |
|-----------|---------|--------|------|
| MMLU | 多学科知识 | 14K | 学术知识基准 |
| GSM8K | 数学推理 | 8.5K | 小学数学 |
| MATH | 高等数学 | 12.5K | 竞赛数学 |
| HumanEval | 代码生成 | 164 | 函数级编程 |
| MBPP | 代码生成 | 974 | 基础编程 |
| HellaSwag | 常识推理 | 10K | 多选 |
| TruthfulQA | 事实性 | 817 | 反幻觉 |
| **MT-Bench** | 多轮对话 | 80 | **GPT-4评分** |
| **Arena-Hard** | 复杂指令 | 500 | **最强区分度** |
| **C-Eval** | 中文综合 | 14K | 中文基准 |

- **局限性:**
1. **数据污染** - 训练数据可能包含测试题
2. **过拟合** - 针对benchmark优化
3. **覆盖面** - 无法覆盖真实使用场景
4. **多选题偏差** - 真实任务不是选择题

- **推荐组合:** C-Eval + GSM8K + HumanEval + MT-Bench + 真实用户A/B测试

- **实战案例**：在评估某垂直领域客服模型时，尽管 MMLU 分数很高，但在处理带脏话的真实用户投诉时表现极差。这说明通用 Benchmarks 无法完全代表业务场景，必须构建包含“Bad Case”的内部 Eval 集合。

- **代码示例 (Python)**：
```python
# 使用 LM Evaluation Harness 自动化评估
import lm_eval
from lm_eval.models.huggingface import HFLM

model = HFLM(pretrained="meta-llama/Llama-2-7b-hf")
results = lm_eval.simple_evaluate(
    model=model,
    tasks=["hellaswag", "gsm8k"],  # 指定评估基准
    num_fewshot=5,
    batch_size=4
)
print(results["results"])
```

- **补充关键细节**：
  - **MMLU (Massive Multitask Language Understanding)**: 包含57个学科（STEM、人文、社科等），采用Few-shot（5-shot）设置测试模型的泛化能力。局限性在于多为选择题，无法评估模型的生成流畅度。
  - **GSM8K**: 评测多步数学推理能力，关键看模型是否能生成正确的解题步骤。SOTA模型通常需要使用外部工具（如代码解释器）或思维链才能达到高分。
  - **HumanEval**: 由OpenAI发布，包含164个Python编程问题。评估指标通常使用Pass@k（k=1,10），表示生成k个代码样本中至少有一个通过测试用例的概率。
  - **MT-Bench**: 侧重于多轮对话能力和指令遵循。由于人工评估昂贵，它利用GPT-4作为裁判来打分，这引入了“裁判偏见”（Judge Alignment）的问题。
  - **Arena-Hard (LMSYS)**: 基于Chatbot Arena的真实用户对战数据，精选了500个困难提示词。其核心优势在于区分度强，能很好区分GPT-4级别和Claude-3级别的模型。

```text
              ┌─────────────────────────────────────────────────────┐
              │                  LLM 评估全景图                      │
              └─────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│  静态基准      │       │  基于模型     │       │  人类评估      │
│  (Static)     │       │  (Model-based)│       │  (Human)      │
├───────────────┤       ├───────────────┤       ├───────────────┤
│ MMLU (知识)   │       │ MT-Bench      │       │ Chatbot Arena │
│ GSM8K (数学)  │ ────> │ (裁判打分)    │ ────> │ ( Elo Rating) │
│ HumanEval(代码)│      │ AlpacaEval    │       │ 真实A/B Test  │
└───────────────┘       └───────────────┘       └───────────────┘
```

## 记忆要点

- 知识基准：MMLU（多学科）、C-EVAL（中文），考察广度，多为选择题
- 能力基准：GSM8K（数学推理）、HumanEval（代码生成）、TruthfulQA（反幻觉）
- 对话基准：MT-Bench（多轮对话，GPT-4打分）、Arena-Hard（高难度，强区分度）
- 局限性：数据污染、过拟合、无法覆盖真实场景、多选题偏差
- 最佳实践：静态基准 + 模型裁判 + 真实业务A/B测试组合评估

## 结构化回答

**30 秒电梯演讲：** 评估基准像给模型"高考"，但高分不等于能干活。知识广度看 MMLU 和 C-Eval，逻辑推理看 GSM8K（数学）和 HumanEval（代码），对话体验看 MT-Bench 和 Arena-Hard。局限是数据污染、过拟合、多选题偏差、覆盖不了真实场景。最佳实践是静态基准加模型裁判加真实业务 A/B 测试组合评估。

**展开框架：**
1. **知识基准** — MMLU 覆盖多学科、C-Eval 覆盖中文，考察知识广度，多为选择题，特点是快速但只能考"知道不知道"。
2. **能力基准** — GSM8K 考数学推理、HumanEval 考代码生成、TruthfulQA 考反幻觉，针对的是模型的实际推理和生成能力。
3. **对话基准与局限** — MT-Bench 多轮对话用 GPT-4 打分、Arena-Hard 高难度强区分度；局限包括数据污染、过拟合、多选题偏差、无法覆盖真实业务场景，所以必须组合 A/B 测试。

**收尾：** 一句话，Benchmark 只是起点，真实业务效果才是终点。您想深入聊聊怎么检测 benchmark 过拟合，还是 LiveBench 怎么解决数据污染？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题《评估基准》+ 高考漫画 | 评估基准像给模型办高考，统一出题打分，但高分未必代表能干好真实工作。 | 类比开场 |
| 0:25 | 知识基准：MMLU / C-Eval | 知识广度看 MMLU 多学科、C-Eval 中文，多是选择题，快速考察"知道不知道"。 | 知识基准 |
| 0:55 | 能力基准：GSM8K / HumanEval / TruthfulQA | 逻辑能力看 GSM8K 数学推理、HumanEval 代码生成、TruthfulQA 反幻觉，针对实际推理。 | 能力基准 |
| 1:25 | 对话基准：MT-Bench / Arena-Hard | 对话体验看 MT-Bench 多轮对话用 GPT-4 打分，Arena-Hard 难度高、区分度强。 | 对话基准 |
| 1:50 | 局限 + 最佳实践组合图 | 局限是数据污染、过拟合、多选题偏差，所以最佳实践是静态基准加模型裁判加真实 A/B 测试。 | 局限与实践 |

