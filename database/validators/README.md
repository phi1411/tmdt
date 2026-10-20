# MongoDB validators — schema v1 đã khóa

Mỗi `<collection>.json` là **nội dung validator** chứa `$jsonSchema`, không phải script tạo collection. Sáu collection MVP: users, categories, products, carts, orders, payment_attempts. Phase02 tạo artifact; phase03 dùng [init_db.py](../../scripts/db/init_db.py) apply trực tiếp với `validationLevel: strict`, `validationAction: error`. [Live verifier](../../scripts/validation/verify_database.py) đối chiếu validator thực và insert các probe accepted/rejected trên MongoDB; không chép lại schema trong backend/docs.

MongoDB target local Community8.0 replica set `rs0`. Dùng subset JSON Schema draft4 với `bsonType`; không `$ref`, `definitions`, `default`, `format` hoặc `if/then`. [Keyword MongoDB hỗ trợ](https://www.mongodb.com/docs/v8.0/reference/operator/query/jsonschema/).

Root và embedded cấu trúc nghiệp vụ có additionalProperties=false; `products.attributes`/`orders.items.attributesSnapshot` cho phép key động an toàn và scalar/array/object bounded3 mức. Nhánh productType chỉ type-check known fields, không yêu cầu mọi thiết bị có cùng bộ attributes. Quyền linh hoạt nằm trong attributes, không root fields tùy tiện.

Các default được service/seed ghi explicit (schema không tự thêm): schemaVersion1, version1 (Cart persisted>=1), tokenVersion0, discount long0, paymentReviewRequired false, User addresses=[]/defaultAddressId=null/phone="" khi signup chưa có phone, Category.description="" khi API bỏ qua. Product derived fields tính trên server. Optional timestamps được **omit**, không ghi null trừ defaultAddressId.

DB validator enforce shape/types/enums/bounds và một số status/time-field presence. Service vẫn chịu trách nhiệm reference/ownership, normalization, selectedAttributes membership, arithmetic, timestamp ordering, legal transitions, immutable snapshots và once-only stock/payment side effects. Unique constraints nằm ở candidate-indexes.json; không được tuyên bố JSON Schema tự bảo đảm chúng.

Kiểm tra tĩnh: `python scripts/validation/validate_design.py` (cần jsonschema trong môi trường kiểm tra). Script chỉ đọc artifacts/đánh giá mẫu, không kết nối MongoDB. Kết quả không thay thế việc MongoDB8.0 thật chấp nhận validator ở phase foundation runtime.


ADR015: Cart.couponCode optional; Order.discount long0..50000 thay enum0, coupon snapshot và items.discountAllocated optional cho legacy. Đơn có coupon bắt buộc phân bổ và kiểm tra tiền/điều kiện bằng $expr. `scripts/db/migrate_cart_coupons.py --database ecommerce_test --apply` áp dụng cộng thêm, không sửa document/index; dừng runtime writer khi migration để fingerprint có ý nghĩa. Bản cũ backup riêng trong .local, không commit thông tin riêng.
