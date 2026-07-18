---
id: misc-045
difficulty: L2
category: ai-basics
subcategory: 大模型原理
images:
- svg_normalization.svg
feynman:
  essence: RMSNorm简化了LayerNorm去掉了均值减法，Pre-Norm解决了深层训练梯度消失。
  analogy: RMSNorm是省略了「平均分」计算的标准化；Pre-Norm是先清理再干活，避免越干越乱。
  first_principle: 如何在保证模型稳定训练的前提下，最大化计算效率并支持更深网络？
  key_points:
  - RMSNorm移去中心化减法，仅保留方差缩放，计算效率高。
  - Pre-Norm将LayerNorm置于残差连接之前，保证梯度顺畅传播。
  - 现代大模型标配：Pre-Norm结构配合RMSNorm归一化。
follow_up:
- DeepNorm如何解决Post-Norm的稳定性问题?
- 为什么Post-Norm在浅层模型中效果更好?
memory_points:
- RMSNorm优势：去中心化计算，速度快且大模型训练更稳。
- Pre-Norm：先Norm再残差，梯度传得稳，支持深模型。
- Post-Norm：先残差后Norm，深层易梯度消失，训练难。
- 实战：LLaMA用RMSNorm+Pre-Norm解决Loss震荡问题。
---

# 为什么LLaMA用RMSNorm而不是LayerNorm?Pre-Norm和Post-Norm有什么区别

- **RMSNorm vs LayerNorm:**

- **LayerNorm:** y = gamma * (x - mean) / √(var + eps) + beta
- **RMSNorm:** y = gamma * x / √(mean(x²) + eps)

- **RMSNorm优势:**
1. **计算更快** - 不需要计算均值,减少约7-64%计算
2. **效果相当** - 实验表明去掉减均值操作不影响效果
3. **更稳定** - 大模型训练中更稳定

- **Pre-Norm vs Post-Norm:**
- **Post-Norm**(原始Transformer):x = LayerNorm(x + SubLayer(x))
- 深层训练不稳定
- **Pre-Norm**(GPT-2/LLaMA):x = x + SubLayer(LayerNorm(x))
- **训练更稳定**,支持更深模型
- 效果略差但可通过增加深度补偿

- **实战案例**：在迁移 LLaMA 架构进行 70B 参数量级模型预训练时，初期尝试使用 LayerNorm + Post-Norm，导致 Loss 在 2K steps 后开始剧烈震荡甚至变为 NaN。切换为 RMSNorm + Pre-Norm 并调整 Warmup 后，训练平滑收敛。

- **代码示例 (PyTorch - RMSNorm 实现)**：
```python
import torch
import torch.nn as nn

class RMSNorm(nn.Module):
    def __init__(self, dim: int, eps: float = 1e-6):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim)) # gamma

    def _norm(self, x):
        # 1. 计算均方根, 2. 不需要减去均值, 3. 保持维度以便广播
        return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)

    def forward(self, x):
        output = self._norm(x.float()).type_as(x)
        return output * self.weight # 乘以可学习 gamma
```

- **补充关键细节**：
  - **LayerNorm 作用机制**：通过将数据分布拉回到均值为0、方差为1的标准正态分布，缓解梯度消失/爆炸，加速收敛。包含两个可学习参数：缩放 gamma 和平移 beta。
  - **RMSNorm (Root Mean Square Layer Normalization)**：基于假设——输入数据的均值已经接近0（ReLU等激活函数的特性），因此省略了减去均值操作。它只保留了方差缩放部分，公式中的分母是所有元素平方和的均值的根（即RMS），因此不依赖 beta 参数（通常简化掉）。
  - **Post-Norm 的问题**：在深层网络中，梯度需要经过多个LayerNorm和非线性层才能传回输入层，容易导致梯度消失或爆炸，训练非常困难，通常需要Warmup等技巧配合。
  - **Pre-Norm 的工作原理**：先做Norm再进入Attention/FFN。这样建立了一个残差连接，梯度可以直接通过残差路径“无损”地流向浅层，极大缓解了深层训练的梯度问题，使得Transformer可以扩展到100层以上（如DeepMind的GPT-3变体）。
  - **Transformer-Normalization (DeepNorm)**：介于两者之间，针对Pre-Norm在极深网络下可能出现的数值不稳定问题，通过调整初始化和残差连接的系数（如 `alpha` 放大深层输入）来增强稳定性。

```text
┌────────────────────────────────────────────────────────────────┐
│                Pre-Norm vs Post-Norm 结构对比                  │
└────────────────────────────────────────────────────────────────┘

  Post-Norm (原始 Transformer / BERT)             Pre-Norm (GPT-2 / LLaMA)
  ┌───────────────────────────────┐          ┌───────────────────────────────┐
  │                               │          │                               │
  │  x ──► [SubLayer] ──► (+) ──► │  Layer   │          ┌─────────────────┐   │
  │               ▲       │      │  Norm    │          │                 │   │
  │               │       │      │          │  x ──► │    LayerNorm    │──►│ 
  │               └───────┘      │          │          └────────┬────────┘   │
  │             (残差连接)        │          │                   ▼            │
  │                               │          │                [SubLayer]     │
  │   Output ◄────────────────────┘          │                   │            │
  │                               │          │  x ──► (+) ◄─────┘            │
  └───────────────────────────────┘          │          ▲                    │
                                            │          └────────────────────┘  │
                                            │             (残差连接)           │
                                            └───────────────────────────────┘
```


## 记忆要点

- RMSNorm优势：去中心化计算，速度快且大模型训练更稳。
- Pre-Norm：先Norm再残差，梯度传得稳，支持深模型。
- Post-Norm：先残差后Norm，深层易梯度消失，训练难。
- 实战：LLaMA用RMSNorm+Pre-Norm解决Loss震荡问题。

## 结构化回答

**30 秒电梯演讲：** RMSNorm 是省掉了"平均分"计算的标准化，只保留方差缩放，计算更快；Pre-Norm 是先清理再干活，把 LayerNorm 放在残差连接之前，保证梯度顺畅传播。两者的组合——Pre-Norm 加 RMSNorm——是现代大模型的标配，LLaMA 就用它解决了深层训练的 Loss 震荡。

**展开框架：**
1. **RMSNorm** — 相比 LayerNorm 去掉了均值中心化（减均值）步骤，只用均方根做缩放，计算量更小、速度更快，在大模型训练里也更稳定。
2. **Pre-Norm vs Post-Norm** — Pre-Norm 把归一化放在残差加法之前（先 Norm 再残差），主干梯度有直连通路，梯度传得稳，支持更深网络；Post-Norm 先残差后 Norm，深层易梯度消失、训练难。
3. **实战组合** — LLaMA 等现代大模型标配 Pre-Norm + RMSNorm 组合，既快又稳，解决了深层 Transformer 的 Loss 震荡和梯度消失问题。

**收尾：** 一句话，RMSNorm + Pre-Norm 是深层大模型的稳定基石。您想深入聊聊 DeepNorm 怎么解决 Post-Norm 的稳定性，还是为什么 Post-Norm 在浅层模型反而更好？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题《RMSNorm 与 Pre-Norm》+ 标准化漫画 | RMSNorm 是省略了"平均分"计算的标准化，Pre-Norm 是先清理再干活、避免越干越乱。 | 类比开场 |
| 0:25 | RMSNorm vs LayerNorm 公式对比 | RMSNorm 相比 LayerNorm 去掉了均值中心化，只用均方根做缩放，计算量更小、速度更快。 | RMSNorm |
| 0:55 | Pre-Norm vs Post-Norm 结构对比图 | Pre-Norm 把归一化放在残差之前，主干梯度有直连通路，传得稳、支持深模型；Post-Norm 深层易梯度消失。 | Pre/Post-Norm |
| 1:25 | 梯度传播示意：Pre-Norm 直连 vs Post-Norm 阻塞 | 关键区别在梯度：Pre-Norm 有直连通路，梯度顺畅；Post-Norm 深层容易梯度消失，训练难。 | 梯度传播 |
| 1:50 | LLaMA 标签 + 组合优势 | 实战上，LLaMA 用 RMSNorm 加 Pre-Norm 的组合，既快又稳，解决了深层训练的 Loss 震荡。 | 实战组合 |

