---
id: ai-scen-022
difficulty: L3
category: ai-scenario
subcategory: LLM推理与部署
tags:
- 模型网关
- LiteLLM
- 智能路由
- 限流
- 成本管理
- 故障转移
feynman:
  essence: 作为应用与模型间的中间件，统一接口、智能路由并管控多供应商的流量与成本。
  analogy: 像万能旅行插座适配器，既插即用还能根据电压要求自动切换最佳电源。
  first_principle: 如何在多供应商异构环境下，提供稳定、高效且可控的模型调用服务？
  key_points:
  - 通过适配器模式统一异构模型API，屏蔽底层差异
  - 基于能力、成本或延迟的多维度智能路由策略
  - 精细化限流熔断与成本预算控制防止超支
  - 全链路追踪保障高可用与可观测性
follow_up:
- 如何设计模型路由的决策策略？
- 多供应商之间的输出格式差异如何兼容？
- 模型网关自身如何保证高可用？
memory_points:
- 核心职责：统一接口适配、智能路由（成本/能力/延迟）、流量治理、成本归因。
- 路由策略：代码→DeepSeek，创意→Claude，通用→GPT-4，故障自动切换。
- 流量治理：限流（RPM/TPM）、熔断（连续错误暂停）、重试（指数退避）。
- 成本管理：Token计量关联租户，预算控制超额拒绝，Key加密存储。
- 实战价值：网关熔断防OpenAI宕机瘫痪，动态Key刷新防Git泄露风险。
---

# 如何设计一个模型网关（Model Gateway）系统？统一管理多个LLM供应商的路由、限流和成本。

【场景分析】
模型网关是生产级AI应用的必备组件：统一接入多个LLM供应商、路由、限流、成本追踪。

**【实战案例】**
某金融客服项目初期直接对接OpenAI，某日OpenAI API大面积宕机，导致客服全线瘫痪。接入网关后，配置了熔断器，当检测到错误率>50%时，50ms内自动切换至Azure OpenAI，实现业务无感。此外，某次开发人员误将API Key提交至Git，网关的动态Key刷新功能避免了Key泄露后的长期风险。

【核心职责】
1. 供应商适配：
   - 统一接口：OpenAI/Anthropic/Azure/本地模型 → 统一API格式
   - 参数映射：不同供应商的temperature/max_tokens等参数映射
   - 流式协议适配：SSE/WebSocket统一
2. 智能路由：
   - 基于能力路由：代码任务→DeepSeek，创意→Claude，通用→GPT-4
   - 基于成本路由：简单任务→便宜模型，复杂→贵模型
   - 基于延迟路由：选择响应最快的供应商
   - 基于可用性路由：自动故障转移
3. 流量治理：
   - 限流：RPM（请求/分钟）、TPM（Token/分钟）、并发数
   - 熔断：供应商连续错误 → 暂停路由到该供应商
   - 重试：瞬态错误自动重试（指数退避）
   - 降级：主模型不可用 → 自动切换备选
4. 成本管理：
   - Token计量：按供应商定价计算费用
   - 成本归因：费用关联到租户/用户/功能/Prompt版本
   - 预算控制：租户级Token预算，超额拒绝
   - 成本报表：按维度统计成本趋势

【技术选型】
- 开源方案：LiteLLM / Portkey / OneAPI
- 自研优势：深度定制路由策略和成本模型
- 关键能力：低延迟（<10ms路由开销）、高可用（99.9%+）

【设计要点】
- 异步非阻塞：路由层不成为瓶颈
- 可插拔：新增供应商只需实现适配器接口
- 可观测：每次调用的全链路Trace
- 安全：API Key加密存储、最小权限原则

**【代码示例：统一适配接口】**
```python
# 定义统一的请求响应模型
class UnifiedRequest(BaseModel):
    model: str
    messages: List[Dict]
    temperature: float = 0.7
    stream: bool = False

# 供应商适配器接口
class ProviderAdapter(ABC):
    @abstractmethod
    async def completion(self, req: UnifiedRequest) -> AsyncIterator[str]:
        pass

# OpenAI适配实现
class OpenAIAdapter(ProviderAdapter):
    async def completion(self, req: UnifiedRequest) -> AsyncIterator[str]:
        client = AsyncOpenAI(api_key=self._get_key())
        stream = await client.chat.completions.create(
            model=req.model, messages=req.messages, stream=True
        )
        async for chunk in stream:
            yield chunk.choices[0].delta.content or ""
```

**【开源方案对比】**

| 特性 | LiteLLM | Portkey | OneAPI | 自研方案 |
| :--- | :--- | :--- | :--- | :--- |
| **接入难度** | 低（一行代码） | 低（SDK丰富） | 中（需部署服务） | 高（全栈开发） |
| **路由策略** | 预设规则 | 预设+简单权重 | 基础负载均衡 | **深度定制（如意图识别路由）** |
| **成本观测** | 基础统计 | 详细Dashboard | 基础统计 | **完全自定义（如按部门分摊）** |
| **性能开销** | 低 (<20ms) | 低 (<30ms) | 中 (>50ms) | **最低 (<10ms)** |
| **适用场景** | 快速M验证 | 中小企业统一管理 | 多模型私有化部署 | 大型企业核心业务 |

## 记忆要点

- 核心职责：统一接口适配、智能路由（成本/能力/延迟）、流量治理、成本归因。
- 路由策略：代码→DeepSeek，创意→Claude，通用→GPT-4，故障自动切换。
- 流量治理：限流（RPM/TPM）、熔断（连续错误暂停）、重试（指数退避）。
- 成本管理：Token计量关联租户，预算控制超额拒绝，Key加密存储。
- 实战价值：网关熔断防OpenAI宕机瘫痪，动态Key刷新防Git泄露风险。


## 结构化回答

**30 秒电梯演讲：** 作为应用与模型间的中间件，统一接口、智能路由并管控多供应商的流量与成本。——打个比方，像万能旅行插座适配器，既插即用还能根据电压要求自动切换最佳电源。

**展开框架：**
1. **核心职责** — 统一接口适配、智能路由（成本/能力/延迟）、流量治理、成本归因。
2. **路由策略** — 代码→DeepSeek，创意→Claude，通用→GPT-4，故障自动切换。
3. **流量治理** — 限流（RPM/TPM）、熔断（连续错误暂停）、重试（指数退避）。

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「如何设计模型路由的决策策略」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "设计一个模型网关（Model Gateway）系统，30 秒讲清楚。" | 开场钩子 |
| 0:36 | 概念定义动画 | "一句话：作为应用与模型间的中间件，统一接口、智能路由并管控多供应商的流量与成本。" | 核心定义 |
| 1:12 | 核心职责图解 | "统一接口适配、智能路由（成本/能力/延迟）、流量治理、成本归因。" | 核心职责 |
| 1:48 | 路由策略图解 | "代码→DeepSeek，创意→Claude，通用→GPT-4，故障自动切换。" | 路由策略 |
| 2:24 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
