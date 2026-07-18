---
id: agmu-003
difficulty: L1
category: ai-agent
subcategory: 多智能体系统
feynman:
  essence: 通过隔离失败域和重试机制提升系统鲁棒性。
  analogy: 流水线坏了一个工人，只停那条线，整间工厂不倒闭。
  first_principle: 如何构建具备高可用性的容错协作系统？
  key_points:
  - 隔离：单点失败不污染全局
  - 替换：失败步骤可独立重试
  - 配合：重试、断路器、降级
  - 治理：仲裁机制防止推诿
memory_points:
- 核心体现：失败隔离（不污染主流程）与可替换性（沙箱执行）。
- 工程机制：指数退避重试、断路器防雪崩、降级模板兜底。
- 逻辑容错：需检测部分成功（格式对内容错），引入 Schema 校验层。
- 避坑指南：逻辑错误无限重试只会浪费 Token，需配合修改提示词策略。
frequency: medium
---

# 多 Agent 的「容错」具体怎么体现

### 多 Agent 的「容错」具体怎么体现

**核心体现**：失败隔离 + 可替换性。

**具体机制**：
- **失败隔离**：例如审查 Agent 发现实现 Agent 的代码不合规，可打回重写而不污染主对话上下文，避免错误传播。
- **沙箱隔离**：执行 Agent 运行代码在沙箱中，崩溃仅导致该任务失败，不影响调度器或其他 Agent。
- **状态回滚**：基于状态机的系统可在某步骤失败时回滚到上一个稳定状态。

**工程配套设施**：
- **重试策略**：指数退避重试，处理瞬时网络或模型 jitter 错误。
- **断路器**：当某个 Agent 连续失败 N 次，暂停调用，防止 Token 浪费和系统雪崩。
- **降级模板**：Agent 无响应时，返回预设的安全兜底回复。

**架构示意图**：
```
┌─────────────┐
│  Scheduler  │
└──────┬──────┘
       │ (Assign Task)
       ▼
┌─────────────┐     Fail      ┌──────────────┐
│  Agent A    │──────────────▶│  Retry Logic │
│  (Executor) │◀──────────────│ (Circuit Brk)│
└──────┬──────┘   Retry       └──────────────┘
       │ Success
       ▼
┌─────────────┐
│  Agent B    │
│  (Reviewer) │
└─────────────┘
```

**追问应对**：
若问「会不会互相甩锅？」——答：会。解决方案包括：明确每个 Agent 的输入输出契约、引入主席/仲裁机制裁决、记录全过程可观测日志用于事后定责。

### 深化实战
- **实战案例**：在生产环境中，API 解析 Agent 偶发因格式变化崩溃。由于没有熔断机制，导致下游调用该 Agent 的主流程不断重试，单小时消耗数千美元成本。后增加“失败计数器”，超过 3 次直接跳过该步骤返回默认值。
- **代码示例（Python - 带熔断的重试）**：
```python
from tenacity import retry, stop_after_attempt, wait_exponential

class CircuitBreaker:
    def __init__(self, threshold=3):
        self.fail_count = 0
        self.threshold = threshold
    
    def call_agent(self, agent_func, *args):
        if self.fail_count >= self.threshold:
            return "Fallback Response: Service Unavailable"
        try:
            res = agent_func(*args)
            self.fail_count = 0 # Reset on success
            return res
        except Exception:
            self.fail_count += 1
            raise
```

## 边界情况
- **部分成功/部分失败**：Agent 返回了 JSON 格式正确，但关键字段缺失或为 null 的情况。简单的 try-catch 无法捕获，必须增加 Schema 校验层作为容错的一部分。
- **逻辑死循环**：Agent 陷入“产生错误 -> 尝试修复 -> 再次产生错误”的无限循环，此时必须有“最大迭代次数”限制作为硬终止手段。
- **毒化输入**：上游 Agent 输出了无意义但符合格式的幻觉，导致下游 Agent 正常执行但得出错误结果（Garbage In, Garbage Out）。这属于逻辑层面的容错失效，需引入语义校验 Agent。

## 常见考点
1. **断路器在 Agent 系统中的参数怎么设置？**
   答：通常根据任务耗时和成本设定，例如连续 3 次超时或 5 次幻觉错误即熔断，熔断持续时间设为 1-5 分钟。
2. **如何处理部分成功的情况？**
   答：使用事务脚本或 Saga 模式，定义补偿操作，例如 Agent A 写入了数据但 Agent B 审核失败，需触发 Agent A 的回滚接口。

## 易错点
- **误区**：认为容错就是简单地无限重试。
  **正解**：对于 LLM 的逻辑错误或幻觉（如写死代码逻辑漏洞），无限重试只会浪费 Token 且产生相同结果，需配合“修改提示词”或“更换模型”的策略。
- **误区**：认为沙箱隔离就能保证绝对安全。
  **正解**：Agent 可能通过 Prompt Injection 攻击诱导沙箱外泄信息，或进行高资源消耗攻击（如无限循环），必须配合资源限制（Timeout/CPU Quota）。

## 面试追问
1. 如果某个 Agent 因为模型能力不足（而非网络抖动）持续失败，单纯的“重试”和“熔断”并不解决问题，你会设计什么样的“降级”或“路由”策略？
2. 在多 Agent 协作中，如果中间某个 Agent 挂了，是让整个流程 Fail-Fast（快速失败），还是记录状态等待人工介入？决策依据是什么？
3. 如何设计一套机制来自动检测 Agent 的输出是“幻觉”而非“有效但略有偏差”的结果？

## 核心流程图

```mermaid
flowchart TD
    Start([🚀 SQL 请求到达]):::start
    Parser[解析器 Parser<br/>词法/语法分析]:::process
    AST[生成抽象语法树 AST]:::process
    Preproc[预处理器<br/>语义检查 + 权限]:::process
    Optimizer[优化器 Optimizer]:::process
    CostQ{{基于代价选择?<br/>CBO}}:::decision
    IdxScan[索引扫描<br/>range/ref]:::process
    FullScan[全表扫描<br/>ALL]:::warn
    Execute[执行器 Executor<br/>调用存储引擎接口]:::process
    EngineQ{{存储引擎?<br/>InnoDB/MyISAM}}:::decision
    InnoDB[InnoDB 引擎]:::process
    BufferPool[Buffer Pool<br/>内存缓冲池]:::store
    HitQ{{页命中 Buffer Pool?}}:::decision
    ReadDisk[从磁盘读取页<br/>随机 IO]:::warn
    RedoLog[(redo log<br/>WAL 先写日志)]:::store
    BinLog[(binlog<br/>主从复制)]:::store
    UndoLog[(undo log<br/>事务回滚/MVCC)]:::store
    CommitQ{{是否提交事务?<br/>2PC}}:::decision
    TwoPhase[Prepare → 写 redo<br/>→ 写 binlog → Commit]:::process
    Crash[宕机崩溃恢复<br/>redo 重放 + binlog 校验]:::danger
    Final([✅ 返回结果集]):::start

    Start --> Parser --> AST --> Preproc --> Optimizer
    Optimizer --> CostQ
    CostQ -->|有合适索引| IdxScan --> Execute
    CostQ -->|无索引/全表| FullScan --> Execute
    Execute --> EngineQ
    EngineQ -->|默认| InnoDB --> BufferPool
    EngineQ -->|旧版| FullScan
    BufferPool --> HitQ
    HitQ -->|命中| Execute
    HitQ -->|未命中| ReadDisk --> BufferPool
    InnoDB -.修改.-> UndoLog
    InnoDB -.修改.-> RedoLog
    InnoDB -.提交.-> BinLog
    Execute --> CommitQ
    CommitQ -->|是| TwoPhase --> Final
    CommitQ -->|崩溃| Crash --> RedoLog

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef store fill:#8b5cf6,stroke:#6d28d9,color:#fff;
    classDef warn fill:#fee2e2,stroke:#ef4444,color:#7f1d1d;
    classDef danger fill:#b91c1c,stroke:#7f1d1d,color:#fff,stroke-width:2px;

```

## 记忆要点

- 核心体现：失败隔离（不污染主流程）与可替换性（沙箱执行）。
- 工程机制：指数退避重试、断路器防雪崩、降级模板兜底。
- 逻辑容错：需检测部分成功（格式对内容错），引入 Schema 校验层。
- 避坑指南：逻辑错误无限重试只会浪费 Token，需配合修改提示词策略。

## 结构化回答

**30 秒电梯演讲：** 多 Agent 容错核心是失败隔离加可替换性——审查 Agent 打回代码不污染主上下文，沙箱执行崩溃只影响该任务。工程配套是指数退避重试、断路器防雪崩、降级模板兜底。逻辑容错要检测部分成功（格式对内容错）引入 Schema 校验层。关键误区是逻辑错误无限重试只浪费 Token，要配合修改提示词。

**展开框架：**
1. **核心体现** — 失败隔离（不污染主流程）+ 可替换性（沙箱执行）+ 状态回滚（状态机回退到稳定状态）。
2. **工程配套** — 指数退避重试处理网络 jitter、断路器连续失败 N 次暂停防雪崩、降级模板无响应时返回安全兜底。
3. **逻辑容错与误区** — 检测部分成功用 Schema 校验层；逻辑错误无限重试只浪费 Token，需配合修改提示词或换模型。

**收尾：** 踩过坑——API 解析 Agent 偶发崩溃没熔断，下游主流程不断重试单小时烧数千美元，加失败计数器超 3 次跳过返回默认值后解决。您想聊哪块，断路器参数调优还是幻觉检测机制？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：多 Agent 容错怎么体现 | "流水线坏一个工人只停那条线，整间工厂不倒闭。" | 类比开场 |
| 0:15 | 失败隔离示意图 | "审查 Agent 打回不污染主流程，沙箱崩溃只影响该任务。" | 核心体现 |
| 0:45 | 工程配套三件套 | "指数退避重试、断路器防雪崩、降级模板兜底。" | 工程机制 |
| 1:10 | 逻辑容错警示 | "坑：格式对内容错的幻觉要 Schema 校验层兜底。" | 逻辑容错 |
| 1:35 | API 解析熔断案例 | "实战：没熔断单小时烧数千美元，加失败计数器解决。" | 实战教训 |
| 1:50 | 总结卡 | "记住：失败隔离 + 重试 + 断路器 + 降级。下期讲架构模式。" | 收尾 |

### 视频流程图

```mermaid
flowchart LR

    subgraph Intro["🎥 引入"]
        N0["多 Agent 容错怎么体现<br/>0:00"]:::intro
    end

    subgraph Core["📖 核心讲解"]
        N1["失败隔离示意图<br/>0:15"]:::core
        N2["工程配套三件套<br/>0:45"]:::core
        N3["逻辑容错警示<br/>1:10"]:::deep
    end

    subgraph Practice["🔧 实战"]
        N4["API 解析熔断案例<br/>1:35"]:::practice
    end

    subgraph Wrap["🎬 收尾"]
        N5["总结回顾 & 下期预告<br/>1:50"]:::wrap
    end

    N0 --> N1 --> N2 --> N3 --> N4 --> N5

    classDef intro fill:#FF9800,color:#fff
    classDef core fill:#2196F3,color:#fff
    classDef deep fill:#4CAF50,color:#fff
    classDef practice fill:#9C27B0,color:#fff
    classDef wrap fill:#607D8B,color:#fff
```


