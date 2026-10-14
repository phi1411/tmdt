import React from 'react';
import { Navigate, useLocation, Outlet, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Loader2, ShieldAlert } from 'lucide-react';
import { Button } from '../components/ui/Button';

interface ProtectedRouteProps {
  requireCustomer?: boolean;
  requireAdmin?: boolean;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  requireCustomer = false,
  requireAdmin = false,
}) => {
  const { isAuthenticated, isCustomer, isAdmin, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center gap-3">
        <Loader2 className="w-8 h-8 text-brand-600 animate-spin" />
        <span className="text-sm text-slate-500 font-medium">Đang xác thực quyền truy cập...</span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <Navigate
        to={`/login?redirect=${encodeURIComponent(location.pathname + location.search)}`}
        replace
      />
    );
  }

  if (requireAdmin && !isAdmin) {
    return (
      <div className="max-w-xl mx-auto my-20 p-8 bg-white rounded-3xl border border-rose-200 text-center shadow-lg shadow-rose-500/5 space-y-4">
        <div className="w-14 h-14 bg-rose-50 text-rose-600 rounded-2xl flex items-center justify-center mx-auto">
          <ShieldAlert className="w-8 h-8" />
        </div>
        <h2 className="text-xl font-extrabold text-slate-900">Truy Cập Bị Từ Chối (403)</h2>
        <p className="text-sm text-slate-600 leading-relaxed">
          Tài khoản của bạn không có vai trò <span className="font-bold text-slate-900">ADMIN</span> để truy cập vào hệ thống Quản Trị Viên Novamart.
        </p>
        <div className="pt-2">
          <Link to="/">
            <Button variant="primary" size="md">
              Quay lại Trang Chủ Khách Hàng
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  if (requireCustomer && !isCustomer) {
    return (
      <div className="max-w-xl mx-auto my-20 p-8 bg-white rounded-3xl border border-amber-200 text-center shadow-lg shadow-amber-500/5 space-y-4">
        <div className="w-14 h-14 bg-amber-50 text-amber-600 rounded-2xl flex items-center justify-center mx-auto">
          <ShieldAlert className="w-8 h-8" />
        </div>
        <h2 className="text-xl font-extrabold text-slate-900">Chức Năng Dành Cho Khách Hàng</h2>
        <p className="text-sm text-slate-600 leading-relaxed">
          Tài khoản Quản trị viên (Admin) không thực hiện mua sắm, giỏ hàng hoặc đặt đơn hàng theo quy tắc nghiệp vụ hệ thống.
        </p>
        <div className="pt-2 flex justify-center gap-3">
          <Link to="/admin/dashboard">
            <Button variant="primary" size="md">
              Vào Trang Quản Trị
            </Button>
          </Link>
          <Link to="/">
            <Button variant="outline" size="md">
              Về Trang Chủ
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return <Outlet />;
};
