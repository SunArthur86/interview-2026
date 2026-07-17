---
id: core-311
difficulty: L3
category: java-core
feynman:
  essence: 对象间一对多依赖，状态变化自动通知。
  analogy: 气象站更新数据，所有连接的手机APP同步刷新。
  first_principle: 如何实现对象间的松耦合协作，使得状态变化能被多方感知？
  key_points:
  - Subject维护Observer列表
  - Subject状态变化调用notifyObservers
  - Observer实现update接口处理更新
  - 解耦了事件源和事件处理者
memory_points:
- 一句话定义：主题状态一变，自动通知多个依赖的观察者，实现一对多联动
- 核心角色：Subject管状态发通知，Observer听更新做响应
- 高并发避坑：同步阻塞通知会拖垮全链路，实战必须升级为异步MQ或EventBus
- 线程安全注意点：多线程下注册和遍历观察者，需用CopyOnWriteArrayList防并发修改异常
---

# 说一说你了解的观察者模式？

**观察者模式**

### 定义
定义了一种一对多的依赖关系，让多个观察者对象同时监听某一个主题对象，当主题对象状态发生变化时，会通知所有的观察者对象，使得它们能够自动更新。

### 代码示例（气象站）
```java
import java.util.ArrayList;
import java.util.List;

// 主题接口
interface Subject {
    void addObserver(Observer observer);
    void removeObserver(Observer observer);
    void notifyObservers();
}

// 具体主题类
class WeatherStation implements Subject {
    private List<Observer> observers = new ArrayList<>();
    private float temperature;

    public void setTemperature(float temperature) {
        this.temperature = temperature;
        notifyObservers();
    }

    @Override
    public void addObserver(Observer observer) {
        observers.add(observer);
    }

    @Override
    public void removeObserver(Observer observer) {
        observers.remove(observer);
    }

    @Override
    public void notifyObservers() {
        for (Observer observer : observers) {
            observer.update(temperature);
        }
    }
}

// 观察者接口
interface Observer {
    void update(float temperature);
}

// 具体观察者类
class Display implements Observer {
    @Override
    public void update(float temperature) {
        System.out.println("Display: Temperature is " + temperature);
    }
}

class Logger implements Observer {
    @Override
    public void update(float temperature) {
        System.out.println("Logger: Logging temperature data - " + temperature);
    }
}

// 客户端代码
public class Client {
    public static void main(String[] args) {
        WeatherStation weatherStation = new WeatherStation();
        Observer display = new Display();
        Observer logger = new Logger();

        weatherStation.addObserver(display);
        weatherStation.addObserver(logger);

        // 模拟温度变化
        weatherStation.setTemperature(25.5f);
    }
}
```

### 设计细节与改进
1. **顺序通知**：代码中直接遍历 List，观察者会按照注册顺序被通知。如果观察者的 `update` 方法执行时间较长，会阻塞后续观察者的通知（阻塞式观察者）。
2. **线程安全**：当前实现不是线程安全的。如果在多线程环境中添加/删除观察者或并发通知，需使用 `CopyOnWriteArrayList` 或在 `notifyObservers` 加锁。
3. **异常处理**：如果某个观察者的 `update` 方法抛出异常，

### 实战案例：订单状态变更的通知风暴
在电商系统中，订单状态变更（如“支付成功”）需要触发短信通知、积分发放、物流下单等多个观察者。若采用同步阻塞的观察者模式，一旦短信服务超时，会导致物流下单被阻塞，严重影响交易流程。实战中通常引入 **MQ（消息队列）** 或 **异步EventBus**，将同步通知改为异步发布事件，彻底解耦并提高系统吞吐量。

### 代码示例：异步观察者模式（使用 ExecutorService）
```java
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

class AsyncEventStation {
    // 线程安全的 List
    private final List<Observer> observers = new CopyOnWriteArrayList<>();
    // 异步线程池
    private final ExecutorService executor = Executors.newFixedThreadPool(10);

    public void notifyObservers(final float data) {
        observers.forEach(observer -> {
            // 异步执行，不阻塞主线程
            executor.submit(() -> {
                try {
                    observer.update(data);
                } catch (Exception e) {
                    // 异常隔离，防止一个挂掉连累全部
                    System.err.println("Observer failed: " + e.getMessage());
                }
            });
        });
    }
    
    public void addObserver(Observer o) { observers.add(o); }
}
```

### 对比表格：传统观察者 vs EventBus (如 Guava) vs 发布订阅 MQ
| 维度 | 传统观察者 | Guava EventBus | 消息队列 (MQ) |
| :--- | :--- | :--- | :--- |
| **通信方式** | 同步调用 (内存) | 同步/异步 (内存) | 异步 (网络/磁盘) |
| **耦合度** | 强耦合 (需感知接口) | 松耦合 (基于注解/类) | 极松耦合 (Topic 模式) |
| **跨进程** | 不支持 | 不支持 | 支持 |
| **可靠性** | 依赖于进程存活 | 依赖于进程存活 | 持久化，支持重试 |
| **适用场景** | 简单单机事件逻辑 | 复杂单机内部解耦 | 微服务间通信 |

## 记忆要点

- 一句话定义：主题状态一变，自动通知多个依赖的观察者，实现一对多联动
- 核心角色：Subject管状态发通知，Observer听更新做响应
- 高并发避坑：同步阻塞通知会拖垮全链路，实战必须升级为异步MQ或EventBus
- 线程安全注意点：多线程下注册和遍历观察者，需用CopyOnWriteArrayList防并发修改异常

## 结构化回答

**30 秒电梯演讲：** 对象间一对多依赖，状态变化自动通知。打个比方，气象站更新数据，所有连接的手机APP同步刷新。

**展开框架：**
1. **一句话定义** — 主题状态一变，自动通知多个依赖的观察者，实现一对多联动
2. **核心角色** — Subject管状态发通知，Observer听更新做响应
3. **高并发避坑** — 同步阻塞通知会拖垮全链路，实战必须升级为异步MQ或EventBus

**收尾：** 我在项目里踩过坑——实战案例：订单状态变更的通知风暴。您想深入聊哪一段：原理、避坑还是对比选型？

## 视频脚本

> 预计时长：3 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：说一说你了解的观察者模式 | "说一说你了解的观察者模式？一句话——气象站更新数据，所有连接的手机APP同步刷新。" | 开场钩子 |
| 0:45 | 概念动画/示意图 | "对象间一对多依赖，状态变化自动通知——气象站更新数据，所有连接的手机APP同步刷新" | 核心定义 |
| 1:30 | 一句话定义示意 | "主题状态一变，自动通知多个依赖的观察者，实现一对多联动" | 要点1 |
| 2:15 | 核心角色示意 | "Subject管状态发通知，Observer听更新做响应" | 要点2 |
| 3:00 | 总结卡 | "记住这几条，面试不慌。下期讲进阶追问。" | 收尾 |
