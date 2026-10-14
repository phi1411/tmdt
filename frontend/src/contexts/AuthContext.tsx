import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { PublicUser, LoginRequest, RegisterRequest } from '../types/auth';
import { authApi } from '../api/authApi';
import { setClientToken, setOnUnauthenticated } from '../api/client';
import { useToast } from './ToastContext';

interface AuthContextValue {
  user: PublicUser | null;
  loading: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isCustomer: boolean;
  login: (credentials: LoginRequest) => Promise<PublicUser>;
  register: (payload: RegisterRequest) => Promise<PublicUser>;
  logout: () => void;
  refreshUser: () => Promise<PublicUser | null>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const TOKEN_STORAGE_KEY = 'novamart_auth_token';

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<PublicUser | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const { error: toastError } = useToast();

  const logout = useCallback(() => {
    sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    setClientToken(null);
    setUser(null);
  }, []);

  // Listen to 401 unauthenticated events from API client
  useEffect(() => {
    setOnUnauthenticated(() => {
      logout();
      toastError('Phiên đăng nhập đã hết hạn hoặc không hợp lệ. Vui lòng đăng nhập lại.');
    });
  }, [logout, toastError]);

  // Initial authentication check
  useEffect(() => {
    const initializeAuth = async () => {
      const storedToken = sessionStorage.getItem(TOKEN_STORAGE_KEY);
      if (!storedToken) {
        setLoading(false);
        return;
      }

      setClientToken(storedToken);
      try {
        const currentUser = await authApi.getMe();
        setUser(currentUser);
      } catch (err) {
        // Token invalid or expired
        sessionStorage.removeItem(TOKEN_STORAGE_KEY);
        setClientToken(null);
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    initializeAuth();
  }, []);

  const login = async (credentials: LoginRequest): Promise<PublicUser> => {
    const response = await authApi.login(credentials);
    sessionStorage.setItem(TOKEN_STORAGE_KEY, response.accessToken);
    setClientToken(response.accessToken);
    setUser(response.user);
    return response.user;
  };

  const register = async (payload: RegisterRequest): Promise<PublicUser> => {
    const response = await authApi.register(payload);
    return response.user;
  };

  const refreshUser = async (): Promise<PublicUser | null> => {
    try {
      const currentUser = await authApi.getMe();
      setUser(currentUser);
      return currentUser;
    } catch {
      return null;
    }
  };

  const isAuthenticated = !!user;
  const isAdmin = user?.role === 'ADMIN';
  const isCustomer = user?.role === 'CUSTOMER';

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAuthenticated,
        isAdmin,
        isCustomer,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
