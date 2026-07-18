// Collect errors with offending line text
import { JSDOM } from 'jsdom';
import fs from 'fs';
import path from 'path';

const dom = new JSDOM('<!DOCTYPE html><body></body>', { url: 'http://localhost/' });
globalThis.window = dom.window;
globalThis.document = dom.window.document;
try { globalThis.navigator = dom.window.navigator; } catch (e) {}
globalThis.Node = dom.window.Node;
globalThis.Element = dom.window.Element;

const mermaid = (await import('mermaid')).default;
await mermaid.initialize({ startOnLoad: false, securityLevel: 'loose' });

const ROOT = '/Users/sunqingguang/hermes/opt/projects/interview-2026';
const cats = ['java-core', 'database', 'scenario'];
const errors = [];
for (const cat of cats) {
    const d = path.join(ROOT, 'questions', cat);
    for (const f of fs.readdirSync(d).sort()) {
        if (!f.endsWith('.md')) continue;
        const file = path.join(d, f);
        const content = fs.readFileSync(file, 'utf-8');
        const m = content.match(/## 核心流程图\n+```mermaid\n([\s\S]*?)\n```/);
        if (!m) continue;
        try {
            await mermaid.parse(m[1]);
        } catch (e) {
            const lines = (e.message || '').split('\n');
            const ln = (lines[0].match(/line (\d+)/) || [])[1] || '?';
            const blockLines = m[1].split('\n');
            const offender = blockLines[parseInt(ln) - 1] || '';
            errors.push({ file: path.basename(file), ln, offender: offender.trim() });
        }
    }
}

fs.writeFileSync('/tmp/errors.json', JSON.stringify(errors, null, 2));
console.log(`Errors: ${errors.length}`);
for (const e of errors.slice(0, 60)) {
    console.log(`${e.file}:${e.ln}  ${e.offender.slice(0, 110)}`);
}
