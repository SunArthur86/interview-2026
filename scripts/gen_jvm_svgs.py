#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate per-question SVG diagrams for JVM category interview questions.
Each SVG is designed based on the specific knowledge point of the question.
"""
import os
import re
import html

QUESTIONS_DIR = '/Users/sunqingguang/hermes/opt/projects/interview-2026/questions/jvm'
OUTPUT_DIR = '/Users/sunqingguang/hermes/opt/projects/interview-2026/public/images'

# Color scheme
GREEN = '#4CAF50'
ORANGE = '#FF9800'
PURPLE = '#9C27B0'
RED = '#f44336'
BLUE = '#2196F3'
GRAY = '#607D8B'
TEAL = '#009688'
INDIGO = '#3F51B5'
PINK = '#E91E63'
CYAN = '#00BCD4'


class SVG:
    """StringBuilder for SVG generation."""
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.parts = [
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
            f'font-family="system-ui, -apple-system, Segoe UI, Roboto, sans-serif">\n'
            f'<defs>\n'
            f'  <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth">'
            f'<path d="M0,0 L0,6 L9,3 z" fill="#37474F"/></marker>\n'
            f'  <marker id="arrowR" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth">'
            f'<path d="M0,0 L0,6 L9,3 z" fill="#f44336"/></marker>\n'
            f'  <marker id="arrowG" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth">'
            f'<path d="M0,0 L0,6 L9,3 z" fill="#4CAF50"/></marker>\n'
            f'  <marker id="arrowB" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth">'
            f'<path d="M0,0 L0,6 L9,3 z" fill="#2196F3"/></marker>\n'
            f'</defs>\n'
        ]

    def title(self, text, color='#1a202c'):
        self.parts.append(
            f'<text x="{self.w/2:.0f}" y="38" text-anchor="middle" font-size="22" font-weight="700" fill="{color}">'
            f'{html.escape(str(text))}</text>\n'
            f'<line x1="40" y1="56" x2="{self.w-40:.0f}" y2="56" stroke="{GRAY}" stroke-width="1" '
            f'stroke-dasharray="4,3" opacity="0.4"/>\n'
        )
        return self

    def rect(self, x, y, w, h, fill, stroke='#37474F', sw=1.5, rx=6, opacity=1.0, dashed=False):
        dash = ' stroke-dasharray="5,3"' if dashed else ''
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" ry="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{opacity}"{dash}/>'
        )
        return self

    def text(self, x, y, s, size=14, fill='#1a202c', weight='normal', anchor='middle', italic=False):
        fs = ' font-style="italic"' if italic else ''
        self.parts.append(
            f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}"{fs}>{html.escape(str(s))}</text>'
        )
        return self

    def line(self, x1, y1, x2, y2, color='#37474F', width=2, marker=None, dashed=False):
        m = f' marker-end="url(#{marker})"' if marker else ''
        dash = ' stroke-dasharray="4,3"' if dashed else ''
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{width}"{m}{dash}/>'
        )
        return self

    def arrow(self, x1, y1, x2, y2, color='#37474F', width=2, marker='arrow', dashed=False):
        return self.line(x1, y1, x2, y2, color, width, marker, dashed)

    def circle(self, cx, cy, r, fill, stroke='#37474F', sw=2, opacity=0.4, dashed=False):
        dash = ' stroke-dasharray="3,2"' if dashed else ''
        self.parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" fill-opacity="{opacity}" '
            f'stroke="{stroke}" stroke-width="{sw}"{dash}/>'
        )
        return self

    def polyline(self, points, color, width=3, fill='none'):
        pts = ' '.join(f'{x},{y}' for x, y in points)
        self.parts.append(
            f'<polyline points="{pts}" fill="{fill}" stroke="{color}" stroke-width="{width}"/>'
        )
        return self

    def legend(self, items, x=40, y=540, w=720):
        out = [f'<rect x="{x-10}" y="{y-20}" width="{w+20}" height="50" rx="6" fill="#FAFAFA" stroke="#E0E0E0" stroke-width="1"/>']
        n = len(items)
        item_w = w / n
        for i, (c, label) in enumerate(items):
            ix = x + i * item_w
            out.append(f'<rect x="{ix}" y="{y-10}" width="16" height="16" rx="3" fill="{c}" stroke="#37474F" stroke-width="1"/>')
            out.append(f'<text x="{ix + 22}" y="{y + 3}" font-size="12" fill="#37474F" text-anchor="start">{html.escape(label)}</text>')
        self.parts.append(''.join(out) + '\n')
        return self

    def raw(self, s):
        self.parts.append(s)
        return self

    def render(self):
        self.parts.append('</svg>\n')
        return ''.join(self.parts)


# ---------------- Per-question diagram generators ----------------

def gen_jvm_memory_areas():
    s = SVG(800, 500).title('JVM 运行时数据区域划分')
    s.rect(40, 90, 340, 360, '#E3F2FD', stroke=BLUE, sw=2, rx=10)
    s.text(210, 115, '线程私有（Per-Thread）', 17, BLUE, '700')
    s.rect(70, 140, 280, 80, '#BBDEFB', stroke=BLUE)
    s.text(210, 165, '虚拟机栈 (VM Stack)', 15, '#0D47A1', '700')
    s.text(210, 188, '栈帧：局部变量表 / 操作数栈', 12, '#1565C0')
    s.text(210, 205, '动态链接 / 返回地址', 12, '#1565C0')
    s.rect(70, 240, 280, 60, '#BBDEFB', stroke=BLUE)
    s.text(210, 265, '本地方法栈', 15, '#0D47A1', '700')
    s.text(210, 288, 'Native 方法调用', 12, '#1565C0')
    s.rect(70, 320, 280, 60, '#BBDEFB', stroke=BLUE)
    s.text(210, 345, '程序计数器 (PC Register)', 15, '#0D47A1', '700')
    s.text(210, 368, '当前指令地址', 12, '#1565C0')
    s.rect(70, 400, 280, 40, '#E1F5FE', stroke=GRAY, dashed=True)
    s.text(210, 425, '不会 OOM（仅 SOF）', 12, GRAY, '600')
    # 线程共享
    s.rect(420, 90, 340, 360, '#FFF3E0', stroke=ORANGE, sw=2, rx=10)
    s.text(590, 115, '线程共享（Shared）', 17, ORANGE, '700')
    s.rect(450, 140, 280, 130, '#FFE0B2', stroke=ORANGE)
    s.text(590, 165, '堆 (Heap)', 15, '#E65100', '700')
    s.text(590, 190, '新生代：Eden + S0 + S1', 12, '#BF360C')
    s.text(590, 210, '老年代：Old Gen', 12, '#BF360C')
    s.text(590, 234, '对象实例 / 数组', 12, '#BF360C')
    s.text(590, 256, 'GC 主战场', 12, RED, '600')
    s.rect(450, 290, 280, 100, '#FFE0B2', stroke=ORANGE)
    s.text(590, 315, '方法区 (Method Area)', 15, '#E65100', '700')
    s.text(590, 340, '类信息 / 常量池 / 静态变量', 12, '#BF360C')
    s.text(590, 360, 'JIT 编译代码', 12, '#BF360C')
    s.text(590, 380, 'JDK8+: 元空间(Metaspace)', 12, PURPLE, '600')
    s.rect(450, 410, 280, 30, '#FFF8E1', stroke=GRAY, dashed=True)
    s.text(590, 430, '可能 OOM', 12, RED, '600')
    return s.render()


def gen_heap_generations():
    s = SVG(800, 500).title('JVM 堆内存分代结构')
    s.rect(40, 100, 720, 320, '#FFFDE7', stroke=GRAY, sw=2, rx=8)
    s.text(400, 125, 'Java Heap（堆）', 16, '#5D4037', '700')
    s.rect(60, 150, 440, 240, '#E8F5E9', stroke=GREEN, sw=2)
    s.text(280, 175, '新生代 Young Generation', 15, GREEN, '700')
    s.rect(80, 200, 240, 170, '#C8E6C9', stroke=GREEN)
    s.text(200, 225, 'Eden (8)', 15, '#1B5E20', '700')
    s.text(200, 250, '新对象首次分配', 12, '#2E7D32')
    s.text(200, 275, 'Minor GC 触发点', 12, RED, '600')
    s.text(200, 305, '≈ 80% 新生代空间', 11, GRAY, italic=True)
    s.rect(340, 200, 70, 170, '#DCEDC8', stroke=GREEN)
    s.text(375, 225, 'S0', 14, '#33691E', '700')
    s.text(375, 248, '(1)', 11, '#558B2F')
    s.text(375, 280, 'From', 11, '#558B2F')
    s.rect(420, 200, 70, 170, '#F1F8E9', stroke=GREEN, dashed=True)
    s.text(455, 225, 'S1', 14, '#33691E', '700')
    s.text(455, 248, '(1)', 11, '#558B2F')
    s.text(455, 280, 'To', 11, '#558B2F')
    s.rect(520, 150, 220, 240, '#FFEBEE', stroke=RED, sw=2)
    s.text(630, 175, '老年代 Old Gen', 15, RED, '700')
    s.text(630, 210, '长期存活对象', 13, '#B71C1C')
    s.text(630, 240, '大对象直接分配', 13, '#B71C1C')
    s.text(630, 270, 'GC Age >= 15', 12, PURPLE, '600')
    s.text(630, 300, 'Full GC / Major GC', 12, RED, '600')
    s.arrow(280, 410, 540, 290, color=ORANGE, width=2)
    s.text(410, 360, '晋升 (Promotion)', 12, ORANGE, '600')
    s.legend([(GREEN, '新生代 复制算法'), (RED, '老年代 标记整理'), (ORANGE, '对象晋升'), (PURPLE, 'GC年龄阈值')], y=460)
    return s.render()


def gen_gc_collectors():
    s = SVG(800, 600).title('HotSpot 垃圾收集器谱系')
    s.text(200, 100, '新生代 (Young)', 15, GREEN, '700')
    s.text(600, 100, '老年代 (Old)', 15, RED, '700')
    rows = [
        ('Serial', '#81C784', 'Serial Old', '#E57373', '单线程，Client 默认'),
        ('ParNew', '#A5D6A7', 'CMS', '#FF8A65', 'CMS 配套，低停顿'),
        ('Parallel Scavenge', '#66BB6A', 'Parallel Old', '#EF5350', '高吞吐量'),
        ('G1', '#43A047', 'G1', '#E53935', 'Region 化，可预测停顿'),
        ('ZGC / Shenandoah', '#00897B', 'ZGC / Shenandoah', '#C62828', '亚毫秒级停顿'),
    ]
    y0 = 130
    rh = 70
    for i, (n, c, o, c2, desc) in enumerate(rows):
        y = y0 + i * rh
        s.rect(60, y, 240, 56, c, stroke=GREEN, sw=1.5)
        s.text(180, y + 25, n, 14, '#1B5E20', '700')
        s.rect(440, y, 240, 56, c2, stroke=RED, sw=1.5)
        s.text(560, y + 25, o, 14, '#B71C1C', '700')
        s.arrow(300, y + 28, 440, y + 28, color=GRAY, width=1.5)
        s.text(370, y + 22, '搭配', 11, GRAY)
        s.text(700, y + 25, desc, 10, GRAY, anchor='start')
    return s.render()


def gen_nio_selector():
    s = SVG(800, 500).title('NIO 多路复用模型 (Selector)')
    for i, cy in enumerate([140, 190, 240, 290]):
        s.rect(50, cy - 18, 120, 36, '#E3F2FD', stroke=BLUE)
        s.text(110, cy + 4, f'Client {i+1} (Channel)', 12, '#0D47A1', '700')
        s.arrow(170, cy, 320, 250, color=BLUE, width=1.2)
    s.rect(320, 200, 180, 100, '#FFF3E0', stroke=ORANGE, sw=2)
    s.text(410, 230, 'Selector', 16, '#E65100', '700')
    s.text(410, 252, '(事件多路复用器)', 12, '#BF360C')
    s.text(410, 275, 'OP_ACCEPT/READ/WRITE', 11, '#5D4037', italic=True)
    s.arrow(500, 250, 580, 250, color=ORANGE, width=2)
    s.rect(580, 200, 170, 100, '#E8F5E9', stroke=GREEN, sw=2)
    s.text(665, 230, 'EventLoop', 15, '#1B5E20', '700')
    s.text(665, 252, '(单线程/线程池)', 12, '#2E7D32')
    s.text(665, 275, '非阻塞 Dispatch', 11, '#388E3C', italic=True)
    s.arrow(665, 300, 665, 360, color=GREEN)
    s.rect(580, 360, 170, 60, '#F3E5F5', stroke=PURPLE)
    s.text(665, 385, 'Handler 处理读写', 13, '#4A148C', '700')
    s.text(665, 405, '基于 Buffer', 11, '#6A1B9A')
    s.rect(40, 440, 350, 50, '#FFEBEE', stroke=RED, dashed=True)
    s.text(215, 462, 'BIO：一连接一线程，阻塞', 12, RED, '600')
    s.text(215, 480, '线程数 == 连接数，浪费', 11, '#B71C1C')
    s.rect(410, 440, 350, 50, '#E8F5E9', stroke=GREEN, dashed=True)
    s.text(585, 462, 'NIO：单线程管多连接', 12, GREEN, '600')
    s.text(585, 480, '无事件时去服务其他连接', 11, '#1B5E20')
    return s.render()


def gen_cms_phases():
    s = SVG(800, 500).title('CMS 收集器工作流程（标记-清除）')
    phases = [
        ('初始标记', 'Initial Mark', RED, 'STW', '标记 GC Roots 直接关联', True),
        ('并发标记', 'Concurrent Mark', GREEN, '并发', 'GC Roots Tracing', False),
        ('重新标记', 'Remark', ORANGE, 'STW', '修正并发期间变动(SATB)', True),
        ('并发清除', 'Concurrent Sweep', GREEN, '并发', '清除死亡对象', False),
    ]
    x = 60
    pw = 160
    y = 130
    ph = 180
    for i, (cn, en, color, mode, desc, stw) in enumerate(phases):
        s.rect(x, y, pw, ph, color + '22', stroke=color, sw=2)
        s.rect(x, y, pw, 36, color, stroke=color, sw=2)
        s.text(x + pw/2, y + 23, cn, 15, '#FFFFFF', '700')
        s.text(x + pw/2, y + 56, en, 11, '#37474F', italic=True)
        tag_color = RED if stw else GREEN
        s.rect(x + 10, y + 75, pw - 20, 26, tag_color, stroke=tag_color, rx=4)
        s.text(x + pw/2, y + 92, mode, 12, '#FFFFFF', '700')
        s.text(x + pw/2, y + 125, desc, 11, '#37474F')
        s.text(x + pw/2, y + 145, f'Step {i+1}', 10, GRAY, italic=True)
        if i < len(phases) - 1:
            s.arrow(x + pw, y + ph/2, x + pw + 30, y + ph/2, color=GRAY, width=2)
        x += pw + 30
    s.rect(60, 360, 680, 60, '#FFF3E0', stroke=ORANGE, rx=6)
    s.text(400, 385, '特性：低停顿 (并发执行)，但产生内存碎片 + 浮动垃圾', 13, '#E65100', '700')
    s.text(400, 405, '退化风险：碎片过多 → Promotion Failed → Serial Old 单线程 Full GC', 12, RED, '600')
    s.legend([(RED, 'STW 停顿'), (GREEN, '并发执行')], y=450)
    return s.render()


def gen_class_loading():
    s = SVG(800, 500).title('类加载机制生命周期')
    phases = [
        ('加载', 'Loading', BLUE, '通过类加载器读取字节码\n生成 Class 对象'),
        ('验证', 'Verification', ORANGE, '文件格式/元数据/\n字节码/符号引用'),
        ('准备', 'Preparation', PURPLE, 'static 变量分配内存\n设默认零值'),
        ('解析', 'Resolution', TEAL, '常量池符号引用\n→ 直接引用'),
        ('初始化', 'Initialization', GREEN, '执行 <clinit>\nstatic 变量赋值'),
    ]
    x = 40
    pw = 132
    y = 150
    ph = 200
    for i, (cn, en, color, desc) in enumerate(phases):
        s.rect(x, y, pw, ph, color + '18', stroke=color, sw=2)
        s.rect(x, y, pw, 34, color, stroke=color)
        s.text(x + pw/2, y + 22, cn, 15, '#FFFFFF', '700')
        s.text(x + pw/2, y + 55, en, 11, color, '600', italic=True)
        lines = desc.split('\n')
        for j, line in enumerate(lines):
            s.text(x + pw/2, y + 95 + j * 22, line, 11, '#37474F')
        s.text(x + pw/2, y + 165, f'Step {i+1}', 10, GRAY, italic=True)
        if i < len(phases) - 1:
            s.arrow(x + pw, y + ph/2, x + pw + 12, y + ph/2, color=GRAY, width=2)
        x += pw + 12
    s.rect(182, 130, 396, 24, '#F3E5F5', stroke=PURPLE, dashed=True, rx=4)
    s.text(380, 146, '连接阶段 Linking', 12, PURPLE, '700')
    s.rect(40, 380, 720, 50, '#ECEFF1', stroke=GRAY, rx=6)
    s.text(400, 400, '使用 (Using) 与 卸载 (Unloading) 阶段', 13, '#37474F', '700')
    s.text(400, 420, '配合双亲委派模型保证核心类安全与唯一性', 12, GRAY, italic=True)
    return s.render()


def gen_parent_delegation():
    s = SVG(800, 600).title('双亲委派模型工作流程')
    layers = [
        ('Bootstrap ClassLoader', '启动类加载器 (C++)', '加载 JAVA_HOME/lib/rt.jar', '#B71C1C', RED, 130),
        ('Extension ClassLoader', '扩展类加载器 (Java)', '加载 JAVA_HOME/lib/ext', '#E65100', ORANGE, 230),
        ('Application ClassLoader', '应用类加载器 (Java)', '加载 classpath 用户类', '#1B5E20', GREEN, 330),
        ('Custom ClassLoader', '自定义类加载器', '继承 ClassLoader 重写 findClass', '#4A148C', PURPLE, 430),
    ]
    for name, cn, path, txt_color, color, y in layers:
        s.rect(200, y, 400, 70, color + '18', stroke=color, sw=2)
        s.rect(200, y, 400, 28, color, stroke=color)
        s.text(400, y + 19, name, 14, '#FFFFFF', '700')
        s.text(400, y + 46, cn, 11, txt_color, '600')
        s.text(400, y + 62, path, 11, '#37474F', italic=True)
    s.arrow(300, 430, 300, 200, color=BLUE, width=2.5)
    s.text(280, 320, '1. 委派父类加载', 12, BLUE, '700', anchor='end')
    s.text(280, 338, '(自底向上)', 11, BLUE, italic=True, anchor='end')
    s.arrow(500, 200, 500, 430, color=RED, width=2.5, marker='arrowR')
    s.text(520, 320, '2. 父失败则子加载', 12, RED, '700', anchor='start')
    s.text(520, 338, '(自顶向下)', 11, RED, italic=True, anchor='start')
    s.arrow(400, 530, 400, 505, color=GRAY, width=2)
    s.text(400, 555, '收到加载请求 loadClass()', 13, '#37474F', '700')
    s.rect(40, 100, 150, 70, '#E8F5E9', stroke=GREEN, rx=6)
    s.text(115, 125, '安全性', 12, GREEN, '700')
    s.text(115, 145, '防核心 API', 10, '#1B5E20')
    s.text(115, 160, '被篡改', 10, '#1B5E20')
    s.rect(610, 100, 150, 70, '#FFF3E0', stroke=ORANGE, rx=6)
    s.text(685, 125, '唯一性', 12, ORANGE, '700')
    s.text(685, 145, '避免重复', 10, '#BF360C')
    s.text(685, 160, '加载同一名', 10, '#BF360C')
    return s.render()


def gen_object_creation():
    s = SVG(800, 600).title('JVM 对象创建完整过程')
    steps = [
        ('1. 类加载检查', '遇到 new 指令\n检查常量池符号引用\n类是否已加载', BLUE),
        ('2. 分配内存', '指针碰撞(Bump)\n或 空闲列表(Free List)\nCAS+TLAB 并发安全', ORANGE),
        ('3. 初始化零值', '内存空间置零\n(不含对象头)\n字段无需赋初值可用', TEAL),
        ('4. 设置对象头', '类元数据 Klass Pointer\nHash Code / GC Age\n锁状态 Mark Word', PURPLE),
        ('5. 执行 <init>', '构造函数\n字段赋真实值\n对象才真正"可用"', GREEN),
    ]
    x = 30
    pw = 146
    y = 130
    ph = 200
    for i, (cn, desc, color) in enumerate(steps):
        s.rect(x, y, pw, ph, color + '18', stroke=color, sw=2)
        s.rect(x, y, pw, 34, color, stroke=color)
        s.text(x + pw/2, y + 22, cn, 13, '#FFFFFF', '700')
        lines = desc.split('\n')
        for j, line in enumerate(lines):
            s.text(x + pw/2, y + 70 + j * 24, line, 11, '#37474F')
        if i < len(steps) - 1:
            s.arrow(x + pw, y + ph/2, x + pw + 4, y + ph/2, color=GRAY, width=2)
        x += pw + 4
    s.rect(40, 360, 350, 120, '#FFF8E1', stroke=ORANGE, rx=6)
    s.text(215, 385, '内存分配方式对比', 13, '#E65100', '700')
    s.text(70, 410, '指针碰撞', 12, '#37474F', '700', anchor='start')
    s.text(70, 428, '堆规整 (Serial/ParNew)', 11, GRAY, anchor='start')
    s.text(70, 445, '指针移动分配', 11, GRAY, anchor='start')
    s.text(220, 410, '空闲列表', 12, '#37474F', '700', anchor='start')
    s.text(220, 428, '堆不规整 (CMS)', 11, GRAY, anchor='start')
    s.text(220, 445, '查找可用块', 11, GRAY, anchor='start')
    s.text(215, 468, '并发：CAS 重试 / TLAB', 11, PURPLE, '600', italic=True)
    s.rect(410, 360, 350, 120, '#FCE4EC', stroke=PINK, rx=6)
    s.text(585, 385, '关键陷阱：new 不是原子操作', 13, '#880E4F', '700')
    s.text(585, 410, '步骤 2/3/4 之间可能被重排序', 11, '#AD1457')
    s.text(585, 430, '可能导致"半初始化"对象泄漏', 11, '#AD1457')
    s.text(585, 455, '经典案例：DCL 单例需 volatile', 11, RED, '600')
    return s.render()


def gen_object_layout():
    s = SVG(800, 500).title('Java 对象内存布局')
    s.rect(60, 100, 680, 280, '#FAFAFA', stroke=GRAY, sw=2, rx=8)
    s.text(400, 125, 'Java Object', 16, '#37474F', '700')
    s.rect(80, 150, 640, 80, '#E1F5FE', stroke=BLUE, sw=2)
    s.text(400, 175, '对象头 (Object Header)', 14, '#0D47A1', '700')
    s.rect(90, 188, 290, 36, '#BBDEFB', stroke=BLUE)
    s.text(235, 210, 'Mark Word (8B): hash/age/lock', 11, '#0D47A1', '700')
    s.rect(420, 188, 290, 36, '#90CAF9', stroke=BLUE)
    s.text(565, 210, 'Klass Pointer (4B 压缩): 类型元数据', 11, '#0D47A1', '700')
    s.rect(80, 250, 640, 80, '#E8F5E9', stroke=GREEN, sw=2)
    s.text(400, 275, '实例数据 (Instance Data)', 14, '#1B5E20', '700')
    s.text(400, 300, '各字段值 (基本类型 / 引用)', 12, '#2E7D32')
    s.text(400, 320, 'longs/doubles → ints → shorts/chars → bytes → refs', 10, GRAY, italic=True)
    s.rect(80, 350, 640, 20, '#FFF3E0', stroke=ORANGE, sw=2)
    s.text(400, 365, '对齐填充 (Padding) → 8 字节整数倍', 11, '#E65100', '700')
    s.rect(60, 410, 680, 70, '#F3E5F5', stroke=PURPLE, rx=6)
    s.text(400, 432, 'Mark Word 锁状态复用', 12, '#4A148C', '700')
    s.text(400, 452, '无锁 → 偏向锁 → 轻量级锁 → 重量级锁 → GC 标记', 11, PURPLE)
    s.text(400, 470, '同一块内存动态复用，实现锁升级', 10, GRAY, italic=True)
    return s.render()


def gen_gc_roots():
    s = SVG(800, 500).title('GC Roots 可达性分析（如何确定垃圾）')
    s.rect(40, 100, 200, 280, '#E3F2FD', stroke=BLUE, sw=2, rx=8)
    s.text(140, 125, 'GC Roots', 15, BLUE, '700')
    roots = [
        '虚拟机栈中引用对象',
        '本地方法栈 JNI 引用',
        '方法区静态字段引用',
        '方法区常量引用',
        '同步锁 synchronized',
        'JVM 内部引用',
    ]
    for i, r in enumerate(roots):
        s.text(140, 160 + i * 30, '• ' + r, 11, '#0D47A1', anchor='start')
    s.rect(280, 110, 480, 280, '#FAFAFA', stroke=GRAY, dashed=True, rx=8)
    s.text(520, 130, '对象引用图 (Object Graph)', 13, GRAY, '700')
    s.circle(360, 180, 40, GREEN)
    s.text(360, 184, 'A', 14, '#FFFFFF', '700')
    s.circle(450, 240, 36, GREEN)
    s.text(450, 244, 'B', 13, '#FFFFFF', '700')
    s.circle(550, 180, 36, GREEN)
    s.text(550, 184, 'C', 13, '#FFFFFF', '700')
    s.arrow(396, 190, 422, 226, color=GREEN)
    s.arrow(476, 220, 524, 198, color=GREEN)
    s.arrow(240, 220, 326, 184, color=BLUE, width=2)
    s.text(280, 200, '可达', 11, GREEN, '700')
    s.circle(380, 330, 32, RED, dashed=True)
    s.text(380, 334, 'D', 12, '#FFFFFF', '700')
    s.circle(460, 330, 32, RED, dashed=True)
    s.text(460, 334, 'E', 12, '#FFFFFF', '700')
    s.arrow(410, 330, 432, 330, color=RED, dashed=True)
    s.arrow(360, 215, 372, 305, color=RED, dashed=True, marker='arrowR')
    s.text(345, 270, '断开', 11, RED, '700')
    s.text(560, 340, 'D-E 环', 11, RED, italic=True)
    s.text(560, 358, '无 GC Root 路径', 11, RED)
    s.legend([(BLUE, 'GC Roots 起点'), (GREEN, '存活 (Reachable)'), (RED, '垃圾 (Unreachable)')], y=440)
    return s.render()


def gen_g1_regions():
    s = SVG(800, 600).title('G1 收集器 Region 化堆布局')
    s.rect(40, 90, 720, 280, '#FFFDE7', stroke=GRAY, sw=2, rx=8)
    s.text(400, 115, 'Java Heap (划分为多个等大 Region, 1~32MB)', 14, '#5D4037', '700')
    cell_w = 72
    cell_h = 50
    start_x = 60
    start_y = 140
    region_types = [
        ('E', '#C8E6C9', GREEN, 'Eden'),
        ('S', '#DCEDC8', GREEN, 'Survivor'),
        ('O', '#FFCDD2', RED, 'Old'),
        ('H', '#FFE0B2', ORANGE, 'Humongous'),
        ('U', '#ECEFF1', GRAY, 'Unused'),
    ]
    layout = [
        ['E','E','S','O','O','H','H','U'],
        ['E','E','E','O','O','O','U','U'],
        ['S','E','E','O','O','H','H','U'],
        ['U','E','E','S','O','O','U','U'],
    ]
    for ri, row in enumerate(layout):
        for ci, code in enumerate(row):
            x = start_x + ci * cell_w
            y = start_y + ri * cell_h
            label, fill, stroke, _ = next(t for t in region_types if t[0] == code)
            s.rect(x, y, cell_w - 4, cell_h - 4, fill, stroke=stroke, sw=1)
            s.text(x + (cell_w-4)/2, y + (cell_h-4)/2 + 4, label, 12, '#37474F', '700')
    s.text(60, 395, '图例：', 12, '#37474F', '700', anchor='start')
    lx = 110
    for code, fill, stroke, name in region_types:
        s.rect(lx, 385, 18, 18, fill, stroke=stroke)
        s.text(lx + 22, 397, f'{code}={name}', 10, '#37474F', anchor='start')
        lx += 130
    s.rect(40, 425, 720, 150, '#ECEFF1', stroke=GRAY, rx=6)
    s.text(400, 445, 'G1 工作流程', 13, '#37474F', '700')
    flow = [
        ('年轻代 GC', 'Evacuation', GREEN),
        ('混合 GC', 'Mixed (含 Old Region)', ORANGE),
        ('Full GC', 'Fallback (单线程 Serial)', RED),
    ]
    for i, (cn, desc, color) in enumerate(flow):
        x = 80 + i * 230
        s.rect(x, 470, 200, 50, color + '22', stroke=color, sw=2)
        s.text(x + 100, 492, cn, 13, color, '700')
        s.text(x + 100, 510, desc, 10, '#37474F', italic=True)
        if i < 2:
            s.arrow(x + 200, 495, x + 230, 495, color=GRAY)
    s.text(400, 555, '可预测停顿模型：-XX:MaxGCPauseMillis 指定目标停顿时间', 11, PURPLE, '600', italic=True)
    return s.render()


def gen_tricolor_marking():
    s = SVG(800, 600).title('三色标记法 与 漏标问题')
    s.circle(180, 200, 50, '#9E9E9E')
    s.text(180, 205, 'White', 14, '#212121', '700')
    s.text(180, 270, '未访问', 12, '#616161')
    s.text(180, 288, '(候选垃圾)', 11, GRAY, italic=True)
    s.circle(400, 200, 50, '#9E9E9E')
    s.text(400, 205, 'Gray', 14, '#212121', '700')
    s.text(400, 270, '已标记', 12, '#616161')
    s.text(400, 288, '引用未扫完', 11, GRAY, italic=True)
    s.circle(620, 200, 50, '#212121')
    s.text(620, 205, 'Black', 14, '#FFFFFF', '700')
    s.text(620, 270, '已标记', 12, '#616161')
    s.text(620, 288, '引用全扫完', 11, GRAY, italic=True)
    s.arrow(235, 195, 348, 195, color=GRAY, width=2)
    s.text(290, 185, '扫描引用', 11, GRAY, '600')
    s.arrow(455, 195, 568, 195, color=GRAY, width=2)
    s.text(510, 185, '处理完引用', 11, GRAY, '600')
    s.rect(40, 330, 350, 230, '#FFEBEE', stroke=RED, sw=2, rx=6)
    s.text(215, 355, '漏标问题 (两个条件同时发生)', 13, RED, '700')
    s.text(60, 385, '1. 黑色对象 新增 → 白色引用', 12, '#B71C1C', anchor='start')
    s.text(60, 408, '2. 灰色对象 断开 → 白色引用', 12, '#B71C1C', anchor='start')
    s.text(60, 440, '结果：白色对象被误判为垃圾', 12, RED, '700', anchor='start')
    s.text(60, 460, '       导致存活对象被回收', 11, '#B71C1C', anchor='start')
    s.circle(90, 510, 14, '#212121')
    s.text(90, 513, 'B', 9, '#FFF', '700')
    s.circle(180, 510, 14, '#9E9E9E')
    s.text(180, 513, 'W', 9, '#212121', '700')
    s.arrow(104, 510, 166, 510, color=RED, marker='arrowR')
    s.text(135, 500, '+new', 10, RED, '600')
    s.rect(410, 330, 350, 230, '#E8F5E9', stroke=GREEN, sw=2, rx=6)
    s.text(585, 355, '解决方案 (写屏障)', 13, GREEN, '700')
    solutions = [
        ('CMS', '增量更新', '关注黑新增白引用', ORANGE),
        ('G1', 'SATB', '关注灰断白引用快照', PURPLE),
        ('ZGC', '染色指针+读屏障', '并发整理无需 STW', TEAL),
    ]
    for i, (impl, method, desc, color) in enumerate(solutions):
        y = 380 + i * 50
        s.rect(425, y, 320, 42, color + '22', stroke=color, sw=1.5)
        s.text(440, y + 17, impl, 12, color, '700', anchor='start')
        s.text(440, y + 33, method, 11, '#37474F', anchor='start')
        s.text(740, y + 25, desc, 10, GRAY, italic=True, anchor='end')
    return s.render()


def gen_zgc_colored_pointer():
    s = SVG(800, 600).title('ZGC 染色指针 + 读屏障')
    s.rect(60, 110, 680, 70, '#ECEFF1', stroke=GRAY, sw=2)
    s.text(400, 132, '64-bit 指针布局 (ZGC)', 14, '#37474F', '700')
    s.rect(80, 145, 100, 28, '#E0E0E0', stroke=GRAY)
    s.text(130, 163, '16 bits 未用', 11, '#616161')
    s.rect(180, 145, 60, 28, '#FFEB3B', stroke=ORANGE, sw=2)
    s.text(210, 163, '4 bits', 11, '#E65100', '700')
    s.rect(240, 145, 280, 28, '#C8E6C9', stroke=GREEN, sw=2)
    s.text(380, 163, '44 bits 堆地址 (支持 4TB~16TB)', 11, '#1B5E20', '700')
    s.text(530, 163, '... (64-bit total)', 10, GRAY, italic=True, anchor='start')
    s.text(400, 215, '染色指针 4 bits 元数据 (Marked0/Marked1/Remapped/Finalizable)', 13, '#E65100', '700')
    states = [
        ('Marked0', 'M0', '#BBDEFB', '标记阶段 1 引用'),
        ('Marked1', 'M1', '#90CAF9', '标记阶段 2 引用'),
        ('Remapped', 'R', '#C8E6C9', '已转移到新地址'),
        ('Finalizable', 'F', '#FFCDD2', '通过 finalize 创建'),
    ]
    for i, (name, code, fill, desc) in enumerate(states):
        x = 70 + i * 175
        s.rect(x, 230, 160, 100, fill, stroke=GRAY, sw=1.5)
        s.text(x + 80, 255, code, 20, '#212121', '700')
        s.text(x + 80, 280, name, 12, '#37474F', '700')
        s.text(x + 80, 300, desc, 10, GRAY, italic=True)
        s.text(x + 80, 320, '指针自带状态', 9, GRAY)
    s.rect(60, 360, 680, 170, '#FFF3E0', stroke=ORANGE, rx=6)
    s.text(400, 385, '读屏障工作流程 (并发转移)', 14, '#E65100', '700')
    s.text(80, 415, '应用读取对象引用', 12, '#37474F', '700', anchor='start')
    s.arrow(220, 410, 280, 410, color=GRAY)
    s.rect(280, 395, 160, 32, '#FFE0B2', stroke=ORANGE)
    s.text(360, 415, '读屏障拦截', 12, '#E65100', '700')
    s.arrow(440, 410, 500, 410, color=GRAY)
    s.rect(500, 395, 220, 32, '#C8E6C9', stroke=GREEN)
    s.text(610, 415, '检查染色 → 转发指针', 12, '#1B5E20', '700')
    s.text(400, 460, '若指针过期：自动转发到新地址 (Forwarding Table)', 11, '#BF360C', anchor='start')
    s.text(400, 480, '更新引用 = 即时修正 (Self-healing)', 11, '#BF360C', anchor='start')
    s.text(400, 505, '结果：标记/转移/重定位 全程并发，停顿 < 1ms', 12, GREEN, '700')
    return s.render()


def gen_oom_vs_leak():
    s = SVG(800, 500).title('内存溢出 (OOM) vs 内存泄漏 (Leak)')
    s.rect(40, 90, 350, 350, '#E8F5E9', stroke=GREEN, sw=2, rx=8)
    s.text(215, 115, '内存泄漏 (Memory Leak)', 15, GREEN, '700')
    s.text(215, 138, '无用对象未释放，逐渐累积', 11, '#1B5E20', italic=True)
    s.rect(80, 180, 250, 200, '#FAFAFA', stroke=GRAY)
    s.text(95, 200, '内存使用', 10, GRAY, anchor='start')
    points = [(80,370), (110,360), (140,345), (170,335), (200,310), (230,290), (260,260), (290,220), (320,180)]
    s.polyline(points, RED)
    s.arrow(80, 380, 330, 380, color=GRAY, width=1)
    s.arrow(80, 380, 80, 175, color=GRAY, width=1)
    s.text(205, 397, '时间 →', 10, GRAY)
    s.text(70, 280, '内存', 10, GRAY)
    s.text(360, 180, 'OOM!', 12, RED, '700', anchor='end')
    s.text(215, 425, '静态集合/未关闭资源/ThreadLocal', 10, GRAY, italic=True)
    s.rect(410, 90, 350, 350, '#FFEBEE', stroke=RED, sw=2, rx=8)
    s.text(585, 115, '内存溢出 (OOM)', 15, RED, '700')
    s.text(585, 138, '分配时内存不够 (一次事件)', 11, '#B71C1C', italic=True)
    s.rect(450, 180, 250, 200, '#FAFAFA', stroke=GRAY)
    s.text(465, 200, '内存使用', 10, GRAY, anchor='start')
    s.rect(470, 320, 100, 50, '#90CAF9', stroke=BLUE)
    s.text(520, 350, '正常', 11, '#0D47A1', '700')
    s.arrow(570, 345, 600, 240, color=RED, width=2.5, marker='arrowR')
    s.text(590, 290, '申请大对象', 11, RED, '700')
    s.rect(600, 200, 90, 60, '#EF5350', stroke=RED)
    s.text(645, 225, '超限', 12, '#FFF', '700')
    s.text(645, 245, 'OOM!', 11, '#FFF', '700')
    s.arrow(450, 380, 700, 380, color=GRAY, width=1)
    s.text(575, 397, '时间 →', 10, GRAY)
    s.text(585, 425, '堆/元空间/栈/直接内存', 10, GRAY, italic=True)
    s.legend([(GREEN, '泄漏=慢性病'), (RED, '溢出=急性病'), (BLUE, '正常使用')], y=470)
    return s.render()


def gen_escape_analysis():
    s = SVG(800, 500).title('逃逸分析 与 三大优化')
    s.rect(40, 100, 250, 280, '#ECEFF1', stroke=GRAY, sw=2, rx=8)
    s.text(165, 125, '方法内对象', 14, '#37474F', '700')
    s.rect(60, 150, 210, 50, '#C8E6C9', stroke=GREEN)
    s.text(165, 175, '未逃逸 (No Escape)', 13, '#1B5E20', '700')
    s.text(165, 195, '局部使用，方法结束即销毁', 10, '#2E7D32', italic=True)
    s.rect(60, 220, 210, 50, '#FFE0B2', stroke=ORANGE)
    s.text(165, 245, '方法逃逸 (Method Escape)', 13, '#E65100', '700')
    s.text(165, 265, '返回/被外部引用', 10, '#BF360C', italic=True)
    s.rect(60, 290, 210, 50, '#FFCDD2', stroke=RED)
    s.text(165, 315, '线程逃逸 (Thread Escape)', 13, '#B71C1C', '700')
    s.text(165, 335, '赋值给静态/全局字段', 10, '#B71C1C', italic=True)
    s.text(165, 365, 'JIT 编译期分析对象作用域', 10, GRAY, italic=True)
    s.text(490, 125, '未逃逸 → 三种优化', 14, GREEN, '700')
    optis = [
        ('栈上分配', 'Stack Allocation', '对象分配到栈帧\n随栈帧弹出回收\n减少 GC 压力', GREEN, 150),
        ('锁消除', 'Lock Elision', '同步块无竞争\n自动去掉 synchronized\n经典: string concat', PURPLE, 250),
        ('标量替换', 'Scalar Replacement', '对象拆解为字段\n分散到寄存器\n避免内存分配', ORANGE, 350),
    ]
    s.arrow(290, 175, 350, 230, color=GREEN, width=2)
    for name, en, desc, color, y in optis:
        s.rect(350, y, 410, 80, color + '22', stroke=color, sw=2)
        s.text(365, y + 25, name, 14, color, '700', anchor='start')
        s.text(365, y + 42, en, 10, GRAY, italic=True, anchor='start')
        lines = desc.split('\n')
        for j, line in enumerate(lines):
            s.text(540, y + 22 + j * 18, line, 11, '#37474F', anchor='start')
    return s.render()


def gen_jmm():
    s = SVG(800, 500).title('Java 内存模型 (JMM)')
    s.rect(40, 110, 220, 340, '#E3F2FD', stroke=BLUE, sw=2, rx=8)
    s.text(150, 135, '主内存 (Main Memory)', 15, BLUE, '700')
    s.rect(60, 160, 180, 50, '#BBDEFB', stroke=BLUE)
    s.text(150, 180, '共享变量', 12, '#0D47A1', '700')
    s.text(150, 198, 'static field / heap', 10, '#1565C0', italic=True)
    s.rect(60, 230, 180, 50, '#BBDEFB', stroke=BLUE)
    s.text(150, 250, '实例字段', 12, '#0D47A1', '700')
    s.text(150, 268, 'instance fields', 10, '#1565C0', italic=True)
    s.rect(60, 300, 180, 50, '#BBDEFB', stroke=BLUE)
    s.text(150, 320, '数组元素', 12, '#0D47A1', '700')
    s.text(150, 338, 'array elements', 10, '#1565C0', italic=True)
    s.text(150, 400, '所有线程共享', 11, GRAY, italic=True)
    for i, (tx, tcolor) in enumerate([(420, GREEN), (420, ORANGE)]):
        ty = 110 if i == 0 else 280
        s.rect(tx, ty, 320, 150, tcolor + '18', stroke=tcolor, sw=2, rx=8)
        s.text(tx + 160, ty + 25, f'线程 {i+1}', 14, tcolor, '700')
        s.rect(tx + 20, ty + 45, 130, 40, '#FAFAFA', stroke=tcolor)
        s.text(tx + 85, ty + 60, '工作内存', 11, tcolor, '700')
        s.text(tx + 85, ty + 78, 'Working Memory', 9, GRAY, italic=True)
        s.rect(tx + 160, ty + 45, 140, 40, '#FAFAFA', stroke=tcolor)
        s.text(tx + 230, ty + 60, '执行引擎', 11, tcolor, '700')
        s.text(tx + 230, ty + 78, 'CPU Registers', 9, GRAY, italic=True)
        s.text(tx + 160, ty + 110, '变量副本 + 操作缓冲', 10, '#37474F', italic=True)
    s.arrow(260, 180, 420, 175, color=GREEN, width=2)
    s.text(340, 168, 'read/load', 10, GREEN, '600')
    s.arrow(420, 195, 260, 215, color=GREEN, width=2, marker='arrowG')
    s.text(340, 235, 'store/write', 10, GREEN, '600')
    s.arrow(260, 340, 420, 340, color=ORANGE, width=2)
    s.text(340, 332, 'read/load', 10, ORANGE, '600')
    s.arrow(420, 360, 260, 380, color=ORANGE, width=2)
    s.text(340, 395, 'store/write', 10, ORANGE, '600')
    s.text(400, 470, '8 大原子操作 + happens-before 保证可见性与有序性', 12, PURPLE, '600', italic=True)
    return s.render()


def gen_jit_compiler():
    s = SVG(800, 600).title('JIT 即时编译器分层模型')
    layers = [
        ('第 0层', '解释执行', '启动快，无监控', '#ECEFF1', GRAY, 150),
        ('第 1层 (C1)', '简单编译', '可靠优化，无监控', '#C8E6C9', GREEN, 230),
        ('第 2层 (C1)', '有限监控', '方法调用/回边次数', '#DCEDC8', GREEN, 310),
        ('第 3层 (C1)', '完整监控', '分支/类型继承信息', '#A5D6A7', GREEN, 390),
        ('第 4层 (C2)', '深度优化', '激进优化，最高性能', '#FFCDD2', RED, 470),
    ]
    for name, cn, desc, fill, color, y in layers:
        s.rect(80, y, 640, 60, fill, stroke=color, sw=2)
        s.rect(80, y, 140, 60, color, stroke=color)
        s.text(150, y + 28, name, 13, '#FFFFFF', '700')
        s.text(150, y + 47, cn, 11, '#FFFFFF', '600')
        s.text(310, y + 28, desc, 12, '#37474F', anchor='start')
        s.text(680, y + 35, f'y={5-(y-150)//80}', 10, GRAY, italic=True, anchor='end')
    s.arrow(50, 175, 75, 175, color=BLUE, width=2)
    s.text(35, 180, '启动', 11, BLUE, '700', anchor='end')
    s.arrow(400, 210, 400, 230, color=GREEN, width=2)
    s.arrow(400, 290, 400, 310, color=GREEN, width=2)
    s.arrow(400, 370, 400, 390, color=GREEN, width=2)
    s.arrow(400, 450, 400, 470, color=RED, width=2.5, marker='arrowR')
    s.text(420, 460, '热点触发', 11, RED, '700', anchor='start')
    s.rect(40, 90, 350, 50, '#E8F5E9', stroke=GREEN, rx=6)
    s.text(215, 110, '解释器 (Interpreter)', 13, GREEN, '700')
    s.text(215, 130, '逐行翻译，启动快，性能低', 11, '#1B5E20', italic=True)
    s.rect(410, 90, 350, 50, '#FFEBEE', stroke=RED, rx=6)
    s.text(585, 110, '编译器 (JIT Compiler)', 13, RED, '700')
    s.text(585, 130, '编译本地码，启动慢，性能高', 11, '#B71C1C', italic=True)
    s.arrow(700, 470, 730, 470, color=GRAY, width=1.5, dashed=True)
    s.arrow(730, 470, 730, 180, color=GRAY, width=1.5, dashed=True)
    s.arrow(730, 180, 720, 180, color=GRAY, width=1.5, dashed=True)
    s.text(740, 320, '激进优化失败\n退回解释器', 10, GRAY, italic=True, anchor='start')
    return s.render()


def gen_tomcat_classloader():
    s = SVG(800, 600).title('Tomcat 类加载机制（破坏双亲委派）')
    layers_top = [
        ('Bootstrap', 'rt.jar 核心', '#B71C1C', RED, 100),
        ('System (App)', 'CLASSPATH (Tomcat 启动)', '#1B5E20', GREEN, 175),
        ('Common', 'CATALINA_HOME/lib 共享', '#E65100', ORANGE, 250),
    ]
    for name, path, txt, color, y in layers_top:
        s.rect(120, y, 560, 60, color + '22', stroke=color, sw=2)
        s.rect(120, y, 140, 60, color, stroke=color)
        s.text(190, y + 28, name, 12, '#FFFFFF', '700')
        s.text(190, y + 47, 'ClassLoader', 9, '#FFFFFF', italic=True)
        s.text(290, y + 35, path, 12, txt, '600', anchor='start')
    s.arrow(400, 310, 250, 325, color=GRAY, width=1.5)
    s.arrow(400, 310, 550, 325, color=GRAY, width=1.5)
    s.rect(120, 325, 220, 60, '#79554822', stroke='#795548', sw=2)
    s.rect(120, 325, 100, 60, '#795548', stroke='#795548')
    s.text(170, 352, 'Catalina', 11, '#FFFFFF', '700')
    s.text(170, 370, 'Tomcat 自身', 9, '#FFFFFF', italic=True)
    s.text(245, 360, 'catalina.jar', 10, '#5D4037', anchor='start')
    s.rect(460, 325, 220, 60, '#1565C022', stroke=BLUE, sw=2)
    s.rect(460, 325, 100, 60, BLUE, stroke=BLUE)
    s.text(510, 352, 'Shared', 11, '#FFFFFF', '700')
    s.text(510, 370, '共享类', 9, '#FFFFFF', italic=True)
    s.text(585, 360, 'shared/lib', 10, '#1565C0', anchor='start')
    s.arrow(400, 385, 280, 425, color=PURPLE, width=2)
    s.arrow(400, 385, 520, 425, color=PURPLE, width=2)
    s.rect(120, 425, 320, 60, '#4A148C22', stroke=PURPLE, sw=2)
    s.rect(120, 425, 120, 60, PURPLE, stroke=PURPLE)
    s.text(180, 452, 'WebApp 1', 11, '#FFFFFF', '700')
    s.text(180, 470, 'WebAppClassLoader', 9, '#FFFFFF', italic=True)
    s.text(255, 452, 'WEB-INF/classes', 10, '#4A148C', '700', anchor='start')
    s.text(255, 470, 'WEB-INF/lib/*.jar', 10, '#4A148C', anchor='start')
    s.rect(460, 425, 320, 60, '#4A148C22', stroke=PURPLE, sw=2)
    s.rect(460, 425, 120, 60, PURPLE, stroke=PURPLE)
    s.text(520, 452, 'WebApp 2', 11, '#FFFFFF', '700')
    s.text(520, 470, 'WebAppClassLoader', 9, '#FFFFFF', italic=True)
    s.text(595, 452, 'Spring 5.x 版本', 10, '#4A148C', '700', anchor='start')
    s.text(595, 470, '可不同于 WebApp 1', 10, '#4A148C', anchor='start')
    s.rect(40, 510, 720, 70, '#FFEBEE', stroke=RED, rx=6)
    s.text(400, 532, '加载策略：优先自己加载 (破坏双亲委派)', 13, '#B71C1C', '700')
    s.text(400, 552, 'WebApp → Local → Shared → Common → System → Bootstrap', 11, '#37474F')
    s.text(400, 570, 'java.* 等核心类仍走双亲委派，保证安全', 10, GRAY, italic=True)
    return s.render()


def gen_memory_model_runtime():
    s = SVG(800, 500).title('JVM 运行时数据区 (综合视图)')
    s.rect(30, 90, 740, 360, '#FAFAFA', stroke=GRAY, sw=2, rx=10)
    s.text(400, 115, 'JVM 进程', 16, '#37474F', '700')
    s.rect(50, 140, 130, 290, '#E3F2FD', stroke=BLUE, sw=2)
    s.text(115, 160, 'Thread 1', 13, BLUE, '700')
    s.rect(60, 175, 110, 60, '#BBDEFB', stroke=BLUE)
    s.text(115, 200, 'PC 寄存器', 11, '#0D47A1', '700')
    s.text(115, 218, '当前指令', 9, '#1565C0', italic=True)
    s.rect(60, 245, 110, 80, '#BBDEFB', stroke=BLUE)
    s.text(115, 270, '虚拟机栈', 11, '#0D47A1', '700')
    s.text(115, 288, '栈帧 Frame', 9, '#1565C0', italic=True)
    s.text(115, 305, '[Frame 1]', 9, '#1565C0')
    s.text(115, 318, '[Frame 2]', 9, '#1565C0')
    s.rect(60, 335, 110, 80, '#BBDEFB', stroke=BLUE)
    s.text(115, 360, '本地方法栈', 11, '#0D47A1', '700')
    s.text(115, 378, 'Native', 9, '#1565C0', italic=True)
    s.text(115, 395, '方法调用', 9, '#1565C0', italic=True)
    s.rect(190, 140, 130, 290, '#E1F5FE', stroke=BLUE, sw=2)
    s.text(255, 160, 'Thread 2', 13, BLUE, '700')
    s.rect(200, 175, 110, 60, '#B3E5FC', stroke=BLUE)
    s.text(255, 200, 'PC 寄存器', 11, '#01579B', '700')
    s.text(255, 218, '当前指令', 9, '#0277BD', italic=True)
    s.rect(200, 245, 110, 80, '#B3E5FC', stroke=BLUE)
    s.text(255, 270, '虚拟机栈', 11, '#01579B', '700')
    s.text(255, 288, '栈帧 Frame', 9, '#0277BD', italic=True)
    s.rect(200, 335, 110, 80, '#B3E5FC', stroke=BLUE)
    s.text(255, 360, '本地方法栈', 11, '#01579B', '700')
    s.rect(340, 140, 250, 200, '#FFF3E0', stroke=ORANGE, sw=2)
    s.text(465, 165, '堆 (Heap) [共享]', 13, ORANGE, '700')
    s.rect(355, 185, 220, 60, '#FFE0B2', stroke=ORANGE)
    s.text(465, 210, '新生代', 12, '#E65100', '700')
    s.text(465, 230, 'Eden | S0 | S1', 10, '#BF360C', italic=True)
    s.rect(355, 255, 220, 70, '#FFCCBC', stroke=RED)
    s.text(465, 280, '老年代', 12, '#B71C1C', '700')
    s.text(465, 302, '长寿命对象', 10, '#D84315', italic=True)
    s.text(465, 320, '大对象直接分配', 10, '#D84315', italic=True)
    s.rect(340, 360, 250, 70, '#F3E5F5', stroke=PURPLE, sw=2)
    s.text(465, 385, '方法区 (共享)', 13, PURPLE, '700')
    s.text(465, 405, '类信息/常量池/静态变量', 10, '#6A1B9A')
    s.text(465, 420, 'JDK8+: 元空间(本地内存)', 9, '#4A148C', italic=True)
    s.rect(610, 140, 140, 290, '#ECEFF1', stroke=GRAY, sw=2, rx=6)
    s.text(680, 165, '直接内存', 13, GRAY, '700')
    s.text(680, 188, '(Direct Memory)', 10, '#455A64', italic=True)
    s.text(680, 220, 'NIO Buffer', 11, '#37474F')
    s.text(680, 240, '通过 unsafe', 10, GRAY, italic=True)
    s.text(680, 258, 'allocateMemory', 10, GRAY, italic=True)
    s.text(680, 295, '不受 -Xmx', 10, RED, '600')
    s.text(680, 312, '限制', 10, RED, '600')
    s.text(680, 360, '可能 OOM:', 10, RED, '700')
    s.text(680, 378, 'DirectMemory', 9, '#B71C1C')
    s.text(680, 395, 'buffer OOM', 9, '#B71C1C')
    s.legend([(BLUE, '线程私有'), (ORANGE, '堆共享'), (PURPLE, '方法区'), (GRAY, '直接内存')], y=470)
    return s.render()


def gen_method_area():
    s = SVG(800, 500).title('方法区（永久代/元空间）')
    s.rect(40, 90, 720, 80, '#F3E5F5', stroke=PURPLE, sw=2)
    s.text(400, 115, '方法区 Method Area (JVM 规范)', 15, PURPLE, '700')
    s.text(400, 140, '存储：类信息 / 常量池 / 静态变量 / JIT 编译代码', 12, '#4A148C')
    s.rect(40, 200, 350, 200, '#FFEBEE', stroke=RED, sw=2)
    s.rect(40, 200, 350, 40, RED, stroke=RED)
    s.text(215, 225, 'JDK 7 及之前：永久代 (PermGen)', 13, '#FFFFFF', '700')
    s.text(60, 270, '- XX:PermSize / -XX:MaxPermSize', 11, '#B71C1C', anchor='start')
    s.text(60, 295, '位于 JVM 堆内存', 11, '#B71C1C', anchor='start')
    s.text(60, 320, '大小固定，易 OOM', 11, RED, '700', anchor='start')
    s.text(60, 350, 'java.lang.OutOfMemoryError:', 10, '#B71C1C', anchor='start')
    s.text(60, 368, '  PermGen space', 10, '#B71C1C', anchor='start')
    s.text(60, 388, '字符串常量池在此 (JDK6-)', 10, '#B71C1C', italic=True, anchor='start')
    s.rect(410, 200, 350, 200, '#E8F5E9', stroke=GREEN, sw=2)
    s.rect(410, 200, 350, 40, GREEN, stroke=GREEN)
    s.text(585, 225, 'JDK 8+：元空间 (Metaspace)', 13, '#FFFFFF', '700')
    s.text(430, 270, '- XX:MetaspaceSize / -XX:MaxMetaspaceSize', 11, '#1B5E20', anchor='start')
    s.text(430, 295, '位于本地内存 (Native Memory)', 11, '#1B5E20', anchor='start')
    s.text(430, 320, '大小动态，受系统内存限制', 11, GREEN, '700', anchor='start')
    s.text(430, 350, '不易 OOM (除非系统内存满)', 10, '#1B5E20', anchor='start')
    s.text(430, 368, '类元数据迁移至此', 10, '#1B5E20', anchor='start')
    s.text(430, 388, '字符串常量池 → 堆 (JDK7+)', 10, '#1B5E20', italic=True, anchor='start')
    s.legend([(RED, '永久代 PermGen'), (GREEN, '元空间 Metaspace'), (PURPLE, '方法区(抽象)')], y=430)
    return s.render()


def gen_permgen_vs_metaspace():
    s = SVG(800, 500).title('永久代 (PermGen) vs 元空间 (Metaspace)')
    s.rect(40, 100, 350, 320, '#FFEBEE', stroke=RED, sw=2, rx=8)
    s.text(215, 125, '永久代 PermGen', 16, RED, '700')
    s.text(215, 150, '(JDK 7 及之前)', 11, '#B71C1C', italic=True)
    s.rect(60, 175, 310, 40, '#FFCDD2', stroke=RED)
    s.text(215, 200, '位置：JVM 堆内存', 12, '#B71C1C', '700')
    s.rect(60, 225, 310, 40, '#FFCDD2', stroke=RED)
    s.text(215, 250, '大小：固定 (-XX:MaxPermSize)', 11, '#B71C1C', '700')
    s.rect(60, 275, 310, 40, '#FFCDD2', stroke=RED)
    s.text(215, 300, '易 OOM: PermGen space', 11, RED, '700')
    s.rect(60, 325, 310, 40, '#FFCDD2', stroke=RED)
    s.text(215, 350, '存：类信息/常量池/静态变量', 11, '#B71C1C')
    s.rect(60, 375, 310, 30, '#FFE0B2', stroke=ORANGE, dashed=True)
    s.text(215, 395, '字符串常量池 (JDK6-)', 11, '#E65100', italic=True)
    s.rect(410, 100, 350, 320, '#E8F5E9', stroke=GREEN, sw=2, rx=8)
    s.text(585, 125, '元空间 Metaspace', 16, GREEN, '700')
    s.text(585, 150, '(JDK 8+)', 11, '#1B5E20', italic=True)
    s.rect(430, 175, 310, 40, '#C8E6C9', stroke=GREEN)
    s.text(585, 200, '位置：本地内存 (Native)', 12, '#1B5E20', '700')
    s.rect(430, 225, 310, 40, '#C8E6C9', stroke=GREEN)
    s.text(585, 250, '大小：动态 (系统内存限制)', 11, '#1B5E20', '700')
    s.rect(430, 275, 310, 40, '#C8E6C9', stroke=GREEN)
    s.text(585, 300, '不易 OOM', 11, GREEN, '700')
    s.rect(430, 325, 310, 40, '#C8E6C9', stroke=GREEN)
    s.text(585, 350, '存：类元数据 (Klass)', 11, '#1B5E20')
    s.rect(430, 375, 310, 30, '#FFF8E1', stroke=ORANGE, dashed=True)
    s.text(585, 395, '字符串常量池 → 堆 (JDK7+)', 11, '#E65100', italic=True)
    s.text(400, 450, '迁移原因：调优困难 + 便于与 JRockit 融合', 12, PURPLE, '600', italic=True)
    return s.render()


def gen_jdk18_metaspace():
    s = SVG(800, 500).title('JDK 1.8 为何用元空间替代永久代？')
    s.rect(40, 100, 720, 60, '#E3F2FD', stroke=BLUE, sw=2, rx=6)
    s.text(400, 130, '核心动机：解决 PermGen OOM 调优困难', 14, BLUE, '700')
    s.text(400, 150, '同时为 HotSpot 与 JRockit 融合铺路', 11, '#1565C0', italic=True)
    s.rect(40, 180, 340, 240, '#FFEBEE', stroke=RED, sw=2)
    s.rect(40, 180, 340, 32, RED, stroke=RED)
    s.text(210, 201, '永久代 痛点', 14, '#FFFFFF', '700')
    s.text(60, 240, '1. 大小固定，需手动调优', 12, '#B71C1C', anchor='start')
    s.text(60, 265, '   -XX:MaxPermSize 难预估', 11, '#D84315', italic=True, anchor='start')
    s.text(60, 295, '2. 动态生成类易 OOM', 12, '#B71C1C', anchor='start')
    s.text(60, 320, '   CGLIB/Spring AOP/反射代理', 11, '#D84315', italic=True, anchor='start')
    s.text(60, 350, '3. 字符串常量池占用大', 12, '#B71C1C', anchor='start')
    s.text(60, 375, '   JDK6- intern 都进 PermGen', 11, '#D84315', italic=True, anchor='start')
    s.text(60, 400, '4. GC 效率低', 12, '#B71C1C', anchor='start')
    s.rect(420, 180, 340, 240, '#E8F5E9', stroke=GREEN, sw=2)
    s.rect(420, 180, 340, 32, GREEN, stroke=GREEN)
    s.text(590, 201, '元空间 优势', 14, '#FFFFFF', '700')
    s.text(440, 240, '1. 使用本地内存', 12, '#1B5E20', anchor='start')
    s.text(440, 265, '   突破 JVM 堆上限', 11, '#388E3C', italic=True, anchor='start')
    s.text(440, 295, '2. 大小动态伸缩', 12, '#1B5E20', anchor='start')
    s.text(440, 320, '   -XX:MaxMetaspaceSize 兜底', 11, '#388E3C', italic=True, anchor='start')
    s.text(440, 350, '3. 字符串常量池移到堆', 12, '#1B5E20', anchor='start')
    s.text(440, 375, '   可被 GC 正常回收', 11, '#388E3C', italic=True, anchor='start')
    s.text(440, 400, '4. 类卸载更高效', 12, '#1B5E20', anchor='start')
    s.legend([(RED, 'PermGen 缺点'), (GREEN, 'Metaspace 优点'), (BLUE, '动机')], y=445)
    return s.render()


def gen_vm_stack():
    s = SVG(800, 600).title('虚拟机栈结构与栈帧组成')
    s.rect(40, 90, 720, 380, '#E3F2FD', stroke=BLUE, sw=2, rx=8)
    s.text(400, 115, '虚拟机栈 (VM Stack) - 线程私有', 16, BLUE, '700')
    s.rect(80, 145, 640, 70, '#90CAF9', stroke=BLUE, sw=2)
    s.text(400, 175, '当前方法栈帧 (Top of Stack)', 13, '#0D47A1', '700')
    s.text(400, 198, 'push: 方法调用', 11, '#1565C0', italic=True)
    s.arrow(720, 180, 745, 180, color=GREEN, width=2)
    s.text(760, 184, '↑ push', 10, GREEN, '700', anchor='start')
    s.rect(80, 225, 640, 50, '#BBDEFB', stroke=BLUE)
    s.text(400, 255, '上层方法栈帧 (Caller)', 12, '#0D47A1', '700')
    s.rect(80, 285, 640, 50, '#BBDEFB', stroke=BLUE)
    s.text(400, 315, 'main() 栈帧 (Bottom)', 12, '#0D47A1', '700')
    s.arrow(720, 340, 745, 340, color=RED, width=2, marker='arrowR')
    s.text(760, 344, '↓ pop', 10, RED, '700', anchor='start')
    s.rect(80, 360, 640, 100, '#FFFDE7', stroke=ORANGE, sw=2)
    s.text(400, 382, '栈帧内部结构 (4 组件)', 13, '#E65100', '700')
    s.rect(100, 395, 130, 55, '#FFE0B2', stroke=ORANGE)
    s.text(165, 418, '局部变量表', 11, '#E65100', '700')
    s.text(165, 436, 'Slot[0]=this', 9, '#BF360C', italic=True)
    s.rect(240, 395, 130, 55, '#FFE0B2', stroke=ORANGE)
    s.text(305, 418, '操作数栈', 11, '#E65100', '700')
    s.text(305, 436, 'LIFO', 9, '#BF360C', italic=True)
    s.rect(380, 395, 130, 55, '#FFE0B2', stroke=ORANGE)
    s.text(445, 418, '动态链接', 11, '#E65100', '700')
    s.text(445, 436, '符号→直接', 9, '#BF360C', italic=True)
    s.rect(520, 395, 180, 55, '#FFE0B2', stroke=ORANGE)
    s.text(610, 418, '方法返回地址', 11, '#E65100', '700')
    s.text(610, 436, '恢复 PC 寄存器', 9, '#BF360C', italic=True)
    s.rect(40, 490, 350, 50, '#FFEBEE', stroke=RED, dashed=True)
    s.text(215, 510, 'StackOverflowError', 12, RED, '700')
    s.text(215, 528, '递归过深 / -Xss 过小', 10, '#B71C1C', italic=True)
    s.rect(410, 490, 350, 50, '#FFEBEE', stroke=RED, dashed=True)
    s.text(585, 510, 'OutOfMemoryError', 12, RED, '700')
    s.text(585, 528, '栈扩展无法申请内存', 10, '#B71C1C', italic=True)
    return s.render()


def gen_io_evolution():
    s = SVG(800, 500).title('Java IO 演进：BIO → NIO → AIO')
    s.rect(40, 100, 220, 320, '#FFEBEE', stroke=RED, sw=2)
    s.text(150, 125, 'BIO', 18, RED, '700')
    s.text(150, 148, '(Blocking IO)', 11, '#B71C1C', italic=True)
    s.text(150, 180, '同步阻塞', 12, '#B71C1C', '700')
    s.text(150, 210, '一连接一线程', 11, '#B71C1C')
    s.text(150, 235, '读写时线程阻塞', 11, '#B71C1C')
    s.text(150, 260, '线程浪费严重', 11, '#B71C1C')
    s.text(150, 295, 'JDK 1.4 之前', 10, GRAY, italic=True)
    s.text(150, 350, '连接数少', 11, GREEN, '700')
    s.text(150, 370, '架构简单', 11, GREEN, '700')
    s.rect(290, 100, 220, 320, '#FFF3E0', stroke=ORANGE, sw=2)
    s.text(400, 125, 'NIO', 18, ORANGE, '700')
    s.text(400, 148, '(Non-blocking IO)', 11, '#BF360C', italic=True)
    s.text(400, 180, '同步非阻塞', 12, '#BF360C', '700')
    s.text(400, 210, 'Channel + Buffer', 11, '#BF360C')
    s.text(400, 235, 'Selector 多路复用', 11, '#BF360C')
    s.text(400, 260, '一线程管多连接', 11, '#BF360C')
    s.text(400, 295, 'JDK 1.4+', 10, GRAY, italic=True)
    s.text(400, 350, '高并发场景', 11, GREEN, '700')
    s.text(400, 370, 'Netty 基础', 11, GREEN, '700')
    s.rect(540, 100, 220, 320, '#E8F5E9', stroke=GREEN, sw=2)
    s.text(650, 125, 'AIO', 18, GREEN, '700')
    s.text(650, 148, '(Asynchronous IO)', 11, '#1B5E20', italic=True)
    s.text(650, 180, '异步非阻塞', 12, '#1B5E20', '700')
    s.text(650, 210, 'Future / Callback', 11, '#1B5E20')
    s.text(650, 235, 'OS 回调完成', 11, '#1B5E20')
    s.text(650, 260, '真正异步', 11, '#1B5E20')
    s.text(650, 295, 'JDK 1.7+', 10, GRAY, italic=True)
    s.text(650, 350, '连接数海量', 11, GREEN, '700')
    s.text(650, 370, 'Linux 支持弱', 11, ORANGE, '700')
    s.arrow(260, 260, 290, 260, color=GRAY, width=2)
    s.arrow(510, 260, 540, 260, color=GRAY, width=2)
    s.text(400, 450, '核心演进：减少线程阻塞 → 提升并发能力', 12, PURPLE, '600', italic=True)
    return s.render()


def gen_gc_algorithms():
    s = SVG(800, 600).title('JVM 垃圾回收四大基础算法')
    s.rect(40, 100, 350, 200, '#E3F2FD', stroke=BLUE, sw=2, rx=8)
    s.rect(40, 100, 350, 36, BLUE, stroke=BLUE)
    s.text(215, 124, '1. 标记-清除 (Mark-Sweep)', 14, '#FFFFFF', '700')
    s.text(60, 165, '流程：标记存活 → 清除垃圾', 12, '#0D47A1', '700', anchor='start')
    s.text(60, 190, '优点：实现简单', 11, GREEN, anchor='start')
    s.text(60, 210, '缺点：', 11, RED, '700', anchor='start')
    s.text(80, 230, '• 内存碎片化严重', 11, '#B71C1C', anchor='start')
    s.text(80, 250, '• 分配大对象易失败', 11, '#B71C1C', anchor='start')
    s.text(80, 270, '• 效率不稳定', 11, '#B71C1C', anchor='start')
    s.text(60, 290, '使用：CMS 老年代', 11, PURPLE, '600', anchor='start')
    s.rect(410, 100, 350, 200, '#E8F5E9', stroke=GREEN, sw=2, rx=8)
    s.rect(410, 100, 350, 36, GREEN, stroke=GREEN)
    s.text(585, 124, '2. 复制 (Copying)', 14, '#FFFFFF', '700')
    s.text(430, 165, '流程：分两半 → 复制存活 → 清空', 12, '#1B5E20', '700', anchor='start')
    s.text(430, 190, '优点：', 11, GREEN, '700', anchor='start')
    s.text(450, 210, '• 无内存碎片', 11, '#1B5E20', anchor='start')
    s.text(450, 230, '• 分配快 (指针碰撞)', 11, '#1B5E20', anchor='start')
    s.text(430, 255, '缺点：浪费 50% 内存', 11, RED, '700', anchor='start')
    s.text(430, 280, '存活多时效率低', 11, '#B71C1C', anchor='start')
    s.text(430, 300, '使用：新生代 (Eden+S0+S1)', 11, PURPLE, '600', anchor='start')
    s.rect(40, 320, 350, 200, '#FFF3E0', stroke=ORANGE, sw=2, rx=8)
    s.rect(40, 320, 350, 36, ORANGE, stroke=ORANGE)
    s.text(215, 344, '3. 标记-整理 (Mark-Compact)', 14, '#FFFFFF', '700')
    s.text(60, 385, '流程：标记存活 → 整理到一端', 12, '#E65100', '700', anchor='start')
    s.text(60, 410, '优点：', 11, GREEN, '700', anchor='start')
    s.text(80, 430, '• 无内存碎片', 11, '#1B5E20', anchor='start')
    s.text(80, 450, '• 不浪费内存', 11, '#1B5E20', anchor='start')
    s.text(60, 475, '缺点：移动对象开销大', 11, RED, '700', anchor='start')
    s.text(60, 495, '更新引用耗时', 11, '#B71C1C', anchor='start')
    s.text(60, 515, '使用：老年代 (Serial Old)', 11, PURPLE, '600', anchor='start')
    s.rect(410, 320, 350, 200, '#F3E5F5', stroke=PURPLE, sw=2, rx=8)
    s.rect(410, 320, 350, 36, PURPLE, stroke=PURPLE)
    s.text(585, 344, '4. 分代收集 (Generational)', 14, '#FFFFFF', '700')
    s.text(430, 385, '思想：按对象生命周期分代', 12, '#4A148C', '700', anchor='start')
    s.text(430, 410, '新生代 (存活少):', 11, '#4A148C', '700', anchor='start')
    s.text(450, 430, '复制算法', 11, '#1B5E20', anchor='start')
    s.text(430, 455, '老年代 (存活多):', 11, '#4A148C', '700', anchor='start')
    s.text(450, 475, '标记-清除/整理', 11, '#1B5E20', anchor='start')
    s.text(430, 500, '现代 JVM 默认策略', 11, GREEN, '700', anchor='start')
    s.text(430, 520, 'HotSpot / G1 / ZGC', 11, GRAY, italic=True, anchor='start')
    return s.render()


def gen_generational_collection():
    s = SVG(800, 500).title('分代收集算法核心思想')
    s.rect(40, 90, 720, 70, '#ECEFF1', stroke=GRAY, rx=6)
    s.text(400, 115, '核心：不同生命周期对象采用不同回收策略', 14, '#37474F', '700')
    s.text(400, 138, '"朝生夕灭" → 复制  |  "长命百岁" → 标记整理', 11, GRAY, italic=True)
    s.rect(40, 180, 350, 220, '#E8F5E9', stroke=GREEN, sw=2, rx=8)
    s.rect(40, 180, 350, 36, GREEN, stroke=GREEN)
    s.text(215, 204, '新生代 (Young)', 14, '#FFFFFF', '700')
    s.text(60, 245, '特点：', 12, GREEN, '700', anchor='start')
    s.text(80, 268, '• 98% 对象朝生夕灭', 11, '#1B5E20', anchor='start')
    s.text(80, 290, '• Minor GC 频繁但快', 11, '#1B5E20', anchor='start')
    s.text(60, 320, '算法：复制 (Copying)', 12, GREEN, '700', anchor='start')
    s.text(80, 343, 'Eden + S0 + S1 (8:1:1)', 11, '#1B5E20', anchor='start')
    s.text(80, 365, '只需浪费 10% 内存', 11, '#1B5E20', anchor='start')
    s.text(80, 387, 'S0/S1 来回复制存活', 11, '#1B5E20', anchor='start')
    s.rect(410, 180, 350, 220, '#FFEBEE', stroke=RED, sw=2, rx=8)
    s.rect(410, 180, 350, 36, RED, stroke=RED)
    s.text(585, 204, '老年代 (Old)', 14, '#FFFFFF', '700')
    s.text(430, 245, '特点：', 12, RED, '700', anchor='start')
    s.text(450, 268, '• 存活率高', 11, '#B71C1C', anchor='start')
    s.text(450, 290, '• GC 频率低但慢', 11, '#B71C1C', anchor='start')
    s.text(430, 320, '算法：标记-清除 / 整理', 12, RED, '700', anchor='start')
    s.text(450, 343, 'CMS: 标记-清除', 11, '#B71C1C', anchor='start')
    s.text(450, 365, 'Serial Old: 标记-整理', 11, '#B71C1C', anchor='start')
    s.text(450, 387, '避免复制大对象开销', 11, '#B71C1C', anchor='start')
    s.arrow(390, 290, 410, 290, color=ORANGE, width=2)
    s.text(400, 280, '晋升', 10, ORANGE, '600')
    s.legend([(GREEN, '新生代/复制'), (RED, '老年代/标记整理'), (ORANGE, '晋升 Promotion')], y=420)
    return s.render()


def gen_copying_algorithm():
    s = SVG(800, 500).title('复制算法 (Copying) 原理')
    s.rect(40, 100, 220, 300, '#ECEFF1', stroke=GRAY, sw=2)
    s.text(150, 125, 'Step 1: 分配前', 13, '#37474F', '700')
    s.rect(60, 150, 80, 230, '#C8E6C9', stroke=GREEN)
    s.text(100, 175, 'From', 12, '#1B5E20', '700')
    s.rect(70, 195, 60, 25, '#4CAF50', stroke='#1B5E20')
    s.rect(70, 225, 60, 25, '#FFCDD2', stroke=RED)
    s.rect(70, 255, 60, 25, '#4CAF50', stroke='#1B5E20')
    s.rect(70, 285, 60, 25, '#FFCDD2', stroke=RED)
    s.rect(70, 315, 60, 25, '#4CAF50', stroke='#1B5E20')
    s.rect(70, 345, 60, 25, '#FFCDD2', stroke=RED)
    s.text(100, 400, '混杂存活/死亡', 10, GRAY, italic=True)
    s.rect(160, 150, 80, 230, '#ECEFF1', stroke=GRAY, dashed=True)
    s.text(200, 175, 'To', 12, GRAY, '700')
    s.text(200, 280, '(空)', 12, GRAY, italic=True)
    s.rect(290, 100, 220, 300, '#FFF3E0', stroke=ORANGE, sw=2)
    s.text(400, 125, 'Step 2: 复制存活', 13, '#E65100', '700')
    s.rect(310, 150, 80, 230, '#C8E6C9', stroke=GREEN)
    s.text(350, 175, 'From', 12, '#1B5E20', '700')
    s.arrow(390, 280, 410, 280, color=ORANGE, width=2)
    s.rect(410, 150, 80, 230, '#FFF8E1', stroke=ORANGE, dashed=True)
    s.text(450, 175, 'To', 12, '#E65100', '700')
    s.rect(420, 195, 60, 25, '#4CAF50', stroke='#1B5E20')
    s.rect(420, 225, 60, 25, '#4CAF50', stroke='#1B5E20')
    s.rect(420, 255, 60, 25, '#4CAF50', stroke='#1B5E20')
    s.text(350, 400, '存活→To 连续排列', 10, '#BF360C', italic=True)
    s.rect(540, 100, 220, 300, '#E8F5E9', stroke=GREEN, sw=2)
    s.text(650, 125, 'Step 3: 清空+互换', 13, '#1B5E20', '700')
    s.rect(560, 150, 80, 230, '#ECEFF1', stroke=GRAY, dashed=True)
    s.text(600, 175, 'From', 12, GRAY, '700')
    s.text(600, 280, '(清空)', 12, GRAY, italic=True)
    s.arrow(640, 280, 660, 280, color=GREEN, width=2)
    s.rect(660, 150, 80, 230, '#C8E6C9', stroke=GREEN)
    s.text(700, 175, 'To→新From', 11, '#1B5E20', '700')
    s.rect(670, 195, 60, 25, '#4CAF50', stroke='#1B5E20')
    s.rect(670, 225, 60, 25, '#4CAF50', stroke='#1B5E20')
    s.rect(670, 255, 60, 25, '#4CAF50', stroke='#1B5E20')
    s.text(650, 400, '角色互换，无碎片', 10, '#1B5E20', italic=True)
    s.legend([(GREEN, '存活'), (RED, '垃圾'), (GRAY, '空闲')], y=420)
    s.text(400, 465, '优点：无碎片 / 缺点：浪费一半空间 (新生代优化为 8:1:1)', 12, PURPLE, '600', italic=True)
    return s.render()


def gen_generational_vs_regional():
    s = SVG(800, 500).title('分代收集 VS 分区收集')
    s.rect(40, 100, 350, 350, '#E8F5E9', stroke=GREEN, sw=2)
    s.rect(40, 100, 350, 36, GREEN, stroke=GREEN)
    s.text(215, 124, '分代收集 (Generational)', 14, '#FFFFFF', '700')
    s.text(60, 165, '维度：对象生命周期 (时间)', 12, '#1B5E20', '700', anchor='start')
    s.rect(60, 185, 310, 70, '#C8E6C9', stroke=GREEN)
    s.text(215, 205, '新生代 (Eden + S0 + S1)', 12, '#1B5E20', '700')
    s.text(215, 225, '复制算法 / Minor GC', 11, '#388E3C', italic=True)
    s.text(215, 245, '短命对象', 11, '#1B5E20')
    s.rect(60, 270, 310, 70, '#FFCDD2', stroke=RED)
    s.text(215, 290, '老年代 (Old)', 12, '#B71C1C', '700')
    s.text(215, 310, '标记-整理 / Major GC', 11, '#D84315', italic=True)
    s.text(215, 330, '长寿对象', 11, '#B71C1C')
    s.text(60, 365, '代表：CMS / Parallel Old', 11, PURPLE, '600', anchor='start')
    s.text(60, 390, '特点：堆物理分两块', 11, GRAY, italic=True, anchor='start')
    s.text(60, 415, '      回收粒度=整个代', 11, GRAY, italic=True, anchor='start')
    s.text(60, 440, '      停顿时间不可控', 11, RED, '600', anchor='start')
    s.rect(410, 100, 350, 350, '#FFF3E0', stroke=ORANGE, sw=2)
    s.rect(410, 100, 350, 36, ORANGE, stroke=ORANGE)
    s.text(585, 124, '分区收集 (Regional)', 14, '#FFFFFF', '700')
    s.text(430, 165, '维度：堆空间 (物理)', 12, '#E65100', '700', anchor='start')
    cellw = 50
    cellh = 40
    startx = 440
    starty = 190
    region_layout = [
        ['E','E','O','S','O'],
        ['E','O','O','H','E'],
        ['O','E','S','O','E'],
        ['H','O','E','O','U'],
    ]
    colors_map = {'E':('#C8E6C9', GREEN), 'S':('#DCEDC8', GREEN), 'O':('#FFCDD2', RED), 'H':('#FFE0B2', ORANGE), 'U':('#ECEFF1', GRAY)}
    for ri, row in enumerate(region_layout):
        for ci, code in enumerate(row):
            x = startx + ci * cellw
            y = starty + ri * cellh
            fill, stroke = colors_map[code]
            s.rect(x, y, cellw - 3, cellh - 3, fill, stroke=stroke, sw=1)
            s.text(x + (cellw-3)/2, y + (cellh-3)/2 + 4, code, 10, '#37474F', '700')
    s.text(585, 380, '堆切分为等大 Region', 11, '#BF360C', italic=True)
    s.text(585, 400, '每个 Region 角色可动态切换', 11, '#E65100', '700')
    s.text(585, 425, '代表：G1 / ZGC / Shenandoah', 11, PURPLE, '600')
    s.text(585, 450, '特点：可预测停顿时间', 11, '#1B5E20', '700')
    return s.render()


def gen_serial_old():
    s = SVG(800, 500).title('Serial Old 收集器 (单线程标记-整理)')
    s.rect(40, 100, 720, 80, '#FFEBEE', stroke=RED, sw=2, rx=6)
    s.text(400, 130, '老年代 单线程 标记-整理算法', 15, RED, '700')
    s.text(400, 155, 'Client 模式默认 / CMS 后备方案', 12, '#B71C1C', italic=True)
    s.rect(60, 220, 130, 80, '#ECEFF1', stroke=GRAY, sw=2)
    s.text(125, 248, '标记', 13, '#37474F', '700')
    s.text(125, 270, 'Mark', 10, GRAY, italic=True)
    s.text(125, 287, '单线程', 10, RED, '600')
    s.arrow(190, 260, 240, 260, color=GRAY, width=2)
    s.rect(240, 220, 130, 80, '#FFF3E0', stroke=ORANGE, sw=2)
    s.text(305, 248, '整理', 13, '#E65100', '700')
    s.text(305, 270, 'Compact', 10, GRAY, italic=True)
    s.text(305, 287, '移动对象', 10, '#BF360C')
    s.arrow(370, 260, 420, 260, color=GRAY, width=2)
    s.rect(420, 220, 130, 80, '#E8F5E9', stroke=GREEN, sw=2)
    s.text(485, 248, '清除', 13, '#1B5E20', '700')
    s.text(485, 270, 'Sweep', 10, GRAY, italic=True)
    s.text(485, 287, '无碎片', 10, '#388E3C')
    s.arrow(550, 260, 600, 260, color=GRAY, width=2)
    s.rect(600, 220, 130, 80, '#F3E5F5', stroke=PURPLE, sw=2)
    s.text(665, 248, '完成', 13, '#4A148C', '700')
    s.text(665, 270, 'Done', 10, GRAY, italic=True)
    s.text(665, 287, 'STW', 10, RED, '700')
    s.rect(60, 340, 340, 100, '#E8F5E9', stroke=GREEN, rx=6)
    s.text(230, 365, '优点', 13, GREEN, '700')
    s.text(80, 390, '• 简单稳定', 11, '#1B5E20', anchor='start')
    s.text(80, 410, '• 内存整理无碎片', 11, '#1B5E20', anchor='start')
    s.text(80, 430, '• 单 CPU 效率高', 11, '#1B5E20', anchor='start')
    s.rect(420, 340, 340, 100, '#FFEBEE', stroke=RED, rx=6)
    s.text(590, 365, '缺点', 13, RED, '700')
    s.text(440, 390, '• 单线程停顿时间长', 11, '#B71C1C', anchor='start')
    s.text(440, 410, '• 不适合服务端', 11, '#B71C1C', anchor='start')
    s.text(440, 430, '• CMS 失败时退化于此', 11, RED, '700', anchor='start')
    return s.render()


def gen_stw():
    s = SVG(800, 500).title('STW (Stop-The-World) 与 减少策略')
    s.rect(40, 100, 720, 60, '#FFEBEE', stroke=RED, sw=2, rx=6)
    s.text(400, 130, 'STW：暂停所有应用线程', 15, RED, '700')
    s.text(400, 150, '保证 GC 一致性，但影响响应时间', 12, '#B71C1C', italic=True)
    s.rect(60, 200, 680, 50, '#E8F5E9', stroke=GREEN)
    s.text(400, 230, '应用运行 (用户线程)', 12, '#1B5E20', '700')
    s.rect(180, 200, 60, 50, RED, stroke=RED)
    s.text(210, 230, 'STW', 12, '#FFFFFF', '700')
    s.rect(380, 200, 80, 50, RED, stroke=RED)
    s.text(420, 230, 'STW', 12, '#FFFFFF', '700')
    s.rect(580, 200, 60, 50, RED, stroke=RED)
    s.text(610, 230, 'STW', 12, '#FFFFFF', '700')
    s.text(60, 275, '← 时间 →', 11, GRAY, italic=True, anchor='start')
    s.rect(40, 310, 720, 150, '#ECEFF1', stroke=GRAY, rx=6)
    s.text(400, 335, '减少 STW 的策略', 14, '#37474F', '700')
    strategies = [
        ('分代回收', GREEN, '减少扫描范围'),
        ('并发标记', ORANGE, 'CMS/G1/ZGC'),
        ('Region 化', PURPLE, '部分回收'),
        ('读屏障', TEAL, 'ZGC 染色指针'),
    ]
    for i, (name, color, desc) in enumerate(strategies):
        x = 60 + i * 170
        s.rect(x, 360, 160, 80, color + '22', stroke=color, sw=2)
        s.text(x + 80, 385, name, 12, color, '700')
        s.text(x + 80, 405, desc, 10, '#37474F', italic=True)
        s.text(x + 80, 425, ['复制算法', '标记-清除', '可预测停顿', '亚毫秒级'][i], 10, GRAY)
    s.legend([(GREEN, '应用运行'), (RED, 'STW 停顿')], y=475)
    return s.render()


def gen_gc_types():
    s = SVG(800, 600).title('GC 类型对比 (Minor/Major/Mixed/Full)')
    types = [
        ('Minor GC', '新生代 GC', GREEN, '(Eden 满)', '复制算法', '频繁 / 快 (<50ms)', 130),
        ('Major GC', '老年代 GC', ORANGE, '(Old 满)', '标记-清除/整理', '慢 (CMS 等同 Major)', 250),
        ('Mixed GC', '混合 GC', PURPLE, '(G1 特有)', '回收新生代+部分老年代', 'G1 回收 Region', 370),
        ('Full GC', '全堆 GC', RED, '(System.gc/担保失败)', 'STW 整个堆', '最慢 (秒级)', 490),
    ]
    for name, cn, color, trigger, algo, perf, y in types:
        s.rect(40, y, 720, 100, color + '18', stroke=color, sw=2, rx=8)
        s.rect(40, y, 180, 100, color, stroke=color)
        s.text(130, y + 35, name, 16, '#FFFFFF', '700')
        s.text(130, y + 60, cn, 12, '#FFFFFF', '600')
        s.text(130, y + 82, algo, 10, '#FFFFFF', italic=True)
        s.text(250, y + 35, '触发条件', 12, color, '700', anchor='start')
        s.text(250, y + 58, trigger, 11, '#37474F', anchor='start')
        s.text(560, y + 35, '性能', 12, color, '700', anchor='start')
        s.text(560, y + 58, perf, 11, '#37474F', anchor='start')
    return s.render()


def gen_gc_trigger():
    s = SVG(800, 500).title('Young GC 与 Full GC 触发条件')
    s.rect(40, 100, 350, 350, '#E8F5E9', stroke=GREEN, sw=2, rx=8)
    s.rect(40, 100, 350, 36, GREEN, stroke=GREEN)
    s.text(215, 124, 'Young GC 触发', 14, '#FFFFFF', '700')
    s.text(60, 165, '主因：Eden 区满', 13, '#1B5E20', '700', anchor='start')
    s.text(60, 195, '常见触发：', 12, GREEN, '700', anchor='start')
    triggers_y = ['• 新对象分配，Eden 满', '• TLAB 分配失败', '• 分配速率 > 回收速率']
    for i, t in enumerate(triggers_y):
        s.text(80, 220 + i * 25, t, 11, '#1B5E20', anchor='start')
    s.text(60, 310, '不触发：', 12, ORANGE, '700', anchor='start')
    s.text(80, 335, '• 老年代不足时', 11, '#BF360C', anchor='start')
    s.text(80, 355, '   晋升失败 → Full GC', 11, '#BF360C', anchor='start')
    s.text(60, 395, '频率：高 (~秒级)', 11, GRAY, italic=True, anchor='start')
    s.text(60, 415, '耗时：短 (~10-50ms)', 11, GRAY, italic=True, anchor='start')
    s.text(60, 435, '影响：可接受', 11, GREEN, '700', anchor='start')
    s.rect(410, 100, 350, 350, '#FFEBEE', stroke=RED, sw=2, rx=8)
    s.rect(410, 100, 350, 36, RED, stroke=RED)
    s.text(585, 124, 'Full GC 触发', 14, '#FFFFFF', '700')
    s.text(430, 165, '主因：老年代 / 元空间不足', 13, '#B71C1C', '700', anchor='start')
    s.text(430, 195, '常见触发：', 12, RED, '700', anchor='start')
    triggers_f = [
        '• 老年代使用率 > 阈值',
        '• Metaspace 空间不足',
        '• 空间分配担保失败',
        '• System.gc() 显式调用',
        '• CMS Concurrent Mode Failure',
        '• Promotion Failed (晋升失败)',
    ]
    for i, t in enumerate(triggers_f):
        s.text(450, 220 + i * 22, t, 11, '#B71C1C', anchor='start')
    s.text(430, 395, '频率：低 (异常情况)', 11, GRAY, italic=True, anchor='start')
    s.text(430, 415, '耗时：长 (~秒级)', 11, RED, '700', anchor='start')
    s.text(430, 435, '影响：致命 (需排查)', 11, RED, '700', anchor='start')
    return s.render()


def gen_promotion_guarantee():
    s = SVG(800, 500).title('空间分配担保机制')
    s.rect(40, 100, 720, 60, '#ECEFF1', stroke=GRAY, rx=6)
    s.text(400, 125, 'Minor GC 前的检查机制', 14, '#37474F', '700')
    s.text(400, 145, '确保老年代能容纳新生代晋升对象，避免 Promotion Failed', 11, GRAY, italic=True)
    s.rect(60, 200, 200, 60, '#E3F2FD', stroke=BLUE, sw=2)
    s.text(160, 225, 'Minor GC 前', 12, BLUE, '700')
    s.text(160, 245, '检查老年代可用', 11, '#0D47A1')
    s.arrow(260, 230, 300, 230, color=GRAY, width=2)
    s.rect(300, 200, 200, 60, '#FFF3E0', stroke=ORANGE, sw=2)
    s.text(400, 225, '计算: 是否 >=', 12, '#E65100', '700')
    s.text(400, 245, '所有新生代对象?', 11, '#BF360C')
    s.arrow(500, 230, 540, 230, color=GRAY, width=2)
    s.rect(540, 180, 110, 40, '#E8F5E9', stroke=GREEN, sw=2)
    s.text(595, 205, '是 → 安全', 11, GREEN, '700')
    s.rect(540, 240, 110, 40, '#FFEBEE', stroke=RED, sw=2)
    s.text(595, 265, '否 → 风险', 11, RED, '700')
    s.rect(60, 320, 350, 130, '#FFEBEE', stroke=RED, rx=6)
    s.text(235, 345, '不允许冒险时:', 12, RED, '700')
    s.text(80, 370, '→ 触发 Full GC', 12, '#B71C1C', '700', anchor='start')
    s.text(80, 390, '(HandlePromotionFailure=false)', 10, GRAY, italic=True, anchor='start')
    s.rect(430, 320, 350, 130, '#FFF3E0', stroke=ORANGE, rx=6)
    s.text(605, 345, '允许冒险时:', 12, ORANGE, '700')
    s.text(450, 370, '→ 检查历次平均晋升大小', 11, '#BF360C', anchor='start')
    s.text(450, 390, '   >= 老年代连续空间?', 11, '#BF360C', anchor='start')
    s.text(450, 415, '   是 → 尝试 Minor GC', 11, GREEN, '700', anchor='start')
    s.text(450, 435, '   否 → Full GC', 11, RED, '700', anchor='start')
    return s.render()


def gen_cms_vs_g1():
    s = SVG(800, 600).title('CMS vs G1 对比与选择')
    s.rect(40, 90, 350, 400, '#FFEBEE', stroke=RED, sw=2, rx=8)
    s.rect(40, 90, 350, 36, RED, stroke=RED)
    s.text(215, 114, 'CMS (Concurrent Mark Sweep)', 13, '#FFFFFF', '700')
    s.text(60, 155, '算法: 标记-清除', 12, '#B71C1C', '700', anchor='start')
    s.text(60, 180, '内存碎片: 有 (致命)', 12, RED, '700', anchor='start')
    s.text(60, 205, '停顿时间: 低 (但不可预测)', 11, '#B71C1C', anchor='start')
    s.text(60, 230, '堆要求: 小到中等 (<8G)', 11, '#B71C1C', anchor='start')
    s.text(60, 255, '回收粒度: 整个老年代', 11, '#B71C1C', anchor='start')
    s.text(60, 280, '浮动垃圾: 有', 11, '#B71C1C', anchor='start')
    s.text(60, 305, 'CPU 占用: 高 (并发)', 11, '#B71C1C', anchor='start')
    s.text(60, 335, '退化风险:', 12, RED, '700', anchor='start')
    s.text(80, 358, 'Concurrent Mode Failure', 11, '#B71C1C', anchor='start')
    s.text(80, 378, '→ Serial Old (单线程)', 11, '#B71C1C', anchor='start')
    s.text(60, 415, 'JDK 9 起废弃', 11, GRAY, italic=True, anchor='start')
    s.text(60, 440, 'JDK 14 移除', 11, GRAY, italic=True, anchor='start')
    s.text(60, 470, '场景: 老系统', 11, GRAY, italic=True, anchor='start')
    s.rect(410, 90, 350, 400, '#E8F5E9', stroke=GREEN, sw=2, rx=8)
    s.rect(410, 90, 350, 36, GREEN, stroke=GREEN)
    s.text(585, 114, 'G1 (Garbage First)', 13, '#FFFFFF', '700')
    s.text(430, 155, '算法: 标记-整理 + 复制', 12, '#1B5E20', '700', anchor='start')
    s.text(430, 180, '内存碎片: 无', 12, GREEN, '700', anchor='start')
    s.text(430, 205, '停顿时间: 可预测 (设定目标)', 11, '#1B5E20', anchor='start')
    s.text(430, 230, '堆要求: 大堆 (>6G 优势明显)', 11, '#1B5E20', anchor='start')
    s.text(430, 255, '回收粒度: Region (部分)', 11, '#1B5E20', anchor='start')
    s.text(430, 280, '浮动垃圾: 较少', 11, '#1B5E20', anchor='start')
    s.text(430, 305, 'CPU 占用: 适中', 11, '#1B5E20', anchor='start')
    s.text(430, 335, '特色: ', 12, GREEN, '700', anchor='start')
    s.text(450, 358, 'Region 化堆布局', 11, '#1B5E20', anchor='start')
    s.text(450, 378, 'Mature GC + Mixed GC', 11, '#1B5E20', anchor='start')
    s.text(450, 398, 'Garbage First 策略', 11, '#1B5E20', anchor='start')
    s.text(430, 435, 'JDK 9+ 默认', 12, GREEN, '700', anchor='start')
    s.text(430, 460, '主推选择', 11, GREEN, '700', anchor='start')
    s.text(430, 480, '场景: 服务端主流', 11, '#1B5E20', italic=True, anchor='start')
    s.rect(40, 510, 720, 60, '#FFFDE7', stroke=ORANGE, rx=6)
    s.text(400, 535, '选择建议', 13, '#E65100', '700')
    s.text(400, 555, '小堆 (<4G) / 老系统 → CMS  |  大堆 / 新项目 → G1 (默认)', 11, '#37474F')
    return s.render()


def gen_hotspot_code():
    s = SVG(800, 500).title('热点代码 (Hot Spot Code)')
    s.rect(40, 100, 720, 80, '#FFF3E0', stroke=ORANGE, sw=2, rx=6)
    s.text(400, 125, '运行时频繁执行的代码 → JIT 编译为本地机器码', 14, '#E65100', '700')
    s.text(400, 150, '两种检测方式', 12, '#BF360C', italic=True)
    s.rect(60, 220, 340, 100, '#E3F2FD', stroke=BLUE, sw=2)
    s.rect(60, 220, 340, 32, BLUE, stroke=BLUE)
    s.text(230, 242, '1. 方法调用计数器', 13, '#FFFFFF', '700')
    s.text(80, 275, '方法被调用次数', 12, '#0D47A1', anchor='start')
    s.text(80, 295, '阈值: -XX:CompileThreshold=10000', 10, GRAY, italic=True, anchor='start')
    s.text(80, 312, '(Client) / 10000 (Server)', 10, GRAY, italic=True, anchor='start')
    s.rect(420, 220, 340, 100, '#E8F5E9', stroke=GREEN, sw=2)
    s.rect(420, 220, 340, 32, GREEN, stroke=GREEN)
    s.text(590, 242, '2. 回边计数器', 13, '#FFFFFF', '700')
    s.text(440, 275, '循环体回边次数', 12, '#1B5E20', anchor='start')
    s.text(440, 295, '触发 OSR (栈上替换)', 10, GRAY, italic=True, anchor='start')
    s.text(440, 312, '可在循环中即时编译', 10, '#388E3C', italic=True, anchor='start')
    s.rect(40, 360, 720, 100, '#F3E5F5', stroke=PURPLE, rx=6)
    s.text(400, 385, '热点代码处理流程', 13, PURPLE, '700')
    s.rect(60, 405, 140, 40, '#E1BEE7', stroke=PURPLE)
    s.text(130, 425, '方法/循环', 11, '#4A148C', '700')
    s.text(130, 440, '频繁执行', 10, '#6A1B9A', italic=True)
    s.arrow(200, 425, 220, 425, color=PURPLE, width=2)
    s.rect(220, 405, 140, 40, '#CE93D8', stroke=PURPLE)
    s.text(290, 425, 'JIT 编译', 11, '#4A148C', '700')
    s.text(290, 440, 'C1 → C2', 10, '#6A1B9A', italic=True)
    s.arrow(360, 425, 380, 425, color=PURPLE, width=2)
    s.rect(380, 405, 140, 40, '#BA68C8', stroke=PURPLE)
    s.text(450, 425, '本地机器码', 11, '#FFFFFF', '700')
    s.text(450, 440, '缓存 CodeCache', 10, '#E1BEE7', italic=True)
    s.arrow(520, 425, 540, 425, color=PURPLE, width=2)
    s.rect(540, 405, 200, 40, '#AB47BC', stroke=PURPLE)
    s.text(640, 425, '后续直接执行机器码', 11, '#FFFFFF', '700')
    s.text(640, 440, '跳过解释', 10, '#E1BEE7', italic=True)
    return s.render()


def gen_interpreter():
    s = SVG(800, 500).title('JVM 解释器工作原理')
    s.rect(40, 100, 720, 60, '#E3F2FD', stroke=BLUE, sw=2, rx=6)
    s.text(400, 130, '逐行读取字节码 → 翻译为机器指令执行', 14, BLUE, '700')
    s.text(400, 150, '启动快，无需编译等待', 11, '#1565C0', italic=True)
    steps = [
        ('字节码', '.class 文件\n0x B2 00 02...', BLUE, 100),
        ('字节码读取', 'Bytecode Reader\n按 PC 取指令', TEAL, 250),
        ('字节码翻译', 'Interpreter\n解释为机器码', ORANGE, 400),
        ('执行', 'CPU 执行\n机器指令', GREEN, 550),
    ]
    for i, (name, desc, color, x) in enumerate(steps):
        s.rect(x, 220, 130, 100, color + '22', stroke=color, sw=2)
        s.rect(x, 220, 130, 28, color, stroke=color)
        s.text(x + 65, 240, name, 12, '#FFFFFF', '700')
        lines = desc.split('\n')
        for j, line in enumerate(lines):
            s.text(x + 65, 270 + j * 18, line, 10, '#37474F', italic=True)
        if i < 3:
            s.arrow(x + 130, 270, x + 150, 270, color=GRAY, width=2)
    s.rect(40, 360, 720, 100, '#FFFDE7', stroke=ORANGE, rx=6)
    s.text(400, 385, '执行示例: int a = 1 + 2', 13, '#E65100', '700')
    s.text(60, 410, 'iconst_1   (0x04)', 11, '#5D4037', anchor='start')
    s.text(60, 428, 'iconst_2   (0x05)', 11, '#5D4037', anchor='start')
    s.text(60, 446, 'iadd       (0x60)', 11, '#5D4037', anchor='start')
    s.text(400, 410, '→ 解释器翻译每条指令', 11, BLUE, '700', anchor='start')
    s.text(400, 428, '→ 操作数栈计算', 11, ORANGE, '700', anchor='start')
    s.text(400, 446, '→ 结果存局部变量表', 11, GREEN, '700', anchor='start')
    return s.render()


def gen_aot_vs_jit():
    s = SVG(800, 500).title('AOT 提前编译 vs JIT 即时编译')
    s.rect(40, 100, 350, 350, '#E8F5E9', stroke=GREEN, sw=2, rx=8)
    s.rect(40, 100, 350, 36, GREEN, stroke=GREEN)
    s.text(215, 124, 'JIT 即时编译', 14, '#FFFFFF', '700')
    s.text(60, 165, '时机：运行时', 12, '#1B5E20', '700', anchor='start')
    s.text(60, 190, '原理：边运行边编译', 11, '#1B5E20', anchor='start')
    s.text(60, 220, '优点：', 12, GREEN, '700', anchor='start')
    s.text(80, 245, '• 基于运行数据优化', 11, '#1B5E20', anchor='start')
    s.text(80, 265, '• 激进优化 (逃逸分析)', 11, '#1B5E20', anchor='start')
    s.text(80, 285, '• 峰值性能高', 11, '#1B5E20', anchor='start')
    s.text(60, 315, '缺点：', 12, RED, '700', anchor='start')
    s.text(80, 340, '• 启动慢 (warmup)', 11, '#B71C1C', anchor='start')
    s.text(80, 360, '• 内存占用大', 11, '#B71C1C', anchor='start')
    s.text(80, 380, '• 优化可能退化', 11, '#B71C1C', anchor='start')
    s.text(60, 415, '场景：长期运行服务', 11, PURPLE, '600', anchor='start')
    s.text(60, 435, '默认 HotSpot 模式', 11, GRAY, italic=True, anchor='start')
    s.rect(410, 100, 350, 350, '#E3F2FD', stroke=BLUE, sw=2, rx=8)
    s.rect(410, 100, 350, 36, BLUE, stroke=BLUE)
    s.text(585, 124, 'AOT 提前编译', 14, '#FFFFFF', '700')
    s.text(430, 165, '时机：构建时', 12, '#0D47A1', '700', anchor='start')
    s.text(430, 190, '原理：编译期生成机器码', 11, '#0D47A1', anchor='start')
    s.text(430, 220, '优点：', 12, GREEN, '700', anchor='start')
    s.text(450, 245, '• 启动极快', 11, '#1B5E20', anchor='start')
    s.text(450, 265, '• 内存占用小', 11, '#1B5E20', anchor='start')
    s.text(450, 285, '• 包体积小', 11, '#1B5E20', anchor='start')
    s.text(430, 315, '缺点：', 12, RED, '700', anchor='start')
    s.text(450, 340, '• 不能动态优化', 11, '#B71C1C', anchor='start')
    s.text(450, 360, '• 反射需配置', 11, '#B71C1C', anchor='start')
    s.text(450, 380, '• 峰值不如 JIT', 11, '#B71C1C', anchor='start')
    s.text(430, 415, '场景：云原生 / 短任务', 11, PURPLE, '600', anchor='start')
    s.text(430, 435, 'GraalVM Native Image', 11, GRAY, italic=True, anchor='start')
    return s.render()


def gen_cpu_troubleshoot():
    s = SVG(800, 600).title('CPU 占用过高排查流程')
    s.rect(40, 90, 720, 50, '#ECEFF1', stroke=GRAY, rx=6)
    s.text(400, 115, '从进程 → 线程 → 代码栈 三层定位', 13, '#37474F', '700')
    s.text(400, 132, '核心命令: top → top -Hp → printf %x → jstack', 11, GRAY, italic=True)
    steps = [
        ('Step 1', 'top', '找到 CPU 高的\nJava 进程 PID', RED, 100),
        ('Step 2', 'top -Hp <pid>', '查看进程内\n各线程 CPU', ORANGE, 240),
        ('Step 3', 'printf "%x" <tid>', '线程 ID 转\n16 进制', PURPLE, 380),
        ('Step 4', 'jstack <pid>', '找 nid=0xXXX\n对应线程栈', BLUE, 520),
    ]
    for i, (step, cmd, desc, color, x) in enumerate(steps):
        s.rect(x, 170, 130, 200, color + '18', stroke=color, sw=2)
        s.rect(x, 170, 130, 30, color, stroke=color)
        s.text(x + 65, 190, step, 12, '#FFFFFF', '700')
        s.text(x + 65, 225, cmd, 11, color, '700')
        lines = desc.split('\n')
        for j, line in enumerate(lines):
            s.text(x + 65, 260 + j * 20, line, 10, '#37474F')
        s.text(x + 65, 350, f'→ 结果', 9, GRAY, italic=True)
        if i < 3:
            s.arrow(x + 130, 270, x + 150, 270, color=GRAY, width=2)
    s.rect(40, 400, 720, 160, '#FFEBEE', stroke=RED, rx=6)
    s.text(400, 425, '常见 CPU 高的根因', 13, RED, '700')
    causes = [
        ('死循环', 'while(true) 漏 break', RED),
        ('频繁 GC', 'Full GC 频繁触发', ORANGE),
        ('正则灾难', '恶意输入导致回溯', PURPLE),
        ('序列化', '深拷贝/反射过多', BLUE),
    ]
    for i, (name, desc, color) in enumerate(causes):
        x = 60 + i * 175
        s.rect(x, 445, 160, 90, color + '22', stroke=color, sw=2)
        s.text(x + 80, 470, name, 12, color, '700')
        s.text(x + 80, 495, desc, 10, '#37474F', italic=True)
    s.legend([(RED, '进程级'), (ORANGE, '线程级'), (PURPLE, '栈定位')], y=575)
    return s.render()


def gen_full_gc_troubleshoot():
    s = SVG(800, 600).title('频繁 Full GC 排查思路')
    s.rect(40, 90, 720, 50, '#FFEBEE', stroke=RED, rx=6)
    s.text(400, 115, '目标：找到 Full GC 触发条件 → 定位根因', 13, RED, '700')
    s.text(400, 132, '工具: jstat -gc / jmap / GC 日志 / Arthas', 11, '#B71C1C', italic=True)
    s.rect(40, 170, 720, 220, '#ECEFF1', stroke=GRAY, rx=6)
    s.text(400, 195, '排查步骤', 13, '#37474F', '700')
    diag_steps = [
        ('1', 'jstat -gc <pid> 1000', '观察 GC 频率/各代增长', BLUE, 60),
        ('2', '查看 Full GC 次数', '频繁 → 内存配置/泄漏', ORANGE, 240),
        ('3', 'jmap -histo:live', 'Top N 对象类型', PURPLE, 420),
        ('4', 'jmap -dump', 'Heap dump → MAT 分析', RED, 600),
    ]
    for i, (n, cmd, desc, color, x) in enumerate(diag_steps):
        s.rect(x, 215, 130, 150, color + '18', stroke=color, sw=2)
        s.rect(x, 215, 30, 30, color, stroke=color)
        s.text(x + 15, 234, n, 13, '#FFFFFF', '700')
        s.text(x + 80, 240, cmd.split(' ')[0], 10, color, '700')
        lines = desc.split('\n')
        for j, line in enumerate(lines):
            s.text(x + 65, 270 + j * 18, line, 10, '#37474F')
        if i < 3:
            s.arrow(x + 130, 290, x + 150, 290, color=GRAY, width=2)
    s.rect(40, 410, 720, 160, '#FFF3E0', stroke=ORANGE, rx=6)
    s.text(400, 435, '常见 Full GC 根因', 13, ORANGE, '700')
    causes = [
        ('内存泄漏', 'static 集合\n未清理', RED),
        ('大对象', '直接进老年代\n频繁分配', ORANGE),
        ('Metaspace 满', '动态生成类\nCGLIB/反射', PURPLE),
        ('System.gc', '代码显式调用\n应禁用', BLUE),
        ('空间担保失败', '晋升失败\n触发 Full', TEAL),
    ]
    for i, (name, desc, color) in enumerate(causes):
        x = 60 + i * 140
        s.rect(x, 450, 130, 110, color + '22', stroke=color, sw=1.5)
        s.text(x + 65, 475, name, 11, color, '700')
        lines = desc.split('\n')
        for j, line in enumerate(lines):
            s.text(x + 65, 500 + j * 16, line, 9, '#37474F')
    return s.render()


def gen_oom_types():
    s = SVG(800, 600).title('各种 OOM 排查与解决')
    types = [
        ('Java heap space', '堆内存溢出', RED, '对象太多/内存泄漏', '-Xmx / MAT 分析'),
        ('Metaspace', '元空间溢出', PURPLE, '动态生成类过多', '-XX:MaxMetaspaceSize'),
        ('GC overhead', 'GC 回收失败', ORANGE, '98% 时间 GC', '通常堆将满/加大堆'),
        ('Direct memory', '直接内存溢出', TEAL, 'NIO ByteBuf 未释放', '-XX:MaxDirectMemorySize'),
        ('StackOverflow', '栈溢出', BLUE, '递归过深 / -Xss 小', '-Xss 增大栈'),
        ('Unable to create', '无法创建线程', PINK, '线程数超系统限制', 'ulimit -u / 减线程'),
    ]
    for i, (err, name, color, cause, fix) in enumerate(types[:5]):
        x = 40 if i < 3 else 410
        yy = 100 + (i % 3) * 150
        s.rect(x, yy, 350, 130, color + '18', stroke=color, sw=2)
        s.rect(x, yy, 350, 28, color, stroke=color)
        s.text(x + 175, yy + 19, f'OutOfMemoryError: {err}', 12, '#FFFFFF', '700')
        s.text(x + 20, yy + 50, name, 13, color, '700', anchor='start')
        s.text(x + 20, yy + 75, '原因: ' + cause, 11, '#37474F', anchor='start')
        s.text(x + 20, yy + 100, '解决:', 11, GREEN, '700', anchor='start')
        s.text(x + 60, yy + 100, fix, 10, '#37474F', anchor='start')
    err, name, color, cause, fix = types[5]
    s.rect(40, 550, 720, 40, color + '22', stroke=color, sw=2)
    s.text(60, 575, f'{err}: {name}', 12, color, '700', anchor='start')
    s.text(440, 575, '原因: ' + cause, 10, '#37474F', anchor='start')
    s.text(720, 575, '解决: ' + fix, 10, GREEN, '600', anchor='end')
    return s.render()


def gen_arthas():
    s = SVG(800, 600).title('Arthas 线上诊断神器')
    s.rect(40, 90, 720, 50, '#E3F2FD', stroke=BLUE, rx=6)
    s.text(400, 115, 'Attach 到运行 JVM，无需重启即可诊断', 13, BLUE, '700')
    s.text(400, 132, '基于字节码增强 + Instrumentation API', 11, '#1565C0', italic=True)
    s.rect(40, 170, 350, 380, '#FAFAFA', stroke=GRAY, rx=6)
    s.text(215, 195, '常用命令', 14, '#37474F', '700')
    cmds = [
        ('dashboard', 'JVM 概览', GREEN),
        ('thread', '线程分析', BLUE),
        ('jad', '反编译', PURPLE),
        ('watch', '方法观测', ORANGE),
        ('trace', '调用链', TEAL),
        ('stack', '调用栈', PINK),
        ('monitor', '统计', INDIGO),
        ('sc', '类搜索', GRAY),
        ('heapdump', '堆转储', RED),
    ]
    for i, (cmd, cn, color) in enumerate(cmds):
        row = i // 3
        col = i % 3
        x = 55 + col * 110
        y = 220 + row * 100
        s.rect(x, y, 100, 90, color + '18', stroke=color, sw=1.5)
        s.rect(x, y, 100, 22, color, stroke=color)
        s.text(x + 50, y + 15, cmd, 10, '#FFFFFF', '700')
        s.text(x + 50, y + 50, cn, 10, color, '700')
    s.rect(410, 170, 350, 380, '#FFF3E0', stroke=ORANGE, rx=6)
    s.text(585, 195, '典型排查流程', 14, '#E65100', '700')
    flow_steps = [
        ('1. 启动', 'java -jar arthas-boot.jar'),
        ('2. 概览', 'dashboard 看整体'),
        ('3. 定位', 'thread <id> 看热点'),
        ('4. 反编译', 'jad com.xxx.Service'),
        ('5. 观测', 'watch 方法 返回值'),
        ('6. 追踪', 'trace 方法 耗时'),
        ('7. 退出', 'stop / shutdown'),
    ]
    for i, (step, desc) in enumerate(flow_steps):
        y = 220 + i * 45
        s.rect(425, y, 80, 35, BLUE + '22', stroke=BLUE, sw=1)
        s.text(465, y + 22, step, 11, BLUE, '700')
        s.text(515, y + 22, desc, 10, '#37474F', anchor='start')
    return s.render()


def gen_final_field():
    s = SVG(800, 500).title('final 字段的线程安全初始化')
    s.rect(40, 100, 720, 60, '#E8F5E9', stroke=GREEN, rx=6)
    s.text(400, 125, 'final 利用 JMM 内存屏障禁止构造期间重排序', 13, GREEN, '700')
    s.text(400, 148, '保证构造完成后所有线程可见正确状态', 11, '#1B5E20', italic=True)
    s.rect(40, 200, 350, 240, '#FFEBEE', stroke=RED, rx=6)
    s.rect(40, 200, 350, 32, RED, stroke=RED)
    s.text(215, 222, '普通字段 (无 final)', 13, '#FFFFFF', '700')
    s.text(60, 255, '可能重排序:', 12, RED, '700', anchor='start')
    s.text(80, 280, '1. 分配内存', 11, '#B71C1C', anchor='start')
    s.text(80, 300, '2. 设置引用 (publish)', 11, '#B71C1C', anchor='start')
    s.text(80, 320, '3. 初始化字段', 11, '#B71C1C', anchor='start')
    s.text(60, 355, '风险:', 12, RED, '700', anchor='start')
    s.text(80, 380, '其他线程看到 "半初始化" 对象', 11, '#B71C1C', anchor='start')
    s.text(80, 400, '字段为 null 或 0', 11, '#B71C1C', anchor='start')
    s.text(80, 420, '经典: DCL 单例模式', 11, RED, '700', anchor='start')
    s.rect(410, 200, 350, 240, '#E8F5E9', stroke=GREEN, rx=6)
    s.rect(410, 200, 350, 32, GREEN, stroke=GREEN)
    s.text(585, 222, 'final 字段', 13, '#FFFFFF', '700')
    s.text(430, 255, '保证顺序:', 12, GREEN, '700', anchor='start')
    s.text(450, 280, '1. 分配内存', 11, '#1B5E20', anchor='start')
    s.text(450, 300, '2. 初始化字段 (frozen)', 11, '#1B5E20', anchor='start')
    s.text(450, 320, '3. 设置引用 (publish)', 11, '#1B5E20', anchor='start')
    s.text(430, 355, '保证:', 12, GREEN, '700', anchor='start')
    s.text(450, 380, '构造完成 → 字段对所有线程可见', 11, '#1B5E20', anchor='start')
    s.text(450, 400, '不需 synchronized / volatile', 11, '#1B5E20', anchor='start')
    s.text(450, 420, '不可变对象天然线程安全', 11, GREEN, '700', anchor='start')
    s.rect(40, 460, 720, 30, '#ECEFF1', stroke=GRAY, rx=4)
    s.text(400, 480, 'final vs volatile: final 一次性写+读屏障, volatile 每次读写都屏障', 11, '#37474F', italic=True)
    return s.render()


def gen_virtual_thread():
    s = SVG(800, 600).title('虚拟线程 vs 平台线程 (JDK 21)')
    s.rect(40, 90, 350, 400, '#E3F2FD', stroke=BLUE, rx=8)
    s.rect(40, 90, 350, 36, BLUE, stroke=BLUE)
    s.text(215, 114, 'Platform Thread (传统)', 13, '#FFFFFF', '700')
    s.text(60, 155, '调度: OS 内核 (1:1)', 12, '#0D47A1', '700', anchor='start')
    s.text(60, 180, '栈: 固定 (~1MB)', 11, '#1565C0', anchor='start')
    s.text(60, 205, '创建成本: 高', 11, '#1565C0', anchor='start')
    s.text(60, 230, '上下文切换: 内核态 (~us)', 11, '#1565C0', anchor='start')
    s.text(60, 255, '数量: 千级 (受内存限制)', 11, '#1565C0', anchor='start')
    s.text(60, 290, 'IO 阻塞:', 12, RED, '700', anchor='start')
    s.text(80, 312, '整个线程阻塞', 11, '#B71C1C', anchor='start')
    s.text(80, 332, 'OS 线程被挂起', 11, '#B71C1C', anchor='start')
    s.text(80, 352, '需要线程池复用', 11, '#B71C1C', anchor='start')
    s.text(60, 395, '池化焦虑:', 12, ORANGE, '700', anchor='start')
    s.text(80, 418, '大小难调', 11, '#BF360C', anchor='start')
    s.text(80, 438, '小=排队，大=浪费', 11, '#BF360C', anchor='start')
    s.text(80, 458, '阻塞 = 资源浪费', 11, '#BF360C', anchor='start')
    s.rect(410, 90, 350, 400, '#E8F5E9', stroke=GREEN, rx=8)
    s.rect(410, 90, 350, 36, GREEN, stroke=GREEN)
    s.text(585, 114, 'Virtual Thread (JDK 21)', 13, '#FFFFFF', '700')
    s.text(430, 155, '调度: JVM 用户态 (M:N)', 12, '#1B5E20', '700', anchor='start')
    s.text(430, 180, '栈: 动态 (堆上, ~KB)', 11, '#388E3C', anchor='start')
    s.text(430, 205, '创建成本: 极低', 11, '#388E3C', anchor='start')
    s.text(430, 230, '上下文切换: 用户态 (~ns)', 11, '#388E3C', anchor='start')
    s.text(430, 255, '数量: 百万级', 11, '#388E3C', anchor='start')
    s.text(430, 290, 'IO 阻塞:', 12, GREEN, '700', anchor='start')
    s.text(450, 312, 'unmount 载体线程', 11, '#1B5E20', anchor='start')
    s.text(450, 332, '栈存堆，让出 OS 线程', 11, '#1B5E20', anchor='start')
    s.text(450, 352, '载体线程继续干活', 11, '#1B5E20', anchor='start')
    s.text(430, 395, '解决池化焦虑:', 12, GREEN, '700', anchor='start')
    s.text(450, 418, '一请求一线程', 11, '#1B5E20', anchor='start')
    s.text(450, 438, '同步代码风格', 11, '#1B5E20', anchor='start')
    s.text(450, 458, '异步性能', 11, '#1B5E20', anchor='start')
    s.rect(40, 510, 720, 70, '#ECEFF1', stroke=GRAY, rx=6)
    s.text(400, 535, 'M:N 调度模型', 13, '#37474F', '700')
    s.text(400, 555, '少量 Carrier Thread (ForkJoinPool) ↔ 海量 Virtual Thread', 11, '#37474F')
    s.text(400, 572, 'VirtualThread.block() → unmount → yield → Carrier 跑下一个', 10, GRAY, italic=True)
    return s.render()


def gen_jvm_tuning():
    s = SVG(800, 600).title('生产 JVM 调优流程')
    s.rect(40, 90, 720, 50, '#FFF3E0', stroke=ORANGE, rx=6)
    s.text(400, 115, '场景 → 收集器 → 堆大小 → 关键参数 → 监控', 13, '#E65100', '700')
    s.text(400, 132, '迭代调优：监控 → 分析 → 调整 → 验证', 11, '#BF360C', italic=True)
    steps = [
        ('1. 场景', '业务特征', '吞吐 / 延迟 / 内存', BLUE, 100),
        ('2. 收集器', 'GC 选择', 'Parallel/G1/ZGC', GREEN, 250),
        ('3. 堆大小', 'Xms=Xmx', '物理内存 1/2~2/3', ORANGE, 400),
        ('4. 关键参数', '监控诊断', 'GC 日志/HeapDumpOnOOM', PURPLE, 550),
    ]
    for i, (step, name, desc, color, x) in enumerate(steps):
        s.rect(x, 170, 130, 130, color + '18', stroke=color, sw=2)
        s.rect(x, 170, 130, 30, color, stroke=color)
        s.text(x + 65, 190, step, 11, '#FFFFFF', '700')
        s.text(x + 65, 225, name, 12, color, '700')
        lines = desc.split('\n')
        for j, line in enumerate(lines):
            s.text(x + 65, 250 + j * 18, line, 10, '#37474F')
        if i < 3:
            s.arrow(x + 130, 235, x + 150, 235, color=GRAY, width=2)
    s.rect(40, 330, 720, 240, '#FAFAFA', stroke=GRAY, rx=6)
    s.text(400, 355, '收集器选择矩阵', 13, '#37474F', '700')
    collectors = [
        ('Parallel', '高吞吐', '批处理/离线计算', '#66BB6A', 'JDK8 默认'),
        ('G1', '可预测停顿', '服务端主流', '#FF7043', 'JDK9+ 默认'),
        ('ZGC', '亚毫秒停顿', '低延迟/大堆', '#42A5F5', 'JDK15+ 生产'),
        ('Shenandoah', '并发整理', 'RedHat 主推', '#AB47BC', 'JDK12+ 可选'),
    ]
    for i, (name, feature, scene, color, note) in enumerate(collectors):
        x = 60 + i * 170
        s.rect(x, 380, 160, 170, color + '22', stroke=color, sw=2)
        s.rect(x, 380, 160, 28, color, stroke=color)
        s.text(x + 80, 400, name, 13, '#FFFFFF', '700')
        s.text(x + 80, 428, feature, 11, color, '700')
        s.text(x + 80, 452, scene, 10, '#37474F', italic=True)
        s.text(x + 80, 488, '推荐场景', 9, GRAY)
        s.text(x + 80, 505, scene, 9, '#37474F')
        s.text(x + 80, 535, note, 9, GRAY, italic=True)
    return s.render()


def gen_mat_oom():
    s = SVG(800, 600).title('OOM 现场 + MAT 排查流程')
    s.rect(40, 90, 350, 220, '#E3F2FD', stroke=BLUE, rx=8)
    s.rect(40, 90, 350, 32, BLUE, stroke=BLUE)
    s.text(215, 112, '保留现场证据', 13, '#FFFFFF', '700')
    ev = [
        ('JVM 启动参数', '-XX:+HeapDumpOnOutOfMemoryError'),
        ('GC 日志', '-Xlog:gc*:file=gc.log'),
        ('Heap Dump', '.hprof 文件 (自动生成)'),
        ('Error 日志', 'hs_err_pid<pid>.log'),
        ('应用日志', 'OOM 前后业务日志'),
        ('容器快照', 'docker top / kubectl describe'),
    ]
    for i, (name, detail) in enumerate(ev):
        y = 140 + i * 28
        s.text(60, y, '• ' + name, 11, BLUE, '700', anchor='start')
        s.text(220, y, detail, 9, GRAY, italic=True, anchor='start')
    s.rect(410, 90, 350, 220, '#FFF3E0', stroke=ORANGE, rx=8)
    s.rect(410, 90, 350, 32, ORANGE, stroke=ORANGE)
    s.text(585, 112, 'MAT 工具快速定位', 13, '#FFFFFF', '700')
    mat_steps = [
        ('1. 打开 hprof', 'MAT 自动解析'),
        ('2. Leak Suspects', '自动报告嫌疑对象'),
        ('3. Dominator Tree', '支配树 - 看保留大小'),
        ('4. Histogram', '按类统计对象数'),
        ('5. Path to GC Roots', '找引用链'),
        ('6. OQL 查询', 'SQL 风格查对象'),
    ]
    for i, (step, desc) in enumerate(mat_steps):
        y = 140 + i * 28
        s.text(430, y, step, 11, ORANGE, '700', anchor='start')
        s.text(580, y, desc, 9, GRAY, italic=True, anchor='start')
    s.rect(40, 330, 720, 240, '#FAFAFA', stroke=GRAY, rx=6)
    s.text(400, 355, '定位内存泄漏嫌疑对象流程', 13, '#37474F', '700')
    flow = [
        ('Histogram', '按 Retained\nHeap 排序', BLUE, 60),
        ('→ 找出', '异常大的\n类/对象', ORANGE, 230),
        ('Dominator', '查看 Path\nTo GC Roots', PURPLE, 400),
        ('→ 引用链', '定位到具体\n代码位置', RED, 570),
    ]
    for i, (name, desc, color, x) in enumerate(flow):
        s.rect(x, 390, 150, 80, color + '22', stroke=color, sw=2)
        s.rect(x, 390, 150, 24, color, stroke=color)
        s.text(x + 75, 408, name, 11, '#FFFFFF', '700')
        lines = desc.split('\n')
        for j, line in enumerate(lines):
            s.text(x + 75, 435 + j * 18, line, 10, '#37474F')
        if i < 3:
            s.arrow(x + 150, 430, x + 170, 430, color=GRAY, width=2)
    s.text(400, 510, '关键指标: Shallow Heap (自身) vs Retained Heap (含引用)', 11, PURPLE, '600', italic=True)
    s.text(400, 535, '深堆 (Retained) 大 = GC 后可释放多 = 重点嫌疑', 11, RED, '700')
    return s.render()


def gen_zgc_generational():
    s = SVG(800, 600).title('ZGC Generational 分代优化')
    s.rect(40, 90, 720, 60, '#E3F2FD', stroke=BLUE, rx=6)
    s.text(400, 115, 'JDK 21: ZGC 引入分代模式', 14, BLUE, '700')
    s.text(400, 137, '减少扫描范围 + 保持低停顿 + 兼顾吞吐量', 11, '#1565C0', italic=True)
    s.rect(40, 180, 350, 180, '#FFEBEE', stroke=RED, rx=8)
    s.rect(40, 180, 350, 32, RED, stroke=RED)
    s.text(215, 202, '非分代 ZGC (旧)', 13, '#FFFFFF', '700')
    s.text(60, 240, '问题:', 12, RED, '700', anchor='start')
    s.text(80, 265, '• 全堆并发标记', 11, '#B71C1C', anchor='start')
    s.text(80, 285, '• 朝生夕灭对象也要扫', 11, '#B71C1C', anchor='start')
    s.text(80, 305, '• 标记成本随堆增大', 11, '#B71C1C', anchor='start')
    s.text(80, 325, '• 吞吐量损失较大', 11, '#B71C1C', anchor='start')
    s.text(80, 345, '• barrier 开销大', 11, '#B71C1C', anchor='start')
    s.rect(410, 180, 350, 180, '#E8F5E9', stroke=GREEN, rx=8)
    s.rect(410, 180, 350, 32, GREEN, stroke=GREEN)
    s.text(585, 202, 'Generational ZGC (新)', 13, '#FFFFFF', '700')
    s.text(430, 240, '优化:', 12, GREEN, '700', anchor='start')
    s.text(450, 265, '• 物理分代 (Young/Old)', 11, '#1B5E20', anchor='start')
    s.text(450, 285, '• Young GC 只扫新生代', 11, '#1B5E20', anchor='start')
    s.text(450, 305, '• 90%+ 对象短命 → 快速回收', 11, '#1B5E20', anchor='start')
    s.text(450, 325, '• 减少 remembered set 维护', 11, '#1B5E20', anchor='start')
    s.text(450, 345, '• barrier 优化 (双层指针)', 11, '#1B5E20', anchor='start')
    s.rect(40, 390, 720, 180, '#FAFAFA', stroke=GRAY, rx=6)
    s.text(400, 415, '关键指标对比', 13, '#37474F', '700')
    metrics = [
        ('GC 停顿', '< 1ms (保持)', GREEN),
        ('吞吐量', '+10~20%', BLUE),
        ('堆扫描量', '大幅减少', PURPLE),
        ('屏障开销', '降低', ORANGE),
    ]
    for i, (name, value, color) in enumerate(metrics):
        x = 60 + i * 170
        s.rect(x, 440, 160, 110, color + '22', stroke=color, sw=2)
        s.text(x + 80, 470, name, 12, color, '700')
        s.text(x + 80, 500, value, 13, '#37474F', '700')
        s.text(x + 80, 530, ['亚毫秒', '吞吐回升', 'Young GC 快', 'barrier 简化'][i], 10, GRAY, italic=True)
    return s.render()


def gen_graalvm_reflection():
    s = SVG(800, 500).title('GraalVM Native Image 反射方案')
    s.rect(40, 100, 720, 60, '#E3F2FD', stroke=BLUE, rx=6)
    s.text(400, 125, 'Native Image 构建时封闭世界分析 (Closed World)', 13, BLUE, '700')
    s.text(400, 148, '反射类需提前告知，传统方案：手动 reflect-config.json', 11, '#1565C0', italic=True)
    s.rect(40, 200, 340, 220, '#FFEBEE', stroke=RED, rx=6)
    s.rect(40, 200, 340, 32, RED, stroke=RED)
    s.text(210, 222, '传统方案: 手动配置', 12, '#FFFFFF', '700')
    s.text(60, 260, 'reflect-config.json', 11, RED, '700', anchor='start')
    s.text(80, 282, '痛点:', 11, '#B71C1C', '700', anchor='start')
    s.text(100, 302, '• 类名/方法易遗漏', 10, '#B71C1C', anchor='start')
    s.text(100, 322, '• 字段需逐个声明', 10, '#B71C1C', anchor='start')
    s.text(100, 342, '• 调试成本高', 10, '#B71C1C', anchor='start')
    s.text(100, 362, '• 框架集成复杂', 10, '#B71C1C', anchor='start')
    s.text(100, 382, '• 升级易踩坑', 10, '#B71C1C', anchor='start')
    s.text(100, 405, '维护噩梦', 11, RED, '700', anchor='start')
    s.rect(420, 200, 340, 220, '#E8F5E9', stroke=GREEN, rx=6)
    s.rect(420, 200, 340, 32, GREEN, stroke=GREEN)
    s.text(590, 222, '现代方案: 4 种替代', 12, '#FFFFFF', '700')
    modern = [
        ('Tracing Agent', '运行时记录反射 → 自动生成配置', BLUE),
        ('Runtime Hints API', 'Spring 6+ 编程式声明 ReflectionHints', GREEN),
        ('公共元数据库', 'Reachability Metadata Hub 共享配置', PURPLE),
        ('AOT 友好 API', 'MethodHandle/VarHandle 替代反射', ORANGE),
    ]
    for i, (name, desc, color) in enumerate(modern):
        y = 250 + i * 42
        s.rect(440, y, 300, 36, color + '18', stroke=color, sw=1.5)
        s.text(455, y + 15, name, 11, color, '700', anchor='start')
        s.text(455, y + 30, desc, 9, '#37474F', anchor='start')
    return s.render()


def gen_leyden():
    s = SVG(800, 500).title('Project Leyden: 云原生 Java AOT')
    s.rect(40, 100, 720, 60, '#E3F2FD', stroke=BLUE, rx=6)
    s.text(400, 125, '目标: AOT + 保留完整 Java 特性', 14, BLUE, '700')
    s.text(400, 148, '解决云原生场景下 Java 冷启动慢 + 内存占用高', 11, '#1565C0', italic=True)
    s.rect(40, 200, 340, 240, '#FFEBEE', stroke=RED, rx=6)
    s.rect(40, 200, 340, 32, RED, stroke=RED)
    s.text(210, 222, '云原生痛点', 12, '#FFFFFF', '700')
    pains = [
        ('冷启动慢', 'JIT warmup 数秒~分钟'),
        ('内存占用高', '运行时数据 + CodeCache'),
        ('实例频繁扩缩', '每次冷启动都付代价'),
        ('Serverless 不友好', '请求超时风险'),
        ('与 Go/Rust 差距', '启动/内存落后'),
    ]
    for i, (name, desc) in enumerate(pains):
        y = 250 + i * 36
        s.text(60, y, '• ' + name, 11, RED, '700', anchor='start')
        s.text(180, y, desc, 9, '#B71C1C', italic=True, anchor='start')
    s.rect(420, 200, 340, 240, '#E8F5E9', stroke=GREEN, rx=6)
    s.rect(420, 200, 340, 32, GREEN, stroke=GREEN)
    s.text(590, 222, 'Leyden 方案', 12, '#FFFFFF', '700')
    sols = [
        ('提前加载/链接', 'Loading/Linking AOT'),
        ('提前方法解析', 'Method Resolution AOT'),
        ('代码预热 (CDS)', 'Class Data Sharing 扩展'),
        ('AOT 编译', '关键方法编译为本地码'),
        ('保持 JIT 能力', '运行时仍可优化'),
    ]
    for i, (name, desc) in enumerate(sols):
        y = 250 + i * 36
        s.text(440, y, '• ' + name, 11, GREEN, '700', anchor='start')
        s.text(580, y, desc, 9, '#1B5E20', italic=True, anchor='start')
    s.legend([(RED, '云原生痛点'), (GREEN, 'Leyden 解决'), (BLUE, '保留 Java 特性')], y=465)
    return s.render()


def gen_async_profiler():
    s = SVG(800, 600).title('Async-Profiler 火焰图分析')
    s.rect(40, 90, 720, 50, '#E3F2FD', stroke=BLUE, rx=6)
    s.text(400, 115, '低开销采样 → 生成火焰图 → 定位 CPU 热点', 13, BLUE, '700')
    s.text(400, 132, '基于 async-get-call-tree (无 instrumentation 开销)', 11, '#1565C0', italic=True)
    s.rect(40, 170, 720, 280, '#FAFAFA', stroke=GRAY)
    s.text(400, 195, '火焰图 (Flame Graph)', 13, '#37474F', '700')
    rects = [
        (40, 410, 720, 25, '#90CAF9', 'main', BLUE),
        (40, 385, 600, 25, '#64B5F6', 'Tomcat.handleRequest', BLUE),
        (40, 360, 500, 25, '#42A5F5', 'Controller.process', BLUE),
        (40, 335, 400, 25, '#2196F3', 'Service.calc', BLUE),
        (40, 310, 200, 25, '#FF7043', 'DAO.executeQuery', ORANGE),
        (240, 310, 150, 25, '#EF5350', 'Regex.match', RED),
        (40, 285, 150, 25, '#FF8A65', 'JDBC.executeQuery', ORANGE),
        (240, 285, 120, 25, '#E57373', 'Pattern.compile', RED),
        (240, 260, 80, 25, '#EF5350', 'backtrack!', RED),
    ]
    for x, y, w, h, fill, label, color in rects:
        s.rect(x, y, w, h, fill, stroke=color, sw=1, rx=2)
        s.text(x + w/2, y + 17, label, 10, '#212121', '700')
    s.arrow(280, 250, 280, 240, color=RED, width=2, marker='arrowR')
    s.text(310, 245, '↑ 栈顶最宽 = CPU 热点', 11, RED, '700', anchor='start')
    s.rect(40, 470, 720, 100, '#FFF3E0', stroke=ORANGE, rx=6)
    s.text(400, 495, '使用步骤', 13, '#E65100', '700')
    steps_text = [
        ('1. 启动采样', './profiler.sh -d 30 -f flame.html <pid>', BLUE),
        ('2. 分析火焰图', '找最宽的栈顶 → 定位方法', GREEN),
        ('3. 优化代码', '消除热点 (缓存/算法/批处理)', PURPLE),
    ]
    for i, (step, desc, color) in enumerate(steps_text):
        x = 60 + i * 230
        s.rect(x, 510, 220, 50, color + '22', stroke=color, sw=1.5)
        s.text(x + 110, 528, step, 11, color, '700')
        s.text(x + 110, 548, desc, 9, '#37474F', italic=True)
    return s.render()


def gen_mat_views():
    s = SVG(800, 500).title('MAT: Dominator Tree vs Histogram')
    s.rect(40, 90, 720, 60, '#E3F2FD', stroke=BLUE, rx=6)
    s.text(400, 115, 'MAT 两大核心视图对比', 13, BLUE, '700')
    s.text(400, 137, '直方图找数量 → 支配树找源头', 11, '#1565C0', italic=True)
    s.rect(40, 180, 340, 250, '#FFF3E0', stroke=ORANGE, rx=8)
    s.rect(40, 180, 340, 32, ORANGE, stroke=ORANGE)
    s.text(210, 202, 'Histogram (直方图)', 12, '#FFFFFF', '700')
    s.text(60, 235, '维度: 按 类 分组统计', 11, '#E65100', '700', anchor='start')
    s.text(60, 260, '关心: 对象 数量 与 浅堆', 11, '#BF360C', anchor='start')
    s.rect(60, 280, 310, 24, '#FFE0B2', stroke=ORANGE, sw=1)
    s.text(70, 297, 'Class', 9, '#37474F', '700', anchor='start')
    s.text(220, 297, 'Objects', 9, '#37474F', '700', anchor='start')
    s.text(290, 297, 'Shallow', 9, '#37474F', '700', anchor='start')
    rows = [
        ('byte[]', '1.2M', '480MB'),
        ('java.lang.String', '950K', '45MB'),
        ('java.util.HashMap$Node', '800K', '38MB'),
        ('char[]', '600K', '28MB'),
    ]
    for i, (cls, num, size) in enumerate(rows):
        y = 308 + i * 22
        s.text(70, y, cls, 9, '#37474F', anchor='start')
        s.text(220, y, num, 9, '#37474F', anchor='start')
        s.text(290, y, size, 9, '#37474F', anchor='start')
    s.text(60, 410, '适合: 找重复对象多的类', 10, PURPLE, '600', italic=True, anchor='start')
    s.rect(420, 180, 340, 250, '#E8F5E9', stroke=GREEN, rx=8)
    s.rect(420, 180, 340, 32, GREEN, stroke=GREEN)
    s.text(590, 202, 'Dominator Tree (支配树)', 12, '#FFFFFF', '700')
    s.text(440, 235, '维度: 按 支配关系 树状结构', 11, '#1B5E20', '700', anchor='start')
    s.text(440, 260, '关心: 保留堆 (Retained Heap)', 11, '#388E3C', anchor='start')
    s.rect(560, 280, 80, 24, '#A5D6A7', stroke=GREEN, sw=1)
    s.text(600, 297, 'ClassLoader', 9, '#1B5E20', '700')
    s.arrow(590, 304, 510, 326, color=GREEN, width=1.5)
    s.arrow(610, 304, 690, 326, color=GREEN, width=1.5)
    s.rect(470, 326, 90, 24, '#81C784', stroke=GREEN, sw=1)
    s.text(515, 343, 'HashMap', 9, '#1B5E20', '700')
    s.rect(660, 326, 80, 24, '#81C784', stroke=GREEN, sw=1)
    s.text(700, 343, 'ArrayList', 9, '#1B5E20', '700')
    s.arrow(500, 350, 480, 372, color=GREEN, width=1.5)
    s.rect(440, 372, 90, 22, '#66BB6A', stroke=GREEN, sw=1)
    s.text(485, 387, 'Node[]', 9, '#1B5E20', '700')
    s.text(590, 410, '适合: 找内存占用源头', 10, PURPLE, '600', italic=True, anchor='start')
    s.legend([(ORANGE, '直方图: 找数量'), (GREEN, '支配树: 找源头')], y=450)
    return s.render()


def gen_js_gc():
    s = SVG(800, 500).title('JS/现代动态语言 内存管理 GC')
    s.rect(40, 100, 720, 60, '#ECEFF1', stroke=GRAY, rx=6)
    s.text(400, 125, '自动识别并回收不再使用的内存', 13, '#37474F', '700')
    s.text(400, 145, '现代引擎主要使用 标记-清除 (Mark-Sweep)', 11, GRAY, italic=True)
    s.rect(40, 200, 720, 200, '#FFFDE7', stroke=ORANGE, rx=8)
    s.text(400, 225, '分代回收 (V8 / JVM 类似)', 13, '#E65100', '700')
    s.rect(60, 250, 320, 130, '#C8E6C9', stroke=GREEN, sw=2)
    s.text(220, 275, '新生代 (Young)', 13, '#1B5E20', '700')
    s.text(220, 300, 'Scavenger / Cheney 复制算法', 11, '#388E3C')
    s.text(220, 325, 'From → To 半区复制', 11, '#388E3C')
    s.text(220, 355, '短命对象快速回收', 11, '#388E3C', italic=True)
    s.rect(400, 250, 320, 130, '#FFCDD2', stroke=RED, sw=2)
    s.text(560, 275, '老年代 (Old)', 13, '#B71C1C', '700')
    s.text(560, 300, 'Mark-Sweep-Compact', 11, '#D84315')
    s.text(560, 325, '标记 → 清除 → 整理', 11, '#D84315')
    s.text(560, 355, '长寿命对象', 11, '#D84315', italic=True)
    s.rect(40, 420, 720, 60, '#FFEBEE', stroke=RED, rx=6)
    s.text(400, 445, '常见内存泄漏源', 12, RED, '700')
    s.text(400, 465, '闭包持有 / 全局变量 / 未清理的定时器 / DOM 引用 / 循环引用', 11, '#B71C1C')
    return s.render()


def gen_instruction_set():
    s = SVG(800, 500).title('指令集 (Instruction Set)')
    s.rect(40, 100, 720, 60, '#ECEFF1', stroke=GRAY, rx=6)
    s.text(400, 125, 'CPU 能识别的命令集合', 14, '#37474F', '700')
    s.text(400, 148, 'JVM 执行引擎: 字节码 → 指令集 → 机器码', 11, GRAY, italic=True)
    s.rect(40, 190, 350, 250, '#E3F2FD', stroke=BLUE, rx=8)
    s.rect(40, 190, 350, 32, BLUE, stroke=BLUE)
    s.text(215, 212, 'CISC (复杂指令集)', 13, '#FFFFFF', '700')
    s.text(60, 250, '代表: x86/x64', 12, '#0D47A1', '700', anchor='start')
    s.text(60, 275, '特点:', 12, BLUE, '700', anchor='start')
    s.text(80, 300, '• 指令长度可变', 11, '#1565C0', anchor='start')
    s.text(80, 320, '• 指令丰富 (1000+)', 11, '#1565C0', anchor='start')
    s.text(80, 340, '• 单指令完成复杂操作', 11, '#1565C0', anchor='start')
    s.text(80, 360, '• 内存直接操作', 11, '#1565C0', anchor='start')
    s.text(60, 395, '优势: 编程简单', 11, GREEN, '700', anchor='start')
    s.text(60, 415, '劣势: 功耗/解码复杂', 11, RED, '700', anchor='start')
    s.rect(410, 190, 350, 250, '#E8F5E9', stroke=GREEN, rx=8)
    s.rect(410, 190, 350, 32, GREEN, stroke=GREEN)
    s.text(585, 212, 'RISC (精简指令集)', 13, '#FFFFFF', '700')
    s.text(430, 250, '代表: ARM/RISC-V', 12, '#1B5E20', '700', anchor='start')
    s.text(430, 275, '特点:', 12, GREEN, '700', anchor='start')
    s.text(450, 300, '• 指令长度固定', 11, '#388E3C', anchor='start')
    s.text(450, 320, '• 指令少 (~100)', 11, '#388E3C', anchor='start')
    s.text(450, 340, '• Load/Store 架构', 11, '#388E3C', anchor='start')
    s.text(450, 360, '• 单周期执行', 11, '#388E3C', anchor='start')
    s.text(430, 395, '优势: 低功耗/流水线', 11, GREEN, '700', anchor='start')
    s.text(430, 415, '劣势: 指令数多', 11, RED, '700', anchor='start')
    return s.render()


def gen_user_class():
    s = SVG(800, 500).title('用户自定义类 (POJO/Bean)')
    s.rect(40, 100, 720, 60, '#ECEFF1', stroke=GRAY, rx=6)
    s.text(400, 125, '封装数据与行为的模板', 14, '#37474F', '700')
    s.text(400, 148, '通过构造器初始化 → 方法暴露功能 → 保护内部状态', 11, GRAY, italic=True)
    s.rect(150, 190, 500, 280, '#FAFAFA', stroke=GRAY, sw=2, rx=8)
    s.rect(150, 190, 500, 40, '#37474F', stroke=GRAY)
    s.text(400, 215, 'class User { }', 15, '#FFFFFF', '700')
    s.rect(170, 250, 460, 80, '#E3F2FD', stroke=BLUE, sw=1.5)
    s.text(190, 273, '字段 (Fields) - 状态', 12, BLUE, '700', anchor='start')
    s.text(190, 295, 'private String name;', 11, '#0D47A1', anchor='start')
    s.text(190, 315, 'private int age;  // 封装隐藏', 11, '#0D47A1', anchor='start')
    s.rect(170, 345, 460, 50, '#FFF3E0', stroke=ORANGE, sw=1.5)
    s.text(190, 368, '构造器 (Constructor) - 初始化', 12, '#E65100', '700', anchor='start')
    s.text(190, 388, 'public User(name, age) { ... }', 11, '#BF360C', anchor='start')
    s.rect(170, 410, 460, 50, '#E8F5E9', stroke=GREEN, sw=1.5)
    s.text(190, 433, '方法 (Methods) - 行为', 12, '#1B5E20', '700', anchor='start')
    s.text(190, 453, 'getter / setter / business logic', 11, '#388E3C', anchor='start')
    s.legend([(BLUE, '状态(字段)'), (ORANGE, '初始化'), (GREEN, '行为(方法)')], y=490)
    return s.render()


def gen_g1_mixed_gc():
    s = SVG(800, 600).title('G1 Mixed GC 触发条件与 Region 回收')
    s.rect(40, 90, 720, 60, '#FFF3E0', stroke=ORANGE, rx=6)
    s.text(400, 115, 'Mixed GC = 年轻代 GC + 部分老年代 Region', 13, '#E65100', '700')
    s.text(400, 138, '基于停顿预测模型，按收益排序回收', 11, '#BF360C', italic=True)
    s.rect(40, 170, 720, 130, '#ECEFF1', stroke=GRAY, rx=6)
    s.text(400, 195, '触发条件', 13, '#37474F', '700')
    triggers = [
        ('Heap Use > 45%', '-XX:InitiatingHeapOccupancyPercent', RED),
        ('预测到期', 'G1 自动判断', ORANGE),
        ('Mixed GC 后', '上年老年代回收不充分', PURPLE),
        ('显式调用', 'System.gc() (humorous)', GRAY),
    ]
    for i, (name, desc, color) in enumerate(triggers):
        x = 60 + i * 170
        s.rect(x, 215, 160, 70, color + '22', stroke=color, sw=2)
        s.text(x + 80, 240, name, 11, color, '700')
        s.text(x + 80, 265, desc, 9, GRAY, italic=True)
    s.rect(40, 320, 720, 240, '#FAFAFA', stroke=GRAY, rx=6)
    s.text(400, 345, 'Region 回收优先级 (Garbage First)', 13, '#37474F', '700')
    cellw = 70
    cellh = 45
    cells = [
        ('S', '#DCEDC8', GREEN, ''),
        ('E', '#C8E6C9', GREEN, ''),
        ('O(80%)', '#FFCDD2', RED, '1st'),
        ('O(70%)', '#FFCDD2', RED, '2nd'),
        ('O(60%)', '#FFE0B2', ORANGE, '3rd'),
        ('O(50%)', '#FFE0B2', ORANGE, 'skip'),
        ('H', '#FFE0B2', ORANGE, ''),
        ('U', '#ECEFF1', GRAY, ''),
    ]
    for i, (label, fill, stroke, badge) in enumerate(cells):
        x = 70 + i * 80
        y = 380
        s.rect(x, y, cellw, cellh, fill, stroke=stroke, sw=1.5)
        s.text(x + cellw/2, y + 25, label, 11, '#37474F', '700')
        if badge:
            s.rect(x + cellw - 30, y - 12, 30, 18, BLUE, stroke=BLUE, rx=3)
            s.text(x + cellw - 15, y, badge, 8, '#FFFFFF', '700')
    s.text(400, 455, '回收规则:', 12, '#37474F', '700')
    s.text(60, 480, '1. 在 -XX:MaxGCPauseMillis 内尽可能回收收益最高的 Region', 11, '#1B5E20', anchor='start')
    s.text(60, 500, '2. 回收 = 复制存活对象到空 Region (无碎片)', 11, '#1B5E20', anchor='start')
    s.text(60, 520, '3. CSet (Collection Set) 选择高 garbage 比例的 Region', 11, '#1B5E20', anchor='start')
    s.text(60, 540, '4. -XX:G1MixedGCCountTarget 控制混合回收次数', 11, '#1B5E20', anchor='start')
    return s.render()


def gen_default_diagram(title, essence, key_points):
    s = SVG(800, 500).title(title[:40] if title else '知识点图')
    s.text(400, 90, essence[:50] + ('...' if len(essence) > 50 else ''), 13, GRAY, italic=True)
    n = min(len(key_points), 6)
    cw = 340
    ch = 90
    sx = 50
    sy = 130
    colors = [BLUE, GREEN, ORANGE, PURPLE, TEAL, PINK]
    for i in range(n):
        col = i % 2
        row = i // 2
        x = sx + col * (cw + 20)
        y = sy + row * (ch + 20)
        color = colors[i % len(colors)]
        s.rect(x, y, cw, ch, color + '18', stroke=color, sw=2)
        s.rect(x, y, 50, ch, color, stroke=color)
        s.text(x + 25, y + ch/2 + 5, str(i+1), 18, '#FFFFFF', '700')
        kp = key_points[i]
        if len(kp) > 35:
            mid = len(kp) // 2
            sl = kp.rfind('：', 0, mid)
            if sl < 0: sl = kp.rfind(' ', 0, mid)
            if sl < 0: sl = mid
            s.text(x + 195, y + 38, kp[:sl], 12, '#37474F', '700')
            s.text(x + 195, y + 60, kp[sl:].strip(), 12, '#37474F')
        else:
            s.text(x + 195, y + 50, kp, 13, '#37474F', '700')
    s.legend([(BLUE, '要点 1'), (GREEN, '要点 2'), (ORANGE, '要点 3')], y=470)
    return s.render()


def gen_primitive_vs_wrapper():
    s = SVG(800, 600).title('Java 基本类型 vs 包装类型 (Wrapper)')
    s.rect(40, 100, 720, 60, '#ECEFF1', stroke=GRAY, rx=6)
    s.text(400, 125, '基本类型是数据值，包装类型是对象，差异巨大', 13, '#37474F', '700')
    s.text(400, 148, '自动装箱/拆箱是编译期语法糖', 11, GRAY, italic=True)
    # Primitive
    s.rect(40, 190, 350, 200, '#E8F5E9', stroke=GREEN, sw=2, rx=8)
    s.rect(40, 190, 350, 36, GREEN, stroke=GREEN)
    s.text(215, 213, '基本类型 (Primitive)', 14, '#FFFFFF', '700')
    rows_p = [
        ('存储位置', '栈 / 方法区 (final)'),
        ('默认值', '0 / 0.0 / false'),
        ('内存占用', '小 (int=4B)'),
        ('比较方式', '== 比较数值'),
        ('泛型支持', '不支持 (List<int> 无效)'),
    ]
    for i, (k, v) in enumerate(rows_p):
        y = 240 + i * 28
        s.text(60, y, k + ':', 11, '#1B5E20', '700', anchor='start')
        s.text(180, y, v, 11, '#37474F', anchor='start')
    # Wrapper
    s.rect(410, 190, 350, 200, '#FFEBEE', stroke=RED, sw=2, rx=8)
    s.rect(410, 190, 350, 36, RED, stroke=RED)
    s.text(585, 213, '包装类型 (Wrapper)', 14, '#FFFFFF', '700')
    rows_w = [
        ('存储位置', '堆 (对象实例)'),
        ('默认值', 'null (易触发 NPE!)'),
        ('内存占用', '大 (对象头+数据)'),
        ('比较方式', '== 比较地址'),
        ('泛型支持', '支持 (List<Integer>)'),
    ]
    for i, (k, v) in enumerate(rows_w):
        y = 240 + i * 28
        s.text(430, y, k + ':', 11, '#B71C1C', '700', anchor='start')
        s.text(550, y, v, 11, '#37474F', anchor='start')
    # Integer cache
    s.rect(40, 410, 350, 140, '#FFF3E0', stroke=ORANGE, rx=6)
    s.text(215, 432, 'Integer 缓存陷阱', 13, '#E65100', '700')
    s.text(60, 458, '默认缓存 -128 ~ 127', 11, '#BF360C', '700', anchor='start')
    s.text(60, 480, 'Integer a=100, b=100;', 10, '#37474F', anchor='start')
    s.text(60, 498, '  a == b  →  true  (命中缓存)', 10, GREEN, '700', anchor='start')
    s.text(60, 518, 'Integer a=200, b=200;', 10, '#37474F', anchor='start')
    s.text(60, 536, '  a == b  →  false (新对象)', 10, RED, '700', anchor='start')
    # Memory layout
    s.rect(410, 410, 350, 140, '#F3E5F5', stroke=PURPLE, rx=6)
    s.text(585, 432, '包装类型内存布局', 13, '#4A148C', '700')
    s.text(430, 458, '栈: 引用 → 堆对象', 11, '#4A148C', '700', anchor='start')
    s.text(430, 480, '[堆 Integer 对象]', 10, '#37474F', anchor='start')
    s.text(450, 498, 'Mark Word (8B) + Class Ptr (4B)', 9, '#6A1B9A', anchor='start')
    s.text(450, 516, '+ int value (4B) = 16B+', 9, '#6A1B9A', anchor='start')
    s.text(450, 534, 'vs 基本类型仅 4B (4x)', 9, RED, '700', anchor='start')
    return s.render()


# ---------------- Map filename -> generator ----------------
GENERATORS = {
    # Memory
    'jkc-001': gen_jvm_memory_areas,
    'jkc-002': gen_heap_generations,
    'jkc-004': gen_gc_collectors,
    'jvm-007': gen_jvm_memory_areas,
    'jvm-019': gen_method_area,
    'jvm-020': gen_memory_model_runtime,
    'jvm-029': gen_memory_model_runtime,
    'jvm-004': gen_permgen_vs_metaspace,
    'jvm-045': gen_jdk18_metaspace,
    'jvm-005': gen_vm_stack,

    # NIO
    'jvm-001': gen_nio_selector,
    'jvm-006': gen_nio_selector,
    'jvm-008': gen_nio_selector,
    'jvm-024': gen_nio_selector,
    'jvm-027': gen_io_evolution,

    # GC algorithms
    'jvm-017': gen_gc_algorithms,
    'jvm-037': gen_generational_collection,
    'jvm-038': gen_copying_algorithm,
    'jvm-039': gen_gc_roots,
    'jvm-013': gen_generational_vs_regional,
    'jvm-018': gen_heap_generations,

    # GC collectors
    'jvm-003': gen_cms_phases,
    'jvm-015': gen_g1_regions,
    'jvm-026': gen_serial_old,
    'jvm-051': gen_stw,
    'jvm-053': gen_escape_analysis,
    'jvm-055': gen_oom_vs_leak,
    'jvm-057': gen_gc_types,
    'jvm-059': gen_gc_trigger,
    'jvm-061': gen_promotion_guarantee,
    'jvm-065': gen_cms_phases,
    'jvm-069': gen_zgc_colored_pointer,
    'jvm-071': gen_cms_vs_g1,
    'jvm-083': gen_zgc_colored_pointer,
    'jvm-089': gen_tricolor_marking,

    # Class loading
    'jvm-014': gen_class_loading,
    'jvm-040': gen_class_loading,
    'jvm-041': gen_class_loading,
    'jvm-035': gen_parent_delegation,
    'jvm-016': gen_parent_delegation,
    'jvm-081': gen_tomcat_classloader,
    'jvm-010': lambda: gen_primitive_vs_wrapper(),

    # Object
    'jvm-047': gen_object_creation,
    'jvm-086': gen_object_creation,
    'jvm-049': gen_object_layout,
    'tr5-009': gen_object_layout,

    # tr4/tr3 specific
    'tr4-003': gen_g1_mixed_gc,

    # JIT / Compiler
    'jvm-009': gen_hotspot_code,
    'jvm-021': gen_interpreter,
    'jvm-028': gen_jit_compiler,
    'jvm-033': gen_aot_vs_jit,
    'jvm-032': gen_instruction_set,
    'jvm-034': gen_user_class,

    # Diagnosis
    'jvm-073': gen_cpu_troubleshoot,
    'jvm-075': gen_full_gc_troubleshoot,
    'jvm-087': gen_oom_types,
    'jvm-090': gen_arthas,
    'jvm-091': gen_final_field,
    'trd-001': gen_virtual_thread,
    'jvm-084': gen_jvm_tuning,
    'jvm-030': gen_jmm,

    # tr2/tr3/tr4
    'tr2-001': gen_mat_oom,
    'tr2-013': gen_escape_analysis,
    'tr3-002': gen_zgc_generational,
    'tr3-004': gen_graalvm_reflection,
    'tr3-014': gen_leyden,
    'tr4-001': gen_async_profiler,
    'tr4-002': gen_mat_views,
    'dsl-061': gen_js_gc,
}


def find_generator(filename):
    base = filename.replace('.md', '')
    if base in GENERATORS:
        return GENERATORS[base]
    return None


def insert_or_replace_diagram_section(content, fname_base, knowledge_name):
    img_md = (
        f'## 核心知识点图\n\n'
        f'<img src="/interview-2026/images/diagram_jvm_{fname_base}.svg" alt="{knowledge_name}" '
        f'style="max-width:100%;height:auto;border:1px solid var(--border);border-radius:8px;margin:1em 0;" />'
    )
    pattern = re.compile(
        r'^## (核心知识点图|核心架构图|核心流程图)[^\n]*\n(?:(?!^## ).+\n|\n)*',
        re.MULTILINE
    )
    content = pattern.sub('', content)
    memory_pattern = re.compile(r'^## 记忆要点\s*\n', re.MULTILINE)
    if memory_pattern.search(content):
        content = memory_pattern.sub(img_md + '\n\n## 记忆要点\n', content, count=1)
    else:
        content = content.rstrip() + '\n\n' + img_md + '\n'
    return content


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    files = sorted([f for f in os.listdir(QUESTIONS_DIR)
                    if f.endswith('.md') and f.startswith(('jvm', 'jkc', 'dsl', 'tr2', 'tr3', 'tr4', 'tr5', 'trd'))])
    print(f'Found {len(files)} files')
    success = 0
    defaulted = 0
    for fname in files:
        base = fname.replace('.md', '')
        path = os.path.join(QUESTIONS_DIR, fname)
        with open(path) as f:
            content = f.read()
        fm_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        fm = fm_match.group(1) if fm_match else ''
        title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else base
        essence_match = re.search(r'essence:\s*(.+)', fm)
        essence = essence_match.group(1).strip() if essence_match else ''
        kp_match = re.search(r'key_points:\s*\n((?:\s*-\s+.+\n?)+)', fm)
        kps = re.findall(r'-\s+(.+)', kp_match.group(1)) if kp_match else []
        gen = find_generator(fname)
        if gen is None:
            svg = gen_default_diagram(title, essence, kps)
            defaulted += 1
            tag = 'DEFAULT'
        else:
            try:
                svg = gen()
                tag = 'CUSTOM'
            except Exception as e:
                print(f'  ERR {fname}: {e}, using default')
                svg = gen_default_diagram(title, essence, kps)
                defaulted += 1
                tag = 'FALLBACK'
        svg_path = os.path.join(OUTPUT_DIR, f'diagram_jvm_{base}.svg')
        with open(svg_path, 'w') as f:
            f.write(svg)
        new_content = insert_or_replace_diagram_section(content, base, title)
        if new_content != content:
            with open(path, 'w') as f:
                f.write(new_content)
        success += 1
        print(f'  [{tag}] {fname} -> diagram_jvm_{base}.svg')
    print(f'\nDone: {success} SVG files generated ({defaulted} defaulted)')


if __name__ == '__main__':
    main()
