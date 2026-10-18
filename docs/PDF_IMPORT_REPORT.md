# Báo cáo chuyển PDF và import dữ liệu local

Ngày kiểm chứng: 18/10/2026. Đã OCR local 830/830 trang của 4 PDF khác nhau; hai file Shinkanzen GOI trùng SHA-256 nên chỉ xử lý một bản.

## Số liệu từ database sau import

| Sách | Textbook ID | Trang PDF | Mục theo trang | Lesson | Visibility |
| --- | ---: | ---: | ---: | ---: | --- |
| Mimi Kara Oboeru N3 - Goi (PDF OCR) | 1 | 236 | 840 | 131 | private |
| Shinkanzen N3 - Goi (PDF OCR) | 2 | 186 | 2158 | 153 | private |
| Shinkanzen N3 - Kanji (từ trích xuất từ PDF) | 3 | 192 | 4649 | 174 | private |
| Shinkanzen N3 - Dokkai (từ trích xuất từ bài đọc) | 4 | 216 | 4259 | 194 | private |

Tổng **11,906 mục theo trang**. Dictionary có 3,367 cặp từ/cách đọc. Một từ có thể xuất hiện trên nhiều trang hoặc sách; số mục không phải số từ duy nhất.

## Cách chuyển và giới hạn

- Mimikara: giữ số mục in trên sách; đã đối chiếu 842/880 số mục, còn 38 số mục chưa xác định chắc từ/cách đọc. Các số này nằm trong `data/pdf_imports/mimikara_missing_order_nos.json`; chưa nhập dữ liệu đoán.
- Mỗi lesson tương ứng số trang PDF, không suy đoán unit. Một số mục Mimikara chỉ khôi phục được từ chỉ mục cuối sách nên chưa tách đủ ví dụ/collocation; raw block ghi rõ trường hợp này.
- Shinkanzen GOI, Kanji và Dokkai là **chỉ mục từ tự động trích từ câu tiếng Nhật theo trang**, đối chiếu JMdict. Đây chưa phải bản số hóa chính xác toàn bộ bài học, câu hỏi hoặc danh sách từ của nhà xuất bản.
- OCR dùng PaddleOCR 3.3.2 / PP-OCRv5 chạy Docker trên máy. Mọi mục OCR được đánh dấu `ocr_review_required=true`. Có thể sai chữ, dấu câu, ghép dòng, tách block hoặc chọn nghĩa không đúng ngữ cảnh.
- Nghĩa tiếng Anh từ PDF khi trích được, nếu không thì từ JMdict; nguồn nằm trong raw block. Không tạo bản dịch Việt, âm Hán Việt hoặc JLPT cho từng từ khi thiếu nguồn. Level N3 chỉ là metadata sách.
- Nội dung PDF được import private theo yêu cầu của chủ file. Bản PDF không chứng minh giấy phép phân phối lại. Nguồn PDF, OCR, JSON, credentials và backup được Git bỏ qua.

## Dữ liệu và truy cập

- `data/pdf_imports/access.json`: tài khoản chủ sở hữu local để login API; giữ riêng file này.
- `data/pdf_imports/*_n3.json`: rows chuẩn hóa với content block, số trang và SHA-256 nguồn.
- `data/pdf_imports/*_pages.jsonl`: OCR toàn bộ trang, confidence và bounding box để rà soát; giữ cả dòng chưa lập mục từ.
- `data/pdf_imports/review_required.json` và `mimikara_missing_order_nos.json`: các vấn đề OCR và số mục cần rà soát.
- `data/pdf_imports/import_receipt.json`: textbook/job ID và SHA-256 từng payload; số dòng commit lũy kế bao gồm lượt upsert, không dùng để tính số entry hiện tại.
- `data/pdf_imports/live_verification.json`: số entry thực tế và kết quả search sau import.
- API / Swagger đang chạy: http://localhost:8000/docs. Frontend chưa triển khai.

Có thể chạy lại import từ project root: `uv run python -m scripts.import_local_data`. Payload trùng SHA-256 được bỏ qua, payload thay đổi được upsert qua pipeline review/commit; script không xóa entry cũ nếu người dùng tự loại dòng khỏi JSON.

## Kiểm chứng

- Toàn bộ rows qua NormalizedRow/Pydantic và giới hạn content block trước khi upload.
- Đối chiếu chính xác tập (kanji, kana, trang PDF) trong DB với JSON của từng sách; mọi textbook đều private.
- Search thật `きんちょう`, `kinchou`, `緊張` đều trả 緊張, số mục 357, có example và raw block.
- `/health` và `/docs` trả 200. 77 test qua PostgreSQL testcontainers đều xanh; coverage service/NLP 95,67%; Ruff check và format sạch.

## Attribution dữ liệu từ điển

JMdict / EDRDG, CC BY-SA 4.0: https://www.edrdg.org/edrdg/licence.html. Bản JSON từ scriptin/jmdict-simplified, release `3.6.2+20261012204142`. `jmdict_subset.json` là tập con có biến đổi: chỉ giữ các cặp từ/cách đọc đã dùng và nghĩa tiếng Anh. Ghi công và ShareAlike áp dụng khi tái phân phối phần dữ liệu từ điển này.

## Còn thiếu

- Rà soát OCR, bổ sung 38 số mục Mimikara và kiểm tra đầy đủ block theo ảnh nguồn.
- Tách lesson/unit thật, bài tập và cấu trúc nội dung Shinkanzen bằng quy trình biên tập riêng.
- Bản dịch tiếng Việt, nguồn Hán Việt và nhãn JLPT từng từ có giấy phép phù hợp.
- Không có frontend hoặc chức năng P1/P2 mới trong lượt này.
