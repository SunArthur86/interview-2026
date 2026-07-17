---
id: scen-074
difficulty: L2
category: scenario
subcategory: 安全与风控
tags:
- 权限管理
- RBAC
- ABAC
- 数据权限
- Spring Security
- 菜单权限
feynman:
  essence: 通过角色或属性规则，精确控制用户对资源的访问权限。
  analogy: 像公司的门禁卡系统，不同职级刷卡能进不同房间。
  first_principle: 如何在安全性和灵活性之间平衡，精确控制资源访问？
  key_points:
  - RBAC核心：用户关联角色，角色关联权限
  - 数据权限：通过SQL拦截控制行/列可见范围
  - ABAC进阶：基于用户、资源、环境属性动态判断
  - 权限缓存：登录后预加载，使用拦截器快速校验
follow_up:
- RBAC和ABAC如何选择？
- 数据权限如何实现？
- 角色继承如何设计？
memory_points:
- 核心模型：RBAC基于静态角色(用户-角色-权限)，简单直观；ABAC基于动态属性，极灵活
- RBAC进阶：RBAC1支持角色继承，RBAC2引入互斥/数量限制约束，满足复杂企业架构
- 权限粒度：功能权限控菜单按钮，数据权限控行级(部门)/列级(脱敏)可见度
- 校验机制：登录将权限列表注入Redis，请求时拦截器利用AntPathMatcher做URL匹配
- 数据权限实现：底层依赖MyBatis拦截器动态拼装SQL条件(如 WHERE dept_id = ?)
---

# 如何设计一个权限管理系统（RBAC/ABAC）？

【场景分析】
权限管理需求：控制谁能访问什么资源、做什么操作。

【RBAC（基于角色的访问控制）】
模型：用户 → 角色 → 权限 → 资源
```
用户(User)     角色(Role)     权限(Permission)
张三    →    管理员    →   [用户管理, 商品管理, 订单查看]
李四    →    运营      →   [商品管理, 订单管理]
王五    →    客服      →   [订单查看, 退款处理]
```

【RBAC数据模型】
```sql
-- 用户表
user(id, name, email, ...)
-- 角色表
role(id, name, description)
-- 权限表
permission(id, name, code, resource, action)
-- 用户-角色关联
user_role(user_id, role_id)
-- 角色-权限关联
role_permission(role_id, permission_id)
```

【实战案例】
在SaaS系统中，不同租户（租户A、租户B）可能有自定义的角色名（如A叫“经理”，B叫“主管”），但权限逻辑相同。设计时需将Role表增加`tenant_id`字段，确保权限隔离；或者增加“角色组”概念，将通用权限模板化，避免每个租户重复配置底层数据权限规则。

【代码示例】
```java
// 权限校验拦截器 (Java Spring风格)
@Component
public class AuthInterceptor implements HandlerInterceptor {
    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        String userId = request.getHeader("UserId");
        String requestUri = request.getRequestURI();
        
        // 1. 获取用户权限缓存
        Set<String> permissions = redisTemplate.opsForSet().members("auth:user:" + userId);
        
        // 2. Ant路径匹配
        boolean hasPermission = permissions.stream()
            .anyMatch(perm -> new AntPathMatcher().match(perm, requestUri));
            
        if (!hasPermission) throw new AccessDeniedException("无权访问");
        return true;
    }
}
```

【权限校验流程】
1. 用户登录 → 获取用户角色 → 获取权限列表 → 缓存到Redis
2. 请求到达 → 拦截器检查权限
3. 权限匹配方式：
   - 精确匹配：`user:list`
   - 通配符：`user:*`
   - Ant风格：`/api/user/**`

【RBAC扩展】
1. RBAC0：基础模型（用户-角色-权限）
2. RBAC1：增加角色继承（角色树）
   - 管理员继承运营的权限
3. RBAC2：增加约束
   - 互斥角色（不能同时是审批人和申请人）
   - 角色数量限制
4. RBAC3：RBAC1 + RBAC2

【数据权限】
- 行级权限：只能看到自己部门的订单
- 列级权限：只能看到手机号后4位
- 实现：MyBatis拦截器动态拼接SQL
```sql
-- 自动追加数据权限条件
SELECT * FROM orders WHERE 1=1
AND dept_id IN (SELECT dept_id FROM user_dept WHERE user_id = ?)
```

【ABAC（基于属性的访问控制）】
基于属性而非角色：
- 用户属性：部门、职级、地区
- 资源属性：类型、敏感等级
- 环境属性：时间、IP
- 策略：IF 用户.职级>=5 AND 资源.类型='财务' AND 环境.时间='工作时间' THEN 允许

ABAC更灵活但更复杂，适合大型企业。

【RBAC vs ABAC】

| 维度 | RBAC | ABAC |
| :--- | :--- | :--- |
| **核心逻辑** | 基于静态角色（你是谁） | 基于动态属性（你具备什么特征） |
| **复杂度** | 低，易于理解和管理 | 高，需维护复杂的策略规则引擎 |
| **灵活性** | 中，变更角色需重新分配 | 极高，可直接修改属性满足临时授权 |
| **适用场景** | 传统企业后台、常规CMS | 云资源(IAM)、金融风控、多租户SaaS |
| **性能** | 快，通常查表即可 | 较慢，需实时计算布尔逻辑表达式 |

【菜单权限 vs 按钮权限】
- 菜单权限：控制导航菜单显示
- 按钮权限：控制页面内操作按钮（增删改查）
- 数据权限：控制数据可见范围
- API权限：控制接口访问

【Spring Security集成】
- `@PreAuthorize("hasPermission('user', 'create')")`
- 自定义PermissionEvaluator
- 注解 + AOP实现声明式权限控制

## 记忆要点

- 核心模型：RBAC基于静态角色(用户-角色-权限)，简单直观；ABAC基于动态属性，极灵活
- RBAC进阶：RBAC1支持角色继承，RBAC2引入互斥/数量限制约束，满足复杂企业架构
- 权限粒度：功能权限控菜单按钮，数据权限控行级(部门)/列级(脱敏)可见度
- 校验机制：登录将权限列表注入Redis，请求时拦截器利用AntPathMatcher做URL匹配
- 数据权限实现：底层依赖MyBatis拦截器动态拼装SQL条件(如 WHERE dept_id = ?)

## 结构化回答

**30 秒电梯演讲：** 通过角色或属性规则，精确控制用户对资源的访问权限。打比方——像公司的门禁卡系统，不同职级刷卡能进不同房间。落到工程上，用户关联角色，角色关联权限。

**展开框架：**
1. **RBAC核心** — 用户关联角色，角色关联权限
2. **数据权限** — 通过SQL拦截控制行/列可见范围
3. **ABAC进阶** — 基于用户、资源、环境属性动态判断

**收尾：** 这几个点都能配合实战展开。您想继续聊哪个追问——比如 「RBAC和ABAC如何选择」 或者 「数据权限如何实现」？

## 视频脚本

> 预计时长：2 分钟 | 由浅入深

| 时间 | 画面/字幕 | 口播台词 | 讲解要点 |
|------|----------|----------|----------|
| 0:00 | 标题卡：权限管理系统（RBAC/ABAC） | "权限管理系统（RBAC/ABAC），一分钟讲透。" | 开场钩子 |
| 0:35 | 生活类比动画 | "打个比方——像公司的门禁卡系统，不同职级刷卡能进不同房间。" | 核心类比 |
| 1:10 | 概念定义动画 | "一句话：通过角色或属性规则，精确控制用户对资源的访问权限。" | 核心定义 |
| 1:50 | RBAC核心 图解 | "用户关联角色，角色关联权限。" | RBAC核心 |
