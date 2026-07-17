---
id: conc-132
difficulty: L3
category: concurrent
feynman:
  essence: JMM定义的可见性顺序规则，保证多线程操作的有序性。
  analogy: 就像先盖好楼才能装修，装修完才能入住，有先后顺序，前面的结果后面一定能看到。
  first_principle: 在不依赖锁的情况下，如何保证一个线程的操作对另一个线程可见？
  key_points:
  - 程序顺序内前序后
  - 解锁后加锁可见
  - volatile写后读可见
  - 传递性规则
memory_points:
- 核心作用：JMM中保证多线程间操作的可见性与有序性
- 口诀记忆八大规则：程序次序、锁、volatile、传递、start、join、中断、终结
- 核心原理：底层通过插入内存屏障禁止处理器重排序
- 易混概念：happens-before是JMM语义保证，未必等同于代码实际执行的时间顺序
---

# 什么是happens-before规则？

happens-before是JMM（Java内存模型）中定义的**可见性**与**有序性**的核心规则。如果一个操作A happens-before 操作B，则A的执行结果对B可见，且A的执行顺序在B之前。

### 8条核心规则：
1. **程序顺序规则**：同一线程内，书写在前的操作 happens-before 书写在后的操作。
2. **监视器锁规则**：unlock 操作 happens-before 后续（针对同一锁）的 lock 操作。
3. **volatile变量规则**：volatile 写 happens-before 后续（针对同一变量）的 volatile 读。
4. **线程启动规则**：Thread 对象的 start() 方法 happens-before 该线程的每一个动作。
5. **线程终止规则**：线程中的所有操作都 happens-before 其他线程从该线程的 join() 方法成功返回。
6. **线程中断规则**：对线程 interrupt() 的调用 happens-before 被中断线程的代码检测到中断事件的发生。
7. **对象终结规则**：一个对象的初始化完成（构造函数执行结束） happens-before 它的 finalize() 方法的开始。
8. **传递性**：如果 A happens-before B，且 B happens-before C，那么 A happens-before C。

### 原理解析（底层支持）：
JMM 通过内存屏障来实现这些规则，禁止特定类型的处理器重排序：
- **LoadLoad 屏障**：禁止读操作重排序（如 Volatile 读）。
- **StoreStore 屏障**：禁止写操作重排序（如 Volatile 写）。
- **LoadStore / StoreLoad**：组合屏障确保读写顺序。

### 双重检查锁中的体现：
```java
// 1. 分配内存
// 2. 初始化对象
// 3. 引用指向内存
```
若无 volatile，2 和 3 可能重排序，导致其他线程获取到未初始化的对象。volatile 保证了 happens-before，禁止了这种重排序。

### 💡 实战案例
在高并发网关中，曾出现因未将 **“配置初始化”** 标志位设为 volatile，导致请求线程读取到空配置从而引发 NPE 的线上故障。修复后利用 volatile 规则保证了配置发布立即可见。

### 💻 代码示例
```java
// 利用 happens-before 规则实现简单的“启动开关”
public class VolatileFlag {
    private volatile boolean started = false;

    public void start() {
        init(); // 1. 初始化操作
        started = true; // 2. volatile 写（遵循程序顺序规则：1 hb 2）
    }

    public void execute() {
        if (!started) return; // 3. volatile 读
        // volatile 读 happens-after volatile 写，因此此处能看到 init 的结果
        doWork(); 
    }
}
```

### 🆚 概念对比：时间顺序 vs 先行发生
| 维度 | 时间上 | 先行发生 |
| :--- | :--- | :--- |
| **定义** | 物理时间发生的先后顺序 | JMM 定义的语义保证 |
| **关系** | A 先于 B 发生 | A 的结果对 B 可见，且顺序在 B 之前 |
| **因果性** | 如果 A hb B，A 未必在时间上先于 B（重排序） | 如果 A hb B，A 的结果一定对 B 可见 |

## 常见考点
1. **as-if-serial 语义**：单线程内结果不可改变，但多线程下不保证有序性，happens-before 如何解决？
2. **时间顺序 vs 先行发生**：happens-before 不代表时间上的先后，只代表语义上的保证。
3. **实际应用**：请结合单例模式的双重检查锁（DCL）解释 volatile 的作用。

## 记忆要点

- 核心作用：JMM中保证多线程间操作的可见性与有序性
- 口诀记忆八大规则：程序次序、锁、volatile、传递、start、join、中断、终结
- 核心原理：底层通过插入内存屏障禁止处理器重排序
- 易混概念：happens-before是JMM语义保证，未必等同于代码实际执行的时间顺序

## 结构化回答




**30 秒电梯演讲：** 就像先盖好楼才能装修，装修完才能入住，有先后顺序，前面的结果后面一定能看到。

**展开框架：**
1. **程序顺序内前** — 程序顺序内前序后
2. **解锁后加锁** — 解锁后加锁可见
3. **volatile写后读** — volatile写后读可见

**收尾：** 这是我实战中的理解，您想深入哪一段？




## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：什么是happens-before规则 | 今天这道题：什么是happens-before规则。30 秒先给你讲清楚。 | 开场钩子 |
| 0:20 | 核心概念动画/示意图 | 就像先盖好楼才能装修，装修完才能入住，有先后顺序，前面的结果后面一定能看到。 | 核心概念 |
| 0:40 | 程序顺序内前序后示意图 | 程序顺序内前序后 | 程序顺序内前序后 |
| 1:10 | 解锁后加锁示意图 | 解锁后加锁可见 | 解锁后加锁 |
| 1:40 | 总结卡 + 下期预告 | 记住今天这几个关键词，面试一定用得上。下期见。 | 收尾 |
