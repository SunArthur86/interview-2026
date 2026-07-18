---
id: core-081
difficulty: L2
category: java-core
feynman:
  essence: URI是资源ID，URL是资源的具体地址
  analogy: URI是身份证号（标识人），URL是家庭住址（定位并找到人）
  first_principle: 如何在网络上唯一标识并定位一个资源？
  key_points:
  - URL是URI的子集
  - URI侧重标识，URL侧重定位
  - URL包含协议、域名、端口等具体信息
memory_points:
- 概念对比：URI强调资源标识，而URL不仅标识还侧重提供具体的网络定位路径
- 包含关系：URI是顶级统称概念，URL和URN都是其子集
- URN特性：URN与物理位置无关，通过特定名称定位资源(如磁力链接或ISBN号)
- 结构拆解：协议+主机名+端口+路径+查询参数+片段标识符共同组成完整URL
- 编码避坑：URL拼接时必须用URLEncoder处理特殊字符，且仅对查询参数编码，切勿整体编码
---

# 什么是URL和URI是什么？

### URL 和 URI

#### URI (Uniform Resource Identifier)
**统一资源标识符**。URI 是一个通用的术语，用于标识任何互联网上的资源，无论资源是什么类型。

#### URL (Uniform Resource Locator)
**统一资源定位符**。URL 是 URI 的一种特殊形式，它不仅标识资源，还提供了资源的位置信息，即如何定位和获取资源。

#### URN (Uniform Resource Name)
**统一资源名称**。URN 是 URI 的另一种形式，通过名称标识资源（如 `isbn:978-0-123-45678-9`），与位置无关。即使资源移动，URN 也不变，但目前应用不如 URL 广泛。

#### URL 组成
URL 由以下几部分组成：
1. **协议**：指定访问资源的协议，例如 HTTP、HTTPS、FTP 等。
2. **域名或 IP 地址**：标识资源所在的主机或服务器的名称或 IP 地址。
3. **端口号**：指定服务器上监听资源请求的端口号，通常根据协议有默认端口（HTTP 80，HTTPS 443）。
4. **路径**：描述服务器上资源的具体路径或位置。
5. **查询参数**：用于向服务器传递参数，以影响资源的获取或显示。
6. **片段标识**：标识资源中的特定片段或位置。

```text
  协议    用户信息    主机名      端口   路径         查询参数        片段
  │       │           │           │      │            │              │
https://user:pass@example.com:8080/path/resource?key=value#section
```

#### 关系图解
URI 包含 URL 和 URN。URL 侧重于“定位”，URN 侧重于“命名”。

```text
       ┌───────────────────── URI ─────────────────────┐
       │                                                  │
       ├───────────────── URL ──────────┐   ┌───────── URN ───┐
       │                                  │   │                  │
  http://example.com/index.html      isbn:9787111
```

#### 示例
`https://www.example.com:8080/path/resource?param=value#section`
- 协议：HTTPS
- 域名：www.example.com
- 端口：8080
- 路径：/path/resource
- 参数：param=value
- 片段：section

#### 实战案例：编码陷阱导致的资源加载失败
在微服务间调用或前端请求时，如果参数中包含特殊字符（如 `&` 空格 `+`）且未进行 **URL 编码**，会导致解析错误。例如，文件名 `a & b.txt` 直接拼接到 URL 中会被解析为两个参数。实战中必须使用 `URLEncoder.encode(query, "UTF-8")` 对参数部分进行编码，将空格转为 `%20`，`&` 转为 `%26`。

#### 对比表格：URI 与 URL 的代码操作对比

| 操作 | Java 类 | 典型方法/用途 | 注意事项 |
| :--- | :--- | :--- | :--- |
| **解析** | `java.net.URI` | `create()`, `getHost()`, `getPath()` | 更符合规范，支持严格语法检查 |
| **请求/连接** | `java.net.URL` | `openConnection()`, `openStream()` | 实际用于建立网络连接，获取资源 |
| **编码** | `java.net.URLEncoder` | `encode(String, "UTF-8")` | 仅编码 URL 的**参数部分**，不要编码整个 URL |

#### 代码示例：安全的 URL 参数构建
```java
public String buildUrl(String baseUrl, String query) throws UnsupportedEncodingException {
    // 实战：只对查询参数进行编码，保留 base URL 结构
    String encodedParam = URLEncoder.encode(query, StandardCharsets.UTF_8.name());
    return String.format("%s/search?q=%s", baseUrl, encodedParam);
}
```

#### ## 常见考点
1. **URI 和 URL 的区别**：URL 是 URI 的子集，URI 强调标识，URL 强调定位。
2. **URL 编码**：为什么要编码？（保留字符、非 ASCII 字符、不安全字符）以及 `%20` 与 `+` 的区别。
3. **URN 的应用场景**：P2P 下载中的磁力链接（Magnet URI）。


## 记忆要点

- 概念对比：URI强调资源标识，而URL不仅标识还侧重提供具体的网络定位路径
- 包含关系：URI是顶级统称概念，URL和URN都是其子集
- URN特性：URN与物理位置无关，通过特定名称定位资源(如磁力链接或ISBN号)
- 结构拆解：协议+主机名+端口+路径+查询参数+片段标识符共同组成完整URL
- 编码避坑：URL拼接时必须用URLEncoder处理特殊字符，且仅对查询参数编码，切勿整体编码

## 结构化回答

**30 秒电梯演讲：** URI是资源ID，URL是资源的具体地址。打个比方，URI是身份证号（标识人），URL是家庭住址（定位并找到人）。

**展开框架：**
1. **概念对比** — URI强调资源标识，而URL不仅标识还侧重提供具体的网络定位路径
2. **包含关系** — URI是顶级统称概念，URL和URN都是其子集
3. **URN特性** — URN与物理位置无关，通过特定名称定位资源(如磁力链接或ISBN号)

**收尾：** 我在项目里踩过坑——实战案例：编码陷阱导致的资源加载失败。您想深入聊哪一段：原理、避坑还是对比选型？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：什么是URL和URI是什么 | "什么是URL和URI是什么？一句话——URI是身份证号（标识人），URL是家庭住址（定位并找到人）。" | 开场钩子 |
| 0:40 | 概念动画/示意图 | "URI是资源ID，URL是资源的具体地址——URI是身份证号（标识人），URL是家庭住址（定位并找到人）" | 核心定义 |
| 1:20 | 概念对比示意 | "URI强调资源标识，而URL不仅标识还侧重提供具体的网络定位路径" | 要点1 |
| 2:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |
