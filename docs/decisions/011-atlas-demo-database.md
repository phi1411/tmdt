# ADR-011 — Database demo Atlas riêng

Ngày14/10/2026. Người dùng chọn phương án deploy miễn phí Render+Atlas và yêu cầu “up db tôi lên” sau khi tạo Cluster0/cung cấp credential qua ảnh.

## Quyết định

Sao chép sáu collection hiện tại của ecommerce_dev sang **novamart_demo** trên cluster Atlas đã chỉ định, chỉ khi database đích chưa có collections/data. Không sửa hoặc xóa DB local, benchmark hay sample datasets trên Atlas. Giữ nguyên schema v1,6validators strict/error,14declared+6_id_indexes,ObjectId/Date/long/embedded documents và password hashes. Không reseed, đổi password, rewrite Order history hoặc thêm collections kỹ thuật vào DBnghiệp vụ.

Replica set Atlas được driver khám phá qua SRV và hello, tên khácrs0. Đây là deployment target riêng, không đổi kiến trúc document hoặc bỏ transaction. Application config hiện vẫn khóa localrs0: migration dùng MongoClient riêng với allowlist exact hostname+DB, không nới guard của tooling local và không đổi .envlocal. Tích hợp backend hosting là bước riêng, chưa được nghiệm thu chỉ vì uploadDBthành công.

## Migration và verification

Capture source snapshot trong transaction read-only, private BSON/EJSON backup+journal trước mọi write. Preflight ping/PRIMARY/sessions/targetempty, schema/indexsourcerefsPASS. Tạo destination collections/indexes từ canonical artifacts rồi insert nguyên documents trong một transaction snapshot/majority; không drop/delete/replace bất kỳ dữ liệu đích có sẵn. Khi lỗi, giữ journal và partialschema để đối chiếu, không tự reset. Resume chỉ khi đúng ownership,source digest,canonical schema và đích rỗng hoặc hoàn toàn khớp corpusđãghi.

So sánh canonical BSONdocuments từng collection/count/digest; canonical schema/index/ref checks, snapshot aggregation revenue/Top5 giống nhau. Fingerprint local trước/sau giữ nguyên. Public evidence chỉ counts/digests/status, không URIcredential/documents/passwordhash/address. Credential và sourcebackup ở ignored.local, không commit/push.

## Phạm vi và trade-off

CloudDBsẵn sàng không đồng nghĩa Flask/React đã deploy hoặc VNPAYLivePASS. Local vẫn là bản demo offline và nguồn benchmark; benchmark30.000/10.000 không upload. Live corpus bao gồm tài khoản được giữ và fixture07C theo chỉ dẫn trước, không ép counts về seed40/180/100. Cần kiểm thử transaction trên chínhAtlas trước khi nghiệm thu checkoutpublic; mutation giao dịch thử phải có ownership/cleanupriêng.
