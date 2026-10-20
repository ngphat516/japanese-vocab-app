# Yêu cầu Backend – Web App Từ vựng Tiếng Nhật

Oct 18, 2026 · @kakushi

## 1. Tổng quan

Backend cho phép người dùng tra một từ tiếng Nhật và xem toàn bộ nội dung của từ đó trong từng giáo trình (nghĩa, câu ví dụ, cách dùng đúng/sai, cụm từ đi kèm), kèm Hán tự, âm Hán Việt và cấp JLPT. Người dùng lưu được từ đã tra vào Sổ từ và xuất ra Anki, CSV hoặc Markdown. Hệ thống ưu tiên chi phí vận hành gần bằng 0 và dễ bảo trì cho 1 người phát triển.

### 1.1. Mục tiêu

Gom từ vựng của nhiều giáo trình về một từ chuẩn duy nhất, bắt đầu với Mimikara Oboeru, sau đó Minna no Nihongo, Genki, Soumatome...

Hiển thị đầy đủ nội dung mục từ của mọi giáo trình, dù mỗi giáo trình có bố cục khác nhau.

Tìm kiếm linh hoạt bằng kanji, kana, romaji, nghĩa tiếng Việt và cả dạng đã chia (食べました → 食べる).

Hiển thị Hán tự và âm Hán Việt cạnh nghĩa khi từ có chữ Hán; gắn nhãn cấp JLPT.

Lưu lịch sử tra cứu và Sổ từ, xuất ra định dạng phổ biến thay vì tích hợp trực tiếp từng app.

Áp dụng NLP tiếng Nhật (tách từ, lemmatize, embedding) để tăng chất lượng tìm kiếm và matching.

### 1.2. Phạm vi

| Trong phạm vi (MVP → V3) | Ngoài phạm vi (hiện tại) |
| --- | --- |
| Auth, quản lý giáo trình và bài học | Module ngữ pháp |
| Seed JMdict, Kanjidic, nhãn JLPT, bảng Hán Việt | Audio phát âm |
| Nội dung mục từ dạng block, hiển thị đầy đủ | Tích hợp trực tiếp Obsidian/Notion |
| Import qua adapter: Mimikara trước, sau đó CSV/XLSX, Anki, văn bản tự do | App mobile riêng |
| Tìm kiếm có chuẩn hóa và lemmatize | Thanh toán, gói trả phí |
| Lịch sử tra cứu, Sổ từ, xuất Anki/CSV/Markdown | Chia sẻ giáo trình giữa người dùng |
| Học và ôn tập (SRS) theo giáo trình hoặc Sổ từ | Tính năng cộng đồng, bình luận |

### 1.3. Thuật ngữ

| Thuật ngữ | Ý nghĩa |
| --- | --- |
| Word (từ chuẩn) | Một mục từ duy nhất, xác định bằng cặp (kanji, kana), gắn với jmdict_id nếu có |
| Textbook (giáo trình) | Một bộ sách, có cấp độ, chủ sở hữu, chế độ hiển thị và nguồn dữ liệu |
| Lesson (bài) | Một bài hoặc một unit trong giáo trình |
| Entry (mục từ giáo trình) | Sự xuất hiện của một Word trong một Lesson, có số thứ tự và nội dung riêng |
| Block | Một phần nội dung của Entry có kiểu xác định: nghĩa, ví dụ, cách dùng, cụm từ... |
| Hán tự / Hán Việt | Các chữ Hán trong từ và âm Hán Việt tương ứng (緊 KHẨN, 張 TRƯƠNG) |
| Adapter | Đoạn code chuyển dữ liệu của một nguồn cụ thể (Mimikara, Anki...) về dạng chuẩn để import |
| Import job | Một lần nhập dữ liệu, đi qua các trạng thái từ chờ xử lý đến hoàn tất |
| Staging row | Một dòng dữ liệu đã parse, chờ người dùng xác nhận trước khi ghi thật |
| Sổ từ | Danh sách từ người dùng chủ động lưu, kèm ghi chú và tag |
| JMdict / Kanjidic | Từ điển Nhật và từ điển kanji mở, dùng làm nguồn từ chuẩn và chữ Hán |

## 2. Tech stack và ràng buộc chi phí

Backend dùng Python + FastAPI vì hệ sinh thái NLP tiếng Nhật của Python mạnh nhất, và toàn bộ hạ tầng chỉ xoay quanh một PostgreSQL để không phát sinh thêm dịch vụ trả phí.

| Thành phần | Lựa chọn | Lý do |
| --- | --- | --- |
| Ngôn ngữ | Python 3.12 | NLP tiếng Nhật, dễ tích hợp AI |
| Framework | FastAPI | Async, tự sinh Swagger tại /docs |
| Validate | Pydantic v2 | Đi kèm FastAPI; validate block nội dung bằng discriminated union |
| ORM | SQLAlchemy 2.0 | Chuẩn, type hint tốt |
| Migration | Alembic | Quản lý phiên bản schema |
| Database | PostgreSQL + pg_trgm + pgvector | Dữ liệu quan hệ, JSONB cho nội dung block, tìm theo nghĩa, semantic search |
| Queue / worker | Procrastinate | Queue chạy trên Postgres, không cần Redis |
| Auth | JWT tự phát hành (hoặc Supabase Auth) | Không phụ thuộc dịch vụ ngoài |
| Lưu file import | Supabase Storage hoặc Cloudflare R2 | Free tier, chuẩn S3 |
| NLP | SudachiPy (từ điển core), cutlet/pykakasi, jaconv | Tách từ, lemmatize, sinh furigana, chuyển kana/romaji |
| Embedding | intfloat/multilingual-e5-small hoặc API embedding | Đa ngôn ngữ Việt–Nhật, chạy được trên CPU |
| Quản lý package | uv | Nhanh, lock file rõ ràng |
| Test | pytest + httpx | Test service và endpoint |
| Lint / format | Ruff | Một công cụ thay cho nhiều công cụ |
| Deploy | Docker, chạy trên Render / Railway / Fly.io | Deploy từ GitHub, có free tier |
| Dữ liệu từ điển | jmdict-simplified (JMdict + Kanjidic dạng JSON), bảng Hán Việt | Từ chuẩn, thông tin chữ Hán và âm Hán Việt |
| Xuất dữ liệu | genanki, csv, Markdown tự sinh | Xuất Sổ từ sang Anki, Excel/Quizlet, Obsidian/Notion |

### 2.1. Ràng buộc chi phí

Không dùng dịch vụ trả phí ở giai đoạn MVP; mọi thành phần phải có free tier hoặc tự host được.

Không thêm Redis, Elasticsearch hay Meilisearch khi Postgres còn đáp ứng được.

Embedding chỉ tính khi import (trong worker) và lưu vào pgvector; lúc tìm kiếm chỉ embed câu truy vấn ngắn.

Nếu RAM của gói free không đủ cho model embedding, chuyển embedding sang API, giữ Sudachi chạy local.

## 3. Kiến trúc hệ thống

Hệ thống là một modular monolith: một codebase, chia module theo nghiệp vụ, chạy thành hai process là API và worker. Không tách microservice ở giai đoạn này.

kiến trúc backend · API, worker, PostgreSQL

API nhận request và đẩy việc nặng (parse file, tách từ, embedding) sang worker qua queue trong Postgres. Ở MVP, import chạy đồng bộ ngay trong API, chưa cần worker.

### 3.1. Cấu trúc thư mục

backend/├── pyproject.toml├── alembic.ini├── alembic/│   ├── env.py│   └── versions/├── scripts/│   ├── seed_jmdict.py     # từ chuẩn + Kanjidic│   ├── seed_jlpt.py       # nhãn JLPT N5–N1│   └── seed_hanviet.py    # bảng kanji → âm Hán Việt├── tests/└── app/    ├── main.py            # khởi tạo FastAPI, gắn router    ├── worker.py          # entrypoint worker    ├── models.py          # chỉ import model các module cho Alembic    ├── core/              # config, exceptions, logging, security    ├── db/                # base.py, session.py    ├── common/            # pagination, schema dùng chung    ├── nlp/               # tokenizer.py, reading.py, normalize.py, furigana.py, embedding.py    ├── jobs/              # import_job.py    └── modules/        ├── auth/          # đăng ký, đăng nhập, người dùng        ├── dictionary/    # từ chuẩn, kanji, Hán Việt, nhãn JLPT        ├── textbooks/     # giáo trình, bài, mục từ, block nội dung (blocks.py)        ├── search/        # tìm kiếm (chỉ đọc)        ├── imports/       # upload, staging, review, commit        │   └── adapters/  # mimikara.py, csv_template.py, anki_apkg.py, free_text.py        ├── notebook/      # lịch sử tra cứu, Sổ từ, bộ sưu tập, xuất dữ liệu        └── study/         # trạng thái học, SRS, tiến độ

Mỗi module gồm models.py, schemas.py, service.py, router.py, và dependencies.py khi cần.

### 3.2. Quy tắc phụ thuộc

Luồng gọi một chiều: router → service → models/db; service được phép gọi nlp/.

Router chỉ validate input và gọi service, không chứa logic nghiệp vụ.

Module này chỉ gọi module khác qua service, không import router hay truy cập trực tiếp model của module khác.

nlp/ không import gì từ modules/ hay db/, để test độc lập và dễ thay thư viện.

search chỉ đọc dữ liệu; mọi thao tác ghi đi qua dictionary, textbooks hoặc imports.

## 4. Mô hình dữ liệu

Điểm cốt lõi của schema là tách từ chuẩn (words) khỏi mục từ trong giáo trình (textbook_entries): một từ chuẩn có nhiều mục từ, mỗi mục từ thuộc một bài của một giáo trình.

### 4.1. Các bảng

| Bảng | Module | Cột chính | Ghi chú |
| --- | --- | --- | --- |
| users | auth | id, email, password_hash, display_name, role, created_at | role: user / admin |
| words | dictionary | id, jmdict_id, kanji, kana, kana_norm, romaji, hanviet, pos, jlpt_level, embedding (vector) | Unique (kanji, kana); jmdict_id null với từ tự tạo; hanviet sinh tự động, sửa tay được |
| word_senses | dictionary | id, word_id, lang, gloss, order | Nghĩa gốc từ JMdict (en, có thể thêm vi) |
| kanji | dictionary | char (PK), hanviet (text[]), meaning, strokes, jlpt_level | Từ Kanjidic + bảng Hán Việt; chữ nhiều âm lưu mảng (楽 → LẠC, NHẠC) |
| textbooks | textbooks | id, name, publisher, level, edition, visibility, owner_id, license, source_url, created_at | visibility: private / public; edition phân biệt bản cũ và 改訂版 |
| lessons | textbooks | id, textbook_id, number, title | Unique (textbook_id, number); Mimikara: một unit là một lesson |
| textbook_entries | textbooks | id, word_id, lesson_id, order_no, content (jsonb), search_text, created_at | Unique (word_id, lesson_id); order_no = số thứ tự trong sách (357); content = danh sách block (mục 4.5) |
| import_jobs | imports | id, user_id, textbook_id, adapter, file_key, status, total, matched, ambiguous, failed, error, created_at | adapter: mimikara, csv_template, anki_apkg, free_text |
| import_rows | imports | id, job_id, row_no, raw (jsonb), kanji, kana, lesson_no, order_no, content (jsonb), match_status, candidate_word_ids, chosen_word_id | Bảng staging; content đã map sang block |
| search_history | notebook | id, user_id, word_id, query, searched_at | Lưu khi user mở chi tiết một từ; giữ 500 dòng gần nhất mỗi user |
| saved_words | notebook | id, user_id, word_id, note, tags (text[]), created_at | Unique (user_id, word_id) |
| collections | notebook | id, user_id, name, created_at | Bộ sưu tập do user tự đặt tên |
| collection_words | notebook | collection_id, saved_word_id | Bảng nối |
| study_items | study | id, user_id, entry_id hoặc saved_word_id, ease, interval_days, due_at, reps, lapses | Trạng thái SRS |
| review_logs | study | id, study_item_id, rating, reviewed_at | Lịch sử ôn tập, dùng để tính tiến độ |

### 4.2. Giá trị trạng thái

import_jobs.status: pending → processing → review → committing → done, hoặc failed.

import_rows.match_status: auto (khớp đúng 1 từ), ambiguous (nhiều ứng viên), none (không khớp, sẽ tạo từ mới), skipped (người dùng bỏ qua).

review_logs.rating: again, hard, good, easy.

### 4.3. Index bắt buộc

words(kanji text_pattern_ops) và words(kana_norm text_pattern_ops) cho tìm theo tiền tố.

GIN (gloss gin_trgm_ops) trên word_senses và GIN (search_text gin_trgm_ops) trên textbook_entries cho tìm theo nghĩa và tìm trong câu ví dụ.

HNSW (embedding vector_cosine_ops) trên words cho semantic search (V3).

textbook_entries(word_id), textbook_entries(lesson_id, order_no), study_items(user_id, due_at).

search_history(user_id, searched_at desc), saved_words(user_id, created_at desc).

### 4.4. Quy tắc dữ liệu

kana_norm luôn là hiragana, đã bỏ khoảng trắng và ký tự đặc biệt; được sinh trong service, không nhận từ client.

search_text được sinh lại mỗi khi content thay đổi: gộp text của mọi block, bỏ cú pháp furigana và gạch chân, thêm dạng từ điển (lemma) của các từ trong câu ví dụ.

words.hanviet sinh từ bảng kanji khi seed hoặc tạo từ mới; chữ nhiều âm lấy âm đầu tiên, admin sửa tay được.

Xóa giáo trình sẽ xóa cascade bài học và mục từ, nhưng không xóa words.

Chỉ admin được tạo giáo trình public. Giáo trình private chỉ chủ sở hữu thấy và sửa được.

### 4.5. Nội dung mục từ dạng block

Mỗi giáo trình có bố cục riêng, nên textbook_entries.content lưu nội dung thành danh sách block có kiểu. Adapter của từng nguồn map dữ liệu về các block này; frontend có một component cho mỗi loại block nên giáo trình nào cũng hiển thị đầy đủ.

| Block | Trường | Dùng cho |
| --- | --- | --- |
| meaning | vi, en | Nghĩa của từ trong giáo trình |
| example | ja, vi | Câu ví dụ và bản dịch, đánh dấu từ đích |
| usage | context, variants[{ja, correct}], vi | So sánh cách dùng đúng/sai (○/×) |
| collocation | items[], vi | Cụm từ hay đi kèm (連) |
| synonym / antonym / related | items[{text, word_id?}] | Từ đồng nghĩa (類), trái nghĩa (対), liên quan (合) |
| note | text | Ghi chú tự do |
| raw | data (jsonb) | Trường không map được, kể cả tên file âm thanh; không làm mất dữ liệu nguồn |

Quy ước định dạng trong các trường tiếng Nhật:

漢字[よみ] là furigana (cùng cú pháp với Anki). Nguồn không có furigana thì nlp/furigana.py sinh bằng Sudachi.

{{...}} là phần gạch chân, tức từ đích trong câu.

Ví dụ một mục từ Mimikara:

{  "order_no": 357,  "content": [    { "type": "meaning", "vi": "Căng thẳng, lo lắng" },    { "type": "example",      "ja": "面接[めんせつ]では{{緊張[きんちょう]して}}、うまく答[こた]えられなかった",      "vi": "Tôi đã căng thẳng trong buổi phỏng vấn và không thể trả lời trôi chảy được." },    { "type": "usage",      "context": "試合[しあい]の前[まえ]なので、みんな",      "variants": [        { "ja": "{{緊張[きんちょう]して}}いる", "correct": true },        { "ja": "緊張[きんちょう]だ", "correct": false }      ],      "vi": "Vì là trước trận đấu nên mọi người đều căng thẳng." },    { "type": "collocation",      "items": ["__がとける", "__が高[たか]まる", "__がゆるむ"],      "vi": "Căng thẳng giải tỏa, căng thẳng tăng lên, căng thẳng giảm bớt" }  ]}

Block được validate bằng Pydantic discriminated union theo trường type; dữ liệu sai cấu trúc bị chặn ngay ở bước import. Âm Hán Việt và Hán tự không nằm trong block mà lấy từ words và kanji, để mọi giáo trình dùng chung.

### 4.6. Nguồn dữ liệu

| Nguồn | Dùng cho | Hiển thị | Ưu tiên |
| --- | --- | --- | --- |
| jmdict-simplified | Từ chuẩn (JMdict) và chữ Hán (Kanjidic) | public | P0 |
| Bluskyo/JLPT_Vocabulary hoặc OpenJLPT | Nhãn JLPT N5–N1 cho từ và giáo trình "JLPT Nx" | public | P0 |
| Bảng kanji → âm Hán Việt | kanji.hanviet, words.hanviet | public | P0 (nguồn cụ thể còn cần tìm) |
| Mimikara Oboeru N3/N2/N1 | Giáo trình đầu tiên, qua adapter mimikara | private | P0 (file nguồn do người dùng cung cấp) |
| Minna no Nihongo, Genki, Soumatome... | Các giáo trình tiếp theo | private | P1 |

Dữ liệu giáo trình thương mại (Mimikara, Minna...) có bản quyền của nhà xuất bản: mặc định để private, ghi rõ license và source_url, chỉ dùng phi thương mại.

## 5. Yêu cầu chức năng

Mỗi yêu cầu có mã để tham chiếu khi viết task và test. Mức ưu tiên: P0 bắt buộc cho MVP, P1 cho V2, P2 cho V3.

### 5.1. Auth (auth)

| Mã | Yêu cầu | Ưu tiên |
| --- | --- | --- |
| AUTH-01 | Đăng ký bằng email và mật khẩu; mật khẩu băm bằng Argon2 hoặc bcrypt | P0 |
| AUTH-02 | Đăng nhập trả về access token (JWT, sống 15 phút) và refresh token (7 ngày) | P0 |
| AUTH-03 | Làm mới access token bằng refresh token; đăng xuất thu hồi refresh token | P0 |
| AUTH-04 | Lấy và cập nhật thông tin cá nhân (/me) | P0 |
| AUTH-05 | Phân quyền theo role user / admin qua dependency | P0 |

### 5.2. Từ điển (dictionary)

| Mã | Yêu cầu | Ưu tiên |
| --- | --- | --- |
| DICT-01 | Script seed JMdict vào words và word_senses, chạy lại được mà không tạo trùng | P0 |
| DICT-02 | Sinh kana_norm và romaji cho mọi từ khi seed và khi tạo mới | P0 |
| DICT-03 | Hàm match(kanji, kana) trả về danh sách từ ứng viên, dùng cho import | P0 |
| DICT-04 | Xem chi tiết một từ kèm nghĩa gốc | P0 |
| DICT-05 | Gắn nhãn cấp JLPT (N5–N1) từ danh sách mở; từ không có trong danh sách để null ("Ngoài JLPT") | P0 |
| DICT-06 | Seed bảng kanji từ Kanjidic và bảng âm Hán Việt | P0 |
| DICT-07 | Sinh words.hanviet và kanji_breakdown (từng chữ Hán + âm Hán Việt) cho mọi từ có chữ Hán; bỏ qua okurigana, từ toàn kana trả mảng rỗng | P0 |
| DICT-08 | Admin sửa tay âm Hán Việt của một từ khi chữ có nhiều âm | P1 |
| DICT-09 | Trang chi tiết một chữ Hán: nghĩa, số nét, các từ chứa chữ đó | P1 |
| DICT-10 | Tính và lưu embedding cho từ, dùng cho semantic search và gợi ý matching | P2 |

### 5.3. Giáo trình (textbooks)

| Mã | Yêu cầu | Ưu tiên |
| --- | --- | --- |
| TB-01 | CRUD giáo trình (kèm edition, license, source_url); người dùng chỉ thao tác trên giáo trình của mình | P0 |
| TB-02 | CRUD bài học/unit trong giáo trình | P0 |
| TB-03 | Xem danh sách mục từ theo bài, sắp theo order_no, có phân trang | P0 |
| TB-04 | Lưu nội dung mục từ dạng danh sách block (mục 4.5), validate bằng Pydantic trước khi ghi | P0 |
| TB-05 | Sinh lại search_text mỗi khi nội dung mục từ thay đổi | P0 |
| TB-06 | Thêm, sửa, xóa một mục từ thủ công (chọn từ chuẩn có sẵn hoặc tạo mới) | P1 |
| TB-07 | Tự sinh furigana cho câu tiếng Nhật thiếu cú pháp 漢字[よみ] | P1 |
| TB-08 | Admin tạo giáo trình public dùng chung (JLPT N5–N1) | P1 |

### 5.4. Tìm kiếm (search)

| Mã | Yêu cầu | Ưu tiên |
| --- | --- | --- |
| SRCH-01 | Chuẩn hóa truy vấn: katakana → hiragana, romaji → kana, bỏ khoảng trắng | P0 |
| SRCH-02 | Tự nhận diện loại truy vấn (có kanji, toàn kana, chữ Latin/tiếng Việt) để chọn cột tìm | P0 |
| SRCH-03 | Tìm theo tiền tố trên kanji và kana_norm; tìm theo nghĩa bằng trigram | P0 |
| SRCH-04 | Kết quả gom theo từ chuẩn; mỗi từ trả Hán tự, Hán Việt, cấp JLPT và toàn bộ nội dung block của từng giáo trình (không chỉ vị trí bài) | P0 |
| SRCH-05 | Chỉ trả về mục từ thuộc giáo trình public hoặc của chính người dùng | P0 |
| SRCH-06 | Lọc theo giáo trình, cấp JLPT; xếp hạng: khớp chính xác trước, tiền tố sau, nghĩa cuối | P0 |
| SRCH-07 | Trả đầy đủ block cho 10 kết quả đầu; kết quả sau chỉ trả tóm tắt, lấy chi tiết qua /words/{id} | P0 |
| SRCH-08 | Ghi lịch sử tra cứu khi người dùng mở chi tiết một từ | P1 |
| SRCH-09 | Lemmatize bằng Sudachi để tìm được dạng đã chia (行かなかった → 行く) | P1 |
| SRCH-10 | Đếm và liệt kê câu ví dụ ở mục từ khác có chứa từ đang tra (appears_in_examples) | P1 |
| SRCH-11 | Semantic search theo nghĩa bằng pgvector khi tìm thường ít kết quả | P2 |

### 5.5. Import (imports)

| Mã | Yêu cầu | Ưu tiên |
| --- | --- | --- |
| IMP-01 | Kiến trúc adapter: mỗi nguồn có một adapter chuyển dữ liệu về dạng chuẩn (kanji, kana, lesson_no, order_no, content[]) rồi đi chung pipeline | P0 |
| IMP-02 | Adapter mimikara: map unit → lesson, số thứ tự → order_no, nghĩa/ví dụ/○×/連/類/対 → block tương ứng; hỗ trợ cả bản cũ và 改訂版 qua edition | P0 |
| IMP-03 | Adapter csv_template: CSV/XLSX theo template cột lesson, order, kanji, kana, meaning_vi, meaning_en, example_ja, example_vi, note | P0 |
| IMP-04 | Kiểm tra dữ liệu trước khi xử lý: định dạng, kích thước tối đa 5 MB, tối đa 5.000 dòng, cột bắt buộc | P0 |
| IMP-05 | Ghi từng dòng vào import_rows, tự tạo bài học nếu chưa có | P0 |
| IMP-06 | Matching từng dòng với từ chuẩn, gán auto / ambiguous / none | P0 |
| IMP-07 | Người dùng xem và chọn từ đúng cho dòng ambiguous, hoặc bỏ qua dòng | P0 |
| IMP-08 | Commit trong một transaction: tạo từ mới cho dòng none, ghi textbook_entries; lỗi thì rollback toàn bộ | P0 |
| IMP-09 | Trường không map được (kể cả âm thanh) đưa vào block raw, không làm mất dữ liệu | P0 |
| IMP-10 | Xử lý bất đồng bộ bằng worker, client theo dõi tiến độ qua trạng thái job | P1 |
| IMP-11 | Adapter anki_apkg với bước chọn trường tương ứng; giữ nguyên cú pháp furigana của Anki | P1 |
| IMP-12 | Adapter free_text: tách từ đoạn văn, lọc loại từ, đề xuất danh sách từ vựng | P1 |
| IMP-13 | Dùng embedding của nghĩa để xếp hạng ứng viên cho dòng ambiguous | P2 |

### 5.6. Sổ từ (notebook)

| Mã | Yêu cầu | Ưu tiên |
| --- | --- | --- |
| NB-01 | Xem và xóa lịch sử tra cứu (giữ tối đa 500 dòng mỗi người dùng) | P1 |
| NB-02 | Lưu từ vào Sổ từ kèm ghi chú và tag; mỗi từ chỉ lưu một lần | P1 |
| NB-03 | Lọc Sổ từ theo cấp JLPT, tag, giáo trình; thống kê số từ theo từng cấp | P1 |
| NB-04 | Trả jlpt_level cho mọi từ; màu do frontend quyết định (N1 đỏ, N2 cam, N3 xanh dương, N4 xanh lá, N5 tím, ngoài JLPT xám), badge luôn kèm chữ "N1"… | P1 |
| NB-05 | Bộ sưu tập: tạo, đổi tên, thêm/bớt từ | P1 |
| NB-06 | Xuất Sổ từ hoặc một bộ sưu tập ra Anki .apkg, CSV, Markdown (.zip, mỗi từ một file có frontmatter) | P1 |
| NB-07 | Đưa từ trong Sổ từ vào danh sách ôn tập SRS | P2 |

### 5.7. Học và tiến độ (study)

| Mã | Yêu cầu | Ưu tiên |
| --- | --- | --- |
| STD-01 | Thêm cả bài, cả giáo trình hoặc từ trong Sổ từ vào danh sách học | P2 |
| STD-02 | Lấy danh sách thẻ đến hạn ôn, chấm điểm và cập nhật lịch theo thuật toán SM-2 | P2 |
| STD-03 | Thống kê tiến độ: số từ đã học, đến hạn, tỷ lệ nhớ theo giáo trình | P2 |

## 6. Danh sách API

Tất cả endpoint có tiền tố /api/v1, trả JSON, dùng header Authorization: Bearer <token> trừ các endpoint đăng ký, đăng nhập và làm mới token.

| Method | Endpoint | Mô tả | Quyền | Mã yêu cầu |
| --- | --- | --- | --- | --- |
| POST | /auth/register | Đăng ký | Công khai | AUTH-01 |
| POST | /auth/login | Đăng nhập, trả token | Công khai | AUTH-02 |
| POST | /auth/refresh | Làm mới access token | Công khai | AUTH-03 |
| POST | /auth/logout | Thu hồi refresh token | User | AUTH-03 |
| GET / PATCH | /me | Xem, sửa thông tin cá nhân | User | AUTH-04 |
| GET | /search | Tìm từ: q, textbook_ids, jlpt, page, size; trả đầy đủ block | User | SRCH-01 → 11 |
| GET | /words/{id} | Chi tiết từ chuẩn: Hán tự, Hán Việt, JLPT, mọi mục từ giáo trình; ghi lịch sử | User | DICT-04, DICT-07, SRCH-08 |
| GET | /words/{id}/examples | Câu ví dụ ở mục từ khác có chứa từ này | User | SRCH-10 |
| PATCH | /words/{id} | Sửa âm Hán Việt | Admin | DICT-08 |
| GET | /kanji/{char} | Chi tiết chữ Hán và các từ chứa nó | User | DICT-09 |
| GET / POST | /textbooks | Danh sách, tạo giáo trình | User | TB-01 |
| GET / PATCH / DELETE | /textbooks/{id} | Xem, sửa, xóa giáo trình | Chủ sở hữu | TB-01 |
| GET / POST | /textbooks/{id}/lessons | Danh sách, tạo bài học | Chủ sở hữu | TB-02 |
| PATCH / DELETE | /lessons/{id} | Sửa, xóa bài học | Chủ sở hữu | TB-02 |
| GET / POST | /lessons/{id}/entries | Danh sách, thêm mục từ | Chủ sở hữu | TB-03, TB-06 |
| GET / PATCH / DELETE | /entries/{id} | Xem, sửa nội dung block, xóa mục từ | Chủ sở hữu | TB-04, TB-06 |
| GET | /imports/adapters | Danh sách adapter và định dạng mỗi adapter nhận | User | IMP-01 |
| GET | /imports/template | Tải file CSV mẫu | User | IMP-03 |
| POST | /imports | Upload file + chọn adapter, tạo import job | User | IMP-01 → 05 |
| GET | /imports/{id} | Trạng thái và thống kê job | Chủ sở hữu | IMP-10 |
| GET | /imports/{id}/rows | Danh sách dòng, lọc theo match_status | Chủ sở hữu | IMP-07 |
| PATCH | /imports/{id}/rows/{row_id} | Chọn từ đúng hoặc bỏ qua dòng | Chủ sở hữu | IMP-07 |
| POST | /imports/{id}/commit | Ghi dữ liệu chính thức | Chủ sở hữu | IMP-08 |
| GET / DELETE | /history | Xem, xóa lịch sử tra cứu | User | NB-01 |
| GET / POST | /saved-words | Sổ từ (lọc jlpt, tag, textbook_id), lưu từ | User | NB-02, NB-03 |
| PATCH / DELETE | /saved-words/{id} | Sửa ghi chú, tag; bỏ lưu | User | NB-02 |
| GET | /saved-words/stats | Số từ đã lưu theo cấp JLPT | User | NB-03 |
| GET / POST | /collections | Danh sách, tạo bộ sưu tập | User | NB-05 |
| PATCH / DELETE | /collections/{id} | Đổi tên, xóa bộ sưu tập | User | NB-05 |
| POST / DELETE | /collections/{id}/words | Thêm, bớt từ | User | NB-05 |
| GET | /saved-words/export?format=anki\|csv\|markdown&collection_id= | Xuất dữ liệu | User | NB-06 |
| POST | /study/items | Thêm bài, giáo trình hoặc từ trong Sổ từ vào danh sách học | User | STD-01, NB-07 |
| GET | /study/due | Lấy thẻ đến hạn ôn | User | STD-02 |
| POST | /study/items/{id}/review | Chấm điểm một thẻ | User | STD-02 |
| GET | /study/stats | Thống kê tiến độ | User | STD-03 |
| GET | /health | Kiểm tra API và kết nối DB | Công khai | — |

### 6.1. Định dạng phản hồi

Kết quả /search:

{  "items": [    {      "word": {        "id": 1024, "kanji": "緊張", "kana": "きんちょう", "romaji": "kinchou",        "jlpt_level": "N3", "hanviet": "KHẨN TRƯƠNG",        "kanji_breakdown": [          { "char": "緊", "hanviet": "KHẨN" },          { "char": "張", "hanviet": "TRƯƠNG" }        ],        "saved": false      },      "entries": [        {          "textbook": "Mimikara Oboeru N3", "lesson": "Unit 5", "order_no": 357,          "content": [            { "type": "meaning", "vi": "Căng thẳng, lo lắng" },            { "type": "example", "ja": "面接[めんせつ]では{{緊張[きんちょう]して}}、…", "vi": "…" },            { "type": "usage", "variants": [ { "ja": "…", "correct": true }, { "ja": "…", "correct": false } ] },            { "type": "collocation", "items": ["__がとける", "__が高[たか]まる", "__がゆるむ"], "vi": "…" }          ]        }      ],      "appears_in_examples": 12    }  ],  "page": 1,  "size": 20,  "total": 1}

Frontend hiển thị nghĩa kèm Hán tự ngay cạnh: » Căng thẳng, lo lắng   緊 KHẨN · 張 TRƯƠNG. Khi kanji_breakdown rỗng (từ toàn kana) thì chỉ hiện nghĩa. Mỗi giáo trình là một thẻ/tab riêng với đầy đủ block.

Lỗi dùng chung một dạng, mã HTTP phản ánh loại lỗi (400, 401, 403, 404, 409, 422, 500):

{ "error": { "code": "IMPORT_FILE_TOO_LARGE", "message": "File vượt quá 5 MB", "details": {} } }

## 7. Yêu cầu phi chức năng

Các chỉ tiêu dưới đây áp dụng cho dữ liệu cỡ JMdict (khoảng 200.000 từ) chạy trên gói free của nhà cung cấp hosting.

| Mã | Nhóm | Yêu cầu |
| --- | --- | --- |
| NFR-01 | Hiệu năng | /search không semantic có p95 < 300 ms khi tuần tự và < 600 ms ở 10 request đồng thời, đo bằng uvicorn qua HTTP thật trên môi trường deploy; ASGITransport chỉ dùng để so sánh trước/sau |
| NFR-02 | Hiệu năng | Import 1.000 dòng xong bước matching trong dưới 30 giây |
| NFR-03 | Tài nguyên | API chạy được với 512 MB RAM khi đã nạp Sudachi bản core |
| NFR-04 | Bảo mật | Mật khẩu băm Argon2/bcrypt; JWT ký bằng secret lấy từ biến môi trường |
| NFR-05 | Bảo mật | Kiểm tra quyền sở hữu ở tầng service cho mọi thao tác ghi và đọc dữ liệu private |
| NFR-06 | Bảo mật | Giới hạn tần suất: 60 request/phút cho /search, 10 request/phút cho /auth/* và /imports |
| NFR-07 | Bảo mật | CORS chỉ cho phép domain frontend; không trả stack trace ra client |
| NFR-08 | Dữ liệu | Mọi thay đổi schema đi qua Alembic; không sửa migration đã chạy trên production |
| NFR-09 | Dữ liệu | Backup DB hằng ngày (dùng backup của nhà cung cấp hoặc pg_dump định kỳ) |
| NFR-10 | Chất lượng | Test coverage của service và nlp/ từ 70% trở lên; CI chạy Ruff và pytest trên mỗi pull request |
| NFR-11 | Vận hành | Log dạng JSON có request id; endpoint /health cho nhà cung cấp hosting kiểm tra |
| NFR-12 | Vận hành | Cấu hình hoàn toàn qua biến môi trường; có file .env.example |
| NFR-13 | Tài liệu | Swagger tại /docs luôn khớp với code; README hướng dẫn chạy local bằng Docker Compose |
| NFR-14 | Pháp lý | Ghi nguồn JMdict, Kanjidic và danh sách JLPT theo giấy phép của từng nguồn; dữ liệu giáo trình có bản quyền chỉ ở chế độ private của người import |
| NFR-15 | Hiệu năng | Một trang kết quả /search (kèm đầy đủ block) không vượt quá 200 KB; bật nén gzip |
| NFR-16 | Mở rộng | Thêm giáo trình mới chỉ cần viết một adapter; thêm loại block mới không làm vỡ dữ liệu cũ (block lạ hiển thị dạng raw) |
| NFR-17 | Hiệu năng | Xuất Sổ từ 1.000 từ ra Anki/CSV/Markdown trong dưới 10 giây |

## 8. Lộ trình phát triển

Dự án chia làm 3 giai đoạn, ứng với mức ưu tiên P0, P1, P2 ở mục 5. Chỉ chuyển sang giai đoạn sau khi đạt đủ tiêu chí hoàn thành của giai đoạn trước.

lộ trình · 3 giai đoạn

Giai đoạn 1 đã đủ để dùng thật và đưa vào portfolio; NLP và semantic search là phần nâng cấp, không chặn việc ra mắt.

### 8.1. Việc cần làm cho MVP

☐ Khởi tạo project với uv, FastAPI, SQLAlchemy, Alembic, Docker Compose

☐ Viết model và migration đầu tiên cho các bảng P0

☐ Module auth (AUTH-01 → 05)

☐ Script seed JMdict, Kanjidic, nhãn JLPT, bảng Hán Việt (DICT-01 → 07)

☐ Định nghĩa block Pydantic và sinh search_text (TB-04, TB-05)

☐ Module textbooks (TB-01 → 03)

☐ Adapter mimikara + pipeline import đồng bộ (IMP-01, 02, 04 → 09); chờ file nguồn Mimikara

☐ Adapter csv_template (IMP-03)

☐ Module search trả đầy đủ block, Hán tự, Hán Việt, JLPT (SRCH-01 → 07)

☐ CI với Ruff + pytest, deploy lên môi trường free
