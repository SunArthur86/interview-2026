---
id: ai-scen-025
difficulty: L3
category: ai-scenario
subcategory: LLM推理与部署
tags:
- 端侧部署
- llama.cpp
- 量化压缩
- 知识蒸馏
- 端云协同
- MLC-LLM
feynman:
  essence: 通过量化压缩和框架优化，在资源受限的设备上运行模型。
  analogy: 把大胖子（模型）压缩成精瘦特种兵，塞进手机里干活。
  first_principle: 如何在低内存、无GPU的终端设备上高效运行大模型？
  key_points:
  - 选1B-3B小模型并做INT4量化压缩
  - 用llama.cpp等跨平台框架加速推理
  - 简单任务端侧跑，复杂任务上云端（端云协同）
  - 利用KV Cache和内存映射节省显存与功耗
follow_up:
- 端侧1.5B模型能胜任哪些任务？
- 如何平衡模型大小和电池消耗？
- 端侧部署的数据隐私优势如何量化？
memory_points:
- 核心约束：内存受限（4-8GB），需INT4量化（1.5B模型约800MB）+KV Cache清理防OOM。
- 推理框架：iOS首选Core ML（ANE加速），Android选MediaPipe/MLC-LLM，跨平台选llama.cpp。
- 端云协同：隐私/简单任务端侧，复杂/耗电任务上云；基于Prompt复杂度动态路由。
- 性能优化：滑动窗口分段摘要、Speculative Decoding加速、内存映射按需加载。
- 关键指标：iPhone 15 Pro跑1.5B INT4，内存约1GB，速度15-20 tokens/s。
frequency: high
---

# 如何设计端侧LLM部署方案？在手机或IoT设备上运行大语言模型。

【场景分析】
端侧LLM部署场景：手机助手、车载系统、IoT设备。核心约束：内存有限（4-8GB）、无GPU、电池敏感。

**【实战案例】**
在开发离线会议摘要App时，直接使用FP16的3B模型导致老款Android手机频繁OOM（内存溢出）。将模型量化为INT4后，内存占用从6GB降至1.2GB，但在长会议（>30分钟）转录时仍会因KV Cache增长过大而闪退。最终采用“滑动窗口+分段摘要”策略：每处理5分钟文本清理一次KV Cache，生成中间摘要，最后汇总摘要，成功在低端机上稳定运行。此外，iPhone上利用Core ML的ANE加速，推理速度相比纯CPU提升3倍。

【模型选择与压缩】
1. 模型选型：
   - 小模型：Qwen2.5-1.5B/3B / Gemma-2B / Phi-3-mini
   - 蒸馏模型：从大模型蒸馏的小模型保持较好效果
   - MoE小模型：激活参数少但总参数大
2. 量化压缩：
   - INT4量化：1.5B模型约800MB，可在手机运行
   - GPTQ/AWQ：训练后量化，无需重训
   - QLoRA：4bit推理 + 低秩适配
3. 剪枝与蒸馏：
   - 结构化剪枝：删除不重要的注意力头/层
   - 知识蒸馏：大模型→小模型，保留关键能力

【推理框架】
- llama.cpp：C++实现，支持CPU/GPU/Metal，跨平台
- MLC-LLM：移动端优化，支持iOS/Android
- MediaPipe LLM：Google方案，Android原生
- Core ML：Apple生态，利用Neural Engine

【性能优化】
- KV Cache量化：减少内存占用
- Speculative Decoding：草稿模型加速
- 内存映射：模型文件mmap，按需加载
- 流式输出：逐Token生成，不等完整响应

【端云协同策略】
- 分层路由：简单任务端侧处理，复杂任务上传云端
- 预加载：根据用户习惯预加载模型到内存
- 降级策略：内存不足时切换到更小模型
- 隐私优先：敏感数据（如短信内容）端侧处理

【端云协同架构】
```text
┌──────────────────────┐
│    On-Device App     │
│  (iOS / Android)     │
│                      │
│ ┌──────────────────┐ │
│ │  Local LLM (INT4)│ │<──┐
│ │  (Privacy/Low    │ │   │
│ │   Latency)       │ │   │ Offload
│ └────────┬─────────┘ │   │ Strategy
│          │           │   │
│    Router│           │   │
│          │           │   │
└──────────┼───────────┘   │
           │               │
           │ (Cloud Path)  │
           ▼               │
    ┌──────────────┐       │
    │ Cloud LLM    │       │
    │ (Reasoning/  │───────┘
    │  Knowledge)  │
    └──────────────┘
```

【典型指标】
- 1.5B INT4模型在iPhone 15 Pro上：
  - 内存占用：约1GB
  - 生成速度：约15-20 tokens/s
  - 首Token延迟：约300ms
  - 电池影响：连续使用1小时约消耗10%电量

## 常见考点
1. **端侧模型的内存占用主要来自哪里？**
   - 模型权重（主要部分，通过INT4量化压缩）和KV Cache（随上下文长度增长）。推理时需动态分配KV Cache，需严格限制最大上下文长度以防止OOM。
2. **如何解决端侧推理发热和耗电问题？**
   - 利用NPU（神经网络处理器）而非CPU进行推理，效率更高；限制每秒生成的Token数（TPS）以平摊功耗；后台任务暂停推理。
3. **端云协同的决策逻辑是什么？**
   - 基于Prompt复杂度、设备电量、网络状况动态决策。例如：检测到“总结文档”且电量低→上云；检测到“设置闹钟”→端侧。
4. **移动端推理框架的选择依据？**
   - iOS首选Core ML（最佳硬件加速），Android首选MediaPipe或MLC-LLM（兼容性好），跨平台首选llama.cpp。

**【代码示例：端云路由决策】**
```python
import psutil

def decide_route(prompt: str, context: dict):
    # 1. 检查敏感词（隐私优先）
    if contains_sensitive_data(prompt):
        return "local"
    
    # 2. 检查上下文长度（端侧模型通常限制Context Window）
    if len(prompt) > 2000:
        return "cloud"
        
    # 3. 检查设备状态（电量/内存）
    battery = psutil.sensors_battery()
    if battery.percent < 20 and not battery.power_plugged:
        return "cloud" # 省电模式
        
    # 4. 意图分类（简单任务本地化）
    intent = classify_intent(prompt)
    if intent in ["alarm", "call", "note"]:
        return "local"
    
    return "cloud"
```

**【推理框架对比】**

| 框架 | 核心优势 | 支持平台 | 硬件加速 | 适用模型格式 |
| :--- | :--- | :--- | :--- | :--- |
| **llama.cpp** | 轻量、兼容性最强 | iOS/Android/Web/PC | CPU/Metal/Vulkan | GGUF (量化首选) |
| **MLC LLM** | TVM生态，编译优化极深 | iOS/Android/Web | Vulkan/Metal/OpenGL | MLC格式 (需编译) |
| **MediaPipe** | Google官方，集成度高 | Android/iOS/Web | GPU/NPU | TFLite (有限) |
| **Core ML** | Apple生态原生性能 | iOS/macOS | ANE (NPU) | Core ML模型 |


## 核心流程图

```mermaid
flowchart TD
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
    classDef danger fill:#b91c1c,stroke:#7f1d1d,color:#fff,stroke-width:2px;

```

## 记忆要点

- 核心约束：内存受限（4-8GB），需INT4量化（1.5B模型约800MB）+KV Cache清理防OOM。
- 推理框架：iOS首选Core ML（ANE加速），Android选MediaPipe/MLC-LLM，跨平台选llama.cpp。
- 端云协同：隐私/简单任务端侧，复杂/耗电任务上云；基于Prompt复杂度动态路由。
- 性能优化：滑动窗口分段摘要、Speculative Decoding加速、内存映射按需加载。
- 关键指标：iPhone 15 Pro跑1.5B INT4，内存约1GB，速度15-20 tokens/s。


## 结构化回答

**30 秒电梯演讲：** 通过量化压缩和框架优化，在资源受限的设备上运行模型。——打个比方，把大胖子（模型）压缩成精瘦特种兵，塞进手机里干活。

**展开框架：**
1. **核心约束** — 内存受限（4-8GB），需INT4量化（1.5B模型约800MB）+KV Cache清理防OOM。
2. **推理框架** — iOS首选Core ML（ANE加速），Android选MediaPipe/MLC-LLM，跨平台选llama.cpp。
3. **端云协同** — 隐私/简单任务端侧，复杂/耗电任务上云；基于Prompt复杂度动态路由。

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「端侧1.5B模型能胜任哪些任务」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "设计端侧LLM部署方案，30 秒讲清楚。" | 开场钩子 |
| 0:36 | 概念定义动画 | "一句话：通过量化压缩和框架优化，在资源受限的设备上运行模型。" | 核心定义 |
| 1:12 | 核心约束图解 | "内存受限（4-8GB），需INT4量化（1.5B模型约800MB）+KV Cache清理防OOM。" | 核心约束 |
| 1:48 | 推理框架图解 | "iOS首选Core ML（ANE加速），Android选MediaPipe/MLC-LLM，跨平台选llama.cpp。" | 推理框架 |
| 2:24 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
