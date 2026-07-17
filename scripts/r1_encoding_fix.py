#!/usr/bin/env python3
"""
R1: Fix CJK character corruption from PDF extraction.
PDF extraction often produces half-width CJK variants instead of standard characters.
"""
import json
import os
import sys

# Mapping: corrupted → correct (these are CJK Compatibility Ideographs / half-width forms)
CJK_FIX_MAP = {
    '⽅': '方', '⼩': '小', '⽬': '目', '⽐': '比', '⽓': '气',
    '⽔': '水', '⽕': '火', '⽊': '木', '⽉': '月', '⽇': '日',
    '⼤': '大', '⼩': '小', '⼩': '小', '⼭': '山', '⼯': '工',
    '⼈': '人', '⼊': '入', '⼒': '力', '⼥': '女', '⼼': '心',
    '⼿': '手', '⽀': '支', '⽂': '文', '⼆': '二', '⼀': '一',
    '三': '三', '四': '四', '五': '五', '六': '六', '七': '七',
    '八': '八', '九': '九', '十': '十',
    '⽤': '用', '⽥': '田', '⽩': '白', '⽚': '片', '⽛': '牙',
    '⽜': '牛', '⽪': '皮', '⽫': '皿', '⽬': '目', '⽭': '矛',
    '⽮': '矢', '⽯': '石', '⽰': '示', '⽱': '禸', '⽲': '禾',
    '⽳': '穴', '⽴': '立', '⽵': '竹', '⽶': '米', '⽷': '糸',
    '⽸': '缶', '⽹': '网', '⽺': '羊', '⽻': '羽', '⽼': '老',
    '⽽': '而', '⽾': '耒', '⽿': '耳', '⾀': '聿', '⾁': '肉',
    '⾂': '臣', '⾃': '自', '⾄': '至', '⾅': '臼', '⾆': '舌',
    '⾇': '舟', '⾈': '色', '⾉': '艸', '⾊': '虍', '⾋': '虫',
    '⾌': '血', '⾍': '行', '⾎': '衣', '⾏': '行', '⾐': '衣',
    '⾟': '辛', '⾠': '辰', '⾡': '辶', '⾢': '邑', '⾣': '酉',
    '⾤': '采', '⾥': '里', '⾦': '金', '⾧': '長', '⾨': '門',
    '⾩': '阜', '⾪': '隶', '⾫': '隹', '⾬': '雨', '⾭': '靑',
    '⾮': '非', '⾯': '面', '⾰': '革', '⾱': '韋', '⾲': '韭',
    '⾳': '音', '⾴': '頁', '⾵': '風', '⾶': '飛', '⾷': '食',
    '⾸': '首', '⾹': '香', '⾺': '馬', '⾻': '骨', '⾼': '高',
    '⾽': '髟', '⾾': '鬥', '⾿': '鬯', '⿀': '鬲', '⿁': '鬼',
    '⿂': '魚', '⿃': '鳥', '⿄': '鹵', '⿅': '鹿', '⿆': '麥',
    '⿇': '麻', '⿈': '黃', '⿉': '黍', '⿊': '黑', '⿋': '黹',
    '⿌': '黽', '⿍': '鼎', '⿎': '鼓', '⿏': '鼠', '⿐': '鼻',
    '⿑': '齊', '⿒': '齒', '⿓': '龍', '⿔': '龜', '⿕': '龠',
    # Common individual fixes
    '⼩': '小', '⼤': '大', '⼈': '人', '⼀': '一', '⼆': '二',
    '⼒': '力', '⼥': '女', '⼼': '心', '⼿': '手', '⽇': '日',
    '⽉': '月', '⽊': '木', '⽔': '水', '⽕': '火', '⼟': '土',
    '⽥': '田', '⽬': '目', '⽷': '糸', '⾦': '金',
    # Also fix fullwidth → halfwidth for common chars in code
    '（': '(', '）': ')', '，': ',', '。': '.',
    '：': ':', '；': ';', '！': '!', '？': '?',
    '"': '"', '"': '"', ''': "'", ''': "'",
    '【': '[', '】': ']', '《': '<', '》': '>',
    '—': '-', '–': '-', '…': '...',
}

def fix_text(text):
    """Fix CJK corruption in text."""
    if not text:
        return text
    for bad, good in CJK_FIX_MAP.items():
        text = text.replace(bad, good)
    return text

def process_file(path):
    """Fix all text fields in a JSON data file."""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    fixed_count = 0
    for q in data:
        for field in ['question', 'answer', 'tags', 'follow_up']:
            if field in q and isinstance(q[field], str):
                old = q[field]
                q[field] = fix_text(old)
                if q[field] != old:
                    fixed_count += 1
            elif field in q and isinstance(q[field], list):
                q[field] = [fix_text(t) if isinstance(t, str) else t for t in q[field]]
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return len(data), fixed_count

def main():
    projects = [
        ('java-interview', '/opt/data/projects/java-interview/data'),
        ('ai-interview', '/opt/data/projects/ai-interview/data'),
    ]
    
    print("=" * 60)
    print("R1: CJK Encoding Fix")
    print("=" * 60)
    
    for proj_name, data_dir in projects:
        print(f"\n--- {proj_name} ---")
        total_qs = 0
        total_fixed = 0
        for fname in sorted(os.listdir(data_dir)):
            if not fname.endswith('.json'):
                continue
            path = os.path.join(data_dir, fname)
            count, fixed = process_file(path)
            total_qs += count
            total_fixed += fixed
            if fixed > 0:
                print(f"  {fname}: {count} questions, {fixed} fields fixed")
        print(f"  Total: {total_qs} questions, {total_fixed} fields fixed")

if __name__ == '__main__':
    main()
