---
id: core-168
difficulty: L3
category: java-core
feynman:
  essence: List存单值列表，Map存键值对映射。
  analogy: List是花名册（按名单找人），Map是字典（按页码找字）。
  first_principle: 如何根据数据查询方式（按索引查 vs 按键值查）选择合适的容器？
  key_points:
  - List存储单值，Map存储键值对
  - List允许重复，Map的Key不可重复
  - List有序可索引，Map通常无序通过Key查找
  - List常用ArrayList，Map常用HashMap
memory_points:
- 数据结构对比：List是单列集合允许重复且有序，Map是双列双列Key不可重复。
- 访问方式差异：List支持索引下标O(1)访问，Map通过Key映射快速获取Value。
- Null值处理：List通常允许多个null，HashMap仅允许1个null Key。
- 选型口诀：线性排序选List，键值映射与快速查找选Map。
---

# List和Map有什么区别？

### List 和 Map 的主要区别

| 特性 | List | Map |
|:------|:------|:-----|
| **数据结构** | 单列集合，存储单个元素 | 双列集合，存储键值对 |
| **元素重复** | **允许重复**元素 | **Key 不允许重复**，Value 可以重复 |
| **顺序性** | **有序**（存储和取出顺序一致） | 大部分实现无序，TreeMap/LinkedHashMap 可排序或保持顺序 |
| **索引访问** | 支持索引下标访问（如 `list.get(0)`） | 不支持索引，通过 Key 访问 Value（`map.get(key)`） |
| **常见实现** | ArrayList, LinkedList, Vector | HashMap, TreeMap, ConcurrentHashMap |
| **典型场景** | 存储序列数据、列表 | 存储配置信息、ID与对象的映射、缓存 |

### 总结
- List 是线性表，侧重于“列表”和“索引”操作。
- Map 是映射表，侧重于通过 Key 快速查找 Value（映射关系）。

### 增强细节：接口视角的对比
```
   Collection (Interface)          Map (Interface)
          │                             │
    ┌─────┴─────┐                     ┌──┴──┐
    │   add(E)  │                     │ put(K,V)
    │ get(int) │                     │ get(K) │
    │ remove()  │                     │ remove(K)│
    └───────────┘                     └───────┘
```
- List 继承自 Iterable，支持 `forEach` 和 `Iterator`。
- Map 虽然不继承 Collection，但提供了 `entrySet()`、`keySet()` 和 `values()` 视图，这些视图返回的集合是支持迭代和删除操作的。

### 增强细节：Null 值处理
- **List**：通常允许多个 null 元素（ArrayList, LinkedList）。
- **Map**：HashMap 允许一个 null key 和多个 null value；ConcurrentHashMap 不允许 null key 和 null value（多线程下无法区分是“没有值”还是“值为null”的二义性）；TreeMap 不允许 null key（比较时会抛 NPE），但 value 允许 null。

### 常见考点
1. **ArrayList 和 HashMap 的扩容机制区别**：ArrayList 扩容 1.5 倍，HashMap 扩容 2 倍。
2. **如何选择 List 还是 Map**：如果数据是一维的、有顺序的（如用户列表），选 List；如果是需要通过唯一标识快速查找的（如 ID->User），选 Map。
3. **Map 的 values() 方法返回的 List 可以修改吗**：返回的是 Collection，且不支持 add 操作（结构修改受限），支持 remove。
4. **如果想用 List 存储键值对**：通常定义一个包含 key/value 字段的类，或者直接存储 Map.Entry 对象。

### 5. 实战深化
#### 实战案例
在实现 **“部门-员工”** 数据结构时，如果使用 `List<Employee>`，查询某个部门的所有员工需要遍历整个列表（O(N)）；改用 `Map<DeptId, List<Employee>>` 后，通过部门 ID 查询员工列表的时间复杂度降为 O(1)。但在需要“所有员工按入职时间排序打印”时，必须将 Map 的 values() 转回 List 处理。

#### 代码示例
```java
// List: 适合按索引/顺序操作
List<String> users = new ArrayList<>();
users.add("Alice");
String firstUser = users.get(0); // O(1)

// Map: 适合键值对快速查找
Map<Long, User> userMap = new HashMap<>();
userMap.put(1001L, new User("Bob"));
User bob = userMap.get(1001L); // O(1) 快速定位
```


## 记忆要点

- 数据结构对比：List是单列集合允许重复且有序，Map是双列双列Key不可重复。
- 访问方式差异：List支持索引下标O(1)访问，Map通过Key映射快速获取Value。
- Null值处理：List通常允许多个null，HashMap仅允许1个null Key。
- 选型口诀：线性排序选List，键值映射与快速查找选Map。

## 结构化回答

**30 秒电梯演讲：** List存单值列表，Map存键值对映射。打个比方，List是花名册（按名单找人），Map是字典（按页码找字）。

**展开框架：**
1. **数据结构对比** — List是单列集合允许重复且有序，Map是双列双列Key不可重复。
2. **访问方式差异** — List支持索引下标O(1)访问，Map通过Key映射快速获取Value。
3. **Null值处理** — List通常允许多个null，HashMap仅允许1个null Key。

**收尾：** 我在项目里踩过坑——在实现 “部门-员工” 数据结构时，如果使用 `List<Employee>`，查询某个部门的所有员工需要遍历整个列表（O(N)）；改用 `Map<DeptId, List<Employee>>` 后，通过部门 ID 查询员工列表的时间复杂度降为 O(1)。您想深入聊哪一段：原理、避坑还是对比选型？

## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：List和Map有什么区别 | "List和Map有什么区别？一句话——List是花名册（按名单找人），Map是字典（按页码找字）。" | 开场钩子 |
| 0:45 | 概念动画/示意图 | "List存单值列表，Map存键值对映射——List是花名册（按名单找人），Map是字典（按页码找字）" | 核心定义 |
| 1:30 | 数据结构对比示意 | "List是单列集合允许重复且有序，Map是双列双列Key不可重复。" | 要点1 |
| 2:15 | 访问方式差异示意 | "List支持索引下标O(1)访问，Map通过Key映射快速获取Value。" | 要点2 |
| 3:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |
