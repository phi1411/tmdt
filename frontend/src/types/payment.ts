export interface PaymentAttemptResult {
  attemptId: string;
  attemptStatus: string;
  expiresAt: string;
  orderVersion?: number;
  paymentUrl?: string;
  retryRequired?: boolean;
}

export interface VnpayReturnResult {
  result: 'SUCCESS' | 'FAILED' | 'PENDING' | 'INVALID_SIGNATURE' | 'INVALID_RESPONSE';
  providerResult?: 'SUCCESS' | 'FAILED';
  verified: boolean;
  confirmed: boolean;
  authoritative: boolean;
  orderId?: string;
  attemptId?: string;
  paymentStatus?: string;
  orderStatus?: string;
  paymentReviewRequired?: boolean;
}

export interface CreateOrderPaymentResponse {
  method: 'COD' | 'VNPAY';
  attemptId?: string;
  attemptStatus?: string;
  expiresAt?: string;
  paymentUrl?: string;
  retryRequired?: boolean;
}
