---
id: agmu-014
difficulty: L1
category: ai-agent
subcategory: 多智能体系统
tags:
- 熔断
feynman:
  essence: 通过步数、状态指纹和预算熔断防止无限循环。
  analogy: 给机器人设死线、防重复记忆和超时自动断电。
  first_principle: 如何在非确定性系统中保证执行的终止性？
  key_points:
  - 步数：全局最大步数限制
  - 去重：状态哈希检测重复
  - 进展：关键指标监控
  - 熔断：Token或时间预算
memory_points:
- 检测死循环需组合策略：步数上限、状态哈希去重、无进展检测。
- 哈希粒度选关键参数，避免微小差异导致失效。
- 预算熔断是保护成本的最后一道防线。
frequency: high
---

# 如何检测多 Agent 系统的「死循环」

检测多 Agent 系统的「死循环」需要 **组合策略**，单一方法往往会有漏网之鱼。
1. **全局步数上限**：最简单粗暴的硬熔断，设置 Agent 交互的最大轮次（如 50 步）。
2. **状态哈希去重**：若连续重复同一计划、同一工具入参或产生完全相同的输出，则判定为死循环。
3. **无进展检测**：监控关键指标（如 `tokens_spent` 增加，但 `task_completion_score` 不变，或者 `error_count` 未降）。
4. **预算熔断**：基于 Token/费用/时间的绝对阈值。

**死循环检测流程图**：
```text
[ Start Loop ]
      │
      ├─▶ Check: Step Count > Max? ──Yes──▶ [ Abort: Max Steps ]
      │
      ├─▶ Check: Hash(Current State) in History?
      │      │                               │
      │     Yes                              No
      │      │                               │
      ▼      ▼                               ▼
[ Abort: Repeated State ]           Check: Progress Delta < Threshold?
                                          │            │
                                         Yes           No
                                          │            │
                                          ▼            ▼
                                 [ Abort: No Progress ]   [ Continue ]
```

**关键细节补充**：
- **哈希粒度**：不要对整个 Context 窗口做哈希，只对「Action Plan」或「Tool Call Arguments」做哈希，避免因长对话日志微小差异导致哈希失效。
- **滑动窗口**：有些循环是周期性的（A->B->C->A），需要维护一个固定大小的历史状态窗口（如最近 5 步）进行比对。
- **人为介入**：在触发熔断前，可以尝试插入一个「人类审核」节点，确认是否真的陷入死循环。

**实战案例**：在一次实现 Agent 自动纠错代码的迭代中，遇到模型在「修复报错」和「回滚修改」之间来回拉锯的死循环。因为每次生成的代码略有不同，简单的字符串对比失效。后来改用对「工具调用的 JSON 参数」做 MD5 哈希去重，成功检测到了该无限循环并自动触发中断，节省了大量 API 费用。

**代码示例**：
```python
import hashlib

class LoopGuard:
    def __init__(self, max_steps=20, history_len=5):
        self.max_steps = max_steps
        self.state_history = []  # 滑动窗口
        self.step_count = 0

    def check_break(self, current_action: dict) -> bool:
        self.step_count += 1
        
        # 1. 全局步数熔断
        if self.step_count > self.max_steps:
            return True
        
        # 2. 状态哈希去重 (只比对关键参数)
        action_sig = hashlib.md5(str(current_action).encode()).hexdigest()
        if action_sig in self.state_history:
            return True
            
        # 维护滑动窗口
        self.state_history.append(action_sig)
        if len(self.state_history) > self.history_len:
            self.state_history.pop(0)
            
        return False
```

**检测策略对比**：

| 策略 | 优点 | 缺点 | 适用场景 |
| :--- | :--- | :--- | :--- |
| **步数上限** | 实现简单，零漏报 | 可能误杀正常长流程 | 所有流程的兜底防线 |
| **状态哈希** | 精准识别重复逻辑 | 对微小差异不敏感 (需规范化) | 代码纠错、工具调用循环 |
| **无进展检测** | 更符合业务逻辑 | 定义“进展”指标困难 | 创作类、分析类任务 |
| **预算熔断** | 直接保护成本 | 无法区分正常与异常消耗 | 严格控制预算的场合 |

**追问应对**：若问「误杀怎么办？」——答：提高进展定义粒度、允许人类确认继续，或者增加恢复策略（如切换 Prompt 模板重试）。

## 常见考点
1. **状态哈希**：如何实现高效的状态去重？（答：使用布隆过滤器或 Redis Set 存储 Hash，注意设置过期时间）。
2. **无进展定义**：如何量化「进展」？（答：基于特定 Token 的出现（如 [DONE]）、任务状态位的变化，或者使用 Critic Agent 评分）。

## 核心流程图

```mermaid
flowchart TD
    Start([🚀 应用发起读请求]):::start
    App[应用层<br/>查询数据]:::client
    CacheHitQ{{缓存命中?}}:::decision
    ReturnCache["直接返回缓存数据<br/>O(1) 低延迟"]:::process
    MissDB{缓存未命中}:::decision
    QueryDB[查询数据库<br/>执行 SQL]:::process
    PenetrateQ{{是否为恶意请求?<br/>查询不存在的 key}}:::decision
    BloomFilter[布隆过滤器拦截<br/>+ 缓存空值]:::process
    BreakDownQ{{热点 key 失效?<br/>缓存击穿}}:::decision
    Mutex[加互斥锁<br/>单线程回源]:::process
    AvalancheQ{{大批 key 同时过期?<br/>缓存雪崩}}:::decision
    TTLJitter[随机 TTL<br/>+ 多级缓存]:::process
    WriteBackQ{{是否回写缓存?}}:::decision
    WriteCache[写入 Redis<br/>设置 TTL]:::process
    BigKeyCheck{{大 Key / 热 Key?}}:::decision
    SplitKey[拆分大 Key<br/>本地缓存热 Key]:::process
    DB[(MySQL 主从<br/>持久化数据)]:::store
    Cache[(Redis Cluster<br/>分片缓存)]:::store
    Final([✅ 返回结果]):::start
    Alarm[告警 + 限流降级]:::danger

    Start --> App --> CacheHitQ
    CacheHitQ -->|命中| ReturnCache --> BigKeyCheck
    BigKeyCheck -->|是| SplitKey --> Final
    BigKeyCheck -->|否| Final
    CacheHitQ -->|未命中| MissDB --> PenetrateQ
    PenetrateQ -->|是| BloomFilter --> Alarm
    PenetrateQ -->|否| BreakDownQ
    BreakDownQ -->|是| Mutex --> QueryDB
    BreakDownQ -->|否| AvalancheQ
    AvalancheQ -->|是| TTLJitter --> QueryDB
    AvalancheQ -->|否| QueryDB
    QueryDB --> DB --> WriteBackQ
    WriteBackQ -->|是| WriteCache --> Cache --> ReturnCache
    WriteBackQ -->|否| ReturnCache

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef client fill:#10b981,stroke:#047857,color:#fff;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef store fill:#8b5cf6,stroke:#6d28d9,color:#fff;
    classDef danger fill:#b91c1c,stroke:#7f1d1d,color:#fff,stroke-width:2px;

```

## 记忆要点

- 检测死循环需组合策略：步数上限、状态哈希去重、无进展检测。
- 哈希粒度选关键参数，避免微小差异导致失效。
- 预算熔断是保护成本的最后一道防线。

## 结构化回答

**30 秒电梯演讲：** 检测多 Agent 死循环要组合策略，单一方法有漏网之鱼。四招：全局步数上限（最粗暴的硬熔断）、状态哈希去重（连续重复同一计划或工具入参判定死循环）、无进展检测（tokens_spent 增但 task_completion_score 不变）、预算熔断（Token/费用/时间阈值）。关键是哈希粒度选关键参数（Action Plan 或 Tool Call Arguments）不做整个 Context 哈希，避免微小差异失效。

**展开框架：**
1. **四招组合** — 步数上限（兜底零漏报但可能误杀）、状态哈希去重（精准识别重复逻辑）、无进展检测（符合业务逻辑但定义进展困难）、预算熔断（直接保护成本）。
2. **哈希与窗口** — 只对 Action Plan 或 Tool Call Arguments 做哈希不做整个 Context；周期性循环（A→B→C→A）维护固定大小滑动窗口比对。
3. **误杀处理** — 提高进展定义粒度、允许人类确认继续、增加恢复策略（切换 Prompt 模板重试）。

**收尾：** 做 Agent 自动纠错代码时踩过坑——模型在"修复报错"和"回滚修改"间拉锯，字符串对比失效，改用工具调用 JSON 参数做 MD5 哈希去重成功检测并节省大量 API 费用。您想聊哪块，哈希粒度选择还是无进展指标定义？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：怎么检测多 Agent 死循环 | "给机器人设死线、防重复记忆和超时自动断电。" | 类比开场 |
| 0:15 | 四招组合策略 | "步数上限、状态哈希、无进展检测、预算熔断四招组合。" | 检测策略 |
| 0:45 | 哈希粒度警示 | "坑：哈希只对关键参数不做整个 Context，避免微小差异失效。" | 关键细节 |
| 1:10 | 滑动窗口示意 | "周期性循环 A→B→C→A 要滑动窗口比对最近 N 步。" | 周期检测 |
| 1:35 | 代码纠错案例 | "实战：修复/回滚拉锯，JSON 参数 MD5 哈希检测省费用。" | 实战教训 |
| 1:50 | 总结卡 | "记住：组合四招 + 关键参数哈希 + 滑动窗口。下期讲错误隔离。" | 收尾 |

### 视频流程图

```mermaid
flowchart LR

    subgraph Intro["🎥 引入"]
        N0["怎么检测多 Agent 死循环<br/>0:00"]:::intro
    end

    subgraph Core["📖 核心讲解"]
        N1["四招组合策略<br/>0:15"]:::core
        N2["哈希粒度警示<br/>0:45"]:::deep
        N3["滑动窗口示意<br/>1:10"]:::deep
    end

    subgraph Practice["🔧 实战"]
        N4["代码纠错案例<br/>1:35"]:::practice
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


