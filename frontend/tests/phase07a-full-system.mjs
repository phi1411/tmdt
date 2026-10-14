import puppeteer from 'puppeteer-core';
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../../', import.meta.url));
const base = process.env.E2E_BASE_URL || 'http://127.0.0.1:5174';
const seedPassword = process.env.E2E_SEED_PASSWORD;
assert(seedPassword, 'E2E_SEED_PASSWORD required');
const run = Date.now().toString(36);
const email = `phase07a-${run}@example.test`;
const password = `Fixture-${run}-only-password`;
const report = { checks: [], http: [], failedAssets: [], pageErrors: [], consoleErrors: [], consoleWarnings: [], requestFailures: [], views: [] };
const browser = await puppeteer.launch({ executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  headless: true, args: ['--disable-dev-shm-usage','--disable-background-timer-throttling','--disable-renderer-backgrounding'] });
const expectedFailures = new Set();
const shots = path.join(root, '.local/phase07a-shots');
fs.mkdirSync(shots, { recursive: true });

async function newPage(label) {
  const p = await browser.newPage();
  p.setDefaultTimeout(15000);
  p.setDefaultNavigationTimeout(60000);
  p.pendingApi = new Set();
  p.on('request', r => { if (r.url().includes('/api/v1/')) p.pendingApi.add(r); });
  p.on('requestfinished', r => p.pendingApi.delete(r));
  p.on('requestfailed', r => p.pendingApi.delete(r));
  await p.setViewport({ width: 1440, height: 900 });
  await p.setCacheEnabled(false);
  p.on('pageerror', e => report.pageErrors.push({ page: label, message: e.message }));
  p.on('console', m => {
    if (m.type() === 'error') report.consoleErrors.push({ page: label, message: m.text() });
    if (m.type() === 'warn') report.consoleWarnings.push({ page: label, message: m.text() });
  });
  p.on('requestfailed', req => report.requestFailures.push({ page: label, url: req.url().split('?')[0], error: req.failure()?.errorText }));
  p.on('response', res => {
    if (res.url().includes('/api/v1/')) {
      const u = new URL(res.url());
      report.http.push({ page: label, method: res.request().method(), path: u.pathname, status: res.status() });
    } else if (res.status() >= 400) report.failedAssets.push({ page: label, url: res.url().split('?')[0], status: res.status() });
  });
  return p;
}
async function step(name, fn) {
  try { console.log('RUN '+name); const details = await fn(); report.checks.push({ name, status: 'PASS', details }); console.log('PASS ' + name); }
  catch (e) { report.checks.push({ name, status: 'FAIL', message: e.message }); throw e; }
}
async function go(p, route) {
  await p.bringToFront();
  const res = await p.goto(base + route, { waitUntil: 'domcontentloaded' });
  assert([200,304].includes(res.status()), 'SPA deep-link HTTP status: '+res.status()+' route='+route+' response='+res.url());
  await p.waitForFunction(() => document.querySelector('main') || document.body.textContent.includes('403'), { polling: 'mutation' });
  await p.waitForFunction(() => !document.querySelector('main .animate-pulse, main .animate-spin'), { polling: 'mutation' });
  // Wait for application requests; external lazy images must not stall routing.
  const deadline = Date.now() + 15000;
  while (true) {
    await new Promise(resolve => setTimeout(resolve, 300));
    if (p.pendingApi.size === 0) break;
    assert(Date.now() < deadline, 'API did not settle on ' + route);
  }
}
async function button(p, text, container = null) {
  await p.bringToFront();
  await p.waitForFunction((text, container) => [...(container ? document.querySelector(container) : document).querySelectorAll('button')]
    .some(b => b.textContent.trim() === text && b.getBoundingClientRect().width > 0 && !b.disabled), { polling: 'mutation' }, text, container);
  const h = await p.evaluateHandle((text, container) => [...(container ? document.querySelector(container) : document).querySelectorAll('button')]
    .find(b => b.textContent.trim() === text && b.getBoundingClientRect().width > 0), text, container);
  assert(h.asElement(), 'Missing visible button: ' + text);
  await h.asElement().asLocator().click(); await h.dispose();
}
async function field(p, label, value) {
  await p.bringToFront();
  await p.waitForFunction(label => [...document.querySelectorAll('label')].some(l => l.textContent.trim().replace(/\s*\*$/, '') === label), { polling: 'mutation' }, label);
  const h = await p.evaluateHandle(label => {
    const l = [...document.querySelectorAll('label')].find(l => l.textContent.trim().replace(/\s*\*$/, '') === label);
    return l && (document.getElementById(l.htmlFor) || l.parentElement.querySelector('input,textarea,select'));
  }, label);
  const el = h.asElement(); assert(el, 'Missing field: ' + label);
  const tag = await el.evaluate(e => e.tagName);
  if (tag === 'SELECT') await el.select(String(value));
  else { await el.click({ clickCount: 3 }); await p.keyboard.down('Control'); await el.press('A'); await p.keyboard.up('Control'); await el.type(String(value)); }
  await h.dispose();
}
async function response(p, method, endpoint, action, status = 200) {
  await p.bringToFront();
  const promise = new Promise((resolve, reject) => {
    const timeout = setTimeout(() => { p.off('response', handler); reject(new Error('No HTTP response: '+method+' '+endpoint)); }, 15000);
    function handler(r) {
      if (r.request().method() === method && r.url().split('?')[0].endsWith('/api/v1'+endpoint)) {
        clearTimeout(timeout); p.off('response', handler); resolve(r);
      }
    }
    p.on('response', handler);
  });
  const [res] = await Promise.all([promise, action()]);
  assert.equal(res.status(), status, endpoint);
  if (status === 204) return null;
  const body = await res.json(); assert(body.meta?.requestId);
  assert(!/passwordHash|tokenVersion|checkoutRequestHash|checkoutKey/.test(JSON.stringify(body)));
  return body.data;
}
async function api(p, method, endpoint, payload, status = 200, tokenOverride = undefined) {
  await p.bringToFront();
  if (status >= 400) expectedFailures.add(`${method} /api/v1${endpoint.split('?')[0]} ${status}`);
  const res = await p.evaluate(async (args) => {
    const token = args.tokenOverride === undefined ? sessionStorage.getItem('novamart_auth_token') : args.tokenOverride;
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers.Authorization = 'Bearer ' + token;
    if (args.method === 'POST' && (args.endpoint === '/orders' || args.endpoint.includes('/payment-attempts'))) headers['Idempotency-Key'] = crypto.randomUUID();
    const r = await fetch('/api/v1' + args.endpoint, { method: args.method, headers, ...(args.payload === undefined ? {} : { body: JSON.stringify(args.payload) }) });
    return { status: r.status, body: r.status === 204 ? null : await r.json() };
  }, { method, endpoint, payload, tokenOverride });
  assert.equal(res.status, status, `${method} ${endpoint}`);
  return res.body?.data ?? res.body;
}
async function login(p, account, pw, status = 200) {
  await go(p, '/login');
  await p.type('main input[type=email]', account); await p.type('main input[type=password]', pw);
  if (status >= 400) expectedFailures.add(`POST /api/v1/auth/login ${status}`);
  const loginRes = await response(p, 'POST', '/auth/login', () => p.click('main form button[type=submit]'), status);
  if (status === 200) await p.waitForFunction(() => !location.pathname.includes('/login'));
  return loginRes;
}
async function rowButton(p, text, buttonText) {
  await p.bringToFront();
  await p.waitForFunction((text, buttonText) => [...document.querySelectorAll('tbody tr')].some(tr => tr.textContent.includes(text) && [...tr.querySelectorAll('button')].some(b => b.textContent.trim() === buttonText)), { polling: 'mutation' }, text, buttonText);
  const h = await p.evaluateHandle((text, buttonText) => {
    const tr = [...document.querySelectorAll('tbody tr')].find(t => t.textContent.includes(text));
    return tr && [...tr.querySelectorAll('button')].find(b => b.textContent.trim() === buttonText);
  }, text, buttonText);
  assert(h.asElement(), `Missing row/action: ${text}/${buttonText}`); await h.asElement().asLocator().click(); await h.dispose();
}
const admin = await newPage('ADMIN'), customer = await newPage('CUSTOMER'), guest = await newPage('SECURITY');
let product, category, customerUser, cancelled, completed, adminLogin;
try {
  await step('Development and isolated application health', async () => {
    await go(guest, '/'); const health = await api(guest, 'GET', '/health'); assert.equal(health.checks.replicaSet, 'ok');
  });
  await step('Guest UI/API Admin guard', async () => {
    await go(guest, '/admin/dashboard'); assert(new URL(guest.url()).pathname === '/login');
    await api(guest, 'GET', '/admin/users', undefined, 401, null);
  });
  await step('Admin login through UI', async () => { adminLogin = await login(admin, 'admin@example.test', seedPassword); assert.equal(adminLogin.user.role, 'ADMIN'); });
  await step('Admin Category create/read/edit/delete through UI', async () => {
    await go(admin, '/admin/categories'); await button(admin, 'Thêm ngành hàng');
    await field(admin, 'Tên ngành hàng', `PHASE07A ${run}`); await field(admin, 'Đường dẫn tĩnh (Slug)', `phase07a-${run}`);
    category = await response(admin, 'POST', '/admin/categories', () => button(admin, 'Tạo ngành hàng'), 201);
    await admin.waitForFunction(name => document.querySelector('tbody')?.textContent.includes(name), {}, category.name);
    await rowButton(admin, category.name, 'Sửa'); await field(admin, 'Tên ngành hàng', `PHASE07A edited ${run}`);
    category = await response(admin, 'PATCH', '/admin/categories/' + category.id, () => button(admin, 'Lưu thay đổi'));
    assert(category.name.includes('edited'));
    // An empty category demonstrates physical delete; a separate category owns Product fixtures.
    await admin.waitForFunction(name => document.querySelector('tbody')?.textContent.includes(name), {}, category.name);
    await rowButton(admin, category.name, 'Xóa'); await response(admin, 'DELETE', '/admin/categories/' + category.id, () => button(admin, 'Xác nhận xóa'), 204);
    assert.equal((await api(admin, 'GET', '/admin/categories?pageSize=100')).some(x => x.id === category.id), false);
    await button(admin, 'Thêm ngành hàng'); await field(admin, 'Tên ngành hàng', `PHASE07A products ${run}`);
    await field(admin, 'Đường dẫn tĩnh (Slug)', `phase07a-products-${run}`);
    category = await response(admin, 'POST', '/admin/categories', () => button(admin, 'Tạo ngành hàng'), 201);
  });
  await step('Admin Product create/read through UI', async () => {
    await go(admin, '/admin/products/new'); await field(admin, 'Mã SKU (Duy nhất)', 'PHASE07A_' + run.toUpperCase());
    await field(admin, 'Tên sản phẩm', `PHASE07A Phone ${run}`); await field(admin, 'Đường dẫn tĩnh (Slug)', `phase07a-phone-${run}`);
    await field(admin, 'Danh Mục (Category)', category.id); await field(admin, 'Thương hiệu (Brand)', 'Phase07a');
    await field(admin, 'Giá bán (VND)', 100000); await field(admin, 'Số lượng tồn kho', 12);
    const image = (await api(admin, 'GET', '/products?productType=ELECTRONICS&pageSize=1'))[0].images[0];
    const area = await admin.$$('textarea'); await area[0].type(image); await field(admin, 'Dung lượng RAM', '8GB');
    product = await response(admin, 'POST', '/admin/products', () => admin.click('form button[type=submit]'), 201);
    assert.equal(product.price, 100000); assert.equal(product.stock, 12);
    product = await api(admin, 'PATCH', '/admin/products/' + product.id, { expectedVersion: product.version,
      attributes: { ...product.attributes, battery: '5000mAh', customSpecification: { certified: true, batch: 'Phase07a' } } });
  });
  await step('Customer registration/login through UI', async () => {
    await go(customer, '/register'); await field(customer, 'Họ và tên', 'PHASE07A Customer');
    await field(customer, 'Địa chỉ Email', email); await field(customer, 'Số điện thoại', '0901234567');
    await field(customer, 'Mật khẩu (Tối thiểu 12 ký tự)', password); await field(customer, 'Xác nhận mật khẩu', password);
    const data = await response(customer, 'POST', '/auth/register', () => customer.click('main form button[type=submit]'), 201); customerUser = data.user;
    const dataLogin = await login(customer, email, password); assert.equal(dataLogin.user.id, customerUser.id);
  });
  await step('Customer browse/search/filter Product', async () => {
    await go(customer, '/products'); await customer.type('header input[placeholder*="Tìm"]', `PHASE07A Phone ${run}`);
    await response(customer, 'GET', '/products', () => customer.click('header form button[type=submit]'));
    await customer.type('input[placeholder="Từ"]', '90000');
    await customer.type('input[placeholder="Đến"]', '150000');
    const filtered = await response(customer, 'GET', '/products', () => button(customer, 'Áp dụng giá'));
    assert.equal(filtered.length, 1); assert.equal(filtered[0].id, product.id);
  });
  await step('Polymorphic attributes API and UI for all 3 types', async () => {
    for (const type of ['ELECTRONICS', 'FASHION', 'HOME_APPLIANCE']) {
      const p = type === 'ELECTRONICS' ? product : (await api(customer, 'GET', '/products?productType=' + type + '&pageSize=1'))[0];
      await go(customer, '/products/' + p.slug);
      const body = await customer.$eval('main', n => n.textContent);
      const labels = {ram:'RAM',storage:'Bộ nhớ lưu trữ',chip:'Vi xử lý (Chip)',screen:'Màn hình',battery:'Dung lượng pin',material:'Chất liệu',gender:'Giới tính',power:'Công suất',capacity:'Dung lượng / Thể tích',voltage:'Điện áp',warranty:'Bảo hành'};
      for (const [key, value] of Object.entries(p.attributes)) {
        if (typeof value === 'string') { assert(body.includes(labels[key] || key), 'Attribute label absent: ' + key); assert(body.includes(value), 'Attribute value absent: ' + key); }
        if (Array.isArray(value) && ['sizes','colors'].includes(key)) for (const option of value) assert(body.includes(option));
      }
      report.views.push({ productType: type, attributeKeys: Object.keys(p.attributes) });
    }
  });
  await step('Customer Add Cart then Update Cart through UI', async () => {
    await go(customer, '/products/' + product.slug);
    const cart = await response(customer, 'POST', '/cart/items', () => button(customer, 'Thêm vào giỏ hàng'));
    assert.equal(cart.items[0].quantity, 1); await go(customer, '/cart');
    const updated = await response(customer, 'PATCH', '/cart/items/' + cart.items[0].lineId, () => customer.click('button:has(svg.lucide-plus)'));
    assert.equal(updated.items[0].quantity, 2); assert.equal(updated.subtotal, 200000);
  });
  await step('Customer Address create/select and Checkout quote', async () => {
    await go(customer, '/checkout');
    await button(customer, 'Thêm địa chỉ ngay'); await field(customer, 'Họ và tên người nhận', 'PHASE07A Customer');
    await field(customer, 'Số điện thoại', '0901234567'); await field(customer, 'Địa chỉ cụ thể (Số nhà, tên đường)', '07A Fixture Street');
    await field(customer, 'Tỉnh / Thành phố', 'Ho Chi Minh');
    const quoteResponse = customer.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/checkout/quote' && r.status() === 200);
    await response(customer, 'POST', '/users/me/addresses', () => button(customer, 'Lưu địa chỉ'), 201);
    const quote = (await (await quoteResponse).json()).data;
    assert(quote.quoteToken); assert.equal(quote.subtotal, 200000); assert.equal(quote.total, 230000);
  });
  await step('Disabled VNPAY quote fallback then COD recovery', async () => {
    expectedFailures.add('GET /api/v1/checkout/quote 503');
    await response(customer, 'GET', '/checkout/quote', () => customer.click('div.cursor-pointer:has(span):has(svg.lucide-credit-card)'), 503);
    assert((await customer.$eval('main', n => n.textContent)).includes('VNPAY Sandbox'));
    await response(customer, 'GET', '/checkout/quote', () => customer.click('div.cursor-pointer:has(span):has(svg.lucide-banknote)'));
  });
  await step('Customer COD Order/Success/My Orders/Detail/Cancel', async () => {
    cancelled = (await response(customer, 'POST', '/orders', () => button(customer, 'Xác nhận đặt hàng'), 201)).order;
    await customer.waitForFunction(() => location.pathname === '/order-success');
    assert((await customer.$eval('main', n => n.textContent)).includes(cancelled.orderCode));
    await go(customer, '/orders'); assert((await customer.$eval('main', n => n.textContent)).includes(cancelled.orderCode));
    await go(customer, '/orders/' + cancelled.id); await button(customer, 'Hủy đơn hàng này');
    const result = await response(customer, 'POST', '/orders/' + cancelled.id + '/cancel', () => button(customer, 'Xác nhận hủy'));
    assert.equal(result.orderStatus, 'CANCELLED'); assert(result.stockReleasedAt);
    assert.equal((await api(admin, 'GET', '/admin/products/' + product.id)).stock, 12);
  });
  await step('Create second Order for Admin lifecycle and snapshot', async () => {
    await go(customer, '/products/' + product.slug); await response(customer, 'POST', '/cart/items', () => button(customer, 'Thêm vào giỏ hàng'));
    await go(customer, '/checkout');
    completed = (await response(customer, 'POST', '/orders', () => button(customer, 'Xác nhận đặt hàng'), 201)).order;
    assert.equal(completed.items[0].priceAtPurchase, 100000); assert.equal(completed.items[0].productName, product.name);
  });
  await step('Admin edit name/price preserves flexible live attributes', async () => {
    await go(admin, '/admin/products/' + product.id + '/edit'); await field(admin, 'Tên sản phẩm', `PHASE07A changed ${run}`);
    await field(admin, 'Giá bán (VND)', 120000);
    product = await response(admin, 'PATCH', '/admin/products/' + product.id, () => admin.click('form button[type=submit]'));
    assert.equal(product.price, 120000); assert.equal(product.stock, 11);
    assert.equal(product.attributes.battery, '5000mAh', 'Admin edit silently deleted unexposed attributes');
    assert.deepEqual(product.attributes.customSpecification, { certified: true, batch: 'Phase07a' });
  });
  await step('Order historical snapshot unchanged after Product mutation', async () => {
    const detail = await api(customer, 'GET', '/orders/' + completed.id);
    assert.deepEqual(detail.items, completed.items); assert.equal(detail.total, completed.total);
    await go(customer, '/orders/' + completed.id);
    assert((await customer.$eval('main', n => n.textContent)).includes(completed.items[0].productName));
  });
  await step('Admin confirm/ship/complete through UI', async () => {
    await go(admin, '/admin/orders/' + completed.id);
    const before = await api(admin, 'GET', '/admin/dashboard/summary?from=2026-10-01T00:00:00Z&to=2026-10-31T00:00:00Z');
    for (const [action, label, status] of [['confirm', 'Xác nhận đơn', 'CONFIRMED'], ['ship', 'Chuyển giao hàng', 'SHIPPING'], ['complete', 'Hoàn tất đơn & Thu tiền', 'COMPLETED']]) {
      const d = await response(admin, 'POST', '/admin/orders/' + completed.id + '/' + action, () => button(admin, label));
      assert.equal(d.orderStatus, status); if (action === 'complete') { assert.equal(d.paymentStatus, 'PAID'); assert(d.completedAt); }
    }
    const after = await api(admin, 'GET', '/admin/dashboard/summary?from=2026-10-01T00:00:00Z&to=2026-10-31T00:00:00Z');
    assert.equal(after.totalRevenue - before.totalRevenue, 100000); assert.equal(after.totalProductsSold - before.totalProductsSold, 1);
    report.revenueOracle = { delta: 100000, excludedShipping: 30000 };
  });
  await step('Admin Dashboard/Summary/Revenue/Top5/Category/Status UI', async () => {
    const started = report.http.length; await go(admin, '/admin/dashboard');
    for (const endpoint of ['summary', 'revenue', 'top-products', 'category-revenue', 'order-status'])
      assert(report.http.slice(started).some(r => r.path.endsWith('/dashboard/' + endpoint) && r.status === 200));
    assert(await admin.$('svg.recharts-surface')); assert((await admin.$eval('main', n => n.textContent)).includes('Doanh Thu'));
    const top = await api(admin, 'GET', '/admin/dashboard/top-products?from=2026-07-01T00:00:00Z&to=2026-10-31T00:00:00Z'); assert.equal(top.items.length, 5);
  });
  await step('Customer Admin forbidden; cross-owner Order; invalid JWT', async () => {
    await go(customer, '/admin/dashboard'); assert((await customer.$eval('body', n => n.textContent)).includes('403'));
    await api(customer, 'GET', '/admin/users', undefined, 403);
    const otherOrder = (await api(admin, 'GET', '/admin/orders?pageSize=100')).find(o => o.id !== completed.id && o.id !== cancelled.id);
    await api(customer, 'GET', '/orders/' + otherOrder.id, undefined, 404);
    await api(guest, 'GET', '/auth/me', undefined, 401, 'invalid.jwt.signature');
  });
  await step('Payload tampering rejected', async () => {
    await api(guest, 'POST', '/auth/register', { name: 'Fixture', email: `phase07a-tamper-${run}@example.test`, password, role: 'ADMIN' }, 422, null);
    await api(customer, 'POST', '/cart/items', { productId: product.id, quantity: 1, cartVersion: 4, price: 1 }, 422);
    await api(customer, 'POST', '/orders', { cartVersion: 4, addressId: '0'.repeat(24), paymentMethod: 'COD', quoteToken: 'tamper', total: 1 }, 422);
    await api(admin, 'POST', '/admin/orders/' + completed.id + '/ship', { expectedVersion: 1, paymentStatus: 'PAID' }, 422);
    await api(admin, 'DELETE', '/admin/categories/' + category.id, { expectedVersion: (await api(admin, 'GET', '/admin/categories/' + category.id)).version }, 409);
  });
  await step('Admin User Management block/revoke/unblock through UI', async () => {
    const oldToken = await customer.evaluate(() => sessionStorage.getItem('novamart_auth_token'));
    await go(admin, '/admin/users'); await admin.type('input[placeholder*="Tìm kiếm"]', email);
    await response(admin, 'GET', '/admin/users', () => admin.click('form button[type=submit]'));
    await rowButton(admin, email, 'Khóa');
    const blocked = await response(admin, 'PATCH', '/admin/users/' + customerUser.id + '/status', () => button(admin, 'Xác nhận khóa'));
    assert.equal(blocked.status, 'BLOCKED'); await api(guest, 'GET', '/auth/me', undefined, 401, oldToken);
    await login(guest, email, password, 401);
    await admin.bringToFront();
    await admin.waitForFunction(email => document.querySelector('tbody')?.textContent.includes(email), { polling: 'mutation' }, email);
    await rowButton(admin, email, 'Mở khóa');
    const active = await response(admin, 'PATCH', '/admin/users/' + customerUser.id + '/status', () => button(admin, 'Xác nhận mở khóa'));
    assert.equal(active.status, 'ACTIVE'); await api(guest, 'GET', '/auth/me', undefined, 401, oldToken);
    await login(customer, email, password);
    await api(admin, 'PATCH', '/admin/users/' + adminLogin.user.id + '/status', { expectedVersion: adminLogin.user.version, status: 'BLOCKED' }, 409);
  });
  await step('Product archive UI preserves completed Order; unavailable detail', async () => {
    await go(admin, '/admin/products?q=' + encodeURIComponent('PHASE07A changed'));
    await rowButton(admin, product.name, 'Lưu trữ');
    await response(admin, 'DELETE', '/admin/products/' + product.id, () => button(admin, 'Xác nhận lưu trữ'), 204);
    await api(customer, 'GET', '/products/' + product.slug, undefined, 404);
    assert.deepEqual((await api(customer, 'GET', '/orders/' + completed.id)).items, completed.items);
  });
  await step('VNPAY Return/IPN disabled safely, no live provider claim', async () => {
    expectedFailures.add('GET /api/v1/payments/vnpay/return 503'); await go(guest, '/payment/return?vnp_ResponseCode=00');
    assert(!(await guest.$eval('main', n => n.textContent)).includes('Thanh Toán Thành Công!'));
    const ipn = await api(guest, 'GET', '/payments/vnpay/ipn', undefined, 200, null); assert.equal(ipn.RspCode, '99');
  });
  await step('Deep routes and 404 render correctly', async () => {
    for (const route of ['/', '/products', '/account/profile', '/account/addresses', '/cart', '/orders', '/orders/' + completed.id]) await go(customer, route);
    for (const route of ['/admin/dashboard', '/admin/products', '/admin/categories', '/admin/users', '/admin/orders', '/admin/orders/' + completed.id]) await go(admin, route);
    await go(guest, '/phase07a-route-does-not-exist'); assert((await guest.$eval('main', n => n.textContent)).includes('404'));
  });
  await step('Desktop/Tablet/Mobile layout and image health', async () => {
    for (const [name, width, height] of [['desktop', 1440, 900], ['tablet', 900, 768], ['mobile', 390, 844]]) {
      for (const [p, route, label] of [[customer, '/products', 'catalog'], [customer, '/orders/' + completed.id, 'order'], [admin, '/admin/dashboard', 'dashboard'], [admin, '/admin/products', 'admin-products'], [admin, '/admin/categories', 'admin-categories'], [admin, '/admin/users', 'admin-users'], [admin, '/admin/orders', 'admin-orders']]) {
        await p.setViewport({ width, height }); await go(p, route);
        if (label === 'catalog') {
          // Scroll every card into view so lazy images are actually requested.
          for (const img of await p.$$('main img')) {
            await img.scrollIntoView();
            await p.waitForFunction(i => i.complete && i.naturalWidth > 0, { timeout: 15000 }, img);
          }
          await p.evaluate(() => scrollTo(0, 0));
        }
        await p.waitForFunction(() => [...document.images].filter(i => { const r = i.getBoundingClientRect(); return r.width > 0 && r.top < innerHeight && r.bottom > 0; }).every(i => i.complete), { timeout: 15000 });
        const metrics = await p.evaluate(() => ({ width: innerWidth, scrollWidth: document.documentElement.scrollWidth,
          broken: [...document.images].filter(i => i.complete && i.naturalWidth === 0 && i.src && i.getBoundingClientRect().width > 0).map(i => i.src),
          visibleImages: [...document.images].filter(i => i.getBoundingClientRect().width > 0).length,
          loadedInViewport: [...document.images].filter(i => { const r = i.getBoundingClientRect(); return r.width > 0 && r.top < innerHeight && r.bottom > 0 && i.complete && i.naturalWidth > 0; }).length }));
        report.views.push({ viewport: name, route, ...metrics }); assert(metrics.scrollWidth <= width + 1, 'Root horizontal overflow on ' + route + '/' + name);
        assert.equal(metrics.broken.length, 0, 'Broken images on ' + route + '/' + name);
        if (['desktop', 'mobile'].includes(name) && ['catalog', 'dashboard'].includes(label)) await p.screenshot({ path: path.join(shots, name + '-' + label + '.png'), fullPage: true });
      }
    }
  });
  await step('No unexpected HTTP failures or browser exceptions', async () => {
    report.expectedNegativeResponses = [...expectedFailures];
    report.unexpectedHttp = report.http.filter(r => r.status >= 400 && !expectedFailures.has(`${r.method} ${r.path} ${r.status}`));
    assert.equal(report.unexpectedHttp.length, 0, JSON.stringify(report.unexpectedHttp));
    assert.equal(report.pageErrors.length, 0, JSON.stringify(report.pageErrors));
    report.unexpectedConsoleErrors = report.consoleErrors.filter(e => !e.message.startsWith('Failed to load resource: the server responded with a status of '));
    assert.equal(report.unexpectedConsoleErrors.length, 0, JSON.stringify(report.unexpectedConsoleErrors));
    report.unexpectedRequestFailures = report.requestFailures.filter(e => e.error !== 'net::ERR_ABORTED');
    assert.equal(report.unexpectedRequestFailures.length, 0, JSON.stringify(report.unexpectedRequestFailures));
    assert.equal(report.failedAssets.length, 0, JSON.stringify(report.failedAssets));
  });
  report.status = 'FULL SYSTEM E2E PASS';
} catch (e) {
  report.status = 'FAILED'; report.failure = e.stack;
  console.error(e.message);
  await admin.bringToFront(); await admin.screenshot({ path: path.join(shots, 'failure-admin.png'), fullPage: true }).catch(() => {});
  await customer.bringToFront(); await customer.screenshot({ path: path.join(shots, 'failure-customer.png'), fullPage: true }).catch(() => {});
} finally {
  await browser.close();
  fs.writeFileSync(path.join(root, 'frontend/tests/phase07a-full-system-results.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({ status: report.status, passed: report.checks.filter(c => c.status === 'PASS').length, failed: report.checks.filter(c => c.status === 'FAIL').length, http: report.http.length }));
  process.exitCode = report.status === 'FULL SYSTEM E2E PASS' ? 0 : 1;
}
