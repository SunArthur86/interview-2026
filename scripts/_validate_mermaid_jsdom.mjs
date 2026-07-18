// Real mermaid parser validation using jsdom for DOM environment
import { JSDOM } from 'jsdom';
import fs from 'fs';
import path from 'path';

// Set up a DOM
const dom = new JSDOM('<!DOCTYPE html><body></body>', { url: 'http://localhost/' });
globalThis.window = dom.window;
globalThis.document = dom.window.document;
// navigator is read-only on newer Node, but the property exists
try { globalThis.navigator = dom.window.navigator; } catch (e) { /* ignore */ }
// DOMPurify needs these
globalThis.Node = dom.window.Node;
globalThis.Element = dom.window.Element;
globalThis.HTMLElement = dom.window.HTMLElement;

// Now import mermaid
const mermaid = (await import('mermaid')).default;

await mermaid.initialize({
    startOnLoad: false,
    securityLevel: 'loose',
    flowchart: { useMaxWidth: false },
    sequence: { useMaxWidth: false },
});

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

let checked = 0, valid = 0, invalid = 0;
const errors = [];
const detailedErrors = [];
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
        const msg = (e.message || String(e)).split('\n').slice(0, 6).join(' | ').slice(0, 400);
        errors.push(`${file}: ${msg}`);
        detailedErrors.push({ file, block, error: e.message || String(e) });
    }
}

console.log(`Checked: ${checked}`);
console.log(`Valid: ${valid}`);
console.log(`Invalid: ${invalid}`);
if (detailedErrors.length) {
    console.log('\n=== Detailed errors (first 5) ===');
    for (const d of detailedErrors.slice(0, 5)) {
        console.log(`\n--- ${d.file} ---`);
        console.log('Block:');
        console.log(d.block);
        console.log('Error:');
        console.log(d.error);
    }
}

