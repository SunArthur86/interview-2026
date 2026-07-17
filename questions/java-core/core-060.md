---
id: core-060
difficulty: L2
category: java-core
feynman:
  essence: 优化传输效率，支持长连接、缓存、断点续传。
  analogy: 送货服务升级，不用每次重新下单，支持送半截货。
  first_principle: 如何提升网络传输效率并支持更复杂的Web应用？
  key_points:
  - 长连接减少握手开销，断点续传节省带宽
  - 引入ETag、Cache-Control等更精细的缓存控制
  - Host头实现虚拟主机，单IP多站点
memory_points:
- 核心区别记“长管缓带”：1.1支持长连接、管道化、强缓存(ETag)、断点续传
- 虚拟主机靠Host：因为1.1新增Host字段，所以一个IP能托管多个Web站点
- 缓存与断点：引入ETag解决精度问题；支持Range请求且返回206实现断点续传
- 连接特性：1.0默认短连接，1.1默认Keep-Alive长连接
---

# 什么是HTTP1.1有什么特性？

客户端在请求头部的 If-Modified-Since  字段中携带上次响应的 Last-Modified  时间。
服务器比较请求中的 If-Modified-Since  值与当前资源的 Last-Modified  值，如果请求时间早于资源的
最后修改时间，表示资源未发生变化，返回状态码 304 Not Modified 。
HTTP1.0和HTTP1.1的区别？
 
1. 长连接 
HTTP1.1 支持长连接，每一个TCP连接上可以传送多个HTTP请求和响应，默认开启Connection:Keep-
Alive
HTTP1.0 默认为短连接，每次请求都需要建立一个TCP连接。 
2. 缓存 
HTTP1.0 主要使用If-Modified-Since/Expires 来做为缓存判断的标准
HTTP1.1 则引⼊了更多的缓存控制策略例如Entity tag / If-None-Match 等更多可供选择的缓存头来控
制缓存策略。 
3. 管道化
基于HTTP1.1 的长连接，使得请求管线化成为可能。管线化使得请求能够“并行”传输，但是响应必须按照请
求发出的顺序依次返回，性能在一定程度上得到了改善。 
4. 增加Host字段
使得一个服务器能够用来创建多个 Web 站点。
5. 状态码 
新增了24个错误状态响应码 
6. 带宽优化 
HTTP1.0 中，存在一些浪费带宽的现象，例如客户端只是需要某个对象的一部分，而服务器却将整个对象送
过来了，并且不支持断点续传功能
HTTP1.1 则在请求头引⼊了range 头域，它允许只请求资源的某个部分，即返回码是206（Partial 
Content）
HTTP1.1有什么特性
 
1、持久连接：只要客户端任意一端没有明确提出断开TCP连接，就一直保持连接，也称为“Keep-Alive”。
2、管线化：允许客户端在不等待前一个响应返回的情况下发送多个请求
3、增加了 PUT、DELETE、OPTIONS、PATCH 等新的方法
4、新增了24个错误状态响应码 
5、新增了一些缓存的字段（If-Modified-Since, If-None-Match ）
6、HTTP1.1 在请求头引⼊了range 头域，它允许只请求资源的某个部分，即返回码是206（Partial Content）
7、允许响应数据分块，利于传输大文件
8、增加Host 字段：使得一个服务器能够用来创建多个 Web 站点。

**实战案例**：在电商商品详情页优化中，曾出现因浏览器缓存了 CSS 文件但未获更新导致页面错乱。使用 `ETag` (指纹哈希) 替代 `Last-Modified` 后，解决了秒级更新导致缓存失效的“时间精度”问题。

**代码示例**：
```javascript
// Node.js (Express): 设置强缓存与协商缓存
app.get('/app.js', (req, res) => {
  const file = fs.readFileSync('./app.js');
  // 生成 ETag 哈希值
  const etag = crypto.createHash('md5').update(file).digest('hex');
  
  // 检查 If-None-Match
  if (req.headers['if-none-match'] === etag) {
    return res.status(304).end(); // 协商缓存命中
  }
  
  res.set('Cache-Control', 'public, max-age=3600'); // 强缓存1小时
  res.set('ETag', etag);
  res.send(file);
});
```

**版本对比**：

| 特性 | HTTP/1.0 | HTTP/1.1 |
| :--- | :--- | :--- |
| **连接方式** | 短连接（默认） | 长连接（默认 Keep-Alive） |
| **Host 头** | 不支持 | 必须支持（虚拟主机基础） |
| **缓存策略** | Expires (时间), If-Modified-Since | Cache-Control (精细指令), ETag (指纹) |
| **断点续传** | 不支持 | 支持 (Range: bytes, 206 状态码) |
| **传输编码** | 仅 Content-Length | 支持 Transfer-Encoding: chunked (流式) |

## 记忆要点

- 核心区别记“长管缓带”：1.1支持长连接、管道化、强缓存(ETag)、断点续传
- 虚拟主机靠Host：因为1.1新增Host字段，所以一个IP能托管多个Web站点
- 缓存与断点：引入ETag解决精度问题；支持Range请求且返回206实现断点续传
- 连接特性：1.0默认短连接，1.1默认Keep-Alive长连接

## 结构化回答

**30 秒电梯演讲：** 优化传输效率，支持长连接、缓存、断点续传。打个比方，送货服务升级，不用每次重新下单，支持送半截货。

**展开框架：**
1. **核心区别记“长管缓带”** — 1.1支持长连接、管道化、强缓存(ETag)、断点续传
2. **虚拟主机靠Host** — 因为1.1新增Host字段，所以一个IP能托管多个Web站点
3. **缓存与断点** — 引入ETag解决精度问题；支持Range请求且返回206实现断点续传

**收尾：** 我在项目里踩过坑——在电商商品详情页优化中，曾出现因浏览器缓存了 CSS 文件但未获更新导致页面错乱。您想深入聊哪一段：原理、避坑还是对比选型？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：什么是HTTP1.1有什么特性 | "什么是HTTP1.1有什么特性？一句话——送货服务升级，不用每次重新下单，支持送半截货。" | 开场钩子 |
| 0:40 | 概念动画/示意图 | "优化传输效率，支持长连接、缓存、断点续传——送货服务升级，不用每次重新下单，支持送半截货" | 核心定义 |
| 1:20 | 核心区别记“长管缓带”示意 | "1.1支持长连接、管道化、强缓存(ETag)、断点续传" | 要点1 |
| 2:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |
