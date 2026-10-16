import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ShoppingBag,
  User as UserIcon,
  Menu,
  X,
  LogOut,
  Package,
  MapPin,
  ShieldAlert,
  Sparkles,
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { useCart } from '../../contexts/CartContext';
import { Button } from '../ui/Button';
import { SmartSearchBar } from './SmartSearchBar';

export const Navbar: React.FC = () => {
  const navigate = useNavigate();
  const { user, isAuthenticated, isAdmin, isCustomer, logout } = useAuth();
  const { itemCount } = useCart();

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);

  const handleLogout = () => {
    logout();
    setUserDropdownOpen(false);
    navigate('/');
  };

  return (
    <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-sm transition-all">
      {/* Top Promotional Bar */}
      <div className="bg-gradient-to-r from-rose-600 via-rose-500 to-amber-500 text-white text-xs py-1.5 px-4 text-center tracking-wide font-medium flex items-center justify-center gap-1.5">
        <Sparkles className="w-3.5 h-3.5 text-amber-200 fill-amber-200 animate-pulse flex-shrink-0" />
        <span>Chào mừng đến với NovaMart — Miễn phí vận chuyển toàn quốc cho đơn hàng từ 0đ!</span>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 sm:h-20 gap-4">
          {/* Brand Logo */}
          <Link to="/" className="flex items-center gap-2.5 flex-shrink-0 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-600 to-brand-800 flex items-center justify-center text-white shadow-md shadow-brand-500/20 group-hover:scale-105 transition-transform">
              <ShoppingBag className="w-5 h-5" />
            </div>
            <div>
              <span className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900">
                Nova<span className="text-brand-600">mart</span>
              </span>
              <span className="hidden sm:inline-block ml-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">
                E-Commerce
              </span>
            </div>
          </Link>

          {/* Search Bar (Desktop) */}
          <SmartSearchBar className="hidden md:flex flex-1 max-w-lg" />

          {/* Navigation Links & Action Icons */}
          <div className="flex items-center gap-2 sm:gap-4">
            {/* Quick Catalog Link */}
            <Link
              to="/products"
              className="hidden lg:inline-flex text-sm font-medium text-slate-600 hover:text-brand-600 transition-colors px-2 py-1"
            >
              Sản phẩm
            </Link>

            {/* Quick Admin Portal Button for Admin */}
            {isAdmin && (
              <Link
                to="/admin/dashboard"
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-slate-900 hover:bg-brand-600 text-white text-xs font-bold transition-all shadow-xs"
              >
                <ShieldAlert className="w-3.5 h-3.5 text-brand-400" />
                <span>Quản Trị</span>
              </Link>
            )}

            {/* Cart Icon */}
            {isCustomer && (
              <Link
                to="/cart"
                className="relative p-2.5 text-slate-600 hover:text-brand-600 hover:bg-slate-100 rounded-full transition-colors"
                title="Giỏ hàng"
              >
                <ShoppingBag className="w-5 h-5" />
                {itemCount > 0 && (
                  <span className="absolute top-1 right-1 w-5 h-5 rounded-full bg-rose-600 text-white text-xs font-bold flex items-center justify-center animate-in zoom-in shadow-sm">
                    {itemCount > 99 ? '99+' : itemCount}
                  </span>
                )}
              </Link>
            )}

            {/* User Profile / Auth buttons */}
            {isAuthenticated ? (
              <div className="relative">
                <button
                  onClick={() => setUserDropdownOpen(!userDropdownOpen)}
                  className="flex items-center gap-2 p-1.5 sm:px-3 sm:py-2 rounded-full border border-slate-200 hover:border-slate-300 hover:bg-slate-50 transition-colors"
                >
                  <div className="w-8 h-8 rounded-full bg-brand-100 text-brand-700 font-semibold flex items-center justify-center text-sm">
                    {user?.name ? user.name.charAt(0).toUpperCase() : 'U'}
                  </div>
                  <div className="hidden sm:block text-left text-xs">
                    <div className="font-semibold text-slate-800 line-clamp-1 max-w-[100px]">
                      {user?.name}
                    </div>
                    <div className="text-[10px] text-slate-400 uppercase tracking-wider">
                      {user?.role}
                    </div>
                  </div>
                </button>

                {/* Dropdown Menu */}
                {userDropdownOpen && (
                  <div
                    className="absolute right-0 mt-2 w-56 bg-white rounded-2xl shadow-xl border border-slate-100 py-2 z-50 animate-in fade-in zoom-in-95"
                    onMouseLeave={() => setUserDropdownOpen(false)}
                  >
                    <div className="px-4 py-2 border-b border-slate-100">
                      <p className="text-xs text-slate-400">Đã đăng nhập với</p>
                      <p className="text-sm font-semibold text-slate-900 truncate">{user?.email}</p>
                    </div>

                    {isCustomer && (
                      <>
                        <Link
                          to="/orders"
                          onClick={() => setUserDropdownOpen(false)}
                          className="flex items-center gap-2.5 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                        >
                          <Package className="w-4 h-4 text-slate-400" />
                          <span>Đơn hàng của tôi</span>
                        </Link>
                        <Link
                          to="/account/addresses"
                          onClick={() => setUserDropdownOpen(false)}
                          className="flex items-center gap-2.5 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                        >
                          <MapPin className="w-4 h-4 text-slate-400" />
                          <span>Sổ địa chỉ</span>
                        </Link>
                        <Link
                          to="/account/profile"
                          onClick={() => setUserDropdownOpen(false)}
                          className="flex items-center gap-2.5 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                        >
                          <UserIcon className="w-4 h-4 text-slate-400" />
                          <span>Thông tin tài khoản</span>
                        </Link>
                      </>
                    )}

                    {isAdmin && (
                      <Link
                        to="/admin/dashboard"
                        onClick={() => setUserDropdownOpen(false)}
                        className="flex items-center gap-2 px-3 py-2 text-xs font-bold text-white bg-slate-900 hover:bg-brand-700 rounded-xl transition-colors mx-3 my-1.5"
                      >
                        <ShieldAlert className="w-4 h-4 text-brand-400 flex-shrink-0" />
                        <span>Trang Quản Trị (Admin)</span>
                      </Link>
                    )}

                    <div className="border-t border-slate-100 mt-1 pt-1">
                      <button
                        onClick={handleLogout}
                        className="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-rose-600 hover:bg-rose-50 transition-colors text-left"
                      >
                        <LogOut className="w-4 h-4" />
                        <span>Đăng xuất</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link to="/login">
                  <Button variant="ghost" size="sm">
                    Đăng nhập
                  </Button>
                </Link>
                <Link to="/register" className="hidden sm:inline-block">
                  <Button variant="primary" size="sm">
                    Đăng ký
                  </Button>
                </Link>
              </div>
            )}

            {/* Mobile menu trigger */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 text-slate-600 md:hidden hover:bg-slate-100 rounded-lg transition-colors"
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {/* Mobile Search & Menu Overlay */}
        {mobileMenuOpen && (
          <div className="md:hidden py-4 border-t border-slate-100 space-y-4 animate-in fade-in">
            <SmartSearchBar
              className="w-full"
              placeholder="Tìm kiếm sản phẩm..."
              onSearchComplete={() => setMobileMenuOpen(false)}
            />

            <nav className="flex flex-col gap-1 text-sm font-medium">
              <Link
                to="/"
                onClick={() => setMobileMenuOpen(false)}
                className="px-3 py-2 rounded-lg text-slate-700 hover:bg-slate-100"
              >
                Trang chủ
              </Link>
              <Link
                to="/products"
                onClick={() => setMobileMenuOpen(false)}
                className="px-3 py-2 rounded-lg text-slate-700 hover:bg-slate-100"
              >
                Tất cả sản phẩm
              </Link>
              {isCustomer && (
                <>
                  <Link
                    to="/cart"
                    onClick={() => setMobileMenuOpen(false)}
                    className="px-3 py-2 rounded-lg text-slate-700 hover:bg-slate-100 flex items-center justify-between"
                  >
                    <span>Giỏ hàng</span>
                    {itemCount > 0 && (
                      <span className="px-2 py-0.5 rounded-full bg-brand-600 text-white text-xs font-bold">
                        {itemCount}
                      </span>
                    )}
                  </Link>
                  <Link
                    to="/orders"
                    onClick={() => setMobileMenuOpen(false)}
                    className="px-3 py-2 rounded-lg text-slate-700 hover:bg-slate-100"
                  >
                    Đơn hàng của tôi
                  </Link>
                </>
              )}
              {isAdmin && (
                <Link
                  to="/admin/dashboard"
                  onClick={() => setMobileMenuOpen(false)}
                  className="px-3 py-2 rounded-lg text-white font-bold bg-slate-900 hover:bg-brand-700 flex items-center gap-2"
                >
                  <ShieldAlert className="w-4 h-4 text-brand-400" />
                  <span>Trang Quản Trị (Admin)</span>
                </Link>
              )}
            </nav>
          </div>
        )}
      </div>
    </header>
  );
};
