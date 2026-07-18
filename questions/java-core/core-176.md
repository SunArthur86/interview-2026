---
id: core-176
difficulty: L3
category: java-core
feynman:
  essence: String是不可变对象，利用常量池共享内存。
  analogy: 像刻好的石碑，一旦刻好不可修改，多人可以指着同一个石碑念。
  first_principle: 如何高效处理大量重复的字符串数据？
  key_points:
  - final修饰类和数组，不可变
  - 字符串常量池位于堆中
  - 直接赋值使用池中已有对象
  - JDK9底层由char[]改为byte[]省空间
memory_points:
- 核心特性：类与底层value数组均final修饰，故天然线程安全且不可变。
- 版本对比：JDK8底层为定长2字节char[]，JDK9+改为byte[]加coder标识。
- 常量池变迁：JDK1.7由永久代转移至堆内存，减少GC压力防OOM。
- intern()机制：JDK6拷贝字符串至永久代，JDK7+仅拷贝堆对象引用。
---

# String存储原理是什么？

### Java String 存储原理

#### 1. 不可变性
String 类被 `final` 修饰，不可被继承。其内部存储数据的数组（JDK 9+ 为 `byte[]`，JDK 8 为 `char[]`）也被 `final` 修饰，这意味着 String 对象一旦创建，其值**不可改变**。

**原理细节**：
- **安全性**：不可变性使得 String 天然线程安全，无需同步。
- **Hash 缓存**：String 重写了 `hashCode()`，并缓存了 hash 值（`hash` 字段），因为 String 不可变，所以 hash 值计算一次即可，重复使用，这使得 String 非常适合作为 HashMap 的 Key。
- **反射破坏**：虽然 String 设计为不可变，但通过反射机制可以修改其内部 `value` 数组的值，但这破坏了安全性，不推荐使用。

#### 2. 字符串常量池
*   **位置**：JDK 1.7 之前位于永久代，JDK 1.7 及以后转移到了**堆** 中。
*   **作用**：为了减少内存开销，JVM 维护了一块特殊的存储区域——字符串常量池。当使用双引号直接赋值（如 `String s = "abc"`）时，JVM 会先检查池中是否存在该字符串：
    *   **存在**：直接返回引用。
    *   **不存在**：在池中创建该字符串并返回引用。
    *   `intern()` 方法：可以手动将堆中的字符串对象放入常量池。如果池中已存在等于该 String 对象的字符串，则返回池中的引用；否则，将此 String 对象包含的字符串添加到常量池中，并返回此 String 对象的引用（JDK 6/7/8 实现略有不同，JDK 7+ 将堆中的引用拷贝到池中）。

#### 3. 内存布局
*   **JDK 8 及以前**：底层使用 `char[]` 数组，每个字符占 2 字节，采用 UTF-16 编码。
*   **JDK 9 及以后**：底层改为 `byte[]` 数组，引入了 `coder`（编码标识）。如果是纯拉丁字符（ASCII），使用 Latin-1 编码（每字符 1 字节），节省内存；如果是汉字等，使用 UTF-16 编码。

```text
┌─────────────────────────────────────────────┐
│              Java Object Header             │
├─────────────────────────────────────────────┤
│  hash (int)  │  coder (byte)  │  (flags...) │
├─────────────────────────────────────────────┤
│           value (byte[] or char[])          │
│  [索引0] [索引1] [索引2] ... [索引len-1]    │
└─────────────────────────────────────────────┘
```

## 实战案例：内存泄漏排查与 intern
在处理海量的 Excel 导入数据（如数百万行地址信息）时，发现堆内存迅速溢出。代码逻辑是读取每一行地址字符串并进行处理。虽然局部变量在方法结束应被回收，但由于大量地址前缀（如“广东省深圳市”）高度重复，且代码中不小心显式调用了 `str.intern()`（或依赖于某些 JSON 库的 intern 机制），导致这些字符串被永久放入了常量池（位于堆中但生命周期通常很长），且常量池大小难以通过常规 GC 回收，最终导致 OOM。**解决方案**：在确定不需要重复利用的场景下，慎用 `intern`，或限制数据导入批次大小。

## 代码示例：JDK 版本差异与 intern
```java
// JDK 6 vs JDK 7+ intern 行为差异
String s1 = new String("a");
s1.intern(); // 常量池中已有 "a"
String s2 = "a";
System.out.println(s1 == s2); // false，s1 指向堆，s2 指向池

String s3 = new String("b") + new String("c");
s3.intern();
String s4 = "bc";
// JDK 7+ 返回 true，因为 intern() 将堆中的引用拷贝到了常量池
// JDK 6 返回 false，因为 intern() 是拷贝对象到永久代
System.out.println(s3 == s4); 
```

## String 字符编码对比

| 版本 | 底层实现 | 编码方式 | 空间占用 | 典型场景影响 |
| :--- | :--- | :--- | :--- | :--- |
| **JDK 8** | `char[]` | UTF-16 (BE) | 固定 2字节/字符 | 存储纯英文浪费 50% 空间 |
| **JDK 9+** | `byte[]` | Latin-1 (默认) / UTF-16 | 1字节 (ASCII) / 2字节 (中文) | 内部字符串内存占用显著下降，GC 压力减小 |

#### ## 常见考点
1. **字符串拼接（+）的原理**：编译期常量优化 vs 运行期 `StringBuilder` 优化。
2. **`intern()` 的内存变化**：JDK 6 将字符串复制永久代 vs JDK 7+ 将堆引用复制到常量池。
3. **String 为什么不可变？**：安全性（如网络参数、文件路径）、线程安全、Hash 缓存、常量池实现基础。



## 核心流程图

```mermaid
flowchart TD
    NEW(["String s = #quot;abc#quot;"]):::start --> JMM["在堆中创建对象<br/>final char["]/byte[] value]
    JMM --> FINAL[value数组final<br/>不可重新赋值]
    FINAL --> IMM["内容不可变<br/>#quot;abc#quot;永远等于#quot;abc#quot;"]
    IMM --> BEN{不可变带来的好处}:::decision
    BEN -->|1 线程安全| TS[多线程共享无需同步<br/>天然不可变]
    BEN -->|2 hashCode缓存| HC[计算一次缓存<br/>适合做Map的key]
    BEN -->|3 字符串常量池| POOL[相同字面量复用<br/>节省内存]:::async
    BEN -->|4 安全性| SEC[作为参数传递<br/>不可被恶意修改]
    BEN -->|5 不可变支持| SUB["substring/concat<br/>返回新对象 不改原对象"]
    POOL --> EQ{s == s2 ?}:::decision
    EQ -->|字面量 字面量| Y[true 同一引用]:::success
    EQ -->|new String new String| N[false 堆中新对象]:::error
    EQ -->|intern| IN[手动入池<br/>返回常量池引用]
    NEW --> MOD{需要频繁修改?}:::decision
    MOD -->|否| USE_S[继续用String]
    MOD -->|是 拼接循环| SB[改用StringBuilder<br/>避免创建大量中间对象]
    SB --> BUF["可变char["] 缓冲区<br/>append高效]
        classDef start fill:#e3f2fd,stroke:#1976d2,stroke-width:2px,color:#0d47a1
    classDef decision fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#e65100
    classDef success fill:#e8f5e9,stroke:#388e3c,stroke-width:2px,color:#1b5e20
    classDef error fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#b71c1c
    classDef storage fill:#eceff1,stroke:#455a64,stroke-width:2px,color:#263238
    classDef async fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#4a148c
```
## 记忆要点

- 核心特性：类与底层value数组均final修饰，故天然线程安全且不可变。
- 版本对比：JDK8底层为定长2字节char[]，JDK9+改为byte[]加coder标识。
- 常量池变迁：JDK1.7由永久代转移至堆内存，减少GC压力防OOM。
- intern()机制：JDK6拷贝字符串至永久代，JDK7+仅拷贝堆对象引用。

## 结构化回答

**30 秒电梯演讲：** String是不可变对象，利用常量池共享内存。打个比方，像刻好的石碑，一旦刻好不可修改，多人可以指着同一个石碑念。

**展开框架：**
1. **核心特性** — 类与底层value数组均final修饰，故天然线程安全且不可变。
2. **版本对比** — JDK8底层为定长2字节char[]，JDK9+改为byte[]加coder标识。
3. **常量池变迁** — JDK1.7由永久代转移至堆内存，减少GC压力防OOM。

**收尾：** 我在项目里踩过坑——实战案例：内存泄漏排查与 intern。您想深入聊哪一段：原理、避坑还是对比选型？

## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：String存储原理是什么 | "String存储原理是什么？一句话——像刻好的石碑，一旦刻好不可修改，多人可以指着同一个石碑念。" | 开场钩子 |
| 0:45 | 概念动画/示意图 | "String是不可变对象，利用常量池共享内存——像刻好的石碑，一旦刻好不可修改，多人可以指着同一个石碑念" | 核心定义 |
| 1:30 | 核心特性示意 | "类与底层value数组均final修饰，故天然线程安全且不可变。" | 要点1 |
| 2:15 | 版本对比示意 | "JDK8底层为定长2字节char[]，JDK9+改为byte[]加coder标识。" | 要点2 |
| 3:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |
