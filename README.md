# Backend từ vựng tiếng Nhật P0

FastAPI modular monolith, Python 3.12, uv, Pydantic v2, async SQLAlchemy 2.0,
Alembic, PostgreSQL 16 + pg_trgm + pgvector. Chưa có frontend. Chỉ triển khai
AUTH-01..05, DICT-01..07, TB-01..05, IMP-01..09, SRCH-01..07.

Trạng thái kiểm chứng và bảng từng mã nằm trong [docs/REPORT.md](docs/REPORT.md).
Các lựa chọn khi tài liệu chưa rõ nằm trong [docs/DECISIONS.md](docs/DECISIONS.md).
Tài liệu yêu cầu đầy đủ được trích từ file Word vào [docs/requirements.md](docs/requirements.md).

## Chạy bằng Docker Compose

Cần Docker Desktop với Linux engine đang chạy. Tại thư mục project:

```powershell
python scripts/init_env.py
docker compose up --build
```

API: http://localhost:8000; Swagger: http://localhost:8000/docs;
health: http://localhost:8000/health và /api/v1/health.
API tự chạy `alembic upgrade head` trước khi khởi động. Dữ liệu DB nằm trong named volume.
Không có tài khoản admin/mật khẩu mẫu được tự tạo.

## Chạy local với uv

Nếu máy chưa có uv: cài theo https://docs.astral.sh/uv/getting-started/installation/
(có thể dùng `python -m pip install uv`), sau đó mở terminal mới.

```powershell
uv sync --frozen
uv run python scripts/init_env.py
# DATABASE_URL mặc định kết nối DB ở localhost:5432.
docker compose up -d db
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Project trên máy đã có .env với JWT secret sinh ngẫu nhiên; script init_env không ghi đè
config đã có. Khi clone project ở máy khác, chạy script để sinh cấu hình local riêng.

Đăng ký bằng /api/v1/auth/register, đăng nhập bằng /api/v1/auth/login rồi dùng nút
Authorize trên Swagger. Login nhận JSON email/password; refresh rotate token,
token cũ bị thu hồi. Logout thu hồi refresh token; access token hết hiệu lực sau 15 phút.

Muốn bootstrap admin: đăng ký tài khoản thường trước rồi chạy
`uv run python -m scripts.create_admin email@example.com` từ terminal quản trị DB.
Client không thể tự chọn role. Không có API admin sửa từ hay tạo bộ JLPT P1.

## Seed dữ liệu

Không tự tải dataset. Đặt các file đã chuẩn bị, đã kiểm tra giấy phép vào `data/`:

- `jmdict.json`: JSON jmdict-simplified có `words`, mỗi mục có id, kanji, kana, sense.
- `kanjidic.json`: JSON có `characters`, literal, misc.strokeCounts, readingMeaning.groups.meanings.
- `hanviet.csv`: UTF-8 cột `kanji,hanviet`; nhiều âm tách bằng `|`, ví dụ `楽,LẠC|NHẠC`.
- `jlpt.csv`: UTF-8 cột `kanji,kana,jlpt_level`, level từ N1 tới N5.

```powershell
uv run python -m scripts.seed_jmdict data/jmdict.json --kanjidic data/kanjidic.json
uv run python -m scripts.seed_hanviet data/hanviet.csv
uv run python -m scripts.seed_jlpt data/jlpt.csv
```

Chạy lại seed không tạo trùng word/sense, kanji được upsert. Chạy Hán Việt sau JMdict
để cập nhật cả words đã có. Từ ngoài danh sách JLPT giữ null. Chuyển danh sách JLPT
nguồn về CSV trên trước khi seed; chưa có downloader hoặc adapter cho mọi format nguồn.
Khi chạy qua container, dùng `docker compose exec api uv run --no-sync python -m scripts...`;
file data phải được copy/mount vào `/app/data` trước.

Nguồn và giấy phép:

- [jmdict-simplified](https://github.com/scriptin/jmdict-simplified) chuyển đổi
  dữ liệu [JMdict và KANJIDIC của EDRDG](https://www.edrdg.org/edrdg/licence.html).
  Giữ attribution và các điều kiện license của bản dataset tải về khi phân phối.
- JLPT: [Bluskyo/JLPT_Vocabulary](https://github.com/Bluskyo/JLPT_Vocabulary)
  hoặc OpenJLPT như tài liệu đề xuất. Chưa đóng gói dataset hoặc khẳng định license;
  kiểm tra license của nguồn cụ thể trước khi sử dụng/phân phối và ghi attribution.
- TODO: chưa xác định nguồn Hán Việt thật và giấy phép. Script chỉ đọc file do bạn cung cấp.
- Mimikara là sách thương mại; chỉ import vào giáo trình private, giữ source_url/license
  từ nguồn hợp lệ. Fixture không chép nội dung sách và không đại diện format thật.

## Import

1. Tạo textbook private, ghi edition, license, source_url nếu có.
2. POST `/api/v1/imports` multipart: textbook_id, adapter, file.
3. GET `/api/v1/imports/{id}/rows?match_status=ambiguous`.
4. PATCH dòng với `{"chosen_word_id": id}` hoặc `{"skipped": true}`.
5. POST `/api/v1/imports/{id}/commit` khi đã review hết.

Adapter `csv_template` nhận CSV UTF-8/XLSX sheet đầu, cột lesson, order, kanji, kana,
meaning_vi, meaning_en, example_ja, example_vi, note. Bốn cột đầu bắt buộc; mỗi dòng
phải có ít nhất một block hợp lệ. Kanji có thể để trống. GET `/api/v1/imports/template`
tải mẫu. Cột ngoài template được giữ trong raw.

Adapter `mimikara` dùng format giả định được ghi chi tiết trong docstring
`app/modules/imports/adapters/mimikara.py` và DECISIONS. Các trường danh sách dùng
JSON trong ô CSV/XLSX. Có thể xem fixture `tests/fixtures/mimikara.csv` tự bịa.
Không có chức năng audio; tên file audio chỉ được bảo toàn trong raw.

File tối đa 5 MB, 5.000 dòng; XLSX giải nén tối đa 50 MB. Job import chạy đồng bộ,
không cần worker/Redis. Staging tạo bài trước; commit nguyên tử cho words/entries.
Lỗi commit trả 409 và job failed; không tự retry job failed, upload lại sau khi sửa nguồn.
Import cùng word vào cùng lesson cập nhật entry (unique word_id, lesson_id).

### Dữ liệu chuyển từ PDF local

Adapter `normalized_json` nhận `{ "source": {...}, "rows": [...] }`, mỗi row có
kanji, kana, lesson_no, order_no, content (đầy đủ block), raw tùy chọn. Adapter giữ
metadata nguồn và cột lạ trong staging raw; không tự OCR, đoán cách đọc hoặc dịch nghĩa.
Giới hạn 5 MB / 5.000 dòng và pipeline review/commit vẫn áp dụng.

Dữ liệu chuyển từ PDF người dùng nằm trong `data/pdf_imports/`, được Git bỏ qua.
`uv run python -m scripts.import_local_data` nhập JSON tại đây vào các textbook private,
lưu receipt và thông tin tài khoản local trong cùng thư mục. Không commit access.json.
Các bài được đặt theo số trang PDF để đối chiếu. Mục từ OCR có ghi chú cần rà ảnh nguồn;
với Kanji/Dokkai, danh sách từ được trích tự động, không phải danh mục từ do nhà xuất bản
biên soạn. Hai file GOI trùng SHA-256 chỉ được xử lý một lần.

## Search và endpoint P0

Prefix `/api/v1`; danh sách chi tiết luôn xem tại `/docs`.

- Auth register/login/refresh/logout; GET/PATCH /me.
- GET /search?q=...&textbook_ids=1&textbook_ids=2&jlpt=N3&page=1&size=20.
- GET /words/{id} trả word, nghĩa gốc, đầy đủ entries được phép đọc.
- Textbook CRUD; lesson CRUD; GET entries theo lesson và GET entry theo id.
- Import adapters/template/upload/job/rows/review/commit.
- Health công khai ở /health và /api/v1/health.

Search gom theo word, xếp exact → prefix → nghĩa, giữ full block cho 10 word đầu
của toàn bộ tập kết quả. Các word sau có content=null và summary; lấy full qua /words/{id}.
Chỉ entry public hoặc của chủ sở hữu xuất hiện trong search và word detail.
Canonical dictionary words dùng chung; user khác vẫn có thể thấy từ chuẩn nhưng không thấy
nội dung private. Truy vấn nghĩa không được tìm xuyên vào nội dung private của người khác.
P0 chưa có lemmatization, furigana tự sinh, semantic search, Sổ từ hoặc SRS.

## Test và chất lượng

Docker engine phải truy cập được từ terminal chạy test. Bộ integration tự tạo container
`pgvector/pgvector:pg16` bằng testcontainers-python, chạy Alembic, mỗi test có transaction
và rollback. Chỉ dùng fixture nhỏ (30 từ, 20 kanji), không tải dữ liệu từ điển thật.
Docker có thể tải image Postgres ở lần đầu. Không fallback SQLite và không skip test DB.

```powershell
uv run pytest --cov --cov-report=term-missing --cov-report=json
uv run python scripts/check_coverage.py coverage.json
uv run ruff check .
uv run ruff format --check .
```

Coverage tối thiểu 70% toàn tập service/NLP, đồng thời script kiểm tra từng service
đã triển khai và tổng package nlp. CI chạy các lệnh trên khi push/PR.
Unit test độc lập Docker: `uv run pytest tests/test_units.py tests/test_security_and_contract.py`.
Unit xanh không thay thế integration xanh. Tiến độ milestone setup → auth → dictionary
→ textbooks → imports → search → hoàn thiện; chỉ commit khi cả pytest và Ruff xanh.

## Vận hành

Config qua .env/biến môi trường; secret bắt buộc, CORS dùng danh sách domain frontend.
Rate limit theo phút được lưu Postgres để chia sẻ giữa process: auth 10/phút/IP,
upload imports 10/phút/user, search 60/phút/user. Không tin X-Forwarded-For từ client.
Nếu deploy sau proxy cần cấu hình trusted proxy chính xác. JSON log có request id,
không ghi token/password; gzip bật cho response từ 1 KB. Search vượt 200 KB trả 422
yêu cầu giảm size/lọc textbook. Chưa benchmark 200.000 từ hoặc RAM 512 MB.

Backup: `powershell -File scripts/backup.ps1` tạo pg_dump custom-format trong backups/.
Operator phải cấu hình Windows Task Scheduler hoặc cron chạy hằng ngày, retention và
lưu bản sao ngoài máy. Khôi phục thử trên DB riêng bằng `pg_restore`; không ghi đè DB
production để kiểm thử. Schema chỉ thay đổi bằng Alembic migration, không create_all khi chạy API.

## Kết quả kiểm chứng và dữ liệu còn thiếu

77 test đã xanh trên PostgreSQL 16 + pgvector qua testcontainers; coverage service/NLP
95,67%, từng service vượt 70%; Ruff check và format sạch. Docker Compose đã build/chạy,
Alembic ở head, /health và /docs trả 200. Chi tiết từng mã P0 trong REPORT.

Đã chuyển PDF Mimikara và Shinkanzen người dùng cung cấp, đối chiếu từ/cách đọc với
JMdict và import vào textbook private trong DB local. Xem [báo cáo dữ liệu](docs/PDF_IMPORT_REPORT.md)
và thư mục `data/pdf_imports/` (được Git bỏ qua). Các mục OCR cần rà soát với bản gốc;
nguồn Hán Việt có license, dataset JLPT thật và benchmark 200.000 từ vẫn còn thiếu.
Không có frontend trong project này.
