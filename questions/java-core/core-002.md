---
id: core-002
difficulty: L1
category: java-core
feynman:
  essence: 利用HashMap的Key唯一性来实现元素去重。
  analogy: 像一个不贴标签的篮子，相同的球（内容）只能放进去一个，不管你扔几次。
  first_principle: 如何快速判断集合中是否已存在某个元素？
  key_points:
  - 底层基于HashMap实现
  - 通过hashCode和equals判断重复
  - 元素无序且不可重复
  - 非线程安全
memory_points:
- 底层本质：HashSet底层本质就是HashMap，存入的元素作为Key，Value固定占位
- 去重铁律：只有当对象的hashCode相同且equals为true时，才判定为重复拒绝存入
- 核心参数：初始容量16，负载因子0.75，链表超8且总数达64则树化
- 避坑指南：自定义对象存入HashSet，必须严格重写hashCode与equals方法
---

# HashSet（Hash表）是什么？

HashSet 是基于 HashMap 实现的 Set 接口，它不允许存储重复元素，且存储顺序不固定。

### 核心原理

1.  **存储结构**
    - 内部维护一个 `HashMap<E, Object>` 实例。
    - 添加到 HashSet 的元素作为 HashMap 的 **Key**。
    - Value 是一个固定的 `private static final Object PRESENT = new Object()` 对象（仅仅为了占位，关联 Map 的 Value）。

2.  **添加逻辑与去重（核心面试点）**
    当调用 `add(e)` 方法时，实际调用的是 `map.put(e, PRESENT)`：
    - **Step 1**：计算元素的 `hashCode()`，通过哈希函数 `(n - 1) & hash` 定位到 HashMap 中的桶索引。
    - **Step 2**：如果该位置为空，直接存入。
    - **Step 3**：如果该位置有元素（哈希冲突），则遍历链表或红黑树：
        - 先比较 `hashCode` 是否相等，不等则视为不同对象。
        - 若 `hashCode` 相等，再调用 `equals()` 方法比较内容。
    - **Step 4**：只有当 `hashCode` 和 `equals()` **都相等**时，HashMap 认为 Key 已存在，`put` 方法返回旧 Value，HashSet 的 `add` 则返回 `false`，拒绝存入。

3.  **扩容机制**
    - 因为底层是 HashMap，扩容机制与 HashMap 一致。
    - **默认容量**：16。
    - **负载因子**：0.75。当元素数量 > 容量 * 0.75 时，触发扩容（`resize`），容量翻倍。
    - **树化阈值**：当单个桶内链表长度 > 8 且总容量 >= 64 时，链表转为红黑树（提高查询效率）。

4.  **注意事项**
    - 存入自定义对象时，**必须重写** `hashCode()` 和 `equals()` 方法，且必须保证一致性（相等的对象必须有相同的 hashCode）。
    - 非线程安全。多线程环境下推荐使用 `CopyOnWriteArraySet` 或 `Collections.synchronizedSet`。

### 实战案例
在电商促销系统中，曾使用 `HashSet` 存储参与“秒杀”的用户ID以去重。某次线上排查发现内存溢出（OOM），原因是未重写用户ID包装类的 `hashCode`，导致所有对象都被当作不同元素存入，且链表过长未及时树化（未达到容量阈值），最终导致哈希表退化成链表，查询性能从 O(1) 恶化到 O(n)。

### 代码示例
```java
// 自定义对象去重实战：确保 hashCode 和 equals 一致
public class User {
    private String name;
    private int age;

    // IDE 自动生成，必须保证相等的对象返回相同的 hash
    @Override
    public int hashCode() {
        return Objects.hash(name, age);
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        User user = (User) o;
        return age == user.age && Objects.equals(name, user.name);
    }
}

Set<User> users = new HashSet<>();
users.add(new User("Alice", 25));
boolean isAdded = users.add(new User("Alice", 25)); // 返回 false，去重生效
```

### 对比表格
| 特性 | HashSet | ArrayList | TreeSet |
| :--- | :--- | :--- | :--- |
| **底层实现** | HashMap (哈希表) | 动态数组 | 红黑树 |
| **元素顺序** | 无序 (不保证插入顺序) | 有序 (保持插入顺序) | 有序 (自然排序或比较器排序) |
| **插入/删除复杂度** | O(1) (平均) | O(n) (涉及数组拷贝) | O(log n) |
| **去重机制** | hashCode() + equals() | equals() (需手动遍历) | compareTo() / equals() |
| **null 值** | 允许一个 null | 允许多个 null | 不允许 null (需比较) |

### 数据结构示意图

```text
HashSet 内部
+---------------------------------------------------+
|  HashMap                                           |
|  +-------+  +-------+  +-------+  +-------+        |
|  | Index |  | Index |  | Index |  | Index | ...    |
|  +---+---+  +---+---+  +---+---+  +---+---+        |
|      |          |          |          |            |
|      v          v          v          v            |
|   [Entry]    [Entry]    null      [Entry]          |
|   /    \                           /    \          |
|  K=Val  K=Val                     K=Val  K=Val     |
|  |PRESET| |PRESET|               |PRESET| |PRESET| |
|  \_____/ \_____/               \_____/ \_____/     |
|                                                     |
|  Entry 中的 K 即 HashSet 的元素                     |
|  Entry 中的 V 即固定的 PRESENT 对象                 |
+---------------------------------------------------+
```

## 常见考点

1.  **HashSet 如何判断元素重复？**
    - 先判断 `hashCode` 是否相同，不同则肯定不是重复对象；若相同，再调用 `equals` 判断。

## 记忆要点

- 底层本质：HashSet底层本质就是HashMap，存入的元素作为Key，Value固定占位
- 去重铁律：只有当对象的hashCode相同且equals为true时，才判定为重复拒绝存入
- 核心参数：初始容量16，负载因子0.75，链表超8且总数达64则树化
- 避坑指南：自定义对象存入HashSet，必须严格重写hashCode与equals方法

## 结构化回答

**30 秒电梯演讲：** 利用HashMap的Key唯一性来实现元素去重。打个比方，像一个不贴标签的篮子，相同的球（内容）只能放进去一个，不管你扔几次。

**展开框架：**
1. **底层本质** — HashSet底层本质就是HashMap，存入的元素作为Key，Value固定占位
2. **去重铁律** — 只有当对象的hashCode相同且equals为true时，才判定为重复拒绝存入
3. **核心参数** — 初始容量16，负载因子0.75，链表超8且总数达64则树化

**收尾：** 我在项目里踩过坑——在电商促销系统中，曾使用 `HashSet` 存储参与“秒杀”的用户ID以去重。您想深入聊哪一段：原理、避坑还是对比选型？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：HashSet（Hash表）是什么 | "HashSet（Hash表）是什么？一句话——像一个不贴标签的篮子，相同的球（内容）只能放进去一个，不管你扔几次。" | 开场钩子 |
| 0:40 | 概念动画/示意图 | "利用HashMap的Key唯一性来实现元素去重——像一个不贴标签的篮子，相同的球（内容）只能放进去一个，不管你扔几次" | 核心定义 |
| 1:20 | 底层本质示意 | "HashSet底层本质就是HashMap，存入的元素作为Key，Value固定占位" | 要点1 |
| 2:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |
