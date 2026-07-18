---
id: misc-039
difficulty: L2
category: ai-basics
subcategory: 多模态
tags:
- IO
- IOC
feynman:
  essence: 通过简单的投影层将视觉特征对齐到语言模型的词向量空间。
  analogy: 像给只有文字界面的电脑接个“显卡转接头”，让它能看懂图片。
  first_principle: 如何赋予纯语言大模型“看懂”图像并生成语言描述的能力？
  key_points:
  - CLIP提取图像特征
  - 投影层映射特征到词嵌入空间
  - 两阶段训练：特征对齐+指令微调
follow_up:
- Projection Layer用线性层还是MLP好?
- BLIP-2的Q-Former和LLaVA的Projection有什么区别?
memory_points:
- 架构三件套：CLIP ViT视觉编码器、投影层（MLP）、LLM（Vicuna/LLaMA）
- 接入方式：图像经ViT编码，通过投影层映射到LLM Token维度，作为前缀输入
- 训练两阶段：1.特征对齐（冻ViT/LLM，训投影层） 2.指令微调（训投影+LLM）
- 为何有效：CLIP提供高质量语义特征，LLM提供强推理，简单MLP足矣
- 实战优势：多模态理解（如表格结构）比传统CV方案更鲁棒，代码量少
---

# LLaVA的架构是什么?它是如何将视觉信息接入LLM的

- **LLaVA架构:**

```text
┌─────────────────────────────────────────────────────────────┐
│                      LLaVA 架构图                            │
└─────────────────────────────────────────────────────────────┘

[输入图像]         [输入文本提示]
    │                   │
    ▼                   │
┌───────────┐          │
│   CLIP    │          │
│ ViT-L/14  │          │
└─────┬─────┘          │
      │ [576个Patch Tokens] │
      ▼                   │
┌───────────┐          │
│ Projection│          │
│  Layer    │          │
│ (2-层MLP) │          │
└─────┬─────┘          │
      │ [Visual Tokens]│
      │    (映射到LLM维度)│
      └─────┬──────────┘
            ▼
    ┌───────────────┐
    │     LLM       │
    │ (Vicuna/LLaMA)│ <─── 视觉token充当前缀或嵌入文本中
    └───────┬───────┘
            │
            ▼
       [文本输出]
```

- **核心组件:**
1. **视觉编码器** - CLIP ViT-L/14, 取倒数第二层特征，输出576个patch token (分辨率 336x336, patch size 14)。 
2. **投影层** - 简单的线性层或2层MLP,将视觉特征(768维)映射到LLM的Token Embedding空间(如4096维)。这是连接模态的关键"适配器"。
3. **LLM** - LLaMA/Vicuna,处理文本+视觉token,进行自回归生成。

- **训练阶段:**
1. **Stage 1 (特征对齐)** - 
   - 冻结ViT和LLM，只训练Projection Layer。
   - 数据：CC3M数据集中的595K图文对。
   - 目标：让视觉特征能被LLM理解（类似LLM的预训练任务）。
2. **Stage 2 (指令微调)** - 
   - 冻结视觉编码器，训练Projection Layer + LLM。
   - 数据：基于COCO/GQA等数据集，利用GPT-4生成的复杂多模态指令数据（150K）。
   - 目标：让模型学会遵循指令进行多模态对话。

- **为什么有效:**
- CLIP已经对齐了图文语义空间，提供了高质量的视觉特征。
- LLM本身具有很强的推理和泛化能力，只需一个简单的投影层就能"看懂"视觉特征。
- 高质量的指令微调数据（GPT-4生成）极大地激发了模型的跟随指令能力。

- **后续发展:** LLaVA-1.5 (增加MLP深度、学术任务数据), LLaVA-NeXT (高分辨率、更多训练数据), LLaVA-Video (视频理解)。

- **实战案例:**
曾将LLaVA用于工业报表识别，原方案需要训练YOLO+OCR+分类器多个模型。改用LLaVA-1.5后，直接输入截图并Prompt:"识别表格中的Item列和Price列，输出JSON"。我们发现虽然它偶尔会OCR错字符，但对表格结构的理解（行列对齐、合并单元格）比传统的OpenCV版图解析方案鲁棒得多，代码量从2000行缩减到50行。

- **代码示例:**
```python
from transformers import LlavaForConditionalGeneration, AutoProcessor

model_id = "llava-hf/llava-1.5-7b-hf"
model = LlavaForConditionalGeneration.from_pretrained(
    model_id, device_map="auto", load_in_4bit=True # 实战中常需量化显存优化
)
processor = AutoProcessor.from_pretrained(model_id)

# 构造Prompt
prompt = "USER: <image>\nDescribe this image in detail. ASSISTANT:"
image = Image.open("example.jpg")
inputs = processor(text=prompt, images=image, return_tensors="pt").to("cuda")

# 生成
output = model.generate(**inputs, max_new_tokens=200)
print(processor.decode(output[0], skip_special_tokens=True))
```

## 常见考点
1. **LLaVA中的投影层可以换成什么？** 
   除了简单的MLP，可以使用Q-Former (BLIP-2)、Cross-Attention (Flamingo) 等更复杂的结构，但LLaVA证明了简单MLP配合强数据足矣。
2. **为何LLaVA要使用GPT-4生成数据？** 
   人工标注多模态对话成本极高且质量难以保证。利用GPT-4将纯文本/图像数据转化为复杂的指令跟随数据，是一种高效的数据蒸馏策略。
3. **视觉特征如何注入LLM？** 
   通常将视觉Token序列拼接到文本Token序列之前（或替换掉文本中的占位符<image>），让LLM将其作为上下文进行处理。


## 核心流程图

```mermaid
flowchart TD
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
    classDef store fill:#8b5cf6,stroke:#6d28d9,color:#fff;
```

## 记忆要点

- 架构三件套：CLIP ViT视觉编码器、投影层（MLP）、LLM（Vicuna/LLaMA）
- 接入方式：图像经ViT编码，通过投影层映射到LLM Token维度，作为前缀输入
- 训练两阶段：1.特征对齐（冻ViT/LLM，训投影层） 2.指令微调（训投影+LLM）
- 为何有效：CLIP提供高质量语义特征，LLM提供强推理，简单MLP足矣
- 实战优势：多模态理解（如表格结构）比传统CV方案更鲁棒，代码量少

## 结构化回答

**30 秒电梯演讲：** LLaVA 给只有文字界面的 LLM 接个"显卡转接头"看图。架构三件套：CLIP ViT 提取图像特征、投影层（MLP）把特征映射到 LLM 的 token 维度、LLM 负责推理生成。训练分两阶段：先冻结 ViT 和 LLM 只训投影层做特征对齐，再指令微调训投影加 LLM。简单 MLP 就够用，因为 CLIP 给的特征质量高。

**展开框架：**
1. **架构三件套** — CLIP ViT 做视觉编码器提取图像特征；投影层（MLP）将视觉特征映射到 LLM 的词嵌入维度；LLM（如 Vicuna/LLaMA）接收视觉 token 作为前缀输入，负责理解和生成。
2. **两阶段训练** — 阶段一特征对齐：冻结 ViT 和 LLM，只训练投影层，用图文对学习映射；阶段二指令微调：训练投影层加 LLM，让模型学会按指令描述图像。
3. **为何有效** — CLIP 提供高质量语义特征，LLM 提供强推理能力，中间一个简单 MLP 就能桥接，工程量小；对表格结构等场景比传统 CV 方案更鲁棒。

**收尾：** 一句话，LLaVA 用最简单的投影层打通视觉和语言。您想深入聊聊投影层用线性层还是 MLP 好，还是 BLIP-2 的 Q-Former 和它有什么区别？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题《LLaVA 视觉接入》+ 文字电脑接显卡转接头漫画 | LLaVA 像给只有文字界面的电脑接个显卡转接头，让它能看懂图片，赋予纯语言大模型视觉能力。 | 类比开场 |
| 0:25 | 架构三件套图：ViT + 投影层 + LLM | 架构三件套：CLIP ViT 提取图像特征，投影层用 MLP 把特征映射到 LLM 的 token 维度，LLM 负责推理生成。 | 架构组成 |
| 0:55 | 两阶段训练流程图 | 训练分两阶段：先冻结 ViT 和 LLM 只训投影层做特征对齐，再指令微调训投影加 LLM。 | 两阶段训练 |
| 1:25 | 为何有效：CLIP 高质量特征 + LLM 强推理 | 之所以简单 MLP 就够用，是因为 CLIP 给的特征质量高，LLM 推理能力强，中间桥接很轻量。 | 为何有效 |
| 1:50 | 实战优势：表格结构理解鲁棒 | 实战上，LLaVA 对表格结构这类多模态理解，比传统 CV 方案更鲁棒，而且代码量少。 | 实战优势 |

