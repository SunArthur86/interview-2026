---
id: scen-012
difficulty: L2
category: scenario
subcategory: 高并发系统设计
tags:
- 签到系统
- Bitmap
- Redis
- 连续签到
- HyperLogLog
- 数据归档
feynman:
  essence: 利用位图的极简存储与位运算高效处理连续状态。
  analogy: 像挂历，每天打个勾，用0和1标记有无签到，超级省纸。
  first_principle: 如何以最小存储成本高效记录和统计海量用户的周期性状态？
  key_points:
  - Bitmap位运算极大节省空间
  - BITFIELD或位运算计算连续签到
  - Key按年月分片方便管理
  - 异步持久化保证性能
follow_up:
- Bitmap如何统计连续签到天数？
- 如何处理跨年签到？
- 签到数据如何做冷热分离？
memory_points:
- 核心结构：因为签到是状态布尔值，所以完美适配Redis Bitmap结构。
- 极致压缩：Key设计按月聚合，单用户一月仅占31位约4字节，彻底防OOM。
- 核心指令：记录用SETBIT，统计总数用BITCOUNT，算连续天数用BITFIELD。
- 存储分离：明细存Redis，全站活动总人数统计交由HyperLogLog去重计算。
- 冷热隔离：近3个月热数据留存Redis，历史签到冷数据归档至MySQL或ES。
---

# 如何设计一个签到打卡系统？支持亿级用户每日签到 + 签到统计。

### 场景分析
签到特点：写多（每日亿级）、读少（主要查自己）、数据有时间维度、连续签到奖励。

### 核心数据结构 — Bitmap
Redis Bitmap 完美适配签到场景：
- Key: `sign:{userId}:{yyyyMM}`
- Bit 位：第 N 位表示当月第 N 天是否签到
- 1 个用户 1 个月只需 31 bit ≈ 4 字节
- 亿级用户 × 12 月 ≈ 50GB（可接受）

### 核心操作
1. 签到：`SETBIT sign:{uid}:{ym} {day} 1`
2. 查某天是否签到：`GETBIT sign:{uid}:{ym} {day}`
3. 统计当月签到天数：`BITCOUNT sign:{uid}:{ym}`
4. 连续签到天数：`BITFIELD sign:{uid}:{ym} GET u{day}` → 从后往前数连续 1

### 架构设计
1. **签到写入**
   - 用户签到 → Redis Bitmap 写入 → 异步 MQ → 统计 DB
   - 签到奖励：检查连续天数 → 发放积分/优惠券
2. **签到统计**
   - 个人维度：Bitmap 直接统计
   - 活动维度（如某活动总签到人数）：HyperLogLog
   - 全站统计：定时聚合写入 ClickHouse

### 补签机制
- 允许补签前 N 天
- 补签需要消耗积分或道具
- Bitmap 支持任意位置设置

### 数据归档
- 热数据（近 3 个月）：Redis
- 冷数据（3 个月前）：迁移到 MySQL/ES

### 扩展功能
- 签到日历可视化
- 团队/小组签到排行榜
- 签到提醒推送（Push 通知）

### 实战案例
在双11大促活动中，曾遇到因 Redis Key 设计为 `sign:{uid}:{yyyy-MM-dd}` 导致 Key 数量爆炸，内存碎片化严重，引起 OOM。后优化为月维度 Key，内存占用降低90%，且利用 `BITOP` 命令能极速计算团队全员签到情况。

### 代码示例 (Java + Redisson)
```java
// 获取用户当月签到状态（返回二进制位串，如"11011"）
RLock lock = redissonClient.getLock("sign_lock:" + uid);
lock.lock();
try {
    // 设置第5天签到（offset从0开始，所以是4）
    redissonClient.getBitSet("sign:{uid}:202310").set(4, true);
    // 统计当月签到次数
    long count = redissonClient.getBitSet("sign:{uid}:202310").cardinality();
} finally {
    lock.unlock();
}
```

## 记忆要点

- 核心结构：因为签到是状态布尔值，所以完美适配Redis Bitmap结构。
- 极致压缩：Key设计按月聚合，单用户一月仅占31位约4字节，彻底防OOM。
- 核心指令：记录用SETBIT，统计总数用BITCOUNT，算连续天数用BITFIELD。
- 存储分离：明细存Redis，全站活动总人数统计交由HyperLogLog去重计算。
- 冷热隔离：近3个月热数据留存Redis，历史签到冷数据归档至MySQL或ES。

## 结构化回答




**30 秒电梯演讲：** 像挂历，每天打个勾，用0和1标记有无签到，超级省纸。

**展开框架：**
1. **Bitmap** — Bitmap位运算极大节省空间
2. **BITFIELD** — BITFIELD或位运算计算连续签到
3. **Key** — Key按年月分片方便管理

**收尾：** Bitmap如何统计连续签到天数？




## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：签到打卡系统 | "签到打卡系统，一分钟讲透。" | 开场钩子 |
| 0:35 | 生活类比动画 | "打个比方——像挂历，每天打个勾，用0和1标记有无签到，超级省纸。" | 核心类比 |
| 1:10 | 概念定义动画 | "一句话：利用位图的极简存储与位运算高效处理连续状态。" | 核心定义 |
| 1:50 | Bitmap位运算极 图解 | "Bitmap位运算极大节省空间。" | Bitmap位运算极 |
