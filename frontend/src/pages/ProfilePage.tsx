import React, { useEffect, useState } from 'react';
import { User, Lock, Save, KeyRound } from 'lucide-react';
import { userApi } from '../api/userApi';
import { authApi } from '../api/authApi';
import { PublicProfile } from '../types/user';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Skeleton } from '../components/ui/Skeleton';
import { formatDateTime } from '../utils/formatters';
import { CustomApiError } from '../types/api';

export const ProfilePage: React.FC = () => {
  const { refreshUser, logout } = useAuth();
  const { success: toastSuccess, error: toastError, warning: toastWarning } = useToast();

  const [profile, setProfile] = useState<PublicProfile | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Edit profile states
  const [name, setName] = useState<string>('');
  const [phone, setPhone] = useState<string>('');
  const [updatingProfile, setUpdatingProfile] = useState<boolean>(false);

  // Change password states
  const [currentPassword, setCurrentPassword] = useState<string>('');
  const [newPassword, setNewPassword] = useState<string>('');
  const [confirmPassword, setConfirmPassword] = useState<string>('');
  const [updatingPassword, setUpdatingPassword] = useState<boolean>(false);

  const loadProfile = async () => {
    try {
      setLoading(true);
      const data = await userApi.getProfile();
      setProfile(data);
      setName(data.name);
      setPhone(data.phone || '');
    } catch (err: any) {
      toastError('Không thể tải thông tin tài khoản.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProfile();
  }, []);

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profile) return;

    if (!name.trim()) {
      toastWarning('Họ tên không được để trống.');
      return;
    }

    setUpdatingProfile(true);
    try {
      const updated = await userApi.updateProfile({
        name: name.trim(),
        phone: phone.trim() || undefined,
        expectedVersion: profile.version,
      });
      setProfile(updated);
      await refreshUser();
      toastSuccess('Đã cập nhật thông tin cá nhân!');
    } catch (err: any) {
      if (err instanceof CustomApiError && err.code === 'CONFLICT') {
        toastWarning('Thông tin đã thay đổi, đang làm mới...');
        await loadProfile();
      } else {
        toastError(err?.message || 'Không thể cập nhật hồ sơ.');
      }
    } finally {
      setUpdatingProfile(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentPassword || !newPassword) {
      toastWarning('Vui lòng điền mật khẩu hiện tại và mật khẩu mới.');
      return;
    }

    if (newPassword.length < 12) {
      toastWarning('Mật khẩu mới phải có độ dài từ 12 ký tự trở lên.');
      return;
    }

    if (newPassword !== confirmPassword) {
      toastWarning('Xác nhận mật khẩu mới không khớp.');
      return;
    }

    setUpdatingPassword(true);
    try {
      const res = await authApi.changePassword({
        currentPassword,
        newPassword,
      });

      if (res.reauthenticationRequired) {
        toastSuccess('Đổi mật khẩu thành công! Vui lòng đăng nhập lại.');
        logout();
      } else {
        toastSuccess('Đổi mật khẩu thành công!');
        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');
      }
    } catch (err: any) {
      toastError(err?.message || 'Không thể đổi mật khẩu.');
    } finally {
      setUpdatingPassword(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-8 space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Profile Overview Card */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-8 shadow-sm space-y-6">
        <div className="flex items-center gap-2 pb-4 border-b border-slate-100">
          <User className="w-5 h-5 text-brand-600" />
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Hồ Sơ Cá Nhân</h1>
        </div>

        <form onSubmit={handleUpdateProfile} className="space-y-4 max-w-xl">
          <Input
            label="Họ và tên"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            placeholder="Nguyễn Văn A"
          />

          <Input
            label="Địa chỉ Email"
            value={profile?.email || ''}
            disabled
            helperText="Email tài khoản cố định và không thể thay đổi."
          />

          <Input
            label="Số điện thoại"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="Ví dụ: 0912345678"
            helperText="Dùng để liên hệ giao hàng và thông báo trạng thái đơn hàng."
          />

          <div className="pt-2 flex items-center justify-between text-xs text-slate-400">
            <span>Ngày tạo tài khoản: {formatDateTime(profile?.createdAt)}</span>
            <span>Phiên bản dữ liệu (OCC): v{profile?.version}</span>
          </div>

          <div className="pt-2">
            <Button
              type="submit"
              variant="primary"
              size="md"
              loading={updatingProfile}
              icon={<Save className="w-4 h-4" />}
            >
              Lưu thay đổi
            </Button>
          </div>
        </form>
      </div>

      {/* Change Password Card */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-8 shadow-sm space-y-6">
        <div className="flex items-center gap-2 pb-4 border-b border-slate-100">
          <KeyRound className="w-5 h-5 text-brand-600" />
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Đổi Mật Khẩu</h2>
        </div>

        <form onSubmit={handleChangePassword} className="space-y-4 max-w-xl">
          <Input
            label="Mật khẩu hiện tại"
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            required
            placeholder="••••••••••••"
          />

          <Input
            label="Mật khẩu mới"
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            placeholder="Ít nhất 12 ký tự"
            helperText="Hệ thống yêu cầu mật khẩu tối thiểu 12 ký tự chuẩn mã hóa Argon2id."
          />

          <Input
            label="Xác nhận mật khẩu mới"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            placeholder="Nhập lại mật khẩu mới"
          />

          <div className="pt-2">
            <Button
              type="submit"
              variant="outline"
              size="md"
              loading={updatingPassword}
              icon={<Lock className="w-4 h-4" />}
            >
              Cập nhật mật khẩu
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
