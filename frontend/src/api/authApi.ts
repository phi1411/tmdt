import { request } from './client';
import { LoginRequest, LoginResponse, RegisterRequest, RegisterResponse, PublicUser, ChangePasswordRequest } from '../types/auth';

export const authApi = {
  login: async (credentials: LoginRequest): Promise<LoginResponse> => {
    const res = await request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
    return res.data;
  },

  register: async (payload: RegisterRequest): Promise<RegisterResponse> => {
    const res = await request<RegisterResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return res.data;
  },

  getMe: async (): Promise<PublicUser> => {
    const res = await request<PublicUser>('/auth/me', {
      method: 'GET',
    });
    return res.data;
  },

  changePassword: async (payload: ChangePasswordRequest): Promise<{ reauthenticationRequired: boolean }> => {
    const res = await request<{ reauthenticationRequired: boolean }>('/auth/password', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
    return res.data;
  },
};
