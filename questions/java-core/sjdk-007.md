---
id: sjdk-007
difficulty: L1
category: java-core
feynman:
  essence: 统一有序集合的首尾操作API
  analogy: 给List、Set、Map都装上统一的“前门”和“后门”开关
  first_principle: 解决不同有序集合访问首尾元素方法不一致的问题
  key_points:
  - 引入SequencedCollection/Map接口
  - 统一getFirst/getLast/addFirst等操作
  - reversed()返回反向视图
  - List、LinkedHashSet、TreeMap等均已实现
memory_points:
- 痛点：解决List、Deque、LinkedHashSet等有序集合首尾操作API各不相同的问题
- 核心：新增SequencedCollection统一接口，提供getFirst、addLast等方法
- reversed()：返回双向迭代视图而非新集合，修改视图直接影响原对象
- 避坑：ArrayList调用addFirst时间复杂度为O(N)，大数量批量操作慎用
---

# JDK 21的Sequenced Collections是什么？解决了什么问题？

🎯 本质：Sequenced Collections 是 JDK 21 引入的新接口体系，为有明确相遇顺序的集合提供统一的 API。

🔧 **问题背景**：之前获取第一个/最后一个元素的方式各不相同，缺乏统一接口导致代码难以泛化：
- `List`: `list.get(0)` / `list.get(list.size()-1)`
- `Deque`: `deque.getFirst()` / `deque.getLast()`
- `SortedSet`: `set.first()` / `set.last()`

**实战案例**：在编写通用的 LRU 缓存工具类时，以前需要分别处理 `ArrayList` 和 `LinkedHashSet` 的首尾移除逻辑，代码充斥着 `instanceof` 判断。使用 `SequencedCollection` 后，统一调用 `removeFirst()` 和 `addLast()` 即可，代码行数减少 40%。

**新接口层次架构图**：

```text
         Collection (Iterable)
               △
               │
      ┌────────┴─────────┐
      │                  │
      │         SequencedCollection
      │ (新增: addFirst, addLast, getFirst...)
      │                  △
      │      ┌───────────┴───────────┐
      │      │                       │
   List      │               SequencedSet (新增接口)
             │                       △
             │         ┌─────────────┴─────────────┐
             │         │                           │
        Deque    LinkedHashSet          SortedSet
                                     │
                                     ▼
                                  SequencedMap (新增接口)
                          (提供 firstEntry, lastEntry, reversed...)
```

核心方法：
- `getFirst()` / `getLast()` - 获取首尾元素（相当于 peek）
- `addFirst(e)` / `addLast(e)` - 头尾添加
- `removeFirst()` / `removeLast()` - 头尾删除
- `reversed()` - 反转视图（不修改原集合，返回反向视图）

使用示例：
```java
LinkedHashSet<String> set = new LinkedHashSet<>();
set.add("A"); set.add("B"); set.add("C");
set.getFirst(); // "A"
set.getLast();   // "C"
set.reversed();  // [C, B, A] 视图

SequencedMap<String, Integer> map = new LinkedHashMap<>();
map.putFirst("New", 1); // 新增方法
```

这是一个向后兼容的改进——所有现有的有序集合（`ArrayList`, `LinkedList`, `LinkedHashSet`, `TreeMap` 等）都新增实现了这些接口。

## 常见考点
1. **reversed() 返回的是新集合还是视图？**
   返回的是**视图**。修改视图会直接影响原集合，反之亦然。类似 `subList` 的行为。
2. **List 既然已经实现了 Collection，为什么还需要 SequencedCollection？**
   虽然 List 有顺序，但 `Set` 和 `Map` 的有序实现（如 LinkedHashSet）之前没有通用接口。为了统一所有“有序”容器，引入了中间接口 `SequencedCollection`，让 `List` 也实现它，从而允许泛型代码同时处理 List 和 LinkedHashSet。
3. **ArrayList 使用 addFirst 性能如何？**
   由于 `ArrayList` 底层是数组，`addFirst` 需要移动所有元素（System.arraycopy），时间复杂度为 O(N)。虽然 API 统一了，但在大数据量下仍需注意性能开销。

## 记忆要点

- 痛点：解决List、Deque、LinkedHashSet等有序集合首尾操作API各不相同的问题
- 核心：新增SequencedCollection统一接口，提供getFirst、addLast等方法
- reversed()：返回双向迭代视图而非新集合，修改视图直接影响原对象
- 避坑：ArrayList调用addFirst时间复杂度为O(N)，大数量批量操作慎用

## 结构化回答


**30 秒电梯演讲：** 给List、Set、Map都装上统一的“前门”和“后门”开关

**展开框架：**
1. **引入Sequen** — 引入SequencedCollection/Map接口
2. **统一getFir** — 统一getFirst/getLast/addFirst等操作
3. **reversed** — reversed()返回反向视图

**收尾：** 这是我实战中的理解，您想深入哪一段？


## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：JDK 21的Sequenced C… | "JDK 21的Sequenced Collections是什么？解决了什么问题？一句话——给List、Set、Map都装上统一的“前门”和“后门”开关。" | 开场钩子 |
| 0:40 | 概念动画/示意图 | "统一有序集合的首尾操作API——给List、Set、Map都装上统一的“前门”和“后门”开关" | 核心定义 |
| 1:20 | 痛点示意 | "解决List、Deque、LinkedHashSet等有序集合首尾操作API各不相同的问题" | 要点1 |
| 2:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |
