---
id: bd-ai-java-004
difficulty: L4
category: scenario
subcategory: 系统设计
tags:
- 字节
- 面经
- Agent
- 上下文漂移
- 记忆管理
- Java
feynman:
  essence: 通过分层记忆和目标锚定防止任务跑偏。
  analogy: 像考试时时刻盯着题目（目标），把草稿纸折起来存（压缩）。
  first_principle: 如何在有限的上下文窗口内保持长期对话的连贯性？
  key_points:
  - 每轮Prompt重申原始目标锚定方向
  - 短期记忆用摘要替代历史对话
  - 长期记忆存向量数据库，按需检索
follow_up:
- 上下文腐化（Lost in the Middle）是什么？——中间位置的信息注意力下降，需把重要信息放首尾
- 记忆衰减怎么做？——时间权重 + 访问频率 + 相关性评分综合排序
- Java 生态向量数据库选型？——Milvus（大规模）/ Qdrant（轻量）/ Redis Vector（简单场景）
memory_points:
- 治漂移根因：每轮Prompt强制注入原始目标，并附“已完成列表”防重复执行
- 压缩策略对比：滑动窗口省Token但丢信息，对话摘要法保真度高
- 分层记忆架构：当前约束(工作)、近N轮(短期)、向量库(长期)、快照(事件)
- Java实操：发请求前必用JTokKit预计算Token，超限则触发动态截断
---

# 【字节面经】如何解决 Agent 的上下文漂移问题？如何在有限上下文窗口内做短期和长期记忆压缩？

**上下文漂移问题：** Agent 在多轮执行中跑偏了，忘了最初的任务目标。

**解决方案（Java 架构视角）：**

**1. 每轮注入原始目标** — 在每轮 System Prompt 中重复用户的原始需求，相当于不断提醒 Agent 别跑偏。用 Spring AI 可以在每次调用时自动注入。

**2. 阶段性总结** — Agent 每执行 N 步用模型总结当前进度，用摘要替代原始完整对话，既能控制 Token 量又能保持方向。

**3. 分层记忆架构：**
- 工作记忆 (Working Memory) → System Prompt（当前任务约束）
- 短期记忆 (Short-term Memory) → 最近 N 轮对话（滑动窗口）
- 长期记忆 (Long-term Memory) → 向量数据库（Redis/Milvus）
- 事件记忆 (Episodic Memory) → 执行日志（Checkpoints）

**短期记忆压缩策略：**
| 策略 | 原理 | Token节省 | 信息损失 |
|------|------|-----------|----------|
| 滑动窗口 | 只保留最近 N 轮 | 高 | 高（早期全丢） |
| 对话摘要 | 模型总结早期对话 | 中 | 低 |
| 重要信息提取 | 单独存关键决策 | 中 | 极低 |

**长期记忆实现（Java + Redis Vector）：**
用 RedisTemplate 存储记忆内容+向量+时间戳，检索时用向量相似度+时间衰减排序。Spring AI 的 VectorStore 抽象可以统一适配 Milvus/Qdrant/Redis/PGVector。

**记忆衰减机制：** 不是所有历史信息都同等重要，越早的信息权重越低，结合访问频率和相关性评分定期清理过期记忆。

**实战案例：**
在一个代码重构 Agent 中，随着对话轮次增加，Agent 开始修改它自己在第 1 轮刚写好的代码，陷入死循环。通过引入“关键决策快照”，在 Prompt 中显式列出“已完成的任务列表（Do not touch again）”，成功将重构任务的完成率从 60% 提升至 90%。

**Token 优化代码片段（使用 JTokKit）：**
```java
// 在发送请求前预计算 Token，防止超限或浪费
EncodingRegistry registry = EncodingRegistry.newDefaultInstance();
Encoding enc = registry.getEncoding(Cl100kBase.ID);
int tokens = enc.countTokens(message); 
if (tokens > MAX_INPUT_TOKENS) {
    // 执行摘要逻辑或滑动窗口截断
    message = summarizeOrTruncate(message);
}
```

## 常见考点
1. **数据结构选择**：为什么长期记忆首选向量数据库而非关系型数据库？答案：Agent 的查询通常是语义化的（模糊匹配），向量数据库支持语义相似度检索，而 MySQL/Like 只支持精确或简单模式匹配。
2. **Checkpoint 机制**：如果 Agent 中途崩溃，如何恢复？答案：利用 Event Memory 记录每一步的 State Snapshot（快照）。重启时，从最后一个成功的 Checkpoint 恢复 State 和 Prompt Context。
3. **Token 优化细节**：在 Java 中如何高效管理 Token 统计？答案：可以使用 TikToken 的 Java 移植版（如 `jtokkit`）在发送请求前预计算 Token 数，动态截断 Context。

## 记忆要点

- 治漂移根因：每轮Prompt强制注入原始目标，并附“已完成列表”防重复执行
- 压缩策略对比：滑动窗口省Token但丢信息，对话摘要法保真度高
- 分层记忆架构：当前约束(工作)、近N轮(短期)、向量库(长期)、快照(事件)
- Java实操：发请求前必用JTokKit预计算Token，超限则触发动态截断

## 结构化回答


**30 秒电梯演讲：** 像考试时时刻盯着题目（目标），把草稿纸折起来存（压缩）。

**展开框架：**
1. **每轮Prompt** — 重申原始目标锚定方向
2. **短期记忆用摘要替** — 短期记忆用摘要替代历史对话
3. **长期记忆存向量数据库** — 长期记忆存向量数据库，按需检索

**收尾：** 上下文腐化（Lost in the Middle）是什么？


## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：解决 Agent 的上下文漂移问题 | "解决 Agent 的上下文漂移问题，30 秒讲清楚核心。" | 开场钩子 |
| 0:45 | 概念定义动画 | "一句话：通过分层记忆和目标锚定防止任务跑偏。" | 核心定义 |
| 1:30 | 生活类比动画 | "打个比方——像考试时时刻盯着题目(目标)，把草稿纸折起来存(压缩)。" | 核心类比 |
| 2:15 | 每轮Prompt重申 图解 | "每轮Prompt重申原始目标锚定方向。" | 每轮Prompt重申 |
| 3:00 | 短期记忆用摘要替代历 图解 | "短期记忆用摘要替代历史对话。" | 短期记忆用摘要替代历 |
| 3:50 | 长期记忆存向量数据库 图解 | "长期记忆存向量数据库，按需检索。" | 长期记忆存向量数据库 |
