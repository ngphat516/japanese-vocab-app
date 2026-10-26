# Dữ liệu bên ngoài

Không commit dataset thật. CSV, ZIP, license tải kèm và mẫu kiểm chứng nằm local/Git-ignore.

## OpenJLPT (TB-08)

[OpenJLPT](https://github.com/evanclan/OpenJLPT), commit
`0d1d3410bec90bd4098a7c72de820543cb4f707c`, năm CSV `data/csv/vocab-n{1..5}.csv`
được tải vào `data/openjlpt/`. Giữ `LICENSE`, `NOTICE.md` và `COMMIT.txt` cùng dữ liệu.
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/); ghi công OpenJLPT,
JMdict/EDRDG và danh sách JLPT của Jonathan Waller (CC BY), theo
[NOTICE](https://github.com/evanclan/OpenJLPT/blob/0d1d3410bec90bd4098a7c72de820543cb4f707c/NOTICE.md).
Script chỉ dùng word/reading/meanings/level, không lấy câu Tatoeba. JLPT là danh sách
cộng đồng, không phải danh sách từ chính thức của đơn vị tổ chức kỳ thi.

```powershell
uv run python -m scripts.seed_jlpt_textbooks --admin-email YOUR_ADMIN_EMAIL --directory data/openjlpt
```

Script yêu cầu tài khoản admin đã tồn tại, không tự nâng quyền. Tạo năm sách public,
nghĩa English đúng CSV, bài gồm 50 dòng theo thứ tự nguồn; chạy lại không thêm entry trùng.
SHA-256 từng CSV được in trong báo cáo seed. Không tải mạng trong script hoặc test.

## Unihan Hán Việt

Nguồn [Unihan 17.0.0](https://www.unicode.org/Public/17.0.0/ucd/Unihan.zip), lấy riêng
`Unihan_Readings.txt` vào `data/unihan/`; header Unicode Version 17.0.0.
SHA-256 file TXT: `575e69c9ad85a4737a889a4f94cbd987042a90a1a6cc16dd3f4ed995c715b17c`.
Chỉ lấy trường kVietnamese, chuẩn NFC + viết hoa, khử trùng và nối nhiều âm bằng `|`.
**kVietnamese có thể gồm âm Nôm**, không bảo đảm mọi âm là Hán Việt phù hợp từ tiếng Nhật.

```powershell
uv run python -m scripts.build_hanviet_unihan data/unihan/Unihan_Readings.txt --version 17.0.0
```

Xuất `data/hanviet.csv`, `data/hanviet.metadata.json` và
`verification/m4_hanviet_sample.md` (30 chữ seed20261020). Không ghi DB.
M4 dừng ở bước duyệt; M5 đã được người dùng cho phép seed với provenance và override.
Âm chưa duyệt vẫn hiển thị kèm hanviet_source để frontend đánh dấu, sửa dần qua PATCH /kanji.

M5 trích thêm Unihan_Variants.txt từ cùng ZIP17.0.0. Chỉ tra Traditional/Semantic/Z/
SpecializedSemanticVariant khi chữ thiếu kVietnamese; nhiều nguồn mâu thuẫn để trống.
`hanviet_overrides.csv` gồm13 âm đã duyệt và dòng 滝 rỗng/chờ duyệt, được version-control.
Không dùng lại script build M4 để ghi đè CSV M5 khi chưa có chủ đích.

```powershell
uv run python -m scripts.build_hanviet_m5
uv run python -m scripts.seed_hanviet --overrides data/hanviet_overrides.csv
```

CSV M5 thêm source, metadata ghi SHA-256 cả readings/variants/overrides. Review300 chữ
ở verification/m5_hanviet_review.md; seed giữ các sửa tay Kanji/Word có audit và chạy lại0 thay đổi.

[Unicode License V3](https://www.unicode.org/license.txt), SPDX `Unicode-3.0`.
Copyright © Unicode, Inc.; file nguồn ghi © 2025. Toàn bộ thông báo bản quyền và
điều khoản đi kèm tại `data/unihan/LICENSE.txt`; giữ file này khi chia sẻ CSV/dữ liệu.
Dữ liệu được cung cấp nguyên trạng theo điều khoản Unicode, không bảo đảm độ chính xác.
