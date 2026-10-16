import React from 'react';
import { ShieldCheck, FileText, CheckCircle2 } from 'lucide-react';

export const PolicyTermsPage: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6 sm:p-10 space-y-8">
        <div className="border-b border-slate-100 pb-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-50 text-brand-700 text-xs font-semibold mb-3">
            <FileText className="w-3.5 h-3.5" />
            <span>Văn bản Quy chế Sàn TMĐT</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Điều Khoản Dịch Vụ & Quy Chế Hoạt Động
          </h1>
          <p className="text-xs text-slate-500 mt-2">
            Cập nhật lần cuối: Ngày 15 tháng 10 năm 2026 • Tuân thủ Nghị định 52/2013/NĐ-CP & Nghị định 85/2021/NĐ-CP
          </p>
        </div>

        <section className="space-y-4 text-slate-700 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-brand-600 flex-shrink-0" />
            1. Nguyên tắc chung & Phạm vi áp dụng
          </h2>
          <p>
            Sàn thương mại điện tử NovaMart là kênh giao dịch trực tuyến cung cấp các sản phẩm Điện tử, Thời trang và Đồ gia dụng chính hãng. Khách hàng khi đăng ký tài khoản hoặc đặt hàng tại NovaMart đồng ý tuân thủ toàn bộ các điều khoản được quy định trong bản quy chế này.
          </p>
        </section>

        <section className="space-y-4 text-slate-700 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-brand-600 flex-shrink-0" />
            2. Quyền và nghĩa vụ của người mua
          </h2>
          <ul className="list-disc pl-5 space-y-1.5 text-slate-600">
            <li>Cung cấp chính xác thông tin giao hàng gồm họ tên, số điện thoại và địa chỉ chi tiết.</li>
            <li>Được quyền kiểm tra ngoại quan hàng hóa khi nhận (đồng kiểm) trước khi thanh toán đối với đơn COD.</li>
            <li>Được yêu cầu đổi trả, bảo hành hoặc hoàn tiền theo Chính sách Đổi trả 15 ngày của NovaMart.</li>
            <li>Không được lợi dụng hệ thống để đặt hàng ảo, gian lận mã giảm giá hoặc gây cản trở hoạt động của sàn.</li>
          </ul>
        </section>

        <section className="space-y-4 text-slate-700 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-brand-600 flex-shrink-0" />
            3. Quy định về giá bán và thanh toán
          </h2>
          <p>
            Giá bán niêm yết trên NovaMart là giá thanh toán cuối cùng đã bao gồm thuế Giá trị gia tăng (VAT) theo quy định hiện hành. Các phương thức thanh toán hợp lệ bao gồm Thanh toán khi nhận hàng (COD) và Thanh toán trực tuyến qua Cổng thanh toán VNPAY an toàn.
          </p>
        </section>

        <section className="space-y-4 text-slate-700 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-brand-600 flex-shrink-0" />
            4. Bảo vệ quyền lợi người tiêu dùng & Giải quyết tranh chấp
          </h2>
          <p>
            Mọi khiếu nại phát sinh trong quá trình giao dịch đều được tiếp nhận và xử lý trong vòng 24 - 48 giờ làm việc qua Hotline 1900 1234 hoặc email support@novamart.vn. Trường hợp không thể thương lượng, tranh chấp sẽ được giải quyết tại Tòa án có thẩm quyền theo pháp luật Việt Nam.
          </p>
        </section>

        <div className="bg-slate-50 rounded-xl p-4 border border-slate-200 text-xs text-slate-600 flex items-start gap-3">
          <ShieldCheck className="w-5 h-5 text-brand-600 flex-shrink-0 mt-0.5" />
          <p>
            NovaMart cam kết vận hành minh bạch, bảo vệ dữ liệu cá nhân của người tiêu dùng và tuân thủ tuyệt đối quy định pháp luật về thương mại điện tử tại Việt Nam.
          </p>
        </div>
      </div>
    </div>
  );
};
