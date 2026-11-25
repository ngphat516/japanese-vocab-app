# Kotonoha (言の葉) · Frontend

Web app tra từ vựng tiếng Nhật qua nhiều giáo trình. Vite + React 18 + TypeScript (strict),
React Router v6, TanStack Query, Tailwind CSS (màu qua CSS variables), Radix UI, zod, Vitest.

## Chạy

Yêu cầu Node 20+ và backend FastAPI đang chạy ở `http://localhost:8000`
(xem README gốc: `docker compose up -d db api worker`). CORS backend cho phép `http://localhost:3000`.

```bash
cd apps/frontend
npm install
npm run dev        # http://localhost:3000
```

| Lệnh | Việc |
|---|---|
| `npm run dev` | Copy asset theme + dev server cổng 3000 |
| `npm run build` | Copy asset theme, `tsc -b`, `vite build` ra `dist/` |
| `npm run preview` | Xem bản build ở cổng 3000 |
| `npm run typecheck` | `tsc -b --noEmit` |
| `npm run lint` | ESLint, không cho phép warning |
| `npm test` | Vitest + Testing Library (jsdom) |
| `npm run gen:api` | Sinh type API từ OpenAPI (xem dưới) |
| `npm run copy:themes` | Copy `docs/design/themes` → `public/themes` và sinh CSS theme |

## Biến môi trường

Tạo `apps/frontend/.env.local` (xem `.env.example`):

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000/api/v1` | Gốc REST API của backend |

Access token chỉ nằm trong bộ nhớ; refresh token lưu ở `localStorage['kotonoha.refresh']`.
Gặp 401 client gọi `/auth/refresh` đúng một lần rồi thử lại request. Lựa chọn giao diện lưu ở
`localStorage['kotonoha.theme']` (mặc định `auto`).

## Sinh type API

Type nằm ở `src/api/schema.d.ts` (được commit), sinh bằng `openapi-typescript`:

```bash
# backend đang chạy
npm run gen:api                       # đọc http://localhost:8000/openapi.json
OPENAPI_URL=https://… npm run gen:api # nguồn khác

# không chạy backend: xuất schema từ app FastAPI rồi sinh từ file
cd ../backend && .venv/Scripts/python -c "import json; from app.main import app; print(json.dumps(app.openapi()))" > ../frontend/openapi.json
cd ../frontend && npm run gen:api:file
```

`src/api/types.ts` đặt alias cho các schema dùng trong app. Một số endpoint chưa khai báo
response model (kanji, imports, textbooks) nên type viết tay trong `types.ts`; xem `docs/DECISIONS.md`.

## Theme

Sáu theme `day 昼`, `night 夜`, `spring 春`, `summer 夏`, `autumn 秋`, `winter 冬` và chế độ `auto`
(tháng 3–5 xuân, 6–8 hạ, 9–11 thu, 12–2 đông; hàm thuần `resolveTheme(pref, date)` trong
`src/theme/resolveTheme.ts`). Theme đặt bằng `data-theme` trên `<html>`; script inline trong
`index.html` đặt nó trước khi React render để không nháy màu.

Nguồn duy nhất là `docs/design/`:

- `tokens.json` → `scripts/copy-themes.mjs` sinh `src/styles/themes.generated.css` gồm
  `--bg --card --ink --acc --light --mid --muted --scene-bg --ok` và `--jlpt-*` cho mỗi theme.
  Nội dung chữ (chip, tagline, từ của mùa, footer) và bảng màu badge JLPT được import trực tiếp từ JSON
  (`src/theme/tokens.ts`, alias `@design`).
- `themes/<theme>/*.svg` được copy nguyên vào `public/themes/<theme>/` (không vẽ lại).

Cả hai output đều được sinh khi `dev`/`build` và nằm trong `.gitignore`.

### Thêm theme mới

1. Thêm object mới vào `docs/design/tokens.json` với đủ key như các theme khác
   (`bg card ink acc light mid muted sceneBg ok dark label kanji chip tagline word footer`).
   `dark: true` thì badge JLPT dùng bảng `_jlpt.dark`.
2. Tạo `docs/design/themes/<tên>/` với `hero.svg`, `landscape.svg`, `strip.svg`, `particle-1..4.svg`.
3. Thêm tên vào mảng `THEMES` trong `src/theme/tokens.ts` và vào mảng `themes` của script inline trong `index.html`.
4. Nếu là theme mùa, cập nhật `seasonOf()` trong `src/theme/resolveTheme.ts` và test đi kèm.
5. `npm run dev`, chuyển sang theme mới bằng picker, kiểm tra tương phản chữ ≥ 4.5:1.

## Cấu trúc

```
src/
  api/          client fetch (token, refresh 1 lần), endpoints, type OpenAPI
  auth/         AuthProvider, RequireAuth
  theme/        tokens, resolveTheme, ThemeProvider
  components/   Window, JlptBadge, ThemePicker, SearchBox, PixelImage, AppShell, Hero,
                ruby/ (parser + Ruby), blocks/ (BlockRenderer)
  pages/        SearchPage (+ search/), NotebookPage, ImportPage, AuthPages, AccountPage
  styles/       index.css (+ themes.generated.css sinh tự động)
```

Quy ước giao diện: khung cửa sổ viền `2px var(--ink)`, bóng `6px 6px 0 var(--mid)`, không bo góc;
pixel art chỉ trong ảnh SVG (`image-rendering: pixelated`, `alt=""`); icon lucide-react; focus ring
`3px solid var(--acc)`.
