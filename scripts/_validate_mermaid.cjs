// Validate mermaid syntax using the mermaid library
// Usage: node _validate_mermaid.cjs
const fs = require('fs');
const path = require('path');
const os = require('os');

const ROOT = '/Users/sunqingguang/hermes/opt/projects/interview-2026';

// Try to load mermaid from node_modules
let mermaid;
try {
    mermaid = require('mermaid');
} catch (e) {
    console.error('mermaid not installed:', e.message);
    process.exit(2);
}

const cats = ['java-core', 'database', 'scenario'];
const files = [];
for (const cat of cats) {
    const d = path.join(ROOT, 'questions', cat);
    for (const f of fs.readdirSync(d).sort()) {
        if (!f.endsWith('.md')) continue;
        files.push(path.join(d, f));
    }
}

// Extract the FIRST mermaid block we inserted (marked with ## 核心流程图)
function extractOurBlock(content) {
    const m = content.match(/## 核心流程图\n+```mermaid\n([\s\S]*?)\n```/);
    return m ? m[1] : null;
}

(async () => {
    let checked = 0;
    let valid = 0;
    let invalid = 0;
    const errors = [];
    // mermaid 10+ uses async parse
    for (const file of files) {
        const content = fs.readFileSync(file, 'utf-8');
        const block = extractOurBlock(content);
        if (!block) continue;
        checked++;
        try {
            // Try parse via mermaid
            await mermaid.parse(block);
            valid++;
        } catch (e) {
            invalid++;
            errors.push(`${file}: ${e.message.split('\n')[0].slice(0, 200)}`);
        }
    }
    console.log(`Checked: ${checked}`);
    console.log(`Valid: ${valid}`);
    console.log(`Invalid: ${invalid}`);
    if (errors.length) {
        console.log('\nErrors (first 20):');
        for (const e of errors.slice(0, 20)) console.log('  ' + e);
    }
})();
