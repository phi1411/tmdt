import React, { useEffect, useState, useMemo } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ShoppingCart,
  ChevronRight,
  ShieldCheck,
  Truck,
  RotateCcw,
  Plus,
  Minus,
  Check,
  Star,
  Store,
  ThumbsUp,
  Tag,
  Zap,
  Award,
  MessageCircle,
  ImageOff,
} from 'lucide-react';
import { catalogApi } from '../api/catalogApi';
import { Product, ProductReview } from '../types/product';
import { formatVND } from '../utils/formatters';
import { Button } from '../components/ui/Button';
import { useCart } from '../contexts/CartContext';
import { useToast } from '../contexts/ToastContext';
import { Skeleton } from '../components/ui/Skeleton';
import { ErrorState } from '../components/ui/ErrorState';

export const ProductDetailPage: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const { addToCart } = useCart();
  const { warning: toastWarning, success: toastSuccess } = useToast();

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
  const [buyingNow, setBuyingNow] = useState<boolean>(false);

  // Reviews state
  const [reviews, setReviews] = useState<ProductReview[]>([]);
  const [selectedStarFilter, setSelectedStarFilter] = useState<number | null>(null);
  const [hasCommentFilter, setHasCommentFilter] = useState<boolean>(false);

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

        // Load reviews for this product
        try {
          const reviewData = await catalogApi.getProductReviews(slug);
          setReviews(reviewData.reviews || []);
        } catch {
          // Reviews fail-safe
          setReviews([]);
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
  const originalPrice = Math.round(currentPrice * 1.15);
  const currentStock = matchedSku ? matchedSku.stock : product.stock;
  const isOutOfStock = currentStock <= 0;

  const isFashion = product.productType === 'FASHION';
  const hasSizes = !hasTierVariations && isFashion && Array.isArray(product.attributes.sizes) && product.attributes.sizes.length > 0;
  const hasColors = !hasTierVariations && isFashion && Array.isArray(product.attributes.colors) && product.attributes.colors.length > 0;

  const getPayloadAttributes = () => {
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
          return null;
        }
        selectedAttributes.size = selectedSize;
      }

      if (hasColors) {
        if (!selectedColor) {
          toastWarning('Vui lòng chọn Màu sắc trước khi thêm vào giỏ hàng.');
          return null;
        }
        selectedAttributes.color = selectedColor;
      }
    }
    return selectedAttributes;
  };

  const handleAddToCart = async () => {
    if (isOutOfStock || !product) return;
    const selectedAttributes = getPayloadAttributes();
    if (!selectedAttributes) return;

    setAddingToCart(true);
    await addToCart(product.id, quantity, selectedAttributes);
    setAddingToCart(false);
  };

  const handleBuyNow = async () => {
    if (isOutOfStock || !product) return;
    const selectedAttributes = getPayloadAttributes();
    if (!selectedAttributes) return;

    setBuyingNow(true);
    await addToCart(product.id, quantity, selectedAttributes);
    setBuyingNow(false);
    navigate('/cart');
  };

  const images = product.images && product.images.length > 0 ? product.images : [];
  const currentImageUrl = images[selectedImageIndex] || '';

  // Filtered reviews
  const filteredReviews = reviews.filter((r) => {
    if (selectedStarFilter !== null && r.rating !== selectedStarFilter) return false;
    if (hasCommentFilter && (!r.reviewText || r.reviewText.trim().length === 0)) return false;
    return true;
  });

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
              {/* Shopee Authentic Badge Overlay */}
              <div className="absolute top-3 left-3 bg-rose-600 text-white text-[11px] font-extrabold px-2.5 py-1 rounded-md shadow-sm uppercase tracking-wider flex items-center gap-1">
                <Award className="w-3.5 h-3.5" />
                <span>Shopee Mall</span>
              </div>
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
                <span className="bg-rose-600 text-white text-[11px] font-bold px-2 py-0.5 rounded uppercase tracking-wider">
                  Yêu Thích+
                </span>
                <span className="text-xs text-slate-500 font-mono">Mã: {product.sku}</span>
              </div>

              <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight leading-snug">
                {product.name}
              </h1>

              {/* Shopee Rating Bar */}
              <div className="flex flex-wrap items-center gap-4 text-xs pt-1 pb-2 border-b border-slate-100">
                <div className="flex items-center gap-1.5">
                  <span className="font-extrabold text-brand-600 text-sm border-b border-brand-600">
                    {product.ratingSummary?.averageRating.toFixed(1) || '5.0'}
                  </span>
                  <div className="flex text-amber-400">
                    {[1, 2, 3, 4, 5].map((s) => (
                      <Star key={s} className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                    ))}
                  </div>
                </div>

                <span className="text-slate-300">|</span>

                <div className="text-slate-600">
                  <span className="font-bold text-slate-900 text-sm border-b border-slate-900 mr-1">
                    {product.ratingSummary?.totalReviews || 24}
                  </span>
                  Đánh Giá
                </div>

                <span className="text-slate-300">|</span>

                <div className="text-slate-600">
                  <span className="font-bold text-slate-900 text-sm mr-1">
                    {product.stock > 0 ? 120 + product.stock : 850}
                  </span>
                  Đã Bán
                </div>
              </div>
            </div>

            {/* Shopee Iconic Pricing Box */}
            <div className="p-5 rounded-2xl bg-slate-50/90 border border-slate-200/80 space-y-3">
              <div className="flex items-baseline gap-3.5">
                <span className="text-sm sm:text-base text-slate-400 line-through font-medium">
                  {formatVND(originalPrice)}
                </span>
                <span className="text-3xl sm:text-4xl font-extrabold text-rose-600 tracking-tight">
                  {formatVND(currentPrice)}
                </span>
                <span className="text-xs font-bold bg-rose-100 text-rose-700 px-2 py-0.5 rounded-full">
                  -15% GIẢM
                </span>
              </div>

              {/* Shopee Voucher Tags Banner */}
              <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-200/60 text-xs">
                <div className="flex items-center gap-1 text-slate-500 font-medium">
                  <Tag className="w-3.5 h-3.5 text-rose-600" />
                  <span>Mã Giảm Giá Của Shop:</span>
                </div>
                <span className="border border-dashed border-rose-400 bg-rose-50 text-rose-700 font-semibold px-2 py-0.5 rounded text-[11px]">
                  Giảm ₫30k
                </span>
                <span className="border border-dashed border-rose-400 bg-rose-50 text-rose-700 font-semibold px-2 py-0.5 rounded text-[11px]">
                  Giảm ₫50k
                </span>
                <span className="border border-dashed border-emerald-400 bg-emerald-50 text-emerald-700 font-semibold px-2 py-0.5 rounded text-[11px] flex items-center gap-0.5">
                  <Zap className="w-3 h-3" /> Freeship Xtra
                </span>
              </div>
            </div>

            {/* Shopee Shipping Info */}
            <div className="p-4 rounded-xl bg-slate-50/60 border border-slate-200/60 flex items-start gap-3.5 text-xs text-slate-600">
              <Truck className="w-5 h-5 text-brand-600 flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <div className="font-bold text-slate-800 flex items-center gap-2">
                  <span>Vận Chuyển Toàn Quốc</span>
                  <span className="bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded text-[10px] font-bold">
                    MIỄN PHÍ VẬN CHUYỂN
                  </span>
                </div>
                <p className="text-slate-500 leading-relaxed">
                  Nhận hàng từ 2 - 3 ngày. Đổi trả miễn phí trong vòng 15 ngày nếu lỗi nhà sản xuất.
                </p>
              </div>
            </div>

            {/* Dynamic Tier Variations (Shopee Variation Matrix) */}
            {hasTierVariations ? (
              <div className="space-y-4 pt-1">
                {product.tierVariations!.map((tier, tierIdx) => (
                  <div key={tierIdx} className="space-y-2">
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                      {tier.name}:{' '}
                      <span className="text-rose-600 font-extrabold normal-case text-sm">
                        {selectedTiers[tierIdx]}
                      </span>
                    </label>
                    <div className="flex flex-wrap gap-2.5">
                      {tier.options.map((opt) => {
                        const isSelected = selectedTiers[tierIdx] === opt;
                        return (
                          <button
                            key={opt}
                            type="button"
                            onClick={() => setSelectedTiers((prev) => ({ ...prev, [tierIdx]: opt }))}
                            className={`px-4 py-2.5 rounded-xl text-xs sm:text-sm font-semibold border transition-all flex items-center gap-1.5 relative ${
                              isSelected
                                ? 'border-rose-600 bg-rose-50/60 text-rose-700 ring-2 ring-rose-200 shadow-xs'
                                : 'border-slate-200 bg-white text-slate-700 hover:border-slate-400'
                            }`}
                          >
                            {isSelected && <Check className="w-3.5 h-3.5 text-rose-600" />}
                            <span>{opt}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <>
                {/* Fallback Legacy Fashion */}
                {hasSizes && (
                  <div className="space-y-2 pt-1">
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                      Kích cỡ (Size): <span className="text-rose-600 font-bold text-sm">{selectedSize}</span>
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {product.attributes.sizes.map((sz: string) => (
                        <button
                          key={sz}
                          type="button"
                          onClick={() => setSelectedSize(sz)}
                          className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold border transition-all ${
                            selectedSize === sz
                              ? 'border-rose-600 bg-rose-50 text-rose-700 ring-2 ring-rose-200'
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
                  <div className="space-y-2 pt-1">
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                      Màu sắc: <span className="text-rose-600 font-bold text-sm">{selectedColor}</span>
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {product.attributes.colors.map((clr: string) => (
                        <button
                          key={clr}
                          type="button"
                          onClick={() => setSelectedColor(clr)}
                          className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold border transition-all flex items-center gap-1.5 ${
                            selectedColor === clr
                              ? 'border-rose-600 bg-rose-50 text-rose-700 ring-2 ring-rose-200'
                              : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
                          }`}
                        >
                          {selectedColor === clr && <Check className="w-3.5 h-3.5 text-rose-600" />}
                          <span>{clr}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}

            {/* Quantity Selector & Real-time Stock */}
            <div className="pt-2 flex flex-wrap items-center gap-6">
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">Số Lượng:</span>
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

              <span className="text-xs text-slate-500 font-medium">
                {isOutOfStock ? (
                  <span className="text-rose-600 font-bold">Hết hàng</span>
                ) : (
                  <span>
                    <strong className="text-slate-800">{currentStock}</strong> sản phẩm có sẵn
                  </span>
                )}
              </span>
            </div>

            {/* Shopee Dual Action Buttons (Thêm vào giỏ & Mua ngay) */}
            <div className="pt-4 flex flex-col sm:flex-row items-center gap-3.5">
              <button
                type="button"
                onClick={handleAddToCart}
                disabled={isOutOfStock || addingToCart}
                className="w-full sm:flex-1 py-3.5 px-6 rounded-2xl border-2 border-rose-600 bg-rose-50/70 text-rose-700 hover:bg-rose-100 font-bold text-sm sm:text-base flex items-center justify-center gap-2 transition-all shadow-xs disabled:opacity-50"
              >
                <ShoppingCart className="w-5 h-5 text-rose-600" />
                <span>{addingToCart ? 'Đang thêm...' : 'Thêm Vào Giỏ Hàng'}</span>
              </button>

              <button
                type="button"
                onClick={handleBuyNow}
                disabled={isOutOfStock || buyingNow}
                className="w-full sm:flex-1 py-3.5 px-6 rounded-2xl bg-rose-600 hover:bg-rose-700 text-white font-bold text-sm sm:text-base flex items-center justify-center gap-2 transition-all shadow-md shadow-rose-600/30 disabled:opacity-50"
              >
                <Zap className="w-5 h-5" />
                <span>{buyingNow ? 'Đang xử lý...' : 'Mua Ngay'}</span>
              </button>
            </div>

            {/* Shopee Policy Safeguards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-6 border-t border-slate-100 text-xs text-slate-600">
              <div className="flex items-center gap-2">
                <RotateCcw className="w-4 h-4 text-rose-600" />
                <span>7 Ngày Trả Hàng Miễn Phí</span>
              </div>
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <span>Chính Hãng 100%</span>
              </div>
              <div className="flex items-center gap-2">
                <Truck className="w-4 h-4 text-blue-600" />
                <span>Miễn Phí Vận Chuyển</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Shopee Seller / Shop Information Card */}
      <div className="bg-white rounded-3xl border border-slate-200/90 shadow-sm p-6 sm:p-8">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-gradient-to-tr from-rose-500 to-amber-500 text-white flex items-center justify-center font-black text-xl shadow-md">
              NM
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <h3 className="font-extrabold text-slate-900 text-base">NovaMart Official Store</h3>
                <span className="bg-rose-600 text-white text-[10px] font-bold px-1.5 py-0.5 rounded">
                  MALL
                </span>
              </div>
              <p className="text-xs text-emerald-600 font-semibold flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                Online 5 phút trước
              </p>
              <div className="flex gap-2 pt-1">
                <Button variant="outline" size="sm" className="text-xs py-1 px-3">
                  <Store className="w-3.5 h-3.5 mr-1" /> Xem Shop
                </Button>
                <Button variant="ghost" size="sm" className="text-xs py-1 px-3 text-slate-600">
                  <MessageCircle className="w-3.5 h-3.5 mr-1" /> Chat Ngay
                </Button>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-6 text-xs text-slate-600 border-t md:border-t-0 md:border-l border-slate-100 pt-4 md:pt-0 md:pl-8">
            <div>
              <span className="text-slate-400 block mb-0.5">Đánh Giá:</span>
              <strong className="text-rose-600 font-bold text-sm">4.9 / 5.0</strong>
            </div>
            <div>
              <span className="text-slate-400 block mb-0.5">Tỉ Lệ Phản Hồi:</span>
              <strong className="text-slate-800 font-bold text-sm">99%</strong>
            </div>
            <div>
              <span className="text-slate-400 block mb-0.5">Thời Gian Phản Hồi:</span>
              <strong className="text-slate-800 font-bold text-sm">Trong vài phút</strong>
            </div>
            <div>
              <span className="text-slate-400 block mb-0.5">Sản Phẩm:</span>
              <strong className="text-slate-800 font-bold text-sm">190</strong>
            </div>
            <div>
              <span className="text-slate-400 block mb-0.5">Tham Gia:</span>
              <strong className="text-slate-800 font-bold text-sm">2 năm trước</strong>
            </div>
            <div>
              <span className="text-slate-400 block mb-0.5">Người Theo Dõi:</span>
              <strong className="text-slate-800 font-bold text-sm">24.5k</strong>
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

      {/* Shopee-Grade Customer Reviews Section (ĐÁNH GIÁ SẢN PHẨM) */}
      <div className="bg-white rounded-3xl border border-slate-200/90 shadow-sm p-6 sm:p-8 space-y-6">
        <h2 className="text-lg font-extrabold text-slate-900 tracking-tight uppercase border-b border-slate-100 pb-4">
          Đánh Giá Sản Phẩm
        </h2>

        {/* Shopee Rating Overview Card */}
        <div className="p-6 rounded-2xl bg-amber-50/50 border border-amber-200/60 flex flex-col md:flex-row items-center gap-8">
          <div className="text-center md:text-left space-y-1">
            <div className="text-4xl sm:text-5xl font-black text-rose-600">
              {product.ratingSummary?.averageRating.toFixed(1) || '5.0'}
              <span className="text-xl font-normal text-slate-500"> trên 5</span>
            </div>
            <div className="flex justify-center md:justify-start text-amber-400 pt-1">
              {[1, 2, 3, 4, 5].map((s) => (
                <Star key={s} className="w-5 h-5 fill-amber-400 text-amber-400" />
              ))}
            </div>
            <p className="text-xs text-slate-500 font-medium">
              Dựa trên {reviews.length || product.ratingSummary?.totalReviews || 12} đánh giá xác thực
            </p>
          </div>

          {/* Shopee Filter Pills */}
          <div className="flex-1 flex flex-wrap gap-2.5">
            <button
              type="button"
              onClick={() => {
                setSelectedStarFilter(null);
                setHasCommentFilter(false);
              }}
              className={`px-4 py-2 rounded-xl text-xs font-semibold border transition-all ${
                selectedStarFilter === null && !hasCommentFilter
                  ? 'border-rose-600 bg-rose-600 text-white shadow-xs'
                  : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
              }`}
            >
              Tất Cả ({reviews.length})
            </button>
            <button
              type="button"
              onClick={() => setSelectedStarFilter(5)}
              className={`px-4 py-2 rounded-xl text-xs font-semibold border transition-all ${
                selectedStarFilter === 5
                  ? 'border-rose-600 bg-rose-600 text-white shadow-xs'
                  : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
              }`}
            >
              5 Sao ({reviews.filter((r) => r.rating === 5).length})
            </button>
            <button
              type="button"
              onClick={() => setSelectedStarFilter(4)}
              className={`px-4 py-2 rounded-xl text-xs font-semibold border transition-all ${
                selectedStarFilter === 4
                  ? 'border-rose-600 bg-rose-600 text-white shadow-xs'
                  : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
              }`}
            >
              4 Sao ({reviews.filter((r) => r.rating === 4).length})
            </button>
            <button
              type="button"
              onClick={() => setHasCommentFilter(!hasCommentFilter)}
              className={`px-4 py-2 rounded-xl text-xs font-semibold border transition-all ${
                hasCommentFilter
                  ? 'border-rose-600 bg-rose-600 text-white shadow-xs'
                  : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
              }`}
            >
              Có Bình Luận ({reviews.filter((r) => r.reviewText).length})
            </button>
          </div>
        </div>

        {/* Review Items List */}
        <div className="space-y-6 pt-2">
          {filteredReviews.length === 0 ? (
            <div className="py-12 text-center text-slate-400 text-sm">
              Chưa có đánh giá nào phù hợp với bộ lọc đã chọn.
            </div>
          ) : (
            filteredReviews.map((rev) => (
              <div key={rev.id} className="pb-6 border-b border-slate-100 space-y-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center font-bold text-slate-600 text-xs">
                      {rev.userSnapshot?.displayName?.[0] || 'U'}
                    </div>
                    <div>
                      <div className="text-xs font-bold text-slate-900">
                        {rev.userSnapshot?.displayName || 'Người mua ẩn danh'}
                      </div>
                      <div className="flex text-amber-400 pt-0.5">
                        {[1, 2, 3, 4, 5].map((s) => (
                          <Star
                            key={s}
                            className={`w-3 h-3 ${
                              s <= rev.rating ? 'fill-amber-400 text-amber-400' : 'text-slate-200'
                            }`}
                          />
                        ))}
                      </div>
                    </div>
                  </div>

                  <span className="text-[11px] text-slate-400">
                    {new Date(rev.createdAt).toLocaleDateString('vi-VN')}
                  </span>
                </div>

                {/* SKU specification purchased badge */}
                {rev.skuSpecSnapshot && Object.keys(rev.skuSpecSnapshot).length > 0 && (
                  <div className="flex flex-wrap gap-2 text-[11px] text-slate-500">
                    <span className="font-medium text-slate-400">Phân loại hàng:</span>
                    {Object.entries(rev.skuSpecSnapshot).map(([k, v]) => (
                      <span key={k} className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded">
                        {k}: {v}
                      </span>
                    ))}
                  </div>
                )}

                {/* Review Text */}
                <p className="text-sm text-slate-800 leading-relaxed whitespace-pre-line">
                  {rev.reviewText}
                </p>

                {/* Helpful count */}
                <div className="flex items-center gap-1.5 text-xs text-slate-400 pt-1">
                  <button
                    type="button"
                    onClick={() => toastSuccess('Cảm ơn bạn đã phản hồi đánh giá hữu ích!')}
                    className="flex items-center gap-1 hover:text-slate-600 transition-colors"
                  >
                    <ThumbsUp className="w-3.5 h-3.5" />
                    <span>Hữu ích ({rev.helpfulCount || 0})</span>
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
