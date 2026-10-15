"""Seed authentic, realistic e-commerce products with multi-tier SKU variations,
dynamic attributes, and verified UGC reviews for NovaMart NoSQL project.
"""
from __future__ import annotations
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from bson import ObjectId
from bson.int64 import Int64

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'db'))
from common import connection, normalize

START_TIME = datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc)

REAL_PRODUCTS = [
    # ==================== ĐIỆN TỬ (ELECTRONICS) ====================
    {
        "sku": "IPHONE-16-PRO-MAX",
        "name": "Điện thoại Apple iPhone 16 Pro Max Chính Hãng VN/A",
        "slug": "dien-thoai-apple-iphone-16-pro-max-chinh-hang-vna",
        "productType": "ELECTRONICS",
        "brand": "Apple",
        "description": "iPhone 16 Pro Max với khung viền Titan Cấp 5 bền bỉ, màn hình Super Retina XDR 6.9 inch cùng nút Điều Khiển Camera hoàn toàn mới. Trang bị chip A18 Pro đột phá mang lại thời lượng pin vượt trội.",
        "price": Int64(34990000),
        "stock": 50,
        "images": [
            "https://images.unsplash.com/photo-1695048133142-1a20484d2569?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=800&auto=format&fit=crop&q=80"
        ],
        "attributes": {
            "ram": "8GB",
            "storage": "256GB / 512GB / 1TB",
            "chip": "Apple A18 Pro 6 lõi",
            "screen": "6.9 inch OLED Super Retina XDR 120Hz",
            "battery": "4685 mAh sạc nhanh 30W"
        },
        "tierVariations": [
            {
                "tier": 1,
                "name": "Màu sắc",
                "options": ["Titan Sa Mạc", "Titan Tự Nhiên", "Titan Đen", "Titan Trắng"]
            },
            {
                "tier": 2,
                "name": "Dung lượng",
                "options": ["256GB", "512GB", "1TB"]
            }
        ],
        "skus": [
            # Titan Sa Mạc
            {"skuId": "IP16PM-DES-256", "tierIndex": [0, 0], "price": Int64(34990000), "stock": 10},
            {"skuId": "IP16PM-DES-512", "tierIndex": [0, 1], "price": Int64(40990000), "stock": 5},
            {"skuId": "IP16PM-DES-1TB", "tierIndex": [0, 2], "price": Int64(46990000), "stock": 2},
            # Titan Tự Nhiên
            {"skuId": "IP16PM-NAT-256", "tierIndex": [1, 0], "price": Int64(34990000), "stock": 8},
            {"skuId": "IP16PM-NAT-512", "tierIndex": [1, 1], "price": Int64(40990000), "stock": 4},
            {"skuId": "IP16PM-NAT-1TB", "tierIndex": [1, 2], "price": Int64(46990000), "stock": 3},
            # Titan Đen
            {"skuId": "IP16PM-BLK-256", "tierIndex": [2, 0], "price": Int64(34990000), "stock": 6},
            {"skuId": "IP16PM-BLK-512", "tierIndex": [2, 1], "price": Int64(40990000), "stock": 4},
            {"skuId": "IP16PM-BLK-1TB", "tierIndex": [2, 2], "price": Int64(46990000), "stock": 2},
            # Titan Trắng
            {"skuId": "IP16PM-WHT-256", "tierIndex": [3, 0], "price": Int64(34990000), "stock": 4},
            {"skuId": "IP16PM-WHT-512", "tierIndex": [3, 1], "price": Int64(40990000), "stock": 3},
            {"skuId": "IP16PM-WHT-1TB", "tierIndex": [3, 2], "price": Int64(46990000), "stock": 1}
        ]
    },
    {
        "sku": "SAM-S24-ULTRA",
        "name": "Điện thoại Samsung Galaxy S24 Ultra 5G AI",
        "slug": "dien-thoai-samsung-galaxy-s24-ultra-5g-ai",
        "productType": "ELECTRONICS",
        "brand": "Samsung",
        "description": "Galaxy S24 Ultra mở ra kỷ nguyên quyền năng Galaxy AI hoàn toàn mới với khung titan bền chắc, màn hình phẳng 6.8 inch và bút S-Pen tích hợp.",
        "price": Int64(28990000),
        "stock": 35,
        "images": [
            "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1580910051074-3eb694886505?w=800&auto=format&fit=crop&q=80"
        ],
        "attributes": {
            "ram": "12GB",
            "storage": "256GB / 512GB / 1TB",
            "chip": "Snapdragon 8 Gen 3 for Galaxy",
            "screen": "6.8 inch Dynamic AMOLED 2X 120Hz",
            "battery": "5000 mAh sạc nhanh 45W"
        },
        "tierVariations": [
            {
                "tier": 1,
                "name": "Màu sắc",
                "options": ["Xám Titan", "Đen Titan", "Vàng Titan"]
            },
            {
                "tier": 2,
                "name": "Dung lượng",
                "options": ["256GB", "512GB", "1TB"]
            }
        ],
        "skus": [
            # Xám Titan
            {"skuId": "S24U-GRY-256", "tierIndex": [0, 0], "price": Int64(28990000), "stock": 8},
            {"skuId": "S24U-GRY-512", "tierIndex": [0, 1], "price": Int64(33990000), "stock": 4},
            {"skuId": "S24U-GRY-1TB", "tierIndex": [0, 2], "price": Int64(39990000), "stock": 2},
            # Đen Titan
            {"skuId": "S24U-BLK-256", "tierIndex": [1, 0], "price": Int64(28990000), "stock": 6},
            {"skuId": "S24U-BLK-512", "tierIndex": [1, 1], "price": Int64(33990000), "stock": 3},
            {"skuId": "S24U-BLK-1TB", "tierIndex": [1, 2], "price": Int64(39990000), "stock": 2},
            # Vàng Titan
            {"skuId": "S24U-YEL-256", "tierIndex": [2, 0], "price": Int64(28990000), "stock": 5},
            {"skuId": "S24U-YEL-512", "tierIndex": [2, 1], "price": Int64(33990000), "stock": 3},
            {"skuId": "S24U-YEL-1TB", "tierIndex": [2, 2], "price": Int64(39990000), "stock": 2}
        ]
    },
    {
        "sku": "MACBOOK-PRO-M3",
        "name": "Laptop Apple MacBook Pro 14 inch M3 Pro",
        "slug": "laptop-apple-macbook-pro-14-inch-m3-pro",
        "productType": "ELECTRONICS",
        "brand": "Apple",
        "description": "MacBook Pro 14 inch trang bị chip M3 Pro mang lại hiệu năng phi thường cho các tác vụ chuyên nghiệp nặng. Màn hình Liquid Retina XDR rực rỡ và thời lượng pin lên đến 18 giờ.",
        "price": Int64(49990000),
        "stock": 30,
        "images": [
            "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=800&auto=format&fit=crop&q=80"
        ],
        "attributes": {
            "ram": "18GB Unified Memory / 36GB Unified Memory",
            "storage": "512GB SSD / 1TB SSD",
            "chip": "Apple M3 Pro 11-core CPU",
            "screen": "14.2 inch Liquid Retina XDR 120Hz ProMotion",
            "battery": "70Wh Lithium-polymer"
        },
        "tierVariations": [
            {
                "tier": 1,
                "name": "Màu sắc",
                "options": ["Space Black", "Silver"]
            },
            {
                "tier": 2,
                "name": "Cấu hình RAM & SSD",
                "options": [
                    "18GB RAM / 512GB SSD",
                    "18GB RAM / 1TB SSD",
                    "36GB RAM / 512GB SSD",
                    "36GB RAM / 1TB SSD"
                ]
            }
        ],
        "skus": [
            # Space Black
            {"skuId": "MBP-BLK-18G-512", "tierIndex": [0, 0], "price": Int64(49990000), "stock": 8},
            {"skuId": "MBP-BLK-18G-1TB", "tierIndex": [0, 1], "price": Int64(54990000), "stock": 5},
            {"skuId": "MBP-BLK-36G-512", "tierIndex": [0, 2], "price": Int64(59990000), "stock": 4},
            {"skuId": "MBP-BLK-36G-1TB", "tierIndex": [0, 3], "price": Int64(65990000), "stock": 3},
            # Silver
            {"skuId": "MBP-SLV-18G-512", "tierIndex": [1, 0], "price": Int64(49990000), "stock": 5},
            {"skuId": "MBP-SLV-18G-1TB", "tierIndex": [1, 1], "price": Int64(54990000), "stock": 3},
            {"skuId": "MBP-SLV-36G-512", "tierIndex": [1, 2], "price": Int64(59990000), "stock": 3},
            {"skuId": "MBP-SLV-36G-1TB", "tierIndex": [1, 3], "price": Int64(65990000), "stock": 2}
        ]
    },
    {
        "sku": "SONY-WH1000XM5",
        "name": "Tai nghe chống ồn không dây Sony WH-1000XM5 Hi-Res",
        "slug": "tai-nghe-chong-on-khong-day-sony-wh-1000xm5-hi-res",
        "productType": "ELECTRONICS",
        "brand": "Sony",
        "description": "Tai nghe trùm đầu hàng đầu với công nghệ chống ồn Auto NC Optimizer, 8 micro tích hợp và chất lượng âm thanh chuẩn phòng thu Hi-Res Audio Wireless.",
        "price": Int64(7990000),
        "stock": 25,
        "images": [
            "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800&auto=format&fit=crop&q=80"
        ],
        "attributes": {
            "ram": "N/A",
            "storage": "N/A",
            "chip": "Sony V1 & QN1 HD",
            "screen": "N/A",
            "battery": "30 giờ chống ồn liên tục"
        },
        "tierVariations": [
            {
                "tier": 1,
                "name": "Màu sắc",
                "options": ["Đen", "Bạc Bạch Kim", "Xanh Midnight"]
            }
        ],
        "skus": [
            {"skuId": "WHXM5-BLK", "tierIndex": [0], "price": Int64(7990000), "stock": 12},
            {"skuId": "WHXM5-SLV", "tierIndex": [1], "price": Int64(7990000), "stock": 8},
            {"skuId": "WHXM5-BLU", "tierIndex": [2], "price": Int64(8290000), "stock": 5}
        ]
    },

    # ==================== THỜI TRANG (FASHION) ====================
    {
        "sku": "COOLMATE-POLO",
        "name": "Áo Polo Nam Coolmate Pique Cotton Kháng Khuẩn Co Giãn",
        "slug": "ao-polo-nam-coolmate-pique-cotton-khang-khuan-co-gian",
        "productType": "FASHION",
        "brand": "Coolmate",
        "description": "Áo polo nam công nghệ dệt Pique tổ ong thoáng khí, thấm hút mồ hôi tối ưu, kháng khuẩn tự nhiên, phom dáng Regular Fit tôn dáng hiện đại.",
        "price": Int64(269000),
        "stock": 120,
        "images": [
            "https://images.unsplash.com/photo-1625910513413-5bb2155fbe5b?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1581655353564-df123a1eb820?w=800&auto=format&fit=crop&q=80"
        ],
        "attributes": {
            "sizes": ["M", "L", "XL", "2XL"],
            "colors": ["Đen", "Xanh Navy", "Trắng"],
            "material": "95% Cotton Combed, 5% Spandex",
            "gender": "Nam"
        },
        "tierVariations": [
            {
                "tier": 1,
                "name": "Màu sắc",
                "options": ["Đen", "Xanh Navy", "Trắng"]
            },
            {
                "tier": 2,
                "name": "Kích cỡ",
                "options": ["M", "L", "XL", "2XL"]
            }
        ],
        "skus": [
            # Đen
            {"skuId": "POLO-BLK-M", "tierIndex": [0, 0], "price": Int64(269000), "stock": 15},
            {"skuId": "POLO-BLK-L", "tierIndex": [0, 1], "price": Int64(269000), "stock": 20},
            {"skuId": "POLO-BLK-XL", "tierIndex": [0, 2], "price": Int64(269000), "stock": 15},
            {"skuId": "POLO-BLK-2XL", "tierIndex": [0, 3], "price": Int64(269000), "stock": 10},
            # Xanh Navy
            {"skuId": "POLO-NAVY-M", "tierIndex": [1, 0], "price": Int64(269000), "stock": 12},
            {"skuId": "POLO-NAVY-L", "tierIndex": [1, 1], "price": Int64(269000), "stock": 18},
            {"skuId": "POLO-NAVY-XL", "tierIndex": [1, 2], "price": Int64(269000), "stock": 12},
            {"skuId": "POLO-NAVY-2XL", "tierIndex": [1, 3], "price": Int64(269000), "stock": 8},
            # Trắng
            {"skuId": "POLO-WHT-M", "tierIndex": [2, 0], "price": Int64(269000), "stock": 10},
            {"skuId": "POLO-WHT-L", "tierIndex": [2, 1], "price": Int64(269000), "stock": 15},
            {"skuId": "POLO-WHT-XL", "tierIndex": [2, 2], "price": Int64(269000), "stock": 10},
            {"skuId": "POLO-WHT-2XL", "tierIndex": [2, 3], "price": Int64(269000), "stock": 5}
        ]
    },
    {
        "sku": "LANO-WALLET",
        "name": "Ví Da Nam Dáng Ngang Da Bò Thật Cao Cấp Lano",
        "slug": "vi-da-nam-dang-ngang-da-bo-that-cao-cap-lano",
        "productType": "FASHION",
        "brand": "Lano",
        "description": "Ví da bò sáp nguyên tấm 100%, thiết kế dáng ngang gọn gàng, nhiều ngăn đựng thẻ ATM và tiền mặt tiện dụng. Đường chỉ may thủ công tỉ mỉ chống đứt chỉ.",
        "price": Int64(350000),
        "stock": 40,
        "images": [
            "https://images.unsplash.com/photo-1627123424574-724758594e93?w=800&auto=format&fit=crop&q=80"
        ],
        "attributes": {
            "colors": ["Nâu Bò", "Nâu Cà Phê", "Đen Tuyển"],
            "material": "Da bò sáp thật 100%",
            "gender": "Nam"
        },
        "tierVariations": [
            {
                "tier": 1,
                "name": "Màu sắc",
                "options": ["Nâu Bò", "Nâu Cà Phê", "Đen Tuyển"]
            }
        ],
        "skus": [
            {"skuId": "LANO-BRN", "tierIndex": [0], "price": Int64(350000), "stock": 18},
            {"skuId": "LANO-COF", "tierIndex": [1], "price": Int64(350000), "stock": 12},
            {"skuId": "LANO-BLK", "tierIndex": [2], "price": Int64(350000), "stock": 10}
        ]
    },
    {
        "sku": "RAYBAN-AVIATOR",
        "name": "Kính Mát Unisex Phi Công Ray-Ban Aviator Classic Chống Tia UV",
        "slug": "kinh-mat-unisex-phi-cong-ray-ban-aviator-classic-chong-tia-uv",
        "productType": "FASHION",
        "brand": "Ray-Ban",
        "description": "Biểu tượng thời trang phi công Aviator kinh điển từ năm 1937. Tròng kính thủy tinh khoáng cao cấp chống 100% tia cực tím UVA/UVB.",
        "price": Int64(3850000),
        "stock": 15,
        "images": [
            "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=800&auto=format&fit=crop&q=80"
        ],
        "attributes": {
            "colors": ["Gọng Đen Tròng Đen", "Gọng Vàng Tròng Xanh G-15"],
            "material": "Gọng kim loại mạ titan cao cấp",
            "gender": "Unisex"
        },
        "tierVariations": [
            {
                "tier": 1,
                "name": "Phân loại gọng & tròng",
                "options": ["Gọng Đen Tròng Đen", "Gọng Vàng Tròng Xanh G-15"]
            }
        ],
        "skus": [
            {"skuId": "RB-BLK-BLK", "tierIndex": [0], "price": Int64(3850000), "stock": 8},
            {"skuId": "RB-GLD-GRN", "tierIndex": [1], "price": Int64(4150000), "stock": 7}
        ]
    },

    # ==================== GIA DỤNG (HOME_APPLIANCE) ====================
    {
        "sku": "PHILIPS-AIRFRYER",
        "name": "Nồi Chiên Không Dầu Điện Tử Philips HD9252 Dung Tích 4.1L",
        "slug": "noi-chien-khong-dau-dien-tu-philips-hd9252-dung-tich-4-1l",
        "productType": "HOME_APPLIANCE",
        "brand": "Philips",
        "description": "Công nghệ Rapid Air lốc xoáy độc quyền giảm đến 90% lượng chất béo trong thức ăn. Bảng điều khiển cảm ứng với 7 chương trình nấu cài đặt sẵn tiện dụng.",
        "price": Int64(1890000),
        "stock": 30,
        "images": [
            "https://images.unsplash.com/photo-1556911220-e15b29be8c8f?w=800&auto=format&fit=crop&q=80"
        ],
        "attributes": {
            "power": "1400W",
            "capacity": "4.1 Lít",
            "voltage": "220V",
            "material": "Vỏ nhựa cách nhiệt, lòng nồi chống dính Starfish"
        },
        "tierVariations": [
            {
                "tier": 1,
                "name": "Màu sắc",
                "options": ["Đen Bóng", "Trắng Ngọc"]
            }
        ],
        "skus": [
            {"skuId": "HD9252-BLK", "tierIndex": [0], "price": Int64(1890000), "stock": 20},
            {"skuId": "HD9252-WHT", "tierIndex": [1], "price": Int64(1950000), "stock": 10}
        ]
    },
    {
        "sku": "TEFAL-RICECOOKER",
        "name": "Nồi Cơm Điện Cao Tần Tefal 1.5L Induction RK762168",
        "slug": "noi-com-dien-cao-tan-tefal-1-5l-induction-rk762168",
        "productType": "HOME_APPLIANCE",
        "brand": "Tefal",
        "description": "Công nghệ nấu cảm ứng từ IH gia nhiệt tuần hoàn 360 độ giúp hạt cơm chín đều từ trong ra ngoài. Lòng nồi niêu độc quyền 6 lớp phủ khoáng chất bền bỉ.",
        "price": Int64(1790000),
        "stock": 20,
        "images": [
            "https://images.unsplash.com/photo-1585515320310-259814833e62?w=800&auto=format&fit=crop&q=80"
        ],
        "attributes": {
            "power": "1200W",
            "capacity": "1.5 Lít",
            "voltage": "220V",
            "material": "Hợp kim nhôm phủ chống dính ceramic"
        },
        "tierVariations": [
            {
                "tier": 1,
                "name": "Dung tích & Phiên bản",
                "options": ["1.5L Tiêu Chuẩn", "1.8L Nắp Cảm Ứng"]
            }
        ],
        "skus": [
            {"skuId": "TEFAL-15L", "tierIndex": [0], "price": Int64(1790000), "stock": 12},
            {"skuId": "TEFAL-18L", "tierIndex": [1], "price": Int64(2390000), "stock": 8}
        ]
    },
    {
        "sku": "XIAOMI-AIRPURIFIER",
        "name": "Máy Lọc Không Khí Xiaomi Smart Air Purifier 4 Pro",
        "slug": "may-loc-khong-khi-xiaomi-smart-air-purifier-4-pro",
        "productType": "HOME_APPLIANCE",
        "brand": "Xiaomi",
        "description": "Bộ lọc hiệu suất cao 3 trong 1 loại bỏ 99.97% các hạt bụi mịn PM2.5, phấn hoa và lông thú cưng. Diện tích lọc hiệu quả lên đến 60m2.",
        "price": Int64(4290000),
        "stock": 15,
        "images": [
            "https://images.unsplash.com/photo-1585771724684-38269d6639fd?w=800&auto=format&fit=crop&q=80"
        ],
        "attributes": {
            "power": "50W",
            "capacity": "CADR 500m3/h",
            "voltage": "220V",
            "material": "Nhựa ABS kháng khuẩn"
        },
        "tierVariations": [
            {
                "tier": 1,
                "name": "Màu sắc",
                "options": ["Trắng Tinh Khôi"]
            }
        ],
        "skus": [
            {"skuId": "MIAIR-PRO4-WHT", "tierIndex": [0], "price": Int64(4290000), "stock": 15}
        ]
    }
]

REAL_REVIEWS_TEMPLATES = [
    # MacBook Pro M3
    ("MACBOOK-PRO-M3", 5, "Màu Silver sang chảnh cổ điển, bản 36GB RAM / 512GB SSD chạy máy ảo Docker và render After Effects không bị giật lag chút nào. Đáng đồng tiền bát gạo!", {"Màu sắc": "Silver", "Cấu hình RAM & SSD": "36GB RAM / 512GB SSD"}),
    ("MACBOOK-PRO-M3", 5, "Bản 18GB RAM / 512GB SSD Space Black màu đen nhám hạn chế bám vân tay rất tốt. Bàn phím gõ êm, màn hình XDR 120Hz mượt mà.", {"Màu sắc": "Space Black", "Cấu hình RAM & SSD": "18GB RAM / 512GB SSD"}),
    ("MACBOOK-PRO-M3", 5, "Hàng chính hãng SA/A chuẩn chỉ, bảo hành 12 tháng tại Apple Care. Pin dùng liên tục cả ngày từ sáng đến tối vẫn còn 35%.", {"Màu sắc": "Space Black", "Cấu hình RAM & SSD": "18GB RAM / 1TB SSD"}),
    ("MACBOOK-PRO-M3", 4, "Máy mạnh, đóng gói bọc chống sốc 6 lớp. Trừ 1 sao vì đơn vị giao hàng chậm hơn dự kiến 1 ngày.", {"Màu sắc": "Silver", "Cấu hình RAM & SSD": "18GB RAM / 512GB SSD"}),

    # iPhone 16 Pro Max
    ("IPHONE-16-PRO-MAX", 5, "Máy quá đẹp, màu Titan Sa Mạc bên ngoài sang hơn trong ảnh nhiều. Nút Camera Control bấm nhạy, pin trâu hơn hẳn 15 Pro Max.", {"Màu sắc": "Titan Sa Mạc", "Dung lượng": "256GB"}),
    ("IPHONE-16-PRO-MAX", 5, "Giao hàng đóng gói 5 lớp chống sốc nguyên seal chính hãng. Máy dùng mượt mà, màn hình 120Hz siêu nét.", {"Màu sắc": "Titan Tự Nhiên", "Dung lượng": "512GB"}),
    ("IPHONE-16-PRO-MAX", 5, "Màu Titan Đen nam tính, bản 1TB quay video ProRes 4K 120fps thoải mái không lo đầy bộ nhớ. Rất hài lòng!", {"Màu sắc": "Titan Đen", "Dung lượng": "1TB"}),
    ("IPHONE-16-PRO-MAX", 4, "Camera chụp đêm cực sáng và rõ nét. Điểm trừ là sạc nhanh máy hơi ấm nhẹ.", {"Màu sắc": "Titan Trắng", "Dung lượng": "256GB"}),

    # Galaxy S24 Ultra
    ("SAM-S24-ULTRA", 5, "Tính năng Galaxy AI dịch cuộc gọi trực tiếp và khoanh tròn tìm kiếm cực kỳ hữu ích cho công việc. Bút S-Pen tiện lợi.", {"Màu sắc": "Xám Titan", "Dung lượng": "256GB"}),
    ("SAM-S24-ULTRA", 5, "Màn hình phẳng chống chói Anti-Reflective đỉnh chóp, ra trời nắng gắt nhìn vẫn trong veo. Bản 512GB lưu trữ thoải mái.", {"Màu sắc": "Đen Titan", "Dung lượng": "512GB"}),
    ("SAM-S24-ULTRA", 4, "Chụp zoom 5x và 10x chi tiết rõ nét. Shop giao nhanh trong 24h.", {"Màu sắc": "Vàng Titan", "Dung lượng": "256GB"}),

    # Sony WH-1000XM5
    ("SONY-WH1000XM5", 5, "Chống ồn chủ động ANC tốt nhất từng dùng, ngồi quán cafe bật nhạc lên là như ở không gian riêng. Đệm tai êm không đau vành tai.", {"Màu sắc": "Đen"}),
    ("SONY-WH1000XM5", 5, "Màu Xanh Midnight độc quyền nhìn ngoài rất đẹp và lạ mắt. Pin nghe liên tục cả tuần mới phải cắm sạc.", {"Màu sắc": "Xanh Midnight"}),

    # Áo Polo Coolmate
    ("COOLMATE-POLO", 5, "Vải pique dày dặn co giãn tốt, form Regular Fit che bụng tốt. Mình cao 1m72 nặng 68kg mặc size L vừa như in.", {"Màu sắc": "Đen", "Kích cỡ": "L"}),
    ("COOLMATE-POLO", 5, "Áo đẹp mát, giặt máy không bị nhăn hay xù lông. Đã mua chiếc thứ 3 ở shop.", {"Màu sắc": "Xanh Navy", "Kích cỡ": "M"}),
    ("COOLMATE-POLO", 4, "Form áo đứng dáng, cổ áo cứng cáp mặc đi làm văn phòng hay đi chơi đều lịch sự.", {"Màu sắc": "Trắng", "Kích cỡ": "XL"}),

    # Ví Da Lano
    ("LANO-WALLET", 5, "Da bò sáp thật ngửi thơm mùi da tự nhiên, nhiều ngăn đựng được đủ thẻ căn cước và bằng lái.", {"Màu sắc": "Nâu Bò"}),
    ("LANO-WALLET", 5, "Đường may thủ công chắc chắn, da mềm mịn càng dùng càng bóng đẹp. Hộp đóng gói lịch sự làm quà tặng người yêu rất ưng.", {"Màu sắc": "Nâu Cà Phê"}),

    # Ray-Ban Aviator
    ("RAYBAN-AVIATOR", 5, "Kính chuẩn chính hãng tròng G-15 dịu mắt dưới trời nắng gắt Sài Gòn. Form kính phi công kinh điển không bao giờ lỗi mốt.", {"Phân loại gọng & tròng": "Gọng Vàng Tròng Xanh G-15"}),

    # Nồi chiên Philips
    ("PHILIPS-AIRFRYER", 5, "Nồi chiên làm nóng nhanh, khoai tây và cánh gà chiên giòn tan ráo dầu. Lòng nồi chống dính Starfish dễ vệ sinh.", {"Màu sắc": "Đen Bóng"}),
    ("PHILIPS-AIRFRYER", 5, "Dùng hơn 1 tháng thấy rất tiện cho gia đình 4 người, bảng cảm ứng dễ dùng kể cả bố mẹ lớn tuổi.", {"Màu sắc": "Trắng Ngọc"}),

    # Nồi cơm Tefal
    ("TEFAL-RICECOOKER", 5, "Nấu cơm gạo ST25 bằng chế độ cơm dẻo cực ngon, cơm tơi xốp giữ ấm 24h không bị thiu.", {"Dung tích & Phiên bản": "1.5L Tiêu Chuẩn"}),
    ("TEFAL-RICECOOKER", 5, "Lòng nồi niêu dày dặn giữ nhiệt tốt, nấu cháo hầm gà đều rất nhanh mềm.", {"Dung tích & Phiên bản": "1.8L Nắp Cảm Ứng"}),

    # Xiaomi Air Purifier
    ("XIAOMI-AIRPURIFIER", 5, "Máy chạy êm ái ban đêm hầu như không nghe tiếng, chỉ số không khí hiển thị trực quan qua màn hình OLED.", {"Màu sắc": "Trắng Tinh Khôi"})
]

def run_seed():
    client, db = connection('ecommerce_dev', claim=True)
    try:
        categories = list(db.categories.find({}))
        cat_map = {c['productType']: c['_id'] for c in categories}
        users = list(db.users.find({'role': 'CUSTOMER'}))
        orders = list(db.orders.find({}))

        print(f"Bắt đầu cập nhật toàn bộ {len(REAL_PRODUCTS)} sản phẩm thực tế kèm ma trận SKU đầy đủ...")
        inserted_pids = {}

        for p in REAL_PRODUCTS:
            cid = cat_map.get(p['productType'])
            doc = {
                "schemaVersion": 1,
                "createdAt": START_TIME,
                "updatedAt": START_TIME,
                "sku": p["sku"],
                "name": p["name"],
                "slug": p["slug"],
                "productType": p["productType"],
                "categoryId": cid,
                "brand": p["brand"],
                "description": p["description"],
                "nameNormalized": normalize(p["name"]),
                "brandNormalized": normalize(p["brand"]),
                "price": p["price"],
                "stock": p["stock"],
                "images": p["images"],
                "attributes": p["attributes"],
                "tierVariations": p.get("tierVariations", []),
                "skus": p.get("skus", []),
                "status": "ACTIVE",
                "version": 1,
                "ratingSummary": {
                    "averageRating": 5.0,
                    "totalReviews": 0,
                    "starsBreakdown": {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0}
                }
            }
            res = db.products.update_one(
                {"sku": p["sku"]},
                {"$set": doc},
                upsert=True
            )
            saved = db.products.find_one({"sku": p["sku"]})
            inserted_pids[p["sku"]] = saved["_id"]

        print(f"Đã cập nhật hoàn chỉnh {len(inserted_pids)} sản phẩm.")

        # Xóa các reviews cũ của các sản phẩm này
        db.reviews.delete_many({"productId": {"$in": list(inserted_pids.values())}})

        review_docs = []
        rating_stats = {sku: {"count": 0, "sum": 0, "stars": {"1":0,"2":0,"3":0,"4":0,"5":0}} for sku in inserted_pids}

        for i, (sku, rating, text, spec) in enumerate(REAL_REVIEWS_TEMPLATES):
            pid = inserted_pids[sku]
            u = users[i % len(users)]
            ord_id = orders[i % len(orders)]["_id"] if orders else ObjectId()
            ord_code = orders[i % len(orders)]["orderCode"] if orders else f"ORD-REAL-{i+1:04d}"

            r_doc = {
                "_id": ObjectId(),
                "schemaVersion": 1,
                "createdAt": START_TIME + timedelta(days=i * 2),
                "updatedAt": START_TIME + timedelta(days=i * 2),
                "productId": pid,
                "orderId": ord_id,
                "orderCode": ord_code,
                "userId": u["_id"],
                "userSnapshot": {
                    "displayName": u["name"][0] + "***" + u["name"][-1] if len(u["name"]) > 2 else "h***g",
                    "avatarUrl": ""
                },
                "skuSpecSnapshot": spec,
                "rating": rating,
                "reviewText": text,
                "images": [],
                "helpfulCount": 4 + (i * 3 % 20),
                "status": "VISIBLE"
            }
            review_docs.append(r_doc)
            rating_stats[sku]["count"] += 1
            rating_stats[sku]["sum"] += rating
            rating_stats[sku]["stars"][str(rating)] += 1

        if review_docs:
            db.reviews.insert_many(review_docs)
            print(f"Đã nạp {len(review_docs)} đánh giá thực tế chi tiết.")

        # Cập nhật ratingSummary tương ứng
        for sku, stat in rating_stats.items():
            if stat["count"] > 0:
                avg = round(stat["sum"] / stat["count"], 1)
                db.products.update_one(
                    {"sku": sku},
                    {"$set": {
                        "ratingSummary": {
                            "averageRating": float(avg),
                            "totalReviews": stat["count"],
                            "starsBreakdown": stat["stars"]
                        }
                    }}
                )

        print("Nạp dữ liệu thực tế và ma trận biến thể hoàn tất 100%!")

    finally:
        client.close()

if __name__ == '__main__':
    run_seed()
