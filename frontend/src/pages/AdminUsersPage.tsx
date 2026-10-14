import React, { useState, useEffect, useCallback } from 'react';
import { adminUsersApi } from '../api/adminUsersApi';
import { AdminUser } from '../types/adminUser';
import { PaginationMeta } from '../types/api';
import { formatDateTime } from '../utils/formatters';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Pagination } from '../components/ui/Pagination';
import { Skeleton } from '../components/ui/Skeleton';
import { useToast } from '../contexts/ToastContext';
import {
  Users,
  Search,
  Filter,
  RotateCcw,
  UserCheck,
  UserX,
  AlertCircle,
  Lock,
} from 'lucide-react';

export const AdminUsersPage: React.FC = () => {
  const { success: toastSuccess, error: toastError, warning: toastWarning } = useToast();

  const [users, setUsers] = useState<AdminUser[]>([]);
  const [meta, setMeta] = useState<PaginationMeta>({
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 0,
  });

  // Filters
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [appliedSearchQuery, setAppliedSearchQuery] = useState<string>('');
  const [selectedRole, setSelectedRole] = useState<'CUSTOMER' | 'ADMIN' | ''>('');
  const [selectedStatus, setSelectedStatus] = useState<'ACTIVE' | 'BLOCKED' | ''>('');
  const [currentPage, setCurrentPage] = useState<number>(1);

  // Loading States
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Status Modal States
  const [targetUser, setTargetUser] = useState<AdminUser | null>(null);
  const [actionType, setActionType] = useState<'BLOCK' | 'REACTIVATE'>('BLOCK');
  const [updating, setUpdating] = useState<boolean>(false);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await adminUsersApi.getList({
        q: appliedSearchQuery || undefined,
        role: selectedRole || undefined,
        status: selectedStatus || undefined,
        page: currentPage,
        pageSize: 20,
      });

      setUsers(res.users);
      setMeta(res.meta);
    } catch (err: any) {
      setError(err?.message || 'Không thể tải danh sách tài khoản người dùng.');
    } finally {
      setLoading(false);
    }
  }, [appliedSearchQuery, selectedRole, selectedStatus, currentPage]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
    setAppliedSearchQuery(searchQuery.trim());
  };

  const handleResetFilters = () => {
    setSearchQuery('');
    setAppliedSearchQuery('');
    setSelectedRole('');
    setSelectedStatus('');
    setCurrentPage(1);
  };

  const openStatusModal = (user: AdminUser, type: 'BLOCK' | 'REACTIVATE') => {
    if (user.role === 'ADMIN') {
      toastWarning('Tài khoản Quản trị viên (ADMIN) được bảo vệ, không thể thay đổi trạng thái từ giao diện này.');
      return;
    }
    setTargetUser(user);
    setActionType(type);
  };

  const handleStatusConfirm = async () => {
    if (!targetUser) return;
    setUpdating(true);
    const newStatus = actionType === 'BLOCK' ? 'BLOCKED' : 'ACTIVE';

    try {
      await adminUsersApi.updateStatus(targetUser.id, {
        status: newStatus,
        expectedVersion: targetUser.version,
      });

      toastSuccess(
        actionType === 'BLOCK'
          ? `Đã khóa tài khoản khách hàng "${targetUser.name}". Phiên đăng nhập sẽ bị thu hồi ngay lập tức.`
          : `Đã mở khóa tài khoản khách hàng "${targetUser.name}".`
      );

      setTargetUser(null);
      await fetchUsers();
    } catch (err: any) {
      if (err?.code === 'CONFLICT' || err?.status === 409) {
        toastWarning('Tài khoản đã có cập nhật hoặc xung đột phiên bản. Đang tải lại dữ liệu...');
        await fetchUsers();
      } else {
        toastError(err?.message || 'Không thể cập nhật trạng thái người dùng.');
      }
    } finally {
      setUpdating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Users className="w-5 h-5 text-brand-600" />
              <span>Quản Lý Tài Khoản (User Management)</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Kiểm soát tài khoản người dùng, giám sát bảo mật phân quyền và thu hồi phiên truy cập
            </p>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={fetchUsers}
            loading={loading}
            icon={<RotateCcw className="w-3.5 h-3.5" />}
          >
            Làm mới
          </Button>
        </div>

        {/* Filters */}
        <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center gap-3">
          <form onSubmit={handleSearchSubmit} className="flex items-center gap-2 flex-1 min-w-[240px]">
            <div className="relative flex-1">
              <input
                type="text"
                placeholder="Tìm kiếm họ tên hoặc email khách hàng..."
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

          {/* Role Filter */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-500 flex items-center gap-1">
              <Filter className="w-3.5 h-3.5" />
              Vai trò:
            </span>
            <select
              value={selectedRole}
              onChange={(e) => {
                setSelectedRole(e.target.value as any);
                setCurrentPage(1);
              }}
              className="text-xs bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-800 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-100"
            >
              <option value="">Tất cả vai trò</option>
              <option value="CUSTOMER">CUSTOMER (Khách hàng)</option>
              <option value="ADMIN">ADMIN (Quản trị viên)</option>
            </select>
          </div>

          {/* Status Filter */}
          <div className="flex items-center gap-2">
            <select
              value={selectedStatus}
              onChange={(e) => {
                setSelectedStatus(e.target.value as any);
                setCurrentPage(1);
              }}
              className="text-xs bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-800 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-100"
            >
              <option value="">Tất cả trạng thái</option>
              <option value="ACTIVE">ACTIVE (Hoạt động)</option>
              <option value="BLOCKED">BLOCKED (Đã khóa)</option>
            </select>
          </div>

          {(appliedSearchQuery || selectedRole || selectedStatus) && (
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
            <div className="font-bold">Lỗi tải danh sách người dùng:</div>
            <div className="text-xs mt-0.5">{error}</div>
          </div>
          <Button variant="outline" size="sm" onClick={fetchUsers}>
            Thử lại
          </Button>
        </div>
      )}

      {/* Users Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200/80 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-3.5 px-4 sm:px-6">Họ Và Tên</th>
                <th className="py-3.5 px-4">Email</th>
                <th className="py-3.5 px-4">Số Điện Thoại</th>
                <th className="py-3.5 px-4 text-center">Vai Trò</th>
                <th className="py-3.5 px-4 text-center">Trạng Thái</th>
                <th className="py-3.5 px-4 text-center">Phiên Bản (OCC)</th>
                <th className="py-3.5 px-4">Ngày Tạo</th>
                <th className="py-3.5 px-4 sm:px-6 text-center">Hành Động</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
              {loading ? (
                Array.from({ length: 6 }).map((_, idx) => (
                  <tr key={idx}>
                    <td className="py-4 px-4 sm:px-6"><Skeleton className="h-4 w-32" /></td>
                    <td className="py-4 px-4"><Skeleton className="h-4 w-40" /></td>
                    <td className="py-4 px-4"><Skeleton className="h-4 w-24" /></td>
                    <td className="py-4 px-4 text-center"><Skeleton className="h-5 w-16 mx-auto" /></td>
                    <td className="py-4 px-4 text-center"><Skeleton className="h-5 w-16 mx-auto" /></td>
                    <td className="py-4 px-4 text-center"><Skeleton className="h-4 w-8 mx-auto" /></td>
                    <td className="py-4 px-4"><Skeleton className="h-4 w-28" /></td>
                    <td className="py-4 px-4 sm:px-6 text-center"><Skeleton className="h-6 w-20 mx-auto" /></td>
                  </tr>
                ))
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    <Users className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                    <span>Không tìm thấy tài khoản người dùng nào.</span>
                  </td>
                </tr>
              ) : (
                users.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="py-4 px-4 sm:px-6 font-bold text-slate-900">
                      {u.name}
                    </td>

                    <td className="py-4 px-4 font-mono text-slate-600">
                      {u.email}
                    </td>

                    <td className="py-4 px-4 text-slate-500 font-mono">
                      {u.phone || <span className="text-slate-300 italic">Chưa có</span>}
                    </td>

                    <td className="py-4 px-4 text-center">
                      {u.role === 'ADMIN' ? (
                        <Badge variant="primary">ADMIN</Badge>
                      ) : (
                        <Badge variant="neutral">CUSTOMER</Badge>
                      )}
                    </td>

                    <td className="py-4 px-4 text-center">
                      {u.status === 'ACTIVE' ? (
                        <Badge variant="success">Hoạt động</Badge>
                      ) : (
                        <Badge variant="danger">Đã khóa</Badge>
                      )}
                    </td>

                    <td className="py-4 px-4 text-center font-mono text-slate-400">
                      v{u.version}
                    </td>

                    <td className="py-4 px-4 text-slate-500">
                      {formatDateTime(u.createdAt)}
                    </td>

                    <td className="py-4 px-4 sm:px-6 text-center">
                      {u.role === 'ADMIN' ? (
                        <span
                          className="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-400 px-2 py-1 rounded bg-slate-100"
                          title="Tài khoản quản trị viên được bảo vệ bất biến"
                        >
                          <Lock className="w-3 h-3 text-slate-400" />
                          <span>Bảo vệ</span>
                        </span>
                      ) : u.status === 'ACTIVE' ? (
                        <Button
                          variant="danger"
                          size="sm"
                          onClick={() => openStatusModal(u, 'BLOCK')}
                          icon={<UserX className="w-3.5 h-3.5" />}
                        >
                          Khóa
                        </Button>
                      ) : (
                        <Button
                          variant="primary"
                          size="sm"
                          className="bg-emerald-600 hover:bg-emerald-700 text-white"
                          onClick={() => openStatusModal(u, 'REACTIVATE')}
                          icon={<UserCheck className="w-3.5 h-3.5" />}
                        >
                          Mở khóa
                        </Button>
                      )}
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

      {/* Status Confirmation Modal */}
      <Modal
        isOpen={!!targetUser}
        onClose={() => setTargetUser(null)}
        title={actionType === 'BLOCK' ? 'Xác Nhận Khóa Tài Khoản' : 'Xác Nhận Mở Khóa Tài Khoản'}
        description="Điều chỉnh trạng thái tài khoản người dùng theo cơ chế Token Revocation NoSQL."
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-600 leading-relaxed">
            {actionType === 'BLOCK' ? (
              <>
                Bạn có chắc chắn muốn <span className="font-bold text-rose-600">KHÓA</span> tài khoản của khách hàng{' '}
                <span className="font-bold text-slate-900">{targetUser?.name}</span> ({targetUser?.email}) không? Khi bị khóa, hệ thống sẽ tăng <code className="bg-slate-100 px-1 py-0.5 rounded text-slate-800">tokenVersion</code> và lập tức vô hiệu hóa mọi phiên đăng nhập của người dùng này.
              </>
            ) : (
              <>
                Bạn có chắc chắn muốn <span className="font-bold text-emerald-600">MỞ KHÓA</span> tài khoản cho khách hàng{' '}
                <span className="font-bold text-slate-900">{targetUser?.name}</span> ({targetUser?.email}) không? Người dùng sẽ có thể đăng nhập và tiếp tục mua hàng bình thường.
              </>
            )}
          </p>

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <Button variant="outline" size="sm" onClick={() => setTargetUser(null)}>
              Hủy bỏ
            </Button>
            <Button
              variant={actionType === 'BLOCK' ? 'danger' : 'primary'}
              size="sm"
              className={actionType === 'REACTIVATE' ? 'bg-emerald-600 hover:bg-emerald-700 text-white' : ''}
              loading={updating}
              onClick={handleStatusConfirm}
            >
              {actionType === 'BLOCK' ? 'Xác nhận khóa' : 'Xác nhận mở khóa'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
