import { chromium } from 'playwright';
import fs from 'fs';

const results = [];
function check(name, cond, detail = '') {
  results.push({ name, pass: !!cond, detail });
  console.log(`${cond ? '✅' : '❌'} ${name}${detail ? ' — ' + detail : ''}`);
}

console.log('=== R5: PWA + Mobile (java-interview) ===');

const outDir = '/Users/sunqingguang/hermes/opt/projects/java-interview/out';

console.log('\n--- PWA assets ---');
check('manifest.json present', fs.existsSync(outDir + '/manifest.json'));
check('sw.js present', fs.existsSync(outDir + '/sw.js'));
const manifest = JSON.parse(fs.readFileSync(outDir + '/manifest.json', 'utf-8'));
check('manifest has name (Java 面试题库)', manifest.name === 'Java 面试题库');
check('manifest start_url /java-interview/', manifest.start_url === '/java-interview/');
check('manifest theme_color orange', manifest.theme_color === '#f89820');
check('manifest display standalone', manifest.display === 'standalone');
const swContent = fs.readFileSync(outDir + '/sw.js', 'utf-8');
check('sw.js has fetch handler', swContent.includes('fetch'));
check('sw.js BASE /java-interview', swContent.includes("'/java-interview'"));
const homeHtml = fs.readFileSync(outDir + '/index.html', 'utf-8');
check('manifest linked in HTML', homeHtml.includes('manifest.json'));

console.log('\n--- Mobile ---');
const browser = await chromium.launch({
  executablePath: '/Users/sunqingguang/Library/Caches/ms-playwright/chromium-1208/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing',
});
const mobile = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
const mpage = await mobile.newPage();
const merrors = [];
mpage.on('pageerror', (e) => merrors.push(String(e)));

await mpage.goto('http://localhost:8097/java-interview/', { waitUntil: 'networkidle' });
await mpage.waitForTimeout(2500);
const mCards = await mpage.locator('button[aria-label="收藏"]').count();
check('mobile renders cards', mCards > 0, `${mCards} cards`);
const overflow = await mpage.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
check('no horizontal overflow on mobile', overflow <= 2, `overflow=${overflow}px`);

await mpage.evaluate(() => { const c = Array.from(document.querySelectorAll('div')).find(d => d.style.cursor === 'pointer'); c?.click(); });
await mpage.waitForTimeout(1200);
check('mobile modal opens on tap', (await mpage.locator('.markdown-body:visible').count()) > 0);
check('mobile: no page errors', merrors.length === 0, merrors.slice(0, 2).join(' | '));
await mpage.keyboard.press('Escape');
await mpage.waitForTimeout(400);

console.log('\n--- Deep link ---');
await mpage.goto('http://localhost:8097/java-interview/#q=jvm-003', { waitUntil: 'networkidle' });
await mpage.waitForTimeout(2500);
check('deep link #q=id opens modal', (await mpage.locator('.markdown-body:visible').count()) > 0);
await mpage.keyboard.press('Escape');
await mpage.waitForTimeout(400);

console.log('\n--- Shortcuts ---');
await mpage.goto('http://localhost:8097/java-interview/', { waitUntil: 'networkidle' });
await mpage.waitForTimeout(1500);
await mpage.keyboard.press('?');
await mpage.waitForTimeout(500);
check('shortcuts panel opens on ?', (await mpage.locator('text=快捷键').count()) > 0);
const scText = await mpage.evaluate(() => document.body.innerText);
check('shortcuts lists L (random)', scText.includes('随机一题'));
check('shortcuts lists 1-7 (category)', scText.includes('1-7'));
await mpage.keyboard.press('Escape');
await mpage.waitForTimeout(400);

console.log('\n--- SW fetchable ---');
const swRes = await mpage.evaluate(async () => { try { return (await fetch('/java-interview/sw.js')).status; } catch { return 0; } });
check('sw.js is fetchable', swRes === 200, `status=${swRes}`);

await browser.close();
const passed = results.filter((r) => r.pass).length;
const failed = results.filter((r) => !r.pass).length;
console.log(`\n=== R5 Result: ${passed}/${results.length} passed, ${failed} failed ===`);
process.exit(failed > 0 ? 1 : 0);
