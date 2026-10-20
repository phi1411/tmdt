# Checklist trước bảo vệ —20/10/2026

[Handoff](defense-final-handoff-20261020.md) ghi trạng thái kỹ thuật, account private và đường dẫn. Chỉ tick sau khi đã thực hiện; không coi evidence cũ là rehearsal người thật hôm nay.

- [x] Backend mới nhất714/714tests; frontend strict/build và6status tests PASS theo audit20/10.
- [x] Public66HTTPchecks;2luồng NCB/testOTP/automaticIPN; SIT chính thức6/6Đạt.
- [x] Demo SKU/review/snapshot tạo qua API có journal; corpus gốc479699... giữ nguyên, không reset seed.
- [x] Full7collections canonical export/import sang `ecommerce_defense`; docs/BSON/options/indexes equal.
- [x] Local Mongo PRIMARY, Flask5000, Vite5173;20HTTPchecks COD/idempotency/cancel/stock-once/VNPAYdisabled503 PASS và exact cleanup.
- [x] Browser public SKU XL120k/stock10/review4sao; local login/Order180k/snapshot50k; scoped console warn/error0.
- [ ] Chọn xuyên suốt local Web+local Compass hoặc public Web+Atlas Compass; không trộn DB.
- [ ] SV3 mở Compass:3ngành, Order, Aggregation/Explain; tự Export/Import sang DB mới theo guide.
- [ ] Customer/Admin hai phiên riêng; Cart2items/địa chỉ/quote/tồn sẵn trước timer; giữ kín private credentials.
- [ ] Ba SV tập5phút và10phút có bấm giờ, điền kết quả bên dưới.
- [ ] Nếu cần chứng minh offlineOS: tự ngắt Internet, giữ Mongo/API/FE loopback chạy, thử COD/cancel rồi nối lại. Agent chưa tắt mạngOS; VNPAY/ảnhCDN cần Internet.
- [ ] Sau buổi, hủy đúng đơn chưa PAID/chưa hoàn thành và restore giá fixture. Không xóa lịch sử completed hoặc reset/reseed.

Khởi động lại từ working clone `tmdt-review-20261017`:

```powershell
C:/Users/Admin/Documents/ChatGPT/tmdt/.venv/Scripts/python.exe -X utf8 scripts/demo/start_defense_local.py
```

Nếu port5000/5173 đang có service, helper từ chối tạo bản trùng; mở health/Web hiện có, không kill process chưa rõ nguồn. Helper dùng private `.local/defense-final/runtime.json`, không sửa .env, không tự seed/expiry hoặc ghi Atlas. Có file chạy nhanh `.local/defense-final/start-local.cmd`.

Account note: `.local/defense-final/demo-credentials.md`. Backup/export chứa User hash và địa chỉ, chỉ giữ private; không chiếu lên màn hình hoặc commit. Checkout gốc `tmdt` có helper/demo concurrent chưa commit được giữ nguyên.

Người rehearsal: ______; ngày: ______; bản5phút thực tế: ______; bản10phút: ______. Compass Documents/Aggregation/Explain: ______; GUI Export/Import: ______; ngắt InternetOS/COD: ______.
