import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ShoppingCart,
  ChevronRight,
  ShieldCheck,
  Truck,
  RotateCcw,
  Star,
  Zap,
  ImageOff,
} from 'lucide-react';
import { catalogApi } from '../api/catalogApi';
import { Product } from '../types/product';
import { formatVND } from '../utils/formatters';
import { ProductReviews } from '../components/reviews/ProductReviews';
import { Skeleton } from '../components/ui/Skeleton';
import { ErrorState } from '../components/ui/ErrorState';
import { ProductPurchaseModal, PurchaseIntent } from '../components/common/ProductPurchaseModal';
import { hasPurchasableStock } from '../utils/productSelection';

export const ProductDetailPage: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();

  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedImageIndex, setSelectedImageIndex] = useState<number>(0);
  const [purchaseIntent, setPurchaseIntent] = useState<PurchaseIntent | null>(null);

  useEffect(() => {
    if (!slug) return;
    const loadDetail = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await catalogApi.getProductBySlug(slug);
        setProduct(data);
        setSelectedImageIndex(0);
        setPurchaseIntent(null);

      } catch (err: any) {
        setError(err?.message || 'Không tìm thấy sản phẩm này hoặc sản phẩm đã ngừng kinh doanh.');
      } finally {
        setLoading(false);
      }
    };

    loadDetail();
  }, [slug]);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
        <Skeleton className="h-4 w-1/4 rounded" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
          <Skeleton className="aspect-square w-full rounded-2xl" />
          <div className="space-y-4">
            <Skeleton className="h-8 w-3/4 rounded-lg" />
            <Skeleton className="h-6 w-1/3 rounded-lg" />
            <Skeleton className="h-24 w-full rounded-xl" />
            <Skeleton className="h-12 w-1/2 rounded-xl" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <ErrorState
          title="Sản phẩm không khả dụng"
          message={error || 'Sản phẩm không tồn tại hoặc đã bị ẩn khỏi danh mục.'}
          onRetry={() => window.location.reload()}
        />
      </div>
    );
  }

  const currentPrice = product.price;
  const isOutOfStock = !hasPurchasableStock(product);

  const images = product.images && product.images.length > 0 ? product.images : [];
  const currentImageUrl = images[selectedImageIndex] || '';

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-10 space-y-10">
      {/* Shopee Breadcrumb */}
      <nav className="flex items-center gap-2 text-xs text-slate-500 font-medium">
        <Link to="/" className="hover:text-brand-600 transition-colors">
          Trang chủ
        </Link>
        <ChevronRight className="w-3.5 h-3.5" />
        <Link to="/products" className="hover:text-brand-600 transition-colors">
          Sản phẩm
        </Link>
        {product.category && (
          <>
            <ChevronRight className="w-3.5 h-3.5" />
            <Link
              to={`/products?categoryId=${product.category.id}`}
              className="hover:text-brand-600 transition-colors"
            >
              {product.category.name}
            </Link>
          </>
        )}
        <ChevronRight className="w-3.5 h-3.5" />
        <span className="text-slate-800 truncate max-w-[260px]">{product.name}</span>
      </nav>

      {/* Main Product Showcase (Shopee Layout) */}
      <div className="bg-white rounded-3xl border border-slate-200/90 shadow-sm p-6 sm:p-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-start">
          {/* Left Column: Image Gallery (5 cols) */}
          <div className="lg:col-span-5 space-y-4">
            <div className="aspect-square w-full rounded-2xl bg-slate-50 border border-slate-200/80 overflow-hidden shadow-inner flex items-center justify-center p-4 relative group">
              {currentImageUrl ? (
                <img
                  src={currentImageUrl}
                  alt={product.name}
                  className="w-full h-full object-contain object-center transition-all duration-300 group-hover:scale-105"
                />
              ) : (
                <div className="flex flex-col items-center gap-2 text-slate-400">
                  <ImageOff className="w-12 h-12 stroke-[1.5]" />
                  <span className="text-xs">Chưa có ảnh mô tả</span>
                </div>
              )}

            </div>

            {/* Thumbnails */}
            {images.length > 1 && (
              <div className="flex gap-3 overflow-x-auto pb-2">
                {images.map((img, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setSelectedImageIndex(idx)}
                    className={`relative w-20 h-20 rounded-xl bg-slate-50 border-2 overflow-hidden flex-shrink-0 transition-all ${
                      selectedImageIndex === idx
                        ? 'border-brand-600 ring-2 ring-brand-100 shadow-sm'
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <img src={img} alt={`Thumbnail ${idx}`} className="w-full h-full object-contain p-1" />
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Right Column: Title, Ratings, Pricing, Variations, Actions (7 cols) */}
          <div className="lg:col-span-7 space-y-6">
            {/* Title & Brand */}
            <div className="space-y-2.5">
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500 font-mono">Mã: {product.sku}</span>
              </div>

              <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight leading-snug">
                {product.name}
              </h1>

              {/* Shopee Rating Bar */}
              <div className="flex flex-wrap items-center gap-4 text-xs pt-1 pb-2 border-b border-slate-100">
                <div className="flex items-center gap-1.5">
                  <span className="font-extrabold text-brand-600 text-sm border-b border-brand-600">
                    {product.ratingSummary?.totalReviews ? product.ratingSummary.averageRating.toFixed(1) : 'Chưa có'}
                  </span>
                  <div className="flex text-amber-400">
                    {[1, 2, 3, 4, 5].map((s) => (
                      <Star key={s} className={`w-3.5 h-3.5 ${s <= (product.ratingSummary?.averageRating ?? 0) ? 'fill-amber-400 text-amber-400' : 'text-slate-200'}`} />
                    ))}
                  </div>
                </div>

                <span className="text-slate-300">|</span>

                <div className="text-slate-600">
                  <span className="font-bold text-slate-900 text-sm border-b border-slate-900 mr-1">
                    {product.ratingSummary?.totalReviews ?? 0}
                  </span>
                  Đánh Giá
                </div>

                <span className="text-slate-300">|</span>


              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
              <span className="text-3xl font-bold text-rose-600">{formatVND(currentPrice)}</span>
            </div>

            {/* Shopee Shipping Info */}
            <div className="p-4 rounded-xl bg-slate-50/60 border border-slate-200/60 flex items-start gap-3.5 text-xs text-slate-600">
              <Truck className="w-5 h-5 text-brand-600 flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <div className="font-bold text-slate-800 flex items-center gap-2">
                  <span>Vận Chuyển Toàn Quốc</span>
                  <span className="bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded text-[10px] font-bold">
                    PHÍ GIAO HÀNG TẠI THANH TOÁN
                  </span>
                </div>
                <p className="text-slate-500 leading-relaxed">
                  Xem phí giao hàng và tổng thanh toán trước khi xác nhận đặt hàng.
                </p>
              </div>
            </div>

            <p className="text-sm text-slate-500">
              {isOutOfStock ? 'Sản phẩm hiện đã hết hàng.' : 'Chọn phân loại và số lượng khi bấm thêm vào giỏ hoặc mua ngay.'}
            </p>

            {/* Shopee Dual Action Buttons (Thêm vào giỏ & Mua ngay) */}
            <div className="pt-4 flex flex-col sm:flex-row items-center gap-3.5">
              <button
                type="button"
                onClick={() => setPurchaseIntent('cart')}
                disabled={isOutOfStock}
                className="w-full sm:flex-1 py-3.5 px-6 rounded-2xl border-2 border-rose-600 bg-rose-50/70 text-rose-700 hover:bg-rose-100 font-bold text-sm sm:text-base flex items-center justify-center gap-2 transition-all shadow-xs disabled:opacity-50"
              >
                <ShoppingCart className="w-5 h-5 text-rose-600" />
                <span>Thêm Vào Giỏ Hàng</span>
              </button>

              <button
                type="button"
                onClick={() => setPurchaseIntent('buy')}
                disabled={isOutOfStock}
                className="w-full sm:flex-1 py-3.5 px-6 rounded-2xl bg-rose-600 hover:bg-rose-700 text-white font-bold text-sm sm:text-base flex items-center justify-center gap-2 transition-all shadow-md shadow-rose-600/30 disabled:opacity-50"
              >
                <Zap className="w-5 h-5" />
                <span>Mua Ngay</span>
              </button>
            </div>

            {/* Shopee Policy Safeguards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-6 border-t border-slate-100 text-xs text-slate-600">
              <div className="flex items-center gap-2">
                <RotateCcw className="w-4 h-4 text-rose-600" />
                <span>Xem chính sách đổi trả</span>
              </div>
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <span>Thông tin sản phẩm rõ ràng</span>
              </div>
              <div className="flex items-center gap-2">
                <Truck className="w-4 h-4 text-blue-600" />
                <span>Kiểm tra phí khi đặt hàng</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Description & Technical Specifications Tabs */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Description */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-white p-6 sm:p-8 rounded-3xl border border-slate-200/90 shadow-sm space-y-4">
            <h2 className="text-lg font-extrabold text-slate-900 tracking-tight uppercase border-b border-slate-100 pb-3">
              Mô tả chi tiết sản phẩm
            </h2>
            <div className="prose prose-slate max-w-none text-sm text-slate-700 leading-relaxed whitespace-pre-line">
              {product.description || 'Chưa có thông tin mô tả chi tiết cho sản phẩm này.'}
            </div>
          </div>
        </div>

        {/* Technical Specifications (Polymorphic attributes display) */}
        <div className="space-y-4">
          <div className="bg-white rounded-3xl border border-slate-200/90 p-6 shadow-sm space-y-4">
            <h2 className="text-lg font-extrabold text-slate-900 tracking-tight uppercase border-b border-slate-100 pb-3">
              Thông số kỹ thuật
            </h2>
            <div className="space-y-2.5 text-xs">
              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-slate-500 font-medium">Ngành hàng</span>
                <span className="font-semibold text-slate-900">{product.productType}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-slate-500 font-medium">Thương hiệu</span>
                <span className="font-semibold text-slate-900">{product.brand || '--'}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-slate-500 font-medium">Mã SKU</span>
                <span className="font-mono text-slate-900">{product.sku}</span>
              </div>

              {/* Dynamic Polymorphic Attributes Renderer */}
              {Object.entries(product.attributes || {}).map(([key, val]) => {
                if (val === null || val === undefined || typeof val === 'object') return null;
                const labelMap: Record<string, string> = {
                  ram: 'RAM',
                  storage: 'Bộ nhớ lưu trữ',
                  chip: 'Vi xử lý (Chip)',
                  screen: 'Màn hình',
                  battery: 'Dung lượng pin',
                  material: 'Chất liệu',
                  gender: 'Giới tính',
                  power: 'Công suất',
                  capacity: 'Dung lượng / Thể tích',
                  voltage: 'Điện áp',
                  warranty: 'Bảo hành',
                };
                return (
                  <div key={key} className="flex justify-between py-1.5 border-b border-slate-100">
                    <span className="text-slate-500 font-medium">{labelMap[key] || key}</span>
                    <span className="font-semibold text-slate-900 text-right">{String(val)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      <ProductReviews key={product.id} slug={product.id} />
      {purchaseIntent && <ProductPurchaseModal key={product.id} product={product} intent={purchaseIntent} onClose={() => setPurchaseIntent(null)} />}
    </div>
  );
};
