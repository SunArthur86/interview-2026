---
id: dist-028
difficulty: L3
category: distributed
feynman:
  essence: 保证跨多个独立系统的一组操作要么全做，要么全不做。
  analogy: 跨行转账：A银行扣款和B银行加款必须同时成功，否则两边都退回。
  first_principle: 如何让分散在不同网络节点的数据操作像在单机一样保持一致性？
  key_points:
  - 涉及多个独立的资源节点（如不同数据库）
  - 需要一个协调者统一指挥
  - 遵循原子性原则，杜绝部分成功
  - 通常通过两阶段提交（2PC）等协议实现
memory_points:
- 一句话定义：跨多个网络节点的事务，需协调多方资源保证全局要么全成功要么全失败
- 强一致方案：2PC/XA（数据库原生，靠全局锁，性能极差，适合传统场景）
- 最终一致方案：TCC（高侵入高性能）、Saga（长流程）、Seata AT（无侵入主流）
- 对比记忆：因为高并发下强一致锁引发雪崩，所以互联网业务普遍采用柔性事务（最终一致）
---

# 什么是分布式事务？

分布式事务是指事务的参与者、支持事务的服务器、资源服务器以及事务管理器分别位于分布式系统的不同节点上。通过事务管理器协调多个资源管理器（如数据库），确保这些分散在不同节点的操作要么全部成功，要么全部失败，从而保持数据的一致性。

### 核心原理与补充细节
分布式事务的核心难点在于需要在网络不可靠（可能丢包、延迟）、节点可能宕机的情况下，保证 ACID 特性。

**关键协议：两阶段提交 (2PC)**
1.  **准备阶段**：协调者向所有参与者发送“准备”请求，参与者执行事务但不提交，写入 Undo 和 Redo 日志，并锁住资源，向协调者返回“成功”或“失败”。
2.  **提交阶段**：
    - 若所有参与者均回复“成功”，协调者发送“提交”指令，参与者正式提交并释放锁。
    - 若任一参与者回复“失败”或超时，协调者发送“回滚”指令，参与者利用 Undo 日志回滚。

**2PC 的缺陷**：
- **同步阻塞**：所有参与者在事务未提交前一直处于阻塞状态，占用锁资源，导致并发度低。
- **单点故障**：如果协调者在第二阶段发生故障，参与者将一直阻塞，无法知道是提交还是回滚。

### 实战案例
在电商下单场景中，订单库扣减库存和积分库增加积分需要保证一致性。早期使用 XA 事务导致数据库长连接过多，拖垮了库存服务的吞吐量。后来改用 Seata AT 模式，第一阶段释放本地锁，仅在回滚时进行补偿，吞吐量提升了约 5 倍，虽然牺牲了少许实时强一致性，但保证了高可用。

### 分布式事务解决方案对比
| 方案 | 一致性模型 | 实现复杂度 | 性能影响 | 适用场景 |
| :--- | :--- | :--- | :--- | :--- |
| **2PC / XA** | 强一致性 | 低（数据库原生支持） | 极高（全局锁，阻塞） | 传统后台，并发量不大，强一致要求高 |
| **TCC (Try-Confirm-Cancel)** | 最终一致性 | 高（需编写三个接口） | 中等（取决于业务逻辑） | 核心业务，对性能和一致性有要求，如金融支付 |
| **Saga** | 最终一致性 | 高（状态机定义） | 高（长事务占用资源） | 长流程业务，如旅游预订、订单流转 |
| **本地消息表** | 最终一致性 | 中 | 高（依赖 MQ 吞吐） | 跨系统异步通知，如支付成功后发短信 |
| **Seata AT** | 最终一致性 | 低（无侵入） | 中等（全局锁竞争） | 常见的互联网业务，Java 生态主流 |

## 常见考点
1. **2PC 和 3PC 的区别是什么？**（提示：3PC 引入了 CanCommit 阶段和超时机制，降低了阻塞范围，但无法彻底解决数据不一致问题）。
2. **XA 协议是强一致还是最终一致？**（提示：XA 是基于 2PC 的强一致性协议，但性能较差）。
3. **解决分布式事务的方案有哪些？**（提示：TCC、Saga、本地消息表、Seata 等）。

## 技术原理

分布式事务的核心难点是**在网络不可靠、节点可能宕机的环境下，让分散在多个节点的操作保持 ACID**。不同方案在"一致性强度"和"性能"间做不同权衡：

- **2PC/XA 的强一致与性能代价**：
  - **准备阶段**：协调者问所有参与者"能否提交"，参与者执行事务但只写 undo/redo 不提交，**锁住资源**，返回 yes/no。
  - **提交阶段**：全 yes 则发 commit，任一 no 或超时则发 rollback。
  - **缺陷**：准备阶段持有资源锁直到第二阶段结束，高并发下锁等待严重；协调者宕机会让所有参与者阻塞（单点故障）；网络分区时部分参与者收不到 commit 导致数据不一致。
- **TCC（Try-Confirm-Cancel）的最终一致**：把每个操作拆成三个接口——Try（预留资源，如冻结余额）、Confirm（真正扣减）、Cancel（解冻）。一阶段就提交本地事务释放锁，性能高；代价是业务侵入大（每个服务要写三个接口），且要处理 Confirm/Cancel 的重试和幂等。
- **Seata AT（无侵入主流方案）**：
  - 一阶段：各分支本地事务提交并释放本地锁，同时把"修改前镜像"和"修改后镜像"存到 undo_log 表。
  - 二阶段：全部成功则异步删除 undo_log；有失败则根据 undo_log 的前镜像**自动生成反向 SQL 补偿回滚**。
  - 优势是业务零侵入（只加 `@GlobalTransactional` 注解），代价是全局锁（TC 协调器管理）和短暂读写不一致。
- **本地消息表（最终一致，最轻量）**：本地事务 + 消息表写入放在同一个本地事务里保证原子性，后台定时扫描消息表发 MQ，下游消费后 ack。适合跨系统异步通知（支付成功发短信），不要求强一致。

## 代码示例

Seata AT 模式（互联网主流，无侵入）：

```java
import io.seata.spring.annotation.GlobalTransactional;
import org.springframework.stereotype.Service;

@Service
public class OrderService {
    @Autowired private StockFeignClient stockClient;
    @Autowired private OrderMapper orderMapper;
    @Autowired private PointsFeignClient pointsClient;

    // @GlobalTransactional 开启全局事务，AT 模式自动生成回滚镜像
    @GlobalTransactional(name = "create-order", timeoutMills = 60000, rollbackFor = Exception.class)
    public void createOrder(OrderDTO dto) {
        // 1. 扣库存（远程调用库存服务，Seata 自动记录前/后镜像到 undo_log）
        stockClient.deduct(dto.getProductId(), dto.getCount());
        // 2. 创建订单（本地事务，Seata 拦截 SQL 生成反向回滚 SQL）
        orderMapper.insert(dto);
        // 3. 加积分（远程调用积分服务）
        pointsClient.add(dto.getUserId(), dto.getAmount());
        // 任一步抛异常，Seata TC 自动协调所有分支用 undo_log 回滚
    }
}
```

```java
// TCC 模式（高侵入高性能，金融场景）
@LocalTCC
public interface StockTccAction {
    @TwoPhaseBusinessAction(name = "deductStock",
        commitMethod = "confirm", rollbackMethod = "cancel")
    boolean tryDeduct(BusinessActionContext ctx,
                      @BusinessActionContextParameter(paramName = "productId") Long productId,
                      @BusinessActionContextParameter(paramName = "count") Integer count);

    boolean confirm(BusinessActionContext ctx);   // 真正扣减
    boolean cancel(BusinessActionContext ctx);    // 解冻
}
// Try 阶段冻结库存（available_stock -= count, frozen_stock += count）
// Confirm 阶段扣减冻结（frozen_stock -= count）
// Cancel 阶段解冻（frozen_stock -= count, available_stock += count）
// Confirm/Cancel 必须幂等（可能被重试）
```

## 注意事项

- **强一致（2PC/XA）在互联网场景基本不用**：全局锁导致并发度极低，高并发下会拖垮整个链路。仅在传统金融核心（如银行核心账务）等并发量低但强一致要求极高的场景使用。
- **TCC 的 Confirm/Cancel 必须幂等**：网络抖动会导致 TC 重试调用，若不幂等会重复扣减/解冻。用业务流水号 + 状态机保证幂等。
- **Seata AT 有短暂读写不一致**：一阶段提交后、二阶段回滚前的窗口期，其他事务可能读到"将被回滚"的中间状态。对强一致读敏感的场景要配合全局锁或读已提交隔离。
- **本地消息表要处理重复消费**：MQ 可能重复投递，下游消费必须幂等（用唯一键去重）。消息表扫描 + MQ 发送要有重试和死信处理。
- **空回滚和悬挂问题（TCC）**：Try 请求因网络丢失但 Cancel 先到达时，要能识别"空回滚"（没 Try 就 Cancel）；Try 延迟到达 Cancel 之后时形成"悬挂"（业务已结束又 Try），要靠事务记录表防止。

## 记忆要点

- 一句话定义：跨多个网络节点的事务，需协调多方资源保证全局要么全成功要么全失败
- 强一致方案：2PC/XA（数据库原生，靠全局锁，性能极差，适合传统场景）
- 最终一致方案：TCC（高侵入高性能）、Saga（长流程）、Seata AT（无侵入主流）
- 对比记忆：因为高并发下强一致锁引发雪崩，所以互联网业务普遍采用柔性事务（最终一致）

## 结构化回答




**30 秒电梯演讲：** 跨行转账：A银行扣款和B银行加款必须同时成功，否则两边都退回。

**展开框架：**
1. **涉及多个独立** — 涉及多个独立的资源节点（如不同数据库）
2. **需要一个协调** — 需要一个协调者统一指挥
3. **遵循原子性原则** — 遵循原子性原则，杜绝部分成功

**收尾：** 这是我实战中的理解，您想深入哪一段？




## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：分布式事务 | "分布式事务，这题我会分三步讲。" | 开场钩子 |
| 0:41 | 概念定义动画 | "一句话：保证跨多个独立系统的一组操作要么全做，要么全不做。" | 核心定义 |
| 1:22 | 生活类比动画 | "打个比方——跨行转账：A银行扣款和B银行加款必须同时成功，否则两边都退回。" | 核心类比 |
| 2:03 | 涉及多个独立 图解 | "涉及多个独立的资源节点(如不同数据库)。" | 涉及多个独立 |
| 2:50 | 需要一个协调者统一 图解 | "需要一个协调者统一指挥。" | 需要一个协调者统一 |
