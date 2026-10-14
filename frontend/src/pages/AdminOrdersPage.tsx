import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { adminOrdersApi } from '../api/adminOrdersApi';
import { AdminOrderSummary } from '../types/adminOrder';
import { OrderStatus, PaymentStatus } from '../types/order';
import { PaginationMeta } from '../types/api';
import { formatVND, formatDateTime } from '../utils/formatters';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Pagination } from '../components/ui/Pagination';
import { Skeleton } from '../components/ui/Skeleton';
import {
  Package,
  Search,
  Filter,
  RotateCcw,
  AlertCircle,
  Eye,
  CreditCard,
  Banknote,
  AlertTriangle,
} from 'lucide-react';

export const AdminOrdersPage: React.FC = () => {
  const [orders, setOrders] = useState<AdminOrderSummary[]>([]);
  const [meta, setMeta] = useState<PaginationMeta>({
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 0,
  });

  // Filter States
  const [selectedStatus, setSelectedStatus] = useState<OrderStatus | ''>('');
  const [selectedPaymentStatus, setSelectedPaymentStatus] = useState<PaymentStatus | ''>('');
  const [searchCode, setSearchCode] = useState<string>('');
  const [appliedSearchCode, setAppliedSearchCode] = useState<string>('');
  const [currentPage, setCurrentPage] = useState<number>(1);

  // Loading States
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOrders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await adminOrdersApi.getList({
        status: selectedStatus || undefined,
        paymentStatus: selectedPaymentStatus || undefined,
        orderCode: appliedSearchCode ? appliedSearchCode.trim().toUpperCase() : undefined,
        page: currentPage,
        pageSize: 20,
      });

      setOrders(res.orders);
      setMeta(res.meta);
    } catch (err: any) {
      setError(err?.message || 'Không thể tải danh sách đơn hàng từ máy chủ.');
    } finally {
      setLoading(false);
    }
  }, [selectedStatus, selectedPaymentStatus, appliedSearchCode, currentPage]);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
    setAppliedSearchCode(searchCode.trim());
  };

  const handleResetFilters = () => {
    setSelectedStatus('');
    setSelectedPaymentStatus('');
    setSearchCode('');
    setAppliedSearchCode('');
    setCurrentPage(1);
  };

  const getOrderStatusBadge = (status: OrderStatus) => {
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

  const getPaymentStatusBadge = (status: PaymentStatus) => {
    switch (status) {
      case 'PAID':
        return <Badge variant="success">Đã thanh toán</Badge>;
      case 'UNPAID':
        return <Badge variant="warning">Chưa thanh toán</Badge>;
      case 'PENDING':
        return <Badge variant="info">Đang chờ</Badge>;
      case 'FAILED':
        return <Badge variant="danger">Thất bại</Badge>;
      case 'REVIEW_REQUIRED':
        return <Badge variant="warning">Cần đối soát</Badge>;
      default:
        return <Badge>{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header and Filter Controls */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Package className="w-5 h-5 text-brand-600" />
              <span>Quản Lý Đơn Hàng</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Theo dõi và điều phối vòng đời đơn hàng theo các quy tắc nghiệp vụ NoSQL
            </p>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={fetchOrders}
            loading={loading}
            icon={<RotateCcw className="w-3.5 h-3.5" />}
          >
            Làm mới
          </Button>
        </div>

        {/* Filters Form */}
        <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center gap-3">
          {/* Order Code Search */}
          <form onSubmit={handleSearchSubmit} className="flex items-center gap-2 flex-1 min-w-[240px]">
            <div className="relative flex-1">
              <input
                type="text"
                placeholder="Nhập mã đơn hàng (VD: ORD-6AC...)"
                value={searchCode}
                onChange={(e) => setSearchCode(e.target.value)}
                className="w-full text-xs bg-slate-50 border border-slate-200 rounded-xl pl-9 pr-3 py-2 text-slate-800 placeholder:text-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-500 font-mono"
              />
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
            </div>
            <Button type="submit" variant="primary" size="sm">
              Tìm
            </Button>
          </form>

          {/* Status Filter */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-500 flex items-center gap-1">
              <Filter className="w-3.5 h-3.5" />
              Trạng thái:
            </span>
            <select
              value={selectedStatus}
              onChange={(e) => {
                setSelectedStatus(e.target.value as OrderStatus | '');
                setCurrentPage(1);
              }}
              className="text-xs bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-800 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-100"
            >
              <option value="">Tất cả trạng thái</option>
              <option value="PENDING">PENDING (Chờ xử lý)</option>
              <option value="CONFIRMED">CONFIRMED (Đã xác nhận)</option>
              <option value="SHIPPING">SHIPPING (Đang giao hàng)</option>
              <option value="COMPLETED">COMPLETED (Hoàn thành)</option>
              <option value="CANCELLED">CANCELLED (Đã hủy)</option>
              <option value="EXPIRED">EXPIRED (Hết hạn)</option>
            </select>
          </div>

          {/* Payment Status Filter */}
          <div className="flex items-center gap-2">
            <select
              value={selectedPaymentStatus}
              onChange={(e) => {
                setSelectedPaymentStatus(e.target.value as PaymentStatus | '');
                setCurrentPage(1);
              }}
              className="text-xs bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-800 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-100"
            >
              <option value="">Tất cả thanh toán</option>
              <option value="UNPAID">UNPAID (Chưa thanh toán)</option>
              <option value="PENDING">PENDING (Đang chờ)</option>
              <option value="PAID">PAID (Đã thanh toán)</option>
              <option value="FAILED">FAILED (Thất bại)</option>
              <option value="REVIEW_REQUIRED">REVIEW_REQUIRED (Cần đối soát)</option>
            </select>
          </div>

          {(selectedStatus || selectedPaymentStatus || appliedSearchCode) && (
            <button
              onClick={handleResetFilters}
              className="text-xs text-brand-600 hover:text-brand-800 font-semibold underline px-1"
            >
              Xóa bộ lọc
            </button>
          )}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <div className="font-bold">Lỗi tải danh sách đơn hàng:</div>
            <div className="text-xs mt-0.5">{error}</div>
          </div>
          <Button variant="outline" size="sm" onClick={fetchOrders}>
            Thử lại
          </Button>
        </div>
      )}

      {/* Orders Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200/80 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-3.5 px-4 sm:px-6">Mã Đơn Hàng</th>
                <th className="py-3.5 px-4">Thời Gian Tạo</th>
                <th className="py-3.5 px-4">Hình Thức</th>
                <th className="py-3.5 px-4">Thanh Toán</th>
                <th className="py-3.5 px-4">Trạng Thái Đơn</th>
                <th className="py-3.5 px-4 text-right">Tổng Tiền</th>
                <th className="py-3.5 px-4 sm:px-6 text-center">Thao Tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
              {loading ? (
                Array.from({ length: 6 }).map((_, idx) => (
                  <tr key={idx}>
                    <td className="py-4 px-4 sm:px-6"><Skeleton className="h-4 w-32" /></td>
                    <td className="py-4 px-4"><Skeleton className="h-4 w-24" /></td>
                    <td className="py-4 px-4"><Skeleton className="h-4 w-20" /></td>
                    <td className="py-4 px-4"><Skeleton className="h-4 w-24" /></td>
                    <td className="py-4 px-4"><Skeleton className="h-4 w-24" /></td>
                    <td className="py-4 px-4 text-right"><Skeleton className="h-4 w-20 ml-auto" /></td>
                    <td className="py-4 px-4 sm:px-6 text-center"><Skeleton className="h-6 w-16 mx-auto" /></td>
                  </tr>
                ))
              ) : orders.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    <Package className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                    <span>Không tìm thấy đơn hàng nào phù hợp với bộ lọc.</span>
                  </td>
                </tr>
              ) : (
                orders.map((ord) => (
                  <tr key={ord.id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="py-4 px-4 sm:px-6 font-mono font-bold text-slate-900">
                      <Link
                        to={`/admin/orders/${ord.id}`}
                        className="text-brand-600 hover:text-brand-800 hover:underline flex items-center gap-1.5"
                      >
                        <span>{ord.orderCode}</span>
                        {ord.paymentReviewRequired && (
                          <span title="Cần đối soát thanh toán" className="text-amber-500">
                            <AlertTriangle className="w-3.5 h-3.5" />
                          </span>
                        )}
                      </Link>
                    </td>

                    <td className="py-4 px-4 text-slate-500">
                      {formatDateTime(ord.createdAt)}
                    </td>

                    <td className="py-4 px-4">
                      <div className="flex items-center gap-1.5 font-medium">
                        {ord.paymentMethod === 'COD' ? (
                          <>
                            <Banknote className="w-3.5 h-3.5 text-emerald-600" />
                            <span>COD</span>
                          </>
                        ) : (
                          <>
                            <CreditCard className="w-3.5 h-3.5 text-sky-600" />
                            <span>VNPAY</span>
                          </>
                        )}
                      </div>
                    </td>

                    <td className="py-4 px-4">
                      {getPaymentStatusBadge(ord.paymentStatus)}
                    </td>

                    <td className="py-4 px-4">
                      {getOrderStatusBadge(ord.orderStatus)}
                    </td>

                    <td className="py-4 px-4 text-right font-bold text-slate-900">
                      {formatVND(ord.total)}
                    </td>

                    <td className="py-4 px-4 sm:px-6 text-center">
                      <Link to={`/admin/orders/${ord.id}`}>
                        <Button variant="outline" size="sm" icon={<Eye className="w-3.5 h-3.5" />}>
                          Chi tiết
                        </Button>
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Controls */}
        {!loading && meta.totalPages > 1 && (
          <div className="p-4 border-t border-slate-100 flex justify-center">
            <Pagination
              currentPage={currentPage}
              totalPages={meta.totalPages}
              onPageChange={(page) => setCurrentPage(page)}
            />
          </div>
        )}
      </div>
    </div>
  );
};
