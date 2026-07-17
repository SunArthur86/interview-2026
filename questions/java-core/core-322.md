---
id: core-322
difficulty: L1
category: java-core
feynman:
  essence: 引入函数式编程、流式处理和新日期时间API，大幅提升开发效率。
  analogy: 像从手动挡换到自动挡跑车（Stream/Lambda），修好了老旧的仪表盘（Date API），加装了防撞系统。
  first_principle: 如何让Java代码更简洁、更符合现代函数式编程范式？
  key_points:
  - Lambda：简化代码写法
  - Stream：集合流式操作
  - Optional：优雅防空指针
  - Date：全新的时间API
memory_points:
- 两大基石：Lambda表达式（简化代码）与Stream API（函数式处理集合）。
- 防NPE利器：Optional容器，优雅链式处理多层嵌套对象的null判断。
- 接口增强：引入default方法让接口能具备默认实现，完美解决向后兼容问题。
- 异步与时间：CompletableFuture实现多任务编排，java.time包提供更安全的全新日期API。
---

# Java 8有哪些新特性？

### Java 8 新特性详解

1. **Lambda表达式**：函数式编程，简化匿名内部类
   `(a, b) → a + b`

2. **Stream API**：流式处理集合
   `list.stream().filter(x → x > 0).map(String::valueOf).collect(Collectors.toList())`

3. **Optional**：解决NPE
   `Optional.ofNullable(obj).map(Object::toString).orElse("null")`

4. **方法引用**：::语法
   `System.out::println`

5. **接口增强**：default方法和static方法

6. **新日期API**：java.time包
   LocalDate、LocalTime、LocalDateTime、Instant、Duration、Period

7. **CompletableFuture**：异步编程

8. **类型注解**：@NonNull String str

9. **forEach遍历Map**：map.forEach((k, v) → ...)

---

#### 深化实战补充

1. **实战案例（Stream & Optional）**：
   在处理电商订单详情时，曾遇到多层嵌套对象调用导致的 NPE。使用 `Optional.ofNullable(order.getUser()).map(User::getAddress).map(Address::getCity).orElse("Unknown")` 成功消除了 5 处显式的 `if null` 判断，代码简洁性提升 40%。

2. **代码示例（CompletableFuture 异步编排）**：
   ```java
   // 场景：并行查询用户信息和订单历史，合并后返回
   CompletableFuture<User> userFuture = CompletableFuture.supplyAsync(() -> userDao.findById(userId));
   CompletableFuture<List<Order>> ordersFuture = CompletableFuture.supplyAsync(() -> orderService.findOrders(userId));
   
   // 等待两个任务完成
   CompletableFuture<Void> allFutures = CompletableFuture.allOf(userFuture, ordersFuture);
   
   // 组装结果
   allFutures.thenApply(v -> new DetailDto(userFuture.join(), ordersFuture.join())).join();
   ```

## 记忆要点

- 两大基石：Lambda表达式（简化代码）与Stream API（函数式处理集合）。
- 防NPE利器：Optional容器，优雅链式处理多层嵌套对象的null判断。
- 接口增强：引入default方法让接口能具备默认实现，完美解决向后兼容问题。
- 异步与时间：CompletableFuture实现多任务编排，java.time包提供更安全的全新日期API。

## 结构化回答

**30 秒电梯演讲：** 引入函数式编程、流式处理和新日期时间API，大幅提升开发效率。打个比方，像从手动挡换到自动挡跑车（Stream/Lambda），修好了老旧的仪表盘（Date API），加装了防撞系统。

**展开框架：**
1. **两大基石** — Lambda表达式（简化代码）与Stream API（函数式处理集合）。
2. **防NPE利器** — Optional容器，优雅链式处理多层嵌套对象的null判断。
3. **接口增强** — 引入default方法让接口能具备默认实现，完美解决向后兼容问题。

**收尾：** 我在项目里踩过坑——实战案例（Stream & Optional）：。您想深入聊哪一段：原理、避坑还是对比选型？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：Java 8有哪些新特性 | "Java 8有哪些新特性？一句话——像从手动挡换到自动挡跑车（Stream/Lambda），修好了老旧的仪表盘（Date API），加装了防撞系统。" | 开场钩子 |
| 0:40 | 概念动画/示意图 | "引入函数式编程、流式处理和新日期时间API，大幅提升开发效率——像从手动挡换到自动挡跑车（Stream/Lambda），修好了老旧的仪表盘（Date API），加装了防撞系统" | 核心定义 |
| 1:20 | 两大基石示意 | "Lambda表达式（简化代码）与Stream API（函数式处理集合）。" | 要点1 |
| 2:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |
