import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

export interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  className?: string;
}

export const Pagination: React.FC<PaginationProps> = ({
  currentPage,
  totalPages,
  onPageChange,
  className = '',
}) => {
  if (totalPages <= 1) return null;

  const getPageNumbers = () => {
    const pages: (number | string)[] = [];
    const maxVisible = 5;

    if (totalPages <= maxVisible) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      pages.push(1);
      let start = Math.max(2, currentPage - 1);
      let end = Math.min(totalPages - 1, currentPage + 1);

      if (currentPage <= 3) {
        start = 2;
        end = 4;
      } else if (currentPage >= totalPages - 2) {
        start = totalPages - 3;
        end = totalPages - 1;
      }

      if (start > 2) pages.push('...');
      for (let i = start; i <= end; i++) pages.push(i);
      if (end < totalPages - 1) pages.push('...');
      pages.push(totalPages);
    }
    return pages;
  };

  return (
    <nav className={`flex items-center justify-center gap-1.5 ${className}`} aria-label="Pagination">
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage <= 1}
        className="p-2 rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:pointer-events-none transition-colors"
        aria-label="Trang trước"
      >
        <ChevronLeft className="w-4 h-4" />
      </button>

      {getPageNumbers().map((page, idx) => {
        if (page === '...') {
          return (
            <span key={`dots-${idx}`} className="px-2 py-1 text-slate-400 text-sm select-none">
              ...
            </span>
          );
        }
        const isCurrent = page === currentPage;
        return (
          <button
            key={`page-${page}`}
            onClick={() => onPageChange(page as number)}
            className={`min-w-[36px] h-9 px-3 text-sm font-medium rounded-lg transition-colors ${
              isCurrent
                ? 'bg-brand-600 text-white font-semibold shadow-sm'
                : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
            }`}
          >
            {page}
          </button>
        );
      })}

      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage >= totalPages}
        className="p-2 rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:pointer-events-none transition-colors"
        aria-label="Trang sau"
      >
        <ChevronRight className="w-4 h-4" />
      </button>
    </nav>
  );
};
