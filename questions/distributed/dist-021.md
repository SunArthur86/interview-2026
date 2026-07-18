---
id: dist-021
difficulty: L3
category: distributed
feynman:
  essence: 接收客户端请求，按规则转发给后端多台服务器，实现流量分担。
  analogy: 像公司的前台（Nginx），接待客户（请求）后根据情况把工作分给不同的员工（后端服务）。
  first_principle: 如何将进入系统的请求透明地分配到多个处理节点以提升并发处理能力？
  key_points:
  - 反向代理隐藏后端服务器
  - upstream模块定义服务器组
  - 支持加权轮询、IP哈希等多种策略
  - 利用max_fails实现简单健康检查
memory_points:
- 反向代理：隐藏真实后端，Nginx 作为统一代理接收并转发请求。
- 核心配置：通过 upstream 模块定义后端组，利用 proxy_pass 指令转发。
- 调度策略：RR 轮询、weight 权重、ip_hash 会话保持、least_conn 最少连接。
- 容错参数：利用 max_fails 和 fail_timeout 控制健康检查与失败剔除。
- 避坑要点：因为默认 60s 超时易断开，慢接口需单独调大 proxy_read_timeout。
---

# Nginx如何实现反向代理和负载均衡？

Nginx 不仅可以用作 Web 服务器，更是一款高性能的反向代理和负载均衡器。

### 反向代理原理
客户端向 Nginx 发送请求，Nginx 作为代理服务器接收请求，然后根据配置将请求转发给后端的服务器池，后端服务器处理完成后将结果返回给 Nginx，最后由 Nginx 返回给客户端。
- 对客户端而言，Nginx 就是服务器，并不感知后端存在。

### 负载均衡实现
通过 `upstream` 模块定义后端服务器组，并使用 `proxy_pass` 指令转发请求。

#### 1. 定义 Upstream
```nginx
upstream backend {
    server 192.168.1.10 weight=1;      # 权重
    server 192.168.1.11:8080;         # 默认权重1
    server 192.168.1.12 backup;       # 备用节点
    server 192.168.1.13 max_fails=2 fail_timeout=30s;
}
```

#### 2. 负载均衡策略
- **轮询（默认）**：按时间顺序逐一分配。
- **weight**：指定权重，权重越高被分配的几率越大。
- **ip_hash**：根据客户端 IP 进行哈希，保证同一 IP 的客户端固定访问同一台服务器（解决会话保持）。注意：不能与 `weight` 一起使用。
- **least_conn**：最少连接，将请求分配给当前连接数最少的服务器（适合长连接场景）。
- **hash**：支持自定义 key（如 `$request_uri`）进行哈希，实现一致性哈希，便于缓存服务器的分片。
- **least_time**：商业版功能，分配给平均响应时间最短的服务器。

#### 3. 健康检查与容错
- **max_fails**：允许失败的次数。默认为 1，0 表示禁止检查。
- **fail_timeout**：失败后暂停请求的时间。默认 10 秒。
- **backup**：标记为备用服务器，仅当其他非备份服务器全部挂掉或繁忙时才启用。
- **down**：标记服务器永久不可用。
- **max_conns**：限制最大连接数，防止过载。

### 反向代理数据流图
```text
                    ┌─────────────┐
                    │   客户端    │
                    └──────┬──────┘
                           │
                           ▼
              ┌────────────────────────┐
              │        Nginx           │
              │  (反向代理 / 负载均衡)  │
              └────────┬───────────────┘
                       │
     ┌─────────────────┼─────────────────┐
     │                 │                 │
     ▼                 ▼                 ▼
┌──────────┐    ┌──────────┐     ┌──────────┐
│ Backend 1│    │ Backend 2│     │ Backend 3│
└──────────┘    └──────────┘     └──────────┘
```

### 常见考点
1. **长连接配置**：在 HTTP 层面，如何配置 `keepalive` 连接池（`keepalive`, `keepalive_requests`, `keepalive_timeout`）以减少 Nginx 与后端服务器建立 TCP 连接的开销。
2. **缓冲区设置**：`proxy_buffering` 的作用。开启缓冲后 Nginx 会尽可能从后端接收完响应再发给客户端，适合大文件下载；关闭则适合实时性要求高的接口（流式传输）。
3. **头信息传递**：`Host` 头的传递问题（`proxy_set_header Host $host`）以及获取真实客户端 IP 的 X-Forwarded-For 链路。
4. **公平调度**：第三方模块 `fair` 的原理，它不是基于轮询，而是根据后端服务器的响应时间进行调度。

### 实战案例
曾遇到业务侧反馈偶发 504 Gateway Timeout。排查发现是后端 Go 服务处理慢请求时，Nginx 默认的 `proxy_read_timeout`（60秒）触发断开。通过针对慢接口单独调整超时时间，并结合 `proxy_next_upstream error timeout` 实现故障自动重试，解决了偶发性超时导致的业务报错。

### 一致性哈希策略对比 (普通 vs 一致性)
| 特性 | 轮询 | IP Hash | 一致性 Hash (`hash`) | 最少连接 |
| :--- | :--- | :--- | :--- | :--- |
| **算法基础** | 计数器 | IP 地址模运算 | 虚拟节点环 | 活动连接计数 |
| **节点扩容** | 影响全部分配 | 影响全部分配 | 仅影响相邻节点 | 仅影响新请求路由 |
| **会话保持** | 否 | 是 (按源IP) | 是 (按Key) | 否 |
| **适用场景** | 无状态服务 | 需要固定后端 | 缓存分片/分库分表 | 长连接/任务处理 |

### 关键配置代码
```nginx
# 实战配置：长连接 + 一致性哈希 + 健康检查
upstream backend_cache {
    hash $request_uri consistent; # 一致性哈希，利于缓存命中
    server 10.0.0.1:8080 max_fails=3 fail_timeout=10s max_conns=1000;
    server 10.0.0.2:8080 max_fails=3 fail_timeout=10s max_conns=1000;
    keepalive 32; # 保持32个长连接到后端
}

server {
    location / {
        proxy_pass http://backend_cache;
        proxy_http_version 1.1;
        proxy_set_header Connection ""; # 清除Connection头以启用keepalive
        proxy_connect_timeout 5s;
        proxy_read_timeout 30s;
        proxy_send_timeout 30s;
    }
}
```


## 记忆要点

- 反向代理：隐藏真实后端，Nginx 作为统一代理接收并转发请求。
- 核心配置：通过 upstream 模块定义后端组，利用 proxy_pass 指令转发。
- 调度策略：RR 轮询、weight 权重、ip_hash 会话保持、least_conn 最少连接。
- 容错参数：利用 max_fails 和 fail_timeout 控制健康检查与失败剔除。
- 避坑要点：因为默认 60s 超时易断开，慢接口需单独调大 proxy_read_timeout。

## 结构化回答


**30 秒电梯演讲：** 像公司的前台（Nginx），接待客户（请求）后根据情况把工作分给不同的员工（后端服务）。

**展开框架：**
1. **反向代理隐藏** — 反向代理隐藏后端服务器
2. **upstre** — upstream模块定义服务器组
3. **IP** — 支持加权轮询、IP哈希等多种策略

**收尾：** 这是我实战中的理解，您想深入哪一段？


## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：Nginx如何实现反向代理和负载均衡 | "Nginx如何实现反向代理和负载均衡，这题我会分三步讲。" | 开场钩子 |
| 0:41 | 概念定义动画 | "一句话：接收客户端请求，按规则转发给后端多台服务器，实现流量分担。" | 核心定义 |
| 1:22 | 生活类比动画 | "打个比方——像公司的前台(Nginx)，接待客户(请求)后根据情况把工作分给不同的员工(后端服务)。" | 核心类比 |
| 2:03 | 反向代理隐藏后端 图解 | "反向代理隐藏后端服务器。" | 反向代理隐藏后端 |
| 2:50 | upstream模块 图解 | "upstream模块定义服务器组。" | upstream模块 |
