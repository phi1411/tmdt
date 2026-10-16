import React from 'react';
import { RotateCcw, CheckCircle2, AlertCircle } from 'lucide-react';

export const PolicyReturnsPage: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6 sm:p-10 space-y-8">
        <div className="border-b border-slate-100 pb-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-50 text-purple-700 text-xs font-semibold mb-3">
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Chính Sách Đổi Trả</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Chính Sách Đổi Trả & Hoàn Tiền 15 Ngày
          </h1>
          <p className="text-xs text-slate-500 mt-2">
            Đổi trả miễn phí — Cam kết bảo vệ quyền lợi người mua tối đa
          </p>
        </div>

        <section className="space-y-4 text-slate-700 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-purple-600 flex-shrink-0" />
            1. Điều kiện áp dụng đổi trả
          </h2>
          <p>
            Khách hàng được yêu cầu đổi trả hàng trong vòng <strong>15 ngày</strong> kể từ thời điểm đơn hàng chuyển sang trạng thái <strong>Đã Giao Hàng (COMPLETED)</strong> khi thỏa mãn các điều kiện:
          </p>
          <ul className="list-disc pl-5 space-y-1.5 text-slate-600">
            <li>Sản phẩm giao sai mẫu mã, màu sắc, kích thước so với đơn hàng đã đặt.</li>
            <li>Sản phẩm bị lỗi kỹ thuật từ nhà sản xuất hoặc hư hỏng trong quá trình vận chuyển.</li>
            <li>Sản phẩm còn nguyên tem mác, hộp đóng gói ban đầu, chưa qua sử dụng (đối với hàng Thời trang) và đầy đủ phụ kiện kèm theo (đối với hàng Điện tử, Gia dụng).</li>
          </ul>
        </section>

        <section className="space-y-4 text-slate-700 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-purple-600 flex-shrink-0" />
            2. Quy trình xử lý yêu cầu đổi trả
          </h2>
          <ol className="list-decimal pl-5 space-y-2 text-slate-600">
            <li><strong>Gửi yêu cầu:</strong> Khách hàng liên hệ bộ phận CSKH qua Hotline hoặc Email, gửi kèm mã đơn hàng và video mở hộp/hình ảnh lỗi sản phẩm.</li>
            <li><strong>Thẩm định:</strong> NovaMart phản hồi xác nhận trong vòng 24 giờ làm việc.</li>
            <li><strong>Thu hồi bưu kiện:</strong> Đơn vị vận chuyển liên kết của sàn sẽ đến lấy hàng tận nơi miễn phí.</li>
            <li><strong>Hoàn tiền:</strong> Tiền được hoàn trả theo phương thức thanh toán ban đầu (hoàn tiền qua VNPAY trong 2-5 ngày làm việc hoặc chuyển khoản ngân hàng đối với đơn COD).</li>
          </ol>
        </section>

        <div className="bg-amber-50 rounded-xl p-4 border border-amber-200 text-xs text-amber-800 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <p>
            Lưu ý: Quý khách vui lòng quay video khi bóc kiện hàng để làm cơ sở đối soát giải quyết khiếu nại nhanh chóng nhất.
          </p>
        </div>
      </div>
    </div>
  );
};
