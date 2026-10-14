import React from 'react';
import { Skeleton } from '../ui/Skeleton';

export const ProductCardSkeleton: React.FC = () => {
  return (
    <div className="flex flex-col bg-white rounded-2xl border border-slate-200/80 p-4 space-y-3">
      <Skeleton className="aspect-square w-full rounded-xl" />
      <div className="flex justify-between items-center pt-2">
        <Skeleton className="h-3 w-1/4 rounded" />
        <Skeleton className="h-3 w-1/6 rounded" />
      </div>
      <Skeleton className="h-4 w-5/6 rounded" />
      <Skeleton className="h-4 w-2/3 rounded" />
      <div className="pt-4 flex justify-between items-center border-t border-slate-100">
        <Skeleton className="h-6 w-1/3 rounded" />
        <Skeleton className="h-8 w-16 rounded-xl" />
      </div>
    </div>
  );
};
