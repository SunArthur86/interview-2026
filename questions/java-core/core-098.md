---
id: core-098
difficulty: L2
category: java-core
feynman:
  essence: 基于StringBuilder和常量池的内存操作
  analogy: 原本写在纸上的字（String）不能改，要拼接就得拿新纸抄写；编译器会帮你自动用草稿纸（StringBuilder）优化过程
  first_principle: 在字符串不可变的前提下，如何高效地进行字符串组合操作？
  key_points:
  - 常量拼接在编译期完成
  - 变量拼接使用StringBuilder实现
  - 循环中务必手动用StringBuilder避免频繁创建对象
memory_points:
- 不可变性：字符串拼接本质是创建新的字符串对象
- 常量优化：纯字面量拼接在编译期直接合为一个常量，不走StringBuilder
- 变量拼接：底层被编译器优化为 StringBuilder 的 append 与 toString 操作
- 性能雷区：循环内使用+拼接，每次都会 new 对象，应改为循环外提创建 SB
---

# 什么是字符串拼接发生了什么？

### 字符串拼接发生了什么

在 Java 中，字符串是不可变的，所有的拼接操作本质上都是创建新的字符串对象。

#### 1. 常量拼接
```java
String s = "a" + "b";
```
- **编译期优化**：如果拼接的都是字面量常量，编译器在编译阶段就会将其直接优化为 `"ab"`。 Class 文件中不存在加号操作，直接从常量池加载。

#### 2. 变量拼接
```java
String s1 = "a";
String s2 = "b";
String s3 = s1 + s2;
```
- **编译器优化**：编译器会自动创建 `StringBuilder` 对象，并调用其 `append()` 方法。
- **等价代码**：`new StringBuilder().append(s1).append(s2).toString();`
- **性能**：在单次拼接中效率尚可。

#### 3. 循环中的拼接
```java
String str = "";
for (int i = 0; i < 100; i++) {
    str += i;
}
```
- **性能问题**：编译器会在每次循环时创建一个新的 `StringBuilder` 对象，拼接后转成 String 赋给 str，导致产生大量中间对象和 GC 压力。
- **优化建议**：应显式在循环外创建 `StringBuilder`，循环内调用 `append()`。

#### 4. concat() 方法
`String.concat(String str)` 方法内部会创建一个新的字符数组，长度为两者之和，然后复制数据。它也是创建新对象，效率不如 `StringBuilder` 的扩容机制灵活。

#### 5. 字符串常量池
字符串常量池是 JVM 堆内存中的一块特殊区域，用于存储字符串字面量。通过 `String.intern()` 方法可以将手动创建的字符串放入池中，如果池中已存在，则返回引用。

#### 6. Java 9 的优化
- Java 9 引入了 `invokedynamic` 指令和 `StringConcatFactory`。对于 `+` 号拼接，不再硬编码生成 `StringBuilder`，而是根据动态策略生成调用字节码。这使得未来可以替换更高效的拼接算法（如基于 `java.lang.invoke`），且性能在某些场景下优于手动 `StringBuilder`。

#### 编译期处理流程图
```text
   Java 代码: "a" + "b" + s1
       │
       ▼
   编译器分析
       │
   ┌───┴────┐
   │        │
   ▼        ▼
全是常量    含有变量
   │        │
   ▼        ▼
直接合成   优化为 StringBuilder
"ab"       .append("a").append(s1).toString()
```

#### 拼接方式对比
| 特性 | `+` 号操作符 | `StringBuilder` | `String.concat` | `String.format` |
| :--- | :--- | :--- | :--- | :--- |
| **底层原理** | 编译器优化为 StringBuilder 或直接合成 | 动态数组扩容 (`AbstractStringBuilder`) | 创建新数组，数组拷贝 (`System.arraycopy`) | Formatter 解析，临时对象多 |
| **适用场景** | 简单、单次拼接 | 循环中、大量拼接 | 两个字符串拼接 | 复杂格式化 (如日志、日期) |
| **线程安全** | 非线程安全 (编译后依赖 SB) | **非线程安全** | 线程安全 (本身不可变) | 线程安全 |
| **性能** | 循环中极差，单次好 | **极佳** | 一般 (次优) | 差 (最慢) |

#### 实战案例
在高并发的日志打印场景中，若使用 `"Result=" + code + ", msg=" + msg` 进行字符串拼接，且代码位于 `if (logger.isDebugEnabled())` 判断之外，即使日志级别不满足，拼接操作依然会执行，消耗 CPU。**建议**：始终使用占位符 `logger.debug("Result={}, msg={}", code, msg)`，既避免无谓拼接，又保持代码清晰。

#### 关键代码示例
```java
// 错误示范：循环内拼接，产生约100个临时对象
String s = "";
for(int i=0; i<100; i++) { s += i; }

// 正确示范：循环外复用 StringBuilder
StringBuilder sb = new StringBuilder();
for(int i=0; i<100; i++) { sb.append(i); }
String result = sb.toString();
```

## 常见考点
1. **StringBuilder vs StringBuffer**：两者的区别？后者是线程安全的（方法加 `synchronized`），前者非线程安全但性能更高。
2. **intern() 机制**：JDK 6 与 JDK 7/8 中 `intern()` 的实现有何不同？（JDK 6 永久代，JDK 7+ 移至堆中；是否重复拷贝字符串的区别）。
3. **`javap` 指令验证**：是否使用过 `javap -c` 查看字节码来验证字符串拼接底层使用的是 `StringBuilder`？

## 记忆要点

- 不可变性：字符串拼接本质是创建新的字符串对象
- 常量优化：纯字面量拼接在编译期直接合为一个常量，不走StringBuilder
- 变量拼接：底层被编译器优化为 StringBuilder 的 append 与 toString 操作
- 性能雷区：循环内使用+拼接，每次都会 new 对象，应改为循环外提创建 SB

## 结构化回答

**30 秒电梯演讲：** 基于StringBuilder和常量池的内存操作。打个比方，原本写在纸上的字（String）不能改，要拼接就得拿新纸抄写；编译器会帮你自动用草稿纸（StringBuilder）优化过程。

**展开框架：**
1. **不可变性** — 字符串拼接本质是创建新的字符串对象
2. **常量优化** — 纯字面量拼接在编译期直接合为一个常量，不走StringBuilder
3. **变量拼接** — 底层被编译器优化为 StringBuilder 的 append 与 toString 操作

**收尾：** 这三点都能配合实战聊。您想深入聊原理、对比还是避坑？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：什么是字符串拼接发生了什么 | "什么是字符串拼接发生了什么？一句话——原本写在纸上的字（String）不能改，要拼接就得拿新纸抄写；编译器会帮你自动用草稿纸（StringBuilder）优化过程。" | 开场钩子 |
| 0:40 | 概念动画/示意图 | "基于StringBuilder和常量池的内存操作——原本写在纸上的字（String）不能改，要拼接就得拿新纸抄写；编译器会帮你自动用草稿纸（StringBuilder）优化过程" | 核心定义 |
| 1:20 | 不可变性示意 | "字符串拼接本质是创建新的字符串对象" | 要点1 |
| 2:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |
