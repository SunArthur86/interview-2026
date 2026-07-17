---
id: core-321
difficulty: L2
category: java-core
feynman:
  essence: hashCode定桶位，equals定具体对象，必须保持逻辑一致。
  analogy: 找人先看他在哪个楼（hashCode），进楼再看具体房间（equals）。如果认定是一个人，那他必须在同一个楼里。
  first_principle: 哈希集合如何高效且准确地判断对象是否存在？
  key_points:
  - equals相等则hashCode必等
  - hashCode相等不一定equals
  - 仅重写equals会导致集合功能失效
  - 必须配对重写
memory_points:
- 契约铁律：equals相等，hashCode必相等；hashCode相等，equals不一定相等。
- 致命后果：只重写equals会导致相同对象在HashMap中算出不同Hash，存进去就查不出来。
- HashMap机制：先用hashCode定位桶位置，再用equals防哈希碰撞，两者缺一不可。
- Lombok避坑：在继承体系下用@Data，务必加@EqualsAndHashCode(callSuper=true)。
---

# equals()和hashCode()的关系是什么？

**规则：**
1. equals相等的两个对象，hashCode必须相等
2. hashCode相等的两个对象，equals不一定相等
3. equals不相等的两个对象，hashCode可以相等（hash冲突）

**为什么要同时重写？**
以HashMap为例，存储和查询依赖这两个方法的配合：

```text
HashMap Put 流程简化：
┌─────────────┐
│  1. hash()  │ 计算 hash = (h = key.hashCode()) ^ (h >>> 16)
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│ 2. 定位桶位置   │ index = hash & (n-1)
└──────┬──────────┘
       │
       ▼
┌─────────────────┐     ┌───────────────────┐
│ 3. 遍历链表/树  │────▶│ 4. hash相等?      │---No──▶ 尾插/Judge树化
└──────┬──────────┘     └─────┬─────────────┘
       │                     │Yes
       ▼                     ▼
┌─────────────────┐   ┌───────────────┐
│   覆盖 Value    │◀──│ 5. equals相等?│---No──▶ 继续遍历
└─────────────────┘   └───────────────┘
```

**核心原理细节：**
1. 如果只重写 equals 不重写 hashCode：两个逻辑上相等（equals为true）的对象，计算出的 hashCode 可能不同。
2. 后果：它们会被存放在 HashMap 的不同桶中。
3. 最终结果：调用 `get(key)` 时，计算出的 hash 定位到错误的桶，导致找不到数据，违反了 Map 契约。

**正确实现：**
```java
@Override
public boolean equals(Object o) {
    // 1. 地址引用相同
    if (this == o) return true;
    // 2. 类型检查（null 检查包含在 instanceof 中）
    if (!(o instanceof Person)) return false;
    Person p = (Person) o;
    // 3. 关键字段比较（基本类型用==，引用类型用Objects.equals）
    return Objects.equals(name, p.name) && age == p.age;
}

@Override
public int hashCode() {
    // 必须保证与 equals 中用到的字段一致
    return Objects.hash(name, age);
}
```

**## 常见考点**
1. **为什么用 `Objects.hash()` 而不是自己写？**
   它内部封装了数组处理，且能处理 null 值，自动计算散列值，减少手动错误。
2. **hashCode 相等但 equals 不等会怎样？**
   这就是 Hash 冲突。HashMap 会拉出链表（或红黑树），虽然能存数据，但会降低查询效率（从 O(1) 退化为 O(n) 或 O(logn)）。
3. **作为 Set 集合元素时为什么要重写？**
   Set (如 HashSet) 底层依赖 HashMap 的 key，不重复特性依赖 hashCode 和 equals，如果不重写会导致重复元素被添加。

---

### 深化内容

**实战案例**：
某系统使用 `Lombok` 的 `@Data` 注解自动生成 `equals`，但在继承体系中，父类包含 ID 字段而子类未重写 `hashCode`，导致两个 ID 相同但类型不同的对象被判定为相等（`equals` 逐字段比较忽略了类型区分）。结果在作为 `HashMap` Key 时发生覆盖，导致严重的数据错乱（资金记录相互覆盖）。

**代码示例（重写示例）**：
```java
// 使用 Lombok 时需注意继承场景，建议手动重写或使用 @EqualsAndHashCode(callSuper=true)
@Override
public int hashCode() {
    int result = 17;
    result = 31 * result + (name == null ? 0 : name.hashCode());
    result = 31 * result + age;
    return result;
}

@Override
public boolean equals(Object obj) {
    if (this == obj) return true;
    if (obj == null || getClass() != obj.getClass()) return false;
    Person person = (Person) obj;
    return age == person.age && Objects.equals(name, person.name);
}
```

**对比表格（HashCode 状态对比）**：

| 场景 | 只重写 equals | 只重写 hashCode | 正确重写两者 |
| :--- | :--- | :--- | :--- |
| 逻辑相等对象 | 可能存入不同桶 | 存入同一桶 | 存入同一桶 |
| HashMap 查找 | 找不到数据 | 找得到（但需遍历链表） | O(1) 直接命中 |
| HashSet 去重 | 失败（出现重复） | 失败（误判为相同） | 成功 |
| 约定合规性 | 违反（hashCode 不一致） | 违反（equals 不一致） | 符合规范 |

## 记忆要点

- 契约铁律：equals相等，hashCode必相等；hashCode相等，equals不一定相等。
- 致命后果：只重写equals会导致相同对象在HashMap中算出不同Hash，存进去就查不出来。
- HashMap机制：先用hashCode定位桶位置，再用equals防哈希碰撞，两者缺一不可。
- Lombok避坑：在继承体系下用@Data，务必加@EqualsAndHashCode(callSuper=true)。

## 结构化回答

**30 秒电梯演讲：** hashCode定桶位，equals定具体对象，必须保持逻辑一致。打个比方，找人先看他在哪个楼（hashCode），进楼再看具体房间（equals）。如果认定是一个人，那他必须在同一个楼里。

**展开框架：**
1. **契约铁律** — equals相等，hashCode必相等；hashCode相等，equals不一定相等。
2. **致命后果** — 只重写equals会导致相同对象在HashMap中算出不同Hash，存进去就查不出来。
3. **HashMap机制** — 先用hashCode定位桶位置，再用equals防哈希碰撞，两者缺一不可。

**收尾：** 我在项目里踩过坑——某系统使用 `Lombok` 的 `@Data` 注解自动生成 `equals`，但在继承体系中，父类包含 ID 字段而子类未重写 `hashCode`，导致两个 ID 相同但类型不同的对象被判定为相等（`equals` 逐字段比较忽略了类型区分）。您想深入聊哪一段：原理、避坑还是对比选型？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：equals()和hashCode(… | "equals()和hashCode()的关系是什么？一句话——找人先看他在哪个楼（hashCode），进楼再看具体房间（equals）。如果认定是一个人，那他必须在同一个楼里。" | 开场钩子 |
| 0:40 | 概念动画/示意图 | "hashCode定桶位，equals定具体对象，必须保持逻辑一致——找人先看他在哪个楼（hashCode），进楼再看具体房间（equals）。如果认定是一个人，那他必须在同一个楼里" | 核心定义 |
| 1:20 | 契约铁律示意 | "equals相等，hashCode必相等；hashCode相等，equals不一定相等。" | 要点1 |
| 2:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |
