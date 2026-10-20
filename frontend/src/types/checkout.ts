import { OrderDetail } from './order';
import { Coupon } from './cart';

export interface QuoteItem {
  productId: string;
  sku: string;
  productName: string;
  image: string;
  productType: string;
  categoryId: string;
  categoryName: string;
  attributesSnapshot: Record<string, any>;
  selectedAttributes: Record<string, any>;
  priceAtPurchase: number;
  quantity: number;
  lineTotal: number;
  discountAllocated?: number;
}

export interface CheckoutQuote {
  cartVersion: number;
  items: QuoteItem[];
  subtotal: number;
  shippingFee: number;
  discount: number;
  coupon?: Coupon;
  total: number;
  currency: 'VND';
  quoteToken: string;
  expiresAt: string;
  issues: string[];
}

export interface CreateOrderRequest {
  cartVersion: number;
  addressId: string;
  paymentMethod: 'COD' | 'VNPAY';
  quoteToken: string;
}

export interface OrderCreateResponse {
  order: OrderDetail;
  payment: {
    method: 'COD' | 'VNPAY';
    attemptId?: string;
    paymentUrl?: string;
    expiresAt?: string;
    retryRequired?: boolean;
  };
}
