# Giai đoạn 2 — báo cáo kiểm chứng

Ngày bắt đầu: 20/10/2026. Phạm vi: backend P1; không triển khai frontend/P2.

## Baseline trước thay đổi

- Python 3.12.5, PostgreSQL 16 (`pgvector/pgvector:pg16`) qua Testcontainers.
- 77/77 test cũ đạt, 41,20 giây; coverage service/NLP 95,67%.
- Ruff check đạt; Ruff format: 91 file đúng định dạng.
- Log: `apps/backend/verification/phase2-baseline.log`, XML cùng thư mục.
- Không có `docs/PHASE1_CHECK.md` trong repo tại thời điểm bắt đầu.
- Benchmark dùng script `apps/backend/scripts/bench_search.py`, database
  `vocab_bench` trong container tạm, tự xóa sau đo; không dùng database PDF local.

## Tiến độ

Đã tiếp tục và kiểm chứng xong bước tối ưu search (milestone 0) ngày 20/10/2026.
Chưa hoàn thành toàn bộ P1; các tính năng P1 còn lại chưa được triển khai trong bước này.

## Thay đổi search

- Đếm và phân trang trong SQL trước khi tải Word/Entry, tránh truyền toàn bộ ID vào
  asyncpg khi truy vấn rộng. Mỗi nguồn chỉ đóng góp tối đa `page * size` ID phân biệt,
  sau khi áp dụng quyền xem và bộ lọc JLPT/giáo trình; giữ thứ tự rank rồi ID.
- Tải nội dung entry và mô tả Hán tự theo trang; truy vấn Hán tự được gộp thành một lần.
- Dùng toán tử pg_trgm `%` cho similarity để planner có thể dùng index; bỏ nhánh
  similarity dư thừa với truy vấn chữ/số dài 1–2 ký tự. Cấu hình planner/work_mem
  chỉ áp dụng trong transaction search. Xem quyết định 23–25 trong DECISIONS.md.
- Test `test_NFR_01_large_prefix_paginates_before_loading` kiểm tra 40.000 từ,
  tổng kết quả và thứ tự trang 2; đây là hồi quy cho lỗi vượt giới hạn tham số asyncpg.
- Khi tiếp tục, sửa lỗi thứ tự import trong script benchmark để Ruff đạt.

## Kiểm chứng khi tiếp tục

- 78/78 test đạt trong 37,36 giây trên PostgreSQL 16 qua Testcontainers.
- Coverage service/NLP: 93,48%; auth 95,2%, dictionary 89,9%, imports 97,2%,
  search 96,4%, textbooks 91,2%, NLP 98,1%. Script kiểm tra ngưỡng 70% từng service đạt.
- Ruff check và format theo phạm vi CI đạt (93 file); `git diff --check` đạt.
- Log mới: `apps/backend/verification/phase2-resumed.log`, XML cùng tên;
  benchmark mới: `bench-resumed.json` và `bench-resumed.log` trong cùng thư mục.
  Thư mục verification được Git bỏ qua; bảng dưới giữ số liệu trong tài liệu.

## Benchmark HTTP trước/sau

Dataset tổng hợp: 200.000 words, 400.000 senses, 12.000 entries. Mỗi truy vấn đo
20 request tuần tự, size=20, page=1, qua ASGITransport, tắt rate limit.
Baseline lấy orchestration search từ commit P0 `deb52bc`; sau tối ưu dùng code hiện tại.
Database/container tạm tách biệt dữ liệu PDF local và được dọn sau phép đo.

| Truy vấn | p95 trước (ms) | p95 sau (ms) | Tổng kết quả sau | HTTP sau |
| --- | ---: | ---: | ---: | --- |
| きんちょう | 878,8 | 82,4 | 1 | 20/20 × 200 |
| kinchou | 861,3 | 82,4 | 1 | 20/20 × 200 |
| 緊張 | 829,0 | 75,4 | 1 | 20/20 × 200 |
| căng thẳng | 974,5 | 96,2 | 1 | 20/20 × 200 |
| school | 940,9 | 99,5 | 2.061 | 20/20 × 200 |
| い | lỗi 500 toàn bộ | 76,2 | 199.999 | 20/20 × 200 |
| a | lỗi 500 toàn bộ | 167,9 | 199.999 | 20/20 × 200 |

Baseline từ `bench-before.json`; kết quả sau từ `bench-resumed.json`. Baseline có
statement timeout 5 giây, vì vậy các request lỗi không được tính là đạt NFR.
EXPLAIN (ANALYZE, BUFFERS) của SQL chậm nhất được lưu trong JSON sau đo.

Tất cả truy vấn đo mới có p95 dưới 300 ms trên máy local. Chưa xác nhận NFR-01
trên hosting free, tải đồng thời hoặc dữ liệu JMdict thực; ASGITransport không đo
độ trễ mạng/proxy. Chưa đo RAM 512 MB, import 1.000 dòng hoặc xuất Sổ từ.

## Điểm tiếp tục

Bước tối ưu search đã kiểm chứng; phần tiếp theo là các tính năng backend P1 trong
requirements.md (DICT-08/09, TB-06/07/08, SRCH-08/09/10, IMP-10/11/12,
NB-01…06), kèm kiểm chứng riêng. Frontend/P2 chưa triển khai. Chưa commit các thay đổi.

Chạy lại từ `apps/backend` khi Docker Desktop sẵn sàng:

```powershell
uv run pytest --cov --cov-report=term-missing --cov-report=json
uv run python scripts/check_coverage.py coverage.json
uv run ruff check . ../../scripts
uv run ruff format --check . ../../scripts
uv run python -m scripts.bench_search --output verification/bench-search.json
```
