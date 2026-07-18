---
id: dist-006
difficulty: L2
category: distributed
feynman:
  essence: Raft易懂通用，ZAB专为ZooKeeper设计，都基于多数派原则。
  analogy: 都是投票选班长（Leader），Raft规则简单通用，ZAB针对特定学校（ZK）优化。
  first_principle: 如何在分布式环境中通过多数派共识保证数据的一致性和高可用？
  key_points:
  - 都依赖过半节点确认。
  - Raft核心是日志复制和任期。
  - ZAB核心是原子广播和崩溃恢复。
  - ZAB使用Zxid保证全局顺序。
memory_points:
- 共同基础：两者皆依赖 Quorum（过半机制）、Leader 驱动及心跳检测
- 设计目标：Raft 追求「通俗易懂与通用」，而 ZAB 专为 ZooKeeper「协调与高可用」设计
- 事务标识：Raft 使用 (Term, Index) 标识日志，而 ZAB 使用单一 Zxid（高32位纪元+低32位计数）
- 广播机制：Raft 直接追加复制并提交，而 ZAB 采用严格的 Proposal 和 Commit 两阶段广播
---

# Raft协议和ZAB协议有什么区别？

### Raft 协议和 ZAB 协议区别
两者都是分布式一致性算法，基于 Majority Quorum 机制，但设计理念和应用场景有所不同。

#### 相同点
1.  **Quorum 机制**：采用“过半数”原则来确定整个系统的一致性（N/2 + 1）。
2.  **Leader 驱动**：都由 Leader 来发起写操作（日志复制/事务提议），Follower 只负责处理来自 Leader 的请求。
3.  **心跳检测**：都通过心跳机制检测节点的存活性。
4.  **日志复制**：Leader 将日志追加到本地磁盘后，并行发送给 Follower，当收到过半确认后，认为日志已提交。

#### 不同点
1.  **设计目标与理念**：
    *   **Raft**：强调**易懂性**（Understandability）。将一致性分解为选主、日志复制、安全性三个相对独立的子问题，逻辑清晰，状态机模型简单。
    *   **ZAB**：专为 **ZooKeeper** 设计，侧重于构建高可用的**协调服务**。除了数据一致性，还需处理 Watcher 通知、会话管理等业务逻辑。

2.  **崩溃恢复与数据同步**：
    *   **Raft**：选举过程中，Follower 只会投给 Log 比自己新的 Candidate。新 Leader 选出后，通过 `AppendEntries` RPC 逐步同步 Follower 的日志（处理不一致日志通常采用“覆盖”或“回滚”策略）。
    *   **ZAB**：崩溃恢复阶段更复杂，分为 **Leader 选举** 和 **数据同步**。新 Leader 必须确保拥有所有已提交的事务。同步时，Follower 会将自己的 `lastZxid` 发送给 Leader，Leader 根据差异情况决定是发送快照、差异提议还是直接截断。ZAB 明确了“事务提议”和“事务提交”两个阶段的消息广播。

3.  **事务编号与顺序保证**：
    *   **Raft**：使用 `(Term, Index)` 组合唯一标识日志。Term 递增，Index 在 Term 内递增。
    *   **ZAB**：使用 **Zxid**（64 位长整型）。高 32 位是纪元，每次 Leader 变更自增；低 32 位是计数器，Leader 每提议一个事务递增。Zxid 保证了全局严格递增的顺序。

4.  **消息广播模式**：
    *   **Raft**：Leader 一旦收到请求，立即追加日志并复制，半数成功后立即提交并 Apply。
    *   **ZAB**：包含两个阶段：
        1.  **Proposal 广播**：Leader 发起提议。
        2.  **Commit 广播**：当过半 Follower ACK Proposal 后，Leader 再广播 Commit 消息，Follower 收到 Commit 后才真正应用数据到内存树。这种两阶段提交在 ZooKeeper 中用于保证事务顺序。

```text
ZAB 协议消息广播简化流程：

        Follower 1             Leader              Follower 2
            |                     |                     |
            |<---(1) Proposal------|                     |
            |                     |---(1) Proposal----->|
            |----(2) ACK--------->|<---(2) ACK----------|
            |                     |                     |
            |<---(3) Commit-------|---(3) Commit------->|
            |                     |
```

#### 实战对比表

| 维度 | Raft | ZAB |
| :--- | :--- | :--- |
| **核心目标** | 通用一致性，易于理解 | 服务协调，强一致性，支持高性能读 |
| **日志ID** | (Term, Index) | Zxid (Epoch << 32 | Counter) |
| **Leader 选举** | 选票 majority，先到先得 | 事务ID最大者（zxid最大）优先，保证数据最新
| **恢复阶段** | Leader 截断 Follower 冲突日志 | Follower 向 Leader 同步，Leader 决定同步策略(DIFF/SNAP)
| **消息流程** | AppendEntries(含Commit) | 两阶段：Proposal -> Commit |

#### 实战案例
ZAB 协议中的 Epoch 机制主要用于防止“幽灵复辟”。在实际生产中，曾出现过 Leader 假死（网络隔离）后重新加入集群的情况，依靠 Zxid 的高 32 位 Epoch 判断，旧 Leader 发起的提议会被新集群直接拒绝，避免了数据脏写。

#### 关键代码片段
```java
// ZooKeeper Zxid 结构简化示意
public long makeZxid(long epoch, long count) {
    return (epoch << 32) | (count & 0xFFFFFFFFL);
}

// ZAB Follower 处理 Proposal 伪代码
public void processProposal(Proposal p) {
    if (p.getZxid() < lastProcessedZxid) {
        return; // 拒绝旧事务
    }
    logToFile(p); // 先写日志
    ackToLeader(p.getZxid()); // 再回复 ACK
}
```

## 常见考点
1.  **Zxid 的结构是什么？**（答：64位，高32位 epoch，低32位计数器）
2.  **ZAB 协议的两阶段提交指的是哪两个阶段？**（答：Proposal 广播阶段和 Commit 广播阶段）
3.  **Raft 和 ZAB 在处理日志不一致时的策略有何不同？**（答：Raft 是 Leader 强制覆盖 Follower 的冲突日志；ZAB 是 Leader 根据差异发送 DIFF 或 SNAP，Follower 主动同步。）



## 核心知识点图

<img src="/interview-2026/images/diagram_distributed_dist-006.svg" alt="Raft协议和ZAB协议有什么区别？" style="max-width:100%;height:auto;border:1px solid var(--border);border-radius:8px;margin:1em 0;" />

## 记忆要点

- 共同基础：两者皆依赖 Quorum（过半机制）、Leader 驱动及心跳检测
- 设计目标：Raft 追求「通俗易懂与通用」，而 ZAB 专为 ZooKeeper「协调与高可用」设计
- 事务标识：Raft 使用 (Term, Index) 标识日志，而 ZAB 使用单一 Zxid（高32位纪元+低32位计数）
- 广播机制：Raft 直接追加复制并提交，而 ZAB 采用严格的 Proposal 和 Commit 两阶段广播

## 结构化回答




**30 秒电梯演讲：** 都是投票选班长（Leader），Raft规则简单通用，ZAB针对特定学校（ZK）优化。

**展开框架：**
1. **都依赖** — 都依赖过半节点确认。
2. **Raft** — Raft核心是日志复制和任期。
3. **ZAB** — ZAB核心是原子广播和崩溃恢复。

**收尾：** 这是我实战中的理解，您想深入哪一段？




## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：Raft协议和ZAB协议有什么区别 | "Raft协议和ZAB协议有什么区别，一分钟讲透。" | 开场钩子 |
| 0:35 | 生活类比动画 | "打个比方——都是投票选班长(Leader)，Raft规则简单通用，ZAB针对特定学校(ZK)优化。" | 核心类比 |
| 1:10 | 概念定义动画 | "一句话：Raft易懂通用，ZAB专为ZooKeeper设计，都基于多数派原则。" | 核心定义 |
| 1:50 | 都依赖过半节点确认 图解 | "都依赖过半节点确认。" | 都依赖过半节点确认 |
