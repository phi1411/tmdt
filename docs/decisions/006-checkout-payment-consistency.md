# ADR-006 — Checkout, giữ kho và thanh toán

## Status

LOCKED DESIGN v1 — PHASE02,07/10/2026. Ship/quote/hold/expiry và manual-review policy đã khóa tại foundation-decisions; credentials/IPN runtime deferred tới phasePayment, chưa chạy sandbox.

## Context

Add Cart không thể đảm bảo kho còn khi checkout. Retry/mất mạng/callback trùng có thể tạo đơn/trừ kho/thu tiền nhiều lần. Transaction không bao phủ server VNPAY.

## Decision

Cart không reserve. Server quoteToken ký giá/fee/selection/version để Customer xác nhận đúng giá. Checkout revalidate, decrement conditional stock theo tổng qty/Product, snapshot Order, clear items và tăng Cart.version (giữ document) và create attempt trong transaction. Idempotency-Key scoped User/hash intent chống double-order. UI dựng payment URL sau commit, không gọi provider trong transaction callback retryable.

Stock Product là available quantity. CANCELLED/EXPIRED trả một lần bằng state predicate/stockReleasedAt + transaction. Không TTL-delete chứng từ. VNPAY callbacks verify trước mutation và serialize với cancel/expiry bằng Order version/state guard; ReturnUrl chỉ polling. Late success sau terminal→REVIEW_REQUIRED, không tự hồi sinh Order. COD PAID chỉ lúc COMPLETED. [Transaction MongoDB](https://www.mongodb.com/docs/manual/core/transactions/), [VNPAY IPN/ReturnUrl](https://sandbox.vnpayment.vn/apis/docs/thanh-toan-pay/pay.html).

## Alternatives and trade-offs

Reserve khi add Cart: giữ kho lâu, cần expiry mọi Cart; không chọn. Decrement không transaction rồi bù từng bước: topology dễ nhưng partial crash làm lệch đơn/kho; không chọn baseline. Ghi paid từ browser return: không đáng tin; loại. Một payment field không attempt history: đơn giản nhưng retry/callback nhiều txn khó dedup; chọn attempt collection.

## Consequences and verification

Yêu cầu replica set, bounded retries, invariant tests và expiry worker explicit. Late payment cần manual reconciliation ngoài ứng dụng; success deadline guard theo BR-PAYMENT, refund automation DEFERRED. Request/callback metadata canonical ở database-schema/validators, pending attempt partial unique theo Order. Double-click/network replay/success callback lặp không tạo doanh thu/tồn kho lần hai. Fault injection sau decrement item thứ hai phải rollback; race expiry/callback/cancel phải có một stock outcome.
