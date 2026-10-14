import { request } from './client';
import {
  DashboardSummary,
  RevenueSeriesResponse,
  TopProductsResponse,
  CategoryRevenueResponse,
  OrderStatusResponse,
  DashboardFilterParams,
} from '../types/dashboard';

export const dashboardApi = {
  getSummary: async (params: { from: string; to: string }): Promise<DashboardSummary> => {
    const res = await request<DashboardSummary>('/admin/dashboard/summary', {
      params: { from: params.from, to: params.to },
    });
    return res.data;
  },

  getRevenue: async (params: DashboardFilterParams): Promise<RevenueSeriesResponse> => {
    const res = await request<RevenueSeriesResponse>('/admin/dashboard/revenue', {
      params: {
        from: params.from,
        to: params.to,
        interval: params.interval || 'day',
      },
    });
    return res.data;
  },

  getTopProducts: async (params: { from: string; to: string }): Promise<TopProductsResponse> => {
    const res = await request<TopProductsResponse>('/admin/dashboard/top-products', {
      params: { from: params.from, to: params.to },
    });
    return res.data;
  },

  getCategoryRevenue: async (params: { from: string; to: string }): Promise<CategoryRevenueResponse> => {
    const res = await request<CategoryRevenueResponse>('/admin/dashboard/category-revenue', {
      params: { from: params.from, to: params.to },
    });
    return res.data;
  },

  getOrderStatus: async (params: { from: string; to: string }): Promise<OrderStatusResponse> => {
    const res = await request<OrderStatusResponse>('/admin/dashboard/order-status', {
      params: { from: params.from, to: params.to },
    });
    return res.data;
  },
};
