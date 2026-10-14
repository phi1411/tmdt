// Browser contract fault injection against the production bundle. No provider or DB writes.
import puppeteer from 'puppeteer-core';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const base = process.env.E2E_BASE_URL || 'http://127.0.0.1:5174';
const id = '123456789012345678901234', addressId = '223456789012345678901234';
const user = { id, name: 'Contract Fixture', email: 'fixture@example.test', phone: '0912345678', role: 'CUSTOMER', status: 'ACTIVE', version: 1 };
const address = { id: addressId, receiverName: user.name, phone: user.phone, addressLine: 'Fixture only', province: 'Hà Nội' };
const item = { productId: id, sku: 'FIXTURE', productName: 'Contract fixture', productType: 'ELECTRONICS', categoryName: 'Fixture', priceAtPurchase: 100000, quantity: 1, lineTotal: 100000 };
const order = { id, orderCode: 'FIXTURE07A', userId: id, customerSnapshot: user, shippingAddress: address, items: [item], subtotal: 100000, shippingFee: 30000, discount: 0, total: 130000, currency: 'VND', paymentMethod: 'VNPAY', paymentStatus: 'FAILED', orderStatus: 'PENDING', version: 1, createdAt: new Date().toISOString(), paymentExpiresAt: new Date(Date.now() + 900000).toISOString() };
const quote = { cartVersion: 1, items: [item], subtotal: 100000, shippingFee: 30000, discount: 0, total: 130000, currency: 'VND', quoteToken: 'fixture-only-no-signature', expiresAt: order.paymentExpiresAt, issues: [] };
const browser = await puppeteer.launch({ executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe', headless: true });
const results = { scope: 'DETERMINISTIC_FRONTEND_CONTRACT_ONLY_NOT_LIVE_SANDBOX', checks: [] };
async function button(p, text) {
  const h = await p.evaluateHandle(text => [...document.querySelectorAll('button')].find(b => b.textContent.trim() === text), text);
  assert(h.asElement(), 'Missing button ' + text); await h.asElement().click(); await h.dispose();
}
async function run(name, kind, state = {}) {
  const p = await browser.newPage(); const posts = [];
  await p.evaluateOnNewDocument(() => sessionStorage.setItem('novamart_auth_token', 'fixture-only'));
  await p.setRequestInterception(true);
  p.on('request', async r => {
    const u = new URL(r.url()); if (!u.pathname.startsWith('/api/v1/')) return r.continue();
    const endpoint = u.pathname.slice(7); let data = [];
    if (r.method() === 'POST') {
      posts.push({ endpoint, key: r.headers()['idempotency-key'], body: r.postData() });
      if (kind === 'network' && posts.length === 1) return r.abort('failed');
      if (endpoint === '/orders') data = { order: { ...order, paymentStatus: 'PENDING' }, payment: { method: 'VNPAY', attemptId: id, ...(posts.length === 1 ? { retryRequired: true } : { paymentUrl: base + '/phase07a-provider-placeholder' }) } };
      else data = { attemptId: id, attemptStatus: 'PENDING', orderVersion: 2, expiresAt: order.paymentExpiresAt, ...(posts.length === 1 ? { retryRequired: true } : { paymentUrl: base + '/phase07a-provider-placeholder' }) };
    } else if (endpoint === '/auth/me') data = user;
    else if (endpoint === '/users/me') data = { ...user, addresses: [address], defaultAddressId: addressId };
    else if (endpoint === '/cart') data = { version: 1, items: [], subtotal: 0, issues: [] };
    else if (endpoint === '/checkout/quote') data = quote;
    else if (endpoint === '/orders/' + id) data = { ...order, ...state };
    else if (endpoint === '/payments/vnpay/return') data = { result: 'FAILED', verified: true, confirmed: false, authoritative: false, orderId: id };
    await r.respond({ status: 200, contentType: 'application/json', body: JSON.stringify({ data, meta: { requestId: 'fixture-only' } }) });
  });
  try {
    if (kind === 'initial' || kind === 'network') {
      await p.goto(base + '/checkout', { waitUntil: 'networkidle2' });
      await Promise.all([p.waitForResponse(r => r.url().includes('/checkout/quote') && r.url().includes('VNPAY')), p.click('div.cursor-pointer:has(span):has(svg.lucide-credit-card)')]);
      await p.waitForFunction(() => [...document.querySelectorAll('button')].some(b => b.textContent.trim() === 'Xác nhận đặt hàng' && !b.disabled));
      await button(p, 'Xác nhận đặt hàng');
      if (kind === 'network') {
        await p.waitForFunction(() => document.body.textContent.includes('Lỗi máy chủ khi tạo đơn hàng.'));
        await p.waitForFunction(() => [...document.querySelectorAll('button')].some(b => b.textContent.trim() === 'Xác nhận đặt hàng' && !b.disabled));
        await button(p, 'Xác nhận đặt hàng');
      }
      await p.waitForFunction(() => location.pathname !== '/checkout', { timeout: 6000 });
      assert.equal(posts.length, 2, 'Must replay checkout, not create a new attempt');
      assert(posts.every(r => r.endpoint === '/orders'), 'Initial attempt recovery called competing retry endpoint');
      assert.equal(posts[0].key, posts[1].key, 'Idempotency key changed after uncertain response');
      assert.equal(posts[0].body, posts[1].body, 'Replay body changed');
      assert(new URL(p.url()).pathname === '/phase07a-provider-placeholder');
    } else if (kind === 'attempt') {
      await p.goto(base + '/orders/' + id, { waitUntil: 'networkidle2' }); await button(p, 'Thanh toán qua VNPAY');
      await p.waitForFunction(() => [...document.querySelectorAll('button')].some(b => b.textContent.trim() === 'Thanh toán qua VNPAY' && !b.disabled));
      await button(p, 'Thanh toán qua VNPAY');
      await p.waitForFunction(() => location.pathname === '/phase07a-provider-placeholder', { timeout: 6000 });
      assert.equal(posts.length, 2); assert.equal(posts[0].key, posts[1].key, 'Attempt recovery changed key'); assert.equal(posts[0].body, posts[1].body);
    } else {
      await p.goto(base + (kind === 'return-guard' ? '/payment/return' : '/orders/' + id), { waitUntil: 'networkidle2' });
      const labels = await p.$$eval('button', bs => bs.map(b => b.textContent.trim()));
      assert(!labels.includes(kind === 'return-guard' ? 'Thử lại thanh toán' : 'Thanh toán qua VNPAY'), 'Retry displayed for ineligible payment state');
    }
    results.checks.push({ name, status: 'PASS', requests: posts.length, sameKeyBody: posts.length === 2 ? posts[0].key === posts[1].key && posts[0].body === posts[1].body : undefined });
  } catch (e) { results.checks.push({ name, status: 'FAIL', error: e.message }); }
  finally { await p.close(); }
}
try {
  await run('Initial URL fault replays exact checkout', 'initial');
  await run('Lost checkout response retains key/body', 'network');
  await run('Retry attempt URL fault retains key/body', 'attempt');
  await run('Pending initial attempt does not show new retry', 'order-guard', { paymentStatus: 'PENDING' });
  await run('Return rejects review-required retry', 'return-guard', { paymentReviewRequired: true });
  await run('Return rejects COD retry', 'return-guard', { paymentMethod: 'COD' });
} finally {
  await browser.close(); fs.writeFileSync('tests/phase07a-payment-contract-results.json', JSON.stringify(results, null, 2) + '\n');
  console.log(JSON.stringify(results)); process.exitCode = results.checks.every(c => c.status === 'PASS') ? 0 : 1;
}
