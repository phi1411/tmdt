import React from 'react';
import { ShoppingBag, ShieldCheck, Truck, RotateCcw, Headphones, Heart } from 'lucide-react';
import { Link } from 'react-router-dom';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-slate-900 text-slate-300 mt-20 border-t border-slate-800">
      {/* Service Highlights */}
      <div className="border-b border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-slate-800 text-brand-400 flex items-center justify-center flex-shrink-0">
                <Truck className="w-6 h-6" />
              </div>
              <div>
                <h4 className="font-semibold text-white text-sm">Giao Hàng Tận Nơi</h4>
                <p className="text-xs text-slate-400 mt-0.5">Vận chuyển nhanh chóng toàn quốc</p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-slate-800 text-brand-400 flex items-center justify-center flex-shrink-0">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <div>
                <h4 className="font-semibold text-white text-sm">Thanh Toán An Toàn</h4>
                <p className="text-xs text-slate-400 mt-0.5">Bảo mật đa tầng COD & VNPAY</p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-slate-800 text-brand-400 flex items-center justify-center flex-shrink-0">
                <RotateCcw className="w-6 h-6" />
              </div>
              <div>
                <h4 className="font-semibold text-white text-sm">Chính Sách Đổi Trả</h4>
                <p className="text-xs text-slate-400 mt-0.5">Đổi trả miễn phí trong 15 ngày</p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-slate-800 text-brand-400 flex items-center justify-center flex-shrink-0">
                <Headphones className="w-6 h-6" />
              </div>
              <div>
                <h4 className="font-semibold text-white text-sm">Hỗ Trợ Khách Hàng</h4>
                <p className="text-xs text-slate-400 mt-0.5">Tư vấn tận tâm 24/7</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Footer Links */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div className="space-y-4 md:col-span-1">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center text-white font-bold">
                <ShoppingBag className="w-4 h-4" />
              </div>
              <span className="text-xl font-bold tracking-tight text-white">
                Nova<span className="text-brand-400">mart</span>
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              NovaMart — Sàn thương mại điện tử hàng đầu cung cấp sản phẩm chính hãng, trải nghiệm mua sắm tiện lợi và giao hàng nhanh chóng trên toàn quốc.
            </p>
          </div>

          <div>
            <h5 className="text-sm font-semibold text-white uppercase tracking-wider mb-3">Ngành Hàng</h5>
            <ul className="space-y-2 text-xs text-slate-400">
              <li>
                <Link to="/products?productType=ELECTRONICS" className="hover:text-white transition-colors">
                  Điện tử & Công nghệ
                </Link>
              </li>
              <li>
                <Link to="/products?productType=FASHION" className="hover:text-white transition-colors">
                  Thời trang & Phụ kiện
                </Link>
              </li>
              <li>
                <Link to="/products?productType=HOME_APPLIANCE" className="hover:text-white transition-colors">
                  Đồ gia dụng & Đời sống
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h5 className="text-sm font-semibold text-white uppercase tracking-wider mb-3">Tài Khoản</h5>
            <ul className="space-y-2 text-xs text-slate-400">
              <li>
                <Link to="/orders" className="hover:text-white transition-colors">
                  Đơn hàng của tôi
                </Link>
              </li>
              <li>
                <Link to="/account/addresses" className="hover:text-white transition-colors">
                  Sổ địa chỉ nhận hàng
                </Link>
              </li>
              <li>
                <Link to="/account/profile" className="hover:text-white transition-colors">
                  Thông tin cá nhân
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h5 className="text-sm font-semibold text-white uppercase tracking-wider mb-3">Chăm Sóc Khách Hàng</h5>
            <ul className="text-xs text-slate-400 space-y-2">
              <li className="text-slate-300 font-medium">Hotline: 1900 1234 (8:00 - 21:00)</li>
              <li className="text-slate-300 font-medium">Email: support@novamart.vn</li>
              <li>
                <Link to="/policy/shipping" className="hover:text-white transition-colors">
                  Chính sách giao hàng & đồng kiểm
                </Link>
              </li>
              <li>
                <Link to="/policy/returns" className="hover:text-white transition-colors">
                  Chính sách đổi trả & hoàn tiền 15 ngày
                </Link>
              </li>
              <li>
                <Link to="/policy/terms" className="hover:text-white transition-colors">
                  Quy chế hoạt động & Điều khoản
                </Link>
              </li>
              <li>
                <Link to="/policy/privacy" className="hover:text-white transition-colors">
                  Chính sách bảo mật thông tin
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="border-t border-slate-800 mt-10 pt-6 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-4">
          <p>© 2026 NovaMart. Tất cả các quyền được bảo lưu.</p>
          <div className="flex items-center gap-1">
            <span>Thiết kế & Xây dựng với</span>
            <Heart className="w-3.5 h-3.5 text-rose-500 fill-rose-500 inline" />
            <span>cho trải nghiệm mua sắm hiện đại</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
