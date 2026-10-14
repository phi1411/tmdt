import { request } from './client';
import {
  PublicProfile,
  UpdateProfileRequest,
  CreateAddressRequest,
  UpdateAddressRequest,
  DeleteAddressRequest,
  SetDefaultAddressRequest,
  Address,
} from '../types/user';

export const userApi = {
  getProfile: async (): Promise<PublicProfile> => {
    const res = await request<PublicProfile>('/users/me', {
      method: 'GET',
    });
    return res.data;
  },

  updateProfile: async (payload: UpdateProfileRequest): Promise<PublicProfile> => {
    const res = await request<PublicProfile>('/users/me', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
    return res.data;
  },

  createAddress: async (payload: CreateAddressRequest): Promise<{ address: Address; version: number }> => {
    const res = await request<{ address: Address; version: number }>('/users/me/addresses', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return res.data;
  },

  updateAddress: async (
    addressId: string,
    payload: UpdateAddressRequest
  ): Promise<{ address: Address; version: number }> => {
    const res = await request<{ address: Address; version: number }>(`/users/me/addresses/${addressId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
    return res.data;
  },

  deleteAddress: async (addressId: string, payload: DeleteAddressRequest): Promise<void> => {
    await request<void>(`/users/me/addresses/${addressId}`, {
      method: 'DELETE',
      body: JSON.stringify(payload),
    });
  },

  setDefaultAddress: async (
    payload: SetDefaultAddressRequest
  ): Promise<{ defaultAddressId: string; version: number }> => {
    const res = await request<{ defaultAddressId: string; version: number }>('/users/me/default-address', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
    return res.data;
  },
};
