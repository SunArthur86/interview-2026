---
id: conc-040
difficulty: L3
category: concurrent
feynman:
  essence: 写时复制，修改操作复制新数组，读写分离。
  analogy: 写黑板报时，为了不影响别人看，先把内容抄到另一块黑板上改完了再换上去，大家看的还是旧的那块。
  first_principle: 如何在高并发读场景下避免写操作阻塞读操作？
  key_points:
  - 写操作加锁并复制新数组修改
  - 读操作无锁直接读原数组
  - 保证最终一致性而非实时一致性
  - 适合读多写少场景，写时内存消耗大
memory_points:
- 核心机制：写时复制，写操作加 ReentrantLock 拷贝新数组，而读操作无锁
- 内存可见：底层用 volatile 修饰数组引用，保证写后对读线程立即可见
- 一致性取舍：牺牲强一致性换取高性能，弱一致性迭代不抛 ConcurrentModificationException
- 适用场景：仅适合读多写少（如黑白名单），高频写或大数组极易引发内存OOM
---

# CopyOnWriteArrayList是什么？

CopyOnWriteArrayList

1. **概述**

CopyOnWriteArrayList可以理解成是ArrayList的线程安全的版本，内部也是使用数组实现；  
每次对数组的修改都完全拷⻉一份新的数组来修改，修改后再替换原来的老数组，这样⼦只阻塞的了写操作，不阻
塞读操作，实现读写分离。  
有一问题是，其无法保证实时的一致性，只能保证最终的一致性，所以适用于对实时性要求不高，读多写少的场
景，譬如黑白名单。  

2. **部分细节**

1. 每次对原数组的修改操作，都先加锁，然后copy一份新的数组，在新数组上做修改  
2. 锁使用的是ReentrantLock，独占的不公平锁  
3. 整个数组使用volatile修饰保证了可⻅性，结合锁之后，也就确保了单个api操作的原子性  
4. 内部无size属性，直接通过获取当前数组大小得到对应的元素的个数  
5. 需要注意的是，因为写时会复制一个近乎等大小的数组，所以需要考虑内存空间和集合使用的业务场景  
6. 看完源码之后，加深了System.arraycopy、Arrays.copyOf的理解

3. **边界情况**
7. **迭代器弱一致性**：迭代器基于创建时的数组快照，即便迭代期间其他线程修改了原数组，迭代器既不会抛出 `ConcurrentModificationException`，也不会遍历到新增加的元素。  
8. **批量修改开销**：`addAll` 等批量操作会复制大数组，若数据量大且并发高，极易引发 Full GC 或系统负载飙升。  
9. **数组溢出风险**：虽然底层是动态扩容，但若单次写入导致数组大小超过 `Integer.MAX_VALUE`，会抛出 `OutOfMemoryError: Requested array size exceeds VM limit`。

4. **写操作流程图**

```text
      Thread A (Write)                Thread B (Read)
           |                                |
           v                                |
    [lock.lock()]                        |
           |                                |
           v                                |
    [Copy Array] <------------------------| (Read Old Array Snapshot)
           |                                |
           v                                |
    [Modify New Array]                    |
           |                                |
           v                                |
    [volatile setArray]                   |
           |                                |
           v                                |
    [lock.unlock()]                       |
```

5. **实战与深化**

- **实战案例**：在网关服务中用于存储“系统黑名单”，由于黑名单更新频率极低（分钟级），而读取频率极高（QPS万级），使用 CopyOnWriteArrayList 避免了读锁竞争；但曾因一次批量导入数万个黑名单节点，导致堆内存瞬间翻倍引发 Young GC 频繁报警，后改为分批导入。
- **代码示例**：
```java
List<String> blacklist = new CopyOnWriteArrayList<>();

// 读操作：无锁，性能极高
public boolean isBlocked(String ip) {
    return blacklist.contains(ip); // 直接访问 volatile 数组
}

// 写操作：有锁，复制数组
public void addBlacklist(String ip) {
    blacklist.add(ip); // 内部使用 ReentrantLock 保证原子性
}
```
- **对比表格**：

| 特性 | CopyOnWriteArrayList | Collections.synchronizedList | Vector |
| :--- | :--- | :--- | :--- |
| **实现原理** | 写时复制（COW） | synchronized 代码块 | synchronized 方法 |
| **读操作** | **无锁**（高性能） | 有锁（串行） | 有锁（串行） |
| **写操作** | 有锁（复制数组） | 有锁 | 有锁 |
| **迭代器一致性** | 弱一致性（快照） | 强一致性（需加锁） | 强一致性（需加锁） |
| **内存消耗** | 写时双倍内存 | 正常 | 正常 |

## 面试追问
1. 如果遍历 CopyOnWriteArrayList 时，另一个线程正在修改数组，遍历到的数据是旧的还是新的？会不会报错？
2. 既然写操作通过复制数组实现，那如果数组非常大（例如百万级数据），频繁修改会导致什么问题？如何优化？
3. CopyOnWriteArrayList 的迭代器为什么不支持 `remove()` 操作？

## 易错点
1. **误以为读操作完全不需要 volatile**：读操作虽然不需要锁，但必须通过 `volatile` 读取引用才能保证可见性，否则可能读到旧引用。
2. **误以为适用于写多读少**：恰恰相反，任何写操作都会复制整个底层数组，写多会导致 CPU 和内存消耗巨大，应严格限制在读多写少场景。

## 记忆要点

- 核心机制：写时复制，写操作加 ReentrantLock 拷贝新数组，而读操作无锁
- 内存可见：底层用 volatile 修饰数组引用，保证写后对读线程立即可见
- 一致性取舍：牺牲强一致性换取高性能，弱一致性迭代不抛 ConcurrentModificationException
- 适用场景：仅适合读多写少（如黑白名单），高频写或大数组极易引发内存OOM

## 结构化回答




**30 秒电梯演讲：** 写黑板报时，为了不影响别人看，先把内容抄到另一块黑板上改完了再换上去，大家看的还是旧的那块。

**展开框架：**
1. **写操作加锁并** — 写操作加锁并复制新数组修改
2. **读操作无锁直** — 读操作无锁直接读原数组
3. **保证最终一致** — 保证最终一致性而非实时一致性

**收尾：** 这是我实战中的理解，您想深入哪一段？




## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：CopyOnWriteArrayList是什么 | 今天这道题：CopyOnWriteArrayList是什么。30 秒先给你讲清楚。 | 开场钩子 |
| 0:20 | 核心概念动画/示意图 | 写黑板报时，为了不影响别人看，先把内容抄到另一块黑板上改完了再换上去，大家看的还是旧的那块。 | 核心概念 |
| 0:40 | 写操作加锁并复制新数组修改示意图 | 写操作加锁并复制新数组修改 | 写操作加锁并复制新数组修改 |
| 1:10 | 读操作无锁直接读原数组示意图 | 读操作无锁直接读原数组 | 读操作无锁直接读原数组 |
| 1:40 | 总结卡 + 下期预告 | 记住今天这几个关键词，面试一定用得上。下期见。 | 收尾 |
