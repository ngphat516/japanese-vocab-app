# Deploy backend: Render + Neon (free tier)

Mục tiêu: chạy API thật trên gói free để kiểm chứng NFR (RAM 512MB, độ trễ HTTP).
Chỉ đưa **dữ liệu công khai** lên cloud: JMdict, KANJIDIC2, Hán Việt, giáo trình
OpenJLPT. Không dump DB local, không đưa giáo trình OCR/PDF lên server bên thứ ba.

| Thành phần | Dịch vụ | Giới hạn free cần nhớ |
| --- | --- | --- |
| API (Docker) | Render Web Service | 512MB RAM, 0,1 CPU, ngủ sau 15 phút không có request (cold start 30–60s) |
| PostgreSQL 16 | Neon | 0,5GB storage/project, compute tự suspend sau 5 phút |

Chế độ import là `IMPORT_MODE=sync`, không chạy worker (quyết định 88 trong DECISIONS).

## 1. Tạo database Neon

1. Đăng ký https://neon.tech, tạo project, chọn **Postgres 16**, region gần Render
   (ví dụ `AWS Asia Pacific (Singapore)` khi Render dùng `singapore`).
2. Trong **Connection details**, **tắt "Connection pooling"** để lấy URL trực tiếp
   (host không có `-pooler`). PgBouncer transaction mode không hợp với prepared
   statement của asyncpg và Alembic.
3. Copy URL dạng `postgresql://user:pass@ep-xxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require`.
   App tự chuyển sang `postgresql+asyncpg://...?ssl=require`, không cần sửa tay.

Extension `pg_trgm` và `vector` được migration `0001_p0` tạo tự động; Neon hỗ trợ cả hai.

## 2. Migration + seed từ máy local lên Neon

Chạy từ `apps/backend`, dùng biến môi trường tạm cho phiên PowerShell, **không ghi
URL Neon vào `.env` hay commit**:

```powershell
cd apps/backend
$env:DATABASE_URL = "postgresql://...neon.tech/neondb?sslmode=require&channel_binding=require"
uv run alembic upgrade head
uv run python -m scripts.seed_jmdict data/bench/jmdict-eng-3.6.2.json --kanjidic data/kanjidic2/kanjidic2-en-3.6.2.json
uv run python -m scripts.seed_hanviet data/hanviet.csv --overrides data/hanviet_overrides.csv --kanjidic2 data/kanjidic2/kanjidic2-en-3.6.2.json
```

Kiểm tra dung lượng ngay sau seed JMdict, trước các bước tiếp theo:

```powershell
uv run python -m scripts.db_size
```

Nếu vượt ~450MB, dừng lại: JMdict đầy đủ không vừa gói 0,5GB, cần chọn tập con
hoặc đổi nơi chứa DB. Ghi số đo vào báo cáo.

Admin và giáo trình OpenJLPT (đăng ký tài khoản qua API đã deploy ở bước 3 trước):

```powershell
uv run python -m scripts.create_admin YOUR_ADMIN_EMAIL
uv run python -m scripts.seed_jlpt_textbooks --admin-email YOUR_ADMIN_EMAIL --directory data/openjlpt
Remove-Item Env:DATABASE_URL
```

## 3. Tạo Web Service trên Render

1. Đăng ký https://render.com bằng GitHub, cấp quyền repo `japanese-vocab-app`.
2. **New → Blueprint**, chọn repo; Render đọc [render.yaml](../render.yaml).
3. Nhập `DATABASE_URL` (URL Neon trực tiếp ở bước 1). `JWT_SECRET` được Render sinh
   ngẫu nhiên. `CORS_ORIGINS` sửa lại khi có domain frontend.
4. Deploy. Container chạy `alembic upgrade head` rồi uvicorn trên `$PORT`.
   `autoDeploy: false` nên mỗi lần muốn cập nhật phải bấm **Manual Deploy**.

Kiểm tra: `https://<service>.onrender.com/health` trả 200 và Swagger ở `/docs`.

## 4. Kiểm chứng NFR trên deploy

- **RAM (NFR-03):** tab **Metrics** của Render, ghi peak memory sau khi gọi search,
  import CSV 1.000 dòng và export 1.000 từ.
- **Độ trễ (NFR-01):** chạy benchmark HTTP từ máy local tới URL Render sau khi đã
  gọi `/health` để đánh thức service; báo cáo riêng cold start và warm.
- **Swagger/CORS/health (NFR-07, 11, 13):** xác nhận trên URL deploy.
- Backup hằng ngày (NFR-09): Neon free có point-in-time restore ngắn hạn; lịch
  `pg_dump` riêng vẫn chưa thiết lập.

## Ghi công dữ liệu

Dữ liệu trên server phân phối qua API nên phải giữ ghi công JMdict/KANJIDIC2 (EDRDG,
CC BY-SA 4.0), Unihan (Unicode-3.0) và OpenJLPT (CC BY-SA 4.0). Xem
[data/README](../apps/backend/data/README.md).
