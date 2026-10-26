# Japanese Vocabulary App

Một monorepo chung cho frontend và backend của web app từ vựng tiếng Nhật.

```text
japanese-vocab-app/
├── apps/
│   ├── frontend/          # Nơi triển khai FE; chưa viết giao diện
│   └── backend/           # Backend MVP P0, Python / FastAPI
├── docs/                  # Requirements, quyết định và báo cáo
├── scripts/               # Cấu hình, kiểm tra và backup chung
├── docker-compose.yml     # Postgres + API + import worker
└── .env.example
```

FE và BE nằm trong cùng repo, cùng nhánh và lịch sử Git. Chưa khởi tạo framework
frontend; folder `apps/frontend` dành cho giai đoạn làm giao diện.

## Chạy từ thư mục gốc repo

Cần Python 3.12, uv và Docker Desktop với Linux engine.

```powershell
python scripts/init_env.py
docker compose up --build -d
```

Swagger: http://localhost:8000/docs. Health: http://localhost:8000/health.
Config dùng `.env` tại root, không commit secret. DB lưu trong named volume.

## Phát triển backend

```powershell
cd apps/backend
uv sync --frozen
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Import mặc định bất đồng bộ (`IMPORT_MODE=async`). Chạy thêm một terminal backend:

```powershell
uv run python -m app.worker
```

Chạy migration trước worker. Trên Windows, entrypoint worker tự cấu hình SelectorEventLoop
cho psycopg; API tiếp tục dùng asyncpg. Compose dùng cùng build backend cho worker và đợi
API healthy sau migration. `IMPORT_MODE=sync` giữ luồng import đồng bộ để kiểm thử tương thích.
Async upload/commit trả202; theo dõi GET /api/v1/imports/{id} tới review/done hoặc failed.
Thông tin progress gồm processed/total; xử lý worker lỗi quá15 phút được đánh dấu failed khi khởi động lại.

Khi chạy uvicorn trực tiếp, chỉ bật DB bằng `docker compose up -d db` và tắt API
container để nhường cổng 8000. Hướng dẫn seed/import và endpoint ở
[README backend](apps/backend/README.md).

## Kiểm tra và backup từ root

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1
powershell -File scripts/backup.ps1
```

CI chạy backend tại `apps/backend`. Frontend chưa có pipeline vì chưa triển khai.
PDF, dữ liệu OCR/import, tài khoản local và backup không vào Git.
Dữ liệu đã chuyển nằm tại `apps/backend/data/pdf_imports/`; cấu hình local giữ
volume DB cũ bằng `POSTGRES_VOLUME_NAME` để bảo toàn dữ liệu đã import.

- [Yêu cầu](docs/requirements.md)
- [Quyết định triển khai](docs/DECISIONS.md)
- [Báo cáo backend P0](docs/REPORT.md)
- [Báo cáo dữ liệu PDF](docs/PDF_IMPORT_REPORT.md)
