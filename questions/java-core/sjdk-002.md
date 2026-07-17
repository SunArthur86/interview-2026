---
id: sjdk-002
difficulty: L2
category: java-core
feynman:
  essence: 将类型检查与数据绑定合二为一，消除样板代码。
  analogy: 像安检仪，过检的同时直接把身份证信息读出来，不用再查册子。
  first_principle: 如何减少类型强制转换带来的冗余代码和潜在错误？
  key_points:
  - instanceof模式匹配：类型判断与变量声明合并
  - Switch模式匹配：支持直接匹配对象类型和null
  - Record模式：直接解构数据载体
  - 支持卫语句（when）进行条件过滤
memory_points:
- 核心目的：消除冗余的类型检查与强转，新instanceof直接绑定局部变量
- Switch增强：JDK 21转正，支持复杂对象匹配且必须显式处理case null
- 卫语句：用when结合布尔表达式，提供比枚举常量更灵活的条件过滤
- 模式分类：涵盖类型模式、Record解构模式，大幅简化多分支业务逻辑
---

# JDK 21的Pattern Matching（模式匹配）有哪些重要改进？

🎯 **本质**：模式匹配让Java代码更简洁安全，减少冗余的类型检查和转换。

📊 **主要特性**：
1. **instanceof模式匹配**（JDK 16正式）
```java
// 新: if (obj instanceof String s) { ... }
```

2. **Switch模式匹配**（JDK 21正式）
```java
return switch (o) {
    case null      → "Oops, null";
    case Integer i → String.format("int %d", i);
    case String s  → String.format("String %s", s);
    default        → o.toString();
};
```

3. **Record模式**（JDK 21正式）
```java
if (obj instanceof Point(int x, int y)) { System.out.println(x + y); }
```

4. **卫语句**
```java
switch (shape) {
    case Circle c when c.radius() > 100 → "large";
    case Circle c                        → "small";
}
```

**实战案例**：在支付回调处理逻辑中，以前需要写一堆 `if-else` 配合 `instanceof` 判断不同的支付渠道对象（支付宝、微信、银联），然后强转后获取订单号。使用 Switch 模式匹配后，代码变成了一个清晰的 Switch 块，利用卫语句 `when channel.status() == SUCCESS` 直接过滤无效状态，不仅减少了NPE风险，还使得新增渠道只需增加一个 case 分支。

## 常见考点
1. **Switch 模式匹配的 `null` 处理有什么变化？**
   - 在旧版 Switch 中，传 `null` 会直接抛出 NPE。在模式匹配 Switch 中，必须显式处理 `case null`，或者由类型模式隐式处理（如果是对象引用类型）。如果没有 `null` 处理分支且传入了 `null`，会抛出 `NullPointerException`，但这发生在运行时匹配失败时，编译器允许这种情况。
2. **卫语句中的 `when` 表达式必须是常量吗？**
   - 不是。`when` 后面可以跟任意布尔表达式，能够访问 case 标签中捕获的变量（如 `when s.length() > 5`）。这提供了比枚举常量更灵活的条件过滤能力。
3. **模式匹配是否覆盖了基本类型？**
   - 部分覆盖。Switch 表达式现在支持直接匹配基本类型（如 `case int i`），但要注意如果传入的是 `Integer` 对象，依然需要进行拆箱匹配，且要注意处理 `null` 的情况（基本类型 case 不能匹配 null）。

## 记忆要点

- 核心目的：消除冗余的类型检查与强转，新instanceof直接绑定局部变量
- Switch增强：JDK 21转正，支持复杂对象匹配且必须显式处理case null
- 卫语句：用when结合布尔表达式，提供比枚举常量更灵活的条件过滤
- 模式分类：涵盖类型模式、Record解构模式，大幅简化多分支业务逻辑

## 结构化回答

**30 秒电梯演讲：** 将类型检查与数据绑定合二为一，消除样板代码。打个比方，像安检仪，过检的同时直接把身份证信息读出来，不用再查册子。

**展开框架：**
1. **核心目的** — 消除冗余的类型检查与强转，新instanceof直接绑定局部变量
2. **Switch增强** — JDK 21转正，支持复杂对象匹配且必须显式处理case null
3. **卫语句** — 用when结合布尔表达式，提供比枚举常量更灵活的条件过滤

**收尾：** 这三点都能配合实战聊。您想深入聊原理、对比还是避坑？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：JDK 21的Pattern Mat… | "JDK 21的Pattern Matching（模式匹配）有哪些重要改进？一句话——像安检仪，过检的同时直接把身份证信息读出来，不用再查册子。" | 开场钩子 |
| 0:40 | 概念动画/示意图 | "将类型检查与数据绑定合二为一，消除样板代码——像安检仪，过检的同时直接把身份证信息读出来，不用再查册子" | 核心定义 |
| 1:20 | 核心目的示意 | "消除冗余的类型检查与强转，新instanceof直接绑定局部变量" | 要点1 |
| 2:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |
