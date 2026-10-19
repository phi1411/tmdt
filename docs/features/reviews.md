# Đánh giá sản phẩm đã mua

## Goal

IMPLEMENTED19/10/2026: khách đánh giá sản phẩm từ đơn COMPLETED+PAID; công khai VISIBLE và tổng sao đúng. Thay proposal DEFERRED cũ bằng contract tại ADR013. Không có edit/delete/moderation/helpful vote/reply API trong phạm vi này.

## Actors

Guest/Customer/Admin đọc sản phẩm public; chỉ CUSTOMER ACTIVE gửi đánh giá từ đơn của mình.

## Functional Requirements

GET reviews phân trang, lọc rating1..5/hasComment; POST một đánh giá mỗi User/Order/Product. Modal trong Order Detail; Product Detail hiển thị summary/counts/empty/loading/error thật.

## Business Rules

Đơn đúng owner, COMPLETED+PAID, có productId trong items; Product và Category ACTIVE. Unique(userId,orderId,productId). Insert review và cập nhật Product.ratingSummary/version cùng transaction snapshot/majority; aggregate chỉ VISIBLE. Retry transient giới hạn theo shared utility; duplicate409 ALREADY_REVIEWED. Không sửa Order snapshot/totals. Tên public được che; không coi template seed là mua thật.

## Permission

POST Guest401/Admin403, blocked/tokenVersion invalid401; order khác owner404. GET không lộ product/category inactive, orderId/orderCode/userId/email/địa chỉ/password.

## API

Prefix /api/v1; success/error envelope chuẩn.

| Method/path | Request | Response | Errors |
| --- | --- | --- | --- |
| GET /products/:slugOrId/reviews | page/pageSize (1/20,max100), rating?1..5, hasComment?true/false | 200 data{reviews,stats}, meta{page,pageSize,total,totalPages,requestId} | 404visibility,400/422query |
| POST /products/:slugOrId/reviews | Bearer; {orderId,rating,reviewText?,images?} | 201 owner review | 401/403/404,409ORDER_NOT_COMPLETED/PRODUCT_NOT_IN_ORDER/ALREADY_REVIEWED,422,503 |

Public review: id,productId,userSnapshot.displayName,skuSpecSnapshot?,rating,reviewText?,images?,helpfulCount,status,createdAt,updatedAt. POST owner response có thêm orderId/orderCode/userId; GET tuyệt đối không trả các trường này. stats{averageRating,totalReviews,starsBreakdown:{1..5}} toàn Product, meta.total theo filter. Không có fake rating/review count.

## Data

reviews collection + uq_reviews_user_order_product và ix_reviews_product_feed. Product.ratingSummary là cache cập nhật atomic với insert; endpoint stats tính từ VISIBLE reviews. Paths api/products.py; services/review_service.py; repositories/review_repository.py; schemas/review_schema.py; FE components/reviews/ProductReviews.tsx,ReviewModal.tsx. Dependencies Auth, public Product/Category visibility, Order ownership/state/items, shared transaction.

## Validation

Rating JSONinteger1..5 (không bool/float); reviewText<=2000, images<=5 URLs HTTPS (HTTP loopback dev), URL<=2048; ObjectId và body allowlist. Không nhận owner/name/status/counter từ client. Text hiển thị plain escaped.

## Edge Cases

Hai review khác đơn đồng thời không mất count; duplicate cùng đơn409; summary write fail rollback cả review; Product version limit; archived Product404; old invalid seeded reviews PENDING_AUDIT qua migration có backup, không xóa.

## Security

Owner/liveJWT guards; masked public displayName; no order/user identifiers in public DTO. HTTPS imageURL-only, không backend fetch; hidden reviews bị loại; unknown/repeated query reject. Không thêm quyền user/admin mới.

## UI Behavior

Customer COMPLETED order mở modal chọn sao/nhận xét/URLảnh. Lỗi giữ modal; duplicate có thông báo. ProductReviews dùng pagination/filter backend; empty0 và lỗi tải tách biệt; không giả lập like/helpful/chat hay seller metrics.

## Acceptance Criteria

Verified eligibility/visibility/privacy; transaction exact under concurrency/failure; pagination đúng count/filter; UI roundtrip và full backend/build pass. Không claim VNPAY Live.

## Testing Checklist

- Eligibility/ownership/role, bounds và injection.
- Duplicate, concurrent distinct orders, transaction rollback và summary exact.
- Public projection/archived Category/page/filter/empty.
- UI completed COD→review→feed, server pagination và lỗi tải.
