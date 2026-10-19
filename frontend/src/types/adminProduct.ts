import { ProductType, CategorySummary, TierVariation, SkuItem } from './product';

export type ProductStatus = 'ACTIVE' | 'INACTIVE' | 'ARCHIVED';

export interface AdminProduct {
  id: string;
  sku: string;
  name: string;
  slug: string;
  categoryId: string;
  category?: CategorySummary;
  productType: ProductType;
  brand: string;
  description: string;
  price: number;
  stock: number;
  images: string[];
  tierVariations?: TierVariation[];
  skus?: SkuItem[];
  attributes: Record<string, any>;
  status: ProductStatus;
  version: number;
  createdAt: string;
  updatedAt: string;
}

export interface AdminProductCreate {
  sku: string;
  name: string;
  slug: string;
  categoryId: string;
  productType: ProductType;
  brand: string;
  description: string;
  price: number;
  stock: number;
  images: string[];
  tierVariations?: TierVariation[];
  skus?: SkuItem[];
  attributes: Record<string, any>;
  status: ProductStatus;
}

export interface AdminProductPatch {
  name?: string;
  slug?: string;
  categoryId?: string;
  productType?: ProductType;
  brand?: string;
  description?: string;
  price?: number;
  stock?: number;
  images?: string[];
  tierVariations?: TierVariation[];
  skus?: SkuItem[];
  attributes?: Record<string, any>;
  status?: ProductStatus;
  expectedVersion: number;
}

export interface AdminProductFilterParams {
  q?: string;
  categoryId?: string;
  status?: ProductStatus;
  page?: number;
  pageSize?: number;
  sort?: string;
}
