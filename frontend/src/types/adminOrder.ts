import { Coupon } from './cart';
import {
  OrderStatus,
  PaymentStatus,
  PaymentMethod,
  CustomerSnapshot,
  ShippingAddressSnapshot,
  OrderItemSnapshot,
  OrderSummary,
} from './order';

export type AdminOrderAllowedAction = 'confirm' | 'ship' | 'complete' | 'cancel';

export interface AdminOrder {
  id: string;
  orderCode: string;
  userId: string;
  customerSnapshot: CustomerSnapshot;
  shippingAddress: ShippingAddressSnapshot;
  items: OrderItemSnapshot[];
  subtotal: number;
  shippingFee: number;
  discount: number;
  coupon?: Coupon;
  total: number;
  currency: 'VND';
  paymentMethod: PaymentMethod;
  paymentStatus: PaymentStatus;
  paymentReviewRequired: boolean;
  orderStatus: OrderStatus;
  version: number;
  allowedActions: AdminOrderAllowedAction[];
  createdAt: string;
  updatedAt: string;
  paidAt?: string;
  completedAt?: string;
  cancelledAt?: string;
  expiredAt?: string;
  paymentExpiresAt?: string;
  stockReleasedAt?: string;
}

export type AdminOrderSummary = OrderSummary;

export interface AdminOrderFilterParams {
  status?: OrderStatus;
  paymentStatus?: PaymentStatus;
  orderCode?: string;
  from?: string;
  to?: string;
  page?: number;
  pageSize?: number;
}
