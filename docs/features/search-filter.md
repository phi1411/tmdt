# Search và Filter

## Goal

Tìm/lọc Product đa ngành bằng MongoDB local, phục vụ catalogue và compound-index demo. Backend IMPLEMENTED PHASE05B; algorithm canonical [ADR008](../decisions/008-local-vietnamese-search.md), index canonical database/indexes. UI/full benchmark chưa làm; [contract](../api-contract.md), [review/evidence](../phase-05b-review.md).

## Actors

Guest/Customer xem public; Admin search/filter status qua admin-products.

## Functional Requirements

q theo name, Category/productType/brand/price range, size/color/ram/capacity phù hợp; sort price_asc/price_desc/latest và pagination. Vietnamese có/không dấu dùng normalized fields, literal substringANDtokens; không fuzzy/full-text/relevance/Atlas Search.

## Business Rules

BR-CATALOG và ADR008: public Product/Category ACTIVE; nameNormalized/brandNormalized server-derived cùng Product write. q only name; brand exact normalized; các filter intersection. Price query compound được tối ưu độc lập q; substring/attributes là residual filter, không claim mọi query có IXSCAN hiệu quả.

## Permission

Public read chỉ ACTIVE, không status parameter để xem hidden. Admin GET/admin/products có status ACTIVE/INACTIVE/ARCHIVED allowlist; role enforced backend.

## API

| Method / path | Request | Response data | Error |
| --- | --- | --- | --- |
| GET /products | q?,categoryId?,productType?,brand?,minPrice?,maxPrice?,size?,color?,ram?,capacity?,sort,page,pageSize |200 cards+pagination |400 ID/query;422 unsupported/range |
| GET /admin/products | cùng filters +status? |200 products/version+pagination |401/403/400/422 |

size/color map attributes.sizes/colors membership; ram/capacity exact values. Sort/default/pagination conventions tại api-conventions; unsupported arbitrary attribute path/operator reject, không raw Mongo query.

## Data

Read products/categories, no writes. Product repository/schema+frontend features/search-filter là paths cần inspect; direct dependencies Product projection/schema/ADR008/candidate index manifest. Không cần Orders/Payment/Review cho task này.

## Validation

q trim<=100,<=8 normalized tokens; pagination limits, integer price range min<=max, sort allowlist, IDs valid. Field normalization/regex escape rules ở ADR008; service không nhận client-generated normalized fields. Filter type/category mismatch trả empty, không runtimeerror.

Giá query unsigned integer0..1e9 inclusive; size/color nonempty<=50, ram/capacity nonempty<=100; brand<=100 exact normalized, empty sau normalize bỏ filter. Page1/pageSize20/max100; page vượt cuối[] giữ total, emptytotal→totalPages0. Query integer syntax/ID sai400; unknown/repeated/status public/sort ngoài allowlist/invalid enum/bounds422. Pipeline `$match/$sort` trước current Category `$lookup`, visibility guard trước `$facet` count/items; không Python filter toàn collection. Category-price IXSCAN đã có explain smoke; type-price candidate chưa applied; latest INDEX CANDIDATE cần phase performance đánh giá, chưa tạo index.

## Edge Cases

Đ/đ, uppercase/accents/spaces, literal regex metacharacters, noresults/out-of-rangepage, equal price/date stable tie, category archived. Price_desc sort _id desc để index reverse scan; latest createdAt/_id desc. q không có relevance score.

## Security

Server allowlist/escape tokens, no operator injection, bounded queries; no explain publicendpoint. Không expose hidden Product bằng status query public.

## UI Behavior

Debounce search, URL filter state, reset page khi đổi filter, discard stale network responses. Supported attributes theo nhóm; loading/empty/error tách rõ. Frontend chỉ hiển thị server result/pagination.

## Acceptance Criteria

Name có/không dấu tìm đúng theo ADR008, filters/sort stable đúng server và public statusguard; compound price-filter có explain evidence ở phaseperformance sau. Không Atlas-only dependency hoặc frontend tải toàn catalogue để lọc.

## Testing Checklist

- [x] Unicode/Đ/case/spaces/tokenAND/metacharacter semantics trên MongoDB thật.
- [x] Filter combinations/bounds/status/type/category/attribute membership.
- [x] Pagination, stable ties cho cả3 sorts, empty/out-of-range, unknown/repeated query.
- [ ] Stale UI responses và full index benchmark: phase sau.
