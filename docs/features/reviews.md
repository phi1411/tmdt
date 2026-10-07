# Product Reviews — tùy chọn

## Goal

**DEFERRED theo PHASE02**. Review xác minh khách đã mua không thuộc MVP bắt buộc; không tạo collection/API/UI và không block backend. Phần bên dưới giữ proposal cho tương lai, không contract active.

## Actors

Guest/Customer đọc VISIBLE; Customer đã mua tạo/sửa/xóa review của mình; Admin moderation ẩn/hiện nếu feature bật.

## Functional Requirements

List rating/comment paginated, owner create/update/delete, Admin visibility. Không upload ảnh review/reply/helpful vote trong baseline đề xuất.

## Business Rules

Order owner có productId và COMPLETED+PAID mới review; một review/User/Product (unique). orderId reference kiểm tra eligibility, không làm đơn join giá lịch sử. Rating1..5, comment plain text. Admin không sửa nội dung thành lời khách.

## Permission

Public read visible, Customer owner writes eligible, Admin moderation. Trước feature enable không expose các endpoints dự kiến.

## API

**Đề xuất nếu bật; chưa khóa contract**:

| Method / path | Request | Response data | Error |
| --- | --- | --- | --- |
| GET /products/:id/reviews | page/pageSize | 200 visible reviews | 404 Product;422 |
| POST /products/:id/reviews | {orderId,rating,comment} | 201 review | 403 ineligible;409 duplicate;422 |
| PATCH /reviews/:id | {rating?,comment?} | 200 review | 404 owner;422 |
| DELETE /reviews/:id | Bearer | 204 | 404 owner |
| PATCH /admin/reviews/:id | {status:VISIBLE/HIDDEN} | 200 review | 401/403/404/422 |

## Data

Read/write reviews, read orders ownership/items/state; read products public status. Reference all linked aggregates, không embed unbounded reviews vào Product. Future paths review API/service/repository/schema + `features/reviews/`; dependencies Orders eligibility/Auth/Product, không Payment provider internals.

## Validation

rating integer1..5 no bool; comment đề xuất1..2000; object IDs valid; eligibility and unique index. UI không gửi reviewerName/avatar authoritative; projection public chỉ tên hiển thị đã duyệt, no email/phone/address.

## Edge Cases

Multiple Orders cùng Product vẫn one review; duplicate concurrent submission; Order cancelled/not completed, Product archived, hidden review update không tự unhide. Policy xóa rồi tạo lại và Product archived cần chốt khi enable.

## Security

Ownership/verified purchase server; plain text XSS escaping; rate limits bounded comments. Không lộ Order detail/orderCode/user PII trong list review public.

## UI Behavior

Nếu disabled không có review tab/star rating giả. Nếu enabled, empty state, verified badge server-proven, own form và Admin hide; aggregate rating nếu cần phải bổ sung contract/data design, không tải toàn review để tính client.

## Acceptance Criteria

Chỉ triển khai nếu người dùng sau này yêu cầu bật Review và chốt proposal contract; eligibility/ownership/visibility/unique enforced, UI/API/tests chạy. Disabled được ghi rõ optional, không claim đã có review.

## Testing Checklist

- [ ] Eligibility completed/owner/product, duplicate/concurrent review.
- [ ] Public PII projection/hidden review, owner vs admin actions.
- [ ] Rating/comment/input injection and UI disabled/empty states.
