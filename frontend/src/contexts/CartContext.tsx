import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { Cart, CartItem } from '../types/cart';
import { cartApi } from '../api/cartApi';
import { useAuth } from './AuthContext';
import { useToast } from './ToastContext';
import { CustomApiError } from '../types/api';

interface CartContextValue {
  cart: Cart | null;
  loading: boolean;
  itemCount: number;
  refreshCart: () => Promise<Cart | null>;
  addToCart: (productId: string, quantity: number, selectedAttributes?: Record<string, any>) => Promise<boolean>;
  updateQuantity: (lineId: string, quantity: number) => Promise<boolean>;
  removeItem: (lineId: string) => Promise<boolean>;
  clearCart: () => Promise<boolean>;
  setCoupon: (code: string) => Promise<boolean>;
}

const CartContext = createContext<CartContextValue | undefined>(undefined);

export const CartProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [cart, setCart] = useState<Cart | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const { isAuthenticated, isCustomer } = useAuth();
  const { success: toastSuccess, error: toastError, warning: toastWarning } = useToast();

  const refreshCart = useCallback(async (): Promise<Cart | null> => {
    if (!isAuthenticated || !isCustomer) {
      setCart(null);
      return null;
    }

    try {
      setLoading(true);
      const data = await cartApi.getCart();
      setCart(data);
      return data;
    } catch (err: any) {
      // If error is 401 or not customer, ignore
      if (err instanceof CustomApiError && err.status === 401) {
        setCart(null);
      }
      return null;
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, isCustomer]);

  // Refetch cart whenever auth status changes
  useEffect(() => {
    if (isAuthenticated && isCustomer) {
      refreshCart();
    } else {
      setCart(null);
    }
  }, [isAuthenticated, isCustomer, refreshCart]);

  const addToCart = async (
    productId: string,
    quantity: number,
    selectedAttributes?: Record<string, any>
  ): Promise<boolean> => {
    if (!isAuthenticated || !isCustomer) {
      toastWarning('Vui lòng đăng nhập tài khoản khách hàng để thêm vào giỏ hàng.');
      return false;
    }

    try {
      const cartVersion = cart?.version ?? 0;
      const updatedCart = await cartApi.addToCart({
        productId,
        quantity,
        selectedAttributes: selectedAttributes || {},
        cartVersion,
      });
      setCart(updatedCart);
      toastSuccess('Đã thêm sản phẩm vào giỏ hàng!');
      return true;
    } catch (err: any) {
      if (err instanceof CustomApiError) {
        if (err.code === 'CART_CHANGED') {
          toastWarning('Giỏ hàng đã có thay đổi, đang đồng bộ lại...');
          await refreshCart();
        } else if (err.code === 'STOCK_CONFLICT') {
          toastError('Số lượng sản phẩm trong kho không đủ để đáp ứng yêu cầu.');
        } else {
          toastError(err.message || 'Không thể thêm sản phẩm vào giỏ hàng.');
        }
      } else {
        toastError('Lỗi kết nối. Vui lòng thử lại.');
      }
      return false;
    }
  };

  const updateQuantity = async (lineId: string, quantity: number): Promise<boolean> => {
    if (!cart) return false;

    try {
      const updatedCart = await cartApi.updateCartItem(lineId, {
        quantity,
        cartVersion: cart.version,
      });
      setCart(updatedCart);
      return true;
    } catch (err: any) {
      if (err instanceof CustomApiError) {
        if (err.code === 'CART_CHANGED') {
          toastWarning('Giỏ hàng đã có thay đổi, đang đồng bộ lại...');
          await refreshCart();
        } else if (err.code === 'STOCK_CONFLICT') {
          toastError('Số lượng vượt quá tồn kho khả dụng.');
        } else {
          toastError(err.message || 'Không thể cập nhật số lượng.');
        }
      }
      return false;
    }
  };

  const removeItem = async (lineId: string): Promise<boolean> => {
    if (!cart) return false;

    try {
      await cartApi.deleteCartItem(lineId, {
        cartVersion: cart.version,
      });
      toastSuccess('Đã xóa sản phẩm khỏi giỏ hàng.');
      await refreshCart();
      return true;
    } catch (err: any) {
      if (err instanceof CustomApiError && err.code === 'CART_CHANGED') {
        toastWarning('Giỏ hàng đã có thay đổi, đang đồng bộ lại...');
      }
      await refreshCart();
      return false;
    }
  };

  const clearCart = async (): Promise<boolean> => {
    if (!cart) return false;

    try {
      await cartApi.clearCart({
        cartVersion: cart.version,
      });
      toastSuccess('Đã dọn sạch giỏ hàng.');
      await refreshCart();
      return true;
    } catch (err: any) {
      await refreshCart();
      return false;
    }
  };

  const itemCount = cart?.items?.reduce((sum: number, item: CartItem) => sum + item.quantity, 0) || 0;

  const setCoupon = async (code: string): Promise<boolean> => {
    if (!cart) return false;
    try {
      const updated = await cartApi.setCoupon(code, cart.version);
      setCart(updated);
      toastSuccess(code.trim() ? 'Đã áp dụng mã giảm giá.' : 'Đã bỏ mã giảm giá.');
      return true;
    } catch (err: unknown) {
      if (err instanceof CustomApiError) {
        toastError(err.details[0]?.reason || (err.code === 'CART_CHANGED'
          ? 'Giỏ hàng đã thay đổi. Vui lòng thử lại.' : err.message));
      } else {
        toastError('Không thể cập nhật mã giảm giá. Vui lòng thử lại.');
      }
      await refreshCart();
      return false;
    }
  };

  return (
    <CartContext.Provider
      value={{
        cart,
        loading,
        itemCount,
        refreshCart,
        addToCart,
        updateQuantity,
        removeItem,
        clearCart,
        setCoupon,
      }}
    >
      {children}
    </CartContext.Provider>
  );
};

export function useCart() {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error('useCart must be used within CartProvider');
  }
  return context;
}
