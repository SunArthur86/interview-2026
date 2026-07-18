---
id: scen-036
difficulty: L3
category: scenario
subcategory: 社交与IM
tags:
- 协同编辑
- OT算法
- CRDT
- 冲突解决
- WebSocket
- 操作变换
feynman:
  essence: OT/CRDT解决冲突，操作日志同步，快照持久化。
  analogy: 像多人同时改一张草稿纸：OT是改的时候告诉别人“我在第三行加了字”，CRDT是每行字都有编号自动排队。
  first_principle: 如何让多人同时编辑同一内容而不打架、数据不乱？
  key_points:
  - OT需中心协调，CRDT支持P2P自动合并
  - WebSocket实时广播操作流
  - 定期快照+增量日志恢复文档
  - 冲突解决：算法定序或数据结构合并
follow_up:
- OT和CRDT有什么区别？
- 如何处理大规模并发编辑？
- 离线编辑如何同步？
memory_points:
- 核心难点：多人实时并发编辑引发的内容冲突与一致性，防抖与最终收敛是关键
- OT算法：操作转换，强依赖中心服务器定序，转换函数极难实现（Google Docs代表）
- CRDT算法：无冲突复制数据类型，不依赖中心，数学上保证自然收敛，但元数据开销大（Figma代表）
- 工程落地：长连接广播Op日志，高频操作按100ms时间窗口合并压缩，文档快照+Op回放恢复
---

# 如何设计一个在线协同编辑系统？类似Google Docs / 腾讯文档。

【场景分析】
协同编辑核心挑战：多人同时编辑同一文档、实时同步、冲突解决、一致性保证。

**实战案例**：曾遇到因网络波动导致客户端连接断开重连后，Op Log同步出现乱序，文档内容混乱。解决方案是客户端重连时带上本地的Version向量，服务端只发送增量的Op Log，并增加严格的版本号校验。

【两种核心算法】

【1. OT算法（Operational Transformation）】
- Google Docs使用
- **原理细节**：基于操作转换。设 $Op_1$ 和 $Op_2$ 是并发操作，定义转换函数 $T(Op_1, Op_2)$，使得 $Op_1$ 在 $Op_2$ 之后的执行结果等价于 $T(Op_1, Op_2)$ 在 $Op_2$ 之前执行。核心是满足 $TP2$（变换后保持原意）和 $C1$（收敛性）定理。
- **示例**：A在第3位插入"X"，B删除第5位字符
  - 对B：B的操作在A插入后，删除位置+1 → 删除第6位
- **缺点**：服务端必须是中央协调器来定序，强依赖服务端状态，算法实现极其复杂。

【2. CRDT（Conflict-free Replicated Data Type）】
- 腾讯文档/Figma/Yjs使用
- **原理细节**：基于数学的幂等半环结构。利用RGA（Replicated Growable Array）或 LWW-Element-Set。每个字符分配唯一ID (ClientID + Counter + Lamport Timestamp)。
- **优势**：最终一致性自然收敛，支持离线编辑，无序网络下可用，无需服务端定序。
- **缺点**：元数据开销大（通常是文本内容的5-10倍），删除操作需保留"墓碑"（Tombstone）标记，需定期GC。

**对比表格：OT vs CRDT**

| 维度 | OT (Operational Transformation) | CRDT (Conflict-free Replicated Data Types) |
| :--- | :--- | :--- |
| **一致性模型** | 强一致性（需中心定序） | 最终一致性（自然收敛） |
| **网络依赖** | 需稳定连接，转换依赖服务端状态 | 支持离线编辑，断网可继续操作 |
| **元数据开销** | 低 | 高（需携带ID、Lamport时间戳等） |
| **实现复杂度** | 极高（Transform函数难写） | 中等（数据结构定义较难） |
| **典型应用** | Google Docs | 腾讯文档、Figma、Notion |

【系统架构】

```text
┌──────────┐  WebSocket  ┌─────────────┐  Op/Log  ┌───────────┐
│ Client A │ ──────────> │             │ ────────> │           │
└──────────┘             │             │           │           │
┌──────────┐             │  Gateway &  │           │  Storage  │
│ Client B │ ──────────> │ Collaborate │ ────────> │  Service  │
└──────────┘             │   Engine    │           │           │
                         │  (OT/CRDT)  │           └───────────┘
┌──────────┐             │             │                 │
│ Client C │ ──────────> │             │ <───────────────┘
└──────────┘             └─────────────┘
                               │
                               ▼
                         ┌───────────┐
                         │ Message   │
                         │ Queue (MQ)│
                         └───────────┘
```

1. 连接层：
   - WebSocket长连接 + 心跳保活（30s间隔）
   - 文档ID Hash 分片路由到不同的协同引擎节点（单机百万连接优化）
2. 协同引擎：
   - 接收操作 → 序列化 → OT/CRDT变换 → 广播
   - **操作压缩**：高频输入（如打字）在100ms窗口内合并，只广播最终结果。
3. 存储层：
   - **文档快照**：每隔10分钟或每1000次操作存储全量。
   - **操作日志**：仅追加，不可变。
   - **恢复流程**：加载最近快照 → 回放快照之后的Op Log → 内存重建文档树。

【关键技术点】
1. 感知一致性：
   - 用户A看到的操作应基于"自己已发出的操作"进行变换，避免"抖动"。
2. 光标与选择区同步：
   - 独立于内容流的通道广播，基于相对位置（如果附近内容变化，光标需随之漂移）。
3. **冲突边界处理**：
   - OT难点在于"Undo/Redo"操作，需要将Undo也视为一种Op进行转换。

**代码示例（CRDT 字符插入简化逻辑 - Yjs风格伪代码）**：
```javascript
// 客户端生成操作：在 index 2 处插入 'x'
const insertOp = {
    type: 'insert',
    content: 'x',
    id: clientID + '-' + clock++,  // 唯一ID：user:0_5
    origin: leftId,                // 左侧字符的ID（用于定位）
    right: rightId                 // 右侧字符的ID（用于定位）
};

// 集合CRDT合并逻辑（简化版）
function integrate(op, docArray) {
    // 根据Lamport Timestamp或ID排序逻辑找到插入位置
    // 如果位置冲突，利用ClientID的确定性比较（如字符串比较）来解决
    const index = findIndex(docArray, op.origin, op.right);
    docArray.splice(index, 0, op);
}
```

【性能优化】
- **本地优先**

## 核心知识点图

<img src="/interview-2026/images/diagram_scenario_scen-036.svg" alt="如何设计一个在线协同编辑系统？类似Google Docs / 腾讯文档。 - 核心知识点图" style="max-width:100%;height:auto;border:1px solid var(--border);border-radius:8px;margin:1em 0;" />

## 记忆要点

- 核心难点：多人实时并发编辑引发的内容冲突与一致性，防抖与最终收敛是关键
- OT算法：操作转换，强依赖中心服务器定序，转换函数极难实现（Google Docs代表）
- CRDT算法：无冲突复制数据类型，不依赖中心，数学上保证自然收敛，但元数据开销大（Figma代表）
- 工程落地：长连接广播Op日志，高频操作按100ms时间窗口合并压缩，文档快照+Op回放恢复

## 结构化回答




**30 秒电梯演讲：** 像多人同时改一张草稿纸：OT是改的时候告诉别人“我在第三行加了字”，CRDT是每行字都有编号自动排队。

**展开框架：**
1. **OT** — OT需中心协调，CRDT支持P2P自动合并
2. **WebSocket** — WebSocket实时广播操作流
3. **定期快照+增** — 定期快照+增量日志恢复文档

**收尾：** OT和CRDT有什么区别？




## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：在线协同编辑系统 | "在线协同编辑系统，这题我会分三步讲。" | 开场钩子 |
| 0:41 | 概念定义动画 | "一句话：OT/CRDT解决冲突，操作日志同步，快照持久化。" | 核心定义 |
| 1:22 | 生活类比动画 | "打个比方——像多人同时改一张草稿纸：OT是改的时候告诉别人“我在第三行加了字”，CRDT是每行字都有编号自动排队。" | 核心类比 |
| 2:03 | OT需中心协调 图解 | "OT需中心协调，CRDT支持P2P自动合并。" | OT需中心协调 |
| 2:50 | WebSocket实 图解 | "WebSocket实时广播操作流。" | WebSocket实 |
