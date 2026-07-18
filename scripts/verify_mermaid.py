#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证生成脚本的 mermaid 代码：括号平衡、节点定义引用、classDef 引用。
不会渲染图（无浏览器依赖），但能捕获绝大多数语法错误。"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

from gen_mermaid import THEMES, _extract_title


def validate_mermaid(code):
    """轻量静态检查。真正的语法验证由 mmdc 渲染完成。
    此处只检查：边引用未定义的节点 ID、未定义的 classDef。"""
    errors = []
    lines = code.strip().split('\n')
    # 1. 整体括号平衡（每行）
    for i, ln in enumerate(lines, 1):
        # 跳过 classDef 定义行（包含 fill:）
        if 'classDef' in ln or 'class ' in ln:
            continue
        op = ln.count('{')
        cp = ln.count('}')
        ob = ln.count('[')
        cb = ln.count(']')
        op2 = ln.count('(')
        cp2 = ln.count(')')
        # 检查 decision 节点 { } 是否平衡
        if op != cp:
            errors.append(f'L{i} 大括号不平衡: {ln.strip()[:80]}')
    # 2. 节点 ID 定义收集
    node_defs = set()
    # 形如：  ID[...] / ID(...) / ID{...} / ID([..]) / ID[(..)]
    for ln in lines:
        m = re.match(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*[\[\(\{]', ln)
        if m:
            node_defs.add(m.group(1))
    # 3. 边引用的节点 ID
    edge_pattern = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)\s*[-.\-]+[>o]')
    edge_targets = re.compile(r'[-.\-]+[>o]\s*([A-Za-z_][A-Za-z0-9_]*)')
    referenced = set()
    for ln in lines:
        if 'classDef' in ln or ln.strip().startswith('class '):
            continue
        if not re.search(r'-[-.>]|-->|-.->|==>|-\.-|~~>', ln):
            continue
        for m in edge_pattern.finditer(ln):
            referenced.add(m.group(1))
        for m in edge_targets.finditer(ln):
            referenced.add(m.group(1))
    # 4. 检查未定义引用
    undefined = referenced - node_defs - {'TD', 'LR', 'BT', 'RL', 'flowchart'}
    # 容忍子图关键词等
    undefined -= {'subgraph', 'end'}
    if undefined:
        errors.append(f'引用了未定义的节点 ID: {sorted(undefined)}')
    # 5. classDef 类引用
    classes_used = set()
    for ln in lines:
        for m in re.finditer(r':::(\w+)', ln):
            classes_used.add(m.group(1))
    classes_defined = set()
    for ln in lines:
        m = re.match(r'^\s*classDef\s+(\w+)\s+', ln)
        if m:
            classes_defined.add(m.group(1))
    unknown_classes = classes_used - classes_defined
    if unknown_classes:
        errors.append(f'使用了未定义的 classDef: {sorted(unknown_classes)}')
    return errors


def main():
    import subprocess
    import shutil
    mmdc = shutil.which('mmdc')
    total = 0
    fail = 0
    for theme, fn in THEMES.items():
        total += 1
        fm = {'id': 'test-' + theme}
        title = '测试-' + theme
        code = fn(fm, title)
        errs = validate_mermaid(code)
        rendered = False
        render_err = ''
        if mmdc:
            import tempfile
            with tempfile.NamedTemporaryFile('w', suffix='.mmd', delete=False, encoding='utf-8') as f:
                f.write(code)
                mmd = f.name
            svg = mmd.replace('.mmd', '.svg')
            try:
                if os.path.exists(svg):
                    os.remove(svg)
                r = subprocess.run([mmdc, '-i', mmd, '-o', svg, '--quiet'], capture_output=True, text=True, timeout=60)
                rendered = r.returncode == 0 and os.path.exists(svg)
                if not rendered:
                    render_err = (r.stderr or r.stdout)[-300:]
            finally:
                for p in (mmd, svg):
                    try:
                        os.remove(p)
                    except OSError:
                        pass
        if errs or (mmdc and not rendered):
            fail += 1
            print(f'[FAIL] 主题={theme}')
            for e in errs:
                print('  - 静态:', e)
            if mmdc and not rendered:
                print('  - 渲染失败:', render_err)
        else:
            tag = '渲染通过' if mmdc else '静态通过(无 mmdc)'
            print(f'[OK]   主题={theme} ({tag})')
    print(f'\n总计 {total} 个主题, 失败 {fail}')


if __name__ == '__main__':
    main()
