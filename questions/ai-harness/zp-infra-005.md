---
id: zp-infra-005
difficulty: L4
category: ai-harness
subcategory: 推理优化
tags:
- 智谱
- 面经
- Speculative Decoding
- 投机解码
- PEARL
- EAGLE
feynman:
  essence: 用低成本草稿预测并用高质量模型验证，变串行为并行
  analogy: 大师让徒弟先画草图（Draft），大师只需检查并修改错误，比大师从头画快
  first_principle: 如何在不牺牲生成质量的前提下，利用并行计算减少推理延迟？
  key_points:
  - Draft模型生成候选，Target模型并行验证
  - Medusa利用多头输出，EAGLE利用特征层预测
  - Pearl通过节点解耦实现流水线并行
  - 数学保证输出分布与原模型一致
follow_up:
- 投机解码接受率多少才有意义？—— 通常 >50% 才有正向加速（draft 开销不能忽略）
- DFlash 是什么？—— 参考工作，结合 PEARL 思路的改进
- 高 batch 下投机解码还有用吗？—— 传统方式没用（batch 已打满计算），但并行投机（PEARL）仍有优势
memory_points:
- 基础投机：小模型Draft生成候选，大模型Target并行验证，猜对免费，保证分布一致。
- Medusa：Target多头并行预测，无需额外模型。EAGLE：特征级投机，接受率高。
- 并行vs树状：树状单次验证延迟低，并行节点分离吞吐高。低延迟选树状，高吞吐选并行。
---

# 【智谱Infra面经】Speculative Decoding / Medusa / EAGLE / PEARL 在推理加速中的实现细节？并行投机 vs 树状投机？

**投机解码核心思想：用小模型快速生成候选 token，大模型批量验证，加速推理。**

**基础 Speculative Decoding：**
```
1. Draft 模型生成 γ 个候选 token: [t1, t2, ..., tγ]
2. Target 模型一次前向计算所有 γ+1 个位置
3. 逐个验证：如果 draft 猜对 → 免费获得 token
4. 猜错的 token 之后重新用 target 生成
5. 数学保证：最终输出分布与纯 target 完全一致
```

**Medusa（多头并行投机）：**
- 不需要单独的 draft 模型
- 在 target 模型上增加多个 prediction head
- 每个 head 预测下一个 token（head1=+1, head2=+2, ...）
- 一次前向预测多个候选
- **优势**：无需额外模型、无 draft-model 对齐问题

**EAGLE（特征级投机）：**
- Draft 模型复用 target 的隐藏层特征（不是 token embedding）
- 更精确的预测 → 更高的接受率
- 支持树状推测
- **接受率 60-80%+**

**PEARL（并行投机解码）：**
- DT 分离
- Draft 和 Target 在不同节点/设备并行运行
- 节点级并行 → 无串行等待
- 高 batch 下优势大

**并行投机 vs 树状投机：**
| 维度 | 树状投机 | 并行投机 |
|------|---------|---------|
| 结构 | 构建候选 token 树 | Draft/Target 节点分离 |
| 验证 | 树形 attention 一次验证 | 流水线式持续生成验证 |
| 延迟 | 单次前向延迟高 | 持续低延迟 |
| 吞吐 | 低 batch 好 | 高 batch 好 |
| 实现 | Medusa/EAGLE | PEARL |

---

**实战案例**：
在 Code LLM 推理中接入 EAGLE，由于代码结构规律性强，Draft 模型接受率极高（常 >75%），首字生成时间（TTFT）略微增加，但整体端到端吞吐提升了 2.2 倍。但在重 QA 任务中因接受率跌至 40% 以下，反而增加了 15% 的延迟，需根据场景动态切换。

**代码示例（Python - Speculative Sampling 验证逻辑）**：
```python
import torch

def verify_sampling(draft_tokens, target_logits, base_model_probs):
    # target_logits: [seq_len, vocab_size]
    n = draft_tokens.shape[0]
    for i in range(n):
        draft_token = draft_tokens[i]
        # 简单接受逻辑：概率对比或随机采样
        q = base_model_probs[i, draft_token]
        p = target_logits[i, draft_token].softmax(dim=-1)
        if p < q: # 简化的拒绝条件
            return i # 返回接受位置
    return n
```

## 常见考点
1. **Speculative Decoding 如何保证数学上的等价性？**（涉及 rejection sampling 的概率证明）
2. **树状投机验证时 Attention Mask 是如何构造的？**（需构建稀疏 Mask 以并行计算所有候选路径）
3. **Acceptance Rate 是什么？低于多少时投机解码会变成负优化？**（通常需 >50% 才能抵消并行计算开销）

## 记忆要点

- 基础投机：小模型Draft生成候选，大模型Target并行验证，猜对免费，保证分布一致。
- Medusa：Target多头并行预测，无需额外模型。EAGLE：特征级投机，接受率高。
- 并行vs树状：树状单次验证延迟低，并行节点分离吞吐高。低延迟选树状，高吞吐选并行。


## 结构化回答

**30 秒电梯演讲：** 用低成本草稿预测并用高质量模型验证，变串行为并行——打个比方，大师让徒弟先画草图（Draft），大师只需检查并修改错误，比大师从头画快

**展开框架：**
1. **基础投机** — 小模型Draft生成候选，大模型Target并行验证，猜对免费，保证分布一致。
2. **Medusa** — Target多头并行预测，无需额外模型。EAGLE：特征级投机，接受率高。
3. **并行vs树状** — 树状单次验证延迟低，并行节点分离吞吐高。低延迟选树状，高吞吐选并行。

**收尾：** 以上三点都能配合实战聊。我可以展开任一要点，比如「投机解码接受率多少才有意义？—— 通常 >50% 才有正向加速（draft 开销不能忽略）」这类追问您感兴趣吗？

## 视频脚本

> 预计时长：4 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡 | "【智谱Infra面经】Speculative Decoding / Medusa，30 秒讲清楚。" | 开场钩子 |
| 0:40 | 概念定义动画 | "一句话：用低成本草稿预测并用高质量模型验证，变串行为并行" | 核心定义 |
| 1:20 | 基础投机图解 | "小模型Draft生成候选，大模型Target并行验证，猜对免费，保证分布一致。" | 基础投机 |
| 2:00 | Medusa图解 | "Target多头并行预测，无需额外模型。EAGLE：特征级投机，接受率高。" | Medusa |
| 2:40 | 并行vs树状图解 | "树状单次验证延迟低，并行节点分离吞吐高。低延迟选树状，高吞吐选并行。" | 并行vs树状 |
| 3:20 | 总结卡 | "记好这几条，面试不慌。下期见。" | 收尾 |
