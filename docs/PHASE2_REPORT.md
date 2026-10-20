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
Milestone 0 đã commit tại `51e0278` (`perf(search): paginate in SQL, trigram operators`).
Chưa hoàn thành toàn bộ P1; các tính năng P1 còn lại chưa được triển khai trong bước này.

## Thay đổi search

- Đếm và phân trang trong SQL trước khi tải Word/Entry, tránh truyền toàn bộ ID vào
  asyncpg khi truy vấn rộng. Mỗi nguồn chỉ đóng góp tối đa `page * size` ID phân biệt,
  sau khi áp dụng quyền xem và bộ lọc JLPT/giáo trình; giữ thứ tự rank rồi ID.
- Tải nội dung entry và mô tả Hán tự theo trang; truy vấn Hán tự được gộp thành một lần.
- Dùng toán tử pg_trgm `%` cho similarity để planner có thể dùng index; bỏ nhánh
  similarity dư thừa với truy vấn chữ/số dài 1–2 ký tự. Đây là trạng thái Milestone 0;
  thay đổi tiếp theo bỏ ép planner và bổ sung quy tắc Latin ngắn (quyết định 26–32).
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

## Benchmark HTTP trước/sau tại Milestone 0 (lịch sử)

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
requirements.md (DICT-08/09, TB-06/07/08, SRCH-08/09/10, IMP-10/12,
NB-01…06), kèm kiểm chứng riêng. **IMP-11 import Anki được hoãn khỏi Phase 2**;
NB-06 xuất Anki vẫn giữ. Frontend/P2 chưa triển khai. Người dùng sẽ gửi định nghĩa
Milestone 1 sau khi hoàn tất các mục 1–7 trước milestone; không suy diễn phạm vi
Milestone 1 từ prompt kiểm tra Phase 1.

Chạy lại từ `apps/backend` khi Docker Desktop sẵn sàng:

```powershell
uv run pytest --cov --cov-report=term-missing --cov-report=json
uv run python scripts/check_coverage.py coverage.json
uv run ruff check . ../../scripts
uv run ruff format --check . ../../scripts
uv run python -m scripts.bench_search --output verification/bench-search.json
```

## Rà soát mục 1–7 trước Milestone 1

- Commit Milestone 0: `51e0278`, sau 78 test đạt, coverage 93,48%, Ruff xanh.
- Latin 1–2 ký tự: chỉ tìm đầu trường nghĩa/entry, không phân biệt hoa thường;
  không `%q%`, không fuzzy. Index mới trong migration `0002_meaning_prefix`.
- Search trả `total <= 1000`, `total_capped=true` khi có hơn 1.000 từ phân biệt;
  đúng 1.000 trả false. COUNT chỉ trên tập DISTINCT/LIMIT 1001, không đếm toàn bảng.
  Có test mốc 1.000/1.001, khử trùng senses, SQL giới hạn đếm và phân trang 40.000 từ.
- `い` có 199.999 khớp vì fixture tạo 200.000 kana có cùng tiền tố `い`, rồi thay
  từ thứ nhất thành `きんちょう`. Không phải lỗi khớp giữa từ; test mới xác nhận
  `い` tìm được `いぬ`, không tìm `かい` hoặc `きんちょう`.
- Nhánh `search_candidates` cũ (dòng 101–129 trước sửa) đã có test exact/prefix/meaning,
  thứ tự, bộ lọc JLPT và không có kết quả; vẫn giữ để tái hiện baseline P0.
- Không có enable_seqscan/enable_*; đã bỏ force_custom_plan và SET similarity_threshold.
  Chỉ còn SET LOCAL work_mem trong search, statement_timeout/work_mem trong benchmark.
  Viết lại bằng khoảng prefix có index, CTE cho nguồn text và strpos cho substring
  ngắn không có phân biệt hoa/thường. DECISIONS đánh số tiếp 26–32.
- IMP-11 import Anki hoãn khỏi Phase 2; NB-06 xuất Anki vẫn giữ.

### Kiểm tra cuối trước commit bổ sung

- **84/84 test đạt trong 37,47 giây**, coverage service/NLP **95,73%**.
- Auth 95,2%, dictionary **97,7%**, imports 97,2%, search 96,4%, textbooks 91,2%,
  NLP 98,1%; script kiểm tra ngưỡng 70% từng service đạt. Không hạ ngưỡng coverage.
- Ruff check và format theo phạm vi CI đạt, 96 file đúng định dạng; git diff --check đạt.
- Bằng chứng: `apps/backend/verification/pre-m1-tests.log`, `pre-m1-tests.xml`,
  `apps/backend/coverage.json`. Các file bằng chứng local được Git bỏ qua.
- Commit bổ sung dùng message `perf(search): bound totals and short Latin matching`;
  bao gồm migration, code, test và báo cáo. Chưa triển khai migration lên DB thật.

### Dữ liệu và phương pháp đo bổ sung

Mỗi phép đo dùng container PostgreSQL 16/database `vocab_bench` riêng, migration tới
head và ANALYZE; Testcontainers dọn container/database khi kết thúc. Không chạy migration,
seed hay benchmark lên database PDF local. Planner mặc định, rate limit tắt riêng process đo.
ASGITransport đo HTTP trong process, gồm xác thực, SQL và serialize, không gồm mạng/proxy.

- Tổng hợp: giữ 200.000 words, 400.000 senses, 12.000 entries như Milestone 0.
- JMdict: [jmdict-simplified release 3.6.2+20261019180022](https://github.com/scriptin/jmdict-simplified/releases/tag/3.6.2%2B20261019180022),
  bản English đầy đủ (`commonOnly=false`, dictDate 2026-10-19), 218.930 mục nguồn.
  Duyệt tất cả spelling/reading và appliesTo, gộp cặp kanji/kana theo seed hiện có:
  **323.447 words, 721.391 senses**. Không có textbook entries trong phép đo JMdict.
  Loader COPY có test đối chiếu kết quả projection với production seed và test ghi/đọc
  trên database tạm; không thêm nghĩa Việt, Hán Việt hoặc JLPT giả.
- SHA-256 JSON JMdict: `12c39ce51f2e257d04968e5557f4e30249998bb13a7ae07420066a309e6b3a9a`.
  Dữ liệu nguồn thuộc JMdict/EDRDG, phân phối theo CC-BY-SA-4.0; file nằm trong data bị Git bỏ qua.
- Tuần tự: 20 request/truy vấn. Đồng thời: 100 request/truy vấn theo 10 đợt,
  mỗi đợt 10 request, pool tối đa 10 kết nối. Tất cả dùng size=20, page=1, tính cả
  lần đầu; p95 theo nearest rank. Không loại request lỗi khỏi thống kê.
- Capture SQL bao gồm SELECT và WITH. EXPLAIN (ANALYZE, BUFFERS) chạy lại câu SQL có
  thời gian quan sát lớn nhất; đây là chẩn đoán riêng, không phải thời gian HTTP.

### p95 HTTP (ms)

| Query | Synthetic 1 | JMdict 1 | Synthetic 10 | JMdict 10 |
| --- | ---: | ---: | ---: | ---: |
| きんちょう | 62.76 | 22.90 | 346.75 | 212.77 |
| kinchou | 81.30 | 43.23 | 346.19 | 153.24 |
| 緊張 | 95.30 | 140.95 | 274.24 | 293.60 |
| căng thẳng | 90.20 | 299.58 | 248.02 | 475.08 |
| school | 105.83 | 58.41 | 289.10 | 109.48 |
| い | 213.35 | 162.39 | 408.46 | 551.63 |
| a | 37.04 | 83.44 | 239.71 | 261.16 |

### Median / max HTTP (ms)

| Query | Synthetic 1 | JMdict 1 | Synthetic 10 | JMdict 10 |
| --- | ---: | ---: | ---: | ---: |
| きんちょう | 58.25 / 127.53 | 19.77 / 87.51 | 156.40 / 356.37 | 96.82 / 217.04 |
| kinchou | 70.41 / 119.97 | 38.26 / 46.28 | 155.72 / 352.26 | 117.11 / 158.05 |
| 緊張 | 79.24 / 122.58 | 133.70 / 149.80 | 168.05 / 278.93 | 230.21 / 299.11 |
| căng thẳng | 81.86 / 91.95 | 279.36 / 299.68 | 169.43 / 254.26 | 444.32 / 492.51 |
| school | 87.15 / 122.14 | 54.95 / 63.79 | 186.46 / 292.16 | 102.99 / 110.85 |
| い | 164.81 / 214.83 | 157.46 / 164.29 | 307.25 / 416.63 | 290.02 / 563.94 |
| a | 24.60 / 48.81 | 77.38 / 92.05 | 138.66 / 248.55 | 154.01 / 268.47 |

### JSON / log

| Dataset | JSON | HTTP 200 |
| --- | --- | ---: |
| synthetic, c=1 | `apps/backend/verification/bench-pre-m1-final-s1.json` | 140/140 |
| jmdict-simplified-full-eng, c=1 | `apps/backend/verification/bench-pre-m1-final-j1.json` | 140/140 |
| synthetic, c=10 | `apps/backend/verification/bench-pre-m1-final-s10.json` | 700/700 |
| jmdict-simplified-full-eng, c=10 | `apps/backend/verification/bench-pre-m1-jmdict-c10.json` | 700/700 |

Log có cùng tên JSON với đuôi `.log`. JSON chứa từng sample, total/capped, status,
SQL timings và EXPLAIN đầy đủ; thư mục verification không được commit.

### Đánh giá kết quả mới

- Tổng cộng **1.680/1.680 request trả 200**. Tuần tự: tổng hợp p95 37,04–213,35 ms,
  JMdict p95 22,90–299,58 ms. JMdict `căng thẳng` sát mốc 300 ms; lần đo thăm dò
  trước có p95 321,23 ms, vì vậy chưa thể kết luận đạt ổn định.
- 10 đồng thời: tổng hợp có `きんちょう` 346,75 ms, `kinchou` 346,19 ms,
  `い` 408,46 ms; JMdict có `căng thẳng` 475,08 ms và `い` 551,63 ms.
  **Chưa đạt p95 <300 ms cho toàn bộ truy vấn ở tải 10 đồng thời.**
- `a` trên dữ liệu tổng hợp hiện trả total=0, capped=false: nghĩa đều bắt đầu
  bằng invented/school/tension/căng thẳng, không còn khớp chữ a ở giữa trường.
  `school` và `い` trả total=1000, capped=true. Trên JMdict, `school`, `い`, `a`
  cũng capped; `căng thẳng` trả 0 do dataset English không có nghĩa Việt.
- EXPLAIN câu chậm nhất của synthetic: substring Nhật ngắn dùng Seq Scan trên
  word_senses, prefix rất rộng dùng Parallel Seq Scan words; kế hoạch tự chọn vì
  tính chọn lọc thấp, không tắt planner. SQL thực thi khoảng 56,29 ms (c=1) và
  58,66 ms (c=10) trong lần chạy lại EXPLAIN ngoài tải.
- EXPLAIN câu chậm nhất của JMdict: **dùng ix_senses_gloss_trgm** cho substring
  và similarity, cùng các index prefix words; similarity phải recheck khoảng
  26.414 ứng viên để kết luận không có kết quả. SQL khoảng 134,39 ms (c=1),
  136,20 ms (c=10) trong EXPLAIN. Có Seq Scan trên bảng entries/lessons/textbooks
  rỗng; không phải thiếu index trigram trên senses.
- Các phép đo vẫn là local ASGI, chưa chứng minh NFR trên hosting free/mạng thật,
  chưa đo RAM 512 MB. Hướng xử lý hiệu năng tiếp theo: giảm ứng viên fuzzy/recheck
  cho truy vấn không có kết quả và chi phí truy vấn kana rất rộng, rồi đo lại tải.

### Tái chạy benchmark mới

Từ apps/backend, sau khi tải bản JSON đầy đủ nêu trên vào `data/bench`:

```powershell
uv run python -m scripts.bench_search --output verification/bench-s1.json
uv run python -m scripts.bench_search --jmdict data/bench/jmdict-eng-3.6.2.json --output verification/bench-j1.json
uv run python -m scripts.bench_search --concurrency 10 --iterations 100 --output verification/bench-s10.json
uv run python -m scripts.bench_search --jmdict data/bench/jmdict-eng-3.6.2.json --concurrency 10 --iterations 100 --output verification/bench-j10.json
```
