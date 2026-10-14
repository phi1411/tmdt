import React from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, Home, ShoppingBag } from 'lucide-react';
import { Button } from '../components/ui/Button';

export const NotFoundPage: React.FC = () => {
  return (
    <div className="min-h-[70vh] flex items-center justify-center py-16 px-4 text-center">
      <div className="max-w-md space-y-6">
        <div className="w-16 h-16 rounded-full bg-slate-100 text-slate-500 flex items-center justify-center mx-auto">
          <AlertCircle className="w-8 h-8" />
        </div>

        <div className="space-y-2">
          <span className="text-4xl font-extrabold text-slate-900 tracking-tight font-mono">404</span>
          <h1 className="text-xl font-bold text-slate-800">Trang không tồn tại</h1>
          <p className="text-sm text-slate-500 leading-relaxed">
            Đường dẫn bạn yêu cầu không tồn tại hoặc đã được thay đổi.
          </p>
        </div>

        <div className="flex items-center justify-center gap-3 pt-2">
          <Link to="/">
            <Button variant="primary" size="md" icon={<Home className="w-4 h-4" />}>
              Về trang chủ
            </Button>
          </Link>
          <Link to="/products">
            <Button variant="outline" size="md" icon={<ShoppingBag className="w-4 h-4" />}>
              Xem sản phẩm
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
};
