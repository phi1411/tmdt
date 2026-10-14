import { request } from './client';
import {
  AdminProduct,
  AdminProductCreate,
  AdminProductPatch,
  AdminProductFilterParams,
} from '../types/adminProduct';
import { PaginationMeta } from '../types/api';

export const adminProductsApi = {
  getList: async (
    params: AdminProductFilterParams = {}
  ): Promise<{ products: AdminProduct[]; meta: PaginationMeta }> => {
    const res = await request<AdminProduct[]>('/admin/products', {
      params: {
        q: params.q,
        categoryId: params.categoryId,
        status: params.status,
        page: params.page,
        pageSize: params.pageSize,
        sort: params.sort,
      },
    });

    return {
      products: res.data || [],
      meta: {
        page: res.meta?.page ?? 1,
        pageSize: res.meta?.pageSize ?? 20,
        total: res.meta?.total ?? 0,
        totalPages: res.meta?.totalPages ?? 0,
        requestId: res.meta?.requestId,
      },
    };
  },

  getById: async (id: string): Promise<AdminProduct> => {
    const res = await request<AdminProduct>(`/admin/products/${id}`);
    return res.data;
  },

  create: async (data: AdminProductCreate): Promise<AdminProduct> => {
    const res = await request<AdminProduct>('/admin/products', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return res.data;
  },

  update: async (id: string, data: AdminProductPatch): Promise<AdminProduct> => {
    const res = await request<AdminProduct>(`/admin/products/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
    return res.data;
  },

  archive: async (id: string, expectedVersion: number): Promise<void> => {
    await request<void>(`/admin/products/${id}`, {
      method: 'DELETE',
      body: JSON.stringify({ expectedVersion }),
    });
  },
};
