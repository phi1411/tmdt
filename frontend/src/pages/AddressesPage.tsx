import React, { useEffect, useState } from 'react';
import { MapPin, Plus, Check, Trash2, Edit2 } from 'lucide-react';
import { userApi } from '../api/userApi';
import { Address, PublicProfile } from '../types/user';
import { useToast } from '../contexts/ToastContext';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Input } from '../components/ui/Input';
import { Skeleton } from '../components/ui/Skeleton';
import { EmptyState } from '../components/ui/EmptyState';

export const AddressesPage: React.FC = () => {
  const { success: toastSuccess, error: toastError, warning: toastWarning } = useToast();

  const [profile, setProfile] = useState<PublicProfile | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Address modal states
  const [modalOpen, setModalOpen] = useState<boolean>(false);
  const [editingAddressId, setEditingAddressId] = useState<string | null>(null);

  const [receiverName, setReceiverName] = useState<string>('');
  const [phone, setPhone] = useState<string>('');
  const [addressLine, setAddressLine] = useState<string>('');
  const [province, setProvince] = useState<string>('');
  const [ward, setWard] = useState<string>('');
  const [district, setDistrict] = useState<string>('');
  const [label, setLabel] = useState<string>('');
  const [saving, setSaving] = useState<boolean>(false);

  // Delete modal
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<boolean>(false);

  const loadData = async () => {
    try {
      setLoading(true);
      const data = await userApi.getProfile();
      setProfile(data);
    } catch (err: any) {
      toastError('Không thể tải sổ địa chỉ.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const openAddModal = () => {
    setEditingAddressId(null);
    setReceiverName('');
    setPhone('');
    setAddressLine('');
    setProvince('');
    setWard('');
    setDistrict('');
    setLabel('');
    setModalOpen(true);
  };

  const openEditModal = (addr: Address) => {
    setEditingAddressId(addr.id);
    setReceiverName(addr.receiverName);
    setPhone(addr.phone);
    setAddressLine(addr.addressLine);
    setProvince(addr.province);
    setWard(addr.ward || '');
    setDistrict(addr.district || '');
    setLabel(addr.label || '');
    setModalOpen(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profile) return;

    if (!receiverName || !phone || !addressLine || !province) {
      toastWarning('Vui lòng điền đầy đủ các thông tin bắt buộc (*)');
      return;
    }

    setSaving(true);
    try {
      if (editingAddressId) {
        await userApi.updateAddress(editingAddressId, {
          receiverName: receiverName.trim(),
          phone: phone.trim(),
          addressLine: addressLine.trim(),
          province: province.trim(),
          ward: ward.trim() || undefined,
          district: district.trim() || undefined,
          label: label.trim() || undefined,
          expectedVersion: profile.version,
        });
        toastSuccess('Cập nhật địa chỉ thành công!');
      } else {
        await userApi.createAddress({
          receiverName: receiverName.trim(),
          phone: phone.trim(),
          addressLine: addressLine.trim(),
          province: province.trim(),
          ward: ward.trim() || undefined,
          district: district.trim() || undefined,
          label: label.trim() || undefined,
          expectedVersion: profile.version,
        });
        toastSuccess('Đã thêm địa chỉ mới!');
      }
      setModalOpen(false);
      await loadData();
    } catch (err: any) {
      toastError(err?.message || 'Không thể lưu địa chỉ.');
    } finally {
      setSaving(false);
    }
  };

  const handleSetDefault = async (addrId: string) => {
    if (!profile) return;
    try {
      await userApi.setDefaultAddress({
        addressId: addrId,
        expectedVersion: profile.version,
      });
      toastSuccess('Đã đặt làm địa chỉ mặc định!');
      await loadData();
    } catch (err: any) {
      toastError(err?.message || 'Không thể đặt địa chỉ mặc định.');
    }
  };

  const handleDelete = async () => {
    if (!profile || !deleteConfirmId) return;

    setDeleting(true);
    try {
      await userApi.deleteAddress(deleteConfirmId, {
        expectedVersion: profile.version,
      });
      toastSuccess('Đã xóa địa chỉ.');
      setDeleteConfirmId(null);
      await loadData();
    } catch (err: any) {
      toastError(err?.message || 'Không thể xóa địa chỉ.');
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-8 space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Skeleton className="h-36 rounded-xl" />
          <Skeleton className="h-36 rounded-xl" />
        </div>
      </div>
    );
  }

  const addresses = profile?.addresses || [];

  return (
    <div className="bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-8 shadow-sm space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-slate-100">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <MapPin className="w-5 h-5 text-brand-600" />
            <span>Sổ Địa Chỉ Giao Hàng</span>
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Tối đa 10 địa chỉ nhận hàng theo giới hạn thiết kế NoSQL.
          </p>
        </div>

        <Button
          variant="primary"
          size="sm"
          onClick={openAddModal}
          disabled={addresses.length >= 10}
          icon={<Plus className="w-4 h-4" />}
        >
          Thêm địa chỉ
        </Button>
      </div>

      {addresses.length === 0 ? (
        <EmptyState
          icon={<MapPin className="w-8 h-8" />}
          title="Chưa có địa chỉ nào"
          description="Thêm địa chỉ giao hàng để tiện cho việc mua sắm và thanh toán sau này."
          actionLabel="Thêm địa chỉ ngay"
          onAction={openAddModal}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {addresses.map((addr) => {
            const isDefault = addr.id === profile?.defaultAddressId;

            return (
              <div
                key={addr.id}
                className={`p-5 rounded-2xl border flex flex-col justify-between transition-all ${
                  isDefault
                    ? 'border-brand-500 bg-brand-50/20 shadow-xs ring-1 ring-brand-100'
                    : 'border-slate-200 hover:border-slate-300 bg-white'
                }`}
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-sm text-slate-900">{addr.receiverName}</span>
                    {isDefault ? (
                      <span className="px-2 py-0.5 rounded-full bg-brand-100 text-brand-700 text-[11px] font-semibold flex items-center gap-1">
                        <Check className="w-3 h-3" /> Mặc định
                      </span>
                    ) : (
                      <button
                        onClick={() => handleSetDefault(addr.id)}
                        className="text-xs text-slate-400 hover:text-brand-600 font-medium"
                      >
                        Đặt làm mặc định
                      </button>
                    )}
                  </div>

                  <div className="text-xs text-slate-500 font-mono">{addr.phone}</div>
                  <div className="text-xs text-slate-600 leading-relaxed">
                    {addr.addressLine}
                    {addr.ward ? `, ${addr.ward}` : ''}
                    {addr.district ? `, ${addr.district}` : ''}
                    {`, ${addr.province}`}
                  </div>

                  {addr.label && (
                    <span className="inline-block mt-1 text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-medium">
                      {addr.label}
                    </span>
                  )}
                </div>

                <div className="flex items-center justify-end gap-2 pt-4 border-t border-slate-100 mt-4">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => openEditModal(addr)}
                    className="text-xs px-2.5 py-1"
                    icon={<Edit2 className="w-3.5 h-3.5" />}
                  >
                    Sửa
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setDeleteConfirmId(addr.id)}
                    className="text-xs px-2.5 py-1 text-rose-600 hover:text-rose-700 hover:bg-rose-50"
                    icon={<Trash2 className="w-3.5 h-3.5" />}
                  >
                    Xóa
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Add / Edit Modal */}
      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editingAddressId ? 'Chỉnh Sửa Địa Chỉ' : 'Thêm Địa Chỉ Nhận Hàng'}
      >
        <form onSubmit={handleSave} className="space-y-4">
          <Input
            label="Họ và tên người nhận"
            required
            value={receiverName}
            onChange={(e) => setReceiverName(e.target.value)}
            placeholder="Ví dụ: Nguyễn Văn A"
          />

          <Input
            label="Số điện thoại"
            required
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="Ví dụ: 0912345678"
          />

          <Input
            label="Địa chỉ cụ thể (Số nhà, tên đường)"
            required
            value={addressLine}
            onChange={(e) => setAddressLine(e.target.value)}
            placeholder="Ví dụ: 123 Đường Nguyễn Huệ"
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              label="Tỉnh / Thành phố"
              required
              value={province}
              onChange={(e) => setProvince(e.target.value)}
              placeholder="Ví dụ: TP. Hồ Chí Minh"
            />
            <Input
              label="Quận / Huyện"
              value={district}
              onChange={(e) => setDistrict(e.target.value)}
              placeholder="Ví dụ: Quận 1"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              label="Phường / Xã"
              value={ward}
              onChange={(e) => setWard(e.target.value)}
              placeholder="Ví dụ: Phường Bến Nghé"
            />
            <Input
              label="Nhãn địa chỉ"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="Nhà riêng, Văn phòng..."
            />
          </div>

          <div className="pt-4 flex justify-end gap-3 border-t border-slate-100">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setModalOpen(false)}
            >
              Hủy
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              loading={saving}
            >
              Lưu địa chỉ
            </Button>
          </div>
        </form>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={!!deleteConfirmId}
        onClose={() => setDeleteConfirmId(null)}
        title="Xác Nhận Xóa Địa Chỉ"
        description="Bạn có chắc chắn muốn xóa địa chỉ nhận hàng này không?"
      >
        <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setDeleteConfirmId(null)}
          >
            Hủy
          </Button>
          <Button
            variant="danger"
            size="sm"
            loading={deleting}
            onClick={handleDelete}
          >
            Xác nhận xóa
          </Button>
        </div>
      </Modal>
    </div>
  );
};
