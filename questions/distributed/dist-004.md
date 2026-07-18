---
id: dist-004
difficulty: L2
category: distributed
feynman:
  essence: 同时修改源IP和目的IP，允许LVS和RS跨网段部署。
  analogy: 快递中转站（LB）改了发件人和收件人地址，收件人回信也寄给中转站。
  first_principle: 如何突破物理网络限制，让负载均衡器能调度任意网段的后端服务器？
  key_points:
  - 双向NAT：同时改写源IP和目的IP。
  - 解决LVS与RS必须在同一网段的限制。
  - RS获取真实客户端IP较难。
  - 适合大型跨机房集群部署。
memory_points:
- 核心原理：同时修改源 IP（CIP转DIP）和目的 IP（VIP转RIP），实现双向 NAT
- 组网优势：因为 RS 网关无需指向 LB，所以支持跨 VLAN 和跨机房网络部署
- 真实IP痛点：因为源 IP 被替换，所以 RS 无法直接获取真实 CIP，必须依赖 TOA 模块或 HTTP 头
- 性能代价：因为要维护海量的四元组连接追踪表，所以比 DR 模式更消耗内存
---

# LVS FULLNAT模式的工作原理是什么？

### LVS FULLNAT 模式工作原理
无论是 DR 还是 NAT 模式，LVS 和 Real Server (RS) 必须在同一个 VLAN 下（因为 LVS 需作为 RS 的网关）。这带来的两个问题是：
1. 同一个 VLAN 的限制导致运维不方便，跨 VLAN 的 RS 无法接入。
2. LVS 的水平扩展受到制约。

Full-NAT 由此而生，解决的是 LVS 和 RS 跨 VLAN 的问题。Full-NAT 相比 NAT 的主要改进是，在 SNAT/DNAT 的基础上，同时转换源 IP 和目的 IP。

**转换过程**：
1.  **请求包**：CIP -> DIP（LB 将客户端 IP 替换为 LB 的 IP），VIP -> RIP（LB 将虚拟 IP 替换为真实服务器 IP）。
2.  **响应包**：RIP -> VIP，DIP -> CIP（RS 将包回给 LB，LB 再转换回客户端 IP）。

**特点**：
1.  RS 的网关不需要指向 LB，只要是路由可达即可，支持跨 VLAN、跨机房部署。
2.  解决了单点 LVS 瓶颈问题，可以做 LVS 集群（因为 RS 也不属于特定 LB，可以由任何 LB 回源）。
3.  由于转换了源 IP，RS 获取不到真实客户端 IP，需要通过 TOA (TCP Option Address) 模块在 TCP 选项中插入真实客户端 IP 信息来解决，或者 HTTP 层使用 `X-Forwarded-For`。

```text
FULLNAT 模式数据流向

    Client              LVS (Director)          Real Server
   ┌──────┐            ┌──────────┐            ┌───────────┐
   │      │            │          │            │           │
   │ CIP  │───────────►│ VIP/DIP  │───────────►│   RIP     │
   │:Port │  VIP       │   Local  │  DIP:Port  │:Port      │
   │      │            │          │            │           │
   └──────┘            └──────────┘            └───────────┘
                                   ▲              │
                                   │              │
                                   │ RIP -> VIP   │ RIP (src=DIP)
                                   │ DIP -> CIP   │
   ┌──────┐            ┌──────────┐ │            │
   │      │            │          │ └────────────┘
   │ CIP  │◄───────────│ VIP/DIP  │
   │:Port │  DIP->CIP   │   Local  │
   │      │  VIP->RIP   │          │
   └──────┘            └──────────┘

注：LB上维护 CIP-VIP -> DIP-RIP 的连接追踪表
```

**常见考点**
1.  **Local 模式**：LVS FULLNAT 常配合 `-L` 参数使用，目的是让 RS 的回包尽量落在同一个 LB 上，利用连接复用，减少 LB 之间转发。
2.  **连接跟踪**：FULLNAT 转换四元组，LB 需要维护大量的并发连接表，对 LB 的内存消耗较大。
3.  **TOA 原理**：TCP Option 最多 40 字节，TOA 占用一部分字节插入 IP 和 Port 信息，需要客户端和服务器端（内核模块）同时支持或应用层解析。

**实战案例**：
在公有云混合云部署场景中，常利用 FULLNAT 将流量从公网 LB 转发到内网跨机房的 K8s Node 节点，此时 RS 网关指向 VPC 路由器而非 LB，实现灵活组网。但需注意若未开启 `SYN Proxy`，LB 可能因 SYN Flood 攻击耗尽连接跟踪表。

**代码示例（ipvsadm 配置）**：
```bash
# 添加 FULLNAT 模式服务
ipvsadm -A -t 10.0.0.1:80 -s wrr -p 300
# 添加后端 Real Server，-b 指定 FULLNAT 模式
# 10.0.0.2 为 Local IP (DIP), 192.168.1.10 为 Real Server IP (RIP)
ipvsadm -a -t 10.0.0.1:80 -r 192.168.1.10:80 -b -w 100
# 查看 FULLNAT 连接追踪情况
ipvsadm -ln --connection
```

**LVS 模式对比（适用场景）**：

| 模式 | RS 网络要求 | RS 配置复杂度 | 真实 IP 获取 | 性能 | 适用场景 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DR** | 必须同网段（二层） | 高（需配置 lo, ARP 抑制） | 容易（CIP 不变） | 最高 | 高性能本地集群 |
| **NAT** | 私有网络，网关指向 LB | 低（只需改网关） | 容易（CIP 不变） | 一般（LB 瓶颈） | 小规模内部服务 |
| **FULLNAT** | 路由可达（跨网段/机房） | 低（无特殊配置） | 困难（需 TOA/Proxy Protocol） | 较高（消耗 LB 内存） | 跨机房/云原生/大规模集群 |



## 核心知识点图

<img src="/interview-2026/images/diagram_distributed_dist-004.svg" alt="LVS FULLNAT模式的工作原理是什么？" style="max-width:100%;height:auto;border:1px solid var(--border);border-radius:8px;margin:1em 0;" />

## 记忆要点

- 核心原理：同时修改源 IP（CIP转DIP）和目的 IP（VIP转RIP），实现双向 NAT
- 组网优势：因为 RS 网关无需指向 LB，所以支持跨 VLAN 和跨机房网络部署
- 真实IP痛点：因为源 IP 被替换，所以 RS 无法直接获取真实 CIP，必须依赖 TOA 模块或 HTTP 头
- 性能代价：因为要维护海量的四元组连接追踪表，所以比 DR 模式更消耗内存

## 结构化回答


**30 秒电梯演讲：** 快递中转站（LB）改了发件人和收件人地址，收件人回信也寄给中转站。

**展开框架：**
1. **双向NAT** — 同时改写源IP和目的IP。
2. **解决LVS与RS** — 必须在同一网段的限制
3. **RS获取真实客户** — RS获取真实客户端IP较难。

**收尾：** 这是我实战中的理解，您想深入哪一段？


## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：LVS FULLNAT模式的工作原理 | "LVS FULLNAT模式的工作原理，一分钟讲透。" | 开场钩子 |
| 0:35 | 生活类比动画 | "打个比方——快递中转站(LB)改了发件人和收件人地址，收件人回信也寄给中转站。" | 核心类比 |
| 1:10 | 概念定义动画 | "一句话：同时修改源IP和目的IP，允许LVS和RS跨网段部署。" | 核心定义 |
| 1:50 | 双向NAT 图解 | "同时改写源IP和目的IP。" | 双向NAT |
