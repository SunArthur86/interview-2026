---
id: core-183
difficulty: L3
category: java-core
feynman:
  essence: 通过超时或冗余确认触发数据重新发送以保障可靠。
  analogy: 寄信没回音就再寄一封（超时）；对方说“没收到第3封”，就立刻补寄（快速重传）。
  first_principle: 如何在不可靠的传输环境下保证数据不丢失？
  key_points:
  - 超时重传时间RTO略大于RTT且动态调整
  - 连续3个重复ACK触发快速重传
  - SACK机制支持只重传丢失的包
  - D-SACK用于告知发送方重复接收的情况
  - 超时重传采用指数退避避免加重拥塞
memory_points:
- 四大机制：超时重传、快速重传、SACK、D-SACK，解决数据丢失恢复问题。
- 超时重传：基于时间，RTO动态略大于RTT，触发指数退避，认为网络拥塞严重。
- 快速重传：基于数据，收到3个重复ACK即触发，无需等待超时。
- SACK与D-SACK：SACK确认收到的分片，D-SACK解决重复接收判断，避免盲目重传。
frequency: low
---

# TCP的重传机制是什么？

### TCP的重传机制

TCP 实现可靠传输的方式之一，是通过序列号与确认应答。但是如果传输过程中数据包丢失，就会使用重传机制来解决。

#### 1. 超时重传
设定一个计时器，当超过指定的时间后，没有收到对方的确认 ACK 应答报文，就会重发该数据。
*   **RTO（Retransmission Timeout）**：超时重传时间，应略大于报文往返 RTT 的值，且是动态变化的。通常采用加权平均 RTT 计算平滑 RTT (SRTT)，并计算 RTT 的方差来动态调整 RTO，以适应网络波动。
*   **策略**：每当遇到一次超时重传时，都会将下一次超时时间间隔设为先前值的两倍（指数退避），避免网络拥塞恶化。

#### 2. 快速重传
快速重传机制不以时间为驱动，而是以数据驱动重传。
*   **工作原理**：当收到三个相同的 ACK 报文（重复 ACK）时，会在定时器过期之前，重传丢失的报文段。
*   **触发条件**：接收方收到乱序报文时会重复发送最后一个已确认报文的 ACK，发送方一旦累计收到 3 个重复 ACK，即认为中间报文丢失。

#### 3. SACK（Selective Acknowledgment，选择性确认）
为了解决“重传哪些报文”的问题而提出。
*   **原理**：在 TCP 头部「选项」字段里加一个 SACK 信息，将已收到的数据的信息发送给「发送方」，这样发送方就可以知道哪些数据收到了，哪些数据没收到，从而只重传丢失的数据。
*   **作用**：在批量丢包或窗口较大的情况下，避免重传已发送的数据包，提高吞吐量。

#### 4. D-SACK（Duplicate SACK）
主要使用了 SACK 来告诉「发送方」有哪些数据被重复接收了。
*   **作用**：
    1.  让「发送方」知道，是发出去的包丢了，还是接收方回应的 ACK 包丢了。
    2.  可以知道是不是「发送方」的数据包被网络延迟了。
    3.  可以知道网络中是不是把「发送方」的数据包给复制了。

**重传机制判断流程图：**

```
发送数据
    |
    v
收到 ACK? --(超时)--> [指数退避 RTO] -> [重传数据]
    |
   (否) 是
    |
    v
是重复 ACK (DupACK)?
    |
   (否) 是
    |
    v
累计 3 个 DupACK? --(否)--> 继续等待
    |
   (是)
    |
    v
[快速重传] -> [调整 cwnd] -> [进入快速恢复]
```

#### 5. 实战案例与抓包分析
**实战案例**：在排查微服务接口偶发性超时（500ms - 1s）时，通过 `tcpdump` 抓包发现服务端未收到请求，但客户端却触发了超时重传。进一步分析发现是防火墙因连接数过高丢弃了 SYN 包或 ACK 包。开启 SACK 后，减少了不必要的重传，降低了链路拥塞。

**代码示例 (tcpdump 过滤重传包)**：
```bash
# 抓取 TCP 重传包 (tcp[13] & 0x16 != 0x18 或使用 -v 输出中含 [TCP Retransmission])
tcpdump -i eth0 'tcp[tcpflags] & tcp-rst != 0 or tcp[tcpflags] & tcp-syn != 0' -nn -vv
# 更通用的方式是抓包后用 Wireshark 过滤：
# tcp.analysis.retransmission
```

#### 6. 重传机制对比
| 特性 | 超时重传 (RTO) | 快速重传 | SACK | 
| :--- | :--- | :--- | :--- | 
| **触发条件** | 定时器超时 | 收到 3 个重复 ACK (DupACK) | 配合快速重传使用 | 
| **响应速度** | 慢 (需等待 RTO) | 快 (无需等待 RTO) | 快 | 
| **拥塞判断** | 认为拥塞严重 (cwnd=1) | 认为拥塞较轻 (cwnd减半) | 辅助判断丢失范围 | 
| **重传粒度** | 重传最早未确认的段 | 重传丢失的段 | 仅重传真正丢失的段 | 
| **性能影响** | 大 (吞吐量骤降) | 中等 | 小 (最高效) |


## 核心架构图

```mermaid
sequenceDiagram
    classDef start fill:#4CAF50,color:#fff
    classDef process fill:#2196F3,color:#fff
    classDef decision fill:#FF9800,color:#fff
    classDef special fill:#9C27B0,color:#fff
    classDef error fill:#f44336,color:#fff
    classDef info fill:#607D8B,color:#fff
    class ACK start
    class C process
    class ESTABLISHED decision
    class FIN special
    class S error
    class SYN info
    class TIME_WAIT start
    class ack process
    class as decision
    class seq special
    class u error
    class v info
    class w start
    class x process
    class y decision
    participant C as 客户端
    participant S as 服务端
    Note over C,S: 三次握手 建立连接
    C->>S: SYN seq=x
    S->>C: SYN+ACK seq=y ack=x+1
    C->>S: ACK seq=x+1 ack=y+1
    Note over C,S: 数据传输 ESTABLISHED
    Note over C,S: 四次挥手 断开连接
    C->>S: FIN seq=u 主动关闭
    S->>C: ACK seq=v ack=u+1 半关闭
    S->>C: FIN seq=w 数据发完
    C->>S: ACK seq=u+1 ack=w+1
    Note over C: TIME_WAIT 2MSL 后关闭
```

## 记忆要点

- 四大机制：超时重传、快速重传、SACK、D-SACK，解决数据丢失恢复问题。
- 超时重传：基于时间，RTO动态略大于RTT，触发指数退避，认为网络拥塞严重。
- 快速重传：基于数据，收到3个重复ACK即触发，无需等待超时。
- SACK与D-SACK：SACK确认收到的分片，D-SACK解决重复接收判断，避免盲目重传。

## 结构化回答

**30 秒电梯演讲：** 通过超时或冗余确认触发数据重新发送以保障可靠。打个比方，寄信没回音就再寄一封（超时）；对方说“没收到第3封”，就立刻补寄（快速重传）。

**展开框架：**
1. **四大机制** — 超时重传、快速重传、SACK、D-SACK，解决数据丢失恢复问题。
2. **超时重传** — 基于时间，RTO动态略大于RTT，触发指数退避，认为网络拥塞严重。
3. **快速重传** — 基于数据，收到3个重复ACK即触发，无需等待超时。

**收尾：** 这三点都能配合实战聊。您想深入聊原理、对比还是避坑？

## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：TCP的重传机制是什么 | "TCP的重传机制是什么？一句话——寄信没回音就再寄一封（超时）；对方说“没收到第3封”，就立刻补寄（快速重传）。" | 开场钩子 |
| 0:45 | 概念动画/示意图 | "通过超时或冗余确认触发数据重新发送以保障可靠——寄信没回音就再寄一封（超时）；对方说“没收到第3封”，就立刻补寄（快速重传）" | 核心定义 |
| 1:30 | 四大机制示意 | "超时重传、快速重传、SACK、D-SACK，解决数据丢失恢复问题。" | 要点1 |
| 2:15 | 超时重传示意 | "基于时间，RTO动态略大于RTT，触发指数退避，认为网络拥塞严重。" | 要点2 |
| 3:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |
