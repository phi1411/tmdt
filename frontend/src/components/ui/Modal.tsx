import React, { useEffect, ReactNode } from 'react';
import { X } from 'lucide-react';
import { cn } from '../../utils/cn';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl';
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  description,
  children,
  footer,
  maxWidth = 'md',
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.body.style.overflow = 'unset';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const maxWidths = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm transition-opacity animate-in fade-in"
        onClick={onClose}
      />

      {/* Modal Dialog */}
      <div
        className={cn(
          'relative w-full rounded-2xl bg-white shadow-2xl border border-slate-100 z-10 transition-all animate-in zoom-in-95',
          maxWidths[maxWidth]
        )}
      >
        {/* Header */}
        {(title || description) && (
          <div className="flex items-start justify-between border-b border-slate-100 p-5 sm:p-6">
            <div>
              {title && <h3 className="text-lg font-semibold text-slate-900">{title}</h3>}
              {description && <p className="text-sm text-slate-500 mt-1">{description}</p>}
            </div>
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-slate-600 rounded-lg p-1.5 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        )}

        {/* Body */}
        <div className="p-5 sm:p-6">{children}</div>

        {/* Footer */}
        {footer && (
          <div className="flex items-center justify-end gap-3 border-t border-slate-100 p-4 sm:px-6 bg-slate-50/50 rounded-b-2xl">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};
