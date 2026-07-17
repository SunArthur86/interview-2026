---
id: conc-006
difficulty: L1
category: concurrent
feynman:
  essence: 将对象高效压缩为二进制流以减少传输体积和CPU耗时。
  analogy: 把行李（对象）压缩成真空袋（二进制流），省空间好搬运。
  first_principle: 如何在网络传输中平衡数据的体积（带宽）与转换的代价（CPU）？
  key_points:
  - 相比 Java 原生序列化，体积更小，速度更快。
  - 常见框架：Protobuf, Thrift, Kryo。
  - 多用于 RPC 调用和数据持久化。
  - 通常跨语言支持更好（如 Protobuf）。
memory_points:
- 性能对比：因为二进制省去字段名且变长编码，所以比JSON快且小
- 选型对比：Protobuf跨语言强且Schema强约束，Kryo极快但限Java
- 演进机制：Protobuf靠Tag匹配，所以新增字段能兼容但不可改旧Tag
- 实战替换：RPC或MQ场景中，将JSON换成Protobuf可大幅降带宽提吞吐
---

# 什么是高性能的序列化框架？

在网络通信（如 RPC）中，序列化是将对象转换为字节流以便传输的过程。性能瓶颈通常在于**空间占用（带宽）**和**CPU 消耗（编解码速度）**。

**常见的高性能序列化框架：**

1. **Protobuf (Google Protocol Buffers)**
   - **原理**：使用 `.proto` 文件定义 Schema，通过 IDL 编译器生成代码。编码时采用 Varint（变长整数）编码，去除多余字段名，仅保留 Tag 和值。
   - **参数**：Tag 由 (field_number << 3) | wire_type 计算得出，支持向前兼容（新加字段不影响老解析）和向后兼容（忽略未知字段）。
   - **场景**：对性能要求极高的内部微服务通信。

2. **Thrift**
   - **特点**：Facebook 开源，既包含序列化框架也包含 RPC 框架，支持二进制压缩编码。支持多种数据类型（容器、Map 等）。
   - **场景**：需要全栈 RPC 解决方案的场景。

3. **Kryo**
   - **原理**：基于字节码生成或反射，使用变长 int/long 处理整型，减少 0-255 字节占用。针对 Java 优化，自动注册类以提升序列化速度。
   - **注意**：非线程安全，需要配合 KryoPool 使用。
   - **场景**：Java 生态内的高性能通信（如 Spark）。

**对比 Java 原生序列化：**
Java 原生的序列化效率低（仅支持 Java 语言、流式传输效率低、安全性差，包含类元信息），高性能框架通常采用二进制非文本格式，并优化了字段存储策略（如 Tag-Length-Value 结构）。

### 实战案例
在千万级消息量的 Kafka 集群中，曾遇到 JSON 序列化导致网卡带宽被打满的瓶颈，切换到 Protobuf 后消息体积减少约 60%，吞吐量翻倍。但要注意 Protobuf 不支持直接修改已有字段的 tag 号，否则会导致旧数据解析失败或错位。

### 代码示例 (Protobuf Java)
```java
// 编码：对象转字节数组
MyMessage.Builder builder = MyMessage.newBuilder();
builder.setId(101).setContent("Hello High Perf");
byte[] data = builder.build().toByteArray(); 

// 解码：字节数组转对象
MyMessage msg = MyMessage.parseFrom(data);
System.out.println(msg.getContent());
```

### 框架对比表
| 特性 | Protobuf | Thrift | Kryo | Hessian | JSON (Jackson) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **序列化速度** | 极快 | 快 | **极快 (Java)** | 较快 | 慢
| **体积大小** | 极小 | 小 | 小 | 较小 | 大
| **跨语言支持** | 优秀 | **优秀** | 弱 (主要Java) | 良好 | 优秀
| **兼容性** | 强 (向前/向后) | 一般 | 弱 (需注册) | 一般 | 弱
| **是否需要Schema** | 必须 (.proto) | 必须 (.idl) | 否 (推荐注册) | 否 | 否
| **适用场景** | 存储/RPC | 通用RPC | Java内部缓存 | RPC传输 | API/浏览器

## 常见考点
1. **Schema 演进**：Protobuf 如何保证新增字段后旧版服务仍能正常解析？（利用 Tag 忽略未知字段，但不可删除已有字段）。
2. **为什么选 Protobuf 而不是 JSON？** JSON 是文本格式，字段名重复占用带宽，解析需正则或 split，速度比二进制慢 5-10 倍。
3. **粘包/拆包问题**：二进制序列化通常需要在传输层（如 Netty）配合 LengthFieldBasedFrameDecoder 处理粘包。

## 记忆要点

- 性能对比：因为二进制省去字段名且变长编码，所以比JSON快且小
- 选型对比：Protobuf跨语言强且Schema强约束，Kryo极快但限Java
- 演进机制：Protobuf靠Tag匹配，所以新增字段能兼容但不可改旧Tag
- 实战替换：RPC或MQ场景中，将JSON换成Protobuf可大幅降带宽提吞吐

## 结构化回答




**30 秒电梯演讲：** 把行李（对象）压缩成真空袋（二进制流），省空间好搬运。

**展开框架：**
1. **Java** — 相比 Java 原生序列化，体积更小，速度更快。
2. **常见框架** — Protobuf, Thrift, Kryo。
3. **RPC** — 多用于 RPC 调用和数据持久化。

**收尾：** 这是我实战中的理解，您想深入哪一段？




## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：什么是高性能的序列化框架 | 今天这道题：什么是高性能的序列化框架。30 秒先给你讲清楚。 | 开场钩子 |
| 0:20 | 核心概念动画/示意图 | 把行李（对象）压缩成真空袋（二进制流），省空间好搬运。 | 核心概念 |
| 0:40 | 相比 Java 原生序列化示意图 | 相比 Java 原生序列化，体积更小，速度更快。 | 相比 Java 原生序列化 |
| 1:10 | 总结卡 + 下期预告 | 记住今天这几个关键词，面试一定用得上。下期见。 | 收尾 |
