export type CartIssueType =
  | 'PRODUCT_MISSING'
  | 'PRODUCT_UNAVAILABLE'
  | 'CATEGORY_UNAVAILABLE'
  | 'SELECTION_CHANGED'
  | 'STOCK_CONFLICT';

export interface CartItem {
  lineId: string;
  productId: string;
  name: string | null;
  slug: string | null;
  image: string;
  currentPrice: number | null;
  quantity: number;
  selectedAttributes: Record<string, any>;
  stock: number;
  available: boolean;
  issues: CartIssueType[];
  lineTotal: number;
}

export interface Cart {
  version: number;
  items: CartItem[];
  subtotal: number;
  currency: 'VND';
  issues: CartIssueType[];
  checkoutAllowed: boolean;
}

export interface AddToCartRequest {
  productId: string;
  quantity: number;
  selectedAttributes?: Record<string, any>;
  cartVersion: number;
}

export interface UpdateCartItemRequest {
  quantity: number;
  cartVersion: number;
}

export interface DeleteCartItemRequest {
  cartVersion: number;
}

export interface ClearCartRequest {
  cartVersion: number;
}
