import React, { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Filter,
  SlidersHorizontal,
  X,
} from 'lucide-react';
import { catalogApi } from '../api/catalogApi';
import { Category, Product, ProductFilterParams, ProductSortOption } from '../types/product';
import { ProductCard } from '../components/common/ProductCard';
import { ProductCardSkeleton } from '../components/common/ProductCardSkeleton';
import { Pagination } from '../components/ui/Pagination';
import { EmptyState } from '../components/ui/EmptyState';
import { ErrorState } from '../components/ui/ErrorState';
import { Button } from '../components/ui/Button';

export const ProductsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  const [categories, setCategories] = useState<Category[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [mobileFilterOpen, setMobileFilterOpen] = useState(false);

  // Local filter states for inputs that need confirmation
  const [minPriceInput, setMinPriceInput] = useState<string>(searchParams.get('minPrice') || '');
  const [maxPriceInput, setMaxPriceInput] = useState<string>(searchParams.get('maxPrice') || '');

  // Extract query values
  const q = searchParams.get('q') || '';
  const categoryId = searchParams.get('categoryId') || '';
  const productType = searchParams.get('productType') || '';
  const brand = searchParams.get('brand') || '';
  const minPrice = searchParams.get('minPrice');
  const maxPrice = searchParams.get('maxPrice');
  const sort = (searchParams.get('sort') as ProductSortOption) || 'latest';
  const page = parseInt(searchParams.get('page') || '1', 10);

  // Legacy variant query parameters are purchase choices, not catalog filters.
  useEffect(() => {
    const keys = ['size', 'color', 'ram', 'capacity'];
    if (keys.some((key) => searchParams.has(key))) {
      const next = new URLSearchParams(searchParams);
      keys.forEach((key) => next.delete(key));
      setSearchParams(next, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  // Load categories list for filter sidebar
  useEffect(() => {
    catalogApi.getCategories().then((res) => {
      setCategories(res.categories);
    }).catch(console.error);
  }, []);

  // Sync price inputs with search params
  useEffect(() => {
    setMinPriceInput(minPrice || '');
    setMaxPriceInput(maxPrice || '');
  }, [minPrice, maxPrice]);

  // Fetch products matching searchParams
  const fetchProducts = useCallback(async () => {
    setLoading(true);
    setError(null);

    const filterPayload: ProductFilterParams = {
      page,
      pageSize: 16,
      sort,
    };

    if (q) filterPayload.q = q;
    if (categoryId) filterPayload.categoryId = categoryId;
    if (productType) filterPayload.productType = productType as any;
    if (brand) filterPayload.brand = brand;
    if (minPrice) filterPayload.minPrice = parseInt(minPrice, 10);
    if (maxPrice) filterPayload.maxPrice = parseInt(maxPrice, 10);

    try {
      const res = await catalogApi.getProducts(filterPayload);
      setProducts(res.products);
      setTotalCount(res.meta.total || 0);
      setTotalPages(res.meta.totalPages || 1);
    } catch (err: any) {
      setError(err?.message || 'Không thể tải danh sách sản phẩm.');
    } finally {
      setLoading(false);
    }
  }, [q, categoryId, productType, brand, minPrice, maxPrice, sort, page]);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  // Helpers to update params
  const updateParam = (key: string, value: string | undefined | null) => {
    const next = new URLSearchParams(searchParams);
    if (value) {
      next.set(key, value);
    } else {
      next.delete(key);
    }
    next.set('page', '1'); // Reset to page 1 on filter change
    setSearchParams(next);
  };

  const handleApplyPrice = (e: React.FormEvent) => {
    e.preventDefault();
    const next = new URLSearchParams(searchParams);
    if (minPriceInput) next.set('minPrice', minPriceInput);
    else next.delete('minPrice');

    if (maxPriceInput) next.set('maxPrice', maxPriceInput);
    else next.delete('maxPrice');

    next.set('page', '1');
    setSearchParams(next);
  };

  const handleClearAllFilters = () => {
    setSearchParams(new URLSearchParams());
    setMinPriceInput('');
    setMaxPriceInput('');
  };

  const handlePageChange = (newPage: number) => {
    const next = new URLSearchParams(searchParams);
    next.set('page', String(newPage));
    setSearchParams(next);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const activeFiltersCount = [
    q,
    categoryId,
    productType,
    brand,
    minPrice,
    maxPrice,
  ].filter(Boolean).length;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-200">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            {q ? `Kết quả tìm kiếm cho "${q}"` : 'Danh mục sản phẩm'}
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Tìm thấy <span className="font-semibold text-slate-800">{totalCount}</span> sản phẩm phù hợp
          </p>
        </div>

        {/* Sort & Mobile Filter Toggle */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setMobileFilterOpen(true)}
            className="lg:hidden flex items-center gap-2 px-3.5 py-2 rounded-xl border border-slate-300 bg-white text-sm font-medium text-slate-700 shadow-sm"
          >
            <SlidersHorizontal className="w-4 h-4" />
            <span>Bộ lọc {activeFiltersCount > 0 && `(${activeFiltersCount})`}</span>
          </button>

          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 hidden sm:inline whitespace-nowrap">Sắp xếp:</span>
            <select
              value={sort}
              onChange={(e) => updateParam('sort', e.target.value)}
              className="bg-white border border-slate-300 text-slate-800 text-sm rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500 font-medium shadow-sm"
            >
              <option value="latest">Mới nhất</option>
              <option value="price_asc">Giá: Thấp đến Cao</option>
              <option value="price_desc">Giá: Cao đến Thấp</option>
            </select>
          </div>
        </div>
      </div>

      {/* Active Filter Pills */}
      {activeFiltersCount > 0 && (
        <div className="flex flex-wrap items-center gap-2 pt-4">
          <span className="text-xs text-slate-400 font-medium">Đang lọc theo:</span>
          {q && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-50 text-brand-700 border border-brand-200 text-xs">
              Từ khóa: {q}
              <button onClick={() => updateParam('q', null)}>
                <X className="w-3.5 h-3.5" />
              </button>
            </span>
          )}
          {categoryId && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-50 text-brand-700 border border-brand-200 text-xs">
              Danh mục: {categories.find((c) => c.id === categoryId)?.name || categoryId}
              <button onClick={() => updateParam('categoryId', null)}>
                <X className="w-3.5 h-3.5" />
              </button>
            </span>
          )}
          {productType && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-50 text-brand-700 border border-brand-200 text-xs">
              Ngành: {productType}
              <button onClick={() => updateParam('productType', null)}>
                <X className="w-3.5 h-3.5" />
              </button>
            </span>
          )}
          {(minPrice || maxPrice) && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-50 text-brand-700 border border-brand-200 text-xs">
              Giá: {minPrice ? `${minPrice}đ` : '0đ'} - {maxPrice ? `${maxPrice}đ` : 'Max'}
              <button
                onClick={() => {
                  updateParam('minPrice', null);
                  updateParam('maxPrice', null);
                }}
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </span>
          )}
          <button
            onClick={handleClearAllFilters}
            className="text-xs text-rose-600 hover:text-rose-700 font-semibold underline ml-1"
          >
            Xóa tất cả
          </button>
        </div>
      )}

      {/* Main Layout: Sidebar Filters + Products Grid */}
      <div className="flex gap-8 items-start pt-6">
        {/* Desktop Filter Sidebar */}
        <aside className="hidden lg:block w-64 bg-white rounded-2xl border border-slate-200 p-6 shadow-sm flex-shrink-0 space-y-6">
          <div className="flex items-center justify-between pb-4 border-b border-slate-100">
            <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
              <Filter className="w-4 h-4 text-brand-600" />
              <span>Bộ Lọc Sản Phẩm</span>
            </h3>
            {activeFiltersCount > 0 && (
              <button
                onClick={handleClearAllFilters}
                className="text-xs text-slate-400 hover:text-rose-600 font-medium"
              >
                Đặt lại
              </button>
            )}
          </div>

          {/* Categories Filter */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">Danh Mục</h4>
            <div className="space-y-1.5 text-sm">
              <button
                onClick={() => updateParam('categoryId', null)}
                className={`w-full text-left px-2.5 py-1.5 rounded-lg transition-colors ${
                  !categoryId ? 'bg-brand-50 text-brand-700 font-semibold' : 'text-slate-600 hover:bg-slate-50'
                }`}
              >
                Tất cả danh mục
              </button>
              {categories.map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => updateParam('categoryId', cat.id)}
                  className={`w-full text-left px-2.5 py-1.5 rounded-lg transition-colors truncate ${
                    categoryId === cat.id
                      ? 'bg-brand-50 text-brand-700 font-semibold'
                      : 'text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {cat.name}
                </button>
              ))}
            </div>
          </div>

          {/* Price Range Filter */}
          <div className="space-y-3 pt-4 border-t border-slate-100">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">Khoảng Giá (VND)</h4>
            <form onSubmit={handleApplyPrice} className="space-y-2">
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="number"
                  placeholder="Từ"
                  value={minPriceInput}
                  onChange={(e) => setMinPriceInput(e.target.value)}
                  className="w-full text-xs px-2.5 py-1.5 rounded-lg border border-slate-200 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
                <input
                  type="number"
                  placeholder="Đến"
                  value={maxPriceInput}
                  onChange={(e) => setMaxPriceInput(e.target.value)}
                  className="w-full text-xs px-2.5 py-1.5 rounded-lg border border-slate-200 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>
              <Button type="submit" variant="outline" size="sm" className="w-full text-xs py-1.5">
                Áp dụng giá
              </Button>
            </form>
          </div>
        </aside>

        {/* Products Grid Area */}
        <section className="flex-1 w-full min-w-0">
          {error ? (
            <ErrorState message={error} onRetry={fetchProducts} />
          ) : loading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {Array.from({ length: 8 }).map((_, idx) => (
                <ProductCardSkeleton key={idx} />
              ))}
            </div>
          ) : products.length === 0 ? (
            <EmptyState
              title="Không tìm thấy sản phẩm phù hợp"
              description="Hãy thử bỏ các tiêu chí lọc hoặc tìm kiếm với từ khóa khác."
              actionLabel="Đặt lại bộ lọc"
              onAction={handleClearAllFilters}
            />
          ) : (
            <div className="space-y-8">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {products.map((product) => (
                  <ProductCard key={product.id} product={product} />
                ))}
              </div>

              {/* Pagination */}
              <Pagination
                currentPage={page}
                totalPages={totalPages}
                onPageChange={handlePageChange}
                className="pt-6"
              />
            </div>
          )}
        </section>
      </div>

      {/* Mobile Filters Drawer Modal */}
      {mobileFilterOpen && (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <div
            className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm"
            onClick={() => setMobileFilterOpen(false)}
          />
          <div className="relative ml-auto w-full max-w-xs h-full bg-white p-6 shadow-2xl flex flex-col justify-between overflow-y-auto">
            <div className="space-y-6">
              <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                <h3 className="font-bold text-slate-900 text-base">Bộ Lọc</h3>
                <button
                  onClick={() => setMobileFilterOpen(false)}
                  className="p-1 text-slate-400 hover:text-slate-600"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Category */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase text-slate-500">Danh Mục</h4>
                <div className="space-y-1">
                  <button
                    onClick={() => {
                      updateParam('categoryId', null);
                      setMobileFilterOpen(false);
                    }}
                    className={`block w-full text-left px-2.5 py-1.5 rounded-lg text-sm ${
                      !categoryId ? 'bg-brand-50 text-brand-700 font-bold' : 'text-slate-700'
                    }`}
                  >
                    Tất cả danh mục
                  </button>
                  {categories.map((cat) => (
                    <button
                      key={cat.id}
                      onClick={() => {
                        updateParam('categoryId', cat.id);
                        setMobileFilterOpen(false);
                      }}
                      className={`block w-full text-left px-2.5 py-1.5 rounded-lg text-sm truncate ${
                        categoryId === cat.id ? 'bg-brand-50 text-brand-700 font-bold' : 'text-slate-700'
                      }`}
                    >
                      {cat.name}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="pt-6 border-t border-slate-100">
              <Button
                variant="primary"
                size="md"
                className="w-full"
                onClick={() => setMobileFilterOpen(false)}
              >
                Xem kết quả
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
