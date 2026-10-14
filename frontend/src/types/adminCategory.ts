import { ProductType } from './product';

export type CategoryStatus = 'ACTIVE' | 'ARCHIVED';

export interface AdminCategory {
  id: string;
  name: string;
  slug: string;
  productType: ProductType;
  description?: string;
  status: CategoryStatus;
  version: number;
  createdAt: string;
  updatedAt: string;
}

export interface AdminCategoryCreate {
  name: string;
  slug: string;
  productType: ProductType;
  description?: string;
}

export interface AdminCategoryPatch {
  name?: string;
  slug?: string;
  description?: string;
  status?: CategoryStatus;
  productType?: ProductType;
  expectedVersion: number;
}

export interface AdminCategoryFilterParams {
  status?: CategoryStatus;
  page?: number;
  pageSize?: number;
}
