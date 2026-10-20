import { request } from './client';
import {
  Cart,
  AddToCartRequest,
  UpdateCartItemRequest,
  DeleteCartItemRequest,
  ClearCartRequest,
} from '../types/cart';

export const cartApi = {
  setCoupon: async (code: string, cartVersion: number): Promise<Cart> => {
    const res = await request<Cart>('/cart/coupon', {
      method: 'PATCH', body: JSON.stringify({ code, cartVersion }),
    });
    return res.data;
  },
  getCart: async (): Promise<Cart> => {
    const res = await request<Cart>('/cart', {
      method: 'GET',
    });
    return res.data;
  },

  addToCart: async (payload: AddToCartRequest): Promise<Cart> => {
    const res = await request<Cart>('/cart/items', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return res.data;
  },

  updateCartItem: async (lineId: string, payload: UpdateCartItemRequest): Promise<Cart> => {
    const res = await request<Cart>(`/cart/items/${encodeURIComponent(lineId)}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
    return res.data;
  },

  deleteCartItem: async (lineId: string, payload: DeleteCartItemRequest): Promise<void> => {
    await request<void>(`/cart/items/${encodeURIComponent(lineId)}`, {
      method: 'DELETE',
      body: JSON.stringify(payload),
    });
  },

  clearCart: async (payload: ClearCartRequest): Promise<void> => {
    await request<void>('/cart', {
      method: 'DELETE',
      body: JSON.stringify(payload),
    });
  },
};
