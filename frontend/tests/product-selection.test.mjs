import { test } from 'node:test';
import assert from 'node:assert/strict';
import { hasVariantPriceRange, purchaseOptions, skuMatches } from '../src/utils/productSelection.ts';

const product = {
  productType: 'FASHION', price: 100000, stock: 12,
  attributes: { sizes: ['M', 'XL'], colors: ['Đen'] },
  tierVariations: [{ tier: 1, name: 'Kích cỡ', options: ['M', 'XL'] }],
  skus: [
    { skuId: 'M', tierIndex: [0], price: 100000, stock: 5 },
    { skuId: 'XL', tierIndex: [1], price: 120000, stock: 7 },
  ],
};

test('different SKU prices require a starting-price label before selection', () => {
  assert.equal(hasVariantPriceRange(product), true);
  const selection = { 'Kích cỡ': 'XL' };
  const selected = product.skus.find(s => skuMatches(product, s, selection));
  assert.equal(selected.price, 120000);
  assert.equal(selected.stock, 7);
});

test('uniform SKU prices do not imply a price range', () => {
  assert.equal(hasVariantPriceRange({ ...product, skus: product.skus.map(s => ({ ...s, price: 100000 })) }), false);
});

test('legacy metadata options keep one common price', () => {
  const legacy = { ...product, tierVariations: [], skus: [] };
  assert.equal(hasVariantPriceRange(legacy), false);
  assert.deepEqual(purchaseOptions(legacy).map(o => o.key), ['size', 'color']);
});

test('configured tiers take precedence over metadata and mismatched selections do not resolve', () => {
  assert.deepEqual(purchaseOptions(product), [{ key: 'Kích cỡ', label: 'Kích cỡ', values: ['M', 'XL'] }]);
  assert.equal(product.skus.some(s => skuMatches(product, s, { 'Kích cỡ': 'XXL' })), false);
});
