import React, { useState } from 'react';
import { SkuItem, TierVariation } from '../../types/product';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';

interface Props {
  tiers: TierVariation[];
  skus: SkuItem[];
  basePrice: number;
  onChange: (tiers: TierVariation[], skus: SkuItem[]) => void;
  onPendingChange: (pending: boolean) => void;
}

export const ProductVariantsEditor: React.FC<Props> = ({ tiers, skus, basePrice, onChange, onPendingChange }) => {
  const [draft, setDraft] = useState(tiers.map(tier => ({ name: tier.name, values: tier.options.join(', ') })));
  const [error, setError] = useState('');
  const changeDraft = (next: typeof draft) => { setDraft(next); onPendingChange(true); setError(''); };
  const rebuild = () => {
    const next = draft.map((tier, index) => ({ tier: index+1, name: tier.name.trim(), options: tier.values.split(',').map(x=>x.trim()).filter(Boolean) }));
    if (next.some(tier=>!tier.name || tier.name==='skuId' || /[.$]/.test(tier.name) || !tier.options.length || new Set(tier.options).size!==tier.options.length || tier.options.length>50) || new Set(next.map(x=>x.name)).size!==next.length) {
      setError('Điền tên phân loại và các lựa chọn không trùng, cách nhau bằng dấu phẩy.'); return;
    }
    const combinations = next.reduce<number[][]>((rows,tier)=>rows.flatMap(row=>tier.options.map((_,index)=>[...row,index])),[[]]);
    if (combinations.length>100) { setError('Tối đa 100 tổ hợp. Hãy giảm số lựa chọn.'); return; }
    const identity = (list: TierVariation[], indexes: number[]) => JSON.stringify(list.map((tier,index)=>[tier.name,tier.options[indexes[index]]]));
    const existing = new Map(skus.map(sku=>[identity(tiers,sku.tierIndex || []),sku]));
    const models = next.length ? combinations.map(indexes=>({
      ...(existing.get(identity(next,indexes)) || { skuId:'VAR-'+crypto.randomUUID().slice(0,12).toUpperCase(),price:Math.max(1,basePrice),stock:0 }),
      tierIndex:indexes,
    })) : [];
    onChange(next,models); onPendingChange(false); setError('');
  };
  const updateSku = (index: number, key: 'price' | 'stock', value: number) => onChange(tiers,skus.map((sku,i)=>i===index?{...sku,[key]:value}:sku));
  return <section className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 sm:p-8">
    <h2 className="font-bold text-slate-900">Phân loại và tồn kho</h2>
    <p className="text-sm text-slate-500">Ví dụ: Kích cỡ S, M, L, XL và Màu sắc Đen, Trắng. Giá và kho tổng được tính từ bảng bên dưới.</p>
    {draft.map((tier,index)=><div key={index} className="grid gap-3 sm:grid-cols-[1fr_2fr_auto]">
      <Input label={`Tên phân loại ${index+1}`} value={tier.name} onChange={e=>changeDraft(draft.map((x,i)=>i===index?{...x,name:e.target.value}:x))} maxLength={100} />
      <Input label={`Các lựa chọn ${index+1}`} value={tier.values} onChange={e=>changeDraft(draft.map((x,i)=>i===index?{...x,values:e.target.value}:x))} placeholder="S, M, L, XL" />
      <Button type="button" variant="ghost" className="self-end" onClick={()=>changeDraft(draft.filter((_,i)=>i!==index))}>Bỏ nhóm {index+1}</Button>
    </div>)}
    <div className="flex flex-wrap gap-3">
      <Button type="button" variant="outline" disabled={draft.length>=4} onClick={()=>changeDraft([...draft,{name:'',values:''}])}>Thêm nhóm phân loại</Button>
      <Button type="button" onClick={rebuild}>Cập nhật bảng phân loại</Button>
    </div>
    {error && <p role="alert" className="text-sm text-rose-600">{error}</p>}
    {skus.length>0 && <div className="overflow-x-auto">
      <table className="w-full min-w-[450px] text-left text-sm"><thead><tr><th className="p-2">Phân loại</th><th className="p-2">Giá (đ)</th><th className="p-2">Tồn kho</th></tr></thead>
        <tbody>{skus.map((sku,index)=>{
          const label=tiers.map((tier,i)=>tier.options[sku.tierIndex?.[i] ?? 0]).join(' / ');
          return <tr key={sku.skuId} className="border-t border-slate-100"><td className="p-2"><div>{label}</div><small className="text-slate-400">{sku.skuId}</small></td>
            <td className="p-2"><input aria-label={`Giá ${label}`} type="number" min={1} max={1000000000} step={1} required value={sku.price} onChange={e=>updateSku(index,'price',Number(e.target.value))} className="w-36 rounded-lg border border-slate-200 p-2" /></td>
            <td className="p-2"><input aria-label={`Kho ${label}`} type="number" min={0} max={2147483647} step={1} required value={sku.stock} onChange={e=>updateSku(index,'stock',Number(e.target.value))} className="w-24 rounded-lg border border-slate-200 p-2" /></td>
          </tr>;
        })}</tbody>
      </table>
    </div>}
    {!tiers.length && <p className="text-sm text-slate-500">Không có bảng phân loại: dùng giá và kho chung của sản phẩm.</p>}
  </section>;
};
