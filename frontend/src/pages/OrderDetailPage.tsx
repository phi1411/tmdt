import React, { useEffect, useState, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ChevronLeft,
  Package,
  MapPin,
  CreditCard,
  Clock,
  ShieldCheck,
  Ban,
  Star,
} from 'lucide-react';
import { orderApi } from '../api/orderApi';
import { paymentApi } from '../api/paymentApi';
import { OrderDetail, OrderStatus } from '../types/order';
import { formatVND, formatDateTime } from '../utils/formatters';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Skeleton } from '../components/ui/Skeleton';
import { ErrorState } from '../components/ui/ErrorState';
import { ReviewModal, ReviewItemInfo } from '../components/reviews/ReviewModal';
import { useToast } from '../contexts/ToastContext';
import { CustomApiError } from '../types/api';

export const OrderDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { success: toastSuccess, error: toastError, warning: toastWarning } = useToast();

  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [showCancelModal, setShowCancelModal] = useState<boolean>(false);
  const [cancelling, setCancelling] = useState<boolean>(false);
  const [retryingPayment, setRetryingPayment] = useState<boolean>(false);
  const [selectedReviewItem, setSelectedReviewItem] = useState<ReviewItemInfo | null>(null);

  const fetchOrderDetail = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await orderApi.getOrderById(id);
      setOrder(data);
    } catch (err: any) {
      setError(err?.message || 'Không thể tìm thấy thông tin đơn hàng này.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchOrderDetail();
  }, [fetchOrderDetail]);

  // Handle Cancel Order
  const handleCancelOrder = async () => {
    if (!order) return;

    setCancelling(true);
    try {
      const updatedOrder = await orderApi.cancelOrder(order.id, {
        expectedVersion: order.version,
      });
      setOrder(updatedOrder);
      toastSuccess('Đã hủy đơn hàng thành công và hoàn trả số lượng vào tồn kho.');
      setShowCancelModal(false);
    } catch (err: any) {
      if (err instanceof CustomApiError) {
        if (err.code === 'ORDER_CHANGED' || err.code === 'INVALID_TRANSITION') {
          toastWarning('Trạng thái đơn hàng đã thay đổi. Đang làm mới dữ liệu...');
          await fetchOrderDetail();
        } else {
          toastError(err.message || 'Không thể hủy đơn hàng.');
        }
      } else {
        toastError('Lỗi máy chủ khi hủy đơn hàng.');
      }
    } finally {
      setCancelling(false);
    }
  };

  const handleRetryPayment = async () => {
    if (!order) return;
    setRetryingPayment(true);
    try {
      const attempt = await paymentApi.createPaymentAttempt(order.id, order.version);
      if (attempt.paymentUrl) {
        toastSuccess('Đang chuyển hướng tới cổng thanh toán VNPAY...');
        window.location.href = attempt.paymentUrl;
      } else {
        toastWarning('Chưa khởi tạo được liên kết thanh toán ngay. Vui lòng thử lại sau.');
      }
    } catch (err: any) {
      if (err instanceof CustomApiError && err.status === 503) {
        toastError('Cổng thanh toán VNPAY hiện chưa khả dụng.');
      } else {
        toastError(err?.message || 'Không thể tạo phiên thanh toán mới.');
      }
    } finally {
      setRetryingPayment(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-6">
        <Skeleton className="h-6 w-32 rounded" />
        <Skeleton className="h-10 w-64 rounded-xl" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <Skeleton className="lg:col-span-2 h-96 rounded-2xl" />
          <Skeleton className="h-80 rounded-2xl" />
        </div>
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <ErrorState
          title="Không tìm thấy đơn hàng"
          message={error || 'Đơn hàng không tồn tại hoặc bạn không có quyền xem đơn hàng này.'}
          onRetry={fetchOrderDetail}
        />
      </div>
    );
  }

  // Cancellation eligibility rule according to BR-ORDER:
  // "cancel PENDING/CONFIRMED khi chưa PAID/REVIEW_REQUIRED; không SHIPPING/COMPLETED"
  const canCancel =
    (order.orderStatus === 'PENDING' || order.orderStatus === 'CONFIRMED') &&
    order.paymentStatus !== 'PAID' &&
    !order.paymentReviewRequired;

  const getOrderStatusBadge = (status: OrderStatus) => {
    switch (status) {
      case 'PENDING':
        return <Badge variant="warning">Chờ xử lý</Badge>;
      case 'CONFIRMED':
        return <Badge variant="primary">Đã xác nhận</Badge>;
      case 'SHIPPING':
        return <Badge variant="info">Đang vận chuyển</Badge>;
      case 'COMPLETED':
        return <Badge variant="success">Hoàn thành</Badge>;
      case 'CANCELLED':
        return <Badge variant="danger">Đã hủy</Badge>;
      case 'EXPIRED':
        return <Badge variant="neutral">Hết hạn</Badge>;
      default:
        return <Badge>{status}</Badge>;
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-8">
      {/* Top Bar / Back button */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-200">
        <Link
          to="/orders"
          className="inline-flex items-center gap-1.5 text-xs sm:text-sm font-semibold text-slate-600 hover:text-brand-600 transition-colors"
        >
          <ChevronLeft className="w-4 h-4" />
          <span>Quay lại danh sách đơn hàng</span>
        </Link>

        {canCancel && (
          <Button
            variant="danger"
            size="sm"
            onClick={() => setShowCancelModal(true)}
            icon={<Ban className="w-4 h-4" />}
          >
            Hủy đơn hàng này
          </Button>
        )}
      </div>

      {/* Order Header Card */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-8 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight font-mono">
              {order.orderCode}
            </h1>
            {getOrderStatusBadge(order.orderStatus)}
          </div>
          <p className="text-xs text-slate-400 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5" />
            <span>Ngày đặt: {formatDateTime(order.createdAt)}</span>
          </p>
        </div>

        <div className="text-left md:text-right">
          <div className="text-xs text-slate-400">Tổng thanh toán</div>
          <div className="text-2xl font-extrabold text-brand-700 tracking-tight">
            {formatVND(order.total)}
          </div>
        </div>
      </div>

      {/* Snapshot Verification Notice */}
      <div className="p-4 rounded-2xl bg-slate-100/70 border border-slate-200/60 flex items-start gap-3 text-xs text-slate-600">
        <ShieldCheck className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <span className="font-bold text-slate-800">Dữ liệu Snapshot lịch sử bất biến: </span>
          <span>
            Thông tin sản phẩm, đơn giá tại thời điểm mua, danh mục và địa chỉ nhận hàng được cố định trong bản ghi đơn hàng của MongoDB.
          </span>
        </div>
      </div>

      {/* Grid: Items Snapshot (Left) + Order Info (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Ordered Items Snapshot Table */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm space-y-6">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2 pb-3 border-b border-slate-100">
            <Package className="w-5 h-5 text-brand-600" />
            <span>Sản Phẩm Đã Mua ({order.items.length})</span>
          </h2>

          <div className="divide-y divide-slate-100">
            {order.items.map((item, idx) => (
              <div key={idx} className="py-4 first:pt-0 last:pb-0 flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center">
                <div className="flex gap-4 items-center flex-1 min-w-0">
                  <div className="w-16 h-16 rounded-xl bg-slate-100 border border-slate-200/60 overflow-hidden flex-shrink-0 flex items-center justify-center">
                    {item.image ? (
                      <img src={item.image} alt={item.productName} className="w-full h-full object-cover" />
                    ) : (
                      <span className="text-[10px] text-slate-400">Không có ảnh</span>
                    )}
                  </div>

                  <div className="space-y-1 min-w-0">
                    <h3 className="text-sm font-semibold text-slate-900 line-clamp-2">
                      {item.productName}
                    </h3>
                    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                      <span className="font-mono text-[11px] text-slate-400">SKU: {item.sku}</span>
                      <span>•</span>
                      <span>Ngành: {item.categoryName || item.productType}</span>
                    </div>

                    {/* Snapshot Selected Attributes */}
                    {item.selectedAttributes && Object.keys(item.selectedAttributes).length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {Object.entries(item.selectedAttributes).filter(([k]) => k !== 'skuId').map(([k, v]) => (
                          <span key={k} className="px-2 py-0.5 rounded bg-slate-100 text-[11px] font-medium text-slate-700">
                            {k === 'size' ? 'Size' : k === 'color' ? 'Màu' : k}: {String(v)}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex sm:flex-col items-center sm:items-end justify-between w-full sm:w-auto text-xs sm:text-right pt-2 sm:pt-0">
                  <div className="text-slate-500">
                    {formatVND(item.priceAtPurchase)} × <span className="font-bold">{item.quantity}</span>
                  </div>
                  <div className="text-sm font-bold text-slate-900 sm:mt-1">
                    {formatVND(item.lineTotal)}
                  </div>
                  {order.orderStatus === 'COMPLETED' && (
                    <div className="mt-2.5">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setSelectedReviewItem(item)}
                        icon={<Star className="w-3.5 h-3.5 fill-amber-400 text-amber-500" />}
                        className="text-xs border-amber-300 hover:bg-amber-50 text-amber-900"
                      >
                        Viết đánh giá
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Pricing Totals Breakdown */}
          <div className="pt-6 border-t border-slate-100 space-y-2.5 text-sm">
            <div className="flex justify-between text-slate-600">
              <span>Tạm tính tiền hàng:</span>
              <span className="font-semibold text-slate-900">{formatVND(order.subtotal)}</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>Phí vận chuyển:</span>
              <span className="font-semibold text-slate-900">{formatVND(order.shippingFee)}</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>Giảm giá:</span>
              <span className="font-semibold text-emerald-700">{order.discount ? '−' : ''}{formatVND(order.discount)}</span>
            </div>
            <div className="flex justify-between pt-3 border-t border-slate-100 items-baseline">
              <span className="font-bold text-slate-900 text-base">Tổng thanh toán:</span>
              <span className="text-xl font-extrabold text-brand-700">{formatVND(order.total)}</span>
            </div>
          </div>
        </div>

        {/* Right: Shipping Address Snapshot & Payment Info */}
        <div className="space-y-6">
          {/* Shipping Address Snapshot Card */}
          <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm space-y-3">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2 pb-2 border-b border-slate-100">
              <MapPin className="w-5 h-5 text-brand-600" />
              <span>Địa Chỉ Giao Hàng</span>
            </h2>

            <div className="text-xs text-slate-600 space-y-1.5 leading-relaxed">
              <div className="font-bold text-sm text-slate-900">
                {order.shippingAddress.receiverName}
              </div>
              <div className="text-slate-500 font-mono">{order.shippingAddress.phone}</div>
              <div>
                {order.shippingAddress.addressLine}
                {order.shippingAddress.ward ? `, ${order.shippingAddress.ward}` : ''}
                {order.shippingAddress.district ? `, ${order.shippingAddress.district}` : ''}
                {`, ${order.shippingAddress.province}`}
              </div>
            </div>
          </div>

          {/* Payment Status Card */}
          <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm space-y-3">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2 pb-2 border-b border-slate-100">
              <CreditCard className="w-5 h-5 text-brand-600" />
              <span>Thanh Toán & Trạng Thái</span>
            </h2>

            <div className="text-xs space-y-2">
              <div className="flex justify-between">
                <span className="text-slate-500">Phương thức:</span>
                <span className="font-semibold text-slate-900">
                  {order.paymentMethod === 'COD' ? 'Thanh toán khi nhận hàng (COD)' : 'VNPAY Sandbox'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Trạng thái tiền:</span>
                <span className="font-semibold text-slate-900">{order.paymentStatus}</span>
              </div>
              {order.paidAt && (
                <div className="flex justify-between">
                  <span className="text-slate-500">Thời gian trả:</span>
                  <span className="text-slate-800">{formatDateTime(order.paidAt)}</span>
                </div>
              )}
              {order.completedAt && (
                <div className="flex justify-between">
                  <span className="text-slate-500">Hoàn thành lúc:</span>
                  <span className="text-slate-800">{formatDateTime(order.completedAt)}</span>
                </div>
              )}
              {order.cancelledAt && (
                <div className="flex justify-between">
                  <span className="text-slate-500">Hủy đơn lúc:</span>
                  <span className="text-rose-600 font-medium">{formatDateTime(order.cancelledAt)}</span>
                </div>
              )}

              {order.paymentMethod === 'VNPAY' &&
                order.orderStatus === 'PENDING' &&
                order.paymentStatus === 'FAILED' &&
                !!order.paymentExpiresAt && Date.parse(order.paymentExpiresAt) > Date.now() &&
                !order.paymentReviewRequired && (
                  <div className="pt-3 border-t border-slate-100">
                    <Button
                      variant="primary"
                      size="sm"
                      className="w-full justify-center"
                      loading={retryingPayment}
                      onClick={handleRetryPayment}
                    >
                      Thanh toán qua VNPAY
                    </Button>
                  </div>
                )}
            </div>
          </div>
        </div>
      </div>

      {/* Cancel Order Confirmation Modal */}
      <Modal
        isOpen={showCancelModal}
        onClose={() => setShowCancelModal(false)}
        title="Xác Nhận Hủy Đơn Hàng"
        description="Bạn có chắc chắn muốn hủy đơn hàng này không?"
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-600 leading-relaxed">
            Hành động này sẽ cập nhật trạng thái đơn thành <span className="font-bold text-rose-600">ĐÃ HỦY (CANCELLED)</span> và giải phóng tồn kho cho các sản phẩm trong đơn một lần duy nhất theo quy định nghiệp vụ NoSQL.
          </p>

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowCancelModal(false)}
            >
              Giữ lại đơn
            </Button>
            <Button
              variant="danger"
              size="sm"
              loading={cancelling}
              onClick={handleCancelOrder}
            >
              Xác nhận hủy
            </Button>
          </div>
        </div>
      </Modal>

      {/* UGC Review Submission Modal */}
      <ReviewModal
        isOpen={!!selectedReviewItem}
        onClose={() => setSelectedReviewItem(null)}
        orderId={order.id}
        item={selectedReviewItem}
        onSuccess={async () => {
          await fetchOrderDetail();
        }}
      />
    </div>
  );
};
