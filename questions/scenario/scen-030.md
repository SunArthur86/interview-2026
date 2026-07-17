---
id: scen-030
difficulty: L2
category: scenario
subcategory: 支付与交易
tags:
- 幂等
- 防重提交
- 唯一索引
- Token
- 乐观锁
- 状态机
- 分布式锁
feynman:
  essence: 为请求分配唯一标识，通过去重机制保证同一操作只生效一次。
  analogy: 像电影票，每张票有唯一座位号，检票时撕角，想拿同一张票再看第二场会被拒绝。
  first_principle: 如何消除网络重试或用户误操作带来的重复执行风险？
  key_points:
  - 前端：Token机制防表单重复提交
  - 后端：唯一索引防DB重复插入
  - 状态机：利用条件更新防重复处理
  - 分布式：Redis SETNX实现并发控制
follow_up:
- Token机制如何防止并发？
- MQ消费幂等用什么方案？
- 乐观锁和悲观锁的适用场景？
memory_points:
- 本质定义：相同请求执行多次，产生的副作用与执行一次完全相同
- 方案对比：Token防表单重复提交，唯一索引防并发创建，状态机/乐观锁防状态乱序更新
- Token实现：服务端发UUID给前端，提交时用Lua脚本原子get并删Redis，成功才执行业务
- 高并发兜底：前端防抖+Token拦截+DB唯一索引三层防御，DuplicateKeyException捕获转友好提示
---

# 如何设计一个防重提交/幂等方案？适用于下单、支付等核心业务。

【场景分析】
重复提交场景：
- 前端：用户快速双击“提交”按钮
- 网络：客户端超时重试
- 后端：MQ消息重复投递
- 第三方：支付渠道重复回调

【幂等定义】
**Idempotency**：对于同一个请求，无论执行多少次，系统产生的副作用（状态改变）与执行一次完全相同。

【核心实现方案对比】
1. **数据库唯一索引**：
   - 原理：利用DB的强一致性约束，对`biz_no`（业务单号）建唯一索引
   - 场景：INSERT操作（如创建订单）
   - 优点：绝对可靠，基于DB锁
   - 缺点：依赖数据库，无法处理UPDATE
2. **Token机制（防重复提交）**：
   - 原理：
     1. 服务端生成Token (`UUID`) 存入Redis，并返回给前端
     2. 前端提交表单时携带Token
     3. 服务端删除Redis中的Token（Lua脚本保证原子性：get+del）
     4. 删除成功则处理业务，删除失败则拒绝
   - 场景：表单提交、按钮防抖
   - 关键：Token必须是一次性的（用完即毁）
3. **乐观锁（版本号/CAS）**：
   - 原理：`UPDATE account SET balance = balance - 100, version = version + 1 WHERE id = 1 AND version = old_version`
   - 场景：扣减库存、更新余额
   - 关键：通过影响行数判断是否成功（row=1成功，row=0失败）
4. **状态机约束（条件更新）**：
   - 原理：利用业务状态流转的约束，拒绝非法状态变更
   - SQL：`UPDATE orders SET status = 'PAID' WHERE id = ? AND status = 'UNPAID'`
   - 场景：订单状态流转、支付回调
5. **分布式锁**：
   - 原理：`SETNX key value PX 30000`，获取锁成功则执行业务
   - 场景：高并发下的写入/读取缓存
   - 注意：需配合业务逻辑判断状态（如先查后写），锁只是保护代码块串行
6. **独立去重表**：
   - 原理：建立独立的`dedup_table`，包含`unique_key`和`response_content`
   - 流程：先INSERT去重表（唯一索引防重），成功后再处理业务，最后更新去重表状态
   - 场景：MQ消费者、复杂的异步回调

【架构流程图：Token机制】
```
 Client                Server (Redis)           Database
  │                      │                       │
 │──(1) Get Token ──────>│                       │
 │<──── Token ───────────│                       │
 │                      │                       │
 │──(2) Submit Form ────>│                       │
 │      (携带Token)      │                       │
 │                      │──(3) Del Token? ─────>│ (Optional: Log)
 │                      │                       │
 │<──── 409 Conflict ───│ (if Token not exist)  │
 │                      │                       │
 │<──── 200 OK ─────────│ (if Del Success)      │
 │                      │──(4) Execute Biz ────>│
```

【实现示例 - 订单创建幂等】
```java
@Transactional
public void createOrder(OrderRequest req) {
    // 1. Token防重（防止前端重复点击）
    String tokenKey = "order:token:" + req.getToken();
    boolean isLock = redisTemplate.delete(tokenKey); // 原子操作
    if (!isLock) {
        throw new BusinessException("请勿重复提交");
    }
    
    try {
        // 2. 数据库唯一索引兜底（防止网络重试/并发）
        Order order = new Order(req.getBizNo(), ...);
        orderMapper.insert(order); 
        // ... 后续业务逻辑
    } catch (DuplicateKeyException e) {
        // 3. 异常捕获后返回“订单已存在”，避免报错给前端
        log.warn("Duplicate order creation: {}", req.getBizNo());
        throw new BusinessException("订单已创建，请勿重复操作");
    }
}
```

## 常见考点
1. **Token机制 vs 分布式锁**：Token机制是一次性的，且必须伴随删除操作；分布式锁通常有超时释放，且处理完业务后主动释放，适用于保护复杂代码段。
2. **幂等Key设计**：如何设计唯一ID？（UUID、雪花算法、业务号+时间戳+随机数）。如果是GET请求，如何做幂等？（通常只能靠前端限制或服务端缓存结果）。
3. **MQ消费幂等**：如果消费失败导致消息重回队列，如何保证不重复扣款？（先查去重表，或利用数据库唯一索引做Insert Select Where Not Exists）。
4. **并发边界**：如果两个请求同时通过Redis Token校验怎么办？（Redis单线程模型保证了原子性，delete是串行的；但若后端处理慢，需配合DB唯一索引兜底）。

## 记忆要点

- 本质定义：相同请求执行多次，产生的副作用与执行一次完全相同
- 方案对比：Token防表单重复提交，唯一索引防并发创建，状态机/乐观锁防状态乱序更新
- Token实现：服务端发UUID给前端，提交时用Lua脚本原子get并删Redis，成功才执行业务
- 高并发兜底：前端防抖+Token拦截+DB唯一索引三层防御，DuplicateKeyException捕获转友好提示

## 结构化回答

**30 秒电梯演讲：** 为请求分配唯一标识，通过去重机制保证同一操作只生效一次。打比方——像电影票，每张票有唯一座位号，检票时撕角，想拿同一张票再看第二场会被拒绝。落到工程上，Token机制防表单重复提交。

**展开框架：**
1. **前端** — Token机制防表单重复提交
2. **后端** — 唯一索引防DB重复插入
3. **状态机** — 利用条件更新防重复处理

**收尾：** 这几个点都能配合实战展开。您想继续聊哪个追问——比如 「Token机制如何防止并发」 或者 「MQ消费幂等用什么方案」？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：防重提交/幂等方案 | "防重提交/幂等方案，一分钟讲透。" | 开场钩子 |
| 0:35 | 生活类比动画 | "打个比方——像电影票，每张票有唯一座位号，检票时撕角，想拿同一张票再看第二场会被拒绝。" | 核心类比 |
| 1:10 | 概念定义动画 | "一句话：为请求分配唯一标识，通过去重机制保证同一操作只生效一次。" | 核心定义 |
| 1:50 | 前端 图解 | "Token机制防表单重复提交。" | 前端 |
