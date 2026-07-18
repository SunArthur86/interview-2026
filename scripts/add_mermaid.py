#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch-generate detailed mermaid diagrams for interview-2026 markdown files.

For each .md file in questions/{java-core,database,scenario} that does not
already contain a ```mermaid``` block, this script:
  1. Reads the frontmatter (title, essence, key_points, category, id)
  2. Picks a domain-specific mermaid template (or falls back to a generic one)
  3. Inserts "## 核心流程图" + mermaid block before "## 记忆要点"
     (or before "## 结构化回答" if there is no 记忆要点)
"""

import os
import re
import sys

ROOT = '/Users/sunqingguang/hermes/opt/projects/interview-2026'

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def write(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def parse_frontmatter(text):
    """Return a dict with title, id, category, essence, key_points."""
    m = re.match(r'^---\n(.*?)\n---\n(.*)$', text, re.DOTALL)
    if not m:
        return {}
    fm = m.group(1)
    body = m.group(2)

    # title from first H1
    t = re.search(r'^#\s+(.+?)$', body, re.MULTILINE)
    title = t.group(1).strip() if t else ''

    # id
    i = re.search(r'^id:\s*(\S+)', fm, re.MULTILINE)
    fid = i.group(1).strip() if i else ''

    # category
    c = re.search(r'^category:\s*(\S+)', fm, re.MULTILINE)
    cat = c.group(1).strip() if c else ''

    # essence
    e = re.search(r'essence:\s*(.+?)(?=\n\s+\w+:|\n\w+:|\Z)', fm, re.DOTALL)
    essence = e.group(1).strip() if e else ''

    # first_principle
    fp = re.search(r'first_principle:\s*(.+?)(?=\n\s+\w+:|\n\w+:|\Z)', fm, re.DOTALL)
    principle = fp.group(1).strip() if fp else ''

    # key_points list
    kp = re.search(r'key_points:\s*\n((?:\s+-\s+.+\n?)+)', fm)
    key_points = []
    if kp:
        key_points = [ln.strip().lstrip('-').strip().strip("'\"")
                      for ln in kp.group(1).splitlines()
                      if ln.strip().startswith('-')]

    return {
        'title': title, 'id': fid, 'category': cat,
        'essence': essence, 'principle': principle,
        'key_points': key_points
    }


# ---------------------------------------------------------------------------
# Mermaid templates (rich, detailed, domain-aware)
# ---------------------------------------------------------------------------
# Each template is a function returning a string of mermaid code.
# Color palette: green=success/hit, blue=input/start, orange=decision,
# red=error/miss, purple=async/special, gray=storage.

def _common_styles():
    return """    classDef start fill:#e3f2fd,stroke:#1976d2,stroke-width:2px,color:#0d47a1
    classDef decision fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#e65100
    classDef success fill:#e8f5e9,stroke:#388e3c,stroke-width:2px,color:#1b5e20
    classDef error fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#b71c1c
    classDef storage fill:#eceff1,stroke:#455a64,stroke-width:2px,color:#263238
    classDef async fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#4a148c"""


# ============== Spring MVC / 注解 ==============
def tpl_spring_mvc(meta):
    return """```mermaid
flowchart TD
    BR([浏览器发起HTTP请求]):::start --> DS[DispatcherServlet<br/>前端控制器接收]
    DS --> HM[HandlerMapping<br/>解析RequestMapping注解]
    HM --> EC{URL匹配成功?}:::decision
    EC -->|否| N404[404 Not Found<br/>响应客户端]:::error
    EC -->|是| HA[HandlerAdapter<br/>适配器调用Controller]
    HA --> AN[解析方法注解<br/>@PathVariable/@RequestBody/@RequestParam]
    AN --> CONV[HandlerMethodArgumentResolver<br/>参数类型转换与绑定]
    CONV --> CH{参数校验通过?}:::decision
    CH -->|否 @Valid失败| BEX[MethodArgumentNotValidException<br/>全局异常处理]:::error
    CH -->|是| CTRL[Controller业务方法执行<br/>调用Service/Repository]
    CTRL --> RT{返回类型判断}:::decision
    RT -->|@ResponseBody / @RestController| JACK[Jackson序列化为JSON]
    RT -->|ModelAndView / 视图名| VR[ViewResolver视图解析器]
    JACK --> WR[WriteResponseBodyAdvice<br/>响应体输出]
    VR --> RD[渲染视图HTML/JSP/Thymeleaf]
    WR --> CL([客户端收到JSON响应]):::success
    RD --> CL
    {_common_styles()}
```"""


# ============== 代理模式 ==============
def tpl_proxy(meta):
    return """```mermaid
flowchart TD
    CL([Client客户端调用]):::start --> P[Proxy代理对象<br/>实现相同接口]
    P --> CH{调用类型判断}:::decision
    CH -->|静态代理| SP[编译期生成代理类<br/>持有RealSubject引用]
    CH -->|JDK动态代理| JP[JDK Proxy.newProxyInstance<br/>基于接口生成]
    CH -->|CGLIB动态代理| CG[CGLIB Enhancer<br/>基于子类继承生成]
    JP --> IH[InvocationHandler.invoke<br/>前置增强: 日志/权限/事务]
    CG --> MI[MethodInterceptor.intercept<br/>前置增强: 日志/权限/事务]
    SP --> RS
    IH --> RS[RealSubject真实方法<br/>业务核心逻辑]
    MI --> RS
    RS --> POST[后置增强: 缓存/提交事务/统计]
    POST --> RET[返回结果给代理对象]
    RET --> CL2([客户端拿到增强后的结果]):::success
    {_common_styles()}
```"""


# ============== 内存分段分页 ==============
def tpl_paging(meta):
    return """```mermaid
flowchart TD
    P([程序生成虚拟地址VA]):::start --> SP[CPU分段/分页单元]
    SP --> SEG{是否启用分段?}:::decision
    SEG -->|是| STB[查段表Segment Table<br/>基址+界限+权限]
    SEG -->|否纯分页| PG[地址切分: 页号+页内偏移]
    STB --> BC{段界限检查}:::decision
    BC -->|越界| TRAP1[触发段越界异常<br/>Segmentation Fault]:::error
    BC -->|合法| LIN[线性地址生成]
    LIN --> PG
    PG --> TLB[查TLB快表<br/>页号→物理页框]
    TLB --> TH{TLB命中?}:::decision
    TH -->|命中| PHYS[直接拼接物理地址]
    TH -->|未命中| PT[遍历多级页表Page Table]
    PT --> PV{页表有效位P=1?}:::decision
    PV -->|P=0缺页| DF[缺页中断Page Fault]
    PV -->|P=1| CAC[更新TLB缓存]
    DF --> DISK[从磁盘Swap区加载到空闲页框]:::storage
    DISK --> REP{内存已满?}:::decision
    REP -->|是| LRU[执行页面置换LRU/FIFO<br/>选牺牲页换出]:::async
    REP -->|否| LOAD[写入物理页框 更新PTE]
    LRU --> LOAD
    LOAD --> CAC
    CAC --> PHYS
    PHYS --> MEM[访问物理内存RAM]:::success
    {_common_styles()}
```"""


# ============== TCP拥塞控制 ==============
def tpl_congestion(meta):
    return """```mermaid
flowchart TD
    ST([TCP连接建立<br/>cwnd=1 ssthresh=16]):::start --> SS[慢启动Slow Start<br/>每RTT cwnd翻倍]
    SS --> CHK1{cwnd >= ssthresh?}:::decision
    CHK1 -->|否 继续指数增长| SS
    CHK1 -->|是| AV[拥塞避免Congestion Avoidance<br/>每RTT cwnd+1 线性增长]
    AV --> LOSS{是否检测到丢包?}:::decision
    LOSS -->|否| ACK[收到ACK 继续发送]
    ACK --> AV
    LOSS -->|3个重复ACK 快重传| FR[快恢复Fast Recovery<br/>ssthresh=cwnd/2<br/>cwnd=ssthresh+3]
    LOSS -->|RTO超时 重传| TO[严重拥塞<br/>ssthresh=cwnd/2<br/>cwnd=1]
    TO --> SS2[重新进入慢启动]
    FR --> ACK2[收到新ACK<br/>cwnd=ssthresh]
    SS2 --> AV2[再次进入拥塞避免]
    ACK2 --> AV2
    AV2 --> STABLE([稳定传输状态]):::success
    {_common_styles()}
```"""


# ============== 滑动窗口 ==============
def tpl_sliding_window(meta):
    return """```mermaid
flowchart LR
    SND([发送方Sender]):::start --> BUF[发送缓冲区<br/>已发送未确认+待发送]
    BUF --> WN[按cwnd/rwnd<br/>划分四个窗口区域]
    WN --> W1[1.已确认<br/>可滑出窗口]:::success
    WN --> W2[2.已发送未确认<br/>等待ACK]:::async
    WN --> W3[3.可发送未发送<br/>可用窗口]:::decision
    WN --> W4[4.不可发送<br/>超出窗口]:::storage
    W3 --> SEG[封装TCP段 携带Seq]
    SEG --> NET((网络传输)):::storage
    NET --> RCV[接收方Receiver]
    RCV --> RW{按序到达?}:::decision
    RW -->|失序| CACHE[缓存失序段<br/>发送重复ACK]:::async
    RW -->|按序| APP[提交应用层]
    APP --> ACK[回送ACK+更新rwnd<br/>告知剩余接收窗口]
    ACK --> NET
    NET --> RCV2[发送方收到ACK]
    RCV2 --> SLIDE[窗口前沿滑动<br/>移除已确认段]
    SLIDE --> W3
    {_common_styles()}
```"""


# ============== 摘要算法 + 数字签名 ==============
def tpl_signature(meta):
    return """```mermaid
flowchart TD
    PL([发送方: 原始消息M]):::start --> H1[哈希函数SHA-256/MD5<br/>定长摘要生成]
    H1 --> DG[消息摘要Digest<br/>128/256位固定长度]
    DG --> SK[发送方私钥Private Key<br/>RSA/ECDSA加密摘要]
    SK --> SIG[生成数字签名<br/>附在消息后发送]
    SIG --> CH((网络传输通道)):::storage
    PL --> CH
    CH --> RCV([接收方收到 M+签名]):::start
    RCV --> H2[同样哈希函数<br/>对M重新计算摘要Hm]
    RCV --> VRF[用发送方公钥<br/>解密签名得到Hs]
    H2 --> CMP{Hm == Hs ?}:::decision
    VRF --> CMP
    CMP -->|相等| OK[验证通过<br/>消息完整+身份可信+不可否认]:::success
    CMP -->|不等| FAIL[验证失败<br/>消息被篡改或伪造]:::error
    OK --> CER{是否需要CA背书?}:::decision
    CER -->|是| CA[CA数字证书<br/>公钥绑定身份]
    CER -->|否| DONE([完成]):::success
    CA --> DONE
    {_common_styles()}
```"""


# ============== 混合加密 ==============
def tpl_hybrid(meta):
    return """```mermaid
flowchart TD
    PL([发送方: 明文数据]):::start --> GEN[生成临时会话密钥<br/>Session Key随机数]
    GEN --> SYM[对称加密AES<br/>用Session Key加密明文]
    SYM --> CPH[密文Ciphertext<br/>加密速度快]
    PL2([接收方: RSA公钥]):::start --> ENC[非对称加密RSA<br/>用公钥加密Session Key]
    ENC --> SKC[加密后的会话密钥]
    CPH --> TRANS((传输通道: TLS/SSL)):::storage
    SKC --> TRANS
    TRANS --> RCV([接收方收到密文+加密会话密钥])
    RCV --> DEC1[用RSA私钥<br/>解密得到Session Key]:::async
    DEC1 --> DEC2[用Session Key<br/>AES解密密文]
    DEC2 --> ORIG([恢复原始明文]):::success
    {_common_styles()}
```"""


# ============== 缓存机制 ==============
def tpl_cache_mechanism(meta):
    return """```mermaid
flowchart TD
    REQ([CPU访问内存地址]):::start --> L1[L1 Cache 指令/数据<br/>几十KB 纳秒级]
    L1 --> H1{L1命中?}:::decision
    H1 -->|是| R1[返回数据 延迟约1ns]:::success
    H1 -->|否| L2[L2 Cache 多核共享<br/>几百KB]
    L2 --> H2{L2命中?}:::decision
    H2 -->|是| UP1[数据回填L1 返回]:::success
    H2 -->|否| L3[L3 Cache<br/>几MB~几十MB]
    L3 --> H3{L3命中?}:::decision
    H3 -->|是| UP2[逐级回填L1/L2 返回]:::success
    H3 -->|否| MISS[Cache Miss<br/>触发硬件读内存]
    MISS --> RAM[访问主内存DRAM<br/>约100ns]:::storage
    RAM --> FILL[按Cache Line 64B<br/>加载并替换]
    FILL --> REPL{Cache已满?}:::decision
    REPL -->|是| EV[LRU/随机替换策略<br/>淘汰旧块]:::async
    REPL -->|否| INS[直接插入新块]
    EV --> RTN([返回数据给CPU]):::success
    INS --> RTN
    {_common_styles()}
```"""


# ============== Keep-Alive ==============
def tpl_keep_alive(meta):
    return """```mermaid
flowchart TD
    R1([HTTP/1.1首次请求]):::start --> CONN[TCP三次握手建立连接]
    CONN --> HDR[请求头携带<br/>Connection: keep-alive]
    HDR --> SEND1[发送HTTP Request 1]
    SEND1 --> RESP1[服务器返回Response 1<br/>Connection: keep-alive]
    RESP1 --> IDLE[连接保持空闲<br/>等待后续请求复用]
    IDLE --> TM{是否超时?}:::decision
    TM -->|是 默认Timeout| CLOSE[TCP四次挥手关闭]:::error
    TM -->|否| R2([HTTP第二次请求]):::start
    R2 --> REUSE[复用现有TCP连接<br/>跳过握手节省RTT]
    REUSE --> SEND2[直接发送Request 2]
    SEND2 --> RESP2[服务器返回Response 2]
    RESP2 --> LOOP{继续请求?}:::decision
    LOOP -->|是| IDLE
    LOOP -->|否 Connection: close| CLOSE
    {_common_styles()}
```"""


# ============== TCP vs UDP ==============
def tpl_tcp_udp(meta):
    return """```mermaid
flowchart TD
    APP([应用层数据]):::start --> CHO{传输需求}:::decision
    CHO -->|需要可靠传输| TCP[TCP 传输控制协议]
    CHO -->|需要实时/低延迟| UDP[UDP 用户数据报协议]
    TCP --> CONN[面向连接<br/>三次握手建立]
    CONN --> SEQ[数据分seq编号<br/>保证顺序]
    SEQ --> ACK[确认重传机制<br/>丢包自动重传]
    ACK --> FLOW[流量控制sliding window<br/>拥塞控制]
    FLOW --> HDP[头部20字节<br/>开销大]
    HDP --> TCPAPP[Web/邮件/文件传输<br/>HTTP/FTP/SMTP]:::success
    UDP --> NC[无连接<br/>直接发送]
    NC --> BEST[尽力而为<br/>不保证可靠]
    BEST --> NH[头部仅8字节<br/>开销小]
    NH --> MC[支持广播/多播<br/>一对多]
    MC --> UDPAPP[视频直播/语音/DNS<br/>实时性高容忍丢包]:::success
    {_common_styles()}
```"""


# ============== select/poll/epoll ==============
def tpl_epoll(meta):
    return """```mermaid
flowchart TD
    APP([应用调用IO多路复用]):::start --> SEL{机制选择}:::decision
    SEL -->|select| SL[select: fd_set位图<br/>FD上限1024]
    SEL -->|poll| PL[poll: pollfd数组<br/>无FD数量限制]
    SEL -->|epoll| EP[epoll: 红黑树+就绪链表<br/>Linux专用]
    SL --> CO1[拷贝全部fd到内核<br/>每次调用全量扫描]
    PL --> CO2[拷贝pollfd数组到内核<br/>线性扫描O(n)]
    CO1 --> BL1[内核轮询所有fd<br/>复杂度O(n)]
    CO2 --> BL1
    BL1 --> RET1[返回就绪fd数量<br/>应用需再次遍历]
    EP --> CT[epoll_create 创建实例<br/>红黑树管理fd]:::async
    CT --> ADD[epoll_ctl 注册fd<br/>关联回调函数]
    ADD --> WAIT[epoll_wait 阻塞等待]
    WAIT --> EVT[网卡中断→回调<br/>就绪fd加入就绪链表]:::success
    EVT --> RET2[直接返回就绪fd<br/>复杂度O(1)~O(就绪数)]
    RET1 --> PR[应用处理IO事件]
    RET2 --> PR
    PR --> DONE([继续下一轮监听]):::success
    {_common_styles()}
```"""


# ============== TCP三次握手 ==============
def tpl_3way(meta):
    return """```mermaid
sequenceDiagram
    autonumber
    participant C as 客户端 Client
    participant S as 服务端 Server
    Note over C,S: 初始: 双方CLOSED / LISTEN
    C->>S: SYN=1, seq=x (我要建立连接)
    Note right of C: 进入 SYN_SENT 状态
    S->>C: SYN=1, ACK=1, seq=y, ack=x+1 (确认收到你的SYN,我也想连)
    Note right of S: 进入 SYN_RCVD 状态
    C->>S: ACK=1, seq=x+1, ack=y+1 (确认收到你的SYN)
    Note right of C: 进入 ESTABLISHED 状态
    Note right of S: 收到后进入 ESTABLISHED 状态
    rect rgba(76,175,80,0.15)
    Note over C,S: 可以双向传输数据
    C->>S: 发送HTTP请求等业务数据
    S->>C: 返回响应数据
    end
```"""


# ============== TIME_WAIT / 2MSL ==============
def tpl_time_wait(meta):
    return """```mermaid
flowchart TD
    A([主动关闭方: 发送FIN]):::start --> B[进入FIN_WAIT_1]
    B --> C[被动方回ACK]
    C --> D[主动方进入FIN_WAIT_2<br/>等待对端FIN]
    D --> E[被动方发FIN]
    E --> F[主动方回ACK<br/>进入TIME_WAIT状态]:::async
    F --> G{为什么等待2MSL?}:::decision
    G -->|原因1: 防止ACK丢失| R1[若最后的ACK丢失<br/>被动方重发FIN]
    R1 --> R2[主动方需保持socket<br/>才能重发ACK]
    G -->|原因2: 防止旧报文干扰| O1[让本次连接的所有报文<br/>在网络中消亡]
    O1 --> O2[MSL=最大报文生存时间<br/>2MSL确保往返消亡]
    R2 --> W[等待2*MSL 默认60秒]
    O2 --> W
    W --> CLOSE([进入CLOSED 释放端口资源]):::success
    F -.->|副作用| ISSUE[大量短连接→TIME_WAIT堆积<br/>解决: SO_REUSEADDR/缩短MSL]
    {_common_styles()}
```"""


# ============== DNS解析 ==============
def tpl_dns(meta):
    return """```mermaid
flowchart TD
    U([用户输入 www.example.com]):::start --> LC[查浏览器DNS缓存]
    LC --> H1{本地命中?}:::decision
    H1 -->|是| IP1[直接返回IP]:::success
    H1 -->|否| OS[查操作系统DNS缓存]
    OS --> H2{OS命中?}:::decision
    H2 -->|是| IP1
    H2 -->|否| LH[查本地hosts文件]
    LH --> H3{hosts命中?}:::decision
    H3 -->|是| IP1
    H3 -->|否| RD[向本地DNS服务器<br/>递归查询]
    RD --> ROOT[查询根域名服务器.<br/>返回TLD NS地址]
    ROOT --> TLD[查询顶级域.com NS<br/>返回权威NS地址]
    TLD --> AUTH[查询example.com权威服务器<br/>返回最终A记录]
    AUTH --> RTN[本地DNS缓存结果<br/>返回浏览器]
    RTN --> H4{是否CDN调度?}:::decision
    H4 -->|是| CDN[根据用户EDNS<br/>返回最近CDN节点IP]:::async
    H4 -->|否| IP2([拿到目标IP]):::success
    CDN --> IP2
    IP1 --> IP2
    {_common_styles()}
```"""


# ============== HTTP/1.1 ==============
def tpl_http11(meta):
    return """```mermaid
flowchart TD
    HTTP([HTTP/1.1主要特性]):::start --> F1[长连接Persistent<br/>默认keep-alive]
    HTTP --> F2[管道化Pipelining<br/>请求可并发发送]
    HTTP --> F3[虚拟主机Host头<br/>同IP多域名]
    HTTP --> F4[分块传输chunked<br/>流式响应]
    HTTP --> F5[缓存控制<br/>Cache-Control/ETag]
    F1 --> BEN1[省去频繁握手<br/>降低延迟]:::success
    F2 --> LIMIT1{响应须按序返回}:::decision
    LIMIT1 -->|队头阻塞HOL| CON1[慢响应阻塞后续<br/>浏览器6连接并发补救]:::error
    F3 --> VHS[服务器路由分发<br/>基于Host]
    F4 --> STREAM[未知Content-Length<br/>支持动态生成]
    F5 --> COND[协商缓存If-None-Match<br/>304减少带宽]:::async
    BEN1 --> UPG{需要更强性能?}:::decision
    UPG -->|是| H2[升级HTTP/2<br/>多路复用+二进制分帧]
    UPG -->|否| KEEP[继续使用HTTP/1.1]
    H2 --> H3[升级HTTP/3<br/>基于QUIC/UDP]:::success
    {_common_styles()}
```"""


# ============== HTTP特性 ==============
def tpl_http_feature(meta):
    return """```mermaid
flowchart TD
    HTTP([HTTP协议本质特征]):::start --> P1[无状态stateless<br/>每次请求相互独立]
    HTTP --> P2[无连接<br/>请求-响应一次完成]
    HTTP --> P3[基于TCP<br/>默认80端口]
    HTTP --> P4[请求-响应模型<br/>客户端主动]
    HTTP --> P5[文本协议<br/>人类可读]
    P1 --> CON1[优点: 简单易扩展<br/>缺点: 需Cookie/Session维持状态]:::decision
    CON1 --> SOL1[Cookie: 客户端存储<br/>Set-Cookie响应头]
    CON1 --> SOL2[Session: 服务端存储<br/>JSESSIONID Cookie关联]
    P2 --> SOL3[Keep-Alive复用连接<br/>弥补无连接开销]
    P3 --> SOL4[握手3次+挥手4次<br/>HTTP/3改用UDP]
    P4 --> SOL5[WebSocket升级后<br/>支持双向推送]
    SOL1 --> SEC{安全考量}:::decision
    SEC -->|明文传输风险| HTTPS[升级HTTPS<br/>TLS加密+证书]:::async
    SEC -->|Cookie被窃取| FLAG[HttpOnly+Secure+SameSite]
    HTTPS --> DONE([安全可靠HTTP]):::success
    {_common_styles()}
```"""


# ============== 阻塞队列 ==============
def tpl_blocking_queue(meta):
    return """```mermaid
flowchart TD
    subgraph PROD [生产者线程]
        P1([生产者1]):::start
        P2([生产者2]):::start
    end
    subgraph CONS [消费者线程]
        C1([消费者1]):::start
        C2([消费者2]):::start
    end
    P1 --> PUT[put 阻塞入队]
    P2 --> PUT
    PUT --> LK{队列状态判断}:::decision
    LK -->|已满 ArrayBlockingQueue有界| FULL[notFull.await<br/>线程阻塞挂起]:::error
    LK -->|未满| ENQ[ReentrantLock加锁<br/>元素入队尾]
    FULL --> NOTIFY[notFull.signal<br/>唤醒后等待]
    NOTIFY --> ENQ
    ENQ --> SIG[notEmpty.signal<br/>唤醒等待的消费者]:::async
    SIG --> Q[(底层: 数组/链表/堆)]:::storage
    Q --> TAKE[take 阻塞出队]
    C1 --> TAKE
    C2 --> TAKE
    TAKE --> LK2{队列状态判断}:::decision
    LK2 -->|为空| EMPTY[notEmpty.await<br/>线程阻塞挂起]:::error
    LK2 -->|非空| DEQ[ReentrantLock加锁<br/>取队首元素]
    EMPTY --> SIG2[notEmpty.signal]:::async
    SIG2 --> DEQ
    DEQ --> SIG3[notFull.signal<br/>唤醒生产者]
    SIG3 --> PROC[消费处理]:::success
    {_common_styles()}
```"""


# ============== Java基础数据类型 ==============
def tpl_java_type(meta):
    return """```mermaid
flowchart TD
    JT([Java数据类型体系]):::start --> PRI[基本类型Primitive 8种]
    JT --> REF[引用类型Reference]
    PRI --> NUM[数值型]
    PRI --> BOOL[boolean 1位 true/false]
    PRI --> CHR[char 2字节 Unicode字符]:::storage
    NUM --> INT[整数型]
    NUM --> FLT[浮点型]
    INT --> B1[byte 1字节 -128~127]
    INT --> S2[short 2字节]
    INT --> I4[int 4字节 默认整型]
    INT --> L8[long 8字节 L后缀]
    FLT --> F4[float 4字节 F后缀 IEEE754]
    FLT --> D8[double 8字节 默认浮点]
    REF --> CLS[类class: String/Object]
    REF --> ARR[数组array: int[]/Object[]]
    REF --> IF[接口interface: List/Map]
    B1 --> CACHE{包装类缓存机制}:::decision
    CACHE -->|Integer Cache -128~127| SH[相同地址 ==为true]
    CACHE -->|超出范围或new| NSH[不同对象 ==为false<br/>须用equals]:::error
    SH --> AUT[自动装箱拆箱<br/>编译期 valueOf/xxxValue]:::async
    NSH --> AUT
    {_common_styles()}
```"""


# ============== Linux网络 ==============
def tpl_linux_net(meta):
    return """```mermaid
flowchart TD
    APP([应用层: socket编程]):::start --> SYSCALL[系统调用<br/>send/write]
    SYSCALL --> KER[(内核态 网络协议栈)]:::storage
    KER --> TCP[TCP层<br/>分片/序号/校验]
    TCP --> IP[IP层<br/>路由选择/TTL]
    IP --> DM{数据流向}:::decision
    DM -->|发送| NIC[网卡驱动DMA<br/>RingBuffer]
    DM -->|接收| SOFT[软中断处理<br/>net_rx_action]
    NIC --> HW[硬件中断 → 队列]:::async
    HW --> SOFT
    SOFT --> SKB[构建sk_buff<br/>向上传递]
    SKB --> PRO[协议栈逐层解包<br/>TCP/IP]
    PRO --> APPSK[放入socket接收队列<br/>唤醒应用进程]
    APPSK --> APP
    DM --> NAPI{NAPI机制}:::decision
    NAPI -->|低负载 轮询模式| POL[中断+轮询结合<br/>减少中断风暴]
    NAPI -->|高负载| BATCH[批量处理包<br/>提升吞吐]:::success
    POL --> TUNE[调优: RPS/RFS/XPS<br/>多队列负载均衡]
    {_common_styles()}
```"""


# ============== Linux虚拟内存 ==============
def tpl_linux_vm(meta):
    return """```mermaid
flowchart TD
    P([进程访问虚拟地址]):::start --> MMU[MMU单元查页表]
    MMU --> VMA[内核VMA虚拟内存区域<br/>代码段/数据段/堆/栈]
    VMA --> PGD[遍历4级页表<br/>PGD→PUD→PMD→PTE]
    PGD --> PRE{页是否在内存?}:::decision
    PRE -->|在内存 命中| PHY[返回物理地址<br/>访问RAM]:::success
    PRE -->|不在内存 P=0| PF[触发缺页异常<br/>Page Fault]
    PF --> TY{缺页类型}:::decision
    TY -->|匿名页 首次分配| ANON[物理页框分配<br/>零页填充]:::async
    TY -->|文件页| MAP[mmap文件映射<br/>从磁盘加载]
    TY -->|COW写时复制| COW[复制页框<br/>父子分离]
    ANON --> SWP{内存压力?}:::decision
    MAP --> SWP
    SWP -->|紧张| KSWAPD[kswapd内核线程<br/>LRU换出冷页到Swap]:::error
    SWP -->|空闲| INS[更新PTE指向新页框]
    KSWAPD --> INS
    COW --> INS
    INS --> PHY
    {_common_styles()}
```"""


# ============== OSI 七层 ==============
def tpl_osi(meta):
    return """```mermaid
flowchart TD
    APP([用户数据 Data]):::start --> L7[/应用层 HTTP FTP DNS SMTP<br/>为应用程序提供网络服务/]
    L7 --> L6[/表示层 加解密/编码/压缩<br/>SSL/TLS JPEG ASCII/]
    L6 --> L5[/会话层 建立/管理/终止会话<br/>RPC NetBIOS/]
    L5 --> L4[/传输层 TCP UDP<br/>端到端可靠传输/]
    L4 --> SEG[数据分段 Segment<br/>加TCP头含端口号]
    SEG --> L3[/网络层 IP ICMP<br/>路由选择与寻址/]
    L3 --> PKT[数据分组 Packet<br/>加IP头含IP地址]
    PKT --> L2[/数据链路层 MAC/ARP<br/>帧封装与MAC寻址/]
    L2 --> FRA[数据帧 Frame<br/>加帧头含MAC地址]
    FRA --> L1[/物理层 比特传输<br/>电信号/光纤/无线电/]
    L1 --> BIT[比特流 Bit Stream<br/>通过网卡发送]
    BIT --> RECV([接收方逆过程<br/>逐层解封装]):::success
    L4 -.->|TCP/IP四层合并| MERG[应用层 = 5/6/7<br/>传输层/网际层/网络接口]
    MERG --> TCP[(实际工程中<br/>TCP/IP模型更常用)]:::storage
    {_common_styles()}
```"""


# ============== URL和URI ==============
def tpl_url_uri(meta):
    return """```mermaid
flowchart TD
    ID([资源标识问题]):::start --> URI[URI 统一资源标识符<br/>定位/命名 两种形式]
    URI --> URL[URL 统一资源定位符<br/>强调"在哪里"]
    URI --> URN[URN 统一资源名称<br/>强调"叫什么"]
    URL --> SC[scheme协议: http/https]
    SC --> AU[authority: //user:pass@host:port]
    AU --> PT[path路径 /api/user]
    PT --> QR[query: ?name=abc&age=18]
    QR --> FR[fragment: #section1<br/>仅浏览器本地使用]
    URN --> URNEX[urn:isbn:0451450523<br/>永久标识不依赖位置]
    QR --> ENC{特殊字符处理}:::decision
    ENC -->|未编码| BUG[& / = / 空格<br/>导致解析歧义]:::error
    ENC -->|URL编码| SAFE[百分号编码%20<br/>空格→%20 中文→UTF8]
    SAFE --> REQ([浏览器构造HTTP请求]):::success
    {_common_styles()}
```"""


# ============== finally ==============
def tpl_finally(meta):
    return """```mermaid
flowchart TD
    TRY([进入try块]):::start --> CODE[执行try内业务代码]
    CODE --> CHK{是否抛出异常?}:::decision
    CHK -->|无异常| FIN1[跳过catch<br/>直接执行finally]
    CHK -->|抛出Throwable| MT{匹配catch类型?}:::decision
    MT -->|是| CAT[执行对应catch块<br/>处理异常]
    MT -->|否 未捕获| PROP[异常向上抛出<br/>finally仍会执行]
    CAT --> FIN2[执行finally块]
    PROP --> FIN2
    FIN1 --> RET{finally含return?}:::decision
    FIN2 --> RET
    RET -->|是 覆盖try/catch的return| OVR[finally的return<br/>覆盖之前的返回值]:::error
    RET -->|否 普通语句| NORM[finally执行完毕<br/>原return生效]
    OVR --> CLR[资源关闭/锁释放<br/>建议放finally]
    NORM --> CLR
    CLR --> SYSTEM{JVM退出情况?}:::decision
    SYSTEM -->|System.exit / 进程崩溃| SKIP[finally不执行<br/>JVM直接终止]:::async
    SYSTEM -->|线程中断/守护线程结束| SKIP2[可能不执行]
    SYSTEM -->|正常| DONE([方法返回]):::success
    {_common_styles()}
```"""


# ============== 半连接队列 ==============
def tpl_syn_queue(meta):
    return """```mermaid
flowchart TD
    C1([客户端A: 发送SYN]):::start --> S1[服务端收到SYN]
    S1 --> Q1[(SYN队列 半连接队列<br/>记录未完成连接)]
    Q1 --> R1[服务端回SYN+ACK<br/>进入SYN_RCVD]
    R1 --> W1[等待客户端ACK<br/>超时重传SYN+ACK]
    C2([客户端B: 发送SYN]):::start --> S2[服务端收到SYN]
    S2 --> Q1
    W1 --> AK{是否收到ACK?}:::decision
    AK -->|是| MOV[从SYN队列移除<br/>加入ACCEPT队列 全连接]
    AK -->|否 超时5次重传| DROP[丢弃半连接<br/>释放资源]:::error
    MOV --> ACC[(ACCEPT队列<br/>等待accept系统调用)]
    ACC --> ACPT[应用调用accept<br/>取出连接]
    ACPT --> EST([连接建立ESTABLISHED<br/>开始传输]):::success
    Q1 -.->|SYN Flood攻击| ATK[恶意客户端不发ACK<br/>填满队列拒绝服务]:::error
    ATK --> DEF{防御手段}:::decision
    DEF --> SYN_C[Syn Cookies<br/>不分配资源 算法验证]
    DEF --> RED[减小syn_backlog+<br/>增大tcp_max_syn_backlog]
    DEF --> FW[防火墙限速]
    {_common_styles()}
```"""


# ============== 单例模式应用场景 ==============
def tpl_singleton(meta):
    return """```mermaid
flowchart TD
    NEED([需要单例的场景]):::start --> CHO{选哪种实现?}:::decision
    CHO -->|饿汉式| EH[类加载时初始化<br/>static final]
    CHO -->|懒汉式| LZ[首次调用getInstance<br/>才初始化]
    CHO -->|双重检查| DCL[volatile + synchronized<br/>推荐]
    CHO -->|静态内部类| IC[Holder模式<br/>类加载机制保证线程安全]
    CHO -->|枚举| ENM[enum天然单例<br/>防反射防序列化]
    EH --> USE{资源是否重?}:::decision
    USE -->|轻量可提前| AP1[配置/日志/连接池<br/>启动即用]:::success
    USE -->|重量级 IO/DB| BAD1[启动慢 内存浪费<br/>改用懒加载]:::error
    LZ --> SYN{线程安全?}:::decision
    SYN -->|是 加synchronized| SAFE1[每次调用加锁<br/>性能差]:::error
    SYN -->|否| RISK[多线程下创建多个实例<br/>违反单例]:::error
    DCL --> APP1[延迟加载+高性能<br/>JDK5+ 推荐]
    IC --> APP2[延迟加载+无锁<br/>最佳实践]
    ENM --> APP3[Effective Java推荐<br/>最简洁安全]
    APP1 --> SC[典型应用<br/>Runtime/Logger/DataSource]:::success
    APP2 --> SC
    APP3 --> SC
    {_common_styles()}
```"""


# ============== 异常分类 ==============
def tpl_exception(meta):
    return """```mermaid
flowchart TD
    ROOT([Throwable 根类]):::start --> ERR[Error 错误<br/>JVM级 程序无法处理]
    ROOT --> EXC[Exception 异常<br/>程序可处理]
    ERR --> OOM[OutOfMemoryError<br/>内存溢出]
    ERR --> SOF[StackOverflowError<br/>栈溢出/深递归]
    ERR --> VMERR[VirtualMachineError<br/>JVM崩溃]
    EXC --> RNT[RuntimeException 运行时异常<br/>非受检 unchecked]
    EXC --> CHK[其他Exception 受检<br/>checked 编译期强制]
    RNT --> NPE[NullPointerException 空指针]
    RNT --> IDX[IndexOutOfBoundsException 越界]
    RNT --> CLS[ClassNotFoundException 类找不到]
    RNT --> CAST[ClassCastException 类型转换]
    RNT --> ARITH[ArithmeticException 算术异常]
    CHK --> IOE[IOException IO异常]
    CHK --> SQLE[SQLException 数据库异常]
    CHK --> FILE[FileNotFoundException]
    NPE --> HAND{处理策略}:::decision
    IOE --> HAND
    HAND -->|受检异常| TRY[必须try-catch或throws<br/>编译期强制]
    HAND -->|运行时异常| COD[编程时主动防御<br/>前置判空/校验]:::async
    HAND -->|自定义异常| CST[extends RuntimeException/Exception<br/>携带业务码]
    TRY --> GLB[全局异常处理器<br/>@ControllerAdvice]:::success
    COD --> GLB
    {_common_styles()}
```"""


# ============== 排序二叉树/BST ==============
def tpl_bst(meta):
    return """```mermaid
flowchart TD
    INS([插入新节点]):::start --> CMP[与根节点比较]
    CMP --> DEC{新值 vs 当前节点}:::decision
    DEC -->|小于| LEFT[进入左子树]
    DEC -->|大于| RIGHT[进入右子树]
    DEC -->|等于 不允许重复| DUP[忽略或更新<br/>避免重复键]:::error
    LEFT --> CHL{左子树为空?}:::decision
    RIGHT --> CHR{右子树为空?}:::decision
    CHL -->|是| PL[作为左孩子插入]
    CHL -->|否| CMP
    CHR -->|是| PR[作为右孩子插入]
    CHR -->|否| CMP
    PL --> BAL{插入后是否失衡?}:::decision
    PR --> BAL
    BAL -->|是 AVL/红黑树| ROT[触发旋转LL/RR/LR/RL<br/>或变色保持平衡]:::async
    BAL -->|否 普通BST| KEEP[无需调整]
    ROT --> OK([树保持有序]):::success
    KEEP --> OK
    OK --> SEARCH[中序遍历得有序序列<br/>支持范围查找]
    SEARCH --> PERF{性能}:::decision
    PERF -->|平衡树| OLOGN[查找/插入 O log n]
    PERF -->|退化成链表| ON[最坏O n 需自平衡]:::error
    {_common_styles()}
```"""


# ============== 编译系统 ==============
def tpl_compile(meta):
    return """```mermaid
flowchart TD
    SRC([Hello.java 源文件]):::start --> LEX[词法分析 Lexer<br/>源码→Token流]
    LEX --> PARSE[语法分析 Parser<br/>构建AST抽象语法树]
    PARSE --> SEMA[语义分析<br/>类型检查/符号表/注解处理]
    SEMA --> CHK{编译错误?}:::decision
    CHK -->|是| ERR[报错终止 javac退出]:::error
    CHK -->|否| GEN[生成字节码 .class]
    GEN --> CLS[(Hello.class<br/>JVM字节码文件)]:::storage
    CLS --> LOAD[类加载器ClassLoader<br/>加载/链接/初始化]
    LOAD --> VERIFY[字节码验证<br/>确保安全合法]
    VERIFY --> PREP[准备阶段<br/>静态变量分配默认值]
    PREP --> INIT[执行&lt;clinit&gt;<br/>静态变量赋值+静态块]
    INIT --> JIT{执行模式}:::decision
    JIT -->|解释执行| INTERP[逐条解释字节码<br/>启动快但慢]
    JIT -->|JIT编译热点| HOT[热点探测→编译本地码<br/>优化内联/逃逸分析]:::async
    INTERP --> RUN([JVM运行时]):::success
    HOT --> RUN
    {_common_styles()}
```"""


# ============== GET vs POST ==============
def tpl_get_post(meta):
    return """```mermaid
flowchart TD
    HTTP([HTTP请求构造]):::start --> CHO{方法选择}:::decision
    CHO -->|GET| GET[GET: 查询资源<br/>幂等 安全]
    CHO -->|POST| POST[POST: 提交数据<br/>非幂等 创建资源]
    GET --> URL1[参数拼在URL后<br/>?key=value&...]
    URL1 --> CACHE[可被浏览器/CDN缓存<br/>可加入书签]
    CACHE --> LOG[参数记录在访问日志<br/>敏感信息泄露风险]:::error
    GET --> LEN1{长度限制}:::decision
    LEN1 -->|浏览器/服务器有限制| LIMIT1[约2KB~8KB<br/>不宜大数据]
    POST --> BODY[参数放Request Body<br/>支持任意格式]
    BODY --> TYPE[Content-Type多样化<br/>form/json/multipart]
    TYPE --> SECURE[不在URL日志<br/>相对安全但仍需HTTPS]
    POST --> LEN2{长度限制}:::decision
    LEN2 -->|理论无限制| BIG[适合大文件上传<br/>服务端可配maxPostSize]
    LIMIT1 --> SEMANTIC{语义区别}:::decision
    BIG --> SEMANTIC
    SEMANTIC --> GET_IDE[GET幂等: 多次执行结果相同<br/>适合查询]
    SEMANTIC --> POST_NONIDE[POST非幂等<br/>每次创建新资源]
    GET_IDE --> USE1[搜索/分页/跳转]:::success
    POST_NONIDE --> USE2[登录/下单/支付]:::success
    {_common_styles()}
```"""


# ============== 程序执行流程 ==============
def tpl_program_flow(meta):
    return """```mermaid
flowchart TD
    SRC([源代码 .java/.c]):::start --> CMP[编译器处理]
    CMP --> CHK{编译通过?}:::decision
    CHK -->|否 语法/类型错误| ERR[编译失败 修复后重试]:::error
    CHK -->|是| BIN[目标文件<br/>JVM字节码 / 机器码]
    BIN --> LD[加载器载入内存]
    LD --> SEGC[代码段.text 只读]
    LD --> SEGD[数据段.data/.bss<br/>全局/静态变量]
    LD --> OS[操作系统创建进程<br/>分配虚拟地址空间]
    OS --> PC[初始化PC寄存器<br/>指向main入口]
    PC --> FETCH[取指令 Fetch]
    FETCH --> DEC2[解码 Decode]
    DEC2 --> EXEC[执行 Execute]
    EXEC --> WB[写回 WriteBack<br/>更新寄存器]
    WB --> STK{是否栈帧?}:::decision
    STK -->|方法调用| PUSH[压栈帧 局部变量/操作数栈]
    STK -->|返回| POP[弹栈 返回上层]
    PUSH --> NXT{下一条指令?}:::decision
    POP --> NXT
    NXT --> JMP{跳转/循环/异常?}:::decision
    JMP -->|是 修改PC| FETCH
    JMP -->|否 PC自增| FETCH
    FETCH --> EXIT{进程结束?}:::decision
    EXIT -->|是| DONE([回收资源 退出]):::success
    EXIT -->|否 继续| FETCH
    {_common_styles()}
```"""


# ============== 页面置换 LRU/FIFO ==============
def tpl_page_replace(meta):
    return """```mermaid
flowchart TD
    REF([CPU访问页P]):::start --> TLB[查TLB/页表]
    TLB --> H{P在内存?}:::decision
    H -->|是 命中| UPD[更新访问位/时间<br/>LRU更新链表]:::success
    H -->|否 缺页| PF[触发Page Fault]
    PF --> FREE{有空闲页框?}:::decision
    FREE -->|是| LOAD1[直接加载页P到空闲框]
    FREE -->|否| ALG{选择置换算法}:::decision
    ALG -->|FIFO| FIFO[队列先进先出<br/>淘汰最早进入的页]
    ALG -->|LRU| LRU[淘汰最久未访问<br/>链表/计数器]
    ALG -->|LFU| LFU[淘汰访问次数最少]
    ALG -->|Clock 时钟| CLOCK[循环扫描访问位<br/>二次机会]:::async
    ALG -->|OPT 最佳| OPT[理论最优 不可实现<br/>作为对比基准]
    FIFO --> VCT{Belady异常?}:::decision
    VCT -->|是 FIFO特有| BAD[增加页框 缺页率反升]:::error
    VCT -->|否 LRU无此问题| OK[性能稳定]
    LRU --> EVICT[选出牺牲页]
    CLOCK --> EVICT
    LFU --> EVICT
    EVICT --> MOD{牺牲页是否修改?}:::decision
    MOD -->|是 dirty=1| WRITE[写回磁盘swap<br/>额外IO开销]:::async
    MOD -->|否 dirty=0| DISC[直接丢弃无需IO]
    WRITE --> LOAD2[加载页P到腾出的页框]
    DISC --> LOAD2
    LOAD1 --> ACC([访问完成]):::success
    LOAD2 --> ACC
    UPD --> ACC
    {_common_styles()}
```"""


# ============== 多态 ==============
def tpl_polymorphism(meta):
    return """```mermaid
flowchart TD
    CLS([定义父类Animal<br/>方法speak]):::start --> SUB1[子类Dog extends Animal<br/>override speak: 汪汪]
    CLS --> SUB2[子类Cat extends Animal<br/>override speak: 喵喵]
    SUB1 --> REF1[父类引用指向子类对象<br/>Animal a = new Dog]
    SUB2 --> REF2[Animal b = new Cat]
    REF1 --> CALL[a.speak 方法调用]
    REF2 --> CALL
    CALL --> BIND{绑定方式}:::decision
    BIND -->|编译期 静态分派| STATIC[重载overload<br/>按引用类型选择]
    BIND -->|运行期 动态分派| DYN[重写override<br/>按实际对象类型选择]:::async
    STATIC --> OVLD[方法签名不同<br/>参数列表决定]
    DYN --> VTBL[查对象头中的虚方法表vtable<br/>定位实际子类方法]:::storage
    VTBL --> INVK[调用Dog.speak 输出汪汪]
    OVLD --> RES([结果返回]):::success
    INVK --> RES
    CALL --> TRIPLE{多态三要素}:::decision
    TRIPLE -->|继承/实现| T1[extends/implements]
    TRIPLE -->|方法重写| T2[@Override]
    TRIPLE -->|父类引用指向子类| T3[向上转型upcast]
    T1 --> APP[应用: 策略模式/模板方法/集合框架<br/>List list = new ArrayList]
    {_common_styles()}
```"""


# ============== 进程调度算法 ==============
def tpl_schedule(meta):
    return """```mermaid
flowchart TD
    RQ([就绪队列中的进程]):::start --> SCHED[调度器Scheduler<br/>CPU调度]
    SCHED --> ALG{调度算法}:::decision
    ALG -->|FCFS 先来先服务| FCFS[按到达顺序执行<br/>简单但短作业等待长]
    ALG -->|SJF 短作业优先| SJF[优先短作业<br/>平均等待最优 但可能饿生长作业]:::error
    ALG -->|RR 时间片轮转| RR[每个进程分时间片<br/>公平 但切换开销大]
    ALG -->|优先级调度| PRIO[静态/动态优先级<br/>低优先级可能饥饿]
    ALG -->|多级反馈队列 MLFQ| MLFQ[多个队列不同时间片<br/>动态调整 综合]:::async
    FCFS --> CW{是否阻塞/时间片到?}:::decision
    SJF --> CW
    RR --> CW
    PRIO --> CW
    MLFQ --> CW
    CW -->|时间片到/主动让出| YIELD[挂起 回就绪队列]
    CW -->|阻塞IO/等待| BLOCK[进入阻塞队列<br/>等待事件]
    CW -->|正常结束| TERM[释放资源 退出]:::success
    YIELD --> RQ
    BLOCK --> EVT{事件就绪?}:::decision
    EVT -->|是 IO完成| RQ
    EVT -->|否 继续等待| BLOCK
    MLFQ --> PROMO{频繁让出CPU?}:::decision
    PROMO -->|是 交互型| UP[提升优先级<br/>响应快]
    PROMO -->|否 CPU密集| DOWN[降低优先级<br/>避免独占]
    {_common_styles()}
```"""


# ============== Cookie ==============
def tpl_cookie(meta):
    return """```mermaid
flowchart TD
    R1([首次请求<br/>无Cookie]):::start --> SRV[服务端处理请求<br/>创建会话]
    SRV --> GEN[生成Session/用户数据<br/>生成Set-Cookie响应头]
    GEN --> SC[Set-Cookie: JSESSIONID=abc123;<br/>Path=/; HttpOnly; Secure; SameSite=Lax]
    SC --> R2([响应返回浏览器])
    R2 --> STORE[浏览器存储Cookie<br/>按domain/path组织]
    STORE --> CHK{是否过期?}:::decision
    CHK -->|Max-Age/Expires到期| DEL[删除Cookie]
    CHK -->|未过期 持久/会话级| KEEP[保留Cookie]
    KEEP --> R3([第二次请求同域]):::start
    R3 --> SEND[自动携带Cookie请求头<br/>Cookie: JSESSIONID=abc123]
    SEND --> SRV2[服务端读取Cookie<br/>识别Session恢复状态]
    SRV2 --> BIZ[执行业务逻辑<br/>无需重复登录]
    SEND --> SEC{安全风险}:::decision
    SEC -->|XSS窃取| XSS[脚本读取Cookie<br/>HttpOnly阻止JS访问]:::error
    SEC -->|CSRF伪造| CSRF[跨站请求携带Cookie<br/>SameSite=Strict防御]:::error
    SEC -->|网络嗅探| SNIF[明文传输<br/>Secure仅HTTPS发送]
    {_common_styles()}
```"""


# ============== DelayQueue ==============
def tpl_delay_queue(meta):
    return """```mermaid
flowchart TD
    TASK([延迟任务对象<br/>实现Delayed接口]):::start --> PUT[put 入队]
    PUT --> CMP[按getDelay排序<br/>PriorityQueue最小堆]
    CMP --> HEAP[(底层堆结构<br/>按到期时间排序)]:::storage
    HEAP --> TH[take线程检查队首]
    TH --> DEC{getDelay<=0?}:::decision
    DEC -->|否 未到期| WAIT[available.awaitNanos<br/>阻塞剩余时间]:::async
    DEC -->|是 到期| POLL[出队返回任务]
    WAIT --> WAKE[到期/有新元素signal<br/>重新检查]
    WAKE --> TH
    POLL --> EXEC[执行定时任务<br/>订单取消/缓存失效/消息重试]
    EXEC --> NXT{还有任务?}:::decision
    NXT -->|是| TH
    NXT -->|否| IDLE([线程等待]):::success
    {_common_styles()}
```"""


# ============== HTTP原理 ==============
def tpl_http_principle(meta):
    return """```mermaid
flowchart TD
    U([用户输入URL]):::start --> DNS[DNS解析获取IP]
    DNS --> TCP[TCP三次握手建立连接]
    TCP --> TLS{是否HTTPS?}:::decision
    TLS -->|是| TLSHK[TLS握手<br/>证书验证+密钥协商]:::async
    TLS -->|否| REQ[构造HTTP请求]
    TLSHK --> REQ[加密通道建立后构造请求]
    REQ --> SEND[请求行+请求头+空行+请求体<br/>GET /path HTTP/1.1<br/>Host: www.x.com]
    SEND --> NET[(网络传输 TCP/IP栈)]:::storage
    NET --> SRV[服务端Web容器接收]
    SRV --> PARSE[解析请求行/头/体]
    PARSE --> ROUTE[路由分发<br/>Filter链→Servlet/Controller]
    ROUTE --> BIZ[业务处理<br/>查DB/调RPC/组装数据]
    BIZ --> RESP[构造HTTP响应<br/>状态行+响应头+响应体<br/>HTTP/1.1 200 OK]
    RESP --> CLOSE{是否keep-alive?}:::decision
    CLOSE -->|是| KEEP[保持连接 复用]
    CLOSE -->|否 Connection: close| FIN[四次挥手关闭]
    KEEP --> BROWSER[浏览器解析HTML]
    FIN --> BROWSER
    BROWSER --> RENDER[构建DOM/CSSOM→渲染树→布局→绘制]
    RENDER --> SHOW([页面展示]):::success
    {_common_styles()}
```"""


# ============== Java NIO Selector ==============
def tpl_selector(meta):
    return """```mermaid
flowchart TD
    CH([创建Selector.open]):::start --> REG[Channel注册到Selector<br/>register + SelectionKey]
    REG --> IT[(Selector维护<br/>SelectionKey集合)]:::storage
    IT --> INT[设置感兴趣的事件<br/>OP_READ/OP_WRITE/OP_ACCEPT/OP_CONNECT]
    INT --> LOOP[selector.select 阻塞等待]
    LOOP --> EVT{有事件就绪?}:::decision
    EVT -->|否 超时返回0| LOOP
    EVT -->|是| READY[返回就绪的SelectionKey集合]
    READY --> ITER[遍历就绪Keys]
    ITER --> T{事件类型}:::decision
    T -->|OP_ACCEPT 接受连接| ACC[ServerSocketChannel.accept<br/>注册新SocketChannel]
    T -->|OP_READ 可读| RD[SocketChannel.read<br/>读到Buffer]
    T -->|OP_WRITE 可写| WR[SocketChannel.write<br/>从Buffer写]
    T -->|OP_CONNECT 连接完成| CNN[完成连接握手]
    ACC --> RMV[移除已处理Key<br/>避免重复]
    RD --> RMV
    WR --> RMV
    CNN --> RMV
    RMV --> LOOP
    RD --> BUF[(Buffer: position/limit/capacity<br/>flip/clear切换读写)]:::storage
    {_common_styles()}
```"""


# ============== Java RMI ==============
def tpl_rmi(meta):
    return """```mermaid
flowchart TD
    SRV([服务端发布远程对象]):::start --> EXP[UnicastRemoteObject.exportObject<br/>生成Stub代理]
    EXP --> REG2[RMI Registry注册表<br/>bind name→Stub]
    REG2 --> WAT[等待客户端调用]
    CLT([客户端 lookup]):::start --> LOOK[Naming.lookup 查Registry]
    LOOK --> STUB[获得Stub代理对象]
    STUB --> INV[调用Stub方法<br/>序列化参数]
    INV --> NET[(网络传输 JRMP协议<br/>默认端口1099)]:::storage
    NET --> SKEL[服务端Skeleton<br/>反序列化参数]
    SKEL --> REAL[调用真实远程对象方法]
    REAL --> RESULT[返回结果]
    RESULT --> SER[序列化返回值]
    SER --> NET2[(网络回传)]:::storage
    NET2 --> STUB2[Stub反序列化结果]
    STUB2 --> CLT2([客户端拿到返回值]):::success
    EXP --> GC[DGC分布式GC<br/>租约机制防对象回收]
    {_common_styles()}
```"""


# ============== Java集合框架 ==============
def tpl_collection(meta):
    return """```mermaid
flowchart TD
    COL([Collection接口]):::start --> LST[List 有序可重复]
    COL --> SET[Set 无序不可重复]
    COL --> QUE[Queue 队列 FIFO]
    LST --> AL[ArrayList<br/>数组 查询快]
    LST --> LL[LinkedList<br/>双向链表 增删快]
    LST --> VEC[Vector<br/>线程安全synchronized 已淘汰]
    SET --> HS[HashSet<br/>基于HashMap]
    SET --> LTS[LinkedHashSet<br/>保留插入顺序]
    SET --> TS[TreeSet<br/>红黑树有序]
    QUE --> PQ[PriorityQueue<br/>堆 优先级]
    QUE --> DQ[Deque 双端队列]
    DQ --> ARR[ArrayDeque<br/>数组实现 推荐]
    DQ --> LL2[LinkedList<br/>也实现Deque]
    MAP([Map接口 独立体系]):::start --> HM[HashMap<br/>数组+链表+红黑树]
    MAP --> LHM[LinkedHashMap<br/>维护插入/LRU顺序]
    MAP --> TM[TreeMap<br/>红黑树按键排序]
    MAP --> HTM[Hashtable<br/>古老线程安全 已淘汰]
    MAP --> CHM[ConcurrentHashMap<br/>分段锁/CAS 高并发推荐]:::async
    HM --> CHO{选型决策}:::decision
    CHO -->|线程不安全 单线程| APP1[默认选HashMap]
    CHO -->|高并发| APP2[ConcurrentHashMap]:::success
    CHO -->|需要排序| APP3[TreeMap]
    CHO -->|保持插入顺序| APP4[LinkedHashMap]
    {_common_styles()}
```"""


# ============== List vs Map ==============
def tpl_list_map(meta):
    return """```mermaid
flowchart LR
    subgraph LIST [List体系]
        L0([List特征]):::start
        L0 --> L1[有序<br/>按插入顺序]
        L0 --> L2[可重复<br/>允许相同元素]
        L0 --> L3[索引访问<br/>get index]
        L0 --> L4[允许null<br/>多个null]
        L1 --> LA[ArrayList 数组]
        L2 --> LB[LinkedList 链表]
    end
    subgraph MAP [Map体系]
        M0([Map特征])
        M0 --> M1[键值对<br/>key-value Entry]
        M0 --> M2[key唯一<br/>value可重复]
        M0 --> M3[按key查找<br/>O1 哈希]
        M0 --> M4[key最多一个null<br/>HashMap允许]
        M1 --> MA[HashMap]
        M2 --> MB[TreeMap]
        M3 --> MC[ConcurrentHashMap]
    end
    LA --> CMP{本质区别}:::decision
    MA --> CMP
    CMP -->|存储模型| DIFF1[List单列元素<br/>Map双列映射]
    CMP -->|查询复杂度| DIFF2[List O(n)按值查<br/>Map O(1)按键查]
    CMP -->|迭代方式| DIFF3[List: for+索引/迭代器<br/>Map: entrySet/keySet]
    DIFF2 --> USE{应用场景}:::decision
    USE -->|顺序集合| USEL[购物车/排行榜/历史记录]
    USE -->|KV映射| USEM[用户ID→对象/缓存/字典]
    {_common_styles()}
```"""


# ============== Protocol Buffer ==============
def tpl_protobuf(meta):
    return """```mermaid
flowchart TD
    PROTO([.proto定义文件<br/>message结构]):::start --> CMP[protoc编译器]
    CMP --> GEN[生成各语言代码<br/>Java/Python/C++]
    CMP --> CHK{编译检查}:::decision
    CHK -->|字段编号冲突| ERR[编译失败]:::error
    CHK -->|合法| DESC[生成二进制描述符]
    GEN --> OBJ[运行时构造对象<br/>Builder模式]
    OBJ --> SER[序列化 toByteArray]
    SER --> ENC[字段按编号编码<br/>varint + length-delimited]
    ENC --> CMPCT[(紧凑二进制<br/>省空间 反序列化快)]:::storage
    CMPCT --> NET[(网络/RPC传输)]:::storage
    NET --> DES[反序列化 parseFrom]
    DES --> READ[按字段编号读取<br/>未知字段跳过/保留]
    READ --> OBJ2[重建对象]
    OBJ2 --> APP([业务使用]):::success
    ENC --> ADV{优势}:::decision
    ADV -->|1| S1[体积小 比JSON小3-10倍]
    ADV -->|2| S2[解析快 无字符串解析]
    ADV -->|3| S3[强类型 编译期检查]
    ADV -->|4| S4[前向/后向兼容<br/>新增字段不影响旧版本]:::async
    ADV -->|劣势| W1[不可读 二进制需工具<br/>schema维护成本]
    {_common_styles()}
```"""


# ============== RSA ==============
def tpl_rsa(meta):
    return """```mermaid
flowchart TD
    GEN([密钥生成]):::start --> P[选两个大素数 p, q]
    P --> N[n = p × q<br/>模数公开]
    N --> PHI[φn = p-1 × q-1<br/>欧拉函数]
    PHI --> E[选公钥指数 e<br/>与φn互质 常用65537]
    E --> D[计算私钥 d<br/>d × e ≡ 1 mod φn]
    D --> PK[公钥 e, n 公开分发]
    D --> SK[私钥 d, n 严格保密]
    PK --> ENC([加密过程]):::start
    ENC --> MSG[明文M 转为整数m<n]
    MSG --> C[m^e mod n = c<br/>密文c]
    C --> NET[(传输密文)]:::storage
    NET --> DEC([解密过程]):::start
    DEC --> DEC2[c^d mod n = m<br/>恢复明文m]
    DEC2 --> RTN([得到原始M]):::success
    PK --> SIGN([签名过程 用私钥]):::async
    SIGN --> SH[对消息哈希]
    SH --> SD[哈希^d mod n = 签名]
    SD --> VF[接收方用公钥验证<br/>签名^e mod n 对比哈希]
    {_common_styles()}
```"""


# ============== Redis数据类型应用场景 ==============
def tpl_redis_type(meta):
    return """```mermaid
flowchart TD
    R([Redis五大数据类型]):::start --> STR[String 字符串]
    R --> HS2[Hash 哈希表]
    R --> LST[List 列表]
    R --> SET2[Set 集合]
    R --> ZSET[ZSet 有序集合]
    STR --> STR1[单值缓存<br/>验证码/商品库存]
    STR --> STR2[对象JSON缓存<br/>用户信息]
    STR --> STR3[计数器 incr<br/>点赞数/阅读量]:::async
    STR --> STR4[分布式锁<br/>setnx+expire]
    STR --> STR5[Bitmap签到<br/>底层就是String]
    HS2 --> HS1[对象字段存储<br/>用户属性 商品详情]
    HS2 --> HS2A[购物车<br/>userId→{skuId:num}]
    LST --> L1[消息队列<br/>lpush+brpop]
    LST --> L2[最新N条<br/>朋友圈/文章列表]
    LST --> L3[操作日志栈]
    SET2 --> S1[标签/共同好友<br/>sinter交集]
    SET2 --> S2[去重<br/>UV统计 抽奖 srandmember]
    SET2 --> S3[黑名单/白名单]
    ZSET --> Z1[排行榜<br/>score排序 游戏/热搜]
    ZSET --> Z2[延时队列<br/>score=到期时间戳]:::async
    ZSET --> Z3[范围查找<br/>滑动窗口限流]
    {_common_styles()}
```"""


# ============== String存储原理 ==============
def tpl_redis_string(meta):
    return """```mermaid
flowchart TD
    SET([执行SET key value]):::start --> PARSE[解析命令]
    PARSE --> LOOK[全局dict查找key<br/>redisDb.dict]
    LOOK --> EX{key存在?}:::decision
    EX -->|是| UPD[更新SDS值<br/>释放旧对象]
    EX -->|否| ADD[新增dictEntry<br/>指向redisObject]
    UPD --> OBJ
    ADD --> OBJ[redisObject结构]
    OBJ --> TYP{type判断}:::decision
    TYP -->|OBJ_STRING| EN{encoding判断}:::decision
    EN -->|短整数 ≤LONG_MAX| INT[embstr/int<br/>直接存long]:::storage
    EN -->|字符串 ≤44字节| EMB[embstr<br/>redisObject+SDS连续内存]
    EN -->|字符串 >44字节| RAW[raw<br/>redisObject + 独立SDS指针]
    INT --> SDS[SDS动态字符串<br/>header+len+free+buf]
    EMB --> SDS
    RAW --> SDS
    SDS --> BEN{SDS优势}:::decision
    BEN -->|1| B1[O1 获取长度<br/>无需遍历]
    BEN -->|2| B2[二进制安全<br/>可存\\0]
    BEN -->|3| B3[空间预分配<br/>减少realloc]
    BEN -->|4| B4[惰性释放<br/>缩容不立即释放]
    {_common_styles()}
```"""


# ============== TCP Keepalive vs HTTP Keep-Alive ==============
def tpl_keepalive_compare(meta):
    return """```mermaid
flowchart TD
    Q([两者混淆对比]):::start --> TK[TCP Keepalive<br/>传输层]
    Q --> HK[HTTP Keep-Alive<br/>应用层]
    TK --> TK1[探测对端是否存活<br/>防止半开连接]
    TK --> TK2[默认7200s空闲后<br/>每75s探测 共9次]
    TK --> TK3[系统级参数<br/>tcp_keepalive_time]
    TK2 --> TK4{对端无响应?}:::decision
    TK4 -->|是| DEAD[判定对端死亡<br/>关闭连接]:::error
    TK4 -->|否| ALIVE[连接保活<br/>避免NAT超时]:::success
    HK --> HK1[复用TCP连接<br/>避免每次握手]
    HK --> HK2[请求头Connection: keep-alive<br/>默认开启 HTTP/1.1]
    HK --> HK3[服务端设置timeout<br/>超时主动关闭]
    HK2 --> HK4{是否继续请求?}:::decision
    HK4 -->|是| REUSE[复用连接发新请求<br/>省RTT]:::async
    HK4 -->|否 Connection: close| END[关闭连接]
    TK1 --> REL{关系}:::decision
    HK1 --> REL
    REL -->|独立| IND[两者互不依赖<br/>可单独开启]
    REL -->|互补| COMP[HTTP层复用业务<br/>TCP层保活底层]
    {_common_styles()}
```"""


# ============== TCP/IP原理 ==============
def tpl_tcp_ip(meta):
    return """```mermaid
flowchart TD
    APP([应用层数据]):::start --> SEG[加TCP/UDP头<br/>Segment段]
    SEG --> PKT[加IP头<br/>Packet包 含源/目的IP]
    PKT --> FRM[加帧头/帧尾<br/>Frame帧 含MAC地址]
    FRM --> BIT[转为比特流<br/>物理层传输]
    BIT --> NIC1[源网卡发送]
    NIC1 --> ROUTE{路由转发}:::decision
    ROUTE -->|同网段| ARP[ARP广播查MAC<br/>直接送达]
    ROUTE -->|跨网段| GW[发给默认网关<br/>逐跳路由]
    GW --> HOP[每个路由器<br/>查路由表 TTL-1]
    HOP --> TTL{TTL=0?}:::decision
    TTL -->|是| DROP[丢弃包 ICMP超时]:::error
    TTL -->|否| CONT[继续转发]
    CONT --> DST[到达目的网段]
    ARP --> DST
    DST --> NIC2[目的网卡接收]
    NIC2 --> LIFT[逐层解封装]
    LIFT --> APP2[应用层收到数据]:::success
    PKT --> FRAG{包大于MTU?}:::decision
    FRAG -->|是 1500字节| FG[IP分片 fragmentation<br/>目标重组]
    FRAG -->|否| PASS[直接封装]
    {_common_styles()}
```"""


# ============== TCP保活机制 ==============
def tpl_tcp_keepalive(meta):
    return """```mermaid
flowchart TD
    EST([TCP连接已建立<br/>空闲无数据传输]):::start --> TM[计时 tcp_keepalive_time<br/>默认7200s]
    TM --> CHK{空闲超过阈值?}:::decision
    CHK -->|否| WAIT[继续等待<br/>有数据则重置计时]
    CHK -->|是| PRB[发送保活探测包<br/>空ACK或1字节]
    PRB --> RESP{对端响应?}:::decision
    RESP -->|ACK 正常| ALIVE[连接保活<br/>重置计时器]
    RESP -->|无响应| INTV[间隔tcp_keepalive_intvl<br/>默认75s 重发]
    RESP -->|RST 复位| RST[对端已重启/崩溃<br/>连接异常关闭]:::error
    INTV --> CNT[累计重试计数<br/>tcp_keepalive_probes 默认9]
    CNT --> MAX{达到最大次数?}:::decision
    MAX -->|否| PRB
    MAX -->|是| DEAD[判定对端死亡<br/>通知应用层连接断开]:::error
    ALIVE --> BEN[保活价值]:::decision
    BEN -->|1| B1[检测对端崩溃<br/>避免半开连接]
    BEN -->|2| B2[防止NAT/防火墙<br/>超时回收连接]
    BEN -->|3| B3[服务端及时清理<br/>无效连接资源]
    WAIT --> DAT{有新数据?}:::decision
    DAT -->|是| RESET[重置保活计时<br/>正常传输]:::success
    DAT -->|否| TM
    {_common_styles()}
```"""


# ============== Map.put ==============
def tpl_map_put(meta):
    return """```mermaid
flowchart TD
    PUT([put key,value]):::start --> HASH[计算hash key.hashCode ^ 高16位扰动]
    HASH --> IDX[计算桶位置<br/>index = n-1 & hash]
    IDX --> TAB{数组table为空?}:::decision
    TAB -->|是 首次put| RSZ[resize 初始化容量16<br/>阈值12]
    TAB -->|否| NODE[定位到桶 i]
    RSZ --> NODE
    NODE --> EMPTY{桶为空?}:::decision
    EMPTY -->|是| INS[新建Node放入桶]:::success
    EMPTY -->|否| HEAD{首节点key相同?}:::decision
    HEAD -->|是 hash&&equals| REPL[替换value 返回旧值]
    HEAD -->|否 树化?| TREE{链表长度≥8 && table≥64?}:::decision
    TREE -->|是| TREEIFY[转红黑树TreeNode<br/>插入并平衡]:::async
    TREE -->|否| LIST[遍历链表尾插法 JDK8]
    TREEIFY --> NEW[树节点插入完成]
    LIST --> TAIL{找到相同key?}:::decision
    TAIL -->|是| REPL
    TAIL -->|否| APP[链表尾部追加新Node]
    INS --> SIZE[modCount++ size++]
    REPL --> SIZE
    NEW --> SIZE
    APP --> SIZE
    SIZE --> BIG{size > threshold?}:::decision
    BIG -->|是| RSZ2[resize 扩容2倍<br/>rehash迁移]:::async
    BIG -->|否| DONE([插入完成 null]):::success
    RSZ2 --> DONE
    {_common_styles()}
```"""


# ============== OSGI ==============
def tpl_osgi(meta):
    return """```mermaid
flowchart TD
    APP([OSGi应用启动]):::start --> FW[OSGi Framework<br/>Equinox/Felix]
    FW --> BND[(Bundle集合<br/>每个=JAR+MANIFEST)]:::storage
    BND --> INST[Bundle安装 install]
    INST --> RES[解析依赖<br/>Import-Package/Require-Bundle]
    RES --> CHK{依赖满足?}:::decision
    CHK ->|否| FAIL[等待/报错]:::error
    CHK ->|是| START[Bundle.start<br/>激活Activator]
    START --> SVC[(OSGi服务注册表<br/>Bundle间通过服务通信)]:::storage
    SVC --> CONSUMER[消费者Bundle<br/>查找ServiceReference]
    CONSUMER --> INVK[动态调用服务]
    INVK --> UPDATE{Bundle升级?}:::decision
    UPDATE ->|热更新| HOT[停止旧版→启动新版<br/>无需重启容器]:::async
    UPDATE ->|卸载| UN[Bundle.uninstall]
    UPDATE ->|正常运行| RUN[持续提供服务]:::success
    HOT --> RUN
    {_common_styles()}
```"""


# ============== Queue接口 ==============
def tpl_queue(meta):
    return """```mermaid
flowchart TD
    Q([Queue接口 继承Collection]):::start --> OP{操作分类}:::decision
    OP -->|抛异常| TH[add/remove/element]
    OP -->|返回特殊值| RV[offer/poll/peek]
    TH --> ADD[add 失败抛IllegalStateException]
    TH --> RM[remove 队空抛NoSuchElementException]
    TH --> EL[element 查看队首 失败抛异常]
    RV --> OFFER[offer 入队 失败返回false]
    RV --> POLL[poll 出队 队空返回null]
    RV --> PEEK[peek 查看队首 空返回null]
    OFFER --> IMPL{实现类}:::decision
    POLL --> IMPL
    PEEK --> IMPL
    IMPL -->|基本| BQ[LinkedList / ArrayDeque]
    IMPL -->|阻塞| BLKQ[BlockingQueue子接口]
    IMPL -->|并发| CONQ[ConcurrentLinkedQueue<br/>CAS无锁]
    BLKQ --> ABQ[ArrayBlockingQueue<br/>有界数组+ReentrantLock]
    BLKQ --> LBQ[LinkedBlockingQueue<br/>链表 两把锁分离]
    BLKQ --> PBQ[PriorityBlockingQueue<br/>堆 优先级]
    BLKQ --> DQ[DelayQueue<br/>延时到期才能取]
    BLKQ --> SQ[SynchronousQueue<br/>无容量 直接传递]:::async
    {_common_styles()}
```"""


# ============== TCP三次/四次握手 ==============
def tpl_3way_4way(meta):
    return """```mermaid
sequenceDiagram
    autonumber
    participant C as 客户端
    participant S as 服务端
    Note over C,S: === 三次握手 建立连接 ===
    C->>S: SYN, seq=x
    Note right of C: CLOSED→SYN_SENT
    S->>C: SYN+ACK, seq=y, ack=x+1
    Note right of S: LISTEN→SYN_RCVD
    C->>S: ACK, seq=x+1, ack=y+1
    Note right of C: →ESTABLISHED
    Note right of S: →ESTABLISHED
    Note over C,S: === 双向数据传输 ===
    C->>S: 业务数据
    S->>C: 业务数据
    Note over C,S: === 四次挥手 断开连接 ===
    C->>S: FIN, seq=u
    Note right of C: ESTABLISHED→FIN_WAIT_1
    S->>C: ACK, ack=u+1
    Note right of S: →CLOSE_WAIT 半关闭
    Note right of C: →FIN_WAIT_2
    S->>C: FIN, seq=w
    Note right of S: →LAST_ACK
    C->>S: ACK, seq=u+1, ack=w+1
    Note right of C: →TIME_WAIT 等2MSL
    Note right of C: →CLOSED
    Note right of S: →CLOSED
```"""


# ============== TreeMap ==============
def tpl_treemap(meta):
    return """```mermaid
flowchart TD
    PUT([put key,value]):::start --> CMP[比较key<br/>Comparator或Comparable]
    CMP --> ROOT{根节点为空?}:::decision
    ROOT -->|是| NEW[新建根节点<br/>颜色黑]:::success
    ROOT -->|否| SRH[从根开始二分查找]
    SRH --> LOOP{cmp结果}:::decision
    LOOP -->|cmp<0| LT[进入左子树]
    LOOP -->|cmp>0| RT[进入右子树]
    LOOP -->|cmp=0 找到相同key| UPD[替换value 返回旧值]:::success
    LT --> LEAF{子节点为空?}:::decision
    RT --> LEAF
    LEAF -->|是| INS[新建红色节点插入<br/>作为孩子]
    LEAF -->|否| SRH
    INS --> CHK{红黑树性质检查}:::decision
    NEW --> DONE([完成]):::success
    CHK -->|父黑 平衡| OK[无需调整]
    CHK -->|父红 叔红| C1[变色 父叔变黑 爷变红<br/>向上递归]
    CHK -->|父红 叔黑| C2[旋转 LL/RR/LR/RL<br/>+变色]
    C1 --> CHK
    C2 --> OK
    OK --> DONE
    UPD --> DONE
    {_common_styles()}
```"""


# ============== 协商缓存 ==============
def tpl_conditional_cache(meta):
    return """```mermaid
flowchart TD
    R1([浏览器请求资源]):::start --> CHK1{本地有缓存?}:::decision
    CHK1 -->|否 强缓存未命中| REQ1[直接请求服务器]
    CHK1 -->|是| EXP{强缓存过期?}:::decision
    EXP -->|否 Cache-Control/Expires未到| USE[直接用本地缓存 200 from disk cache]:::success
    EXP -->|是| REQ2[带条件请求头<br/>询问服务器是否变更]
    REQ1 --> SERVER[服务器处理]
    REQ2 --> STR{协商策略}:::decision
    STR -->|If-Modified-Since| IMS[携带Last-Modified<br/>上次修改时间]
    STR -->|If-None-Match| INM[携带ETag<br/>资源唯一标识]
    IMS --> CMP{服务器对比}:::decision
    INM --> CMP
    CMP -->|未变更| N304[返回304 Not Modified<br/>无响应体 浏览器用旧缓存]:::async
    CMP -->|已变更| N200[返回200 + 新资源<br/>+新的Last-Modified/ETag]
    N304 --> SHOW([显示页面]):::success
    N200 --> SHOW
    SERVER --> N200
    {_common_styles()}
```"""


# ============== 字节输入流 ==============
def tpl_input_stream(meta):
    return """```mermaid
flowchart TD
    APP([读取文件/网络数据]):::start --> NEW[创建InputStream<br/>FileInputStream等]
    NEW --> READ[read 每次读1字节]
    READ --> BUF{是否缓冲?}:::decision
    BUF -->|否 直接读| SYS[每次read触发系统调用<br/>频繁切换内核态 性能差]:::error
    BUF -->|是 装饰器| BIS[BufferedInputStream包装<br/>8KB缓冲区]
    BIS --> PRE[预读填满缓冲区<br/>后续read直接从内存取]
    PRE --> RET[返回字节 0~255<br/>-1表示EOF结束]
    SYS --> RET
    RET --> END{是否-1?}:::decision
    END -->|否| LOOP[处理字节<br/>循环读取]
    LOOP --> READ
    END -->|是| CLOSE[关闭流 释放资源<br/>try-with-resources]:::async
    CLOSE --> DONE([读取完成]):::success
    NEW --> DEC{需要增强功能?}:::decision
    DEC -->|缓冲| BIS
    DEC -->|基本类型| DIS[DataInputStream<br/>readInt/readUTF]
    DEC -->|对象反序列化| OIS[ObjectInputStream<br/>readObject]
    DEC -->|字节数组| BAIS[ByteArrayInputStream<br/>内存读取]
    {_common_styles()}
```"""


# ============== 对称加密 ==============
def tpl_symmetric(meta):
    return """```mermaid
flowchart TD
    PL([发送方: 明文]):::start --> KEY[共享密钥K<br/>发送方接收方相同]
    KEY --> ALG{加密算法}:::decision
    ALG -->|DES| DES[56位密钥 已不安全]
    ALG -->|3DES| TDES[3次DES 168位 慢]
    ALG -->|AES| AES[128/192/256位 主流推荐]:::async
    ALG -->|RC4| RC4[流加密 已被淘汰]
    ALG -->|SM4| SM4[国密算法 中国标准]
    AES --> ENC[加密: 明文+密钥+IV<br/>→密文]
    ENC --> MODE{加密模式}:::decision
    MODE -->|ECB 电子密码本| ECB[相同明文→相同密文<br/>不安全 暴露模式]:::error
    MODE -->|CBC 密文分组链接| CBC[前块密文异或后块<br/>需IV 推荐已用]
    MODE -->|CTR 计数器| CTR[并行加密 速度快<br/>流式加密]
    MODE -->|GCM| GCM[带认证标签 AEAD<br/>防篡改 最推荐]:::success
    CBC --> SEND[密文+IV 通过网络发送]
    GCM --> SEND
    SEND --> RCV([接收方收到密文])
    RCV --> SAME[用相同密钥K解密]
    SAME --> DEC[反向运算 恢复明文]
    DEC --> ORIG([得到原始明文]):::success
    {_common_styles()}
```"""


# ============== 工厂模式 ==============
def tpl_factory(meta):
    return """```mermaid
flowchart TD
    CLT([客户端 需要对象]):::start --> Q[不想直接new<br/>解耦创建过程]
    Q --> CHO{工厂模式选择}:::decision
    CHO -->|简单工厂| SF[SimpleFactory<br/>一个工厂方法+switch]
    CHO -->|工厂方法| FM[Factory Method<br/>每类产品一个工厂]
    CHO -->|抽象工厂| AF[Abstract Factory<br/>创建产品族]
    SF --> SF1[传type参数<br/>返回具体Product]
    SF1 --> SF2[违反开闭原则<br/>新增产品需改工厂]:::error
    FM --> FM1[定义Product接口<br/>每个具体产品对应具体工厂]
    FM1 --> FM2[符合开闭原则<br/>扩展新产品加新类即可]
    AF --> AF1[AbstractFactory接口<br/>创建多个相关产品]
    AF1 --> AF2[UI主题: Win/Mac<br/>Button+TextBox+ScrollBar]
    FM2 --> PRD[具体产品 ProductA/B]
    AF2 --> PRD
    SF2 --> PRD
    PRD --> CLT2([客户端拿到对象<br/>不关心创建细节]):::success
    CLT --> APP{应用场景}:::decision
    APP -->|JDBC| JDBC[DriverManager.getConnection<br/>不同数据库不同驱动]
    APP -->|Spring| SPI[BeanFactory.getBean<br/>IOC容器管理]
    APP -->|日志| LOG[SLF4J LoggerFactory<br/>切换Logback/Log4j]
    {_common_styles()}
```"""


# ============== 数据读请求和后台修复 ==============
def tpl_data_repair(meta):
    return """```mermaid
flowchart TD
    R([读数据请求]):::start --> MEM[查内存页表]
    MEM --> HIT{页在内存?}:::decision
    HIT -->|是| CKSUM[计算校验和<br/>比对存储的checksum]
    HIT -->|否| PF[触发Page Fault]
    PF --> DISK1[从磁盘加载页]:::storage
    DISK1 --> CKSUM
    CKSUM --> OK{校验一致?}:::decision
    OK -->|是| RET[返回数据给应用]:::success
    OK -->|否 数据损坏| REPAIR[触发后台修复]
    REPAIR --> MIR{是否有副本?}:::decision
    MIR -->|是 RAID/副本| MIRR[从副本/校验盘恢复<br/>RAID重建]
    MIR -->|否| ERASURE[从纠删码恢复<br/>Reed-Solomon]
    MIRR --> WRITE[修复后写回<br/>更新checksum]:::async
    ERASURE --> WRITE
    WRITE --> RET2[返回恢复后的数据]:::success
    RET --> BG[后台巡检scrub<br/>定期扫描发现潜在坏块]
    BG --> BAD{发现坏块?}:::decision
    BAD -->|是| REPAIR
    BAD -->|否| IDLE([健康 继续服务]):::success
    {_common_styles()}
```"""


# ============== 文件系统实现 ==============
def tpl_fs_impl(meta):
    return """```mermaid
flowchart TD
    APP([open /path/file.txt]):::start --> VFS[虚拟文件系统VFS<br/>统一接口]
    VFS --> PATH[路径解析<br/>逐级查目录项dentry]
    PATH --> INO[得到inode号<br/>文件的元数据索引]
    INO --> ICACHE[(inode缓存<br/>权限/大小/块指针)]:::storage
    ICACHE --> ALLOC{存储布局}:::decision
    ALLOC -->|连续分配| CON[extents 起始块+长度<br/>大文件高效]
    ALLOC -->|链式分配| LNK[FAT表 下一块指针<br/>随机访问慢]
    ALLOC -->|索引分配| IDX[inode多级间接块指针<br/>主流Unix/Ext4]
    CON --> BLK[(磁盘数据块<br/>扇区组成)]:::storage
    LNK --> BLK
    IDX --> BLK
    BLK --> BUF[页缓存Page Cache<br/>预读+延迟写]
    BUF --> APP2[read返回数据给应用]:::success
    APP2 --> WR{是否写操作?}:::decision
    WR -->|是| WB[写Page Cache 标记dirty]
    WB --> JNL{是否日志文件系统?}:::decision
    JNL -->|是 ext3/ext4| JNL2[先写journal日志<br/>再写实际数据]
    JNL -->|否| DWRITE[直接写回 可能不一致]:::error
    JNL2 --> FSCK[崩溃后用日志恢复<br/>保证一致性]:::async
    {_common_styles()}
```"""


# ============== 文件系统 ==============
def tpl_filesystem(meta):
    return """```mermaid
flowchart TD
    FS([文件系统核心职责]):::start --> ORG[组织存储空间<br/>块/簇管理]
    FS --> NAM[命名空间<br/>目录树结构]
    FS --> META[元数据管理<br/>inode/属性]
    FS --> ACCESS[访问控制<br/>权限rwx]
    FS --> RELI[可靠性<br/>日志/冗余]
    ORG --> FREE[空闲块位图/组<br/>位图bitmap/空闲链表]
    ORG --> ALLOC[分配策略<br/>连续/链式/索引]
    NAM --> DIR[目录结构<br/>dentry缓存加速]
    NAM --> HARD[硬链接<br/>多个路径指向同inode]
    NAM --> SYML[软链接<br/>独立inode指向路径]
    META --> INO[inode: 权限/时间/大小<br/>直接+间接块指针]
    ACCESS --> MODE[rwxrwxrwx 模式位]
    ACCESS --> ACL[ACL精细权限<br/>多用户多组]
    RELI --> JNL[日志Journal<br/>先写日志再改数据]
    RELI --> COW[写时复制CoW<br/>ZFS/Btrfs 快照]
    RELI --> RAID[RAID冗余<br/>镜像/校验]
    JNL --> TYPES{文件系统类型}:::decision
    TYPES -->|本地| EXT[ext4/xfs<br/>Linux主流]
    TYPES -->|网络| NFS[NFS/SMB<br/>远程挂载]
    TYPES -->|分布式| DFS[HDFS/Ceph<br/>海量存储]
    TYPES -->|内存| TMPFS[tmpfs<br/>内存虚拟盘]:::async
    {_common_styles()}
```"""


# ============== 虚拟内存 ==============
def tpl_virtual_memory(meta):
    return """```mermaid
flowchart TD
    P([进程独享虚拟地址空间]):::start --> SEG[虚拟地址空间划分]
    SEG --> UAREA[用户空间 0~3GB<br/>代码/数据/堆/栈]
    SEG --> KAREA[内核空间 3~4GB<br/>所有进程共享]
    UAREA --> CODE[.text 代码段 只读]
    UAREA --> DATA[.data 已初始化全局变量]
    UAREA --> BSS[.bss 未初始化全局变量]
    UAREA --> HEAP[堆 heap 向上增长<br/>malloc/new分配]
    UAREA --> MMAP[mmap映射区<br/>文件/共享内存]
    UAREA --> STACK[栈 stack 向下增长<br/>局部变量/函数帧]
    P --> MMU[MMU: 虚拟地址→物理地址]
    MMU --> PGTBL[(多级页表<br/>占用少内存)]:::storage
    PGTBL --> TLB[TLB缓存热门映射]
    TLB --> REF([访问物理内存RAM]):::success
    HEAP --> DEM[请求分页<br/>按需分配 实际内存可超物理]:::async
    DEM --> SWP[内存不足时<br/>换出到Swap交换区]
    SWP --> BEN[每个进程4GB独立空间<br/>实际共用物理内存]
    {_common_styles()}
```"""


# ============== 装饰模式 ==============
def tpl_decorator(meta):
    return """```mermaid
flowchart TD
    CMP([Component抽象组件<br/>定义operation接口]):::start --> CONC[ConcreteComponent<br/>具体实现]
    CMP --> DEC[Decorator 抽象装饰器<br/>持有Component引用]
    DEC --> DEC1[ConcreteDecoratorA<br/>增强功能+状态]
    DEC --> DEC2[ConcreteDecoratorB<br/>增强功能+行为]
    CONC --> WRAP[运行时动态包装]
    DEC1 --> WRAP
    DEC2 --> WRAP
    WRAP --> CHAIN{多层装饰}:::decision
    CHAIN -->|第1层| L1[A装饰B]
    CHAIN -->|第2层| L2[C装饰A B]
    CHAIN -->|第N层| LN[层层包装 像洋葱]
    L1 --> CALL[调用最外层operation]
    L2 --> CALL
    LN --> CALL
    CALL --> INVK[逐层向前转发<br/>每层添加自己的增强]
    INVK --> CORE[最终调用ConcreteComponent<br/>原始功能]
    CORE --> RETURN[逐层返回 增强叠加]
    RETURN --> DONE([客户端拿到增强结果]):::success
    CMP --> APP{Java经典应用}:::decision
    APP -->|IO流| IO[BufferedInputStream<br/>包装FileInputStream]
    APP -->|Spring| SPR[BeanWrapper<br/>事务/AOP装饰]
    APP -->|Servlet| SERV[HttpServletRequestWrapper]
    {_common_styles()}
```"""


# ============== 证书信任链 ==============
def tpl_cert_chain(meta):
    return """```mermaid
flowchart TD
    ROOT([Root CA 根证书<br/>自签名 内置操作系统]):::start --> ISSUE1[签发中间CA<br/>私钥签名]
    ISSUE1 --> MID[Intermediate CA<br/>中间证书<br/>有效期较短]
    MID --> ISSUE2[签发服务器证书]
    ISSUE2 --> SVR[www.example.com<br/>服务器终端证书]
    SVR --> SEND[握手时发送<br/>服务器证书+中间证书]
    SEND --> CLT([客户端收到证书链]):::start
    CLT --> CHK1[验证服务器证书签名<br/>用中间CA公钥]
    CHK1 --> CHK2[验证中间证书签名<br/>用Root CA公钥]
    CHK2 --> CHK3[验证到Root<br/>检查是否在受信根列表]
    CHK3 --> TRUST{信任链完整?}:::decision
    TRUST -->|是| EX[校验域名/有效期/用途<br/>吊销列表CRL/OCSP]
    TRUST -->|否 中断链| FAIL[证书不可信<br/>浏览器警告]:::error
    EX --> OK{各项校验通过?}:::decision
    OK -->|是| TLS[TLS握手成功<br/>建立加密通道]:::success
    OK -->|否 过期/域名不符| FAIL
    {_common_styles()}
```"""


# ============== OOP ==============
def tpl_oop(meta):
    return """```mermaid
flowchart TD
    REAL([现实世界问题]):::start --> ABS[抽象Abstraction<br/>提取核心特征]
    ABS --> CLS[定义类Class<br/>属性+方法 模板]
    CLS --> ENC[封装Encapsulation<br/>private+getter/setter]
    ENC --> IHV[隐藏内部细节<br/>暴露稳定接口]
    CLS --> INH[继承Inheritance<br/>extends复用代码]
    INH --> ISA[is-a关系<br/>Dog is an Animal]
    CLS --> POLY[多态Polymorphism<br/>同一接口多种形态]
    POLY --> OVLD[重载Overload<br/>编译期 静态]
    POLY --> OVRR[重写Override<br/>运行期 动态]:::async
    CLS --> OBJ[new创建对象<br/>实例化分配内存]
    OBJ --> MSG[对象间消息传递<br/>方法调用]
    MSG --> INTER[接口Interface<br/>定义契约规范]
    INTER --> DECO[降低耦合<br/>面向接口编程]
    DECO --> APP{设计原则}:::decision
    APP --> SRP[单一职责<br/>一个类只做一件事]
    APP --> OCP[开闭原则<br/>扩展开放 修改关闭]
    APP --> LSP[里氏替换<br/>子类能替换父类]
    APP --> DIP[依赖倒置<br/>依赖抽象非具体]
    {_common_styles()}
```"""


# ============== 归并排序 ==============
def tpl_merge_sort(meta):
    return """```mermaid
flowchart TD
    ARR([原始数组n个元素]):::start --> DEC{n > 1?}:::decision
    DEC -->|否 已有序| RTN([返回单个元素]):::success
    DEC -->|是| SPL[对半切分<br/>left=0~mid right=mid~n-1]
    SPL --> R1[递归排序左半]
    SPL --> R2[递归排序右半]
    R1 --> MERGE[合并两个有序子数组]
    R2 --> MERGE
    MERGE --> TWOP[双指针i/j分别指向<br/>左右子数组首元素]
    TWOP --> CMP{arr[i] <= arr[j]?}:::decision
    CMP -->|是| TA["k++ = arr[i++]<br/>左元素先入结果"]
    CMP -->|否| TB["k++ = arr[j++]<br/>右元素先入结果"]
    TA --> NXT{一方遍历完?}:::decision
    TB --> NXT
    NXT -->|否| CMP
    NXT -->|是| TAIL[剩余元素直接追加]
    TAIL --> COPY[复制回原数组]
    COPY --> DONE([排序完成]):::success
    DEC --> PRO{性能分析}:::decision
    PRO --> T[时间复杂度<br/>最好/最坏/平均 O n log n]
    PRO --> S[空间复杂度<br/>O n 需辅助数组]:::error
    PRO --> ST[稳定性 稳定<br/>相等元素顺序不变]:::success
    {_common_styles()}
```"""


# ============== 扫码登录 ==============
def tpl_qr_login(meta):
    return """```mermaid
sequenceDiagram
    autonumber
    participant W as Web浏览器 PC
    participant S as 服务端
    participant D as 手机APP
    W->>S: 1. 访问登录页 请求二维码
    S->>S: 2. 生成临时token(uuid) 存Redis<br/>状态:待扫描 TTL:5min
    S->>W: 3. 返回二维码图片 含token
    Note over W: 显示二维码 等待扫描
    D->>S: 4. APP扫描二维码 提交token+登录态
    S->>S: 5. 验证token 存APP的用户ID<br/>状态:已确认待登录
    S->>D: 6. 返回确认 提示授权登录
    D->>S: 7. 用户点击确认授权
    S->>S: 8. 生成PC端会话token<br/>状态:已登录
    Note over W,D: 轮询或WebSocket
    W->>S: 9. 轮询查token状态
    S->>W: 10. 返回登录成功+会话凭证
    W->>W: 11. 写Cookie 跳转主页
```"""


# ============== 观察者模式 ==============
def tpl_observer(meta):
    return """```mermaid
flowchart TD
    SUB([Subject 被观察者主题]):::start --> STATE[维护内部状态]
    STATE --> REG[registerObserver 注册观察者]
    REG --> LIST[(观察者列表<br/>List Observer)]:::storage
    LIST --> NOTIFY[状态变更时 notifyObservers]
    NOTIFY --> LOOP[遍历所有观察者]
    LOOP --> UPD[调用observer.update<br/>推送新状态]
    UPD --> O1[ConcreteObserver1<br/>如: 数据图表]
    UPD --> O2[ConcreteObserver2<br/>如: 邮件通知]
    UPD --> O3[ConcreteObserver3<br/>如: 日志记录]
    O1 --> REACT[各自响应处理]
    O2 --> REACT
    O3 --> REACT
    REACT --> DONE([主题与观察者解耦<br/>一对多广播]):::success
    REG --> MOD{模式变体}:::decision
    MOD -->|推模型 push| PUSH[主题把数据推给观察者<br/>可能传无用数据]
    MOD -->|拉模型 pull| PULL[观察者主动拉取需要的<br/>主题只通知事件]
    MOD -->|事件总线 EventBus| BUS[Guava EventBus<br/>解耦更彻底]:::async
    MOD -->|响应式 RxJava| RX[Observable/Flowable<br/>背压支持]
    {_common_styles()}
```"""


# ============== 用户态和核心态 ==============
def tpl_user_kernel(meta):
    return """```mermaid
flowchart TD
    APP([用户进程运行]):::start --> USR[用户态 Ring3<br/>权限受限]
    USR --> EXEC[执行普通指令<br/>访问用户空间内存]
    EXEC --> NEED{需要特权操作?}:::decision
    NEED -->|否| LOOP[继续用户态执行]
    NEED -->|是 系统调用/中断/异常| TRAP[触发trap指令<br/>软中断 int 0x80/syscall]
    TRAP --> SW[切换到内核态 Ring0<br/>保存现场 切换栈]
    SW --> KER[内核处理<br/>访问硬件/文件/网络]
    KER --> RT[执行完成<br/>恢复现场]
    RT --> RET[返回用户态<br/>继续执行下一条指令]
    RET --> LOOP
    LOOP --> NEXT{继续运行?}:::decision
    NEXT -->|是| EXEC
    NEXT -->|否 结束| EXIT([进程退出]):::success
    TRAP --> TYPES{进入内核态的场景}:::decision
    TYPES -->|系统调用| SC[read/write/open<br/>主动请求]
    TYPES -->|异常| EXC[缺页/除零<br/>被动触发]
    TYPES -->|外部中断| IRQ[时钟/网卡/键盘<br/>硬件事件]:::async
    {_common_styles()}
```"""


# ============== 进程同步互斥 ==============
def tpl_sync_mutex(meta):
    return """```mermaid
flowchart TD
    SHARED([多进程/线程访问共享资源]):::start --> CONC{并发访问}:::decision
    CONC -->|无协调| RACE[竞态条件 Race Condition<br/>数据不一致]:::error
    CONC -->|需同步| SOL[同步互斥机制]
    SOL --> MUT[互斥Mutex<br/>同一时刻只允许一个访问]
    SOL --> SEM[信号量Semaphore<br/>计数控制资源数]
    SOL --> MON[管程Monitor<br/>Java synchronized内置]
    SOL --> PV[PV操作 原语<br/>wait/signal]
    MUT --> LOCK[加锁lock → 临界区 → 解锁unlock]
    LOCK --> CS[临界区Critical Section<br/>同一时刻只有一个进程]
    CS --> WAIT{资源被占?}:::decision
    WAIT -->|是 阻塞| BLK[进入等待队列<br/>让出CPU]
    WAIT -->|否| ENTER[进入临界区执行]
    SEM --> BIN{信号量类型}:::decision
    BIN -->|二值 0/1| BIN2[等价互斥锁]
    BIN -->|计数 N| CNT[控制N个并发<br/>如连接池大小]
    PV --> CLASSIC{经典问题}:::decision
    CLASSIC -->|生产者消费者| PC[empty/full信号量<br/>+mutex]
    CLASSIC -->|读者写者| RW[读者优先/写者优先<br/>公平策略]
    CLASSIC -->|哲学家进餐| DP[避免死锁<br/>资源有序/限制人数]
    {_common_styles()}
```"""


# ============== Java泛型擦除 ==============
def tpl_generic_erasure(meta):
    return """```mermaid
flowchart TD
    SRC([源码: List&lt;String&gt; list]):::start --> CMP[javac编译]
    CMP --> ERASE[类型擦除<br/>擦除为原生类型List]
    ERASE --> RES[字节码: List list<br/>元素视为Object]
    RES --> BRIDGE{方法签名冲突?}:::decision
    BRIDGE -->|是 子类重写泛型方法| BDG[生成桥接方法bridge<br/>合成方法维护多态]:::async
    BRIDGE -->|否 普通使用| CAST[编译器自动插入checkcast<br/>读取时强转]
    CAST --> RT[运行时: List&lt;String&gt;与List&lt;Integer&gt;<br/>是同一个Class]:::storage
    RT --> LIM{擦除带来的限制}:::decision
    LIM -->|1| L1[运行时无法获取泛型类型<br/>new T 不允许]
    LIM -->|2| L2[基本类型不能做泛型参数<br/>需包装类]
    LIM -->|3| L3[instanceof无法判断泛型<br/>只能判断原始类型]
    LIM -->|4| L4[静态字段/方法<br/>不能使用类的泛型参数]
    LIM -->|5| L5[异常类不能泛型化]
    SRC --> SOL{运行时需要泛型信息?}:::decision
    SOL -->|反射| REF[getGenericSuperClass<br/>从父类签名提取]
    SOL -->|显式传Class| CLS[传Class&lt;T&gt;参数<br/>TypeToken方案]
    {_common_styles()}
```"""


# ============== String不可变 ==============
def tpl_string_immutable(meta):
    return """```mermaid
flowchart TD
    NEW([String s = "abc"]):::start --> JMM[在堆中创建对象<br/>final char[]/byte[] value]
    JMM --> FINAL[value数组final<br/>不可重新赋值]
    FINAL --> IMM[内容不可变<br/>"abc"永远等于"abc"]
    IMM --> BEN{不可变带来的好处}:::decision
    BEN -->|1 线程安全| TS[多线程共享无需同步<br/>天然不可变]
    BEN -->|2 hashCode缓存| HC[计算一次缓存<br/>适合做Map的key]
    BEN -->|3 字符串常量池| POOL[相同字面量复用<br/>节省内存]:::async
    BEN -->|4 安全性| SEC[作为参数传递<br/>不可被恶意修改]
    BEN -->|5 不可变支持| SUB[substring/concat<br/>返回新对象 不改原对象]
    POOL --> EQ{s == s2 ?}:::decision
    EQ -->|字面量 字面量| Y[true 同一引用]:::success
    EQ -->|new String new String| N[false 堆中新对象]:::error
    EQ -->|intern| IN[手动入池<br/>返回常量池引用]
    NEW --> MOD{需要频繁修改?}:::decision
    MOD -->|否| USE_S[继续用String]
    MOD -->|是 拼接循环| SB[改用StringBuilder<br/>避免创建大量中间对象]
    SB --> BUF[可变char[] 缓冲区<br/>append高效]
    {_common_styles()}
```"""


# ============== equals和hashCode ==============
def tpl_equals_hash(meta):
    return """```mermaid
flowchart TD
    HSK([对象放入HashMap]):::start --> HC[调用hashCode 求桶位置]
    HC --> IDX[计算index = n-1 & hash]
    IDX --> BKT[(定位到桶)]:::storage
    BKT --> SAME{同桶有元素?}:::decision
    SAME -->|否| INS[直接插入]:::success
    SAME -->|是 hash相同| EQ[调用equals逐一比较]
    EQ --> EQRES{equals返回true?}:::decision
    EQRES -->|是 同一逻辑对象| UPD[替换value<br/>视为已存在]
    EQRES -->|否 hash碰撞不同对象| APP[链表/红黑树追加]:::async
    INS --> OK([完成]):::success
    UPD --> OK
    APP --> OK
    HC --> RULE{必须遵守的契约}:::decision
    RULE -->|1| R1[equals相等<br/>hashCode必须相等]
    RULE -->|2| R2[hashCode相等<br/>equals不一定相等 碰撞]
    RULE -->|3| R3[对象未变 多次调用<br/>hashCode稳定不变]
    RULE -->|4| R4[重写equals<br/>必须重写hashCode]
    R4 --> BAD{只重写equals?}:::decision
    BAD -->|是 不重写hashCode| BUG[同逻辑对象hash不同<br/>散列到不同桶→逻辑错误]:::error
    {_common_styles()}
```"""


# ============== HashMap JDK8 ==============
def tpl_hashmap8(meta):
    return """```mermaid
flowchart TD
    INIT([HashMap初始化<br/>table=null]):::start --> PUT[首次put 触发resize]
    PUT --> SZ[容量16 负载因子0.75<br/>阈值12]
    SZ --> ARR[(Node[] table<br/>数组+链表+红黑树)]:::storage
    ARR --> IDX[index = n-1 & hash<br/>hash=hashCode^高16位]
    IDX --> EMP{桶为空?}:::decision
    EMP -->|是| N1[新建Node入桶]
    EMP -->|否| KEY{首节点key相同?}:::decision
    KEY -->|是 equals相等| REP[替换value]
    KEY -->|否| TREE{链表长度>=8 && 表长>=64?}:::decision
    TREE -->|是| TF[链表转红黑树<br/>查找O log n]:::async
    TREE -->|否| APP[尾插法追加JDK8<br/>JDK7头插法会死循环]
    APP --> LOOP{遍历找到相同key?}:::decision
    LOOP -->|是| REP
    LOOP -->|否| NEW[追加新Node]
    NEW --> SIZE[size++ modCount++]
    N1 --> SIZE
    REP --> RET[返回oldValue]
    SIZE --> BIG{size > threshold?}:::decision
    BIG -->|是| RESIZE[扩容2倍<br/>重哈希迁移rehash]:::async
    BIG -->|否| DONE([返回null]):::success
    RESIZE --> DONE
    TF --> SIZE
    {_common_styles()}
```"""


# ============== synchronized锁升级 ==============
def tpl_lock_upgrade(meta):
    return """```mermaid
flowchart TD
    OBJ([对象头Mark Word]):::start --> FIRST{首次有线程访问?}:::decision
    FIRST -->|是 单线程| BIAS[偏向锁 Biased<br/>记录线程ID 无竞争]
    BIAS --> RUN1[同线程再次进入<br/>CAS比较线程ID 即可]
    RUN1 --> COMP{出现第二个线程?}:::decision
    COMP -->|否 仍是单线程| RUN1
    COMP -->|是 竞争出现| LIGHT[轻量级锁 Lightweight<br/>撤销偏向 栈帧Lock Record]
    LIGHT --> CAS[CAS自旋<br/>尝试设置Mark Word指针]
    CAS --> SUCC{CAS成功?}:::decision
    SUCC -->|是| RUN2[自旋持有锁<br/>无系统调用]
    SUCC -->|否| SPIN[自适应自旋<br/>等待一定次数]
    SPIN --> GIVEUP{超过自旋阈值?}:::decision
    GIVEUP -->|否| CAS
    GIVEUP -->|是 严重竞争| HEAVY[重量级锁 Heavyweight<br/>ObjectMonitor]
    HEAVY --> OS[(内核态mutex<br/>等待队列park/unpark)]:::storage
    OS --> BLK[未抢到锁的线程<br/>进入内核态阻塞]
    BLK --> WAKE[锁释放时唤醒<br/>系统调用开销大]
    WAKE --> DONE([执行临界区]):::success
    BIAS -.->|JDK15+默认关闭| OFF[BiasedLocking已废弃<br/>直接进入轻量级锁]:::async
    {_common_styles()}
```"""


# ============== 通用：内存分段/分页/虚拟内存 fallback ==============
def tpl_generic_memory(meta):
    return """```mermaid
flowchart TD
    START([请求/触发]):::start --> PROC[核心处理过程]
    PROC --> CHK{关键判断}:::decision
    CHK -->|条件1| BR1[分支1处理]
    CHK -->|条件2| BR2[分支2处理]
    CHK -->|条件3| BR3[分支3处理]
    BR1 --> STORE[(数据/状态存储)]:::storage
    BR2 --> STORE
    BR3 --> ERR[异常/失败处理]:::error
    STORE --> OUT[输出结果]:::success
    PROC --> ADV{关键特性}:::decision
    ADV -->|优势| ADV1[性能/效率提升]
    ADV -->|注意事项| ADV2[边界/约束条件]:::async
    {_common_styles()}
```"""


# ============== 数据库类通用模板 ==============
def tpl_db_index(meta):
    return """```mermaid
flowchart TD
    Q([查询SQL执行]):::start --> PARSE[解析器Parser<br/>词法/语法/语义分析]
    PARSE --> OPT[优化器Optimizer<br/>基于成本CBO选择执行计划]
    OPT --> IDX{是否走索引?}:::decision
    IDX -->|是 二级索引| SI[扫描二级索引<br/>获取主键PK]
    SI --> COV{是否覆盖索引?}:::decision
    COV -->|是 所需列全在索引| DIRECT[直接返回<br/>无需回表]:::success
    COV -->|否 缺列| BACK[回表: 用PK查聚簇索引<br/>获取完整行]:::async
    BACK --> RES[组装结果集]
    IDX -->|否 全表扫描| FULL[顺序扫描所有数据页<br/>慢 大表慎用]:::error
    DIRECT --> RES
    FULL --> RES
    RES --> RTN([返回结果]):::success
    OPT --> STATS[(统计信息直方图<br/>决定索引选择)]:::storage
    STATS --> BAD{统计信息过期?}:::decision
    BAD -->|是| WRONG[选错执行计划<br/>需analyze更新]:::error
    {_common_styles()}
```"""


# ============== 主从复制 ==============
def tpl_replication(meta):
    return """```mermaid
flowchart LR
    M([Master主库]):::start --> BIN[(binlog二进制日志<br/>记录所有变更)]:::storage
    BIN --> DUMP[Binlog Dump线程<br/>推送给从库]
    DUMP --> NET[(网络传输)]:::storage
    NET --> S([Slave从库])
    S --> IO[IO线程接收binlog]
    IO --> RELAY[(写入relay log<br/>中继日志)]:::storage
    RELAY --> SQL2[SQL线程重放relay log<br/>执行SQL恢复数据]
    SQL2 --> DATAS[(从库数据更新)]:::storage
    DATAS --> READ([读请求分流到从库]):::success
    M --> WRITE([写请求到主库]):::success
    DUMP --> MODE{复制模式}:::decision
    MODE -->|异步复制| ASYNC[主库不等从库<br/>可能丢数据 默认]:::error
    MODE -->|半同步| SEMI[主库等至少1个从库ACK<br/>折中推荐]:::async
    MODE -->|全同步| SYNC[主库等所有从库<br/>强一致 慢]
    {_common_styles()}
```"""


# ============== ACID ==============
def tpl_acid(meta):
    return """```mermaid
flowchart TD
    TX([事务Transaction]):::start --> A[A 原子性 Atomicity<br/>要么全成功 要么全回滚]
    TX --> C[C 一致性 Consistency<br/>数据从一合法状态到另一合法状态]
    TX --> II[I 隔离性 Isolation<br/>多事务并发互不干扰]
    TX --> D[D 持久性 Durability<br/>提交后永久保存]
    A --> UND[(undo log回滚日志<br/>记录修改前镜像)]:::storage
    UND --> ROLL{提交/回滚?}:::decision
    ROLL -->|commit| OK1[持久化生效]
    ROLL -->|rollback| RB[根据undo log逆操作<br/>恢复到事务前状态]
    C --> CON[约束: 主键/外键/触发器<br/>+ 业务规则]
    II --> ISO{隔离级别}:::decision
    ISO -->|读未提交 RU| RU[脏读 不可重复读 幻读]:::error
    ISO -->|读已提交 RC| RC[解决脏读<br/>每次select新视图]
    ISO -->|可重复读 RR| RR[解决不可重复读<br/>MySQL默认 快照读+间隙锁]
    ISO -->|串行化 Serializable| SER[解决幻读<br/>性能最差]
    D --> RED[(redo log重做日志<br/>WAL先写日志)]:::storage
    REDO --> CRASH{崩溃恢复?}:::decision
    CRASH -->|是| REC[用redo重做已提交事务<br/>保证不丢]
    CRASH -->|否| PERM([数据持久保存]):::success
    {_common_styles()}
```"""


# ============== MVCC ==============
def tpl_mvcc(meta):
    return """```mermaid
flowchart TD
    T([事务开始]):::start --> HID[行隐藏字段<br/>trx_id事务ID roll_ptr回滚指针]
    HID --> UNDO[(undo log版本链<br/>历史版本按时间链接)]:::storage
    T --> RV[生成Read View<br/>记录当前活跃事务列表]
    RV --> FIELD[creator_trx_id 本事务<br/>m_ids 活跃列表<br/>min_trx_id/max_trx_id]
    FIELD --> SEL[快照读 SELECT]
    SEL --> VIS{可见性算法}:::decision
    VIS -->|trx_id == creator| SEE[自己修改 可见]
    VIS -->|trx_id < min| SEE2[已提交事务 可见]:::success
    VIS -->|trx_id >= max| SEE3[未来事务 不可见<br/>顺roll_ptr找历史]
    VIS -->|min <= trx_id < max| IN{在m_ids活跃列表?}:::decision
    IN -->|是 未提交| HIDE[不可见 找上一版本]:::error
    IN -->|否 已提交| SEE4[可见]
    HIDE --> UNDO
    UNDO --> SEL
    SEE --> RC{隔离级别}:::decision
    SEE2 --> RC
    SEE3 --> RC
    SEE4 --> RC
    RC -->|RC 读已提交| RC2[每次SELECT<br/>新建ReadView]
    RC -->|RR 可重复读| RR2[首次SELECT<br/>建ReadView并复用]
    RC2 --> RES([返回快照数据]):::success
    RR2 --> RES
    SEL --> CURRENT{当前读?}:::decision
    CURRENT -->|update/delete/select for update| LOCK[加Next-Key Lock<br/>读最新数据]
    {_common_styles()}
```"""


# ============== Redis持久化 ==============
def tpl_redis_persist(meta):
    return """```mermaid
flowchart TD
    R([Redis数据持久化]):::start --> CHO{持久化方式}:::decision
    CHO -->|RDB 快照| RDB[bgsave fork子进程<br/>全量数据二进制]
    CHO -->|AOF 追加| AOF[每条写命令append<br/>到.aof文件]
    CHO -->|混合| MIX[Redis 4.0+<br/>RDB+AOF增量]
    RDB --> CW{触发时机}:::decision
    CW -->|手动 save/bgsave| M[阻塞/非阻塞<br/>fork Copy-On-Write]
    CW -->|配置 save m n| CFG[m秒内n次修改自动触发]
    CW -->|shutdown/shutdown| SH[正常关闭前快照]
    CW -->|主从同步| REP[全量复制时生成]
    AOF --> POL{fsync策略}:::decision
    POL -->|always 同步| ALW[每条命令刷盘<br/>最安全 性能差]:::error
    POL -->|everysec 每秒| EV[每秒刷盘 推荐<br/>最多丢1秒]:::async
    POL -->|no 由OS| NO[操作系统决定<br/>性能好 风险高]
    AOF --> BIG{文件过大?}:::decision
    BIG -->|是 超阈值| RW[bgrewriteaof重写<br/>基于当前数据生成最小命令]
    BIG -->|否| NORMAL[继续追加]
    RW --> COMPACT[压缩文件 减少体积]
    RDB --> ADV1[紧凑恢复快 适合备份<br/>缺点: 可能丢数据]
    AOF --> ADV2[数据完整 可读<br/>缺点: 文件大 恢复慢]
    MIX --> ADV3[RDB快速恢复<br/>+AOF补增量 最佳]:::success
    {_common_styles()}
```"""


# ============== 缓存穿透 ==============
def tpl_cache_penetrate(meta):
    return """```mermaid
flowchart TD
    REQ([查询请求]):::start --> REDIS[查Redis缓存]
    REDIS --> H1{Redis命中?}:::decision
    H1 -->|是| RET1[返回缓存数据]:::success
    H1 -->|否| DB[查MySQL数据库]
    DB --> H2{DB命中?}:::decision
    H2 -->|是| SETCK[写回Redis<br/>设置TTL]:::async
    H2 -->|否 不存在的key| PEN[缓存穿透<br/>每次请求直达DB]:::error
    PEN --> ATTACK{恶意攻击?}:::decision
    ATTACK -->|是 大量不存在的ID| CRASH[DB被压垮<br/>雪崩]:::error
    SETCK --> RET2[返回数据]:::success
    RET1 --> SOL{解决方案}:::decision
    PEN --> SOL
    SOL -->|1 缓存空值| NIL[DB未命中也存null<br/>设短TTL 防止占内存]
    SOL -->|2 布隆过滤器| BF[请求前先查BF<br/>不存在直接拒绝]:::async
    SOL -->|3 接口限流| RATE[限制单IP/用户频率<br/>保护DB]
    SOL -->|4 参数校验| VAL[非法ID格式<br/>前置拦截]
    NIL --> DONE([穿透问题解决]):::success
    BF --> DONE
    {_common_styles()}
```"""


# ============== 分布式锁 ==============
def tpl_distributed_lock(meta):
    return """```mermaid
flowchart TD
    NEED([分布式系统互斥]):::start --> CHO{实现方案}:::decision
    CHO -->|Redis| RD[set key value NX PX<br/>原子加锁]
    CHO -->|ZooKeeper| ZK[创建临时顺序节点<br/>EPHEMERAL_SEQUENTIAL]
    CHO -->|MySQL| SQL[唯一索引/for update<br/>基于数据库]
    CHO -->|etcd| ETCD[Lease租约+Revision版本<br/>Raft一致性]
    RD --> EXPIRE[设置过期时间<br/>防死锁]
    EXPIRE --> UNLOCK{释放锁}:::decision
    UNLOCK ->|直接del 风险| DEL[可能删别人的锁<br/>业务超时导致]:::error
    UNLOCK ->|Lua脚本原子| LUA[value==自己才删<br/>CAS校验]:::async
    UNLOCK ->|Redisson| RS[看门狗自动续期<br/>可重入 公平锁]
    ZK --> NODE1[客户端创建临时节点<br/>/lock/node-xxx]
    NODE1 --> MIN{是否最小节点?}:::decision
    MIN -->|是| GET[获得锁 执行业务]
    MIN -->|否| WAIT[监听前一个节点删除<br/>阻塞等待]
    WAIT --> MIN
    GET --> REL{业务完成}:::decision
    REL -->|是 客户端主动删| DEL2[删除节点<br/>后继节点收到通知]
    REL -->|会话断开| SESS[临时节点自动删除<br/>避免死锁]:::success
    {_common_styles()}
```"""


# ============== 短链系统 ==============
def tpl_short_url(meta):
    return """```mermaid
flowchart TD
    subgraph GEN [生成短链]
        LU([用户提交长URL]):::start --> DUP[查Redis/DB 是否已生成]
        DUP --> DUPRES{已存在?}:::decision
        DUPRES -->|是| REUSE[复用原短码]
        DUPRES -->|否| IDGEN[发号器分配唯一ID]
        IDGEN --> CHOICE{发号方案}:::decision
        CHOICE -->|自增ID| INC[DB自增+Base62编码]
        CHOICE -->|号段模式| SEG[Leaf-Segment<br/>预取一段到内存]
        CHOICE -->|雪花算法| SNOW[Snowflake<br/>时间+机器+序列]
        INC --> B62[Base62编码为6位短码]
        SEG --> B62
        SNOW --> B62
        B62 --> SAVE[存MySQL分库分表<br/>短码 --> 长URL + Redis缓存]
        REUSE --> SAVE
        SAVE --> RTN1([返回短链]):::success
    end
    subgraph REDIR [访问短链]
        SU([用户访问短链 x.com/abc123]):::start --> CDN[CDN边缘缓存]
        CDN --> C1{CDN命中?}:::decision
        C1 -->|是| R302[302重定向到长URL]:::success
        C1 -->|否| NG[Nginx反向代理]
        NG --> BF[布隆过滤器拦截不存在的短码]
        BF --> BFRES{短码存在?}:::decision
        BFRES -->|否| N404[404页面]:::error
        BFRES -->|是| REDIS2[查Redis]
        REDIS2 --> R2H{命中?}:::decision
        R2H -->|是 95%| R302
        R2H -->|否| MYSQL2[查MySQL分库分表]
        MYSQL2 --> MH{命中?}:::decision
        MH -->|是| WCK[回写Redis]:::async
        MH -->|否| N404
        WCK --> R302
    end
    GEN --> REDIR
    {_common_styles()}
```"""


# ============== 秒杀系统 ==============
def tpl_seckill(meta):
    return """```mermaid
flowchart TD
    U([用户点击秒杀按钮]):::start --> JS[前端按钮置灰<br/>校验+限频5s一次]
    JS --> GW[API网关<br/>IP/用户限流令牌桶]
    GW --> GOK{通过限流?}:::decision
    GOK -->|否| BLOCK[返回繁忙/排队]:::error
    GOK -->|是| CPT{需验证码?}:::decision
    CPT -->|是 防机器人| CV[滑块/图形验证码]
    CPT -->|否| SVC[秒杀服务]
    CV --> SVC
    SVC --> RPRE[查Redis预热库存<br/>Lua原子扣减]
    RPRE --> RDEC{扣减成功?}:::decision
    RDEC -->|否 库存<=0| SOLD[售罄提示+熔断]:::error
    RDEC -->|是| ENQ[发送MQ消息 异步下单]
    ENQ --> Q[(消息队列<br/>削峰填谷)]:::storage
    Q --> CONSUMER[订单消费者]
    CONSUMER --> DBOP[MySQL执行下单<br/>乐观锁version兜底]
    DBOP --> DBOK{DB扣减成功?}:::decision
    DBOK -->|是| ORDER[生成订单 返回成功]
    DBOK -->|否 超卖兜底| COMP[回滚Redis补偿<br/>订单失败]
    ORDER --> PAY[引导用户支付<br/>15分钟未支付取消]
    PAY --> NOTIFY([支付成功 异步通知]):::success
    {_common_styles()}
```"""


# ============== 通用：缓存/数据库一致性 ==============
def tpl_cache_consistency(meta):
    return """```mermaid
flowchart TD
    W([写请求更新数据]):::start --> CHO{更新策略}:::decision
    CHO -->|先更新DB再删缓存| UDD[Update DB then Delete Cache<br/>推荐 Canal]
    CHO -->|先删缓存再更新DB| DCD[Delete Cache then Update DB<br/>有并发问题]
    CHO -->|Cache Aside 旁路| CA[读miss查DB回写<br/>写时删缓存]
    UDD --> DEL1[删除Redis缓存]
    DEL1 --> MQ[(消息队列/Canal binlog<br/>保证最终一致)]:::storage
    DCD --> UPD[更新DB]
    UPD --> DELAY{并发问题}:::decision
    DELAY -->|是 读写并发| BUG[旧数据被回写<br/>缓存脏数据]:::error
    DELAY -->|否| OK1[正常一致]
    MQ --> RETRY{删除失败?}:::decision
    RETRY -->|是| RTY[重试/死信队列<br/>订阅binlog补偿]
    RETRY -->|否| DONE([缓存与DB一致]):::success
    RTY --> DONE
    CA --> READ{读请求?}:::decision
    READ -->|缓存miss| DB1[查DB并回写Redis]:::async
    READ -->|缓存hit| RTN[直接返回]
    {_common_styles()}
```"""


# ============== 延迟队列 ==============
def tpl_delay_queue_sys(meta):
    return """```mermaid
flowchart TD
    TASK([延迟任务提交<br/>订单/通知/重试]):::start --> CALC[计算触发时间戳<br/>triggerTime=now+delay]
    CALC --> STORE{存储方案}:::decision
    STORE -->|Redis ZSet| ZS[zadd key score=triggerTime<br/>member=taskId]
    STORE -->|RocketMQ| RMQ[MessageDelayLevel<br/>18个固定级别]
    STORE -->|Kafka| KAF[时间轮+Topic<br/>需自实现]
    STORE -->|MySQL| SQL[定时扫表<br/>where trigger_time<=now]
    STORE -->|时间轮| HW[HashedWheelTimer<br/>Netty内存级]
    ZS --> SCAN[定时扫描<br/>score<=now]
    RMQ --> DELAY[MQ内部按级别暂存<br/>到时投递]
    KAF --> SCAN
    SQL --> SCAN
    HW --> TICK[每tick推进指针<br/>到期任务回调]
    SCAN --> POP[取出到期任务<br/>zrem原子删除]
    POP --> EXEC[执行任务业务逻辑]
    DELAY --> EXEC
    TICK --> EXEC
    EXEC --> RES{执行成功?}:::decision
    RES -->|是| DONE([任务完成]):::success
    RES -->|否 失败| RETRY[记录重试次数<br/>指数退避重新入队]
    RETRY --> DLQ{超过最大次数?}:::decision
    DLQ -->|是| DEAD[进入死信队列<br/>告警人工介入]:::error
    DLQ -->|否| CALC
    {_common_styles()}
```"""


# ============== 分布式ID ==============
def tpl_distributed_id(meta):
    return """```mermaid
flowchart TD
    NEED([需要全局唯一ID]):::start --> REQ{核心要求<br/>唯一/趋势递增/高性能}
    REQ --> CHO{方案选型}:::decision
    CHO -->|UUID| U[UUID v4 128位<br/>无序 字符串]
    CHO -->|数据库自增| AI[auto_increment<br/>单点瓶颈]
    CHO -->|号段模式| SEG[Leaf-Segment<br/>DB号段+内存分配]
    CHO -->|雪花算法| SNOW[Snowflake<br/>64位 时间+机器+序列]
    CHO -->|Redis incr| RDI[INCR命令<br/>性能高 但依赖Redis]
    U --> CONS1[优点: 本地生成 无中心<br/>缺点: 无序 占空间 索引差]:::error
    AI --> CONS2[优点: 简单 递增<br/>缺点: 单点 性能瓶颈]:::error
    SEG --> DB[(DB存储max_id+step<br/>预取号段到内存)]:::storage
    DB --> MEM[内存原子分配ID<br/>号段用完再取]
    MEM --> ADV1[优点: 高性能 趋势递增<br/>缺点: 依赖DB ID可预测]
    SNOW --> BITS[64位: 1位符号+41位时间+10位机器+12位序列]
    BITS --> GEN[各机器本地生成<br/>每ms可生成4096个]
    GEN --> ADV2[优点: 高性能 去中心化 趋势递增<br/>缺点: 时钟回拨问题]:::success
    GEN --> CLK{时钟回拨?}:::decision
    CLK -->|是 系统时间倒退| SOLVE[等待/报错/借用未来位<br/>需特殊处理]
    CLK -->|否| OK2[正常生成]
    {_common_styles()}
```"""


# ============== 分库分表 ==============
def tpl_sharding(meta):
    return """```mermaid
flowchart TD
    SINGLE([单库单表瓶颈<br/>数据量过大 性能下降]):::start --> ANAL{瓶颈类型}:::decision
    ANAL -->|写QPS高| WSP[分库<br/>水平拆分多个DB实例]
    ANAL -->|单表数据多| TSP[分表<br/>单库拆多表]
    ANAL -->|并发+数据双高| BOTH[分库+分表<br/>组合方案]
    BOTH --> KEY{选择分片键}:::decision
    KEY -->|用户ID| UID[用户维度分片<br/>同一用户数据同库]
    KEY -->|订单ID| OID[订单维度<br/>需考虑跨用户查询]
    KEY -->|时间| TM[按月/天分表<br/>冷热分离]
    KEY -->|短码Hash| HSH[均匀分布<br/>但范围查询难]
    KEY --> HASH{分片策略}:::decision
    HASH -->|取模 mod| MOD[user_id % 128<br/>分布均匀]
    HASH -->|范围 range| RNG[id 0~100w库A<br/>100w~200w库B]
    HASH -->|一致性哈希| CONS[节点增减影响小<br/>适合动态扩容]:::async
    MOD --> ROUTE[分片路由<br/>ShardingSphere/MyCat]
    RNG --> ROUTE
    CONS --> ROUTE
    ROUTE --> EXEC[SQL下发到对应分片]
    EXEC --> CROSS{跨分片?}:::decision
    CROSS -->|否 单分片| FAST[单库查询 快]
    CROSS -->|是 多分片聚合| SLOW[并行查各分片+Merge<br/>分布式Join/分页难]::::error
    CROSS --> ISS{衍生问题}:::decision
    ISS -->|全局ID| GID[需分布式ID生成器]
    ISS -->|跨库Join| DENORM[冗余字段/应用层关联]
    ISS -->|分布式事务| DT[Seata/最终一致]
    ISS -->|迁移| MIG[双写+数据同步工具]
    {_common_styles()}
```"""


# ============== 限流 ==============
def tpl_rate_limit(meta):
    return """```mermaid
flowchart TD
    REQ([请求到达]):::start --> ALG{限流算法}:::decision
    ALG -->|计数器固定窗口| CNT[单位时间内计数<br/>超阈值拒绝]
    ALG -->|滑动窗口| SW[细分窗口平滑统计<br/>解决临界问题]:::async
    ALG -->|漏桶| LB[固定速率漏水<br/>超出容量丢弃/排队]
    ALG -->|令牌桶| TB[固定速率发令牌<br/>拿到才处理 允许突发]
    CNT --> CBUG{临界问题?}:::decision
    CBUG -->|是 窗口切换瞬间| SURGE[2倍流量冲击<br/>需滑动窗口补救]:::error
    CBUG -->|否| PASS1[放行]
    SW --> STAT[Redis ZSET统计<br/>score=时间戳]
    STAT --> CHK1{窗口内数量?}:::decision
    CHK1 -->|超阈值| DROP1[拒绝 429 Too Many]
    CHK1 -->|未超| PASS2[放行]
    LB --> QUEUE[请求入桶<br/>队列缓冲]
    QUEUE --> RATE[匀速消费<br/>超出容量溢出]
    RATE --> CHK2{桶满?}:::decision
    CHK2 -->|是| DROP2[拒绝]
    CHK2 -->|否| PASS3[排队处理]
    TB --> TOKEN[(令牌桶<br/>定时添加令牌)]:::storage
    TOKEN --> TAKE{有令牌?}:::decision
    TAKE -->|是| CONSUME[消耗1个令牌 放行]
    TAKE -->|否| DROP3[拒绝/等待]:::error
    PASS1 --> DONE([请求被处理]):::success
    PASS2 --> DONE
    PASS3 --> DONE
    CONSUME --> DONE
    REQ --> LEV{限流层级}:::decision
    LEV -->|网关限流| GW[Nginx/Spring Cloud Gateway]
    LEV -->|应用限流| APP[Sentinel/Resilience4j]
    LEV -->|分布式限流| DIST[Redis+Lua 原子操作]
    {_common_styles()}
```"""


# ============== 消息队列 ==============
def tpl_mq(meta):
    return """```mermaid
flowchart LR
    P([Producer生产者]):::start --> SEND[发送消息]
    SEND --> MQ[(Broker消息中间件<br/>Kafka/RocketMQ)]:::storage
    MQ --> TOPIC[(Topic主题<br/>逻辑分类)]
    TOPIC --> PART[(Partition分区<br/>并行消费单位)]
    PART --> REPL[(副本Replica<br/>主从同步保证高可用)]:::storage
    PART --> C([Consumer消费者])
    C --> GROUP{消费组}:::decision
    GROUP -->|广播| BC[每个组都收到<br/>配置更新场景]
    GROUP -->|集群| CL[每个分区只一个消费者<br/>负载均衡]:::async
    CL --> BIZ[业务处理]
    BIZ --> ACK{处理结果}:::decision
    ACK -->|成功| COMMIT[提交offset<br/>记录消费进度]
    ACK -->|失败| RETRY[重试/死信队列]
    COMMIT --> NEXT([继续消费下一条]):::success
    MQ --> USAGE{核心作用}:::decision
    USAGE -->|解耦| DC[生产消费分离<br/>互不影响]
    USAGE -->|异步| AS[提高响应速度<br/>写消息即返回]
    USAGE -->|削峰| PK[大促流量缓冲<br/>保护下游]
    P -.->|保证可靠| RELI[生产确认+持久化+消费确认]
    {_common_styles()}
```"""


# ============== 通用事务模板（数据库） ==============
def tpl_db_transaction(meta):
    return """```mermaid
flowchart TD
    B([业务操作开始]):::start --> BEGIN[开启事务 BEGIN]
    BEGIN --> OP1[执行SQL1: UPDATE账户扣款]
    OP1 --> OK1{成功?}:::decision
    OK1 -->|是| OP2[执行SQL2: UPDATE积分增加]
    OK1 -->|否| ERR1[异常捕获]
    OP2 --> OK2{成功?}:::decision
    OK2 -->|是| MORE{还有操作?}:::decision
    MORE -->|是| OP1
    MORE -->|否 所有成功| COMMIT[提交事务 COMMIT]
    OK2 -->|否| ERR2[异常捕获]
    COMMIT --> WAL[(redo log先写<br/>WAL保证持久化)]:::storage
    WAL --> SUCCESS([数据持久生效]):::success
    ERR1 --> RB[回滚 ROLLBACK]
    ERR2 --> RB
    RB --> UNDO[(undo log逆操作<br/>恢复事务前数据)]::::storage
    UNDO --> FAIL([事务失败 数据不变]):::error
    BEGIN --> ISO{隔离级别}:::decision
    ISO -->|RU| RU2[读未提交 脏读]
    ISO -->|RC| RC2[读已提交]
    ISO -->|RR| RR2[可重复读 MySQL默认]
    ISO -->|S| S2[串行化]
    {_common_styles()}
```"""


# ============== 通用场景系统设计模板 ==============
def tpl_scenario_system(meta):
    return """```mermaid
flowchart TD
    USER([用户请求]):::start --> CDN[CDN边缘加速<br/>静态资源就近返回]
    CDN --> MISS{CDN命中?}:::decision
    MISS -->|是| FAST[直接返回 首屏快]:::success
    MISS -->|否 动态请求| LB[负载均衡器<br/>Nginx/LVS]
    LB --> GW[API网关<br/>鉴权/限流/路由]
    GW --> GOK{通过?}:::decision
    GOK -->|否 鉴权/限流| REJECT[拒绝 401/429]:::error
    GOK -->|是| SVC[微服务集群<br/>业务逻辑处理]
    SVC --> CACHE[多级缓存<br/>本地+Redis]
    CACHE --> CHIT{命中?}:::decision
    CHIT -->|是| RET1[返回缓存数据]:::success
    CHIT -->|否| MQ2[发消息异步处理<br/>削峰解耦]
    CHIT -->|否 同步| DB[查数据库MySQL分库分表]
    DB --> WCK[回写各级缓存<br/>设置TTL]:::async
    MQ2 --> CONSUMER[消费者处理<br/>写DB/计算]
    WCK --> RET2[返回结果]
    CONSUMER --> RET2
    RET1 --> LOG[日志收集 ELK]
    RET2 --> LOG
    LOG --> MON[(监控告警 Prometheus<br/>+链路追踪 SkyWalking)]:::storage
    MON --> ALERT{指标异常?}:::decision
    ALERT -->|是| NOTIFY[告警/熔断降级<br/>自动恢复]::::async
    ALERT -->|否| STABLE([系统稳定运行]):::success
    {_common_styles()}
```"""


# ============== 布隆过滤器 ==============
def tpl_bloom(meta):
    return """```mermaid
flowchart TD
    ADD([添加元素到布隆过滤器]):::start --> H1[k个哈希函数<br/>h1 h2 ... hk]
    H1 --> BITS[得到k个bit位索引]
    BITS --> SET[(位数组Bitmap<br/>长度m 初始全0)]:::storage
    SET --> ON[将对应位置1<br/>已为1保持不变]
    ON --> DONE1([添加完成]):::success
    Q([查询元素是否存在]):::start --> H2[同样k个哈希函数计算]
    H2 --> IDX[得到k个bit位索引]
    IDX --> CHK{检查所有位}:::decision
    CHK -->|全为1| MAY[可能存在<br/>存在哈希碰撞假阳性]::::error
    CHK -->|有任一为0| NO[一定不存在<br/>真阴性 可靠]:::success
    MAY --> USG{典型用途}:::decision
    USG -->|缓存穿透| CP[请求前过滤<br/>不存在的key直接拒绝]
    USG -->|URL去重| URL[爬虫/短链<br/>海量数据判重]
    USG -->|垃圾邮件| MAIL[黑名单过滤<br/>海量规则匹配]
    USG -->|数据库Block| BLK[HBase/LSM<br/>减少无效磁盘IO]
    SET --> PARA{参数权衡}:::decision
    PARA -->|m越大 k最优| LESS[误判率降低<br/>内存占用增加]
    PARA -->|元素过多| OVERLOAD[误判率上升<br/>需扩容/重建]
    {_common_styles()}
```"""


# ============== 两阶段提交 2PC ==============
def tpl_2pc(meta):
    return """```mermaid
sequenceDiagram
    autonumber
    participant C as 协调者 Coordinator
    participant P1 as 参与者1 Participant
    participant P2 as 参与者2 Participant
    Note over C,P2: === 阶段一: 准备阶段 Prepare/Voting ===
    C->>P1: prepare 询问能否提交
    C->>P2: prepare 询问能否提交
    P1->>P1: 执行事务 写undo/redo log<br/>不提交
    P2->>P2: 执行事务 写undo/redo log<br/>不提交
    P1-->>C: YES 已准备就绪
    P2-->>C: YES 已准备就绪
    Note over C: 协调者收集所有响应
    alt 全部YES
        Note over C,P2: === 阶段二: 提交阶段 Commit ===
        C->>P1: commit 正式提交
        C->>P2: commit 正式提交
        P1->>P1: 提交事务 释放锁
        P2->>P2: 提交事务 释放锁
        P1-->>C: ACK
        P2-->>C: ACK
        Note over C: 事务完成
    else 任一NO 或超时
        C->>P1: rollback 回滚
        C->>P2: rollback 回滚
        P1-->>C: ACK
        P2-->>C: ACK
        Note over C: 事务终止
    end
```"""


# ============== redo/undo/binlog ==============
def tpl_logs(meta):
    return """```mermaid
flowchart TD
    TX([事务执行]):::start --> BUF[修改Buffer Pool数据页]
    BUF --> DIRTY[标记页为dirty<br/>延迟刷盘]
    BUF --> UNDO[(undo log 回滚日志<br/>记录修改前旧值)]:::storage
    BUF --> REDO[(redo log 重做日志<br/>记录修改后新值 WAL先写)]:::storage
    REDO --> FS[顺序写磁盘 fsync<br/>保证持久性]
    UNDO --> FS
    TX --> BIN[(binlog 二进制日志<br/>Server层 记录SQL/行变更)]:::storage
    REDO --> TWOP{两阶段提交 2PC}:::decision
    BIN --> TWOP
    TWOP --> PREPARE[1. redo log prepare状态]
    PREPARE --> WRITE_BIN[2. 写binlog]
    WRITE_BIN --> COMMIT2[3. redo log commit状态]
    COMMIT2 --> OK([崩溃恢复依据<br/>保证redo/binlog一致]):::success
    UNDO --> PURPOSE1[作用: 回滚/MVCC版本链]
    REDO --> PURPOSE2[作用: 崩溃恢复 持久性]
    BIN --> PURPOSE3[作用: 主从复制/数据恢复]
    {_common_styles()}
```"""


# ============== 集群/分片 Redis Cluster ==============
def tpl_redis_cluster(meta):
    return """```mermaid
flowchart TD
    KEY([客户端 SET key value]):::start --> CRC[CRC16计算key哈希]
    CRC --> SLOT[16384个槽位 slot<br/>hash mod 16384]
    SLOT --> OWNER{槽归属?}:::decision
    OWNER --> NODE[(节点A: 槽0~5460<br/>节点B: 槽5461~10922<br/>节点C: 槽10923~16383)]:::storage
    NODE --> MASTER[对应Master处理]
    MASTER --> WRITE[写入并同步给Slave]
    WRITE --> SLAVE[(每主节点配Slave<br/>主从复制高可用)]:::storage
    KEY --> MOVE{key不在本节点?}:::decision
    MOVE -->|是 MOVED重定向| RED[客户端缓存路由表<br/>更新后重试]
    MOVE -->|否 本地处理| MASTER
    MASTER --> DOWN{Master宕机?}:::decision
    DOWN -->|是| FAILOVER[Slave自动故障转移<br/>Gossip协议选举]
    DOWN -->|否| NORMAL[正常服务]:::success
    FAILOVER --> NEW[(新Master接管槽位<br/>继续服务)]:::storage
    {_common_styles()}
```"""


# ============== Spring Boot 嵌入式Tomcat ==============
def tpl_embed_tomcat(meta):
    return """```mermaid
flowchart TD
    START([main方法启动<br/>SpringApplication.run]):::start --> INIT[创建SpringApplication<br/>推断应用类型]
    INIT --> CTX[创建ApplicationContext<br/>AnnotationConfigServletWebServerApplicationContext]
    CTX --> REFRESH[refresh 刷新容器]
    REFRESH --> WEB{Web应用类型?}:::decision
    WEB -->|是 SERVLET| WSC[WebServerFactory<br/>TomcatServletWebServerFactory]
    WEB -->|REACTIVE| NETTY[ReactiveWebServerFactory<br/>Netty]
    WEB -->|NONE| PLAIN[普通应用无容器]
    WSC --> CREATE[创建Tomcat实例<br/>Embedded Tomcat]
    CREATE --> CONFIG[配置Connector端口<br/>设置docBase临时目录]
    CONFIG --> START2[tomcat.start 启动<br/>监听端口默认8080]
    START2 --> DISP[注册DispatcherServlet<br/>映射 /]
    DISP --> BEANS[加载所有Spring Bean<br/>Controller/Service/Repository]
    BEANS --> READY([服务就绪 接收请求]):::success
    PLAIN --> READY2([应用启动完成]):::success
    CONFIG --> ADV{优势}:::decision
    ADV ->|1| A1[无需部署WAR<br/>jar一键启动]
    ADV ->|2| A2[独立运行<br/>DevOps友好]
    ADV ->|3| A3[内嵌简化配置<br/>开箱即用]
    {_common_styles()}
```"""


# ============== Hadoop MapReduce ==============
def tpl_hadoop(meta):
    return """```mermaid
flowchart TD
    JOB([MapReduce作业提交]):::start --> CLIENT[JobClient<br/>打包上传到HDFS]
    CLIENT --> RM[(ResourceManager<br/>YARN资源管理)]:::storage
    RM --> AM[ApplicationMaster<br/>每个作业一个协调者]
    AM --> SPLI[InputFormat切分<br/>InputSplit]
    SPLI --> TASKS[分配Map任务<br/>按分片数]
    TASKS --> NM1[(NodeManager 1<br/>执行Map Task)]:::storage
    TASKS --> NM2[(NodeManager 2<br/>执行Map Task)]::::storage
    NM1 --> READ[读取HDFS数据块<br/>RecordReader解析KV]
    READ --> MAP[用户Map函数<br/>处理生成 &lt;k2,v2&gt;]
    MAP --> SPILL[环形缓冲区溢写<br/>排序+分区+合并]
    SPILL --> SHUFFLE[Shuffle阶段<br/>跨节点拉取数据]
    SHUFFLE --> SORT[按key排序+分组<br/>相同key到同一Reduce]
    SORT --> REDUCE[用户Reduce函数<br/>聚合计算 &lt;k3,v3&gt;]
    REDUCE --> OUT[OutputFormat写出<br/>结果存HDFS]:::success
    {_common_styles()}
```"""


# ============== Spark RDD ==============
def tpl_spark_rdd(meta):
    return """```mermaid
flowchart TD
    SC([SparkContext初始化]):::start --> CREAT{RDD创建方式}:::decision
    CREAT -->|并行化集合| PAR[parallelize 本地集合]
    CREAT -->|外部存储| EXT[textFile HDFS/本地文件]
    CREAT -->|其他RDD转换| TRA[transformation派生]
    PAR --> RDD[(RDD 弹性分布式数据集<br/>不可变 分区 容错)]:::storage
    EXT --> RDD
    TRA --> RDD
    RDD --> OP{操作类型}:::decision
    OP -->|Transformation 转换| TR2[map/filter/groupByKey<br/>懒执行 构建DAG]
    OP -->|Action 行动| AC[collect/count/saveAsTextFile<br/>触发Job提交]
    TR2 --> LINEAGE[记录血缘Lineage<br/>血统依赖窄宽]
    LINEAGE --> NAR{窄依赖 Narrow}:::decision
    NAR -->|是 父分区→子分区1对1| PIPE[管道内pipeline<br/>无需shuffle 快]
    NAR -->|否 宽依赖 Wide| SHUF[shuffle跨节点传输<br/>Stage划分边界]::::async
    AC --> DAG[DAGScheduler<br/>切分Stage]
    DAG --> TASK[TaskScheduler<br/>分发Task到Executor]
    TASK --> EXEC[(Executor执行<br/>多线程跑Task)]:::storage
    EXEC --> FAIL{Task失败?}:::decision
    FAIL -->|是| REC[基于Lineage重算<br/>弹性容错]
    FAIL -->|否| DONE([任务完成返回结果]):::success
    {_common_styles()}
```"""


# ============== Paxos ==============
def tpl_paxos(meta):
    return """```mermaid
sequenceDiagram
    autonumber
    participant P as Proposer 提议者
    participant A1 as Acceptor1 接受者
    participant A2 as Acceptor2
    participant A3 as Acceptor3
    participant L as Learner 学习者
    Note over P,A3: === 阶段一: Prepare 准备 ===
    P->>A1: Prepare(n) 提议编号n
    P->>A2: Prepare(n)
    P->>A3: Prepare(n)
    A1->>P: Promise(n) 承诺不再接受<n的提议
    A2->>P: Promise(n) + 返回已接受过的提议(若有)
    A3->>P: Promise(n) + 返回已接受过的提议(若有)
    Note over P: 收集多数派Majority响应
    alt 多数派承诺
        Note over P,A3: === 阶段二: Accept 接受 ===
        P->>A1: Accept(n, value) value=最高编号已接受值/自己的值
        P->>A2: Accept(n, value)
        P->>A3: Accept(n, value)
        A1->>P: Accepted(n)
        A2->>P: Accepted(n)
        A3->>P: Accepted(n)
        Note over P: 多数派接受=决议通过Chosen
        P->>L: 通知决议结果
        L->>L: 所有Learner学习最终值
        Note over L: 集群达成一致
    else 未达多数派
        Note over P: 提升编号 n+1 重试
    end
```"""


# ============== CAP/BASE ==============
def tpl_cap(meta):
    return """```mermaid
flowchart TD
    DIST([分布式系统]):::start --> CAP[CAP定理<br/>三选二]
    CAP --> C[C 一致性 Consistency<br/>所有节点数据一致]
    CAP --> A[A 可用性 Availability<br/>每个请求都有响应]
    CAP --> P[P 分区容错 Partition tolerance<br/>网络分区仍能工作]
    P --> MUST{网络分区必然发生?}:::decision
    MUST -->|是 P必选| CHOOSE[只能CP或AP二选一]
    MUST -->|否 单机| CA[CA单机系统<br/>RDBMS]
    CHOOSE --> CP{业务场景}:::decision
    CP -->|强一致优先| CP2[CP: 牺牲可用<br/>ZooKeeper/etcd/Redis Cluster<br/>选主/金融交易]
    CP -->|高可用优先| AP2[AP: 牺牲强一致<br/>Cassandra/Eureka/DynamoDB<br/>最终一致 用户系统]
    CP2 --> BASE[BASE理论<br/>工程实践妥协]
    AP2 --> BASE
    BASE --> BA[BA Basically Available<br/>基本可用 降级]
    BASE --> S2[S Soft State<br/>软状态 接受中间态]
    BASE --> E2[E Eventually Consistent<br/>最终一致 异步同步]
    E2 --> REACH{达成最终一致手段}:::decision
    REACH --> MQ3[消息队列异步补偿]
    REACH --> TC[TCC事务 Try-Confirm-Cancel]
    REACH --> CANAL[Canal binlog同步]
    {_common_styles()}
```"""


# ============== Docker ==============
def tpl_docker(meta):
    return """```mermaid
flowchart TD
    DOCKERFILE([Dockerfile构建脚本]):::start --> BUILD[docker build]
    BUILD --> IMG[(镜像Image<br/>分层只读Layer)]:::storage
    IMG --> PUSH[推送镜像仓库<br/>Docker Hub/Harbor]
    PUSH --> REG[(镜像仓库 Registry)]:::storage
    REG --> PULL[目标机器docker pull]
    PULL --> RUN[docker run 启动容器]
    RUN --> CNT[容器Container<br/>可读写层+只读镜像层]
    CNT --> NSP{隔离机制}:::decision
    NSP -->|PID namespace| PID[进程隔离 独立PID]
    NSP -->|NET namespace| NET[网络隔离 独立网卡]
    NSP -->|MNT namespace| MNT[挂载点隔离]
    NSP -->|UTS namespace| UTS[主机名隔离]
    NSP -->|IPC namespace| IPC[信号量/消息队列隔离]
    NSP -->|USER namespace| USER[用户UID隔离]
    NSP --> CG[Control Groups cgroups]
    CG --> LIMIT[限制CPU/内存/IO<br/>资源配额]
    RUN --> UNIONFS{存储驱动}:::decision
    UNIONFS -->|overlay2| OVER[联合挂载<br/>镜像层+容器层叠加]
    OVER --> RW[容器层Copy-On-Write<br/>修改时复制到顶层]
    CNT --> PORT[端口映射 -p 8080:80]
    PORT --> ACCESS([外部访问容器服务]):::success
    {_common_styles()}
```"""


# ============== Kafka Exactly-Once ==============
def tpl_exactly_once(meta):
    return """```mermaid
flowchart TD
    P([Producer生产者]):::start --> PID[分配Producer ID<br/>+递增EpochNumber]
    PID --> SEND[发送消息携带<br/>PID+seq序号]
    SEND --> BRK[(Broker<br/>事务日志transaction log)]:::storage
    BRK --> DEDUP{seq检查}:::decision
    DEDUP ->|重复seq 已存在| DROP[丢弃副本<br/>幂等生产]:::async
    DEDUP ->|新seq| STORE2[持久化记录]
    STORE2 --> TXN{跨分区事务?}:::decision
    TXN ->|是 跨Topic| TC[2PC协调<br/>TransactionCoordinator]
    TXN ->|否 单分区| DONE2[写入完成]
    TC --> PREPARE[Prepare状态<br/>写入所有分区]
    PREPARE --> COMMIT3[COMMIT 提交事务标记]
    COMMIT3 --> CONSUMER([Consumer消费端])
    CONSUMER --> READ{读隔离策略}:::decision
    READ -->|read_committed 推荐| RC3[只读已提交消息<br/>跳过未commit的]
    READ -->|read_uncommitted| RU3[读所有消息<br/>可能读到abort]
    RC3 --> OFFSET[消费+提交offset<br/>原子写入__consumer_offsets]
    OFFSET --> BIZ[业务处理 + 自身输出<br/>端到端EOS]
    BIZ --> ACK2[处理完成 事务关闭]:::success
    {_common_styles()}
```"""


# ============== ES/倒排索引 ==============
def tpl_es(meta):
    return """```mermaid
flowchart TD
    DOC([文档写入Document]):::start --> ANALYZE[Analysis分析器<br/>字符过滤+分词+Token过滤]
    ANALYZE --> TERM[生成词项Term 倒排基础]
    TERM --> INVERT[(倒排索引Inverted Index<br/>Term → DocId列表)]:::storage
    INVERT --> FST[(Term Dictionary<br/>FST有限状态机压缩)]:::storage
    FST --> POST[Posting List 文档ID<br/>+词频+位置+偏移]
    POST --> DOCVAL[(doc_values 列存<br/>排序/聚合用)]:::storage
    Q([查询 "Hello World"]):::start --> QANALYZE[同样分析器分词]
    QANALYZE --> LOOKUP[查Term Dictionary FST]
    LOOKUP --> MATCH{词项存在?}:::decision
    MATCH -->|否| EMPTY[无匹配 空结果]:::error
    MATCH -->|是| FETCH[取Posting List 拉取DocId]
    FETCH --> SCORE{是否打分?}:::decision
    SCORE -->|是 相关性| BM25[BM25/TF-IDF打分<br/>计算文档相关性]
    SCORE -->|否 过滤| FILTER[filter context 不打分<br/>走缓存]
    BM25 --> RANK[按_score排序]
    FILTER --> RANK
    RANK --> SHARD{多分片查询?}:::decision
    SHARD -->|是| GATHER[Coordinator汇总各分片结果<br/>二次排序]
    SHARD -->|否| SINGLE[单分片返回]
    GATHER --> RTN([返回Top-N结果]):::success
    SINGLE --> RTN
    {_common_styles()}
```"""


# ============== LRU缓存 ==============
def tpl_lru(meta):
    return """```mermaid
flowchart TD
    GET([访问key]):::start --> H{缓存命中?}:::decision
    H -->|是| MV[移到链表头部<br/>标记最近使用]:::success
    H -->|否| LOAD[查DB/下游]
    LOAD --> EXIST{数据存在?}:::decision
    EXIST -->|否| MISS[返回空/穿透处理]
    EXIST -->|是| PUT2[写入缓存]
    PUT2 --> FULL{缓存已满?}:::decision
    FULL -->|是| EVICT[淘汰链表尾部<br/>最久未使用LRU]::::error
    FULL -->|否| INSERT[插入链表头部]
    EVICT --> INSERT
    INSERT --> RETN([返回数据]):::success
    MV --> RETN
    MISS --> RETN
    PUT2 --> DATA[(数据结构<br/>HashMap+双向链表)]:::storage
    DATA --> O1[查询/插入/淘汰<br/>均O1 复杂度]
    O1 --> VAR{LRU变体}:::decision
    VAR -->|LRU-K| LRUK[考虑最近K次访问<br/>避免偶然访问污染]
    VAR -->|LFU| LFU[按访问频率<br/>热点数据优先]
    VAR -->|W-TinyLFU| WTL[Count-Min Sketch<br/>过滤突发流量]
    VAR -->|ARC| ARC[自适应调整<br/>LRU+LFU结合]
    {_common_styles()}
```"""


# ============== MySQL Explain/慢SQL ==============
def tpl_slow_sql(meta):
    return """```mermaid
flowchart TD
    SLOW([慢SQL告警<br/>响应慢/CPU高]):::start --> ENABLE[开启慢查询日志<br/>slow_query_log]
    ENABLE --> COLLECT[(收集慢SQL<br/>long_query_time=1s)]:::storage
    COLLECT --> EXPLAIN[EXPLAIN分析执行计划]
    EXPLAIN --> CHECK{关键指标检查}:::decision
    CHECK -->|type=ALL| FULL[全表扫描 红灯]:::error
    CHECK -->|key=NULL| NOIDX[未走索引<br/>需建索引]
    CHECK -->|rows过大| MANY[扫描行数过多<br/>优化条件]
    CHECK -->|Extra Using filesort| SORT[文件排序<br/>需覆盖索引]
    CHECK -->|Extra Using temporary| TMP[临时表<br/>改写SQL]
    FULL --> OPT{优化方向}:::decision
    NOIDX --> OPT
    MANY --> OPT
    OPT -->|加索引| IDX[WHERE/JOIN/ORDER BY列建索引<br/>遵循最左前缀]
    OPT -->|改写SQL| REW[避免SELECT *<br/>limit分页 避免子查询]
    OPT -->|表设计| TBL[大表分区分表<br/>冗余反范式]
    OPT -->|加缓存| CACHE2[Redis缓存热点<br/>减少DB压力]
    IDX --> VERIFY[验证 EXPLAIN再次分析]
    REW --> VERIFY
    TBL --> VERIFY
    CACHE2 --> VERIFY
    VERIFY --> FAST([性能达标 QPS提升]):::success
    {_common_styles()}
```"""


# ============== 可用性/容灾 ==============
def tpl_ha(meta):
    return """```mermaid
flowchart TD
    REQ([用户请求]):::start --> DNS[DNS解析 多IP轮询]
    DNS --> LB[负载均衡 LVS/F5<br/>四层流量分发]
    LB --> NGINX[Nginx 七层反向代理<br/>健康检查 故障剔除]
    NGINX --> SVC[服务集群<br/>多实例部署]
    SVC --> MASTER{主从模式?}:::decision
    MASTER -->|是 主备| MS[主节点写 备节点同步<br/>主挂自动切换VIP]
    MASTER -->|否 多活| MA[多节点同时服务<br/>无单点]
    SVC --> FAIL{实例故障?}:::decision
    FAIL -->|是| HEALTH[健康检查探针<br/>剔除故障实例]
    FAIL -->|否| NORMAL[正常处理]:::success
    HEALTH --> REROUTE[流量转移到健康实例]
    REROUTE --> NORMAL
    MS --> DOWN{主节点宕机?}:::decision
    DOWN -->|是| FAILOVER[Keepalived VIP漂移<br/>Sentinel选主]
    DOWN -->|否| NORMAL
    FAILOVER --> ALERT[告警通知 运维介入]:::async
    NORMAL --> METRIC{SLA指标}:::decision
    METRIC -->|可用性 99.99%| SLA[年停机<53分钟<br/>核心系统目标]
    METRIC -->|RTO 恢复时间| RTO[灾难到恢复服务<br/>分钟级]
    METRIC -->|RPO 数据丢失| RPO[灾难到数据丢失量<br/>秒级 同步复制]
    {_common_styles()}
```"""


# ============== 协程/虚拟线程 ==============
def tpl_virtual_thread(meta):
    return """```mermaid
flowchart TD
    TASK([大量IO任务]):::start --> CHO{并发模型}:::decision
    CHO -->|平台线程 Platform Thread| PT[1:1 操作系统线程<br/>1MB栈 开销大]
    CHO -->|虚拟线程 Virtual Thread| VT[JDK21<br/>M:N调度]
    PT --> BLK1[IO阻塞时<br/>整个OS线程阻塞]:::error
    VT --> CONT[Continuation延续体<br/>用户态保存栈帧]
    CONT --> SCHED[(ForkJoinPool载体线程池<br/>默认CPU核心数)]:::storage
    SCHED --> MOUNT[挂载Mount到载体线程]
    MOUNT --> RUN[在载体线程上运行]
    RUN --> IO{遇到IO阻塞?}:::decision
    IO -->|是| UNMOUNT[卸载Unmount<br/>释放载体线程给其他VT]
    IO -->|否 CPU密集| PIN[钉住pinned<br/>无法卸载 慎用synchronized]:::error
    UNMOUNT --> WAIT2[等待IO完成<br/>不占OS线程]
    WAIT2 --> READY[IO完成 重新入队]
    READY --> SCHED
    PIN --> DONE2[任务完成]:::success
    RUN --> DONE2
    VT --> ADV[百万级虚拟线程<br/>高并发IO场景<br/>代码同同步写法]:::success
    {_common_styles()}
```"""


# ============== Sealed Classes ==============
def tpl_sealed(meta):
    return """```mermaid
flowchart TD
    NEED([需要受限类继承体系]):::start --> CHO{修饰符对比}:::decision
    CHO -->|final| FIN[final类<br/>完全不可继承]
    CHO -->|abstract| ABS[abstract类<br/>任意类可继承 开放]
    CHO -->|sealed| SEA[sealed类<br/>仅许可的子类可继承]
    SEA --> PERMITS[permits关键字<br/>显式列出允许的子类]
    PERMITS --> SUB1[SubClass1 permits内]
    PERMITS --> SUB2[SubClass2 permits内]
    SUB1 --> DECI{子类修饰符}:::decision
    SUB2 --> DECI
    DECI -->|final| FIN2[终结 不能再被继承]
    DECI -->|sealed| SEA2[继续密封 链式约束]
    DECI -->|non-sealed| NS[非密封 任意继承<br/>打开封闭边界]
    SEA --> COMP{与枚举对比}:::decision
    COMP -->|枚举实例固定| ENUM[一组常量<br/>无状态]
    COMP -->|密封类子类| OBJ2[可带状态/行为<br/>面向对象建模]
    SEA --> PATTERN{模式匹配}:::decision
    PATTERN --> SW[switch表达式<br/>编译期穷举检查]
    SW --> CASE1[case SubClass1 -> ...]
    SW --> CASE2[case SubClass2 -> ...]
    SW --> NO_DEFAULT[无需default<br/>覆盖所有情况]:::success
    {_common_styles()}
```"""


# ============== ZGC/Shenandoah GC ==============
def tpl_gc(meta):
    return """```mermaid
flowchart TD
    HEAP([JVM堆内存]):::start --> CHO{GC算法选择}:::decision
    CHO -->|G1| G1[Region分区+SATB<br/>停顿~200ms 主流]
    CHO -->|ZGC| ZGC[着色指针+读屏障<br/>停顿<10ms JDK11+]
    CHO -->|Shenandoah| SH[Brooks指针+并发回收<br/>停顿<10ms JDK12+]
    ZGC --> COLORD[(着色指针Colored Pointers<br/>64位指针高位存状态)]:::storage
    COLORD --> MARK[并发标记<br/>标识存活对象]
    MARK --> RELOC[并发转移<br/>复制存活对象]
    RELOC --> REMAP[并发重映射<br/>更新引用]
    ZGC --> BARRIER[读屏障Load Barrier<br/>访问时修复指针]
    BARRIER --> CONCURRENT[核心阶段全并发<br/>STW仅根扫描]::::async
    SH --> BROOKS[(Brooks指针<br/>每个对象额外1字头)]:::storage
    BROOKS --> CONC2[并发整理内存<br/>压缩避免碎片]
    G1 --> YOUNG[Young GC<br/>Eden+S0/S1 复制]
    YOUNG --> MIXED[Mixed GC<br/>回收年轻代+部分老年代Region]
    MIXED --> FULL{内存严重不足?}:::decision
    FULL -->|是| FULLGC[Full GC STW长<br/>应避免]:::error
    FULL -->|否| STABLE[稳定运行]:::success
    CHO --> CRITERIA{选型标准}:::decision
    CRITERIA -->|低延迟优先| LOW[ZGC/Shenandoah<br/>金融/游戏/实时]
    CRITERIA -->|吞吐量优先| THR[Parallel GC<br/>批处理/离线计算]
    CRITERIA -->|平衡| BAL[G1 JDK9默认<br/>通用服务]
    {_common_styles()}
```"""


# ============== 结构化并发 ==============
def tpl_structured_conc(meta):
    return """```mermaid
flowchart TD
    PARENT([父任务启动]):::start --> SCOPE[StructuredTaskScope<br/>开作用域]
    SCOPE --> SPAWN[启动多个子虚拟线程]
    SPAWN --> T1[子任务1: 查用户服务]
    SPAWN --> T2[子任务2: 查订单服务]
    SPAWN --> T3[子任务3: 查商品服务]
    T1 --> WAIT_ALL[scope.join 等待所有子任务]
    T2 --> WAIT_ALL
    T3 --> WAIT_ALL
    WAIT_ALL --> POLICY{关闭策略 ShutdownPolicy}:::decision
    POLICY -->|AwaitAll| AA[全部等待<br/>收集所有结果]
    POLICY -->|ShutdownOnSuccess| SOS[任一成功则取消其他<br/>竞速场景]:::async
    POLICY -->|ShutdownOnFailure| SOF[任一失败则取消其他<br/>原子性场景]
    SOS --> CANCEL[scope.shutdown<br/>取消未完成子任务]
    SOF --> CANCEL
    AA --> AGG[汇总所有子结果]
    CANCEL --> HANDLE[处理结果或异常]
    AGG --> HANDLE
    HANDLE --> EXIT([作用域退出<br/>所有子线程必然结束]):::success
    SCOPE --> BENEFIT{核心价值}:::decision
    BENEFIT ->|1 可观测性| OBS[子任务生命周期<br/>绑定父作用域]
    BENEFIT ->|2 错误传播| ERR_PROP[子任务异常<br/>自动上报父]
    BENEFIT ->|3 取消传播| CAN[父取消→子全部取消<br/>无泄漏]
    BENEFIT ->|4 资源释放| REL[作用域结束<br/>资源必然释放]
    {_common_styles()}
```"""


# ============== FFM API ==============
def tpl_ffm(meta):
    return """```mermaid
flowchart TD
    JAVA([Java调用本地C库]):::start --> CHO{方案选型}:::decision
    CHO -->|传统JNI| JNI[JNI Java Native Interface<br/>编写.h生成.c 编译]
    CHO -->|FFM JDK21| FFM[Foreign Function & Memory API<br/>纯Java调用]
    JNI --> HEADER[javac -h 生成头文件]
    HEADER --> NATIVE[手写C/C++实现<br/>jniEnv调用]
    NATIVE --> COMPILE[编译成.so/.dll<br/>平台相关]
    COMPILE --> LOAD[System.loadLibrary<br/>绑定native方法]
    LOAD --> CONS1[缺点: 易内存泄漏<br/>平台耦合 API复杂]:::error
    FFM --> LINK[Linker.nativeLinker<br/>获取本地链接器]
    LINK --> LOOKUP[SymbolLookup查找函数<br/>库路径+函数名]
    LOOKUP --> HANDLE2[FunctionHandle 方法句柄<br/>描述C函数签名]
    HANDLE2 --> INVK2[invoke执行调用<br/>类型安全]
    FFM --> MEM[MemorySegment 内存段<br/>安全访问堆外内存]
    MEM --> ALLOC[SemanticAllocator<br/>分配/释放受控]
    ALLOC --> ARENA[Arena作用域<br/>自动释放避免泄漏]:::async
    INVK2 --> ADV[优点: 无需C代码<br/>类型安全 内存可控]
    ARENA --> ADV
    ADV --> USE{典型应用}:::decision
    USE ->|调用C库| CLIB[libc/OpenGL/CUDA<br/>无需包装]
    USE ->|零拷贝| ZERO[堆外内存<br/>直接与本地代码共享]
    {_common_styles()}
```"""


# ============== Switch表达式 ==============
def tpl_switch(meta):
    return """```mermaid
flowchart TD
    VAL([switch表达式输入]):::start --> MOD{语法形式}:::decision
    MOD -->|传统语句| OLD[switch statement<br/>case: + break 易漏break]
    MOD -->|JDK14+ 表达式| NEW[switch expression<br/>返回值 箭头->]
    OLD --> FALL{break遗漏?}:::decision
    FALL -->|是 穿透fall-through| BUG[执行下一个case<br/>逻辑错误]:::error
    FALL -->|否| OK1[正确处理]
    NEW --> ARR[case L --> result<br/>无穿透 自动break]
    ARR --> RTN[返回值直接赋给变量]
    RTN --> YIELD{复杂块?}:::decision
    YIELD -->|是 多行逻辑| YL[yield关键字<br/>显式返回值]
    YIELD -->|否 单表达式| DIRECT[直接箭头返回]
    NEW --> EXH{穷举检查}:::decision
    EXH -->|枚举/sealed所有case| ALL[无需default<br/>编译期检查完整]
    EXH -->|未覆盖| WARN[编译错误<br/>强制处理default]:::async
    NEW --> PAT{模式匹配 JDK21}:::decision
    PAT -->|类型模式| TYPEP[case Integer i -> ...]
    PAT -->|guarded| GUARD[case String s when s.length>0 -> ...]
    PAT -->|null处理| NUL[case null -> ...<br/>避免NPE]
    {_common_styles()}
```"""


# ============== 分布式事务 ==============
def tpl_distributed_tx(meta):
    return """```mermaid
flowchart TD
    BIZ([跨服务业务操作]):::start --> CHO{分布式事务方案}:::decision
    CHO -->|2PC| P2C[XA协议<br/>强一致 阻塞 性能差]
    CHO -->|3PC| P3C[CanCommit+PreCommit+DoCommit<br/>缓解阻塞 仍有不一致]
    CHO -->|TCC| TCC[Try-Confirm-Cancel<br/>业务侵入 最终一致]
    CHO -->|Saga| SAGA[长事务拆分<br/>正反向补偿]
    CHO -->|本地消息表| LMT[DB+MQ<br/>可靠消息最终一致]
    CHO -->|最大努力通知| BTN[多次重试通知<br/>对账兜底]
    P2C --> COORD[(需要协调者<br/>资源管理器锁定)]:::storage
    COORD --> BLOCK[同步阻塞<br/>不适合高并发]:::error
    TCC --> TRY[Try: 预留资源<br/>冻结库存/预扣款]
    TRY --> CMB{业务成功?}:::decision
    CMB -->|是| CONFIRM[Confirm: 确认提交<br/>扣减冻结资源]
    CMB -->|否| CANCEL[Cancel: 释放预留<br/>回滚]
    SAGA --> COMPEN[正向: T1→T2→T3<br/>失败: C3→C2→C1 反向补偿]:::async
    LMT --> LOCAL[(本地DB事务<br/>写业务+消息表)]:::storage
    LOCAL --> MQ3[消息投递MQ]
    MQ3 --> CONSUMER[下游消费 幂等处理]
    BTN --> NOTIFY[主动通知下游<br/>按策略重试N次]
    {_common_styles()}
```"""


# ============== RBAC ==============
def tpl_rbac(meta):
    return """```mermaid
flowchart TD
    U([User用户]):::start --> ROLE[(Role角色<br/>如: 管理员/普通用户)]:::storage
    ROLE --> PERM[(Permission权限<br/>如: user:create)]:::storage
    PERM --> RES[(Resource资源<br/>如: /api/users POST)]:::storage
    U --> AUTH{用户请求资源}:::decision
    AUTH --> INTERCEPT[拦截器/网关<br/>提取用户身份Token]
    INTERCEPT --> LOAD[加载用户角色+权限<br/>缓存加速]
    LOAD --> MATCH{权限匹配?}:::decision
    MATCH -->|是 允许| ALLOW[放行 执行业务]:::success
    MATCH -->|否 拒绝| DENY[返回403 Forbidden]:::error
    ROLE --> ADV{RBAC扩展}:::decision
    ADV -->|RBAC0| B0[基础: User-Role-Permission]
    ADV -->|RBAC1| B1[角色继承<br/>Senior继承Junior权限]
    ADV -->|RBAC2| B2[职责分离<br/>约束: 互斥角色/数量限制]
    ADV -->|RBAC3| B3[1+2 完整模型]
    PERM --> ABAC{ABAC对比}:::decision
    ABAC --> ATT[基于属性Attribute<br/>用户+资源+环境+动作]
    ABAC --> FINE[细粒度<br/>适合复杂规则 灵活但复杂]
    {_common_styles()}
```"""


# ============== Feed流 ==============
def tpl_feed(meta):
    return """```mermaid
flowchart TD
    AUTHOR([作者发布动态]):::start --> SAVE[写入动态DB<br/>MySQL/HBase]
    SAVE --> FANOUT{推送模式}:::decision
    FANOUT -->|推模式 Push| PUSH[写扩散: 遍历粉丝<br/>写入每个粉丝收件箱Redis ZSet]
    FANOUT -->|拉模式 Pull| PULL[读扩散: 用户拉取时<br/>实时聚合关注人最新动态]
    FANOUT -->|推拉结合| HYBRID[普通用户推<br/>大V拉 综合方案]:::async
    PUSH --> INBOX[(粉丝收件箱<br/>Redis ZSet score=时间)]:::storage
    PULL --> QUERY[用户打开Feed时<br/>查关注人最新N条]
    HYBRID --> BIGV{大V判断}:::decision
    BIGV -->|是 粉丝多| LAZY[不推 拉模式<br/>避免写爆炸]
    BIGV -->|否 普通用户| PUSH
    INBOX --> READ([读者打开首页]):::start
    QUERY --> READ
    READ --> PAGINATE[分页查询收件箱<br/>score倒序 时间线]
    PAGINATE --> MERGE{推拉混合?}:::decision
    MERGE -->|是| MGR[合并: 收件箱+大V实时拉取<br/>按时间排序]
    MERGE -->|否| SIMPLE[直接返回收件箱]
    MGR --> FILTER[内容过滤/去重<br/>已读标记]
    SIMPLE --> FILTER
    FILTER --> DISPLAY([展示Feed列表]):::success
    {_common_styles()}
```"""


# ============== IM即时通讯 ==============
def tpl_im(meta):
    return """```mermaid
flowchart TD
    SA([发送方A]):::start --> WS1[建立长连接<br/>WebSocket/TCP]
    WS1 --> AUTH1[登录鉴权<br/>获取connectionId]
    AUTH1 --> SEND[A发送消息<br/>携带接收方B+content]
    SEND --> GW[消息网关<br/>按B的ID路由]
    GW --> SRV[消息服务<br/>处理消息]
    SRV --> SEQ[生成全局递增序列号<br/>保证顺序]
    SEQ --> STORE2[(消息存储<br/>MySQL+HBase+ES搜索)]:::storage
    STORE2 --> ONLINE{B在线?}:::decision
    ONLINE -->|是 同一网关| PUSH2[实时推送给B<br/>WebSocket frame]
    ONLINE -->|是 不同网关| ROUTE[通过用户路由表<br/>找到B所在网关推送]
    ONLINE -->|否 离线| OFF[(离线存储<br/>Redis/MQ待推送)]:::storage
    PUSH2 --> RB([接收方B收到])
    OFF --> NOTIFY[B下次上线时<br/>拉取未读消息]
    ROUTE --> RB
    RB --> ACK[已读回执<br/>更新已读位置]
    ACK --> READ{群聊?}::::decision
    READ -->|是 群消息| GROUP[写扩散/收件箱<br/>每个成员seq独立]
    READ -->|否 单聊| DONE2([消息送达完成]):::success
    GROUP --> DONE2
    STORE2 --> SEARCH[(ES建立索引<br/>支持历史搜索)]:::storage
    {_common_styles()}
```"""


# ============== 推荐系统 ==============
def tpl_recommend(meta):
    return """```mermaid
flowchart TD
    USER([用户访问APP]):::start --> REQ[推荐请求<br/>携带userId/deviceId]
    REQ --> RECALL[召回Recall<br/>从亿级item初筛千级]
    RECALL --> STRATEGY{召回策略}:::decision
    STRATEGY -->|协同过滤| CF[基于用户/物品相似<br/>UserCF/ItemCF]
    STRATEGY -->|内容召回| CB[基于标签/向量<br/>item embedding]
    STRATEGY -->|热门/新品| HOT[运营配置/实时热度]
    STRATEGY -->|深度学习| DL[DSSM双塔模型<br/>向量近邻检索]:::async
    CF --> MERGE[多路召回合并<br/>去重约1000个候选]
    CB --> MERGE
    HOT --> MERGE
    DL --> MERGE
    MERGE --> FILTER[粗排过滤<br/>已读/地域/合规]
    FILTER --> RANK{排序阶段}:::decision
    RANK -->|粗排| ROUGH[简单模型<br/>千→百 快]
    RANK -->|精排| FINE2[复杂深度模型<br/>百→几十 准]
    FINE2 --> FEATURE[特征工程<br/>用户画像+物品特征+上下文]
    FEATURE --> MODEL[训练好的模型<br/>DIN/DeepFM/多任务]
    MODEL --> SCORE2[计算CTR/CVR预测分]
    SCORE2 --> RERANK[重排序Re-rank<br/>多样性/新鲜度/业务规则]
    RERANK --> RTN([返回Top-N推荐列表]):::success
    RTN --> FB[用户行为反馈<br/>点击/停留/购买]
    FB --> LOG[(日志收集 Kafka<br/>样本回流)]:::storage
    LOG --> TRAIN[模型离线/在线训练<br/>持续迭代优化]
    {_common_styles()}
```"""


# ============== ES数据同步 ==============
def tpl_sync_es(meta):
    return """```mermaid
flowchart TD
    MYSQL[(MySQL业务库<br/>增删改数据)]:::storage --> BIN2[binlog变更日志]
    BIN2 --> CANAL[Canal监听<br/>伪装MySQL Slave]
    CANAL --> MQ2[(消息队列 Kafka/MQ<br/>削峰缓冲)]:::storage
    MQ2 --> CONSUMER[同步消费者]
    CONSUMER --> TRANSFORM[数据转换<br/>MySQL行→ES Document]
    TRANSFORM --> ES2[(Elasticsearch<br/>建立倒排索引)]::::storage
    ES2 --> SEARCH2[全文检索/聚合分析]
    MYSQL --> COMP{数据补偿}:::decision
    COMP -->|全量同步| FULL2[定时任务<br/>全表扫描重建]
    COMP -->|增量同步| CANAL
    FULL2 --> ES2
    CANAL --> FAIL{同步失败?}:::decision
    FAIL -->|是 网络抖动| RETRY3[重试/死信队列<br/>保证不丢]
    FAIL -->|否 正常| OK3[继续监听]
    RETRY3 --> RECON[对账机制<br/>定期全量校验]
    RECON --> CONSISTENT([MySQL与ES<br/>秒级最终一致]):::success
    {_common_styles()}
```"""


# ============== 熔断降级 ==============
def tpl_circuit_breaker(meta):
    return """```mermaid
flowchart TD
    REQ2([服务调用请求]):::start --> CB{熔断器状态}:::decision
    CB -->|CLOSED 关闭 正常| CALL[发起远程调用]
    CALL --> RES{调用结果}:::decision
    RES -->|成功| SUCC2[返回结果<br/>成功计数++]
    RES -->|失败/超时| FAIL2[失败计数++]
    SUCC2 --> RATE{失败率>阈值?}:::decision
    FAIL2 --> RATE
    RATE -->|是 50%| OPEN[切换到OPEN 打开<br/>拒绝所有请求]::::error
    RATE -->|否| CLOSED2[保持CLOSED]
    CB -->|OPEN 打开 熔断中| REJECT2[快速失败<br/>走降级逻辑 fallback]
    REJECT2 --> DEGRADE{降级策略}:::decision
    DEGRADE -->|默认值| DEF[返回缓存/默认数据]
    DEGRADE -->|限流| RL2[部分请求拒绝]
    DEGRADE -->|人工兜底| MAN[静态页面/提示]
    DEF --> RTN2([业务可用 但功能降级]):::success
    CB -->|HALF_OPEN 半开试探| PROBE[放行少量探测请求]
    PROBE --> PROBERES{探测结果?}:::decision
    PROBERES -->|成功 恢复| CLOSE3[切换回CLOSED<br/>恢复全量]
    PROBERES -->|失败 仍有问题| BACK[切回OPEN<br/>继续熔断]
    OPEN --> TIMER[等待冷却时间<br/>5~30s]
    TIMER --> HALF[切换到HALF_OPEN]
    HALF --> PROBE
    {_common_styles()}
```"""


# ============== 多级缓存 ==============
def tpl_multi_cache(meta):
    return """```mermaid
flowchart TD
    REQ3([查询请求]):::start --> L1C[浏览器/APP本地缓存<br/>HTTP Cache-Control]
    L1C --> L1H{命中?}:::decision
    L1H -->|是| RTN3[直接返回 零网络]:::success
    L1H -->|否| CDN[CDN边缘节点<br/>静态资源就近]
    CDN --> CDNH{命中?}:::decision
    CDNH -->|是| RTN4[就近返回 快]:::success
    CDNH -->|否| NG2[Nginx本地缓存<br/>proxy_cache]
    NG2 --> NGH{命中?}:::decision
    NGH -->|是| RTN5[返回 减少回源]:::success
    NGH -->|否| APP2[应用本地缓存<br/>Caffeine/Guava]
    APP2 --> APH{命中?}:::decision
    APH -->|是| RTN6[JVM内返回 纳秒级]::::success
    APH -->|否| REDIS3[Redis分布式缓存]
    REDIS3 --> RDH{命中?}:::decision
    RDH -->|是| RTN7[返回 微秒级]:::success
    RDH -->|否| DB3[(MySQL数据库<br/>源头数据)]:::storage
    DB3 --> BACK3[回写多级缓存<br/>设置TTL防雪崩]:::async
    BACK3 --> RTN8([返回数据]):::success
    REQ3 --> SYNC{缓存更新策略}:::decision
    SYNC -->|Cache Aside| CA2[读miss回写<br/>写时删除]
    SYNC -->|binlog订阅| BIN3[Canal监听DB<br/>异步刷新各级]
    SYNC -->|定时刷新| TM2[定时任务主动刷新<br/>热点数据]
    {_common_styles()}
```"""


# ============== 异地多活 ==============
def tpl_multi_active(meta):
    return """```mermaid
flowchart TD
    USER2([用户访问]):::start --> GSLB[全局负载均衡GSLB<br/>DNS/HTTPDNS智能解析]
    GSLB --> REGION{就近接入}:::decision
    REGION -->|北京机房| BJ[(北京数据中心<br/>完整服务+数据)]:::storage
    REGION -->|上海机房| SH[(上海数据中心<br/>完整服务+数据)]:::storage
    REGION -->|广州机房| GZ[(广州数据中心<br/>完整服务+数据)]:::storage
    BJ --> SYNC2{数据同步}:::decision
    SH --> SYNC2
    GZ --> SYNC2
    SYNC2 -->|异步最终一致| ASYNC[Otter/DTS<br/>秒级延迟]
    SYNC2 -->|强一致| STRONG[同步复制<br/>Paxos/Raft]
    ASYNC --> CONFLICT{写冲突?}:::decision
    CONFLICT -->|是 同一记录多地写| RESOLVE[按时间戳/业务规则<br/>冲突解决]
    CONFLICT -->|否 单元化| UNIT[按用户ID分片<br/>同一用户固定一地写]
    UNIT --> MASTER3[每用户单写主节点<br/>避免双主冲突]:::success
    REGION --> DOWN2{机房故障?}:::decision
    DOWN2 -->|是 整机房挂| FAILOVER3[GSLB切换流量<br/>DNS收敛到其他机房]
    DOWN2 -->|否| NORMAL3[正常服务]
    FAILOVER3 --> RECOVER[故障机房恢复<br/>增量数据补偿]
    USER2 --> CORE{核心挑战}:::decision
    CORE -->|数据同步延迟| DELAY[业务容忍<br/>秒级延迟]
    CORE -->|流量分配| TRAFFIC[基于用户地理位置<br/>就近接入]
    CORE -->|单元化部署| CELL[按用户维度拆分<br/>故障隔离]
    {_common_styles()}
```"""


# ============== 通用类：放在最后兜底 ==============
def tpl_generic(meta):
    title = (meta.get('title', '') or '业务场景')[:30]
    body = """```mermaid
flowchart TD
    IN([输入: TITLE_PLACEHOLDER]):::start --> CORE[核心处理逻辑]
    CORE --> CHK{关键判断}:::decision
    CHK -->|条件A| A[处理路径A]
    CHK -->|条件B| B[处理路径B]
    CHK -->|异常| ERR[异常处理/降级]:::error
    A --> STORE[(状态/数据存储)]:::storage
    B --> STORE
    STORE --> OUT[输出结果]:::success
    CORE --> FEAT{关键特性}:::decision
    FEAT -->|优势| ADV1[性能/效率提升]
    FEAT -->|约束| ADV2[边界条件/注意事项]:::async
""" + _common_styles() + "\n```"""
    return body.replace('TITLE_PLACEHOLDER', title)


# ---------------------------------------------------------------------------
# 模板路由：根据 id 前缀和 title/essence 关键词匹配
# ---------------------------------------------------------------------------

# (关键词列表, 模板函数) - 按优先级匹配 title 或 essence
# 关键词都小写，对title+essence拼接后小写匹配
TEMPLATES = [
    # ---- Spring MVC 注解 ----
    (['mvc', '注解', '@restcontroller', '@requestmapping', '@controller', 'spring mvc'], tpl_spring_mvc),
    # ---- 网络协议 ----
    (['mvc注解', '常用注解'], tpl_spring_mvc),
    (['三次握手', '四次挥手'], tpl_3way_4way),
    (['三次握手'], tpl_3way),
    (['time_wait', '2msl'], tpl_time_wait),
    (['keep-alive', 'keepalive', 'keep_alive', 'keep alive'], tpl_keepalive_compare),
    (['tcp保活', 'tcp keepalive'], tpl_tcp_keepalive),
    (['http/1.1', 'http1.1', 'http 1.1'], tpl_http11),
    (['http原理'], tpl_http_principle),
    (['http特性'], tpl_http_feature),
    (['tcp/ip', 'tcpip'], tpl_tcp_ip),
    (['tcp与udp', 'tcp udp', 'tcp/udp'], tpl_tcp_udp),
    (['tcp', 'udp'], tpl_tcp_udp),
    (['select', 'poll', 'epoll'], tpl_epoll),
    (['dns解析', 'dns'], tpl_dns),
    (['半连接队列', 'syn队列', 'syn flood'], tpl_syn_queue),
    (['拥塞发生', '拥塞控制', '快重传', '快恢复'], tpl_congestion),
    (['拥塞避免'], tpl_congestion),
    (['滑动窗口', '接收方滑动窗口'], tpl_sliding_window),
    (['url和uri', 'url', 'uri'], tpl_url_uri),
    (['cookie'], tpl_cookie),
    (['get和post', 'get/post', 'get post'], tpl_get_post),
    # ---- 操作系统 ----
    (['内存分段', '内存分页', '分段和分页', '分页分段'], tpl_paging),
    (['linux虚拟内存', 'linux 虚拟内存'], tpl_linux_vm),
    (['虚拟内存'], tpl_virtual_memory),
    (['linux网络'], tpl_linux_net),
    (['osi', '七层'], tpl_osi),
    (['程序执行流程'], tpl_program_flow),
    (['页面置换', 'lru', 'fifo', '置换算法'], tpl_page_replace),
    (['进程调度', '调度算法'], tpl_schedule),
    (['用户态', '核心态', '内核态'], tpl_user_kernel),
    (['进程同步', '进程互斥', 'pv操作', '同步互斥'], tpl_sync_mutex),
    (['文件系统'], tpl_filesystem),
    (['文件系统的实现'], tpl_fs_impl),
    (['缓存机制', 'cpu缓存', 'l1 cache', 'cache机制'], tpl_cache_mechanism),
    (['编译系统', '编译过程'], tpl_compile),
    # ---- Java基础 ----
    (['基础数据类型', '基本数据类型', 'java数据类型'], tpl_java_type),
    (['finally'], tpl_finally),
    (['异常分类', 'java异常', 'exception'], tpl_exception),
    (['多态'], tpl_polymorphism),
    (['面向对象', 'oop'], tpl_oop),
    (['泛型擦除', '泛型', 'type erasure'], tpl_generic_erasure),
    (['string为什么', 'string不可变', 'string存储'], tpl_string_immutable),
    (['string存储原理'], tpl_redis_string),
    (['equals', 'hashcode'], tpl_equals_hash),
    (['switch表达式', 'switch语句'], tpl_switch),
    (['排序二叉树', 'bst', '二叉搜索树'], tpl_bst),
    (['treemap'], tpl_treemap),
    (['归并排序'], tpl_merge_sort),
    # ---- Java集合 ----
    (['hashmap jdk', 'hashmap底层', 'hashmap 8', 'hashmapjdk'], tpl_hashmap8),
    (['map put', 'put过程'], tpl_map_put),
    (['集合框架', 'collection'], tpl_collection),
    (['list和map', 'list map'], tpl_list_map),
    (['queue接口', 'queue'], tpl_queue),
    (['阻塞队列', 'blockingqueue'], tpl_blocking_queue),
    (['delayqueue', '延迟队列缓存'], tpl_delay_queue),
    # ---- Java并发 ----
    (['synchronized', '锁升级'], tpl_lock_upgrade),
    (['virtual threads', '虚拟线程', 'loom'], tpl_virtual_thread),
    (['project loom', '结构化并发', 'structured concurrency'], tpl_structured_conc),
    (['sealed', '密封类'], tpl_sealed),
    (['zgc', 'shenandoah', 'gc选择', '垃圾回收'], tpl_gc),
    (['ffm', 'foreign function', 'jni'], tpl_ffm),
    # ---- Java IO/NIO ----
    (['java nio', 'selector', 'nio selector'], tpl_selector),
    (['字节输入流', 'inputstream', '输入流'], tpl_input_stream),
    (['java rmi', 'rmi'], tpl_rmi),
    (['protocol buffer', 'protobuf'], tpl_protobuf),
    # ---- 设计模式 ----
    (['代理模式'], tpl_proxy),
    (['单例模式', '单例的应用'], tpl_singleton),
    (['工厂模式'], tpl_factory),
    (['装饰模式', '装饰器'], tpl_decorator),
    (['观察者模式'], tpl_observer),
    # ---- Spring Boot ----
    (['嵌入式tomcat', '嵌入式 tomcat', '嵌入式'], tpl_embed_tomcat),
    # ---- 加密/安全 ----
    (['摘要算法', '数字签名'], tpl_signature),
    (['混合加密'], tpl_hybrid),
    (['对称加密'], tpl_symmetric),
    (['rsa', '非对称加密'], tpl_rsa),
    (['证书信任链', '证书链'], tpl_cert_chain),
    # ---- 数据库索引 ----
    (['b+树', 'b+ 树', 'b+树来作索引', '索引底层', 'mysql索引', 'b+树索引', 'mysql为什么'], tpl_db_index),
    (['回表', '索引覆盖', '覆盖索引'], tpl_db_index),
    (['联合索引', '最左前缀'], tpl_db_index),
    (['意向锁', 'mdl锁'], tpl_db_index),
    (['聚簇索引', '非聚簇索引'], tpl_db_index),
    (['索引下推'], tpl_db_index),
    (['explain', '查看一个sql', '使用索引'], tpl_db_index),
    (['索引有哪些', '索引种类', '索引类别'], tpl_db_index),
    (['查询效率'], tpl_db_index),
    (['主键', '索引', '外键'], tpl_db_index),
    # ---- 数据库事务 ----
    (['acid', '事务的四大特性'], tpl_acid),
    (['mvcc', '多版本并发控制', 'readview', 'read view'], tpl_mvcc),
    (['幻读', '隔离级别'], tpl_db_transaction),
    (['两阶段提交', '2pc'], tpl_2pc),
    (['分布式事务'], tpl_distributed_tx),
    (['事务的启动方式', '事务启动'], tpl_db_transaction),
    (['事务的四大'], tpl_acid),
    # ---- 数据库日志 ----
    (['redo log', 'undo log', 'binlog', '日志文件', '三种日志'], tpl_logs),
    # ---- 数据库存储引擎 ----
    (['innodb', 'myisam', '存储引擎'], tpl_db_index),
    (['分库分表'], tpl_sharding),
    (['mysql架构升级'], tpl_sharding),
    (['直方图'], tpl_db_index),
    # ---- 数据库锁 ----
    (['mysql有哪些锁', 'mysql锁'], tpl_db_transaction),
    # ---- Redis ----
    (['redis为什么快'], tpl_redis_cluster),
    (['redis切片集群', 'redis集群', 'redis cluster'], tpl_redis_cluster),
    (['redis数据类型', 'redis类型'], tpl_redis_type),
    (['redis缓存', 'redis的主要功能'], tpl_redis_type),
    (['string存储'], tpl_redis_string),
    (['aof', '磁盘重写', 'aof的磁盘'], tpl_redis_persist),
    (['rdb', '持久化方式', 'redis 持久化'], tpl_redis_persist),
    (['混合持久化'], tpl_redis_persist),
    (['内存淘汰策略', '过期策略', '淘汰策略'], tpl_redis_persist),
    (['布隆过滤器'], tpl_bloom),
    (['缓存穿透'], tpl_cache_penetrate),
    (['缓存雪崩'], tpl_cache_penetrate),
    (['缓存'], tpl_cache_consistency),
    (['哨兵', 'sentinel'], tpl_redis_cluster),
    (['跳表', 'zset'], tpl_redis_type),
    (['redis 6.0', '多线程'], tpl_redis_cluster),
    (['bigkey'], tpl_redis_type),
    (['bitmap'], tpl_redis_type),
    (['redis实现分布式锁', 'redis分布式锁'], tpl_distributed_lock),
    (['分布式锁'], tpl_distributed_lock),
    # ---- MySQL其他 ----
    (['主从复制'], tpl_replication),
    (['三范式', '反范式'], tpl_db_index),
    (['表连接', 'join'], tpl_db_index),
    (['深度分页'], tpl_db_index),
    (['count(*)', 'count(1)', 'count('], tpl_db_index),
    (['用户权限控制', '权限管理', 'rbac', 'abac'], tpl_rbac),
    (['慢sql', '慢查询'], tpl_slow_sql),
    (['sql多表查询'], tpl_slow_sql),
    (['数据库三范式'], tpl_db_index),
    (['第二范式'], tpl_db_index),
    # ---- ES/搜索 ----
    (['elasticsearch', 'es ', '倒排索引', 'fst'], tpl_es),
    (['es数据同步', 'mysql数据同步'], tpl_sync_es),
    (['全文搜索', '搜索引擎'], tpl_es),
    # ---- 分布式 ----
    (['可用性', 'cap', 'base'], tpl_cap),
    (['paxos'], tpl_paxos),
    (['分布式id', 'snowflake', '号段', 'uuid'], tpl_distributed_id),
    (['延迟队列'], tpl_delay_queue_sys),
    (['docker'], tpl_docker),
    (['kafka', '消息不丢失', 'exactly-once', '消息队列'], tpl_exactly_once),
    (['消息的可靠投递', '消息积压'], tpl_mq),
    (['消息队列'], tpl_mq),
    # ---- 大数据 ----
    (['hadoop', 'mapreduce'], tpl_hadoop),
    (['spark rdd', 'spark'], tpl_spark_rdd),
    (['spark streaming'], tpl_spark_rdd),
    (['mllib'], tpl_spark_rdd),
    (['storm'], tpl_spark_rdd),
    (['spark sql'], tpl_spark_rdd),
    # ---- 场景设计：系统类 ----
    (['短链系统', '短url', '短链'], tpl_short_url),
    (['秒杀系统'], tpl_seckill),
    (['绝不超卖', '超卖', '库存扣减'], tpl_seckill),
    (['限流方案', '令牌桶', '漏桶', '限流系统'], tpl_rate_limit),
    (['熔断降级', '熔断'], tpl_circuit_breaker),
    (['缓存一致性', '缓存与数据库'], tpl_cache_consistency),
    (['多级缓存'], tpl_multi_cache),
    (['lru缓存', '热点数据缓存', '缓存方案'], tpl_lru),
    (['异地多活'], tpl_multi_active),
    (['高可用', '可用性a', '注册中心'], tpl_ha),
    (['推荐系统', '个性化推荐'], tpl_recommend),
    (['feed流', '信息流'], tpl_feed),
    (['im系统', '即时通讯', '消息已读未读'], tpl_im),
    (['消息通知中心', '通知'], tpl_im),
    (['扫码登录'], tpl_qr_login),
    (['延迟队列系统'], tpl_delay_queue_sys),
    (['分布式id生成'], tpl_distributed_id),
    (['红包', '抢红包'], tpl_seckill),
    (['点赞系统', '弹幕系统', '红包雨'], tpl_feed),
    (['评论系统', '朋友圈', '动态系统'], tpl_feed),
    (['搜索建议', '热词'], tpl_es),
    (['认证授权', 'sso', 'oauth2', 'jwt'], tpl_rbac),
    (['验证码'], tpl_rbac),
    (['session'], tpl_rbac),
    (['敏感数据加密', '脱敏'], tpl_rbac),
    (['web安全', 'xss', 'csrf', 'ssrf', 'sql注入', '防刷'], tpl_rbac),
    (['接口安全', '防重放', '防爬虫'], tpl_rbac),
    (['优惠券', '秒杀系统'], tpl_seckill),
    (['分布式定时任务'], tpl_delay_queue_sys),
    (['协同编辑'], tpl_feed),
    (['在线状态'], tpl_im),
    (['蓝绿部署', '金丝雀'], tpl_docker),
    (['容量评估'], tpl_ha),
    (['故障自愈', '自愈'], tpl_ha),
    (['配置中心'], tpl_multi_cache),
    (['链路追踪'], tpl_ha),
    (['数据一致性', 'cqrs', '事件驱动'], tpl_cache_consistency),
    (['service mesh', '服务网格', 'istio'], tpl_ha),
    (['数据迁移'], tpl_multi_active),
    (['中台'], tpl_scenario_system),
    (['优雅上下线', '热更新'], tpl_ha),
    (['技术选型'], tpl_scenario_system),
    (['商品详情页', '商品搜索'], tpl_scenario_system),
    (['网关限流'], tpl_rate_limit),
    (['支付系统', '幂等'], tpl_scenario_system),
    (['冷热分离', '海量数据存储'], tpl_sharding),
    (['搜索系统', '索引重建'], tpl_es),
    (['异步通知'], tpl_mq),
    # ---- 拼多多/字节面经类 ----
    (['redisbitmap'], tpl_redis_type),
    (['ai agent', 'web应用和ai'], tpl_scenario_system),
    # ---- 通用兜底 ----
    ([], tpl_generic),
]


def pick_template(meta):
    """Pick the best template based on title+essence keywords."""
    title = (meta.get('title', '') or '').lower()
    essence = (meta.get('essence', '') or '').lower()
    text = title + ' || ' + essence
    for keywords, template_fn in TEMPLATES:
        if not keywords:
            continue
        for kw in keywords:
            if kw in text:
                return template_fn
    # Fall through to last (generic) template
    return TEMPLATES[-1][1]


# ---------------------------------------------------------------------------
# Mermaid sanitizer
# ---------------------------------------------------------------------------
# Wraps node labels in double quotes when they contain chars that would
# confuse Mermaid's flowchart parser (@, /, (, ), [, ], {, }, ", |).

_PROBLEM_CHARS_RE = re.compile(r'[@()\[\]{}"|/\\<>]')

# Multi-char shape openers (order matters: longest/most-specific first).
# Each entry is (opener_regex, closer_regex).
_SHAPES = [
    (r'\(\[', r'\]\)'),     # stadium     ([text])
    (r'\[\(', r'\)\]'),     # cylinder    [(text)]
    (r'\[\[', r'\]\]'),     # subroutine  [[text]]
    (r'\(\(', r'\)\)'),     # circle      ((text))
    (r'\{\{', r'\}\}'),     # hexagon     {{text}}
    (r'\[', r'\]'),         # rectangle   [text]
    (r'\(', r'\)'),         # round       (text)
    (r'\{', r'\}'),         # diamond     {text}
]


def _needs_quoting(text):
    cleaned = re.sub(r'<[^>]+>', '', text)
    return bool(_PROBLEM_CHARS_RE.search(cleaned))


def _quote_label(text):
    # Mermaid uses #quot; for an escaped quote inside a quoted label.
    # Don't double-escape if already #quot;.
    if '"' in text and '#quot;' not in text:
        text = text.replace('"', '#quot;')
    return '"' + text + '"'


_ARROW_RE = re.compile(r'(-->|-\.-|-\->|--|==>|->|~~~|<--)\s*\|([^|]*)\|')


def _fix_arrow_label(m):
    arrow = m.group(1)
    text = m.group(2)
    # Strip out chars that confuse the parser inside arrow labels.
    if _PROBLEM_CHARS_RE.search(text):
        text = re.sub(r'[@\[\]{}()]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
    return arrow + '|' + text + '|'


def _sanitize_line(line):
    stripped = line.strip()
    if not stripped:
        return line
    # Skip directive / style / subgraph / sequence-only lines.
    if stripped.startswith(('classDef', 'style ', 'linkStyle', 'class ',
                            '%%', 'direction', 'subgraph', 'end',
                            'participant', 'Note', 'alt', 'else', 'loop',
                            'rect', 'autonumber', 'sequenceDiagram',
                            'flowchart', 'graph')):
        return line

    # Fix arrow labels first.
    line = _ARROW_RE.sub(_fix_arrow_label, line)

    # Now walk through the line and quote any node shape label that needs it.
    out = []
    i = 0
    n = len(line)
    while i < n:
        m_id = re.match(r'[A-Za-z_][A-Za-z0-9_]*', line[i:])
        if m_id:
            id_str = m_id.group(0)
            id_end = i + len(id_str)
            matched = False
            for opener_re, closer_re in _SHAPES:
                m_op = re.match(opener_re, line[id_end:])
                if m_op:
                    opener = m_op.group(0)
                    content_start = id_end + len(opener)
                    closer_pat = re.compile(closer_re)
                    # Find the LAST occurrence of the closer on this line.
                    # Mermaid parses greedily when label is quoted, so we want
                    # the closing bracket that's followed by either :::, end of
                    # line, or arrow chars.
                    candidates = list(closer_pat.finditer(line, content_start))
                    if not candidates:
                        continue
                    # Pick the last candidate whose position is followed by a
                    # valid terminator (:::, -->, whitespace-then-end, |).
                    chosen = None
                    for cand in reversed(candidates):
                        tail = line[cand.end():]
                        if (not tail or tail.startswith(('::', ' ', '\t',
                                '-->', '->', '-.->', '~', '|', '#'))) :
                            chosen = cand
                            break
                    if chosen is None:
                        chosen = candidates[-1]
                    label = line[content_start:chosen.start()]
                    close_str = chosen.group(0)
                    new_label = _quote_label(label) if _needs_quoting(label) else label
                    out.append(id_str + opener + new_label + close_str)
                    i = chosen.end()
                    matched = True
                    break
            if matched:
                continue
            out.append(id_str)
            i = id_end
            continue
        out.append(line[i])
        i += 1
    return ''.join(out)


def sanitize_mermaid(block):
    """Apply sanitization to a mermaid block. Skips sequenceDiagram blocks."""
    lines = block.split('\n')
    if lines and lines[0].strip().startswith('sequenceDiagram'):
        return block
    return '\n'.join(_sanitize_line(l) for l in lines)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def process(path):
    text = read(path)
    if '```mermaid' in text:
        return False, 'skip-existing'

    meta = parse_frontmatter(text)
    if not meta:
        return False, 'no-frontmatter'

    template_fn = pick_template(meta)
    mermaid = template_fn(meta).rstrip()
    # Substitute the common styles placeholder.
    mermaid = mermaid.replace('{_common_styles()}', _common_styles())
    # Sanitize the mermaid block so labels with special chars don't break the parser.
    mermaid = sanitize_mermaid(mermaid)

    # 构造插入块
    block = f"\n## 核心流程图\n\n{mermaid}\n"

    # 选择锚点
    if '## 记忆要点' in text:
        anchor = '## 记忆要点'
        new_text = text.replace(anchor, block + anchor, 1)
    elif '## 结构化回答' in text:
        anchor = '## 结构化回答'
        new_text = text.replace(anchor, block + anchor, 1)
    elif '## 视频脚本' in text:
        anchor = '## 视频脚本'
        new_text = text.replace(anchor, block + anchor, 1)
    else:
        # 末尾追加
        new_text = text.rstrip() + '\n' + block

    write(path, new_text)
    return True, template_fn.__name__


def main():
    cats = ['java-core', 'database', 'scenario']
    total_files = 0
    inserted = 0
    skipped = 0
    errors = []
    template_usage = {}

    for cat in cats:
        d = os.path.join(ROOT, 'questions', cat)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.endswith('.md'):
                continue
            path = os.path.join(d, f)
            total_files += 1
            try:
                ok, info = process(path)
                if ok:
                    inserted += 1
                    template_usage[info] = template_usage.get(info, 0) + 1
                else:
                    skipped += 1
            except Exception as e:
                errors.append(f'{path}: {e}')

    print(f'\n========== 统计 ==========')
    print(f'总文件数: {total_files}')
    print(f'已插入: {inserted}')
    print(f'已跳过(已有mermaid): {skipped}')
    print(f'错误: {len(errors)}')
    if errors:
        print('\n错误列表:')
        for e in errors[:30]:
            print(f'  {e}')

    print(f'\n模板使用分布:')
    for t, c in sorted(template_usage.items(), key=lambda x: -x[1]):
        print(f'  {t}: {c}')


if __name__ == '__main__':
    main()
