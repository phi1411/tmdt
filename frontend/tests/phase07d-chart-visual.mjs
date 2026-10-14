// Read-only production UI audit: wait for chart animation before visual evidence.
import puppeteer from 'puppeteer-core';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const base = process.env.E2E_BASE_URL;
assert(base && process.env.E2E_SEED_PASSWORD);
const browser = await puppeteer.launch({ executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe', headless: true, args: ['--disable-background-timer-throttling', '--disable-renderer-backgrounding'] });
const p = await browser.newPage();
await p.bringToFront();
const report = { scope: 'REAL_API_PRODUCTION_DASHBOARD_VISUAL', views: [] };
try {
  await p.goto(base + '/login', { waitUntil: 'domcontentloaded' });
  await p.waitForSelector('main input[type=email]');
  await p.type('main input[type=email]', 'admin@example.test'); await p.type('main input[type=password]', process.env.E2E_SEED_PASSWORD);
  await Promise.all([p.waitForResponse(r => r.url().endsWith('/auth/login')), p.click('main form button[type=submit]')]);
  await p.waitForFunction(() => !location.pathname.includes('/login'));
  for (const [name, width, height] of [['desktop', 1440, 900]]) {
    await p.setViewport({ width, height }); await p.goto(base + '/admin/dashboard', { waitUntil: 'domcontentloaded' });
    await p.waitForSelector('.recharts-pie');
    await p.waitForFunction(() => document.querySelectorAll('.recharts-pie-sector path').length > 0);
    // Recharts default duration is 1500ms; allow the animation to finish before capturing.
    await new Promise(resolve => setTimeout(resolve, 1800));
    const d = await p.evaluate(() => ({ pieSectors: [...document.querySelectorAll('.recharts-pie-sector path')].map(n => n.getAttribute('d')),
      areaPaths: document.querySelectorAll('.recharts-area path').length, bars: document.querySelectorAll('.recharts-bar-rectangle path').length,
      width: innerWidth, scrollWidth: document.documentElement.scrollWidth }));
    assert(d.pieSectors.length >= 3 && d.pieSectors.every(v => v?.length > 20), 'Category pie has no rendered data');
    assert(d.areaPaths > 0 && d.bars > 0); assert(d.scrollWidth <= width + 1);
    report.views.push({ viewport: name, ...d });
    const pie = await p.$('.recharts-wrapper:has(.recharts-pie)');
    await pie.scrollIntoView();
    await p.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    await pie.screenshot({ path: `../database/evidence/phase07d-browser/${name}-category-chart.png` });
    await p.screenshot({ path: `../database/evidence/phase07d-browser/${name}-dashboard-settled.png`, fullPage: true });
  }
  report.status = 'PASS';
} catch (e) { report.status = 'FAIL'; report.error = e.message; }
finally { await browser.close(); fs.writeFileSync('../database/evidence/phase07d-chart-visual.json', JSON.stringify(report, null, 2) + '\n'); console.log(JSON.stringify(report)); process.exitCode = report.status === 'PASS' ? 0 : 1; }
