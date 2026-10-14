import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ShoppingBag, Lock, Mail, User, Phone, ArrowRight, AlertCircle } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { CustomApiError } from '../types/api';

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const { register } = useAuth();
  const { success: toastSuccess } = useToast();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!name || !email || !password) {
      setErrorMessage('Vui lòng điền đầy đủ các thông tin bắt buộc (*)');
      return;
    }

    if (password.length < 12) {
      setErrorMessage('Mật khẩu phải có độ dài từ 12 ký tự trở lên theo yêu cầu bảo mật.');
      return;
    }

    if (password !== confirmPassword) {
      setErrorMessage('Xác nhận mật khẩu không trùng khớp.');
      return;
    }

    setLoading(true);
    try {
      await register({
        name: name.trim(),
        email: email.trim(),
        password,
        phone: phone.trim() || undefined,
      });

      toastSuccess('Đăng ký tài khoản thành công! Vui lòng đăng nhập.');
      navigate('/login');
    } catch (err: any) {
      if (err instanceof CustomApiError) {
        if (err.code === 'DUPLICATE_RESOURCE') {
          setErrorMessage('Địa chỉ email này đã được sử dụng. Vui lòng đăng nhập hoặc dùng email khác.');
        } else if (err.status === 422 && err.details && err.details.length > 0) {
          setErrorMessage(err.details.map((d) => d.reason).join(', '));
        } else {
          setErrorMessage(err.message || 'Đăng ký không thành công.');
        }
      } else {
        setErrorMessage('Lỗi kết nối tới máy chủ.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[85vh] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full bg-white rounded-3xl border border-slate-200/80 p-8 sm:p-10 shadow-sm space-y-6">
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-2xl bg-brand-600 text-white flex items-center justify-center mx-auto shadow-md shadow-brand-500/20">
            <ShoppingBag className="w-6 h-6" />
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Tạo Tài Khoản Mới</h1>
          <p className="text-xs text-slate-500">
            Đăng ký để mua sắm và theo dõi đơn hàng tại Novamart
          </p>
        </div>

        {errorMessage && (
          <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-2.5">
            <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
            <span className="leading-relaxed">{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Họ và tên"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Nguyễn Văn A"
            prefixIcon={<User className="w-4 h-4" />}
          />

          <Input
            label="Địa chỉ Email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="example@test.com"
            prefixIcon={<Mail className="w-4 h-4" />}
          />

          <Input
            label="Số điện thoại"
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="0912345678 (Tùy chọn)"
            prefixIcon={<Phone className="w-4 h-4" />}
          />

          <Input
            label="Mật khẩu (Tối thiểu 12 ký tự)"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••••••"
            prefixIcon={<Lock className="w-4 h-4" />}
          />

          <Input
            label="Xác nhận mật khẩu"
            type="password"
            required
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="••••••••••••"
            prefixIcon={<Lock className="w-4 h-4" />}
          />

          <Button
            type="submit"
            variant="primary"
            size="lg"
            className="w-full py-3 shadow-md shadow-brand-500/20"
            loading={loading}
            icon={<ArrowRight className="w-4 h-4" />}
          >
            Đăng ký tài khoản
          </Button>
        </form>

        <div className="pt-4 border-t border-slate-100 text-center text-xs text-slate-500">
          Đã có tài khoản?{' '}
          <Link to="/login" className="font-semibold text-brand-600 hover:text-brand-700">
            Đăng nhập ngay
          </Link>
        </div>
      </div>
    </div>
  );
};
