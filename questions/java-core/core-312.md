---
id: core-312
difficulty: L3
category: java-core
feynman:
  essence: 通过四个修饰符控制代码可见范围的访问控制机制。
  analogy: 像房间门锁：private只给自己进，default给家人进，protected给家人和亲戚进，public给所有人进。
  first_principle: 如何平衡代码封装性与复用性？
  key_points:
  - private最严格，仅限本类
  - default仅限包内
  - protected包含跨包子类
  - public范围最大，全局可见
memory_points:
- 口诀：私(default)同包保子公，范围从小到大层层递进
- 易混点：protected跨包时，子类只能用super调父类实例，不能直接new父类调用
- 局部变量无权限：方法内的变量不可加任何访问修饰符，仅作用于方法内部
- 设计原则：最小权限法，能private绝不default，为扩展留protected钩子
---

# 说一说你对Java访问权限的了解？

**修正后的答案如下：**

Java通过访问修饰符控制类、变量、方法和构造方法的访问权限，共有四个级别：

1. **private（私有）**
   - 访问范围：仅限当前类内部可见。
   - 用途：封装内部细节，隐藏实现。
   - **补充**：修饰外部类时，只有内部类可以使用 private（静态内部类常用于单例模式）。

2. **default（默认/包私有）**
   - 访问范围：同一包内的类可见。
   - 注意：不写任何修饰符时默认为此级别。

3. **protected（受保护）**
   - 访问范围：同一包内的类 + 所有子类（即使子类在不同包中）。
   - 用途：便于继承体系中的复用。
   - **补充细节**：
     - 若子类与父类不在同一包，子类实例可以访问其继承的 protected 成员，但**不能访问父类实例**的 protected 成员（即 `super.protectedMethod()` 可以，但 `fatherInstance.protectedMethod()` 不行，除非是同一个包）。

4. **public（公共）**
   - 访问范围：对所有类可见。
   - 用途：定义对外暴露的接口。

| 修饰符 | 同一类 | 同一包 | 子类（不同包） | 全局 |
| :--- | :---: | :---: | :---: | :---: |
| private | ✅ | ❌ | ❌ | ❌ |
| default | ✅ | ✅ | ❌ | ❌ |
| protected | ✅ | ✅ | ✅ | ❌ |
| public | ✅ | ✅ | ✅ | ✅ |

### 设计原则
遵循“最小权限原则”：如果一个类成员不需要被外部访问，就将其设为 private；只有在需要被子类复用时才考虑 protected；尽量降低访问权限以提高封装性和安全性。

### 实战案例：API 设计中的 protected 与 default 抉择
在设计一个可扩展的框架（如 Spring Template）时，核心流程方法设为 `public` 供调用，但将钩子方法（如 `beforeExecute`）设为 `protected`。这样既允许外部继承类重写逻辑进行定制，又能防止无关业务类随意调用框架内部逻辑，保证了框架的稳定性和可扩展性。

### 代码示例：访问权限实战
```java
package com.example.lib;

public class BaseService {
    private void secret() { /* ... */ } // 仅本类
    void packageLog() { /* ... */ }      // default，同包可见
    protected void templateHook() { /* ... */ } // 供子类重写
    public void execute() { /* ... */ }  // 对外接口
}

// 同包类
class ServiceHelper {
    void test(BaseService s) {
        s.packageLog(); // ✅ 编译通过
        // s.templateHook(); // ❌ 同包非子类不可访问 protected（取决于具体 JVM 规范理解，通常 protected 跨包只给子类）
    }
}

// 不同包子类
package com.example.app;
import com.example.lib.BaseService;
public class MyService extends BaseService {
    void run() {
        this.execute();       // ✅ public
        this.templateHook();  // ✅ protected (继承的)
        // this.packageLog();  // ❌ default
    }
}
```

---

## 常见考点
1. **protected 的修饰外部类**：外部类能否被 protected 修饰？（不能，外部类只能用 public 或 default）。
2. **访问权限与继承**：父类中 private 的方法，子类能否继承？（不能继承，也就无法重写Override，虽然可以定义同名方法，但这不算多态的重写）。
3. **局部变量的访问权限**：局部变量（方法内定义）能否用 public/protected 修饰？（不能，局部变量只能用 final，访问权限默认仅限于方法内）。

## 记忆要点

- 口诀：私(default)同包保子公，范围从小到大层层递进
- 易混点：protected跨包时，子类只能用super调父类实例，不能直接new父类调用
- 局部变量无权限：方法内的变量不可加任何访问修饰符，仅作用于方法内部
- 设计原则：最小权限法，能private绝不default，为扩展留protected钩子

## 结构化回答

**30 秒电梯演讲：** 通过四个修饰符控制代码可见范围的访问控制机制。打个比方，像房间门锁：private只给自己进，default给家人进，protected给家人和亲戚进，public给所有人进。

**展开框架：**
1. **口诀** — 私(default)同包保子公，范围从小到大层层递进
2. **易混点** — protected跨包时，子类只能用super调父类实例，不能直接new父类调用
3. **局部变量无权限** — 方法内的变量不可加任何访问修饰符，仅作用于方法内部

**收尾：** 我在项目里踩过坑——实战案例：API 设计中的 protected 与 default 抉择。您想深入聊哪一段：原理、避坑还是对比选型？

## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：说一说你对Java访问权限的了解 | "说一说你对Java访问权限的了解？一句话——像房间门锁：private只给自己进，default给家人进，protected给家人和亲戚进，public给所有人进。" | 开场钩子 |
| 0:45 | 概念动画/示意图 | "通过四个修饰符控制代码可见范围的访问控制机制——像房间门锁：private只给自己进，default给家人进，protected给家人和亲戚进，public给所有人进" | 核心定义 |
| 1:30 | 口诀示意 | "私(default)同包保子公，范围从小到大层层递进" | 要点1 |
| 2:15 | 易混点示意 | "protected跨包时，子类只能用super调父类实例，不能直接new父类调用" | 要点2 |
| 3:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |
