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

## 2. Seed trên Postgres tạm local, rồi restore lên Neon

**Không seed thẳng lên Neon.** `seed_jmdict` ghi từng từ (nhiều truy vấn/từ, một
transaction); qua mạng tới Singapore hơn một triệu round-trip sẽ mất hàng chục giờ.
Seed vào container tạm (không đụng volume DB local) rồi dump/restore một lần:

```powershell
docker run -d --name vocab-seed-tmp -e POSTGRES_DB=vocab -e POSTGRES_USER=vocab -e POSTGRES_PASSWORD=vocab -p 127.0.0.1:5433:5432 pgvector/pgvector:pg16
cd apps/backend
$env:DATABASE_URL = "postgresql+asyncpg://vocab:vocab@127.0.0.1:5433/vocab"
uv run alembic upgrade head
uv run python -m scripts.seed_jmdict data/bench/jmdict-eng-3.6.2.json --kanjidic data/kanjidic2/kanjidic2-en-3.6.2.json
uv run python -m scripts.seed_hanviet data/hanviet.csv --overrides data/hanviet_overrides.csv --kanjidic2 data/kanjidic2/kanjidic2-en-3.6.2.json
uv run python -m scripts.db_size
docker exec vocab-seed-tmp pg_dump -Fc -U vocab -d vocab -f /tmp/public.dump
docker cp vocab-seed-tmp:/tmp/public.dump ./public.dump
```

Restore bằng `pg_restore` cùng major version với Neon (Neon hiện chạy Postgres 18).
URL Neon để trong `apps/backend/.env.neon` (Git-ignore qua `.env.*`), truyền vào
container bằng biến môi trường, không đặt trên dòng lệnh:

```powershell
$env:DATABASE_URL = "<URL Neon trực tiếp>"
docker run --rm -e DATABASE_URL -v "${PWD}:/dump:ro" postgres:18 sh -c 'pg_restore --clean --if-exists --no-owner --no-privileges --exit-on-error -d "$DATABASE_URL" /dump/public.dump'
uv run python -m scripts.db_size
```

Số đo 16/11/2026 (JMdict 3.6.2 đầy đủ, KANJIDIC2, Hán Việt M7c):

| | Giá trị |
| --- | --- |
| Seed JMdict + KANJIDIC2 local | ~54 phút |
| Seed Hán Việt (lần 2: 0 thay đổi) | 27 giây |
| words / word_senses / kanji | 323.447 / 721.391 / 16.666 |
| Kanji có âm / words có Hán Việt | 9.825 / 245.748 |
| Dump custom-format | 16MB |
| Restore lên Neon | ~1,5 phút |
| Dung lượng trên Neon | 214MB / 512MB |

Admin và giáo trình OpenJLPT (đăng ký tài khoản qua API đã deploy ở bước 3 trước;
script này cũng ghi từng dòng, có thể chạy thẳng Neon nhưng chậm):

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
