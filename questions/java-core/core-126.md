---
id: core-126
difficulty: L2
category: java-core
feynman:
  essence: 字节流是二进制传输，字符流是文本传输
  analogy: 运煤（字节）和运信（字符）的区别
  first_principle: 如何高效地在不同数据格式和编码间转换
  key_points:
  - 字节流：处理二进制数据（图片、视频），8位
  - 字符流：处理文本数据，16位Unicode
  - 转换：InputStreamReader/OutputStreamWriter
  - 缓冲：BufferedReader/Writer提高效率
memory_points:
- 基本单元：字节流操作 8 位字节，字符流操作 16 位 Unicode 字符。
- 基类区别：字节流是 InputStream/OutputStream，字符流是 Reader/Writer。
- 核心场景：字节流处理音视频等二进制，字符流处理纯文本防乱码。
- 桥梁转换：InputStreamReader/OutputStreamWriter 实现字节转字符，需指定编码。
- 设计模式：IO 流底层大量使用装饰器模式（如 BufferedInputStream 增加缓冲）。
---

# 字节流和字符流的区别？

Java IO 流根据处理数据单元的不同，分为**字节流**（Byte Stream）和**字符流**（Character Stream）。理解两者的区别及转换机制是 IO 处理的基础。

### 1. 核心区别对比表

| 特性 | 字节流 | 字符流 |
| :--- | :--- | :--- |
| **基本单元** | 8位字节 (1 Byte) | 16位 Unicode 字符 (2 Bytes) |
| **顶级基类** | `InputStream`, `OutputStream` | `Reader`, `Writer` |
| **适用场景** | 处理二进制数据（图片、音频、视频、文件拷贝） | 处理文本数据（txt, xml, 读取控制台输出） |
| **编码问题** | 不涉及编码，原样传输 | 必须指定字符集（UTF-8, GBK等），否则乱码 |
| **缓冲** | `BufferedInputStream` / `BufferedOutputStream` | `BufferedReader` / `BufferedWriter` (支持按行读取) |

### 2. 为什么需要字符流？

Java 内部使用 `char` 类型（UTF-16）表示字符。而文件或网络传输通常使用字节（ASCII, UTF-8 等）。

- **字节流的问题**：如果直接用字节流读取文本，需要手动将字节转换为字符，处理多字节字符（如中文在 UTF-8 中占 3 字节）时极易出现“半个汉字”或乱码问题。
- **字符流的优势**：字符流底层封装了字节到字符的解码过程，提供了 `readLine()` 等便捷方法，适合处理文本。

### 3. 字节流与字符流的转换（桥梁）

**转换流** `InputStreamReader` 和 `OutputStreamWriter` 是两者之间的桥梁，它们属于**字符流**，但构造时接收字节流。

```text
File (字节)  -> FileInputStream (字节流) -> InputStreamReader (解码) -> BufferedReader (字符流)
```

- **InputStreamReader**：将字节输入流按指定字符集解码为字符流。
- **OutputStreamWriter**：将字符流按指定字符集编码为字节流输出。

### 4. 使用场景详解

#### A. 字节流 (使用 `FileInputStream` / `FileOutputStream`)

```java
// 拷贝图片、压缩包等二进制文件
try (FileInputStream fis = new FileInputStream("input.jpg");
     FileOutputStream fos = new FileOutputStream("output.jpg")) {
    int b;
    while ((b = fis.read()) != -1) {
        fos.write(b);
    }
}
```
**注意**：不要用字符流操作图片等非文本文件，否则数据会被破坏。

#### B. 字符流 (使用 `FileReader` / `FileWriter` 或转换流)

```java
// 读取文本文件，推荐使用转换流明确指定编码，防止乱码
try (InputStreamReader isr = new InputStreamReader(new FileInputStream("test.txt"), "UTF-8");
     BufferedReader br = new BufferedReader(isr)) {
    String line;
    while ((line = br.readLine()) != null) {
        System.out.println(line);
    }
}
```

### 5. 补充：设计模式（装饰器模式）

Java IO 大量使用了**装饰器模式**。
- **基础组件**：`FileInputStream` (节点流，直接接触数据源)。
- **装饰组件**：`BufferedInputStream` (处理流，给节点流增加缓冲功能)。

```text
InputStream is = new FileInputStream("a.txt"); // 节点流
InputStream bis = new BufferedInputStream(is);   // 装饰流，增强功能
```

## 常见考点

1. **使用字节流读取汉字为什么会出现乱码？**
   - UTF-8 中一个汉字占 3 个字节。如果使用 `read()` 读取一个字节并强制转换为 `char`，或者读取的字节数不是 3 的倍数，就会破坏字符的编码结构，导致乱码。解决方法是使用字符流或 `byte[]` 缓冲区正确解码。

2. **有了字节流为什么还要有缓冲流？**
   - 直接读写磁盘或网络是昂贵操作。缓冲流在内存中维护一个数组（buffer），每次读写一大块数据，减少底层系统调用的次数，显著提升 IO 性能。

3. **`new FileReader("file.txt")` 和 `new InputStreamReader(new FileInputStream("file.txt"), "UTF-8")` 有什么区别？**
   - `FileReader` 使用系统默认字符集（不可控，跨平台可能乱码）。
   - `InputStreamReader` 可以显式指定字符集编码（推荐用法）。

## 记忆要点

- 基本单元：字节流操作 8 位字节，字符流操作 16 位 Unicode 字符。
- 基类区别：字节流是 InputStream/OutputStream，字符流是 Reader/Writer。
- 核心场景：字节流处理音视频等二进制，字符流处理纯文本防乱码。
- 桥梁转换：InputStreamReader/OutputStreamWriter 实现字节转字符，需指定编码。
- 设计模式：IO 流底层大量使用装饰器模式（如 BufferedInputStream 增加缓冲）。

## 结构化回答

**30 秒电梯演讲：** 字节流是二进制传输，字符流是文本传输。打个比方，运煤（字节）和运信（字符）的区别。

**展开框架：**
1. **基本单元** — 字节流操作 8 位字节，字符流操作 16 位 Unicode 字符。
2. **基类区别** — 字节流是 InputStream/OutputStream，字符流是 Reader/Writer。
3. **核心场景** — 字节流处理音视频等二进制，字符流处理纯文本防乱码。

**收尾：** 这三点都能配合实战聊。您想深入聊原理、对比还是避坑？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：字节流和字符流的区别 | "字节流和字符流的区别？一句话——运煤（字节）和运信（字符）的区别。" | 开场钩子 |
| 0:40 | 概念动画/示意图 | "字节流是二进制传输，字符流是文本传输——运煤（字节）和运信（字符）的区别" | 核心定义 |
| 1:20 | 基本单元示意 | "字节流操作 8 位字节，字符流操作 16 位 Unicode 字符。" | 要点1 |
| 2:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |
