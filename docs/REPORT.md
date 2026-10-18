# Báo cáo triển khai backend P0

Đã triển khai và kiểm chứng 33 mã P0 cho backend MVP. Frontend chưa triển khai.
Code nằm trong project này; config local .env có secret sinh ngẫu nhiên và được Git bỏ qua.
Ngày kiểm chứng: 18/10/2026. Nguồn yêu cầu và các phần P1/P2 được giữ trong requirements.md.

## Kết quả thực tế

| Kiểm tra | Kết quả |
| --- | --- |
| Python / dependency | Python 3.12.5, uv sync --frozen thành công, có uv.lock |
| uv run pytest --cov | **77 passed**, 0 failed, 0 errors, 0 skipped; 55,65 giây |
| Coverage service/NLP | **95.67%**; gate 70% đạt |
| Coverage từng service / nlp | scripts/check_coverage.py đạt cho tất cả module P0 |
| uv run ruff check . | All checks passed |
| uv run ruff format --check . | 94 files already formatted |
| DB integration | Testcontainers pgvector/pgvector:pg16, Alembic, transaction rollback mỗi test |
| docker compose up --build -d | Build thành công; DB healthy; API running |
| Alembic trên DB Compose | 0001_p0 (head) |
| PostgreSQL extensions | pg_trgm, vector đều đã cài |
| GET /health | HTTP 200, status=ok, database=ok |
| GET /docs | HTTP 200; OpenAPI có 22 đường dẫn và các method P0 |
| Git | Commit sau khi toàn bộ pytest, coverage và Ruff xanh; không push remote |

Log lần chạy cuối ở verification/ (được Git bỏ qua); scripts/verify.ps1 tái chạy đầy đủ.
Lỗi quyền Docker của phiên đầu đã được giải quyết khi người dùng bật Full access.

| Thành phần | Coverage |
| --- | --- |
| app/modules/auth/service.py | 95.16% |
| app/modules/dictionary/service.py | 96.94% |
| app/modules/imports/service.py | 97.22% |
| app/modules/search/service.py | 97.06% |
| app/modules/textbooks/service.py | 92.25% |
| app/nlp/ | 98.11% |

## Bảng mã P0 và test chứng minh

Tất cả test dưới đây đã chạy thành công trên PostgreSQL thật. Fixture là dữ liệu nhỏ
tự biên soạn, không tải dataset từ điển thật trong test.

| Mã | Trạng thái | Test |
| --- | --- | --- |
| AUTH-01 | done | `test_AUTH_01_register_argon2` |
| AUTH-02 | done | `test_AUTH_02_login_expiry` |
| AUTH-03 | done | `test_AUTH_03_refresh_rotate_logout` |
| AUTH-04 | done | `test_AUTH_04_profile` |
| AUTH-05 | done | `test_AUTH_05_roles` |
| DICT-01 | done | `test_DICT_01_idempotent_seed` |
| DICT-02 | done | `test_DICT_02_normalization` |
| DICT-03 | done | `test_DICT_03_candidate_matching` |
| DICT-04 | done | `test_DICT_04_detail` |
| DICT-05 | done | `test_DICT_05_jlpt_labels` |
| DICT-06 | done | `test_DICT_06_kanji_hanviet` |
| DICT-07 | done | `test_DICT_07_breakdown` |
| TB-01 | done | `test_TB_01_crud_and_private` |
| TB-02 | done | `test_TB_02_lessons_crud` |
| TB-03 | done | `test_TB_03_entries_order_pagination` |
| TB-04 | done | `test_TB_04_full_blocks` |
| TB-05 | done | `test_TB_05_regenerate_search_text` |
| IMP-01 | done | `test_IMP_01_adapter_registry` |
| IMP-02 | done | `test_IMP_02_mimikara_edition` |
| IMP-03 | done | `test_IMP_03_csv_template` |
| IMP-04 | done | `test_IMP_04_validation_limits` |
| IMP-05 | done | `test_IMP_05_staging_lessons` |
| IMP-06 | done | `test_IMP_06_matching_states` |
| IMP-07 | done | `test_IMP_07_review_choose_skip_private` |
| IMP-08 | done | `test_IMP_08_atomic_rollback` |
| IMP-09 | done | `test_IMP_09_raw_preservation` |
| SRCH-01 | done | `test_SRCH_01_normalization_full_flow` |
| SRCH-02 | done | `test_SRCH_02_detect_query` |
| SRCH-03 | done | `test_SRCH_03_prefix_trigram` |
| SRCH-04 | done | `test_SRCH_04_returns_full_blocks` |
| SRCH-05 | done | `test_SRCH_05_private_visibility` |
| SRCH-06 | done | `test_SRCH_06_filters_rank` |
| SRCH-07 | done | `test_SRCH_07_first_ten_full_later_summary` |

Các kiểm tra bổ sung: test_NFR_06_search_rate_limit,
test_NFR_06_auth_and_import_limit, test_NFR_07_cors,
test_NFR_15_search_gzip_and_payload_budget, test_transaction_cleanup_error_prevents_success_response,
test_architecture_nlp_is_independent, test_textbook_delete_cascade_preserves_words.

## Milestone

| Chặng | Kết quả |
| --- | --- |
| Setup | Cấu trúc, env, lock, migration, Compose, health, Swagger đã kiểm chứng |
| Auth | AUTH-01..05 xanh: Argon2, JWT, refresh rotate/revoke, me, role |
| Dictionary | DICT-01..07 xanh: seed idempotent, normalize, match, Hán Việt, JLPT |
| Textbooks | TB-01..05 xanh: CRUD, phân quyền, block validation, search_text |
| Imports | IMP-01..09 xanh: adapter, staging, review, commit/rollback, raw |
| Search | SRCH-01..07 xanh: bốn loại truy vấn, privacy, filters/ranking, full blocks/summary |
| Hoàn thiện | 68 test, coverage, Ruff, CI config, README, DECISIONS và Compose |

Do Docker bị chặn trong phiên ban đầu, các chặng đầu chưa thể commit lúc đó. Sau khi
được cấp quyền, kiểm tra lại toàn bộ rồi commit bản MVP đã kiểm chứng trong một commit
tích hợp; lịch sử không mô phỏng các commit milestone chưa từng được kiểm tra riêng.
CI đã cấu hình cho GitHub; chưa có remote/push nên chưa có kết quả GitHub Actions.

## Giả định trong DECISIONS.md

1. Tài liệu Word được trích đầy đủ theo thứ tự sang requirements.md. Yêu cầu trực tiếp trong chat được ưu tiên khi khác tài liệu.
2. Mimikara chưa có nguồn thật: adapter đọc CSV/XLSX cột unit, no, word, reading, meaning_vi, examples, usage, collocations, synonyms, antonyms. Các cột danh sách là JSON; examples gồm ja/vi, usage là object context/variants/vi. Fixture là nội dung tự biên soạn. Edition lưu ở textbook, cùng adapter dùng cho cả hai edition.
3. Chưa xác định nguồn Hán Việt: chỉ đọc data/hanviet.csv (kanji,hanviet), nhiều âm phân cách bằng dấu |; không tải dữ liệu trong test.
4. P0 không cung cấp API thêm/sửa/xóa entry thủ công (TB-06 P1). TB-04/05 được thực hiện ở service nội bộ dùng chung pipeline import; GET entry vẫn có trong P0.
5. Không xây notebook, study, worker, embedding hay lemmatization P1/P2. Giữ thư mục và entrypoint giải thích hoãn. Vector nullable tồn tại trong schema; chưa tạo HNSW P2.
6. Search xếp exact trước prefix trước meaning; tie-break theo id. Latin thử chuyển romaji hợp lệ rồi đồng thời tìm nghĩa; tiếng Việt tìm nghĩa. Chỉ tìm nội dung entry đã được phép xem. 10 kết quả đầu toàn bộ tập có full content; các kết quả sau có summary và content=null.
7. Giới hạn payload search 200 KB được đo trên JSON UTF-8 trước gzip; entry quá lớn bị từ chối tại import để giữ tính đầy đủ; trang vượt ngân sách trả 422 yêu cầu giảm size thay vì cắt block.
8. Refresh token JWT có jti, chỉ lưu SHA-256 trong DB, rotate mỗi refresh và revoke khi logout. Không tự cấp role admin từ input; bootstrap admin qua CLI riêng.
9. Import staging tự tạo lesson trong bước upload như IMP-05; commit chỉ ghi words/entries trong savepoint nguyên tử, lỗi giữ staging và đánh dấu failed. Job đã done không commit lại.
10. Rate limit lưu bucket trong PostgreSQL để chia sẻ giữa process; dùng IP cho auth, user id cho search/import. Phải cấu hình reverse proxy tin cậy ở production; không tin X-Forwarded-For từ client.
11. License thương mại hoặc adapter mimikara bắt buộc private. Giáo trình public khác chỉ admin được tạo (kiểm tra an toàn dữ liệu P0, không tạo bộ JLPT public P1).
12. NFR hiệu năng trên 200.000 từ và giới hạn RAM cần benchmark môi trường deploy, không suy diễn từ fixture nhỏ. Backup mẫu dùng pg_dump, operator phải cấu hình scheduler và retention.
13. Lỗi commit trả HTTP 409 theo error envelope chung; trạng thái job failed được lưu sau rollback savepoint. Test kiểm tra cả HTTP status, envelope và DB không ghi entry/word mới.
14. romkan cũ không build được với Python 3.12 do import imp đã bị bỏ; dùng fork romkan2 tương thích, không thay đổi quy tắc chuyển âm.
15. Response giữ saved=false để tương thích mẫu (chưa có Sổ từ P1). Không tính/trả appears_in_examples vì đây là SRCH-10 P1; không ghi search_history SRCH-08 P1.
16. Session dependency dùng scope=function để commit/rollback xong trước khi gửi response thành công, theo [FastAPI dependencies with yield](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/). Vì vậy yêu cầu FastAPI >=0.121; có contract test lỗi ở teardown không trả 200.
17. Coverage phải theo dõi cả thread (asyncio.to_thread) và greenlet (SQLAlchemy async bridge). Lần đầu 67 test đều xanh nhưng các dòng sau await bị báo thiếu; cấu hình concurrency=[thread,greenlet] theo [coverage.py concurrency](https://coverage.readthedocs.io/en/7.16.2/config.html#run-concurrency) để đo đúng. Giữ nguyên toàn bộ test và ngưỡng 70%, không loại dòng khỏi coverage.

## Phần còn thiếu hoặc chưa kiểm chứng

- Mimikara thật: adapter hiện dựa trên format giả định, cần file nguồn hợp lệ để xác nhận
  các khác biệt format/edition. Fixture hoàn toàn tự bịa.
- Hán Việt: TODO nguồn thật và giấy phép; script chỉ đọc data/hanviet.csv.
- Đã seed tập con JMdict thật và import 4 PDF vào textbook private; xem PDF_IMPORT_REPORT.md.
  Kanjidic/JLPT thật và nguồn Hán Việt chưa bổ sung.
- Chưa benchmark p95/search với 200.000 từ, import 1.000 dòng dưới 30 giây, hoặc RAM
  512 MB trên hosting free. Các NFR hiệu năng này chưa được chứng minh bằng fixture nhỏ.
- Backup có script pg_dump; operator cần cấu hình lịch hằng ngày, retention, nơi lưu
  ngoài máy và thử restore ở môi trường triển khai.
- Frontend, P1/P2, worker, lemmatization, semantic search, Sổ từ và SRS nằm ngoài phạm vi.

Backend local đang chạy tại http://localhost:8000/docs. Definition of Done về chức năng
P0, test/coverage/lint, Compose và hướng dẫn chạy đã đạt; các điều kiện vận hành quy mô
thật kể trên cần được kiểm chứng khi chuẩn bị dataset/deploy.

## Cập nhật import PDF người dùng cung cấp

Đã thêm normalized_json adapter có test riêng và import dữ liệu thật vào DB private. Xem [báo cáo dữ liệu](PDF_IMPORT_REPORT.md) về số lượng, provenance và giới hạn OCR. Adapter Mimikara CSV/XLSX vẫn giữ format giả định; PDF được chuyển trước bằng OCR local.
