#!/usr/bin/env python3
"""
费曼学习法 + 第一性原理 内容生成器 v2
改进：更好的本质提取、要点清洗、类比匹配优先级
"""

import json, os, re, glob

# ============================================================
# 领域类比库 — 按精确度排序（长的/具体的优先匹配）
# ============================================================
ANALOGY_DB = [
    # === Java 高优先级（具体术语优先）===
    ("concurrenthashmap", "ConcurrentHashMap 就像超市多个收银台——把数据分成多段（段锁/Node锁），不同收银台互不干扰，比单个收银台（HashTable）快多了。"),
    ("completablefuture", "CompletableFuture 就像智能快递——不仅追踪包裹，还能设定「到了通知我」（回调）、「两个都到了再合并」（组合）。"),
    ("countdownlatch", "CountDownLatch 就像会议签到——主持人等到所有人都签到了（count=0），才开始开会。"),
    ("threadlocal", "ThreadLocal 就像每个员工自己的笔记本——各自记各自的，互不干扰，不用抢公共白板。"),
    ("双亲委派", "双亲委派就像公司层级汇报——遇到问题先问直属领导（父加载器），领导搞不定再向上（祖父），最顶层拍板。"),
    ("threadpool", "线程池就像出租车队——核心线程是常驻车辆，队列是候车区，最大线程是高峰加车，拒绝策略是忙不过来时的处理。"),
    ("thread pool", "线程池就像出租车队——核心线程是常驻车辆，队列是候车区，最大线程是高峰加车，拒绝策略是忙不过来时的处理。"),
    ("countdown", "CountDownLatch 就像会议签到——主持人等到所有人都签到了（count=0），才开始开会。"),
    ("spring boot", "Spring Boot 就像精装公寓——基本配置都帮你搞好了（自动配置），拎包入住（开箱即用），不用自己装修。"),
    ("spring cloud", "Spring Cloud 就像连锁酒店的运营体系——统一管理各分店（微服务），包含订房（注册发现）、路由（网关）、监控（追踪）等全套方案。"),
    ("spring", "Spring 就像公司的 HR 部门——负责找人（依赖注入）、安排岗位（Bean管理）、处理跨部门事务（AOP），让各部门不用自己招人。"),
    ("hashmap", "HashMap 就像带编号的储物柜——钥匙做哈希算出柜子号，同一个柜子拉链（链表），太多就换大柜子（红黑树+扩容）。"),
    ("arraylist", "ArrayList 就像可伸缩的收纳盒——本质是数组，满了换个更大的（扩容1.5倍），随机取快但中间插入要挪位置。"),
    ("linkedlist", "LinkedList 就像火车车厢——每节知道前后是谁，插入/拆卸很快，但找第N节得从头数。"),
    ("treemap", "TreeMap 就像字典目录——按字母排序存储，找范围特别快，代价是每次插入要维护排序。"),
    ("volatile", "volatile 就像办公室的白板——写上去所有人立刻看见（可见性），但多个人同时改还是会乱（不保证原子性）。"),
    ("synchronized", "synchronized 就像会议室单人预约——同一时间只有一个线程能进入，其他人门口排队。"),
    ("aqs", "AQS 就像银行排队叫号——用一个状态变量管理排队，公平模式按先后，非公平谁快谁先。"),
    ("lock", "锁就像洗手间的门锁——进去的人锁门，用完解锁，外面的人排队等。"),
    ("cas", "CAS（比较并交换）就像抢红包——大家同时看到金额，只有第一个抢到的人成功，其他人重试。"),
    ("ioc", "IoC（控制反转）就像从「自己做饭」变成「叫外卖」——你不再自己 new 对象，而是告诉容器你需要什么，容器送来。"),
    ("aop", "AOP 就像公司的前台保安——不管哪个部门做什么，进门都要刷卡（切面），这种横切逻辑不用写进每个部门的代码。"),
    ("bean", "Bean 就像公司的正式员工——从招聘（实例化）→ 入职培训（属性填充）→ 上岗（初始化）→ 离职（销毁）。"),
    ("nio", "NIO 就像快递驿站——不再一人送一家（BIO阻塞），而是一人看多个快递柜（Selector+Channel），哪个到了处理哪个。"),
    ("gc", "GC 就像城市的环卫系统——定期清扫无引用对象，不同策略（CMS/G1/ZGC）就像不同的清扫频次和方式。"),
    ("jvm", "JVM 就像一台翻译官机器——把编译后的字节码逐行翻译成 CPU 能听懂的指令，还负责内存管理和垃圾回收。"),
    ("jpa", "JPA 就像 ORM 的标准接口规范——定义了 Java 对象和数据库表怎么映射，Hibernate 是它的实现。"),
    ("mybatis", "MyBatis 就像 SQL 翻译官——你写 SQL，它帮你填参数、转结果，省去手动 JDBC 的繁琐。"),
    ("redis", "Redis 就像办公桌上的便签纸——比去档案室（数据库）快得多，但桌面空间有限（内存），重要的还得抄到档案室。"),
    ("mysql", "MySQL 就像公司的档案室——按目录（索引）高效查找，支持多人同时查阅（事务），有严格的借还规则（锁）。"),
    ("kafka", "Kafka 就像电视台广播——节目发出后多台电视可同时收看，按频道分类，还能回放（持久化）。"),
    ("zookeeper", "ZooKeeper 就像公司的行政部——管理通讯录（注册）、选举领导、发通知（Watch）、管配置。"),
    ("dubbo", "Dubbo 就像远程电话系统——你调用本地方法一样调用远程服务，中间经过序列化→网络→反序列化。"),
    ("rpc", "RPC 就像打电话——拨号就能和远方的人通信，感觉像面对面，中间经过网络传输。"),
    ("cap", "CAP 定理就像不可能三角——一致性、可用性、分区容错，网络出问题时只能保两个。"),
    ("限流", "限流就像地铁早高峰进站限流——不管来多少人，每分钟只放固定数量进站，保护站内不崩。"),
    ("熔断", "熔断就像保险丝——电流过大自动跳闸保护电器，过一会自动恢复（半开探测）。"),
    ("降级", "降级就像餐厅忙不过来时暂停套餐——核心功能保住，非核心功能暂时关闭，保证系统不崩。"),
    ("微服务", "微服务就像把大餐厅拆成多个小档口——各自独立运营，通过统一点餐系统协调。"),
    ("分布式事务", "分布式事务就像跨国转账——多个银行系统要同时成功或同时失败，比单机事务复杂得多。"),
    ("分布式锁", "分布式锁就像多人在不同城市抢同一张票——需要中心化协调（Redis/ZK），确保只有一人抢到。"),
    ("分布式", "分布式系统就像连锁店——一家变多家，需要统一菜单（一致性）、协调库存（分布式事务）、处理网络问题。"),
    ("注册中心", "注册中心就像公司通讯录——每个服务上线登记地址，调用方查通讯录找对方。"),
    ("消息队列", "消息队列就像快递中转站——生产者扔包裹就走，消费者按自己节奏取，解耦时间依赖。"),
    ("索引", "数据库索引就像书的目录——没目录要逐页翻（全表扫描），有目录直接跳到对应页，但目录也占空间。"),
    ("事务隔离", "事务隔离就像办公室隔音等级——读未提交（透明玻璃）→ 读已提交（磨砂）→ 可重复读（单向镜）→ 串行化（独立房间）。"),
    ("mvcc", "MVCC 就像文档的版本历史——每个人看到自己时间点的快照版本，互不干扰，不用加锁就能并发读。"),
    ("事务", "事务就像网购的「七天无理由」——要么全部成功，要么全部回滚，不存在做到一半的状态。"),
    ("垃圾回收", "垃圾回收就像小区保洁——定期巡逻（标记）找出没人用的房间（不可达对象），打扫干净（回收），打扫时居民暂停活动。"),
    ("类加载", "类加载就像入职流程——找档案（加载）→ 检查资格（验证）→ 准备工位（准备）→ 解析岗位（解析）→ 正式入职（初始化）。"),
    ("内存泄漏", "内存泄漏就像借了书一直不还——书架越来越满，最终图书馆爆满。"),
    ("元空间", "元空间就像把仓库从公司大楼搬到外面（本地内存）——不受大楼面积（JVM堆）限制。"),
    ("内存模型", "JVM 内存模型就像一栋大楼——有公共区域（堆/方法区，共享）和私人办公室（栈/程序计数器，独享）。"),
    ("线程池", "线程池就像出租车队——核心线程是常驻车辆，队列是候车区，最大线程是高峰加车。"),
    ("线程", "线程就像公司里的员工——共享资源（堆），各有办公桌（栈），需要协调（同步）。"),
    ("future", "Future 就像快递单号——下单后先做别的，需要结果时再查，没到就等。"),
    ("并发", "并发编程就像十字路口交通管理——多辆车同时通过，需要红绿灯（锁）和规则（内存模型）避免碰撞。"),
    
    # === AI 高优先级 ===
    ("in-context", "In-context Learning 就像给人看几个范例就能上手——不用改大脑结构（参数），在对话中给几个例子就能模仿。"),
    ("function call", "Function Calling 就像 AI 学会了「打电话求助」——需要查天气、算数学时，能主动调用外部工具。"),
    ("chain of thought", "Chain of Thought 就像数学考试写解题过程——一步一步推导比直接写答案准确率高。"),
    ("chain-of-thought", "Chain of Thought 就像数学考试写解题过程——一步一步推导比直接写答案准确率高。"),
    ("rerank", "重排序就像面试二面——初筛（向量检索）找到一批人后，用更精细的标准重新排名。"),
    ("guardrail", "护栏就像 AI 的「安全带」——在输入输出环节设置检查，防止说出有害、越界的话。"),
    ("guardrails", "护栏就像 AI 的「安全带」——在输入输出环节设置检查，防止说出有害、越界的话。"),
    ("kv cache", "KV Cache 就像读书笔记——生成每个词时不用重读前面所有内容，直接查笔记就行。"),
    ("kv_cache", "KV Cache 就像读书笔记——生成每个词时不用重读前面所有内容，直接查笔记就行。"),
    ("lora", "LoRA 就像轻量级微调补丁——不修改原模型全部参数，只训练一个小补丁矩阵，效果接近全量微调但成本低几个数量级。"),
    ("rag", "RAG 就像开卷考试——不靠死记硬背（模型参数），而是先翻书（检索相关文档），再结合理解写答案（生成）。"),
    ("moe", "MoE（混合专家）就像医院分诊台——根据病症分给不同专家（专家网络），每次只激活相关专家。"),
    ("rlhf", "RLHF 就像给 AI 请人类老师——先让人类给 AI 回答打分排序，训练奖励模型，再用强化学习让 AI 越来越懂事。"),
    ("agent", "AI Agent 就像有自主行动能力的实习生——能理解任务、拆解步骤、使用工具、根据反馈调整。"),
    ("transformer", "Transformer 就像高效的读书小组——每个人（注意力头）同时读不同段落，然后交流关键信息，不像 RNN 逐字读。"),
    ("attention", "注意力机制就像在聚会上听人说话——自动聚焦到感兴趣的声音，给不同人不同关注度。"),
    ("embedding", "Embedding 就像把人放到性格地图上——相似的人位置近，不同的人距离远，机器就能算「相似度」。"),
    ("tokenizer", "Tokenizer 就像语言的分词剪刀——把文字切成模型能处理的最小单元。"),
    ("token", "Token 就像语言的基本积木——不完全是字也不完全是词，是模型认为最合理的切分单元。"),
    ("预训练", "预训练就像上大学通识课——先学广泛知识（海量文本），成为通才，再通过专业课（微调）成专家。"),
    ("微调", "微调就像给通才毕业生做岗前培训——已有基础能力，再针对具体岗位做训练。"),
    ("向量数据库", "向量数据库就像相似度搜索引擎——存语义坐标，查询找的不是精确匹配，而是意思最接近的。"),
    ("向量", "向量就像一串数字坐标——把文字/图片的语义编码成数学表示，让机器能计算相似度。"),
    ("prompt", "Prompt 就像给 AI 的工作指令——指令越清晰、上下文越充分，AI 完成质量越高。"),
    ("幻觉", "幻觉就像 AI 在一本正经地胡说八道——根据语言模式生成看似合理但实际错误的内容。"),
    ("hallucination", "幻觉就像 AI 在一本正经地胡说八道——根据语言模式生成看似合理但实际错误的内容。"),
    ("量化", "量化就像把高清图压缩成标清——参数从高精度（32位）变成低精度（8/4位），体积小速度快。"),
    ("quantization", "量化就像把高清图压缩成标清——参数从高精度（32位）变成低精度（8/4位），体积小速度快。"),
    ("langchain", "LangChain 就像 AI 应用的脚手架——帮你把 LLM、记忆、工具、检索像搭积木一样组合。"),
    ("多模态", "多模态就像一个人同时会看、听、摸——不同感官信息融合，对世界的理解比单一感官全面。"),
    ("multimodal", "多模态就像一个人同时会看、听、摸——不同感官信息融合，对世界的理解比单一感官全面。"),
    ("diffusion", "Diffusion 就像从噪点中雕刻图片——先撒满噪点再逐步去噪，慢慢浮现目标图像。"),
    ("benchmark", "Benchmark 就像 AI 的期末考试——用标准化题集测试模型能力，横向对比不同模型。"),
    ("inference", "推理就像模型在考试答题——训练是学习，推理是应用知识回答问题。"),
    ("batch", "Batch Size 就像大巴车座位数——太少跑得频繁效率低，太多转弯难（内存不够）。"),
    ("gradient", "梯度下降就像蒙眼下山——每步感受最陡方向（梯度），朝下坡走，直到谷底（最优解）。"),
    ("过拟合", "过拟合就像死记硬背的学生——训练题完美，新题就懵，因为记了答案不是理解了方法。"),
    ("overfitting", "过拟合就像死记硬背的学生——训练题完美，新题就懵。"),
    ("归一化", "归一化就像统一度量衡——把不同量级数据拉到同一尺度，让模型学得更稳定。"),
    ("normalization", "归一化就像统一度量衡——把不同量级数据拉到同一尺度。"),
    ("softmax", "Softmax 就像投票分配——把一组分数变成概率分布（总和=1），分最高的获最大概率。"),
    ("gpu", "GPU 就像万人施工队——CPU 是少数精英（核心少但强），GPU 是人海战术（核心多），并行计算特别强。"),
    ("llm", "大语言模型就像读过整个互联网的学者——通过预测「下一个词」生成文本，积累了海量语言模式和知识。"),
    ("记忆", "Agent 记忆就像人的记忆——短期记忆是当前对话（工作记忆），长期记忆是过去经验（向量存储）。"),
    ("memory", "Agent 记忆就像人的记忆——短期记忆是当前对话，长期记忆是过去经验。"),
    ("规划", "Agent 规划就像项目经理拆任务——把大目标分解成小步骤，安排顺序，遇问题重新调整。"),
    ("planning", "Agent 规划就像项目经理拆任务——大目标分解成小步骤，安排顺序。"),
    ("反思", "Agent 反思就像做完题后的自我检查——回顾推理过程和结果，发现错误就修正。"),
    ("reflection", "Agent 反思就像做完题后的自我检查——回顾推理过程，发现错误就修正。"),
    ("多agent", "多 Agent 协作就像一个团队——每个 Agent 扮演不同角色（PM、开发、测试），通过沟通协作。"),
    ("multi-agent", "多 Agent 协作就像一个团队——每个 Agent 扮演不同角色，通过沟通协作。"),
    ("工具", "工具调用就像给 AI 配了瑞士军刀——根据任务需要灵活选择搜索、计算等工具。"),
    ("tools", "工具调用就像给 AI 配了瑞士军刀——根据任务需要灵活选择搜索、计算等工具。"),
    ("对齐", "对齐就像给 AI 上品德课——让它不仅有能力，还要 helpful（有用）、honest（诚实）、harmless（无害）。"),
    ("alignment", "对齐就像给 AI 上品德课——不仅要有能力，还要 helpful、honest、harmless。"),
    ("serving", "模型部署就像开店营业——把训练好的模型放服务器上，接 API 接口，让用户实时调用。"),
    ("loss", "Loss 就像考试成绩和满分的差距——差距越大模型越差，训练就是不断缩小差距。"),
    ("分块", "分块就像把书拆成一页一页——整本太长不好检索，拆成小段后检索更精准。"),
    ("chunk", "分块就像把书拆成一页一页——拆成小段后检索更精准。"),
    ("fine-tune", "微调就像定制化培养——在通用能力基础上用特定数据继续训练。"),
    ("finetuning", "微调就像定制化培养——在通用能力基础上用特定数据继续训练。"),
    ("vision", "视觉理解就像教 AI 看图说话——把图片变成数字表示，像处理文字一样理解图片。"),
    ("cot", "Chain of Thought 就像写解题过程——一步一步推导比直接写答案准确率高。"),
    ("ai", "AI 就像教计算机像人一样思考和学习——通过数据和算法让机器具备感知、推理和决策能力。"),
]

GENERIC_ANALOGIES = [
    "想象你用一部新手机——不需要懂芯片原理（底层实现），只要知道怎么操作（接口）就能使用，坏了有售后（异常处理）。",
    "就像搭积木——每个零件有固定接口，按规则拼在一起就能搭出复杂系统，换零件不影响整体。",
    "好比学开车——不关心发动机怎么转（实现细节），掌握方向盘油门刹车（抽象接口）就能上路。",
    "就像一个组织良好的工具箱——每把工具有明确用途，用完放回原处，整个系统井井有条。",
]

def detect_topic(question, answer=""):
    """精确度优先的类比匹配"""
    text = (question + " " + answer[:200]).lower()
    
    best_match = None
    best_len = 0
    
    for keyword, analogy in ANALOGY_DB:
        kw_lower = keyword.lower()
        if kw_lower in text and len(kw_lower) > best_len:
            best_match = analogy
            best_len = len(kw_lower)
    
    if best_match:
        return best_match
    
    hash_val = hash(question) % len(GENERIC_ANALOGIES)
    return GENERIC_ANALOGIES[hash_val]

def clean_answer_noise(text):
    """清理答案中的页码、日期等噪音"""
    text = re.sub(r'\d{2}/\d{2}/\d{4}\s*', '', text)
    text = re.sub(r'Page \d+ of \d+\s*', '', text)
    text = re.sub(r'\\n', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_essence(question, answer=""):
    """从问题和答案中提取一句话本质"""
    q = question.strip().rstrip("?？!！")
    clean_ans = clean_answer_noise(answer)
    
    # 提取概念名
    concept = q
    for prefix in ['什么是', '什么叫', '解释一下', '简述', '简答', '请说明', '说明', '介绍一下', '谈谈对']:
        if q.startswith(prefix):
            concept = q[len(prefix):].rstrip("?？。.")
            break
    for suffix in ['是什么', '是什么意思', '是怎样的', '怎么理解', '如何理解']:
        if concept.endswith(suffix):
            concept = concept[:-len(suffix)]
            break
    
    concept = concept.strip()
    
    # 从答案前100字提取核心描述
    if clean_ans and len(clean_ans) > 20:
        # 取第一个有意义的句子
        first_sentence = re.split(r'[。\n]', clean_ans)[0][:80].strip()
        if len(first_sentence) > 15:
            return first_sentence
    
    return f"{concept}——见参考答案详解"

def extract_key_points(answer, question=""):
    """从答案中提取3个干净的要点"""
    if not answer:
        return ["理解核心定义和概念", "掌握工作原理和流程", "熟悉应用场景和注意事项"]
    
    clean = clean_answer_noise(answer)
    
    # 尝试按编号/段落提取
    # Pattern 1: "1. xxx 2. xxx 3. xxx"
    numbered = re.findall(r'(?:^|\n)\s*(?:\d+[\.\)、]|[-•●])\s*(.+?)(?=\n\s*(?:\d+[\.\)、]|[-•●])|$)', clean, re.DOTALL)
    if len(numbered) >= 2:
        points = []
        for n in numbered[:3]:
            p = n.strip()[:100]
            if len(p) > 10:
                points.append(p)
        if len(points) >= 2:
            while len(points) < 3:
                points.append("结合实践深入理解")
            return points[:3]
    
    # Pattern 2: 按句子分割
    sentences = re.split(r'[。\n；;]', clean)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    
    # 去重
    points = []
    seen_starts = set()
    for s in sentences:
        start = s[:25]
        if start not in seen_starts:
            seen_starts.add(start)
            points.append(s[:100])
        if len(points) >= 3:
            break
    
    if not points:
        points = ["理解核心定义", "掌握工作原理", "熟悉应用场景"]
    
    while len(points) < 3:
        points.append("结合实践深入理解")
    
    return points[:3]

def generate_feynman(question, answer="", category=""):
    analogy = detect_topic(question, answer)
    essence = extract_essence(question, answer)
    key_points = extract_key_points(answer, question)
    return {
        "essence": essence,
        "analogy": analogy,
        "key_points": key_points
    }

def generate_first_principle(question, answer="", category=""):
    q = question.strip()
    analogy = detect_topic(question, answer)
    
    # 根本问题
    concept = q.rstrip("?？").replace("什么是", "").replace("是什么", "").strip()
    
    if q.startswith(('如何', '怎么', '怎样')):
        problem = f"如果要解决这个问题，最本质的方法论是什么？先理解问题约束，再找最优路径。"
    elif q.startswith('为什么'):
        problem = f"追根溯源：{concept} 的根本原因是什么？背后的设计哲学是什么？"
    elif '区别' in q or '对比' in q or '差异' in q:
        problem = "它们本质上为什么不同？各自的设计目标和适用场景是什么？"
    elif '原理' in q:
        problem = f"剥离所有术语：{concept} 底层在做什么？为什么这样做是最优的？"
    elif '优' in q or '缺点' in q or '好处' in q:
        problem = f"从第一性原理看：{concept} 的根本优势/劣势来源于什么？"
    else:
        problem = f"为什么需要 {concept}？如果不存在它会怎样？它解决了什么根本问题？"
    
    # 根据类比来源判断领域
    is_java = any(kw in (question + answer[:300]).lower() for kw in ['java', 'jvm', 'spring', '线程', '锁', 'gc', 'HashMap', 'mysql', 'redis', 'kafka'])
    is_ai = any(kw in (question + answer[:300]).lower() for kw in ['transformer', 'attention', 'llm', 'agent', 'rag', 'embedding', 'model', 'training', 'fine-tune'])
    
    if is_java:
        axioms = [
            "计算资源（CPU、内存、IO）是有限的，必须在正确性和性能间权衡",
            "并发环境下，数据一致性和吞吐量天然存在 tension",
            "抽象和封装是管理复杂度的根本手段——隔离变化、隐藏细节",
        ]
        rebuild = "从零思考：① 这个问题如果不解决会怎样？② 最简方案是什么？③ 工业级方案如何权衡？④ 如果重新设计，你会做什么不同选择？"
    elif is_ai:
        axioms = [
            "模型本质是数学函数的参数优化——所有能力都来自数据和参数",
            "Scaling Law：模型能力与参数量、数据量、算力正相关",
            "质量 > 数量：数据质量决定模型上限，算法决定达到上限的效率",
        ]
        rebuild = "从数学本质出发：① 这个技术的数学基础是什么？② 为什么这个数学结构有效？③ 工程上如何高效实现？④ 资源约束下如何优化？"
    else:
        axioms = [
            "任何技术方案都是 trade-off——没有银弹",
            "复杂系统由简单组件组合涌现——理解了组件就理解了系统",
            "实践是检验真理的唯一标准——理论推导必须经过实验验证",
        ]
        rebuild = "回到根本：① 这个技术为什么存在？② 去掉它会怎样？③ 从零开始你会怎么设计？④ 你的方案和现有方案的根本区别是什么？"
    
    return {
        "problem": problem,
        "axioms": axioms,
        "rebuild": rebuild
    }

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    
    count = 0
    for q in questions:
        # 总是重新生成（v2覆盖v1）
        question_text = q.get('question', '')
        answer_text = q.get('answer', '')
        category = q.get('category', '')
        
        q['feynman'] = generate_feynman(question_text, answer_text, category)
        q['first_principle'] = generate_first_principle(question_text, answer_text, category)
        count += 1
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    
    return len(questions), count

def main():
    projects = [
        "/opt/data/projects/java-interview",
        "/opt/data/projects/ai-interview",
    ]
    
    grand_total = 0
    grand_processed = 0
    
    for project in projects:
        print(f"\n{'='*60}")
        print(f"Processing: {project}")
        print(f"{'='*60}")
        
        data_dir = os.path.join(project, "data")
        files = sorted(glob.glob(os.path.join(data_dir, "*.json")))
        
        project_total = 0
        project_processed = 0
        
        for filepath in files:
            fname = os.path.basename(filepath)
            total, processed = process_file(filepath)
            project_total += total
            project_processed += processed
            print(f"  {fname}: {total} questions, {processed} updated")
        
        print(f"\n  Project total: {project_total}, processed: {project_processed}")
        grand_total += project_total
        grand_processed += project_processed
    
    print(f"\n{'='*60}")
    print(f"GRAND TOTAL: {grand_total} questions, {grand_processed} updated")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
