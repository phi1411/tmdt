import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { adminProductsApi } from '../api/adminProductsApi';
import { adminCategoriesApi } from '../api/adminCategoriesApi';
import { AdminProduct, ProductStatus } from '../types/adminProduct';
import { AdminCategory } from '../types/adminCategory';
import { PaginationMeta } from '../types/api';
import { formatVND } from '../utils/formatters';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Pagination } from '../components/ui/Pagination';
import { Skeleton } from '../components/ui/Skeleton';
import { useToast } from '../contexts/ToastContext';
import {
  ShoppingBag,
  Plus,
  Search,
  Filter,
  RotateCcw,
  Edit2,
  Archive,
  AlertCircle,
} from 'lucide-react';

export const AdminProductsPage: React.FC = () => {
  const { success: toastSuccess, error: toastError, warning: toastWarning } = useToast();

  const [products, setProducts] = useState<AdminProduct[]>([]);
  const [categories, setCategories] = useState<AdminCategory[]>([]);
  const [meta, setMeta] = useState<PaginationMeta>({
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 0,
  });

  // Filters
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [appliedSearchQuery, setAppliedSearchQuery] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedStatus, setSelectedStatus] = useState<ProductStatus | ''>('');
  const [currentPage, setCurrentPage] = useState<number>(1);

  // Loading States
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Archive Modal State
  const [archiveTarget, setArchiveTarget] = useState<AdminProduct | null>(null);
  const [archiving, setArchiving] = useState<boolean>(false);

  const fetchProducts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await adminProductsApi.getList({
        q: appliedSearchQuery || undefined,
        categoryId: selectedCategory || undefined,
        status: selectedStatus || undefined,
        page: currentPage,
        pageSize: 20,
      });

      setProducts(res.products);
      setMeta(res.meta);
    } catch (err: any) {
      setError(err?.message || 'Không thể tải danh sách sản phẩm.');
    } finally {
      setLoading(false);
    }
  }, [appliedSearchQuery, selectedCategory, selectedStatus, currentPage]);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  useEffect(() => {
    const loadCategories = async () => {
      try {
        const res = await adminCategoriesApi.getList({ pageSize: 100 });
        setCategories(res.categories);
      } catch {
        // Soft fail
      }
    };
    loadCategories();
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
    setAppliedSearchQuery(searchQuery.trim());
  };

  const handleResetFilters = () => {
    setSearchQuery('');
    setAppliedSearchQuery('');
    setSelectedCategory('');
    setSelectedStatus('');
    setCurrentPage(1);
  };

  const handleArchiveConfirm = async () => {
    if (!archiveTarget) return;
    setArchiving(true);
    try {
      await adminProductsApi.archive(archiveTarget.id, archiveTarget.version);
      toastSuccess(`Đã lưu trữ (Archive) sản phẩm "${archiveTarget.name}" thành công!`);
      setArchiveTarget(null);
      await fetchProducts();
    } catch (err: any) {
      if (err?.code === 'CONFLICT' || err?.status === 409) {
        toastWarning('Sản phẩm đã có cập nhật hoặc xung đột phiên bản. Đang tải lại...');
        await fetchProducts();
      } else {
        toastError(err?.message || 'Không thể lưu trữ sản phẩm.');
      }
    } finally {
      setArchiving(false);
    }
  };

  const getStatusBadge = (status: ProductStatus) => {
    switch (status) {
      case 'ACTIVE':
        return <Badge variant="success">Đang bán</Badge>;
      case 'INACTIVE':
        return <Badge variant="warning">Tạm ẩn</Badge>;
      case 'ARCHIVED':
        return <Badge variant="neutral">Đã lưu trữ</Badge>;
      default:
        return <Badge>{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Action Bar */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <ShoppingBag className="w-5 h-5 text-brand-600" />
              <span>Quản Lý Sản Phẩm</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Quản trị danh mục hàng hóa đa ngành (Polymorphic Products) và kiểm soát tồn kho
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <Button
              variant="outline"
              size="sm"
              onClick={fetchProducts}
              loading={loading}
              icon={<RotateCcw className="w-3.5 h-3.5" />}
            >
              Làm mới
            </Button>
            <Link to="/admin/products/new">
              <Button variant="primary" size="sm" icon={<Plus className="w-4 h-4" />}>
                Thêm sản phẩm mới
              </Button>
            </Link>
          </div>
        </div>

        {/* Filters */}
        <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center gap-3">
          <form onSubmit={handleSearchSubmit} className="flex items-center gap-2 flex-1 min-w-[240px]">
            <div className="relative flex-1">
              <input
                type="text"
                placeholder="Tìm tên sản phẩm hoặc từ khóa..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full text-xs bg-slate-50 border border-slate-200 rounded-xl pl-9 pr-3 py-2 text-slate-800 placeholder:text-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-500"
              />
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
            </div>
            <Button type="submit" variant="primary" size="sm">
              Tìm
            </Button>
          </form>

          {/* Category Filter */}
          <div className="flex items-center gap-2 max-w-full min-w-0 w-full sm:w-auto">
            <span className="text-xs font-semibold text-slate-500 flex items-center gap-1 flex-shrink-0">
              <Filter className="w-3.5 h-3.5" />
              Ngành hàng:
            </span>
            <select
              value={selectedCategory}
              onChange={(e) => {
                setSelectedCategory(e.target.value);
                setCurrentPage(1);
              }}
              className="min-w-0 flex-1 sm:flex-initial text-xs bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-800 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-100"
            >
              <option value="">Tất cả ngành hàng</option>
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.name} ({cat.productType})
                </option>
              ))}
            </select>
          </div>

          {/* Status Filter */}
          <div className="flex items-center gap-2">
            <select
              value={selectedStatus}
              onChange={(e) => {
                setSelectedStatus(e.target.value as ProductStatus | '');
                setCurrentPage(1);
              }}
              className="text-xs bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-800 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-100"
            >
              <option value="">Tất cả trạng thái</option>
              <option value="ACTIVE">ACTIVE (Đang bán)</option>
              <option value="INACTIVE">INACTIVE (Tạm ẩn)</option>
              <option value="ARCHIVED">ARCHIVED (Đã lưu trữ)</option>
            </select>
          </div>

          {(appliedSearchQuery || selectedCategory || selectedStatus) && (
            <button
              onClick={handleResetFilters}
              className="text-xs text-brand-600 hover:text-brand-800 font-semibold underline px-1"
            >
              Xóa bộ lọc
            </button>
          )}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <div className="font-bold">Lỗi tải danh mục sản phẩm:</div>
            <div className="text-xs mt-0.5">{error}</div>
          </div>
          <Button variant="outline" size="sm" onClick={fetchProducts}>
            Thử lại
          </Button>
        </div>
      )}

      {/* Products Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200/80 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-3.5 px-4 sm:px-6">Sản Phẩm</th>
                <th className="py-3.5 px-4">SKU / Ngành</th>
                <th className="py-3.5 px-4 text-right">Giá Bán</th>
                <th className="py-3.5 px-4 text-center">Tồn Kho</th>
                <th className="py-3.5 px-4 text-center">Trạng Thái</th>
                <th className="py-3.5 px-4 text-center">Phiên Bản</th>
                <th className="py-3.5 px-4 sm:px-6 text-center">Thao Tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
              {loading ? (
                Array.from({ length: 6 }).map((_, idx) => (
                  <tr key={idx}>
                    <td className="py-4 px-4 sm:px-6"><Skeleton className="h-5 w-48" /></td>
                    <td className="py-4 px-4"><Skeleton className="h-4 w-28" /></td>
                    <td className="py-4 px-4 text-right"><Skeleton className="h-4 w-20 ml-auto" /></td>
                    <td className="py-4 px-4 text-center"><Skeleton className="h-4 w-12 mx-auto" /></td>
                    <td className="py-4 px-4 text-center"><Skeleton className="h-4 w-16 mx-auto" /></td>
                    <td className="py-4 px-4 text-center"><Skeleton className="h-4 w-8 mx-auto" /></td>
                    <td className="py-4 px-4 sm:px-6 text-center"><Skeleton className="h-6 w-24 mx-auto" /></td>
                  </tr>
                ))
              ) : products.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    <ShoppingBag className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                    <span>Không tìm thấy sản phẩm nào phù hợp.</span>
                  </td>
                </tr>
              ) : (
                products.map((prod) => (
                  <tr key={prod.id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="py-4 px-4 sm:px-6">
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-xl bg-slate-100 border border-slate-200/60 overflow-hidden flex-shrink-0 flex items-center justify-center">
                          {prod.images?.[0] ? (
                            <img src={prod.images[0]} alt={prod.name} className="w-full h-full object-cover" />
                          ) : (
                            <span className="text-[9px] text-slate-400">Không ảnh</span>
                          )}
                        </div>
                        <div className="min-w-0">
                          <Link
                            to={`/products/${prod.slug}`}
                            target="_blank"
                            className="font-bold text-slate-900 hover:text-brand-600 line-clamp-1"
                            title={prod.name}
                          >
                            {prod.name}
                          </Link>
                          <div className="text-[11px] text-slate-400 truncate">
                            Thương hiệu: <span className="text-slate-600 font-medium">{prod.brand}</span>
                          </div>
                        </div>
                      </div>
                    </td>

                    <td className="py-4 px-4">
                      <div className="font-mono text-[11px] font-bold text-slate-800">{prod.sku}</div>
                      <div className="text-[10px] text-slate-400 font-medium uppercase mt-0.5">
                        {prod.category?.name || prod.productType}
                      </div>
                    </td>

                    <td className="py-4 px-4 text-right font-bold text-slate-900">
                      {formatVND(prod.price)}
                    </td>

                    <td className="py-4 px-4 text-center">
                      <span
                        className={`font-bold ${
                          prod.stock === 0 ? 'text-rose-600' : prod.stock < 10 ? 'text-amber-600' : 'text-emerald-600'
                        }`}
                      >
                        {prod.stock}
                      </span>
                    </td>

                    <td className="py-4 px-4 text-center">
                      {getStatusBadge(prod.status)}
                    </td>

                    <td className="py-4 px-4 text-center font-mono text-slate-400">
                      v{prod.version}
                    </td>

                    <td className="py-4 px-4 sm:px-6 text-center">
                      <div className="flex items-center justify-center gap-1.5">
                        <Link to={`/admin/products/${prod.id}/edit`}>
                          <Button variant="outline" size="sm" icon={<Edit2 className="w-3.5 h-3.5" />}>
                            Sửa
                          </Button>
                        </Link>

                        {prod.status !== 'ARCHIVED' && (
                          <Button
                            variant="danger"
                            size="sm"
                            onClick={() => setArchiveTarget(prod)}
                            icon={<Archive className="w-3.5 h-3.5" />}
                            title="Lưu trữ sản phẩm (Archive)"
                          >
                            Lưu trữ
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {!loading && meta.totalPages > 1 && (
          <div className="p-4 border-t border-slate-100 flex justify-center">
            <Pagination
              currentPage={currentPage}
              totalPages={meta.totalPages}
              onPageChange={(p) => setCurrentPage(p)}
            />
          </div>
        )}
      </div>

      {/* Archive Confirmation Modal */}
      <Modal
        isOpen={!!archiveTarget}
        onClose={() => setArchiveTarget(null)}
        title="Lưu Trữ Sản Phẩm (Archive)"
        description="Bạn có chắc chắn muốn lưu trữ sản phẩm này không?"
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-600 leading-relaxed">
            Hành động này sẽ cập nhật trạng thái của sản phẩm{' '}
            <span className="font-bold text-slate-900 font-mono">
              {archiveTarget?.name} (SKU: {archiveTarget?.sku})
            </span>{' '}
            thành <span className="font-bold text-amber-600">ARCHIVED</span>. Sản phẩm sẽ bị ẩn khỏi Catalog người dùng và giỏ hàng nhưng snapshot trong các đơn hàng đã mua vẫn được giữ nguyên vẹn.
          </p>

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <Button variant="outline" size="sm" onClick={() => setArchiveTarget(null)}>
              Hủy bỏ
            </Button>
            <Button
              variant="danger"
              size="sm"
              loading={archiving}
              onClick={handleArchiveConfirm}
            >
              Xác nhận lưu trữ
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
