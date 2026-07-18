---
id: core-030
difficulty: L1
category: java-core
feynman:
  essence: 利用 GET 请求的幂等性存储响应副本，加速数据加载并减轻服务器压力。
  analogy: GET 像看报纸（可存档反复看），POST 像填表单（每次都要交新的，不能存档复用）。
  first_principle: 如何减少重复网络请求以提升页面加载性能和用户体验？
  key_points:
  - GET 请求默认支持浏览器缓存
  - POST 请求默认不缓存
  - GET 安全且幂等，POST 可能修改资源
  - 缓存由服务器通过响应头（如 Cache-Control）控制
memory_points:
- HTTP缓存分强缓存与协商缓存，强缓存命中不发请求，协商缓存命中返回304
- 强缓存核心看 Cache-Control（max-age/no-store/no-cache），优先级高于Expires
- 协商缓存核心看 ETag（内容哈希，精确度高）与 Last-Modified（秒级时间），ETag 优先级更高
---

# 缓存机制是什么？

HTTP 缓存机制是指浏览器或代理服务器存储 HTTP 响应副本的技术，用于减少网络延迟和服务器负载。

### 缓存策略主要依据请求方法和响应头
1. **GET 请求**：默认是可缓存的、幂等的和安全的。浏览器通常会主动缓存 GET 请求的响应，相同 URL 的后续请求可能直接从缓存读取。
2. **POST 请求**：通常用于修改服务器资源，默认是不可缓存的、非幂等的。除非服务器明确在响应头中设置缓存策略（如 Cache-Control），否则浏览器不会缓存 POST 响应。

### 关键区别
- **幂等性**：GET 是幂等的，多次请求结果一致；POST 通常是非幂等的，多次提交会产生多个资源。
- **安全性**：GET 是安全的，不修改服务器资源；POST 可能会修改资源。
- **缓存行为**：GET 易于缓存，POST 一般不缓存。

### 强缓存与协商缓存流程

```text
                     浏览器请求
                        |
            ┌───────────┴───────────┐
            v                       v
      [ 检查本地缓存 ]         [ 发送网络请求 ]
            |
    ┌───────┴────────┐
    | 强缓存是否命中? |
    └───────┬────────┘
       Yes/ | \No
            |  \-----------------------------------┐
            v                                      v
      [ 直接使用缓存 ]                     [ 检查协商缓存 (ETag/Last-Modified) ]
            |                                      |
            |                               200 (资源变更) / 304 (未变更)
            |                                      |
            |                                      v
            |-------------------------------> [ 更新缓存并渲染 ]
```

### 关键头部详解
- **Cache-Control**：
  - `max-age=<seconds>`：缓存有效时间。
  - `no-store`：禁止任何缓存（内存和磁盘）。
  - `no-cache`：可以缓存，但在使用前必须向服务器验证新鲜度（实际上是走协商缓存）。
  - `private` / `public`：仅限浏览器缓存 / 允许中间代理（如 CDN）缓存。
- **Expires**：HTTP 1.0 字段，值为绝对时间（GMT 格式），受客户端时间影响，已逐渐被 `Cache-Control: max-age` 取代。
- **ETag**：资源的唯一标识符（哈希值），优先级高于 Last-Modified。
- **Last-Modified**：资源最后修改时间，精确到秒。

## 常见考点
1. **ETag vs Last-Modified**：为什么 ETag 优先级更高？如果资源在一秒内被多次修改，Last-Modified 能察觉吗？
2. **Cache-Control: no-cache vs no-store**：两者有什么本质区别？
3. **POST 缓存**：在什么场景下需要缓存 POST 请求？如何实现？

---

### 实战深化

#### 1. 实战案例
*   **Hash命名与强缓存**：在前端工程化中，常使用 `[contenthash].js` 进行文件命名。配合 `Cache-Control: max-age=31536000`（一年），可以永久缓存静态资源。当文件内容变更时，文件名 hash 变化，URL 变化从而自动绕过强缓存，完美解决更新问题。
*   **协商缓存陷阱**：曾遇到过服务器集群中不同机器的时间未同步，导致 `Last-Modified` 时间不一致，结果是用户在负载均衡下访问同一资源时不断往返 304/200，不仅没降低负载，反而增加了协商流量的开销，改用 ETag（基于内容哈希）后解决。

#### 2. 代码示例
以下为 Node.js (Express) 中设置强缓存与协商缓存的代码片段：

```javascript
const express = require('express');
const fs = require('fs');
const app = express();

app.get('/api/data', (req, res) => {
  const data = fs.readFileSync('./data.json');
  // 生成 ETag (通常使用内容的哈希值)
  const etag = require('crypto').createHash('md5').update(data).digest('hex');
  
  // 检查请求头 if-none-match 是否与当前 ETag 一致
  if (req.headers['if-none-match'] === etag) {
    return res.status(304).end(); // 协商缓存命中，不返回 body
  }

  // 设置强缓存策略和 ETag
  res.set({
    'Cache-Control': 'public, max-age=10', // 强缓存 10 秒
    'ETag': etag
  });
  res.send(data);
});
```

#### 3. 对比表格

| 特性 | 强缓存 | 协商缓存 |
| :--- | :--- | :--- |
| **状态码** | 200 (from disk/memory / from ServiceWorker) | 304 (Not Modified) |
| **发送网络请求** | 否 (直接读取本地) | 是 (需携带头部向服务器验证) |
| **核心 Header** | Cache-Control (max-age), Expires | ETag / If-None-Match, Last-Modified / If-Modified-Since |
| **优先级** | 高 (先检查强缓存) | 低 (强缓存失效后才检查) |
| **适用场景** | 静态资源 (JS/CSS/图片) | HTML 文档或频繁变化的动态数据 |


## 记忆要点

- HTTP缓存分强缓存与协商缓存，强缓存命中不发请求，协商缓存命中返回304
- 强缓存核心看 Cache-Control（max-age/no-store/no-cache），优先级高于Expires
- 协商缓存核心看 ETag（内容哈希，精确度高）与 Last-Modified（秒级时间），ETag 优先级更高

## 结构化回答

**30 秒电梯演讲：** 利用 GET 请求的幂等性存储响应副本，加速数据加载并减轻服务器压力。打个比方，GET 像看报纸（可存档反复看），POST 像填表单（每次都要交新的，不能存档复用）。

**展开框架：**
1. **HTTP缓存分强缓存与协商缓存** — 强缓存命中不发请求，协商缓存命中返回304
2. **强缓存核心看 Cache-Control** — max-age/no-store/no-cache
3. **协商缓存核心看 ETag** — 精确度高）与 Last-Modified（秒级时间），ETag 优先级更高

**收尾：** 我在项目里踩过坑——Hash命名与强缓存：在前端工程化中，常使用 `[contenthash].js` 进行文件命名。您想深入聊哪一段：原理、避坑还是对比选型？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：缓存机制是什么 | "缓存机制是什么？一句话——GET 像看报纸（可存档反复看），POST 像填表单（每次都要交新的，不能存档复用）。" | 开场钩子 |
| 0:40 | 概念动画/示意图 | "利用 GET 请求的幂等性存储响应副本，加速数据加载并减轻服务器压力——GET 像看报纸（可存档反复看），POST 像填表单（每次都要交新的，不能存档复用）" | 核心定义 |
| 1:20 | 要点1图解示意 | "强缓存命中不发请求，协商缓存命中返回304" | 要点1 |
| 2:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |
