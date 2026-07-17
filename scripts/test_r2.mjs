import { chromium } from 'playwright';

const BASE = 'http://localhost:8097/java-interview';
const results = [];
function check(name, cond, detail = '') {
  results.push({ name, pass: !!cond, detail });
  console.log(`${cond ? '✅' : '❌'} ${name}${detail ? ' — ' + detail : ''}`);
}

const browser = await chromium.launch({
  executablePath: '/Users/sunqingguang/Library/Caches/ms-playwright/chromium-1208/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing',
});
const page = await browser.newPage();
const errors = [];
page.on('pageerror', (e) => errors.push(String(e)));

console.log('=== R2: Core Features (java-interview) ===');

await page.goto(BASE + '/', { waitUntil: 'networkidle' });
await page.waitForTimeout(2500);
const favButtons = await page.locator('button[aria-label="收藏"]').count();
check('home renders question cards', favButtons > 0, `${favButtons} cards`);
check('no page errors on load', errors.length === 0, errors.slice(0, 3).join(' | '));

const title = await page.title();
check('page title set', title.includes('Java 面试题库'), title);

const catTabs = await page.locator('button:has-text("Java 核心")').count();
check('category tabs rendered', catTabs > 0);

await page.locator('button:has-text("Java 核心")').first().click();
await page.waitForTimeout(600);
const favAfterCat = await page.locator('button[aria-label="收藏"]').count();
check('category filter reduces list', favAfterCat > 0 && favAfterCat <= 260, `${favAfterCat} cards`);

await page.fill('#search-input', 'Spring');
await page.waitForTimeout(800);
const searchResults = await page.locator('button[aria-label="收藏"]').count();
check('search returns results', searchResults > 0, `${searchResults} results`);
const highlights = await page.locator('mark.search-hit').count();
check('search highlight marks present', highlights > 0, `${highlights} marks`);

await page.fill('#search-input', '');
await page.waitForTimeout(500);

// open modal
await page.evaluate(() => { const c = Array.from(document.querySelectorAll('div')).find(d => d.style.cursor === 'pointer'); c?.click(); });
await page.waitForTimeout(1200);
check('modal opens with markdown answer', (await page.locator('.markdown-body:visible').count()) > 0);
const modalText = await page.locator('body').innerText();
check('modal shows feynman section', modalText.includes('费曼') || modalText.includes('本质'));
check('modal has copy button', (await page.locator('button:has-text("复制")').count()) > 0);
check('modal has notes textarea', (await page.locator('textarea:visible').count()) > 0);

await page.keyboard.press('Escape');
await page.waitForTimeout(500);

// static detail page (jvm-001)
await page.goto(BASE + '/question/jvm-001/', { waitUntil: 'networkidle' });
await page.waitForTimeout(1500);
check('static detail page renders answer', (await page.locator('.markdown-body').count()) > 0);

// theme toggle
await page.goto(BASE + '/', { waitUntil: 'networkidle' });
await page.waitForTimeout(1500);
const themeBefore = await page.evaluate(() => document.documentElement.getAttribute('data-theme'));
await page.locator('button[title="主题 (D)"]').click();
await page.waitForTimeout(400);
const themeAfter = await page.evaluate(() => document.documentElement.getAttribute('data-theme'));
check('theme toggles', themeBefore !== themeAfter, `${themeBefore} -> ${themeAfter}`);

await browser.close();
const passed = results.filter((r) => r.pass).length;
const failed = results.filter((r) => !r.pass).length;
console.log(`\n=== R2 Result: ${passed}/${results.length} passed, ${failed} failed ===`);
process.exit(failed > 0 ? 1 : 0);
