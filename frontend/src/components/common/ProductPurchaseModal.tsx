import React, { useEffect, useId, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { Check, ImageOff, Minus, Plus, X } from 'lucide-react';
import { Product } from '../../types/product';
import { useCart } from '../../contexts/CartContext';
import { formatVND } from '../../utils/formatters';
import { purchaseOptions, skuMatches, hasVariantPriceRange } from '../../utils/productSelection';
import { Button } from '../ui/Button';

export type PurchaseIntent = 'cart' | 'buy';

interface Props {
  product: Product;
  intent: PurchaseIntent;
  onClose: () => void;
}

export const ProductPurchaseModal: React.FC<Props> = ({ product, intent, onClose }) => {
  const navigate = useNavigate();
  const { addToCart } = useCart();
  const [selection, setSelection] = useState<Record<string, string>>({});
  const [quantity, setQuantity] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [imageError, setImageError] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const busyRef = useRef(false);
  const closeRef = useRef(onClose);
  const titleId = useId();
  closeRef.current = onClose;

  const options = purchaseOptions(product);
  const usesSkus = !!product.tierVariations?.length;
  const missing = options.filter((option) => !selection[option.key]);
  const matchedSku = usesSkus && missing.length === 0
    ? product.skus?.find((sku) => skuMatches(product, sku, selection))
    : undefined;
  const stock = usesSkus ? (matchedSku ? Math.min(product.stock, matchedSku.stock) : 0) : product.stock;
  const limit = Math.min(99, stock);
  const price = matchedSku?.price ?? product.price;
  const ready = missing.length === 0 && stock > 0 && quantity <= limit;

  useEffect(() => {
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    dialogRef.current?.focus();
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        event.stopPropagation();
        if (!busyRef.current) closeRef.current();
      }
      if (event.key === 'Tab') {
        const elements = dialogRef.current?.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled), [tabindex="0"]');
        if (!elements?.length) return;
        const first = elements[0];
        const last = elements[elements.length - 1];
        if (event.shiftKey && (document.activeElement === first || document.activeElement === dialogRef.current)) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && (document.activeElement === last || document.activeElement === dialogRef.current)) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener('keydown', handleKey, true);
    return () => {
      document.removeEventListener('keydown', handleKey, true);
      document.body.style.overflow = previousOverflow;
      if (previousFocus?.isConnected) previousFocus.focus();
    };
  }, []);

  const choose = (key: string, value: string) => {
    setSelection((current) => {
      const next = { ...current };
      if (next[key] === value) delete next[key];
      else next[key] = value;
      return next;
    });
    setQuantity(1);
  };

  const confirm = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!ready || busyRef.current) return;
    busyRef.current = true;
    setSubmitting(true);
    try {
      const added = await addToCart(product.id, quantity, {
        ...selection,
        ...(matchedSku ? { skuId: matchedSku.skuId } : {}),
      });
      if (added) {
        onClose();
        if (intent === 'buy') navigate('/cart');
      }
    } finally {
      busyRef.current = false;
      setSubmitting(false);
    }
  };

  return createPortal(
    <div className="fixed inset-0 z-[100] flex items-end justify-center bg-slate-900/50 sm:items-center sm:p-6"
      onClick={(event) => { if (event.target === event.currentTarget && !submitting) onClose(); }}>
      <div ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1}
        className="flex max-h-[90dvh] w-full flex-col overflow-hidden rounded-t-3xl bg-white shadow-2xl outline-none sm:max-w-xl sm:rounded-3xl">
        <header className="flex shrink-0 items-center justify-between gap-3 border-b border-slate-100 p-5">
          <h2 id={titleId} className="text-lg font-bold text-slate-900">Chọn phân loại sản phẩm</h2>
          <button type="button" aria-label="Đóng bảng chọn" disabled={submitting} onClick={onClose}
            className="rounded-full p-2 text-slate-500 hover:bg-slate-100 focus-visible:ring-2 focus-visible:ring-brand-500">
            <X className="h-5 w-5" />
          </button>
        </header>
        <form onSubmit={confirm} className="flex min-h-0 flex-1 flex-col">
          <div className="space-y-6 overflow-y-auto p-5 sm:p-6">
            <div className="flex items-center gap-4">
              <div className="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-slate-100">
                {product.images[0] && !imageError
                  ? <img src={product.images[0]} alt={product.name} className="h-full w-full object-cover" onError={() => setImageError(true)} />
                  : <ImageOff className="h-8 w-8 text-slate-400" />}
              </div>
              <div className="min-w-0 space-y-1">
                <p className="break-words text-sm font-semibold text-slate-900">{product.name}</p>
                <p className="text-xl font-bold text-rose-600" aria-live="polite">{!matchedSku && hasVariantPriceRange(product) ? 'Từ ' : ''}{formatVND(price)}</p>
                <p className="text-xs text-slate-500" aria-live="polite">
                  {missing.length ? `Vui lòng chọn ${missing.map((option) => option.label.toLowerCase()).join(', ')}`
                    : stock > 0 ? `Còn ${stock} sản phẩm` : 'Phân loại này đã hết hàng'}
                </p>
              </div>
            </div>
            {options.map((option) => (
              <fieldset key={option.key} disabled={submitting} className="min-w-0 space-y-3">
                <legend className="text-sm font-semibold text-slate-800">{option.label}</legend>
                <div className="flex flex-wrap gap-2">
                  {option.values.map((value) => {
                    const selected = selection[option.key] === value;
                    const available = !usesSkus || !!product.skus?.some((sku) => sku.stock > 0 && skuMatches(product, sku, { ...selection, [option.key]: value }));
                    return <button key={value} type="button" aria-pressed={selected} disabled={!available}
                      onClick={() => choose(option.key, value)}
                      className={`flex max-w-full items-center gap-1.5 break-words rounded-xl border px-4 py-2.5 text-sm font-medium focus-visible:ring-2 focus-visible:ring-brand-500 disabled:cursor-not-allowed disabled:opacity-40 ${selected ? 'border-rose-600 bg-rose-50 text-rose-700' : 'border-slate-200 text-slate-700 hover:border-rose-400'}`}>
                      {selected && <Check className="h-4 w-4 shrink-0" />}<span>{value}</span>
                      {!available && <span className="text-xs">(Hết hàng)</span>}
                    </button>;
                  })}
                </div>
              </fieldset>
            ))}
            {!options.length && <p className="text-sm text-slate-500">Sản phẩm này không có phân loại. Bạn chỉ cần chọn số lượng.</p>}
            <div className="flex flex-wrap items-center justify-between gap-3">
              <label htmlFor={`${titleId}-quantity`} className="text-sm font-semibold text-slate-800">Số lượng</label>
              <div className="flex items-center overflow-hidden rounded-xl border border-slate-200">
                <button type="button" aria-label="Giảm số lượng" disabled={submitting || quantity <= 1 || !ready}
                  onClick={() => setQuantity((current) => Math.max(1, current - 1))} className="p-3 disabled:opacity-30"><Minus className="h-4 w-4" /></button>
                <input id={`${titleId}-quantity`} type="number" min={1} max={Math.max(1, limit)} value={quantity}
                  disabled={submitting || missing.length > 0 || stock <= 0}
                  onChange={(event) => setQuantity(Math.max(1, Math.min(limit, Math.trunc(Number(event.target.value)) || 1)))}
                  className="w-14 min-w-0 bg-transparent text-center text-sm font-semibold" />
                <button type="button" aria-label="Tăng số lượng" disabled={submitting || !ready || quantity >= limit}
                  onClick={() => setQuantity((current) => Math.min(limit, current + 1))} className="p-3 disabled:opacity-30"><Plus className="h-4 w-4" /></button>
              </div>
            </div>
          </div>
          <footer className="shrink-0 border-t border-slate-100 bg-white p-4 pb-[max(1rem,env(safe-area-inset-bottom))] sm:p-5">
            <Button type="submit" loading={submitting} disabled={!ready} className="w-full bg-rose-600 py-3 hover:bg-rose-700">
              {intent === 'buy' ? 'Xác nhận mua' : 'Xác nhận thêm vào giỏ'}
            </Button>
          </footer>
        </form>
      </div>
    </div>, document.body,
  );
};
