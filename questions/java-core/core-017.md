---
id: core-017
difficulty: L1
category: java-core
feynman:
  essence: 双向全双工断开，双方分别停止发送并确认。
  analogy: 挂电话：A说“挂了”，B说“好的（再讲两句）”，B说“我挂了”，A说“拜拜”。
  first_principle: 如何在双向通信中可靠地确认双方都同意且已完成数据传输？
  key_points:
  - 全双工通信需双方分别关闭发送通道
  - 被动方先回ACK（确认请求），发完数据再发FIN（关闭自己）
  - 主动方最后进入TIME_WAIT等待2MSL
  - 确保最后ACK到达及旧报文消散
memory_points:
- 全双工关闭需四步：主动方FIN，被动方ACK与FIN分开发
- 被动方收到FIN先回ACK，处理完剩余数据再发FIN
- 挥手状态：被动方CLOSE_WAIT，主动方最终停留TIME_WAIT
- TIME_WAIT需等2MSL，确保最后的ACK到达并消亡旧报文
- 大量CLOSE_WAIT是程序Bug，因业务阻塞或未及时调用close()
---

# 什么是四次挥手的过程？

## TCP 四次挥手过程

TCP 断开连接通常由一方主动发起，经过四次通信确认双方都关闭数据传输。

### 状态流转
假设 **Client** 主动发起断开，**Server** 被动接收。

1. **第一次挥手 (FIN_WAIT_1)**
   - **Client** 发送 `FIN` 报文，序列号为 `seq = u`。
   - **含义**：Client 没有数据要发了，请求关闭连接。
   - **状态**：Client → `FIN_WAIT_1`。

2. **第二次挥手 (CLOSE_WAIT)**
   - **Server** 收到 `FIN`，回复 `ACK` 报文，确认号 `ack = u + 1`。
   - **含义**：Server 知道 Client 要断开了，但 Server 可能还有数据要发。
   - **状态**：Server → `CLOSE_WAIT`；Client 收到 ACK 后 → `FIN_WAIT_2`。

3. **第三次挥手 (LAST_ACK)**
   - **Server** 处理完剩余数据后，发送 `FIN` 报文，序列号 `seq = w`。
   - **含义**：Server 也准备好断开了。
   - **状态**：Server → `LAST_ACK`。

4. **第四次挥手 (TIME_WAIT)**
   - **Client** 收到 `FIN`，回复 `ACK` 报文，确认号 `ack = w + 1`。
   - **含义**：Client 确认收到断开请求。
   - **状态**：Client → `TIME_WAIT`；Server 收到 ACK 后 → `CLOSED`。

5. **等待结束**
   - Client 在 `TIME_WAIT` 状态等待 **2MSL**（约 1-4 分钟），确保 Server 收到 ACK。
   - 之后 Client → `CLOSED`。

### 为什么是 4 次？
TCP 是**全双工**协议，意味着数据可以在两个方向上同时传输。建立连接时（SYN 同步）可以合并发送，但断开时：
- "我发完了" (FIN) 和 "我知道你发完了" (ACK) 是两件事。
- 当 Client 发 FIN 时，Server 可能还有数据在传输，所以 Server 先回 ACK（确认收到 FIN），等数据发完再发自己的 FIN。因此多了一次，总共 4 次。

## 实战案例
在短连接服务（如早期的 HTTP 1.0 或高频 API 网关）中，若服务器处理速度极快，大量连接会处于 `TIME_WAIT` 状态。**踩坑经验**：在高并发压测场景下，客户端机器因 `TIME_WAIT` 占满所有临时端口（默认约 28,000 个），导致无法发起新的连接，报错 "Cannot assign requested address"。**解决**：开启 `net.ipv4.tcp_tw_reuse`（Linux 允许将 TIME_WAIT socket 重新用于新的 TCP 连接），并调整 `net.ipv4.ip_local_port_range` 扩大端口范围。

## 代码示例 (Shell - 检查 TCP 状态)
```bash
# 统计当前各种 TCP 状态的数量
netstat -ant | awk '{print $6}' | sort | uniq -c | sort -rn

# 查看处于 TIME_WAIT 状态的连接数
ss -ant | grep TIME_WAIT | wc -l

# 快速复用 TIME_WAIT sockets (Linux内核参数调优)
sysctl -w net.ipv4.tcp_tw_reuse=1
```

## 对比表格：三次握手 vs 四次挥手

| 阶段 | 三次握手 | 四次挥手 |
|------|---------|---------|
| **发起方** | 任意一方（通常为 Client） | 任意一方（通常为 Client） |
| **中间状态** | SYN_RECV | CLOSE_WAIT (被动方), FIN_WAIT_2 (主动方) |
| **报文数** | 3 (SYN, SYN+ACK, ACK) | 4 (FIN, ACK, FIN, ACK) |
| **核心原因** | 建立连接时，双方的发送能力同时就绪 | 断开连接时，双方的发送能力可能不同步（一方可能还有数据要发） |
| **特殊状态** | 无 | TIME_WAIT (主动关闭方必须存在) |

## 常见考点
1. **TIME_WAIT 的作用**：为什么需要等待 2MSL？（1. 保证最后的 ACK 能到达 Server，防止 Server 重发 FIN；2. 等待网络中所有旧的报文段消失，避免影响新连接）。
2. **大量 CLOSE_WAIT 原因**：通常是因为程序代码 Bug，如对方关闭了连接，但我方没有及时调用 `close()`，或者业务逻辑阻塞在处理剩余数据上，导致一直停留在 CLOSE_WAIT。
3. **Simultaneous Close**：双方同时发送 FIN 的情况会如何？（状态会直接从 FIN_WAIT_1 跳转到 CLOSING，然后经过 TIME_WAIT 关闭）。

## 记忆要点

- 全双工关闭需四步：主动方FIN，被动方ACK与FIN分开发
- 被动方收到FIN先回ACK，处理完剩余数据再发FIN
- 挥手状态：被动方CLOSE_WAIT，主动方最终停留TIME_WAIT
- TIME_WAIT需等2MSL，确保最后的ACK到达并消亡旧报文
- 大量CLOSE_WAIT是程序Bug，因业务阻塞或未及时调用close()

## 结构化回答

**30 秒电梯演讲：** 双向全双工断开，双方分别停止发送并确认。打个比方，挂电话：A说“挂了”，B说“好的（再讲两句）”，B说“我挂了”，A说“拜拜”。

**展开框架：**
1. **全双工关闭需四步** — 主动方FIN，被动方ACK与FIN分开发
2. **被动方收到FIN先回ACK** — 处理完剩余数据再发FIN
3. **挥手状态** — 被动方CLOSE_WAIT，主动方最终停留TIME_WAIT

**收尾：** 这三点都能配合实战聊。您想深入聊原理、对比还是避坑？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：什么是四次挥手的过程 | "什么是四次挥手的过程？一句话——挂电话：A说“挂了”，B说“好的（再讲两句）”，B说“我挂了”，A说“拜拜”。" | 开场钩子 |
| 0:40 | 概念动画/示意图 | "双向全双工断开，双方分别停止发送并确认——挂电话：A说“挂了”，B说“好的（再讲两句）”，B说“我挂了”，A说“拜拜”" | 核心定义 |
| 1:20 | 全双工关闭需四步示意 | "主动方FIN，被动方ACK与FIN分开发" | 要点1 |
| 2:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |
