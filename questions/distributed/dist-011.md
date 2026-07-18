---
id: dist-011
difficulty: L2
category: distributed
feynman:
  essence: 基于应用层内容（如URL）智能分发流量到不同后端。
  analogy: 像快递分拣员，根据包裹上的具体地址（URL）把货送到对应的货架（服务器）。
  first_principle: 如何根据请求的具体业务内容（而非仅仅IP端口）将流量导向正确的处理服务？
  key_points:
  - 工作在OSI七层（应用层）
  - 能根据HTTP内容（URL、Header）路由
  - 通常作为反向代理使用
  - 比四层更灵活但性能略低
memory_points:
- 一句话定义：工作在应用层，通过解析 HTTP 报文内容（如 URL/Header）进行流量分发
- 四层Vs七层：四层基于 IP+端口极速转发，而七层基于内容代理转发消耗 CPU 算力
- 业务价值：因为能深度识别内容，所以支持按路径路由和灰度发布等精细化业务控制
- 代表软件：四层典型是 LVS，而七层典型是 Nginx 或 HAProxy
frequency: medium
---

# 什么是七层负载均衡（内容交换）？

### 七层负载均衡（内容交换）

七层负载均衡工作在 OSI 模型的应用层（Layer 7），主要通过解析报文中真正有意义的应用层内容（如 HTTP URL、Header、Cookie 信息），结合预设的负载均衡算法，决定最终选择的后端服务器。

### 实战案例
在做多端适配（H5 vs App）时，利用七层负载均衡根据 User-Agent 头将流量分发到不同代码版本的服务器，无需部署两套独立域名，从而简化发布流程。

### 关键代码示例 (Nginx)
```nginx
upstream api_servers {
    server 192.168.1.10:8080;
    server 192.168.1.11:8080;
}

server {
    listen 80;
    # 根据 URL 路径路由
    location /api/ {
        proxy_pass http://api_servers;
    }
    # 根据 Cookie 灰度发布
    location / {
        if ($cookie_version = "v2") {
            proxy_pass http://new_version_servers;
        }
        proxy_pass http://stable_servers;
    }
}
```

### 与四层负载均衡的区别
| 特性 | 四层负载均衡 | 七层负载均衡 |
| :--- | :--- | :--- |
| **工作层次** | 传输层 (TCP/UDP) | 应用层 (HTTP/HTTPS) |
| **依据** | IP + 端口 | URL、Cookie、Header 内容 |
| **处理方式** | 修改目标 IP 转发 | 代理请求，可能重写内容 |
| **性能** | 极高（仅调度包） | 较高（需解析报文，消耗 CPU） |
| **典型软件** | LVS, HAProxy (四层模式) | Nginx, HAProxy (七层模式), Apache |

### 工作原理
1. 客户端发送 HTTP 请求到达负载均衡器。
2. 负载均衡器终止 TCP 连接（或建立新的 TCP 连接），解析 HTTP 报文。
3. 根据报文内容（例如 `/static` 图片请求转发给静态服务器，`/api` 请求转发给应用服务器）选择后端服务器。
4. 负载均衡器作为代理，向后端服务器发起请求，并将响应返回给客户端。

### 常见软件
- **Nginx**：高性能，支持正则表达式路由，常用作七层反向代理。
- **HAProxy**：功能强大，支持七层路由和 ACL 规则。
- **Apache**：模块丰富，历史悠久的七层代理。


## 核心流程图

```mermaid
flowchart TD
    REQ([客户端请求]) --> LB[负载均衡器]

    LB --> STRATEGY{调度策略}
    STRATEGY -->|轮询| RR[Round Robin<br/>依次分配]
    STRATEGY -->|加权| WRR[Weighted RR<br/>按机器性能配比]
    STRATEGY -->|随机| RND[Random<br/>概率均衡]
    STRATEGY -->|最少连接| LC[Least Connections<br/>实时负载感知]
    STRATEGY -->|IP Hash| IPH[IP Hash<br/>会话保持]
    STRATEGY -->|一致性 Hash| CH[Consistent Hash<br/>虚拟节点最小迁移]

    RR --> NODES[后端节点池]
    WRR --> NODES
    RND --> NODES
    LC --> NODES
    IPH --> NODES
    CH --> NODES

    NODES --> HEALTH{健康检查}
    HEALTH -->|健康| ROUTE[转发请求]
    HEALTH -->|异常| EVICT[剔除节点<br/>故障转移]
    EVICT --> LB

    ROUTE --> TIER{层级}
    TIER -->|L4 传输层| L4LVS[LVS/硬件<br/>IP+端口 改包<br/>DR/NAT/TUN/FNAT]
    TIER -->|L7 应用层| L7NG[Nginx/HAProxy<br/>HTTP 头/Cookie/URL<br/>路由+鉴权+限流]

    L4LVS --> UP([上游服务])
    L7NG --> UP

    style REQ fill:#4CAF50,color:#fff
    style UP fill:#2196F3,color:#fff
    style CH fill:#FF9800,color:#fff
    style L4LVS fill:#9C27B0,color:#fff
    style L7NG fill:#009688,color:#fff
    style EVICT fill:#F44336,color:#fff

```

## 记忆要点

- 一句话定义：工作在应用层，通过解析 HTTP 报文内容（如 URL/Header）进行流量分发
- 四层Vs七层：四层基于 IP+端口极速转发，而七层基于内容代理转发消耗 CPU 算力
- 业务价值：因为能深度识别内容，所以支持按路径路由和灰度发布等精细化业务控制
- 代表软件：四层典型是 LVS，而七层典型是 Nginx 或 HAProxy

## 结构化回答


**30 秒电梯演讲：** 像快递分拣员，根据包裹上的具体地址（URL）把货送到对应的货架（服务器）。

**展开框架：**
1. **OSI** — 工作在OSI七层（应用层）
2. **HTTP** — 能根据HTTP内容（URL、Header）路由
3. **通常作为反向代理使** — 通常作为反向代理使用

**收尾：** 这是我实战中的理解，您想深入哪一段？


## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：七层负载均衡（内容交换） | "七层负载均衡（内容交换），一分钟讲透。" | 开场钩子 |
| 0:35 | 生活类比动画 | "打个比方——像快递分拣员，根据包裹上的具体地址(URL)把货送到对应的货架(服务器)。" | 核心类比 |
| 1:10 | 概念定义动画 | "一句话：基于应用层内容(如URL)智能分发流量到不同后端。" | 核心定义 |
| 1:50 | 工作在OSI七层(应 图解 | "工作在OSI七层(应用层)。" | 工作在OSI七层(应 |

### 视频流程图

```mermaid
flowchart LR

    subgraph Intro["引入"]
        A["什么是七层负载均衡（内容交换）？"]:::intro
    end

    subgraph Core["讲解"]
        B["一句话定义：工作在应用层，通过解析 HTTP 报文内…"]:::core
        C["四层Vs七层：四层基于 IP+端口极速转发，而七层基…"]:::deep
    end

    subgraph Practice["实战"]
        D["代码实战"]:::practice
    end

    subgraph Wrap["收尾"]
        E["总结回顾"]:::wrap
    end

    A --> B --> C --> D --> E

    classDef intro fill:#FF9800,color:#fff,stroke:#F57C00,stroke-width:2px
    classDef core fill:#2196F3,color:#fff,stroke:#1976D2,stroke-width:2px
    classDef deep fill:#4CAF50,color:#fff,stroke:#388E3C,stroke-width:2px
    classDef practice fill:#9C27B0,color:#fff,stroke:#7B1FA2,stroke-width:2px
    classDef wrap fill:#607D8B,color:#fff,stroke:#455A64,stroke-width:2px
```

