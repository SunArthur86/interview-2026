---
id: scen-063
difficulty: L2
category: scenario
subcategory: 安全与风控
tags:
- SSO
- OAuth2
- JWT
- 认证授权
- RBAC
- Token刷新
- 微服务安全
feynman:
  essence: 统一管理身份与权限，实现一次登录处处通行。
  analogy: 像公园门票，进门（认证）检票，游乐项目（授权）看票种。
  first_principle: 如何在开放的分布式网络环境中安全地确认身份并控制资源访问？
  key_points:
  - SSO统一登录状态，Cookie或Ticket互通
  - OAuth2分离授权与认证，支持第三方登录
  - JWT无状态自包含，适合微服务跨域
  - 双Token机制平衡安全与用户体验
follow_up:
- JWT如何实现主动失效？
- OAuth2四种模式的区别？
- 微服务如何传递用户身份？
memory_points:
- 概念辨析：认证验明正身是谁，授权决定能做什么操作。
- SSO机制：一次登录全网通行，靠全局Ticket结合SSO域Cookie实现免登。
- OAuth2常用：授权码模式最安全常用，引导用户授权拿Code，后端换Token。
- JWT特性：无状态自包含跨域友好，但难主动失效，Payload切忌存敏感信息。
- 双Token机制：短AccessToken访问，长RefreshToken续期，兼顾安全与体验。
---

# 如何设计统一认证授权系统（SSO/OAuth2/JWT）？

【场景分析】
认证：你是谁？
授权：你能做什么？

【SSO（单点登录）】
一次登录，所有子系统免登录。

SSO流程：
1. 用户访问子系统A → 未登录 → 重定向到SSO中心
2. SSO中心展示登录页 → 用户输入账密
3. SSO验证通过 → 生成Ticket → 写SSO域Cookie
4. 重定向回子系统A，携带Ticket
5. 子系统A向SSO验证Ticket → 获取用户信息 → 发本地Session
6. 用户访问子系统B → 重定向到SSO → SSO域Cookie存在 → 免登录 → 直接返回Ticket

【OAuth2.0（授权框架）】
四种授权模式：
1. 授权码模式（最常用）：
   - 第三方应用引导用户到授权服务器
   - 用户同意授权 → 返回授权码
   - 应用用授权码换AccessToken
   - 适用：有后端的Web应用
2. 简化模式：省略授权码，直接返回Token
3. 密码模式：用户提供账密给应用
4. 客户端模式：应用以自己身份获取Token

【JWT（JSON Web Token）】
结构：Header.Payload.Signature
```
Header: {"alg": "HS256", "typ": "JWT"}
Payload: {"userId": 123, "role": "admin", "exp": 1700000000}
Signature: HMACSHA256(base64(header) + "." + base64(payload), secret)
```

JWT优点：
- 无状态（服务端不存Session）
- 自包含（Payload携带用户信息）
- 跨域友好
- 适合微服务/移动端

JWT缺点：
- 无法主动失效（除非维护黑名单）
- Token较大
- Payload不加密（不要放敏感数据）

【微服务认证方案】
```
客户端 → API网关(JWT验证) → 微服务(透传userId)
网关验证JWT签名和过期时间
微服务从Header获取userId，无需再次验证
```

【Token刷新机制】
- AccessToken：有效期短（2小时）
- RefreshToken：有效期长（7天）
- AccessToken过期 → 用RefreshToken换新的
- RefreshToken过期 → 重新登录

【OAuth2 授权码模式流程图】
```
   User             Browser             Client (App)         Auth Server
    │                   │                     │                     │
    │---(1) Click Login--│                     │                     │
    │                   │---(2) Redirect -----│--(3) Redirect------>│
    │                   │                     │                     │
    │---(4) Input Pass--│                     │                     │
    │                   │                     │                     │
    │                   │                     │<--(5) Auth Code ----│
    │                   │                     │                     │
    │                   │                     │--(6) Token Req ---->│
    │                   │                     │ (Auth Code + Secret)│
    │                   │                     │                     │
    │                   │                     │<--(7) Access Token--│
    │                   │                     │   + Refresh Token   │
    │                   │                     │                     │
    │                   │<--(8) Login Success │                     │
```

【RBAC权限模型】
用户 → 角色 → 权限
- admin → 管理员角色 → [创建/删除/修改/查看]
- user → 普通角色 → [查看]

【安全要点】
- HTTPS传输
- Token安全存储（HttpOnly Cookie / Secure Storage）
- CSRF防护（SameSite Cookie）
- 密码加密存储（BCrypt）

## 常见考点
1. **JWT 注销问题**：JWT 是无状态的，用户点击“注销”后服务端如何使 Token 失效？（答：无法直接让 JWT 失效。方案一：客户端侧删除 Token；方案二：服务端维护 Token 黑名单，将未过期的 Token ID 存入 Redis，校验时拦截）
2. **Token 续期策略**：用户正在操作时 Token 过期了怎么办？（答：滑动会话刷新。前端在请求发出前检测 Token 剩余有效期，如小于阈值则用 RefreshToken 刷新；或者后端返回特定状态码 401 触发前端刷新重试）
3. **SSO 与 OAuth2 区别**：SSO 是一种登录解决方案，OAuth2 是一种授权框架。（答：SSO 侧重于多个应用系统间一次登录，处处通行；OAuth2 侧重于让第三方应用获得用户在某平台的操作权限，而无需告知密码）
4. **网关统一认证 vs 服务自认证**：微服务架构下 JWT 验证放在哪里？（答：通常放在 API 网关做统一鉴权和黑名单拦截，内部服务间调用若走内网信任区可使用透传的 userId 或更轻量的 mTLS 证书认证，避免每个服务重复解析 JWT）


## 记忆要点

- 概念辨析：认证验明正身是谁，授权决定能做什么操作。
- SSO机制：一次登录全网通行，靠全局Ticket结合SSO域Cookie实现免登。
- OAuth2常用：授权码模式最安全常用，引导用户授权拿Code，后端换Token。
- JWT特性：无状态自包含跨域友好，但难主动失效，Payload切忌存敏感信息。
- 双Token机制：短AccessToken访问，长RefreshToken续期，兼顾安全与体验。

## 结构化回答


**30 秒电梯演讲：** 像公园门票，进门（认证）检票，游乐项目（授权）看票种。

**展开框架：**
1. **SSO统一登录状态** — Cookie或Ticket互通
2. **OAuth2分离授权与认证** — OAuth2分离授权与认证，支持第三方登录
3. **JWT无状态自包含** — JWT无状态自包含，适合微服务跨域

**收尾：** JWT如何实现主动失效？


## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：统一认证授权系统（SSO/OAuth2/ | "统一认证授权系统（SSO/OAuth2/，一分钟讲透。" | 开场钩子 |
| 0:35 | 生活类比动画 | "打个比方——像公园门票，进门(认证)检票，游乐项目(授权)看票种。" | 核心类比 |
| 1:10 | 概念定义动画 | "一句话：统一管理身份与权限，实现一次登录处处通行。" | 核心定义 |
| 1:50 | SSO统一登录状态 图解 | "SSO统一登录状态，Cookie或Ticket互通。" | SSO统一登录状态 |
