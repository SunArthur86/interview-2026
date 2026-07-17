#!/usr/bin/env python3
"""
R2+R3: Question cleanup & Answer markdown formatting.
R2: Remove numbering artifacts, fix fragmented/truncated questions, strip noise.
R3: Auto-format answers with markdown (bold key terms, code blocks, lists, headers).
"""
import json
import re
import os
from collections import defaultdict

# ============================================================
# R2: QUESTION CLEANUP
# ============================================================

def clean_question(q):
    """Deep clean question text."""
    q = q.strip()
    
    # Remove leading numbering: "1、", "2.", "3. ", "1) ", "（1）", "第1题"
    q = re.sub(r'^[\d]+[、.．)]\s*', '', q)
    q = re.sub(r'^[（(][\d]+[）)]\s*', '', q)
    q = re.sub(r'^第[一二三四五六七八九十\d]+[题章节条步个种类]\s*[：:]?\s*', '', q)
    
    # Remove prefixes
    for prefix in ['问：', '问:', '答：', '答:', '面试题：', '面试题:', 
                   'Q：', 'Q:', 'Q1：', 'Q2：', 'Q3：', '题目：', '题目:',
                   '请问', '简述', '简答']:
        if q.startswith(prefix):
            q = q[len(prefix):].strip()
    
    # Remove residual numbering after prefix removal
    q = re.sub(r'^[\d]+[、.．)]\s*', '', q)
    
    # Strip leading/trailing punctuation noise
    q = q.strip('：:：?？')
    
    # Remove trailing "？" or "?" and re-add clean
    if q.endswith('？') or q.endswith('?'):
        q = q.rstrip('？?')
    
    # Fix common extraction artifacts
    q = q.replace('|', '')
    q = re.sub(r'\s{2,}', ' ', q)
    
    # Remove HTML entities
    q = re.sub(r'&[a-z]+;', '', q)
    
    return q.strip()

def is_low_quality_question(q_text, a_text):
    """Filter out low-quality entries after cleaning."""
    # Too short after cleanup
    if len(q_text) < 4:
        return True
    # Pure numbers
    if re.match(r'^[\d.、，,\s]+$', q_text):
        return True
    # Code fragments
    code_starts = ['public ', 'private ', 'protected ', 'import ', 'package ',
                   'return ', 'void ', 'static ', 'class ', '@Override', '@Autowired',
                   'if (', 'for (', 'while (', 'try {', 'catch ', 'throw ']
    if any(q_text.startswith(cs) for cs in code_starts):
        return True
    # Fragmented answer starts (these are answer fragments misidentified as questions)
    frag_starts = ['首先', '具体的', '具体方式', '具体来说', '例如', '比如',
                   '1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.']
    if any(q_text.startswith(fs) for fs in frag_starts) and len(q_text) < 20:
        return True
    # Too long (paragraph, not a question)
    if len(q_text) > 150:
        return True
    # Answer too short
    if len(a_text) < 50:
        return True
    # No meaningful content
    chinese = len(re.findall(r'[\u4e00-\u9fff]', q_text))
    alpha = len(re.findall(r'[A-Za-z]', q_text))
    if chinese < 1 and alpha < 3:
        return True
    
    return False

# ============================================================
# R3: ANSWER MARKDOWN FORMATTING
# ============================================================

def format_answer(answer):
    """Transform plain text answer into well-structured markdown."""
    if not answer or len(answer) < 20:
        return answer
    
    lines = answer.split('\n')
    formatted = []
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            formatted.append('')
            continue
        
        # --- Numbered lists ---
        # "1.xxx" or "1、xxx" or "1) xxx" → proper numbered list
        if re.match(r'^[\d]+[、.)]\s*\S', stripped):
            num_match = re.match(r'^([\d]+)[、.)]\s*(.*)', stripped)
            if num_match:
                formatted.append(f"{num_match.group(1)}. {num_match.group(2)}")
                continue
        
        # --- Bullet lists ---
        # "•xxx" or "- xxx" or "* xxx" → markdown bullets
        if re.match(r'^[•●○▪◦\-*]\s*\S', stripped):
            content = re.sub(r'^[•●○▪◦\-*]\s*', '', stripped)
            formatted.append(f"- {content}")
            continue
        
        # --- Section headers ---
        # Short lines (< 30 chars, no ending punctuation) that look like headers
        if len(stripped) < 40 and not stripped.endswith(('。', '.', '：', ':', '，', ',')):
            # Check if it's a known section pattern
            header_patterns = [
                r'^(定义|概念|原理|特点|优势|缺点|区别|比较|分类|类型|步骤|流程|过程|场景|应用|实现|机制|策略|总结|注意|注意点)$',
                r'^(核心|关键|重点|要点|基础|进阶|高级)$',
                r'^(什么是|为什么要|如何)$',
                r'^(适用场景|使用场景|应用场景)$',
                r'^(优点|缺点|优点和缺点|优缺点)$',
                r'^(常见问题|常见错误|注意事项)$',
                r'^(源码|底层|架构|设计)$',
                r'^[A-Z][a-zA-Z\s]{2,30}$',  # English term headers
            ]
            for p in header_patterns:
                if re.match(p, stripped):
                    formatted.append(f"**{stripped}**")
                    continue
        
        # --- Bold key terms ---
        # Common patterns: "XXX：" or "XXX:" → bold the label
        label_match = re.match(r'^([^\s:：]{2,15})[：:]\s*(.*)', stripped)
        if label_match and not stripped.startswith(('http', 'public', 'private', 'import', '//')):
            label = label_match.group(1)
            rest = label_match.group(2)
            # Only bold if it looks like a label (not code)
            if not any(c in label for c in '=;{}()<>|'):
                formatted.append(f"**{label}：** {rest}")
                continue
        
        # --- Inline code detection ---
        # Java class/method names: CamelCase words → inline code
        code_pattern = re.compile(r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b')
        # Only format if it looks like a Java class name (not common English)
        java_terms = {'HashMap', 'ArrayList', 'LinkedList', 'HashSet', 'TreeMap',
                     'ConcurrentHashMap', 'StringBuilder', 'StringBuffer',
                     'ThreadPoolExecutor', 'ReentrantLock', 'ThreadLocal',
                     'AtomicInteger', 'AtomicLong', 'CountDownLatch',
                     'CyclicBarrier', 'Semaphore', 'CompletableFuture',
                     'Future', 'Callable', 'Runnable', 'Thread',
                     'BeanFactory', 'ApplicationContext', 'BeanPostProcessor',
                     'DispatcherServlet', 'RequestMapping',
                     'Integer', 'Boolean', 'Double', 'Float', 'Long',
                     'NullPointerException', 'ClassCastException',
                     'OutOfMemoryError', 'StackOverflowError'}
        
        # Don't over-process — leave lines as-is if they're already complex
        formatted.append(stripped)
    
    result = '\n'.join(formatted)
    
    # Clean up: remove excessive blank lines
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    # Add paragraph breaks: if a line starts with a number followed by text,
    # ensure proper spacing
    
    return result.strip()

# ============================================================
# MAIN
# ============================================================

def process_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    removed = 0
    for q in data:
        # R2: Clean question
        old_q = q['question']
        q['question'] = clean_question(q['question'])
        
        # R3: Format answer
        q['answer'] = format_answer(q['answer'])
    
    # R2: Filter low quality
    original = len(data)
    data = [q for q in data if not is_low_quality_question(q['question'], q['answer'])]
    removed = original - len(data)
    
    # Renumber IDs
    cat = data[0]['category'] if data else 'misc'
    cat_prefix = {
        'java-core': 'core', 'concurrent': 'conc', 'jvm': 'jvm',
        'framework': 'fw', 'database': 'db', 'middleware': 'mw', 'distributed': 'dist',
    }.get(cat, 'misc')
    for i, q in enumerate(data, 1):
        q['id'] = f"{cat_prefix}-{i:03d}"
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return len(data), removed

def main():
    projects = [
        '/opt/data/projects/java-interview/data',
        '/opt/data/projects/ai-interview/data',
    ]
    
    print("=" * 60)
    print("R2+R3: Question Cleanup & Answer Formatting")
    print("=" * 60)
    
    for data_dir in projects:
        proj = os.path.basename(os.path.dirname(data_dir))
        print(f"\n--- {proj} ---")
        total = 0
        total_removed = 0
        for fname in sorted(os.listdir(data_dir)):
            if not fname.endswith('.json'):
                continue
            path = os.path.join(data_dir, fname)
            count, removed = process_file(path)
            total += count
            total_removed += removed
            if removed > 0:
                print(f"  {fname}: {count} kept, {removed} removed")
        print(f"  Total: {total} questions, {total_removed} removed")

if __name__ == '__main__':
    main()
