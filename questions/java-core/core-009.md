---
id: core-009
difficulty: L1
category: java-core
feynman:
  essence: 用注解将URL请求映射到Java方法处理。
  analogy: 像餐厅菜单，你点的菜名（URL）直接对应后厨做菜的配方（方法）。
  first_principle: 如何将HTTP请求高效地映射到业务处理逻辑？
  key_points:
  - '@RestController组合@Controller和@ResponseBody'
  - '@RequestMapping及变体映射URL路径'
  - '@PathVariable获取路径参数'
  - '@RequestBody接收请求体数据'
memory_points:
- 映射类：@RequestMapping通用，而@GetMapping/@PostMapping是语义化的组合注解。
- 接参数对比：@RequestParam接URL问号参数，@PathVariable接URI路径变量。
- '@RequestBody专用于绑定请求体(如JSON数据)。'
- 实战避坑：参数用Integer时若前端传空串，必须设defaultValue防转换异常。
frequency: medium
---

# 什么是MVC常用注解？

Spring MVC 常用注解用于简化 Web 层开发，将 HTTP 请求映射到 Java 方法。

## 核心流程架构

```text
┌─────────┐    1. Request     ┌──────────────────┐
│ Browser │ ─────────────────>│  DispatcherServlet│ (前端控制器)
└─────────┘                   └────────┬─────────┘
                                       │ 2. 根据URL查找
                              ┌────────▼─────────┐
                              │  HandlerMapping  │
                              │ (RequestMapping) │
                              └────────┬─────────┘
                                       │ 3. 返回执行链
                                       │ (Handler+Interceptor)
                              ┌────────▼─────────┐
                              │ HandlerAdapter   │ (适配器，调用Controller)
                              └────────┬─────────┘
                                       │ 4. 执行业务逻辑
                              ┌────────▼─────────┐
                              │   @Controller    │
                              │                  │
                              │ @RestController  │
                              └────────┬─────────┘
                                       │ 5. 返回 ModelAndView / Data
                              ┌────────▼─────────┐
                              │   ViewResolver   │ (视图解析器)
                              └────────┬─────────┘
                                       │ 6. 返回 View 对象
                              ┌────────▼─────────┐
                              │      View        │ (JSP/HTML/JSON)
                              └────────┬─────────┘
                                       │ 7. 渲染页面/数据
                                       └────────────────┘
```

## 常用注解详解

### 1. 请求映射类
- **@RequestMapping**：通用映射，支持类和方法级，可配置 method, params, headers。
- **@GetMapping / @PostMapping** 等：组合注解，语义更清晰。

### 2. 参数绑定类
- **@RequestParam**：绑定 URL 查询参数或表单数据。
- **@PathVariable**：绑定 URI 路径变量（如 `/user/{id}`）。
- **@RequestBody**：绑定请求体（通常用于 JSON）。
- **@RequestHeader**：绑定请求头信息。

**实战案例**：
在开发 RESTful API 时，前端传来 `userId` 为空字符串 `""`，若使用 `@RequestParam(required = false)` 且未指定 `defaultValue`，Spring 会尝试将其转换为 Integer 从而抛出 `NumberFormatException`。正确的做法是显式设置 `defaultValue` 或在业务层做空串判断。此外，若遇到中文乱码，需检查是否在 WebMvcConfigurer 中配置了 `StringHttpMessageConverter` 的字符集为 UTF-8。

**代码示例（参数校验与接收实战）**：
```java
@RestController
@RequestMapping("/api/users")
public class UserController {

    // 路径变量 + 必填参数校验
    @GetMapping("/{id}")
    public Result getUser(@PathVariable Long id, 
                          @RequestParam(value = "detail", defaultValue = "false") boolean isDetail) {
        // 业务逻辑
        return Result.ok(userService.findById(id, isDetail));
    }

    // JSON Body 接收 + 自动校验 (需开启 @Validated)
    @PostMapping
    public Result createUser(@Validated @RequestBody UserCreateDTO dto) {
        // 若 DTO 字段有 @NotBlank，校验失败会自动抛出 MethodArgumentNotValidException
        return Result.ok(userService.create(dto));
    }
}
```

**对比表格：参数接收注解区别**

| 注解 | 数据来源 | Content-Type 要求 | 典型应用场景 |
|------|----------|------------------|--------------|
| @RequestParam | URL Query / Form Data | application/x-www-form-urlencoded | 搜索过滤、表单提交 |
| @PathVariable | URL Path | 无 | RESTful 资源定位 (如 /user/1) |
| @RequestBody | Request Body | application/json (或 XML) | 复杂对象创建、POST 请求体 |
| @RequestHeader | HTTP Headers | 无 | 获取 Token、User-Agent |
| @CookieValue | Cookies | 无 | 获取 SessionID、追踪信息 |



## 核心流程图

```mermaid
flowchart TD
    BR([浏览器发起HTTP请求]):::start --> DS[DispatcherServlet<br/>前端控制器接收]
    DS --> HM[HandlerMapping<br/>解析RequestMapping注解]
    HM --> EC{URL匹配成功?}:::decision
    EC -->|否| N404[404 Not Found<br/>响应客户端]:::error
    EC -->|是| HA[HandlerAdapter<br/>适配器调用Controller]
    HA --> AN["解析方法注解<br/>@PathVariable/@RequestBody/@RequestParam"]
    AN --> CONV[HandlerMethodArgumentResolver<br/>参数类型转换与绑定]
    CONV --> CH{参数校验通过?}:::decision
    CH -->|否 Valid失败| BEX[MethodArgumentNotValidException<br/>全局异常处理]:::error
    CH -->|是| CTRL["Controller业务方法执行<br/>调用Service/Repository"]
    CTRL --> RT{返回类型判断}:::decision
    RT -->|ResponseBody / RestController| JACK[Jackson序列化为JSON]
    RT -->|ModelAndView / 视图名| VR[ViewResolver视图解析器]
    JACK --> WR[WriteResponseBodyAdvice<br/>响应体输出]
    VR --> RD["渲染视图HTML/JSP/Thymeleaf"]
    WR --> CL([客户端收到JSON响应]):::success
    RD --> CL
        classDef start fill:#e3f2fd,stroke:#1976d2,stroke-width:2px,color:#0d47a1
    classDef decision fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#e65100
    classDef success fill:#e8f5e9,stroke:#388e3c,stroke-width:2px,color:#1b5e20
    classDef error fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#b71c1c
    classDef storage fill:#eceff1,stroke:#455a64,stroke-width:2px,color:#263238
    classDef async fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#4a148c

```
## 记忆要点

- 映射类：@RequestMapping通用，而@GetMapping/@PostMapping是语义化的组合注解。
- 接参数对比：@RequestParam接URL问号参数，@PathVariable接URI路径变量。
- @RequestBody专用于绑定请求体(如JSON数据)。
- 实战避坑：参数用Integer时若前端传空串，必须设defaultValue防转换异常。

## 结构化回答


**30 秒电梯演讲：** 像餐厅菜单，你点的菜名（URL）直接对应后厨做菜的配方（方法）。

**展开框架：**
1. **@RestCon** — @RestController组合@Controller和@ResponseBody
2. **@Request** — @RequestMapping及变体映射URL路径
3. **@PathVar** — @PathVariable获取路径参数

**收尾：** 这是我实战中的理解，您想深入哪一段？


## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：什么是MVC常用注解 | "什么是MVC常用注解？一句话——像餐厅菜单，你点的菜名（URL）直接对应后厨做菜的配方（方法）。" | 开场钩子 |
| 0:40 | 概念动画/示意图 | "用注解将URL请求映射到Java方法处理——像餐厅菜单，你点的菜名（URL）直接对应后厨做菜的配方（方法）" | 核心定义 |
| 1:20 | 映射类示意 | "@RequestMapping通用，而@GetMapping/@PostMapping是语义化的组合注解。" | 要点1 |
| 2:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |

### 视频流程图

```mermaid
flowchart LR

    subgraph Intro["引入"]
        A["什么是MVC常用注解？"]:::intro
    end

    subgraph Core["讲解"]
        B["映射类：@RequestMapping通用，而@Ge…"]:::core
        C["接参数对比：@RequestParam接URL问号参…"]:::deep
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

