export interface DashboardReportMetadata {
  currency: string;
  timezone: string;
  from: string;
  to: string;
  revenueBasis: string;
  fetchedAt: string;
}

export interface DashboardSummary extends DashboardReportMetadata {
  totalRevenue: number;
  totalOrders: number;
  totalProductsSold: number;
  totalCustomers: number;
}

export interface RevenuePoint {
  bucket: string;
  revenue: number;
  orders: number;
}

export interface RevenueSeriesResponse extends DashboardReportMetadata {
  series: RevenuePoint[];
  interval: 'day' | 'month';
}

export interface TopProductItem {
  productId: string;
  productName: string;
  quantity: number;
  revenue: number;
}

export interface TopProductsResponse extends DashboardReportMetadata {
  items: TopProductItem[];
}

export interface CategoryRevenueItem {
  categoryId: string;
  categoryName: string;
  revenue: number;
}

export interface CategoryRevenueResponse extends DashboardReportMetadata {
  items: CategoryRevenueItem[];
}

export interface OrderStatusItem {
  status: 'PENDING' | 'CONFIRMED' | 'SHIPPING' | 'COMPLETED' | 'CANCELLED' | 'EXPIRED';
  count: number;
}

export interface OrderStatusResponse extends DashboardReportMetadata {
  items: OrderStatusItem[];
  dateBasis: string;
}

export interface DashboardFilterParams {
  from: string;
  to: string;
  interval?: 'day' | 'month';
}
