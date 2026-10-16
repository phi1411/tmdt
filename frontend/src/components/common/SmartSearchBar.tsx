import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  History,
  TrendingUp,
  X,
  Sparkles,
  ShoppingBag,
  ArrowRight,
  Loader2,
} from 'lucide-react';
import { catalogApi } from '../../api/catalogApi';
import { Product } from '../../types/product';
import { useSearchHistory } from '../../hooks/useSearchHistory';
import { formatVND } from '../../utils/formatters';

interface SmartSearchBarProps {
  className?: string;
  placeholder?: string;
  onSearchComplete?: () => void;
}

export const SmartSearchBar: React.FC<SmartSearchBarProps> = ({
  className = '',
  placeholder = 'Tìm kiếm điện tử, thời trang, đồ gia dụng...',
  onSearchComplete,
}) => {
  const navigate = useNavigate();
  const { history, addSearch, removeSearch, clearHistory, trendingSearches } = useSearchHistory();

  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [suggestedProducts, setSuggestedProducts] = useState<Product[]>([]);
  const [imageErrors, setImageErrors] = useState<Record<string, boolean>>({});

  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent | TouchEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('touchstart', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside);
    };
  }, []);

  // Debounced auto-suggest when query >= 2 characters
  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length < 2) {
      setSuggestedProducts([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    const timer = setTimeout(async () => {
      try {
        const response = await catalogApi.getProducts({ q: trimmed, pageSize: 5 });
        setSuggestedProducts(response.products || []);
      } catch {
        setSuggestedProducts([]);
      } finally {
        setLoading(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [query]);

  const executeSearch = useCallback(
    (searchKeyword: string) => {
      const trimmed = searchKeyword.trim();
      if (!trimmed) return;

      addSearch(trimmed);
      setIsOpen(false);
      inputRef.current?.blur();
      navigate(`/products?q=${encodeURIComponent(trimmed)}`);
      onSearchComplete?.();
    },
    [addSearch, navigate, onSearchComplete]
  );

  const handleProductClick = useCallback(
    (product: Product) => {
      addSearch(product.name);
      setIsOpen(false);
      inputRef.current?.blur();
      navigate(`/products/${product.slug}`);
      onSearchComplete?.();
    },
    [addSearch, navigate, onSearchComplete]
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    executeSearch(query);
  };

  const handleClearInput = () => {
    setQuery('');
    setSuggestedProducts([]);
    inputRef.current?.focus();
  };

  const handleImageError = (productId: string) => {
    setImageErrors((prev) => ({ ...prev, [productId]: true }));
  };

  const showSuggestions = query.trim().length >= 2;

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      {/* Search Input Bar */}
      <form onSubmit={handleSubmit} className="relative w-full flex items-center">
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            if (!isOpen) setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          placeholder={placeholder}
          className="w-full bg-slate-100/90 hover:bg-slate-100 focus:bg-white text-sm text-slate-800 placeholder:text-slate-400 pl-10 pr-24 py-2.5 rounded-full border border-slate-200 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100 transition-all shadow-inner"
        />

        {/* Search Icon (Left) */}
        <Search className="w-4 h-4 text-slate-400 absolute left-3.5 pointer-events-none" />

        {/* Clear Button (Right before submit) */}
        {query && (
          <button
            type="button"
            onClick={handleClearInput}
            className="absolute right-20 p-1 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-200 transition-colors"
            title="Xóa nội dung"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}

        {/* Submit Button (Right) */}
        <button
          type="submit"
          className="absolute right-1.5 px-3 py-1 bg-brand-600 hover:bg-brand-700 text-white rounded-full text-xs font-semibold tracking-wide transition-colors flex items-center gap-1 shadow-xs"
        >
          {loading && showSuggestions ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : (
            <span>Tìm kiếm</span>
          )}
        </button>
      </form>

      {/* Dropdown Suggestions */}
      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-white rounded-2xl shadow-xl border border-slate-200/90 overflow-hidden z-50 animate-in fade-in-50 zoom-in-95 max-h-[460px] overflow-y-auto">
          {showSuggestions ? (
            /* Mode 1: Auto-suggest Results for query >= 2 chars */
            <div className="p-3 space-y-2">
              <div className="flex items-center justify-between px-2 pb-1 text-xs text-slate-500 font-medium border-b border-slate-100">
                <span className="flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-brand-600" />
                  <span>Gợi ý sản phẩm ({suggestedProducts.length})</span>
                </span>
                {loading && (
                  <span className="flex items-center gap-1 text-[11px] text-slate-400">
                    <Loader2 className="w-3 h-3 animate-spin" />
                    Đang tìm...
                  </span>
                )}
              </div>

              {loading && suggestedProducts.length === 0 ? (
                <div className="py-6 flex flex-col items-center justify-center text-slate-400 text-xs gap-2">
                  <Loader2 className="w-5 h-5 animate-spin text-brand-600" />
                  <span>Đang tìm kiếm sản phẩm phù hợp...</span>
                </div>
              ) : suggestedProducts.length > 0 ? (
                <div className="space-y-1">
                  {suggestedProducts.map((product) => {
                    const primaryImage = product.images?.[0];
                    const hasError = imageErrors[product.id];
                    return (
                      <button
                        key={product.id}
                        type="button"
                        onClick={() => handleProductClick(product)}
                        className="w-full flex items-center gap-3 p-2 rounded-xl hover:bg-slate-50 transition-colors text-left group"
                      >
                        <div className="w-12 h-12 rounded-lg bg-slate-100 flex-shrink-0 overflow-hidden border border-slate-200/70 flex items-center justify-center">
                          {primaryImage && !hasError ? (
                            <img
                              src={primaryImage}
                              alt={product.name}
                              onError={() => handleImageError(product.id)}
                              className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                            />
                          ) : (
                            <ShoppingBag className="w-5 h-5 text-slate-400" />
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-semibold text-slate-800 line-clamp-1 group-hover:text-brand-600 transition-colors">
                            {product.name}
                          </p>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className="text-xs font-bold text-rose-600">
                              {formatVND(product.price)}
                            </span>
                            {product.category?.name && (
                              <span className="text-[10px] text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded truncate max-w-[120px]">
                                {product.category.name}
                              </span>
                            )}
                          </div>
                        </div>
                      </button>
                    );
                  })}

                  {/* View all matching results */}
                  <div className="pt-2 border-t border-slate-100">
                    <button
                      type="button"
                      onClick={() => executeSearch(query)}
                      className="w-full flex items-center justify-center gap-2 py-2 px-3 text-xs font-semibold text-brand-600 hover:text-brand-700 hover:bg-brand-50 rounded-xl transition-colors"
                    >
                      <span>Xem tất cả kết quả cho &quot;{query}&quot;</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ) : (
                <div className="py-6 text-center text-xs text-slate-500 space-y-2">
                  <p>Không tìm thấy sản phẩm nào khớp với &quot;{query}&quot;</p>
                  <button
                    type="button"
                    onClick={() => executeSearch(query)}
                    className="inline-flex items-center gap-1 text-brand-600 hover:underline font-semibold"
                  >
                    <span>Vẫn tìm kiếm &quot;{query}&quot; trong danh mục</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
              )}
            </div>
          ) : (
            /* Mode 2: Empty input - Search History & Trending Searches */
            <div className="p-4 space-y-4">
              {/* Search History */}
              {history.length > 0 && (
                <div>
                  <div className="flex items-center justify-between pb-2 mb-1 border-b border-slate-100">
                    <span className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
                      <History className="w-3.5 h-3.5 text-slate-500" />
                      Lịch sử tìm kiếm
                    </span>
                    <button
                      type="button"
                      onClick={clearHistory}
                      className="text-[11px] text-rose-600 hover:text-rose-700 font-medium hover:underline"
                    >
                      Xóa tất cả
                    </button>
                  </div>
                  <div className="space-y-0.5">
                    {history.map((item) => (
                      <div
                        key={item}
                        className="flex items-center justify-between group px-2 py-1.5 rounded-lg hover:bg-slate-50 transition-colors"
                      >
                        <button
                          type="button"
                          onClick={() => executeSearch(item)}
                          className="flex items-center gap-2 flex-1 text-left text-xs text-slate-700 hover:text-brand-600 truncate"
                        >
                          <History className="w-3 h-3 text-slate-400 flex-shrink-0" />
                          <span className="truncate">{item}</span>
                        </button>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            removeSearch(item);
                          }}
                          className="p-1 text-slate-300 hover:text-slate-600 rounded-md hover:bg-slate-200 opacity-60 group-hover:opacity-100 transition-opacity"
                          title="Xóa từ khóa này"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Trending Searches */}
              <div>
                <div className="flex items-center gap-1.5 pb-2 mb-2 border-b border-slate-100">
                  <TrendingUp className="w-3.5 h-3.5 text-amber-500" />
                  <span className="text-xs font-semibold text-slate-700">
                    Tìm kiếm phổ biến / Xu hướng
                  </span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {trendingSearches.map((keyword) => (
                    <button
                      key={keyword}
                      type="button"
                      onClick={() => executeSearch(keyword)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium bg-slate-100 hover:bg-brand-50 text-slate-700 hover:text-brand-600 rounded-full border border-slate-200/80 hover:border-brand-200 transition-colors"
                    >
                      <Sparkles className="w-2.5 h-2.5 text-brand-500" />
                      <span>{keyword}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
