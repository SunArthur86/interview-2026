---
id: core-165
difficulty: L3
category: java-core
feynman:
  essence: 元数据标签，通过反射或编译器在编译/运行时生效。
  analogy: 像给商品贴标签，价格条形码（编译期）或说明书（运行期）告诉机器怎么处理。
  first_principle: 如何在不侵入业务逻辑代码的情况下，为代码添加元数据或配置信息？
  key_points:
  - 使用@interface定义，配合元注解配置范围和生命周期
  - 编译期解析用于生成代码（如Lombok）
  - 运行期解析通过反射读取（如Spring依赖注入）
  - RetentionPolicy决定了注解存活到哪个阶段
memory_points:
- 工作三步曲：用@interface定义，打标签使用，最后配合解析器发挥作用。
- Retention决定生命周期：默认CLASS，SOURCE编译丢弃，RUNTIME可反射(框架常用)。
- 底层原理：注解本质继承自Annotation接口，运行时由动态代理生成实例。
- 两种解析时机：编译期APT生成代码(如Lombok)，运行期反射读取(如Spring)。
frequency: high
---

# Java 注解的工作原理是什么？如何自定义注解？

**注解（Annotation）** 是 JDK 5 引入的元数据机制，本身不直接影响代码逻辑，需要配合「解析器」才能发挥作用。

### 注解的工作原理（三步）：
1. **定义注解：** 用 `@interface` 声明，可加元注解（@Target、@Retention、@Documented、@Inherited）。
2. **使用注解：** 标注在类/方法/字段上。
3. **解析注解：**
   - **编译期解析：** 编译器/APT（Annotation Processing Tool）读取，如 Lombok 生成 getter/setter、ButterKnife 生成绑定代码。
   - **运行期解析：** 程序通过反射（Class.getAnnotation）读取，如 Spring 的 @Autowired、@Controller。

### 自定义注解示例：
```java
@Retention(RetentionPolicy.RUNTIME)  // 运行时保留
@Target(ElementType.METHOD)            // 作用于方法
public @interface MyCache {
    String key();
    int expire() default 60;
}

// 使用
@MyCache(key = "user:1", expire = 120)
public User getUser(long id) { ... }

// 反射解析
Method m = ...;
if (m.isAnnotationPresent(MyCache.class)) {
    MyCache c = m.getAnnotation(MyCache.class);
    String key = c.key();
}
```

### @Retention 三种策略：
- SOURCE：仅源码（如 @Override），编译后丢弃。
- CLASS（默认）：保留到 class 文件，运行时不可见。
- RUNTIME：运行时可通过反射读取（框架最常用）。

### 增强细节：原理与流程
注解本质上是继承自 `java.lang.annotation.Annotation` 的接口，其成员变量被编译器处理为抽象方法。当程序在编译或运行时处理注解时，实际上是通过动态代理机制生成了该注解接口的实现类实例。

**编译期处理流程图：**
```text
┌─────────────┐    Parse/AST    ┌───────────────────────────┐
│   Source    │ ──────────────> │  Compiler (javac)         │
│  (.java)    │                 │  ┌─────────────────────┐  │
└─────────────┘                 │  │ Abstract Syntax Tree│  │
                                │  └──────────┬──────────┘  │
                                └─────────────┼─────────────┘
                                              │ Check Annotations
                    ┌─────────────────────────┴─────────────────────┐
                    │          Does @Processor exist?               │
                    └─────────────────────────┬─────────────────────┘
                                             / \
                          YES (APT Process) /   \ NO (Standard Compile)
                                       /     \
                               ┌───────▼──────┐  ┌───────▼────────┐
                               │ Generate    │  │ Write .class   │
                               │ New Source  │  │ (Metadata)     │
                               └─────────────┘  └────────────────┘
```

### 实战经验与对比
**实战案例**：开发了一个自定义注解 `@PermissionCheck` 用于接口鉴权。初期使用 `RetentionPolicy.RUNTIME` 配合 Spring AOP 反射解析，发现高并发下反射有性能损耗。后来将鉴权逻辑改为编译期 APT（类似于 AutoService），自动生成一个静态的权限映射类，将运行时计算变为编译时生成，吞吐量提升 15%。

**代码示例（Spring 切面解析注解）**：
```java
@Around("@annotation(myCache)")
public Object cacheInterceptor(ProceedingJoinPoint pjp, MyCache myCache) throws Throwable {
    String key = myCache.key(); // 直接获取注解属性，无需反射
    // ... 缓存逻辑 ...
    return pjp.proceed();
}
```

**元注解 @Retention 生命周期对比**：
| 策略 | 编译期可见 | Class文件存在 | 运行时可见 | 典型应用 |
| :--- | :--- | :--- | :--- | :--- |
| **SOURCE** | 是 | 否 | 否 | Lombok, @Override |
| **CLASS** | 是 | 是 | 否 | 字节码操作工具 |
| **RUNTIME** | 是 | 是 | 是 | Spring, JUnit (反射) |


## 核心架构图

```mermaid
flowchart TD
    classDef start fill:#4CAF50,color:#fff
    classDef process fill:#2196F3,color:#fff
    classDef decision fill:#FF9800,color:#fff
    classDef special fill:#9C27B0,color:#fff
    classDef error fill:#f44336,color:#fff
    classDef info fill:#607D8B,color:#fff
    class A start
    class APT process
    class ASM decision
    class Annotation special
    class B error
    class ButterKnife info
    class C start
    class CGLIB process
    class Class decision
    class Component special
    class D error
    class Documented info
    class E start
    class F process
    class G decision
    class H special
    class I error
    class Inherited info
    class J start
    class JUnit process
    class K decision
    class L special
    class Lombok error
    class M info
    class N start
    class O process
    class Override decision
    class P special
    class Q error
    class Retention info
    class Runtime start
    class Source process
    class Spring decision
    class SpringBoot special
    class Target error
    class View info
    class br start
    A[注解 Annotation] --> B[元注解 标注注解]
    B --> C[Target 目标位置]
    B --> D[Retention 保留期]
    B --> E[Inherited 可继承]
    B --> F[Documented 文档]
    D --> G[Source 源码如 Override]
    D --> H[Class 字节码默认]
    D --> I[Runtime 运行时 反射可读]
    J[处理机制] --> K[APT 编译期<br/>生成代码 Lombok]
    J --> L[字节码增强<br/>ASM/CGLIB]
    J --> M["运行时反射扫描<br/>Spring @Component"]
    N[典型应用] --> O[Spring/SpringBoot 配置]
    N --> P[JUnit 测试]
    N --> Q[ButterKnife View 绑定]
```

## 记忆要点

- 工作三步曲：用@interface定义，打标签使用，最后配合解析器发挥作用。
- Retention决定生命周期：默认CLASS，SOURCE编译丢弃，RUNTIME可反射(框架常用)。
- 底层原理：注解本质继承自Annotation接口，运行时由动态代理生成实例。
- 两种解析时机：编译期APT生成代码(如Lombok)，运行期反射读取(如Spring)。

## 结构化回答

**30 秒电梯演讲：** 元数据标签，通过反射或编译器在编译/运行时生效。打个比方，像给商品贴标签，价格条形码（编译期）或说明书（运行期）告诉机器怎么处理。

**展开框架：**
1. **工作三步曲** — 用@interface定义，打标签使用，最后配合解析器发挥作用。
2. **Retention决定生命周期** — 默认CLASS，SOURCE编译丢弃，RUNTIME可反射(框架常用)。
3. **底层原理** — 注解本质继承自Annotation接口，运行时由动态代理生成实例。

**收尾：** 我在项目里踩过坑——开发了一个自定义注解 `@PermissionCheck` 用于接口鉴权。您想深入聊哪一段：原理、避坑还是对比选型？

## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：Java 注解的工作原理是什么？如何… | "Java 注解的工作原理是什么？如何自定义注解？一句话——像给商品贴标签，价格条形码（编译期）或说明书（运行期）告诉机器怎么处理。" | 开场钩子 |
| 0:45 | 概念动画/示意图 | "元数据标签，通过反射或编译器在编译/运行时生效——像给商品贴标签，价格条形码（编译期）或说明书（运行期）告诉机器怎么处理" | 核心定义 |
| 1:30 | 工作三步曲示意 | "用@interface定义，打标签使用，最后配合解析器发挥作用。" | 要点1 |
| 2:15 | 要点2图解示意 | "默认CLASS，SOURCE编译丢弃，RUNTIME可反射(框架常用)。" | 要点2 |
| 3:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |

### 视频流程图

```mermaid
flowchart LR

    subgraph Intro["引入"]
        A["Java 注解的工作原理是什么？如何自定义注解？"]:::intro
    end

    subgraph Core["讲解"]
        B["工作三步曲：用@interface定义，打标签使用，…"]:::core
        C["Retention决定生命周期：默认CLASS，SO…"]:::deep
    end

    subgraph Practice["实战"]
        D["代码实战"]:::practice
    end

    subgraph Wrap["收尾"]
        E["总结回顾"]:::wrap
    end

    A --> B --> C --> D --> E

    classDef intro fill:#FF9800,color:#fff,stroke:#F57C00,stroke-width:2px
    classDef core fill:#2196F3,color:#fff,stroke:#1976D2,stroke-width:2px
    classDef deep fill:#4CAF50,color:#fff,stroke:#388E3C,stroke-width:2px
    classDef practice fill:#9C27B0,color:#fff,stroke:#7B1FA2,stroke-width:2px
    classDef wrap fill:#607D8B,color:#fff,stroke:#455A64,stroke-width:2px
```

