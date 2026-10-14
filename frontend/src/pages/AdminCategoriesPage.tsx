import React, { useState, useEffect, useCallback } from 'react';
import { adminCategoriesApi } from '../api/adminCategoriesApi';
import { AdminCategory, CategoryStatus } from '../types/adminCategory';
import { ProductType } from '../types/product';
import { PaginationMeta } from '../types/api';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Modal } from '../components/ui/Modal';
import { Pagination } from '../components/ui/Pagination';
import { Skeleton } from '../components/ui/Skeleton';
import { useToast } from '../contexts/ToastContext';
import {
  FolderTree,
  Plus,
  RotateCcw,
  Edit2,
  Trash2,
  AlertCircle,
  Tag,
  Layers,
} from 'lucide-react';

export const AdminCategoriesPage: React.FC = () => {
  const { success: toastSuccess, error: toastError, warning: toastWarning } = useToast();

  const [categories, setCategories] = useState<AdminCategory[]>([]);
  const [meta, setMeta] = useState<PaginationMeta>({
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 0,
  });

  const [selectedStatus, setSelectedStatus] = useState<CategoryStatus | ''>('');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Modal Create / Edit States
  const [modalOpen, setModalOpen] = useState<boolean>(false);
  const [editingCategory, setEditingCategory] = useState<AdminCategory | null>(null);
  const [saving, setSaving] = useState<boolean>(false);

  // Form Fields
  const [name, setName] = useState<string>('');
  const [slug, setSlug] = useState<string>('');
  const [productType, setProductType] = useState<ProductType>('ELECTRONICS');
  const [description, setDescription] = useState<string>('');
  const [status, setStatus] = useState<CategoryStatus>('ACTIVE');

  // Delete Modal States
  const [deleteTarget, setDeleteTarget] = useState<AdminCategory | null>(null);
  const [deleting, setDeleting] = useState<boolean>(false);

  const fetchCategories = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await adminCategoriesApi.getList({
        status: selectedStatus || undefined,
        page: currentPage,
        pageSize: 20,
      });

      setCategories(res.categories);
      setMeta(res.meta);
    } catch (err: any) {
      setError(err?.message || 'Không thể tải danh sách ngành hàng.');
    } finally {
      setLoading(false);
    }
  }, [selectedStatus, currentPage]);

  useEffect(() => {
    fetchCategories();
  }, [fetchCategories]);

  const openCreateModal = () => {
    setEditingCategory(null);
    setName('');
    setSlug('');
    setProductType('ELECTRONICS');
    setDescription('');
    setStatus('ACTIVE');
    setModalOpen(true);
  };

  const openEditModal = (cat: AdminCategory) => {
    setEditingCategory(cat);
    setName(cat.name);
    setSlug(cat.slug);
    setProductType(cat.productType);
    setDescription(cat.description || '');
    setStatus(cat.status);
    setModalOpen(true);
  };

  const handleNameChange = (val: string) => {
    setName(val);
    if (!editingCategory && !slug) {
      const generated = val
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/[đĐ]/g, 'd')
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '');
      setSlug(generated);
    }
  };

  const handleSaveSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name.trim() || !slug.trim()) {
      toastWarning('Vui lòng nhập tên ngành hàng và đường dẫn tĩnh (Slug).');
      return;
    }

    setSaving(true);
    try {
      if (editingCategory) {
        await adminCategoriesApi.update(editingCategory.id, {
          name: name.trim(),
          slug: slug.trim(),
          productType,
          description: description.trim() || undefined,
          status,
          expectedVersion: editingCategory.version,
        });
        toastSuccess(`Đã cập nhật ngành hàng "${name}" thành công!`);
      } else {
        await adminCategoriesApi.create({
          name: name.trim(),
          slug: slug.trim(),
          productType,
          description: description.trim() || undefined,
        });
        toastSuccess(`Đã tạo ngành hàng mới "${name}" thành công!`);
      }

      setModalOpen(false);
      await fetchCategories();
    } catch (err: any) {
      if (err?.code === 'CONFLICT' || err?.status === 409) {
        toastWarning(err?.message || 'Slug đã tồn tại hoặc danh mục đang có xung đột phiên bản.');
      } else {
        toastError(err?.message || 'Không thể lưu ngành hàng.');
      }
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await adminCategoriesApi.delete(deleteTarget.id, deleteTarget.version);
      toastSuccess(`Đã xóa ngành hàng "${deleteTarget.name}" thành công!`);
      setDeleteTarget(null);
      await fetchCategories();
    } catch (err: any) {
      if (err?.code === 'CATEGORY_IN_USE' || err?.status === 409) {
        toastWarning(
          'Không thể xóa ngành hàng này vì đang có sản phẩm trong cơ sở dữ liệu tham chiếu tới nó. Vui lòng chuyển hoặc xóa sản phẩm liên quan trước.'
        );
      } else {
        toastError(err?.message || 'Không thể xóa ngành hàng.');
      }
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <FolderTree className="w-5 h-5 text-brand-600" />
              <span>Quản Lý Ngành Hàng (Categories)</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Cấu trúc danh mục một cấp gắn kết với mô hình Polymorphic Schema NoSQL
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <Button
              variant="outline"
              size="sm"
              onClick={fetchCategories}
              loading={loading}
              icon={<RotateCcw className="w-3.5 h-3.5" />}
            >
              Làm mới
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={openCreateModal}
              icon={<Plus className="w-4 h-4" />}
            >
              Thêm ngành hàng
            </Button>
          </div>
        </div>

        {/* Filters */}
        <div className="pt-3 border-t border-slate-100 flex items-center gap-3">
          <span className="text-xs font-semibold text-slate-500">Lọc theo trạng thái:</span>
          <select
            value={selectedStatus}
            onChange={(e) => {
              setSelectedStatus(e.target.value as CategoryStatus | '');
              setCurrentPage(1);
            }}
            className="text-xs bg-slate-50 border border-slate-200 rounded-xl px-3 py-1.5 text-slate-800 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-100"
          >
            <option value="">Tất cả trạng thái</option>
            <option value="ACTIVE">ACTIVE (Đang hoạt động)</option>
            <option value="ARCHIVED">ARCHIVED (Đã lưu trữ)</option>
          </select>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <div className="font-bold">Lỗi tải danh mục ngành hàng:</div>
            <div className="text-xs mt-0.5">{error}</div>
          </div>
          <Button variant="outline" size="sm" onClick={fetchCategories}>
            Thử lại
          </Button>
        </div>
      )}

      {/* Categories Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200/80 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-3.5 px-4 sm:px-6">Tên Ngành Hàng</th>
                <th className="py-3.5 px-4">Đường Dẫn (Slug)</th>
                <th className="py-3.5 px-4">Loại Schema</th>
                <th className="py-3.5 px-4">Mô Tả</th>
                <th className="py-3.5 px-4 text-center">Trạng Thái</th>
                <th className="py-3.5 px-4 text-center">Phiên Bản</th>
                <th className="py-3.5 px-4 sm:px-6 text-center">Thao Tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
              {loading ? (
                Array.from({ length: 4 }).map((_, idx) => (
                  <tr key={idx}>
                    <td className="py-4 px-4 sm:px-6"><Skeleton className="h-5 w-36" /></td>
                    <td className="py-4 px-4"><Skeleton className="h-4 w-28" /></td>
                    <td className="py-4 px-4"><Skeleton className="h-4 w-24" /></td>
                    <td className="py-4 px-4"><Skeleton className="h-4 w-40" /></td>
                    <td className="py-4 px-4 text-center"><Skeleton className="h-5 w-16 mx-auto" /></td>
                    <td className="py-4 px-4 text-center"><Skeleton className="h-4 w-8 mx-auto" /></td>
                    <td className="py-4 px-4 sm:px-6 text-center"><Skeleton className="h-6 w-20 mx-auto" /></td>
                  </tr>
                ))
              ) : categories.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    <FolderTree className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                    <span>Không có ngành hàng nào.</span>
                  </td>
                </tr>
              ) : (
                categories.map((cat) => (
                  <tr key={cat.id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="py-4 px-4 sm:px-6 font-bold text-slate-900 flex items-center gap-2">
                      <Tag className="w-4 h-4 text-brand-600 flex-shrink-0" />
                      <span>{cat.name}</span>
                    </td>

                    <td className="py-4 px-4 font-mono text-slate-600">
                      {cat.slug}
                    </td>

                    <td className="py-4 px-4">
                      <span className="inline-flex items-center gap-1 font-semibold text-[11px] text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200/60">
                        <Layers className="w-3 h-3" />
                        <span>{cat.productType}</span>
                      </span>
                    </td>

                    <td className="py-4 px-4 text-slate-500 max-w-xs truncate" title={cat.description}>
                      {cat.description || <span className="italic text-slate-300">Không có mô tả</span>}
                    </td>

                    <td className="py-4 px-4 text-center">
                      {cat.status === 'ACTIVE' ? (
                        <Badge variant="success">Hoạt động</Badge>
                      ) : (
                        <Badge variant="neutral">Lưu trữ</Badge>
                      )}
                    </td>

                    <td className="py-4 px-4 text-center font-mono text-slate-400">
                      v{cat.version}
                    </td>

                    <td className="py-4 px-4 sm:px-6 text-center">
                      <div className="flex items-center justify-center gap-1.5">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => openEditModal(cat)}
                          icon={<Edit2 className="w-3.5 h-3.5" />}
                        >
                          Sửa
                        </Button>
                        <Button
                          variant="danger"
                          size="sm"
                          onClick={() => setDeleteTarget(cat)}
                          icon={<Trash2 className="w-3.5 h-3.5" />}
                          title="Xóa ngành hàng chưa có sản phẩm"
                        >
                          Xóa
                        </Button>
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

      {/* Add / Edit Category Modal */}
      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editingCategory ? 'Chỉnh Sửa Ngành Hàng' : 'Thêm Ngành Hàng Mới'}
        description="Quản lý thông tin phân loại sản phẩm và định tuyến mô hình đa hình NoSQL."
      >
        <form onSubmit={handleSaveSubmit} className="space-y-4">
          <Input
            label="Tên ngành hàng"
            required
            value={name}
            onChange={(e) => handleNameChange(e.target.value)}
            placeholder="VD: Điện thoại & Máy tính bảng"
          />

          <Input
            label="Đường dẫn tĩnh (Slug)"
            required
            value={slug}
            onChange={(e) => setSlug(e.target.value.toLowerCase())}
            placeholder="VD: dien-thoai-may-tinh-bang"
          />

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Loại Schema Thuộc Tính (Product Type) <span className="text-rose-500">*</span>
            </label>
            <select
              value={productType}
              onChange={(e) => setProductType(e.target.value as ProductType)}
              className="w-full text-xs bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-slate-800 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-100"
            >
              <option value="ELECTRONICS">ELECTRONICS (Điện tử - Công nghệ)</option>
              <option value="FASHION">FASHION (Thời trang - Phụ kiện)</option>
              <option value="HOME_APPLIANCE">HOME_APPLIANCE (Đồ gia dụng - Đời sống)</option>
            </select>
          </div>

          {editingCategory && (
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Trạng thái
              </label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value as CategoryStatus)}
                className="w-full text-xs bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-slate-800 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-100"
              >
                <option value="ACTIVE">ACTIVE (Đang hoạt động)</option>
                <option value="ARCHIVED">ARCHIVED (Đã lưu trữ)</option>
              </select>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Mô tả ngành hàng
            </label>
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Nhập thông tin giới thiệu ngành hàng..."
              className="w-full text-xs bg-slate-50 border border-slate-200 rounded-xl p-3 text-slate-800 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-100"
            />
          </div>

          <div className="pt-4 flex justify-end gap-3 border-t border-slate-100">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setModalOpen(false)}
            >
              Hủy
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              loading={saving}
            >
              {editingCategory ? 'Lưu thay đổi' : 'Tạo ngành hàng'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Delete Category Modal */}
      <Modal
        isOpen={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Xác Nhận Xóa Ngành Hàng"
        description="Xóa vĩnh viễn ngành hàng khỏi hệ thống nếu không có sản phẩm liên kết."
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-600 leading-relaxed">
            Hành động này sẽ xóa hoàn toàn ngành hàng{' '}
            <span className="font-bold text-slate-900">{deleteTarget?.name}</span> khỏi MongoDB. Nếu ngành hàng vẫn còn sản phẩm đang tham chiếu, máy chủ sẽ từ chối thao tác này theo quy tắc ràng buộc toàn vẹn NoSQL.
          </p>

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <Button variant="outline" size="sm" onClick={() => setDeleteTarget(null)}>
              Hủy bỏ
            </Button>
            <Button
              variant="danger"
              size="sm"
              loading={deleting}
              onClick={handleDeleteConfirm}
            >
              Xác nhận xóa
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
