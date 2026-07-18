#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为 distributed 和 middleware 分类的每道面试题生成核心知识点 SVG 静态精绘图。

输入：questions/<category>/<filename>.md （读取 frontmatter: title/essence/key_points）
输出：
  - public/images/diagram_<category>_<filename>.svg
  - 在 md 的 ## 记忆要点 前插入 ## 核心知识点图 引用块
"""
import os
import re
import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_DIR = ROOT / "questions"
IMAGES_DIR = ROOT / "public" / "images"

CATEGORIES = ["distributed", "middleware"]

# 主题色
COLORS = {
    "green": "#4CAF50",
    "orange": "#FF9800",
    "purple": "#9C27B0",
    "red": "#f44336",
    "blue": "#2196F3",
    "gray": "#607D8B",
}
# 浅色填充
FILL = {
    "green": "#E8F5E9",
    "orange": "#FFF3E0",
    "purple": "#F3E5F5",
    "red": "#FFEBEE",
    "blue": "#E3F2FD",
    "gray": "#ECEFF1",
}
TEXT_DARK = {
    "green": "#2E7D32",
    "orange": "#E65100",
    "purple": "#6A1B9A",
    "red": "#C62828",
    "blue": "#1565C0",
    "gray": "#37474F",
}

SVG_HEADER = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500" '
    'style="max-width:100%;height:auto;font-family:system-ui,-apple-system,\'PingFang SC\',sans-serif;">\n'
)
SVG_DEFS = (
    '  <defs>\n'
    '    <marker id="arr" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto">\n'
    '      <path d="M0,0 L10,4 L0,8 Z" fill="#666"/>\n'
    '    </marker>\n'
    '    <marker id="arrg" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto">\n'
    '      <path d="M0,0 L10,4 L0,8 Z" fill="#4CAF50"/>\n'
    '    </marker>\n'
    '    <marker id="arro" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto">\n'
    '      <path d="M0,0 L10,4 L0,8 Z" fill="#FF9800"/>\n'
    '    </marker>\n'
    '    <marker id="arrr" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto">\n'
    '      <path d="M0,0 L10,4 L0,8 Z" fill="#f44336"/>\n'
    '    </marker>\n'
    '  </defs>\n'
)


def esc(s):
    """XML-escape text content."""
    return html.escape(str(s), quote=True)


# ============================================================
#  通用图元工具
# ============================================================

def _background(title):
    return [
        f'  <rect width="800" height="500" rx="12" fill="#fafafa" stroke="#e0e0e0"/>',
        f'  <text x="400" y="36" text-anchor="middle" font-size="18" font-weight="700" '
        f'fill="#263238">{esc(title)}</text>',
        f'  <line x1="60" y1="52" x2="740" y2="52" stroke="#e0e0e0" stroke-width="1"/>',
    ]


def _box(cx, cy, w, h, text, sub, color, key="blue"):
    """圆角矩形节点。cx,cy 中心点。"""
    x, y = cx - w / 2, cy - h / 2
    out = [
        f'  <rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" rx="10" '
        f'fill="{FILL[key]}" stroke="{color}" stroke-width="2"/>',
        f'  <text x="{cx:.0f}" y="{cy - (5 if sub else 0):.0f}" text-anchor="middle" '
        f'font-size="13" font-weight="700" fill="{TEXT_DARK[key]}">{esc(text)}</text>',
    ]
    if sub:
        out.append(
            f'  <text x="{cx:.0f}" y="{cy + 14:.0f}" text-anchor="middle" '
            f'font-size="11" fill="{TEXT_DARK[key]}">{esc(sub)}</text>'
        )
    return out


def _circle(cx, cy, r, text, sub, color, key="blue"):
    out = [
        f'  <circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r:.0f}" fill="{FILL[key]}" '
        f'stroke="{color}" stroke-width="2"/>',
        f'  <text x="{cx:.0f}" y="{cy - 2:.0f}" text-anchor="middle" '
        f'font-size="12" font-weight="700" fill="{TEXT_DARK[key]}">{esc(text)}</text>',
    ]
    if sub:
        out.append(
            f'  <text x="{cx:.0f}" y="{cy + 14:.0f}" text-anchor="middle" '
            f'font-size="10" fill="{TEXT_DARK[key]}">{esc(sub)}</text>'
        )
    return out


def _diamond(cx, cy, half_w, half_h, text, color, key="orange"):
    pts = f"{cx},{cy - half_h} {cx + half_w},{cy} {cx},{cy + half_h} {cx - half_w},{cy}"
    out = [
        f'  <polygon points="{pts}" fill="{FILL[key]}" stroke="{color}" stroke-width="2"/>',
        f'  <text x="{cx:.0f}" y="{cy + 4:.0f}" text-anchor="middle" font-size="11" '
        f'font-weight="700" fill="{TEXT_DARK[key]}">{esc(text)}</text>',
    ]
    return out


def _ellipse(cx, cy, rx, ry, text, color, key="green"):
    out = [
        f'  <ellipse cx="{cx:.0f}" cy="{cy:.0f}" rx="{rx:.0f}" ry="{ry:.0f}" fill="{color}" stroke="none"/>',
        f'  <text x="{cx:.0f}" y="{cy + 4:.0f}" text-anchor="middle" font-size="12" '
        f'font-weight="700" fill="#fff">{esc(text)}</text>',
    ]
    return out


def _arrow(x1, y1, x2, y2, marker="arr", color="#666", dashed=False):
    dash = ' stroke-dasharray="5,3"' if dashed else ""
    return [
        f'  <line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" '
        f'stroke="{color}" stroke-width="2"{dash} marker-end="url(#{marker})"/>'
    ]


def _label(x, y, text, color, size=10):
    return [f'  <text x="{x:.0f}" y="{y:.0f}" font-size="{size}" '
            f'font-weight="600" fill="{color}">{esc(text)}</text>']


def _legend(items, x=40, y=440):
    """items: list of (color_key, label)"""
    out = [f'  <rect x="{x - 10}" y="{y - 12}" width="380" height="{26 + 12 * len(items)}" '
           f'rx="6" fill="#ffffff" stroke="#e0e0e0"/>',
           f'  <text x="{x}" y="{y + 4}" font-size="10" fill="#888" font-weight="700">图例</text>']
    yy = y + 18
    for k, label in items:
        out.append(f'  <rect x="{x}" y="{yy}" width="12" height="12" rx="2" fill="{COLORS[k]}"/>')
        out.append(f'  <text x="{x + 18}" y="{yy + 10}" font-size="10" fill="#666">{esc(label)}</text>')
        yy += 16
    return out


def _footer_note(text):
    return [f'  <text x="400" y="486" text-anchor="middle" font-size="10" '
            f'fill="#999" font-style="italic">{esc(text)}</text>']


# ============================================================
#  模板：根据知识点语义生成对应图表
# ============================================================

# 关键词 -> 模板选择（顺序敏感：先匹配的优先）
TEMPLATE_HINTS = [
    (r"熔断|断路器|hystrix|circuit", "circuit_breaker"),
    (r"分布式事务|2pc|3pc|tcc|saga|seata|xa事务", "distributed_tx"),
    (r"分布式锁", "distributed_lock"),
    (r"限流|令牌桶|漏桶|滑动窗口|sentinel|漏斗", "rate_limit"),
    (r"缓存.*穿透|缓存.*击穿|缓存.*雪崩|布隆", "cache_failure"),
    (r"顺序|有序", "mq_order"),
    (r"幂等|重复", "idempotent"),
    (r"堆积|积压|backlog", "backlog"),
    (r"不丢失|可靠性|ack|持久化|防丢失", "reliability"),
    (r"raft|zab|paxos|选举|leader|多数派|共识", "consensus"),
    (r"cap|acid|base.*最终", "cap_triangle"),
    (r"脑裂|split.brain", "split_brain"),
    (r"消息队列|mq|kafka|rocketmq|rabbitmq", "mq_generic"),
    (r"网关|gateway|spring cloud gateway|apisix|kong", "gateway"),
    (r"注册中心|eureka|nacos|zookeeper|consul|服务发现|服务注册", "service_discovery"),
    (r"配置中心|apollo", "config_center"),
    (r"链路追踪|skywalking|zipkin|jaeger|trace", "tracing"),
    (r"分布式id|雪花|snowflake|发号", "distributed_id"),
    (r"分库分表|sharding|分片|分表", "sharding"),
    (r"主从|副本|复制|replication|mysql.*复制", "replication"),
    (r"负载均衡|ribbon|lvs|nginx|轮询|一致性.*哈希|负载策略", "load_balance"),
    (r"redis|缓存", "cache_generic"),
    (r"keepalive|keep.alive|心跳", "heartbeat"),
    (r"虚拟化|容器|docker|k8s|kubernetes", "container"),
    (r"jwt|oauth|token|鉴权|认证|sso", "auth"),
    (r"grpc|dubbo|rpc|thrift|序列化", "rpc"),
    (r"压测|性能测试|jmeter|benchmark", "benchmark"),
    (r"灰度|蓝绿|金丝雀|发布|部署", "deploy"),
    (r"监控|告警|prometheus|grafana|可观测", "monitor"),
    (r"vmware|vm\s*tools", "vmware"),
]


def pick_template(title, essence, key_points):
    """根据关键词选择最匹配的模板。"""
    blob = (title + " " + essence + " " + " ".join(key_points)).lower()
    for pat, name in TEMPLATE_HINTS:
        if re.search(pat, blob):
            return name
    # 默认通用模板
    if len(key_points) >= 4:
        return "pillars"
    return "flow"


# ------------------------------------------------------------
#  各类模板
# ------------------------------------------------------------

def tpl_flow(title, essence, points, colors_keys=None):
    """通用流程图：横向 N 个节点。"""
    colors_keys = colors_keys or ["blue", "orange", "purple", "green", "blue"]
    n = min(len(points), 5) if points else 3
    pts = points if points else ["步骤一", "步骤二", "步骤三"]
    y = 200
    x_start, x_end = 100, 700
    if n == 1:
        xs = [400]
    else:
        step = (x_end - x_start) / (n - 1)
        xs = [x_start + i * step for i in range(n)]
    out = _background(title)
    out.append(f'  <text x="400" y="80" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    # 上方短摘要
    for i in range(n):
        k = colors_keys[i % len(colors_keys)]
        label = pts[i] if i < len(pts) else ""
        # 取主标题前 14 字
        short = label.split("：")[0].split(":")[0][:16]
        out += _box(xs[i], y, 130, 70, f"步骤 {i + 1}", short, COLORS[k], k)
        if i < n - 1:
            out += _arrow(xs[i] + 65, y, xs[i + 1] - 65, y)
    # 下方为完整描述
    out.append('  <text x="400" y="330" text-anchor="middle" font-size="12" fill="#666" font-weight="700">核心要点</text>')
    for i, p in enumerate(pts[:5]):
        out.append(f'  <text x="60" y="{358 + i * 22}" font-size="11" fill="#455A64">• {esc(p[:60])}{"…" if len(p) > 60 else ""}</text>')
    out += _footer_note("横向流程：步骤 1 → N，节点颜色表示不同语义阶段")
    return out


def tpl_pillars(title, essence, points, colors_keys=None):
    """柱状图：N 个核心支柱。"""
    colors_keys = colors_keys or ["blue", "orange", "purple", "green", "red"]
    out = _background(title)
    out.append(f'  <text x="400" y="82" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    pts = points if points else ["核心要点"]
    n = min(len(pts), 5)
    if n == 0:
        n = 3
        pts = pts + ["要点"] * (3 - len(pts))
    width = 120
    gap = 30
    total = n * width + (n - 1) * gap
    x0 = (800 - total) / 2
    for i in range(n):
        k = colors_keys[i % len(colors_keys)]
        x = x0 + i * (width + gap)
        # 柱
        out.append(f'  <rect x="{x:.0f}" y="{150:.0f}" width="{width:.0f}" height="{200:.0f}" rx="6" '
                   f'fill="{FILL[k]}" stroke="{COLORS[k]}" stroke-width="2"/>')
        # 序号圆
        out.append(f'  <circle cx="{x + width / 2:.0f}" cy="175" r="16" fill="{COLORS[k]}"/>')
        out.append(f'  <text x="{x + width / 2:.0f}" y="180" text-anchor="middle" font-size="14" '
                   f'font-weight="700" fill="#fff">{i + 1}</text>')
        # 标题（自动折行）
        title_text = pts[i][:8]
        out.append(f'  <text x="{x + width / 2:.0f}" y="220" text-anchor="middle" font-size="13" '
                   f'font-weight="700" fill="{TEXT_DARK[k]}">{esc(title_text)}</text>')
        # 剩余文字换行展示在柱内
        rest = pts[i][8:50]
        lines = [rest[j:j + 8] for j in range(0, len(rest), 8)]
        for li, line in enumerate(lines[:6]):
            out.append(f'  <text x="{x + width / 2:.0f}" y="{244 + li * 16:.0f}" text-anchor="middle" '
                       f'font-size="10" fill="{TEXT_DARK[k]}">{esc(line)}</text>')
    # 底部说明
    out.append(f'  <text x="400" y="400" text-anchor="middle" font-size="12" fill="#666" font-weight="700">各要点并列同等重要，共同支撑核心知识体系</text>')
    out += _footer_note("柱状结构：每个柱代表一个独立核心点")
    return out


def tpl_circuit_breaker(title, essence, points, colors_keys=None):
    """熔断器三态闭环。"""
    out = _background(title)
    out.append(f'  <text x="400" y="82" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    # 三个节点
    out += _box(180, 230, 180, 70, "Closed（关闭）", "正常通过，统计失败率", COLORS["green"], "green")
    out += _box(620, 230, 180, 70, "Open（打开）", "熔断，快速失败", COLORS["red"], "red")
    out += _box(400, 380, 180, 70, "Half-Open（半开）", "放行单请求试探", COLORS["orange"], "orange")
    # Closed -> Open
    out += _arrow(270, 230, 525, 230, "arro", COLORS["orange"])
    out += _label(400, 220, "失败率 > 阈值（50%）", COLORS["orange"])
    # Open -> Half-Open
    out += _arrow(620, 265, 470, 345, "arr", COLORS["gray"])
    out += _label(560, 320, "休眠窗 5s 后", "#888")
    # Half-Open -> Closed
    out += _arrow(330, 360, 230, 270, "arrg", COLORS["green"])
    out += _label(220, 330, "试探成功", COLORS["green"])
    # Half-Open -> Open
    out += _arrow(470, 360, 580, 270, "arrr", COLORS["red"])
    out += _label(540, 330, "试探失败", COLORS["red"])
    # 关键点
    out.append('  <text x="400" y="135" text-anchor="middle" font-size="12" fill="#666" font-weight="700">断路器三态闭环（Closed ⇄ Open ⇄ Half-Open）</text>')
    out += _legend([("green", "Closed 正常"), ("red", "Open 熔断"), ("orange", "Half-Open 探测")], x=560, y=420)
    out += _footer_note("Hystrix：滚动窗口统计失败率，半开态放行单请求验证恢复")
    return out


def tpl_consensus(title, essence, points, colors_keys=None):
    """共识协议：Leader/Follower + 多数派 + Term。"""
    out = _background(title)
    out.append(f'  <text x="400" y="82" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    # Leader
    out += _ellipse(400, 170, 70, 36, "Leader", COLORS["orange"], "orange")
    # Followers
    out += _circle(220, 300, 45, "Follower", "投票", COLORS["blue"], "blue")
    out += _circle(580, 300, 45, "Follower", "投票", COLORS["blue"], "blue")
    out += _circle(400, 360, 45, "Candidate", "发起选举", COLORS["purple"], "purple")
    # Leader -> Followers 心跳
    out += _arrow(360, 195, 250, 275, "arrg", COLORS["green"])
    out += _arrow(440, 195, 550, 275, "arrg", COLORS["green"])
    out += _label(280, 240, "心跳/日志", COLORS["green"])
    out += _label(510, 240, "心跳/日志", COLORS["green"])
    # Followers -> Leader 投票
    out += _arrow(250, 280, 370, 200, "arro", COLORS["orange"])
    out += _arrow(550, 280, 430, 200, "arro", COLORS["orange"])
    # Term 标签
    out.append('  <rect x="60" y="110" width="100" height="40" rx="8" fill="#F3E5F5" stroke="#9C27B0" stroke-width="2"/>')
    out.append('  <text x="110" y="128" text-anchor="middle" font-size="11" font-weight="700" fill="#6A1B9A">Term 任期</text>')
    out.append('  <text x="110" y="142" text-anchor="middle" font-size="9" fill="#8E24AA">逻辑时钟</text>')
    # 多数派说明
    out.append('  <rect x="640" y="110" width="120" height="40" rx="8" fill="#FFF3E0" stroke="#FF9800" stroke-width="2"/>')
    out.append('  <text x="700" y="128" text-anchor="middle" font-size="11" font-weight="700" fill="#E65100">多数派 Quorum</text>')
    out.append('  <text x="700" y="142" text-anchor="middle" font-size="9" fill="#F57C00">N/2 + 1</text>')
    # 关键点
    out.append('  <text x="400" y="420" text-anchor="middle" font-size="11" fill="#666" font-weight="700">核心：Leader 写入 → 复制到多数派 Followers → Commit</text>')
    out += _footer_note("Raft/ZAB：Leader 选举 + 日志复制 + 多数派提交，Term 防脑裂")
    return out


def tpl_cap_triangle(title, essence, points, colors_keys=None):
    """CAP/ACID 三角。"""
    import math
    out = _background(title)
    out.append(f'  <text x="400" y="82" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    # 三角形顶点
    cx, cy = 400, 260
    r = 130
    pts = [(cx, cy - r), (cx - r * math.cos(math.pi / 6), cy + r / 2),
           (cx + r * math.cos(math.pi / 6), cy + r / 2)]
    pts_xyd = " ".join(f"{x:.0f},{y:.0f}" for x, y in pts)
    out.append(f'  <polygon points="{pts_xyd}" fill="none" stroke="#90A4AE" stroke-width="2" stroke-dasharray="6,3"/>')
    # 标签 C/A/P
    labels = ["一致性 Consistency", "可用性 Availability", "分区容错 Partition"]
    colors_list = ["blue", "green", "orange"]
    for (x, y), label, c in zip(pts, labels, colors_list):
        out += _circle(x, y, 50, label.split()[0], label.split()[-1] if len(label.split()) > 1 else "", COLORS[c], c)
    # 中间提示
    out.append(f'  <text x="{cx}" y="{cy + 10}" text-anchor="middle" font-size="12" '
              f'font-weight="700" fill="#546E7A">三选二</text>')
    out.append(f'  <text x="{cx}" y="{cy + 28}" text-anchor="middle" font-size="10" '
              f'fill="#78909C">CA / CP / AP</text>')
    # 关键点
    for i, p in enumerate(points[:3]):
        out.append(f'  <text x="60" y="{410 + i * 18}" font-size="11" fill="#455A64">• {esc(p[:65])}{"…" if len(p) > 65 else ""}</text>')
    out += _footer_note("CAP 定理：分布式系统网络分区不可避免，常在 C 与 A 间权衡")
    return out


def tpl_distributed_tx(title, essence, points, colors_keys=None):
    """分布式事务方案对比。"""
    out = _background(title)
    out.append(f'  <text x="400" y="82" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    # 四种方案
    plans = [
        ("2PC", "两阶段提交", "强一致 · 阻塞", "red"),
        ("3PC", "三阶段提交", "降低阻塞 · 仍有风险", "orange"),
        ("TCC", "Try-Confirm-Cancel", "业务侵入 · 最终一致", "purple"),
        ("Saga", "长事务补偿", "最终一致 · 反向补偿", "blue"),
    ]
    x0, y, w, h, gap = 50, 160, 165, 130, 18
    for i, (name, sub, desc, c) in enumerate(plans):
        x = x0 + i * (w + gap)
        out.append(f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" '
                   f'fill="{FILL[c]}" stroke="{COLORS[c]}" stroke-width="2"/>')
        out.append(f'  <text x="{x + w / 2:.0f}" y="{y + 30}" text-anchor="middle" font-size="15" '
                   f'font-weight="700" fill="{TEXT_DARK[c]}">{name}</text>')
        out.append(f'  <text x="{x + w / 2:.0f}" y="{y + 55}" text-anchor="middle" font-size="11" '
                   f'fill="{TEXT_DARK[c]}">{sub}</text>')
        out.append(f'  <line x1="{x + 15}" y1="{y + 70}" x2="{x + w - 15}" y2="{y + 70}" stroke="{COLORS[c]}" stroke-width="1"/>')
        out.append(f'  <text x="{x + w / 2:.0f}" y="{y + 90}" text-anchor="middle" font-size="10" '
                   f'fill="{TEXT_DARK[c]}">{desc}</text>')
        # 流程箭头
        if i < len(plans) - 1:
            out += _arrow(x + w + 2, y + h / 2, x + w + gap - 2, y + h / 2)
    # 一致性 vs 性能坐标轴
    out.append('  <line x1="60" y1="350" x2="740" y2="350" stroke="#90A4AE" stroke-width="1.5" marker-end="url(#arr)"/>')
    out.append('  <text x="745" y="354" font-size="10" fill="#78909C">性能 / 可用性</text>')
    out.append('  <text x="70" y="345" font-size="10" fill="#78909C" font-weight="600">弱一致</text>')
    out.append('  <text x="640" y="345" font-size="10" fill="#78909C" font-weight="600">强一致</text>')
    # 标注位置
    positions = [("2PC", 700), ("3PC", 580), ("TCC", 380), ("Saga", 180)]
    for name, px in positions:
        c = {"2PC": "red", "3PC": "orange", "TCC": "purple", "Saga": "blue"}[name]
        out.append(f'  <circle cx="{px}" cy="350" r="5" fill="{COLORS[c]}"/>')
        out.append(f'  <text x="{px - 12}" y="370" font-size="10" font-weight="700" fill="{TEXT_DARK[c]}">{name}</text>')
    out += _footer_note("分布式事务：强一致（2PC）← 性能权衡 → 最终一致（Saga/TCC）")
    return out


def tpl_distributed_lock(title, essence, points, colors_keys=None):
    """分布式锁实现方案。"""
    out = _background(title)
    out.append(f'  <text x="400" y="82" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    # 三种方案
    out += _box(180, 170, 220, 80, "Redis SETNX + EX", "性能高 · 可能丢锁", COLORS["red"], "red")
    out += _box(400, 170, 220, 80, "Redisson 看门狗", "自动续期 · 推荐方案", COLORS["green"], "green")
    out += _box(620, 170, 220, 80, "ZooKeeper 临时节点", "强一致 · CP", COLORS["blue"], "blue")
    # 中央加锁流程
    out.append('  <text x="400" y="295" text-anchor="middle" font-size="13" fill="#546E7A" font-weight="700">加锁流程（Redis 为例）</text>')
    steps = ["1.SET key NX PX", "2.执行业务", "3.看门狗续期", "4.Lua 释放锁"]
    step_colors = ["blue", "orange", "orange", "green"]
    x0 = 100
    for i, s in enumerate(steps):
        x = x0 + i * 160
        out.append(f'  <rect x="{x}" y="320" width="140" height="40" rx="6" '
                   f'fill="{FILL[step_colors[i]]}" stroke="{COLORS[step_colors[i]]}" stroke-width="2"/>')
        out.append(f'  <text x="{x + 70}" y="345" text-anchor="middle" font-size="11" '
                   f'font-weight="700" fill="{TEXT_DARK[step_colors[i]]}">{esc(s)}</text>')
        if i < len(steps) - 1:
            out += _arrow(x + 140, 340, x + 160, 340)
    # 关键点
    for i, p in enumerate(points[:3]):
        out.append(f'  <text x="60" y="{410 + i * 18}" font-size="11" fill="#455A64">• {esc(p[:65])}{"…" if len(p) > 65 else ""}</text>')
    out += _footer_note("三要素：互斥（NX）+ 过期（PX）+ 唯一释放（Lua 校验）")
    return out


def tpl_rate_limit(title, essence, points, colors_keys=None):
    """限流算法对比：计数器 / 滑动窗口 / 漏桶 / 令牌桶。"""
    out = _background(title)
    out.append(f'  <text x="400" y="82" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    # 四象限算法
    algos = [
        ("固定窗口计数", "简单 · 临界突刺", "blue", 80, 150),
        ("滑动窗口", "平滑 · 推荐使用", "green", 460, 150),
        ("漏桶 Leaky", "恒定速率 · 平滑", "orange", 80, 270),
        ("令牌桶 Token", "允许突发 · 最常用", "purple", 460, 270),
    ]
    for name, desc, c, x, y in algos:
        out.append(f'  <rect x="{x}" y="{y}" width="260" height="80" rx="8" '
                   f'fill="{FILL[c]}" stroke="{COLORS[c]}" stroke-width="2"/>')
        out.append(f'  <text x="{x + 130}" y="{y + 30}" text-anchor="middle" font-size="13" '
                   f'font-weight="700" fill="{TEXT_DARK[c]}">{esc(name)}</text>')
        out.append(f'  <text x="{x + 130}" y="{y + 55}" text-anchor="middle" font-size="11" '
                   f'fill="{TEXT_DARK[c]}">{esc(desc)}</text>')
    # 令牌桶示意（最常用）
    out.append('  <text x="400" y="395" text-anchor="middle" font-size="12" fill="#666" font-weight="700">令牌桶原理：固定速率投放令牌 → 请求消耗令牌</text>')
    out += _box(160, 430, 130, 40, "令牌生成器", "r 个/秒", COLORS["purple"], "purple")
    out += _box(400, 430, 130, 40, "令牌桶", "容量 N", COLORS["orange"], "orange")
    out += _box(640, 430, 130, 40, "请求", "无令牌拒绝", COLORS["green"], "green")
    out += _arrow(225, 430, 335, 430, "arr", COLORS["purple"])
    out += _arrow(465, 430, 575, 430, "arr", COLORS["purple"])
    out += _footer_note("Sentinel：滑动窗口统计 QPS，配合预热/排队策略")
    return out


def tpl_load_balance(title, essence, points, colors_keys=None):
    """负载均衡：流量分发示意 + 算法对比。"""
    out = _background(title)
    out.append(f'  <text x="400" y="82" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    # 客户端
    out += _box(100, 200, 130, 50, "客户端", "Client", COLORS["gray"], "gray")
    # LB
    out += _box(330, 200, 140, 60, "Load Balancer", "负载均衡器", COLORS["orange"], "orange")
    # 后端 RS
    rs_y = [120, 200, 280]
    for i, y in enumerate(rs_y):
        out += _box(640, y, 130, 50, f"RS-{i + 1}", "Real Server", COLORS["blue"], "blue")
    # 箭头 客户端 -> LB
    out += _arrow(165, 200, 260, 200)
    # LB -> RS
    for y in rs_y:
        out += _arrow(400, 220, 575, y)
    # 算法对比
    algos = [("轮询", "Round Robin"), ("随机", "Random"), ("加权", "Weighted"),
             ("最少连接", "Least Conn"), ("一致性哈希", "Consistent Hash")]
    out.append('  <text x="400" y="350" text-anchor="middle" font-size="12" fill="#666" font-weight="700">常见算法</text>')
    x0 = 60
    for i, (n, e) in enumerate(algos):
        x = x0 + i * 145
        out.append(f'  <rect x="{x}" y="370" width="135" height="50" rx="6" '
                   f'fill="{FILL["blue"]}" stroke="{COLORS["blue"]}" stroke-width="1.5"/>')
        out.append(f'  <text x="{x + 67}" y="390" text-anchor="middle" font-size="11" '
                   f'font-weight="700" fill="{TEXT_DARK["blue"]}">{esc(n)}</text>')
        out.append(f'  <text x="{x + 67}" y="408" text-anchor="middle" font-size="9" '
                   f'fill="{TEXT_DARK["blue"]}">{esc(e)}</text>')
    out += _footer_note("LVS/Nginx/Ribbon：四层（LVS DR/FULLNAT）vs 七层（Nginx 按请求分发）")
    return out


def tpl_cache_failure(title, essence, points, colors_keys=None):
    """缓存三大问题：穿透 / 击穿 / 雪崩。"""
    out = _background(title)
    out.append(f'  <text x="400" y="82" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    issues = [
        ("缓存穿透", "查不存在的 key", "布隆过滤器 / 空值缓存", "red", 80),
        ("缓存击穿", "热点 key 过期", "互斥锁 / 永不过期", "orange", 320),
        ("缓存雪崩", "大量 key 同时过期", "随机 TTL / 多级缓存", "purple", 560),
    ]
    for name, desc, sol, c, x in issues:
        out.append(f'  <rect x="{x}" y="130" width="200" height="180" rx="10" '
                   f'fill="{FILL[c]}" stroke="{COLORS[c]}" stroke-width="2"/>')
        out.append(f'  <text x="{x + 100}" y="165" text-anchor="middle" font-size="14" '
                   f'font-weight="700" fill="{TEXT_DARK[c]}">{esc(name)}</text>')
        out.append(f'  <line x1="{x + 20}" y1="180" x2="{x + 180}" y2="180" stroke="{COLORS[c]}" stroke-width="1"/>')
        out.append(f'  <text x="{x + 100}" y="210" text-anchor="middle" font-size="11" '
                   f'fill="{TEXT_DARK[c]}">现象</text>')
        out.append(f'  <text x="{x + 100}" y="232" text-anchor="middle" font-size="10" '
                   f'fill="{TEXT_DARK[c]}">{esc(desc)}</text>')
        out.append(f'  <text x="{x + 100}" y="265" text-anchor="middle" font-size="11" '
                   f'fill="{TEXT_DARK[c]}">解决方案</text>')
        # sol 长度截断换行
        if len(sol) > 12:
            out.append(f'  <text x="{x + 100}" y="287" text-anchor="middle" font-size="10" '
                       f'fill="{TEXT_DARK[c]}">{esc(sol[:12])}</text>')
            out.append(f'  <text x="{x + 100}" y="300" text-anchor="middle" font-size="10" '
                       f'fill="{TEXT_DARK[c]}">{esc(sol[12:])}</text>')
        else:
            out.append(f'  <text x="{x + 100}" y="290" text-anchor="middle" font-size="10" '
                       f'fill="{TEXT_DARK[c]}">{esc(sol)}</text>')
    # 底部三层结构
    out.append('  <text x="400" y="360" text-anchor="middle" font-size="12" fill="#666" font-weight="700">请求 → 缓存层 → DB 层（缺失导致直击 DB）</text>')
    out += _box(180, 400, 130, 45, "请求", "Request", COLORS["gray"], "gray")
    out += _box(400, 400, 130, 45, "Redis 缓存", "MISS 命中 DB", COLORS["red"], "red")
    out += _box(620, 400, 130, 45, "DB", "压力源", COLORS["purple"], "purple")
    out += _arrow(245, 400, 335, 400)
    out += _arrow(465, 400, 555, 400)
    out += _footer_note("区分：穿透=不存在 / 击穿=单热点 / 雪崩=批量同时失效")
    return out


def tpl_cache_generic(title, essence, points, colors_keys=None):
    """通用缓存架构。"""
    out = _background(title)
    out.append(f'  <text x="400" y="82" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    # 多级缓存
    out += _box(120, 200, 130, 55, "L1 本地缓存", "Caffeine", COLORS["green"], "green")
    out += _box(330, 200, 130, 55, "L2 Redis", "分布式缓存", COLORS["orange"], "orange")
    out += _box(540, 200, 130, 55, "DB", "MySQL", COLORS["blue"], "blue")
    # 客户端
    out += _box(330, 100, 130, 50, "应用", "Application", COLORS["purple"], "purple")
    out += _arrow(330, 125, 180, 175, "arrg", COLORS["green"])
    out += _arrow(400, 150, 395, 175, "arrg", COLORS["green"])
    out += _arrow(460, 125, 600, 175, "arro", COLORS["orange"])
    out += _label(230, 145, "1.先查本地", COLORS["green"])
    out += _label(470, 145, "3.最终回源", COLORS["orange"])
    # 关键点
    out.append('  <text x="400" y="320" text-anchor="middle" font-size="12" fill="#666" font-weight="700">缓存三大问题与策略</text>')
    strategies = [
        ("Cache Aside", "旁路缓存 · 推荐"),
        ("Read/Write Through", "读写穿透"),
        ("Write Back", "异步回写"),
    ]
    x0 = 100
    for i, (n, d) in enumerate(strategies):
        x = x0 + i * 220
        out.append(f'  <rect x="{x}" y="345" width="200" height="55" rx="8" '
                   f'fill="{FILL["blue"]}" stroke="{COLORS["blue"]}" stroke-width="2"/>')
        out.append(f'  <text x="{x + 100}" y="368" text-anchor="middle" font-size="11" '
                   f'font-weight="700" fill="{TEXT_DARK["blue"]}">{esc(n)}</text>')
        out.append(f'  <text x="{x + 100}" y="386" text-anchor="middle" font-size="10" '
                   f'fill="{TEXT_DARK["blue"]}">{esc(d)}</text>')
    out += _footer_note("多级缓存：本地（快）→ Redis（共享）→ DB（持久），降低回源压力")
    return out


def tpl_mq_generic(title, essence, points, colors_keys=None):
    """消息队列架构：生产者-Broker-消费者。"""
    out = _background(title)
    out.append(f'  <text x="400" y="82" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    # Producer
    out += _box(110, 220, 140, 60, "Producer", "生产者", COLORS["blue"], "blue")
    # Broker (Topic/Queue)
    out.append('  <rect x="280" y="140" width="240" height="220" rx="10" fill="#FFF8E1" stroke="#FF9800" stroke-width="2"/>')
    out.append('  <text x="400" y="165" text-anchor="middle" font-size="13" font-weight="700" fill="#E65100">Broker</text>')
    out.append('  <line x1="295" y1="175" x2="505" y2="175" stroke="#FF9800" stroke-width="1"/>')
    # 多个队列
    for i in range(3):
        out.append(f'  <rect x="300" y="{195 + i * 50}" width="200" height="40" rx="4" '
                   f'fill="{FILL["orange"]}" stroke="{COLORS["orange"]}" stroke-width="1.5"/>')
        out.append(f'  <text x="400" y="{220 + i * 50}" text-anchor="middle" font-size="11" '
                   f'font-weight="700" fill="{TEXT_DARK["orange"]}">Queue-{i + 1}</text>')
    # Consumer Group
    out += _box(660, 180, 130, 50, "Consumer-1", "消费者", COLORS["green"], "green")
    out += _box(660, 260, 130, 50, "Consumer-2", "消费者", COLORS["green"], "green")
    # 箭头
    out += _arrow(180, 220, 275, 220)
    out += _arrow(500, 215, 590, 200)
    out += _arrow(500, 265, 590, 270)
    out += _label(225, 210, "发送", COLORS["blue"])
    out += _label(525, 195, "消费", COLORS["green"])
    # 三大价值
    out.append('  <text x="400" y="395" text-anchor="middle" font-size="12" fill="#666" font-weight="700">三大核心价值</text>')
    vals = [("解耦", "Decouple"), ("异步", "Async"), ("削峰", "Peak Shaving")]
    x0 = 200
    for i, (n, e) in enumerate(vals):
        x = x0 + i * 160
        out.append(f'  <rect x="{x}" y="410" width="140" height="50" rx="8" '
                   f'fill="{FILL["purple"]}" stroke="{COLORS["purple"]}" stroke-width="2"/>')
        out.append(f'  <text x="{x + 70}" y="432" text-anchor="middle" font-size="12" '
                   f'font-weight="700" fill="{TEXT_DARK["purple"]}">{esc(n)}</text>')
        out.append(f'  <text x="{x + 70}" y="450" text-anchor="middle" font-size="10" '
                   f'fill="{TEXT_DARK["purple"]}">{esc(e)}</text>')
    out += _footer_note("Kafka/RocketMQ/RabbitMQ：生产 → Broker 暂存 → 消费，异步解耦削峰")
    return out


def tpl_mq_order(title, essence, points, colors_keys=None):
    """消息有序性：分区内有序。"""
    out = _background(title)
    out.append(f'  <text x="400" y="82" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    # Producer 发送有序
    out += _box(110, 240, 130, 60, "Producer", "相同 key", COLORS["blue"], "blue")
    # 三个分区
    out.append('  <text x="400" y="135" text-anchor="middle" font-size="12" fill="#666" font-weight="700">Topic（多分区）</text>')
    parts = [
        ("Partition-0", "msg1 → msg2 → msg3", "green", 170),
        ("Partition-1", "msg4 → msg5", "orange", 240),
        ("Partition-2", "msg6", "purple", 310),
    ]
    for name, msgs, c, y in parts:
        out.append(f'  <rect x="290" y="{y - 22}" width="220" height="44" rx="6" '
                   f'fill="{FILL[c]}" stroke="{COLORS[c]}" stroke-width="2"/>')
        out.append(f'  <text x="320" y="{y}" text-anchor="start" font-size="11" '
                   f'font-weight="700" fill="{TEXT_DARK[c]}">{esc(name)}</text>')
        out.append(f'  <text x="510" y="{y}" text-anchor="end" font-size="10" '
                   f'fill="{TEXT_DARK[c]}">{esc(msgs)}</text>')
    # Hash 路由
    out.append(f'  <text x="220" y="200" font-size="10" font-weight="600" fill="#FF9800">hash(key) % N</text>')
    out += _arrow(240, 240, 285, 195, "arro", COLORS["orange"])
    out += _arrow(240, 240, 285, 240, "arro", COLORS["orange"])
    out += _arrow(240, 240, 285, 285, "arro", COLORS["orange"])
    # Consumer 单线程消费
    out += _box(680, 240, 100, 60, "Consumer", "单线程", COLORS["red"], "red")
    out += _arrow(510, 200, 630, 230, "arr", COLORS["red"])
    out += _arrow(510, 240, 630, 250, "arr", COLORS["red"])
    out += _arrow(510, 290, 630, 270, "arr", COLORS["red"])
    # 核心结论
    out.append('  <rect x="100" y="380" width="600" height="80" rx="8" '
               f'fill="{FILL["gray"]}" stroke="{COLORS["gray"]}" stroke-width="2"/>')
    out.append('  <text x="400" y="405" text-anchor="middle" font-size="12" font-weight="700" fill="#37474F">有序性保障原则</text>')
    out.append('  <text x="400" y="428" text-anchor="middle" font-size="11" fill="#37474F">① 同 key 进同 Partition  ② Partition 内单 Consumer 单线程消费</text>')
    out.append('  <text x="400" y="448" text-anchor="middle" font-size="11" fill="#37474F">③ 全局有序只能单 Partition，吞吐大降</text>')
    out += _footer_note("局部有序 vs 全局有序：业务上 99% 场景只需分区内有序")
    return out


def tpl_idempotent(title, essence, points, colors_keys=None):
    """幂等性设计。"""
    out = _background(title)
    out.append(f'  <text x="400" y="82" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    # 重复请求来源
    out.append('  <text x="400" y="125" text-anchor="middle" font-size="12" fill="#666" font-weight="700">重复消息来源</text>')
    srcs = [("网络重试", "Producer 重发"), ("Consumer 重启", "Offset 未提交"), ("Rebalance", "分区重分配")]
    x0 = 80
    for i, (n, d) in enumerate(srcs):
        x = x0 + i * 230
        out.append(f'  <rect x="{x}" y="140" width="210" height="50" rx="6" '
                   f'fill="{FILL["red"]}" stroke="{COLORS["red"]}" stroke-width="2"/>')
        out.append(f'  <text x="{x + 105}" y="162" text-anchor="middle" font-size="11" '
                   f'font-weight="700" fill="{TEXT_DARK["red"]}">{esc(n)}</text>')
        out.append(f'  <text x="{x + 105}" y="180" text-anchor="middle" font-size="10" '
                   f'fill="{TEXT_DARK["red"]}">{esc(d)}</text>')
    # 幂等方案
    out.append('  <text x="400" y="230" text-anchor="middle" font-size="12" fill="#666" font-weight="700">幂等性实现方案</text>')
    plans = [
        ("唯一索引", "DB 兜底", "blue"),
        ("Token 机制", "防重令牌", "green"),
        ("状态机", "状态流转校验", "orange"),
        ("乐观锁", "version 控制", "purple"),
    ]
    x0 = 40
    for i, (n, d, c) in enumerate(plans):
        x = x0 + i * 185
        out.append(f'  <rect x="{x}" y="250" width="170" height="65" rx="8" '
                   f'fill="{FILL[c]}" stroke="{COLORS[c]}" stroke-width="2"/>')
        out.append(f'  <text x="{x + 85}" y="277" text-anchor="middle" font-size="12" '
                   f'font-weight="700" fill="{TEXT_DARK[c]}">{esc(n)}</text>')
        out.append(f'  <text x="{x + 85}" y="297" text-anchor="middle" font-size="10" '
                   f'fill="{TEXT_DARK[c]}">{esc(d)}</text>')
    # 流程图：检查
    out.append('  <text x="400" y="355" text-anchor="middle" font-size="12" fill="#666" font-weight="700">通用幂等流程</text>')
    flow = ["请求", "查 Redis 标记", "已处理?", "执行业务", "设标记"]
    colors_f = ["gray", "blue", "orange", "green", "purple"]
    x0 = 60
    for i, s in enumerate(flow):
        x = x0 + i * 145
        if s.endswith("?"):
            out += _diamond(x + 65, 400, 60, 28, s, COLORS["orange"], "orange")
        else:
            out.append(f'  <rect x="{x}" y="380" width="130" height="40" rx="6" '
                       f'fill="{FILL[colors_f[i]]}" stroke="{COLORS[colors_f[i]]}" stroke-width="2"/>')
            out.append(f'  <text x="{x + 65}" y="405" text-anchor="middle" font-size="11" '
                       f'font-weight="700" fill="{TEXT_DARK[colors_f[i]]}">{esc(s)}</text>')
        if i < len(flow) - 1:
            out += _arrow(x + 130, 400, x + 145, 400)
    out += _footer_note("业务幂等：f(f(x)) = f(x)，靠唯一键/状态/版本拦截重复执行")
    return out


def tpl_backlog(title, essence, points, colors_keys=None):
    """消息堆积处理。"""
    out = _background(title)
    out.append(f'  <text x="400" y="82" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    # 瓶颈定位流程
    out.append('  <text x="400" y="125" text-anchor="middle" font-size="12" fill="#666" font-weight="700">问题定位 → 临时方案 → 根治方案</text>')
    # 现象
    out += _box(150, 175, 180, 55, "现象", "Lag 持续增长", COLORS["red"], "red")
    out += _box(400, 175, 180, 55, "定位瓶颈", "Producer?Consumer?", COLORS["orange"], "orange")
    out += _box(650, 175, 180, 55, "根治", "扩容 / 优化消费", COLORS["green"], "green")
    out += _arrow(240, 175, 310, 175)
    out += _arrow(490, 175, 560, 175)
    # 临时方案
    out.append('  <text x="200" y="290" text-anchor="middle" font-size="12" fill="#666" font-weight="700">临时方案</text>')
    tmp = [("消费降级", "跳过非关键"), ("扩 Partition", "+ Consumer")]
    for i, (n, d) in enumerate(tmp):
        x = 100 + i * 200
        out.append(f'  <rect x="{x}" y="300" width="180" height="55" rx="6" '
                   f'fill="{FILL["orange"]}" stroke="{COLORS["orange"]}" stroke-width="2"/>')
        out.append(f'  <text x="{x + 90}" y="322" text-anchor="middle" font-size="11" '
                   f'font-weight="700" fill="{TEXT_DARK["orange"]}">{esc(n)}</text>')
        out.append(f'  <text x="{x + 90}" y="340" text-anchor="middle" font-size="10" '
                   f'fill="{TEXT_DARK["orange"]}">{esc(d)}</text>')
    # 根治
    out.append('  <text x="600" y="290" text-anchor="middle" font-size="12" fill="#666" font-weight="700">根治方案</text>')
    root = [("水平扩容", "Part=Cons"), ("批量消费", "pull 500"), ("异步处理", "多线程")]
    for i, (n, d) in enumerate(root):
        x = 480 + i * 110
        out.append(f'  <rect x="{x}" y="300" width="100" height="55" rx="6" '
                   f'fill="{FILL["green"]}" stroke="{COLORS["green"]}" stroke-width="2"/>')
        out.append(f'  <text x="{x + 50}" y="322" text-anchor="middle" font-size="10" '
                   f'font-weight="700" fill="{TEXT_DARK["green"]}">{esc(n)}</text>')
        out.append(f'  <text x="{x + 50}" y="340" text-anchor="middle" font-size="9" '
                   f'fill="{TEXT_DARK["green"]}">{esc(d)}</text>')
    # 底部关键点
    out.append('  <rect x="60" y="390" width="680" height="80" rx="8" '
               f'fill="{FILL["blue"]}" stroke="{COLORS["blue"]}" stroke-width="2"/>')
    out.append('  <text x="400" y="415" text-anchor="middle" font-size="12" font-weight="700" fill="#1565C0">关键约束</text>')
    out.append('  <text x="400" y="438" text-anchor="middle" font-size="11" fill="#1565C0">扩容前提：Consumer 数 ≤ Partition 数（否则多余 Consumer 空闲）</text>')
    out.append('  <text x="400" y="458" text-anchor="middle" font-size="11" fill="#1565C0">注意：扩 Partition 会破坏分区内有序性</text>')
    out += _footer_note("堆积本质：消费速率 < 生产速率，根因多为慢 SQL/外部依赖/串行化")
    return out


def tpl_reliability(title, essence, points, colors_keys=None):
    """消息可靠性：生产-存储-消费三端。"""
    out = _background(title)
    out.append(f'  <text x="400" y="82" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    # 三层保障
    layers = [
        ("① 生产端", "Ack 确认 / 事务消息", "同步发送 + 重试", "blue", 150),
        ("② Broker 存储", "同步刷盘 + 副本", "主从同步复制", "orange", 260),
        ("③ 消费端", "手动提交 Offset", "业务完成后再 ack", "green", 370),
    ]
    for name, method, detail, c, y in layers:
        out.append(f'  <rect x="80" y="{y - 35}" width="640" height="80" rx="10" '
                   f'fill="{FILL[c]}" stroke="{COLORS[c]}" stroke-width="2"/>')
        out.append(f'  <text x="120" y="{y}" font-size="14" font-weight="700" fill="{TEXT_DARK[c]}">{esc(name)}</text>')
        out.append(f'  <text x="120" y="{y + 22}" font-size="11" fill="{TEXT_DARK[c]}">{esc(method)}</text>')
        out.append(f'  <text x="460" y="{y}" font-size="11" font-weight="600" fill="{TEXT_DARK[c]}">{esc(detail)}</text>')
    # 箭头连接
    out += _arrow(400, 195, 400, 225)
    out += _arrow(400, 305, 400, 335)
    # 底部三方权衡
    out.append('  <text x="400" y="435" text-anchor="middle" font-size="12" fill="#666" font-weight="700">可靠性 vs 性能：权衡取舍</text>')
    out.append('  <text x="400" y="458" text-anchor="middle" font-size="11" fill="#666">同步刷盘 → 可靠性高但延迟高；异步刷盘 → 性能高但有丢数据风险</text>')
    out += _footer_note("全链路防丢失：生产端 Ack + Broker 持久化 + 消费端手动 Offset 提交")
    return out


def tpl_gateway(title, essence, points, colors_keys=None):
    """API 网关。"""
    out = _background(title)
    out.append(f'  <text x="400" y="82" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    # 客户端
    out += _box(80, 240, 110, 60, "客户端", "Web/App", COLORS["gray"], "gray")
    # Gateway 中央
    out.append('  <rect x="280" y="120" width="240" height="290" rx="10" fill="#FFF8E1" stroke="#FF9800" stroke-width="2"/>')
    out.append('  <text x="400" y="148" text-anchor="middle" font-size="14" font-weight="700" fill="#E65100">API Gateway</text>')
    out.append('  <line x1="300" y1="160" x2="500" y2="160" stroke="#FF9800" stroke-width="1"/>')
    # 内部职能
    funcs = [
        ("路由转发", "Route", "blue", 185),
        ("鉴权认证", "Auth", "purple", 225),
        ("限流熔断", "RateLimit", "red", 265),
        ("日志监控", "Log", "orange", 305),
        ("协议转换", "HTTP→RPC", "green", 345),
        ("灰度发布", "Canary", "gray", 385),
    ]
    for n, e, c, y in funcs:
        out.append(f'  <rect x="300" y="{y - 12}" width="200" height="28" rx="4" '
                   f'fill="{FILL[c]}" stroke="{COLORS[c]}" stroke-width="1.5"/>')
        out.append(f'  <text x="400" y="{y + 5}" text-anchor="middle" font-size="11" '
                   f'font-weight="700" fill="{TEXT_DARK[c]}">{esc(n)} · {esc(e)}</text>')
    # 后端服务
    for i in range(3):
        y = 160 + i * 130
        out += _box(680, y, 100, 50, f"服务-{i + 1}", "Service", COLORS["blue"], "blue")
    out += _arrow(190, 240, 280, 240)
    out += _arrow(520, 180, 630, 160)
    out += _arrow(520, 265, 630, 290)
    out += _arrow(520, 350, 630, 420)
    out += _label(220, 230, "请求", COLORS["gray"])
    out += _label(550, 170, "分发", COLORS["orange"])
    out += _footer_note("Spring Cloud Gateway / Kong / APISIX：统一流量入口 + 横切关注点")
    return out


def tpl_service_discovery(title, essence, points, colors_keys=None):
    """注册中心 / 服务发现。"""
    out = _background(title)
    out.append(f'  <text x="400" y="82" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    # 注册中心
    out += _box(400, 200, 200, 70, "注册中心", "Registry · CP/AP", COLORS["orange"], "orange")
    # 服务提供者
    out += _box(120, 350, 150, 60, "Provider-1", "注册", COLORS["green"], "green")
    out += _box(400, 350, 150, 60, "Provider-2", "注册", COLORS["green"], "green")
    out += _box(680, 350, 150, 60, "Provider-3", "注册", COLORS["green"], "green")
    # Consumer
    out += _box(120, 110, 150, 60, "Consumer", "订阅", COLORS["blue"], "blue")
    # 箭头 注册
    out += _arrow(190, 320, 350, 235, "arro", COLORS["orange"])
    out += _arrow(400, 320, 400, 235, "arro", COLORS["orange"])
    out += _arrow(610, 320, 450, 235, "arro", COLORS["orange"])
    out += _label(280, 280, "注册/心跳", COLORS["orange"])
    # 箭头 订阅
    out += _arrow(195, 140, 330, 175, "arrg", COLORS["green"])
    out += _label(225, 125, "拉取实例列表", COLORS["green"])
    # Consumer -> Provider 调用
    out.append('  <path d="M 270 130 Q 100 220 195 320" fill="none" stroke="#2196F3" '
              'stroke-width="2" stroke-dasharray="5,3" marker-end="url(#arr)"/>')
    out += _label(80, 220, "调用", COLORS["blue"])
    # 中心说明
    out.append('  <rect x="540" y="100" width="220" height="80" rx="8" '
               f'fill="{FILL["purple"]}" stroke="{COLORS["purple"]}" stroke-width="2"/>')
    out.append('  <text x="650" y="125" text-anchor="middle" font-size="12" font-weight="700" fill="#6A1B9A">健康检查机制</text>')
    out.append('  <text x="650" y="148" text-anchor="middle" font-size="11" fill="#6A1B9A">心跳续约 + 失效剔除</text>')
    out.append('  <text x="650" y="165" text-anchor="middle" font-size="11" fill="#6A1B9A">Eureka AP · Nacos CP+AP</text>')
    out += _footer_note("Eureka/Nacos/ZK/Consul：服务上下线自动感知，Consumer 本地缓存实例列表")
    return out


def tpl_config_center(title, essence, points, colors_keys=None):
    """配置中心。"""
    out = _background(title)
    out.append(f'  <text x="400" y="82" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    # 配置中心
    out += _box(400, 150, 200, 60, "配置中心", "Apollo / Nacos", COLORS["purple"], "purple")
    # 多服务订阅
    for i, c in enumerate(["blue", "orange", "green"]):
        x = 130 + i * 280
        out += _box(x, 280, 160, 60, f"应用-{i + 1}", "本地缓存配置", COLORS[c], c)
        # 推送
        out += _arrow(400, 180, x, 250, "arrg", COLORS["green"])
    out += _label(200, 220, "推送变更", COLORS["green"])
    # 配置生命周期
    out.append('  <text x="400" y="350" text-anchor="middle" font-size="12" fill="#666" font-weight="700">配置管理流程</text>')
    flow = [("编辑", "blue"), ("发布", "orange"), ("推送", "purple"), ("热更新", "green"), ("审计", "gray")]
    x0 = 80
    for i, (s, c) in enumerate(flow):
        x = x0 + i * 145
        out.append(f'  <rect x="{x}" y="370" width="130" height="40" rx="6" '
                   f'fill="{FILL[c]}" stroke="{COLORS[c]}" stroke-width="2"/>')
        out.append(f'  <text x="{x + 65}" y="395" text-anchor="middle" font-size="11" '
                   f'font-weight="700" fill="{TEXT_DARK[c]}">{esc(s)}</text>')
        if i < len(flow) - 1:
            out += _arrow(x + 130, 390, x + 145, 390)
    out += _footer_note("核心价值：动态生效（无需重启）+ 灰度发布 + 版本回滚 + 多环境隔离")
    return out


def tpl_tracing(title, essence, points, colors_keys=None):
    """链路追踪。"""
    out = _background(title)
    out.append(f'  <text x="400" y="82" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    # 调用链
    out.append('  <text x="400" y="125" text-anchor="middle" font-size="12" fill="#666" font-weight="700">一次请求的完整调用链（Trace = 多个 Span）</text>')
    # Span 层级
    spans = [
        ("Gateway", "trace-id=abc", 50, 700, "blue", 160),
        ("Order-Svc", "span-id=1", 100, 500, "orange", 210),
        ("User-Svc", "span-id=2", 150, 250, "purple", 260),
        ("DB", "span-id=3", 200, 100, "green", 310),
    ]
    for name, sid, x, w, c, y in spans:
        out.append(f'  <rect x="{x + 50}" y="{y - 18}" width="{w}" height="32" rx="4" '
                   f'fill="{FILL[c]}" stroke="{COLORS[c]}" stroke-width="2"/>')
        out.append(f'  <text x="{x + 60}" y="{y}" font-size="11" font-weight="700" fill="{TEXT_DARK[c]}">{esc(name)}</text>')
        out.append(f'  <text x="{x + 60}" y="{y + 13}" font-size="9" fill="{TEXT_DARK[c]}">{esc(sid)}</text>')
    # 时间轴
    out.append('  <line x1="50" y1="350" x2="770" y2="350" stroke="#90A4AE" stroke-width="1" marker-end="url(#arr)"/>')
    out.append('  <text x="775" y="354" font-size="10" fill="#78909C">时间</text>')
    # 关键概念
    out.append('  <rect x="60" y="380" width="680" height="90" rx="8" '
               f'fill="{FILL["gray"]}" stroke="{COLORS["gray"]}" stroke-width="2"/>')
    out.append('  <text x="400" y="405" text-anchor="middle" font-size="12" font-weight="700" fill="#37474F">核心概念</text>')
    out.append('  <text x="80" y="428" font-size="11" fill="#37474F">• Trace：一次完整请求，全局唯一的 trace-id</text>')
    out.append('  <text x="80" y="448" font-size="11" fill="#37474F">• Span：一次服务调用，span-id + parent-id 构成树形结构</text>')
    out.append('  <text x="440" y="428" font-size="11" fill="#37474F">• 采样率：降低开销</text>')
    out.append('  <text x="440" y="448" font-size="11" fill="#37474F">• Agent 上报：异步非阻塞</text>')
    out += _footer_note("SkyWalking/Zipkin/Jaeger：自动埋点 + Trace 树还原，定位慢调用与错误")
    return out


def tpl_distributed_id(title, essence, points, colors_keys=None):
    """分布式 ID 方案。"""
    out = _background(title)
    out.append(f'  <text x="400" y="82" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    # 方案对比
    plans = [
        ("UUID", "简单 · 无序 · 占空间", "red", 80, 140),
        ("DB 自增", "简单 · 单点瓶颈", "orange", 320, 140),
        ("号段模式", "预分配 · 性能高", "purple", 560, 140),
        ("Snowflake", "有序 · 趋势递增", "green", 80, 250),
        ("Redis INCR", "性能高 · 依赖 Redis", "blue", 320, 250),
        ("ZK 序列号", "强一致 · 性能低", "gray", 560, 250),
    ]
    for name, desc, c, x, y in plans:
        out.append(f'  <rect x="{x}" y="{y - 30}" width="200" height="80" rx="8" '
                   f'fill="{FILL[c]}" stroke="{COLORS[c]}" stroke-width="2"/>')
        out.append(f'  <text x="{x + 100}" y="{y}" text-anchor="middle" font-size="13" '
                   f'font-weight="700" fill="{TEXT_DARK[c]}">{esc(name)}</text>')
        out.append(f'  <text x="{x + 100}" y="{y + 22}" text-anchor="middle" font-size="10" '
                   f'fill="{TEXT_DARK[c]}">{esc(desc)}</text>')
    # Snowflake 结构（最常用）
    out.append('  <text x="400" y="345" text-anchor="middle" font-size="12" fill="#666" font-weight="700">Snowflake 结构（64 bit）</text>')
    # 拆分：1 + 41 + 10 + 12
    bits = [("1 bit", "符号位", "gray"), ("41 bit", "时间戳", "blue"),
            ("10 bit", "机器 ID", "orange"), ("12 bit", "序列号", "green")]
    x = 80
    widths = [60, 200, 140, 180]
    for (b, n, c), w in zip(bits, widths):
        out.append(f'  <rect x="{x}" y="365" width="{w}" height="60" rx="4" '
                   f'fill="{FILL[c]}" stroke="{COLORS[c]}" stroke-width="2"/>')
        out.append(f'  <text x="{x + w / 2}" y="388" text-anchor="middle" font-size="11" '
                   f'font-weight="700" fill="{TEXT_DARK[c]}">{esc(b)}</text>')
        out.append(f'  <text x="{x + w / 2}" y="408" text-anchor="middle" font-size="10" '
                   f'fill="{TEXT_DARK[c]}">{esc(n)}</text>')
        x += w + 4
    out.append('  <text x="400" y="450" text-anchor="middle" font-size="11" fill="#666">时间戳 + 机器 + 序列号 = 全局唯一 + 趋势递增</text>')
    out += _footer_note("核心诉求：全局唯一 + 趋势递增 + 高可用 + 信息安全（防猜测）")
    return out


def tpl_sharding(title, essence, points, colors_keys=None):
    """分库分表。"""
    out = _background(title)
    out.append(f'  <text x="400" y="82" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    # 拆分方式
    out.append('  <text x="400" y="125" text-anchor="middle" font-size="12" fill="#666" font-weight="700">垂直拆分 vs 水平拆分</text>')
    # 垂直
    out.append('  <rect x="60" y="145" width="320" height="120" rx="8" fill="#E3F2FD" stroke="#2196F3" stroke-width="2"/>')
    out.append('  <text x="220" y="170" text-anchor="middle" font-size="13" font-weight="700" fill="#1565C0">垂直拆分</text>')
    out.append('  <text x="220" y="195" text-anchor="middle" font-size="11" fill="#1565C0">按业务/字段拆分</text>')
    for i, name in enumerate(["User DB", "Order DB", "Item DB"]):
        x = 80 + i * 100
        out.append(f'  <rect x="{x}" y="215" width="85" height="40" rx="4" '
                   f'fill="{FILL["blue"]}" stroke="{COLORS["blue"]}" stroke-width="1.5"/>')
        out.append(f'  <text x="{x + 42}" y="240" text-anchor="middle" font-size="10" '
                   f'font-weight="700" fill="{TEXT_DARK["blue"]}">{esc(name)}</text>')
    # 水平
    out.append('  <rect x="420" y="145" width="320" height="120" rx="8" fill="#E8F5E9" stroke="#4CAF50" stroke-width="2"/>')
    out.append('  <text x="580" y="170" text-anchor="middle" font-size="13" font-weight="700" fill="#2E7D32">水平拆分（Sharding）</text>')
    out.append('  <text x="580" y="195" text-anchor="middle" font-size="11" fill="#2E7D32">按 hash/range 拆分</text>')
    for i, name in enumerate(["Shard-0", "Shard-1", "Shard-2"]):
        x = 440 + i * 100
        out.append(f'  <rect x="{x}" y="215" width="85" height="40" rx="4" '
                   f'fill="{FILL["green"]}" stroke="{COLORS["green"]}" stroke-width="1.5"/>')
        out.append(f'  <text x="{x + 42}" y="240" text-anchor="middle" font-size="10" '
                   f'font-weight="700" fill="{TEXT_DARK["green"]}">{esc(name)}</text>')
    # 分片策略
    out.append('  <text x="400" y="300" text-anchor="middle" font-size="12" fill="#666" font-weight="700">分片键路由策略</text>')
    strategies = [("hash 取模", "均匀分布"), ("range 范围", "按时间/ID"), ("一致性哈希", "扩容影响小"), ("基因法", "避免广播")]
    x0 = 60
    for i, (n, d) in enumerate(strategies):
        x = x0 + i * 180
        out.append(f'  <rect x="{x}" y="320" width="170" height="55" rx="6" '
                   f'fill="{FILL["orange"]}" stroke="{COLORS["orange"]}" stroke-width="2"/>')
        out.append(f'  <text x="{x + 85}" y="343" text-anchor="middle" font-size="11" '
                   f'font-weight="700" fill="{TEXT_DARK["orange"]}">{esc(n)}</text>')
        out.append(f'  <text x="{x + 85}" y="362" text-anchor="middle" font-size="10" '
                   f'fill="{TEXT_DARK["orange"]}">{esc(d)}</text>')
    # 关键问题
    out.append('  <rect x="60" y="395" width="680" height="70" rx="8" '
               f'fill="{FILL["purple"]}" stroke="{COLORS["purple"]}" stroke-width="2"/>')
    out.append('  <text x="400" y="418" text-anchor="middle" font-size="12" font-weight="700" fill="#6A1B9A">引入分片后的新挑战</text>')
    out.append('  <text x="400" y="440" text-anchor="middle" font-size="11" fill="#6A1B9A">跨片 Join 困难 · 分布式事务 · 全局唯一 ID · 扩容数据迁移</text>')
    out += _footer_note("ShardingSphere/Vitess：客户端/代理模式屏蔽分片细节")
    return out


def tpl_replication(title, essence, points, colors_keys=None):
    """主从复制。"""
    out = _background(title)
    out.append(f'  <text x="400" y="82" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    # Master
    out += _box(150, 220, 160, 70, "Master", "读写（部分场景）", COLORS["orange"], "orange")
    # Slaves
    out += _box(550, 130, 160, 60, "Slave-1", "只读", COLORS["blue"], "blue")
    out += _box(550, 220, 160, 60, "Slave-2", "只读", COLORS["blue"], "blue")
    out += _box(550, 310, 160, 60, "Slave-3", "只读", COLORS["blue"], "blue")
    # 复制箭头
    for y in [130, 220, 310]:
        out += _arrow(230, 220, 470, y, "arro", COLORS["orange"])
    out += _label(330, 180, "binlog 复制", COLORS["orange"])
    # 三种复制方式
    out.append('  <text x="400" y="380" text-anchor="middle" font-size="12" fill="#666" font-weight="700">三种复制方式对比</text>')
    reps = [
        ("异步复制", "性能高 · 可能丢", "orange"),
        ("半同步复制", "至少 1 从 ACK", "blue"),
        ("全同步复制", "强一致 · 性能低", "green"),
    ]
    x0 = 80
    for i, (n, d, c) in enumerate(reps):
        x = x0 + i * 220
        out.append(f'  <rect x="{x}" y="395" width="200" height="60" rx="8" '
                   f'fill="{FILL[c]}" stroke="{COLORS[c]}" stroke-width="2"/>')
        out.append(f'  <text x="{x + 100}" y="420" text-anchor="middle" font-size="12" '
                   f'font-weight="700" fill="{TEXT_DARK[c]}">{esc(n)}</text>')
        out.append(f'  <text x="{x + 100}" y="440" text-anchor="middle" font-size="10" '
                   f'fill="{TEXT_DARK[c]}">{esc(d)}</text>')
    out += _footer_note("MySQL 主从：binlog → relay log → 重放；读写分离提升读吞吐")
    return out


def tpl_split_brain(title, essence, points, colors_keys=None):
    """脑裂问题。"""
    out = _background(title)
    out.append(f'  <text x="400" y="82" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    # 正常情况
    out.append('  <text x="200" y="125" text-anchor="middle" font-size="12" fill="#2E7D32" font-weight="700">正常（单 Leader）</text>')
    out += _ellipse(200, 200, 50, 28, "Leader", COLORS["green"], "green")
    out += _circle(120, 290, 35, "F1", "", COLORS["blue"], "blue")
    out += _circle(280, 290, 35, "F2", "", COLORS["blue"], "blue")
    out += _arrow(180, 220, 140, 260, "arrg", COLORS["green"])
    out += _arrow(220, 220, 260, 260, "arrg", COLORS["green"])
    # 脑裂
    out.append('  <text x="600" y="125" text-anchor="middle" font-size="12" fill="#C62828" font-weight="700">脑裂（双 Leader）</text>')
    out += _ellipse(520, 200, 45, 28, "L1", COLORS["red"], "red")
    out += _ellipse(680, 200, 45, 28, "L2", COLORS["red"], "red")
    out += _circle(520, 290, 30, "F1", "", COLORS["orange"], "orange")
    out += _circle(680, 290, 30, "F2", "", COLORS["orange"], "orange")
    # 中间网络分区
    out.append('  <line x1="400" y1="120" x2="400" y2="350" stroke="#f44336" stroke-width="2" stroke-dasharray="6,4"/>')
    out.append('  <rect x="350" y="330" width="100" height="28" rx="4" fill="#FFEBEE" stroke="#f44336" stroke-width="1.5"/>')
    out.append('  <text x="400" y="348" text-anchor="middle" font-size="11" font-weight="700" fill="#C62828">网络分区</text>')
    # 解决方案
    out.append('  <text x="400" y="385" text-anchor="middle" font-size="12" fill="#666" font-weight="700">解决方案：多数派（Quorum）</text>')
    out.append('  <rect x="100" y="405" width="600" height="60" rx="8" '
               f'fill="{FILL["purple"]}" stroke="{COLORS["purple"]}" stroke-width="2"/>')
    out.append('  <text x="400" y="428" text-anchor="middle" font-size="12" font-weight="700" fill="#6A1B9A">必须获得 N/2 + 1 节点投票才能成为 Leader</text>')
    out.append('  <text x="400" y="450" text-anchor="middle" font-size="11" fill="#6A1B9A">少数派分区自动降级为 Candidate/Follower，无法提交日志</text>')
    out += _footer_note("Raft Term + 多数派 / ZooKeeper ZAB / Sentinel quorum 防脑裂")
    return out


def tpl_vmware(title, essence, points, colors_keys=None):
    return tpl_flow(title, essence, points)


def tpl_heartbeat(title, essence, points, colors_keys=None):
    """心跳检测。"""
    out = _background(title)
    out.append(f'  <text x="400" y="82" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    # 中心节点
    out += _box(150, 220, 160, 60, "检测方", "Monitor", COLORS["blue"], "blue")
    # 被检测节点
    out += _box(550, 130, 160, 50, "Node-1", "健康", COLORS["green"], "green")
    out += _box(550, 220, 160, 50, "Node-2", "健康", COLORS["green"], "green")
    out += _box(550, 310, 160, 50, "Node-3", "无响应", COLORS["red"], "red")
    # 心跳
    out += _arrow(230, 215, 470, 140, "arrg", COLORS["green"])
    out += _arrow(230, 220, 470, 220, "arrg", COLORS["green"])
    out += _arrow(230, 230, 470, 305, "arrr", COLORS["red"])
    out += _label(330, 175, "ping", COLORS["green"])
    out += _label(330, 250, "timeout", COLORS["red"])
    # 三个状态
    out.append('  <text x="400" y="390" text-anchor="middle" font-size="12" fill="#666" font-weight="700">检测时机与判定</text>')
    states = [("周期心跳", "每 3s ping"), ("超时阈值", "连续 3 次失败"), ("标记下线", "剔除实例列表")]
    x0 = 100
    for i, (n, d) in enumerate(states):
        x = x0 + i * 220
        out.append(f'  <rect x="{x}" y="405" width="200" height="50" rx="6" '
                   f'fill="{FILL["orange"]}" stroke="{COLORS["orange"]}" stroke-width="2"/>')
        out.append(f'  <text x="{x + 100}" y="425" text-anchor="middle" font-size="11" '
                   f'font-weight="700" fill="{TEXT_DARK["orange"]}">{esc(n)}</text>')
        out.append(f'  <text x="{x + 100}" y="445" text-anchor="middle" font-size="10" '
                   f'fill="{TEXT_DARK["orange"]}">{esc(d)}</text>')
    out += _footer_note("心跳/Keepalive：周期探测 + 超时累计 + 自愈恢复（如 Eureka 90s）")
    return out


def tpl_container(title, essence, points, colors_keys=None):
    """容器 / 虚拟化。"""
    out = _background(title)
    out.append(f'  <text x="400" y="82" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    # VM vs Container
    out.append('  <text x="200" y="125" text-anchor="middle" font-size="12" fill="#1565C0" font-weight="700">虚拟机（VM）</text>')
    out.append('  <text x="600" y="125" text-anchor="middle" font-size="12" fill="#2E7D32" font-weight="700">容器（Container）</text>')
    # VM 结构
    vm_layers = [("App A", "blue"), ("Bins/Libs", "blue"), ("Guest OS", "blue"), ("Hypervisor", "orange"), ("Host OS", "gray"), ("Infra", "gray")]
    for i, (n, c) in enumerate(vm_layers):
        y = 140 + i * 32
        out.append(f'  <rect x="80" y="{y}" width="240" height="28" rx="3" '
                   f'fill="{FILL[c]}" stroke="{COLORS[c]}" stroke-width="1.5"/>')
        out.append(f'  <text x="200" y="{y + 18}" text-anchor="middle" font-size="11" '
                   f'font-weight="700" fill="{TEXT_DARK[c]}">{esc(n)}</text>')
    # Container 结构
    ct_layers = [("App A", "green"), ("App B", "green"), ("Bins/Libs", "green"), ("Docker Engine", "orange"), ("Host OS", "gray"), ("Infra", "gray")]
    for i, (n, c) in enumerate(ct_layers):
        y = 140 + i * 32
        out.append(f'  <rect x="480" y="{y}" width="240" height="28" rx="3" '
                   f'fill="{FILL[c]}" stroke="{COLORS[c]}" stroke-width="1.5"/>')
        out.append(f'  <text x="600" y="{y + 18}" text-anchor="middle" font-size="11" '
                   f'font-weight="700" fill="{TEXT_DARK[c]}">{esc(n)}</text>')
    # 对比说明
    out.append('  <text x="400" y="375" text-anchor="middle" font-size="12" fill="#666" font-weight="700">核心差异</text>')
    out.append('  <text x="200" y="400" text-anchor="middle" font-size="11" fill="#1565C0">VM：硬件级虚拟化 · 重 · 隔离强</text>')
    out.append('  <text x="600" y="400" text-anchor="middle" font-size="11" fill="#2E7D32">容器：OS 级虚拟化 · 轻 · 共享内核</text>')
    out.append('  <text x="400" y="435" text-anchor="middle" font-size="11" fill="#666" font-weight="600">Kubernetes = 容器编排：Pod/Service/Deployment/Ingress</text>')
    out += _footer_note("Namespace + Cgroups 实现隔离与资源限制；镜像分层复用")
    return out


def tpl_auth(title, essence, points, colors_keys=None):
    """鉴权 / 认证。"""
    out = _background(title)
    out.append(f'  <text x="400" y="82" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    # 流程
    out += _box(110, 220, 120, 55, "用户", "User", COLORS["gray"], "gray")
    out += _box(290, 220, 130, 55, "认证中心", "Auth Server", COLORS["purple"], "purple")
    out += _box(490, 220, 110, 55, "Token", "JWT/Access", COLORS["orange"], "orange")
    out += _box(670, 220, 110, 55, "业务服务", "Resource", COLORS["green"], "green")
    out += _arrow(170, 220, 225, 220)
    out += _arrow(355, 220, 435, 220)
    out += _arrow(545, 220, 615, 220)
    out += _label(195, 210, "登录", COLORS["purple"])
    out += _label(395, 210, "签发", COLORS["orange"])
    out += _label(580, 210, "携带", COLORS["green"])
    # JWT 结构
    out.append('  <text x="400" y="320" text-anchor="middle" font-size="12" fill="#666" font-weight="700">JWT 结构（Header.Payload.Signature）</text>')
    parts = [("Header", "alg + typ", "blue"), ("Payload", "claims 数据", "purple"), ("Signature", "HMAC 签名", "red")]
    x0 = 130
    for i, (n, d, c) in enumerate(parts):
        x = x0 + i * 200
        out.append(f'  <rect x="{x}" y="340" width="180" height="60" rx="6" '
                   f'fill="{FILL[c]}" stroke="{COLORS[c]}" stroke-width="2"/>')
        out.append(f'  <text x="{x + 90}" y="363" text-anchor="middle" font-size="12" '
                   f'font-weight="700" fill="{TEXT_DARK[c]}">{esc(n)}</text>')
        out.append(f'  <text x="{x + 90}" y="383" text-anchor="middle" font-size="10" '
                   f'fill="{TEXT_DARK[c]}">{esc(d)}</text>')
    # 注意点
    out.append('  <text x="400" y="430" text-anchor="middle" font-size="11" fill="#C62828" font-weight="700">注意：JWT 无状态 → 无法主动失效，需配合黑名单/短期 Token + Refresh Token</text>')
    out += _footer_note("OAuth2 / JWT / SSO：认证（你是谁）vs 授权（你能做什么）")
    return out


def tpl_rpc(title, essence, points, colors_keys=None):
    """RPC 调用。"""
    out = _background(title)
    out.append(f'  <text x="400" y="82" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    # Consumer
    out.append('  <rect x="60" y="120" width="280" height="280" rx="8" fill="#E3F2FD" stroke="#2196F3" stroke-width="2"/>')
    out.append('  <text x="200" y="148" text-anchor="middle" font-size="14" font-weight="700" fill="#1565C0">Consumer（调用方）</text>')
    cons_parts = [("业务代码", "调用本地方法"), ("动态代理", "屏蔽远程细节"), ("序列化", "对象 → 字节"), ("网络客户端", "Netty/HTTP")]
    for i, (n, d) in enumerate(cons_parts):
        y = 170 + i * 55
        out.append(f'  <rect x="80" y="{y}" width="240" height="45" rx="4" '
                   f'fill="{FILL["blue"]}" stroke="{COLORS["blue"]}" stroke-width="1.5"/>')
        out.append(f'  <text x="200" y="{y + 19}" text-anchor="middle" font-size="11" font-weight="700" fill="{TEXT_DARK["blue"]}">{esc(n)}</text>')
        out.append(f'  <text x="200" y="{y + 36}" text-anchor="middle" font-size="10" fill="{TEXT_DARK["blue"]}">{esc(d)}</text>')
    # Provider
    out.append('  <rect x="460" y="120" width="280" height="280" rx="8" fill="#E8F5E9" stroke="#4CAF50" stroke-width="2"/>')
    out.append('  <text x="600" y="148" text-anchor="middle" font-size="14" font-weight="700" fill="#2E7D32">Provider（服务方）</text>')
    prov_parts = [("网络服务端", "接收请求"), ("反序列化", "字节 → 对象"), ("反射调用", "执行业务"), ("返回结果", "序列化回写")]
    for i, (n, d) in enumerate(prov_parts):
        y = 170 + i * 55
        out.append(f'  <rect x="480" y="{y}" width="240" height="45" rx="4" '
                   f'fill="{FILL["green"]}" stroke="{COLORS["green"]}" stroke-width="1.5"/>')
        out.append(f'  <text x="600" y="{y + 19}" text-anchor="middle" font-size="11" font-weight="700" fill="{TEXT_DARK["green"]}">{esc(n)}</text>')
        out.append(f'  <text x="600" y="{y + 36}" text-anchor="middle" font-size="10" fill="{TEXT_DARK["green"]}">{esc(d)}</text>')
    # 中间网络
    out += _arrow(340, 240, 460, 240)
    out += _arrow(460, 290, 340, 290)
    out += _label(400, 230, "网络", COLORS["orange"])
    out += _label(400, 305, "回写", COLORS["orange"])
    out += _footer_note("Dubbo/gRPC：代理透明化远程调用；序列化 + 注册中心 + 负载均衡")
    return out


def tpl_benchmark(title, essence, points, colors_keys=None):
    """压测 / 性能测试。"""
    out = _background(title)
    out.append(f'  <text x="400" y="82" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    # 指标
    out.append('  <text x="400" y="125" text-anchor="middle" font-size="12" fill="#666" font-weight="700">核心性能指标</text>')
    metrics = [("QPS/TPS", "吞吐量", "blue"), ("RT", "响应时间 P99", "orange"),
               ("并发数", "同时在线", "purple"), ("错误率", "失败请求占比", "red"), ("资源", "CPU/内存/IO", "green")]
    x0 = 40
    for i, (n, d, c) in enumerate(metrics):
        x = x0 + i * 150
        out.append(f'  <rect x="{x}" y="140" width="140" height="55" rx="6" '
                   f'fill="{FILL[c]}" stroke="{COLORS[c]}" stroke-width="2"/>')
        out.append(f'  <text x="{x + 70}" y="162" text-anchor="middle" font-size="12" '
                   f'font-weight="700" fill="{TEXT_DARK[c]}">{esc(n)}</text>')
        out.append(f'  <text x="{x + 70}" y="182" text-anchor="middle" font-size="10" '
                   f'fill="{TEXT_DARK[c]}">{esc(d)}</text>')
    # 压测分层
    out.append('  <text x="400" y="250" text-anchor="middle" font-size="12" fill="#666" font-weight="700">分层压测</text>')
    layers = [("基准压测", "单接口", "blue", 270), ("负载压测", "梯度加压", "orange", 330), ("稳定性压测", "长时间运行", "purple", 390)]
    for n, d, c, y in layers:
        out.append(f'  <rect x="100" y="{y - 18}" width="600" height="34" rx="4" '
                   f'fill="{FILL[c]}" stroke="{COLORS[c]}" stroke-width="2"/>')
        out.append(f'  <text x="200" y="{y + 3}" font-size="11" font-weight="700" fill="{TEXT_DARK[c]}">{esc(n)}</text>')
        out.append(f'  <text x="500" y="{y + 3}" font-size="11" fill="{TEXT_DARK[c]}">{esc(d)}</text>')
    out += _footer_note("Little Law：L = λ × W；并发 = 吞吐 × 平均响应时间")
    return out


def tpl_deploy(title, essence, points, colors_keys=None):
    """发布 / 部署策略。"""
    out = _background(title)
    out.append(f'  <text x="400" y="82" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    # 三种发布策略
    plans = [
        ("蓝绿发布", "Blue/Green", "两套环境切换", "blue", 80, 140),
        ("灰度发布", "Canary", "按比例渐进放量", "orange", 320, 140),
        ("滚动发布", "Rolling", "逐批替换实例", "green", 560, 140),
    ]
    for name, e, desc, c, x, y in plans:
        out.append(f'  <rect x="{x}" y="{y}" width="200" height="120" rx="8" '
                   f'fill="{FILL[c]}" stroke="{COLORS[c]}" stroke-width="2"/>')
        out.append(f'  <text x="{x + 100}" y="{y + 28}" text-anchor="middle" font-size="13" '
                   f'font-weight="700" fill="{TEXT_DARK[c]}">{esc(name)}</text>')
        out.append(f'  <text x="{x + 100}" y="{y + 50}" text-anchor="middle" font-size="11" '
                   f'fill="{TEXT_DARK[c]}">{esc(e)}</text>')
        out.append(f'  <line x1="{x + 20}" y1="{y + 65}" x2="{x + 180}" y2="{y + 65}" stroke="{COLORS[c]}" stroke-width="1"/>')
        out.append(f'  <text x="{x + 100}" y="{y + 88}" text-anchor="middle" font-size="10" '
                   f'fill="{TEXT_DARK[c]}">{esc(desc)}</text>')
        out.append(f'  <text x="{x + 100}" y="{y + 105}" text-anchor="middle" font-size="10" '
                   f'fill="{TEXT_DARK[c]}">回滚快</text>')
    # 灰度比例示意
    out.append('  <text x="400" y="305" text-anchor="middle" font-size="12" fill="#666" font-weight="700">灰度放量曲线（推荐策略）</text>')
    ratios = [(5, "blue"), (20, "green"), (50, "orange"), (100, "purple")]
    x0 = 120
    for i, (r, c) in enumerate(ratios):
        x = x0 + i * 150
        h = 30 + r * 0.5
        out.append(f'  <rect x="{x}" y="{420 - h:.0f}" width="100" height="{h:.0f}" rx="3" '
                   f'fill="{FILL[c]}" stroke="{COLORS[c]}" stroke-width="2"/>')
        out.append(f'  <text x="{x + 50}" y="{430}" text-anchor="middle" font-size="11" '
                   f'font-weight="700" fill="{TEXT_DARK[c]}">{r}%</text>')
    out += _footer_note("灰度：观察指标（错误率/RT）→ 逐步放量 → 全量；A/B 测试 + 特性开关")
    return out


def tpl_monitor(title, essence, points, colors_keys=None):
    """监控告警。"""
    out = _background(title)
    out.append(f'  <text x="400" y="82" text-anchor="middle" font-size="13" fill="#607D8B">{esc(essence)}</text>')
    # 监控分层
    layers = [
        ("Metrics 指标", "Prometheus", "数值时序 · QPS/RT/CPU", "blue", 140),
        ("Logging 日志", "ELK/Loki", "事件记录 · 检索分析", "orange", 210),
        ("Tracing 链路", "SkyWalking", "调用链 · 拓扑图", "purple", 280),
        ("Alerting 告警", "AlertManager", "阈值触发 · 钉钉/邮件", "red", 350),
    ]
    for name, tool, desc, c, y in layers:
        out.append(f'  <rect x="60" y="{y - 25}" width="680" height="50" rx="8" '
                   f'fill="{FILL[c]}" stroke="{COLORS[c]}" stroke-width="2"/>')
        out.append(f'  <text x="100" y="{y + 3}" font-size="13" font-weight="700" fill="{TEXT_DARK[c]}">{esc(name)}</text>')
        out.append(f'  <text x="330" y="{y + 3}" font-size="12" font-weight="600" fill="{TEXT_DARK[c]}">{esc(tool)}</text>')
        out.append(f'  <text x="600" y="{y + 3}" font-size="11" fill="{TEXT_DARK[c]}">{esc(desc)}</text>')
    # 黄金信号
    out.append('  <text x="400" y="410" text-anchor="middle" font-size="12" fill="#666" font-weight="700">SRE 四大黄金信号</text>')
    gold = [("延迟", "Latency"), ("流量", "Traffic"), ("错误", "Errors"), ("饱和度", "Saturation")]
    x0 = 80
    for i, (n, e) in enumerate(gold):
        x = x0 + i * 175
        out.append(f'  <rect x="{x}" y="425" width="160" height="45" rx="6" '
                   f'fill="{FILL["green"]}" stroke="{COLORS["green"]}" stroke-width="2"/>')
        out.append(f'  <text x="{x + 80}" y="445" text-anchor="middle" font-size="11" '
                   f'font-weight="700" fill="{TEXT_DARK["green"]}">{esc(n)}</text>')
        out.append(f'  <text x="{x + 80}" y="461" text-anchor="middle" font-size="10" '
                   f'fill="{TEXT_DARK["green"]}">{esc(e)}</text>')
    out += _footer_note("可观测性三支柱：Metrics + Logging + Tracing 联动定位问题")
    return out


# 模板分发
TEMPLATES = {
    "flow": tpl_flow,
    "pillars": tpl_pillars,
    "circuit_breaker": tpl_circuit_breaker,
    "consensus": tpl_consensus,
    "cap_triangle": tpl_cap_triangle,
    "distributed_tx": tpl_distributed_tx,
    "distributed_lock": tpl_distributed_lock,
    "rate_limit": tpl_rate_limit,
    "load_balance": tpl_load_balance,
    "cache_failure": tpl_cache_failure,
    "cache_generic": tpl_cache_generic,
    "mq_generic": tpl_mq_generic,
    "mq_order": tpl_mq_order,
    "idempotent": tpl_idempotent,
    "backlog": tpl_backlog,
    "reliability": tpl_reliability,
    "gateway": tpl_gateway,
    "service_discovery": tpl_service_discovery,
    "config_center": tpl_config_center,
    "tracing": tpl_tracing,
    "distributed_id": tpl_distributed_id,
    "sharding": tpl_sharding,
    "replication": tpl_replication,
    "split_brain": tpl_split_brain,
    "vmware": tpl_vmware,
    "heartbeat": tpl_heartbeat,
    "container": tpl_container,
    "auth": tpl_auth,
    "rpc": tpl_rpc,
    "benchmark": tpl_benchmark,
    "deploy": tpl_deploy,
    "monitor": tpl_monitor,
}


# ============================================================
#  Frontmatter 解析
# ============================================================

def parse_frontmatter(text):
    m = re.match(r'^---\n(.*?)\n---\n', text, re.DOTALL)
    if not m:
        return {}
    fm = m.group(1)
    data = {}
    # title 在正文
    title_m = re.search(r'^#\s+(.+?)$', text, re.MULTILINE)
    title = title_m.group(1).strip() if title_m else ""
    # essence
    essence_m = re.search(r'essence:\s*(.+)', fm)
    essence = essence_m.group(1).strip() if essence_m else ""
    # key_points (列表)
    kp_m = re.search(r'key_points:\s*\n((?:\s*-\s+.+\n?)+)', fm)
    key_points = []
    if kp_m:
        for line in kp_m.group(1).splitlines():
            line = line.strip()
            if line.startswith("- "):
                key_points.append(line[2:].strip())
    return {
        "title": title,
        "essence": essence,
        "key_points": key_points,
    }


def build_svg(title, essence, key_points):
    tpl_name = pick_template(title, essence, key_points)
    fn = TEMPLATES.get(tpl_name, tpl_flow)
    body = fn(title, essence, key_points)
    parts = [SVG_HEADER, SVG_DEFS] + body + ['</svg>\n']
    return "\n".join(parts)


def update_md(md_path, category, filename, svg_name, title):
    text = md_path.read_text(encoding="utf-8")
    section_header = "## 核心知识点图"
    img_block = (
        f'\n{section_header}\n\n'
        f'<img src="/interview-2026/images/{svg_name}" alt="{esc(title)}" '
        f'style="max-width:100%;height:auto;border:1px solid var(--border);'
        f'border-radius:8px;margin:1em 0;" />\n'
    )
    # 若已存在 section 则替换其下内容直到下一个 ## 标题
    pattern = re.compile(
        r'## 核心知识点图\s*\n.*?(?=\n##\s)',
        re.DOTALL,
    )
    if pattern.search(text):
        replacement = img_block.rstrip() + "\n"
        new_text = pattern.sub(replacement, text)
    else:
        # 在 ## 记忆要点 前插入
        if "## 记忆要点" not in text:
            return False
        new_text = text.replace('## 记忆要点', img_block + '## 记忆要点', 1)
    if new_text != text:
        md_path.write_text(new_text, encoding="utf-8")
        return True
    return False


def process_category(category):
    cat_dir = QUESTIONS_DIR / category
    files = sorted([f for f in cat_dir.iterdir() if f.suffix == ".md"])
    stats = {"total": 0, "svg_ok": 0, "md_ok": 0, "errors": [], "tpl_count": {}}
    for fp in files:
        stats["total"] += 1
        filename = fp.stem  # 例如 dist-001
        try:
            text = fp.read_text(encoding="utf-8")
            fm = parse_frontmatter(text)
            if not fm["title"]:
                stats["errors"].append(f"{filename}: no title")
                continue
            svg = build_svg(fm["title"], fm["essence"], fm["key_points"])
            tpl_name = pick_template(fm["title"], fm["essence"], fm["key_points"])
            stats["tpl_count"][tpl_name] = stats["tpl_count"].get(tpl_name, 0) + 1
            svg_name = f"diagram_{category}_{filename}.svg"
            svg_path = IMAGES_DIR / svg_name
            svg_path.write_text(svg, encoding="utf-8")
            stats["svg_ok"] += 1
            # 更新 md
            if update_md(fp, category, filename, svg_name, fm["title"]):
                stats["md_ok"] += 1
        except Exception as e:
            stats["errors"].append(f"{filename}: {e}")
    return stats


def main():
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    all_stats = {}
    for cat in CATEGORIES:
        print(f"\n=== 处理 {cat} ===")
        stats = process_category(cat)
        all_stats[cat] = stats
        print(f"  扫描: {stats['total']}")
        print(f"  SVG 生成: {stats['svg_ok']}")
        print(f"  MD 更新: {stats['md_ok']}")
        print(f"  模板分布:")
        for tpl, cnt in sorted(stats["tpl_count"].items(), key=lambda x: -x[1]):
            print(f"    {tpl}: {cnt}")
        if stats["errors"]:
            print(f"  错误: {len(stats['errors'])}")
            for e in stats["errors"][:10]:
                print(f"    - {e}")
    # 汇总
    total = sum(s["total"] for s in all_stats.values())
    svg_ok = sum(s["svg_ok"] for s in all_stats.values())
    md_ok = sum(s["md_ok"] for s in all_stats.values())
    err_total = sum(len(s["errors"]) for s in all_stats.values())
    print("\n========== 汇总 ==========")
    print(f"  扫描文件总数: {total}")
    print(f"  SVG 成功生成: {svg_ok}")
    print(f"  MD 成功更新: {md_ok}")
    print(f"  错误数: {err_total}")
    return 0 if err_total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
