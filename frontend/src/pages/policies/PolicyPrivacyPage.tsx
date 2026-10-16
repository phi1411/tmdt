import React from 'react';
import { Lock, Shield, CheckCircle2 } from 'lucide-react';

export const PolicyPrivacyPage: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6 sm:p-10 space-y-8">
        <div className="border-b border-slate-100 pb-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 text-xs font-semibold mb-3">
            <Lock className="w-3.5 h-3.5" />
            <span>Chính Sách Bảo Mật</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Chính Sách Bảo Mật Thông Tin Khách Hàng
          </h1>
          <p className="text-xs text-slate-500 mt-2">
            Tuân thủ Nghị định 13/2023/NĐ-CP về Bảo vệ dữ liệu cá nhân
          </p>
        </div>

        <section className="space-y-4 text-slate-700 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            1. Mục đích thu thập dữ liệu cá nhân
          </h2>
          <p>
            NovaMart chỉ thu thập các thông tin cần thiết phục vụ cho việc: xác thực tài khoản, xử lý đơn đặt hàng, giao nhận bưu kiện, cung cấp dịch vụ chăm sóc khách hàng và gửi thông báo trạng thái đơn hàng.
          </p>
        </section>

        <section className="space-y-4 text-slate-700 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            2. Cam kết bảo mật & Hạ tầng kỹ thuật
          </h2>
          <ul className="list-disc pl-5 space-y-1.5 text-slate-600">
            <li>Mật khẩu người dùng được mã hóa một chiều bằng thuật toán Argon2id hiện đại, không lưu trữ dạng plaintext.</li>
            <li>Giao dịch trực tuyến được mã hóa qua chuẩn HTTPS/TLS 1.3 và chữ ký số HMAC-SHA512 đối với cổng thanh toán VNPAY.</li>
            <li>Không mua bán, chia sẻ hoặc chuyển giao thông tin cá nhân khách hàng cho bất kỳ bên thứ ba nào khi chưa có sự đồng ý, trừ trường hợp cơ quan nhà nước có thẩm quyền yêu cầu theo luật.</li>
          </ul>
        </section>

        <section className="space-y-4 text-slate-700 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            3. Quyền của chủ thể dữ liệu
          </h2>
          <p>
            Khách hàng có toàn quyền tra cứu, chỉnh sửa thông tin cá nhân, sổ địa chỉ hoặc yêu cầu xóa tài khoản trực tiếp trong trang Quản lý tài khoản cá nhân tại NovaMart.
          </p>
        </section>

        <div className="bg-slate-50 rounded-xl p-4 border border-slate-200 text-xs text-slate-600 flex items-start gap-3">
          <Shield className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
          <p>
            An toàn thông tin của bạn là ưu tiên tuyệt đối tại NovaMart. Mọi thắc mắc về quyền riêng tư, vui lòng liên hệ Bộ phận An ninh Thông tin: privacy@novamart.vn.
          </p>
        </div>
      </div>
    </div>
  );
};
