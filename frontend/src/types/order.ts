export type OrderStatus =
  | 'PENDING'
  | 'CONFIRMED'
  | 'SHIPPING'
  | 'COMPLETED'
  | 'CANCELLED'
  | 'EXPIRED';

export type PaymentStatus =
  | 'UNPAID'
  | 'PENDING'
  | 'PAID'
  | 'FAILED'
  | 'REVIEW_REQUIRED';

export type PaymentMethod = 'COD' | 'VNPAY';

export interface CustomerSnapshot {
  name: string;
  phone: string;
  email: string;
}

export interface ShippingAddressSnapshot {
  receiverName: string;
  phone: string;
  addressLine: string;
  province: string;
  ward?: string;
  district?: string;
}

export interface OrderItemSnapshot {
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
}

export interface OrderSummary {
  id: string;
  orderCode: string;
  orderStatus: OrderStatus;
  paymentStatus: PaymentStatus;
  paymentMethod: PaymentMethod;
  paymentReviewRequired?: boolean;
  total: number;
  currency: 'VND';
  version: number;
  createdAt: string;
  updatedAt: string;
}

export interface OrderDetail extends OrderSummary {
  userId: string;
  customerSnapshot: CustomerSnapshot;
  shippingAddress: ShippingAddressSnapshot;
  items: OrderItemSnapshot[];
  subtotal: number;
  shippingFee: number;
  discount: number;
  paidAt?: string | null;
  completedAt?: string | null;
  cancelledAt?: string | null;
  stockReleasedAt?: string | null;
  paymentExpiresAt?: string | null;
}

export interface CancelOrderRequest {
  expectedVersion: number;
}

export interface OrderFilterParams {
  status?: OrderStatus;
  from?: string;
  to?: string;
  page?: number;
  pageSize?: number;
}
