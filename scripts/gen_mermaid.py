#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为 interview-2026 项目中没有 mermaid 图的面试题生成详细的 mermaid 流程图。
工作目录：/Users/sunqingguang/hermes/opt/projects/interview-2026

用法：
    cd /Users/sunqingguang/hermes/opt/projects/interview-2026
    python3 scripts/gen_mermaid.py            # 处理范围内所有缺失 mermaid 的文件
    python3 scripts/gen_mermaid.py --dry-run  # 仅打印统计不写入
    python3 scripts/gen_mermaid.py --limit 10 # 只处理前 10 个（测试用）
"""
import os
import re
import sys
import argparse
import hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCOPE_DIRS = {
    'ai-agent', 'ai-harness', 'ai-basics', 'ai-scenario',
    'java-architect', 'eng-practice', 'system-design',
    'middleware', 'framework', 'fde', 'java', 'ant-risk',
    'boss-ai', 'pdd-ai', 'pdd-content', 'pdd-scm', 'pdd-trade',
    'biopharm', 'network', 'frontend', 'algorithm',
}

# ---------------------------------------------------------------------------
# Frontmatter 解析（轻量级，不依赖 PyYAML 以保证离线运行）
# ---------------------------------------------------------------------------

FM_RE = re.compile(r'^---\n(.*?)\n---\n', re.DOTALL)


def _strip_inline(s):
    """移除行内 YAML 注释、引号、首尾空白"""
    if s is None:
        return ''
    s = str(s)
    # 去掉行内注释 # ...
    s = re.sub(r'(?<!\\)#.*$', '', s)
    s = s.strip()
    if len(s) >= 2 and s[0] in '"\'' and s[-1] == s[0]:
        s = s[1:-1]
    return s.strip()


def parse_frontmatter(content):
    m = FM_RE.match(content)
    if not m:
        return {}
    body = m.group(1)
    data = {}
    cur_key = None
    cur_list = None
    cur_sub = None  # 当前二级 dict key
    # 按行解析，简化版
    for raw in body.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        # 顶层 key:
        tm = re.match(r'^([\w\-]+):\s*(.*)$', line)
        # 列表项
        li = re.match(r'^\s*-\s+(.*)$', line)
        sli = re.match(r'^\s{4,}([\w\-]+):\s*(.*)$', line)
        if li and cur_list is not None:
            cur_list.append(_strip_inline(li.group(1)))
            continue
        if sli and cur_sub is not None and isinstance(data.get(cur_key), dict):
            sub_k = sli.group(1)
            data[cur_key][sub_k] = _strip_inline(sli.group(2))
            continue
        if tm:
            k = tm.group(1)
            v = tm.group(2).strip()
            cur_sub = None
            if v == '':
                # 可能是 dict 或 list
                cur_key = k
                # 暂时不知道是 dict 还是 list，存空
                data[k] = {}
                cur_list = None
            else:
                data[k] = _strip_inline(v)
                cur_key = k
                cur_list = None
            continue
        # 如果遇到列表项但还没 cur_list，提升 cur_key 为 list
        if li and cur_key is not None and isinstance(data.get(cur_key), dict) and not data.get(cur_key):
            data[cur_key] = [_strip_inline(li.group(1))]
            cur_list = data[cur_key]
            continue
    return data


# ---------------------------------------------------------------------------
# 主题分类
# ---------------------------------------------------------------------------

THEME_RULES = [
    # (正则模式(匹配 frontmatter/标题/正文), 主题)
    (r'(?i)(kafka|rocketmq|rabbitmq|消息队列|消息中间件|broker|producer|consumer|offset|mq\b|topic|queue|刷盘|消息丢失|消息顺序|消息幂等|消息积压|死信|延迟队列|顺序消息|事务消息|广播|消费者|生产者)', 'mq'),
    (r'(?i)(redis|缓存|cache|热点\s*key|大\s*key|缓存击穿|缓存穿透|缓存雪崩|布隆|过期策略|分布式锁|sencelock|redlock)', 'redis'),
    (r'(?i)(zookeeper|zk\s|nacos|etcd|consul|注册中心|配置中心|服务发现|一致性\s*hash|paxos|raft|zab)', 'coordination'),
    (r'(?i)(mysql|innodb|索引|b\+?\s*树|事务|acid|mvcc|隔离级别|锁\s*表|乐观锁|悲观锁|分库分表|主从|binlog|redolog|undolog)', 'database'),
    (r'(?i)(jvm|gc|g1|zgc|cms|新生代|老年代|内存模型|内存泄漏|内存溢出|oom|堆|栈|class\s*文件|类加载|双亲委派|字节码)', 'jvm'),
    (r'(?i)(线程|thread|线程池|threadpool|并发|concurrent|synchronized|lock|aqs|cas|volatile|atomic|future|completablefuture|lock\s*support)', 'concurrent'),
    (r'(?i)(netty|nio|reactor|epoll|selector|channel|bytebuf|pipeline|eventloop|tcp\s*粘包|io\s*模型|零拷贝)', 'netty'),
    (r'(?i)(spring\s*boot|spring\s*cloud|spring|bean|ioc|aop|autoconfig|starter|springmvc|springframework|mybatis)', 'spring'),
    (r'(?i)(dubbo|rpc|grpc|thrift|序列化|protobuf|服务治理|注册\s*中心|负载均衡|熔断|sentinel|hystrix|限流)', 'rpc'),
    (r'(?i)(k8s|kubernetes|docker|容器|编排|pod|deployment|service\b|ingress|helm|istio|服务网格|sidecar)', 'cloudnative'),
    (r'(?i)(nginx|负载均衡|反向代理|网关|gateway|lvs|haproxy|keepalived|slb)', 'gateway'),
    (r'(?i)(分布式锁|分布式事务|seata|分布式\s*id|分布式\s*缓存|分布式\s*存储|一致性\s*hash|分片|partition|副本|一致性)', 'distributed'),
    (r'(?i)(agent|llm|rag|prompt|tool\s*call|tool\s*use|function\s*call|reAct|function calling|chatgpt|gpt|in\-context|fine-?tun|向量|embedding|向量数据库|大模型|prompt\s*工程|多模态|tool\s*choos|mcp|context|token)', 'llm'),
    (r'(?i)(搜索|es\b|elastic|lucene|倒排索引|检索|召回|排序|retrieval|search)', 'search'),
    (r'(?i)(秒杀|抢购|高并发|缓存预热|预热|库存扣减|限流|降级|熔断|大促|洪峰|超卖)', 'flashsale'),
    (r'(?i)(分布式\s*系统|微服务|系统设计|架构设计|cap|base|最终一致性|高可用|容灾|异地多活|单元化)', 'sysdesign'),
    (r'(?i)(前端|react|vue|前端框架|组件|浏览器|渲染|webpack|vite|html|css|dom|js\b|javascript|typescript)', 'frontend'),
    (r'(?i)(算法|dp|动态规划|dfs|bfs|树|链表|二叉树|排序|查找|复杂度|递归|贪心|回溯|sliding|双指针|单调栈)', 'algorithm'),
    (r'(?i)(网络|tcp|udp|http|https|三次握手|四次挥手|tls|ssl|quic|http2|http3|流量控制|拥塞控制)', 'network'),
    (r'(?i)(支付|订单|交易|电商|营销|优惠券|购物车|结算|账务|对账)', 'trade'),
    (r'(?i)(供应链|库存|采购|销售|wms|仓储|物流|商品|类目|spu|sku)', 'scm'),
    (r'(?i)(内容|推荐|推荐系统|召回|排序|画像|标签|ctr|个性化)', 'content'),
    (r'(?i)(biopharm|蛋白|药物|分子|生物|crispr|序列|基因|质谱|药物研发)', 'biopharm'),
    (r'(?i)(fde|现场工程|交付|客户|实施|信任|项目)', 'fde'),
    (r'(?i)(工程实践|devops|cicd|代码质量|测试|code\s*review|研发效能|效能|sre|监控|告警|故障|稳定性)', 'engpractice'),
    (r'(?i)(架构|java\s*架构|系统架构|微服务|ddd|领域驱动|中间件|技术选型|架构师)', 'architect'),
]


def detect_theme(text, fm):
    # 优先使用 subcategory + tags
    probe = ' '.join([
        str(fm.get('subcategory', '')),
        ' '.join(fm.get('tags', []) if isinstance(fm.get('tags'), list) else [str(fm.get('tags', ''))] if fm.get('tags') else []),
        text[:3000],
    ])
    for pat, theme in THEME_RULES:
        if re.search(pat, probe):
            return theme
    return 'generic'


# ---------------------------------------------------------------------------
# Mermaid 流程图模板（每个主题 8-15 个节点，含判断分支 + classDef）
# ---------------------------------------------------------------------------

def _short(s, n=24):
    if not s:
        return ''
    s = re.sub(r'\s+', ' ', str(s)).strip()
    return s if len(s) <= n else s[:n - 1] + '…'


def render_flowchart(theme, fm, body):
    """根据主题返回 mermaid 代码块（不含围栏）"""
    title = _extract_title(body, fm)
    fn = THEMES.get(theme, THEMES['generic'])
    return fn(fm, title)


def _extract_title(body, fm):
    # markdown 一级标题
    m = re.search(r'^#\s+(.+?)$', body, re.MULTILINE)
    if m:
        return _short(m.group(1), 40)
    if fm.get('id'):
        return str(fm['id'])
    return '面试题流程'


# ---- 主题：mq 消息队列 ----
def theme_mq(fm, title):
    return f"""flowchart TD
    Start([🚀 客户端发起请求]):::start
    Producer[Producer 生产者<br/>发送消息]:::client
    DecideSync{{发送模式?<br/>同步/异步/单向}}:::decision
    Sync[同步发送<br/>阻塞等待 ACK]:::process
    Async[异步发送<br/>回调通知]:::process
    Oneway[单向发送<br/>不等响应]:::warn
    RetryQ{{是否收到 ACK?}}:::decision
    Retry[重试 N 次<br/>+ 幂等去重]:::process
    DLQ[多次失败 → 死信队列 DLQ]:::danger
    Broker[Broker 主节点<br/>写 PageCache]:::broker
    FlushQ{{刷盘策略?}}:::decision
    SyncFlush[同步刷盘 SYNC_FLUSH<br/>落盘后才返回]:::process
    AsyncFlush[异步刷盘<br/>后台异步落盘]:::warn
    ReplicaQ{{复制策略?}}:::decision
    SyncRep[同步复制 SYNC_MASTER<br/>等 Slave 落盘]:::process
    AsyncRep[异步复制<br/>Master 立即返回]:::warn
    Persist[(磁盘 + 多副本<br/>持久化存储)]:::store
    Consumer[Consumer 消费者<br/>拉取消息]:::client
    OffsetQ{{Offset 提交方式?}}:::decision
    AutoCommit[自动提交<br/>风险:业务异常也消费]:::warn
    ManualCommit[手动提交<br/>业务成功后再 ACK]:::process
    Business[执行业务逻辑]:::process
    BizQ{{业务是否成功?}}:::decision
    Reconsume[消费失败 → 重试<br/>RECONSUME_LATER]:::process
    Final([✅ 消息消费完成]):::start

    Start --> Producer --> DecideSync
    DecideSync -->|高可靠| Sync --> Broker
    DecideSync -->|高吞吐| Async --> Broker
    DecideSync -->|日志类| Oneway --> Broker
    Broker --> FlushQ
    FlushQ -->|金融级| SyncFlush --> ReplicaQ
    FlushQ -->|性能优先| AsyncFlush --> ReplicaQ
    ReplicaQ -->|强一致| SyncRep --> Persist
    ReplicaQ -->|弱一致| AsyncRep --> Persist
    Persist --> Consumer --> OffsetQ
    OffsetQ -->|不推荐| AutoCommit --> Business
    OffsetQ -->|推荐| ManualCommit --> Business
    Business --> BizQ
    BizQ -->|成功| ManualCommit --> Final
    BizQ -->|失败| Reconsume --> Consumer
    Producer -.ACK 超时/失败.-> RetryQ
    RetryQ -->|<N 次| Retry --> Producer
    RetryQ -->|>=N 次| DLQ

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef client fill:#10b981,stroke:#047857,color:#fff;
    classDef broker fill:#f59e0b,stroke:#b45309,color:#fff;
    classDef store fill:#8b5cf6,stroke:#6d28d9,color:#fff;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef warn fill:#fee2e2,stroke:#ef4444,color:#7f1d1d;
    classDef danger fill:#b91c1c,stroke:#7f1d1d,color:#fff,stroke-width:2px;"""


# ---- 主题：redis 缓存 ----
def theme_redis(fm, title):
    return """flowchart TD
    Start([🚀 应用发起读请求]):::start
    App[应用层<br/>查询数据]:::client
    CacheHitQ{{缓存命中?}}:::decision
    ReturnCache["直接返回缓存数据<br/>O(1) 低延迟"]:::process
    MissDB{缓存未命中}:::decision
    QueryDB[查询数据库<br/>执行 SQL]:::process
    PenetrateQ{{是否为恶意请求?<br/>查询不存在的 key}}:::decision
    BloomFilter[布隆过滤器拦截<br/>+ 缓存空值]:::process
    BreakDownQ{{热点 key 失效?<br/>缓存击穿}}:::decision
    Mutex[加互斥锁<br/>单线程回源]:::process
    AvalancheQ{{大批 key 同时过期?<br/>缓存雪崩}}:::decision
    TTLJitter[随机 TTL<br/>+ 多级缓存]:::process
    WriteBackQ{{是否回写缓存?}}:::decision
    WriteCache[写入 Redis<br/>设置 TTL]:::process
    BigKeyCheck{{大 Key / 热 Key?}}:::decision
    SplitKey[拆分大 Key<br/>本地缓存热 Key]:::process
    DB[(MySQL 主从<br/>持久化数据)]:::store
    Cache[(Redis Cluster<br/>分片缓存)]:::store
    Final([✅ 返回结果]):::start
    Alarm[告警 + 限流降级]:::danger

    Start --> App --> CacheHitQ
    CacheHitQ -->|命中| ReturnCache --> BigKeyCheck
    BigKeyCheck -->|是| SplitKey --> Final
    BigKeyCheck -->|否| Final
    CacheHitQ -->|未命中| MissDB --> PenetrateQ
    PenetrateQ -->|是| BloomFilter --> Alarm
    PenetrateQ -->|否| BreakDownQ
    BreakDownQ -->|是| Mutex --> QueryDB
    BreakDownQ -->|否| AvalancheQ
    AvalancheQ -->|是| TTLJitter --> QueryDB
    AvalancheQ -->|否| QueryDB
    QueryDB --> DB --> WriteBackQ
    WriteBackQ -->|是| WriteCache --> Cache --> ReturnCache
    WriteBackQ -->|否| ReturnCache

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef client fill:#10b981,stroke:#047857,color:#fff;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef store fill:#8b5cf6,stroke:#6d28d9,color:#fff;
    classDef danger fill:#b91c1c,stroke:#7f1d1d,color:#fff,stroke-width:2px;"""


# ---- 主题：database / mysql ----
def theme_database(fm, title):
    return """flowchart TD
    Start([🚀 SQL 请求到达]):::start
    Parser[解析器 Parser<br/>词法/语法分析]:::process
    AST[生成抽象语法树 AST]:::process
    Preproc[预处理器<br/>语义检查 + 权限]:::process
    Optimizer[优化器 Optimizer]:::process
    CostQ{{基于代价选择?<br/>CBO}}:::decision
    IdxScan[索引扫描<br/>range/ref]:::process
    FullScan[全表扫描<br/>ALL]:::warn
    Execute[执行器 Executor<br/>调用存储引擎接口]:::process
    EngineQ{{存储引擎?<br/>InnoDB/MyISAM}}:::decision
    InnoDB[InnoDB 引擎]:::process
    BufferPool[Buffer Pool<br/>内存缓冲池]:::store
    HitQ{{页命中 Buffer Pool?}}:::decision
    ReadDisk[从磁盘读取页<br/>随机 IO]:::warn
    RedoLog[(redo log<br/>WAL 先写日志)]:::store
    BinLog[(binlog<br/>主从复制)]:::store
    UndoLog[(undo log<br/>事务回滚/MVCC)]:::store
    CommitQ{{是否提交事务?<br/>2PC}}:::decision
    TwoPhase[Prepare → 写 redo<br/>→ 写 binlog → Commit]:::process
    Crash[宕机崩溃恢复<br/>redo 重放 + binlog 校验]:::danger
    Final([✅ 返回结果集]):::start

    Start --> Parser --> AST --> Preproc --> Optimizer
    Optimizer --> CostQ
    CostQ -->|有合适索引| IdxScan --> Execute
    CostQ -->|无索引/全表| FullScan --> Execute
    Execute --> EngineQ
    EngineQ -->|默认| InnoDB --> BufferPool
    EngineQ -->|旧版| FullScan
    BufferPool --> HitQ
    HitQ -->|命中| Execute
    HitQ -->|未命中| ReadDisk --> BufferPool
    InnoDB -.修改.-> UndoLog
    InnoDB -.修改.-> RedoLog
    InnoDB -.提交.-> BinLog
    Execute --> CommitQ
    CommitQ -->|是| TwoPhase --> Final
    CommitQ -->|崩溃| Crash --> RedoLog

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef store fill:#8b5cf6,stroke:#6d28d9,color:#fff;
    classDef warn fill:#fee2e2,stroke:#ef4444,color:#7f1d1d;
    classDef danger fill:#b91c1c,stroke:#7f1d1d,color:#fff,stroke-width:2px;"""


# ---- 主题：jvm ----
def theme_jvm(fm, title):
    return """flowchart TD
    Start([🚀 Java 源码 .java]):::start
    Javac[javac 编译<br/>词法/语法/语义分析]:::process
    ClassFile[.class 字节码文件<br/>常量池/方法表]:::store
    ClassLoad[类加载子系统<br/>ClassLoader]:::process
    LoadPhase[加载 Loading<br/>读取字节流]:::process
    LinkPhase[链接 Linking<br/>验证/准备/解析]:::process
    ParentQ{{双亲委派?<br/>向上委托}}:::decision
    BootClass[BootStrap 加载<br/>rt.jar 核心类]:::process
    AppClass[AppClassLoader<br/>加载应用类]:::process
    InitPhase[初始化 Initialization<br/>执行 <clinit>]:::process
    Runtime[运行时数据区]:::process
    Heap[(堆 Heap<br/>对象/数组 GC 区)]:::store
    Method[(方法区<br/>类元信息/常量)]:::store
    Stack[(虚拟机栈<br/>栈帧/局部变量)]:::store
    NativeStack[(本地方法栈<br/>JNI)]:::store
    PC[(程序计数器 PC)]:::store
    Alloc[对象分配 Eden]:::process
    GcQ{{GC 触发?<br/>Eden 满/老年代满}}:::decision
    YoungGC[Young GC<br/>复制算法]:::process
    OldGC[Old GC / Full GC<br/>标记-整理]:::process
    CollectorQ{{GC 收集器?<br/>G1/ZGC/CMS}}:::decision
    G1[G1 Region 化<br/>可预测暂停]:::process
    ZGC[ZGC 染色指针<br/><10ms STW]:::process
    Final([✅ 字节码执行完成]):::start

    Start --> Javac --> ClassFile --> ClassLoad
    ClassLoad --> LoadPhase --> LinkPhase --> ParentQ
    ParentQ -->|核心类| BootClass --> InitPhase
    ParentQ -->|应用类| AppClass --> InitPhase
    InitPhase --> Runtime
    Runtime --> Heap & Method & Stack & NativeStack & PC
    Heap --> Alloc --> GcQ
    GcQ -->|Eden 满| YoungGC --> Alloc
    GcQ -->|Old 满| OldGC --> CollectorQ
    CollectorQ -->|默认 9+| G1 --> Final
    CollectorQ -->|大堆低延迟| ZGC --> Final

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef store fill:#8b5cf6,stroke:#6d28d9,color:#fff;
    classDef danger fill:#b91c1c,stroke:#7f1d1d,color:#fff,stroke-width:2px;"""


# ---- 主题：concurrent ----
def theme_concurrent(fm, title):
    return """flowchart TD
    Start([🚀 多线程并发任务]):::start
    Submit[提交任务到线程池<br/>execute / submit]:::process
    CoreQ{{核心线程数满?<br/>corePoolSize}}:::decision
    NewCore[创建核心线程<br/>立即执行]:::process
    QueueQ{{工作队列满?<br/>workQueue}}:::decision
    Enqueue[任务入队<br/>LinkedBlockingQueue]:::process
    MaxQ{{达到最大线程数?<br/>maxPoolSize}}:::decision
    NewWorker[创建非核心线程]:::process
    RejectQ{{拒绝策略?<br/>RejectedHandler}}:::decision
    Abort[AbortPolicy<br/>抛异常]:::danger
    Caller[CallerRunsPolicy<br/>调用线程执行]:::process
    Discard[DiscardPolicy<br/>丢弃]:::warn
    Worker[Worker 线程<br/>循环 take 任务]:::process
    SyncQ{{是否需要同步?<br/>共享资源}}:::decision
    CAS[CAS 无锁操作<br/>compareAndSwap]:::process
    Lock[加锁 synchronized / AQS]:::process
    VolatileQ{{可见性需求?<br/>禁止指令重排}}:::decision
    Volatile[volatile 修饰<br/>内存屏障]:::process
    Final[业务执行完成]:::process
    WaitQ{{是否需要等待?<br/>Future/Condition}}:::decision
    Future[CompletableFuture<br/>异步编排]:::process
    Done([✅ 任务完成]):::start

    Start --> Submit --> CoreQ
    CoreQ -->|否| NewCore --> Worker
    CoreQ -->|是| QueueQ
    QueueQ -->|否| Enqueue --> Worker
    QueueQ -->|是| MaxQ
    MaxQ -->|否| NewWorker --> Worker
    MaxQ -->|是| RejectQ
    RejectQ -->|默认| Abort
    RejectQ -->|降级| Caller
    RejectQ -->|容忍| Discard
    Worker --> SyncQ
    SyncQ -->|无锁| CAS --> Final
    SyncQ -->|互斥| Lock --> VolatileQ
    VolatileQ -->|是| Volatile --> Final
    VolatileQ -->|否| Final
    Final --> WaitQ
    WaitQ -->|是| Future --> Done
    WaitQ -->|否| Done

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef warn fill:#fee2e2,stroke:#ef4444,color:#7f1d1d;
    classDef danger fill:#b91c1c,stroke:#7f1d1d,color:#fff,stroke-width:2px;"""


# ---- 主题：netty / nio ----
def theme_netty(fm, title):
    return """flowchart TD
    Start([🚀 服务端启动]):::start
    BossGroup[BossGroup<br/>Accept 线程]:::process
    WorkerGroup[WorkerGroup<br/>IO 处理线程]:::process
    Bind[绑定端口<br/>ServerSocketChannel]:::process
    EventLoop[EventLoop<br/>单线程 Selector 轮询]:::process
    Selector[(Selector<br/>多路复用器)]:::store
    IOModelQ{{IO 模型?<br/>select/poll/epoll}}:::decision
    Epoll[epoll 边缘触发<br/>事件驱动 高性能]:::process
    SelectIO[select 水平触发<br/>跨平台]:::process
    AcceptEvent[OP_ACCEPT 事件<br/>新连接到达]:::process
    Register[注册到 Worker<br/>SocketChannel]:::process
    ReadEvent[OP_READ 事件<br/>数据可读]:::process
    Pipeline[Pipeline 处理链<br/>责任链模式]:::process
    Decoder[Decoder 解码器<br/>解决粘包/半包]:::process
    Handler[业务 Handler<br/>处理业务逻辑]:::process
    Encoder[Encoder 编码器<br/>序列化响应]:::process
    ZeroCopyQ{{是否零拷贝?<br/>FileRegion}}:::decision
    ZeroCopy[sendfile/mmap<br/>减少内核态拷贝]:::process
    WriteBack[写回 Channel]:::process
    BackPressureQ{{背压?<br/>写缓冲区高水位}}:::decision
    BackPressure[isWritable=false<br/>自动降级]:::warn
    Final([✅ 响应返回客户端]):::start

    Start --> BossGroup --> Bind --> EventLoop
    EventLoop --> Selector --> IOModelQ
    IOModelQ -->|Linux| Epoll --> AcceptEvent
    IOModelQ -->|通用| SelectIO --> AcceptEvent
    AcceptEvent --> Register --> WorkerGroup
    WorkerGroup --> ReadEvent --> Pipeline
    Pipeline --> Decoder --> Handler --> Encoder
    Encoder --> ZeroCopyQ
    ZeroCopyQ -->|大文件| ZeroCopy --> WriteBack
    ZeroCopyQ -->|否| WriteBack
    WriteBack --> BackPressureQ
    BackPressureQ -->|高水位| BackPressure --> Final
    BackPressureQ -->|正常| Final

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef store fill:#8b5cf6,stroke:#6d28d9,color:#fff;
    classDef warn fill:#fee2e2,stroke:#ef4444,color:#7f1d1d;"""


# ---- 主题：spring ----
def theme_spring(fm, title):
    return """flowchart TD
    Start([🚀 SpringBoot 启动<br/>main 方法]):::start
    SpringApplication[SpringApplication.run<br/>启动入口]:::process
    PrepareEnv[准备 Environment<br/>加载 application.yml]:::process
    ContextQ{{应用上下文?<br/>Servlet/Reactive}}:::decision
    ServletCtx[AnnotationConfigCtx<br/>传统 MVC]:::process
    ReactiveCtx[ReactiveWebCtx<br/>WebFlux]:::process
    Refresh[refresh 刷新容器<br/>核心入口]:::process
    BeanFactory[BeanFactory<br/>IoC 容器]:::store
    BeanDef[BeanDefinition<br/>扫描 @Component/@Bean]:::process
    ScanQ{{配置方式?<br/>注解/XML}}:::decision
    AnnoScan[ComponentScan<br/>ClassPathBeanDefinitionScanner]:::process
    XmlScan[XmlBeanDefinitionReader<br/>解析 XML]:::process
    Instantiate[实例化 Bean<br/>反射 newInstance]:::process
    Populate[属性填充<br/>依赖注入 @Autowired]:::process
    AwareQ{{实现 Aware 接口?}}:::decision
    Aware[BeanNameAware / ContextAware<br/>回调注入]:::process
    InitQ{{自定义初始化?}}:::decision
    PostConstruct[@PostConstruct<br/>初始化方法]:::process
    AOPQ{{需要 AOP 增强?<br/>切面 @Aspect}}:::decision
    Proxy[创建动态代理<br/>JDK/CGLIB]:::process
    ProxyChain[代理链<br/>MethodInvocation]:::process
    Final([✅ Bean 就绪 可用]):::start

    Start --> SpringApplication --> PrepareEnv --> ContextQ
    ContextQ -->|传统| ServletCtx --> Refresh
    ContextQ -->|响应式| ReactiveCtx --> Refresh
    Refresh --> BeanFactory --> BeanDef --> ScanQ
    ScanQ -->|注解| AnnoScan --> Instantiate
    ScanQ -->|XML| XmlScan --> Instantiate
    Instantiate --> Populate --> AwareQ
    AwareQ -->|是| Aware --> InitQ
    AwareQ -->|否| InitQ
    InitQ -->|是| PostConstruct --> AOPQ
    InitQ -->|否| AOPQ
    AOPQ -->|是| Proxy --> ProxyChain --> Final
    AOPQ -->|否| Final

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef store fill:#8b5cf6,stroke:#6d28d9,color:#fff;"""


# ---- 主题：rpc / dubbo ----
def theme_rpc(fm, title):
    return """flowchart TD
    Start([🚀 调用方发起 RPC 调用]):::start
    Proxy[客户端代理 Stub<br/>屏蔽网络细节]:::process
    Invoke[Invoker 调用链<br/>Filter 拦截]:::process
    ClusterQ{{集群容错策略?<br/>Cluster}}:::decision
    Failover[Failover 失败重试<br/>默认]:::process
    Failfast[Failfast 快速失败]:::warn
    Forking[Forking 并行调用]:::process
    Router[Router 路由<br/>按规则筛选 provider]:::process
    LBQ{{负载均衡策略?<br/>LoadBalance}}:::decision
    Random[Random 随机<br/>默认]:::process
    RoundRobin[RoundRobin 轮询]:::process
    ConsistentHash[一致性 Hash<br/>相同参数同一台]:::process
    Registry[(注册中心<br/>Nacos/ZK)]:::store
    Subscribe[订阅 provider 列表<br/>推送变更]:::process
    Serialize[序列化请求<br/>Hessian/Protobuf]:::process
    Network[网络传输<br/>Netty 长连接]:::process
    Server[服务端 Invoker<br/>解包请求]:::process
    Filter[服务端 Filter<br/>前置处理]:::process
    Reflect[反射调用真实方法<br/>业务执行]:::process
    ResultQ{{业务执行结果?}}:::decision
    Success[序列化响应<br/>返回]:::process
    Exception[包装异常<br/>RpcException]:::danger
    Final([✅ 调用方拿到结果]):::start

    Start --> Proxy --> Invoke --> ClusterQ
    ClusterQ -->|默认| Failover --> Router
    ClusterQ -->|快速失败| Failfast --> Router
    ClusterQ -->|并行| Forking --> Router
    Router --> LBQ
    LBQ -->|默认| Random --> Serialize
    LBQ -->|轮询| RoundRobin --> Serialize
    LBQ -->|亲和| ConsistentHash --> Serialize
    Registry -.推送.-> Subscribe --> Router
    Serialize --> Network --> Server --> Filter --> Reflect --> ResultQ
    ResultQ -->|成功| Success --> Final
    ResultQ -->|失败| Exception --> Failover

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef store fill:#8b5cf6,stroke:#6d28d9,color:#fff;
    classDef warn fill:#fee2e2,stroke:#ef4444,color:#7f1d1d;
    classDef danger fill:#b91c1c,stroke:#7f1d1d,color:#fff,stroke-width:2px;"""


# ---- 主题：gateway / 网关 ----
def theme_gateway(fm, title):
    return """flowchart TD
    Start([🚀 客户端请求<br/>HTTP/TCP]):::start
    DNS[DNS 解析<br/>就近接入]:::process
    SLB[SLB 负载均衡<br/>LVS/F5 四层]:::process
    NginxQ{{反向代理?<br/>七层}}:::decision
    Nginx[Nginx<br/>转发 + SSL 卸载]:::process
    WAF[WAF 防火墙<br/>SQL 注入/CC 拦截]:::process
    RateLimitQ{{限流策略?<br/>令牌桶/漏桶}}:::decision
    TokenBucket[令牌桶<br/>突发流量]:::process
    LeakyBucket[漏桶<br/>平滑速率]:::process
    Reject[429 Too Many<br/>请求拒绝]:::danger
    Gateway[API 网关<br/>鉴权/路由/熔断]:::process
    AuthQ{{鉴权?}}:::decision
    JWT[JWT/Token 校验]:::process
    Unauthorized[401 Unauthorized]:::danger
    RouteQ{{路由到哪个服务?}}:::decision
    Filter[全局 Filter<br/>日志/埋点/灰度]:::process
    CircuitQ{{熔断/降级?<br/>Sentinel}}:::decision
    Break[CircuitBreaker 开启<br/>快速失败]:::warn
    Backend[后端微服务集群]:::process
    Final([✅ 业务响应返回]):::start

    Start --> DNS --> SLB --> NginxQ
    NginxQ -->|是| Nginx --> WAF
    NginxQ -->|否| SLB
    WAF --> RateLimitQ
    RateLimitQ -->|令牌| TokenBucket --> Gateway
    RateLimitQ -->|漏桶| LeakyBucket --> Gateway
    RateLimitQ -->|超限| Reject
    Gateway --> AuthQ
    AuthQ -->|通过| JWT --> RouteQ
    AuthQ -->|失败| Unauthorized
    RouteQ --> Filter --> CircuitQ
    CircuitQ -->|熔断| Break --> Final
    CircuitQ -->|正常| Backend --> Final

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef warn fill:#fee2e2,stroke:#ef4444,color:#7f1d1d;
    classDef danger fill:#b91c1c,stroke:#7f1d1d,color:#fff,stroke-width:2px;"""


# ---- 主题：distributed 分布式 ----
def theme_distributed(fm, title):
    return """flowchart TD
    Start([🚀 客户端请求分布式系统]):::start
    Gateway[API 网关<br/>入口路由]:::process
    Coordinator[协调者 Coordinator<br/>2PC/3PC/TCC]:::process
    PhaseQ{{一致性协议?<br/>CAP 权衡}}:::decision
    CP[CP 强一致<br/>Raft/Paxos]:::process
    AP[AP 最终一致<br/>Gossip/Dynamo]:::process
    PartitionQ{{网络分区?<br/>Network Partition}}:::decision
    Minority[少数派降级<br/>拒绝服务]:::warn
    Majority[多数派继续<br/>保证一致]:::process
    Replica[多副本写入<br/>Leader → Followers]:::process
    QuorumQ{{Quorum 写策略?}}:::decision
    WQAll[W=All 同步所有副本<br/>强一致 低可用]:::process
    WQMajority[W=Majority<br/>平衡]:::process
    VectorClock[向量时钟<br/>冲突检测]:::process
    ConflictQ{{写冲突?}}:::decision
    LWW[Last Write Wins<br/>时间戳定序]:::process
    Merge[业务合并<br/>CRDT/手动解决]:::process
    Compensate[补偿事务 TCC<br/>Try-Confirm-Cancel]:::process
    MQ[(消息队列<br/>最终一致性)]:::store
    Final([✅ 全局一致状态]):::start

    Start --> Gateway --> Coordinator --> PhaseQ
    PhaseQ -->|强一致| CP --> PartitionQ
    PhaseQ -->|高可用| AP --> Replica
    PartitionQ -->|是| Minority
    PartitionQ -->|否| Majority --> Replica
    Replica --> QuorumQ
    QuorumQ -->|强一致| WQAll --> VectorClock
    QuorumQ -->|平衡| WQMajority --> VectorClock
    VectorClock --> ConflictQ
    ConflictQ -->|无冲突| MQ --> Final
    ConflictQ -->|有冲突| LWW --> Final
    ConflictQ -->|复杂| Merge --> Final
    PhaseQ -.跨服务.-> Compensate --> MQ

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef store fill:#8b5cf6,stroke:#6d28d9,color:#fff;
    classDef warn fill:#fee2e2,stroke:#ef4444,color:#7f1d1d;"""


# ---- 主题：llm / agent / rag ----
def theme_llm(fm, title):
    return """flowchart TD
    Start([🚀 用户 Query 输入]):::start
    InputGuard[输入安全过滤<br/>敏感词/Prompt 注入]:::process
    Router[Router 路由<br/>意图识别]:::process
    NeedRAGQ{{需要外部知识?<br/>RAG}}:::decision
    DirectLLM[直接调用 LLM<br/>参数化知识]:::process
    Embed[Query Embedding<br/>向量编码]:::process
    VectorDB[(向量数据库<br/>Milvus/Chroma)]:::store
    Retrieve[Top-K 检索召回<br/>语义相似度]:::process
    Rerank[Cross-Encoder 重排<br/>精排 Top-N]:::process
    Context[组装上下文<br/>System + Context + Query]:::process
    NeedToolQ{{需要工具调用?<br/>Tool/Function Call}}:::decision
    ToolSelect[LLM 输出 JSON<br/>name + arguments]:::process
    ToolExec[宿主执行 Tool<br/>API/DB/函数]:::process
    ToolResult[结果回填<br/>注入 Context]:::process
    MultiStepQ{{多步推理?<br/>ReAct/Plan}}:::decision
    ReActLoop[Reason→Act→Observe<br/>迭代循环]:::process
    LLM[LLM 推理生成<br/>流式输出 Token]:::process
    OutputGuard[输出过滤<br/>合规/毒性检测]:::process
    Final([✅ 返回最终回答]):::start

    Start --> InputGuard --> Router --> NeedRAGQ
    NeedRAGQ -->|闲聊/参数知识| DirectLLM --> NeedToolQ
    NeedRAGQ -->|事实型问答| Embed --> VectorDB --> Retrieve --> Rerank --> Context --> NeedToolQ
    NeedToolQ -->|是| ToolSelect --> ToolExec --> ToolResult --> MultiStepQ
    NeedToolQ -->|否| MultiStepQ
    MultiStepQ -->|是| ReActLoop --> LLM
    MultiStepQ -->|否| LLM
    LLM --> OutputGuard --> Final

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef store fill:#8b5cf6,stroke:#6d28d9,color:#fff;"""


# ---- 主题：search ----
def theme_search(fm, title):
    return """flowchart TD
    Start([🚀 文档/查询入库]):::start
    Crawl[数据采集<br/>爬虫/数据库]:::process
    Clean[清洗去重<br/>HTML 标签]:::process
    Tokenize[分词<br/>IK/标准分词器]:::process
    Analysis[语言处理<br/>小写/词干化/同义词]:::process
    IndexBuild[构建倒排索引<br/>Term → DocList]:::process
    Store[(索引存储<br/>Segment 段)]:::store
    Query[用户查询]:::process
    ParseQ[Query Parser<br/>解析布尔/短语]:::process
    IdxQ{{查询类型?}}:::decision
    TermQ[Term Query<br/>精确匹配]:::process
    MatchQ[Match Query<br/>分词后 OR]:::process
    BoolQ[Bool Query<br/>must/should/filter]:::process
    PhraseQ[Phrase Query<br/>位置临近]:::process
    Retrieve[倒排表合并<br/>AND/OR 交集]:::process
    Score[相关性打分<br/>TF-IDF / BM25]:::process
    Rerank[二次排序<br/>业务权重]:::process
    Highlight[高亮匹配片段]:::process
    Final([✅ 返回结果集]):::start

    Start --> Crawl --> Clean --> Tokenize --> Analysis --> IndexBuild --> Store
    Query --> ParseQ --> IdxQ
    IdxQ -->|精确| TermQ --> Retrieve
    IdxQ -->|模糊| MatchQ --> Retrieve
    IdxQ -->|组合| BoolQ --> Retrieve
    IdxQ -->|短语| PhraseQ --> Retrieve
    Retrieve --> Score --> Rerank --> Highlight --> Final

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef store fill:#8b5cf6,stroke:#6d28d9,color:#fff;"""


# ---- 主题：flashsale 秒杀 ----
def theme_flashsale(fm, title):
    return """flowchart TD
    Start([🚀 秒杀活动开始<br/>大促洪峰]):::start
    CDN[CDN 静态资源<br/>JS/CSS/图片]:::process
    WAF[WAF + 黑名单<br/>拦截刷子]:::process
    Gateway[网关层限流<br/>令牌桶 N QPS]:::process
    RateQ{{QPS 超限?}}:::decision
    Drop[快速拒绝<br/>降级页面]:::danger
    CacheQ{{缓存层预热库存?<br/>Redis Lua}}:::decision
    PreHeat[提前预热库存到 Redis<br/>Lua 原子扣减]:::process
    StockQ{{库存是否充足?}}:::decision
    SoldOut[售罄提示<br/>提前返回]:::warn
    MQ[(消息队列<br/>异步削峰)]:::store
    AsyncSend[发送下单消息<br/>异步化]:::process
    Consumer[消费端串行处理<br/>幂等校验]:::process
    IdempQ{{是否重复下单?}}:::decision
    RejectDup[拒绝重复订单]:::warn
    DeductDB[DB 扣库存<br/>乐观锁 version]:::process
    OverSellQ{{扣减成功?<br/>防超卖}}:::decision
    OrderOK[生成订单<br/>DB 事务]:::process
    Pay[支付回调<br/>更新订单状态]:::process
    Final([✅ 秒杀成功]):::start

    Start --> CDN --> WAF --> Gateway --> RateQ
    RateQ -->|超限| Drop
    RateQ -->|通过| CacheQ
    CacheQ -->|未预热| PreHeat --> StockQ
    CacheQ -->|已预热| StockQ
    StockQ -->|售罄| SoldOut
    StockQ -->|有库存| AsyncSend --> MQ --> Consumer --> IdempQ
    IdempQ -->|重复| RejectDup
    IdempQ -->|首次| DeductDB --> OverSellQ
    OverSellQ -->|成功| OrderOK --> Pay --> Final
    OverSellQ -->|"失败(version冲突)"| StockQ

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef store fill:#8b5cf6,stroke:#6d28d9,color:#fff;
    classDef warn fill:#fee2e2,stroke:#ef4444,color:#7f1d1d;
    classDef danger fill:#b91c1c,stroke:#7f1d1d,color:#fff,stroke-width:2px;"""


# ---- 主题：sysdesign ----
def theme_sysdesign(fm, title):
    return """flowchart TD
    Start([🚀 需求分析<br/>明确场景与 QPS]):::start
    Est[容量估算<br/>QPS/存储/带宽]:::process
    Arch[架构概览<br/>分层设计]:::process
    LayerQ{{架构分层?}}:::decision
    Client[接入层<br/>APP/Web/小程序]:::process
    Gateway[网关层<br/>鉴权/限流/路由]:::process
    Service[服务层<br/>微服务集群]:::process
    DataQ{{数据访问层?}}:::decision
    Cache[(缓存层<br/>Redis 多级)]:::store
    DB[(存储层<br/>MySQL 分库分表)]:::store
    MQ[(消息队列<br/>异步解耦)]:::store
    HAQ{{高可用方案?<br/>异地多活}}:::decision
    SingleDC[单机房<br/>主从备份]:::warn
    MultiDC[两地三中心<br/>单元化部署]:::process
    ConsistencyQ{{一致性要求?}}:::decision
    Strong[强一致<br/>2PC/同步复制]:::process
    Eventual[最终一致<br/>异步补偿]:::process
    ScaleQ{{扩展方式?}}:::decision
    Vertical[垂直扩展<br/>升配]:::warn
    Horizontal[水平扩展<br/>分片/集群]:::process
    Monitor[监控告警<br/>全链路追踪]:::process
    Final([✅ 系统设计完成]):::start

    Start --> Est --> Arch --> LayerQ
    LayerQ -->|前端| Client
    LayerQ -->|网关| Gateway --> Service
    LayerQ -->|业务| Service
    Service --> DataQ
    DataQ -->|热数据| Cache
    DataQ -->|持久化| DB
    DataQ -->|异步| MQ
    Service --> HAQ
    HAQ -->|初级| SingleDC
    HAQ -->|高可用| MultiDC
    HAQ --> ConsistencyQ
    ConsistencyQ -->|交易类| Strong
    ConsistencyQ -->|内容类| Eventual
    Service --> ScaleQ
    ScaleQ -->|短期| Vertical
    ScaleQ -->|长期| Horizontal --> Monitor --> Final

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef store fill:#8b5cf6,stroke:#6d28d9,color:#fff;
    classDef warn fill:#fee2e2,stroke:#ef4444,color:#7f1d1d;"""


# ---- 主题：frontend ----
def theme_frontend(fm, title):
    return """flowchart TD
    Start([🚀 浏览器输入 URL]):::start
    DNS[DNS 解析<br/>本地→递归→权威]:::process
    TCP[TCP 三次握手<br/>建立连接]:::process
    TLS[TLS 握手<br/>证书校验/密钥协商]:::process
    HTTP[发送 HTTP 请求<br/>Request]:::process
    Server[服务器处理<br/>返回 HTML]:::process
    ParseHTML[解析 HTML<br/>构建 DOM 树]:::process
    ParseCSS[解析 CSS<br/>构建 CSSOM]:::process
    ParseJS{遇到 JS?}:::decision
    Block[阻塞 DOM 解析<br/>同步加载执行]:::warn
    Async[async 异步<br/>不阻塞加载完执行]:::process
    Defer[defer 延迟<br/>DOMContentLoaded 前]:::process
    RenderTree[构建渲染树<br/>DOM + CSSOM]:::process
    Layout[Layout 布局<br/>计算位置大小]:::process
    Paint[Paint 绘制<br/>像素绘制]:::process
    Composite[合成 Composite<br/>图层合并]:::process
    FrameQ{{是否触发重排?<br/>Layout}}:::decision
    Reflow[Reflow 重排<br/>几何变化]:::danger
    Repaint[Repaint 重绘<br/>样式变化]:::warn
    Event[事件循环 Event Loop<br/>任务队列]:::process
    Final([✅ 页面渲染完成]):::start

    Start --> DNS --> TCP --> TLS --> HTTP --> Server
    Server --> ParseHTML --> ParseCSS --> ParseJS
    ParseJS -->|script 同步| Block --> RenderTree
    ParseJS -->|async| Async --> RenderTree
    ParseJS -->|defer| Defer --> RenderTree
    ParseJS -->|无| RenderTree
    RenderTree --> Layout --> Paint --> Composite
    Composite --> FrameQ
    FrameQ -->|几何变化| Reflow --> Layout
    FrameQ -->|样式变化| Repaint --> Paint
    FrameQ -->|无| Event --> Final

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef warn fill:#fee2e2,stroke:#ef4444,color:#7f1d1d;
    classDef danger fill:#b91c1c,stroke:#7f1d1d,color:#fff,stroke-width:2px;"""


# ---- 主题：algorithm ----
def theme_algorithm(fm, title):
    return """flowchart TD
    Start([🚀 接到算法题]):::start
    Understand[理解题意<br/>边界/输入/输出]:::process
    Example[举例验证<br/>手算样例]:::process
    BruteForce[暴力解<br/>朴素思路]:::process
    Analyze[复杂度分析<br/>时间/空间]:::process
    AcceptQ{{"复杂度可接受?<br/>O(n²)→O(n)"}}:::decision
    Optimize[优化方向]:::process
    PatternQ{{数据结构/算法模式?}}:::decision
    HashPattern[Hash 表<br/>空间换时间]:::process
    TwoPointer[双指针/滑窗<br/>区间问题]:::process
    DPSearch[DFS/BFS<br/>图/树/回溯]:::process
    DP[动态规划<br/>状态转移]:::process
    Greedy[贪心<br/>局部最优]:::process
    DivideConquer[分治<br/>递归拆分]:::process
    Implement[编码实现]:::process
    EdgeQ{{边界情况?}}:::decision
    Edge[空输入/极大值/负数<br/>特判]:::process
    Test[测试用例验证<br/>正常/异常/性能]:::process
    Final([✅ AC 通过]):::start

    Start --> Understand --> Example --> BruteForce --> Analyze --> AcceptQ
    AcceptQ -->|是| Implement
    AcceptQ -->|否| Optimize --> PatternQ
    PatternQ -->|查找/计数| HashPattern --> Implement
    PatternQ -->|数组/字符串| TwoPointer --> Implement
    PatternQ -->|连通/路径| DPSearch --> Implement
    PatternQ -->|最优子结构| DP --> Implement
    PatternQ -->|无后效| Greedy --> Implement
    PatternQ -->|可分解| DivideConquer --> Implement
    Implement --> EdgeQ
    EdgeQ -->|有| Edge --> Test
    EdgeQ -->|无| Test
    Test --> Final

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;"""


# ---- 主题：network ----
def theme_network(fm, title):
    return """flowchart TD
    Start([🚀 应用层数据<br/>HTTP 请求]):::start
    App[应用层<br/>HTTP/SMTP/DNS]:::process
    EncApp[应用层封装<br/>Header + Body]:::process
    TransQ{{传输层?<br/>TCP/UDP}}:::decision
    TCP[TCP 面向连接<br/>可靠传输]:::process
    UDP[UDP 无连接<br/>不可靠快]:::process
    Handshake[三次握手<br/>SYN/SYN+ACK/ACK]:::process
    SeqNum[序列号/确认号<br/>有序可靠]:::process
    FlowControl[流量控制<br/>滑动窗口]:::process
    CongestQ{{拥塞控制?<br/>慢启动/拥塞避免}}:::decision
    SlowStart[慢启动<br/>cwnd 指数增长]:::process
    Avoid[拥塞避免<br/>线性增长]:::process
    LossQ{{丢包?}}:::decision
    FastRetrans[快速重传<br/>3 次重复 ACK]:::process
    Timeout[超时重传 RTO<br/>cwnd=1]:::danger
    Segment[TCP 段封装<br/>Port + Seq]:::process
    IP[网络层<br/>IP 路由]:::process
    Route[路由选择<br/>跳跳转发]:::process
    FragQ{{需要分片?<br/>MTU}}:::decision
    Frag[IP 分片<br/>标记 offset]:::process
    DataLink[数据链路层<br/>MAC 帧]:::process
    ARP[ARP 解析 MAC<br/>IP→MAC]:::process
    Physical[物理层<br/>比特传输]:::process
    Final([✅ 数据到达对端]):::start

    Start --> App --> EncApp --> TransQ
    TransQ -->|可靠| TCP --> Handshake --> SeqNum
    TransQ -->|快| UDP --> Segment
    SeqNum --> FlowControl --> CongestQ
    CongestQ -->|开始| SlowStart --> Avoid
    Avoid --> LossQ
    LossQ -->|3 重复 ACK| FastRetrans --> Segment
    LossQ -->|超时| Timeout --> SlowStart
    Segment --> IP --> Route --> FragQ
    FragQ -->|超 MTU| Frag --> DataLink
    FragQ -->|否| DataLink
    DataLink --> ARP --> Physical --> Final

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef danger fill:#b91c1c,stroke:#7f1d1d,color:#fff,stroke-width:2px;"""


# ---- 主题：trade 交易/订单 ----
def theme_trade(fm, title):
    return """flowchart TD
    Start([🚀 用户下单]):::start
    Cart[购物车<br/>选择商品]:::process
    Settle[结算页<br/>确认收货/优惠]:::process
    StockLock[预扣库存<br/>Redis Lua 原子]:::process
    CouponQ{{使用优惠券?}}:::decision
    Coupon[核销优惠券<br/>幂等校验]:::process
    OrderCreate[生成订单<br/>状态:待支付]:::process
    IdempKey[幂等键<br/>防止重复创建]:::process
    Pay[发起支付<br/>微信/支付宝]:::process
    PayCallback[支付回调<br/>异步通知]:::process
    SignVerify[签名验证<br/>防伪造]:::process
    PayQ{{支付结果?}}:::decision
    PayFail[支付失败<br/>订单关闭]:::warn
    PaySuccess[支付成功<br/>状态:已支付]:::process
    MQ[(消息队列<br/>下游解耦)]:::store
    Inventory[库存服务<br/>DB 真实扣减]:::process
    Points[积分服务<br/>发放积分]:::process
    Logistics[物流服务<br/>生成运单]:::process
    Risk[风控服务<br/>反欺诈检测]:::process
    RiskQ{{风控通过?}}:::decision
    RiskReject[订单拦截<br/>退款]:::danger
    Notify[消息通知<br/>短信/Push]:::process
    Final([✅ 订单完成]):::start

    Start --> Cart --> Settle --> StockLock --> CouponQ
    CouponQ -->|是| Coupon --> OrderCreate
    CouponQ -->|否| OrderCreate
    OrderCreate --> IdempKey --> Risk
    Risk --> RiskQ
    RiskQ -->|通过| Pay
    RiskQ -->|拦截| RiskReject
    Pay --> PayCallback --> SignVerify --> PayQ
    PayQ -->|失败| PayFail
    PayQ -->|成功| PaySuccess --> MQ
    MQ --> Inventory & Points & Logistics
    Logistics --> Notify --> Final

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef store fill:#8b5cf6,stroke:#6d28d9,color:#fff;
    classDef warn fill:#fee2e2,stroke:#ef4444,color:#7f1d1d;
    classDef danger fill:#b91c1c,stroke:#7f1d1d,color:#fff,stroke-width:2px;"""


# ---- 主题：scm 供应链 ----
def theme_scm(fm, title):
    return """flowchart TD
    Start([🚀 供应链流程启动]):::start
    Forecast[需求预测<br/>历史+大促预估]:::process
    Plan[采购计划<br/>MRP 物料需求]:::process
    Supplier[供应商管理<br/>资质/价格/产能]:::process
    PO[采购订单 PO<br/>下单]:::process
    ReceiveQ{{到货验收?}}:::decision
    Reject[拒收退货<br/>质量不合格]:::warn
    Receive[入库收货<br/>WMS 扫码]:::process
    QC[质检 QC<br/>抽检/全检]:::process
    Putaway[上架<br/>分配库位]:::process
    Inventory[(库存中心<br/>SKU/库位/批次)]:::store
    Order[销售订单 SO<br/>客户下单]:::process
    AllocQ{{库存分配?<br/>ATP 可承诺量}}:::decision
    Shortage[缺货<br/>补货/分单]:::warn
    Pick[拣货<br/>波次拣选]:::process
    Pack[打包复核<br/>面单打印]:::process
    Ship[发货<br/>对接物流]:::process
    Track[物流追踪<br/>签收确认]:::process
    Return[逆向物流<br/>退货入库]:::process
    Final([✅ 交付完成]):::start

    Start --> Forecast --> Plan --> Supplier --> PO --> ReceiveQ
    ReceiveQ -->|不合格| Reject
    ReceiveQ -->|合格| Receive --> QC --> Putaway --> Inventory
    Inventory -.销售.-> Order --> AllocQ
    AllocQ -->|不足| Shortage --> PO
    AllocQ -->|充足| Pick --> Pack --> Ship --> Track --> Final
    Track -.退货.-> Return --> Receive

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef store fill:#8b5cf6,stroke:#6d28d9,color:#fff;
    classDef warn fill:#fee2e2,stroke:#ef4444,color:#7f1d1d;"""


# ---- 主题：content 内容/推荐 ----
def theme_content(fm, title):
    return """flowchart TD
    Start([🚀 用户访问内容]):::start
    Profile[用户画像<br/>长期兴趣+实时行为]:::process
    RecallStage[召回阶段 Recall<br/>百万级→千级]:::process
    RecallQ{{多路召回策略?}}:::decision
    CF[协同过滤<br/>User/Item CF]:::process
    ContentBased[内容召回<br/>标签匹配]:::process
    VectorRecall[向量召回<br/>ANN 检索]:::process
    HotRecall[热门召回<br/>兜底]:::process
    Merge[合并去重<br/>千级候选]:::process
    Filter[粗排过滤<br/>曝光去重/敏感]:::process
    RankStage[精排阶段 Ranking<br/>千级→百级]:::process
    Model[排序模型<br/>DSSM/Wide&Deep/DIN]:::process
    Features[特征工程<br/>用户/物品/上下文]:::process
    ScoreQ{{多目标?}}:::decision
    CTR[点击率预估<br/>pCTR]:::process
    CVR[转化率预估<br/>pCVR]:::process
    Combine[融合公式<br/>ctr*cvr*price]:::process
    Rerank[重排 Rerank<br/>多样性/打散]:::process
    BanditQ{{探索利用?<br/>EE 策略}}:::decision
    Explore[探索<br/>Bandit 新内容]:::process
    Exploit[利用<br/>Top 推荐位]:::process
    Final([✅ 返回推荐列表]):::start

    Start --> Profile --> RecallStage --> RecallQ
    RecallQ -->|相似用户| CF --> Merge
    RecallQ -->|标签| ContentBased --> Merge
    RecallQ -->|语义| VectorRecall --> Merge
    RecallQ -->|兜底| HotRecall --> Merge
    Merge --> Filter --> RankStage
    RankStage --> Features --> Model --> ScoreQ
    ScoreQ -->|单目标| CTR --> Rerank
    ScoreQ -->|多目标| CTR & CVR --> Combine --> Rerank
    Rerank --> BanditQ
    BanditQ -->|新内容| Explore --> Final
    BanditQ -->|稳定| Exploit --> Final

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef store fill:#8b5cf6,stroke:#6d28d9,color:#fff;"""


# ---- 主题：biopharm 生物医药 ----
def theme_biopharm(fm, title):
    return """flowchart TD
    Start([🚀 药物/靶点发现]):::start
    Target[靶点识别<br/>疾病-基因关联]:::process
    Validation[靶点验证<br/>体内外实验]:::process
    HitDiscovery[先导化合物发现<br/>高通量筛选 HTS]:::process
    ScreenQ{{筛选方式?}}:::decision
    Virtual[虚拟筛选<br/>分子对接 Docking]:::process
    AI[AI 筛选<br/>深度学习生成]:::process
    HTS[实验筛选<br/>化合物库]:::process
    HitOpt[先导优化<br/>SAR 构效关系]:::process
    PreClinic[临床前研究<br/>动物/细胞]:::process
    ADMET[ADMET 评估<br/>吸收/代谢/毒性]:::process
    ClinicQ{{进入临床?}}:::decision
    Phase1[I 期临床<br/>安全性 健康人]:::process
    Phase2[II 期临床<br/>有效性 患者]:::process
    Phase3[III 期临床<br/>大规模验证]:::process
    FailQ{{试验结果?}}:::decision
    Fail[失败终止<br/>重新优化]:::danger
    Approve[申报 NDA<br/>监管审批]:::process
    Market[上市销售<br/>商业化]:::process
    Phase4[IV 期临床<br/>上市后监测]:::process
    Final([✅ 药物上市]):::start

    Start --> Target --> Validation --> HitDiscovery --> ScreenQ
    ScreenQ -->|计算| Virtual --> HitOpt
    ScreenQ -->|AI| AI --> HitOpt
    ScreenQ -->|实验| HTS --> HitOpt
    HitOpt --> PreClinic --> ADMET --> ClinicQ
    ClinicQ -->|通过| Phase1 --> Phase2 --> Phase3 --> FailQ
    ClinicQ -->|失败| Fail
    FailQ -->|失败| Fail
    FailQ -->|成功| Approve --> Market --> Phase4 --> Final

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef danger fill:#b91c1c,stroke:#7f1d1d,color:#fff,stroke-width:2px;"""


# ---- 主题：fde 现场工程 ----
def theme_fde(fm, title):
    return """flowchart TD
    Start([🚀 接手烂尾/危机项目]):::start
    Assess[现状评估<br/>诚实不甩锅]:::process
    DiagQ{{根因诊断?}}:::decision
    CodeDebt[代码债<br/>架构/技术选型]:::process
    DataIssue[数据问题<br/>质量/完整性]:::process
    AlgoIssue[算法问题<br/>模型/调优]:::process
    ReqIssue[需求偏差<br/>理解错误]:::process
    Phase1[Phase 1 信任修复<br/>止血]:::process
    TopBugs[定位 Top 3 Bug<br/>24h 内修复]:::process
    CommitLow[降低承诺<br/>留余地]:::process
    Phase2[Phase 2 诊断<br/>1-2 周]:::process
    Audit[代码审计<br/>技术债清单]:::process
    Eval[效果评测<br/>量化当前水平]:::process
    Phase3[Phase 3 快速见效<br/>高价值场景]:::process
    QuickWin[10 个核心问题<br/>可视化展示]:::process
    DemoQ{{演示结果?}}:::decision
    Customer[客户验收<br/>重建信任]:::process
    Phase4[Phase 4 重新奠基<br/>长期]:::process
    Refactor[架构重构<br/>文档+评估体系]:::process
    Trace[留下交接痕迹<br/>防再烂尾]:::process
    Final([✅ 项目扭转为正循环]):::start

    Start --> Assess --> DiagQ
    DiagQ -->|代码| CodeDebt --> Phase1
    DiagQ -->|数据| DataIssue --> Phase1
    DiagQ -->|算法| AlgoIssue --> Phase1
    DiagQ -->|需求| ReqIssue --> Phase1
    Phase1 --> TopBugs --> CommitLow --> Phase2
    Phase2 --> Audit --> Eval --> Phase3
    Phase3 --> QuickWin --> DemoQ
    DemoQ -->|认可| Customer --> Phase4
    DemoQ -->|质疑| Eval
    Phase4 --> Refactor --> Trace --> Final

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;"""


# ---- 主题：engpractice 工程实践 ----
def theme_engpractice(fm, title):
    return """flowchart TD
    Start([🚀 需求进入研发流程]):::start
    Plan[需求评审<br/>拆分任务]:::process
    Design[技术设计<br/>方案评审]:::process
    Develop[开发编码<br/>本地自测]:::process
    CodeStyle[代码规范<br/>lint/格式化]:::process
    SelfTest[单元测试<br/>覆盖率 >80%]:::process
    CodeReview[Code Review<br/>同行评审]:::process
    ReviewQ{{Review 通过?}}:::decision
    Fix[修改问题<br/>迭代]:::warn
    CI[CI 流水线<br/>自动构建]:::process
    BuildQ{{构建+测试通过?}}:::decision
    BuildFail[失败通知<br/>修复]:::danger
    DeployDev[部署 Dev 环境<br/>联调]:::process
    TestQ[QA 测试<br/>功能+回归]:::process
    BugQ{{Bug 修复?}}:::decision
    BugFix[Bug 修复<br/>回归测试]:::warn
    DeployProd[部署生产<br/>灰度发布]:::process
    Canary[金丝雀发布<br/>小流量验证]:::process
    MonitorQ{{监控告警?}}:::decision
    Rollback[自动回滚<br/>快速止血]:::danger
    Stable[全量发布]:::process
    SRE[SRE 巡检<br/>SLA/SLO]:::process
    Final([✅ 上线稳定运行]):::start

    Start --> Plan --> Design --> Develop --> CodeStyle --> SelfTest --> CodeReview --> ReviewQ
    ReviewQ -->|拒绝| Fix --> CodeReview
    ReviewQ -->|通过| CI --> BuildQ
    BuildQ -->|失败| BuildFail
    BuildQ -->|通过| DeployDev --> TestQ --> BugQ
    BugQ -->|有| BugFix --> TestQ
    BugQ -->|无| DeployProd --> Canary --> MonitorQ
    MonitorQ -->|告警| Rollback
    MonitorQ -->|稳定| Stable --> SRE --> Final

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef warn fill:#fee2e2,stroke:#ef4444,color:#7f1d1d;
    classDef danger fill:#b91c1c,stroke:#7f1d1d,color:#fff,stroke-width:2px;"""


# ---- 主题：architect 架构 ----
def theme_architect(fm, title):
    return """flowchart TD
    Start([🚀 架构设计起点<br/>业务理解]):::start
    Domain[领域建模<br/>DDD 限界上下文]:::process
    BoundQ{{微服务边界?<br/>限界上下文}}:::decision
    Monolith[单体架构<br/>快速验证]:::warn
    Microservice[微服务<br/>独立部署]:::process
    SOA[SOA 服务化<br/>ESB 总线]:::process
    Decompose[服务拆分<br/>单一职责]:::process
    CommQ{{服务间通信?}}:::decision
    Sync[同步 RPC<br/>Dubbo/gRPC]:::process
    Async[异步 MQ<br/>解耦削峰]:::process
    EventDriven[事件驱动<br/>EDA]:::process
    DataQ{{数据一致性?}}:::decision
    Saga[Saga 分布式事务<br/>长流程]:::process
    TCC[TCC 补偿<br/>强一致]:::process
    FinalEvent[最终一致<br/>消息+补偿]:::process
    GovQ{{服务治理?}}:::decision
    Registry[注册中心<br/>服务发现]:::process
    Config[配置中心<br/>动态配置]:::process
    Monitor[全链路监控<br/>Trace/Metric/Log]:::process
    Govern[服务治理<br/>限流/熔断/降级]:::process
    Final([✅ 架构落地完成]):::start

    Start --> Domain --> BoundQ
    BoundQ -->|早期| Monolith --> Decompose
    BoundQ -->|主流| Microservice --> Decompose
    BoundQ -->|遗留| SOA --> Decompose
    Decompose --> CommQ
    CommQ -->|实时| Sync --> DataQ
    CommQ -->|解耦| Async --> DataQ
    CommQ -->|响应式| EventDriven --> DataQ
    DataQ -->|长事务| Saga --> GovQ
    DataQ -->|强一致| TCC --> GovQ
    DataQ -->|容忍| FinalEvent --> GovQ
    GovQ --> Registry & Config & Monitor & Govern --> Final

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef warn fill:#fee2e2,stroke:#ef4444,color:#7f1d1d;"""


# ---- 主题：coordination 注册中心/一致性 ----
def theme_coordination(fm, title):
    return """flowchart TD
    Start([🚀 服务注册与发现]):::start
    Provider[服务提供者<br/>启动]:::process
    Register[注册到注册中心<br/>写临时节点]:::process
    Registry[(注册中心<br/>Nacos/ZK/etcd)]:::store
    Consumer[服务消费者<br/>启动]:::process
    Subscribe[订阅服务列表<br/>拉取+长轮询]:::process
    Cache[本地缓存<br/>provider 列表]:::process
    Heartbeat[心跳上报<br/>5s 周期]:::process
    HealthQ{{健康检查?}}:::decision
    Healthy[节点健康<br/>保留注册]:::process
    Unhealthy[节点故障<br/>摘除]:::warn
    Push[推送变更<br/>消费者更新]:::process
    ElectionQ{{一致性协议?<br/>CP/AP}}:::decision
    Raft[Raft<br/>强一致 CP]:::process
    Distro[Distro<br/>最终一致 AP]:::process
    SplitQ{{网络分区?}}:::decision
    Minor[少数派不可用<br/>CP]:::warn
    Major[多数派可用<br/>保证一致]:::process
    Failover[消费者容错<br/>本地缓存兜底]:::process
    Config[配置中心<br/>动态配置]:::process
    Final([✅ 服务发现稳定]):::start

    Start --> Provider --> Register --> Registry
    Consumer --> Subscribe --> Registry --> Cache
    Provider --> Heartbeat --> HealthQ
    HealthQ -->|健康| Healthy
    HealthQ -->|故障| Unhealthy --> Push
    Registry --> ElectionQ
    ElectionQ -->|强一致| Raft --> SplitQ
    ElectionQ -->|高可用| Distro --> Failover
    SplitQ -->|分区| Minor
    SplitQ -->|正常| Major
    Push --> Failover --> Config --> Final

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef store fill:#8b5cf6,stroke:#6d28d9,color:#fff;
    classDef warn fill:#fee2e2,stroke:#ef4444,color:#7f1d1d;"""


# ---- 主题：cloudnative ----
def theme_cloudnative(fm, title):
    return """flowchart TD
    Start([🚀 应用容器化部署]):::start
    Code[源代码]:::process
    Dockerfile[编写 Dockerfile<br/>基础镜像+依赖]:::process
    Build[构建镜像<br/>docker build]:::process
    Image[(镜像仓库<br/>Registry)]:::store
    K8sCluster[K8s 集群<br/>控制面+数据面]:::process
    APIServer[API Server<br/>唯一入口]:::process
    Deploy[创建 Deployment<br/>声明式 YAML]:::process
    SchedulerQ{{调度决策?<br/>Scheduler}}:::decision
    Filter[预选 Filter<br/>资源/亲和性]:::process
    Score[优选 Score<br/>打分排序]:::process
    Bind[绑定到 Node<br/>更新 Pod]:::process
    Kubelet[Kubelet<br/>节点代理]:::process
    PullImage[拉取镜像<br/>CRI 接口]:::process
    Container[创建容器<br/>containerd]:::process
    ProbeQ{{健康探针?<br/>Liveness/Readiness}}:::decision
    Liveness[Liveness Probe<br/>失败重启]:::process
    Readiness[Readiness Probe<br/>就绪接流量]:::process
    RestartQ{{容器崩溃?}}:::decision
    Restart[重启策略<br/>Always]:::process
    ScaleQ{{HPA 自动扩缩?<br/>CPU/QPS}}:::decision
    Scale[水平扩缩<br/>动态调整副本]:::process
    Service[Service 服务<br/>稳定 ClusterIP]:::process
    Ingress[Ingress 入口<br/>七层路由]:::process
    Final([✅ 服务对外可用]):::start

    Start --> Code --> Dockerfile --> Build --> Image
    K8sCluster --> APIServer --> Deploy --> SchedulerQ
    Image -.拉取.-> PullImage
    SchedulerQ --> Filter --> Score --> Bind
    Bind --> Kubelet --> PullImage --> Container --> ProbeQ
    ProbeQ -->|存活| Liveness --> RestartQ
    ProbeQ -->|就绪| Readiness --> ScaleQ
    RestartQ -->|崩溃| Restart --> Container
    RestartQ -->|正常| ScaleQ
    ScaleQ -->|高峰| Scale --> Service
    ScaleQ -->|平稳| Service
    Service --> Ingress --> Final

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef store fill:#8b5cf6,stroke:#6d28d9,color:#fff;"""


# ---- 主题：generic 通用 ----
def theme_generic(fm, title):
    return """flowchart TD
    Start([🚀 问题/需求提出]):::start
    Analyze[需求分析<br/>明确边界]:::process
    Why1[第一性原理<br/>追问本质]:::process
    Design[方案设计<br/>架构与流程]:::process
    AltQ{{候选方案?<br/>权衡 Tradeoff}}:::decision
    PlanA[方案 A<br/>可靠性优先]:::process
    PlanB[方案 B<br/>性能优先]:::process
    PlanC[方案 C<br/>成本优先]:::warn
    Evaluate[综合评估<br/>场景适配]:::process
    Implement[编码实现<br/>关键路径]:::process
    Test[测试验证<br/>单元+集成]:::process
    EdgeQ{{边界情况?}}:::decision
    Edge[异常/并发/大流量<br/>特判处理]:::process
    Deploy[灰度上线<br/>可回滚]:::process
    Monitor[监控告警<br/>SLA 保障]:::process
    AlertQ{{出现告警?}}:::decision
    Rollback[快速回滚<br/>止血]:::danger
    Optimize[持续优化<br/>复盘沉淀]:::process
    Final([✅ 目标达成]):::start

    Start --> Analyze --> Why1 --> Design --> AltQ
    AltQ -->|稳定场景| PlanA --> Evaluate
    AltQ -->|高并发| PlanB --> Evaluate
    AltQ -->|成本敏感| PlanC --> Evaluate
    Evaluate --> Implement --> Test --> EdgeQ
    EdgeQ -->|有| Edge --> Deploy
    EdgeQ -->|无| Deploy
    Deploy --> Monitor --> AlertQ
    AlertQ -->|告警| Rollback
    AlertQ -->|正常| Optimize --> Final

    classDef start fill:#2563eb,stroke:#1e3a8a,color:#fff,stroke-width:2px;
    classDef process fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a;
    classDef decision fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:2px;
    classDef warn fill:#fee2e2,stroke:#ef4444,color:#7f1d1d;
    classDef danger fill:#b91c1c,stroke:#7f1d1d,color:#fff,stroke-width:2px;"""


THEMES = {
    'mq': theme_mq,
    'redis': theme_redis,
    'database': theme_database,
    'jvm': theme_jvm,
    'concurrent': theme_concurrent,
    'netty': theme_netty,
    'spring': theme_spring,
    'rpc': theme_rpc,
    'gateway': theme_gateway,
    'distributed': theme_distributed,
    'llm': theme_llm,
    'search': theme_search,
    'flashsale': theme_flashsale,
    'sysdesign': theme_sysdesign,
    'frontend': theme_frontend,
    'algorithm': theme_algorithm,
    'network': theme_network,
    'trade': theme_trade,
    'scm': theme_scm,
    'content': theme_content,
    'biopharm': theme_biopharm,
    'fde': theme_fde,
    'engpractice': theme_engpractice,
    'architect': theme_architect,
    'coordination': theme_coordination,
    'cloudnative': theme_cloudnative,
    'generic': theme_generic,
}


# ---------------------------------------------------------------------------
# 文件处理
# ---------------------------------------------------------------------------

def has_mermaid(content):
    return '```mermaid' in content


def make_section(theme_code, fm, title):
    body = render_flowchart(theme_code, fm, title)
    section = '## 核心流程图\n\n```mermaid\n' + body.strip() + '\n```\n'
    return section


def insert_before(content, section_text, anchor='## 记忆要点'):
    """在 anchor 前插入。anchor 不存在则插到 ## 结构化回答 前；都没有则追加到文件末尾。"""
    # 严格按行的标题匹配（前缀匹配，避免变体如 "## 记忆要点 / xxx"）
    pattern = re.compile(r'(^|\n)(##\s+' + re.escape(anchor[3:].strip()) + r')(\b|$)')
    if pattern.search(content):
        new_content, n = pattern.subn(r'\1' + section_text + r'\n\2', content, count=1)
        if n:
            return new_content
    # 兜底：## 结构化回答
    pattern2 = re.compile(r'(^|\n)(##\s+结构化回答)(\b|$)')
    if pattern2.search(content):
        new_content, n = pattern2.subn(r'\1' + section_text + r'\n\2', content, count=1)
        if n:
            return new_content
    # 最后兜底：追加
    return content.rstrip() + '\n\n' + section_text


def process_file(path, dry=False):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    if has_mermaid(content):
        return ('skip_has_mermaid', None)
    fm = parse_frontmatter(content)
    body = content
    theme = detect_theme(body, fm)
    title = _extract_title(body, fm)
    section = make_section(theme, fm, title)
    new_content = insert_before(content, section)
    if new_content == content:
        return ('no_anchor', theme)
    if not dry:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
    return ('ok', theme)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--only', help='仅处理指定分类(逗号分隔)')
    args = ap.parse_args()

    os.chdir(ROOT)

    only = set(args.only.split(',')) if args.only else None

    files = []
    for root, dirs, fs in os.walk('questions'):
        rel = os.path.relpath(root, 'questions')
        top = rel.split(os.sep)[0]
        if top not in SCOPE_DIRS:
            continue
        for f in sorted(fs):
            if not f.endswith('.md'):
                continue
            files.append(os.path.join(root, f))

    stats = {'ok': 0, 'skip_has_mermaid': 0, 'no_anchor': 0, 'error': 0}
    theme_count = {}
    failed = []
    total = 0
    for path in files:
        if only and os.path.relpath(path, 'questions').split(os.sep)[0] not in only:
            continue
        try:
            with open(path, 'r', encoding='utf-8') as f:
                if '```mermaid' not in f.read():
                    pass
                else:
                    stats['skip_has_mermaid'] += 1
                    continue
        except Exception:
            stats['error'] += 1
            failed.append((path, 'read_fail'))
            continue
        total += 1
        if args.limit and total > args.limit:
            break
        try:
            status, theme = process_file(path, dry=args.dry_run)
            stats[status] = stats.get(status, 0) + 1
            if theme:
                theme_count[theme] = theme_count.get(theme, 0) + 1
            if status == 'no_anchor':
                failed.append((path, 'no_anchor'))
        except Exception as e:
            stats['error'] += 1
            failed.append((path, str(e)))

    print('===== 处理统计 =====')
    print('待处理(无 mermaid):', total)
    print('已写入:', stats.get('ok', 0))
    print('已有 mermaid(跳过):', stats.get('skip_has_mermaid', 0))
    print('未找到锚点:', stats.get('no_anchor', 0))
    print('错误:', stats.get('error', 0))
    print('===== 主题分布 =====')
    for k, v in sorted(theme_count.items(), key=lambda x: -x[1]):
        print(f'  {k}: {v}')
    if failed:
        print('===== 失败列表(前20) =====')
        for p, e in failed[:20]:
            print(f'  {p} : {e}')


if __name__ == '__main__':
    main()
