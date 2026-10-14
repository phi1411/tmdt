import { request } from './client';
import {
  AdminUser,
  AdminUserFilterParams,
  AdminUserStatusPayload,
} from '../types/adminUser';
import { PaginationMeta } from '../types/api';

export const adminUsersApi = {
  getList: async (
    params: AdminUserFilterParams = {}
  ): Promise<{ users: AdminUser[]; meta: PaginationMeta }> => {
    const res = await request<AdminUser[]>('/admin/users', {
      params: {
        q: params.q,
        role: params.role,
        status: params.status,
        page: params.page,
        pageSize: params.pageSize,
      },
    });

    return {
      users: res.data || [],
      meta: {
        page: res.meta?.page ?? 1,
        pageSize: res.meta?.pageSize ?? 20,
        total: res.meta?.total ?? 0,
        totalPages: res.meta?.totalPages ?? 0,
        requestId: res.meta?.requestId,
      },
    };
  },

  getById: async (id: string): Promise<AdminUser> => {
    const res = await request<AdminUser>(`/admin/users/${id}`);
    return res.data;
  },

  updateStatus: async (
    id: string,
    payload: AdminUserStatusPayload
  ): Promise<AdminUser> => {
    const res = await request<AdminUser>(`/admin/users/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
    return res.data;
  },
};
