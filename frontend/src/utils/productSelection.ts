import type { Product, SkuItem } from '../types/product';

export interface PurchaseOption {
  key: string;
  label: string;
  values: string[];
}

export function hasVariantPriceRange(product: Product): boolean {
  return !!product.tierVariations?.length && new Set(product.skus?.map(sku => sku.price)).size > 1;
}

export function purchaseOptions(product: Product): PurchaseOption[] {
  if (product.tierVariations?.length) {
    return product.tierVariations.map((tier) => ({ key: tier.name, label: tier.name, values: tier.options }));
  }
  if (product.productType !== 'FASHION') return [];
  return [
    { key: 'size', label: 'Kích cỡ', values: product.attributes.sizes },
    { key: 'color', label: 'Màu sắc', values: product.attributes.colors },
  ].filter((option): option is PurchaseOption => Array.isArray(option.values) && option.values.length > 0);
}

export function skuMatches(product: Product, sku: SkuItem, selection: Record<string, string>): boolean {
  const tiers = product.tierVariations || [];
  return !!sku.tierIndex && sku.tierIndex.length === tiers.length && tiers.every((tier, index) => {
    const value = tier.options[sku.tierIndex![index]];
    return value !== undefined && (!selection[tier.name] || selection[tier.name] === value);
  });
}

export function hasPurchasableStock(product: Product): boolean {
  if (product.stock <= 0) return false;
  return !product.tierVariations?.length || !!product.skus?.some((sku) => sku.stock > 0 && skuMatches(product, sku, {}));
}
