---
id: scen-085
difficulty: L2
category: scenario
subcategory: 稳定性与容灾
tags:
- 监控
- 秒杀监控
- 实时大屏
- 链路追踪
- 告警体系
- SkyWalking
- Metrics
feynman:
  essence: 全链路数据埋点与实时告警，确保秒杀过程可观测。
  analogy: 像给赛车装几十个传感器，仪表盘实时显示转速、油温，异常立刻报警。
  first_principle: 如何在瞬时高流量下，快速发现系统瓶颈并定位故障根因？
  key_points:
  - 四维监控：业务指标、系统资源、链路追踪、日志
  - 实时大屏：可视化QPS、库存、成功率趋势
  - 分级告警：P0电话，P1短信，P2钉钉
  - 关键埋点：入口、成功、失败、耗时全记录
follow_up:
- 秒杀场景的关键监控指标有哪些？
- 如何设计秒级告警？
- 活动后如何做性能分析？
memory_points:
- 工具铁三角：Prometheus看指标数值，SkyWalking查链路拓扑，ELK捞文本日志。
- 精细化埋点：核心接口需打上业务Tag（如UserId、成功或失败原因），方便追踪特定问题。
- 立体监控维度：不仅盯业务成功率与QPS，更要监控Redis/MQ等基础依赖组件的健康度。
- 告警分级：P0级超卖/宕机需电话拉起，P1级异常波动/P99延迟走高发钉钉告警。
---

# 如何设计一个秒杀系统的全链路追踪和监控？

【场景分析】
秒杀活动持续时间短、流量大，需要完善的监控才能快速发现和定位问题。

**【实战代码示例】**
```java
// 基于Micrometer的精细化埋点
@RestController
public class SeckillController {
    private final MeterRegistry registry;
    
    @PostMapping("/do-seckill")
    public Result doSeckill(@RequestParam Long userId, @RequestParam Long goodsId) {
        return Timer.Sample.start(registry).stop(timerBuilder("seckill.api.latency")
            .tag("user_id", String.valueOf(userId)) // 便于追踪特定用户问题
            .register(registry))
            .record(() -> {
                // 业务逻辑
                boolean success = seckillService.execute(userId, goodsId);
                registry.counter("seckill.result", "status", success ? "success" : "fail").increment();
                return success ? Result.ok() : Result.fail();
            });
    }
}
```

**【实战案例】**
某次秒杀中，监控显示成功率仅50%，但后端服务QPS远低于阈值。通过全链路TraceId追踪发现，大量请求在"获取验证码"环节超时。深挖原因是验证码服务依赖的Redis Cluster正在进行节点迁移，导致部分Key槽不可用。**经验总结**：秒杀监控不仅要关注业务指标，更要关注依赖基础组件的健康度。

【监控维度】
1. 业务指标：
   - 秒杀QPS/成功数/失败数
   - 库存消耗速度
   - 订单创建延迟
   - 支付转化率
2. 系统指标：
   - CPU/内存/网络/磁盘
   - JVM GC/线程数
   - Redis QPS/连接数/内存
   - MySQL QPS/慢查询/连接数
   - MQ 积压量/消费延迟
3. 链路追踪：
   - SkyWalking记录全链路
   - 慢请求TopN
   - 错误请求定位

**【监控工具选型对比】**

| 维度 | Prometheus + Grafana | SkyWalking | ELK Stack |
| :--- | :--- | :--- | :--- |
| **核心能力** | 指标监控 & 可视化 | APM (调用链/拓扑图) | 日志聚合 & 检索 |
| **数据类型** | 数值 | 链路/调用关系 | 文本日志 |
| **秒杀场景作用**| 实时大屏、资源瓶颈定位 | 接口慢查询分析、异常报错 | 故障复盘、详细日志排查 |

【实时大屏】
```
┌─────────────────────────────────────────┐
│  秒杀监控大屏                    时间   │
├──────────┬──────────┬──────────┬───────┤
│  QPS     │  成功率   │  库存    │ RT    │
│  10.2w   │  98.5%   │  328/1000│ 45ms  │
├──────────┴──────────┴──────────┴───────┤
│  [实时QPS曲线]                          │
│  [库存消耗曲线]                         │
│  [错误类型分布]                         │
└─────────────────────────────────────────┘
```

【告警体系】
1. P0（电话+短信）：
   - 库存异常（超卖/负数）
   - 成功率骤降
   - 核心服务宕机
2. P1（钉钉+短信）：
   - QPS异常波动
   - RT P99 > 1秒
   - MQ积压 > 1万
3. P2（钉钉）：
   - 缓存命中率下降
   - 错误率上升

【关键监控点设计】
```java
// 秒杀入口埋点
@Metered("seckill.request")
public Result seckill(Long userId, Long skuId) {
    Timer.Sample sample = Timer.start();
    try {
        // 业务逻辑
        Metrics.counter("seckill.success").increment();
        return Result.success();
    } catch (Exception e) {
        Metrics.counter("seckill.fail", "reason", e.getClass().getSimpleName()).increment();
        throw e;
    } finally {
        sample.stop(registry.timer("seckill.duration"));
    }
}
```

【活动后分析】
- 秒杀链路全链路时间线
- 各环节耗时占比
- 系统瓶颈分析
- 容量使用率
- 改进建议

## 记忆要点

- 工具铁三角：Prometheus看指标数值，SkyWalking查链路拓扑，ELK捞文本日志。
- 精细化埋点：核心接口需打上业务Tag（如UserId、成功或失败原因），方便追踪特定问题。
- 立体监控维度：不仅盯业务成功率与QPS，更要监控Redis/MQ等基础依赖组件的健康度。
- 告警分级：P0级超卖/宕机需电话拉起，P1级异常波动/P99延迟走高发钉钉告警。

## 结构化回答

**30 秒电梯演讲：** 全链路数据埋点与实时告警，确保秒杀过程可观测。打比方——像给赛车装几十个传感器，仪表盘实时显示转速、油温，异常立刻报警。落到工程上，业务指标、系统资源、链路追踪、日志。

**展开框架：**
1. **四维监控** — 业务指标、系统资源、链路追踪、日志
2. **实时大屏** — 可视化QPS、库存、成功率趋势
3. **分级告警** — P0电话，P1短信，P2钉钉

**收尾：** 这几个点都能配合实战展开。您想继续聊哪个追问——比如 「秒杀场景的关键监控指标有哪些」 或者 「如何设计秒级告警」？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：秒杀系统的全链路追踪和监控 | "秒杀系统的全链路追踪和监控，一分钟讲透。" | 开场钩子 |
| 0:35 | 生活类比动画 | "打个比方——像给赛车装几十个传感器，仪表盘实时显示转速、油温，异常立刻报警。" | 核心类比 |
| 1:10 | 概念定义动画 | "一句话：全链路数据埋点与实时告警，确保秒杀过程可观测。" | 核心定义 |
| 1:50 | 四维监控 图解 | "业务指标、系统资源、链路追踪、日志。" | 四维监控 |
