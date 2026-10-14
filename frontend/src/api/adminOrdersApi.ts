import { request } from './client';
import {
  AdminOrder,
  AdminOrderSummary,
  AdminOrderFilterParams,
} from '../types/adminOrder';
import { PaginationMeta } from '../types/api';

export const adminOrdersApi = {
  getList: async (
    params: AdminOrderFilterParams = {}
  ): Promise<{ orders: AdminOrderSummary[]; meta: PaginationMeta }> => {
    const res = await request<AdminOrderSummary[]>('/admin/orders', {
      params: {
        status: params.status,
        paymentStatus: params.paymentStatus,
        orderCode: params.orderCode,
        from: params.from,
        to: params.to,
        page: params.page,
        pageSize: params.pageSize,
      },
    });

    return {
      orders: res.data || [],
      meta: {
        page: res.meta?.page ?? 1,
        pageSize: res.meta?.pageSize ?? 20,
        total: res.meta?.total ?? 0,
        totalPages: res.meta?.totalPages ?? 0,
        requestId: res.meta?.requestId,
      },
    };
  },

  getById: async (id: string): Promise<AdminOrder> => {
    const res = await request<AdminOrder>(`/admin/orders/${id}`);
    return res.data;
  },

  confirm: async (id: string, expectedVersion: number): Promise<AdminOrder> => {
    const res = await request<AdminOrder>(`/admin/orders/${id}/confirm`, {
      method: 'POST',
      body: JSON.stringify({ expectedVersion }),
    });
    return res.data;
  },

  ship: async (id: string, expectedVersion: number): Promise<AdminOrder> => {
    const res = await request<AdminOrder>(`/admin/orders/${id}/ship`, {
      method: 'POST',
      body: JSON.stringify({ expectedVersion }),
    });
    return res.data;
  },

  complete: async (id: string, expectedVersion: number): Promise<AdminOrder> => {
    const res = await request<AdminOrder>(`/admin/orders/${id}/complete`, {
      method: 'POST',
      body: JSON.stringify({ expectedVersion }),
    });
    return res.data;
  },

  cancel: async (id: string, expectedVersion: number): Promise<AdminOrder> => {
    const res = await request<AdminOrder>(`/admin/orders/${id}/cancel`, {
      method: 'POST',
      body: JSON.stringify({ expectedVersion }),
    });
    return res.data;
  },
};
