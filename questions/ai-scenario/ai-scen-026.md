---
id: ai-scen-026
difficulty: L2
category: ai-scenario
subcategory: LLM推理与部署
tags:
- Token成本
- 模型路由
- 语义缓存
- 成本归因
- 预算管理
- 降本增效
feynman:
  essence: 按任务难度分级路由模型，配合缓存与精简控制成本。
  analogy: 出租车分级：近距离骑单车（小模型），远距离打专车（大模型），省钱又高效。
  first_principle: 如何在保证效果的前提下，最小化每次推理的Token消耗？
  key_points:
  - 路由器判断任务难度，分级调用不同大小模型
  - Prompt精简、语义缓存和早停减少Token消耗
  - 设置租户和用户级Token预算配额
  - 结构化输出避免模型生成废话
follow_up:
- 模型路由的难度分类器如何训练？
- 如何在不影响回答质量的前提下精简Prompt？
- 成本归因的粒度应该多细？
memory_points:
- 模型路由（核心）：简单任务用7B，复杂用GPT-4，整体成本可降50-70%。
- 请求层优化：Prompt精简、上下文裁断（只留Top K文档）、限制max_tokens。
- 缓存层：语义缓存命中30%直接省30%成本，适合高频重复问题。
- 预算管理：租户/用户/功能三级配额，超额限流，实时告警。
- 成本估算：日均10万次请求，全GPT-4约$300/天，路由优化混合约$80/天。
frequency: high
---

# 如何设计LLM的Token成本控制系统？在不降低用户体验的前提下削减50%以上成本。

【场景分析】
LLM Token成本是企业AI应用的核心运营指标。需要从请求层、模型层、缓存层多维度控制。

**【实战案例】**
某SaaS知识库问答系统，初期盲目使用GPT-4，导致月成本$5万无法落地。通过“小模型意图分类+长文本截断+Prompt精简”三步走：1. 使用Qwen-7B判断意图，非复杂问题拦截；2. 检索Top 3文档而非Top 10，上下文长度缩减60%；3. 将Prompt中的CoT（思维链）指令压缩。最终在不影响准确率的前提下，单次调用成本降低了70%，月成本降至$1.5万。

【成本控制架构】
1. 请求层优化：
   - Prompt精简：去除冗余指令，用简洁模板
   - 上下文裁剪：只保留最相关的历史和检索结果
   - 请求合并：多个短请求合并为一次批量请求
   - 提前终止：检测到完整答案后停止生成
2. 模型路由（成本核心）：
   - 分级路由：
     - 简单FAQ → 7B模型（成本$0.01/1K tokens）
     - 常规对话 → 32B模型（成本$0.05/1K tokens）
     - 复杂推理 → 70B/GPT-4（成本$0.20/1K tokens）
   - 路由判断：用小模型分类请求难度
   - 效果：整体成本可降低50-70%
3. 缓存层：
   - 语义缓存：命中缓存不消耗Token
   - 命中率30% → 直接节省30%成本
4. 输出控制：
   - max_tokens限制：防止冗长输出
   - 结构化输出：JSON模式减少废话
   - 温度调优：低温度减少重复生成

【Token预算管理】
- 租户级配额：每月Token上限，超额限流或收费
- 功能级配额：不同功能不同预算（核心功能优先保障）
- 用户级配额：防止单用户消耗过多资源
- 实时告警：消耗达到80%预算时告警

【成本归因与报表】
维度：租户 × 用户 × 功能 × 模型 × Prompt版本 × 时间
用途：识别成本热点、优化投入产出比、预算规划

【典型成本估算】
日均10万次请求，平均每次500 input + 200 output tokens：
- GPT-4 Turbo: 约$300/天
- GPT-4o-mini: 约$15/天
- 自建vLLM (72B): 约$50/天（含GPU折旧）
- 路由优化后混合: 约$80/天 → 降本73%

**【代码示例：Prompt压缩与截断】**
```python
from transformers import AutoTokenizer

def truncate_context(prompt: str, max_len: int = 4000):
    # 获取Tokenizer
    tokenizer = AutoTokenizer.from_pretrained("gpt-4")
    
    # 1. 强制系统指令部分保留（System Prompt不可截断）
    sys_end = prompt.find("\n\nUser:")
    sys_part = prompt[:sys_end]
    user_part = prompt[sys_end:]
    
    # 2. 截断用户部分（保留后部，因为通常包含最新的关键信息）
    tokens = tokenizer.encode(user_part)
    sys_tokens = tokenizer.encode(sys_part)
    
    # 3. 计算剩余可用Token数
    remaining = max_len - len(sys_tokens)
    if len(tokens) > remaining:
        tokens = tokens[-remaining:] # 尾部截断
        
    return tokenizer.decode(sys_tokens + tokens)
```

**【路由策略成本对比】**

| 路由策略 | 准确率影响 | 成本倍数 | 实现复杂度 | 适用场景 |
| :--- | :--- | :--- | :--- | :--- |
| **全量GPT-4** | 基准 | 10x | 低 | 高价值、低频次场景（医疗诊断） |
| **意图分级路由** | -2% ~ -5% | 1.5x | 中 | **通用客服、知识问答（推荐）** |
| **全量Mini/7B** | -10% ~ -20% | 0.2x | 低 | 简单意图识别、文本分类 |
| **长短文分离** | 无 | 0.7x | 低 | 文档摘要、长对话 |

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
    class B process
    class C decision
    class D special
    class E1 error
    class E2 info
    class E3 start
    class F process
    class G decision
    class GPT special
    class H error
    class I info
    class J start
    class K process
    class L decision
    class br special
    A["用户请求<br/>(LLM调用)"] --> B["请求层预处理<br/>(Prompt精简与上下文裁剪)"]
    B --> C{"语义缓存<br/>命中?"}
    C -- "命中 (省Token)" --> H["直接返回缓存结果"]
    C -- "未命中" --> D["小模型路由器<br/>(7B分类器)"]
    
    D -- "简单FAQ" --> E1["7B小模型<br/>($0.01/1K)"]
    D -- "常规对话" --> E2["32B中模型<br/>($0.05/1K)"]
    D -- "复杂推理" --> E3["70B/GPT-4大模型<br/>($0.20/1K)"]
    
    E1 --> F["输出层控制<br/>(限制max_tokens与JSON格式化)"]
    E2 --> F
    E3 --> F
    
    F --> G["Token计费与成本归因"]
    G --> H
    
    subgraph I ["预算与配额管理 (并行拦截)"]
        J["租户级配额限制"]
        K["功能/用户级配额"]
        L["实时消耗告警 (达80%)"]
    end
    
    I -.-> A
```

## 记忆要点

- 模型路由（核心）：简单任务用7B，复杂用GPT-4，整体成本可降50-70%。
- 请求层优化：Prompt精简、上下文裁断（只留Top K文档）、限制max_tokens。
- 缓存层：语义缓存命中30%直接省30%成本，适合高频重复问题。
- 预算管理：租户/用户/功能三级配额，超额限流，实时告警。
- 成本估算：日均10万次请求，全GPT-4约$300/天，路由优化混合约$80/天。

## 结构化回答

**30 秒电梯演讲：** 出租车分级：近距离骑单车（小模型），远距离打专车（大模型），省钱又高效。

**展开框架：**
1. **路由器判断任务难度** — 分级调用不同大小模型
2. **Prompt精简** — 语义缓存和早停减少Token消耗
3. **设置租户和用户级** — 设置租户和用户级Token预算配额

**收尾：** 模型路由的难度分类器如何训练？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "设计LLM的Token成本控制系统，30 秒讲清楚。" | 开场钩子 |
| 0:30 | 概念定义动画 | "一句话：按任务难度分级路由模型，配合缓存与精简控制成本。" | 核心定义 |
| 1:00 | 模型路由（核心）图解 | "简单任务用7B，复杂用GPT-4，整体成本可降50-70%。" | 模型路由（核心） |
| 1:30 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |

### 视频流程图

```mermaid
flowchart LR

    subgraph Intro["🎥 引入"]
        N0["设计LLM的Token成本控制系统<br/>0:00"]:::intro
    end

    subgraph Core["📖 核心讲解"]
        N1["按任务难度分级路由模型，配合缓存与精简控制成本。<br/>0:30"]:::core
    end

    subgraph Practice["🔧 实战"]
        N2["模型路由（核心）图解<br/>1:00"]:::practice
    end

    subgraph Wrap["🎬 收尾"]
        N3["总结回顾 & 下期预告<br/>1:30"]:::wrap
    end

    N0 --> N1 --> N2 --> N3

    classDef intro fill:#FF9800,color:#fff
    classDef core fill:#2196F3,color:#fff
    classDef deep fill:#4CAF50,color:#fff
    classDef practice fill:#9C27B0,color:#fff
    classDef wrap fill:#607D8B,color:#fff
```


