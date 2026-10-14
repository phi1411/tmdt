import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { User, MapPin, Package, ShieldCheck } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

export const AccountLayout: React.FC = () => {
  const { user } = useAuth();

  const navItems = [
    { to: '/account/profile', label: 'Thông tin cá nhân', icon: User },
    { to: '/account/addresses', label: 'Sổ địa chỉ', icon: MapPin },
    { to: '/orders', label: 'Lịch sử đơn hàng', icon: Package },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
      <div className="flex flex-col lg:flex-row gap-8 items-start">
        {/* Sidebar Nav */}
        <aside className="w-full lg:w-64 bg-white rounded-2xl border border-slate-200 p-5 shadow-sm flex-shrink-0">
          <div className="flex items-center gap-3 pb-5 mb-5 border-b border-slate-100">
            <div className="w-12 h-12 rounded-full bg-brand-100 text-brand-700 font-bold flex items-center justify-center text-lg">
              {user?.name ? user.name.charAt(0).toUpperCase() : 'U'}
            </div>
            <div className="min-w-0">
              <h3 className="font-semibold text-slate-900 text-sm truncate">{user?.name}</h3>
              <p className="text-xs text-slate-400 truncate">{user?.email}</p>
              <div className="mt-1 flex items-center gap-1 text-[11px] text-emerald-600 font-medium">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>{user?.role}</span>
              </div>
            </div>
          </div>

          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-brand-50 text-brand-700 font-semibold shadow-xs'
                        : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                    }`
                  }
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </nav>
        </aside>

        {/* Content Outlet */}
        <section className="flex-1 w-full min-w-0">
          <Outlet />
        </section>
      </div>
    </div>
  );
};
