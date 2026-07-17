import { chromium } from 'playwright';
import fs from 'fs';

const results = [];
function check(name, cond, detail = '') {
  results.push({ name, pass: !!cond, detail });
  console.log(`${cond ? '✅' : '❌'} ${name}${detail ? ' — ' + detail : ''}`);
}

const browser = await chromium.launch({
  executablePath: '/Users/sunqingguang/Library/Caches/ms-playwright/chromium-1208/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing',
});
const ctx = await browser.newContext({ acceptDownloads: true });
await ctx.grantPermissions(['clipboard-read', 'clipboard-write']);
const page = await ctx.newPage();

console.log('=== R4: Data Compatibility + Exports (java-interview) ===');

await page.goto('http://localhost:8097/java-interview/', { waitUntil: 'networkidle' });
await page.evaluate(() => localStorage.clear());
await page.waitForTimeout(300);

// seed legacy keys
await page.evaluate(() => {
  const P = 'java-interview';
  localStorage.setItem(P + '.favorites', JSON.stringify(['jvm-001', 'jvm-002']));
  localStorage.setItem(P + '.viewed', JSON.stringify(['jvm-001']));
  localStorage.setItem(P + '.notes', JSON.stringify({ 'jvm-001': 'legacy note text' }));
  localStorage.setItem(P + '.ratings', JSON.stringify({ 'jvm-001': 'know' }));
  localStorage.setItem(P + '.theme', JSON.stringify('dark'));
  localStorage.setItem(P + '.sortOrder', JSON.stringify('easy-first'));
  localStorage.setItem(P + '.searchHistory', JSON.stringify(['Spring', 'GC']));
  localStorage.setItem(P + '.streak', JSON.stringify(5));
  localStorage.setItem(P + '.dailyGoal', JSON.stringify(25));
  const t = new Date().toISOString().split('T')[0];
  localStorage.setItem(P + '.reviewData', JSON.stringify({ 'jvm-001': { algo: 'sm2', ease: 2.5, interval: 1, reps: 1, lapses: 0, box: 0, phase: 0, nextDate: t, lastDate: t, createdAt: t, history: [] } }));
  localStorage.setItem(P + '.reviewAlgorithm', JSON.stringify('leitner'));
});

await page.reload({ waitUntil: 'networkidle' });
await page.waitForTimeout(2500);

const migrated = await page.evaluate(() => {
  const raw = localStorage.getItem('java-interview');
  if (!raw) return { merged: false };
  return { merged: true, state: JSON.parse(raw).state };
});
check('legacy keys merged into zustand blob', migrated.merged === true);
check('favorites migrated', migrated.state?.favorites?.length === 2, JSON.stringify(migrated.state?.favorites));
check('notes migrated', migrated.state?.notes?.['jvm-001'] === 'legacy note text');
check('ratings migrated', migrated.state?.ratings?.['jvm-001'] === 'know');
check('theme migrated', migrated.state?.theme === 'dark');
check('searchHistory migrated', JSON.stringify(migrated.state?.searchHistory) === JSON.stringify(['Spring', 'GC']));
check('streak migrated', migrated.state?.streak === 5);
check('reviewAlgorithm migrated', migrated.state?.reviewAlgorithm === 'leitner');
check('reviewData migrated', !!migrated.state?.reviewData?.['jvm-001']);

const appliedTheme = await page.evaluate(() => document.documentElement.getAttribute('data-theme'));
check('migrated dark theme applied to DOM', appliedTheme === 'dark', `theme=${appliedTheme}`);

// exports — inject wrong ratings
await page.evaluate(() => {
  const raw = localStorage.getItem('java-interview');
  const parsed = JSON.parse(raw);
  parsed.state.ratings = { ...(parsed.state.ratings || {}), 'jvm-002': 'dont', 'jvm-003': 'fuzzy' };
  localStorage.setItem('java-interview', JSON.stringify(parsed));
});
await page.reload({ waitUntil: 'networkidle' });
await page.waitForTimeout(2500);

await page.locator('button[title="设置"]').click();
await page.waitForTimeout(500);
check('settings panel opens', (await page.locator('text=导出').count()) > 0);

const downloadPaths = [];
page.on('download', async (d) => { const p = '/tmp/jdl-' + d.suggestedFilename(); await d.saveAs(p); downloadPaths.push(p); });

await page.locator('button:has-text("导出学习进度")').click();
await page.waitForTimeout(1500);
check('export triggered downloads', downloadPaths.length >= 1, `${downloadPaths.length} files`);

let backupOk = false, progressOk = false;
for (const p of downloadPaths) {
  const content = fs.readFileSync(p, 'utf-8');
  if (p.includes('backup')) {
    try { const j = JSON.parse(content); backupOk = JSON.stringify(j.favorites) === JSON.stringify(['jvm-001', 'jvm-002']) && !!j.reviewData?.['jvm-001']; } catch {}
  }
  if (p.includes('study-progress')) progressOk = content.includes('学习进度');
}
if (!progressOk) {
  const clip = await page.evaluate(() => navigator.clipboard.readText().catch(() => ''));
  progressOk = clip.includes('学习进度报告');
}
check('backup JSON contains favorites + reviewData', backupOk);
check('progress report exported', progressOk);

const dlBefore = downloadPaths.length;
await page.locator('button:has-text("导出错题本")').click();
await page.waitForTimeout(1500);
let wbOk = downloadPaths.length > dlBefore;
if (wbOk) {
  const wb = downloadPaths[downloadPaths.length - 1];
  wbOk = fs.readFileSync(wb, 'utf-8').includes('错题本');
}
check('wrong-book export produces correct file', wbOk);

await browser.close();
const passed = results.filter((r) => r.pass).length;
const failed = results.filter((r) => !r.pass).length;
console.log(`\n=== R4 Result: ${passed}/${results.length} passed, ${failed} failed ===`);
process.exit(failed > 0 ? 1 : 0);
