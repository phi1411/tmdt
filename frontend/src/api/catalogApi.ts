import { request } from './client';
import { Category, Product, ProductFilterParams } from '../types/product';
import { ResponseMeta } from '../types/api';

export const catalogApi = {
  getCategories: async (params?: { page?: number; pageSize?: number }): Promise<{ categories: Category[]; meta: ResponseMeta }> => {
    const res = await request<Category[]>('/categories', {
      method: 'GET',
      params: {
        page: params?.page,
        pageSize: params?.pageSize,
      },
    });
    return {
      categories: res.data,
      meta: res.meta,
    };
  },

  getCategoryBySlug: async (slug: string): Promise<Category> => {
    const res = await request<Category>(`/categories/${encodeURIComponent(slug)}`, {
      method: 'GET',
    });
    return res.data;
  },

  getProducts: async (params?: ProductFilterParams): Promise<{ products: Product[]; meta: ResponseMeta }> => {
    const queryParams: Record<string, any> = {};
    if (params) {
      if (params.q) queryParams.q = params.q;
      if (params.categoryId) queryParams.categoryId = params.categoryId;
      if (params.productType) queryParams.productType = params.productType;
      if (params.brand) queryParams.brand = params.brand;
      if (params.minPrice !== undefined && params.minPrice !== null) queryParams.minPrice = params.minPrice;
      if (params.maxPrice !== undefined && params.maxPrice !== null) queryParams.maxPrice = params.maxPrice;
      if (params.size) queryParams.size = params.size;
      if (params.color) queryParams.color = params.color;
      if (params.ram) queryParams.ram = params.ram;
      if (params.capacity) queryParams.capacity = params.capacity;
      if (params.sort) queryParams.sort = params.sort;
      if (params.page) queryParams.page = params.page;
      if (params.pageSize) queryParams.pageSize = params.pageSize;
    }

    const res = await request<Product[]>('/products', {
      method: 'GET',
      params: queryParams,
    });
    return {
      products: res.data,
      meta: res.meta,
    };
  },

  getProductBySlug: async (slug: string): Promise<Product> => {
    const res = await request<Product>(`/products/${encodeURIComponent(slug)}`, {
      method: 'GET',
    });
    return res.data;
  },

  getProductReviews: async (slugOrId: string): Promise<{ reviews: import('../types/product').ProductReview[]; stats?: import('../types/product').RatingSummary }> => {
    const res = await request<{ reviews: import('../types/product').ProductReview[]; stats?: import('../types/product').RatingSummary }>(`/products/${encodeURIComponent(slugOrId)}/reviews`, {
      method: 'GET',
    });
    return res.data;
  },
};
