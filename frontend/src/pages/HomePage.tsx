import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  Smartphone,
  Shirt,
  Tv,
  ChevronRight,
  Package,
} from 'lucide-react';
import { catalogApi } from '../api/catalogApi';
import { Category, Product } from '../types/product';
import { ProductCard } from '../components/common/ProductCard';
import { ProductCardSkeleton } from '../components/common/ProductCardSkeleton';

export const HomePage: React.FC = () => {
  const [categories, setCategories] = useState<Category[]>([]);
  const [electronics, setElectronics] = useState<Product[]>([]);
  const [fashion, setFashion] = useState<Product[]>([]);
  const [appliances, setAppliances] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadHomeData = async () => {
      try {
        setLoading(true);
        const [catsRes, elecsRes, fasRes, appRes] = await Promise.all([
          catalogApi.getCategories(),
          catalogApi.getProducts({ productType: 'ELECTRONICS', pageSize: 4, sort: 'latest' }),
          catalogApi.getProducts({ productType: 'FASHION', pageSize: 4, sort: 'latest' }),
          catalogApi.getProducts({ productType: 'HOME_APPLIANCE', pageSize: 4, sort: 'latest' }),
        ]);
        setCategories(catsRes.categories);
        setElectronics(elecsRes.products);
        setFashion(fasRes.products);
        setAppliances(appRes.products);
      } catch (err) {
        console.error('Lỗi khi tải dữ liệu trang chủ:', err);
      } finally {
        setLoading(false);
      }
    };

    loadHomeData();
  }, []);

  const getCategoryIcon = (productType: string) => {
    switch (productType) {
      case 'ELECTRONICS':
        return <Smartphone className="w-6 h-6 text-brand-600" />;
      case 'FASHION':
        return <Shirt className="w-6 h-6 text-purple-600" />;
      case 'HOME_APPLIANCE':
        return <Tv className="w-6 h-6 text-emerald-600" />;
      default:
        return <Package className="w-6 h-6 text-brand-600" />;
    }
  };

  return (
    <div className="space-y-16 sm:space-y-24 pb-16">
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 text-white py-16 sm:py-24 lg:py-28">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-brand-900/30 via-transparent to-transparent pointer-events-none" />
        
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="max-w-3xl space-y-6">
            <div className="inline-flex items-center px-3 py-1 rounded-full bg-brand-500/10 border border-brand-400/20 text-brand-300 text-xs font-semibold tracking-wide uppercase">
              <span>Sàn Thương Mại Điện Tử NoSQL Hiện Đại</span>
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight leading-[1.15]">
              Mua sắm đa ngành, <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-400 to-sky-300">
                trải nghiệm vượt trội.
              </span>
            </h1>

            <p className="text-base sm:text-lg text-slate-300 leading-relaxed max-w-2xl">
              Khám phá hệ sinh thái sản phẩm công nghệ, thời trang xu hướng và đồ gia dụng hiện đại với mô hình dữ liệu MongoDB tối ưu hóa cho tốc độ và tính toàn vẹn giao dịch.
            </p>

            <div className="flex flex-wrap items-center gap-3 pt-2">
              <Link
                to="/products"
                className="px-6 py-3.5 rounded-xl bg-brand-500 hover:bg-brand-400 text-white font-semibold text-sm shadow-lg shadow-brand-500/25 transition-all flex items-center gap-2 active:scale-95"
              >
                <span>Khám phá ngay</span>
                <ArrowRight className="w-4 h-4" />
              </Link>

              <Link
                to="/products?productType=ELECTRONICS"
                className="px-6 py-3.5 rounded-xl bg-white/10 hover:bg-white/15 text-white font-semibold text-sm border border-white/10 backdrop-blur-sm transition-all flex items-center gap-2"
              >
                <span>Đồ điện tử</span>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Categories Bar */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 -mt-8 sm:-mt-12 relative z-20">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6">
          {categories.map((cat) => (
            <Link
              key={cat.id}
              to={`/products?categoryId=${cat.id}`}
              className="group flex items-center gap-4 p-5 sm:p-6 bg-white rounded-2xl border border-slate-200/80 shadow-md hover:shadow-xl hover:border-brand-300 transition-all duration-300"
            >
              <div className="w-14 h-14 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform">
                {getCategoryIcon(cat.productType)}
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-bold text-slate-900 group-hover:text-brand-600 transition-colors text-base truncate">
                  {cat.name}
                </h3>
                <p className="text-xs text-slate-500 line-clamp-1 mt-0.5">
                  {cat.description || `Sản phẩm ngành ${cat.name}`}
                </p>
              </div>
              <ChevronRight className="w-5 h-5 text-slate-400 group-hover:text-brand-600 group-hover:translate-x-1 transition-all" />
            </Link>
          ))}
        </div>
      </section>

      {/* Section 1: Electronics */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        <div className="flex items-end justify-between border-b border-slate-200/80 pb-4">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-brand-600">Đỉnh cao công nghệ</span>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 mt-1">
              Thiết Bị Điện Tử & Phụ Kiện
            </h2>
          </div>
          <Link
            to="/products?productType=ELECTRONICS"
            className="text-xs sm:text-sm font-semibold text-brand-600 hover:text-brand-700 flex items-center gap-1 group"
          >
            <span>Xem tất cả</span>
            <ChevronRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {loading
            ? Array.from({ length: 4 }).map((_, idx) => <ProductCardSkeleton key={idx} />)
            : electronics.map((product) => <ProductCard key={product.id} product={product} />)}
        </div>
      </section>

      {/* Section 2: Fashion */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        <div className="flex items-end justify-between border-b border-slate-200/80 pb-4">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-purple-600">Phong cách thời thượng</span>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 mt-1">
              Thời Trang & Xu Hướng
            </h2>
          </div>
          <Link
            to="/products?productType=FASHION"
            className="text-xs sm:text-sm font-semibold text-purple-600 hover:text-purple-700 flex items-center gap-1 group"
          >
            <span>Xem tất cả</span>
            <ChevronRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {loading
            ? Array.from({ length: 4 }).map((_, idx) => <ProductCardSkeleton key={idx} />)
            : fashion.map((product) => <ProductCard key={product.id} product={product} />)}
        </div>
      </section>

      {/* Section 3: Home Appliance */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        <div className="flex items-end justify-between border-b border-slate-200/80 pb-4">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-600">Tiện nghi không gian sống</span>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 mt-1">
              Thiết Bị Gia Dụng & Nhà Cửa
            </h2>
          </div>
          <Link
            to="/products?productType=HOME_APPLIANCE"
            className="text-xs sm:text-sm font-semibold text-emerald-600 hover:text-emerald-700 flex items-center gap-1 group"
          >
            <span>Xem tất cả</span>
            <ChevronRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {loading
            ? Array.from({ length: 4 }).map((_, idx) => <ProductCardSkeleton key={idx} />)
            : appliances.map((product) => <ProductCard key={product.id} product={product} />)}
        </div>
      </section>
    </div>
  );
};
