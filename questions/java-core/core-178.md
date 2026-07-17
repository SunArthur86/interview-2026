---
id: core-178
difficulty: L2
category: java-core
subcategory: 计算机网络
tags:
- TCP
- HTTP
- Keep-Alive
- Keepalive
feynman:
  essence: TCP Keepalive检测死链，HTTP Keep-Alive复用连接。
  analogy: 前者是定期问“挂了吗”，后者是“别挂电话，我还有话说”。
  first_principle: 如何检测闲置连接以及如何减少连接建立的开销？
  key_points:
  - TCP Keepalive检测连接有效性
  - HTTP Keep-Alive减少握手开销
  - TCP层默认关闭，HTTP层默认开启
  - 一为保活，一为复用
memory_points:
- 层级对比：TCP Keepalive属传输层，HTTP Keep-Alive属应用层。
- 机制对比：TCP保活是发心跳探针防半开，HTTP保活是复用TCP连接防握手。
- 默认参数：TCP保活通常默认关闭探测长达2小时，HTTP保活1.1后默认开启。
- 实战避坑：因NAT超时断连，生产通常不依赖TCP探针，而由应用层发自定义心跳。
---

# TCP 的 Keepalive 和 HTTP 的 Keep-Alive 是一个东西吗？

**TCP Keepalive** 和 **HTTP Keep-Alive** 虽然名字相似，但完全不同：

## 核心区别

| 对比项 | TCP Keepalive | HTTP Keep-Alive |
|--------|--------------|-----------------|
| **层级** | 传输层（TCP协议） | 应用层（HTTP协议） |
| **目的** | 检测连接是否存活 | 复用TCP连接传输多个HTTP请求 |
| **机制** | 定期发心跳包 | 请求头 `Connection: keep-alive` |
| **默认状态** | 通常关闭（需手动开启） | HTTP/1.1 默认开启 |
| **参数** | 时间间隔、探测次数 | 超时时间、最大请求数 |

## TCP Keepalive（保活探针）

```
作用：检测对端是否还活着（防止"半开连接"）

工作机制：
1. 连接空闲超过 tcp_keepalive_time（默认7200秒，2小时）
2. 发送探测包（空数据，不包含上层应用数据）
3. 如果收到ACK → 对端存活
4. 如果无响应 → 重试 tcp_keepalive_intvl 秒（默认75秒）
5. 超过 tcp_keepalive_probes 次无响应（默认9次）→ 判定连接死亡，发送 RST 复位

场景：NAT超时、客户端崩溃、网络断开检测
注意：不仅检测断网，还检测对端进程崩溃（操作系统仍会响应TCP）或主机掉电（无响应）
```

## HTTP Keep-Alive（连接复用）

```
作用：一个TCP连接上发送多个HTTP请求，避免重复握手

请求头：
  Connection: keep-alive    ← HTTP/1.1默认，可省略
  Keep-Alive: timeout=5, max=100  (可选)

响应头：
  Connection: keep-alive    ← 服务器同意保持连接

工作流程：
Client ─────TCP建立──────> Server
  |   Request 1  ───────────>  |
  |   <──────── Response 1   |
  |   (连接保持)            |
  |   Request 2  ───────────>  |
  |   <──────── Response 2   |
  |   ...                   |
  └─── TCP关闭/超时 ────────┘

场景：减少TCP握手/TLS握手开销，提高页面加载速度
```

#### ## 常见考点
1. **HTTP Keep-Alive 的局限性**：即使开启，由于串行传输（队头阻塞，HOL），后一个请求必须等前一个响应回来才能发送。
2. **TCP Keepalive 为什么默认关闭？**：因为默认 2 小时太长，实用性差；且开启后会消耗带宽，可能导致误报（如瞬时的网络抖动误杀连接）。
3. **应用层心跳 vs TCP Keepalive**：应用层心跳更灵活、可控，通常建议在应用层实现保活（如 Netty 空闲检测），不单纯依赖 TCP 层。

#### 4. 实战深化
*   **实战案例**：在移动端 App 与服务器通信时，单纯依赖 HTTP Keep-Alive 导致连接在 Nginx 中断开（通常 Nginx `keepalive_timeout` 为 60s），出现 "Connection reset" 错误；通过应用层实现每 30s 一次的轻量级心跳包解决此问题，规避了 NAT 超时清理连接。

*   **代码示例 (Java NIO 配置)**：
    ```java
    // 开启 TCP Keepalive (Socket 参数)
    ServerSocketChannel server = ServerSocketChannel.open();
    StandardSocketOptions options = StandardSocketOptions;
    server.setOption(options.SO_KEEPALIVE, true);
    // 进一步细化内核参数 (需通过 OS 级别或 JDK 11+ Socket API)
    // server.setOption(options.TCP_KEEPIDLE, 60); // 空闲 60s 后开始探测
    // server.setOption(options.TCP_KEEPINTERVAL, 10);
    ```

## 记忆要点

- 层级对比：TCP Keepalive属传输层，HTTP Keep-Alive属应用层。
- 机制对比：TCP保活是发心跳探针防半开，HTTP保活是复用TCP连接防握手。
- 默认参数：TCP保活通常默认关闭探测长达2小时，HTTP保活1.1后默认开启。
- 实战避坑：因NAT超时断连，生产通常不依赖TCP探针，而由应用层发自定义心跳。

## 结构化回答

**30 秒电梯演讲：** TCP Keepalive检测死链，HTTP Keep-Alive复用连接。打个比方，前者是定期问“挂了吗”，后者是“别挂电话，我还有话说”。

**展开框架：**
1. **层级对比** — TCP Keepalive属传输层，HTTP Keep-Alive属应用层。
2. **机制对比** — TCP保活是发心跳探针防半开，HTTP保活是复用TCP连接防握手。
3. **默认参数** — TCP保活通常默认关闭探测长达2小时，HTTP保活1.1后默认开启。

**收尾：** 我在项目里踩过坑——代码示例 (Java NIO 配置)：。您想深入聊哪一段：原理、避坑还是对比选型？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：TCP 的 Keepalive 和 … | "TCP 的 Keepalive 和 HTTP 的 Keep-Alive 是一个东西吗？一句话——前者是定期问“挂了吗”，后者是“别挂电话，我还有话说”。" | 开场钩子 |
| 0:40 | 概念动画/示意图 | "TCP Keepalive检测死链，HTTP Keep-Alive复用连接——前者是定期问“挂了吗”，后者是“别挂电话，我还有话说”" | 核心定义 |
| 1:20 | 层级对比示意 | "TCP Keepalive属传输层，HTTP Keep-Alive属应用层。" | 要点1 |
| 2:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |
