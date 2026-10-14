import React from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { CheckCircle2, Package, ShoppingBag } from 'lucide-react';
import { formatVND } from '../utils/formatters';
import { Button } from '../components/ui/Button';

export const OrderSuccessPage: React.FC = () => {
  const [searchParams] = useSearchParams();

  const orderId = searchParams.get('orderId') || '';
  const orderCode = searchParams.get('orderCode') || '';
  const total = searchParams.get('total') ? parseInt(searchParams.get('total')!, 10) : 0;
  const method = searchParams.get('method') || 'COD';

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24 text-center">
      <div className="bg-white rounded-3xl border border-slate-200/80 p-8 sm:p-12 shadow-sm space-y-6">
        <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto animate-in zoom-in">
          <CheckCircle2 className="w-10 h-10 sm:w-12 sm:h-12" />
        </div>

        <div className="space-y-2">
          <span className="text-xs font-bold uppercase tracking-wider text-emerald-600">Đặt hàng thành công</span>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Cảm ơn bạn đã mua sắm tại Novamart!
          </h1>
          <p className="text-sm text-slate-500 max-w-md mx-auto">
            Đơn hàng của bạn đã được tiếp nhận và lưu trữ nguyên vẹn snapshot trong cơ sở dữ liệu MongoDB.
          </p>
        </div>

        {/* Order Details Card */}
        <div className="p-5 sm:p-6 rounded-2xl bg-slate-50 border border-slate-200/60 max-w-md mx-auto text-left space-y-3 text-sm">
          <div className="flex justify-between items-center pb-2 border-b border-slate-200">
            <span className="text-slate-500">Mã đơn hàng:</span>
            <span className="font-mono font-bold text-slate-900">{orderCode || orderId || 'Đang cập nhật'}</span>
          </div>
          <div className="flex justify-between items-center pb-2 border-b border-slate-200">
            <span className="text-slate-500">Tổng thanh toán:</span>
            <span className="font-extrabold text-brand-700 text-base">{formatVND(total)}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-slate-500">Phương thức:</span>
            <span className="font-semibold text-slate-800">
              {method === 'COD' ? 'Thanh toán khi nhận hàng (COD)' : 'VNPAY Online'}
            </span>
          </div>
        </div>

        {/* CTAs */}
        <div className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-3">
          {orderId && (
            <Link to={`/orders/${orderId}`}>
              <Button variant="primary" size="lg" icon={<Package className="w-4 h-4" />}>
                Xem chi tiết đơn hàng
              </Button>
            </Link>
          )}

          <Link to="/products">
            <Button variant="outline" size="lg" icon={<ShoppingBag className="w-4 h-4" />}>
              Tiếp tục mua sắm
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
};
