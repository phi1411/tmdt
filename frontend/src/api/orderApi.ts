import { request } from './client';
import { OrderSummary, OrderDetail, CancelOrderRequest, OrderFilterParams } from '../types/order';
import { ResponseMeta } from '../types/api';

export const orderApi = {
  getOrders: async (params?: OrderFilterParams): Promise<{ orders: OrderSummary[]; meta: ResponseMeta }> => {
    const queryParams: Record<string, any> = {};
    if (params) {
      if (params.status) queryParams.status = params.status;
      if (params.from) queryParams.from = params.from;
      if (params.to) queryParams.to = params.to;
      if (params.page) queryParams.page = params.page;
      if (params.pageSize) queryParams.pageSize = params.pageSize;
    }

    const res = await request<OrderSummary[]>('/orders', {
      method: 'GET',
      params: queryParams,
    });
    return {
      orders: res.data,
      meta: res.meta,
    };
  },

  getOrderById: async (id: string): Promise<OrderDetail> => {
    const res = await request<OrderDetail>(`/orders/${encodeURIComponent(id)}`, {
      method: 'GET',
    });
    return res.data;
  },

  getById: async (id: string): Promise<OrderDetail> => {
    return orderApi.getOrderById(id);
  },

  cancelOrder: async (id: string, payload: CancelOrderRequest): Promise<OrderDetail> => {
    const res = await request<OrderDetail>(`/orders/${encodeURIComponent(id)}/cancel`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return res.data;
  },
};
