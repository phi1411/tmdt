import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { adminProductsApi } from '../api/adminProductsApi';
import { adminCategoriesApi } from '../api/adminCategoriesApi';
import { ProductStatus } from '../types/adminProduct';
import { AdminCategory } from '../types/adminCategory';
import { ProductType } from '../types/product';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Skeleton } from '../components/ui/Skeleton';
import { useToast } from '../contexts/ToastContext';
import {
  ChevronLeft,
  Save,
  ShoppingBag,
  Layers,
} from 'lucide-react';

export const AdminProductFormPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const navigate = useNavigate();
  const { success: toastSuccess, error: toastError, warning: toastWarning } = useToast();

  const [categories, setCategories] = useState<AdminCategory[]>([]);
  const [loadingInitial, setLoadingInitial] = useState<boolean>(isEdit);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [currentVersion, setCurrentVersion] = useState<number>(1);
  const [originalAttributes, setOriginalAttributes] = useState<Record<string, any>>({});

  // Common Form States
  const [sku, setSku] = useState<string>('');
  const [name, setName] = useState<string>('');
  const [slug, setSlug] = useState<string>('');
  const [categoryId, setCategoryId] = useState<string>('');
  const [productType, setProductType] = useState<ProductType>('ELECTRONICS');
  const [brand, setBrand] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [price, setPrice] = useState<number>(0);
  const [stock, setStock] = useState<number>(0);
  const [imagesText, setImagesText] = useState<string>('');
  const [status, setStatus] = useState<ProductStatus>('ACTIVE');

  // Polymorphic: ELECTRONICS
  const [warrantyMonths, setWarrantyMonths] = useState<number>(12);
  const [elecRam, setElecRam] = useState<string>('');
  const [elecStorage, setElecStorage] = useState<string>('');
  const [elecChip, setElecChip] = useState<string>('');
  const [elecScreen, setElecScreen] = useState<string>('');

  // Polymorphic: FASHION
  const [fashionGender, setFashionGender] = useState<'MEN' | 'WOMEN' | 'UNISEX'>('UNISEX');
  const [fashionMaterial, setFashionMaterial] = useState<string>('');
  const [fashionSizes, setFashionSizes] = useState<string>('S, M, L, XL');
  const [fashionColors, setFashionColors] = useState<string>('Đen, Trắng');

  // Polymorphic: HOME_APPLIANCE
  const [homePower, setHomePower] = useState<string>('');
  const [homeCapacity, setHomeCapacity] = useState<string>('');
  const [homeVoltage, setHomeVoltage] = useState<string>('220V');
  const [homeMaterial, setHomeMaterial] = useState<string>('');

  // Load Categories & Product (if Edit)
  useEffect(() => {
    const initData = async () => {
      try {
        const catRes = await adminCategoriesApi.getList({ pageSize: 100 });
        setCategories(catRes.categories);

        if (isEdit && id) {
          const prod = await adminProductsApi.getById(id);
          setCurrentVersion(prod.version);
          setSku(prod.sku);
          setName(prod.name);
          setSlug(prod.slug);
          setCategoryId(prod.categoryId);
          setProductType(prod.productType);
          setBrand(prod.brand);
          setDescription(prod.description || '');
          setPrice(prod.price);
          setStock(prod.stock);
          setImagesText((prod.images || []).join('\n'));
          setStatus(prod.status);

          // Populate Polymorphic Attributes
          const attrs = prod.attributes || {};
          setOriginalAttributes(attrs);
          if (prod.productType === 'ELECTRONICS') {
            setWarrantyMonths(attrs.warrantyMonths || 12);
            setElecRam(attrs.ram || '');
            setElecStorage(attrs.storage || '');
            setElecChip(attrs.chip || '');
            setElecScreen(attrs.screen || '');
          } else if (prod.productType === 'FASHION') {
            setFashionGender(attrs.gender || 'UNISEX');
            setFashionMaterial(attrs.material || '');
            setFashionSizes(Array.isArray(attrs.sizes) ? attrs.sizes.join(', ') : '');
            setFashionColors(Array.isArray(attrs.colors) ? attrs.colors.join(', ') : '');
          } else if (prod.productType === 'HOME_APPLIANCE') {
            setHomePower(attrs.power || '');
            setHomeCapacity(attrs.capacity || '');
            setHomeVoltage(attrs.voltage || '220V');
            setHomeMaterial(attrs.material || '');
          }
        }
      } catch (err: any) {
        toastError(err?.message || 'Không thể tải dữ liệu khởi tạo.');
      } finally {
        setLoadingInitial(false);
      }
    };

    initData();
  }, [id, isEdit, toastError]);

  // Auto-slug generator on create
  const handleNameChange = (val: string) => {
    setName(val);
    if (!isEdit && !slug) {
      const generated = val
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/[đĐ]/g, 'd')
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '');
      setSlug(generated);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name.trim() || !slug.trim() || !categoryId) {
      toastWarning('Vui lòng điền đầy đủ các thông tin bắt buộc (*)');
      return;
    }

    if (!isEdit && !sku.trim()) {
      toastWarning('Mã SKU là bắt buộc đối với sản phẩm mới.');
      return;
    }

    // Build Polymorphic Attributes
    const attributes: Record<string, any> = isEdit ? { ...originalAttributes } : {};
    // A full attributes replacement must retain fields this form does not edit.
    const editableKeys = productType === 'ELECTRONICS'
      ? ['warrantyMonths', 'ram', 'storage', 'chip', 'screen']
      : productType === 'FASHION'
      ? ['gender', 'material', 'sizes', 'colors']
      : ['power', 'capacity', 'voltage', 'material'];
    for (const key of editableKeys) delete attributes[key];
    if (productType === 'ELECTRONICS') {
      attributes.warrantyMonths = Number(warrantyMonths) || 12;
      if (elecRam.trim()) attributes.ram = elecRam.trim();
      if (elecStorage.trim()) attributes.storage = elecStorage.trim();
      if (elecChip.trim()) attributes.chip = elecChip.trim();
      if (elecScreen.trim()) attributes.screen = elecScreen.trim();
    } else if (productType === 'FASHION') {
      attributes.gender = fashionGender;
      if (fashionMaterial.trim()) attributes.material = fashionMaterial.trim();
      attributes.sizes = fashionSizes
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);
      attributes.colors = fashionColors
        .split(',')
        .map((c) => c.trim())
        .filter(Boolean);
    } else if (productType === 'HOME_APPLIANCE') {
      if (homePower.trim()) attributes.power = homePower.trim();
      if (homeCapacity.trim()) attributes.capacity = homeCapacity.trim();
      if (homeVoltage.trim()) attributes.voltage = homeVoltage.trim();
      if (homeMaterial.trim()) attributes.material = homeMaterial.trim();
    }

    const images = imagesText
      .split('\n')
      .map((url) => url.trim())
      .filter(Boolean);

    setSubmitting(true);
    try {
      if (isEdit && id) {
        await adminProductsApi.update(id, {
          name: name.trim(),
          slug: slug.trim(),
          categoryId,
          productType,
          brand: brand.trim(),
          description: description.trim(),
          price: Math.max(0, Math.floor(Number(price))),
          stock: Math.max(0, Math.floor(Number(stock))),
          images,
          attributes,
          status,
          expectedVersion: currentVersion,
        });

        toastSuccess(`Đã cập nhật sản phẩm "${name}" thành công!`);
        navigate('/admin/products');
      } else {
        await adminProductsApi.create({
          sku: sku.trim().toUpperCase(),
          name: name.trim(),
          slug: slug.trim(),
          categoryId,
          productType,
          brand: brand.trim(),
          description: description.trim(),
          price: Math.max(0, Math.floor(Number(price))),
          stock: Math.max(0, Math.floor(Number(stock))),
          images,
          attributes,
          status,
        });

        toastSuccess(`Đã tạo sản phẩm mới "${name}" thành công!`);
        navigate('/admin/products');
      }
    } catch (err: any) {
      if (err?.code === 'CONFLICT' || err?.status === 409) {
        toastWarning('Mã SKU hoặc Slug đã tồn tại, hoặc phiên bản dữ liệu đã thay đổi.');
      } else {
        toastError(err?.message || 'Không thể lưu sản phẩm.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const filteredCategories = categories.filter((c) => c.productType === productType);

  if (loadingInitial) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-8 space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-200">
        <Link
          to="/admin/products"
          className="inline-flex items-center gap-1.5 text-xs sm:text-sm font-semibold text-slate-600 hover:text-brand-600 transition-colors"
        >
          <ChevronLeft className="w-4 h-4" />
          <span>Quay lại danh sách sản phẩm</span>
        </Link>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Section 1: Basic Information */}
        <div className="bg-white p-6 sm:p-8 rounded-2xl border border-slate-200/80 shadow-xs space-y-6">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <ShoppingBag className="w-5 h-5 text-brand-600" />
            <h2 className="text-base font-bold text-slate-900">1. Thông Tin Cơ Bản Sản Phẩm</h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Mã SKU (Duy nhất)"
              required
              disabled={isEdit}
              value={sku}
              onChange={(e) => setSku(e.target.value.toUpperCase())}
              placeholder="VD: ELEC-SAM-S24"
              helperText={isEdit ? 'Mã SKU cố định không được chỉnh sửa sau khi tạo.' : 'Dùng làm mã định danh quản lý kho.'}
            />

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Loại Sản Phẩm (Product Type) <span className="text-rose-500">*</span>
              </label>
              <select
                disabled={isEdit}
                value={productType}
                onChange={(e) => {
                  setProductType(e.target.value as ProductType);
                  setCategoryId('');
                }}
                className="w-full text-xs bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-slate-800 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-100 disabled:opacity-60"
              >
                <option value="ELECTRONICS">ELECTRONICS (Điện tử - Công nghệ)</option>
                <option value="FASHION">FASHION (Thời trang - Phụ kiện)</option>
                <option value="HOME_APPLIANCE">HOME_APPLIANCE (Đồ gia dụng - Đời sống)</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Tên sản phẩm"
              required
              value={name}
              onChange={(e) => handleNameChange(e.target.value)}
              placeholder="VD: Điện thoại Samsung Galaxy S24 Ultra 256GB"
            />

            <Input
              label="Đường dẫn tĩnh (Slug)"
              required
              value={slug}
              onChange={(e) => setSlug(e.target.value.toLowerCase())}
              placeholder="VD: dien-thoai-samsung-galaxy-s24-ultra"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Danh Mục (Category) <span className="text-rose-500">*</span>
              </label>
              <select
                value={categoryId}
                onChange={(e) => setCategoryId(e.target.value)}
                required
                className="w-full text-xs bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-slate-800 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-100"
              >
                <option value="">-- Chọn danh mục phù hợp --</option>
                {filteredCategories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>

            <Input
              label="Thương hiệu (Brand)"
              value={brand}
              onChange={(e) => setBrand(e.target.value)}
              placeholder="VD: Samsung, Apple, Nike..."
            />

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Trạng thái hiển thị
              </label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value as ProductStatus)}
                className="w-full text-xs bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-slate-800 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-100"
              >
                <option value="ACTIVE">ACTIVE (Hiển thị bán)</option>
                <option value="INACTIVE">INACTIVE (Tạm ẩn)</option>
                <option value="ARCHIVED">ARCHIVED (Lưu trữ)</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Giá bán (VND)"
              type="number"
              required
              min={0}
              value={price}
              onChange={(e) => setPrice(Number(e.target.value))}
              helperText="Số nguyên VND lưu trữ dưới dạng BSON Int64."
            />

            <Input
              label="Số lượng tồn kho"
              type="number"
              required
              min={0}
              value={stock}
              onChange={(e) => setStock(Number(e.target.value))}
              helperText="Kiểm soát trừ kho đồng thời bằng Conditional Update & OCC."
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Danh sách liên kết hình ảnh (Một đường dẫn mỗi dòng)
            </label>
            <textarea
              rows={3}
              value={imagesText}
              onChange={(e) => setImagesText(e.target.value)}
              placeholder="https://images.unsplash.com/...&#10;https://images.unsplash.com/..."
              className="w-full text-xs font-mono bg-slate-50 border border-slate-200 rounded-xl p-3 text-slate-800 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-100"
            />
            <p className="text-[11px] text-slate-400 mt-1">
              Không bắt buộc. Tối đa 8 liên kết HTTPS; HTTP chỉ dùng cho localhost. Để trống nếu chưa có ảnh.
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Mô tả chi tiết sản phẩm
            </label>
            <textarea
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Nhập thông tin giới thiệu, xuất xứ, tính năng nổi bật..."
              className="w-full text-xs bg-slate-50 border border-slate-200 rounded-xl p-3 text-slate-800 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-100"
            />
          </div>
        </div>

        {/* Section 2: Polymorphic Attributes Form */}
        <div className="bg-white p-6 sm:p-8 rounded-2xl border border-slate-200/80 shadow-xs space-y-6">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <Layers className="w-5 h-5 text-indigo-600" />
              <h2 className="text-base font-bold text-slate-900">
                2. Thuộc Tính Đa Hình Ngành Hàng ({productType})
              </h2>
            </div>
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200/60">
              Polymorphic Schema
            </span>
          </div>

          {/* Form branch: ELECTRONICS */}
          {productType === 'ELECTRONICS' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Thời hạn bảo hành (Tháng)"
                type="number"
                min={0}
                value={warrantyMonths}
                onChange={(e) => setWarrantyMonths(Number(e.target.value))}
                placeholder="VD: 12 hoặc 24"
              />
              <Input
                label="Dung lượng RAM"
                value={elecRam}
                onChange={(e) => setElecRam(e.target.value)}
                placeholder="VD: 8GB, 16GB LPDDR5"
              />
              <Input
                label="Bộ nhớ trong (Storage)"
                value={elecStorage}
                onChange={(e) => setElecStorage(e.target.value)}
                placeholder="VD: 256GB, 512GB UFS 4.0"
              />
              <Input
                label="Vi xử lý (Chipset)"
                value={elecChip}
                onChange={(e) => setElecChip(e.target.value)}
                placeholder="VD: Apple A17 Pro, Snapdragon 8 Gen 3"
              />
              <div className="sm:col-span-2">
                <Input
                  label="Màn hình hiển thị"
                  value={elecScreen}
                  onChange={(e) => setElecScreen(e.target.value)}
                  placeholder="VD: 6.7 inch OLED Super Retina XDR 120Hz"
                />
              </div>
            </div>
          )}

          {/* Form branch: FASHION */}
          {productType === 'FASHION' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Phân loại giới tính (Gender)
                </label>
                <select
                  value={fashionGender}
                  onChange={(e) => setFashionGender(e.target.value as any)}
                  className="w-full text-xs bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-slate-800 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-100"
                >
                  <option value="UNISEX">UNISEX (Nam & Nữ)</option>
                  <option value="MEN">MEN (Dành cho Nam)</option>
                  <option value="WOMEN">WOMEN (Dành cho Nữ)</option>
                </select>
              </div>

              <Input
                label="Chất liệu vải"
                value={fashionMaterial}
                onChange={(e) => setFashionMaterial(e.target.value)}
                placeholder="VD: 100% Cotton Organic, Vải Dạ Cao Cấp"
              />

              <Input
                label="Các kích cỡ (Phân cách bằng dấu phẩy)"
                value={fashionSizes}
                onChange={(e) => setFashionSizes(e.target.value)}
                placeholder="VD: S, M, L, XL, XXL hoặc 39, 40, 41, 42"
                helperText="Khách hàng sẽ chọn kích cỡ này khi thêm vào giỏ hàng."
              />

              <Input
                label="Các màu sắc (Phân cách bằng dấu phẩy)"
                value={fashionColors}
                onChange={(e) => setFashionColors(e.target.value)}
                placeholder="VD: Đen, Trắng, Xanh Navy, Đỏ Rượu"
                helperText="Khách hàng sẽ chọn màu sắc này khi đặt hàng."
              />
            </div>
          )}

          {/* Form branch: HOME_APPLIANCE */}
          {productType === 'HOME_APPLIANCE' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Công suất tiêu thụ"
                value={homePower}
                onChange={(e) => setHomePower(e.target.value)}
                placeholder="VD: 1800W, 2200W"
              />

              <Input
                label="Dung tích thiết bị"
                value={homeCapacity}
                onChange={(e) => setHomeCapacity(e.target.value)}
                placeholder="VD: 5.5 Lít, 350 Lít, 10 Kg"
              />

              <Input
                label="Điện áp định mức"
                value={homeVoltage}
                onChange={(e) => setHomeVoltage(e.target.value)}
                placeholder="VD: 220V / 50Hz"
              />

              <Input
                label="Chất liệu vỏ / lòng nồi"
                value={homeMaterial}
                onChange={(e) => setHomeMaterial(e.target.value)}
                placeholder="VD: Inox 304 không gỉ, Nhựa ABS chịu nhiệt"
              />
            </div>
          )}
        </div>

        {/* Submit Actions */}
        <div className="flex items-center justify-end gap-3 pt-4">
          <Link to="/admin/products">
            <Button variant="outline" size="md">
              Hủy bỏ
            </Button>
          </Link>
          <Button
            type="submit"
            variant="primary"
            size="md"
            loading={submitting}
            icon={<Save className="w-4 h-4" />}
          >
            {isEdit ? 'Lưu thay đổi sản phẩm' : 'Tạo sản phẩm mới'}
          </Button>
        </div>
      </form>
    </div>
  );
};
