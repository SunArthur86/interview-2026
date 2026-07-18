---
id: sjdk-010
difficulty: L3
category: java-core
feynman:
  essence: 将并发子任务的生命周期绑定在父作用域内
  analogy: 就像有组织的团队，解散时自动叫停所有成员，不留“孤儿任务”
  first_principle: 解决并发任务散乱管理导致的资源泄露和错误传播困难
  key_points:
  - 子任务生命周期绑定在Scope内
  - 支持短路失败或成功策略
  - 统一错误处理和资源清理
  - 通常搭配虚拟线程使用
memory_points:
- 一句话定义：将并发任务视为一个单元，生命周期与代码块绑定，消灭孤儿线程
- 核心API：StructuredTaskScope，配合ShutdownOnFailure(一败俱败)或OnSuccess(竞速)使用
- 机制对比：因为Scope退出前保证子任务全部结束，所以能自动取消未完成任务并聚合异常
- 底层绑定：因为需管理父子线程树，所以通常配合虚拟线程使用并依赖中断机制取消任务
---

# JDK 21中的Structured Concurrency（结构化并发）是什么？

🎯 本质：Structured Concurrency（JDK 21预览特性）将多个并发任务视为一个逻辑工作单元，简化错误处理和取消操作，确保并发任务的生命周期与代码块作用域一致。

📊 问题背景：传统并发中，子任务往往是“孤儿线程”，父线程难以管理其生命周期。
```text
传统并发问题
Parent Thread
    ├─> fork Task A (失败)
    └─> fork Task B (仍在运行，浪费资源)

结构化并发
Parent Thread
    └─> Scope [进入]
        ├─> fork Task A (失败) ────┐
        └─> fork Task B             │ 自动取消
             │          ◄───────────┘
             └─> [Scope 退出/关闭] (所有子任务保证结束)
```

🔧 StructuredTaskScope 解决方案与实现：
```java
// 1. ShutdownOnFailure: 只要有一个失败，取消其他所有
try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
    StructuredTaskScope.Subtask<String> userTask  = scope.fork(() -> fetchUser(id));
    StructuredTaskScope.Subtask<String> orderTask = scope.fork(() -> fetchOrder(id));

    scope.join()            // 等待所有子任务完成（成功、失败或被取消）
          .throwIfFailed(); // 如果有失败，抛出异常（聚合异常）

    // 到这里说明两个都成功了
    return new Response(userTask.get(), orderTask.get());
} // scope 自动关闭，未完成或已启动的任务被取消

// 2. ShutdownOnSuccess: 只要有一个成功，取消其他所有（用于竞速场景）
try (var scope = new StructuredTaskScope.ShutdownOnSuccess<String>()) {
    scope.fork(() -> fetchFromFastSource());
    scope.fork(() -> fetchFromSlowSource());
    scope.join();
    // 返回第一个成功的结果
    return scope.result();
}
```

核心特性与原理：
1. **生命周期绑定**：
   - `StructuredTaskScope` 实现了 `AutoCloseable`。当退出 `try` 块时，`scope.join()` 必须已被调用（内部检查），且 `scope.close()` 会确保所有 fork 的子任务都已终止。
2. **错误传播与聚合**：
   - `ShutdownOnFailure` 使用 `join().throwIfFailed(e -> e)`。如果多个子任务失败，可以配置异常策略（如抛出第一个异常或聚合为 `ExecutionException`）。
3. **线程所有权**：
   - Structured Concurrency 通常与 **虚拟线程** 配合使用。`scope.fork()` 会启动一个新的虚拟线程。
   - 结构化并发隐含了“线程树”的概念：父线程拥有子线程，子线程不能超出父线程的生命周期。
4. **取消机制**：
   - 当 `shutdown()` 被调用（例如某个任务失败），scope 会向所有尚未完成的子线程发送中断信号（`Thread.interrupt()`）。子任务应正确处理中断以停止工作。
5. **结果获取**：
   - `Subtask.state()` 返回枚举 `UNSUCCESSFUL`, `SUCCESS`, `FAILED`。只有状态正确时才能调用 `get()` 获取结果，否则抛出异常。

应用场景：
- **聚合数据**：如网关模式，并行调用多个下游服务（用户、订单、库存），任一失败则整体失败。
- **冗余调用**：同时调用两个不同供应商的接口，谁快用谁，取消慢的。

### 常见考点
1. **与 ExecutorService 的区别**：为什么不能直接用 ExecutorService + CompletableFuture？

#### 💡 实战案例
在实际的高并发网关服务中，我们曾遇到下游某个微服务响应超时（30s），导致主线程池被大量等待的 `Future.get()` 耗尽，进而拖垮整个服务。使用结构化并发后，一旦某个子任务超时或失败，Scope 立即中断其他子任务（如取消空闲数据库连接），使得线程资源能瞬间释放，QPS 恢复正常。

#### 🔑 关键代码示例
```java
// 自定义超时策略：利用 joinUntil 替代 join，避免无限期阻塞
try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
    scope.fork(() -> callServiceA());
    scope.fork(() -> callServiceB());
    
    // 设置 2秒超时，超时后会抛出 TimeoutException 并触发 scope 关闭
    scope.joinUntil(Instant.now().plusSeconds(2))
          .throwIfFailed();
    
    // 组合结果
} catch (TimeoutException e) {
    // 处理整体超时逻辑
}
```

#### 📊 Structured Concurrency vs 传统并发模型
| 维度 | 传统并发 | Structured Concurrency (JDK 21) |
| :--- | :--- | :--- |
| **生命周期管理** | 手动管理，父子线程无强关联，容易泄露 | 自动绑定，父线程结束强制子线程结束，无泄露风险 |
| **错误处理** | 需手动捕获多个 Future 的异常，易遗漏 | 聚合异常，一次 `throwIfFailed` 处理所有错误 |
| **取消传播** | 需手动编写逻辑遍历并取消所有任务 | 自动传播，`shutdown()` 会中断所有子任务 |
| **代码可读性** | 回调地狱或复杂的链式调用 | 结构化代码块，同步风格编写异步逻辑 |
| **调试难度** | 线程栈支离破碎，难以追踪 | 保留线程调用树，Stack Trace 清晰直观 |

## 核心知识点图

<img src="/interview-2026/images/diagram_java-core_sjdk-010.svg" alt="核心知识点图" style="max-width:100%;height:auto;border:1px solid var(--border);border-radius:8px;margin:1em 0;" />

## 记忆要点

- 一句话定义：将并发任务视为一个单元，生命周期与代码块绑定，消灭孤儿线程
- 核心API：StructuredTaskScope，配合ShutdownOnFailure(一败俱败)或OnSuccess(竞速)使用
- 机制对比：因为Scope退出前保证子任务全部结束，所以能自动取消未完成任务并聚合异常
- 底层绑定：因为需管理父子线程树，所以通常配合虚拟线程使用并依赖中断机制取消任务

## 结构化回答

**30 秒电梯演讲：** 将并发子任务的生命周期绑定在父作用域内。打个比方，就像有组织的团队，解散时自动叫停所有成员，不留“孤儿任务”。

**展开框架：**
1. **一句话定义** — 将并发任务视为一个单元，生命周期与代码块绑定，消灭孤儿线程
2. **核心API** — StructuredTaskScope，配合ShutdownOnFailure(一败俱败)或OnSuccess(竞速)使用
3. **机制对比** — 因为Scope退出前保证子任务全部结束，所以能自动取消未完成任务并聚合异常

**收尾：** 我在项目里踩过坑——在实际的高并发网关服务中，我们曾遇到下游某个微服务响应超时（30s），导致主线程池被大量等待的 `Future.get()` 耗尽，进而拖垮整个服务。您想深入聊哪一段：原理、避坑还是对比选型？

## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：JDK 21中的Structured… | "JDK 21中的Structured Concurrency（结构化并发）是什么？一句话——就像有组织的团队，解散时自动叫停所有成员，不留“孤儿任务”。" | 开场钩子 |
| 0:45 | 概念动画/示意图 | "将并发子任务的生命周期绑定在父作用域内——就像有组织的团队，解散时自动叫停所有成员，不留“孤儿任务”" | 核心定义 |
| 1:30 | 一句话定义示意 | "将并发任务视为一个单元，生命周期与代码块绑定，消灭孤儿线程" | 要点1 |
| 2:15 | 核心示意 | "StructuredTaskScope，配合ShutdownOnFailure(一败俱败)或OnSuccess(竞速)使用" | 要点2 |
| 3:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |
