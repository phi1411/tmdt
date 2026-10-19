import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useLocation, Link } from 'react-router-dom';
import { paymentApi } from '../api/paymentApi';
import { orderApi } from '../api/orderApi';
import { VnpayReturnResult } from '../types/payment';
import { OrderDetail } from '../types/order';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { formatVND } from '../utils/formatters';
import { paymentViewStatus } from '../utils/paymentStatus';
import { Button } from '../components/ui/Button';
import {
  CheckCircle,
  XCircle,
  Clock,
  ShieldAlert,
  AlertTriangle,
  RotateCcw,
  ShoppingBag,
  ArrowRight,
  Loader2,
} from 'lucide-react';

export const PaymentReturnPage: React.FC = () => {
  const location = useLocation();
  const { isAuthenticated } = useAuth();
  const { success: toastSuccess, error: toastError, warning: toastWarning } = useToast();

  const [loading, setLoading] = useState<boolean>(true);
  const [returnResult, setReturnResult] = useState<VnpayReturnResult | null>(null);
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [polling, setPolling] = useState<boolean>(false);
  const [retrying, setRetrying] = useState<boolean>(false);
  const [verificationError, setVerificationError] = useState(false);
  const verificationGeneration = useRef(0);

  const verifyPayment = useCallback(async () => {
    const generation = ++verificationGeneration.current;
    setLoading(true);
    setVerificationError(false);
    setReturnResult(null);
    setOrder(null);
    try {
      const res = await paymentApi.verifyReturn(location.search);
      if (generation !== verificationGeneration.current) return;
      setReturnResult(res);

      // If orderId is available and user is authenticated, fetch live order state
      if (res.orderId && isAuthenticated) {
        try {
          const ord = await orderApi.getById(res.orderId);
          if (generation !== verificationGeneration.current) return;
          setOrder(ord);
        } catch {
          // Soft fail for order fetch
        }
      }
    } catch (err: any) {
      if (generation !== verificationGeneration.current) return;
      setVerificationError(true);
      toastError(err?.message || 'Không thể xác thực kết quả thanh toán từ máy chủ.');
    } finally {
      if (generation === verificationGeneration.current) setLoading(false);
    }
  }, [location.search, isAuthenticated, toastError]);

  useEffect(() => {
    verifyPayment();
    return () => { verificationGeneration.current += 1; };
  }, [verifyPayment]);

  // Poll order state when pending
  const handlePollOrder = async () => {
    if (!returnResult?.orderId) return;
    const generation = verificationGeneration.current;
    setPolling(true);
    try {
      const updatedOrder = await orderApi.getById(returnResult.orderId);
      if (generation !== verificationGeneration.current) return;
      setOrder(updatedOrder);

      if (updatedOrder.paymentReviewRequired) {
        toastWarning('Giao dịch cần quản trị viên đối soát thêm.');
      } else if (updatedOrder.paymentStatus === 'PAID') {
        toastSuccess('Đơn hàng đã được xác nhận thanh toán thành công!');
      } else {
        toastWarning(`Trạng thái hiện tại: ${updatedOrder.paymentStatus} / ${updatedOrder.orderStatus}`);
      }
    } catch (err: any) {
      toastError(err?.message || 'Không thể kiểm tra trạng thái đơn hàng.');
    } finally {
      setPolling(false);
    }
  };

  // Retry payment attempt for failed online order
  const handleRetryPayment = async () => {
    if (!order) return;
    setRetrying(true);
    try {
      const attempt = await paymentApi.createPaymentAttempt(order.id, order.version);
      if (attempt.paymentUrl) {
        toastSuccess('Đang chuyển hướng tới cổng thanh toán VNPAY...');
        window.location.href = attempt.paymentUrl;
      } else {
        toastWarning('Chưa khởi tạo được URL thanh toán ngay. Vui lòng thử lại sau.');
      }
    } catch (err: any) {
      toastError(err?.message || 'Không thể tạo phiên thanh toán mới.');
    } finally {
      setRetrying(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-xl mx-auto my-20 p-8 bg-white rounded-3xl border border-slate-200 text-center shadow-sm space-y-4">
        <Loader2 className="w-10 h-10 text-brand-600 animate-spin mx-auto" />
        <h2 className="text-lg font-bold text-slate-900">Đang Xác Thực Kết Quả Giao Dịch</h2>
        <p className="text-xs text-slate-500">
          Hệ thống đang kiểm tra chữ ký số và đối soát thông tin với cổng thanh toán VNPAY...
        </p>
      </div>
    );
  }

  if (verificationError) {
    return (
      <div role="alert" className="max-w-xl mx-auto my-16 p-8 bg-white rounded-2xl border border-amber-200 text-center space-y-4">
        <h1 className="text-xl font-bold">Chưa xác minh được giao dịch</h1>
        <p>Không thể kết nối để kiểm tra kết quả. Bạn có thể thử lại hoặc xem trạng thái trong đơn hàng.</p>
        <Button onClick={verifyPayment}>Thử lại xác minh</Button>
        <Link to="/orders" className="block text-brand-700">Xem đơn hàng của tôi</Link>
      </div>
    );
  }

  const { status: resultStatus, needsReview } = paymentViewStatus(returnResult, order);
  const isConfirmed = resultStatus === 'SUCCESS';

  return (
    <div className="max-w-2xl mx-auto my-12 px-4 space-y-6">
      {/* Main Result Card */}
      <div className="bg-white rounded-3xl border border-slate-200/80 p-8 sm:p-10 shadow-sm text-center space-y-6">
        {/* Status Icon */}
        {resultStatus === 'SUCCESS' || isConfirmed ? (
          <div className="w-16 h-16 bg-emerald-50 text-emerald-600 rounded-3xl flex items-center justify-center mx-auto shadow-inner">
            <CheckCircle className="w-10 h-10" />
          </div>
        ) : resultStatus === 'PENDING' ? (
          <div className="w-16 h-16 bg-amber-50 text-amber-600 rounded-3xl flex items-center justify-center mx-auto shadow-inner">
            <Clock className="w-10 h-10" />
          </div>
        ) : resultStatus === 'INVALID_SIGNATURE' || resultStatus === 'INVALID_RESPONSE' ? (
          <div className="w-16 h-16 bg-amber-50 text-amber-600 rounded-3xl flex items-center justify-center mx-auto shadow-inner">
            <ShieldAlert className="w-10 h-10" />
          </div>
        ) : (
          <div className="w-16 h-16 bg-rose-50 text-rose-600 rounded-3xl flex items-center justify-center mx-auto shadow-inner">
            <XCircle className="w-10 h-10" />
          </div>
        )}

        {/* Title & Description */}
        <div className="space-y-2">
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            {resultStatus === 'SUCCESS' || isConfirmed
              ? 'Thanh Toán Thành Công!'
              : resultStatus === 'PENDING'
              ? 'Giao Dịch Đang Chờ Xác Nhận'
              : resultStatus === 'INVALID_SIGNATURE' || resultStatus === 'INVALID_RESPONSE'
              ? 'Chữ Ký Không Hợp Lệ'
              : 'Thanh Toán Chưa Thành Công'}
          </h1>

          <p className="text-sm text-slate-600 max-w-md mx-auto leading-relaxed">
            {resultStatus === 'SUCCESS' || isConfirmed
              ? 'Đơn hàng của bạn đã được ghi nhận thanh toán hoàn tất qua cổng VNPAY Sandbox. Chúng tôi sẽ sớm tiến hành đóng gói và giao hàng.'
              : resultStatus === 'PENDING'
              ? 'Giao dịch đang chờ xác nhận từ VNPAY và ngân hàng. Bấm Kiểm tra lại trạng thái để lấy kết quả mới nhất.'
              : resultStatus === 'INVALID_SIGNATURE' || resultStatus === 'INVALID_RESPONSE'
              ? 'Chữ ký số hoặc định dạng phản hồi từ cổng thanh toán không khớp với dữ liệu bảo mật được ký duyệt.'
              : 'Giao dịch qua cổng VNPAY đã bị hủy hoặc không thành công từ phía ngân hàng phát hành thẻ.'}
          </p>
        </div>

        {/* Review Required Warning */}
        {needsReview && (
          <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-start gap-2.5 text-left">
            <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-bold">Lưu ý đối soát: </span>
              <span>
                Giao dịch này đã được ghi nhận nhưng cần quản trị viên đối soát thêm với ngân hàng do cập nhật sau mốc thời gian quy định.
              </span>
            </div>
          </div>
        )}

        {/* Transaction Summary Details */}
        <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200/60 text-xs space-y-2.5 text-slate-700 text-left max-w-md mx-auto">
          {order && (
            <div className="flex justify-between">
              <span className="text-slate-400">Mã đơn hàng:</span>
              <span className="font-mono font-bold text-slate-900">{order.orderCode}</span>
            </div>
          )}

          {returnResult?.attemptId && (
            <div className="flex justify-between">
              <span className="text-slate-400">Mã phiên (Attempt ID):</span>
              <span className="font-mono text-slate-600 truncate max-w-[200px]" title={returnResult.attemptId}>
                {returnResult.attemptId}
              </span>
            </div>
          )}

          {order && (
            <div className="flex justify-between">
              <span className="text-slate-400">Tổng thanh toán:</span>
              <span className="font-bold text-brand-700 text-sm">{formatVND(order.total)}</span>
            </div>
          )}

          <div className="flex justify-between">
            <span className="text-slate-400">Phương thức:</span>
            <span className="font-semibold text-slate-800">VNPAY Sandbox (Online)</span>
          </div>

          <div className="flex justify-between">
            <span className="text-slate-400">Trạng thái thanh toán:</span>
            <span className="font-bold text-slate-900">
              {order?.paymentStatus || returnResult?.paymentStatus || resultStatus}
            </span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
          {resultStatus === 'PENDING' && (
            <Button
              variant="outline"
              size="md"
              loading={polling}
              onClick={handlePollOrder}
              icon={<RotateCcw className="w-4 h-4" />}
            >
              Kiểm tra lại trạng thái
            </Button>
          )}

          {resultStatus === 'FAILED' && order && order.paymentMethod === 'VNPAY' &&
            order.orderStatus === 'PENDING' && order.paymentStatus === 'FAILED' &&
            !order.paymentReviewRequired && !!order.paymentExpiresAt && Date.parse(order.paymentExpiresAt) > Date.now() && (
            <Button
              variant="primary"
              size="md"
              loading={retrying}
              onClick={handleRetryPayment}
              icon={<RotateCcw className="w-4 h-4" />}
            >
              Thử lại thanh toán
            </Button>
          )}

          {order ? (
            <Link to={`/orders/${order.id}`}>
              <Button variant="primary" size="md" icon={<ArrowRight className="w-4 h-4" />}>
                Xem chi tiết đơn hàng
              </Button>
            </Link>
          ) : (
            <Link to="/orders">
              <Button variant="primary" size="md">
                Về danh sách đơn hàng
              </Button>
            </Link>
          )}

          <Link to="/">
            <Button variant="outline" size="md" icon={<ShoppingBag className="w-4 h-4" />}>
              Tiếp tục mua sắm
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
};
