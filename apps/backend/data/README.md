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

M5 trích thêm Unihan_Variants.txt từ cùng ZIP17.0.0. M7 siết chỉ tra
`kTraditionalVariant` và `kZVariant` khi chữ thiếu kVietnamese; bỏ Semantic và
SpecializedSemanticVariant. Nhiều nguồn mâu thuẫn để trống.
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

## KANJIDIC2 — đánh giá M7

Nguồn [jmdict-simplified release 3.6.2+20261019180022](https://github.com/scriptin/jmdict-simplified/releases/tag/3.6.2%2B20261019180022),
đúng release của JMdict local, `kanjidic2-en-3.6.2+20261019180022.json.zip`.
Giải nén JSON vào `data/kanjidic2/kanjidic2-en-3.6.2.json` (Git-ignore).
JSON version3.6.2, dictDate2026-10-19, fileVersion4, databaseVersion2026-292.
Build chỉ lấy `readingMeaning.groups[].readings[]` có `type=vietnam`, giữ thứ tự nguồn,
chuẩn NFC/vị trí dấu bằng `nlp/vietnamese.py`, viết hoa và khử trùng.

Ghi công KANJIDIC2 / Electronic Dictionary Research and Development Group (EDRDG);
cách đọc tiếng Việt do Minh Chau Pham cung cấp, chuyển JSON bởi scriptin/jmdict-simplified.
Phân phối dữ liệu dẫn xuất theo [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/),
giữ ghi công, link giấy phép và ghi rõ đã chuẩn hóa/chọn trường khi chia sẻ.
Xem [giấy phép nguồn](https://github.com/scriptin/jmdict-simplified#kanjidic).

```powershell
uv run python -m scripts.build_hanviet_m7
# Chỉ seed SAU backup custom-format và kiểm tra pg_restore -l thành công
uv run python -m scripts.seed_hanviet --overrides data/hanviet_overrides.csv
uv run python -m scripts.seed_hanviet --overrides data/hanviet_overrides.csv
```

Metadata local `data/hanviet.metadata.json` lưu phiên bản, URL, SHA-256 JSON và các
nguồn Unihan/overrides; kết quả chi tiết ở `verification/m7-hanviet.json`.
Tập chuẩn là169 chữ có âm trong overrides đã duyệt; mọi tỷ lệ chấm điểm dùng mẫu số169,
kể cả chữ nguồn không phủ. Báo cả chứa âm chuẩn đầu và chứa toàn bộ tập âm chuẩn.
Biến thể được đo riêng (không cộng lại âm Unihan trực tiếp).

KANJIDIC2 đạt147/169=86,98% âm đầu trùng, dưới90%; vì vậy M7 **giữ** thứ tự
override > Unihan trực tiếp > Unihan biến thể đã siết. KANJIDIC2 chỉ dùng đánh giá/review;
seed đã hỗ trợ provenance `kanjidic2` cho trường hợp sau này đạt cổng.
Không tự hạ ngưỡng hay bổ sung fallback KANJIDIC2 khi cổng không đạt.

Overrides hiện gồm171 dòng:169 có âm, 滝 chờ duyệt và 込 là quốc tự Nhật để rỗng.
Lô2 áp dụng88 chữ có âm cùng dòng 込 (note riêng theo yêu cầu).
Review3 chỉ lấy hạng601–1.200 có thiếu âm/khác âm đầu/≥3 âm và loại chữ hai nguồn
có cùng tập âm chuẩn hóa. Dữ liệu/review/metadata/backup không commit.

## M7b — chỉ đánh giá, chưa áp dụng combined

```powershell
uv run python -m scripts.evaluate_hanviet_m7b
```

Evaluator chỉ đọc nguồn/review/DB, ghi kết quả vào `verification/m7b-evaluation.json`
và `verification/m7b-combined-mismatches.md`. Không ghi `hanviet.csv`, metadata M7,
overrides hoặc DB. Đòi hỏi hai file review local gốc M5/M6, mỗi file đúng300 chữ,
và KANJIDIC2 pin M7. Các file này vẫn Git-ignore.

Tập chuẩn mới lấy đủ600 chữ; lọc membership KANJIDIC2 còn599, trong đó 込 có chuẩn
rỗng được báo riêng;598 chữ dùng để so âm. Combined chỉ đổi thứ tự tập âm KANJIDIC2
bằng âm chung đầu tiên của Unihan, không thêm âm Unihan ngoài tập đó. Chuẩn hóa
vị trí dấu/viết hoa bảo toàn i/y; do đó KÍ và KÝ vẫn khác.

Combined đạt565/598=94,48%, dưới cổng95%; **dừng, không áp dụng**. Không seed,
không thêm overrides lô3, chưa có review4. Quy tắc production/source/override vẫn M7.
Điểm593/598=99,16% của combined+override không được dùng thay cho cổng combined.

## M7c — combined làm fallback sau khóa âm đã duyệt

Quyết định người dùng thay cổng M7b: fallback combined94,48% tốt hơn Unihan thô72,58%,
không yêu cầu95%. Phần M7b ở trên ghi kết quả lịch sử; production hiện dùng M7c.

`hanviet_overrides.csv` có636 dòng: giữ nguyên171 dòng cũ, thêm441 âm/thứ tự đã duyệt
(note `accepted M5/M6`) và24 override lô3 (note `review M7 lô 3`).598 chữ chuẩn có âm
đạt598/598 sau khóa; 込 và滝 vẫn rỗng, 繰/扱 tiếp tục cần review.

Thứ tự: override kể cả rỗng > combined > Unihan trực tiếp > biến thể Traditional/Z.
Combined giữ tập/thứ tự âm KANJIDIC2, đưa âm Unihan chung đầu tiên lên đầu nếu có;
source `kanjidic2_unihan` nếu có âm chung, `kanjidic2` nếu không. Không thêm âm chỉ có
ở Unihan (森→SÂM, không CHÙM). Hàm dùng chung production/evaluator ở `app/nlp/hanviet.py`.

Population chỉ gồm membership KANJIDIC2. Xóa âm tự động cũ ngoài population và source=null,
không xóa Kanji hoặc nội dung nguồn. Giữ bảo vệ audit PATCH/DICT-08. Seed cần truyền
`--kanjidic2` để chặn cả chữ ngoài population bị đưa lại qua CSV/overrides.

```powershell
# Backup và kiểm tra pg_restore -l TRƯỚC build/seed
uv run python -m scripts.lock_hanviet_m7c
uv run python -m scripts.build_hanviet_m7c
uv run python -m scripts.seed_hanviet --overrides data/hanviet_overrides.csv --kanjidic2 data/kanjidic2/kanjidic2-en-3.6.2.json
uv run python -m scripts.seed_hanviet --overrides data/hanviet_overrides.csv --kanjidic2 data/kanjidic2/kanjidic2-en-3.6.2.json
uv run python -m scripts.verify_hanviet_m7c
```

Lock chạy lại không thêm dòng/sửa override sẵn có. Build cần review gốc M5/M6 và snapshot
`verification/m7b-evaluation.json` độc lập; không build lại sau seed nếu muốn giữ baseline
trước seed trong `verification/m7c-build.json`. Không dùng build M4–M7 để ghi đè production M7c.
Metadata lưu pin/nguồn/license/SHA, điểm strict và báo cáo có thêm i/y-insensitive;
không đổi chính tả dữ liệu để gộp i/y. Review4 và danh sách đổi âm ở
`verification/m7c_hanviet_review_4.md`, `verification/m7c-hanviet-changes.md`; Git-ignore.
