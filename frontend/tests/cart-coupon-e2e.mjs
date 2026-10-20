import puppeteer from 'puppeteer-core';
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../../', import.meta.url));
const session = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const base = 'http://127.0.0.1:5175';
const report = { checks: [], http: [], pageErrors: [], views: [] };
const shots = path.join(root, '.local/coupon-browser');
fs.mkdirSync(shots, { recursive: true });
const browser = await puppeteer.launch({ executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  headless: true, args: ['--disable-dev-shm-usage'] });
const page = await browser.newPage();
page.setDefaultTimeout(15000);
page.on('pageerror', e => report.pageErrors.push(e.message));
page.on('response', r => {
  if (r.url().includes('/api/v1/')) report.http.push({ method: r.request().method(), path: new URL(r.url()).pathname, status: r.status() });
});
await page.evaluateOnNewDocument(token => sessionStorage.setItem('novamart_auth_token', token), session.token);
const money = (label, scope = 'aside') => page.evaluate(({label, scope}) => {
  const span = [...document.querySelectorAll(scope + ' span')].find(e => e.textContent.trim().startsWith(label));
  return Number(span?.nextElementSibling?.textContent.replace(/\D/g, ''));
}, {label, scope});
const clickButton = async text => {
  await page.waitForFunction(text => [...document.querySelectorAll('button')]
    .some(b => b.textContent.trim() === text && !b.disabled), {}, text);
  const handle = await page.evaluateHandle(text => [...document.querySelectorAll('button')].find(b => b.textContent.trim() === text), text);
  assert(handle.asElement(), `Missing button ${text}`);
  await handle.asElement().evaluate(b => b.scrollIntoView({block: 'center'}));
  await page.waitForFunction(b => {
    const r = b.getBoundingClientRect();
    return b.contains(document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2));
  }, {}, handle);
  await handle.asElement().click();
};
const mutate = async (action, route = '/cart/coupon', status = 200) => {
  const [response] = await Promise.all([page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1' + route && r.request().method() === 'PATCH'), action()]);
  assert.equal(response.status(), status);
  return (await response.json()).data;
};
const code = async value => {
  await page.waitForFunction(() => !document.querySelector('#cart-coupon')?.disabled);
  await page.focus('#cart-coupon');
  await page.keyboard.down('Control'); await page.keyboard.press('KeyA'); await page.keyboard.up('Control');
  await page.keyboard.press('Backspace');
  if (value) await page.type('#cart-coupon', value);
};
const step = async (name, fn) => { await fn(); report.checks.push({ name, status: 'PASS' }); console.log('PASS ' + name); };
try {
  for (let i = 0; i < 40; i++) {
    try { if ((await fetch(base)).ok) break; } catch {}
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  await page.setViewport({ width: 1440, height: 1000 });
  await page.goto(base + '/cart', { waitUntil: 'networkidle0' });
  await page.waitForSelector('#cart-coupon');
  await step('Reject invalid coupon without changing totals', async () => {
    assert.equal(await money('Tạm tính hàng hóa:'), 500000);
    await code('INVALID'); await mutate(() => clickButton('Áp dụng'), '/cart/coupon', 422);
    assert.equal(await money('Giảm giá:'), 0);
  });
  await step('Apply capped campaign at Cart', async () => {
    await code('nova25'); await mutate(() => clickButton('Áp dụng'));
    await page.waitForFunction(() => document.querySelector('aside')?.textContent.includes('Đã chọn NOVA25'));
    assert.equal(await money('Giảm giá:'), 50000);
    assert.equal(await page.$eval('aside .text-2xl', e => Number(e.textContent.replace(/\D/g, ''))), 450000);
  });
  await step('Desktop and mobile Cart have no horizontal overflow', async () => {
    for (const [name, width, height] of [['desktop', 1440, 1000], ['mobile', 375, 812]]) {
      await page.setViewport({ width, height });
      await page.waitForFunction(() => !document.querySelector('.fixed.bottom-4.right-4')?.children.length);
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), name);
      await page.screenshot({ path: path.join(shots, name + '.png'), fullPage: true });
      report.views.push({ name, width, height, overflow: false });
    }
  });
  await step('Quantity below threshold blocks checkout; remove coupon restores eligibility', async () => {
    const item = (await page.$$('button:has(svg.lucide-minus)'))[0];
    assert(item);
    const [response] = await Promise.all([page.waitForResponse(r => r.url().includes('/cart/items/') && r.request().method() === 'PATCH'), item.click()]);
    assert.equal(response.status(), 200);
    report.lastAction = 'quantity updated below threshold';
    await page.waitForSelector('[role="alert"]');
    assert.equal(await money('Giảm giá:'), 0);
    const blocked = await page.evaluate(() => [...document.querySelectorAll('aside button')].some(b => b.disabled && b.textContent.includes('Vui lòng xử lý')));
    assert(blocked);
    report.lastAction = 'removing coupon';
    await mutate(() => clickButton('Bỏ mã'));
    report.lastAction = 'coupon removed';
    await page.waitForFunction(() => !document.querySelector('[role="alert"]'));
    const plus = (await page.$$('button:has(svg.lucide-plus)'))[0];
    const [increased] = await Promise.all([page.waitForResponse(r => r.url().includes('/cart/items/') && r.request().method() === 'PATCH'), plus.click()]);
    assert.equal(increased.status(), 200);
    await code('NOVA25'); await mutate(() => clickButton('Áp dụng'));
  });
  await step('Reload retains server-owned coupon', async () => {
    await page.reload({ waitUntil: 'networkidle0' });
    assert.equal(await money('Giảm giá:'), 50000);
    assert.equal(await page.$eval('#cart-coupon', e => e.value), 'NOVA25');
  });
  await step('Checkout COD/VNPAY show the same net total; no payment coupon input', async () => {
    const [quote] = await Promise.all([page.waitForResponse(r => r.url().includes('/checkout/quote') && r.status() === 200), clickButton('Tiến hành đặt hàng')]);
    assert.equal((await quote.json()).data.total, 480000);
    await page.waitForFunction(() => document.querySelector('aside')?.textContent.includes('NOVA25'));
    assert.equal(await money('Giảm giá'), 50000);
    assert.equal(await page.$('#cart-coupon'), null);
    const [online] = await Promise.all([page.waitForResponse(r => r.url().includes('/checkout/quote') && r.url().includes('VNPAY')),
      page.evaluate(() => [...document.querySelectorAll('span')].find(e => e.textContent === 'Cổng Thanh Toán VNPAY (QR / ATM / Visa)').click())]);
    assert.equal(online.status(), 200); assert.equal((await online.json()).data.total, 480000);
    const [cod] = await Promise.all([page.waitForResponse(r => r.url().includes('/checkout/quote') && r.url().includes('COD')),
      page.evaluate(() => [...document.querySelectorAll('span')].find(e => e.textContent === 'Thanh toán khi nhận hàng (COD)').click())]);
    assert.equal((await cod.json()).data.total, 480000);
    await page.setViewport({ width: 1440, height: 1000 });
    await page.screenshot({ path: path.join(shots, 'checkout.png'), fullPage: true });
  });
  let order;
  await step('Place real discounted COD Order and display immutable discount in detail', async () => {
    const [created] = await Promise.all([page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/orders' && r.request().method() === 'POST'), clickButton('Xác nhận đặt hàng')]);
    assert.equal(created.status(), 201);
    order = (await created.json()).data.order;
    assert.equal(order.total, 480000); assert.equal(order.discount, 50000);
    await page.waitForFunction(() => location.pathname === '/order-success');
    await page.goto(base + '/orders/' + order.id, { waitUntil: 'networkidle0' });
    assert.equal(await money('Giảm giá:', 'main'), 50000);
    await page.screenshot({ path: path.join(shots, 'order-detail.png'), fullPage: true });
  });
  await step('No browser exceptions or unexpected API failures', async () => {
    assert.equal(report.pageErrors.length, 0, JSON.stringify(report.pageErrors));
    assert.equal(report.http.filter(r => r.status >= 400 && !(r.method === 'PATCH' && r.path === '/api/v1/cart/coupon' && r.status === 422)).length, 0);
  });
  report.status = 'PASS';
} catch (e) {
  report.status = 'FAIL'; report.failure = e.stack;
  await page.screenshot({ path: path.join(shots, 'failure.png'), fullPage: true }).catch(() => {});
  console.error(e.message);
} finally {
  await browser.close();
  fs.writeFileSync(path.join(root, 'backend/evidence/cart-coupon-browser.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({ status: report.status, checks: report.checks.length, http: report.http.length }));
  process.exitCode = report.status === 'PASS' ? 0 : 1;
}
