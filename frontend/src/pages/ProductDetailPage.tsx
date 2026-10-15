import React, { useEffect, useState, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ShoppingCart,
  ChevronRight,
  ShieldCheck,
  Truck,
  RotateCcw,
  Plus,
  Minus,
  Check,
  ImageOff,
  Star,
} from 'lucide-react';
import { catalogApi } from '../api/catalogApi';
import { Product } from '../types/product';
import { formatVND } from '../utils/formatters';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { useCart } from '../contexts/CartContext';
import { useToast } from '../contexts/ToastContext';
import { Skeleton } from '../components/ui/Skeleton';
import { ErrorState } from '../components/ui/ErrorState';

export const ProductDetailPage: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const { addToCart } = useCart();
  const { warning: toastWarning } = useToast();

  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedImageIndex, setSelectedImageIndex] = useState<number>(0);
  const [quantity, setQuantity] = useState<number>(1);

  // Dynamic tier variation selection states: mapping tierIndex -> option string
  const [selectedTiers, setSelectedTiers] = useState<Record<number, string>>({});

  // Legacy Fashion selection states
  const [selectedSize, setSelectedSize] = useState<string>('');
  const [selectedColor, setSelectedColor] = useState<string>('');
  const [addingToCart, setAddingToCart] = useState<boolean>(false);

  useEffect(() => {
    if (!slug) return;
    const loadDetail = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await catalogApi.getProductBySlug(slug);
        setProduct(data);
        setSelectedImageIndex(0);
        setQuantity(1);

        // Pre-select first options if tierVariations available
        if (data.tierVariations && data.tierVariations.length > 0) {
          const initial: Record<number, string> = {};
          data.tierVariations.forEach((t, idx) => {
            if (t.options && t.options.length > 0) {
              initial[idx] = t.options[0];
            }
          });
          setSelectedTiers(initial);
        } else if (data.productType === 'FASHION') {
          // Fallback legacy
          if (Array.isArray(data.attributes.sizes) && data.attributes.sizes.length > 0) {
            setSelectedSize(data.attributes.sizes[0]);
          }
          if (Array.isArray(data.attributes.colors) && data.attributes.colors.length > 0) {
            setSelectedColor(data.attributes.colors[0]);
          }
        }
      } catch (err: any) {
        setError(err?.message || 'Không tìm thấy sản phẩm này hoặc sản phẩm đã ngừng kinh doanh.');
      } finally {
        setLoading(false);
      }
    };

    loadDetail();
  }, [slug]);

  const hasTierVariations = Boolean(product?.tierVariations && product.tierVariations.length > 0);

  // Match active SKU from selected tiers
  const matchedSku = useMemo(() => {
    if (!hasTierVariations || !product?.skus || product.skus.length === 0) return null;
    return (
      product.skus.find((sku) => {
        if (!sku.tierIndex || sku.tierIndex.length !== product.tierVariations!.length) return false;
        return sku.tierIndex.every((optIdx, tierIdx) => {
          const optionVal = product.tierVariations![tierIdx]?.options[optIdx];
          return optionVal === selectedTiers[tierIdx];
        });
      }) || product.skus[0]
    );
  }, [hasTierVariations, product, selectedTiers]);

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

  const currentPrice = matchedSku ? matchedSku.price : product.price;
  const currentStock = matchedSku ? matchedSku.stock : product.stock;
  const isOutOfStock = currentStock <= 0;

  const isFashion = product.productType === 'FASHION';
  const hasSizes = !hasTierVariations && isFashion && Array.isArray(product.attributes.sizes) && product.attributes.sizes.length > 0;
  const hasColors = !hasTierVariations && isFashion && Array.isArray(product.attributes.colors) && product.attributes.colors.length > 0;

  const handleAddToCart = async () => {
    if (isOutOfStock || !product) return;

    const selectedAttributes: Record<string, any> = {};

    if (hasTierVariations && product.tierVariations) {
      product.tierVariations.forEach((t, idx) => {
        if (selectedTiers[idx]) {
          selectedAttributes[t.name] = selectedTiers[idx];
        }
      });
      if (matchedSku?.skuId) {
        selectedAttributes.skuId = matchedSku.skuId;
      }
    } else {
      if (hasSizes) {
        if (!selectedSize) {
          toastWarning('Vui lòng chọn Kích cỡ (Size) trước khi thêm vào giỏ hàng.');
          return;
        }
        selectedAttributes.size = selectedSize;
      }

      if (hasColors) {
        if (!selectedColor) {
          toastWarning('Vui lòng chọn Màu sắc trước khi thêm vào giỏ hàng.');
          return;
        }
        selectedAttributes.color = selectedColor;
      }
    }

    setAddingToCart(true);
    await addToCart(product.id, quantity, selectedAttributes);
    setAddingToCart(false);
  };

  const images = product.images && product.images.length > 0 ? product.images : [];
  const currentImageUrl = images[selectedImageIndex] || '';

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-12">
      {/* Breadcrumb */}
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
        <span className="text-slate-800 truncate max-w-[200px]">{product.name}</span>
      </nav>

      {/* Main Product Showcase */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 lg:gap-14 items-start">
        {/* Left: Image Gallery */}
        <div className="space-y-4">
          <div className="aspect-square w-full rounded-2xl bg-white border border-slate-200/80 overflow-hidden shadow-sm flex items-center justify-center p-4">
            {currentImageUrl ? (
              <img
                src={currentImageUrl}
                alt={product.name}
                className="w-full h-full object-contain object-center transition-all duration-300"
              />
            ) : (
              <div className="flex flex-col items-center justify-center text-slate-400">
                <ImageOff className="w-16 h-16 stroke-1 mb-2" />
                <span className="text-sm">Hình ảnh không có sẵn</span>
              </div>
            )}
          </div>

          {/* Thumbnails */}
          {images.length > 1 && (
            <div className="flex gap-3 overflow-x-auto pb-2">
              {images.map((img, idx) => (
                <button
                  key={idx}
                  onClick={() => setSelectedImageIndex(idx)}
                  className={`relative w-20 h-20 rounded-xl bg-white border-2 overflow-hidden flex-shrink-0 transition-all ${
                    selectedImageIndex === idx
                      ? 'border-brand-600 ring-2 ring-brand-100'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <img src={img} alt={`Thumbnail ${idx}`} className="w-full h-full object-contain p-1" />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Right: Product Meta & Purchase Options */}
        <div className="space-y-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Badge variant="primary" size="sm">
                {product.category?.name || product.productType}
              </Badge>
              <span className="text-xs text-slate-400 font-mono">SKU: {product.sku}</span>
            </div>

            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight leading-snug">
              {product.name}
            </h1>

            {product.ratingSummary && product.ratingSummary.totalReviews > 0 && (
              <div className="flex items-center gap-2 pt-1 text-xs">
                <div className="flex items-center gap-1 text-amber-600 font-bold bg-amber-50 px-2.5 py-1 rounded-lg border border-amber-200/60">
                  <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                  <span>{product.ratingSummary.averageRating.toFixed(1)}</span>
                </div>
                <span className="text-slate-400">•</span>
                <span className="text-slate-600 font-medium underline">
                  {product.ratingSummary.totalReviews} đánh giá thực tế
                </span>
                <span className="text-slate-400">•</span>
                <span className="text-emerald-700 font-medium bg-emerald-50 px-2 py-0.5 rounded text-[11px] border border-emerald-200/60">
                  ✓ Verified Purchase
                </span>
              </div>
            )}

            {product.brand && (
              <p className="text-sm text-slate-600 font-medium">
                Thương hiệu: <span className="text-brand-600 font-semibold">{product.brand}</span>
              </p>
            )}
          </div>

          {/* Pricing Box */}
          <div className="p-5 rounded-2xl bg-slate-100/70 border border-slate-200/60 flex items-baseline gap-4">
            <div className="text-3xl sm:text-4xl font-extrabold text-brand-700 tracking-tight">
              {formatVND(currentPrice)}
            </div>
            <span className="text-xs text-slate-500 font-medium uppercase tracking-wider">
              (Đã bao gồm VAT)
            </span>
          </div>

          {/* Stock Availability */}
          <div className="flex items-center gap-2 text-sm">
            <span className="text-slate-500 font-medium">Tình trạng:</span>
            {isOutOfStock ? (
              <span className="font-semibold text-rose-600">Hết hàng</span>
            ) : (
              <span className="font-semibold text-emerald-600">
                Còn hàng ({currentStock} sản phẩm sẵn sàng)
              </span>
            )}
          </div>

          {/* Dynamic Tier Variations (Shopee / TikTok Shop model) */}
          {hasTierVariations ? (
            <div className="space-y-4 pt-2">
              {product.tierVariations!.map((tier, tierIdx) => (
                <div key={tierIdx} className="space-y-2">
                  <label className="block text-sm font-semibold text-slate-900">
                    {tier.name}: <span className="text-brand-600 font-normal">{selectedTiers[tierIdx]}</span>
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {tier.options.map((opt) => {
                      const isSelected = selectedTiers[tierIdx] === opt;
                      return (
                        <button
                          key={opt}
                          type="button"
                          onClick={() => setSelectedTiers((prev) => ({ ...prev, [tierIdx]: opt }))}
                          className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold border transition-all ${
                            isSelected
                              ? 'border-brand-600 bg-brand-50 text-brand-700 ring-2 ring-brand-100 shadow-xs'
                              : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
                          }`}
                        >
                          {isSelected && <Check className="w-3.5 h-3.5 inline mr-1 text-brand-600" />}
                          {opt}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <>
              {/* Fallback Legacy Fashion (Sizes & Colors) */}
              {hasSizes && (
                <div className="space-y-2.5 pt-2">
                  <label className="block text-sm font-semibold text-slate-900">
                    Kích cỡ (Size): <span className="text-brand-600 font-normal">{selectedSize}</span>
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {product.attributes.sizes.map((sz: string) => (
                      <button
                        key={sz}
                        type="button"
                        onClick={() => setSelectedSize(sz)}
                        className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold border transition-all ${
                          selectedSize === sz
                            ? 'border-brand-600 bg-brand-50 text-brand-700 ring-2 ring-brand-100'
                            : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
                        }`}
                      >
                        {sz}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {hasColors && (
                <div className="space-y-2.5 pt-2">
                  <label className="block text-sm font-semibold text-slate-900">
                    Màu sắc: <span className="text-brand-600 font-normal">{selectedColor}</span>
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {product.attributes.colors.map((clr: string) => (
                      <button
                        key={clr}
                        type="button"
                        onClick={() => setSelectedColor(clr)}
                        className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold border transition-all flex items-center gap-1.5 ${
                          selectedColor === clr
                            ? 'border-brand-600 bg-brand-50 text-brand-700 ring-2 ring-brand-100'
                            : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
                        }`}
                      >
                        {selectedColor === clr && <Check className="w-3.5 h-3.5 text-brand-600" />}
                        <span>{clr}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          {/* Quantity Selector & Add to Cart */}
          <div className="pt-4 border-t border-slate-100 space-y-4">
            <div className="flex items-center gap-4">
              <span className="text-sm font-semibold text-slate-900">Số lượng:</span>
              <div className="flex items-center border border-slate-200 rounded-xl bg-white shadow-xs">
                <button
                  type="button"
                  onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                  disabled={quantity <= 1 || isOutOfStock}
                  className="p-2.5 text-slate-600 hover:text-slate-900 disabled:opacity-40"
                >
                  <Minus className="w-4 h-4" />
                </button>
                <span className="w-12 text-center text-sm font-bold text-slate-800">
                  {quantity}
                </span>
                <button
                  type="button"
                  onClick={() => setQuantity((q) => Math.min(currentStock, Math.min(99, q + 1)))}
                  disabled={quantity >= currentStock || isOutOfStock}
                  className="p-2.5 text-slate-600 hover:text-slate-900 disabled:opacity-40"
                >
                  <Plus className="w-4 h-4" />
                </button>
              </div>
            </div>

            <Button
              onClick={handleAddToCart}
              disabled={isOutOfStock}
              loading={addingToCart}
              size="lg"
              variant="primary"
              className="w-full sm:w-auto min-w-[240px] py-3.5 text-base shadow-md shadow-brand-500/20"
              icon={<ShoppingCart className="w-5 h-5" />}
            >
              {isOutOfStock ? 'Sản phẩm đã hết hàng' : 'Thêm vào giỏ hàng'}
            </Button>
          </div>

          {/* Store Guarantees */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-6 border-t border-slate-100">
            <div className="flex items-center gap-2.5 text-xs text-slate-600">
              <Truck className="w-4 h-4 text-brand-600 flex-shrink-0" />
              <span>Giao hàng toàn quốc</span>
            </div>
            <div className="flex items-center gap-2.5 text-xs text-slate-600">
              <ShieldCheck className="w-4 h-4 text-emerald-600 flex-shrink-0" />
              <span>Bảo hành chính hãng</span>
            </div>
            <div className="flex items-center gap-2.5 text-xs text-slate-600">
              <RotateCcw className="w-4 h-4 text-purple-600 flex-shrink-0" />
              <span>Đổi trả thuận tiện</span>
            </div>
          </div>
        </div>
      </div>

      {/* Description & Technical Specifications Tabs */}
      <div className="pt-10 border-t border-slate-200">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
          {/* Description */}
          <div className="lg:col-span-2 space-y-4">
            <h2 className="text-xl font-bold text-slate-900 tracking-tight">Mô tả sản phẩm</h2>
            <div className="prose prose-slate max-w-none text-sm text-slate-600 leading-relaxed whitespace-pre-line bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs">
              {product.description || 'Chưa có thông tin mô tả chi tiết cho sản phẩm này.'}
            </div>
          </div>

          {/* Technical Specifications (Polymorphic attributes display) */}
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-slate-900 tracking-tight">Thông số kỹ thuật</h2>
            <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs space-y-3">
              <div className="flex justify-between py-2 border-b border-slate-100 text-xs">
                <span className="text-slate-500 font-medium">Ngành hàng</span>
                <span className="font-semibold text-slate-900">{product.productType}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-slate-100 text-xs">
                <span className="text-slate-500 font-medium">Thương hiệu</span>
                <span className="font-semibold text-slate-900">{product.brand || '--'}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-slate-100 text-xs">
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
                  <div key={key} className="flex justify-between py-2 border-b border-slate-100 text-xs">
                    <span className="text-slate-500 font-medium">{labelMap[key] || key}</span>
                    <span className="font-semibold text-slate-900 text-right">{String(val)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
