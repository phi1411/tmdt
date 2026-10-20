import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { adminOrdersApi } from '../api/adminOrdersApi';
import { AdminOrder, AdminOrderAllowedAction } from '../types/adminOrder';
import { formatVND, formatDateTime } from '../utils/formatters';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Skeleton } from '../components/ui/Skeleton';
import { useToast } from '../contexts/ToastContext';
import {
  ChevronLeft,
  Package,
  User,
  MapPin,
  Clock,
  ShieldCheck,
  CheckCircle,
  Truck,
  CheckSquare,
  Ban,
  AlertCircle,
  AlertTriangle,
  RotateCcw,
} from 'lucide-react';

export const AdminOrderDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { success: toastSuccess, error: toastError, warning: toastWarning } = useToast();

  const [order, setOrder] = useState<AdminOrder | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Action Loading & Modal States
  const [actionLoading, setActionLoading] = useState<AdminOrderAllowedAction | null>(null);
  const [showCancelModal, setShowCancelModal] = useState<boolean>(false);

  const fetchOrder = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await adminOrdersApi.getById(id);
      setOrder(data);
    } catch (err: any) {
      setError(err?.message || 'Không thể tải chi tiết đơn hàng.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchOrder();
  }, [fetchOrder]);

  const handleAction = async (action: AdminOrderAllowedAction) => {
    if (!order) return;
    setActionLoading(action);

    try {
      let updated: AdminOrder;
      if (action === 'confirm') {
        updated = await adminOrdersApi.confirm(order.id, order.version);
        toastSuccess('Đã xác nhận đơn hàng thành công (CONFIRMED)!');
      } else if (action === 'ship') {
        updated = await adminOrdersApi.ship(order.id, order.version);
        toastSuccess('Đã chuyển đơn hàng sang trạng thái đang giao (SHIPPING)!');
      } else if (action === 'complete') {
        updated = await adminOrdersApi.complete(order.id, order.version);
        toastSuccess('Đơn hàng đã hoàn thành và đối soát thanh toán (COMPLETED & PAID)!');
      } else if (action === 'cancel') {
        updated = await adminOrdersApi.cancel(order.id, order.version);
        toastSuccess('Đã hủy đơn hàng và hoàn trả tồn kho sản phẩm (CANCELLED)!');
        setShowCancelModal(false);
      } else {
        return;
      }

      setOrder(updated);
    } catch (err: any) {
      if (err?.code === 'ORDER_CHANGED' || err?.status === 409) {
        toastWarning('Đơn hàng đã có thay đổi bởi tiến trình khác. Đang tải lại dữ liệu...');
        await fetchOrder();
      } else {
        toastError(err?.message || `Thao tác ${action} thất bại.`);
      }
    } finally {
      setActionLoading(null);
    }
  };

  const getOrderStatusBadge = (status: string) => {
    switch (status) {
      case 'PENDING':
        return <Badge variant="warning">Chờ xử lý</Badge>;
      case 'CONFIRMED':
        return <Badge variant="info">Đã xác nhận</Badge>;
      case 'SHIPPING':
        return <Badge variant="primary">Đang giao hàng</Badge>;
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

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-32 w-full rounded-2xl" />
        <Skeleton className="h-64 w-full rounded-2xl" />
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="p-8 bg-white rounded-2xl border border-slate-200 text-center space-y-4">
        <AlertCircle className="w-8 h-8 text-rose-500 mx-auto" />
        <div className="font-bold text-slate-800">{error || 'Không tìm thấy đơn hàng.'}</div>
        <div className="flex justify-center gap-3">
          <Button variant="outline" size="sm" onClick={fetchOrder}>
            Thử lại
          </Button>
          <Link to="/admin/orders">
            <Button variant="primary" size="sm">
              Về danh sách
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  const allowed = order.allowedActions || [];

  return (
    <div className="space-y-8">
      {/* Top Header & Breadcrumb */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-200">
        <Link
          to="/admin/orders"
          className="inline-flex items-center gap-1.5 text-xs sm:text-sm font-semibold text-slate-600 hover:text-brand-600 transition-colors"
        >
          <ChevronLeft className="w-4 h-4" />
          <span>Quay lại danh sách đơn hàng</span>
        </Link>

        <Button
          variant="outline"
          size="sm"
          onClick={fetchOrder}
          icon={<RotateCcw className="w-3.5 h-3.5" />}
        >
          Làm mới
        </Button>
      </div>

      {/* Main Order Meta Header */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-8 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-xl sm:text-2xl font-black text-slate-900 font-mono tracking-tight">
              {order.orderCode}
            </h1>
            {getOrderStatusBadge(order.orderStatus)}
            {order.paymentReviewRequired && (
              <Badge variant="warning">
                <AlertTriangle className="w-3 h-3 mr-1 inline" />
                Cần đối soát thanh toán
              </Badge>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500 font-medium">
            <span className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              Ngày tạo: {formatDateTime(order.createdAt)}
            </span>
            <span>•</span>
            <span>Phiên bản (OCC): v{order.version}</span>
            <span>•</span>
            <span>Phương thức: <strong>{order.paymentMethod}</strong> ({order.paymentStatus})</span>
          </div>
        </div>

        <div className="text-left md:text-right space-y-1">
          <div className="text-xs text-slate-400 font-medium">Tổng tiền thanh toán</div>
          <div className="text-2xl sm:text-3xl font-black text-brand-700 tracking-tight">
            {formatVND(order.total)}
          </div>
        </div>
      </div>

      {/* Allowed Actions Bar */}
      <div className="bg-slate-900 text-white p-6 rounded-2xl shadow-md flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-sm font-bold tracking-tight text-white flex items-center gap-2">
            <Package className="w-4 h-4 text-brand-400" />
            <span>Thao Tác Quản Trị Vòng Đời Đơn Hàng</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Các nút thao tác dưới đây được kích hoạt theo đúng trạng thái hiện hành từ MongoDB (`allowedActions`)
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {allowed.includes('confirm') && (
            <Button
              variant="primary"
              size="sm"
              loading={actionLoading === 'confirm'}
              onClick={() => handleAction('confirm')}
              icon={<CheckCircle className="w-4 h-4" />}
            >
              Xác nhận đơn
            </Button>
          )}

          {allowed.includes('ship') && (
            <Button
              variant="secondary"
              size="sm"
              loading={actionLoading === 'ship'}
              onClick={() => handleAction('ship')}
              icon={<Truck className="w-4 h-4" />}
            >
              Chuyển giao hàng
            </Button>
          )}

          {allowed.includes('complete') && (
            <Button
              variant="primary"
              size="sm"
              className="bg-emerald-600 hover:bg-emerald-700 text-white"
              loading={actionLoading === 'complete'}
              onClick={() => handleAction('complete')}
              icon={<CheckSquare className="w-4 h-4" />}
            >
              Hoàn tất đơn & Thu tiền
            </Button>
          )}

          {allowed.includes('cancel') && (
            <Button
              variant="danger"
              size="sm"
              loading={actionLoading === 'cancel'}
              onClick={() => setShowCancelModal(true)}
              icon={<Ban className="w-4 h-4" />}
            >
              Hủy đơn & Hoàn kho
            </Button>
          )}

          {allowed.length === 0 && (
            <span className="text-xs text-slate-400 italic">
              Đơn hàng đang ở trạng thái kết thúc ({order.orderStatus}), không còn thao tác hợp lệ.
            </span>
          )}
        </div>
      </div>

      {/* Snapshot Verification Banner */}
      <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200/80 flex items-start gap-3 text-xs text-emerald-900">
        <ShieldCheck className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
        <div>
          <span className="font-bold">Tính toàn vẹn dữ liệu NoSQL: </span>
          <span>
            Thông tin người mua, địa chỉ nhận hàng và đơn giá sản phẩm được đóng băng dưới dạng snapshot nhúng trong Order document tại thời điểm đặt hàng. Mọi thay đổi giá trong Catalog không làm ảnh hưởng lịch sử đơn này.
          </span>
        </div>
      </div>

      {/* 2-Column Details: Customer Snapshot (Left) + Shipping Address (Right) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Customer Snapshot */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs space-y-4">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 pb-3 border-b border-slate-100">
            <User className="w-4 h-4 text-brand-600" />
            <span>Thông Tin Khách Hàng (Snapshot)</span>
          </h3>

          <div className="space-y-2 text-xs text-slate-700">
            <div className="flex justify-between">
              <span className="text-slate-400">Họ và tên:</span>
              <span className="font-bold text-slate-900">{order.customerSnapshot?.name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Số điện thoại:</span>
              <span className="font-mono text-slate-900">{order.customerSnapshot?.phone}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Email:</span>
              <span className="text-slate-900">{order.customerSnapshot?.email}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Mã người dùng (User ID):</span>
              <span className="font-mono text-[10px] text-slate-500">{order.userId}</span>
            </div>
          </div>
        </div>

        {/* Shipping Address Snapshot */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs space-y-4">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 pb-3 border-b border-slate-100">
            <MapPin className="w-4 h-4 text-brand-600" />
            <span>Địa Chỉ Giao Hàng (Snapshot)</span>
          </h3>

          <div className="space-y-2 text-xs text-slate-700">
            <div className="flex justify-between">
              <span className="text-slate-400">Người nhận hàng:</span>
              <span className="font-bold text-slate-900">{order.shippingAddress?.receiverName}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Số điện thoại nhận:</span>
              <span className="font-mono text-slate-900">{order.shippingAddress?.phone}</span>
            </div>
            <div className="pt-2 border-t border-slate-100">
              <span className="text-slate-400 block mb-1">Địa chỉ chi tiết:</span>
              <span className="font-medium text-slate-900 leading-relaxed block">
                {order.shippingAddress?.addressLine}
                {order.shippingAddress?.ward ? `, ${order.shippingAddress.ward}` : ''}
                {order.shippingAddress?.district ? `, ${order.shippingAddress.district}` : ''}
                {`, ${order.shippingAddress?.province}`}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Snapshot Items List */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs p-6 space-y-4">
        <h3 className="text-base font-bold text-slate-900 flex items-center gap-2 pb-3 border-b border-slate-100">
          <Package className="w-5 h-5 text-brand-600" />
          <span>Danh Sách Sản Phẩm Đặt Hàng ({order.items?.length || 0})</span>
        </h3>

        <div className="divide-y divide-slate-100">
          {order.items?.map((item, idx) => (
            <div key={idx} className="py-4 first:pt-0 last:pb-0 flex items-center justify-between gap-4">
              <div className="flex items-center gap-4 min-w-0">
                <div className="w-16 h-16 rounded-xl bg-slate-100 border border-slate-200/60 overflow-hidden flex-shrink-0 flex items-center justify-center">
                  {item.image ? (
                    <img src={item.image} alt={item.productName} className="w-full h-full object-cover" />
                  ) : (
                    <span className="text-[10px] text-slate-400">Không có ảnh</span>
                  )}
                </div>

                <div className="min-w-0 space-y-1">
                  <div className="font-bold text-sm text-slate-900 leading-snug truncate" title={item.productName}>
                    {item.productName}
                  </div>
                  <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                    <span className="font-mono text-[11px] text-slate-400">SKU: {item.sku}</span>
                    <span>•</span>
                    <span>Ngành: {item.categoryName || item.productType}</span>
                    {item.selectedAttributes && Object.keys(item.selectedAttributes).length > 0 && (
                      <>
                        <span>•</span>
                        <span className="text-brand-600">
                          {Object.entries(item.selectedAttributes)
                            .filter(([k]) => k !== 'skuId')
                            .map(([k, v]) => `${k}: ${v}`)
                            .join(', ')}
                        </span>
                      </>
                    )}
                  </div>
                  <div className="text-xs text-slate-500">
                    Đơn giá snapshot: <span className="font-semibold text-slate-800">{formatVND(item.priceAtPurchase)}</span> × {item.quantity}
                  </div>
                </div>
              </div>

              <div className="text-right flex-shrink-0 font-bold text-sm text-slate-900">
                {formatVND(item.lineTotal)}
              </div>
            </div>
          ))}
        </div>

        {/* Totals Breakdown */}
        <div className="pt-4 border-t border-slate-100 flex flex-col items-end gap-2 text-xs">
          <div className="flex justify-between w-64 text-slate-600">
            <span>Tiền hàng (Subtotal):</span>
            <span className="font-semibold text-slate-900">{formatVND(order.subtotal)}</span>
          </div>
          <div className="flex justify-between w-64 text-slate-600">
            <span>Phí vận chuyển:</span>
            <span className="font-semibold text-slate-900">{formatVND(order.shippingFee)}</span>
          </div>
          <div className="flex justify-between w-64 text-slate-600">
            <span>Giảm giá:</span>
            <span className="font-semibold text-emerald-700">{order.discount ? '−' : ''}{formatVND(order.discount || 0)}</span>
          </div>
          <div className="flex justify-between w-64 pt-2 border-t border-slate-200 text-sm font-bold text-slate-900">
            <span>Tổng thanh toán:</span>
            <span className="text-base text-brand-700 font-extrabold">{formatVND(order.total)}</span>
          </div>
        </div>
      </div>

      {/* Cancel Order Modal */}
      <Modal
        isOpen={showCancelModal}
        onClose={() => setShowCancelModal(false)}
        title="Xác Nhận Hủy Đơn Hàng"
        description="Bạn có chắc chắn muốn hủy đơn hàng này với vai trò Quản Trị Viên không?"
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-600 leading-relaxed">
            Hành động này sẽ cập nhật trạng thái đơn thành <span className="font-bold text-rose-600">CANCELLED</span> và giải phóng tồn kho cho các sản phẩm trong đơn một lần duy nhất theo transaction an toàn.
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
              loading={actionLoading === 'cancel'}
              onClick={() => handleAction('cancel')}
            >
              Xác nhận hủy đơn
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
