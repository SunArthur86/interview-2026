// Validate mermaid syntax using ESM import
import mermaid from 'mermaid';
import fs from 'fs';
import path from 'path';
import { pathToFileURL } from 'url';

const ROOT = '/Users/sunqingguang/hermes/opt/projects/interview-2026';

const cats = ['java-core', 'database', 'scenario'];
const files = [];
for (const cat of cats) {
    const d = path.join(ROOT, 'questions', cat);
    for (const f of fs.readdirSync(d).sort()) {
        if (!f.endsWith('.md')) continue;
        files.push(path.join(d, f));
    }
}

function extractOurBlock(content) {
    const m = content.match(/## 核心流程图\n+```mermaid\n([\s\S]*?)\n```/);
    return m ? m[1] : null;
}

// mermaid 11 needs to be initialized before parse
await mermaid.initialize({ startOnLoad: false });

let checked = 0;
let valid = 0;
let invalid = 0;
const errors = [];

for (const file of files) {
    const content = fs.readFileSync(file, 'utf-8');
    const block = extractOurBlock(content);
    if (!block) continue;
    checked++;
    try {
        await mermaid.parse(block);
        valid++;
    } catch (e) {
        invalid++;
        const msg = (e.message || String(e)).split('\n')[0].slice(0, 200);
        errors.push(`${file}: ${msg}`);
    }
}

console.log(`Checked: ${checked}`);
console.log(`Valid: ${valid}`);
console.log(`Invalid: ${invalid}`);
if (errors.length) {
    console.log('\nErrors (first 30):');
    for (const e of errors.slice(0, 30)) console.log('  ' + e);
}
