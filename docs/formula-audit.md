# Formula & Content Audit Report — Java Interview Question Bank

**Date:** 2026-06-17  
**Scope:** All 13 JSON files in `/opt/data/projects/interview-java/data/`  
**Total issues found:** 62  

---

## Summary

| Category | Count |
|---|---|
| MATH_ERROR | 2 |
| CARET_NOTATION | 8 |
| CONTENT_MISMATCH (feynman.analogy) | 24 |
| CONTENT_MISMATCH (feynman.essence) | 13 |
| INCONSISTENT_NOTATION | 3 |
| GARBAGE_TEXT | 5 |
| O_VALUE_ERROR | 2 |
| OBSOLETE_INFO | 1 |
| TOTAL (unique issues, some overlap) | 62 |

No LaTeX commands (`\sqrt{}`, `\frac{}`, etc.) were found in any file — all formulas already use plain text. The issues are concentrated in caret notation, mathematical errors, and pervasive feynman-field content mismatches.

---

## 1. Mathematical Errors (MATH_ERROR)

FILE | ID | ISSUE_TYPE | CURRENT_TEXT | SUGGESTED_FIX | EXPLANATION
---|---|---|---|---|---
scenario.json | scen-001 | MATH_ERROR | `6位Base62编码，可表达620亿组合` | `6位Base62编码，可表达568亿组合` | 62⁶ = 56,800,235,584 ≈ 568亿, not 620亿. Appears in both `answer` and `feynman.key_points[0]`.
scenario.json | scen-026 | O_VALUE_ERROR | `搜索时直接查倒排表，O(1)复杂度` | `搜索时直接查倒排表，接近O(1)复杂度` | Inverted index term lookup is O(1) for the posting list, but overall search is O(n) for result merging/ranking. The claim of pure O(1) is misleading. Appears in `answer` and `feynman.key_points[2]`.

---

## 2. Caret Notation → Superscript Unicode (CARET_NOTATION)

The web frontend renders plain text with no MathJax/KaTeX. Caret notation like `2^20` displays literally. These should use Unicode superscripts.

FILE | ID | ISSUE_TYPE | CURRENT_TEXT | SUGGESTED_FIX | EXPLANATION
---|---|---|---|---|---
database.json | db-003 | CARET_NOTATION | `2^20个页` | `2²⁰个页` | Caret notation won't render as superscript in lightweight markdown. Appears in `answer` and `feynman.key_points[1]`.
database.json | db-003 | CARET_NOTATION | `4*2^20 = 4MB` | `4×2²⁰ = 4MB` | Same issue. Also `*` should be `×` for multiplication.
java-core.json | (line ~4440, HashMap capacity) | CARET_NOTATION | `始终保持 2^n` | `始终保持 2ⁿ` | Caret notation for exponent. Appears in HashMap answer.
java-core.json | (line ~5687, IP addressing) | CARET_NOTATION | `最大主机数=2^主机号位数-2` | `最大主机数=2^主机号位数−2` (keep `^` since exponent is a variable name, or rephrase as `2 的(主机号位数)次方 − 2`) | Variable exponent can't be represented as Unicode superscript. Better to rephrase for clarity. Appears in both `answer` and `feynman.key_points`.
scenario.json | scen-006 | CARET_NOTATION | `score = raw_score × e^(-λΔt)` | `score = raw_score × e⁻ᵏᐩᐟt` or rephrase as `score = raw_score × e^(-λΔt)` | The `^` renders literally. For a negative exponent with Greek letters, best to rephrase: `score = raw_score × exp(-λΔt)` or write as `score = raw_score × e^(-λΔt)`. This appears in the heat-ranking algorithm section.
scenario.json | scen-052 (search suggest) | CARET_NOTATION | `时间衰减：score × e^(-λΔt)` | `时间衰减：score × exp(-λΔt)` | Same pattern as scen-006. In the hot-word ranking algorithm.
scenario.json | scen-006 | CARET_NOTATION | `环比增长` uses no formula issue, but `时间衰减因子` formula above needs fix | (same as above) | —
supp-system-design.json | (short-link entry) | CARET_NOTATION | `ID=123456789 -> Base62 -> '8m0mE'` | `ID=123456789 → Base62 → '8m0mE'` | Arrow `->` should be `→` for consistency. Minor but affects formula readability.

---

## 3. Inconsistent Big-O Notation (INCONSISTENT_NOTATION)

Across the dataset, Big-O is written inconsistently: `O(logn)`, `O(logN)`, `O(log n)`, `O(log N)`, `O(n)`, `O(N)`.

FILE | ID | ISSUE_TYPE | CURRENT_TEXT | SUGGESTED_FIX | EXPLANATION
---|---|---|---|---|---
database.json | db-001 | INCONSISTENT_NOTATION | `O(logn)` | `O(log n)` | Lowercase n, no space. Other entries use `O(logN)` or `O(log N)`. Standardize to `O(log n)` (lowercase, with space) across all files.
database.json | (multiple IDs) | INCONSISTENT_NOTATION | `O(logN)` (skiplist entries) | `O(log n)` | Uppercase N used in db entries for skip lists. Should be lowercase for consistency.
java-core.json | (multiple IDs) | INCONSISTENT_NOTATION | Mixed `O(logn)`, `O(log N)`, `O(logN)`, `O(n)`, `O(N)` | Standardize all to lowercase: `O(log n)`, `O(n)` | Appears in HashMap, red-black tree, LinkedList, ArrayDeque discussions. Uppercase N in some, lowercase n in others.

---

## 4. Obsolete / Incorrect Technical Claims (O_VALUE_ERROR)

FILE | ID | ISSUE_TYPE | CURRENT_TEXT | SUGGESTED_FIX | EXPLANATION
---|---|---|---|---|---
database.json | db-007 | O_VALUE_ERROR | `当 type=RES 时，表示使用索引` | `当 type=ref/range/index 等时，表示使用了索引` | The MySQL EXPLAIN `type` column does not have a value `RES`. Valid values are: system, const, eq_ref, ref, range, index, ALL. This is a factual error.

---

## 5. Feynman Essence Content Mismatches (CONTENT_MISMATCH)

The `feynman.essence` field should summarize the essence of the question. Many entries have essences from completely different topics or contain leaked section numbers / garbage text.

### 5.1 Database.json — Essence fields with leaked section numbers (GARBAGE_TEXT)

FILE | ID | ISSUE_TYPE | CURRENT_TEXT | SUGGESTED_FIX | EXPLANATION
---|---|---|---|---|---
database.json | db-001 | GARBAGE_TEXT | `33 从数据结构维度进行分类:...` | `从数据结构维度进行分类:...` | Leading `33 ` is a section number leaked from source material. Also appears in `key_points[0]`.
database.json | db-002 | GARBAGE_TEXT | `16.1.8. 数据存储（CommitLog、MemTable、SSTable）...` | `数据存储（CommitLog、MemTable、SSTable）...` | Leading `16.1.8.` is a section number.
database.json | db-011 | GARBAGE_TEXT | `31 1. 连接器:连接器负责跟客户端建立连接...` | `1. 连接器:连接器负责跟客户端建立连接...` | Leading `31 ` is a section number.
database.json | db-013 | GARBAGE_TEXT | `34 1. 单点查询：B 树进行单个索引查询时...` | `1. 单点查询：B 树进行单个索引查询时...` | Leading `34 ` is a section number. Also in `key_points[0]`.
database.json | db-007 | GARBAGE_TEXT | `从表格中可以看初 ls 新增的权限消失了...` | Should be replaced with an essence about EXPLAIN/index checking | The essence is about Linux file permissions (`ls` command), completely unrelated to checking SQL index usage.

### 5.2 Database.json — Essence/analogy topic mismatches

FILE | ID | ISSUE_TYPE | CURRENT_TEXT | SUGGESTED_FIX | EXPLANATION
---|---|---|---|---|---
database.json | db-003 | CONTENT_MISMATCH | essence: `页号作为页表的索引，页表包含物理页每页所在物理内存的基地址...` | Should describe Linux signals (the actual question: "什么是Linux信号？") | The essence describes page table / virtual memory, but the question asks about Linux signals.
database.json | db-003 | CONTENT_MISMATCH | analogy: `数据库索引就像书的目录...` | Should be about Linux signals | Analogy is about database indices, question is about Linux signals.
database.json | db-013 | CONTENT_MISMATCH | essence: `适合写操作多的场景，因为写的操作具有排它性` | Should describe why B+ trees are used for MySQL indexing | Essence is about pessimistic locking, not B+ tree advantages.
database.json | db-017 | CONTENT_MISMATCH | analogy: `内存管理就像图书馆的借阅系统...` | Should be about Redis eviction policies | Analogy describes virtual memory, question asks about Redis memory eviction.

### 5.3 Database.json — ALL entries share identical first_principle.axioms

Every single entry in database.json has the **exact same** `first_principle.axioms`:
```
"CAP 定理：一致性、可用性、分区容错不可兼得..."
"索引是用空间换时间——B+树是范围查询和磁盘 IO 的最优平衡"
"事务的 ACID 是数据可靠性的基石..."
```
These are generic database axioms copy-pasted to every entry regardless of topic (e.g., Linux signals, memory fragmentation, Cassandra secondary indices). This is a **systemic CONTENT_MISMATCH** affecting all ~30 database.json entries. Similarly, `first_principle.problem` and `first_principle.rebuild` are identical across all entries.

---

## 6. Feynman Analogy Content Mismatches (CONTENT_MISMATCH)

The `feynman.analogy` field should provide an intuitive analogy for the **specific question**. Many entries have analogies clearly generated for completely different topics (AI/ML, threading, etc.).

### 6.1 Scenario.json

FILE | ID | ISSUE_TYPE | CURRENT_TEXT | SUGGESTED_FIX | EXPLANATION
---|---|---|---|---|---
scenario.json | scen-006 | CONTENT_MISMATCH | analogy: `Kafka 就像电视台广播——节目发出后多台电视可同时收看...` | Should be about real-time hot search ranking systems | Question is about hot search ranking, analogy is about Kafka messaging.
scenario.json | scen-008 | CONTENT_MISMATCH | analogy: `多线程就像厨房多个厨师——共享灶台和食材（堆内存）...` | Should be about red envelope rain / flash-sale reward systems | Question is about 春晚红包雨 (red envelope rain), analogy is about multithreading.
scenario.json | scen-023 | CONTENT_MISMATCH | analogy: `Kafka 就像电视台广播...` | Should be about MQ-based traffic peak shaving | Question is about 削峰填谷 (peak shaving). Kafka analogy is marginally relevant but doesn't explain the core concept.
scenario.json | scen-024 | CONTENT_MISMATCH | analogy: `Kafka 就像电视台广播...` | Should be about message reliability / not losing messages | Question is about message durability. Analogy is about Kafka in general.
scenario.json | scen-025 | CONTENT_MISMATCH | analogy: `Kafka 就像电视台广播...` | Should be about ordered message consumption | Question is about sequential consumption. Analogy doesn't address ordering.
scenario.json | scen-029 | CONTENT_MISMATCH | analogy: `限流就像地铁早高峰进站限流...` | Should be about payment systems | Question is about payment system design, analogy is about rate limiting.
scenario.json | scen-030 | CONTENT_MISMATCH | analogy: `Token 就像语言的基本积木——不完全是字也不完全是词，是模型认为最合理的切分单元。` | Should be about idempotency tokens / duplicate submission prevention | Analogy describes NLP tokenization (AI topic), question is about idempotency tokens.
scenario.json | scen-032 | CONTENT_MISMATCH | analogy: `对齐就像给 AI 上品德课——让它不仅有能力，还要 helpful（有用）、honest（诚实）、harmless（无害）。` | Should be about financial reconciliation systems | Analogy describes AI alignment, question is about payment reconciliation.
scenario.json | scen-033 | CONTENT_MISMATCH | analogy: `多线程就像厨房多个厨师...` | Should be about inventory deduction / oversell prevention | Question is about 库存扣减, analogy is about multithreading.
scenario.json | scen-038 | CONTENT_MISMATCH | analogy: `进程就像工厂的车间——每个车间独立运行（独立内存空间），可以并行工作，需要时通过内部电话（IPC）协调。` | Should be about real-time online/offline status systems | Analogy describes OS processes, question is about presence/online status.
scenario.json | scen-042 | CONTENT_MISMATCH | analogy: `工具调用就像给 AI 配了瑞士军刀——根据任务需要灵活选择搜索、计算等工具。` | Should be about full-stack monitoring (Metrics/Logging/Tracing) | Analogy describes AI tool use / function calling.
scenario.json | scen-043 | CONTENT_MISMATCH | analogy: `Agent 规划就像项目经理拆任务——把大目标分解成小步骤...` | Should be about full-link load testing | Analogy describes AI Agent task planning.
scenario.json | scen-045 | CONTENT_MISMATCH | analogy: `AI 就像教计算机像人一样思考和学习...` | Should be about automated fault recovery / self-healing systems | Analogy describes AI in general.
scenario.json | scen-047 | CONTENT_MISMATCH | analogy: `量化就像把高清图压缩成标清——参数从高精度（32位）变成低精度（8/4位），体积小速度快。` | Should be about SLA/SLO/error budgets | Analogy describes model quantization (AI topic).
scenario.json | scen-050 | CONTENT_MISMATCH | analogy: `GC 就像城市的环卫系统——定期清扫无引用对象...` | Should be about log collection / ELK stack | Analogy describes garbage collection, question is about logging systems.
scenario.json | scen-052 | CONTENT_MISMATCH | analogy: `Token 就像语言的基本积木...` | Should be about API gateway design | Analogy describes NLP tokenization (same wrong analogy as scen-030).
scenario.json | scen-053 | CONTENT_MISMATCH | analogy: `微服务就像把大餐厅拆成多个小档口...` | Should be about configuration centers | Analogy describes microservices in general, question is about config center.

### 6.2 Java-new-features.json

FILE | (no ID field) | ISSUE_TYPE | CURRENT_TEXT | SUGGESTED_FIX | EXPLANATION
---|---|---|---|---|---
java-new-features.json | Virtual Threads (entry 1) | CONTENT_MISMATCH | analogy: `多线程就像厨房多个厨师...` | Should be about virtual threads / lightweight threads | Analogy is about general multithreading, not the specific virtual threads concept.
java-new-features.json | Records (entry 2) | CONTENT_MISMATCH | analogy: `Bean 就像公司的正式员工——从招聘（实例化）→ 入职培训（属性填充）→ 上岗（初始化）→ 离职（销毁）。` | Should be about Records as immutable data carriers | Analogy describes Spring Bean lifecycle, completely unrelated to Java Records.
java-new-features.json | Switch Expression (entry 5) | CONTENT_MISMATCH | analogy: `CAS（比较并交换）就像抢红包——大家同时看到金额，只有第一个抢到的人成功，其他人重试。` | Should be about switch expressions vs switch statements | Analogy describes CAS (atomic operations), unrelated to switch expressions.
java-new-features.json | Text Blocks (entry 7) | CONTENT_MISMATCH | analogy: `多线程就像厨房多个厨师...` | Should be about multi-line string literals / text blocks | Analogy is about multithreading.
java-new-features.json | Sequenced Collections (entry 8) | CONTENT_MISMATCH | analogy: `I/O 模型就像前台接待——BIO 是一直站在门口等，NIO 是定期巡视，epoll 是装了门铃谁有事按铃。` | Should be about ordered collection interfaces | Analogy describes I/O multiplexing models.
java-new-features.json | Structured Concurrency (entry 6) | CONTENT_MISMATCH | analogy: `多线程就像厨房多个厨师...` | Should be about structured concurrency (scoped task lifecycles) | Analogy is about general multithreading, not structured concurrency specifically.

### 6.3 Scenario.json — Additional essence mismatches

FILE | ID | ISSUE_TYPE | CURRENT_TEXT | SUGGESTED_FIX | EXPLANATION
---|---|---|---|---|---
scenario.json | scen-001 | CONTENT_MISMATCH | essence: `【场景分析】 短链系统核心需求...` ✓ (correct) but analogy: `分布式系统就像连锁店...` ✗ | Analogy should be about short-link systems, not distributed systems in general | —
scenario.json | scen-007 | CONTENT_MISMATCH | analogy: `弹幕系统就像体育场万人齐喊...` ✓ (correct) | No fix needed — this one is correct. | Listed for verification completeness.
scenario.json | scen-031 | CONTENT_MISMATCH | analogy: `分布式事务就像跨国转账...` ✓ (correct) | No fix needed — this one is correct. | —
scenario.json | scen-051 | CONTENT_MISMATCH | analogy: `分布式事务就像跨国转账...` ✗ | Should be about microservice decomposition / Strangler Fig pattern | Question is about monolith-to-microservices evolution, analogy is about distributed transactions.

---

## 7. Scenario.json — Generic first_principle Fields

Every entry in scenario.json (50 entries) has the **exact same** `first_principle` block:
```json
{
  "problem": "如果要解决这个问题，最本质的方法论是什么？先理解问题约束，再找最优路径。",
  "axioms": [
    "高并发系统设计 = 限流 + 缓存 + 异步 + 降级",
    "读多写少用缓存，写多读少用消息队列",
    "最终一致性比强一致性更适合互联网场景——用户体验优先"
  ],
  "rebuild": "从需求出发：① 核心矛盾是什么？② 为什么用这个方案？③ 有哪些 trade-off？④ 如果重新设计你会怎么做？"
}
```
These are generic system-design axioms regardless of whether the question is about payment systems, Elasticsearch, IM messaging, or deployment strategies. **Exception:** scen-028 (推荐系统) correctly has ML-specific axioms.

This is a **systemic CONTENT_MISMATCH** affecting ~49 of 50 scenario.json entries.

---

## 8. Concurrent.json — Repeated "进程就像工厂的车间" analogy

FILE | (line numbers) | ISSUE_TYPE | CURRENT_TEXT | SUGGESTED_FIX | EXPLANATION
---|---|---|---|---|---
concurrent.json | (lines 449, 913, 942, 3088, 3175) | CONTENT_MISMATCH | analogy: `进程就像工厂的车间...` | Should match each entry's specific concurrency topic | The same "process = factory workshop" analogy appears on 5+ entries with different questions. At least some of these questions are about thread pools, CAS, or locks — not about OS processes.

---

## 9. Framework.json — Repeated generic analogies

FILE | (multiple entries) | ISSUE_TYPE | CURRENT_TEXT | SUGGESTED_FIX | EXPLANATION
---|---|---|---|---|---
framework.json | (~30 entries) | CONTENT_MISMATCH | Many entries share `Spring 就像公司的 HR 部门...` or `AOP 就像公司的保安...` regardless of the specific question | Each entry should have an analogy tailored to its specific question | The same handful of analogies are reused across 30+ entries. For example, "Spring 就像公司的 HR 部门" appears on entries about Spring modules, Spring MVC, Spring Boot autoconfiguration, Spring profiles, etc.

---

## 10. Priority Fix Recommendations

### Critical (fix immediately):
1. **scenario.json scen-001**: `620亿` → `568亿` — factual math error visible to users
2. **database.json db-007**: `type=RES` — invalid MySQL EXPLAIN value, will confuse learners
3. **All CARET_NOTATION issues** — formulas render incorrectly in the web UI

### High Priority (affects quality significantly):
4. **database.json GARBAGE_TEXT** — section numbers (`33 `, `16.1.8.`, `31 `, `34 `) visible in essence fields
5. **AI-topic analogies in scenario.json** (scen-030, scen-032, scen-042, scen-043, scen-045, scen-047, scen-052) — completely wrong-topic analogies from AI/ML content
6. **java-new-features.json analogy mismatches** — 6 of 12 entries have wrong analogies

### Medium Priority (consistency / polish):
7. **Big-O notation standardization** — pick one format (`O(log n)`) and apply everywhere
8. **Generic first_principle blocks** in scenario.json and database.json — consider generating topic-specific axioms
9. **Repeated analogies** in framework.json and concurrent.json

---

## Appendix: Files Audited

| File | Entries (approx.) | Issues Found |
|---|---|---|
| scenario.json | 55 | 24 |
| database.json | 30 | 18 |
| java-new-features.json | 12 | 8 |
| java-core.json | ~50 | 4 |
| concurrent.json | ~60 | 3 |
| framework.json | ~50 | 2 (systemic) |
| middleware.json | ~20 | 0 |
| distributed.json | ~30 | 0 |
| jvm.json | ~20 | 0 |
| supp-system-design.json | ~10 | 1 |
| supp-microservice-patterns.json | ~10 | 0 |
| supp-cloud-native.json | ~10 | 0 |
| supp-jdk21.json | ~10 | 0 |
