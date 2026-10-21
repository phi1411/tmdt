import puppeteer from 'puppeteer-core';
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../../', import.meta.url));
const session = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const base = 'http://127.0.0.1:5175';
const report = { checks: [], http: [], pageErrors: [] };
const shots = path.join(root, '.local/variant-pricing');
fs.mkdirSync(shots, { recursive: true });
const browser = await puppeteer.launch({ executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe', headless: true,
  args:['--disable-background-timer-throttling','--disable-renderer-backgrounding'] });
const newPage = async token => {
  const page = await browser.newPage();
  page.setDefaultTimeout(15000);
  await page.setViewport({ width: 1440, height: 1000 });
  await page.evaluateOnNewDocument(token => sessionStorage.setItem('novamart_auth_token', token), token);
  page.on('pageerror', e => report.pageErrors.push(e.message));
  page.on('response', r => { if (r.url().includes('/api/v1/')) report.http.push({ method: r.request().method(), path: new URL(r.url()).pathname, status: r.status() }); });
  return page;
};
const admin = await newPage(session.adminToken);
const customer = await newPage(session.token);
const labelInput = async (page, label) => {
  const handle = await page.evaluateHandle(label => {
    const el = [...document.querySelectorAll('label')].find(l => l.textContent.trim().startsWith(label));
    return el?.htmlFor ? document.getElementById(el.htmlFor) : null;
  }, label);
  assert(handle.asElement(), 'Missing input ' + label);
  return handle.asElement();
};
const fill = async (page, input, value) => {
  await page.bringToFront();
  await input.focus();
  await page.keyboard.down('Control'); await page.keyboard.press('KeyA'); await page.keyboard.up('Control');
  await page.keyboard.press('Backspace'); await input.type(String(value)); await page.keyboard.press('Tab');
};
const fillLabel = async (page, label, value) => fill(page, await labelInput(page, label), value);
const fillAria = async (page, label, value) => fill(page, await page.$(`[aria-label="${label}"]`), value);
const click = async (page, text, scope = 'body') => {
  await page.bringToFront();
  await page.waitForFunction(({text, scope}) => [...document.querySelector(scope).querySelectorAll('button')].some(b => b.textContent.trim() === text && !b.disabled), {}, {text, scope});
  const handle = await page.evaluateHandle(({text, scope}) => [...document.querySelector(scope).querySelectorAll('button')].find(b => b.textContent.trim() === text), {text, scope});
  await handle.asElement().evaluate(b => b.scrollIntoView({ block: 'center' }));
  await page.waitForFunction(b => { const r = b.getBoundingClientRect(); return b.contains(document.elementFromPoint(r.x+r.width/2, r.y+r.height/2)); }, {}, handle);
  await handle.asElement().click();
};
const selectLabel = async (page, label, value) => {
  const handle = await page.evaluateHandle(label => [...document.querySelectorAll('label')].find(l => l.textContent.trim().startsWith(label))?.parentElement.querySelector('select'), label);
  assert(handle.asElement(), 'Missing select ' + label);
  await handle.asElement().select(value);
};
const waitApi = (page, method, pathname) => page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1' + pathname && r.request().method() === method);
const step = async (name, fn) => { console.log('RUN ' + name); await fn(); report.checks.push({ name, status: 'PASS' }); console.log('PASS ' + name); };
try {
  for (let i=0;i<40;i++) { try { if ((await fetch(base)).ok) break; } catch {} await new Promise(r=>setTimeout(r,250)); }
  let product, order;
  await step('Admin creates Product with separate prices and stock for M/XL through form', async () => {
    await admin.bringToFront();
    await admin.goto(base + '/admin/products/new', { waitUntil: 'networkidle0' });
    await fillLabel(admin, 'Mã SKU', 'UI-VAR-' + Date.now());
    await selectLabel(admin, 'Loại Sản Phẩm', 'FASHION');
    await selectLabel(admin, 'Danh Mục', session.categoryId);
    await fillLabel(admin, 'Tên sản phẩm', 'Áo kiểm thử phân loại ' + Date.now());
    await fillLabel(admin, 'Giá bán (VND)', 100000);
    await click(admin, 'Thêm nhóm phân loại');
    await fillLabel(admin, 'Tên phân loại 1', 'Kích cỡ');
    await fillLabel(admin, 'Các lựa chọn 1', 'M, XL');
    await click(admin, 'Cập nhật bảng phân loại');
    await fillAria(admin, 'Giá M', 100000); await fillAria(admin, 'Kho M', 5);
    await fillAria(admin, 'Giá XL', 120000); await fillAria(admin, 'Kho XL', 7);
    console.log('Admin matrix filled');
    const commonPrice = await labelInput(admin, 'Giá thấp nhất (VND)');
    assert(await commonPrice.evaluate(e => e.disabled && e.value === '100000'));
    assert(await (await labelInput(admin, 'Số lượng tồn kho')).evaluate(e => e.disabled && e.value === '12'));
    await admin.screenshot({ path: path.join(shots, 'admin-create.png'), fullPage: true });
    const [response] = await Promise.all([waitApi(admin, 'POST', '/admin/products'), click(admin, 'Tạo sản phẩm mới')]);
    assert.equal(response.status(), 201, await response.text());
    product = (await response.json()).data; report.productId = product.id;
    assert.deepEqual(product.skus.map(s => s.price), [100000, 120000]);
    assert.equal(product.price, 100000); assert.equal(product.stock, 12);
  });
  await step('Customer sees starting price then exact selected SKU price', async () => {
    await customer.bringToFront();
    await customer.goto(base + '/products/' + product.slug, { waitUntil: 'networkidle0' });
    assert(await customer.evaluate(() => document.body.textContent.includes('Từ 100.000')));
    await click(customer, 'Thêm Vào Giỏ Hàng');
    assert(await customer.$eval('[role="dialog"] [aria-live="polite"]', e => e.textContent.startsWith('Từ ')));
    assert(await customer.$eval('[role="dialog"] button[type="submit"]', e => e.disabled));
    for (const [name, price] of [['M',100000],['XL',120000]]) {
      await click(customer, name, '[role="dialog"]');
      const text = await customer.$eval('[role="dialog"] [aria-live="polite"]', e => e.textContent);
      assert(!text.startsWith('Từ ')); assert.equal(Number(text.replace(/\D/g,'')), price);
    }
    await customer.setViewport({width:375,height:812});
    assert(await customer.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await customer.screenshot({ path: path.join(shots, 'selected-xl-mobile.png'), fullPage: true });
    await click(customer, 'M', '[role="dialog"]');
    const [response] = await Promise.all([waitApi(customer, 'POST', '/cart/items'), click(customer, 'Xác nhận thêm vào giỏ', '[role="dialog"]')]);
    assert.equal(response.status(), 200);
    await customer.waitForFunction(() => !document.querySelector('[role="dialog"]'));
    await click(customer, 'Thêm Vào Giỏ Hàng');
    await click(customer, 'XL', '[role="dialog"]');
    const [second] = await Promise.all([waitApi(customer, 'POST', '/cart/items'), click(customer, 'Xác nhận thêm vào giỏ', '[role="dialog"]')]);
    const cart = (await second.json()).data;
    assert.deepEqual(cart.items.map(i=>i.currentPrice), [100000, 120000]);
    assert.equal(cart.subtotal, 220000);
    await customer.waitForFunction(() => !document.querySelector('[role="dialog"]'));
  });
  await step('Cart and signed quote preserve each selected SKU price', async () => {
    await customer.goto(base + '/cart', { waitUntil: 'networkidle0' });
    const [response] = await Promise.all([customer.waitForResponse(r=>r.url().includes('/checkout/quote') && r.status()===200), click(customer, 'Tiến hành đặt hàng')]);
    const quote = (await response.json()).data;
    assert.deepEqual(quote.items.map(i=>i.priceAtPurchase), [100000,120000]);
    assert.equal(quote.subtotal, 220000); assert.equal(quote.total, 250000);
    const [created] = await Promise.all([waitApi(customer, 'POST', '/orders'), click(customer, 'Xác nhận đặt hàng')]);
    assert.equal(created.status(), 201);
    order = (await created.json()).data.order; report.orderId = order.id;
    assert.deepEqual(order.items.map(i=>i.priceAtPurchase), [100000,120000]);
  });
  await step('Admin edits each SKU price while historical Order keeps original values', async () => {
    await admin.bringToFront();
    await admin.goto(base + `/admin/products/${product.id}/edit`, {waitUntil:'networkidle0'});
    await fillAria(admin, 'Giá M', 110000); await fillAria(admin, 'Giá XL', 150000);
    const [updated] = await Promise.all([waitApi(admin, 'PATCH', '/admin/products/'+product.id), click(admin,'Lưu thay đổi sản phẩm')]);
    assert.equal(updated.status(),200,await updated.text());
    assert.deepEqual((await updated.json()).data.skus.map(s=>s.price),[110000,150000]);
    await customer.bringToFront();
    const [history] = await Promise.all([waitApi(customer,'GET','/orders/'+order.id), customer.goto(base+'/orders/'+order.id,{waitUntil:'networkidle0'})]);
    const saved = (await history.json()).data;
    assert.deepEqual(saved.items.map(i=>i.priceAtPurchase),[100000,120000]);
    assert.equal(saved.total,250000);
    assert.deepEqual(saved.items.map(i=>i.selectedAttributes['Kích cỡ']),['M','XL']);
    await customer.screenshot({path:path.join(shots,'historical-order.png'),fullPage:true});
  });
  await step('No unexpected API failures or browser exceptions',async()=>{
    assert.equal(report.pageErrors.length,0,JSON.stringify(report.pageErrors));
    assert.equal(report.http.filter(r=>r.status>=400).length,0,JSON.stringify(report.http));
  });
  report.status='PASS';
} catch(e) {
  report.status='FAIL';report.failure=e.stack;console.error(e.message);
  await admin.screenshot({path:path.join(shots,'failure-admin.png'),fullPage:true}).catch(()=>{});
  await customer.screenshot({path:path.join(shots,'failure-customer.png'),fullPage:true}).catch(()=>{});
} finally {
  await browser.close();
  fs.writeFileSync(path.join(root,'backend/evidence/variant-pricing-browser.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({status:report.status,checks:report.checks.length,http:report.http.length}));
  process.exitCode=report.status==='PASS'?0:1;
}
