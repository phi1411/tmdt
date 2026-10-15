import React, { useState, useEffect, useCallback } from 'react';
import { dashboardApi } from '../api/dashboardApi';
import {
  DashboardSummary,
  RevenueSeriesResponse,
  TopProductsResponse,
  CategoryRevenueResponse,
  OrderStatusResponse,
} from '../types/dashboard';
import { formatVND } from '../utils/formatters';
import {
  DollarSign,
  ShoppingCart,
  Package,
  Users,
  Calendar,
  RotateCcw,
  TrendingUp,
  AlertCircle,
  PieChart as PieChartIcon,
  BarChart3,
  Award,
} from 'lucide-react';
import { Skeleton } from '../components/ui/Skeleton';
import { Button } from '../components/ui/Button';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

type DatePreset = '7days' | '30days' | '90days' | 'thisMonth';

export const AdminDashboardPage: React.FC = () => {
  const [preset, setPreset] = useState<DatePreset>('90days');
  const [interval, setInterval] = useState<'day' | 'month'>('day');

  // Dashboard Data States
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [revenue, setRevenue] = useState<RevenueSeriesResponse | null>(null);
  const [topProducts, setTopProducts] = useState<TopProductsResponse | null>(null);
  const [categoryRevenue, setCategoryRevenue] = useState<CategoryRevenueResponse | null>(null);
  const [orderStatus, setOrderStatus] = useState<OrderStatusResponse | null>(null);

  // Loading States
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Compute exact UTC ISO range for selected preset
  const getDateRange = useCallback(() => {
    const now = new Date();
    let fromDate: Date;
    let toDate = new Date(now.getTime() + 86400000); // 1 day buffer into the future for UTC window

    if (preset === '7days') {
      fromDate = new Date(now.getTime() - 7 * 86400000);
    } else if (preset === '30days') {
      fromDate = new Date(now.getTime() - 30 * 86400000);
    } else if (preset === '90days') {
      fromDate = new Date(now.getTime() - 120 * 86400000); // covers full seed dataset window
    } else {
      // thisMonth (from 1st of current month in VN)
      fromDate = new Date(now.getFullYear(), now.getMonth(), 1);
    }

    const fromISO = fromDate.toISOString().replace(/\.\d{3}Z$/, 'Z');
    const toISO = toDate.toISOString().replace(/\.\d{3}Z$/, 'Z');

    return { from: fromISO, to: toISO };
  }, [preset]);

  const loadDashboardData = useCallback(async () => {
    setLoading(true);
    setError(null);
    const { from, to } = getDateRange();

    try {
      const [sumRes, revRes, topRes, catRes, statusRes] = await Promise.all([
        dashboardApi.getSummary({ from, to }),
        dashboardApi.getRevenue({ from, to, interval }),
        dashboardApi.getTopProducts({ from, to }),
        dashboardApi.getCategoryRevenue({ from, to }),
        dashboardApi.getOrderStatus({ from, to }),
      ]);

      setSummary(sumRes);
      setRevenue(revRes);
      setTopProducts(topRes);
      setCategoryRevenue(catRes);
      setOrderStatus(statusRes);
    } catch (err: any) {
      setError(err?.message || 'Không thể tải dữ liệu thống kê từ MongoDB Aggregation.');
    } finally {
      setLoading(false);
    }
  }, [getDateRange, interval]);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  // Chart Color Palettes
  const STATUS_COLORS: Record<string, string> = {
    COMPLETED: '#10b981', // emerald
    SHIPPING: '#3b82f6', // blue
    CONFIRMED: '#6366f1', // indigo
    PENDING: '#f59e0b', // amber
    CANCELLED: '#ef4444', // rose
    EXPIRED: '#64748b', // slate
  };

  const CATEGORY_COLORS = ['#4f46e5', '#06b6d4', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6'];

  return (
    <div className="space-y-8">
      {/* Top Filter & Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs">
        <div>
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Calendar className="w-5 h-5 text-brand-600" />
            <span>Phạm Vi Báo Cáo Phân Tích</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Dữ liệu tổng hợp từ các MongoDB Aggregation Pipelines trên replica set WiredTiger
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* Preset Buttons */}
          <div className="flex items-center bg-slate-100 p-1 rounded-xl text-xs font-semibold">
            <button
              onClick={() => setPreset('90days')}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                preset === '90days' ? 'bg-white text-slate-900 shadow-xs font-bold text-brand-600' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Toàn bộ dữ liệu
            </button>
            <button
              onClick={() => setPreset('30days')}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                preset === '30days' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              30 ngày qua
            </button>
            <button
              onClick={() => setPreset('7days')}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                preset === '7days' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              7 ngày qua
            </button>
            <button
              onClick={() => setPreset('thisMonth')}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                preset === 'thisMonth' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Tháng này
            </button>
          </div>

          {/* Revenue Interval Toggle */}
          <div className="flex items-center bg-slate-100 p-1 rounded-xl text-xs font-semibold">
            <button
              onClick={() => setInterval('day')}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                interval === 'day' ? 'bg-brand-600 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Theo ngày
            </button>
            <button
              onClick={() => setInterval('month')}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                interval === 'month' ? 'bg-brand-600 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Theo tháng
            </button>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={loadDashboardData}
            loading={loading}
            icon={<RotateCcw className="w-3.5 h-3.5" />}
          >
            Làm mới
          </Button>
        </div>
      </div>

      {/* Global Error Banner */}
      {error && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <div className="font-bold">Lỗi truy vấn MongoDB Aggregation:</div>
            <div className="text-xs mt-0.5">{error}</div>
          </div>
          <Button variant="outline" size="sm" onClick={loadDashboardData}>
            Thử lại
          </Button>
        </div>
      )}

      {/* 4 Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Doanh thu hàng hóa */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
              Doanh Thu Hàng Hóa
            </span>
            <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <DollarSign className="w-5 h-5" />
            </div>
          </div>
          {loading ? (
            <Skeleton className="h-8 w-36" />
          ) : (
            <div>
              <div className="text-2xl font-black text-slate-900 tracking-tight">
                {formatVND(summary?.totalRevenue || 0)}
              </div>
              <div className="text-[11px] text-slate-400 mt-1 flex items-center gap-1">
                <span>Chỉ tính đơn</span>
                <span className="font-semibold text-emerald-600">COMPLETED & PAID</span>
              </div>
            </div>
          )}
        </div>

        {/* Card 2: Tổng đơn hàng */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
              Tổng Đơn Hàng
            </span>
            <div className="w-9 h-9 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
              <ShoppingCart className="w-5 h-5" />
            </div>
          </div>
          {loading ? (
            <Skeleton className="h-8 w-24" />
          ) : (
            <div>
              <div className="text-2xl font-black text-slate-900 tracking-tight">
                {summary?.totalOrders?.toLocaleString('vi-VN') || 0}
              </div>
              <div className="text-[11px] text-slate-400 mt-1">
                Theo thời gian tạo đơn trong kỳ
              </div>
            </div>
          )}
        </div>

        {/* Card 3: Sản phẩm đã bán */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
              Sản Phẩm Đã Bán
            </span>
            <div className="w-9 h-9 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center">
              <Package className="w-5 h-5" />
            </div>
          </div>
          {loading ? (
            <Skeleton className="h-8 w-24" />
          ) : (
            <div>
              <div className="text-2xl font-black text-slate-900 tracking-tight">
                {summary?.totalProductsSold?.toLocaleString('vi-VN') || 0}
              </div>
              <div className="text-[11px] text-slate-400 mt-1">
                Khối lượng xuất kho giao thành công
              </div>
            </div>
          )}
        </div>

        {/* Card 4: Tổng khách hàng */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
              Tổng Khách Hàng
            </span>
            <div className="w-9 h-9 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
              <Users className="w-5 h-5" />
            </div>
          </div>
          {loading ? (
            <Skeleton className="h-8 w-24" />
          ) : (
            <div>
              <div className="text-2xl font-black text-slate-900 tracking-tight">
                {summary?.totalCustomers?.toLocaleString('vi-VN') || 0}
              </div>
              <div className="text-[11px] text-slate-400 mt-1">
                Toàn hệ thống vai trò CUSTOMER
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Main Revenue Over Time Chart */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-brand-600" />
              <span>Biểu Đồ Doanh Thu Theo Thời Gian</span>
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Chuỗi thời gian phân nhóm theo {interval === 'day' ? 'ngày' : 'tháng'} (MongoDB Group & Sort Pipeline)
            </p>
          </div>
          <span className="text-xs font-mono text-slate-400">Đơn vị: VND</span>
        </div>

        {loading ? (
          <Skeleton className="h-72 w-full" />
        ) : !revenue || revenue.series.length === 0 ? (
          <div className="h-64 flex flex-col items-center justify-center text-slate-400 text-sm">
            <TrendingUp className="w-8 h-8 text-slate-300 mb-2" />
            <span>Không có dữ liệu doanh thu trong khoảng thời gian này.</span>
          </div>
        ) : (
          <div className="h-72 w-full pt-4">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={revenue.series} margin={{ top: 10, right: 20, left: 20, bottom: 0 }}>
                <defs>
                  <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#4f46e5" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis
                  dataKey="bucket"
                  stroke="#94a3b8"
                  fontSize={11}
                  tickLine={false}
                  axisLine={{ stroke: '#e2e8f0' }}
                />
                <YAxis
                  stroke="#94a3b8"
                  fontSize={11}
                  tickLine={false}
                  axisLine={{ stroke: '#e2e8f0' }}
                  tickFormatter={(val) => `${(val / 1000000).toFixed(1)}M`}
                />
                <Tooltip
                  formatter={(val: any) => [formatVND(Number(val)), 'Doanh thu hàng hóa']}
                  labelFormatter={(lbl) => `Kỳ: ${lbl}`}
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    borderColor: '#334155',
                    borderRadius: '0.75rem',
                    color: '#fff',
                    fontSize: '12px',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="revenue"
                  stroke="#4f46e5"
                  strokeWidth={2.5}
                  fillOpacity={1}
                  fill="url(#revenueGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Row 2: Top 5 Products & Category Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Top 5 Products Sold */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Award className="w-5 h-5 text-amber-500" />
              <span>Top 5 Sản Phẩm Bán Chạy Nhất</span>
            </h3>
            <span className="text-xs text-slate-400 font-mono">Xếp theo số lượng</span>
          </div>

          {loading ? (
            <Skeleton className="h-64 w-full" />
          ) : !topProducts || topProducts.items.length === 0 ? (
            <div className="h-56 flex flex-col items-center justify-center text-slate-400 text-sm">
              <Award className="w-8 h-8 text-slate-300 mb-2" />
              <span>Chưa có sản phẩm nào được bán hoàn tất trong kỳ.</span>
            </div>
          ) : (
            <div className="space-y-3">
              {topProducts.items.map((item, idx) => (
                <div
                  key={item.productId}
                  className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/60 flex items-center justify-between gap-3 text-xs"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span
                      className={`w-6 h-6 rounded-full flex items-center justify-center font-bold text-xs flex-shrink-0 ${
                        idx === 0
                          ? 'bg-amber-400 text-slate-900'
                          : idx === 1
                          ? 'bg-slate-300 text-slate-800'
                          : idx === 2
                          ? 'bg-amber-700/80 text-white'
                          : 'bg-slate-200 text-slate-600'
                      }`}
                    >
                      {idx + 1}
                    </span>
                    <span className="font-semibold text-slate-800 truncate" title={item.productName}>
                      {item.productName}
                    </span>
                  </div>

                  <div className="text-right flex-shrink-0 space-y-0.5">
                    <div className="font-bold text-slate-900">{formatVND(item.revenue)}</div>
                    <div className="text-[10px] text-slate-500 font-medium">
                      Đã bán: <span className="text-brand-600 font-bold">{item.quantity}</span> chiếc
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Category Revenue Distribution */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <PieChartIcon className="w-5 h-5 text-brand-600" />
              <span>Doanh Thu Theo Ngành Hàng</span>
            </h3>
            <span className="text-xs text-slate-400 font-mono">Tỷ trọng doanh số</span>
          </div>

          {loading ? (
            <Skeleton className="h-64 w-full" />
          ) : !categoryRevenue || categoryRevenue.items.length === 0 ? (
            <div className="h-56 flex flex-col items-center justify-center text-slate-400 text-sm">
              <PieChartIcon className="w-8 h-8 text-slate-300 mb-2" />
              <span>Không có dữ liệu ngành hàng trong kỳ.</span>
            </div>
          ) : (
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={categoryRevenue.items}
                    dataKey="revenue"
                    nameKey="categoryName"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    innerRadius={45}
                    paddingAngle={3}
                  >
                    {categoryRevenue.items.map((_, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={CATEGORY_COLORS[index % CATEGORY_COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(val: any) => [formatVND(Number(val)), 'Doanh thu']}
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      borderColor: '#334155',
                      borderRadius: '0.75rem',
                      color: '#fff',
                      fontSize: '12px',
                    }}
                  />
                  <Legend
                    formatter={(val) => <span className="text-xs text-slate-600">{val}</span>}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>

      {/* Row 3: Order Status Distribution */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-slate-100">
          <div>
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-indigo-600" />
              <span>Phân Bố Trạng Thái Đơn Hàng</span>
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Thống kê đầy đủ 6 trạng thái vòng đời đơn hàng theo ngày tạo (createdAt)
            </p>
          </div>
          <span className="text-xs text-slate-400 font-mono">Đơn vị: Đơn</span>
        </div>

        {loading ? (
          <Skeleton className="h-64 w-full" />
        ) : !orderStatus || orderStatus.items.length === 0 ? (
          <div className="h-56 flex flex-col items-center justify-center text-slate-400 text-sm">
            <BarChart3 className="w-8 h-8 text-slate-300 mb-2" />
            <span>Không có đơn hàng nào trong khoảng thời gian này.</span>
          </div>
        ) : (
          <div className="h-64 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={orderStatus.items} margin={{ top: 10, right: 20, left: 10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis
                  dataKey="status"
                  stroke="#94a3b8"
                  fontSize={11}
                  tickLine={false}
                  axisLine={{ stroke: '#e2e8f0' }}
                />
                <YAxis
                  stroke="#94a3b8"
                  fontSize={11}
                  tickLine={false}
                  axisLine={{ stroke: '#e2e8f0' }}
                  allowDecimals={false}
                />
                <Tooltip
                  formatter={(val: any) => [`${val} đơn hàng`, 'Số lượng']}
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    borderColor: '#334155',
                    borderRadius: '0.75rem',
                    color: '#fff',
                    fontSize: '12px',
                  }}
                />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {orderStatus.items.map((entry, index) => (
                    <Cell
                      key={`status-cell-${index}`}
                      fill={STATUS_COLORS[entry.status] || '#64748b'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
};
