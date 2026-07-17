---
id: core-068
difficulty: L2
category: java-core
feynman:
  essence: 数据传输的管道，分字节（8位）和字符（16位）流。
  analogy: 水管运送水，I/O流运送字节或字符数据。
  first_principle: 如何抽象不同数据源的统一读写方式？
  key_points:
  - 按流向分输入流和输出流
  - 按单位分字节流和字符流
  - 按功能分节点流和处理流
  - 四大基类：InputStream/OutputStream, Reader/Writer
memory_points:
- 核心概念：Java以字节(byte)为基本单位处理数据流向的机制
- 基础分类：字节流处理二进制(如音视频)，字符流处理纯文本(解决乱码)
- 性能优化：因为节点流逐字节读写引发频繁IO，所以用缓冲流(如8KB包装)批量读写
- 资源释放：务必用try-with-resources语法，自动调用close防止句柄泄露
---

# 什么是IO流基本认识？

### IO流基本认识

Java中的I/O（Input/Output）流是用于处理输入和输出的机制。I/O 流以字节（byte）为基本单位，提供了一种灵活的方式来读取和写入数据。I/O 流分为输入流和输出流，根据数据的流向分为输入和输出。

Java的I/O流主要分为两大类：字节流和字符流。字节流用于处理原始的二进制数据，而字符流用于处理文本数据。

#### 1. 字节流
- **InputStream 和 OutputStream**：是所有字节输入流和输出流的抽象基类。它们分别用于读取和写入字节。
- **FileInputStream 和 FileOutputStream**：用于从文件中读取字节和向文件中写入字节。
- **ByteArrayInputStream 和 ByteArrayOutputStream**：分别用于从字节数组中读取数据和将数据写入字节数组。

#### 2. 字符流
- **Reader 和 Writer**：是所有字符输入流和输出流的抽象基类。它们分别用于读取和写入字符。
- **FileReader 和 FileWriter**：用于从文件中读取字符和向文件中写入字符。
- **BufferedReader 和 BufferedWriter**：用于提供缓冲区，提高读取和写入的效率。

#### 3. 高级流
- **ObjectInputStream 和 ObjectOutputStream**：用于读取和写入对象。可以序列化和反序列化对象。

**实战案例**：
在生产环境中，直接使用 `FileInputStream` 逐字节读取大文件会导致性能极差（频繁的磁盘 I/O 系统调用）。正确的做法是使用 `BufferedInputStream` 包装流，利用默认 8KB 的缓冲区批量读取。此外，在处理流关闭时，若流 A 依赖流 B（如 `new BufferedReader(new FileReader(...))`），关闭最外层流 A 时会自动关闭内层流 B，但手动将流声明放在 try-with-resources 块中是最安全的做法，能防止句柄泄露。

**代码示例 (Java Try-with-resources)**：
```java
// 推荐做法：使用 try-with-resources 自动关闭流
try (BufferedReader br = new BufferedReader(new FileReader("input.txt"));
     BufferedWriter bw = new BufferedWriter(new FileWriter("output.txt"))) {
    
    String line;
    while ((line = br.readLine()) != null) {
        bw.write(line);
        bw.newLine(); // 跨平台换行
    }
} catch (IOException e) {
    e.printStackTrace();
}
// 离开 try 块时，br 和 bw 会自动按顺序关闭
```

**代码示例 (JDK 7+ NIO)**：
```java
// 使用 Files.copy 一行代码完成文件复制，底层自动优化
import java.nio.file.*;
Files.copy(Paths.get("source.txt"), Paths.get("dest.txt"), StandardCopyOption.REPLACE_EXISTING);
```

## 记忆要点

- 核心概念：Java以字节(byte)为基本单位处理数据流向的机制
- 基础分类：字节流处理二进制(如音视频)，字符流处理纯文本(解决乱码)
- 性能优化：因为节点流逐字节读写引发频繁IO，所以用缓冲流(如8KB包装)批量读写
- 资源释放：务必用try-with-resources语法，自动调用close防止句柄泄露

## 结构化回答

**30 秒电梯演讲：** 数据传输的管道，分字节（8位）和字符（16位）流。打个比方，水管运送水，I/O流运送字节或字符数据。

**展开框架：**
1. **核心概念** — Java以字节(byte)为基本单位处理数据流向的机制
2. **基础分类** — 字节流处理二进制(如音视频)，字符流处理纯文本(解决乱码)
3. **性能优化** — 因为节点流逐字节读写引发频繁IO，所以用缓冲流(如8KB包装)批量读写

**收尾：** 这三点都能配合实战聊。您想深入聊原理、对比还是避坑？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：什么是IO流基本认识 | "什么是IO流基本认识？一句话——水管运送水，I/O流运送字节或字符数据。" | 开场钩子 |
| 0:40 | 概念动画/示意图 | "数据传输的管道，分字节（8位）和字符（16位）流——水管运送水，I/O流运送字节或字符数据" | 核心定义 |
| 1:20 | 核心概念示意 | "Java以字节(byte)为基本单位处理数据流向的机制" | 要点1 |
| 2:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |
