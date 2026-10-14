export interface AdminUser {
  id: string;
  name: string;
  email: string;
  phone?: string;
  role: 'CUSTOMER' | 'ADMIN';
  status: 'ACTIVE' | 'BLOCKED';
  version: number;
  createdAt: string;
}

export interface AdminUserFilterParams {
  q?: string;
  role?: 'CUSTOMER' | 'ADMIN';
  status?: 'ACTIVE' | 'BLOCKED';
  page?: number;
  pageSize?: number;
}

export interface AdminUserStatusPayload {
  status: 'ACTIVE' | 'BLOCKED';
  expectedVersion: number;
}
