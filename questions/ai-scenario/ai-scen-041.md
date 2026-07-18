---
id: ai-scen-041
difficulty: L2
category: ai-scenario
subcategory: AI推荐与搜索
tags:
- 简历筛选
- 信息抽取
- JD匹配
- 公平性
- 偏见消除
- 语义匹配
feynman:
  essence: 结构化解析简历，语义匹配JD，规则+AI综合评分。
  analogy: 像HR助理先筛选硬条件，再由资深HR评估软实力。
  first_principle: 如何将非结构化文本转化为结构化的人才匹配决策？
  key_points:
  - 多格式解析与结构化抽取
  - JD与简历的语义对齐
  - 规则硬约束+LLM软评估
  - 偏见消除与可解释决策
follow_up:
- 如何确保AI筛选不存在性别/年龄歧视？
- 简历格式多样性如何处理？
- 如何衡量筛选系统的效果？
memory_points:
- 流程：简历解析(LayoutLM/LLM) → JD建模 → 规则过滤 → 语义匹配。
- 解析方案：LayoutLMv3微调为主，LLM辅助校验，正则淘汰。
- 匹配引擎：硬性条件(学历/年限)漏斗过滤 + Embedding语义匹配。
- 实体对齐：构建技能图谱，解决AWS与Amazon Web Services归一。
- 易错点：关键词匹配需防Java包含JavaScript误判。
---

# 如何设计一个AI简历筛选系统？日均处理10000+简历，自动匹配岗位要求。

【场景分析】
AI简历筛选系统需求：日均处理10000+简历，自动匹配岗位要求，减少HR 80%的初筛工作量。核心挑战是非结构化文本解析、精准的语义匹配以及公平性合规。

【Pipeline架构】
1. **简历解析层**：
   - **格式处理**：利用PyMuPDF (PDF) 或 python-docx 提取文本。针对扫描件使用OCR（如PaddleOCR或Tesseract）。
   - **信息抽取 (IE)**：
     - *方案A*：微调小模型（如LayoutLMv3）进行实体抽取，成本可控且准确率高。
     - *方案B*：使用LLM进行Few-shot抽取，适合复杂项目经历解析。
   - **结构化输出**：统一输出为JSON Schema（包含：Personal_Info, Skills, Experience, Education, Projects）。
   - **实体对齐**：解决"AWS"与"Amazon Web Services"，"React"与"React.js"的同义/层级归一问题。

2. **岗位需求建模 (JD Parsing)**：
   - **要素提取**：从JD中提取Must-have（硬性门槛：学历、年限、核心技能）和Nice-to-have（软性偏好：框架熟悉度、行业背景）。
   - **技能图谱构建**：构建技能的上下位关系（如："PyTorch" 属于 "Deep Learning"），用于隐性技能匹配。

3. **匹配引擎**：
   - **规则匹配（漏斗）**：
     - 硬性条件过滤（学历>=本科、年限>=3年、必须包含Python）。
     - *边界条件*：处理"3-5年"这种区间匹配，以及"应届生"的特殊逻辑。
   - **语义匹配**：
     - 计算Resume Embedding与JD Embedding的余弦相似度。
     - *细节*：使用Domain-Specific的Embedding模型（如基于RoBERTa在招聘语料上微调）。
   - **LLM深度评估**：
     - 输入：Structured Resume + Structured JD。
     - 任务：评估"项目经历的相关性"、"技能覆盖度"、"成长轨迹"。
     - 输出：JSON格式的评分（0-100） + 缺失技能列表 + 匹配理由。

4. **排序与推荐**：
   - **综合评分**：Score = w1 * 规则匹配分 + w2 * 向量相似度 + w3 * LLM评分。
   - **HR Workbench**：提供搜索、过滤、以及AI生成的面试问题建议。
   - **相似推荐**：利用向量检索找到"与当前高绩效员工相似的候选人"。

【实战案例】
- **踩坑经验**：在早期版本中，简单的关键词匹配导致大量误判（如要求"Java"，简历中出现"JavaScript"也被匹配）。引入技能图谱层级树和Embedding语义距离阈值后，解决了"包含但不等于"的误判问题。

【关键代码实现（工作年限计算）】
```python
from dateutil.relativedelta import relativedelta
from datetime import datetime

def calculate_work_experience(start_date_str, end_date_str="Present"):
    """
    计算工作年限，处理'Present'及日期格式容错
    """
    start = datetime.strptime(start_date_str, "%Y-%m")
    end = datetime.now() if end_date_str == "Present" else datetime.strptime(end_date_str, "%Y-%m")
    
    diff = relativedelta(end, start)
    total_years = diff.years + diff.months / 12.0
    return round(total_years, 1)

# 示例：处理硬性条件过滤
def is_qualified(resume_json, jd_requirements):
    if resume_json['education_degree'] not in jd_requirements['allowed_degrees']:
        return False
    if calculate_work_experience(resume_json['start_date']) < jd_requirements['min_years']:
        return False
    return True
```

【解析方案对比】
| 维度 | 方案A: LayoutLMv3 (微调) | 方案B: LLM (Few-shot) | 方案C: 正则/规则 |
| :--- | :--- | :--- | :--- |
| **准确率** | 高（尤其对排版复杂的简历） | 极高（具备泛化推理能力） | 低（极其依赖模板） |
| **成本** | 中（训练一次，推理便宜） | 高（每次推理Token消耗大） | 低（仅CPU计算） |
| **速度** | 快（<1s） | 慢（3-5s，受限于LLM API） | 极快（ms级） |
| **维护性** | 中（需标注数据微调） | 易（修改Prompt即可） | 差（新模板需重写Regex） |
| **推荐策略** | **首选：作为实体抽取基础服务** | 辅助：用于关键信息的二次校验 | 淘汰：仅用于特定字段清洗 |

【系统处理流程图】
```text
[Resume Upload]  [JD Input]
      │               │
      ▼               ▼
┌───────────┐   ┌───────────┐
│ OCR/Text  │   │ JD Parser │
│  Extract  │   │(LLM/Rules)│
└─────┬─────┘   └─────┬─────┘
      │               │
      ▼               │
┌─────────────┐       │
│ Resume Info │       │
│ Extraction  │       │
│  (Entity)   │       │
└─────┬───────┘       │
      │               │
      └───────┬───────┘
              ▼
     ┌────────────────┐
     │  Normalization │ (Skills, Time, Edu)
     └───────┬────────┘
             │
             ▼
    ┌──────────────────┐
    │  Matching Engine │
    │ 1. Hard Filter   │
    │ 2. Vector Sim    │
    │ 3. LLM Reasoning │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │   Scoring & Rank │
    └──────────────────┘
```

## 核心知识点图

<img src="/interview-2026/images/diagram_ai-scenario_ai-scen-041.svg" alt="如何设计一个AI简历筛选系统？日均处理10000+简历，自动匹配岗位要求。 - 核心知识点图" style="max-width:100%;height:auto;border:1px solid var(--border);border-radius:8px;margin:1em 0;" />

## 记忆要点

- 流程：简历解析(LayoutLM/LLM) → JD建模 → 规则过滤 → 语义匹配。
- 解析方案：LayoutLMv3微调为主，LLM辅助校验，正则淘汰。
- 匹配引擎：硬性条件(学历/年限)漏斗过滤 + Embedding语义匹配。
- 实体对齐：构建技能图谱，解决AWS与Amazon Web Services归一。
- 易错点：关键词匹配需防Java包含JavaScript误判。


## 结构化回答

**30 秒电梯演讲：** 结构化解析简历，语义匹配JD，规则+AI综合评分。——打个比方，像HR助理先筛选硬条件，再由资深HR评估软实力。

**展开框架：**
1. **流程** — 简历解析(LayoutLM/LLM) → JD建模 → 规则过滤 → 语义匹配。
2. **解析方案** — LayoutLMv3微调为主，LLM辅助校验，正则淘汰。
3. **匹配引擎** — 硬性条件(学历/年限)漏斗过滤 + Embedding语义匹配。

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「如何确保AI筛选不存在性别/年龄歧视」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "设计一个AI简历筛选系统，30 秒讲清楚。" | 开场钩子 |
| 0:30 | 概念定义动画 | "一句话：结构化解析简历，语义匹配JD，规则+AI综合评分。" | 核心定义 |
| 1:00 | 流程图解 | "简历解析(LayoutLM/LLM) → JD建模 → 规则过滤 → 语义匹配。" | 流程 |
| 1:30 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
