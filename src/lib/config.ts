import type { Algorithm } from './types';

export interface CategoryConfig {
  label: string;
  icon: string;
  color: string;
}

export const APP_CONFIG = {
  appName: '面试题库 2026',
  appNameShort: '面试2026',
  appIcon: '🎯',
  appVersion: '1.0',
  storagePrefix: 'interview-2026',
  githubUrl: 'https://sunarthur86.github.io/interview-2026/',
  repoUrl: 'https://github.com/SunArthur86/interview-2026',
  themeColor: '#0071e3',
  categories: {
    // === Java ===
    'all':          { label: '全部', icon: '📚', color: '#0071e3' },
    'java-core':    { label: 'Java 核心', icon: '☕', color: '#f89820' },
    'concurrent':   { label: '并发编程', icon: '⚡', color: '#ff3b30' },
    'jvm':          { label: 'JVM', icon: '🔧', color: '#5856d6' },
    'framework':    { label: 'Spring 全家桶', icon: '🌱', color: '#34c759' },
    'database':     { label: '数据库', icon: '🗄️', color: '#af52de' },
    'middleware':   { label: '中间件', icon: '📦', color: '#00c7be' },
    'distributed':  { label: '分布式系统', icon: '🌐', color: '#ff9500' },
    'scenario':     { label: '场景设计', icon: '🏗️', color: '#007aff' },
    // === AI ===
    'llm-core':     { label: 'LLM 核心', icon: '🔥', color: '#ff3b30' },
    'ai-agent':     { label: 'AI Agent', icon: '🤖', color: '#af52de' },
    'ai-harness':   { label: 'AI Harness', icon: '🏗️', color: '#5856d6' },
    'fde':          { label: 'FDE', icon: '🚀', color: '#00c7be' },
    'eng-practice': { label: '工程化实战', icon: '⚙️', color: '#ff9500' },
    'ai-basics':    { label: 'AI 基础', icon: '💡', color: '#34c759' },
    'ai-scenario':  { label: 'AI 场景设计', icon: '🎯', color: '#e74c3c' },
    'multi-agent':  { label: '多智能体', icon: '🐝', color: '#f39c12' },
    // === JD 大厂 ===
    'ant-risk':       { label: '蚂蚁风控 Java', icon: '🐜', color: '#ff3b30' },
    'pdd-scm':        { label: '拼多多·供应链', icon: '🏭', color: '#e02e24' },
    'pdd-trade':      { label: '拼多多·交易核心', icon: '🛒', color: '#ff6c44' },
    'pdd-content':    { label: '拼多多·内容社区', icon: '📱', color: '#34c759' },
    'pdd-ai':         { label: '拼多多·AI 中台', icon: '🤖', color: '#af52de' },
    'java-architect': { label: 'Java 后端架构师', icon: '🏗️', color: '#5856d6' },
    'boss-ai':        { label: '巨剧核 AI 陪伴', icon: '🎭', color: '#ff2d55' },
    'biopharm':       { label: '生物医药 AI 全栈', icon: '🧬', color: '#00c7be' },
  } as Record<string, CategoryConfig>,
  subcatGroups: {
    // === Java 子分类 ===
    'Java基础': ['Java基础', 'Java集合', '集合', '泛型', '反射', '注解', 'IO/NIO', '异常处理', '字符串', '对象'],
    '面向对象': ['面向对象', 'OOP', '设计原则', '设计模式'],
    'JDK新特性': ['JDK新特性', '虚拟线程', 'JIT'],
    '线程与锁': ['线程基础', '线程池', '锁机制', '锁', 'synchronized', 'volatile', 'AQS', 'ThreadLocal', '并发'],
    '并发工具': ['并发工具', '并发容器', '原子类', 'CAS', 'ConcurrentHashMap', 'BlockingQueue', 'CountDownLatch', 'CompletableFuture'],
    'JVM内存': ['JMM', '内存区域', '内存模型', '堆栈', '方法区', '运行时数据区', 'JVM'],
    'GC与类加载': ['垃圾回收', 'GC', 'GC算法', 'GC调优', '调优', 'JVM参数', '类加载', '字节码'],
    'Spring核心': ['Spring', 'Spring IOC', 'Spring AOP', 'Spring事务', 'Bean生命周期', 'Spring核心'],
    'Spring Boot': ['Spring Boot', '自动配置', 'Starter'],
    'Spring Cloud': ['Spring Cloud', '服务注册发现', '配置中心', '网关', '熔断器', '负载均衡'],
    'MySQL': ['MySQL', '索引', 'SQL优化', '事务隔离', '事务', 'MVCC'],
    'Redis': ['Redis', '缓存', '数据结构', '持久化', '集群'],
    'NoSQL': ['NoSQL'],
    '消息队列': ['Kafka', 'RabbitMQ', 'RocketMQ', '消息队列', '消息队列应用'],
    '搜索引擎': ['Elasticsearch', '搜索', '搜索引擎', '搜索与推荐'],
    '分布式基础': ['分布式理论', 'CAP', 'BASE', '一致性', '一致性算法', '分布式锁', '分布式事务'],
    '微服务': ['微服务', '服务治理', '限流熔断', '链路追踪'],
    '容器化': ['Docker', 'Kubernetes', '容器', 'DevOps'],
    '网络': ['计算机网络', '网络基础', '网络安全'],
    '基础与系统': ['计算机基础', '操作系统', '算法', '日志'],
    '高并发系统': ['高并发系统设计'],
    '存储架构': ['存储架构设计'],
    '缓存架构': ['缓存架构设计'],
    '支付交易': ['支付与交易'],
    '社交IM': ['社交与IM'],
    '稳定性容灾': ['稳定性与容灾'],
    '架构演进': ['架构演进'],
    '安全风控': ['安全与风控'],
    '系统设计': ['系统设计'],
    // === AI 子分类 ===
    'Transformer': ['Transformer架构', '注意力机制', '位置编码', '归一化', '激活函数', '模型结构', '模型架构'],
    '训练与微调': ['训练与微调', '训练优化', 'LoRA与微调', '参数高效微调', '微调策略', 'SFT与RLHF', '对齐技术', '对齐训练', '训练理论', '分布式训练'],
    'LLM前沿': ['LLM前沿', 'DeepSeek-R1', '强化学习', 'Tokenizer', '多模态', 'Text2SQL', 'LLM推荐', '实验管理', 'LLM进阶'],
    'AI Agent核心': ['Agent基础概念', 'Agent核心框架', 'Agent架构', 'Agent稳定性', 'Agent评估', '工具调用', 'Function Calling', '工具使用', '记忆系统', 'Agent记忆', '规划与推理', '多智能体', '多智能体系统', '多Agent系统', 'Prompt工程', 'Prompt Engineering'],
    'RAG': ['RAG技术', 'RAG进阶', 'RAG与向量检索', '向量检索', '高级RAG'],
    'AI工程化': ['推理优化', '推理与部署', '生产工程化', '生产化部署', '模型服务', '模型部署', '部署架构', '工程化', '工程化实践', '工程实践', 'Agent工程化', 'Agent框架', 'LLM框架', 'RAG工程化', '向量数据库', '可观测性', '评估与安全', '评估', '评估指标', '评测与质量', 'Agent安全', '安全'],
    '大模型基础': ['大模型基础', '大模型架构', '大模型原理', '大模型综合', '大模型应用', '基础知识', '预训练模型', '表示学习', '长上下文'],
    'AI场景': ['RAG系统设计', 'AI Agent系统设计', 'AI对话系统设计', 'LLM推理与部署', 'AI安全与治理', 'AI评测与监控', '多模态AI系统', 'AI推荐与搜索', 'AI代码助手', 'AI特殊场景'],
    'FDE': ['FDE基础概念', 'FDE工作实践', 'AI解决方案设计', 'AI部署实施', '数据安全与合规'],
    '面试实战': ['企业面试问答', '手撕代码', 'AI编程', '文档处理'],
    // === JD 大厂子分类 ===
    'JD核心技术': ['Java 并发', 'Java 集合', 'HBase', 'ES', '分库分表', '供应链', '商品', '用户', '评价', '直播', '规则引擎', '特征工程', '风控系统', '数据隔离', '系统解耦', 'Agent 编排', '会话管理', '消息系统', '音视频任务', 'Prompt 工程', '内容审核', '模型路由', '埋点实验', 'IM 系统', '实时互动', '定时任务', '分布式调度', '文件存储', '对象存储', 'Workflow 引擎', 'MCP 协议', '知识库', 'API 服务', '成本控制', '医药 AI'],
    'JD架构设计': ['架构设计', '供应链架构', '交易架构', '多活容灾', '网关设计', '内容架构', '直播架构', 'Feed 流', '搜索架构', '中台架构', '风控架构设计', '特征平台设计', '决策引擎设计', '关系网络设计', '设备指纹设计', '安全架构', 'AI 陪伴架构', 'Agent 引擎架构', '记忆系统架构', '音视频平台架构', '消息社区架构', '长连接网关', '多租户 SaaS', '企业级 AI 平台架构', 'RAG 平台架构', '多模型路由架构', '医药数据治理'],
    'JD高可用': ['池化', '缓存', '扩容', '异步', '队列', '限流', '降级', '负载均衡', '隔离', '压测', '预案', '回滚', '灰度发布'],
    'JD AI Infra': ['Agent 改造', 'LLM 训练', 'LLM 推理', 'RAG 工程', '实验平台', '智能风控', 'LLM 风控', 'GraphRAG', 'FDE 解决方案', 'AI Harness', 'LLM 接入工程', 'Tool Calling', '多模型编排', '数字人', 'TTS ASR', '视频生成', 'AI Coding', 'Java 转 AI', '国际化', '数据合规', 'LLMOps', '医药知识图谱', 'B 端 Agent 交付', '企业级安全合规'],
  } as Record<string, string[]>,
  aboutText: '面试题库 2026 — 合并 AI / Java / 大厂 JD 三大方向，2700+ 道精选面试题。涵盖 LLM 核心、AI Agent、Java 并发/JVM/Spring、MySQL、Redis、Kafka、分布式系统、场景设计、蚂蚁风控、拼多多多业务线等。每题含费曼快学、第一性原理、结构化回答、视频脚本、苏格拉底式追问、遗忘曲线智能复习。',
} as const;

export const SUBCAT_REVERSE: Record<string, string> = {};
Object.entries(APP_CONFIG.subcatGroups).forEach(([g, subs]) => {
  subs.forEach((s) => {
    SUBCAT_REVERSE[s] = g;
  });
});

export function getSubcatGroup(sub: string | undefined): string {
  return (sub && SUBCAT_REVERSE[sub]) || '其他';
}

export const ALGO_LABELS: Record<Algorithm, string> = {
  sm2: 'SM-2 智能间隔',
  leitner: 'Leitner 卡盒',
  ebbinghaus: '艾宾浩斯曲线',
};
