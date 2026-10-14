import { request } from './client';
import { CustomApiError } from '../types/api';
import { PaymentAttemptResult, VnpayReturnResult } from '../types/payment';
import { generateIdempotencyKey } from '../utils/idempotency';

// Keep the same retry intent until its post-commit URL is recovered.
const pendingKeys = new Map<string, string>();

export const paymentApi = {
  createPaymentAttempt: async (
    orderId: string,
    expectedVersion: number
  ): Promise<PaymentAttemptResult> => {
    const intent = `${orderId}:${expectedVersion}`;
    const idempotencyKey = pendingKeys.get(intent) || generateIdempotencyKey();
    pendingKeys.set(intent, idempotencyKey);
    try {
      const res = await request<PaymentAttemptResult>(
        `/orders/${orderId}/payment-attempts`,
        {
          method: 'POST',
          idempotencyKey,
          body: JSON.stringify({ expectedVersion }),
        }
      );
      if (res.data.paymentUrl || (!res.data.retryRequired && res.data.attemptStatus !== 'PENDING')) pendingKeys.delete(intent);
      return res.data;
    } catch (error) {
      if (error instanceof CustomApiError && error.status >= 400 && error.status < 500) pendingKeys.delete(intent);
      throw error;
    }
  },

  verifyReturn: async (queryString: string): Promise<VnpayReturnResult> => {
    const cleanQuery = queryString.startsWith('?') ? queryString.slice(1) : queryString;
    const url = `/payments/vnpay/return${cleanQuery ? `?${cleanQuery}` : ''}`;
    const res = await request<VnpayReturnResult>(url);
    return res.data;
  },
};
