import { request } from './client';
import {
  AdminCategory,
  AdminCategoryCreate,
  AdminCategoryPatch,
  AdminCategoryFilterParams,
} from '../types/adminCategory';
import { PaginationMeta } from '../types/api';

export const adminCategoriesApi = {
  getList: async (
    params: AdminCategoryFilterParams = {}
  ): Promise<{ categories: AdminCategory[]; meta: PaginationMeta }> => {
    const res = await request<AdminCategory[]>('/admin/categories', {
      params: {
        status: params.status,
        page: params.page,
        pageSize: params.pageSize,
      },
    });

    return {
      categories: res.data || [],
      meta: {
        page: res.meta?.page ?? 1,
        pageSize: res.meta?.pageSize ?? 20,
        total: res.meta?.total ?? 0,
        totalPages: res.meta?.totalPages ?? 0,
        requestId: res.meta?.requestId,
      },
    };
  },

  getById: async (id: string): Promise<AdminCategory> => {
    const res = await request<AdminCategory>(`/admin/categories/${id}`);
    return res.data;
  },

  create: async (data: AdminCategoryCreate): Promise<AdminCategory> => {
    const res = await request<AdminCategory>('/admin/categories', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return res.data;
  },

  update: async (id: string, data: AdminCategoryPatch): Promise<AdminCategory> => {
    const res = await request<AdminCategory>(`/admin/categories/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
    return res.data;
  },

  delete: async (id: string, expectedVersion: number): Promise<void> => {
    await request<void>(`/admin/categories/${id}`, {
      method: 'DELETE',
      body: JSON.stringify({ expectedVersion }),
    });
  },
};
