import type { VnpayReturnResult } from '../types/payment';
import type { OrderDetail } from '../types/order';

export function paymentViewStatus(result: VnpayReturnResult | null, order: OrderDetail | null) {
  if (!result?.verified) return { status: result?.result || 'FAILED', needsReview: false };
  const current = order?.id === result.orderId ? order : null;
  const needsReview = Boolean(current?.paymentReviewRequired || result.paymentReviewRequired);
  const paid = current ? current.paymentStatus === 'PAID' : result.confirmed;
  const failed = current && (current.paymentStatus === 'FAILED' || ['CANCELLED', 'EXPIRED'].includes(current.orderStatus));
  return { status: paid ? 'SUCCESS' : failed && !needsReview ? 'FAILED' : needsReview ? 'PENDING' : result.result, needsReview };
}
