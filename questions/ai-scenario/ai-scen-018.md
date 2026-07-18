---
id: ai-scen-018
difficulty: L3
category: ai-scenario
subcategory: AI对话系统设计
tags:
- 语音Agent
- ASR
- TTS
- VAD
- 实时对话
- 打断处理
- 端云协同
feynman:
  essence: 构建全链路流式语音处理管道，通过ASR/LLM/TTS并行和状态机管理实现毫秒级响应。
  analogy: 像同声传译，耳朵听进去的同时脑子在转，嘴巴马上说出来，还能随时被打断。
  first_principle: 如何在处理听、想、说三个串行步骤时，将端到端延迟压缩到人类可接受的范围？
  key_points:
  - 采用流式ASR和流式TTS，配合LLM流式生成。
  - 使用VAD检测语音活动，设计状态机管理交互。
  - 打断时立即停止TTS和LLM，保留上下文。
  - 端云协同优化延迟，简单指令端侧执行。
follow_up:
- 如何处理嘈杂环境下的语音识别？
- 端侧部署ASR/TTS有哪些技术选型？
- 语音Agent如何管理多轮对话的上下文？
memory_points:
- 核心链路：VAD检测(50ms) → 流式ASR(200ms) → LLM首字(300ms) → TTS首包(200ms)。
- 状态机：IDLE → LISTENING → THINKING → SPEAKING，支持Barge-in打断。
- 技术选型：ASR用Whisper/Paraformer，TTS选CosyVoice流式合成。
- 延迟控制：边说边转，边合成边播，全链路控制在1秒内。
- 实战难点：噪音环境用双阈值VAD，动态调整灵敏度防误触。
---

# 如何设计一个实时语音AI助手？支持语音输入、实时对话、语音输出，延迟控制在1秒以内。

【场景分析】
实时语音Agent是最具挑战的AI系统之一：多模态链路（ASR->LLM->TTS）、低延迟要求、打断处理、状态管理。

【系统架构】
1. **音频输入处理**：
   - 音频采集：WebSocket传输音频流（16kHz PCM/Opus）
   - VAD（语音活动检测）：Silero VAD检测说话开始/结束
   - 流式ASR：Whisper-streaming / Paraformer流式版
   - 延迟优化：分块识别，边说边转
2. **对话推理**：
   - LLM流式生成：首Token延迟 < 300ms
   - 上下文管理：多轮对话历史 + 系统人设
   - 工具调用：查天气、设闹钟等
3. **语音合成（TTS）**：
   - 流式TTS：逐句合成，不等完整回复
   - 模型：CosyVoice / GPT-SoVITS / Edge-TTS
   - 声纹克隆：可选个性化音色
4. **音频输出**：
   - 流式播放：边合成边播放
   - 打断处理：检测到用户说话 → 立即停止播放

【延迟拆解】
VAD判断 50ms + ASR转写 200ms + LLM首字 300ms + TTS首包 200ms + 网络传输 100ms = 总计约850ms

【状态机设计】
States: IDLE -> LISTENING -> THINKING -> SPEAKING -> IDLE
用户打断: SPEAKING -> INTERRUPTED -> LISTENING
- LISTENING：VAD检测到语音 → 流式ASR
- THINKING：ASR完成 → LLM流式生成
- SPEAKING：TTS流式合成 + 播放
- INTERRUPTED：用户打断 → 停止播放 → 回到LISTENING

【实战案例】
在车载场景下，背景噪音常导致VAD误判为“静默”。我们引入了**双阈值VAD + 能量检测**，并结合环境噪音采样动态调整灵敏度，将高速行驶下的误触率降低了40%。

【关键代码】（VAD与状态流转控制）
```python
import torch

# 加载Silero VAD模型
model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad')
(get_speech_timestamps, _, _, _, _) = utils

def process_audio_chunk(chunk: np.ndarray, current_state: str):
    # VAD检测
    speech_probs = model(chunk, 16000).item()
    
    if current_state == 'SPEAKING':
        if speech_probs > 0.5: 
            return 'INTERRUPTED' # 检测到用户说话，触发打断
    elif current_state == 'LISTENING':
        if speech_probs > 0.8: 
            return 'PROCESSING' # 确认说话结束，开始ASR
        
    return current_state
```

【TTS技术选型对比】
| 指标 | Edge-TTS | VITS/GPT-SoVITS | CosyVoice (阿里) |
| :--- | :--- | :--- | :--- |
| **延迟** | 极低（<100ms） | 中（200-500ms） | 低（150-300ms） |
| **音色自然度** | 机械感明显 | 极高（情感丰富） | 高（拟人度高） |
| **推理资源** | CPU即可 | 需GPU加速 | 需GPU |
| **流式支持** | 差 | 一般 | **优秀（专为流式优化）** |
| **推荐场景** | 简单播报 | 沉浸式有声书 | **实时数字人助手** |

```text
       ┌─────────┐
       │  IDLE   │ (等待输入)
       └────┬────┘
            │ VAD Start
            ▼
       ┌─────────┐
       │LISTENING│ (ASR中...)
       └────┬────┘
            │ VAD End (说话结束)
            ▼
       ┌─────────┐
       │THINKING │ (LLM推理中...)
       └────┬────┘
            │ TTS Start
            ▼
       ┌─────────┐    VAD Start (Barge-in)
       │SPEAKING │ ──────────────────┐
       └────┬────┘                   │
            │ Finish / Interrupt     │
            ▼                         ▼
       ┌─────────┐              ┌──────────┐
       │  IDLE   │              │INTERRUPTED│ (停止


## 记忆要点

- 核心链路：VAD检测(50ms) → 流式ASR(200ms) → LLM首字(300ms) → TTS首包(200ms)。
- 状态机：IDLE → LISTENING → THINKING → SPEAKING，支持Barge-in打断。
- 技术选型：ASR用Whisper/Paraformer，TTS选CosyVoice流式合成。
- 延迟控制：边说边转，边合成边播，全链路控制在1秒内。
- 实战难点：噪音环境用双阈值VAD，动态调整灵敏度防误触。


## 结构化回答

**30 秒电梯演讲：** 构建全链路流式语音处理管道，通过ASR/LLM/TTS并行和状态机管理实现毫秒级响应。——打个比方，像同声传译，耳朵听进去的同时脑子在转，嘴巴马上说出来，还能随时被打断。

**展开框架：**
1. **核心链路** — VAD检测(50ms) → 流式ASR(200ms) → LLM首字(300ms) → TTS首包(200ms)。
2. **状态机** — IDLE → LISTENING → THINKING → SPEAKING，支持Barge-in打断。
3. **技术选型** — ASR用Whisper/Paraformer，TTS选CosyVoice流式合成。

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「如何处理嘈杂环境下的语音识别」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "设计一个实时语音AI助手，30 秒讲清楚。" | 开场钩子 |
| 0:36 | 概念定义动画 | "一句话：构建全链路流式语音处理管道，通过ASR/LLM/TTS并行和状态机管理实现毫秒级响应。" | 核心定义 |
| 1:12 | 核心链路图解 | "VAD检测(50ms) → 流式ASR(200ms) → LLM首字(300ms) → TTS首包(200ms)。" | 核心链路 |
| 1:48 | 状态机图解 | "IDLE → LISTENING → THINKING → SPEAKING，支持Barge-in打断。" | 状态机 |
| 2:24 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
