#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为 interview-2026 项目三个分类批量生成核心知识点 SVG 静态精绘图。

分类：
  - questions/java-core/      （约 356 个；已存在 6 个 SVG，默认跳过）
  - questions/eng-practice/   （约 118 个）
  - questions/java-architect/ （约 199 个）

工作机制：
  - 复用 scripts/gen_javacore_svgs.py 中已经精心设计的 50+ 主题模板与
    关键词路由器（select_template / tpl_*）
  - 为 eng-practice / java-architect 增设补充模板（tpl_*）以覆盖
    RAG / Agent / 限流 / 多租户 / 中台 / 网关 / 容灾 等新主题
  - 路由命中失败时走 tpl_flow_vertical / tpl_layers / tpl_compare / 通用兜底
  - 默认跳过已存在的 SVG（--force 才覆盖）
  - 同时在 md 文件的 `## 记忆要点` 前插入/替换 `## 核心知识点图` 段

用法：
  python3 scripts/gen_interview_svgs.py                   # 处理全部 3 类，跳过已存在
  python3 scripts/gen_interview_svgs.py --force           # 覆盖全部（包括已存在）
  python3 scripts/gen_interview_svgs.py --category eng-practice
  python3 scripts/gen_interview_svgs.py --skip-existing-md  # 不动 md
"""
import argparse
import os
import re
import sys
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / 'scripts'
IMG_DIR = ROOT / 'public' / 'images'

# 复用 gen_javacore_svgs.py 模块
spec = importlib.util.spec_from_file_location(
    'gen_javacore_svgs', SCRIPTS_DIR / 'gen_javacore_svgs.py')
jc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jc)

# 从 gen_javacore_svgs 复用：颜色、模板、工具函数
GREEN, ORANGE, PURPLE, RED, BLUE, GRAY = jc.GREEN, jc.ORANGE, jc.PURPLE, jc.RED, jc.BLUE, jc.GRAY
PALETTE = jc.PALETTE
ARROW_DEFS = jc.ARROW_DEFS
svg_header, svg_footer = jc.svg_header, jc.svg_footer
box, diamond, arrow, section_label, legend = jc.box, jc.diamond, jc.arrow, jc.section_label, jc.legend
wrap_text, esc = jc.wrap_text, jc.esc

# 所有主题模板（dict: name -> fn）
JCM = {
    'flow_vertical': jc.tpl_flow_vertical,
    'layers': jc.tpl_layers,
    'compare': jc.tpl_compare,
    'mindmap': jc.tpl_mindmap,
    'pipeline': jc.tpl_pipeline,
    'two_phase': jc.tpl_two_phase,
    'decision_tree': jc.tpl_decision_tree,
    'jvm_memory': jc.tpl_jvm_memory,
    'gc_flow': jc.tpl_gc_flow,
    'thread_states': jc.tpl_thread_states,
    'thread_pool': jc.tpl_thread_pool,
    'hashmap': jc.tpl_hashmap,
    'three_way_handshake': jc.tpl_three_way_handshake,
    'four_wave': jc.tpl_four_wave,
    'https': jc.tpl_https,
    'concurrence': jc.tpl_concurrence,
    'lock': jc.tpl_lock,
    'synchronized': jc.tpl_synchronized,
    'aqs': jc.tpl_aqs,
    'volatile': jc.tpl_volatile,
    'spring_ioc': jc.tpl_spring_ioc,
    'spring_aop': jc.tpl_spring_aop,
    'spring_bean': jc.tpl_spring_bean,
    'spring_boot': jc.tpl_spring_boot,
    'transaction': jc.tpl_transaction,
    'mybatis': jc.tpl_mybatis,
    'redis_data_structure': jc.tpl_redis_data_structure,
    'cache_pattern': jc.tpl_cache_pattern,
    'mq': jc.tpl_mq,
    'design_pattern': jc.tpl_design_pattern,
    'singleton': jc.tpl_singleton,
    'io_model': jc.tpl_io_model,
    'class_loader': jc.tpl_class_loader,
    'concurrence_map': jc.tpl_concurrence_map,
    'jvm_class_exec': jc.tpl_jvm_class_exec,
    'cas': jc.tpl_cas,
    'threadlocal': jc.tpl_threadlocal,
    'generic': jc.tpl_generic,
    'reflection': jc.tpl_reflection,
    'exception': jc.tpl_exception,
    'string_pool': jc.tpl_string_pool,
    'annotation': jc.tpl_annotation,
    'lambda': jc.tpl_lambda,
    'stream': jc.tpl_stream,
    'sql_index': jc.tpl_sql_index,
    'lock_deadlock': jc.tpl_lock_deadlock,
    'tomcat': jc.tpl_tomcat,
    'dubbo': jc.tpl_dubbo,
    'distributed_lock': jc.tpl_distributed_lock,
    'design_principle': jc.tpl_design_principle,
    'proxy_pattern': jc.tpl_proxy_pattern,
    'factory_pattern': jc.tpl_factory_pattern,
    'observer_pattern': jc.tpl_observer_pattern,
    'strategy_pattern': jc.tpl_strategy_pattern,
    'oop': jc.tpl_oop,
    'collection_hierarchy': jc.tpl_collection_hierarchy,
    'docker_k8s': jc.tpl_docker_k8s,
    'consistency': jc.tpl_consistency,
    'microservice': jc.tpl_microservice,
    'garbage_collector': jc.tpl_garbage_collector,
}


# ============================================================
# 补充模板：覆盖 eng-practice / java-architect 的新主题
# ============================================================

def tpl_rag(title, essence, body_top=110):
    """RAG 检索增强生成。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    stages = [
        ('用户提问', GREEN, 60),
        ('Query 改写\n/ 向量化', BLUE, 200),
        ('向量库召回\n(Top-K)', ORANGE, 340),
        ('Rerank\n精排', PURPLE, 480),
        ('Prompt 拼接\nContext', RED, 620),
    ]
    for i, (n, c, x) in enumerate(stages):
        parts.append(box(x, body_top + 20, 130, 70, n, fill=c + '22', stroke=c, font_size=12))
        if i > 0:
            parts.append(arrow(x - 10, body_top + 55, x, body_top + 55))
    parts.append(box(340, body_top + 130, 130, 60, 'LLM 生成\n(引用回答)', fill=BLUE, stroke=ORANGE,
                     text_color='#FFFFFF', font_size=13))
    parts.append(arrow(690, body_top + 90, 470, body_top + 130, color=BLUE))
    # 优化要点
    parts.append(f'<rect x="50" y="{body_top + 220}" width="700" height="200" rx="8" '
                 f'fill="#FFFFFF" stroke="{PURPLE}" stroke-width="1.5"/>')
    parts.append(f'<text x="70" y="{body_top + 244}" font-size="13" fill="{PURPLE}" font-weight="700">核心优化点</text>')
    items = [
        ('Chunking 切片', '语义切块 256-512 token', GREEN),
        ('Embedding', 'bge/m3e 多语言向量', BLUE),
        ('Vector DB', 'Milvus/Qdrant/PgVector', ORANGE),
        ('Hybrid Search', '向量+BM25 关键词融合', PURPLE),
        ('Rerank', 'bge-reranker 精排 Top-K', RED),
        ('上下文压缩', 'LongLLMLingua 压缩', GRAY),
    ]
    for i, (n, d, c) in enumerate(items):
        col = i % 3
        row = i // 3
        x = 70 + col * 230
        y = body_top + 270 + row * 64
        parts.append(f'<rect x="{x}" y="{y - 18}" width="220" height="56" rx="6" '
                     f'fill="{c}22" stroke="{c}" stroke-width="1.5"/>')
        parts.append(f'<text x="{x + 12}" y="{y}" font-size="12" fill="{c}" font-weight="700">{esc(n)}</text>')
        parts.append(f'<text x="{x + 12}" y="{y + 20}" font-size="11" fill="#37474F">{esc(d)}</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)


def tpl_agent(title, essence, body_top=110):
    """Agent 工程架构。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    # LLM 核心
    parts.append(box(310, body_top + 20, 180, 60, 'LLM 大模型\n(推理核心)', fill=BLUE, stroke=ORANGE,
                     text_color='#FFFFFF', font_size=14))
    # 三个能力
    caps = [
        ('规划 Planning', '拆解任务 / ReAct', GREEN, 50),
        ('记忆 Memory', '短期对话 + 长期向量', ORANGE, 280),
        ('工具 Tools', '函数调用 API', PURPLE, 510),
    ]
    for n, d, c, x in caps:
        parts.append(box(x, body_top + 130, 180, 60, f'{n}\n{d}', fill=c + '22', stroke=c, font_size=12))
        parts.append(arrow(x + 90, body_top + 130, 400, body_top + 80, color=c))
    # 工作流
    flow = ['感知输入', '意图理解', '规划拆解', '调用工具', '观察反馈', '生成响应']
    for i, n in enumerate(flow):
        x = 60 + i * 115
        parts.append(box(x, body_top + 230, 105, 50, n, fill=PALETTE[i % 6] + '22',
                         stroke=PALETTE[i % 6], font_size=11))
        if i > 0:
            parts.append(arrow(x - 10, body_top + 255, x, body_top + 255, color=GRAY))
    # 关键模式
    parts.append(f'<rect x="60" y="{body_top + 310}" width="680" height="120" rx="8" '
                 f'fill="#FFFFFF" stroke="{GRAY}" stroke-width="1.5"/>')
    parts.append(f'<text x="80" y="{body_top + 334}" font-size="13" fill="{GRAY}" font-weight="700">关键架构模式</text>')
    modes = [
        ('ReAct', '思考-行动循环', GREEN),
        ('Plan-Execute', '先规划后执行', BLUE),
        ('Multi-Agent', '协作分工', ORANGE),
        ('Reflection', '自我反思修正', PURPLE),
    ]
    for i, (n, d, c) in enumerate(modes):
        x = 80 + i * 170
        parts.append(f'<rect x="{x}" y="{body_top + 350}" width="160" height="60" rx="6" '
                     f'fill="{c}22" stroke="{c}" stroke-width="1.5"/>')
        parts.append(f'<text x="{x + 80}" y="{body_top + 375}" font-size="13" fill="{c}" '
                     f'text-anchor="middle" font-weight="700">{esc(n)}</text>')
        parts.append(f'<text x="{x + 80}" y="{body_top + 395}" font-size="11" fill="#546E7A" '
                     f'text-anchor="middle">{esc(d)}</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)


def tpl_multi_tenant(title, essence, body_top=110):
    """多租户隔离。"""
    return tpl_compare(title, essence, [
        ('独立数据库\nDB-per-Tenant', ['隔离最强', '成本最高', '大客户/金融', '独立 DB 实例', '合规友好']),
        ('独立 Schema\nSchema-per-Tenant', ['中间态', '同 DB 不同 Schema', '中等隔离', '中等成本', '中型客户']),
        ('共享 Schema\nShared-DB + tenant_id', ['成本最低', 'WHERE tenant_id=?', '逻辑隔离', '小客户', '邻居噪音风险']),
    ], body_top=body_top)


def tpl_rate_limit(title, essence, body_top=110):
    """限流算法对比。"""
    return tpl_compare(title, essence, [
        ('计数器\nCounter', ['固定窗口', '简单', '临界点双倍流量', '粗糙']),
        ('滑动窗口\nSliding Window', ['细分子窗口', '解决临界问题', '内存中等', 'Sentinel 默认']),
        ('漏桶\nLeaky Bucket', ['匀速流出', '恒定速率', '突发流量堆积', '保护下游']),
        ('令牌桶\nToken Bucket', ['匀速发令牌', '允许突发', 'Guava/Sentinel', '主流方案']),
    ], body_top=body_top)


def tpl_gateway(title, essence, body_top=110):
    """API 网关架构。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    # 客户端
    parts.append(box(50, body_top + 60, 110, 60, '客户端\nWeb/App', fill=GREEN + '22', stroke=GREEN, font_size=12))
    parts.append(arrow(160, body_top + 90, 220, body_top + 90))
    # 网关
    parts.append(box(220, body_top + 30, 360, 90, 'API Gateway\n(Spring Cloud Gateway / Kong / Nginx)',
                     fill=BLUE, stroke=ORANGE, text_color='#FFFFFF', font_size=14))
    # 网关功能（6 项）
    funcs = [
        ('路由 Routing', 'path/host 转发', GREEN, 50, body_top + 150),
        ('认证 Auth', 'JWT/OAuth2', BLUE, 220, body_top + 150),
        ('限流 RateLimit', '令牌桶', ORANGE, 390, body_top + 150),
        ('熔断 Circuit', 'Sentinel', RED, 560, body_top + 150),
        ('日志监控', 'access log', PURPLE, 50, body_top + 220),
        ('协议转换', 'HTTP→RPC', GRAY, 220, body_top + 220),
        ('灰度发布', 'Header 路由', GREEN, 390, body_top + 220),
        ('负载均衡', 'Ribbon/LB', BLUE, 560, body_top + 220),
    ]
    for n, d, c, x, y in funcs:
        parts.append(box(x, y, 160, 50, f'{n}\n{d}', fill=c + '22', stroke=c, font_size=10))
    # 后端服务
    for i, (n, c) in enumerate([('用户服务', ORANGE), ('订单服务', PURPLE), ('商品服务', RED)]):
        x = 240 + i * 130
        parts.append(box(x, body_top + 300, 110, 50, n, fill=c + '22', stroke=c, font_size=12))
        parts.append(arrow(400, body_top + 120, x + 55, body_top + 300, color=c, dashed=True))
    # 要点
    parts.append(f'<text x="400" y="{body_top + 390}" font-size="12" fill="{GRAY}" text-anchor="middle">'
                 f'同步网关：Spring Cloud Gateway (Reactor)  |  异步网关：Kong (OpenResty/Lua)</text>')
    parts.append(f'<text x="400" y="{body_top + 412}" font-size="12" fill="{GRAY}" text-anchor="middle">'
                 f'核心价值：统一入口 / 解耦 / 横切关注点收敛</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)


def tpl_multi_dc(title, essence, body_top=110):
    """多活容灾架构。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    # 路由层
    parts.append(box(290, body_top + 10, 220, 50, '全局 DNS / 智能路由\n(GTM + HTTP-DNS)',
                     fill=BLUE + '22', stroke=BLUE, font_size=13))
    # 双机房
    for i, (n, c, x) in enumerate([('机房 A (北京主)', GREEN, 60), ('机房 B (上海备)', ORANGE, 460)]):
        parts.append(f'<rect x="{x}" y="{body_top + 90}" width="280" height="240" rx="10" '
                     f'fill="{c}11" stroke="{c}" stroke-width="2"/>')
        parts.append(f'<text x="{x + 140}" y="{body_top + 116}" font-size="14" fill="{c}" '
                     f'text-anchor="middle" font-weight="700">{esc(n)}</text>')
        # 内部组件
        items = ['接入层 Nginx', '应用集群', 'DB 主/从', 'Redis Cluster', 'MQ']
        for j, it in enumerate(items):
            parts.append(box(x + 30, body_top + 138 + j * 38, 220, 30, it,
                             fill='#FFFFFF', stroke=c, font_size=11))
    # 双向同步
    parts.append(arrow(340, body_top + 200, 460, body_top + 200, color=RED, label='数据同步'))
    parts.append(arrow(460, body_top + 220, 340, body_top + 220, color=RED, label='双向'))
    # 容灾策略
    parts.append(f'<rect x="60" y="{body_top + 350}" width="680" height="100" rx="8" '
                 f'fill="#FFFFFF" stroke="{PURPLE}" stroke-width="1.5"/>')
    parts.append(f'<text x="80" y="{body_top + 374}" font-size="13" fill="{PURPLE}" font-weight="700">容灾策略对比</text>')
    modes = [
        ('主备', '冷备切换', GREEN),
        ('双活', '同强一致', BLUE),
        ('两地三中心', '主流方案', ORANGE),
        ('异地多活', '按用户分片', PURPLE),
    ]
    for i, (n, d, c) in enumerate(modes):
        x = 80 + i * 170
        parts.append(f'<rect x="{x}" y="{body_top + 388}" width="160" height="48" rx="6" '
                     f'fill="{c}22" stroke="{c}" stroke-width="1.5"/>')
        parts.append(f'<text x="{x + 80}" y="{body_top + 410}" font-size="12" fill="{c}" '
                     f'text-anchor="middle" font-weight="700">{esc(n)}</text>')
        parts.append(f'<text x="{x + 80}" y="{body_top + 428}" font-size="10" fill="#546E7A" '
                     f'text-anchor="middle">{esc(d)}</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)


def tpl_observability(title, essence, body_top=110):
    """可观测性三大支柱。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    # 三大支柱
    pillars = [
        ('Metrics 指标', '数值聚合\nQPS/RT/错误率', 'Prometheus\n+ Grafana', GREEN, 60),
        ('Logging 日志', '离散事件\n请求/异常明细', 'ELK\n(ES+Logstash)', BLUE, 290),
        ('Tracing 链路', '跨服务追踪\nTraceID 串联', 'SkyWalking\n+ Zipkin', ORANGE, 520),
    ]
    for n, d, tool, c, x in pillars:
        parts.append(f'<rect x="{x}" y="{body_top + 20}" width="220" height="160" rx="10" '
                     f'fill="{c}11" stroke="{c}" stroke-width="2"/>')
        parts.append(f'<text x="{x + 110}" y="{body_top + 48}" font-size="15" fill="{c}" '
                     f'text-anchor="middle" font-weight="700">{esc(n)}</text>')
        for j, ln in enumerate(wrap_text(d, 18)):
            parts.append(f'<text x="{x + 110}" y="{body_top + 88 + j * 16}" font-size="12" '
                         f'fill="#37474F" text-anchor="middle">{esc(ln)}</text>')
        parts.append(f'<rect x="{x + 20}" y="{body_top + 130}" width="180" height="40" rx="6" '
                     f'fill="{c}22" stroke="{c}"/>')
        parts.append(f'<text x="{x + 110}" y="{body_top + 155}" font-size="12" fill="{c}" '
                     f'text-anchor="middle" font-weight="600">{esc(tool)}</text>')
    # 底部要点
    parts.append(f'<rect x="60" y="{body_top + 210}" width="680" height="220" rx="10" '
                 f'fill="#FFFFFF" stroke="{PURPLE}" stroke-width="1.5"/>')
    parts.append(f'<text x="400" y="{body_top + 234}" font-size="14" fill="{PURPLE}" '
                 f'text-anchor="middle" font-weight="700">协同使用：Metrics 报警 → Tracing 定位 → Logging 查因</text>')
    points = [
        ('黄金指标', '延迟 / 流量 / 错误 / 饱和度（USE/RED 法则）', GREEN),
        ('TraceID 注入', '跨服务透传，串联一次完整请求', BLUE),
        ('采样率', 'Tracing 1%-10% 采样，避免存储爆炸', ORANGE),
        ('告警分级', 'P0 电话 / P1 钉钉 / P2 邮件', PURPLE),
        ('SLO/SLI', '错误预算驱动迭代', RED),
        ('OpenTelemetry', '统一标准协议', GRAY),
    ]
    for i, (n, d, c) in enumerate(points):
        col = i % 2
        row = i // 2
        x = 80 + col * 340
        y = body_top + 260 + row * 50
        parts.append(f'<circle cx="{x + 6}" cy="{y - 4}" r="5" fill="{c}"/>')
        parts.append(f'<text x="{x + 20}" y="{y}" font-size="12" fill="{c}" font-weight="700">{esc(n)}</text>')
        parts.append(f'<text x="{x + 20}" y="{y + 16}" font-size="11" fill="#37474F">{esc(d)}</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)


def tpl_shard(title, essence, body_top=110):
    """分库分表。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    # 应用 -> 路由
    parts.append(box(310, body_top + 10, 180, 50, '应用层\n(写/读)', fill=GREEN + '22', stroke=GREEN, font_size=13))
    parts.append(box(310, body_top + 90, 180, 50, '分片路由层\nShardingSphere / TDDL / MyCat',
                     fill=BLUE + '22', stroke=BLUE, font_size=12))
    parts.append(arrow(400, body_top + 60, 400, body_top + 90))
    # 路由策略
    parts.append(f'<rect x="60" y="{body_top + 160}" width="680" height="100" rx="8" '
                 f'fill="#FFFFFF" stroke="{ORANGE}" stroke-width="1.5"/>')
    parts.append(f'<text x="80" y="{body_top + 184}" font-size="13" fill="{ORANGE}" font-weight="700">分片策略</text>')
    strategies = [
        ('Range 范围', '按 ID/时间区间', GREEN),
        ('Hash 哈希', 'hash(id) % N', BLUE),
        ('一致性哈希', '节点变动平滑', PURPLE),
        ('Tag 路由', '按业务标签', ORANGE),
    ]
    for i, (n, d, c) in enumerate(strategies):
        x = 80 + i * 170
        parts.append(f'<rect x="{x}" y="{body_top + 198}" width="160" height="50" rx="6" '
                     f'fill="{c}22" stroke="{c}" stroke-width="1.5"/>')
        parts.append(f'<text x="{x + 80}" y="{body_top + 218}" font-size="12" fill="{c}" '
                     f'text-anchor="middle" font-weight="700">{esc(n)}</text>')
        parts.append(f'<text x="{x + 80}" y="{body_top + 237}" font-size="10" fill="#546E7A" '
                     f'text-anchor="middle">{esc(d)}</text>')
    # 问题与解决
    parts.append(f'<rect x="60" y="{body_top + 280}" width="680" height="170" rx="8" '
                 f'fill="#FFFFFF" stroke="{RED}" stroke-width="1.5"/>')
    parts.append(f'<text x="80" y="{body_top + 304}" font-size="13" fill="{RED}" font-weight="700">引入的难题与对策</text>')
    issues = [
        ('跨库 Join', '应用层聚合 / 冗余字段', GREEN),
        ('分布式事务', '2PC / TCC / Saga / 本地消息表', BLUE),
        ('全局唯一 ID', 'Snowflake 雪花算法', ORANGE),
        ('分页深翻', '游标分页 / 二次查询', PURPLE),
        ('扩容迁移', '一致性哈希 / 双写灰度', RED),
        ('聚合统计', '预计算 / T+1 离线', GRAY),
    ]
    for i, (n, d, c) in enumerate(issues):
        col = i % 2
        row = i // 2
        x = 80 + col * 340
        y = body_top + 326 + row * 38
        parts.append(f'<circle cx="{x + 6}" cy="{y - 4}" r="5" fill="{c}"/>')
        parts.append(f'<text x="{x + 20}" y="{y}" font-size="12" fill="#37474F">'
                     f'<tspan fill="{c}" font-weight="700">{esc(n)}：</tspan>{esc(d)}</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)


def tpl_distributed_tx(title, essence, body_top=110):
    """分布式事务方案对比。"""
    return tpl_compare(title, essence, [
        ('2PC\n两阶段提交', ['协调者+参与者', '强一致', '阻塞/性能差', '单点故障', 'XA 协议']),
        ('TCC\nTry-Confirm-Cancel', ['业务侵入', '最终一致', '性能好', '需幂等', 'Saga 替代']),
        ('本地消息表', ['异步确保', '业务表+消息表', '最终一致', '可靠', '主流方案']),
        ('Saga', ['长事务拆分', '正反向补偿', '最终一致', '适合长流程', '状态机驱动']),
    ], body_top=body_top)


def tpl_circuit_breaker(title, essence, body_top=110):
    """熔断/降级。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    # 状态机三态
    states = [
        ('CLOSED\n关闭', '正常放行', GREEN, 100),
        ('OPEN\n打开', '熔断拒绝\n快速失败', RED, 350),
        ('HALF_OPEN\n半开', '探测恢复', ORANGE, 600),
    ]
    for n, d, c, x in states:
        parts.append(f'<rect x="{x}" y="{body_top + 20}" width="160" height="80" rx="10" '
                     f'fill="{c}22" stroke="{c}" stroke-width="2"/>')
        parts.append(f'<text x="{x + 80}" y="{body_top + 48}" font-size="14" fill="{c}" '
                     f'text-anchor="middle" font-weight="700">{esc(n)}</text>')
        parts.append(f'<text x="{x + 80}" y="{body_top + 76}" font-size="11" fill="#546E7A" '
                     f'text-anchor="middle">{esc(d)}</text>')
    # 状态迁移
    parts.append(arrow(260, body_top + 60, 350, body_top + 60, color=RED, label='失败率>阈值'))
    parts.append(arrow(510, body_top + 60, 600, body_top + 60, color=ORANGE, label='超时时间到'))
    parts.append(arrow(600, body_top + 100, 180, body_top + 100, color=GREEN, label='探测成功'))
    # 策略
    parts.append(f'<rect x="60" y="{body_top + 130}" width="680" height="120" rx="8" '
                 f'fill="#FFFFFF" stroke="{PURPLE}" stroke-width="1.5"/>')
    parts.append(f'<text x="80" y="{body_top + 154}" font-size="13" fill="{PURPLE}" font-weight="700">核心策略</text>')
    items = [
        ('慢调用比例', 'RT 阈值+比例触发', GREEN),
        ('异常比例', '异常率 > 50%', BLUE),
        ('异常数', '异常次数阈值', ORANGE),
        ('恢复时间', '默认 10s', PURPLE),
        ('Hystrix', '老牌熔断器', RED),
        ('Sentinel', '阿里主流', GRAY),
        ('Resilience4j', '函数式', GREEN),
        ('降级', '兜底返回', BLUE),
    ]
    for i, (n, d, c) in enumerate(items):
        col = i % 4
        row = i // 4
        x = 80 + col * 170
        y = body_top + 180 + row * 32
        parts.append(f'<circle cx="{x + 6}" cy="{y - 4}" r="5" fill="{c}"/>')
        parts.append(f'<text x="{x + 20}" y="{y}" font-size="11" fill="#37474F">'
                     f'<tspan fill="{c}" font-weight="700">{esc(n)}</tspan> {esc(d)}</text>')
    # 配合限流
    parts.append(f'<text x="400" y="{body_top + 280}" font-size="13" fill="{BLUE}" text-anchor="middle" font-weight="700">'
                 f'熔断保护下游  ·  限流保护自身  ·  降级保用户体验</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)


def tpl_security(title, essence, body_top=110):
    """安全架构。"""
    return tpl_layers(title, essence, [
        ('接入层', ['DDoS 防护 / WAF / HTTPS / IP 黑白名单']),
        ('网关层', ['认证(JWT/OAuth2) / 鉴权(RBAC) / 防重放 / 限流']),
        ('应用层', ['SQL 注入参数化 / XSS 过滤 / CSRF Token / 越权校验']),
        ('数据层', ['敏感字段加密(AES) / 脱敏 / 哈希(BCrypt) / KMS 密钥']),
        ('审计层', ['操作日志 / 行为审计 / 完整性校验 / 等保合规']),
    ], body_top=body_top)


def tpl_perf_optimize(title, essence, body_top=110):
    """性能优化全景图。"""
    return tpl_layers(title, essence, [
        ('前端层', ['CDN 加速 / 懒加载 / 资源压缩 / HTTP/2 多路复用']),
        ('网关层', ['限流 / 熔断 / 静态化 / Gzip / 连接池']),
        ('应用层', ['异步化 / 多级缓存 / 批量 / 池化 / 算法优化']),
        ('存储层', ['读写分离 / 分库分表 / 索引优化 / 连接池']),
        ('JVM 层', ['GC 调优 / 堆设置 / JIT / 线程池调优']),
        ('OS/硬件', ['CPU 亲和 / 网卡 / SSD / 内核参数 (tcp_tw_reuse)']),
    ], body_top=body_top)


def tpl_kafka(title, essence, body_top=110):
    """Kafka 架构。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(ARROW_DEFS)
    # Producer
    parts.append(box(40, body_top + 80, 100, 60, 'Producer\n生产者', fill=GREEN + '22', stroke=GREEN, font_size=12))
    # Broker 集群
    parts.append(f'<rect x="160" y="{body_top + 10}" width="480" height="180" rx="10" '
                 f'fill="{BLUE}11" stroke="{BLUE}" stroke-width="2"/>')
    parts.append(f'<text x="400" y="{body_top + 34}" font-size="14" fill="{BLUE}" '
                 f'text-anchor="middle" font-weight="700">Kafka Cluster</text>')
    # Topic + Partition
    parts.append(f'<text x="180" y="{body_top + 60}" font-size="11" fill="{PURPLE}" font-weight="700">'
                 f'Topic: order-events  ·  Partition=3  ·  Replication=2</text>')
    # 3 brokers
    for i in range(3):
        x = 180 + i * 150
        parts.append(box(x, body_top + 76, 140, 100, f'Broker {i+1}\nLeader: P{i}\nFollower: P{(i+1)%3}',
                         fill='#FFFFFF', stroke=BLUE, font_size=10))
    parts.append(arrow(140, body_top + 110, 180, body_top + 110, label='send'))
    # Consumer Group
    parts.append(f'<rect x="160" y="{body_top + 210}" width="480" height="70" rx="8" '
                 f'fill="{ORANGE}11" stroke="{ORANGE}" stroke-width="2"/>')
    parts.append(f'<text x="180" y="{body_top + 232}" font-size="12" fill="{ORANGE}" font-weight="700">'
                 f'Consumer Group: 各消费者各自消费不同分区</text>')
    for i in range(3):
        x = 200 + i * 140
        parts.append(box(x, body_top + 240, 120, 30, f'Consumer {i+1}\n← P{i}', fill='#FFFFFF', stroke=ORANGE, font_size=10))
    parts.append(arrow(400, body_top + 190, 400, body_top + 210, color=ORANGE, label='consume'))
    # 要点
    parts.append(f'<rect x="60" y="{body_top + 300}" width="680" height="150" rx="8" '
                 f'fill="#FFFFFF" stroke="{GRAY}" stroke-width="1.5"/>')
    parts.append(f'<text x="80" y="{body_top + 324}" font-size="13" fill="{GRAY}" font-weight="700">核心机制</text>')
    pts = [
        ('高吞吐', '顺序写盘 + 零拷贝(sendfile)', GREEN),
        ('高可用', '副本机制 + ISR + Leader 选举', BLUE),
        ('顺序保证', '单分区内有序，跨分区无序', ORANGE),
        ('Exactly-Once', '幂等+事务', PURPLE),
        ('Offset 管理', '__consumer_offsets', RED),
        ('ZK/KRaft', 'Kafka 3.x 去 ZK', GRAY),
    ]
    for i, (n, d, c) in enumerate(pts):
        col = i % 2
        row = i // 2
        x = 80 + col * 340
        y = body_top + 350 + row * 36
        parts.append(f'<circle cx="{x + 6}" cy="{y - 4}" r="5" fill="{c}"/>')
        parts.append(f'<text x="{x + 20}" y="{y}" font-size="12" fill="#37474F">'
                     f'<tspan fill="{c}" font-weight="700">{esc(n)}：</tspan>{esc(d)}</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)


def tpl_idempotent(title, essence, body_top=110):
    """幂等性设计。"""
    parts, body_top = svg_header(title, essence)
    parts = [parts]
    parts.append(f'<rect x="60" y="{body_top}" width="680" height="50" rx="8" fill="{BLUE}"/>')
    parts.append(f'<text x="400" y="{body_top + 32}" font-size="15" fill="#FFFFFF" text-anchor="middle" font-weight="700">'
                 f'幂等性：多次相同请求 = 一次请求效果（防重复扣款 / 重复下单）</text>')
    # 6 种方案
    schemes = [
        ('唯一索引', 'DB 层防重\nINSERT 冲突即丢弃', GREEN, 60, body_top + 80),
        ('Token 令牌', '先获取 token\n请求携带验证', BLUE, 290, body_top + 80),
        ('乐观锁', 'version 字段\nUPDATE where v=?', ORANGE, 520, body_top + 80),
        ('状态机', '业务状态约束\n只能单向流转', PURPLE, 60, body_top + 200),
        ('分布式锁', 'Redis setnx\n互斥执行', RED, 290, body_top + 200),
        ('防重表', 'request_id 唯一\n先查后处理', GRAY, 520, body_top + 200),
    ]
    for n, d, c, x, y in schemes:
        parts.append(f'<rect x="{x}" y="{y}" width="220" height="100" rx="8" '
                     f'fill="{c}22" stroke="{c}" stroke-width="2"/>')
        parts.append(f'<text x="{x + 110}" y="{y + 30}" font-size="14" fill="{c}" '
                     f'text-anchor="middle" font-weight="700">{esc(n)}</text>')
        for j, ln in enumerate(wrap_text(d, 24)):
            parts.append(f'<text x="{x + 110}" y="{y + 60 + j * 16}" font-size="11" fill="#37474F" '
                         f'text-anchor="middle">{esc(ln)}</text>')
    # 选型要点
    parts.append(f'<rect x="60" y="{body_top + 320}" width="680" height="130" rx="8" '
                 f'fill="#FFFFFF" stroke="{PURPLE}" stroke-width="1.5"/>')
    parts.append(f'<text x="80" y="{body_top + 344}" font-size="13" fill="{PURPLE}" font-weight="700">选型要点</text>')
    pts = [
        ('支付/下单', '强一致 → Token + DB 唯一索引', GREEN),
        ('消息消费', '至少一次 → request_id 防重表', BLUE),
        ('并发更新', '乐观锁 version 优选', ORANGE),
        ('悲观场景', '分布式锁 + 超时释放', RED),
    ]
    for i, (n, d, c) in enumerate(pts):
        y = body_top + 372 + i * 20
        parts.append(f'<circle cx="86" cy="{y - 4}" r="5" fill="{c}"/>')
        parts.append(f'<text x="100" y="{y}" font-size="12" fill="#37474F">'
                     f'<tspan fill="{c}" font-weight="700">{esc(n)}：</tspan>{esc(d)}</text>')
    parts.append(svg_footer())
    return '\n'.join(parts)


def tpl_cache_arch(title, essence, body_top=110):
    """多级缓存架构。"""
    return tpl_pipeline(title, essence, [
        '浏览器缓存\nHTTP Cache-Control',
        'CDN 边缘缓存\n静态资源',
        'Nginx 缓存\nproxy_cache',
        '本地缓存\nCaffeine/Guava',
        '分布式缓存\nRedis Cluster',
        'DB\nMySQL',
    ], body_top=body_top)


def tpl_design_principle_ext(title, essence, body_top=110):
    """通用 - 没有专用模板时的兜底方案选型类。"""
    return jc.tpl_layers(title, essence, [
        ('核心维度', ['成本 / 性能 / 一致性 / 可用性 / 可维护性 / 团队规模']),
        ('决策框架', ['问题边界 → 候选方案 → 权衡取舍 → 最小可行 → 度量验证 → 持续演进']),
        ('常见反模式', ['过度设计 / YAGNI / 复制粘贴 / 上帝类 / 分布式单体内核']),
    ], body_top=body_top)


# 补充模板注册
EXTRA_TPL = {
    'rag': tpl_rag,
    'agent': tpl_agent,
    'multi_tenant': tpl_multi_tenant,
    'rate_limit': tpl_rate_limit,
    'gateway': tpl_gateway,
    'multi_dc': tpl_multi_dc,
    'observability': tpl_observability,
    'shard': tpl_shard,
    'distributed_tx': tpl_distributed_tx,
    'circuit_breaker': tpl_circuit_breaker,
    'security': tpl_security,
    'perf_optimize': tpl_perf_optimize,
    'kafka': tpl_kafka,
    'idempotent': tpl_idempotent,
    'cache_arch': tpl_cache_arch,
    'design_principle_ext': tpl_design_principle_ext,
}


# ============================================================
# 分类专属的关键词 → 模板路由
# ============================================================

def select_extra_template(cat, title, essence, key_points, subcategory=''):
    """eng-practice / java-architect 专用补充路由。
    返回模板 fn 或 None。"""
    text_all = ' '.join([title or '', essence or '',
                         ' '.join(key_points) if key_points else '',
                         subcategory or ''])
    cn = text_all
    lo = text_all.lower()

    # ===== eng-practice 专属 =====
    if cat == 'eng-practice':
        if any(k in cn for k in ['RAG', '检索增强', 'Embedding', '向量检索', '召回', '知识库',
                                  'Vector', 'Chunking', 'Rerank', '多路召回', 'RRF']):
            return EXTRA_TPL['rag']
        if any(k in cn for k in ['Agent', '智能体', 'ReAct', 'Plan-and-Execute', '多智能体',
                                  '工具调用', 'Function Call', '反思']):
            return EXTRA_TPL['agent']

    # ===== java-architect 专属 =====
    if cat == 'java-architect':
        if any(k in cn for k in ['多租户', 'SaaS', '租户隔离', 'tenant']):
            return EXTRA_TPL['multi_tenant']
        if any(k in cn for k in ['限流', 'RateLimit', '令牌桶', '漏桶', '滑动窗口', 'Sentinel',
                                  '熔断降级']) and not any(k in cn for k in ['熔断', 'Circuit']):
            return EXTRA_TPL['rate_limit']
        if any(k in cn for k in ['熔断', 'Circuit', 'Hystrix', 'Resilience4j', '降级']):
            return EXTRA_TPL['circuit_breaker']
        if any(k in cn for k in ['网关', 'Gateway', 'API Gateway', 'Spring Cloud Gateway', 'Kong']):
            return EXTRA_TPL['gateway']
        if any(k in cn for k in ['多活', '容灾', '同城双活', '两地三中心', '异地多活', '灾备']):
            return EXTRA_TPL['multi_dc']
        if any(k in cn for k in ['可观测', 'Metrics', 'Logging', 'Tracing', '链路追踪',
                                  '监控', 'SkyWalking', 'Prometheus', 'OpenTelemetry']):
            return EXTRA_TPL['observability']
        if any(k in cn for k in ['分库分表', 'Sharding', '分片', 'ShardSphere']):
            return EXTRA_TPL['shard']
        if any(k in cn for k in ['分布式事务', '2PC', 'TCC', 'Saga', '本地消息表', 'XA']):
            return EXTRA_TPL['distributed_tx']
        if any(k in cn for k in ['安全架构', '认证授权', 'JWT', 'OAuth', '越权', 'XSS',
                                  'SQL 注入', 'RBAC', '等保', 'GDPR']):
            return EXTRA_TPL['security']
        if any(k in cn for k in ['性能优化', '性能调优', '高并发优化', '全链路优化']):
            return EXTRA_TPL['perf_optimize']
        if any(k in cn for k in ['Kafka', 'kafka', '消息队列', '消息中间件', 'Topic', 'Partition']):
            return EXTRA_TPL['kafka']
        if any(k in cn for k in ['幂等', '幂等性', '防重', '重复扣款']):
            return EXTRA_TPL['idempotent']
        if any(k in cn for k in ['多级缓存', '缓存架构', 'CDN', 'Caffeine']):
            return EXTRA_TPL['cache_arch']

    return None


# ============================================================
# 主流程
# ============================================================

def process_file(md_path, category, write_md=True, overwrite=False):
    """处理单个 md 文件，生成 SVG 并更新 md。"""
    stem = md_path.stem
    svg_name = f'diagram_{category}_{stem}.svg'
    svg_path = IMG_DIR / svg_name

    if svg_path.exists() and not overwrite:
        # 跳过已存在的，但若 md 没有引用图也要补
        if write_md:
            _patch_md_reference_if_absent(md_path, svg_name, stem)
        return ('skip', svg_name)

    raw = md_path.read_text(encoding='utf-8')
    fm = jc.parse_frontmatter(raw)
    title = jc.parse_title(raw) or fm.get('id', stem)
    essence = ''
    fe = fm.get('feynman')
    if isinstance(fe, dict) and fe.get('essence'):
        essence = str(fe['essence']).strip()
    elif fm.get('essence'):
        essence = str(fm.get('essence')).strip()
    key_points = []
    if isinstance(fe, dict) and isinstance(fe.get('key_points'), list):
        key_points = [str(x) for x in fe['key_points'] if x]
    elif isinstance(fm.get('key_points'), list):
        key_points = [str(x) for x in fm['key_points'] if x]
    subcategory = fm.get('subcategory', '') if isinstance(fm, dict) else ''

    # 先用 jc 自带路由
    sel = jc.select_template(fm.get('id', ''), title, essence, key_points)
    svg = None
    if sel is not None:
        fn, kw = sel
        try:
            svg = fn(title, essence, **kw)
        except Exception:
            svg = None

    # 再用补充路由
    if svg is None:
        ex = select_extra_template(category, title, essence, key_points, subcategory)
        if ex is not None:
            try:
                svg = ex(title, essence)
            except Exception:
                svg = None

    # 兜底
    if svg is None:
        try:
            svg = jc.tpl_generic_collection_or_core(title, essence, key_points)
        except Exception:
            svg = jc.tpl_flow_vertical(title, essence, key_points[:5] or ['核心要点1', '核心要点2', '核心要点3'])

    IMG_DIR.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(svg, encoding='utf-8')

    # 更新 md
    if write_md:
        _patch_md_reference_if_absent(md_path, svg_name, stem, raw=raw)

    return ('new', svg_name)


def _patch_md_reference_if_absent(md_path, svg_name, stem, raw=None):
    """在 `## 记忆要点` 前插入/替换 `## 核心知识点图` 段。"""
    if raw is None:
        raw = md_path.read_text(encoding='utf-8')

    section = (
        '\n## 核心知识点图\n\n'
        f'<img src="/interview-2026/images/{svg_name}" '
        f'alt="核心知识点图" style="max-width:100%;height:auto;'
        f'border:1px solid var(--border);border-radius:8px;margin:1em 0;" />\n'
    )

    # 已存在 → 替换
    pattern = re.compile(
        r'\n?## 核心知识点图\s*\n.*?(?=\n## 记忆要点\b)',
        re.DOTALL
    )
    if pattern.search(raw):
        new_raw = pattern.sub(section, raw)
        if new_raw != raw:
            md_path.write_text(new_raw, encoding='utf-8')
        return

    # 不存在 → 在 `## 记忆要点` 前插入
    mem_pattern = re.compile(r'\n## 记忆要点\b')
    if mem_pattern.search(raw):
        new_raw = mem_pattern.sub(section + '\n## 记忆要点', raw, count=1)
        md_path.write_text(new_raw, encoding='utf-8')
        return

    # 兜底：附加在末尾
    new_raw = raw.rstrip() + '\n' + section
    md_path.write_text(new_raw, encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--category', '-c', action='append', dest='categories',
                    choices=['java-core', 'eng-practice', 'java-architect'],
                    help='指定分类（可多次，默认全部）')
    ap.add_argument('--force', action='store_true',
                    help='覆盖已存在的 SVG')
    ap.add_argument('--skip-md', action='store_true',
                    help='不修改 md 文件')
    args = ap.parse_args()

    cats = args.categories or ['java-core', 'eng-practice', 'java-architect']

    IMG_DIR.mkdir(parents=True, exist_ok=True)

    print('=' * 64)
    print('interview-2026 · 核心 SVG 批量生成')
    print('=' * 64)

    grand_total = 0
    grand_new = 0
    grand_skip = 0
    grand_md = 0
    grand_err = 0

    for cat in cats:
        qdir = ROOT / 'questions' / cat
        files = sorted(qdir.glob('*.md'))
        n_total = len(files)
        n_new = 0
        n_skip = 0
        n_md = 0
        errs = []
        for i, p in enumerate(files, 1):
            try:
                status, name = process_file(
                    p, cat,
                    write_md=not args.skip_md,
                    overwrite=args.force,
                )
                if status == 'new':
                    n_new += 1
                    n_md += 1
                else:
                    n_skip += 1
                if i % 30 == 0 or i == n_total:
                    print(f'  [{cat}] {i}/{n_total}')
            except Exception as e:
                errs.append((p.name, str(e)))
                grand_err += 1
        print(f'[{cat}] files={n_total} new={n_new} skip={n_skip} errs={len(errs)}')
        if errs:
            for name, err in errs[:5]:
                print(f'   ERR: {name} → {err}')
        grand_total += n_total
        grand_new += n_new
        grand_skip += n_skip
        grand_md += n_md

    print('-' * 64)
    print(f'TOTAL files={grand_total} new_svg={grand_new} skipped={grand_skip} md_updated={grand_md} errors={grand_err}')
    print('=' * 64)


if __name__ == '__main__':
    main()
