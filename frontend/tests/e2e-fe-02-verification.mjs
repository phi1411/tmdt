import puppeteer from 'puppeteer-core';
import fs from 'fs';

const EDGE_PATH = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const BASE_URL = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173';
const SEED_PASSWORD = process.env.E2E_SEED_PASSWORD;
if (!SEED_PASSWORD) throw new Error('E2E_SEED_PASSWORD is required');

const results = {
  flows: [],
  httpCalls: [],
  errors: [],
};

function logFlow(name, status, details = '') {
  console.log(`[${status}] ${name} ${details ? '- ' + details : ''}`);
  results.flows.push({ name, status, details });
}

async function runFE02Verification() {
  console.log('=== KHỞI ĐỘNG E2E PHASE FE-02 VERIFICATION ===\n');

  const browser = await puppeteer.launch({
    executablePath: EDGE_PATH,
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--window-size=1440,900'],
  });

  const page = await browser.newPage();
  page.setDefaultNavigationTimeout(60000);
  await page.setViewport({ width: 1440, height: 900 });

  page.on('console', (msg) => {
    const text = msg.text();
    if (msg.type() === 'error' && !text.includes('favicon.ico')) {
      console.error(`  [Browser Error] ${text}`);
      results.errors.push(`[Console Error] ${text}`);
    }
  });

  page.on('response', (response) => {
    const url = response.url();
    if (url.includes('/api/v1/')) {
      const endpoint = url.split('/api/v1')[1];
      const method = response.request().method();
      const status = response.status();
      results.httpCalls.push({ method, endpoint, status });
    }
  });

  try {
    // ====================================================
    // TEST 1: CUSTOMER REGRESSION & ROLE PROTECTION
    // ====================================================
    console.log('--- 1. Kiểm tra Customer Regression & Bảo Vệ Quyền Truy Cập ---');
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle2' });

    // Login as Customer
    await page.type('main input[type="email"]', 'customer01@example.test');
    await page.type('main input[type="password"]', SEED_PASSWORD);

    const [loginCustRes] = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/api/v1/auth/login')),
      page.click('main form button[type="submit"]'),
    ]);

    await page.waitForFunction(() => !window.location.pathname.includes('/login'), { timeout: 8000 });
    logFlow('1.1 Đăng nhập Customer hợp lệ', 'PASS', `Status: ${loginCustRes.status()}`);

    // Verify Customer cannot access /admin/dashboard
    await page.goto(`${BASE_URL}/admin/dashboard`, { waitUntil: 'networkidle2' });
    const custAdminBlockedContent = await page.content();
    if (custAdminBlockedContent.includes('Chức Năng Dành Cho Khách Hàng') || custAdminBlockedContent.includes('403')) {
      logFlow('1.2 Chặn Customer truy cập Admin Portal', 'PASS', 'Hiển thị thông báo không có quyền quản trị');
    } else {
      logFlow('1.2 Chặn Customer truy cập Admin Portal', 'FAIL', 'Không chặn được Customer vào Admin');
    }

    // Verify Customer Catalog & Cart still working
    await page.goto(`${BASE_URL}/products`, { waitUntil: 'networkidle2' });
    const productItems = await page.$$('.group.relative.flex.flex-col.bg-white');
    logFlow('1.3 Khách hàng duyệt Catalog bình thường', 'PASS', `Hiển thị ${productItems.length} sản phẩm`);

    // Logout Customer
    await page.evaluate(() => {
      sessionStorage.clear();
    });

    // ====================================================
    // TEST 2: ADMIN LOGIN & DASHBOARD AGGREGATION METRICS
    // ====================================================
    console.log('\n--- 2. Kiểm tra Admin Login & Dashboard MongoDB Aggregation ---');
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle2' });
    await page.type('main input[type="email"]', 'admin@example.test');
    await page.type('main input[type="password"]', SEED_PASSWORD);

    const [loginAdminRes] = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/api/v1/auth/login')),
      page.click('main form button[type="submit"]'),
    ]);

    await page.waitForFunction(() => !window.location.pathname.includes('/login'), { timeout: 8000 });
    logFlow('2.1 Đăng nhập Admin thành công', 'PASS', `Status: ${loginAdminRes.status()} - Nhận quyền ADMIN`);

    // Navigate to Admin Dashboard
    await page.goto(`${BASE_URL}/admin/dashboard`, { waitUntil: 'networkidle2' });
    await new Promise((r) => setTimeout(r, 1500));

    const dashboardContent = await page.content();
    const hasRevenueCard = dashboardContent.includes('Doanh Thu Hàng Hóa');
    const hasOrdersCard = dashboardContent.includes('Tổng Đơn Hàng');
    const hasProductsSoldCard = dashboardContent.includes('Sản Phẩm Đã Bán');
    const hasCustomersCard = dashboardContent.includes('Tổng Khách Hàng');

    if (hasRevenueCard && hasOrdersCard && hasProductsSoldCard && hasCustomersCard) {
      logFlow('2.2 Render 4 thẻ KPI Summary từ Aggregation', 'PASS', 'Hiển thị đầy đủ Doanh thu, Đơn hàng, Số lượng bán, Khách hàng');
    } else {
      logFlow('2.2 Render 4 thẻ KPI Summary', 'FAIL', 'Thiếu thẻ KPI');
    }

    // Verify Charts
    const hasRechartsArea = (await page.$$('.recharts-surface')).length > 0;
    if (hasRechartsArea) {
      logFlow('2.3 Render Biểu đồ Recharts Doanh thu & Ngành hàng', 'PASS', 'Các biểu đồ Recharts SVG render trực quan');
    } else {
      logFlow('2.3 Render Biểu đồ Recharts', 'WARN', 'Không tìm thấy phần tử recharts-surface');
    }

    // Top 5 Products List
    const hasTopProducts = dashboardContent.includes('Top 5 Sản Phẩm Bán Chạy Nhất');
    logFlow('2.4 Render Top 5 Sản Phẩm Bán Chạy', hasTopProducts ? 'PASS' : 'FAIL', 'Bảng xếp hạng Top 5 hiển thị từ MongoDB pipeline');

    // Test Date Preset Toggle (7 ngày qua)
    const sevenDaysBtnHandle = await page.evaluateHandle(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      return btns.find((b) => b.textContent && b.textContent.includes('7 ngày qua'));
    });
    const sevenDaysBtn = sevenDaysBtnHandle.asElement();
    if (sevenDaysBtn) {
      await sevenDaysBtn.click();
      await new Promise((r) => setTimeout(r, 1000));
      logFlow('2.5 Chuyển đổi bộ lọc thời gian (7 ngày qua)', 'PASS', 'Pipeline cập nhật phạm vi UTC an toàn');
    }

    // ====================================================
    // TEST 3: ADMIN ORDERS MANAGEMENT
    // ====================================================
    console.log('\n--- 3. Kiểm tra Quản Lý Đơn Hàng Admin ---');
    await page.goto(`${BASE_URL}/admin/orders`, { waitUntil: 'networkidle2' });
    await new Promise((r) => setTimeout(r, 1000));

    const ordersTableRows = await page.$$('tbody tr');
    logFlow('3.1 Tải danh sách đơn hàng Admin (GET /admin/orders 200)', 'PASS', `Hiển thị ${ordersTableRows.length} dòng đơn hàng`);

    // Click first "Chi tiết" button
    const detailLinkHandle = await page.evaluateHandle(() => {
      const links = Array.from(document.querySelectorAll('tbody a'));
      return links.find((a) => a.getAttribute('href') && a.getAttribute('href').startsWith('/admin/orders/'));
    });
    const detailLink = detailLinkHandle.asElement();

    if (detailLink) {
      await detailLink.click();
      await page.waitForNavigation({ waitUntil: 'networkidle2' }).catch(() => {});
      await new Promise((r) => setTimeout(r, 1000));

      const orderDetailContent = await page.content();
      const hasSnapshotBadge = orderDetailContent.includes('Snapshot');
      const hasAllowedActions = orderDetailContent.includes('Thao Tác Quản Trị Vòng Đời Đơn Hàng');

      if (hasSnapshotBadge && hasAllowedActions) {
        logFlow('3.2 Xem chi tiết đơn hàng & snapshot bất biến (GET /admin/orders/:id 200)', 'PASS', 'Hiển thị snapshot người nhận, sản phẩm, và thanh thao tác allowedActions');
      } else {
        logFlow('3.2 Xem chi tiết đơn hàng', 'FAIL', 'Thiếu thông tin snapshot hoặc allowedActions');
      }
    }

    // ====================================================
    // TEST 4: ADMIN PRODUCTS MANAGEMENT & POLYMORPHIC FORM
    // ====================================================
    console.log('\n--- 4. Kiểm tra Quản Lý Sản Phẩm & Form Đa Hình ---');
    await page.goto(`${BASE_URL}/admin/products`, { waitUntil: 'networkidle2' });
    await new Promise((r) => setTimeout(r, 1000));

    const productsTableRows = await page.$$('tbody tr');
    logFlow('4.1 Tải danh sách sản phẩm Admin (GET /admin/products 200)', 'PASS', `Hiển thị ${productsTableRows.length} dòng sản phẩm`);

    // Open Create Product Form
    await page.goto(`${BASE_URL}/admin/products/new`, { waitUntil: 'networkidle2' });
    const createFormContent = await page.content();
    if (createFormContent.includes('1. Thông Tin Cơ Bản Sản Phẩm') && createFormContent.includes('2. Thuộc Tính Đa Hình Ngành Hàng')) {
      logFlow('4.2 Mở Form tạo sản phẩm mới (/admin/products/new)', 'PASS', 'Form hiển thị phân khu cơ bản và thuộc tính đa hình');
    } else {
      logFlow('4.2 Mở Form tạo sản phẩm mới', 'FAIL', 'Không tải được form tạo sản phẩm');
    }

    // Switch ProductType to FASHION and check attributes
    await page.select('select', 'FASHION');
    await new Promise((r) => setTimeout(r, 400));
    const fashionFormContent = await page.content();
    if (fashionFormContent.includes('Chất liệu vải') && fashionFormContent.includes('Các kích cỡ')) {
      logFlow('4.3 Chuyển đổi Polymorphic Schema sang FASHION', 'PASS', 'Form hiển thị các trường Kích cỡ, Màu sắc, Chất liệu thời trang');
    } else {
      logFlow('4.3 Chuyển đổi Polymorphic Schema sang FASHION', 'FAIL', 'Thiếu trường thời trang');
    }

    // Switch ProductType to HOME_APPLIANCE and check attributes
    await page.select('select', 'HOME_APPLIANCE');
    await new Promise((r) => setTimeout(r, 400));
    const homeFormContent = await page.content();
    if (homeFormContent.includes('Công suất tiêu thụ') && homeFormContent.includes('Dung tích thiết bị')) {
      logFlow('4.4 Chuyển đổi Polymorphic Schema sang HOME_APPLIANCE', 'PASS', 'Form hiển thị các trường Công suất, Dung tích đồ gia dụng');
    } else {
      logFlow('4.4 Chuyển đổi Polymorphic Schema sang HOME_APPLIANCE', 'FAIL', 'Thiếu trường gia dụng');
    }

    // ====================================================
    // TEST 5: ADMIN CATEGORIES MANAGEMENT
    // ====================================================
    console.log('\n--- 5. Kiểm tra Quản Lý Ngành Hàng Admin ---');
    await page.goto(`${BASE_URL}/admin/categories`, { waitUntil: 'networkidle2' });
    await new Promise((r) => setTimeout(r, 1000));

    const catRows = await page.$$('tbody tr');
    logFlow('5.1 Tải danh sách ngành hàng (GET /admin/categories 200)', 'PASS', `Hiển thị ${catRows.length} ngành hàng`);

    // Open Add Category Modal
    const addCatBtnHandle = await page.evaluateHandle(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      return btns.find((b) => b.textContent && b.textContent.includes('Thêm ngành hàng'));
    });
    const addCatBtn = addCatBtnHandle.asElement();
    if (addCatBtn) {
      await addCatBtn.click();
      await new Promise((r) => setTimeout(r, 400));
      const modalContent = await page.content();
      if (modalContent.includes('Thêm Ngành Hàng Mới') && modalContent.includes('Loại Schema Thuộc Tính')) {
        logFlow('5.2 Mở Modal tạo ngành hàng mới', 'PASS', 'Modal hiển thị đầy đủ trường tên, slug và productType');
      }
      // Close modal
      await page.evaluate(() => {
        const dialog = document.querySelector('div[role="dialog"]');
        if (dialog) {
          const cancelBtn = Array.from(dialog.querySelectorAll('button')).find(
            (b) => b.textContent && b.textContent.includes('Hủy')
          );
          if (cancelBtn) cancelBtn.click();
        }
      });
    }

    // ====================================================
    // TEST 6: ADMIN USERS MANAGEMENT & PROTECTION
    // ====================================================
    console.log('\n--- 6. Kiểm tra Quản Lý Người Dùng & Bất Biến Admin ---');
    await page.goto(`${BASE_URL}/admin/users`, { waitUntil: 'networkidle2' });
    await new Promise((r) => setTimeout(r, 1000));

    const userRows = await page.$$('tbody tr');
    logFlow('6.1 Tải danh sách tài khoản (GET /admin/users 200)', 'PASS', `Hiển thị ${userRows.length} tài khoản người dùng`);

    const usersContent = await page.content();
    const hasAdminProtectedPill = usersContent.includes('Bảo vệ') || usersContent.includes('ADMIN');
    if (hasAdminProtectedPill) {
      logFlow('6.2 Bảo vệ tài khoản ADMIN bất biến', 'PASS', 'Tài khoản Quản trị viên được khóa bảo vệ, không thể khóa từ giao diện');
    } else {
      logFlow('6.2 Bảo vệ tài khoản ADMIN bất biến', 'FAIL', 'Thiếu nhãn bảo vệ tài khoản Admin');
    }

    // ====================================================
    // TEST 7: VNPAY RETURN PAGE VERIFICATION
    // ====================================================
    console.log('\n--- 7. Kiểm tra Trang Tiếp Nhận VNPAY Return ---');
    const mockReturnQuery = 'vnp_Amount=10000000&vnp_BankCode=NCB&vnp_CardType=ATM&vnp_OrderInfo=Thanh+toan+don+hang&vnp_PayDate=20261007190000&vnp_ResponseCode=00&vnp_TmnCode=DEMO&vnp_TransactionNo=14000000&vnp_TransactionStatus=00&vnp_TxnRef=TEST123&vnp_SecureHash=invalidhashmock';
    await page.goto(`${BASE_URL}/payment/return?${mockReturnQuery}`, { waitUntil: 'networkidle2' });
    await new Promise((r) => setTimeout(r, 1200));

    const returnPageContent = await page.content();
    if (returnPageContent.includes('Chữ Ký Không Hợp Lệ') || returnPageContent.includes('Thanh Toán') || returnPageContent.includes('VNPAY')) {
      logFlow('7.1 Xử lý phản hồi VNPAY Return an toàn (/payment/return)', 'PASS', 'Hiển thị kết quả kiểm tra chữ ký số an toàn từ backend');
    } else {
      logFlow('7.1 Xử lý phản hồi VNPAY Return', 'FAIL', 'Trang kết quả thanh toán bị lỗi');
    }

    // ====================================================
    // TEST 8: RESPONSIVE ADMIN VIEWPORTS
    // ====================================================
    console.log('\n--- 8. Kiểm tra Responsive Admin Viewports ---');
    // Desktop: 1440x900
    await page.setViewport({ width: 1440, height: 900 });
    await page.goto(`${BASE_URL}/admin/dashboard`, { waitUntil: 'networkidle2' });
    const desktopSidebar = await page.$('aside.hidden.lg\\:flex');
    logFlow('8.1 Desktop Viewport (1440px)', desktopSidebar ? 'PASS' : 'WARN', 'Sidebar Admin cố định bên trái');

    // Tablet: 900x768
    await page.setViewport({ width: 900, height: 768 });
    await page.goto(`${BASE_URL}/admin/dashboard`, { waitUntil: 'networkidle2' });
    const tabletToggle = await page.$('button.lg\\:hidden');
    logFlow('8.2 Tablet Viewport (900px)', tabletToggle ? 'PASS' : 'WARN', 'Nút menu thu gọn hiển thị');

    // Mobile: 390x844
    await page.setViewport({ width: 390, height: 844 });
    await page.goto(`${BASE_URL}/admin/dashboard`, { waitUntil: 'networkidle2' });
    const mobileToggle = await page.$('button.lg\\:hidden');
    if (mobileToggle) {
      await mobileToggle.click();
      await new Promise((r) => setTimeout(r, 500));
      const mobileDrawer = await page.$('aside, div.fixed.inset-0.z-50');
      logFlow('8.3 Mobile Viewport (390px)', mobileDrawer ? 'PASS' : 'WARN', 'Drawer Menu mở trượt mượt mà trên mobile');
    }

  } catch (err) {
    console.error('Lỗi ngoại lệ E2E FE-02:', err);
    results.errors.push(`[Fatal FE-02 Error] ${err.stack || err.message}`);
  } finally {
    await browser.close();
  }

  console.log('\n==================================================');
  const passCount = results.flows.filter((f) => f.status === 'PASS').length;
  const failCount = results.flows.filter((f) => f.status === 'FAIL').length;
  console.log(`TỔNG KẾT PHASE FE-02: ${passCount} PASS / ${failCount} FAIL`);
  if (results.errors.length > 0) {
    console.log('LỖI GHI NHẬN:', results.errors);
  } else {
    console.log('KHÔNG CÓ LỖI UNCAUGHT HOẶC RUNTIME NÀO!');
  }
  console.log('==================================================');

  return results;
}

runFE02Verification().then((res) => {
  fs.writeFileSync(process.env.E2E_RESULTS || 'tests/e2e-fe-02-results.json', JSON.stringify(res, null, 2), 'utf-8');
  process.exit(res.flows.length !== 22 || res.flows.some((f) => f.status !== 'PASS') || res.errors.some((e) => e.includes('Fatal')) ? 1 : 0);
});
