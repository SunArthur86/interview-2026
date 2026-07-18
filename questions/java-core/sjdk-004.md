---
id: sjdk-004
difficulty: L2
category: java-core
feynman:
  essence: 限制继承范围，介于final和普通类之间。
  analogy: 像私人俱乐部，只有名单上的人才能进去。
  first_principle: 如何在保证扩展性的同时，严格限制继承以维护模型完整性？
  key_points:
  - 通过permits明确指定允许继承的子类
  - 子类必须位于同一模块或包中
  - 子类必须是final、sealed或non-sealed
  - 配合switch实现编译期穷举检查
memory_points:
- 本质：在全开放与final全封闭间提供第三选项，精确控制继承树范围
- 语法：父类用permits指定子类，子类必须声明为final/sealed/non-sealed
- 杀手锏：与Switch模式匹配结合，编译器能穷举检查所有可能分支
- 对比：non-sealed用于打破限制，开放给第三方随意扩展，sealed则锁死
---

# Sealed Classes（密封类）是什么？它和final、abstract有什么区别？

🎯 本质：Sealed Classes 让开发者精确控制哪些类可以继承自己，在全开放和全开放之间提供了中间选项。

📊 对比：
| 修饰符 | 继承限制 | 典型应用场景 | 生命周期控制 |
|--------|---------|--------------|-------------|
| 普通class | 无限制 | 通用业务对象 | 弱 |
| final class | 不可继承 | 工具类、常量类、单例 | 强（终止） |
| sealed class | 仅 permits 列表 | 有限状态机、领域模型 | 强（受限） |
| non-sealed class | 恢复开放 | 兼容第三方扩展 | 弱（放行） |

🔧 用法：
```java
public sealed interface Shape 
    permits Circle, Square, Triangle { }

// permit 的子类必须是 final、sealed 或 non-sealed
public final class Circle(double radius) implements Shape { }
public non-sealed class Triangle implements Shape { ... }
```

💡 与 Pattern Matching 结合实现穷举检查：
```java
public double area(Shape shape) {
    return switch (shape) {
        case Circle c -> Math.PI * c.radius() * c.radius();
        case Square s -> s.side() * s.side();
        case Triangle t -> 0.5 * t.base() * t.height();
        // 编译器知道所有子类，不需要 default！
    };
}
```

**实战案例**：在电商订单状态流转中，使用 `sealed interface OrderState` 仅允许 `Paid`, `Shipped`, `Cancelled` 继承，防止外部定义非法的 `HackedState`，确保 switch 处理逻辑安全且无遗漏。

**密封类架构层级图**：
```text
      ┌──────────────────┐
      │  sealed class A  │  (控制谁能继承我)
      └────────┬─────────┘
               │ permits B, C, D
      ┌────────┴────────┐
      ▼                 ▼
┌──────────┐      ┌──────────┐
│final class B│      │sealed class C│  (C 可继续限制子类)
└──────────┘      └────┬─────┘
                      │ permits E
                 ┌────┴─────┐
                 ▼          ▼
          ┌──────────┐ ┌─────────────────┐
          │final E   │ │non-sealed class D│ (D 开放继承)
          └──────────┘ └─────────────────┘
```

## 常见考点
1. **Sealed Class 和其子类必须在同一个包吗？**
   不一定。如果定义了 `permits` 但子类在不同模块/包，父类和子类都需要 `module` 系统导出或声明。但在同一源码文件中定义时最简单。
2. **为什么需要 non-sealed？**
   为了提供灵活性。Sealed 锁定了继承树，但 `non-sealed` 允许在某个层级打破限制，让第三方库扩展特定的分支。
3. **Sealed Classes 对性能有影响吗？**
   编译时影响为主（类型检查），运行时会有极小的元数据开销，但 JVM 优化通常可以忽略不计。

## 核心知识点图

<img src="/interview-2026/images/diagram_java-core_sjdk-004.svg" alt="核心知识点图" style="max-width:100%;height:auto;border:1px solid var(--border);border-radius:8px;margin:1em 0;" />

## 记忆要点

- 本质：在全开放与final全封闭间提供第三选项，精确控制继承树范围
- 语法：父类用permits指定子类，子类必须声明为final/sealed/non-sealed
- 杀手锏：与Switch模式匹配结合，编译器能穷举检查所有可能分支
- 对比：non-sealed用于打破限制，开放给第三方随意扩展，sealed则锁死

## 结构化回答

**30 秒电梯演讲：** 限制继承范围，介于final和普通类之间。打个比方，像私人俱乐部，只有名单上的人才能进去。

**展开框架：**
1. **本质** — 在全开放与final全封闭间提供第三选项，精确控制继承树范围
2. **语法** — 父类用permits指定子类，子类必须声明为final/sealed/non-sealed
3. **杀手锏** — 与Switch模式匹配结合，编译器能穷举检查所有可能分支

**收尾：** 我在项目里踩过坑——┌──────────────────┐。您想深入聊哪一段：原理、避坑还是对比选型？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：Sealed Classes（密封类… | "Sealed Classes（密封类）是什么？它和final、abstract有什么区别？一句话——像私人俱乐部，只有名单上的人才能进去。" | 开场钩子 |
| 0:40 | 概念动画/示意图 | "限制继承范围，介于final和普通类之间——像私人俱乐部，只有名单上的人才能进去" | 核心定义 |
| 1:20 | 本质示意 | "在全开放与final全封闭间提供第三选项，精确控制继承树范围" | 要点1 |
| 2:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |
