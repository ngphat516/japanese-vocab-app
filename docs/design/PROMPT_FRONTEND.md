# Nhiệm vụ
Xây dựng frontend cho **Kotonoha (言の葉)**, web app tra từ vựng tiếng Nhật qua nhiều giáo trình.
Code đặt trong `apps/frontend` (hiện chỉ có README). Backend FastAPI có sẵn ở `apps/backend`.
API ở `/api/v1`, OpenAPI ở `http://localhost:8000/openapi.json`, CORS backend cho phép `http://localhost:3000`.
KHÔNG sửa backend. Nếu API thiếu thứ gì, ghi vào `docs/DECISIONS.md` và làm phần giao diện với dữ liệu mock.

# Nguồn thiết kế (đọc trước khi code)
`docs/design/`:
- `README.md`: giải thích file và ý nghĩa token.
- `tokens.json`: màu và nội dung chữ của 6 theme, bảng màu badge JLPT light/dark.
- `themes/<theme>/`: `hero.svg`, `landscape.svg`, `strip.svg`, `particle-1..4.svg`. Đây là asset cuối cùng, dùng nguyên, không vẽ lại.
- `mockups/*.html`: markup tham khảo bố cục, khoảng cách, cỡ chữ. Trang Tra từ lấy theo `day.html`…`winter.html`.
  Sổ từ, Import, Mobile chỉ có bố cục trong `*-old.html`. Phải chuyển sang style mới, xem mục "Phong cách".
Copy asset vào `apps/frontend/public/themes/` khi build (script hoặc copy một lần).

# Stack
- Vite + React 18 + TypeScript strict, React Router v6, dev server port 3000.
- TanStack Query cho mọi lời gọi API. zod cho form.
- Tailwind CSS: màu khai báo bằng CSS variables (xem Theme). Radix UI primitives (Tabs, DropdownMenu, Popover, Dialog), tự style, không dùng theme mặc định của shadcn.
- Type API sinh bằng `openapi-typescript` vào `src/api/schema.d.ts`, script `npm run gen:api`.
  Lấy đúng tên field từ OpenAPI, không đoán. Ví dụ `WordSummary`: id, kanji, kana, romaji, jlpt_level, hanviet, kanji_breakdown[{char, hanviet}], saved.
- `VITE_API_URL` (mặc định `http://localhost:8000/api/v1`).
- Vitest + Testing Library.

# Theme
6 theme: `day` 昼, `night` 夜, `spring` 春, `summer` 夏, `autumn` 秋, `winter` 冬, cộng chế độ `auto`.
- Đặt `data-theme` trên `<html>`. Mỗi theme map token sang biến: `--bg --card --ink --acc --light --mid --muted --scene-bg --ok`.
  Sinh CSS từ `tokens.json` (script hoặc import JSON lúc build), không chép tay mã màu.
- `auto`: theo tháng hiện tại, 3–5 spring, 6–8 summer, 9–11 autumn, 12–2 winter. Viết hàm thuần `resolveTheme(pref, date)` có test.
- Lưu lựa chọn ở `localStorage['kotonoha.theme']`, mặc định `auto`. Thêm script inline trong `index.html` set `data-theme` trước khi render để không bị nháy màu.
- Theme picker ở header: nhãn "Giao diện" + 6 nút kanji `昼 夜 春 夏 秋 冬` (mỗi nút có `aria-label`: Sáng, Tối, Mùa xuân…) + checkbox "Tự động theo mùa".
  Khi bật tự động, nút mùa hiện tại được tô chọn. Bấm một nút bất kỳ thì tắt tự động.
- Badge JLPT: dùng bảng `light` hoặc `dark` theo `tokens[theme].dark`, luôn ghi chữ N1…N5 / "Ngoài JLPT", viền 2px cùng màu chữ, không bo góc.

# Phong cách (áp dụng cho mọi trang)
- Khung kiểu cửa sổ: viền `2px solid var(--ink)`, bóng `6px 6px 0 var(--mid)`, không bo góc.
  Thanh tiêu đề nền `--light`, chữ 13px đậm in hoa, bên phải 3 ô vuông trang trí 14px.
- Font: Be Vietnam Pro (tiếng Việt, UI), Noto Sans JP (tiếng Nhật), Noto Serif JP (từ đầu mục, logo 言の葉). Không dùng font pixel cho chữ.
- Pixel art chỉ nằm trong ảnh SVG, luôn có `image-rendering: pixelated`, `alt=""`.
- Nút chính: nền `--ink`, chữ `--card`, có bóng khối. Nút phụ: viền 2px `--ink`, nền `--card`.
- Màu sắc rực chỉ dành cho badge JLPT và trạng thái. Vùng đọc nội dung (nghĩa, ví dụ) luôn là nền `--card`, chữ `--ink`.
- Icon dạng nét (lucide-react), không dùng emoji.
- Tương phản chữ ≥ 4.5:1 ở cả 6 theme. Focus ring `outline: 3px solid var(--acc); outline-offset: 2px`.

# Khung app (AppShell)
- Header: logo `言の葉` (Noto Serif JP) + `Kotonoha` (nhỏ, mờ), nav Tra từ · Sổ từ · Import · "Ôn tập · Sắp có" (disabled),
  theme picker, nút tài khoản (Đăng nhập, hoặc menu tên user + Đăng xuất).
- Footer: đường kẻ 4px `--ink` có `strip.svg` lặp ngang phía trên. Bên dưới là vùng nền `--light` gồm:
  hàng chữ nhỏ (logo + "Tra một từ, đọc mọi giáo trình." | Giới thiệu · Nguồn dữ liệu · Góp ý · GitHub | `footer.ja · footer.vi` của theme),
  rồi `landscape.svg` full width cao 240px (`object-fit: cover; object-position: bottom`).
  Khoảng 20 particle mờ (opacity .35) rải ngẫu nhiên có seed cố định trên vùng này. Footer kéo dài để không còn khoảng trống dưới trang.
- Mobile (< 768px): một cột, ẩn nav trên, có thanh điều hướng dưới cùng (Tra từ · Sổ từ · Ôn tập · Tài khoản),
  hero.svg thu còn cao 160px, landscape giữ nguyên.

# Trang
1. **Tra từ `/`** (theo `mockups/<theme>.html`)
   - Hero: chip `tokens.chip`, H1 "Tra một từ, đọc mọi giáo trình" (Be Vietnam Pro 800, 50px), tagline của theme,
     ô tìm kiếm (Noto Sans JP 20px, viền 3px, bóng `--acc`) có gợi ý phím tắt `⌘K` trên Mac, `Ctrl K` trên máy khác.
     Bên phải là `hero.svg` trên nền `--scene-bg`.
   - Dải từ của mùa / hôm nay (`tokens.word`). Nút "Lưu vào sổ" gọi search từ đó, lưu nếu tìm thấy, không thấy thì ẩn nút.
   - Có query: 2 cửa sổ. "KẾT QUẢ (n)" bên trái (GET `/search?q=`, debounce 250ms, phân trang). "CHI TIẾT TỪ" bên phải (GET `/words/{id}`).
     State nằm trên URL: `?q=…&w=<id>`.
   - Chi tiết: kana · romaji, từ đầu mục 52px serif + badge, 《HÁN VIỆT》 màu `--acc`, nghĩa,
     chip từng chữ Hán (bấm mở Popover GET `/kanji/{char}`), nút ♥ Lưu (POST `/saved-words`, bỏ lưu bằng DELETE).
     Mỗi giáo trình trong `entries` là một tab. Tab cuối "+N ví dụ" lấy GET `/words/{id}/examples`.
     Có nút bật/tắt furigana: ẩn `<rt>` bằng `visibility: hidden` để layout không nhảy.
   - Không có query: hiện lịch sử tra (GET `/history`) và vài từ mới lưu.
2. **Sổ từ `/notebook`**: 6 ô thống kê theo cấp (GET `/saved-words/stats`, bấm để lọc), lọc theo tag / giáo trình / ô tìm,
   chuyển Thẻ ↔ Bảng, menu Xuất Anki / CSV / Markdown (GET `/saved-words/export?format=` kèm bộ lọc, tải file).
3. **Import `/import`**: stepper 3 bước. Bước 1 chọn adapter (GET `/imports/adapters`), tải template, upload (POST `/imports`).
   Bước 2 xem lại: poll GET `/imports/{id}`, các tab Tất cả / Cần chọn / Lỗi (GET `/imports/{id}/rows?match_status=`), chọn phương án bằng PATCH `/imports/{id}/rows/{row_id}`.
   Bước 3 xác nhận: POST `/imports/{id}/commit`.
4. **Đăng nhập / Đăng ký** `/login`, `/register`: card cửa sổ ở giữa trang, có hero.svg nhỏ.
   Access token để trong memory, refresh token trong localStorage. Gặp 401 thì gọi `/auth/refresh` một lần rồi thử lại.
   Route cần đăng nhập thì chuyển về `/login?next=`.

# Component lõi (làm trước, có test)
- `Ruby`: parse `漢字[よみ]` thành `<ruby>漢字<rt>よみ</rt></ruby>`, `{{…}}` thành `<u>` màu `--acc`, hỗ trợ lồng nhau.
  Chuỗi không có cú pháp thì giữ nguyên.
- `BlockRenderer`: meaning, example (đánh số ①②…), usage (chip ✓ viền `--ok` / ✗ gạch ngang nền `--light`),
  collocation, synonym/antonym/related (link sang `/?w=word_id` nếu có), note, raw (`<details>` hiện JSON).
- `Window`, `JlptBadge`, `ThemePicker`, `SearchBox`, `PixelImage`.

# Cách làm việc
1. Milestone: setup + theme + AppShell → Ruby/BlockRenderer → Tra từ → Auth → Sổ từ → Import → mobile + hoàn thiện.
2. Sau mỗi milestone chạy `npm run typecheck`, `npm run lint`, `npm test`, `npm run build`. Tất cả xanh mới commit
   (message dạng `feat(search): …`).
3. Không xoá hay nới test để test qua. Mọi giả định và chỗ API thiếu ghi vào `docs/DECISIONS.md`.
4. Đối chiếu từng trang với mockup ở cả 6 theme: chuyển theme bằng picker, kiểm tra không có chữ chìm nền.

# Định nghĩa hoàn thành
- `npm run dev` chạy ở port 3000, gọi được backend local. Cả 4 trang và 6 theme + auto hoạt động.
- Test cho `resolveTheme`, `Ruby`, `BlockRenderer`, `JlptBadge` (đổi bảng theo dark) đều xanh. typecheck, lint, build sạch.
- `apps/frontend/README.md` có: cách chạy, biến môi trường, cách sinh type API, cách thêm theme mới.
- Cuối cùng in báo cáo: trang và tính năng đã xong / còn thiếu, các giả định trong DECISIONS.md, các endpoint chưa dùng tới.
