# Checklist gói nộp đồ án NoSQL

Mốc tổng hợp:20/10/2026. Không thay thế việc giảng viên chấm hoặc nhóm trình diễn trực tiếp.

## Đã có trong repository

- [x] Source React/Flask, dependencies có lock, hướng dẫn cấu hình không chứa secrets.
- [x] Báo cáo tổng hợp: [final-project-report.md](final-project-report.md).
- [x] Bảng truy vết từng mục barem: [final-rubric-matrix.md](final-rubric-matrix.md).
- [x]7JSON Schema validators,16declared indexes,8canonical aggregation pipelines.
- [x] Seed generator/manifest180Products,40Users,100Orders; mỗi seed Order2–5items.
- [x] Backend714tests và frontend strict/build/status tests; public/API/browser evidence ghi đúng thời điểm và phạm vi.
- [x] Performance benchmark riêng30.000Products/10.000Orders với explain, kết quả bằng nhau, p50/p95.
- [x] VNPAY Sandbox bank/OTP/automaticIPN/Return và6/6SIT; không tiền thật.
- [x] Demo SKU/review/snapshot và full canonical export/import có ownership/integrity receipts.
- [x] Kịch bản5phút/10phút, Compass guide, Q&A và phân công3SV.
- [x] Website public: https://novamart-web.onrender.com . GitHub: https://github.com/phi1411/tmdt .

## Cần nhóm xác nhận trước khi nộp

- [ ] Điền trường/khoa/lớp, giảng viên, họ tên và MSSV3thành viên. Chưa có đủ dữ liệu để agent tự điền.
- [ ] Kiểm tra mẫu/định dạng báo cáo và slide mà giảng viên yêu cầu. Repository chưa có bản Word/PDF hoặc PowerPoint tổng hợp; Markdown hiện có nội dung kỹ thuật, chưa được gọi là đã nộp đúng biểu mẫu của trường.
- [ ] SV3 thao tác Compass Documents/Order/Aggregation/Explain và Export/Import sang DB mới, lưu bằng chứng GUI.
- [ ] Ba SV rehearsal có bấm giờ và ký tên/ngày trong [pre-demo-checklist.md](pre-demo-checklist.md).
- [ ] Nếu cần offline toàn máy: tự ngắt Internet rồi kiểm tra COD local; đây là kiểm tra dự phòng, không phải yêu cầu bắt buộc được nêu trong barem gốc.
- [ ] Đọc báo cáo, đối chiếu phần mình phụ trách và chuẩn bị trả lời; không suy ra điểm10/10 từ test PASS.

## Không đóng gói nhầm

`.env`, `.local`, Atlas URI, JWT/merchant secret, mật khẩu tài khoản, full database backup/export chứa User hash/địa chỉ, virtualenv, node_modules và cache không nằm trong gói source công khai. Seed generator và các ví dụ đã làm sạch đủ để tái tạo dữ liệu mô phỏng; không cần nộp credentials thật.

Nếu giảng viên yêu cầu dump MongoDB, nhóm dùng dữ liệu mẫu đã làm sạch và gửi qua kênh được yêu cầu; không lấy private backup hiện hành rồi tải lên GitHub. Không reset/reseed database demo đang dùng để tạo gói nộp.

Môi trường hiện tại: working clone `tmdt-review-20261017`; checkout gốc `tmdt` còn thay đổi riêng của phiên khác và được giữ nguyên. Xem [handoff](defense-final-handoff-20261020.md) để chạy local và tìm account note private. Public dùng Atlas; local dùng `ecommerce_defense`, không tự đồng bộ hai chiều.
