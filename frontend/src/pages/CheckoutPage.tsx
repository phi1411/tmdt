import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  MapPin,
  CreditCard,
  AlertCircle,
  Plus,
  ShieldCheck,
  RotateCcw,
  Banknote,
  Check,
} from 'lucide-react';
import { userApi } from '../api/userApi';
import { checkoutApi } from '../api/checkoutApi';
import { Address, PublicProfile } from '../types/user';
import { CheckoutQuote, CreateOrderRequest } from '../types/checkout';
import { useCart } from '../contexts/CartContext';
import { useToast } from '../contexts/ToastContext';
import { formatVND } from '../utils/formatters';
import { generateIdempotencyKey } from '../utils/idempotency';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Input } from '../components/ui/Input';
import { Skeleton } from '../components/ui/Skeleton';
import { CustomApiError } from '../types/api';

export const CheckoutPage: React.FC = () => {
  const navigate = useNavigate();
  const { refreshCart } = useCart();
  const { success: toastSuccess, error: toastError, warning: toastWarning } = useToast();

  const [profile, setProfile] = useState<PublicProfile | null>(null);
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [selectedAddressId, setSelectedAddressId] = useState<string>('');
  const [paymentMethod, setPaymentMethod] = useState<'COD' | 'VNPAY'>('COD');

  const [quote, setQuote] = useState<CheckoutQuote | null>(null);
  const [loadingQuote, setLoadingQuote] = useState<boolean>(false);
  const [quoteError, setQuoteError] = useState<string | null>(null);

  const [submitting, setSubmitting] = useState<boolean>(false);
  const pendingIntent = useRef<{ payload: CreateOrderRequest; key: string } | null>(null);

  // Address creation modal
  const [showAddressModal, setShowAddressModal] = useState<boolean>(false);
  const [newReceiverName, setNewReceiverName] = useState<string>('');
  const [newPhone, setNewPhone] = useState<string>('');
  const [newAddressLine, setNewAddressLine] = useState<string>('');
  const [newProvince, setNewProvince] = useState<string>('');
  const [newWard, setNewWard] = useState<string>('');
  const [newDistrict, setNewDistrict] = useState<string>('');
  const [savingAddress, setSavingAddress] = useState<boolean>(false);

  // Load user profile & addresses
  useEffect(() => {
    const loadProfileData = async () => {
      try {
        const prof = await userApi.getProfile();
        setProfile(prof);
        setAddresses(prof.addresses || []);

        if (prof.defaultAddressId) {
          setSelectedAddressId(prof.defaultAddressId);
        } else if (prof.addresses && prof.addresses.length > 0) {
          setSelectedAddressId(prof.addresses[0].id);
        }
      } catch (err: any) {
        toastError('Không thể tải thông tin địa chỉ giao hàng.');
      }
    };

    loadProfileData();
  }, [toastError]);

  // Fetch Checkout Quote from backend
  const fetchQuote = useCallback(async () => {
    if (!selectedAddressId || !paymentMethod) return;

    setLoadingQuote(true);
    setQuoteError(null);

    try {
      const q = await checkoutApi.getCheckoutQuote(selectedAddressId, paymentMethod);
      setQuote(q);
    } catch (err: any) {
      if (err instanceof CustomApiError) {
        if (err.status === 503 && err.code === 'PAYMENT_UNAVAILABLE') {
          setQuoteError(
            'Cổng thanh toán online VNPAY Sandbox hiện đang được bảo trì/nâng cấp. Vui lòng chuyển sang phương thức Thanh toán khi nhận hàng (COD).'
          );
        } else if (err.code === 'CART_EMPTY') {
          toastWarning('Giỏ hàng đang trống.');
          navigate('/cart');
        } else {
          setQuoteError(err.message || 'Không thể tạo báo giá cho giỏ hàng hiện tại.');
        }
      } else {
        setQuoteError('Lỗi kết nối khi lấy báo giá từ máy chủ.');
      }
      setQuote(null);
    } finally {
      setLoadingQuote(false);
    }
  }, [selectedAddressId, paymentMethod, navigate, toastWarning]);

  useEffect(() => {
    if (selectedAddressId) {
      fetchQuote();
    }
  }, [selectedAddressId, paymentMethod, fetchQuote]);

  // Handle new address creation
  const handleSaveAddress = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profile) return;

    if (!newReceiverName || !newPhone || !newAddressLine || !newProvince) {
      toastWarning('Vui lòng điền đầy đủ các thông tin bắt buộc (*)');
      return;
    }

    setSavingAddress(true);
    try {
      const res = await userApi.createAddress({
        receiverName: newReceiverName.trim(),
        phone: newPhone.trim(),
        addressLine: newAddressLine.trim(),
        province: newProvince.trim(),
        ward: newWard.trim() || undefined,
        district: newDistrict.trim() || undefined,
        expectedVersion: profile.version,
      });

      toastSuccess('Đã thêm địa chỉ giao hàng mới!');
      setShowAddressModal(false);

      // Reload profile
      const updatedProfile = await userApi.getProfile();
      setProfile(updatedProfile);
      setAddresses(updatedProfile.addresses || []);
      setSelectedAddressId(res.address.id);

      // Reset form
      setNewReceiverName('');
      setNewPhone('');
      setNewAddressLine('');
      setNewProvince('');
      setNewWard('');
      setNewDistrict('');
    } catch (err: any) {
      toastError(err?.message || 'Không thể lưu địa chỉ.');
    } finally {
      setSavingAddress(false);
    }
  };

  // Submit Order
  const handleConfirmOrder = async () => {
    if (!quote || !selectedAddressId) {
      toastWarning('Vui lòng chọn địa chỉ và đợi hệ thống tính báo giá.');
      return;
    }

    setSubmitting(true);
    const payload: CreateOrderRequest = {
      cartVersion: quote.cartVersion, addressId: selectedAddressId, paymentMethod, quoteToken: quote.quoteToken,
    };
    if (!pendingIntent.current || JSON.stringify(pendingIntent.current.payload) !== JSON.stringify(payload)) {
      pendingIntent.current = { payload, key: generateIdempotencyKey() };
    }
    const intent = pendingIntent.current;

    try {
      let res = await checkoutApi.createOrder(intent.payload, intent.key);

      // If VNPAY method with paymentUrl, redirect to provider sandbox
      if (paymentMethod === 'VNPAY') {
        if (!res.payment?.paymentUrl && res.payment?.retryRequired) {
          // Initial attempt already exists: recover its URL with the exact checkout request.
          res = await checkoutApi.createOrder(intent.payload, intent.key);
        }
        const paymentUrl = res.payment?.paymentUrl;

        if (paymentUrl) {
          pendingIntent.current = null;
          await refreshCart();
          toastSuccess('Đang chuyển hướng tới cổng thanh toán VNPAY Sandbox...');
          window.location.href = paymentUrl;
          return;
        }

        if (res.payment?.retryRequired || !paymentUrl) {
          toastWarning('Đơn hàng đã được ghi nhận. Liên kết thanh toán chưa sẵn sàng; nhấn xác nhận lại để khôi phục liên kết của cùng đơn hàng.');
          return;
        }
      }

      // Redirect to Order Success Page
      pendingIntent.current = null;
      toastSuccess('Đặt hàng thành công!');
      await refreshCart();
      navigate(
        `/order-success?orderId=${res.order.id}&orderCode=${res.order.orderCode}&total=${res.order.total}&method=${res.order.paymentMethod}`
      );
    } catch (err: any) {
      if (err instanceof CustomApiError) {
        if (err.status >= 400 && err.status < 500) pendingIntent.current = null;
        if (err.code === 'PRICE_CHANGED' || err.code === 'QUOTE_CHANGED' || err.code === 'QUOTE_EXPIRED') {
          toastWarning('Báo giá hoặc giỏ hàng đã thay đổi. Đang làm mới báo giá...');
          await fetchQuote();
        } else if (err.code === 'STOCK_CONFLICT') {
          toastError('Tồn kho sản phẩm không đủ. Vui lòng kiểm tra lại giỏ hàng.');
          navigate('/cart');
        } else {
          toastError(err.message || 'Không thể tạo đơn hàng.');
        }
      } else {
        toastError('Lỗi máy chủ khi tạo đơn hàng.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const selectedAddress = addresses.find((a) => a.id === selectedAddressId);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-8">
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Xác Nhận & Đặt Hàng
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Hoàn tất đơn hàng với hệ thống bảo đảm tính toàn vẹn giao dịch NoSQL
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Left Column: Address Selection & Payment Method */}
        <div className="lg:col-span-2 space-y-6">
          {/* Step 1: Delivery Address */}
          <section className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <MapPin className="w-5 h-5 text-brand-600" />
                <span>1. Địa Chỉ Nhận Hàng</span>
              </h2>

              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowAddressModal(true)}
                icon={<Plus className="w-4 h-4" />}
              >
                Thêm địa chỉ mới
              </Button>
            </div>

            {addresses.length === 0 ? (
              <div className="p-6 text-center rounded-xl bg-slate-50 border border-dashed border-slate-300 space-y-3">
                <p className="text-sm text-slate-600">Bạn chưa có địa chỉ nhận hàng nào trong sổ địa chỉ.</p>
                <Button variant="primary" size="sm" onClick={() => setShowAddressModal(true)}>
                  Thêm địa chỉ ngay
                </Button>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                {addresses.map((addr) => {
                  const isSelected = addr.id === selectedAddressId;
                  return (
                    <div
                      key={addr.id}
                      onClick={() => setSelectedAddressId(addr.id)}
                      className={`relative p-4 rounded-xl border cursor-pointer transition-all ${
                        isSelected
                          ? 'border-brand-600 bg-brand-50/30 ring-2 ring-brand-100 shadow-sm'
                          : 'border-slate-200 hover:border-slate-300 bg-white'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="font-semibold text-sm text-slate-900 flex items-center gap-2">
                          <span>{addr.receiverName}</span>
                          {addr.id === profile?.defaultAddressId && (
                            <span className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-medium">
                              Mặc định
                            </span>
                          )}
                        </div>
                        {isSelected && <Check className="w-4 h-4 text-brand-600 flex-shrink-0" />}
                      </div>

                      <div className="text-xs text-slate-500 mt-1 font-mono">{addr.phone}</div>
                      <div className="text-xs text-slate-600 mt-2 leading-relaxed">
                        {addr.addressLine}
                        {addr.ward ? `, ${addr.ward}` : ''}
                        {addr.district ? `, ${addr.district}` : ''}
                        {`, ${addr.province}`}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {/* Step 2: Payment Method */}
          <section className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm space-y-4">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2 pb-3 border-b border-slate-100">
              <CreditCard className="w-5 h-5 text-brand-600" />
              <span>2. Phương Thức Thanh Toán</span>
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
              {/* COD Option */}
              <div
                onClick={() => setPaymentMethod('COD')}
                className={`p-4 rounded-xl border cursor-pointer transition-all flex items-start gap-3 ${
                  paymentMethod === 'COD'
                    ? 'border-brand-600 bg-brand-50/30 ring-2 ring-brand-100 shadow-sm'
                    : 'border-slate-200 hover:border-slate-300 bg-white'
                }`}
              >
                <div className="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center flex-shrink-0">
                  <Banknote className="w-5 h-5" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-sm text-slate-900">Thanh toán khi nhận hàng (COD)</span>
                    {paymentMethod === 'COD' && <Check className="w-4 h-4 text-brand-600" />}
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    Thanh toán bằng tiền mặt trực tiếp cho nhân viên giao hàng khi nhận kiện hàng.
                  </p>
                </div>
              </div>

              {/* VNPAY Sandbox Option */}
              <div
                onClick={() => setPaymentMethod('VNPAY')}
                className={`p-4 rounded-xl border cursor-pointer transition-all flex items-start gap-3 ${
                  paymentMethod === 'VNPAY'
                    ? 'border-brand-600 bg-brand-50/30 ring-2 ring-brand-100 shadow-sm'
                    : 'border-slate-200 hover:border-slate-300 bg-white'
                }`}
              >
                <div className="w-10 h-10 rounded-lg bg-sky-50 text-sky-600 flex items-center justify-center flex-shrink-0">
                  <CreditCard className="w-5 h-5" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-sm text-slate-900">VNPAY Sandbox (Online)</span>
                    {paymentMethod === 'VNPAY' && <Check className="w-4 h-4 text-brand-600" />}
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    Thanh toán mô phỏng qua cổng VNPAY QR / Thẻ nội địa.
                  </p>
                </div>
              </div>
            </div>

            {/* VNPAY Maintenance Warning if selected and error */}
            {paymentMethod === 'VNPAY' && quoteError && (
              <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs leading-relaxed flex items-start gap-2.5">
                <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold">Thông báo từ cổng VNPAY: </span>
                  <span>{quoteError}</span>
                </div>
              </div>
            )}
          </section>
        </div>

        {/* Right Column: Order Quote Summary */}
        <aside className="w-full bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm space-y-6">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h2 className="text-lg font-bold text-slate-900">Đơn Hàng Của Bạn</h2>
            <button
              onClick={fetchQuote}
              disabled={loadingQuote}
              className="text-xs text-slate-400 hover:text-brand-600 flex items-center gap-1"
              title="Tính lại báo giá"
            >
              <RotateCcw className={`w-3.5 h-3.5 ${loadingQuote ? 'animate-spin' : ''}`} />
              <span>Cập nhật</span>
            </button>
          </div>

          {loadingQuote ? (
            <div className="space-y-3 py-4">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
            </div>
          ) : quote ? (
            <div className="space-y-4">
              {/* Items Snapshot Preview */}
              <div className="max-h-56 overflow-y-auto space-y-2.5 pr-1 divide-y divide-slate-100">
                {quote.items.map((item, idx) => (
                  <div key={idx} className="pt-2 first:pt-0 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2.5 min-w-0 pr-2">
                      <div className="w-8 h-8 rounded bg-slate-100 overflow-hidden flex-shrink-0">
                        {item.image && <img src={item.image} alt={item.productName} className="w-full h-full object-cover" />}
                      </div>
                      <div className="truncate">
                        <div className="font-medium text-slate-800 truncate">{item.productName}</div>
                        <div className="text-[10px] text-slate-400">SL: {item.quantity}</div>
                      </div>
                    </div>
                    <div className="font-semibold text-slate-900 whitespace-nowrap">
                      {formatVND(item.lineTotal)}
                    </div>
                  </div>
                ))}
              </div>

              {/* Price Details */}
              <div className="pt-4 border-t border-slate-100 space-y-2.5 text-sm">
                <div className="flex justify-between text-slate-600">
                  <span>Tiền hàng:</span>
                  <span className="font-semibold text-slate-900">{formatVND(quote.subtotal)}</span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>Phí vận chuyển:</span>
                  <span className="font-semibold text-slate-900">{formatVND(quote.shippingFee)}</span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>Giảm giá:</span>
                  <span className="font-semibold text-slate-900">0 ₫</span>
                </div>
              </div>

              {/* Total Payable */}
              <div className="pt-4 border-t border-slate-100 flex justify-between items-baseline">
                <span className="text-base font-bold text-slate-900">Tổng thanh toán:</span>
                <span className="text-2xl font-extrabold text-brand-700">
                  {formatVND(quote.total)}
                </span>
              </div>

              {/* Delivery Address Summary */}
              {selectedAddress && (
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/60 text-xs space-y-1">
                  <div className="text-slate-500 font-medium">Giao tới:</div>
                  <div className="font-semibold text-slate-800">
                    {selectedAddress.receiverName} ({selectedAddress.phone})
                  </div>
                  <div className="text-slate-600 truncate">
                    {selectedAddress.addressLine}, {selectedAddress.province}
                  </div>
                </div>
              )}

              {/* Submit CTA */}
              <Button
                variant="primary"
                size="lg"
                className="w-full py-3.5 text-base shadow-md shadow-brand-500/20"
                disabled={submitting || !quote || loadingQuote}
                loading={submitting}
                onClick={handleConfirmOrder}
              >
                Xác nhận đặt hàng
              </Button>
            </div>
          ) : (
            <div className="text-center py-6 text-sm text-slate-400">
              {quoteError ? (
                <span className="text-rose-600 text-xs">{quoteError}</span>
              ) : (
                'Vui lòng chọn địa chỉ giao hàng để tính toán báo giá.'
              )}
            </div>
          )}

          <div className="flex items-center gap-2 justify-center text-[11px] text-slate-400 pt-2">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>Cam kết snapshot giá và trừ kho nguyên tử</span>
          </div>
        </aside>
      </div>

      {/* Add Address Modal */}
      <Modal
        isOpen={showAddressModal}
        onClose={() => setShowAddressModal(false)}
        title="Thêm Địa Chỉ Nhận Hàng"
        description="Nhập thông tin người nhận hàng chính xác để vận chuyển thuận lợi."
      >
        <form onSubmit={handleSaveAddress} className="space-y-4">
          <Input
            label="Họ và tên người nhận"
            required
            value={newReceiverName}
            onChange={(e) => setNewReceiverName(e.target.value)}
            placeholder="Ví dụ: Nguyễn Văn A"
          />

          <Input
            label="Số điện thoại"
            required
            value={newPhone}
            onChange={(e) => setNewPhone(e.target.value)}
            placeholder="Ví dụ: 0912345678"
          />

          <Input
            label="Địa chỉ cụ thể (Số nhà, tên đường)"
            required
            value={newAddressLine}
            onChange={(e) => setNewAddressLine(e.target.value)}
            placeholder="Ví dụ: 123 Đường Nguyễn Huệ"
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              label="Tỉnh / Thành phố"
              required
              value={newProvince}
              onChange={(e) => setNewProvince(e.target.value)}
              placeholder="Ví dụ: TP. Hồ Chí Minh"
            />
            <Input
              label="Quận / Huyện"
              value={newDistrict}
              onChange={(e) => setNewDistrict(e.target.value)}
              placeholder="Ví dụ: Quận 1"
            />
          </div>

          <Input
            label="Phường / Xã"
            value={newWard}
            onChange={(e) => setNewWard(e.target.value)}
            placeholder="Ví dụ: Phường Bến Nghé"
          />

          <div className="pt-4 flex justify-end gap-3 border-t border-slate-100">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setShowAddressModal(false)}
            >
              Hủy
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              loading={savingAddress}
            >
              Lưu địa chỉ
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
