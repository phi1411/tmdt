import { request } from './client';
import { CheckoutQuote, CreateOrderRequest, OrderCreateResponse } from '../types/checkout';

export const checkoutApi = {
  getCheckoutQuote: async (addressId: string, paymentMethod: 'COD' | 'VNPAY'): Promise<CheckoutQuote> => {
    const res = await request<CheckoutQuote>('/checkout/quote', {
      method: 'GET',
      params: {
        addressId,
        paymentMethod,
      },
    });
    return res.data;
  },

  createOrder: async (payload: CreateOrderRequest, idempotencyKey: string): Promise<OrderCreateResponse> => {
    const res = await request<OrderCreateResponse>('/orders', {
      method: 'POST',
      body: JSON.stringify(payload),
      idempotencyKey,
    });
    return res.data;
  },
};
