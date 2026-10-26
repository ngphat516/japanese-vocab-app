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
Milestone 1 NLP đã hoàn tất; kết quả và tài nguyên ở cuối báo cáo. Dừng trước Milestone 2.

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
NB-06 xuất Anki vẫn giữ (Milestone 3). Frontend/P2 chưa triển khai. Milestone 1
được thực hiện theo prompt NLP mới; không mở rộng sang Milestone 2.

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

## Milestone 1 — Bước 0

- Backup trước migration: `backups/milestone1/vocab-20261020-161758.dump`,
  4.050.202 byte, tạo bằng scripts/backup.ps1 trên volume local hiện có.
- Đã chạy alembic upgrade head lên DB thật: 0001_p0 → 0002_meaning_prefix.
  Health 200, database ok; search 緊張 trả 200, 11 kết quả, 緊張 đứng đầu.
  Bằng chứng: `verification/m1-local-smoke.json`, `m1-local-migration-0002.log`.
- Tiếng Việt có dấu chỉ tìm meaning.vi trong entry có quyền xem và gloss lang=vie.
  CTE lọc ngôn ngữ trước khi tính fuzzy, không fuzzy English; test loại cả gloss eng,
  example.vi và meaning.en dù chứa nguyên chuỗi tiếng Việt. Không đoán tiếng Việt không dấu.
- NFR-01 đã đổi theo yêu cầu và ghi DECISIONS 33: <300 ms tuần tự, <600 ms ở 10
  đồng thời, phải đo uvicorn/HTTP thật trên môi trường deploy. ASGI chỉ so sánh trước/sau.
- Benchmark riêng căng thẳng trên cùng JMdict đầy đủ: p95 **59,13 ms c=1** (20/20 HTTP 200),
  **292,83 ms c=10** (100/100 HTTP 200), total=0. Trước lần lượt 299,58/475,08 ms.
  JSON/log: `verification/m1-vi-j1.*`, `verification/m1-vi-j10.*`; database tạm đã dọn.
- **85 test đạt**, coverage 95,81%; từng service/NLP ≥70%, Ruff/format xanh.
  Log: `verification/m1-step0-tests-final.log`. Không tối ưu thêm tải đồng thời.

## Milestone 1 — NLP, lemma và furigana

### Triển khai

- Bước 0 commit `dcee0b9` (`perf(search): skip English fuzzy for Vietnamese queries`).
- SudachiPy **0.7.0**, core **20261015**, psutil dev **7.2.2**, khóa trong uv.lock;
  uv sync --frozen đạt. SplitMode C; một instance nạp lười/process, khóa thao tác
  tokenization, Token bất biến. Lemma giữ する; trợ từ/trợ động từ/ký hiệu bị lọc.
- Furigana tách okurigana khi căn duy nhất: 食[た]べる, 取[と]り扱[あつか]い,
  緊張[きんちょう]して, 人々[ひとびと]. Fallback cả token nếu không căn được;
  giữ nguyên furigana có sẵn và vùng {{...}}; idempotent. Chưa tự áp furigana vào import/entry.
- Migration **0003_entry_lemmas** đã áp lên DB local sau backup. Entry.lemmas là
  text[] NOT NULL DEFAULT '{}' + GIN; save_entry tính từ các trường Nhật trong thread.
  Search chưa dùng lemma; search_text/summary không nối thêm lemma. DECISIONS **34–39**.

### Backup và backfill local

| Thời điểm | Backup | Kích thước |
| --- | --- | ---: |
| Trước 0002 | `backups/milestone1/vocab-20261020-161758.dump` | 4.050.202 byte |
| Trước 0003/backfill | `backups/milestone1/vocab-20261020-162918.dump` | 4.050.900 byte |

Đây là đường dẫn tương đối root repo. Đã đọc được catalog pg_restore của backup mới
(custom format, 102 TOC entries). Chỉ kiểm tra downgrade trên DB tạm.

- Backfill lô500: **11.906 entry** được quét; dry-run dự báo **11.535** thay đổi.
- Lần ghi thứ nhất: **11.535**; lần thứ hai: **0** thay đổi.
- Hash content + search_text của toàn bộ entry trước/sau giống nhau:
  `5ba73083acd62e73b4cb8a6d1f6d0ae0aeb36c789fa1b008589b63795dae05ad`.
  Không thay nội dung OCR hoặc summary bằng kết quả NLP.
- Bằng chứng: `verification/m1-backfill-dry.log`, `m1-backfill-first.log`,
  `m1-backfill-second.log`, `m1-content-before.json`, `m1-content-after.json`.

### Test và kiểm tra chất lượng

| Môi trường | pytest | Coverage service/NLP |
| --- | --- | ---: |
| Windows, Python 3.12.5 | **105/105 PASS**, 45,64 giây | **96,34%** |
| Linux Docker, Python 3.12.15 | **105/105 PASS**, 52,69 giây | **96,34%** |

Toàn bộ 84 test trước milestone vẫn đạt. Có test lemma đã chia, lọc POS,
dedup/thread safety/lazy initialization, okurigana/fallback/々/idempotence/bảo vệ
markup, save_entry/summary, backfill dry-run + chạy hai lần, migration
upgrade → downgrade → upgrade và GIN/default. Test kiến trúc nlp độc lập vẫn xanh.

Coverage từng service: auth 95,2%, dictionary 97,7%, imports 97,2%, search 96,4%,
textbooks 91,7%; NLP **99,3%**, tokenizer và furigana **100%**. Check coverage ≥70%
đạt; không hạ ngưỡng hoặc bỏ test. Ruff check/format theo phạm vi CI xanh, 103 file;
git diff --check đạt. Linux integration test dùng quyền truy cập Docker socket cho
Testcontainers; image API vẫn chạy user api. Chưa tạo GitHub Actions run mới vì chưa push.

Log: `verification/m1-tests.log`, `m1-tests.xml`, `m1-linux-full-tests.log`,
`m1-linux-tests.log`; build Linux: `m1-linux-final-build.log`.

### Đo tài nguyên và 1.000 câu thật

Nguồn: giáo trình được tìm theo tên **Mimi Kara Oboeru N3 - Goi (PDF OCR)**,
textbook_id=1 sau truy vấn, không hardcode. Có **1.157 câu ví dụ**; chọn **1.000 câu
khác nhau** bằng seed20261020. Bỏ markup trước khi đo để thực sự sinh furigana mới.
Nạp dictionary trước các phép đo 1.000 câu, đo thời gian nạp riêng. Cùng workload
trên Windows và Linux, SHA-256:
`69ac6dabeb095b627b20eae10881a82ef95b700bcd400f7b44be3650778806be`.

| Phép đo | Windows | Linux container |
| --- | ---: | ---: |
| Nạp dictionary | 0,06390 s | 0,02688 s |
| Lemma 1.000 câu | 0,07197 s | 0,08051 s |
| Furigana 1.000 câu | 0,11055 s | 0,11104 s |
| Tổng NLP 1.000 câu | **0,18252 s** | **0,19155 s** |
| RSS API | **174.804.992 byte (166,71 MiB)** | **183.033.856 byte (174,55 MiB)** |

RSS đo PID uvicorn thực, một worker, đã nạp core và xử lý một request search 緊張
HTTP 200 qua loopback. Cả hai snapshot dưới 512 MB (NFR-03 local); không phải phép đo
peak RAM hoặc bằng chứng trên hosting deploy. Probe tạm đã đóng sau đo.

Ước lượng NFR-02: nếu một dòng import có một câu tương tự, phần lemma + furigana
của 1.000 dòng khoảng **0,192 s**, còn nhiều ngân sách trong mốc30 s. **Chưa xác nhận
toàn bộ import/matching 1.000 dòng <30 s**; phép đo này chỉ cô lập thành phần NLP.
Không chạy import hay sửa dữ liệu nguồn để tạo mẫu đo.

JSON: `verification/m1-resources.json` (Windows),
`verification/linux/m1-resources.json` (Linux); log `m1-measure.log`,
`m1-linux-measure.log`. Script: `uv run python -m scripts.measure_m1`.

### Mẫu đối chiếu MANUAL và điểm dừng

**MANUAL**: `apps/backend/verification/m1_nlp_sample.md`, 30 câu thật, seed20261020.
Mỗi câu có entry/order_no/textbook, câu gốc, add_furigana(original), bản sinh lại
sau bỏ markup, và lemma. Nguồn vẫn có lỗi OCR (ví dụ 協カ), nên kết quả đọc tự động
cần người dùng đối chiếu bằng mắt; không sửa bản gốc hoặc âm đọc theo mẫu.

Milestone 1 hoàn tất, commit `feat(nlp): sudachi tokenizer, furigana, entry lemmas`.
Dừng tại đây. **Chưa làm Milestone 2** (search lemma/appears_in_examples), chưa tự áp
furigana ở Milestone 4, IMP-11 vẫn hoãn, NB-06 xuất Anki giữ ở Milestone 3.

## Milestone 2 — SRCH-09/10

### Bước 0: sửa lemma

- Backup trước backfill: `backups/milestone2/vocab-20261026-210303.dump`.
- Loại trợ động từ theo POS/ngữ cảnh; giữ động từ độc lập và する. Thêm normalized_form
  và hiragana của dictionary_form; giữ text[] + GIN, giữ danh từ hình thức trong dữ liệu.
- Quét 11.906 entry, dry-run 11.522 thay đổi; ghi 11.522; chạy lần hai 0.
- Hash content/search_text trước/sau: `9a396627773143b7e8a2f63ea4a5ff4e553b3ec4ba3a72394f7125e7c38067b1`.
  Script M2 dùng JSON sort_keys với id/content/search_text nên không so trực tiếp digest M1.
- Mẫu MANUAL cùng seed/thứ tự 30 câu M1: `apps/backend/verification/m2_lemma_sample.md`.
- Bằng chứng: `verification/m2-content-{before,after}.json`, `m2-backfill-{dry,first,second}.log`.
- SRCH-08/lịch sử và chức năng saved sang M3 (notebook); giữ field saved=false cũ.
  IMP-11 vẫn hoãn. Không thực hiện Milestone 3/4.

### Ghi chú dành cho Milestone 4 — chưa thực hiện

- Thêm furigana bên trong `{{ }}` nhưng giữ ngoặc: `{{協力}}` → `{{協力[きょうりょく]}}`.
- Cách đọc từ đích lấy từ `kana` của entry; ưu tiên từ chuẩn JMdict/entry khi token trùng
  từ đầu mục, ví dụ `腹痛` Mimikara phải là `ふくつう`.
- Override `私` → `わたし`; `金` cạnh `を取る` / `お金` cần `かね`, xem xét ngữ cảnh
  Sudachi hoặc cho người dùng sửa. Không thay đổi furigana trong milestone này.

### Triển khai SRCH-09/10

- Search thêm nguồn ứng viên lemma (`kanji` hoặc `kana_norm`), hạng exact → lemma →
  prefix → meaning và tie-break ID. Giữ nguyên truy vấn exact, bộ lọc/quyền, tổng capped,
  phân trang SQL và các field cũ; thêm `matched_by` trên từng item.
- `appears_in_examples={count,capped}` chỉ cho top 10 toàn cục, phần sau và danh từ
  hình thức trả null. Dùng containment GIN, loại entry cùng word_id và kiểm tra quyền
  trước LIMIT 1001; gom count của trang thành một lần SQL.
- Endpoint `GET /api/v1/words/{id}/examples?page=&size=` trả câu của example/usage,
  lọc lemma từng trường câu, giữ markup/bản dịch; có giáo trình, bài, order_no,
  entry_id, source_word và ocr_review_required. Thứ tự ổn định theo giáo trình/bài/
  order_no/id rồi vị trí block/câu. Không sinh furigana.
- Count là số entry có lemma (có thể từ collocation), total endpoint là số trường câu
  example/usage khớp nên hai số có thể khác nhau. Danh từ hình thức vẫn mở được ví dụ.

### Bổ sung kiểm chứng ngữ cảnh trợ từ

- Bộ lọc dùng POS `助詞/接続助詞` cho `て/で`; `で` chỉ cách thức/địa điểm
  (`格助詞`) không làm mất động từ độc lập: `服で来てください` vẫn có `来る`.
- Lượt đối chiếu bổ sung: dry-run 65, ghi 65 entry, chạy tiếp 0; hash content/search_text
  vẫn là `9a396627773143b7e8a2f63ea4a5ff4e553b3ec4ba3a72394f7125e7c38067b1`.
  Bằng chứng: `verification/m2-refined-backfill-{dry,first,second}.log`. Mẫu 30 câu đã xuất lại.

### Kiểm chứng cuối Milestone 2

- **128/128 test PASS**, gồm toàn bộ 105 test M1 và 23 test bổ sung. Coverage service/NLP tổng **96.65%**; từng service và NLP ≥70% (check_coverage đạt).
- Coverage từng service: auth 95,2%, dictionary 97,8%, imports 97,2%, search 98,0%, textbooks 92,9%; NLP 99,4%.
- Ruff check + format theo phạm vi CI đạt (106 file); git diff --check đạt. Không hạ ngưỡng hoặc loại test cũ.
- Log/XML: `verification/m2-tests.{log,xml}`, `m2-coverage.log`, `m2-ruff.log`, `m2-format.log`.
- RSS uvicorn Windows sau nạp Sudachi và search có count M2: **176,345,088 byte (168.18 MiB)**; M1 **166,71 MiB**. Một worker, PID thực, HTTP 200; snapshot local dưới 512 MB, không phải peak/deploy. `verification/m2/resources.json` và `m2-resources.log`.
- Backup custom-format **4.214.208 byte**, pg_restore đọc catalog thành công; `verification/m2-backup-toc.log`.

### Benchmark HTTP trước/sau M2

PostgreSQL 16 Testcontainers riêng cho từng lượt; baseline orchestration tại `c4686d6`, không dùng DB PDF local. Synthetic 200.000 words/400.000 senses, JMdict 323.447 words/721.391 senses (cùng bản English đầy đủ/SHA-256 đã ghi ở M1). **Mỗi dataset có 12.000 entry**, lemma tính thật bằng tokenizer. c=1: 20 request/query; c=10: 100 request/query, 10 đợt; size=20/page=1, nearest-rank p95, không loại lỗi. ASGI chỉ để so sánh; chưa xác nhận HTTP deploy.

Sau COPY, dọn pending list của riêng `ix_entries_lemmas` trước ANALYZE/timing bằng `gin_clean_pending_list`; đây là bảo trì index bulk-load, không ép planner. Baseline không đọc index lemma. Lượt thăm dò trước bảo trì được giữ ở `m2-probe-j{1,10}.json`; đã đo lại toàn bộ số sau để loại ảnh hưởng thời điểm autovacuum.

**Synthetic — p95 (ms)**

| Query | c=1 trước | c=1 sau | c=10 trước | c=10 sau |
| --- | ---: | ---: | ---: | ---: |
| きんちょう | 102.96 | 104.95 | 351.75 | 455.63 |
| kinchou | 97.25 | 97.18 | 307.59 | 317.36 |
| 緊張 | 94.83 | 103.27 | 363.37 | 384.23 |
| căng thẳng | 73.16 | 74.20 | 334.35 | 343.99 |
| school | 109.75 | 128.14 | 354.59 | 429.12 |
| い | 172.39 | 192.85 | 511.29 | 557.06 |
| a | 33.46 | 34.17 | 282.70 | 272.66 |
| 行かなかった | 96.95 | 107.01 | 311.18 | 387.26 |
| 緊張して | 34.23 | 95.47 | 303.37 | 388.53 |
| /words/{id}/examples | — | 38.87 | — | 451.30 |

- Synthetic c=1: EXPLAIN count dùng **ix_entries_lemmas**; pending pages dọn trước đo: 177.

- Synthetic c=10: EXPLAIN count dùng **ix_entries_lemmas**; pending pages dọn trước đo: 177.

**JMdict — p95 (ms)**

| Query | c=1 trước | c=1 sau | c=10 trước | c=10 sau |
| --- | ---: | ---: | ---: | ---: |
| きんちょう | 97.03 | 130.76 | 432.30 | 497.53 |
| kinchou | 115.74 | 113.99 | 316.31 | 446.42 |
| 緊張 | 173.05 | 163.79 | 378.88 | 431.59 |
| căng thẳng | 93.97 | 75.89 | 333.14 | 708.47 |
| school | 131.90 | 131.98 | 356.70 | 485.93 |
| い | 203.16 | 195.37 | 726.49 | 532.81 |
| a | 102.20 | 109.33 | 330.63 | 461.54 |
| 行かなかった | 92.17 | 110.48 | 370.00 | 493.22 |
| 緊張して | 95.72 | 101.21 | 427.00 | 460.82 |
| /words/{id}/examples | — | 36.23 | — | 440.39 |

- JMdict c=1: EXPLAIN count dùng **ix_entries_lemmas**; pending pages dọn trước đo: 177.

- JMdict c=10: EXPLAIN count dùng **ix_entries_lemmas**; pending pages dọn trước đo: 177.

- Sau M2: **2,400/2,400 HTTP 200**. **Có truy vấn vượt mốc NFR so sánh; xem bảng, không kết luận đạt toàn bộ ngưỡng.**
- JSON/log đầy đủ: `verification/m2-{before,after}-{s1,s10,j1,j10}.{json,log}`; JSON chứa sample/status/total/capped/SQL timings, EXPLAIN SQL chậm nhất và EXPLAIN count. Endpoint examples chưa tồn tại trước M2 nên không có số baseline.

JSON baseline giữ ref e77544b khi đo; hai file service dictionary/search có cùng byte tại c4686d6, dùng ref này để tái chạy.

Tái chạy (từ apps/backend):

```powershell
uv run pytest --cov --cov-report=term-missing --cov-report=json
uv run python scripts/check_coverage.py coverage.json
uv run ruff check . ../../scripts
uv run ruff format --check . ../../scripts
uv run python -m scripts.bench_search --output verification/m2-after-s1.json
uv run python -m scripts.bench_search --concurrency 10 --iterations 100 --output verification/m2-after-s10.json
uv run python -m scripts.bench_search --jmdict data/bench/jmdict-eng-3.6.2.json --output verification/m2-after-j1.json
uv run python -m scripts.bench_search --jmdict data/bench/jmdict-eng-3.6.2.json --concurrency 10 --iterations 100 --output verification/m2-after-j10.json
uv run python -m scripts.measure_m2
```

Thêm `--baseline-ref c4686d6` để đo search trước M2 với cùng loader. Backup và verification là artifact local được Git bỏ qua.

**Triển khai và kiểm chứng phạm vi Milestone 2 hoàn tất; ngưỡng NFR chưa đạt ổn định cho mọi truy vấn. Dừng tại Milestone 2**; SRCH-08/saved ở M3, IMP-11 vẫn hoãn; ghi chú M4 chưa triển khai.

### Đo lặp truy vấn sát/vượt ngưỡng

- Đo riêng `căng thẳng` trên JMdict, c=10, 100 request trong database tạm mới:
  p95 **558,38 ms**, 100/100 HTTP 200; endpoint examples đi kèm **301,77 ms**,
  100/100 HTTP 200. Bằng chứng: `verification/m2-vi-repeat-j10.{json,log}`.
- Giữ nguyên **708,47 ms** của lượt đầy đủ trong bảng; không thay bằng số đo lặp.
  Dữ liệu cho thấy biến thiên local, chưa đủ kết luận NFR ổn định. Triển khai SRCH-09/10
  đã hoàn tất và dừng ở M2; chưa xác nhận NFR trên HTTP môi trường deploy.

## Milestone 3 — Sổ từ (đang triển khai)

### Bước 0: lemma và contract ví dụ

- Backup trước migration/backfill: `backups/milestone3/vocab-20261026-224828.dump`.
- Lọc cấu trúc cấm/nghĩa vụ bằng POS và chuỗi token (không regex câu thô).
  normalized_form chỉ được thêm khi reading bằng dictionary_form; giữ tiềm năng độc lập `行ける`.
- Migration `0004_example_lemmas` thêm mảng riêng text[] + GIN chỉ từ example/usage,
  có downgrade; save_entry/backfill tính cả hai mảng, không sửa content/search_text.
- Quét 11.906 entry, dry-run/ghi 11.528; lần hai0. Hash nguồn trước/sau giữ nguyên
  `9a396627773143b7e8a2f63ea4a5ff4e553b3ec4ba3a72394f7125e7c38067b1`.
- `verification/m3_lemma_diff.md`: 10/30 câu trong mẫu M2 thay đổi; nguồn không đổi.
- Examples trả theo entry với sentences[]; count search và total dùng cùng example_lemmas,
  quyền và loại entry của chính từ. Giữ cap1000 + cờ total_capped, phân trang vẫn tiếp tục.
- IMP-11 vẫn hoãn; không làm M4; không tối ưu/đo thêm tải10 đồng thời.
