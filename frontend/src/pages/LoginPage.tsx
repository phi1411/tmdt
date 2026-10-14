import React, { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ShoppingBag, Lock, Mail, ArrowRight, AlertCircle } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { CustomApiError } from '../types/api';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const redirectUrl = searchParams.get('redirect') || '/';

  const { login } = useAuth();
  const { success: toastSuccess } = useToast();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!email || !password) {
      setErrorMessage('Vui lòng điền đầy đủ email và mật khẩu.');
      return;
    }

    setLoading(true);
    try {
      const user = await login({ email: email.trim(), password });
      toastSuccess(`Chào mừng trở lại, ${user.name}!`);
      navigate(redirectUrl, { replace: true });
    } catch (err: any) {
      if (err instanceof CustomApiError) {
        if (err.status === 401) {
          setErrorMessage('Email hoặc mật khẩu không chính xác, hoặc tài khoản đã bị khóa.');
        } else if (err.status === 429) {
          setErrorMessage('Bạn đã thao tác đăng nhập quá nhiều lần. Vui lòng thử lại sau 60 giây.');
        } else {
          setErrorMessage(err.message || 'Đăng nhập không thành công.');
        }
      } else {
        setErrorMessage('Lỗi kết nối tới máy chủ.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full bg-white rounded-3xl border border-slate-200/80 p-8 sm:p-10 shadow-sm space-y-6">
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-2xl bg-brand-600 text-white flex items-center justify-center mx-auto shadow-md shadow-brand-500/20">
            <ShoppingBag className="w-6 h-6" />
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Đăng Nhập Novamart</h1>
          <p className="text-xs text-slate-500">
            Nhập thông tin tài khoản khách hàng để tiếp tục mua sắm
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
            label="Địa chỉ Email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="example@test.com"
            prefixIcon={<Mail className="w-4 h-4" />}
          />

          <Input
            label="Mật khẩu"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
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
            Đăng nhập
          </Button>
        </form>

        <div className="pt-4 border-t border-slate-100 text-center text-xs text-slate-500">
          Chưa có tài khoản?{' '}
          <Link to="/register" className="font-semibold text-brand-600 hover:text-brand-700">
            Đăng ký tài khoản mới
          </Link>
        </div>
      </div>
    </div>
  );
};
