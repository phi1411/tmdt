import React, { useEffect, useState } from 'react';
import { Star } from 'lucide-react';
import { catalogApi } from '../../api/catalogApi';
import { ProductReview, RatingSummary } from '../../types/product';
import { Pagination } from '../ui/Pagination';
import { Button } from '../ui/Button';

export const ProductReviews: React.FC<{slug: string}> = ({ slug }) => {
  const [items,setItems]=useState<ProductReview[]>([]);
  const [stats,setStats]=useState<RatingSummary>();
  const [page,setPage]=useState(1);
  const [pages,setPages]=useState(0);
  const [rating,setRating]=useState<number>();
  const [comment,setComment]=useState(false);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState(false);
  const [retry,setRetry]=useState(0);
  useEffect(()=>{
    let active=true;
    setLoading(true); setError(false);
    catalogApi.getProductReviews(slug,{page,pageSize:10,rating,hasComment:comment})
      .then(data=>{if(active){setItems(data.reviews);setStats(data.stats);setPages(data.meta.totalPages || 0);}})
      .catch(()=>{if(active)setError(true);})
      .finally(()=>{if(active)setLoading(false);});
    return ()=>{active=false;};
  },[slug,page,rating,comment,retry]);
  return <section className="space-y-6 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
    <h2 className="border-b border-slate-100 pb-4 text-lg font-bold text-slate-900">Đánh giá sản phẩm</h2>
    <div className="flex flex-wrap items-center gap-4 rounded-2xl border border-amber-100 bg-amber-50/50 p-5">
      <div className="mr-3"><strong className="text-3xl text-rose-600">{stats?.totalReviews ? stats.averageRating.toFixed(1) : 'Chưa có'}</strong>
        <p className="mt-1 text-xs text-slate-500">{stats?.totalReviews ?? 0} đánh giá từ đơn hàng hoàn tất</p></div>
      <Button type="button" variant={rating===undefined&&!comment?'primary':'outline'} onClick={()=>{setRating(undefined);setComment(false);setPage(1);}}>Tất cả</Button>
      {[5,4,3,2,1].map(value=><Button key={value} type="button" variant={rating===value?'primary':'outline'} onClick={()=>{setRating(value);setPage(1);}}>{value} sao ({stats?.starsBreakdown?.[String(value)] ?? 0})</Button>)}
      <Button type="button" variant={comment?'primary':'outline'} onClick={()=>{setComment(!comment);setPage(1);}}>Có nhận xét</Button>
    </div>
    {loading ? <p role="status" className="text-sm text-slate-500">Đang tải đánh giá...</p> : error ?
      <div role="alert"><p className="mb-3 text-sm text-rose-600">Chưa tải được đánh giá.</p><Button type="button" variant="outline" onClick={()=>setRetry(x=>x+1)}>Thử lại</Button></div> :
      !items.length ? <p className="py-8 text-center text-sm text-slate-500">Chưa có đánh giá phù hợp.</p> :
      <div className="space-y-6">{items.map(item=><article key={item.id} className="space-y-3 border-b border-slate-100 pb-6">
        <div className="flex items-center justify-between gap-4"><strong className="text-sm text-slate-800">{item.userSnapshot?.displayName || 'Người mua'}</strong>
          <time className="text-xs text-slate-400">{new Date(item.createdAt).toLocaleDateString('vi-VN')}</time></div>
        <div className="flex gap-1" aria-label={`${item.rating} sao`}>{[1,2,3,4,5].map(value=><Star key={value} className={`h-4 w-4 ${value<=item.rating?'fill-amber-400 text-amber-400':'text-slate-200'}`} />)}</div>
        {item.skuSpecSnapshot && <p className="text-xs text-slate-500">{Object.entries(item.skuSpecSnapshot).filter(([key])=>key!=='skuId').map(([key,value])=>`${key}: ${value}`).join(' · ')}</p>}
        <p className="whitespace-pre-wrap text-sm text-slate-700">{item.reviewText}</p>
        {!!item.images?.length && <div className="flex flex-wrap gap-2">{item.images.map((src,index)=><img key={index} src={src} alt={`Ảnh đánh giá ${index+1}`} loading="lazy" className="h-20 w-20 rounded-lg object-cover" />)}</div>}
      </article>)}</div>}
    {!loading&&!error&&pages>1&&<Pagination currentPage={page} totalPages={pages} onPageChange={setPage} />}
  </section>;
};
