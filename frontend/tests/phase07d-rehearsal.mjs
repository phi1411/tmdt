// Same production bundle, isolated Flask/MongoDB clone; credentials stay private.
import puppeteer from 'puppeteer-core';
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../../', import.meta.url));
const fixture = JSON.parse(fs.readFileSync(path.join(root, '.local/phase07c/fixture.json'), 'utf8'));
const seedPassword = process.env.E2E_SEED_PASSWORD;
assert(seedPassword, 'Private demo password must be supplied by the local runner');
const base = 'http://127.0.0.1:5174';
const out = path.join(root, 'database/evidence/phase07d-browser');
fs.mkdirSync(out, { recursive: true });
const priorPath=path.join(root,'database/evidence/phase07d-browser-attempt2.json');
const prior = fs.existsSync(priorPath)?JSON.parse(fs.readFileSync(priorPath,'utf8')):null;
const report = { phase:'07D', recordedAtUtc:new Date().toISOString(), database:'ecommerce_test',
  app:'current production bundle/same Flask source', checks:[], http:[], screenshots:[], pageErrors:[],
  timingsAreAutomationOnly:true, human5MinuteTiming:'MANUAL_PENDING', human10MinuteTiming:'MANUAL_PENDING',
  offline:{mode:'DENY_NON_LOOPBACK_HTTP_HTTPS_IN_BROWSER_COLD_CACHE', blocked:[], localRequests:0,
    hostNetworkDisconnected:false, backendNetworkBlocked:false} };
const browser = await puppeteer.launch({executablePath:'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  headless:true, args:['--disable-dev-shm-usage','--disable-background-timer-throttling','--disable-renderer-backgrounding']});
let offline = false;
let priceGateRecorded = false;
async function page(label) {
  const p = await browser.newPage(); p.setDefaultTimeout(15000); p.setDefaultNavigationTimeout(30000);
  await p.setViewport({width:1440,height:900}); await p.setCacheEnabled(false);
  await p.setRequestInterception(true);
  p.on('request', req => {
    const u = new URL(req.url());
    if (offline && ['http:','https:'].includes(u.protocol) && !['127.0.0.1','localhost','[::1]'].includes(u.hostname)) {
      report.offline.blocked.push({origin:u.origin, resourceType:req.resourceType()}); req.abort('internetdisconnected');
    } else { if (offline && ['http:','https:'].includes(u.protocol)) report.offline.localRequests++; req.continue(); }
  });
  p.on('pageerror', e => report.pageErrors.push({page:label, errorType:e.name}));
  p.on('response', r => { const u = new URL(r.url()); if (u.pathname.startsWith('/api/v1/')) report.http.push({page:label, method:r.request().method(), path:u.pathname, status:r.status()}); });
  return p;
}
async function step(name, fn) {
  const start = performance.now();
  try { const details = await fn(); report.checks.push({name,status:'PASS',automationSeconds:Math.round((performance.now()-start)/10)/100,details}); console.log('PASS '+name); }
  catch(e) { report.checks.push({name,status:'FAIL',errorType:e.name,message:e.message.split('\n')[0]}); throw e; }
}
async function go(p, route) {
  await p.bringToFront(); const r = await p.goto(base+route, {waitUntil:'domcontentloaded'}); assert.equal(r.status(),200);
  await p.waitForFunction(() => document.querySelector('main') && !document.querySelector('main .animate-pulse, main .animate-spin'));
}
async function button(p, text) {
  await p.bringToFront();
  await p.waitForFunction(t => [...document.querySelectorAll('button')].some(b=>b.textContent.trim()===t && !b.disabled && b.getBoundingClientRect().width>0),{},text);
  const h = await p.evaluateHandle(t=>[...document.querySelectorAll('button')].find(b=>b.textContent.trim()===t && b.getBoundingClientRect().width>0),text);
  await h.asElement().asLocator().click(); await h.dispose();
}
async function response(p, method, endpoint, action, expected=200) {
  const promise = p.waitForResponse(r=>r.request().method()===method && new URL(r.url()).pathname==='/api/v1'+endpoint);
  const [r] = await Promise.all([promise,action()]); assert.equal(r.status(),expected,endpoint); return (await r.json()).data;
}
async function api(p, method, endpoint, payload) {
  const result = await p.evaluate(async ({method,endpoint,payload})=>{
    const r = await fetch('/api/v1'+endpoint,{method,headers:{'Content-Type':'application/json',Authorization:'Bearer '+sessionStorage.getItem('novamart_auth_token')},...(payload===undefined?{}:{body:JSON.stringify(payload)})});
    return {status:r.status,body:await r.json()};
  },{method,endpoint,payload});
  assert.equal(result.status,200,method+' '+endpoint); return result.body.data;
}
async function login(p, email, password) {
  await go(p,'/login'); await p.type('main input[type=email]',email); await p.type('main input[type=password]',password);
  assert(await p.$eval('main input[type=email]',(e,v)=>e.value===v,email),'Email input did not match intended local account');
  assert(await p.$eval('main input[type=password]',(e,v)=>e.value===v,password),'Password input did not match private credential (value omitted)');
  const d = await response(p,'POST','/auth/login',()=>p.click('main form button[type=submit]'));
  await p.waitForFunction(()=>!location.pathname.includes('/login')); return d.user.role;
}
async function shot(p,name) {
  await p.screenshot({path:path.join(out,name+'.png'),fullPage:true}); report.screenshots.push('database/evidence/phase07d-browser/'+name+'.png');
}
async function setPrice(p, amount) {
  const product = fixture.products.find(p=>p.productType==='ELECTRONICS');
  const before = await api(p,'GET','/admin/products/'+product.id);
  await go(p,'/admin/products/'+product.id+'/edit');
  const h = await p.evaluateHandle(()=>{const l=[...document.querySelectorAll('label')].find(l=>l.textContent.trim().replace(/\s*\*$/,'')==='Giá bán (VND)'); return l && (document.getElementById(l.htmlFor)||l.parentElement.querySelector('input'));});
  assert(h.asElement(),'Price field missing'); await h.asElement().click({clickCount:3}); await p.keyboard.down('Control'); await p.keyboard.press('A'); await p.keyboard.up('Control'); await h.asElement().type(String(amount)); await h.dispose();
  if (!priceGateRecorded) {
    const started=report.http.length;
    await p.click('form button[type=submit]');
    await p.waitForFunction(()=>document.body.textContent.includes('Vui lòng cung cấp ít nhất một đường dẫn hình ảnh hợp lệ'));
    assert(!report.http.slice(started).some(r=>r.method==='PATCH'&&r.path==='/api/v1/admin/products/'+product.id));
    await shot(p,'admin-price-blocked-empty-image');
    report.checks.push({name:'Required live Web price edit on unchanged 07C images=[] fixture',status:'FAIL',
      details:{uiMessage:'Vui lòng cung cấp ít nhất một đường dẫn hình ảnh hợp lệ (http:// hoặc https://).',patchRequestSent:false,applicationUnmodified:true}});
    priceGateRecorded=true;
  }
  // Continue other checks through the existing price-only API; do not disguise this as a Web editor pass.
  const changed = await api(p,'PATCH','/admin/products/'+product.id,{price:amount,expectedVersion:before.version});
  assert.equal(changed.price,amount); assert.equal(changed.stock,before.stock);
  return {channel:'REAL_HTTP_API_FALLBACK_UI_PRICE_EDITOR_FAILED',price:changed.price, stock:changed.stock, additionalChangedFields:Object.keys(before).filter(k=>!['price','version','updatedAt'].includes(k)&&JSON.stringify(before[k])!==JSON.stringify(changed[k]))};
}
async function order(p) {
  for (const prod of fixture.products) {
    await go(p,'/products/'+prod.slug);
    await p.waitForFunction(()=>document.querySelector('main')?.textContent.includes('Hình ảnh không có sẵn'));
    const cart = await response(p,'POST','/cart/items',()=>button(p,'Thêm vào giỏ hàng')); assert(cart.items.length>=1);
  }
  await go(p,'/cart'); await p.waitForFunction(()=>document.querySelector('main')?.textContent.includes('10.200.000')); await shot(p,(offline?'offline':'online')+'-cart');
  await go(p,'/checkout');
  const d = await response(p,'POST','/orders',()=>button(p,'Xác nhận đặt hàng'),201);
  assert.equal(d.order.orderStatus,'PENDING'); assert.equal(d.order.paymentStatus,'UNPAID'); assert.equal(d.order.subtotal,10200000); assert.equal(d.order.total,10230000);
  assert.equal(d.order.items.length,2); assert(d.order.items.every(i=>i.quantity===1));
  const fashion = d.order.items.find(i=>i.sku==='DEFENSE-07C-FAS'); assert.deepEqual(fashion.selectedAttributes,{size:'M',color:'Black'});
  await p.waitForFunction(()=>location.pathname==='/order-success'); await shot(p,(offline?'offline':'online')+'-order-success');
  return d.order;
}
async function cancel(p,o) {
  console.log('Cancel UI: open Order');
  await go(p,'/orders/'+o.id); await button(p,'Hủy đơn hàng này');
  console.log('Cancel UI: confirm modal');
  const cancelled=await response(p,'POST','/orders/'+o.id+'/cancel',()=>button(p,'Xác nhận hủy'));
  assert.equal(cancelled.orderStatus,'CANCELLED'); assert(cancelled.stockReleasedAt); return cancelled;
}
const admin=await page('ADMIN'),customer=await page('CUSTOMER');
const summaryPath='/admin/dashboard/summary?from=2026-10-01T00:00:00Z&to=2026-11-01T00:00:00Z';
let first,second,third;
try {
  await step('Customer/Admin UI login and local clone health',async()=>{
    assert.equal(await login(admin,'admin@example.test',seedPassword),'ADMIN'); assert.equal(await login(customer,'defense07c@example.test',fixture.customerPassword),'CUSTOMER');
    const health=await api(admin,'GET','/health'); assert.equal(health.checks.replicaSet,'ok');
    assert.equal((await api(customer,'GET','/cart')).items.length,0); return {frontendPort:5174,apiPort:5002,database:'ecommerce_test'};
  });
  await step('Recover exact interrupted test Order, preserve dev fixture',async()=>{
    const failed=prior?.checks.find(c=>c.name==='5-minute functional flow: two Products → Cart → COD Order'&&c.status==='PASS')?.details;
    if(!failed?.orderId) return {needed:false};
    const o=await api(customer,'GET','/orders/'+failed.orderId);
    if(o.orderStatus==='PENDING') await cancel(customer,o); else assert.equal(o.orderStatus,'CANCELLED');
    for(const p of fixture.products) assert.equal((await api(admin,'GET','/admin/products/'+p.id)).stock,20);
    return {exactOrderId:o.id,status:'CANCELLED',testOnly:true,stockEach:20};
  });
  await step('Three polymorphic Products render their attributes',async()=>{
    for (const [slug,values] of [['apple-macbook-pro-14-inch-space-grey-001',['8GB','256GB','Demo CPU A']],['hand-blender-139',['800W','1L','220V']],['defense-07c-ao-thun',['Cotton','Black','M']]]) {
      await go(customer,'/products/'+slug); await customer.waitForFunction(vals=>vals.every(v=>document.querySelector('main')?.textContent.includes(v)),{},values);
    }
    return {types:['ELECTRONICS','FASHION','HOME_APPLIANCE']};
  });
  const baseline=await api(admin,'GET',summaryPath);
  await step('5-minute functional flow: two Products → Cart → COD Order',async()=>{first=await order(customer);return {orderId:first.id,orderCode:first.orderCode,subtotal:first.subtotal,shippingFee:first.shippingFee,total:first.total};});
  await step('Price-only API fallback A→B; historical Web Order/customer/address unchanged',async()=>{
    const changed=await setPrice(admin,12000000); const old=await api(customer,'GET','/orders/'+first.id);
    assert.deepEqual(old.items,first.items); assert.deepEqual(old.customerSnapshot,first.customerSnapshot); assert.deepEqual(old.shippingAddress,first.shippingAddress);
    await go(customer,'/orders/'+first.id); await customer.waitForFunction(()=>document.querySelector('main')?.textContent.includes('10.000.000')); await shot(customer,'snapshot-A-after-B');
    const pending=await api(admin,'GET',summaryPath); assert.equal(pending.totalRevenue,baseline.totalRevenue);
    report.snapshot={orderCode:first.orderCode,priceA:10000000,priceB:12000000,priceAtPurchaseAfterChange:old.items.find(i=>i.sku==='DEFENSE-07C-ELE').priceAtPurchase,itemsUnchanged:true,customerAddressUnchanged:true,adminFormMutation:changed};
    return report.snapshot;
  });
  await step('5-minute functional reset: cancel once and restore A',async()=>{
    await cancel(customer,first); const restore=await setPrice(admin,10000000);
    for(const p of fixture.products) assert.equal((await api(admin,'GET','/admin/products/'+p.id)).stock,20);
    assert.equal((await api(customer,'GET','/cart')).items.length,0); return restore;
  });
  await step('10-minute functional flow: new COD and snapshot A→B',async()=>{
    second=await order(customer); await setPrice(admin,12000000); assert.deepEqual((await api(customer,'GET','/orders/'+second.id)).items,second.items);
    return {orderId:second.id,orderCode:second.orderCode,subtotal:second.subtotal};
  });
  await step('Admin UI confirm → ship → complete; revenue +10.2m/units +2, no ship',async()=>{
    const before=await api(admin,'GET',summaryPath); await go(admin,'/admin/orders/'+second.id);
    for(const [action,label,status] of [['confirm','Xác nhận đơn','CONFIRMED'],['ship','Chuyển giao hàng','SHIPPING'],['complete','Hoàn tất đơn & Thu tiền','COMPLETED']]) {
      const d=await response(admin,'POST','/admin/orders/'+second.id+'/'+action,()=>button(admin,label)); assert.equal(d.orderStatus,status);
      if(action==='complete') {assert.equal(d.paymentStatus,'PAID');assert(d.completedAt);report.completedAt=d.completedAt;}
    }
    await shot(admin,'completed-COD'); const after=await api(admin,'GET',summaryPath);
    assert.equal(after.totalRevenue-before.totalRevenue,10200000); assert.equal(after.totalProductsSold-before.totalProductsSold,2);
    assert.deepEqual((await api(customer,'GET','/orders/'+second.id)).items,second.items);
    for(const p of fixture.products) assert.equal((await api(admin,'GET','/admin/products/'+p.id)).stock,19);
    report.revenueDelta={before,after,revenue:10200000,units:2,excludedShipping:30000,orderTotal:10230000}; return {revenue:10200000,units:2,stockEach:19};
  });
  await step('Dashboard renders all five API reports and charts',async()=>{
    const start=report.http.length; await go(admin,'/admin/dashboard'); await admin.waitForSelector('svg.recharts-surface');
    await admin.waitForFunction(()=>document.querySelector('main')?.textContent.includes('Doanh Thu'));
    for (const endpoint of ['summary','revenue','top-products','category-revenue','order-status']) assert(report.http.slice(start).some(r=>r.path.endsWith('/dashboard/'+endpoint)&&r.status===200),endpoint);
    await shot(admin,'dashboard'); await setPrice(admin,10000000); return {fiveEndpoints200:true,rechartsRendered:true};
  });
  await step('Safe offline drill: block external network, cold reload, login and COD/cancel',async()=>{
    offline=true; const probe=await page('OFFLINE');
    assert.equal(await login(probe,'defense07c@example.test',fixture.customerPassword),'CUSTOMER');
    await probe.evaluate(()=>new Promise(resolve=>{const i=new Image();i.onload=()=>resolve(false);i.onerror=()=>resolve(true);i.src='https://example.invalid/phase07d-probe.png';}));
    assert(report.offline.blocked.some(b=>b.origin==='https://example.invalid'));
    third=await order(probe); await cancel(probe,third); await shot(probe,'offline-cancelled');
    assert.equal((await api(probe,'GET','/cart')).items.length,0);
    for(const p of fixture.products) assert.equal((await api(admin,'GET','/admin/products/'+p.id)).stock,19);
    report.offline.browserLocalCodWithExternalDenied='PASS'; return {orderCode:third.orderCode,externalDenied:true,coldCache:true,localCodCancelled:true,hostDisconnect:'MANUAL_PENDING'};
  });
  assert.equal(report.pageErrors.length,0); assert(report.http.every(r=>r.status>=200&&r.status<300));
  report.status='FAIL_WEB_PRICE_EDITOR_OTHER_FUNCTIONAL_CHECKS_PASS';
  process.exitCode=1;
} catch(e) { report.status='FAIL'; report.failureCustomerUrl=customer.url();report.failureBodyText=await customer.$eval('body',b=>b.textContent);report.failureVisibleButtons=await customer.$$eval('button',bs=>bs.map(b=>b.textContent.trim()).filter(Boolean)); if(await customer.$$eval('input[type=password]',es=>es.every(e=>!e.value))) await shot(customer,'failure-customer'); console.error('Rehearsal stopped: '+e.name); process.exitCode=1; }
finally {
  report.recordedAtEndUtc=new Date().toISOString();
  fs.writeFileSync(path.join(root,'database/evidence/phase07d-browser.json'),JSON.stringify(report,null,2));
  await browser.close(); console.log(JSON.stringify({status:report.status,checks:report.checks.length,http:report.http.length,screenshots:report.screenshots.length}));
}
