---
id: core-006
difficulty: L2
category: java-core
subcategory: 计算机网络
tags:
- HTTP
- 性能优化
- 缓存
- HTTP/2
feynman:
  essence: 通过复用连接、压缩数据、缓存资源减少传输开销。
  analogy: 像送快递，把零散包裹打包（压缩）、用专车直送（复用连接）、在楼下设自提柜（缓存）。
  first_principle: 如何减少网络延迟并提升数据传输效率？
  key_points:
  - 启用Keep-Alive和连接池复用TCP连接
  - 利用强缓存和协商缓存减少请求
  - 使用Gzip或Brotli压缩传输内容
  - 升级HTTP/2实现多路复用
memory_points:
- 传输层优化：HTTP/2解决HTTP队头阻塞，而HTTP/3基于UDP解决TCP队头阻塞。
- 缓存策略：强缓存直接读本地，协商缓存(304)询问服务器是否更新。
- 对比压缩算法：Gzip通用性最好，而Brotli压缩率更高(适合文本)。
- 优化口诀：减请求(合并/懒加载)、减体积(压缩/TreeShaking)、复用连接。
---

# 什么是HTTP优化方案？

HTTP 性能优化从协议栈、网络传输、缓存策略等多个层面提升 Web 请求效率：

## 一、传输层与协议优化

### 1. TCP 连接复用与优化
- **Keep-Alive**：复用 TCP 连接，避免频繁三次握手/四次挥手的开销（RTT）。
- **连接池**：客户端（如 HttpClient, OkHttp）维护连接池，减少建立连接的耗时和系统资源消耗。

### 2. HTTP/2 核心优势
| 特性 | HTTP/1.1 | HTTP/2 |
|------|----------|--------|
| **多路复用** | ❌ 串行请求，需多个连接或队头阻塞 | ✅ 单连接并发，消除 HTTP 层队头阻塞 |
| **头部压缩** | ❌ 纯文本，大量重复头字段 | ✅ HPACK 算法（静态字典+动态字典+霍夫曼编码） |
| **服务端推送** | ❌ | ✅ Server Push，主动推送资源 |
| **二进制分帧** | ❌ 文本协议解析慢 | ✅ 二进制帧，解析效率高 |

### 3. HTTP/3 (QUIC)
- **解决 TCP 队头阻塞**：基于 UDP，丢包只影响对应流，不阻塞其他流。
- **连接迁移**：基于 IP 无关的 Connection ID，支持 4G/Wifi 切换不断连。
- **0-RTT 握手**：首次连接后，后续连接可实现 0 RTT 发送数据。

## 二、缓存策略优化

1. **强缓存**：浏览器无需与服务器确认，直接使用本地缓存。
   - `Cache-Control: max-age=31536000`（优先级高）
   - `Expires`（HTTP/1.0，依赖客户端时间，已少用）
2. **协商缓存**：浏览器询问服务器资源是否变更。
   - `ETag` / `If-None-Match`（指纹比对，精准）
   - `Last-Modified` / `If-Modified-Since`（时间比对，秒级精度不足）
   - 状态码 `304 Not Modified`，只传输 Header，不传输 Body。
3. **CDN 缓存**：静态资源部署到边缘节点，用户就近访问，回源策略需合理配置。

## 三、内容压缩优化

```http
请求头: Accept-Encoding: gzip, deflate, br
响应头: Content-Encoding: gzip, Content-Length: 1024
```

| 算法 | 压缩率 | CPU消耗 | 适用场景 |
|------|--------|---------|----------|
| **Gzip** | ~70% | 中 | 通用，兼容性好 |
| **Deflate** | ~60% | 中 | 较少使用 |
| **Brotli** | ~85-90% | 高 | 现代 Web，文本压缩极佳 |

> **注意**：图片/视频等二进制文件通常已压缩，再次开启 Gzip 可能适得其反（增加 CPU 负担且体积变大）。

## 四、资源加载与网络优化

1. **减少 HTTP 请求数量**：
   - 雪碧图、内联小资源（CSS/JS/Base64 图片）。
   - 按需加载/懒加载。
2. **减小传输体积**：
   - 代码混淆、Tree Shaking、移除 Dead Code。
   - HTTP/2 的 HPACK 头部压缩。
3. **域名分片 vs HTTP/2**：
   - HTTP/1.1 时代利用多域名突破浏览器 6 个 TCP 连接限制。
   - HTTP/2 时代建议合并域名，利用单连接多路复用优势。

### 实战案例
在管理后台项目中，首屏加载慢导致跳出率高。我们通过 Chrome DevTools 分析，发现一个 `vendor.js` 体积高达 2MB，且开启了 Gzip 压缩但未启用 Brotli。**优化方案**：1. Nginx 启用 Brotli 压缩，体积减少 30%；2. 开启 `splitChunks` 进行代码分割；3. 配置 `preload` 预加载关键 JS。最终 TTI (Time to Interactive) 从 3.5s 降至 1.2s。

### 代码示例 (Nginx 配置)
```nginx
# 开启 Gzip 和 Brotli 压缩实战
gx_http_gzip_static_module on;  # 优先预压缩 .gz 文件

http {
    # Gzip 配置
    gzip on;
    gzip_min_length 1k;
    gzip_types text/plain application/json application/javascript text/css application/xml;
    
    # Brotli 配置 (需安装模块)
    brotli on;
    brotli_comp_level 6;
    brotli_types text/plain application/json application/javascript text/css;
}
```

## 常见考点
1. **HTTP/2 多路复用解决了什么层面的队头阻塞？**
   - 解决了 HTTP 层的队头阻塞，但 TCP 层的队头阻塞依然存在（丢包会导致整个 TCP 连接暂停等待重传），这也是 HTTP/3 引入 QUIC 的原因。
2. **ETag 是如何生成的？**
   - 通常有三种：文件哈希（md5/sha1，精准但耗 CPU）、文件修改时间+大小（Inode，快但不够精准）、版本号。
3. **既然有了 HTTP/2，为什么还要保持 Keep-Alive？**
   - HTTP/2 也是基于 TCP 的，建立连接（TCP + TLS）依然昂贵（2-3 RTT），多路复用是建立在同一个 TCP 连接之上的。

## 记忆要点

- 传输层优化：HTTP/2解决HTTP队头阻塞，而HTTP/3基于UDP解决TCP队头阻塞。
- 缓存策略：强缓存直接读本地，协商缓存(304)询问服务器是否更新。
- 对比压缩算法：Gzip通用性最好，而Brotli压缩率更高(适合文本)。
- 优化口诀：减请求(合并/懒加载)、减体积(压缩/TreeShaking)、复用连接。

## 结构化回答

**30 秒电梯演讲：** 通过复用连接、压缩数据、缓存资源减少传输开销。打个比方，像送快递，把零散包裹打包（压缩）、用专车直送（复用连接）、在楼下设自提柜（缓存）。

**展开框架：**
1. **传输层优化** — HTTP/2解决HTTP队头阻塞，而HTTP/3基于UDP解决TCP队头阻塞。
2. **缓存策略** — 强缓存直接读本地，协商缓存(304)询问服务器是否更新。
3. **对比压缩算法** — Gzip通用性最好，而Brotli压缩率更高(适合文本)。

**收尾：** 我在项目里踩过坑——gx_http_gzip_static_module on;  # 优先预压缩 .gz 文件。您想深入聊哪一段：原理、避坑还是对比选型？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：什么是HTTP优化方案 | "什么是HTTP优化方案？一句话——像送快递，把零散包裹打包（压缩）、用专车直送（复用连接）、在楼下设自提柜（缓存）。" | 开场钩子 |
| 0:40 | 概念动画/示意图 | "通过复用连接、压缩数据、缓存资源减少传输开销——像送快递，把零散包裹打包（压缩）、用专车直送（复用连接）、在楼下设自提柜（缓存）" | 核心定义 |
| 1:20 | 传输层优化示意 | "HTTP/2解决HTTP队头阻塞，而HTTP/3基于UDP解决TCP队头阻塞。" | 要点1 |
| 2:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |
