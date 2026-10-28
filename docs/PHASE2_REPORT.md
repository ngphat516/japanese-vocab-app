# Giai đoạn 2 — báo cáo kiểm chứng

## Tổng kết Phase 2

Phạm vi backend P1 đã triển khai đến M6; **IMP-11 hoãn theo yêu cầu**. Không triển khai P2/frontend. Kết quả local không thay thế kiểm chứng môi trường deploy. Chi tiết và số đo lịch sử M0–M5 được giữ nguyên bên dưới.

| Mã P1 | Trạng thái | Test chứng minh (apps/backend/tests) | Milestone |
| --- | --- | --- | --- |
| DICT-08 | done | test_m4_api.test_admin_word_patch_audit_and_kanji_visibility; test_m5_hanviet.test_patch_kanji_source_recomputes_except_manual_words | M4/M5/M6 |
| DICT-09 | done | test_m4_api.test_admin_word_patch_audit_and_kanji_visibility | M4 |
| TB-06 | done | test_m4_api.test_manual_entry_crud_visibility_validation_conflicts | M4 |
| TB-07 | done | test_m4_furigana (5 case); test_m5_hanviet.test_public_headword_reading_fallback_without_global_override | M4/M5 |
| TB-08 | done | test_m4_seeds.test_jlpt_admin_idempotent_source_only | M4 |
| SRCH-08 | done | test_notebook.test_m3_history_limit_upsert_and_user_isolation | M3 |
| SRCH-09 | done | test_search_m2.test_SRCH_09_inflection; test_SRCH_09_rank_exact_lemma_prefix_meaning | M2/M3 |
| SRCH-10 | done | test_search_m2.test_SRCH_10_visibility_sentence_filter_markup_ocr_and_pagination; test_m3_collocation_not_counted_and_entry_total_matches | M2/M3 |
| IMP-10 | done | test_m5_worker: async flow/two workers, rollback, timeout và retries | M5 |
| IMP-11 | hoãn | Không triển khai/test adapter Anki import; NB-06 xuất Anki vẫn done | — |
| IMP-12 | done | test_m6_free_text: grouping/token spans, sync/exclude/permissions, TXT/limits, async full flow | M6 |
| NB-01 | done | test_notebook.test_m3_history_limit_upsert_and_user_isolation | M3 |
| NB-02 | done | test_notebook.test_m3_history_saved_collection_flow; test_m3_tag_and_note_validation | M3 |
| NB-03 | done | test_notebook.test_m3_filters_stats_pagination_and_one_saved_query | M3 |
| NB-04 | done (backend) | test_notebook filters/stats trả cấp JLPT/null; màu và badge thuộc frontend ngoài phạm vi | M3 |
| NB-05 | done | test_notebook.test_m3_history_saved_collection_flow; test_m3_collection_conflicts_and_empty_stats | M3 |
| NB-06 | done | test_notebook_exports.test_m3_export_full_flow_and_round_trip; test_m4_exports | M3/M4 |

| NFR | Bằng chứng/số đo local | Điều kiện / việc chưa xác nhận |
| --- | --- | --- |
| NFR-01 | M3 search c=1 p95 tối đa194,11ms synthetic /188,51ms JMdict; M2 c=10 có lượt708,47ms | Ngưỡng <300ms tuần tự, <600ms c=10 trên HTTP deploy; chưa đạt ổn định mọi query, M6 không đo c=10 |
| NFR-02 | M5 CSV1.000 dòng: review9,749s + commit12,077s =21,827s; M6 free_text20.000 ký tự: max8,937s đến review | HTTP loopback + worker thật, không phải deploy; CSV đã xác nhận1.000 entry |
| NFR-03 | M5 API170,86MiB, worker210,14MiB, tổng381,00MiB | Không gồm DB/OS/proxy; free tier512MB dùng sync/API, cần đo lại trên deploy |
| NFR-04 | Auth tests: Argon2, JWT/rotation/expiry | Secret thật lấy env, không đưa credential lên Git |
| NFR-05 | Tests owner/visibility/private/thu hồi quyền ở dictionary/import/notebook | Không thay bằng kiểm tra frontend |
| NFR-06 | test_operations: search60/phút, auth/import10/phút | Test bật rate limit; benchmark tắt riêng process đo |
| NFR-07 | Test CORS và error envelope, không trả stack trace | Domain deploy cần cấu hình env thực tế |
| NFR-08 | Migration upgrade/downgrade/upgrade PostgreSQL tạm; DB local chỉ upgrade sau backup | Không downgrade DB thật |
| NFR-09 | Backup custom-format mỗi milestone, catalog pg_restore đọc được | Chưa thiết lập/kiểm chứng lịch backup tự động hằng ngày trên deploy |
| NFR-10 | Full suite/coverage/Ruff và ngưỡng70% từng service/NLP/job/worker, xem M6 | GitHub CI mới chỉ chạy sau push |
| NFR-11 | Health200, request log JSON có request id trong probe HTTP M5/M6 | Chưa cấu hình quan sát trên deploy |
| NFR-12 | Settings từ env, .env.example và Compose | Không track .env/credential local |
| NFR-13 | FastAPI OpenAPI tự sinh, README chạy local | Chưa kiểm chứng Swagger trên URL deploy |
| NFR-14 | Nguồn/license JMdict/OpenJLPT/Unihan tại data/README; dữ liệu OCR private/local | Giữ attribution khi phân phối; không push dữ liệu sách |
| NFR-15 | test_NFR_15_search_gzip_and_payload_budget đạt (fixture) | Không khẳng định mọi trang dữ liệu thật đều <200KB |
| NFR-16 | Adapter CSV/Mimikara/JSON/free_text dùng chung staging; block raw bảo toàn nguồn | Block không biết phải được adapter map raw trước validation |
| NFR-17 | M3 xuất1.000 từ: max Anki1,167s / CSV0,894s / Markdown0,930s | ASGI local, chưa gồm mạng/proxy deploy |

Việc còn mở:

- Duyệt Hán Việt lô2+; âm chưa duyệt có thể lẫn Nôm, chữ thiếu và đa âm vẫn cần sửa; file review local ở mục M6.
- OCR nguồn còn lỗi (ví dụ 協カ), không tự sửa nguyên bản hoặc bịa nghĩa/cách đọc.
- Kiểm chứng NFR/peak RAM, vận hành backup hằng ngày và cấu hình free tier trên deploy.
- IMP-11 import Anki tiếp tục hoãn; frontend/P2 không thuộc Phase 2 backend này.

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
Milestone 1 NLP, Milestone 2 search lemma/ví dụ, Milestone 3 Sổ từ, Milestone 4
furigana/dictionary/mục từ thủ công, Milestone 5 Hán Việt/worker import và Milestone 6
free_text/Hán Việt lô1 đã hoàn tất. Kết quả ở từng mục bên dưới; dừng sau M6.

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

## Milestone 3 — Sổ từ

### Bước 0: lemma và contract ví dụ

- Backup trước migration/backfill: `backups/milestone3/vocab-20261026-224828.dump`.
- Lọc cấu trúc cấm/nghĩa vụ bằng POS và chuỗi token (không regex câu thô).
  normalized_form chỉ được thêm khi reading bằng dictionary_form; giữ tiềm năng độc lập `行ける`.
- Migration `0004_example_lemmas` thêm mảng riêng text[] + GIN chỉ từ example/usage,
  có downgrade; save_entry/backfill tính cả hai mảng, không sửa content/search_text.
- Quét 11.906 entry, dry-run/ghi 11.528; lần hai 0. Hash nguồn trước/sau giữ nguyên
  `9a396627773143b7e8a2f63ea4a5ff4e553b3ec4ba3a72394f7125e7c38067b1`.
- `verification/m3_lemma_diff.md`: 10/30 câu trong mẫu M2 thay đổi; nguồn không đổi.
- Examples trả theo entry với sentences[]; count search và total dùng cùng example_lemmas,
  quyền và loại entry của chính từ. Giữ cap 1000 + cờ total_capped, phân trang vẫn tiếp tục.
- IMP-11 vẫn hoãn; không làm M4; không tối ưu/đo thêm tải 10 đồng thời.

### Schema và chức năng Sổ từ

- Migration `0005_notebook`: history unique user/word + index thời gian giảm dần;
  saved_words unique user/word + index created_at; collections unique user/name;
  membership PK hai cột, các FK cascade.
- GET chi tiết từ upsert lịch sử, khóa transaction theo user rồi prune còn 500 dòng;
  /search không ghi lịch sử. saved lấy bằng một truy vấn cho cả trang.
- APIs history/saved/stats/collections/membership có kiểm tra owner, visibility hiện tại,
  nguồn public/own; filter JLPT/none, tag, textbook, collection và phân trang ổn định.
- Tags NFKC/trim/khử trùng, tối đa 20 tag/30 ký tự; stats đủ 6 nhóm kể cả 0.

- Kiểm chứng lõi: **160 test đạt**, coverage tổng 96,38%, notebook service 100%; từng service/NLP ≥70%.
  Có test giữ 500 dòng/upsert, một truy vấn saved/trang, thu hồi quyền nguồn, toàn bộ endpoint
  bắt buộc auth, migration 0005/0004 downgrade→upgrade. Log `verification/m3-core-full-tests.log`,
  XML `m3-core-tests.xml`, coverage `m3-core-coverage.log`. Schema 0005 đã áp DB local sau backup.

### NB-06 — xuất dữ liệu

- Genanki 0.13.1 khóa trong uv.lock; model 2047426001/deck 2047426002 cố định, GUID theo user/word_id. Bảy field đúng contract; JLPT và tag gốc nằm trong Notes, tag Anki dùng underscore thay whitespace. Mặt trước Expression; ví dụ dùng `{{furigana:Examples}}` để hiển thị reading có sẵn. Giữ `漢字[よみ]`, đổi từ đích `{{…}}` thành `<u>…</u>`, không media và không sinh furigana.
- CSV UTF-8 BOM, 9 cột cố định, nhiều ví dụ nối ` / `. ZIP Markdown mỗi từ một file, frontmatter đủ word/reading/jlpt/hanviet/tags/sources; tên Windows an toàn, thêm ID tránh trùng cả cùng reading. Header filename* UTF-8 RFC5987 và rate limit 10/phút/user.
- Nghĩa ưu tiên meaning.vi trong giáo trình của user; fallback gloss có nhãn JMdict/ngôn ngữ, hoặc nguồn hiện có cho từ tự tạo không có gloss. Tối đa 2 ví dụ từ example/usage của entry từ đích; lọc collection/JLPT/tag và kiểm tra quyền nguồn hiện tại.

### Kiểm chứng cuối Milestone 3

- **170/170 test PASS**, gồm toàn bộ 128 test M2 (kỳ vọng normalized forms/contract examples cập nhật theo Bước 0) và 42 case mới. Coverage service/NLP/export **97.23%**; từng service/NLP/export đều ≥70%.
- Notebook service 100%; export và các service khác xem `verification/m3-coverage.log`. Cổng coverage bắt buộc notebook và exports.py; không hạ ngưỡng. Ruff check/format theo phạm vi CI đạt (114 file), uv sync --frozen đạt, git diff --check đạt.
- Test mở lại APKG bằng zipfile+sqlite3 và kiểm tra cả note/card/model/deck; CSV BOM/headers; ZIP parse YAML/frontmatter, tên thiết bị Windows, hai từ cùng reading. Có kiểm tra file rỗng, source visibility, user B, collection filter, notes/tags, GUID sau sửa note và rate limit theo user.
- Test migration upgrade→downgrade→upgrade dùng DB tạm; DB local chỉ upgrade sau backup. Số đếm ví dụ và total endpoint cùng cap 1000/capped, có test mốc 1000/1001 và loại collocation.
- Log/XML: `verification/m3-tests.{log,xml}`, `m3-coverage.log`, `m3-ruff.log`, `m3-format.log`, `m3-sync.log`, `m3-count-cap-test.log`.
- Backup trước thay đổi M3: `backups/milestone3/vocab-20261026-224828.dump`, **4.375.074 byte**, catalog pg_restore đọc được (`verification/m3-backup-toc.log`).
- Hash content/search_text giữ nguyên cả trước/sau backfill và sau kiểm chứng: `9a396627773143b7e8a2f63ea4a5ff4e553b3ec4ba3a72394f7125e7c38067b1`; `verification/m3-content-{before,after,final}.json`.

### NFR-17 — xuất 1.000 từ thật

Mỗi định dạng 3 lượt ASGI HTTP, gồm auth+SQL+NLP+render; warmup bằng file 10 từ không tính. Dataset 1.000 từ thật từ giáo trình local user được xem. Đã mở lại cả 9 file kết quả để xác nhận đủ 1.000 note/card/row/file. Toàn bộ saved_words/collections tạm rollback, số dòng trước/sau bằng nhau: `[0, 0]`.

| Định dạng | Median (s) | Max (s) | Kích thước (byte) |
| --- | ---: | ---: | ---: |
| Anki .apkg | 1.114 | 1.167 | 1,138,906 |
| CSV BOM | 0.894 | 0.894 | 736,391 |
| Markdown .zip | 0.924 | 0.930 | 478,403 |

**Cả 3 định dạng đạt <10 giây trong phép đo local này.** Số đo không gồm mạng/proxy deploy. JSON: `verification/m3/resources.json`; log: `verification/m3-export-measure.log`. Script: `uv run python -m scripts.measure_m3_exports`.

### Search c=1 trước/sau saved

Đo cặp trên cùng DB/process, baseline search service `fa3a07b` (sau Bước 0, trước notebook), thứ tự trước/sau xen kẽ từng cặp. Mỗi query 20 cặp, size=20/page=1; 1.000 saved_words. Cả synthetic 200.000 words/400.000 senses và JMdict 323.447 words/721.391 senses đều có 12.000 entry với lemma thật. Warmup 1 request/query và examples ghi riêng, không tính. Không đo/tối ưu c=10 trong M3.

| Query | Synthetic trước | Sau | Δ p95 (ms) | JMdict trước | Sau | Δ p95 (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| きんちょう | 84.31 | 84.36 | +0.05 | 89.50 | 84.51 | -4.99 |
| kinchou | 71.15 | 74.65 | +3.50 | 111.07 | 112.63 | +1.55 |
| 緊張 | 95.23 | 80.45 | -14.78 | 161.36 | 147.21 | -14.15 |
| căng thẳng | 56.63 | 55.97 | -0.66 | 71.66 | 75.48 | +3.82 |
| school | 36.19 | 38.75 | +2.57 | 136.12 | 145.89 | +9.77 |
| い | 181.53 | 194.11 | +12.57 | 197.91 | 188.51 | -9.39 |
| a | 17.05 | 19.71 | +2.66 | 88.02 | 83.15 | -4.87 |

- **560/560 HTTP 200**, total kết quả trước/sau giống nhau cho mỗi cặp. Tăng p95 tối đa **12.57 ms synthetic**, **9.77 ms JMdict**; cả 14 trường hợp dưới 20 ms. Giá trị âm là biến thiên đo local, không kết luận tăng tốc.
- JSON/log: `verification/m3-search-{s1,j1}.{json,log}`, warmup có đuôi `.warmup.json`. Script `scripts/bench_saved.py`; ASGI chỉ so sánh overhead, NFR-01 vẫn phải đo HTTP môi trường deploy theo DECISIONS 33.

### RSS và file mẫu

- RSS PID uvicorn Windows thật, một worker, đã nạp Sudachi và xử lý search có saved: **177,709,056 byte (169.48 MiB)**. M2 **168,18 MiB**; snapshot M3 dưới 512 MB, không phải peak export/deploy. Probe đã đóng; JSON `verification/m3/resources.json`.
- Ba file mẫu **10 từ thật**, đã mở kiểm tra, nằm local trong `apps/backend/verification/m3_exports/`:
  - `m3-sample-10.apkg` — import bằng Anki.
  - `m3-sample-10.csv` — mở bằng Excel (UTF-8 BOM).
  - `m3-sample-10.zip` — giải nén vào vault Obsidian.
- Sample gồm 動かす/動く/薄い/写す… từ DB thật; giữ lỗi OCR và markup nguồn, không tạo/sửa nội dung giáo trình. `verification/m3_lemma_diff.md` chỉ có 10/30 câu đổi lemma từ mẫu M2. Backup/verification được Git-ignore; không push dữ liệu sách lên GitHub.

### Tái chạy và điểm dừng

```powershell
uv sync --frozen
uv run pytest --cov --cov-report=term-missing --cov-report=json
uv run python scripts/check_coverage.py coverage.json
uv run ruff check . ../../scripts
uv run ruff format --check . ../../scripts
uv run python -m scripts.bench_saved --output verification/m3-search-s1.json
uv run python -m scripts.bench_saved --jmdict data/bench/jmdict-eng-3.6.2.json --output verification/m3-search-j1.json
uv run python -m scripts.measure_m3_exports
```

Ba commit theo phạm vi: `fa3a07b` sửa NLP/count, `5d4011c` history/saved/collections, và `feat(notebook): export anki csv markdown`.

**Milestone 3 hoàn tất; dừng sau Milestone 3.** IMP-11 vẫn hoãn; không triển khai furigana tự động M4, SRS hay frontend. Không thay kết luận NFR deploy bằng kết quả ASGI local.

## Milestone 4 — TB-06/07/08, DICT-08/09 và nguồn Hán Việt

Ngày 27/10/2026. Bắt đầu từ `main` sau merge M3 (`0a082fc`), xóa nhánh M3 local đã
merge, tạo nhánh `milestone-4-furigana`. Không làm M5/M6, không đo tải10 đồng thời;
IMP-11 vẫn hoãn. DECISIONS60–68 ghi các thay đổi và quyền bootstrap admin riêng.

### Triển khai và tương thích

- Export tự render `漢字[よみ]` thành HTML ruby sau escape, gạch chân chứa ruby;
  Anki bỏ filter furigana, mặt sau dùng Reading cho Expression. Giữ model/deck ID,
  GUID và7 field cũ. Markdown dùng cùng ruby; frontmatter text thuần.
- CSV vẫn UTF-8 BOM, thêm cột MeaningSource, ví dụ text thuần, JLPT null để trống.
  Nghĩa ưu tiên meaning.vi, tối đa3 gloss phân biệt, nguồn nghĩa ghi một lần.
- TB-07: migration0006 thêm content_furigana JSONB nullable và auto_furigana defaulttrue.
  Sinh reading bên trong {{}}; giữ annotation có sẵn, override 私→わたし và 腹痛→ふくつう
  theo mẫu đã duyệt. Ưu tiên kana của entry rồi headword cùng sách trước override/Sudachi;
  homograph không duy nhất không được chọn tùy tiện. 金 dùng Sudachi; sửa tay qua TB-06.
  Import tạo/match đầy đủ từ trong batch trước khi tính furigana để không phụ thuộc thứ tự dòng.
- API entry/list/search/detail mặc định trả bản dẫn xuất, `?furigana=false` trả nguồn.
  Export và endpoint examples dùng bản dẫn xuất. Tắt bằng auto_furigana trong JSON tạo/PATCH
  entry, hoặc `POST /imports/{id}/commit?auto_furigana=false`. Các block meaning/raw/note
  và bản dịch không được tự gắn cách đọc.
- DICT-08: admin PATCH hanviet, khóa Word để ghi lịch sử old/new chính xác; không tạo audit
  khi giá trị không đổi. Migration0007 tạo word_edits. DICT-09 trả metadata Hán tự và danh
  sách từ phân trang id, chỉ từ JMdict hoặc entry public/own; ký tự sai422, chưa có404.
- TB-06: POST lesson entries, PATCH/DELETE entry chỉ chủ sách. word_id phải có quyền xem;
  kanji/kana match/tạo như import. Validate block/16.000 byte; trùng word/lesson409.
  Migration0008 thêm version; PATCH bắt buộc ifMatch, khóa row rồi kiểm tra, stale409.
  Mỗi lần save tính lại search_text/lemmas/example_lemmas/content_furigana và tăng version.
  Cả ba migration có downgrade; chỉ thử downgrade trên DB tạm.

### Backup, backfill và bảo toàn nguồn

| Thời điểm | Backup (tương đối root repo) | Byte |
| --- | --- | ---: |
| Trước migration/backfill | `backups/milestone4/vocab-20261027-001411.dump` | 4.486.441 |
| Trước bootstrap admin/seed JLPT | `backups/milestone4/vocab-20261027-002613.dump` | 4.980.529 |

Cả hai là custom format; pg_restore đọc catalog thành công (`m4-backup-toc.log`,
`m4-preseed-backup-toc.log`). Không downgrade DB thật.

- Backfill đầu: quét11.906, dry-run11.906 thay đổi, ghi11.906, chạy lần hai0.
- Sau bổ sung override 腹痛: dry-run1, ghi1, chạy tiếp0; nguồn không đổi.
- Sau thêm7.811 entry JLPT: dry-run toàn bộ19.717 entry trả **0 thay đổi**.
- Hash content + search_text của11.906 entry gốc trước/sau backfill và sau seed vẫn là
  `9a396627773143b7e8a2f63ea4a5ff4e553b3ec4ba3a72394f7125e7c38067b1`.
  Sau seed chỉ đối chiếu tập sách gốc1–4; không so hash toàn bảng đã có thêm entry hợp lệ.
- Bằng chứng: `verification/m4-content-{before,after,final}.json`, `m4-db-final.json`,
  `m4-backfill-{dry,first,second}.log`, `m4-refined-backfill-{dry,first,second}.log`,
  `m4-backfill-postseed-dry.log` và `m4-migration.log`.

### JLPT public và tài khoản admin

Theo xác nhận trực tiếp của người dùng, tạo tài khoản admin **riêng** qua CLI
`scripts/create_admin.py`; mật khẩu ngẫu nhiên chỉ lưu dưới key admin trong
`apps/backend/data/pdf_imports/access.json`, cạnh tài khoản cũ, không in log/commit.
user_id=1 giữ role=user; admin mới user_id=2. Backup trước khi tạo/seed như bảng trên.

Nguồn [OpenJLPT](https://github.com/evanclan/OpenJLPT), commit
`0d1d3410bec90bd4098a7c72de820543cb4f707c`, CC BY-SA4.0; giữ CSV/NOTICE/LICENSE local.
Ghi công OpenJLPT, JMdict/EDRDG và Jonathan Waller theo NOTICE. Chỉ dùng nghĩa English
có trong CSV, không tự dịch Việt hoặc nhập câu Tatoeba. Lesson nhóm50 dòng theo thứ tự.

| Sách | Entry | Lesson | SHA-256 CSV |
| --- | ---: | ---: | --- |
| JLPT N5 | 674 | 14 | `ea82df093658fa35f24fd53073ce9a0a07765f50314bce04debf45b278ebfcd3` |
| JLPT N4 | 630 | 13 | `2e8fe87d271afec8626a4083b268dd9289b5a4be0f5e243a630710ef84d27916` |
| JLPT N3 | 1.659 | 34 | `46ba72fbc08c193f207648e4eea9a7879afb3b2638d74c4f5edd773c867892ba` |
| JLPT N2 | 1.778 | 36 | `898840fe7f7c5c9e8975a0738380a1b86d762d038403b724dc2ece09d737fd30` |
| JLPT N1 | 3.070 | 62 | `6eff6ba068a3951c29f9296a50016dee6c39060d43a13ad33a1e136f2928d35b` |

Tổng **5 sách public, 7.811 entry, 159 lesson**. Lượt hai vẫn cùng ID/số lượng, không
thêm trùng. `verification/m4-jlpt-{first,second}.log`, `m4-admin-bootstrap.log`,
`m4-db-final.json`. Test dùng CSV tự biên soạn trong tmp, không tải mạng.

### Hán Việt — CSV và mẫu, CHƯA seed DB

Nguồn [Unihan17.0.0](https://www.unicode.org/Public/17.0.0/ucd/Unihan.zip), header
Unihan_Readings.txt ghi17.0.0. SHA-256 TXT:
`575e69c9ad85a4737a889a4f94cbd987042a90a1a6cc16dd3f4ed995c715b17c`.
Unicode License V3 (`Unicode-3.0`), nguồn/license/notice tại `data/README.md` và
`data/unihan/LICENSE.txt`; giữ cùng dữ liệu khi chia sẻ.

- `data/hanviet.csv`: **8.306 chữ**, chỉ trường kVietnamese, NFC/viết hoa, nhiều âm nối|;
  **138 chữ** có nhiều âm trong toàn dataset. Có thể lẫn âm Nôm, cần người dùng duyệt.
- Trước JLPT: **840/1.129 chữ =74,40%**, 15 chữ local nhiều âm.
- Sau seed JLPT, toàn bộ sách local: **1.353/2.004 chữ =67,51%**, **32 chữ** local nhiều âm.
  Đếm chữ phân biệt trong words có entry; không tính tần suất xuất hiện.
- Mẫu MANUAL30 chữ seed20261020: `apps/backend/verification/m4_hanviet_sample.md`,
  gồm cả chữ thiếu reading. Metadata: `data/hanviet.metadata.json`, log
  `verification/m4-hanviet{,-final}.log`. CSV nguồn và mẫu không push lên GitHub.
- **Chưa chạy seed_hanviet trên DB thật.** Chờ người dùng duyệt mẫu; không tự thay âm từ chuẩn.

### Mẫu furigana và export

- `apps/backend/verification/m4_furigana_sample.md`: cùng30 câu, seed20261020 và thứ tự M1/M2,
  cột gốc/có furigana. Không sửa OCR, kể cả 協カ; reading cần đối chiếu bằng mắt.
- `apps/backend/verification/m4_exports/m4-sample-10.apkg`
- `apps/backend/verification/m4_exports/m4-sample-10.csv`
- `apps/backend/verification/m4_exports/m4-sample-10.zip`

Đúng10 word_id của report M3; đã mở APKG SQLite (10 note/10 card, không media), CSV BOM
(10 dòng, Examples không còn {{/}}/[reading]) và ZIP Markdown (10 file/frontmatter).
Các dòng notebook/collection tạm đã rollback, saved trước/sau0/0. `verification.json`
cùng thư mục và `verification/m4-export-measure.log` lưu kiểm chứng. Đây là mở lại bằng
parser/SQLite, không tuyên bố đã kiểm tra giao diện Anki/Excel/Obsidian.

### Kiểm chứng cuối

**181/181 test PASS** trong117,28 giây: giữ170 test M3 và11 test mới. Coverage service/NLP
tổng **97,40%**; auth95,2%, dictionary98,2%, imports97,3%, notebook service100%,
notebook exports99,1%, search98,2%, textbooks94,1%, NLP98,0% (furigana100%).
Check ngưỡng70% từng service/NLP đạt; Ruff check/format xanh **127 file**;
git diff --check đạt. Migration upgrade→downgrade→upgrade chỉ chạy trên Testcontainers.

Kết quả test cuối và coverage được ghi ở log/XML `verification/m4-tests.{log,xml}`,
`m4-coverage.log`; Ruff `m4-ruff.log`, `m4-format.log`. Không hạ ngưỡng70%, không bỏ test cũ.
Test mới bao gồm ruby/CSV/giới hạn nghĩa, idempotence/reading theo sách và entry, import
tắt furigana/reading dòng sau, API bản gốc, backfill/source invariant, quyền admin/audit,
kanji privacy, CRUD/ifMatch/trùng/16KB, JLPT offline/chạy lại và Unihan projection.

RSS một worker uvicorn sau nạp core/searchHTTP200: **178.409.472 byte (170,14 MiB)**,
M3 là169,48 MiB. Đo sau triển khai/backfill, trước seed JLPT; snapshot local, không phải
peak RAM/export hay deploy. `verification/m4/resources.json`, `m4-resources.log`.
Không chạy benchmark c=10 và không thay kết luận NFR deploy từ các milestone trước.

Tái chạy từ apps/backend:

```powershell
uv run pytest --cov --cov-report=term-missing --cov-report=json
uv run python scripts/check_coverage.py coverage.json
uv run ruff check . ../../scripts
uv run ruff format --check . ../../scripts
uv run python -m scripts.backfill_furigana --dry-run
uv run python -m scripts.verify_m4
uv run python -m scripts.measure_m4_exports
uv run python -m scripts.seed_jlpt_textbooks --admin-email YOUR_ADMIN_EMAIL --directory data/openjlpt
uv run python -m scripts.build_hanviet_unihan data/unihan/Unihan_Readings.txt --version 17.0.0
```

Năm commit: sửa export; furigana dẫn xuất; dictionary/mục từ thủ công; JLPT public;
Unihan + báo cáo kiểm chứng. **Dừng sau M4**, chưa M5/M6, IMP-11 tiếp tục hoãn;
Hán Việt chỉ ở bước CSV/mẫu để duyệt.

## Milestone 5 — Hán Việt và worker import (IMP-10)

Ngày27/10/2026. Từ main `fc81ff1` sau merge M4, tạo nhánh
`milestone-5-hanviet-worker`; nhánh M4 local đã merge được xóa. Phạm vi chỉ M5,
IMP-11 vẫn hoãn, không làm M6, không đo tải10 đồng thời. DECISIONS69–81.

### Hán Việt: nguồn, overrides và độ phủ

Mẫu M4 được người dùng duyệt:16 đúng,3 sai âm Nôm,11 thiếu. Giữ Unihan17.0.0,
đọc thêm Unihan_Variants.txt từ ZIP local đã có; chỉ lấy Traditional/Semantic/Z/
SpecializedSemanticVariant khi chữ chưa có kVietnamese. Chặn chu trình; chỉ nhận
các nguồn có một âm và đồng thuận, mâu thuẫn để trống. Không đổi chữ có âm trực tiếp
bằng một biến thể chỉ vì âm biến thể trông quen hơn.

`data/hanviet_overrides.csv` chứa13 âm đã duyệt và 滝 rỗng/chờ duyệt; ưu tiên cao nhất.
Sửa 爽→SẢNG, 紳→THÂN; bỏ SÔNG của 滝. Đây là file nhỏ được Git quản lý; CSV sinh,
nguồn Unihan và review không push. Unicode-3.0/license/provenance ở data/README.md.

| Tập đo:2.004 chữ trong words có entry local | Có âm | Độ phủ |
| --- | ---: | ---: |
| kVietnamese trực tiếp (M4) | 1.353 | 67,51% |
| Sau tra biến thể | 1.455 | 72,60% |
| Sau override đã duyệt | 1.461 | **72,90%** |

Script: `scripts/build_hanviet_m5.py`; log `verification/m5-hanviet-build.log`,
SHA-256 readings/variants/overrides trong `data/hanviet.metadata.json`.
SHA-256 Unihan_Variants.txt:
`3f23cd71872633f3350875d25bd388e83b60fa71807634c9a600ec26f38a68ab`.
**MANUAL300 chữ:** `apps/backend/verification/m5_hanviet_review.md`, gồm chữ/âm/source/
số entry, đánh dấu rõ unihan_variant. Xếp theo số entry có chữ giảm dần, tie-break
Unicode; một entry tính một lần/chữ trong headword và trường Nhật example/usage/
collocation. Tập review khác tập headword dùng cho bảng độ phủ.

Migration0009 thêm kanji.hanviet_source và kanji_edits, có downgrade. GET kanji và
kanji_breakdown thêm source: override/unihan/unihan_variant:U+XXXX/null.
PATCH /kanji chỉ admin, chuẩn NFC/uppercase/khử trùng, ghi audit và source=override.
Tính lại words.hanviet trừ mọi từ đã có WordEdit hanviet qua DICT-08; seed cũng giữ
âm Kanji đã sửa qua API có audit. Advisory transaction lock chung với sửa Word.

Đã backup và seed vào DB local theo duyệt M5: **10.386 chữ** cập nhật, **7.032 từ**
tính lại; lần hai và lần đối chiếu cuối đều **kanji_changed=0, words_changed=0**.
Log `verification/m5-hanviet-{first,second,final-idempotence}.log`.
Âm chưa duyệt vẫn hiển thị kèm source để frontend đánh dấu; sửa dần qua PATCH /kanji.

### Bỏ override furigana và bảo toàn nguồn

- Bỏ 腹痛 khỏi bảng override toàn cục, giữ 私→わたし. DB local thực tế không có headword
  腹痛 trong sách gốc; bổ sung riêng cặp chuẩn **JMdict1501230 腹痛/ふくつう** từ JSON
  đầy đủ đã kiểm SHA ở M1, không tạo entry OCR. Không dùng reading はらいた ít phổ biến
  làm mặc định cho câu đã duyệt.
- Reading ưu tiên chính entry/cùng sách, rồi headword public/JMdict duy nhất, rồi override
  và Sudachi; không lấy headword private của sách khác và không chọn tùy tiện homograph.
  Mẫu30 câu seed20261020 tại `verification/m5_furigana_sample.md` vẫn cho 腹痛[ふくつう].
- Backfill: quét19.717, dry-run/ghi **1.134** bản dẫn xuất, chạy lần hai **0**.
  `verification/m5-furigana-{dry,first,second}.log`.
- Hash content+search_text toàn19.717 entry trước/sau và sau phép đo vẫn giống nhau:
  `06dc8ed500a4acdbe639f64fc664c1a6ede03110c552376fd3c0a7b3f9a0449f`.
  `verification/m5-content-{before,after,final}.json`. Sửa dữ liệu từ điển/Hán Việt và
  cột dẫn xuất không làm thay nguồn OCR, summary hay search_text.

### Backup local

| Trước bước | Backup (root repo) | Byte |
| --- | --- | ---: |
| Migration/seed Hán Việt M5 | `backups/milestone5/vocab-20261027-005242.dump` | 5.343.718 |
| Schema worker sau seed/backfill | `backups/milestone5/vocab-20261027-010224.dump` | 5.481.274 |

Custom format pg_dump; cả hai catalog đọc được (`verification/m5-{hanviet,worker}-backup-toc.log`).
Không downgrade DB thật; downgrade0009/0010 nằm trong kiểm thử migration DB tạm.

### Worker và API async

- Procrastinate **3.10.0**, psycopg **3.3.6**, psycopg-pool **3.3.3** trong uv.lock.
  Migration0010 tạo schema procrastinate riêng bằng SQL/license upstream đã pin trong
  repo, function/trigger có search_path riêng; không phụ thuộc chạy schema install CLI.
  Payload BYTEA tối đa5MB, processed/updated_at/auto_furigana và index status/time ở ImportJob.
- IMPORT_MODE=async mặc định; sync giữ contract201/upload,200/commit cho test cũ.
  Async POST /imports trả202/pending, parse→matching/staging→review; POST commit trả202/
  commit_pending, worker chuyển committing→done. GET job thêm progress{processed,total},
  updated_at; không trả payload. Payload được dọn ở review/failed/done.
- Enqueue gọi hàm Procrastinate trong cùng transaction asyncpg với domain job; lock và
  queueing_lock import:{id} cùng claim FOR UPDATE ngăn hai worker ghi trùng. Staging có
  progress từng lô100 sau validate toàn file. Commit giữ toàn bộ words/entries và done
  trong một transaction; progress chỉ hoàn thành sau commit.
- Lỗi parse/business failed có mã lỗi, xóa staging và không retry. Lỗi DB tạm tối đa3
  retry sau lần đầu, backoff2/4/8 giây; kiểm tra cả trường hợp mất DB khi ghi trạng thái lỗi.
  Job processing/committing quá15 phút khi startup thành WORKER_TIMEOUT, không replay
  commit stale; SKIP LOCKED tránh transaction đang hoạt động. Retry cũng kiểm tra tuổi job.
- app.worker cấu hình WindowsSelectorEventLoopPolicy trước asyncio.run; API vẫn asyncpg.
  Pool1–2 connection, connect_timeout5 giây. Compose worker dùng cùng build backend,
  chạy `uv run --no-sync python -m app.worker`, chờ API healthy sau migration.
- Matching theo lô và cache lesson/word/book trong commit giảm truy vấn lặp, giữ đúng
  auto/ambiguous/none, thứ tự ID, quyền và tính nguyên tử. Không tối ưu tải10 đồng thời.

### NFR-02:1.000 dòng thật qua HTTP và worker riêng

`scripts/measure_m5.py` lấy1.000 headword không mơ hồ từ entry local có nghĩa/câu nguồn,
ghi CSV thật (không bịa nghĩa). API uvicorn loopback một worker + process Procrastinate
riêng, API đã warm search, worker khởi động trước upload; poll50ms. Thời gian gồm auth,
SQL, queue, matching/NLP và quan sát trạng thái. CSV SHA-256:
`ed2ba21d2c077e528ef587707c9d0d506a72d45dec2f6cca421b37dba108a304`.

| Lượt đo hợp lệ | Upload→review (s) | Commit→done (s) | Tổng đầu-cuối (s) |
| --- | ---: | ---: | ---: |
| Trước gộp matching/cache | 14,453 | 15,793 | **30,246** |
| Sau gộp matching/cache | 9,749 | 12,077 | **21,827** |

Lượt cuối **đạt mục tiêu tổng <30 giây local**; giữ nguyên lượt30,246 giây trong báo cáo,
không thay số đo cũ. Cả hai dùng cùng CSV, xác nhận đúng1.000 entry sau done rồi xóa
đúng sách/import/queue job tạm; số Word không tăng, hash nguồn giữ nguyên. Không còn
API/worker probe hoặc container worker chạy sau đo. Đây là loopback local, chưa là
bằng chứng hosting deploy. Không đo c=10.

JSON/log cuối: `verification/m5/resources.json`, `verification/m5-measure.log`,
`verification/m5/{api,worker}.log`, CSV `verification/m5/import-1000.csv` (Git-ignore).
Số trước gộp ở `verification/m5/resources-before-batching.json` và
`verification/m5-measure-before-batching.log`. Lượt thăm dò pool Windows bị timeout
không được coi là phép đo thành công; đã cấu hình timeout và đo lại đầy đủ.

### RSS API/worker/tổng

| Process (PID Python thực, không launcher) | Byte | MiB |
| --- | ---: | ---: |
| API | 179.163.136 | **170,86** |
| Worker | 220.344.320 | **210,14** |
| Tổng cùng thời điểm | 399.507.456 | **381,00** |

RSS cuối và peak quan sát ở sample50ms của lượt cuối bằng nhau; không khẳng định bắt
được mọi peak ngắn. Tổng chỉ hai process Python, **không gồm PostgreSQL/OS/proxy** và
không chứng minh instance hosting512MB luôn đủ. PID và sample peak trong resources.json;
probe đã đóng. So với M4 API170,14 MiB, M5 API170,86 MiB trên dataset sau seed.

### Kiểm chứng và tái chạy

**193/193 test PASS** trong135,67 giây: toàn181 case cũ và12 case mới. Coverage tổng
service/NLP/job/worker **97,10%**; từng service và NLP đều≥70%: auth95,2%, dictionary98,0%,
imports97,4%, notebook100%, exports99,1%, search98,2%, textbooks94,1%, NLP98,0%.
Job handler96,8%, worker84,0%; check_coverage đạt. Ruff check/format xanh **134 file**,
git diff --check đạt. Không giảm ngưỡng hoặc bỏ test cũ.

Kết quả cuối ở `verification/m5-tests.{log,xml}`, `m5-coverage.log`, `m5-ruff.log`,
`m5-format.log`; giữ181 case cũ với IMPORT_MODE=sync và thêm case async trong DB tạm
riêng để kiểm tra commit thật giữa API/worker. Có test hai worker, staging đúng một lần,
parse failed không có staging/entry, commit rollback, quyền user khác404, backoff/retry
exhaustion, lỗi ghi trạng thái retry, timeout không replay và Selector Windows.

Coverage gate bổ sung cả job handler/worker ≥70%, không hạ ngưỡng service/NLP hoặc bỏ test.
Build Linux và chạy worker --once trong image backend được kiểm tra; Compose config
đạt. Log `verification/m5-linux-{build,worker}.log`; không tuyên bố toàn suite đã chạy Linux.

Từ apps/backend, sau backup và Alembic upgrade head:

```powershell
uv sync --frozen
uv run pytest --cov --cov-report=term-missing --cov-report=json
uv run python scripts/check_coverage.py coverage.json
uv run ruff check . ../../scripts
uv run ruff format --check . ../../scripts
uv run python -m scripts.build_hanviet_m5
uv run python -m scripts.seed_hanviet --overrides data/hanviet_overrides.csv
uv run python -m app.worker
# Terminal khác: API mặc định IMPORT_MODE=async
uv run uvicorn app.main:app
```

Phép đo độc lập tự mở/dọn process và sách tạm: `uv run python -m scripts.measure_m5`.
Hai commit: `58acb6a feat(dictionary): hanviet variants, overrides and kanji edits` và
`feat(imports): procrastinate worker and async import flow`. **Dừng sau M5**;
IMP-11 vẫn hoãn, chưa M6.

## Milestone 6 — IMP-12, Hán Việt lô 1 và tổng kết Phase 2

Ngày27/10/2026. Nhánh `milestone-6-free-text` từ main `37eab0f` sau merge PR#4 M5.
DECISIONS82–89. Không làm frontend/P2, không đo tải10 đồng thời; IMP-11 vẫn hoãn.

### Hán Việt đã duyệt và độ phủ

- Thêm đầy đủ **68 chữ được liệt kê**:42 thiếu +26 sửa (phần kết luận yêu cầu ghi23 sai,
  nhưng danh sách cụ thể có26; áp dụng toàn bộ danh sách). Note `review M5 lô 1`, thay
  toàn bộ âm cũ; 楽=LẠC|NHẠC, 行=HÀNH|HÀNG. Giữ 滝 rỗng/chờ duyệt như M5.
- `nlp/vietnamese.py` là hàm thuần chuẩn hóa vị trí dấu, NFC, bảo toàn i/y, hoa/thường
  và loại thanh. HOÁ→HÓA, THUỶ→THỦY, HOẠ→HỌA, TOẠ→TỌA. TOÀ→TÒA, không tự biến
  huyền thành nặng theo lỗi gõ TOÀ→TỌA. Build/seed/PATCH dùng chung hàm; vẫn bảo vệ audit
  sửa tay theo M5. Kiểm tra cuối DB:0 chữ còn âm chưa chuẩn hóa vị trí dấu.
- Backup trước seed: **`backups/milestone6/vocab-20261027-125035.dump`**, **5.523.419 byte**,
  custom format, pg_restore đọc catalog thành công: `verification/m6-backup-toc.log`.
  Lượt đầu thử khi Docker chưa chạy/DB đang startup đã thất bại trước seed; backup hợp lệ
  nêu trên được tạo khi DB sẵn sàng, rồi mới ghi dữ liệu.
- Seed ghi **170 chữ, 1.348 từ**; lượt hai **kanji_changed=0, words_changed=0**.
  `verification/m6-hanviet-{first,second}.log`. Không thêm migration ở M6.

| Tập đo | Trước M6 | Sau M6 |
| --- | ---: | ---: |
| Chữ trong headword có entry (2.004 chữ) | 1.461/2.004 =72,90% | **1.503/2.004 =75,00%** |
| Có trọng số entry/chữ, cùng tập headword | 81.500/94.816 =85,96% | **89.559/94.816 =94,46%** |
| Top300 theo tần suất M5: số chữ có âm | 258/300 =86,00% | **300/300 =100%** |
| Top300 có trọng số entry/chữ | 61.469/69.528 =88,41% | **69.528/69.528 =100%** |

Độ phủ là có âm, không khẳng định toàn bộ âm ngoài overrides đã đúng. Trọng số tính một
lần/chữ/entry trong headword + trường Nhật example/usage/collocation, rồi giới hạn tập
chữ headword để so sánh; không phải tỷ lệ entry đã có đủ tất cả âm. Nếu tính toàn bộ
2.212 chữ xuất hiện trong các trường đó:1.652/2.212=74,68%, trọng số90.116/95.565=94,30%.
Số trước seed giữ ở `verification/m6-hanviet-before-seed.json`; lượt build sau seed ở
`m6-hanviet.json`, `m6-hanviet-postseed.log`. Metadata SHA nguồn/overrides hiện tại ở
`data/hanviet.metadata.json`, Unihan17.0.0 và license như M4/M5.

**Review tiếp:** `apps/backend/verification/m6_hanviet_review_2.md`, đúng300 chữ hạng301–600,
cùng cách đếm/tie-break M5, không trùng lô đầu. Thêm cột Từ ví dụ, tra headword từ toàn DB.
**299 chữ có headword ví dụ**; riêng `词` không có headword, lấy nguyên `名词` trong phần
giải thích tiếng Trung của entry8266, đánh dấu “câu nguồn; không có headword”. Đây là
nhiễu nguồn cần đối chiếu, không tạo từ giả hoặc âm mới. Các dòng unihan_variant có đánh dấu.
Đã kiểm tra top300 của file M5 đều có âm trong DB sau seed; review/source không push Git.

### IMP-12 — free_text

- Nhận đúng một `text` form hoặc file TXT UTF-8, tối đa20.000 ký tự (bỏ BOM); quá giới hạn
  trả422 trước enqueue cả sync/async. Options form: `lesson_no` mặc định1,
  `include_proper_nouns=false`, `exclude_jlpt=N5,N4`; options được giữ trong payload nội bộ.
- Tách câu theo 。！？/xuống dòng, Sudachi C và bộ lọc content_tokens dùng chung lemma M2/M3.
  Giữ danh/động/tính/形状詞/phó từ; loại trợ động từ theo ngữ cảnh, proper noun mặc định,
  số, formal noun, lemma1 kana, ký hiệu và token không có reading kana hợp lệ.
- Gom mỗi normalized_form thành một dòng; match bằng dictionary_form + dictionary reading,
  `order_no` theo lần xuất hiện đầu. Tối đa2 câu khác nhau đầu tiên trong example, raw giữ
  nguyên câu; đánh {{}} theo span token, mọi lần xuất hiện trong cùng câu đều được đánh.
  Phần trợ động từ ngoài token vẫn ngoài ngoặc (`{{食べ}}ました`). Không tạo meaning;
  validator vốn cho phép example/raw nên không nới quy tắc chung. Từ đã match xem nghĩa JMdict
  qua dictionary; từ không có nghĩa nguồn vẫn để trống, không tự dịch/bịa nghĩa.
- exclude_jlpt giữ dòng skipped + `raw.skip_reason=EXCLUDED_JLPT` khi tất cả ứng viên thuộc
  cấp bị loại; ứng viên mixed/null vẫn review. Chung matching/staging/review/commit nguyên tử,
  quyền chủ sách/job và furigana với adapter cũ. Giới hạn16.000 byte/content entry khi save
  vẫn giữ; câu nguồn quá dài có thể làm commit fail/rollback theo contract hiện có.

### Đo free_text 20.000 ký tự

`scripts/measure_m6.py`: đoạn tự biên soạn gồm câu đọc sách/ăn uống/đi học/công việc,
lặp/truncate đúng20.000 Unicode code point, **39 lemma**; không chép sách. HTTP thật
uvicorn loopback một process API + một worker Procrastinate, poll50ms; không warm tokenizer
trước lượt đầu. Worker khởi động trước upload, thời gian gồm cả queue/startup/lazy load.

| Lượt | Upload → review (s) |
| --- | ---: |
| 1 (bao gồm khởi động/nạp lười) | **8,937** |
| 2 | **5,083** |
| 3 | **0,182** |

**3/3 dưới10 giây local**; chênh lệch có cả thời gian chờ queue, không chỉ NLP. Đây là
workload39 lemma lặp lại, không cam kết mọi văn bản20.000 ký tự đều có cùng chi phí.
Không thay bằng bằng chứng HTTP deploy. Chỉ đo đến review theo yêu cầu; test sync/async
có commit thật và furigana. Sách/job/queue tạm được dọn, không tạo Word vì không commit
trong benchmark; không còn sách `__m6_measure_` trong DB. API/worker probe đã dừng.

JSON: `verification/m6/resources.json`; log `verification/m6-measure.log`, `m6/{api,worker}.log`;
TXT tự biên soạn `verification/m6/free-text-20000.txt`.
SHA-256 TXT: `7dc2ade95cd223615e0f1f337e25e01f56d0dceb7219b5deab540a25e51799ef`.
Không đo lại RSS/c=10 ở M6; số API/worker/tổng gần nhất ở M5, kèm giới hạn đã ghi.

### Kiểm chứng cuối và bảo toàn nguồn

- **210/210 test PASS**, **93,77 giây**: giữ193 test M5, thêm17 case M6. Kỳ vọng registry cũ
  thêm tên free_text; không bỏ test hoặc hạ ngưỡng. Fixture free_text tự viết.
- Coverage service/NLP/job/worker **97,18%**: auth95,2%, dictionary98,0%, imports97,6%,
  notebook100%, exports99,1%, search98,2%, textbooks94,1%, NLP98,2%, job96,7%, worker84,0%.
  Hàm tone normalization100%; cổng từng service/NLP/job/worker≥70% đạt.
- Ruff check/format xanh **139 file**, uv sync --frozen đạt (exit0), git diff --check đạt.
  Một Alembic DeprecationWarning path_separator có từ trước. Test trên Windows/Python3.12.5,
  PostgreSQL16 Testcontainers; không tuyên bố suite M6 đã chạy Linux/deploy.
- Log/XML: `verification/m6-tests.{log,xml}`, `m6-coverage.log`, `m6-ruff.log`,
  `m6-format.log`, `m6-sync.log`. Kiểm tra DB/review: `m6-db-final.json`.
- Hash content/search_text của19.717 entry vẫn như M5:
  `06dc8ed500a4acdbe639f64fc664c1a6ede03110c552376fd3c0a7b3f9a0449f`.
  `verification/m6-content-final.json`; không sửa nguồn OCR, summary hoặc sinh nghĩa giả.

### Kiểm tra file Git và chuẩn bị release

`git ls-files` không chứa bất kỳ file thuộc nhóm cấm:

| Nhóm kiểm tra | Số file |
| --- | ---: |
| data/pdf_imports/ | 0 |
| access.json | 0 |
| backups/ | 0 |
| verification/ | 0 |
| PDF hoặc dữ liệu OCR (.txt/.json/.csv/.xlsx) | 0 |
| OpenJLPT/Unihan gốc, thư mục nguồn hoặc archive Unihan | 0 |

CSV được track chỉ có **hanviet_overrides.csv đã duyệt** và4 fixture tự biên soạn
(`tests/fixtures/{hanviet,jlpt,mimikara,template}.csv`), không phải CSV sách/nguồn gốc.
Bằng chứng `verification/m6-git-files-audit.json`; audit lại sau stage trước release.
Backups/review/bằng chứng/data nguồn vẫn Git-ignore.

Tổng kết P1/NFR nằm đầu báo cáo; requirements cập nhật contract trạng thái (không mapping),
examples theo entry, content_furigana/?furigana=false, provenance/PATCH Kanji và NFR-01.
Free tier512MB chọn `IMPORT_MODE=sync`, chỉ API; tổng381MiB hai process M5 chưa tính DB/
OS/proxy/overhead, không coi là bằng chứng đủ ngân sách chạy chung worker.

Commit triển khai: `e6436ab fix(dictionary): reviewed hanviet batch 1, tone normalization`;
`eaff7e0 feat(imports): free text adapter`; commit release/tổng kết tiếp theo chứa báo cáo này.
Merge fast-forward vào main và tag `v0.2.0` ở **local**; **KHÔNG push** trước khi người dùng
duyệt danh sách `git log --oneline origin/main..main`. Chưa có GitHub CI run cho M6.

Tái chạy từ apps/backend:

```powershell
uv sync --frozen
uv run pytest --cov --cov-report=term-missing --cov-report=json
uv run python scripts/check_coverage.py coverage.json
uv run ruff check . ../../scripts
uv run ruff format --check . ../../scripts
# Backup trước mọi lần seed; build ghi CSV/review/metadata local
uv run python -m scripts.build_hanviet_m6
uv run python -m scripts.seed_hanviet --overrides data/hanviet_overrides.csv
uv run python -m scripts.measure_m6
```

**Dừng sau M6.** Backend P1 Phase 2 hoàn tất trong phạm vi đã duyệt, ngoại trừ IMP-11 hoãn;
Hán Việt lô2+/OCR/NFR và vận hành trên deploy vẫn là việc mở, không triển khai frontend/P2.

## Sau Phase 2 — M7: Hán Việt lô 2, biến thể nghiêm ngặt, đánh giá KANJIDIC2

Ngày28/10/2026. Nhánh `milestone-7-hanviet-kanjidic2` từ main `ac06f8f`
(merge PR#5 M6), DECISIONS90–97. Chỉ backend dictionary; không frontend/P2.
Mục “Dừng sau M6” ở trên là phạm vi lịch sử; M7 được cho phép riêng trong yêu cầu mới.

### An toàn lịch sử Git public

Đã fetch origin và quét **toàn bộ lịch sử mọi ref local**, không chỉ HEAD:
`git log --all --name-only --format=` có270 đường dẫn ở baseline; không có
data/pdf_imports, access.json, backups, verification, .env thật, dump, PDF,
OCR JSON/JSONL, CSV OpenJLPT gốc hay Unihan gốc. `.env.example` là mẫu cấu hình,
fixtures JSON/CSV là tự biên soạn; không xem chúng là dữ liệu/credentials thật.

Đọc JWT_SECRET từ .env và hai password từ access.json ở local, dùng
`git log --all -p -S` cho từng giá trị, chỉ lưu số khớp: **0/0/0 commit khớp,
0/0/0 lần xuất hiện trong patch được chọn**. Không in secret hoặc diff chứa secret.
Không phát hiện vi phạm, không rewrite lịch sử. Bằng chứng local:
`apps/backend/verification/m7-git-history-audit.json`; audit lại sau commit cuối.

`git log --oneline origin/main..main` rỗng sau fetch: M6 đã có trên GitHub qua PR#5.
Tag local hiện có `v0.2.0`, không tạo tag M7. Sẽ trình danh sách commit nhánh M7 so với
origin/main và chờ xác nhận trước push/tạo PR. Không tự push main/merge PR.
Chưa có CI cho M7 khi chưa push; CI main cho thay đổi M7 chỉ có sau khi PR được merge.

### Lô 2 và siết biến thể

Áp dụng **88 chữ có âm** (55 thiếu +33 sửa), note `review M6 lô 2`, thay toàn bộ âm;
thêm dòng **込 rỗng** với note “quốc tự Nhật, không có âm Hán Việt”. Tổng171 override,
169 dòng có âm; 滝 tiếp tục rỗng/chờ duyệt. Không sửa OCR hoặc tự tạo âm ngoài danh sách.

Chỉ giữ kTraditionalVariant/kZVariant, bỏ hai trường Semantic/SpecializedSemantic.
So với quy tắc M6, **964 chữ toàn nguồn thay đổi âm**, trong đó **55 chữ xuất hiện local**.
Danh sách đầy đủ từng chữ trước→sau (kể cả ngoài tập local):
`apps/backend/verification/m7-strict-variant-changes.md`, JSON ở `m7-hanviet.json`.
Ví dụ 雨: fallback **NGỰA → rỗng** khi bỏ liên kết sang U+99AD 馭;
âm cuối DB là **VŨ** từ override đã duyệt. Dòng rỗng được xuất cho fallback bị loại
để seed xóa được âm cũ thay vì bỏ qua. Giữ chống chu trình/mâu thuẫn M5.

### Chấm điểm nguồn và thứ tự ưu tiên

Nguồn [KANJIDIC2-en, release 3.6.2+20261019180022](https://github.com/scriptin/jmdict-simplified/releases/tag/3.6.2%2B20261019180022)
đúng release JMdict local; version3.6.2, dictDate2026-10-19,
fileVersion4, databaseVersion2026-292. Trích type=vietnam từ mọi nhóm cách đọc,
chuẩn hóa qua nlp/vietnamese.py, viết hoa, khử trùng, giữ thứ tự nguồn.
JSON SHA-256: `7d9eb1f8ee470b713cbf23494286d68edcfbef0d99f551b4a2e29d7a2cf2fb2c`.
Phiên bản/URL/SHA các nguồn được lưu vào `data/hanviet.metadata.json` local;
attribution EDRDG/Minh Chau Pham/scriptin và CC BY-SA4.0 ở `data/README.md`.

Tập chuẩn = **169 chữ override có âm**, gồm M5 và hai lô đã duyệt.
Tất cả tỷ lệ dưới đây dùng mẫu số169, kể cả nguồn không phủ chữ.
“Chứa âm đầu chuẩn” kiểm tra âm đầu override có trong tập nguồn;
“Chứa toàn bộ âm chuẩn” kiểm tra tập override là tập con của nguồn.
Biến thể là fallback riêng, **không** tính lại các âm Unihan trực tiếp.

| Nguồn | Độ phủ tập chuẩn | Âm đầu trùng | Chứa âm đầu chuẩn | Chứa toàn bộ âm chuẩn |
| --- | ---: | ---: | ---: | ---: |
| KANJIDIC2 | 169/169 =100% | 147/169 =86,98% | 158/169 =93,49% | 158/169 =93,49% |
| Unihan trực tiếp | 57/169 =33,73% | 2/169 =1,18% | 10/169 =5,92% | 9/169 =5,33% |
| Unihan biến thể đã siết | 1/169 =0,59% | 0/169 =0% | 0/169 =0% | 0/169 =0% |

KANJIDIC2 cao hơn Unihan trực tiếp nhưng **chưa đạt90% âm đầu trùng**.
Theo cổng người dùng đặt, giữ **override > Unihan trực tiếp > Unihan biến thể đã siết**.
Không thêm fallback KANJIDIC2 khi cổng không đạt. Seed đã chấp nhận source `kanjidic2`
và test precedence/cổng để hỗ trợ nguồn này nếu một lần đánh giá sau đạt điều kiện.
Điểm trên tập overrides thiên về các chữ từng cần sửa; không suy rộng thành độ chính xác
của toàn nguồn. Không thay đổi/ngụy tạo thứ tự âm nguồn để vượt cổng.

| Nguồn riêng, trên2212 chữ local | Có âm | Trọng số entry/chữ có âm |
| --- | ---: | ---: |
| KANJIDIC2 | 2093/2212 =94,62% | 95093/95565 =99,51% |
| Unihan trực tiếp | 1405/2212 =63,52% | 77451/95565 =81,05% |
| Unihan biến thể đã siết | 148/2212 =6,69% | 3336/95565 =3,49% |

### Backup, seed và độ phủ thực tế

Backup **`backups/milestone7/vocab-20261028-221031.dump`**, **5.526.928 byte**,
custom format PostgreSQL16.15; pg_restore đọc230 TOC entries thành công trước build/seed.
Seed đầu **kanji_changed=1046, words_changed=825**; lần hai **0/0**.
Log local `verification/m7-seed-{first,second}.log`. Không thêm migration.
Giữ bảo vệ audit Word sửa tay (DICT-08) và Kanji sửa qua PATCH; test kiểm tra source
KANJIDIC2, KanjiEdit, xóa fallback cũ, seed lặp; test DICT-08/M5 vẫn xanh.

| Tập đo | Trước M7 | Sau seed M7 |
| --- | ---: | ---: |
| Chữ headword có entry | 1503/2004 =75,00% | 1514/2004 =75,55% |
| Trọng số headword | 89559/94816 =94,46% | 91320/94816 =96,31% |
| Toàn bộ chữ trong headword + trường Nhật | 1652/2212 =74,68% | 1663/2212 =75,18% |
| Trọng số toàn bộ | 90116/95565 =94,30% | 91878/95565 =96,14% |

Cùng population và cách đếm M5/M6: một lần/chữ/entry, chỉ trường Nhật được chọn;
độ phủ có âm không đồng nghĩa âm đúng, trọng số không phải tỷ lệ entry đã đủ mọi âm.
Đã kiểm tra DB thực khớp mọi chỉ số trên và cả171 override.

### Review lô 3 và kiểm chứng

`apps/backend/verification/m7_hanviet_review_3.md`: **268 chữ** từ đúng cửa sổ600 chữ
hạng601–1200, sort số entry giảm dần/tie-break code point như M5.
Chỉ đưa thiếu âm, hai nguồn có âm đầu khác nhau hoặc ≥3 âm; loại chữ hai nguồn có
cùng tập âm chuẩn hóa theo yêu cầu không review chữ đồng thuận. Nguồn thiếu không xem
là đồng thuận. Cột đủ âm đang dùng/source/KANJIDIC2/Unihan/số entry/từ ví dụ;
Unihan là trực tiếp rồi fallback đã siết. Ví dụ chỉ dùng headword thật; không có thì
ghi rõ “không có headword”. Review/raw sources/bằng chứng không push Git.

**220/220 test PASS**, **151,63 giây**, giữ210 test M6 và thêm10 case M7.
Coverage service/NLP/job/worker **97,18%**, mọi cổng từng service/NLP/job/worker≥70% đạt;
Ruff check/format xanh142 file, uv sync --frozen exit0, git diff --check đạt.
Test trên Windows/Python3.12.5 với PostgreSQL16 Testcontainers; không tuyên bố Linux/deploy.
Một Alembic DeprecationWarning path_separator từ trước. Venv local được sửa đường dẫn
Python đã mất sang runtime3.12.5 trong workspace; không đổi lock/dependency.
Log/XML `verification/m7-tests.{log,xml}`, `m7-coverage.log`, `m7-build.log`, `m7-sync.log`.

Hash content/search_text **19.717 entry** vẫn như M6:
`06dc8ed500a4acdbe639f64fc664c1a6ede03110c552376fd3c0a7b3f9a0449f`.
Bằng chứng `verification/m7-db-final.json`. Không sửa nội dung nguồn/search_text,
không sinh nghĩa hoặc headword giả. Chỉ push code/docs/overrides khi được xác nhận.

Hai commit triển khai yêu cầu: `fix(dictionary): hanviet batch 2, strict variants`
và `feat(dictionary): kanjidic2 vietnamese readings`. Chưa push/tạo PR/tag mới;
chờ người dùng duyệt danh sách hash cuối. NFR deploy/OCR/IMP-11 vẫn mở như M6.


## M7b — đánh giá combined trên 600 chữ đã duyệt: KHÔNG ĐẠT CỔNG

Ngày28/10/2026. Nhánh `milestone-7b-combined-hanviet` từ main `3700d0d`,
DECISIONS98–103. Không frontend/P2. **Dừng tại đánh giá, không áp dụng combined.**

### Trạng thái M7 và tập chuẩn mới

Bước0 đã hoàn tất trước M7b: [PR#6](https://github.com/ngphat516/japanese-vocab-app/pull/6)
đã merge vào main `3700d0d`; [CI main run40719553529](https://github.com/ngphat516/japanese-vocab-app/actions/runs/40719553529)
PASS. Local đã pull main, nhánh M7 đã xóa local/remote. Không push/tạo lại PR M7.

Đọc nguyên hai file review gốc local: `m5_hanviet_review.md` và
`m6_hanviet_review_2.md`, mỗi file300 chữ, tổng600 không trùng. Chuẩn = override M7
nếu có (kể cả rỗng), nếu không = âm/thứ tự đang dùng lúc duyệt trong file review.
Chuẩn hóa bằng nlp/vietnamese.py và viết hoa, bảo toàn i/y; không sửa KÍ thành KÝ
hoặc đổi thứ tự âm nguồn để cải thiện điểm. Snapshot toàn bộ600 chữ và SHA-256 từng
review/nguồn/overrides nằm trong `verification/m7b-evaluation.json` local.

Lọc membership KANJIDIC2 còn **599 chữ chuẩn**: loại `词`. `込` vẫn thuộc population
nhưng chuẩn rỗng có chủ đích, báo riêng thay vì gán âm; mẫu số so âm là **598**.
Không chỉ lọc theo chữ có reading vietnam để tránh bỏ qua chữ nguồn thiếu âm.

### Quy tắc candidate và bốn chiến lược

Evaluator chỉ giữ tập âm KANJIDIC2; theo thứ tự Unihan trực tiếp rồi fallback
Traditional/Z đã siết, chọn âm chung đầu tiên và đưa đúng âm đó lên đầu.
Không có âm chung thì giữ thứ tự KANJIDIC2, không thêm âm chỉ có ở Unihan.
KANJIDIC2 không có âm thì fallback Unihan. Candidate source là `kanjidic2_unihan`
khi có âm chung, `kanjidic2` khi không; override kể cả rỗng luôn thắng.
Các source/thuật toán này **chỉ nằm trong evaluator**, chưa bật ở service/seed.

| Chiến lược | Độ phủ | Âm đầu trùng | Chứa âm đầu chuẩn |
| --- | ---: | ---: | ---: |
| Unihan hiện tại: pipeline M7 gồm overrides | 589/598 =98,49% | 589/598 =98,49% | 589/598 =98,49% |
| KANJIDIC2 thuần | 598/598 =100% | 550/598 =91,97% | 583/598 =97,49% |
| Combined chưa override | 598/598 =100% | **565/598 =94,48%** | 583/598 =97,49% |
| Combined + overrides baseline M7 | 598/598 =100% | 593/598 =99,16% | 594/598 =99,33% |

Để tránh nhập nhằng giữa “Unihan hiện tại” và nguồn chưa sửa: **Unihan trực tiếp +
biến thể đã siết, chưa overrides** đạt độ phủ488/598=81,61%, âm đầu434/598=72,58%,
chứa âm đầu442/598=73,91%. Điểm này cũng lưu riêng trong JSON, không bỏ đi.

**Cổng KHÔNG ĐẠT**: combined565/598=94,4816% <95% và thấp hơn pipeline M7 hiện tại.
Ngay cả nếu so baseline Unihan chưa override72,58%, điều kiện ≥95% vẫn trượt.
Cần ít nhất569/598 để đạt95% (thiếu4 trường hợp); không lấy điểm99,16% của
combined+override thay cho điểm combined để vượt cổng.

Có33 sai khác âm đầu, liệt kê đủ trong `verification/m7b-combined-mismatches.md`.
Ví dụ candidate đã chọn đúng 税→THUẾ, 治→TRỊ và 森→SÂM (không thêm CHÙM),
nhưng 行 chọn HÀNG thay vì chuẩn HÀNH; 読 chọn ĐẬU thay vì ĐỘC;
戦 chỉ có KHUYẾT thay vì CHIẾN. KÍ/KÝ và KĨ/KỸ vẫn khác theo contract bảo toàn i/y.

### Population mới và độ phủ thực tế

Nguồn KANJIDIC2 giữ đúng release3.6.2+20261019180022 đã dùng ở M7;
membership10384 chữ. Trong2212 chữ local, có **2101 chữ thuộc population mới**,
**111 chữ bị loại**, trọng số bị loại428/95565. Trọng số còn95137,
vẫn đếm một lần/chữ/entry trên cùng trường Nhật M5–M7.

Danh sách đầy đủ111 chữ không có trong KANJIDIC2 (sort code point):

`东 丢 严 为 乐 书 买 仅 值 兴 别 剧 办 动 劲 势 单 发 变 处 妆 实 对 带 强 忧 户 换 搅 摇 时 查 标 样 樱 欢 汉 污 测 渐 满 炖 烦 热 现 產 电 础 简 类 级 纯 组 细 经 结 给 艺 节 茧 荟 莹 虽 见 览 說 订 认 讯 记 许 论 评 词 话 详 语 说 请 读 谁 谢 负 责 货 购 费 跃 车 转 边 过 还 这 邮 释 鉴 钱 问 间 阅 际 险 难 页 项 顺 预 题 饭 龄`

Lưu ý các ví dụ trong yêu cầu: 题/邮/產 thực sự không có trong JSON, nhưng
**您/每/笨/罩 có trong KANJIDIC2** nên vẫn tính theo quy tắc membership.
Membership không tự chứng minh một câu OCR là tiếng Nhật đúng; không sửa/xóa nguồn OCR
hoặc tự tạo blacklist từ nhận định ngôn ngữ.

| Chỉ số trên population mới2101 chữ | Trước đánh giá | Sau đánh giá (không seed) |
| --- | ---: | ---: |
| Có âm | 1573/2101 =74,87% | 1573/2101 =74,87% |
| Có trọng số entry/chữ | 91506/95137 =96,18% | 91506/95137 =96,18% |

Mô phỏng combined + overrides M7 sẽ phủ2099/2101 chữ, trọng số95063/95137;
đây **chỉ là dự phóng chưa áp dụng**, không phải kết quả seed hoặc lý do bỏ cổng.
Độ phủ trước/sau thực tế giữ nguyên vì dừng khi không đạt cổng.

### Phạm vi dừng và kiểm chứng

Không tạo backup/build CSV production/seed hoặc chạy seed lần hai vì không có thay đổi
DB được áp dụng. Giữ nguyên171 overrides, metadata/CSV/source M7 và thứ tự nguồn M7.
**Chưa thêm19 override lô3**; `繰`, `扱` tiếp tục chưa duyệt.
**Không tạo `m7b_hanviet_review_4.md`**, số dòng review4 là **chưa tạo**, không ghi0
để tránh hiểu nhầm toàn bộ hạng1201+ đã qua lọc và không còn gì cần duyệt.
Không tạo commit feature áp dụng combined theo tên dự kiến khi điều kiện chưa đạt.

Evaluator tái chạy bằng `uv run python -m scripts.evaluate_hanviet_m7b`, chỉ đọc DB/
nguồn/reviews và ghi JSON/log/sai khác vào verification local Git-ignore.
Đã đối chiếu SHA nguồn/override với metadata M7 và hash content/search_text19717 entry
vẫn là `06dc8ed500a4acdbe639f64fc664c1a6ede03110c552376fd3c0a7b3f9a0449f`.
Bằng chứng `verification/m7b-content-final.json`. Chưa push/tạo PR M7b;
chỉ thực hiện khi người dùng xác nhận commit đánh giá cụ thể.

**231/231 test PASS**, **120,02 giây**: giữ220 test M7, thêm11 case cho evaluator
(âm chung/thứ tự nguồn, không thêm CHÙM cho 森, membership, override rỗng/thắng candidate,
đọc chuẩn600 chữ, cổng95%/so sánh nghiêm ngặt). Coverage service/NLP/job/worker
**97,18%**, từng cổng service/NLP/job/worker≥70% đạt; Ruff check/format xanh144 file,
git diff --check đạt. Windows/Python3.12.5/PostgreSQL16 Testcontainers;
Alembic path_separator DeprecationWarning có từ trước.
Log/XML `verification/m7b-tests.{log,xml}`, `m7b-coverage.log`, `m7b-ruff.log`,
`m7b-format.log`, `m7b-evaluation.log`. Không tuyên bố CI M7b khi chưa push.
