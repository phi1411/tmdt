import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from './Button';

export interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Đã xảy ra lỗi',
  message = 'Không thể tải dữ liệu từ máy chủ. Vui lòng thử lại sau.',
  onRetry,
  className,
}) => {
  return (
    <div className={`flex flex-col items-center justify-center p-8 sm:p-12 text-center rounded-2xl border border-rose-200 bg-rose-50/50 ${className || ''}`}>
      <div className="w-12 h-12 rounded-full bg-rose-100 flex items-center justify-center text-rose-600 mb-4">
        <AlertCircle className="w-6 h-6" />
      </div>
      <h3 className="text-base sm:text-lg font-semibold text-rose-950 mb-1">{title}</h3>
      <p className="text-sm text-rose-700 max-w-sm mb-6">{message}</p>
      {onRetry && (
        <Button onClick={onRetry} variant="outline" size="sm" icon={<RefreshCw className="w-4 h-4" />}>
          Thử lại
        </Button>
      )}
    </div>
  );
};
