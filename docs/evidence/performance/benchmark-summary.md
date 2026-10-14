# Benchmark summary — PHASE07B

**BENCHMARK DATASET**, không phải seed chính thức của đề.

| Query | BEFORE plan | Docs / keys | AFTER plan | Docs / keys | Final rows | Giảm docs |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| products-category-price | COLLSCAN | 30,000 / 0 | IXSCAN | 20 / 20 | 20 | 99.933% |
| products-category-price-full-api | COLLSCAN | 30,000 / 0 | IXSCAN | 96 / 96 | 1 | 99.68% |
| products-type-brand-price | COLLSCAN | 30,000 / 0 | IXSCAN | 160 / 160 | 20 | 99.467% |
| products-type-brand-price-full-api | COLLSCAN | 30,000 / 0 | IXSCAN | 1,108 / 1108 | 1 | 96.307% |
| revenue-day | COLLSCAN | 10,000 / 0 | IXSCAN | 152 / 152 | 7 | 98.48% |
| top-products | COLLSCAN | 10,000 / 0 | IXSCAN | 152 / 152 | 5 | 98.48% |

Full-api trả1facet document chứa20items; selection trả20Products; Revenue/Top5 là rows cuối pipeline.

| Query | No suitable index p50 / p95 ms | Natural p50 / p95 ms | Named p50 / p95 ms | Planner p50 / p95 ms |
| --- | ---: | ---: | ---: | ---: |
| products-category-price | 29.443 / 33.912 | 29.103 / 42.596 | 1.200 / 3.077 | 1.300 / 3.318 |
| products-category-price-full-api | 45.360 / 87.573 | 44.919 / 83.524 | 17.776 / 30.518 | 18.457 / 31.773 |
| products-type-brand-price | 30.781 / 35.122 | 31.359 / 47.739 | 1.824 / 4.441 | 2.151 / 5.386 |
| products-type-brand-price-full-api | 63.350 / 104.428 | 75.082 / 157.857 | 45.213 / 73.850 | 44.345 / 110.239 |
| revenue-day | 15.057 / 16.090 | 16.149 / 21.643 | 2.974 / 5.254 | 3.045 / 7.314 |
| top-products | 22.607 / 28.065 | 22.540 / 28.986 | 3.726 / 8.039 | 4.239 / 6.400 |

Warmups5/repeats30, single-node rs0/WiredTiger, fully materialized cursor.
Timings là observations local warm cache; không claim speedup X lần hoặc latency production.
Explain bỏ qua plan cache; client latency đo riêng với query thật. Index chỉ hỗ trợ các stages đầu phù hợp, không toàn bộ aggregation.
Raw plans/samples/hashes: [results](benchmark-results.json), [before](before-index.json), [after](after-index.json), [aggregations](aggregation-explain.json).
Index tăng storage và chi phí duy trì khi insert/update. Write throughput chưa đo; không thêm index mọi tổ hợp.
