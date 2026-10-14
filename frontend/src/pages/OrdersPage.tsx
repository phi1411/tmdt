import React, { useEffect, useState, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Package, Clock, Eye } from 'lucide-react';
import { orderApi } from '../api/orderApi';
import { OrderSummary, OrderStatus } from '../types/order';
import { formatVND, formatDateTime } from '../utils/formatters';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Pagination } from '../components/ui/Pagination';
import { EmptyState } from '../components/ui/EmptyState';
import { ErrorState } from '../components/ui/ErrorState';
import { Skeleton } from '../components/ui/Skeleton';

export const OrdersPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  const [orders, setOrders] = useState<OrderSummary[]>([]);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const statusParam = (searchParams.get('status') as OrderStatus) || '';
  const pageParam = parseInt(searchParams.get('page') || '1', 10);

  const statusTabs: { label: string; value: OrderStatus | '' }[] = [
    { label: 'Tất cả đơn', value: '' },
    { label: 'Chờ xử lý', value: 'PENDING' },
    { label: 'Đã xác nhận', value: 'CONFIRMED' },
    { label: 'Đang giao', value: 'SHIPPING' },
    { label: 'Hoàn thành', value: 'COMPLETED' },
    { label: 'Đã hủy', value: 'CANCELLED' },
    { label: 'Hết hạn', value: 'EXPIRED' },
  ];

  const fetchOrders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await orderApi.getOrders({
        status: statusParam || undefined,
        page: pageParam,
        pageSize: 10,
      });
      setOrders(res.orders);
      setTotalPages(res.meta.totalPages || 1);
      setTotalCount(res.meta.total || 0);
    } catch (err: any) {
      setError(err?.message || 'Không thể tải danh sách đơn hàng.');
    } finally {
      setLoading(false);
    }
  }, [statusParam, pageParam]);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  const handleStatusTabChange = (val: OrderStatus | '') => {
    const next = new URLSearchParams(searchParams);
    if (val) next.set('status', val);
    else next.delete('status');
    next.set('page', '1');
    setSearchParams(next);
  };

  const handlePageChange = (newPage: number) => {
    const next = new URLSearchParams(searchParams);
    next.set('page', String(newPage));
    setSearchParams(next);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

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

  const getPaymentStatusBadge = (status: string) => {
    switch (status) {
      case 'PAID':
        return <span className="text-emerald-700 font-medium">Đã thanh toán</span>;
      case 'UNPAID':
        return <span className="text-amber-700 font-medium">Chưa thanh toán (COD)</span>;
      case 'PENDING':
        return <span className="text-sky-700 font-medium">Chờ thanh toán</span>;
      case 'FAILED':
        return <span className="text-rose-700 font-medium">Thất bại</span>;
      default:
        return <span className="text-slate-600 font-medium">{status}</span>;
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-8 shadow-sm space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Lịch Sử Đơn Hàng
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Tổng cộng <span className="font-semibold text-slate-800">{totalCount}</span> đơn hàng đã đặt
          </p>
        </div>
      </div>

      {/* Status Filter Tabs */}
      <div className="flex gap-2 overflow-x-auto pb-2 border-b border-slate-100">
        {statusTabs.map((tab) => {
          const isActive = statusParam === tab.value;
          return (
            <button
              key={tab.value}
              onClick={() => handleStatusTabChange(tab.value)}
              className={`px-3.5 py-2 text-xs font-semibold rounded-xl whitespace-nowrap transition-colors ${
                isActive
                  ? 'bg-brand-600 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200 hover:text-slate-900'
              }`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Orders List */}
      {error ? (
        <ErrorState message={error} onRetry={fetchOrders} />
      ) : loading ? (
        <div className="space-y-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full rounded-2xl" />
          ))}
        </div>
      ) : orders.length === 0 ? (
        <EmptyState
          icon={<Package className="w-8 h-8" />}
          title="Chưa có đơn hàng nào"
          description="Bạn chưa có đơn hàng nào ở trạng thái này."
          actionLabel="Bắt đầu mua sắm"
          onAction={() => (window.location.href = '/products')}
        />
      ) : (
        <div className="space-y-4">
          {orders.map((order) => (
            <div
              key={order.id}
              className="p-5 rounded-2xl border border-slate-200 hover:border-slate-300 transition-all bg-white hover:shadow-xs space-y-3"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-100 text-xs">
                <div className="flex items-center gap-3">
                  <span className="font-mono font-bold text-slate-900 text-sm">{order.orderCode}</span>
                  {getOrderStatusBadge(order.orderStatus)}
                </div>
                <div className="text-slate-400 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5" />
                  <span>{formatDateTime(order.createdAt)}</span>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-1">
                <div className="text-xs space-y-1">
                  <div>
                    <span className="text-slate-500">Hình thức: </span>
                    <span className="font-semibold text-slate-800">
                      {order.paymentMethod === 'COD' ? 'Thanh toán khi nhận hàng (COD)' : 'VNPAY Online'}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500">Thanh toán: </span>
                    {getPaymentStatusBadge(order.paymentStatus)}
                  </div>
                </div>

                <div className="flex items-center justify-between sm:justify-end gap-4">
                  <div className="text-right">
                    <span className="text-xs text-slate-400 block">Tổng tiền</span>
                    <span className="text-base font-bold text-brand-700">
                      {formatVND(order.total)}
                    </span>
                  </div>

                  <Link to={`/orders/${order.id}`}>
                    <Button variant="outline" size="sm" icon={<Eye className="w-3.5 h-3.5" />}>
                      Chi tiết
                    </Button>
                  </Link>
                </div>
              </div>
            </div>
          ))}

          {/* Pagination */}
          <Pagination
            currentPage={pageParam}
            totalPages={totalPages}
            onPageChange={handlePageChange}
            className="pt-4"
          />
        </div>
      )}
    </div>
  );
};
