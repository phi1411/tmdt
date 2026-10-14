export type UserRole = 'CUSTOMER' | 'ADMIN';
export type UserStatus = 'ACTIVE' | 'BLOCKED';

export interface PublicUser {
  id: string;
  name: string;
  email: string;
  phone?: string | null;
  role: UserRole;
  status: UserStatus;
  version: number;
  createdAt: string;
}

export interface LoginResponse {
  accessToken: string;
  expiresIn: number;
  user: PublicUser;
}

export interface RegisterResponse {
  user: PublicUser;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  name: string;
  email: string;
  password: string;
  phone?: string;
}

export interface ChangePasswordRequest {
  currentPassword: string;
  newPassword: string;
}
