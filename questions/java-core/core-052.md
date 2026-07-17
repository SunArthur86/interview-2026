---
id: core-052
difficulty: L2
category: java-core
feynman:
  essence: throws声明风险，throw制造事故。
  analogy: throws是“小心地滑”的警示牌，throw是真扔了一个香蕉皮。
  first_principle: 如何明确异常的产生源头与处理责任的归属？
  key_points:
  - throws用于方法签名，throw用于方法内部
  - throws后面跟类名，throw后面跟对象
  - throws表示可能性，throw表示执行动作
  - throws由上层处理，throw中断当前流程
memory_points:
- 位置差异：throws在方法签名上，throw在方法体内部。
- 跟随内容：throws后跟异常类名（可多个），throw后跟异常对象（仅一个）。
- 职责区分：throws是声明警告（甩锅给调用者），throw是执行动作（真实抛出中断）。
- 实战避坑：Spring声明式事务默认只对throw的RuntimeException回滚。
---

# Throw和throws的区别？

### throw 和 throws 的区别

**1. 作用位置不同**
*   **`throws`**：用在**方法签名（声明）**上，位于参数列表之后。后面跟的是**异常类名**（可以是多个，用逗号分隔），表示该方法可能抛出这些异常。
    ```java
    public void readFile(String path) throws IOException, FileNotFoundException {
        // 方法体
    }
    ```
*   **`throw`**：用在**方法体内部**，通常写在具体的逻辑代码行。后面跟的是**异常对象实例**，表示代码运行到这里显式地抛出一个异常。
    ```java
    if (path == null) {
        throw new IllegalArgumentException("路径不能为空");
    }
    ```

**2. 功能含义不同**
*   **`throws` (声明异常)**：一种**承诺**或**警告**。它告诉方法的调用者：“调用我这个方法是有风险的，你需要处理（捕获）或者继续向上抛出这些可能发生的异常”。它处理的是异常的可能性。
*   **`throw` (抛出异常)**：一种**动作**。它是手动制造一个异常事件，打断当前程序的正常执行流程，将异常对象抛出到调用栈。它处理的是异常的实际发生。

**3. 处理方式不同**
*   **`throws`**：仅仅是声明，并不真正处理异常。它将异常的处理责任**甩锅（委托）**给方法的调用者（JVM 最终处理会打印堆栈并退出）。
*   **`throw`**：实际上是产生了异常，必须有对应的处理机制（try-catch 捕获，或者当前方法用 throws 声明继续向上抛），否则编译器会报错（针对受检异常）。

**4. 与异常类型的关系**
*   `throws` 可以声明 `Exception` 及其子类（包括 `RuntimeException`，虽然通常不强制声明非受检异常）。
*   `throw` 可以抛出任何 `Throwable` 及其子类的实例。

### 5. 实战案例

*   **自定义异常**：在构建 Spring Boot 统一异常处理机制时，我们会在 Service 层校验参数，如果业务逻辑不满足（如“余额不足”），直接 `throw new BusinessException(ErrorCode.NOT_ENOUGH_BALANCE)`，然后由全局 `@ControllerAdvice` 捕获并统一返回 JSON 错误码，避免污染 Controller 层代码。
*   **事务回滚**：在 Spring 声明式事务中，默认只对 `RuntimeException` 和 `Error` 进行回滚。如果你在方法中 `throw` 了一个 checked Exception（如 `throw new Exception("error")`）且未在 `@Transactional(rollbackFor = Exception.class)` 中指定，事务将不会回滚，导致数据不一致的严重 Bug。

### 对比表格

| 维度 | throw | throws |
| :--- | :--- | :--- |
| **位置** | 方法体内部 | 方法签名上 |
| **后面跟的内容** | 异常对象实例 | 异常类名 |
| **作用** | 手动抛出异常 | 声明可能抛出的异常类型 |
| **数量** | 一次只能抛出一个 | 可声明多个异常（逗号分隔） |
| **对调用方影响** | 程序中断，进入异常处理流程 | 调用方必须处理或继续声明 |

## 记忆要点

- 位置差异：throws在方法签名上，throw在方法体内部。
- 跟随内容：throws后跟异常类名（可多个），throw后跟异常对象（仅一个）。
- 职责区分：throws是声明警告（甩锅给调用者），throw是执行动作（真实抛出中断）。
- 实战避坑：Spring声明式事务默认只对throw的RuntimeException回滚。

## 结构化回答

**30 秒电梯演讲：** throws声明风险，throw制造事故。打个比方，throws是“小心地滑”的警示牌，throw是真扔了一个香蕉皮。

**展开框架：**
1. **位置差异** — throws在方法签名上，throw在方法体内部。
2. **跟随内容** — throws后跟异常类名（可多个），throw后跟异常对象（仅一个）。
3. **职责区分** — throws是声明警告（甩锅给调用者），throw是执行动作（真实抛出中断）。

**收尾：** 我在项目里踩过坑——自定义异常：在构建 Spring Boot 统一异常处理机制时，我们会在 Service 层校验参数，如果业务逻辑不满足（如“余额不足”），直接 `throw new BusinessException(ErrorCode.NOT_ENOUGH_BALANCE)`，然后由全局 `@ControllerAdvice` 捕获并统一返回 JSON 错误码，避免污染 Controller 层代码。您想深入聊哪一段：原理、避坑还是对比选型？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：Throw和throws的区别 | "Throw和throws的区别？一句话——throws是“小心地滑”的警示牌，throw是真扔了一个香蕉皮。" | 开场钩子 |
| 0:40 | 概念动画/示意图 | "throws声明风险，throw制造事故——throws是“小心地滑”的警示牌，throw是真扔了一个香蕉皮" | 核心定义 |
| 1:20 | 位置差异示意 | "throws在方法签名上，throw在方法体内部。" | 要点1 |
| 2:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |
