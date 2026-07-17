---
id: sjdk-008
difficulty: L1
category: java-core
feynman:
  essence: 增强Switch支持表达式返回值与模式匹配
  analogy: 把Switch从单纯的“路口选择”升级为“能返回结果的计算器”
  first_principle: 消除传统Switch容易漏写break的陷阱并简化条件赋值
  key_points:
  - 支持表达式形式返回值
  - 箭头语法避免fall-through
  - yield用于复杂逻辑返回
  - 支持多标签合并与穷举检查
memory_points:
- 区别：Switch表达式(JDK14)作为赋值对象必须有返回值，且无fall-through穿透
- 语法：箭头(->)替代冒号(:)自动阻断穿透，多行代码块用yield返回值
- 安全：作表达式使用触发编译器强制穷举检查，避免漏写分支引发BUG
- 进化：JDK 21支持类型与Record模式匹配，并能用when添加灵活条件
---

# JDK 21中Switch表达式和语句有什么区别？有哪些新特性？

🎯 本质：Switch表达式（JDK 14正式）让switch可以作为表达式返回值，同时引入箭头语法和fall-through控制。

📊 新旧对比与编译逻辑：
```java
// 旧语法 - 语句(statement)，容易漏写 break 导致 fall-through穿透
switch (day) {
    case MONDAY: result = 6; break; // 必须手动 break
    default: result = 0;
}

// 新语法 - 表达式(expression)，无 fall-through，直接赋值
int result = switch (day) {
    case MONDAY, FRIDAY, SUNDAY → 6; // 箭头语法，多标签合并
    case TUESDAY → 7;
    default → 0;
};

// 多行逻辑块使用 yield 返回值
int result = switch (day) {
    case MONDAY → {
        log("Monday");
        yield 6; // 必须显式 yield
    }
    default → 0;
};
```

**实战案例**：在策略模式或工厂模式重构中，以前需要写大量的 `if-else` 或 `Map` 映射。现在利用 switch 表达式配合 Record 模式匹配，可以在 5 行代码内完成对象构造并注入 Spring 上下文，且编译器会强制检查是否漏掉了某个枚举类型。

**🏗️ Switch 编译后的差异逻辑**：
```text
┌─────────────────────┐       ┌─────────────────────────┐
│   Old Switch Stmt   │       │   New Switch Expr       │
├─────────────────────┤       ├─────────────────────────┤
│ bytecode: tableswitch       │ bytecode: tableswitch/lookupswitch
│ - Case 0: goto label_a      │ - Case 0: push value 6; return
│ - Case 1: goto label_b      │ - Case 1: push value 7; return
│ - default: goto label_d     │ - default: push value 0; return
│                             │                          │
│ label_a: ... (fall-through) │ (箭头语法自动阻断)        │
│ label_b: break (pop stack)  │                          │
└─────────────────────┘       └─────────────────────────┘
```

关键改进与原理：
1. **箭头语法 (→) vs 冒号 (:)**：
   - `→` 右侧可以是表达式、块或 throw 语句。执行完箭头右侧后自动跳出，无需 break。
   - `:` 保持传统行为，仍需 break 防止穿透。
2. **yield 关键字**：用于在带 `{}` 的代码块中产生值。注意 `yield` 是受限标识符，仍可用作变量名但极不推荐。
3. **穷举检查**：作为表达式使用时，编译器强制要求覆盖所有可能的输入值（对于 enum，必须处理所有枚举值或 default；对于 sealed 类，如果覆盖了所有 permitted 子类则可不加 default）。
4. **类型兼容性**：整个 switch 表达式的结果类型必须与目标变量类型兼容（支持基本类型拓宽、拆箱等）。
5. **模式匹配集成（JDK 21）**：
   ```java
   // 结合 Record 模式匹配
   static String formatter(Object obj) {
       return switch (obj) {
           case Integer i -> String.format("int %d", i);
           case Long l    -> String.format("long %d", l);
           case Double d  -> String.format("double %f", d);
           case String s  -> String.format("String %s", s);
           default        -> obj.toString();
       };
   }
   ```

## 记忆要点

- 区别：Switch表达式(JDK14)作为赋值对象必须有返回值，且无fall-through穿透
- 语法：箭头(->)替代冒号(:)自动阻断穿透，多行代码块用yield返回值
- 安全：作表达式使用触发编译器强制穷举检查，避免漏写分支引发BUG
- 进化：JDK 21支持类型与Record模式匹配，并能用when添加灵活条件

## 结构化回答

**30 秒电梯演讲：** 增强Switch支持表达式返回值与模式匹配。打个比方，把Switch从单纯的“路口选择”升级为“能返回结果的计算器”。

**展开框架：**
1. **区别** — Switch表达式(JDK14)作为赋值对象必须有返回值，且无fall-through穿透
2. **语法** — 箭头(->)替代冒号(:)自动阻断穿透，多行代码块用yield返回值
3. **安全** — 作表达式使用触发编译器强制穷举检查，避免漏写分支引发BUG

**收尾：** 我在项目里踩过坑——┌─────────────────────┐       ┌─────────────────────────┐。您想深入聊哪一段：原理、避坑还是对比选型？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：JDK 21中Switch表达式和语… | "JDK 21中Switch表达式和语句有什么区别？有哪些新特性？一句话——把Switch从单纯的“路口选择”升级为“能返回结果的计算器”。" | 开场钩子 |
| 0:40 | 概念动画/示意图 | "增强Switch支持表达式返回值与模式匹配——把Switch从单纯的“路口选择”升级为“能返回结果的计算器”" | 核心定义 |
| 1:20 | 区别示意 | "Switch表达式(JDK14)作为赋值对象必须有返回值，且无fall-through穿透" | 要点1 |
| 2:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |
