---
id: core-066
difficulty: L2
category: java-core
feynman:
  essence: 客户端发送给服务器的标准数据格式。
  analogy: 填单子：写明要什么（方法）、去哪（URL）、怎么做（头部），最后附上材料（体）。
  first_principle: 客户端如何标准化地向服务器发起操作请求和数据？
  key_points:
  - 请求行：包含方法、URL、协议版本
  - 请求头：包含Host、User-Agent等附加信息
  - 请求体：POST等方法携带的数据，GET方法通常为空
  - 状态行：包含协议版本、状态码和描述
  - 响应头：包含Content-Type、Server等元信息
  - 响应体：实际返回的HTML、图片等数据
memory_points:
- 报文三段：请求行(方法+URI+版本)、请求头(Key-Value)、请求体(数据)
- 请求行方法：GET获取资源、POST提交数据、PUT更新、DELETE删除
- 头体分割：请求头与请求体之间用CRLF空行严格隔开
- 数据格式：POST提交数据时，请求体类型由Content-Type字段(如JSON/表单)决定
- 四大结构：状态行、响应头部、空行、响应体
- 状态行三要素：协议版本、状态码(如200/304)、原因短语(如OK)
- 头体分割：因为用CRLF空行严格分割头部和主体，所以解析时以此为准
- 特殊响应：1xx、204、304状态码均无响应体
follow_up: []
tags: []
---

# 什么是HTTP请求报文？

### 背景知识：网络模型与页面加载过程

**五层网络体系结构**
五层网络体系结构是综合了 OSI 模型和 TCP/IP 模型所得来的。各层功能如下：
1. **应用层**：直接为用户的应用进程提供服务。常见协议有 HTTP、SMTP、FTP、DNS。
2. **传输层**：负责向两个主机中进程之间的通信提供服务（端到端）。主要协议：TCP（可靠）、UDP（不可靠）。
3. **网络层**：负责数据的路由和转发（主机到主机），使用 IP 地址。
4. **数据链路层**：在直连网络中传输数据帧，使用 MAC 地址。
5. **物理层**：负责物理传输媒介的传输（光纤、电波等）。

**从输入 URL 到页面展示发生了什么？**
1. **URL 输入**：用户输入地址。
2. **域名解析 (DNS)**：浏览器解析域名获取 IP 地址（过程：浏览器缓存 -> 系统缓存 -> Hosts 文件 -> DNS 服务器）。
3. **建立连接**：浏览器通过 TCP 三次握手与服务器建立连接（若是 HTTPS，还需 TLS/SSL 握手）。
4. **发送请求**：浏览器发送 HTTP 请求报文。
5. **服务器处理**：服务器接收请求，处理逻辑（可能查询数据库），生成响应。
6. **接收响应**：浏览器接收 HTTP 响应报文。
7. **解析和渲染**：浏览器解析 HTML（构建 DOM 树）、解析 CSS（构建 CSSOM 树）、执行 JS，合并生成渲染树。
8. **页面绘制**：布局与绘制，将像素渲染到屏幕上。
9. **连接结束**：TCP 四次挥手断开连接（若 HTTP/1.1 Keep-Alive 则保持）。

---

### HTTP 请求报文详解

HTTP 请求报文主要由**请求行**、**请求头**、**请求体**构成。

```
┌───────────────────────────────────────────────────────┐
│                     HTTP 请求报文                       │
├───────────────────────────────────────────────────────┤
│  1. 请求行
│     ┌──────────┬─────────────────────┬───────────────┐
│     │ Method   │       URI           │   HTTP/1.1   │
│     │ (GET)    │ (/index.html?...)  │              │
│     └──────────┴─────────────────────┴───────────────┘
├───────────────────────────────────────────────────────┤
│  2. 请求头
│     Host: www.example.com
│     User-Agent: Mozilla/5.0...
│     Accept: text/html
│     Content-Type: application/json
│     Cookie: sessionid=123456
│     └ ... (更多 Key-Value 对)
├───────────────────────────────────────────────────────┤
│  3. 空行 (CRLF)                                        │
├───────────────────────────────────────────────────────┤
│  4. 请求体 (Body, 仅部分请求方法有)                     │
│     { "username": "admin", "password": "123456" }     │
└───────────────────────────────────────────────────────┘
```

#### 1. 请求行
由三部分组成：`请求方法 URI 协议版本号`

- **请求方法**：
  - **GET**：请求获取 Request-URI 所标识的资源。
  - **POST**：在 Request-URI 所标识的资源后附加新的数据（提交表单、上传文件）。
  - **PUT**：向服务器上传资源，更新指定资源。
  - **DELETE**：请求服务器删除 Request-URI 所标识的资源。

#### 2. 请求头
包含客户端环境信息、请求体信息等。关键字段：
- **Host**：指定请求的服务器域名和端口（必需，用于虚拟主机路由）。
- **Content-Type**：请求体的数据格式（如 `application/json`, `multipart/form-data`）。
- **Content-Length**：请求体的字节长度（POST 请求时重要）。
- **Authorization**：用于身份验证，如 `Bearer <token>`。
- **Accept-Encoding**：告诉服务器客户端支持的内容编码（如 gzip, br），用于内容压缩。

#### 3. 请求体
仅在 POST、PUT 等方法中使用，携带具体数据（如表单数据、JSON 字符串）。

**实战案例**：
在处理文件上传时，若未正确设置 `Content-Type: multipart/form-data`，后端可能无法解析文件流。此外，在发送 JSON 数据时，忘记设置 `Content-Type: application/json` 常导致后端（如 Spring MVC）无法将请求体反序列化为对象，报错 415 Unsupported Media Type。

**代码示例 (Fetch API 发送 POST 请求)**：
```javascript
// 发送 JSON 数据
fetch('/api/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json', // 必须指定，否则后端可能解析失败
    'Authorization': 'Bearer token123'
  },
  body: JSON.stringify({ username: 'user', password: 'pwd' })
});
```

**常见请求方法对比**：

| 方法 | 数据位置 | 幂等性 | 安全性 | 典型应用场景 |
| :--- | :--- | :--- | :--- | :--- |
| **GET** | URL 参数 | 幂等 | 安全 | 查询、页面跳转 |
| **POST** | Request Body | 非幂等 | 不安全 | 表单提交、新增数据 |
| **PUT** | Request Body | 幂等 | 不安全 | 更新资源（整体替换） |
| **DELETE** | URL 参数 | 幂等 | 不安全 | 删除资源 |

## 记忆要点

- 报文三段：请求行(方法+URI+版本)、请求头(Key-Value)、请求体(数据)
- 请求行方法：GET获取资源、POST提交数据、PUT更新、DELETE删除
- 头体分割：请求头与请求体之间用CRLF空行严格隔开
- 数据格式：POST提交数据时，请求体类型由Content-Type字段(如JSON/表单)决定

## 结构化回答

**30 秒电梯演讲：** 客户端发送给服务器的标准数据格式。打个比方，填单子：写明要什么（方法）、去哪（URL）、怎么做（头部），最后附上材料（体）。

**展开框架：**
1. **报文三段** — 请求行(方法+URI+版本)、请求头(Key-Value)、请求体(数据)
2. **请求行方法** — GET获取资源、POST提交数据、PUT更新、DELETE删除
3. **头体分割** — 请求头与请求体之间用CRLF空行严格隔开

**收尾：** 我在项目里踩过坑——在处理文件上传时，若未正确设置 `Content-Type: multipart/form-data`，后端可能无法解析文件流。您想深入聊哪一段：原理、避坑还是对比选型？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：什么是HTTP请求报文 | "什么是HTTP请求报文？一句话——填单子：写明要什么（方法）、去哪（URL）、怎么做（头部），最后附上材料（体）。" | 开场钩子 |
| 0:40 | 概念动画/示意图 | "客户端发送给服务器的标准数据格式——填单子：写明要什么（方法）、去哪（URL）、怎么做（头部），最后附上材料（体）" | 核心定义 |
| 1:20 | 报文三段示意 | "请求行(方法+URI+版本)、请求头(Key-Value)、请求体(数据)" | 要点1 |
| 2:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |

---

## 延伸：什么是HTTP响应报文？

> 合并自 `core-061`（相似度 76%）

HTTP 响应报文是服务器接收并处理客户端请求后，返回给客户端的数据包。它由状态行、响应头部、空行和响应体四个部分组成。以下是详细的解析：

**1. 状态行**
状态行位于响应报文的第一行，包含三个字段，格式为：`HTTP-Version Status-Code Reason-Phrase`。
- **HTTP-Version**：服务器使用的 HTTP 协议版本（如 HTTP/1.1）。
- **Status-Code**：3位数字的状态码，告诉客户端请求的结果。
  - `1xx`：指示信息（表示请求已接收，继续处理）。
  - `2xx`：成功（如 200 OK, 206 Partial Content）。
  - `3xx`：重定向（如 301 Moved Permanently, 302 Found）。
  - `4xx`：客户端错误（如 400 Bad Request, 404 Not Found）。
  - `5xx`：服务器错误（如 500 Internal Server Error, 502 Bad Gateway）。
- **Reason-Phrase**：状态码的简短文本描述（如 OK, Not Found）。

**2. 响应头部**
响应头部由一系列键值对组成，用于传递服务器信息、缓存策略、内容类型等元数据。常见字段如下：
- **Content-Type**：告诉客户端响应体的 MIME 类型及编码（如 `text/html; charset=utf-8`），决定浏览器如何渲染内容。
- **Content-Length**：响应体的字节长度（用于非 chunked 传输）。
- **Content-Encoding**：数据的压缩编码格式（如 gzip）。
- **Transfer-Encoding**：指定传输编码方式，常用 `chunked` 分块传输，用于动态生成的大文件。
- **Server**：服务器软件信息（如 nginx/1.18.0）。
- **Set-Cookie**：向客户端发送 Cookie，用于会话管理。
- **Location**：配合 3xx 状态码，指定重定向的目标 URL。
- **Cache-Control**：告诉浏览器如何缓存响应（如 `max-age=3600`）。
- **ETag**：资源的特定版本标识符，用于缓存验证（比 Last-Modified 更精确）。

**3. 空行**
一个 CRLF（\r\n），用于分隔响应头和响应体。

**4. 响应体**
服务器返回的实际资源数据。可以是 HTML 文档、JSON 数据、图片二进制流等。如果状态码是 1xx、204（No Content）或 304（Not Modified），则没有响应体。

**HTTP 响应报文结构图**：
```
┌─────────────────────────────────────────────┐
│ HTTP/1.1 200 OK           (状态行)           │
├─────────────────────────────────────────────┤
│ Content-Type: text/html      (响应头)        │
│ Content-Length: 138                          │
│ Date: Mon, 23 Oct 2023 12:00:00 GMT          │
│ Server: Apache/2.4.41                        │
│                                             │
├─────────────────────────────────────────────┤ (空行)
│ <!DOCTYPE html>             (响应体)         │
│ <html>                                      │
│   <body>Hello World</body>                  │
│ </html>                                     │
└─────────────────────────────────────────────┘
```

**实战案例**：在进行 Excel 文件下载接口开发时，若未设置 `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`，浏览器会将文件识别为文本流并在页面直接显示乱码，而非弹出下载框。

**代码示例**：
```java
// Java (Spring Boot): 构建文件下载响应
@GetMapping("/download")
public ResponseEntity<Resource> downloadFile() throws IOException {
    File file = new File("data.xlsx");
    InputStreamResource resource = new InputStreamResource(new FileInputStream(file));
    
    return ResponseEntity.ok()
            .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=data.xlsx")
            .contentType(MediaType.parseMediaType("application/vnd.ms-excel"))
            .contentLength(file.length())
            .body(resource);
}
```

## 常见考点
1. **常见的状态码及其含义**：特别是 301 vs 302，401 vs 403，500 vs 502 vs 503。
2. **Content-Type 的作用**：如果不正确设置会发生什么？（如下载文件变乱码或直接显示）。

## 记忆要点

- 四大结构：状态行、响应头部、空行、响应体
- 状态行三要素：协议版本、状态码(如200/304)、原因短语(如OK)
- 头体分割：因为用CRLF空行严格分割头部和主体，所以解析时以此为准
- 特殊响应：1xx、204、304状态码均无响应体

## 结构化回答

**30 秒电梯演讲：** 服务器返回给客户端的标准数据格式。打个比方，回信：先写结论（状态码），再写细节（头部），最后是正文（内容）。

**展开框架：**
1. **四大结构** — 状态行、响应头部、空行、响应体
2. **状态行三要素** — 协议版本、状态码(如200/304)、原因短语(如OK)
3. **头体分割** — 因为用CRLF空行严格分割头部和主体，所以解析时以此为准

**收尾：** 我在项目里踩过坑——在进行 Excel 文件下载接口开发时，若未设置 `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`，浏览器会将文件识别为文本流并在页面直接显示乱码，而非弹出下载框。您想深入聊哪一段：原理、避坑还是对比选型？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：什么是HTTP响应报文 | "什么是HTTP响应报文？一句话——回信：先写结论（状态码），再写细节（头部），最后是正文（内容）。" | 开场钩子 |
| 0:40 | 概念动画/示意图 | "服务器返回给客户端的标准数据格式——回信：先写结论（状态码），再写细节（头部），最后是正文（内容）" | 核心定义 |
| 1:20 | 四大结构示意 | "状态行、响应头部、空行、响应体" | 要点1 |
| 2:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |
