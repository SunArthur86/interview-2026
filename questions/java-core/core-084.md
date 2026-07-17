---
id: core-084
difficulty: L2
category: java-core
feynman:
  essence: TCP建立连接时的三次确认过程
  analogy: A问B“在吗？”，B回“在，你呢？”，A回“我也在”，确保双方都能听清
  first_principle: 在不安全的网络中，如何确认双方都已准备好通信并同步了状态？
  key_points:
  - 为了同步双方的初始序列号
  - 防止失效的连接请求突然传到服务端
  - 三次是建立可靠连接的最小握手次数
memory_points:
- 原因口诀：防旧连、同步号、省资源，所以最少需要三次握手
- 握手流程：C发SYN(seq=x)，S回SYN+ACK(seq=y,ack=x+1)，C再发ACK(ack=y+1)
- 状态流转：客户端SYN_SENT，服务端SYN_RCVD，最终双方都进ESTABLISHED
- 常见考点：ISN动态生成防伪造，SYN Flood攻击导致半连接耗尽
---

# 什么是三次握手的过程？

### TCP 三次握手

TCP 是面向连接的协议，使用 TCP 传输数据前必须先建立连接，建立连接是通过**三次握手**来进行的。

#### 为什么需要三次握手？
1. **防止历史连接初始化**：避免因网络滞留的失效 SYN 报文突然传到服务端，导致服务端错误建立连接。
2. **同步初始序列号 (ISN)**：TCP 连接的双方都需要维护自己的序列号，用于保证可靠传输。三次握手是确认双方序列号同步的最小可靠次数。
3. **避免资源浪费**：只有双方确认了连接建立，才会分配资源。防止服务端盲目响应大量无效请求导致资源耗尽。

#### 过程简述
1. **第一次握手 (Client -> Server)**：客户端发送 `SYN=1` 和初始序列号 `seq=x`，请求建立连接。客户端进入 `SYN_SENT` 状态。
2. **第二次握手 (Server -> Client)**：服务端收到 SYN，回复 `SYN=1`，`ACK=1`，确认号 `ack=x+1`，并携带自己的初始序列号 `seq=y`。服务端进入 `SYN_RCVD` 状态。
3. **第三次握手 (Client -> Server)**：客户端收到 SYN+ACK 包，检查确认号是否正确。正确后发送 `ACK=1`，确认号 `ack=y+1`，序列号 `seq=x+1`。服务端收到后进入 `ESTABLISHED` 状态。

#### 状态流转图
```text
   Client                               Server
     │                                    │
     │ ─── SYN, seq=x ───────────────────> │ CLOSED
     │                                    │ (收到 SYN，分配资源)
     │ SYN_SENT                           │ LISTEN -> SYN_RCVD
     │                                    │
     │ <── SYN, ACK, seq=y, ack=x+1 ───── │
     │ (收到 SYN+ACK，分配资源)            │
     │                                    │
     │ ─── ACK, seq=x+1, ack=y+1 ───────> │
     │ ESTABLISHED                        │ (收到 ACK)
     │                                    │ ESTABLISHED
     │                                    │
```

#### 实战案例
在容器化环境（如 Kubernetes）中，若 Pod 的 `readinessProbe` 配置不当，导致 LB 在服务端还未完全启动时就转发流量，可能会因为半连接队列未初始化完成而丢包。或者在公网环境下，第一次握手延迟较高，会导致连接建立时间翻倍，影响首屏加载。

#### 代码示例 (Go - Server 优化)
```go
// 设置 TCP 监听器时调整全连接队列长度，防止突发流量导致队列溢出
lc := net.ListenConfig{
    Control: func(network, address string, c syscall.RawConn) error {
        return c.Control(func(fd uintptr) {
            syscall.SetsockoptInt(int(fd), syscall.SOL_SOCKET, syscall.SO_REUSEADDR, 1)
            // 可根据负载调整 somaxconn
            syscall.SetsockoptInt(int(fd), syscall.SOL_SOCKET, syscall.SO_REUSEPORT, 1)
        })
    },
}
ln, _ := lc.Listen(context.Background(), "tcp", ":8080")
```

#### ## 常见考点
1. **ISN (Initial Sequence Number)**：为什么是动态生成的？（为了防止被攻击者猜到序列号从而伪造 TCP 报文）。
2. **SYN Flood 攻击**：攻击者大量发送 SYN 包，不回第三次握手，耗尽服务端资源。防御手段有哪些？（SYN Cookies, 增大半连接队列）。
3. **连接耗时**：三次握手带来的 RTT（往返时间）延迟，以及如何在 HTTP/1.1 持久连接或 HTTP/2 中减少握手开销。

## 记忆要点

- 原因口诀：防旧连、同步号、省资源，所以最少需要三次握手
- 握手流程：C发SYN(seq=x)，S回SYN+ACK(seq=y,ack=x+1)，C再发ACK(ack=y+1)
- 状态流转：客户端SYN_SENT，服务端SYN_RCVD，最终双方都进ESTABLISHED
- 常见考点：ISN动态生成防伪造，SYN Flood攻击导致半连接耗尽

## 结构化回答

**30 秒电梯演讲：** TCP建立连接时的三次确认过程。打个比方，A问B“在吗？”，B回“在，你呢？”，A回“我也在”，确保双方都能听清。

**展开框架：**
1. **原因口诀** — 防旧连、同步号、省资源，所以最少需要三次握手
2. **握手流程** — C发SYN(seq=x)，S回SYN+ACK(seq=y,ack=x+1)，C再发ACK(ack=y+1)
3. **状态流转** — 客户端SYN_SENT，服务端SYN_RCVD，最终双方都进ESTABLISHED

**收尾：** 我在项目里踩过坑——在容器化环境（如 Kubernetes）中，若 Pod 的 `readinessProbe` 配置不当，导致 LB 在服务端还未完全启动时就转发流量，可能会因为半连接队列未初始化完成而丢包。您想深入聊哪一段：原理、避坑还是对比选型？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：什么是三次握手的过程 | "什么是三次握手的过程？一句话——A问B“在吗？”，B回“在，你呢？”，A回“我也在”，确保双方都能听清。" | 开场钩子 |
| 0:40 | 概念动画/示意图 | "TCP建立连接时的三次确认过程——A问B“在吗？”，B回“在，你呢？”，A回“我也在”，确保双方都能听清" | 核心定义 |
| 1:20 | 原因口诀示意 | "防旧连、同步号、省资源，所以最少需要三次握手" | 要点1 |
| 2:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |
