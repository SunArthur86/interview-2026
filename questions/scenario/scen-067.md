---
id: scen-067
difficulty: L2
category: scenario
subcategory: 高并发系统设计
tags:
- 排行榜
- Redis ZSet
- 实时更新
- 分桶策略
- 多维排序
feynman:
  essence: 利用有序结构高效存储分数，实现实时排名更新与查询。
  analogy: 像运动会记分牌，一有新成绩立刻更新位置，随时能看前几名。
  first_principle: 如何在高并发读写场景下快速维持和查询海量数据的有序状态？
  key_points:
  - Redis ZSet天然支持排序，O(logN)更新
  - 多维榜单分Key存储（日/周/月）
  - 大数据量分桶处理或冷热分离
  - 变更消息驱动前端实时刷新
follow_up:
- 亿级用户的排名如何快速查询？
- 如何实现好友排行榜？
- 实时排行榜如何推送更新？
memory_points:
- 核心结构：Redis ZSet天然排序，亿级数据因单Key过载，所以需分桶/分片ZSet分散压力
- 核心命令：ZINCRBY更新分数，ZREVRANK拿排名，均需结合Lua脚本保证原子性
- 高并发写入：用户行为入MQ异步消费，避免整点活动结算导致单线程CPU打饱和
- 同分排名处理：将微小时间戳偏移量混入Score（score + (now-base)/1e9），完美解决同分按先后排
- 深翻页优化：大偏移量ZREVRANGE极慢，所以改用ZCOUNT或反向查找避免性能雪崩
---

# 如何设计一个排行榜系统？支持亿级用户、实时更新、多种维度排序。

【场景分析】
排行榜需求：游戏积分榜、电商销量榜、直播人气榜、社交影响力榜。

**实战案例**：在日活千万的手游中，曾遇到全服排行榜在活动结算时（整点写入）RT飙升至2秒的问题，原因是单Key ZSet过大导致CPU单核饱和。采用“主榜热Key+分片冷Key”策略后，P99降低到50ms。

【Redis ZSet方案（最常用）】
- ZSet天然排序：score排序 + member存储
- 核心命令：
  - `ZADD rank:score {score} {userId}` — 添加/更新
  - `ZREVRANK rank:score {userId}` — 获取排名
  - `ZREVRANGE rank:score 0 99` — 获取Top100
  - `ZINCRBY rank:score {delta} {userId}` — 增加分数

```redis
# Lua脚本保证原子性：加分并返回当前排名
-- KEYS[1]: leaderboard key
-- ARGV[1]: user_id, ARGV[2]: score_delta
local newScore = redis.call('ZINCRBY', KEYS[1], ARGV[2], ARGV[1])
local rank = redis.call('ZREVRANK', KEYS[1], ARGV[1])
return {newScore, rank}
```

【多维排行榜】
- 日榜：`rank:daily:{date}`
- 周榜：`rank:weekly:{week}`
- 月榜：`rank:monthly:{month}`
- 总榜：`rank:total`
- 定时归档 + 合并计算

【亿级用户优化】
1. 分桶策略：
   - 用户ID hash到不同桶
   - 每个桶独立ZSet
   - 查全局排名需要合并
2. 近似排名：
   - 不需要精确排名时用近似值
   - 如：分数>10000 → 前1%
3. 冷热分离：
   - 活跃用户实时更新
   - 不活跃用户批量更新

【实时更新流程】
```
用户行为(下单/消费/互动) → MQ
  → 消费者计算积分增量
  → Redis ZINCRBY更新分数
  → 推送给在线用户（WebSocket）
```

【排行榜数据结构选择】
| 场景 | 数据结构 | 优点 |
|------|----------|------|
| <千万 | Redis ZSet | 简单高效 |
| 千万-亿 | 分桶ZSet | 分散压力 |
| >亿 | 跳表+LSM | 可扩展 |
| 精确排名 | ZSet | O(log n) |
| 近似排名 | Count-Min Sketch | 省内存 |

【特殊排行榜设计】
1. 并列排名：
   - 同分数相同排名
   - ZSet天然支持（score相同时按member字典序）
2. 分页排名：
   - 只取TOP N（不需要全量排名）
3. 好友排名：
   - 只展示好友中的排名
   - 好友ID集合 + ZSet交集

【数据持久化】
- Redis定期持久化到MySQL
- 历史排行榜归档查询
- 排行榜数据用于数据分析

【## 常见考点】】
1. **写入性能瓶颈**：当大量用户分数同时变化（如活动结算），Redis 写入吞吐量不足如何处理？（Local Cache 聚合写入、分片并行写入、临时牺牲一致性）
2. **ZSet 内存问题**：亿级数据 ZSet 内存占用过高，除了分桶还有什么办法？（使用 Redis 的 `ziplist` 编码配置优化，或迁移至 Sorted Set on Disk 解决方案如 LevelDB）
3. **同分排名逻辑**：ZSet 默认同分按字典序，若需按时间先后排名，如何实现？（Score 设计为 `原始分数 + 微小时间戳偏移量`，如 `score + (now - base)/1e9`）
4. **分页查询深翻问题**：获取排名 100 万之后的用户，为什么慢？（ZSET 的 `ZRANGE` 复杂度与偏移量相关，深翻性能极差；应改为 `ZCOUNT` 统计或反向查询，避免大偏移量分页）

## 记忆要点

- 核心结构：Redis ZSet天然排序，亿级数据因单Key过载，所以需分桶/分片ZSet分散压力
- 核心命令：ZINCRBY更新分数，ZREVRANK拿排名，均需结合Lua脚本保证原子性
- 高并发写入：用户行为入MQ异步消费，避免整点活动结算导致单线程CPU打饱和
- 同分排名处理：将微小时间戳偏移量混入Score（score + (now-base)/1e9），完美解决同分按先后排
- 深翻页优化：大偏移量ZREVRANGE极慢，所以改用ZCOUNT或反向查找避免性能雪崩

## 结构化回答




**30 秒电梯演讲：** 像运动会记分牌，一有新成绩立刻更新位置，随时能看前几名。

**展开框架：**
1. **Redis** — Redis ZSet天然支持排序，O(logN)更新
2. **Key** — 多维榜单分Key存储（日/周/月）
3. **大数据量分桶** — 大数据量分桶处理或冷热分离

**收尾：** 亿级用户的排名如何快速查询？




## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：排行榜系统 | "排行榜系统，一分钟讲透。" | 开场钩子 |
| 0:35 | 生活类比动画 | "打个比方——像运动会记分牌，一有新成绩立刻更新位置，随时能看前几名。" | 核心类比 |
| 1:10 | 概念定义动画 | "一句话：利用有序结构高效存储分数，实现实时排名更新与查询。" | 核心定义 |
| 1:50 | Redis 图解 | "Redis ZSet天然支持排序，O(logN)更新。" | Redis |
