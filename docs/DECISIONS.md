# Quyết định triển khai P0

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
