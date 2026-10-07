# ADR-008 — Search tiếng Việt local, đơn giản

## Status

LOCKED DESIGN v1 — PHASE02,07/10/2026; resolves OQ-04. Không phụ thuộc Atlas Search hoặc language stemming/text-index ranking.

## Decision

Product lưu server-derived `nameNormalized` và `brandNormalized`. Canonical normalize: Unicode NFKD →casefold→đ/Đ thành d→loại combining marks→collapse whitespace/trim. Giữ ký tự punctuation/Unicode còn lại để không tự mất nghĩa; client không ghi derived fields. Ví dụ `Điện thoại Demo A`→`dien thoai demo a`, `Áo thun`→`ao thun`. Query q normalize y hệt, split theo spaces, mỗi token dùng **escaped literal substring** trong nameNormalized và AND giữa tokens. Không q description/brand để tránh search scope trôi; brand là normalized exact filter riêng.

CategoryId/productType/status equality, price range inclusive, brandNormalized equality, optional attrs size/color/ram/capacity exact match. Fashion size/color map attributes.sizes/colors membership; ram/capacity đúng key nhóm, không normalize giá trị kỹ thuật tùy tiện. q<=100 chars,max8 tokens,page<=100 size. Public chỉ ACTIVE + ACTIVE Category; Admin có status filter được allowlist. Sort price_asc (price/_id asc), price_desc (price/_id desc), latest(createdAt/_id desc); không relevance/fuzzy/autocomplete.

## Trade-offs

Substring đơn giản hỗ trợ có dấu/không dấu và tên nhiều từ trong data nhỏ, nhưng không anchored nên không hứa B-tree name index accelerate. Không tạo index nameNormalized “cho đẹp”; candidate compound status/category/price cho workloadfilter giá riêng. [MongoDB regex index behavior](https://www.mongodb.com/docs/v8.0/reference/operator/query/regex/). Full-text/token prefix ranking có thể thêm sau nếu nhu cầu rõ/benchmark.

## Consequences / validation

Create/update name/brand tính lại normalized fields cùng write/version. Seed/import normalize server; schema kiểm tra string type/length, service/script kiểm tra equality với canonical normalization. No client regex/operator, escape metacharacters. Tests accents/Đ/case/whitespace/tokenAND/regex inputs/pagination; source search-filter chỉ tham chiếu ADR này cho algorithm.

q sau normalize không còn token thì coi như không có q filter; brand empty sau normalize cũng bỏ filter. Sort mặc định latest, page1/pageSize20; price filters inclusive và mọi sort có tie-break _id theo chiều sort. Không tạo relevance score hoặc thứ tự implicit khác contract.
