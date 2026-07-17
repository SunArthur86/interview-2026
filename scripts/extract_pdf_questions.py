#!/usr/bin/env python3
# coding: utf-8
"""
从带书签的 PDF 提取面试题目，输出统一的 JSON（供后续去重合并）。
策略：用 PDF 书签(TOC) 作为题目边界；每个一级/二级书签 = 一道题，
正文为该书签起始页到下一个书签页之间的文本。
用法: extract_pdf_questions.py <pdf_path> <output.json> [--min-len 80] [--max-level 2]
"""
import sys, os, re, json, argparse
import fitz  # pymupdf


def clean_text(t):
    """清理 PDF 提取的文本：去零宽字符、合并断行、规整空白。"""
    # 去零宽/不可见字符
    t = re.sub(r'[\u200b\u200c\u200d\ufeff\u00ad]', '', t)
    # 去行尾连字符断词 (e.g. "mod-\nel" -> "model")
    t = re.sub(r'-\n', '', t)
    # 页码脚注（单独一行的纯数字）
    t = re.sub(r'\n\s*\d{1,3}\s*\n', '\n', t)
    # 多余空行
    t = re.sub(r'\n{3,}', '\n\n', t)
    # 行首项目符号规整
    t = re.sub(r'\n[•·▪►]\s*', '\n- ', t)
    return t.strip()


def normalize_title(title):
    """规整书签标题为题目标题。"""
    t = title.strip()
    # 去前导编号 "1." "1.2" "第一章 1." 等
    t = re.sub(r'^第[一二三四五六七八九十百零\d]+[章节课讲部分]?\s*', '', t)
    t = re.sub(r'^\d+[\.\、]\s*', '', t)
    t = re.sub(r'^\d+\.\d+(\.\d+)*\s*', '', t)
    return t.strip()


def extract(path, out_path, min_len=80, max_level=2):
    doc = fitz.open(path)
    toc = doc.get_toc()  # [[level, title, page], ...] page 1-based
    if not toc:
        print(f'  [警告] {path} 无书签，跳过')
        doc.close()
        return []

    # 只取目标层级及以下、非目录页的书签
    entries = [(lvl, title, page) for lvl, title, page in toc
               if lvl <= max_level and not re.search(r'^目\s*录$|^前\s*言$|^Contents?$|作者|我的|介绍$|友情|添加', title)]
    # 计算每题的文本范围：[page, next_page)
    questions = []
    for i, (lvl, title, page) in enumerate(entries):
        next_page = entries[i + 1][2] if i + 1 < len(entries) else doc.page_count + 1
        start = page - 1  # 0-based
        end = next_page - 1
        if start < 0:
            start = 0
        if end <= start:
            end = start + 1
        if end > doc.page_count:
            end = doc.page_count
        text = ''
        for p in range(start, end):
            text += doc[p].get_text() + '\n'
        text = clean_text(text)
        # 去掉正文开头的重复标题行
        norm = normalize_title(title)
        lines = text.split('\n')
        # 若首行与标题相似，去掉首行
        if lines and (norm[:12] in lines[0] or lines[0][:12] in norm):
            lines = lines[1:]
            text = '\n'.join(lines).strip()
        if len(text) < min_len:
            continue
        questions.append({
            'question': norm,
            'answer': text,
            'source_page': page,
            'level': lvl,
        })
    doc.close()

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    print(f'  提取 {len(questions)} 题 -> {out_path}')
    return questions


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('pdf')
    ap.add_argument('output')
    ap.add_argument('--min-len', type=int, default=80)
    ap.add_argument('--max-level', type=int, default=2)
    args = ap.parse_args()
    extract(args.pdf, args.output, args.min_len, args.max_level)
