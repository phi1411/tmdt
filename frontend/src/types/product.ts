export type ProductType = 'ELECTRONICS' | 'FASHION' | 'HOME_APPLIANCE';

export interface CategorySummary {
  id: string;
  name: string;
  slug: string;
  productType: ProductType;
  status?: string;
}

export interface Category extends CategorySummary {
  description: string;
  status: 'ACTIVE' | 'ARCHIVED';
  version: number;
  createdAt: string;
  updatedAt: string;
}

export interface ElectronicsAttributes {
  ram?: string;
  storage?: string;
  chip?: string;
  screen?: string;
  battery?: string;
  [key: string]: any;
}

export interface FashionAttributes {
  sizes?: string[];
  colors?: string[];
  material?: string;
  gender?: string;
  [key: string]: any;
}

export interface HomeApplianceAttributes {
  power?: string;
  capacity?: string;
  voltage?: string;
  material?: string;
  [key: string]: any;
}

export type ProductAttributes = ElectronicsAttributes | FashionAttributes | HomeApplianceAttributes | Record<string, any>;

export interface TierVariation {
  tier: number;
  name: string;
  options: string[];
}

export interface SkuItem {
  skuId: string;
  tierIndex?: number[];
  price: number;
  stock: number;
  image?: string;
}

export interface RatingSummary {
  averageRating: number;
  totalReviews: number;
  starsBreakdown?: Record<string, number>;
}

export interface Product {
  id: string;
  sku: string;
  name: string;
  slug: string;
  categoryId: string;
  category: CategorySummary;
  productType: ProductType;
  brand: string;
  description: string;
  price: number;
  stock: number;
  images: string[];
  attributes: ProductAttributes;
  tierVariations?: TierVariation[];
  skus?: SkuItem[];
  ratingSummary?: RatingSummary;
  version: number;
  createdAt: string;
  updatedAt: string;
}

export type ProductSortOption = 'latest' | 'price_asc' | 'price_desc';

export interface ProductFilterParams {
  q?: string;
  categoryId?: string;
  productType?: ProductType;
  brand?: string;
  minPrice?: number;
  maxPrice?: number;
  size?: string;
  color?: string;
  ram?: string;
  capacity?: string;
  sort?: ProductSortOption;
  page?: number;
  pageSize?: number;
}
