---
id: misc-034
difficulty: L2
category: ai-basics
subcategory: Prompt Engineering
tags:
- IO
- Elasticsearch
feynman:
  essence: 通过格式约束与结构化定义引导模型输出标准JSON数据。
  analogy: 像填表一样给模型空格子，并告诉他不要在格子外写字。
  first_principle: 如何解决非结构化文本输出难以被程序解析和集成的问题？
  key_points:
  - 优先使用Function Calling或原生JSON Mode
  - 提供JSON Schema和Few-shot示例
  - 设置低温度并配合后处理校验
follow_up:
- Function Calling和JSON Mode有什么区别?
- 如何处理模型输出不合法JSON的情况?
memory_points:
- 核心方法：优先用Function Calling或JSON Mode，通用法用Prompt+Schema
- Prompt三要素：XML标签分隔、提供Schema、明确只输出JSON
- 参数设置：温度设为0，预留足够max_tokens防止截断
- 后处理鲁棒性：正则提取JSON块，用json5容错解析，Pydantic校验
- Few-shot作用：复杂结构给示例比单纯描述Schema更有效
---

# 如何设计结构化Prompt确保LLM稳定输出JSON?有哪些最佳实践

- **结构化JSON输出的方法:**

- **方法1:Function Calling / Tool Use(最可靠)**
```json
{"type": "function", "function": {"name": "extract", "parameters": {"type": "object", "properties": {...}}}}
```

- **方法2:JSON Mode(OpenAI/Anthropic原生支持)**
- 设置 response_format = {"type": "json_object"}

- **方法3:结构化Prompt(通用)**
- 用XML标签分隔指令、示例、输出格式
- 提供JSON Schema
- 使用「只输出JSON,不要其他内容」约束

- **最佳实践:**
1. 提供明确的输出Schema(字段名+类型+描述)
2. 给2-3个Few-shot示例
3. 温度设为0
4. 后处理:正则提取JSON / json5解析 / 重试机制
5. 用Pydantic/Zod定义schema并验证

- **鲁棒性设计流程:**

```text
User Request
    │
    ▼
┌───────────────────┐
│ LLM (Temp=0)      │
│ Prompt + Schema   │
└──────┬────────────┘
       │ Raw Output
       ▼
┌───────────────────┐
│ Output Parser     │
│ 1. Regex Extract  │◄── Handle "```json ... ```"
│ 2. JSON Loader    │◄── Handle json5/missing quotes
└──────┬────────────┘
       │
       ▼ Valid? ──No──▶ Retry (Max 3x)
       │ Yes
       ▼
Pydantic Validation
       │
       ▼
   Structured Data
```

## 常见考点
1. **即使使用了 JSON Mode，为什么还需要后处理？**
   - 模型可能会在 JSON 前后添加解释性文字（如 "Here is the JSON: ..."），或者偶尔输出不合法的 JSON（如尾随逗号）。正则提取 `\{.*\}` 和容错解析器（如 `json5` 或 `lark`）能显著提升鲁棒性。

2. **Few-shot 示例在 JSON 提取中的作用？**
   - 对于复杂结构或罕见字段，提供一个完整的输入-输出 JSON 示例比单纯的 Schema 描述更有效，能帮助模型理解嵌套关系和格式要求。

3. **如果模型总是输出不完整怎么办？**
   - 可能是 `max_tokens` 设置过小导致截断。建议预估 JSON 长度并预留足够的 Token 余量，或者使用支持流式 JSON 解析的库进行增量处理。

- **实战案例**：在开发舆情分析 Agent 时，即使指定了 JSON Mode，模型偶尔仍会在 JSON 前输出「以下是根据分析生成的结果：」导致解析器报错。通过引入正则提取 + `json5` 容错解析的双重保险后，服务的稳定性从 95% 提升到了 99.9%。

- **代码示例**：
```python
import re
import json5

def robust_json_parse(text: str):
    # 1. 尝试正则提取第一个 {} 块
    match = re.search(r'\{.*\}', text, re.DOTALL)
    json_str = match.group(0) if match else text
    
    # 2. 使用 json5 处理尾随逗号或注释等非标准格式
    try:
        return json5.loads(json_str)
    except Exception:
        return None  # 触发重试逻辑
```

## 边界情况
1. **空数组/对象的差异**：在定义 Schema 时，明确区分 `null`、`[]` 和 `{}` 的含义，防止模型在无数据时混淆输出。
2. **特殊字符转义**：当用户输入包含换行符、引号或非 ASCII 字符时，容易破坏 JSON 结构。需确保 LLM 理解转义规则，或使用 Marshaling/Unmarshaling 机制在 Prompt 层做隔离。
3. **枚举值幻觉**：如果 Schema 中包含 Enum（如 `status: ["active", "inactive"]`），模型仍可能输出未定义的值。必须在 Pydantic 验证层严格捕获此类错误。

## 易错点
1. **省略 Schema 描述**：很多人只给 JSON 结构示例而不给字段含义描述，导致模型在相似字段间产生歧义（如 `start_date` 和 `create_date`）。
2. **过度依赖 JSON Mode**：认为开启 JSON Mode 就能 100% 保证格式正确，忽略了模型仍可能生成 `null` 或截断后的 JSON 字符串，必须结合业务逻辑验证。

## 面试追问
1. **追问**：如果业务要求必须输出特定的嵌套 JSON 结构（如包含中文字段名），如何保证稳定输出？
2. **追问**：在流式输出场景下，如何实时校验和解析不完整的 JSON 片段而不阻塞响应？
3. **追问**：对比 `json5` 和 `lark` 解析器，在处理 LLM 输出时的容错能力有何区别？

## 核心知识点图

<img src="/interview-2026/images/diagram_ai-basics_misc-034.svg" alt="如何设计结构化Prompt确保LLM稳定输出JSON?有哪些最佳实践 - 核心知识点图" style="max-width:100%;height:auto;border:1px solid var(--border);border-radius:8px;margin:1em 0;" />

## 记忆要点

- 核心方法：优先用Function Calling或JSON Mode，通用法用Prompt+Schema
- Prompt三要素：XML标签分隔、提供Schema、明确只输出JSON
- 参数设置：温度设为0，预留足够max_tokens防止截断
- 后处理鲁棒性：正则提取JSON块，用json5容错解析，Pydantic校验
- Few-shot作用：复杂结构给示例比单纯描述Schema更有效

## 结构化回答

**30 秒电梯演讲：** 让 LLM 稳定输出 JSON，像填表一样给它空格子并告诉它别在格子外写字。优先用 Function Calling 或原生 JSON Mode；通用法是 Prompt 加 Schema 三要素：XML 标签分隔、提供 Schema、明确只输出 JSON。参数上温度设 0、max_tokens 留够防截断，再用正则加 json5 加 Pydantic 做后处理兜底。

**展开框架：**
1. **方法选型** — 优先用 Function Calling 或原生 JSON Mode（模型层面约束，最稳）；通用场景用 Prompt + Schema 组合，兼容性最好。
2. **Prompt 三要素与参数** — XML 标签分隔用户内容与指令、提供清晰的 JSON Schema、明确声明"只输出 JSON"；温度设为 0 降低随机性，max_tokens 预留充足防止结构截断。
3. **后处理与 Few-shot** — 用正则提取 JSON 块、json5 容错解析、Pydantic 做字段校验，保证鲁棒；复杂嵌套结构给 Few-shot 示例比单纯描述 Schema 更有效。

**收尾：** 一句话，稳定 JSON = 模型约束 + Prompt 约束 + 后处理兜底。您想深入聊聊 Function Calling 和 JSON Mode 的区别，还是怎么处理模型输出不合法 JSON？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题《让 LLM 输出 JSON》+ 填表漫画 | 让模型稳定输出 JSON，像填表一样给它空格子，并告诉它别在格子外写字。 | 类比开场 |
| 0:25 | 方法优先级：Function Calling / JSON Mode / Prompt+Schema | 方法选型有优先级：首选 Function Calling 或原生 JSON Mode，模型层面约束最稳；通用场景用 Prompt 加 Schema。 | 方法选型 |
| 0:55 | Prompt 三要素：XML 分隔 + Schema + 明确声明 | Prompt 三要素：用 XML 标签分隔、提供清晰 Schema、明确声明只输出 JSON。 | Prompt 三要素 |
| 1:25 | 参数设置：温度=0 + max_tokens 留够 | 参数上温度设为 0 降低随机性，max_tokens 一定要留够，防止 JSON 结构被截断。 | 参数设置 |
| 1:50 | 后处理链路：正则 → json5 → Pydantic | 后处理用正则提取 JSON 块、json5 容错解析、Pydantic 校验字段，复杂结构再配 Few-shot 示例。 | 后处理兜底 |

