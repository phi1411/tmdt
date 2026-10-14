import { PublicUser } from './auth';

export interface Address {
  id: string;
  receiverName: string;
  phone: string;
  addressLine: string;
  province: string;
  ward?: string;
  district?: string;
  label?: string;
}

export interface PublicProfile extends PublicUser {
  addresses: Address[];
  defaultAddressId: string | null;
  updatedAt: string;
}

export interface UpdateProfileRequest {
  name?: string;
  phone?: string;
  expectedVersion: number;
}

export interface CreateAddressRequest {
  receiverName: string;
  phone: string;
  addressLine: string;
  province: string;
  ward?: string;
  district?: string;
  label?: string;
  expectedVersion: number;
}

export interface UpdateAddressRequest {
  receiverName?: string;
  phone?: string;
  addressLine?: string;
  province?: string;
  ward?: string;
  district?: string;
  label?: string;
  expectedVersion: number;
}

export interface DeleteAddressRequest {
  expectedVersion: number;
}

export interface SetDefaultAddressRequest {
  addressId: string;
  expectedVersion: number;
}
