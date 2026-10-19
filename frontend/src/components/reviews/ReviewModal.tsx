import React, { useState } from 'react';
import { Star, Image as ImageIcon, X, Plus, AlertCircle } from 'lucide-react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { catalogApi } from '../../api/catalogApi';
import { CustomApiError } from '../../types/api';
import { useToast } from '../../contexts/ToastContext';

export interface ReviewItemInfo {
  productId: string;
  productName: string;
  image?: string;
  sku?: string;
  selectedAttributes?: Record<string, any>;
}

export interface ReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  orderId: string;
  item: ReviewItemInfo | null;
  onSuccess?: () => void;
}

const STAR_LABELS: Record<number, string> = {
  1: 'Tệ',
  2: 'Không hài lòng',
  3: 'Bình thường',
  4: 'Hài lòng',
  5: 'Tuyệt vời',
};

export const ReviewModal: React.FC<ReviewModalProps> = ({
  isOpen,
  onClose,
  orderId,
  item,
  onSuccess,
}) => {
  const { success: toastSuccess } = useToast();

  const [rating, setRating] = useState<number>(5);
  const [hoverRating, setHoverRating] = useState<number>(0);
  const [reviewText, setReviewText] = useState<string>('');
  const [images, setImages] = useState<string[]>([]);
  const [imageUrlInput, setImageUrlInput] = useState<string>('');
  const [showImageUrlInput, setShowImageUrlInput] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!item) return null;

  const currentStar = hoverRating || rating;

  const handleAddImageUrl = () => {
    const trimmed = imageUrlInput.trim();
    if (!trimmed) return;

    let validUrl = false;
    try {
      const parsed = new URL(trimmed);
      validUrl = !parsed.username && !parsed.password && !/[\s\\\x00-\x1f\x7f]/.test(trimmed) &&
        (parsed.protocol === 'https:' || (parsed.protocol === 'http:' && ['localhost', '127.0.0.1'].includes(parsed.hostname)));
    } catch { /* Invalid URL is shown in the form. */ }
    if (!validUrl) {
      setErrorMessage('Ảnh phải là URL HTTPS; HTTP chỉ dùng cho localhost.');
      return;
    }

    if (images.length >= 5) {
      setErrorMessage('Chỉ được đính kèm tối đa 5 hình ảnh');
      return;
    }

    setImages((prev) => [...prev, trimmed]);
    setImageUrlInput('');
    setShowImageUrlInput(false);
    setErrorMessage(null);
  };

  const handleRemoveImage = (index: number) => {
    setImages((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (rating < 1 || rating > 5) {
      setErrorMessage('Vui lòng chọn số sao đánh giá (1 - 5 sao).');
      return;
    }

    setSubmitting(true);
    setErrorMessage(null);

    try {
      await catalogApi.createReview(item.productId, {
        orderId,
        rating,
        reviewText: reviewText.trim() || undefined,
        images: images.length > 0 ? images : undefined,
      });

      toastSuccess('Gửi đánh giá sản phẩm thành công! Cảm ơn bạn đã đóng góp.');
      onClose();
      if (onSuccess) {
        onSuccess();
      }
    } catch (err: any) {
      if (err instanceof CustomApiError) {
        if (err.code === 'ALREADY_REVIEWED') {
          setErrorMessage('Bạn đã đánh giá sản phẩm này cho đơn hàng này rồi.');
        } else if (err.code === 'ORDER_NOT_COMPLETED') {
          setErrorMessage('Chỉ có thể đánh giá khi đơn hàng đã hoàn tất giao hàng.');
        } else if (err.code === 'PRODUCT_NOT_IN_ORDER') {
          setErrorMessage('Sản phẩm không thuộc đơn hàng này.');
        } else {
          setErrorMessage(err.message || 'Không thể gửi đánh giá.');
        }
      } else {
        setErrorMessage('Đã xảy ra lỗi khi gửi đánh giá. Vui lòng thử lại sau.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const selectedAttrs = item.selectedAttributes
    ? Object.entries(item.selectedAttributes).filter(([k]) => k !== 'skuId').map(([k, v]) => `${k === 'size' ? 'Size' : k === 'color' ? 'Màu' : k}: ${String(v)}`).join(' • ')
    : '';

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Đánh Giá Sản Phẩm"
      description="Chia sẻ trải nghiệm sử dụng thực tế để giúp cộng đồng mua sắm tốt hơn"
      maxWidth="lg"
    >
      <form onSubmit={handleSubmit} className="space-y-6 pt-2">
        {/* Product summary card */}
        <div className="flex items-center gap-3.5 p-3 rounded-2xl bg-slate-50 border border-slate-100">
          <div className="w-14 h-14 rounded-xl bg-white border border-slate-200/70 overflow-hidden flex-shrink-0 flex items-center justify-center">
            {item.image ? (
              <img src={item.image} alt={item.productName} className="w-full h-full object-cover" />
            ) : (
              <span className="text-[10px] text-slate-400">Không ảnh</span>
            )}
          </div>
          <div className="space-y-0.5 min-w-0 flex-1">
            <h4 className="text-sm font-semibold text-slate-900 line-clamp-1">{item.productName}</h4>
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
              {item.sku && <span className="font-mono text-[11px] text-slate-400">SKU: {item.sku}</span>}
              {selectedAttrs && (
                <>
                  <span>•</span>
                  <span>{selectedAttrs}</span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Rating stars */}
        <div className="space-y-2 text-center py-2">
          <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block">
            Chất lượng sản phẩm
          </label>
          <div className="flex items-center justify-center gap-2">
            {[1, 2, 3, 4, 5].map((star) => {
              const active = star <= currentStar;
              return (
                <button
                  key={star}
                  type="button"
                  onClick={() => setRating(star)}
                  onMouseEnter={() => setHoverRating(star)}
                  onMouseLeave={() => setHoverRating(0)}
                  className="p-1 text-slate-300 hover:scale-110 active:scale-95 transition-transform focus:outline-none"
                  aria-label={`${star} sao`}
                >
                  <Star
                    className={`w-8 h-8 transition-colors ${
                      active ? 'fill-amber-400 text-amber-400' : 'text-slate-300'
                    }`}
                  />
                </button>
              );
            })}
          </div>
          <div className="text-sm font-semibold text-amber-600 min-h-[20px]">
            {STAR_LABELS[currentStar] || ''}
          </div>
        </div>

        {/* Textarea reviewText */}
        <div className="space-y-1.5">
          <div className="flex justify-between items-center text-xs">
            <label htmlFor="review-text" className="font-bold text-slate-700">
              Nhận xét chi tiết
            </label>
            <span className="text-slate-400">{reviewText.length}/2000</span>
          </div>
          <textarea
            id="review-text"
            rows={4}
            value={reviewText}
            onChange={(e) => setReviewText(e.target.value.slice(0, 2000))}
            placeholder="Hãy chia sẻ cảm nhận về chất lượng sản phẩm, độ hoàn thiện, trải nghiệm thực tế..."
            className="w-full rounded-xl border border-slate-200 p-3 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-all resize-none"
          />
        </div>

        {/* Image upload / URL attachment */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
              <ImageIcon className="w-4 h-4 text-slate-500" />
              <span>Hình ảnh thực tế ({images.length}/5)</span>
            </label>
            {images.length < 5 && !showImageUrlInput && (
              <button
                type="button"
                onClick={() => setShowImageUrlInput(true)}
                className="text-xs text-brand-600 font-semibold hover:text-brand-700 flex items-center gap-1"
              >
                <Plus className="w-3.5 h-3.5" /> Thêm link ảnh
              </button>
            )}
          </div>

          {showImageUrlInput && (
            <div className="flex gap-2">
              <input
                type="url"
                value={imageUrlInput}
                onChange={(e) => setImageUrlInput(e.target.value)}
                placeholder="https://example.com/anh-thuc-te.jpg"
                className="flex-1 text-xs rounded-xl border border-slate-200 px-3 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
              <Button type="button" size="sm" onClick={handleAddImageUrl}>
                Thêm
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  setShowImageUrlInput(false);
                  setImageUrlInput('');
                }}
              >
                Hủy
              </Button>
            </div>
          )}

          {images.length > 0 && (
            <div className="flex flex-wrap gap-2.5 pt-1">
              {images.map((img, idx) => (
                <div
                  key={idx}
                  className="relative group w-16 h-16 rounded-xl border border-slate-200 overflow-hidden bg-slate-100"
                >
                  <img src={img} alt={`Đính kèm ${idx + 1}`} className="w-full h-full object-cover" />
                  <button
                    type="button"
                    onClick={() => handleRemoveImage(idx)}
                    className="absolute top-1 right-1 p-0.5 rounded-full bg-slate-900/70 text-white hover:bg-rose-600 transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Error message display */}
        {errorMessage && (
          <div className="p-3 rounded-xl bg-rose-50 border border-rose-200/80 flex items-start gap-2.5 text-xs text-rose-700">
            <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
            <div className="leading-relaxed font-medium">{errorMessage}</div>
          </div>
        )}

        {/* Action buttons */}
        <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
          <Button type="button" variant="outline" onClick={onClose} disabled={submitting}>
            Trở lại
          </Button>
          <Button type="submit" variant="primary" loading={submitting}>
            Gửi đánh giá
          </Button>
        </div>
      </form>
    </Modal>
  );
};
