---
id: core-324
difficulty: L3
category: java-core
subcategory: 并发
tags:
- synchronized
- 锁升级
- JDK优化
feynman:
  essence: 锁状态随竞争激烈程度逐步升级，从偏向锁到重量级锁。
  analogy: 像进门：独占时贴你名字（偏向）直接进；有人争了就改排队叫号（轻量级自旋）；人太多时换保安把守（重量级阻塞）。
  first_principle: 如何在无竞争、低竞争和高竞争场景下分别最小化锁开销？
  key_points:
  - 升级：偏向→轻量级→重量级
  - 偏向锁：记录ID零开销
  - 轻量级：CAS自旋竞争
  - 重量级：内核态阻塞
follow_up:
- 偏向锁撤销为什么要在safepoint？
- 轻量级锁的Lock Record是什么？CAS怎么工作的？
- 重量级锁的ObjectMonitor结构是怎样的？
memory_points:
- 升级单向不可逆：无锁 → 偏向锁(记线程ID) → 轻量级锁(CAS+自旋) → 重量级锁(OS互斥量阻塞)
- 偏向锁假设只有单线程执行，轻量级锁假设多线程交替执行且无激烈竞争
- 轻量级锁 CAS 失败引发自旋，自旋失败或竞争激烈膨胀为重量级锁，线程进入阻塞
- JDK15默认关闭偏向锁：因多核高并发场景下撤销偏向锁需STW，维护代价远超带来的性能收益
frequency: high
---

# synchronized 的锁升级过程是怎样的？偏向锁为什么在 JDK 15 后默认关闭？

【锁升级过程（JDK 1.6+）】
无锁 → 偏向锁 → 轻量级锁 → 重量级锁（不可逆）。

**## 锁状态转换与 Mark Word 结构**
```text
Mark Word (32位 JVM) 布局随锁状态变化：

┌──────────────────────────────────────────────────────┐
│ State (2bits) │    Lock Info (剩余 bits)             │
├──────────────────────────────────────────────────────┤
│   00 (Light)   │  指向栈中 Lock Record 的指针         │
├──────────────────────────────────────────────────────┤
│   01 (Biased)  │  线程ID + Epoch + 分代年龄 (1 bit)  │
├──────────────────────────────────────────────────────┤
│   00 (Heavy)   │  指向堆中 ObjectMonitor 的指针       │
├──────────────────────────────────────────────────────┤
│   01 (Normal)  │  对象 HashCode (25 bits) + 分代年龄 │
└──────────────────────────────────────────────────────┘

升级流程图：

[新对象] (Normal/101)
    │
    ├── Thread A 访问 ──▶ [偏向锁] (Biased/01) 记录 ThreadID
    │                              │
    │                              ├── Thread A 再次进入：零开销
    │                              │
    │                              └── Thread B 竞争 ──▶ [撤销偏向锁] (STW) ──▶ [轻量级锁]
    │                                                             │
    │                                                             ├── CAS 成功：Thread B 获锁
    │                                                             │
    │                                                             ├── CAS 失败：自旋 (Adaptive Spin)
    │                                                             │
    │                                                             └── 自旋失败/竞争激烈 ──▶ [重量级锁] (Heavy/10)
    │                                                                        │
    │                                                                        └── OS Mutex, 线程阻塞
```

【各阶段详解】
1. **无锁**：对象刚创建，Mark Word 存储对象的 HashCode。
2. **偏向锁**：
   - 假设锁主要由同一线程多次获得。
   - 当线程第一次获取锁时，CAS 替换 Mark Word 中的 Thread ID。
   - 后续该线程进入/退出同步块只需检查 Thread ID，无需系统调用。
   - **撤销代价**：一旦有第二个线程尝试获取锁，偏向模式宣告结束，撤销需要到达全局安全点，有一定开销。
3. **轻量级锁**：
   - 假设锁存在竞争但很短（交替执行）。
   - 线程在栈帧创建 Lock Record，尝试用 CAS 将 Mark Word 替换为指向 L

---

#### 深化实战补充

1. **实战案例（批量处理与锁争用）**：
   在一个批量数据同步服务中，由于使用了 `synchronized` 保护共享计数器，当并发量上升时，Monitor 对象膨胀为重量级锁，导致大量线程阻塞。通过将粒度拆分（分段计数）或改用 `LongAdder`（CAS 优化），吞吐量提升了 3 倍。

2. **代码示例（偏向锁撤销演示）**：
   ```java
   // JVM 参数开启偏向锁日志：-XX:+PrintBiasedLockingStatistics -XX:BiasedLockingStartupDelay=0
   public class LockDemo {
       static Object lock = new Object();
       public static void main(String[] args) throws InterruptedException {
           synchronized (lock) { /* Thread 1 获取偏向锁 */ }
           Thread t2 = new Thread(() -> {
               synchronized (lock) { /* Thread 2 竞争，触发偏向锁撤销，升级为轻量级锁 */ }
           });
           t2.start();
           t2.join();
       }
   }
   ```

3. **对比表格（JDK 锁机制选型）**
   | 锁类型 | 适用场景 | 优势 | 劣势 | 复杂度 |
   | :--- | :--- | :--- | :--- | :--- |
   | **偏向锁** | 单线程重复执行同步块 | 几乎无额外开销 | 多线程竞争时撤销有 STW 开销 | O(1) (CAS) |
   | **轻量级锁** | 线程交替执行，无激烈竞争 | 避免内核态切换 | 竞争激烈时自旋消耗 CPU | O(N) (自旋) |
   | **重量级锁** | 猛烈竞争，长时间持有 | 稳定，不消耗 CPU | 线程挂起/唤醒，性能损耗大 | O(OS Context Switch) |

4. **为什么 JDK 15 后默认关闭偏向锁？**
   - **撤销成本不可控**：偏向锁撤销需要到达 Safepoint，如果程序中出现了大量并发竞争（例如使用了线程池、并发容器等），偏向锁的撤销会导致长时间的 STW（Stop The World），反而降低性能。
   - **收益下降**：现代 Java 程序普遍使用并发库，锁的竞争模式比早期更复杂，偏向锁“锁通常由一个线程持有”的假设在复杂系统中往往不成立。



## 核心流程图

```mermaid
flowchart TD
    OBJ([对象头Mark Word]):::start --> FIRST{首次有线程访问?}:::decision
    FIRST -->|是 单线程| BIAS[偏向锁 Biased<br/>记录线程ID 无竞争]
    BIAS --> RUN1[同线程再次进入<br/>CAS比较线程ID 即可]
    RUN1 --> COMP{出现第二个线程?}:::decision
    COMP -->|否 仍是单线程| RUN1
    COMP -->|是 竞争出现| LIGHT[轻量级锁 Lightweight<br/>撤销偏向 栈帧Lock Record]
    LIGHT --> CAS[CAS自旋<br/>尝试设置Mark Word指针]
    CAS --> SUCC{CAS成功?}:::decision
    SUCC -->|是| RUN2[自旋持有锁<br/>无系统调用]
    SUCC -->|否| SPIN[自适应自旋<br/>等待一定次数]
    SPIN --> GIVEUP{超过自旋阈值?}:::decision
    GIVEUP -->|否| CAS
    GIVEUP -->|是 严重竞争| HEAVY[重量级锁 Heavyweight<br/>ObjectMonitor]
    HEAVY --> OS[("内核态mutex<br/>等待队列park/unpark")]:::storage
    OS --> BLK[未抢到锁的线程<br/>进入内核态阻塞]
    BLK --> WAKE[锁释放时唤醒<br/>系统调用开销大]
    WAKE --> DONE([执行临界区]):::success
    BIAS -.->|JDK15+默认关闭| OFF[BiasedLocking已废弃<br/>直接进入轻量级锁]:::async
        classDef start fill:#e3f2fd,stroke:#1976d2,stroke-width:2px,color:#0d47a1
    classDef decision fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#e65100
    classDef success fill:#e8f5e9,stroke:#388e3c,stroke-width:2px,color:#1b5e20
    classDef error fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#b71c1c
    classDef storage fill:#eceff1,stroke:#455a64,stroke-width:2px,color:#263238
    classDef async fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#4a148c

```
## 记忆要点

- 升级单向不可逆：无锁 → 偏向锁(记线程ID) → 轻量级锁(CAS+自旋) → 重量级锁(OS互斥量阻塞)
- 偏向锁假设只有单线程执行，轻量级锁假设多线程交替执行且无激烈竞争
- 轻量级锁 CAS 失败引发自旋，自旋失败或竞争激烈膨胀为重量级锁，线程进入阻塞
- JDK15默认关闭偏向锁：因多核高并发场景下撤销偏向锁需STW，维护代价远超带来的性能收益

## 结构化回答

**30 秒电梯演讲：** 锁状态随竞争激烈程度逐步升级，从偏向锁到重量级锁。打个比方，像进门：独占时贴你名字（偏向）直接进；有人争了就改排队叫号（轻量级自旋）；人太多时换保安把守（重量级阻塞）。

**展开框架：**
1. **升级单向不可逆** — 无锁 → 偏向锁(记线程ID) → 轻量级锁(CAS+自旋) → 重量级锁(OS互斥量阻塞)
2. **偏向锁假设只有单线程执行** — 轻量级锁假设多线程交替执行且无激烈竞争
3. **轻量级锁 CAS 失败引发自旋** — 自旋失败或竞争激烈膨胀为重量级锁，线程进入阻塞

**收尾：** 我在项目里踩过坑——实战案例（批量处理与锁争用）：。您想深入聊哪一段：原理、避坑还是对比选型？

## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：synchronized 的锁升级过… | "synchronized 的锁升级过程是怎样的？偏向锁为什么在 JDK 15 后默认关闭？一句话——像进门：独占时贴你名字（偏向）直接进；有人争了就改排队叫号（轻量级自旋）；人太多时换保安把守（重量级阻塞）。" | 开场钩子 |
| 0:45 | 概念动画/示意图 | "锁状态随竞争激烈程度逐步升级，从偏向锁到重量级锁——像进门：独占时贴你名字（偏向）直接进；有人争了就改排队叫号（轻量级自旋）；人太多时换保安把守（重量级阻塞）" | 核心定义 |
| 1:30 | 升级单向不可逆示意 | "无锁 → 偏向锁(记线程ID) → 轻量级锁(CAS+自旋) → 重量级锁(OS互斥量阻塞)" | 要点1 |
| 2:15 | 偏向锁假设只有单线程执行示意 | "轻量级锁假设多线程交替执行且无激烈竞争" | 要点2 |
| 3:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |

### 视频流程图

```mermaid
flowchart LR

    subgraph Intro["引入"]
        A["synchronized 的锁升级过程是怎样的？偏向锁为什么…"]:::intro
    end

    subgraph Core["讲解"]
        B["升级单向不可逆：无锁 → 偏向锁（记线程ID） → …"]:::core
        C["偏向锁假设只有单线程执行，轻量级锁假设多线程交替执行…"]:::deep
    end

    subgraph Practice["实战"]
        D["代码实战"]:::practice
    end

    subgraph Wrap["收尾"]
        E["总结回顾"]:::wrap
    end

    A --> B --> C --> D --> E

    classDef intro fill:#FF9800,color:#fff,stroke:#F57C00,stroke-width:2px
    classDef core fill:#2196F3,color:#fff,stroke:#1976D2,stroke-width:2px
    classDef deep fill:#4CAF50,color:#fff,stroke:#388E3C,stroke-width:2px
    classDef practice fill:#9C27B0,color:#fff,stroke:#7B1FA2,stroke-width:2px
    classDef wrap fill:#607D8B,color:#fff,stroke:#455A64,stroke-width:2px
```

