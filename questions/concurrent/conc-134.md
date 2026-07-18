---
id: conc-134
difficulty: L3
category: concurrent
feynman:
  essence: CAS仅比较值导致无法感知“改过又改回”的问题，需加版本号解决。
  analogy: 像检查杯子里的水还是满的（A），中间可能被喝光又接满，CAS以为是原样，其实水已经不是原来的水了。
  first_principle: 如何确保并发修改时数据的原子性与一致性，防止中间状态被掩盖？
  key_points:
  - CAS只检查值不检查状态历史
  - 中间变化被掩盖可能导致错误
  - 使用AtomicStampedReference加版本号
  - 乐观锁在特定场景下的局限性
memory_points:
- 问题本质：值由A变B又变A，CAS无法感知中间变化而误判更新成功
- 核心原因：普通CAS只比较值本身，缺乏对修改过程的感知
- 解决方案1：版本号机制，每次更新比对预期版本号，底层类AtomicStampedReference
- 解决方案2：标记位机制，仅判断是否被修改过，底层类AtomicMarkableReference
---

# CAS的ABA问题是什么？如何解决？

ABA 问题是指 CAS（Compare-And-Swap）操作过程中，**共享变量的值从 A 变为 B，又变回了 A**，但当前线程无法感知到中间发生过变化，误认为值未曾修改，从而将 CAS 操作误判为成功。

### 场景举例（链表节点）：
假设链表头节点为 A。
1. 线程 1 读取头节点 A，准备通过 CAS 将其替换为 C。
2. 线程 2 将 A 移除，链表头变为 B。
3. 线程 2 又将 A 重新插回链表头，此时链表头恢复为 A。
4. 线程 1 执行 CAS(A, C)，检查发现头节点确实是 A，CAS 成功。
5. **后果**：线程 2 对 B 的操作丢失了，链表结构可能被破坏。

### 解决方案：
#### 1. AtomicStampedReference（版本号机制）
不仅比较引用值，还比较**版本号**。每次修改更新版本号，即使值回退，版本号也已不同。
```java
// 初始值引用 A，初始版本号 1
AtomicStampedReference<Node> ref = new AtomicStampedReference<>(nodeA, 1);

// CAS 操作：期望引用 A，期望版本 1，更新引用 C，新版本 2
boolean result = ref.compareAndSet(nodeA, nodeC, 1, 2);
```

#### 2. AtomicMarkableReference（标记位机制）
不关心修改次数，只关心是否**被修改过**。使用一个 boolean 标记位（true/false）代替版本号，适用于只需要知道“变没变”的场景。
```java
AtomicMarkableReference<Node> ref = new AtomicMarkableReference<>(nodeA, false);
// 修改时更新标记
ref.compareAndSet(nodeA, nodeC, false, true);
```

### 💡 实战案例
在金融交易对账系统中，使用 AtomicReference 更新账户余额时，若仅依赖 CAS 可能会被并发扣款和回滚操作欺骗（扣款100->加回100，余额未变但流水丢失）。引入 AtomicStampedReference 后，通过递增的“流水版本号”彻底杜绝了此类状态回滚风险。

### 💻 代码示例
```java
// 解决 ABA 问题的通用模板
public class SafeStack<T> {
    private final AtomicStampedReference<Node<T>> top = new AtomicStampedReference<>(null, 0);

    public void push(T item) {
        Node<T> newHead = new Node<>(item);
        int[] stampHolder = new int[1];
        Node<T> oldHead;
        do {
            oldHead = top.get(stampHolder); // 获取当前引用和版本戳
            newHead.next = oldHead;
            // CAS 更新引用，同时版本号 + 1
        } while (!top.compareAndSet(oldHead, newHead, stampHolder[0], stampHolder[0] + 1));
    }
}
```

### 🆚 方案选型对比
| 特性 | AtomicStampedReference | AtomicMarkableReference |
| :--- | :--- | :--- |
| **核心机制** | 传递一个整型版本号 | 传递一个布尔标记
| **适用场景** | 需要精确知道修改次数，如链表结构维护 | 只需知道是否被修改过，如垃圾回收标记
| **空间开销** | 2个int（引用+版本号） | 1个int（引用+boolean合并） |
| **ABA 解决程度** | 完全解决（版本号单调递增） | 解决（修改即翻转标记，可能再次变回但至少发生过修改） |

## 常见考点
1. **版本号溢出**：AtomicStampedReference 的版本号会溢出吗？如何处理？（实际是 int，虽可能溢出但在极高频操作下才需考虑，通常业务场景够用）
2. **性能开销**：StampedReference 比 AtomicReference 多了一个 int 的开销，对性能影响大吗？
3. **适用场景**：为什么还需要 AtomicMarkableReference？（有些场景不需要版本号，只需一个标记，开销更小）


## 记忆要点

- 问题本质：值由A变B又变A，CAS无法感知中间变化而误判更新成功
- 核心原因：普通CAS只比较值本身，缺乏对修改过程的感知
- 解决方案1：版本号机制，每次更新比对预期版本号，底层类AtomicStampedReference
- 解决方案2：标记位机制，仅判断是否被修改过，底层类AtomicMarkableReference

## 结构化回答


**30 秒电梯演讲：** 像检查杯子里的水还是满的（A），中间可能被喝光又接满，CAS以为是原样，其实水已经不是原来的水了。

**展开框架：**
1. **CAS只检查值不** — CAS只检查值不检查状态历史
2. **中间变化被掩盖可** — 中间变化被掩盖可能导致错误
3. **使用Atomic** — StampedReference加版本号

**收尾：** 这是我实战中的理解，您想深入哪一段？


## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：CAS的ABA问题是什么？如何解决 | 今天这道题：CAS的ABA问题是什么？如何解决。30 秒先给你讲清楚。 | 开场钩子 |
| 0:20 | 核心概念动画/示意图 | 像检查杯子里的水还是满的（A），中间可能被喝光又接满，CAS以为是原样，其实水已经不是原来的水了。 | 核心概念 |
| 0:40 | CAS只检查值不检查状态历史示意图 | CAS只检查值不检查状态历史 | CAS只检查值不检查状态历史 |
| 1:10 | 中间变化被掩盖示意图 | 中间变化被掩盖可能导致错误 | 中间变化被掩盖 |
| 1:40 | 总结卡 + 下期预告 | 记住今天这几个关键词，面试一定用得上。下期见。 | 收尾 |
