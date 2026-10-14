import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Trash2,
  Plus,
  Minus,
  AlertTriangle,
  ArrowRight,
  ShoppingBag,
  RotateCcw,
} from 'lucide-react';
import { useCart } from '../contexts/CartContext';
import { formatVND } from '../utils/formatters';
import { Button } from '../components/ui/Button';
import { EmptyState } from '../components/ui/EmptyState';
import { Badge } from '../components/ui/Badge';
import { Skeleton } from '../components/ui/Skeleton';

export const CartPage: React.FC = () => {
  const navigate = useNavigate();
  const { cart, loading, updateQuantity, removeItem, clearCart, refreshCart } = useCart();
  const [updatingLineId, setUpdatingLineId] = useState<string | null>(null);

  const handleUpdateQty = async (lineId: string, currentQty: number, delta: number) => {
    const nextQty = currentQty + delta;
    if (nextQty < 1 || nextQty > 99) return;
    setUpdatingLineId(lineId);
    await updateQuantity(lineId, nextQty);
    setUpdatingLineId(null);
  };

  const handleRemove = async (lineId: string) => {
    setUpdatingLineId(lineId);
    await removeItem(lineId);
    setUpdatingLineId(null);
  };

  if (loading && !cart) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-6">
        <Skeleton className="h-8 w-48 rounded-lg" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-28 w-full rounded-2xl" />
            ))}
          </div>
          <Skeleton className="h-64 w-full rounded-2xl" />
        </div>
      </div>
    );
  }

  const items = cart?.items || [];
  const isEmpty = items.length === 0;

  if (isEmpty) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <EmptyState
          icon={<ShoppingBag className="w-8 h-8" />}
          title="Giỏ hàng của bạn đang trống"
          description="Hãy khám phá các sản phẩm công nghệ, thời trang và gia dụng độc đáo tại Novamart."
          actionLabel="Tiếp tục mua sắm"
          onAction={() => navigate('/products')}
        />
      </div>
    );
  }

  const hasIssues = !cart?.checkoutAllowed;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-8">
      <div className="flex items-center justify-between pb-6 border-b border-slate-200">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Giỏ Hàng
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Bạn có <span className="font-semibold text-slate-800">{items.length}</span> loại sản phẩm trong giỏ
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={refreshCart}
            icon={<RotateCcw className="w-4 h-4" />}
          >
            Đồng bộ giỏ
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={clearCart}
            className="text-rose-600 hover:text-rose-700 hover:bg-rose-50 border-rose-200"
          >
            Xóa toàn bộ
          </Button>
        </div>
      </div>

      {/* Cart Issues Warning Alert */}
      {hasIssues && (
        <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 flex items-start gap-3 text-amber-900">
          <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm leading-relaxed">
            <span className="font-bold">Một số mặt hàng trong giỏ cần kiểm tra lại:</span>
            <p className="text-xs text-amber-800 mt-0.5">
              Tồn kho của sản phẩm đã thay đổi hoặc ngừng hoạt động. Vui lòng cập nhật số lượng hoặc xóa mặt hàng bị lỗi để có thể tiếp tục thanh toán.
            </p>
          </div>
        </div>
      )}

      {/* Cart Layout: Items List (Left) + Summary (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Items List */}
        <div className="lg:col-span-2 space-y-4">
          {items.map((item) => {
            const isUpdating = updatingLineId === item.lineId;
            const hasItemIssue = item.issues && item.issues.length > 0;

            return (
              <div
                key={item.lineId}
                className={`p-4 sm:p-5 bg-white rounded-2xl border transition-all ${
                  hasItemIssue
                    ? 'border-amber-300 bg-amber-50/20 shadow-xs'
                    : 'border-slate-200/80 shadow-xs hover:border-slate-300'
                }`}
              >
                <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
                  {/* Thumbnail & Product Info */}
                  <div className="flex gap-4 items-center flex-1 min-w-0">
                    <div className="w-20 h-20 rounded-xl bg-slate-100 border border-slate-200/60 overflow-hidden flex-shrink-0 flex items-center justify-center">
                      {item.image ? (
                        <img
                          src={item.image}
                          alt={item.name || 'Sản phẩm'}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <span className="text-[10px] text-slate-400">Không có ảnh</span>
                      )}
                    </div>

                    <div className="flex-1 min-w-0 space-y-1">
                      {item.slug ? (
                        <Link
                          to={`/products/${item.slug}`}
                          className="text-sm font-semibold text-slate-900 hover:text-brand-600 transition-colors line-clamp-1"
                        >
                          {item.name}
                        </Link>
                      ) : (
                        <span className="text-sm font-semibold text-slate-500">
                          {item.name || 'Sản phẩm không xác định'}
                        </span>
                      )}

                      {/* Selected Attributes info */}
                      {item.selectedAttributes && Object.keys(item.selectedAttributes).length > 0 && (
                        <div className="flex flex-wrap gap-2 text-xs text-slate-500">
                          {item.selectedAttributes.size && (
                            <span className="px-2 py-0.5 rounded bg-slate-100 text-[11px] font-medium">
                              Size: {item.selectedAttributes.size}
                            </span>
                          )}
                          {item.selectedAttributes.color && (
                            <span className="px-2 py-0.5 rounded bg-slate-100 text-[11px] font-medium">
                              Màu: {item.selectedAttributes.color}
                            </span>
                          )}
                        </div>
                      )}

                      <div className="text-sm font-bold text-slate-800">
                        {item.currentPrice ? formatVND(item.currentPrice) : 'Giá không xác định'}
                      </div>

                      {/* Item Issues Badge */}
                      {hasItemIssue && (
                        <div className="flex flex-wrap gap-1 pt-1">
                          {item.issues.map((iss, idx) => (
                            <Badge key={idx} variant="warning" size="sm">
                              {iss === 'STOCK_CONFLICT'
                                ? `Tồn kho chỉ còn ${item.stock}`
                                : iss === 'PRODUCT_UNAVAILABLE'
                                ? 'Ngừng kinh doanh'
                                : iss}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Quantity Selector & Line Total */}
                  <div className="flex items-center justify-between sm:justify-end gap-6 w-full sm:w-auto pt-3 sm:pt-0 border-t sm:border-0 border-slate-100">
                    <div className="flex items-center border border-slate-200 rounded-xl bg-slate-50">
                      <button
                        onClick={() => handleUpdateQty(item.lineId, item.quantity, -1)}
                        disabled={item.quantity <= 1 || isUpdating}
                        className="p-1.5 text-slate-600 hover:text-slate-900 disabled:opacity-40"
                      >
                        <Minus className="w-3.5 h-3.5" />
                      </button>
                      <span className="w-8 text-center text-xs font-bold text-slate-800">
                        {item.quantity}
                      </span>
                      <button
                        onClick={() => handleUpdateQty(item.lineId, item.quantity, 1)}
                        disabled={item.quantity >= item.stock || isUpdating}
                        className="p-1.5 text-slate-600 hover:text-slate-900 disabled:opacity-40"
                      >
                        <Plus className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    <div className="text-right min-w-[100px]">
                      <div className="text-sm font-bold text-brand-700">
                        {formatVND(item.lineTotal)}
                      </div>
                    </div>

                    <button
                      onClick={() => handleRemove(item.lineId)}
                      disabled={isUpdating}
                      className="p-2 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition-colors"
                      title="Xóa khỏi giỏ"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Order Summary Box */}
        <aside className="w-full bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm space-y-6">
          <h2 className="text-lg font-bold text-slate-900 pb-3 border-b border-slate-100">
            Tóm Tắt Đơn Hàng
          </h2>

          <div className="space-y-3 text-sm">
            <div className="flex justify-between text-slate-600">
              <span>Tạm tính hàng hóa:</span>
              <span className="font-semibold text-slate-900">{formatVND(cart?.subtotal || 0)}</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>Phí vận chuyển:</span>
              <span className="text-xs text-slate-500 italic">Tính tại bước Đặt hàng</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>Giảm giá:</span>
              <span className="font-semibold text-slate-900">0 ₫</span>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-100 flex justify-between items-baseline">
            <span className="text-base font-bold text-slate-900">Tổng cộng tạm tính:</span>
            <div className="text-right">
              <span className="text-2xl font-extrabold text-brand-700">
                {formatVND(cart?.subtotal || 0)}
              </span>
              <p className="text-[11px] text-slate-400 mt-0.5">Chưa gồm phí ship</p>
            </div>
          </div>

          <Button
            variant="primary"
            size="lg"
            className="w-full shadow-md shadow-brand-500/20"
            disabled={hasIssues}
            onClick={() => navigate('/checkout')}
            icon={<ArrowRight className="w-4 h-4" />}
          >
            {hasIssues ? 'Vui lòng xử lý lỗi trước' : 'Tiến hành đặt hàng'}
          </Button>

          <p className="text-[11px] text-slate-400 text-center leading-relaxed">
            Giá và tồn kho sẽ được xác thực chính xác với máy chủ tại bước báo giá thanh toán.
          </p>
        </aside>
      </div>
    </div>
  );
};
