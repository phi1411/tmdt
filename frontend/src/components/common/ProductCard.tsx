import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { ShoppingCart, Eye, ImageOff } from 'lucide-react';
import { Product } from '../../types/product';
import { formatVND } from '../../utils/formatters';
import { Badge } from '../ui/Badge';
import { useCart } from '../../contexts/CartContext';

export interface ProductCardProps {
  product: Product;
}

export const ProductCard: React.FC<ProductCardProps> = ({ product }) => {
  const [imageError, setImageError] = useState(false);
  const { addToCart } = useCart();
  const [adding, setAdding] = useState(false);

  const primaryImage = product.images?.[0] || '';

  const isOutOfStock = product.stock <= 0;
  const isFashion = product.productType === 'FASHION';

  const handleQuickAdd = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    // If fashion, user must pick size/color on detail page
    if (isFashion) {
      window.location.href = `/products/${product.slug}`;
      return;
    }
    setAdding(true);
    await addToCart(product.id, 1, {});
    setAdding(false);
  };

  const getProductTypeLabel = () => {
    switch (product.productType) {
      case 'ELECTRONICS':
        return 'Điện tử';
      case 'FASHION':
        return 'Thời trang';
      case 'HOME_APPLIANCE':
        return 'Gia dụng';
      default:
        return product.category?.name || 'Sản phẩm';
    }
  };

  return (
    <div className="group relative flex flex-col bg-white rounded-2xl border border-slate-200/80 shadow-sm hover:shadow-xl hover:border-slate-300 transition-all duration-300 overflow-hidden">
      {/* Thumbnail area */}
      <Link
        to={`/products/${product.slug}`}
        className="relative block aspect-square w-full overflow-hidden bg-slate-100"
      >
        {primaryImage && !imageError ? (
          <img
            src={primaryImage}
            alt={product.name}
            onError={() => setImageError(true)}
            className="w-full h-full object-cover object-center group-hover:scale-105 transition-transform duration-500"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center text-slate-400 bg-slate-100">
            <ImageOff className="w-10 h-10 stroke-1 mb-1" />
            <span className="text-[11px] font-medium">Chưa có ảnh</span>
          </div>
        )}

        {/* Badges on image */}
        <div className="absolute top-3 left-3 flex flex-col gap-1 items-start z-10">
          <Badge variant="primary" size="sm">
            {getProductTypeLabel()}
          </Badge>
          {isOutOfStock ? (
            <Badge variant="danger" size="sm">
              Hết hàng
            </Badge>
          ) : product.stock < 10 ? (
            <Badge variant="warning" size="sm">
              Còn {product.stock}
            </Badge>
          ) : null}
        </div>

        {/* Hover Quick Action Overlay */}
        <div className="absolute inset-0 bg-slate-900/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2 p-4">
          <span className="p-2.5 rounded-full bg-white text-slate-800 shadow-md hover:bg-brand-50 hover:text-brand-600 transition-colors">
            <Eye className="w-5 h-5" />
          </span>
        </div>
      </Link>

      {/* Card Body */}
      <div className="flex flex-1 flex-col p-4 sm:p-5">
        <div className="flex items-center justify-between text-xs text-slate-400 mb-1.5 font-medium">
          <span className="truncate max-w-[120px]">{product.brand || 'Thương hiệu'}</span>
          <span className="text-[11px] font-mono text-slate-400">{product.sku}</span>
        </div>

        <Link to={`/products/${product.slug}`} className="group-hover:text-brand-600 transition-colors mb-2">
          <h3 className="text-sm font-semibold text-slate-900 line-clamp-2 leading-snug">
            {product.name}
          </h3>
        </Link>

        {/* Key Attributes Snippet */}
        <div className="text-[11px] text-slate-500 mb-4 line-clamp-1">
          {product.productType === 'ELECTRONICS' && (
            <span>
              {product.attributes.ram ? `${product.attributes.ram} RAM • ` : ''}
              {product.attributes.storage ? `${product.attributes.storage} ROM` : ''}
            </span>
          )}
          {product.productType === 'FASHION' && (
            <span>
              {Array.isArray(product.attributes.sizes)
                ? `Size: ${product.attributes.sizes.slice(0, 3).join(', ')}${product.attributes.sizes.length > 3 ? '...' : ''}`
                : 'Thời trang'}
            </span>
          )}
          {product.productType === 'HOME_APPLIANCE' && (
            <span>
              {product.attributes.power ? `${product.attributes.power} • ` : ''}
              {product.attributes.capacity || 'Gia dụng gia đình'}
            </span>
          )}
        </div>

        {/* Pricing & Add to Cart button */}
        <div className="mt-auto pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
          <div>
            <div className="text-base sm:text-lg font-bold text-brand-700 tracking-tight">
              {formatVND(product.price)}
            </div>
          </div>

          <button
            onClick={handleQuickAdd}
            disabled={isOutOfStock || adding}
            className="p-2 sm:px-3 sm:py-2 rounded-xl bg-slate-100 text-slate-700 hover:bg-brand-600 hover:text-white disabled:opacity-40 disabled:pointer-events-none transition-colors flex items-center gap-1.5 text-xs font-semibold"
            title={isFashion ? 'Chọn kích cỡ/màu sắc' : 'Thêm vào giỏ'}
          >
            <ShoppingCart className="w-4 h-4" />
            <span className="hidden sm:inline">{isFashion ? 'Chọn mua' : 'Thêm'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
