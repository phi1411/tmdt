import React from 'react';
import { Truck, CheckCircle2, Clock } from 'lucide-react';

export const PolicyShippingPage: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6 sm:p-10 space-y-8">
        <div className="border-b border-slate-100 pb-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 text-blue-700 text-xs font-semibold mb-3">
            <Truck className="w-3.5 h-3.5" />
            <span>Chính Sách Vận Chuyển</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Chính Sách Giao Hàng & Biểu Phí Vận Chuyển
          </h1>
          <p className="text-xs text-slate-500 mt-2">
            Giao hàng toàn quốc 63 tỉnh thành • Hỗ trợ đồng kiểm khi nhận hàng
          </p>
        </div>

        <section className="space-y-4 text-slate-700 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-blue-600 flex-shrink-0" />
            1. Phạm vi & Thời gian giao hàng
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-2">
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
              <h3 className="font-bold text-slate-900 text-xs uppercase tracking-wider flex items-center gap-1.5 mb-1">
                <Clock className="w-4 h-4 text-blue-600" />
                Nội thành Hà Nội & TP. Hồ Chí Minh
              </h3>
              <p className="text-xs text-slate-600">Thời gian giao: 1 - 2 ngày làm việc.</p>
            </div>
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
              <h3 className="font-bold text-slate-900 text-xs uppercase tracking-wider flex items-center gap-1.5 mb-1">
                <Clock className="w-4 h-4 text-blue-600" />
                Các tỉnh thành và khu vực khác
              </h3>
              <p className="text-xs text-slate-600">Thời gian giao: 2 - 4 ngày làm việc.</p>
            </div>
          </div>
        </section>

        <section className="space-y-4 text-slate-700 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-blue-600 flex-shrink-0" />
            2. Biểu phí vận chuyển
          </h2>
          <p>
            Phí vận chuyển tiêu chuẩn cho mỗi đơn hàng là <strong>30.000 VNĐ</strong> cố định toàn quốc. NovaMart thường xuyên có các chương trình tài trợ <strong>Miễn phí vận chuyển (Freeship Xtra)</strong> cho các đơn hàng đạt giá trị tối thiểu theo quy định từng thời kỳ.
          </p>
        </section>

        <section className="space-y-4 text-slate-700 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-blue-600 flex-shrink-0" />
            3. Quy định đồng kiểm hàng hóa
          </h2>
          <p>
            NovaMart hỗ trợ chính sách <strong>Đồng kiểm khi nhận hàng</strong>: Khách hàng được phép mở gói hàng kiểm tra ngoại quan (đúng sản phẩm, đủ số lượng, nguyên vẹn tem mác, không móp méo) trước khi ký nhận và thanh toán cho nhân viên bưu tá. Không được phép cắm sạc thử điện hay dùng thử sản phẩm tại chỗ.
          </p>
        </section>
      </div>
    </div>
  );
};
