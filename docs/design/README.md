# Thiết kế giao diện Kotonoha (言の葉)

Bộ file bàn giao cho frontend. Nguồn gốc: canvas mockup "Mockup UI – Web App Từ vựng Tiếng Nhật".

## Cấu trúc

```
docs/design/
├── tokens.json            # Màu và nội dung theo 6 theme + bảng màu badge JLPT (light/dark)
├── themes/<theme>/        # theme ∈ day, night, spring, summer, autumn, winter
│   ├── hero.svg           # Tranh pixel khung hero, 520×320, nền trong suốt (tô nền bằng sceneBg)
│   ├── landscape.svg      # Cánh đồng + sông ở chân trang, 1440×240, nền trong suốt
│   ├── strip.svg          # Một ô hoạ tiết lặp ngang (repeat-x) nằm trên đường kẻ chân trang
│   └── particle-1..4.svg  # Hoạ tiết nhỏ rải rác (cánh hoa, lá, bông tuyết, sao)
└── mockups/               # Markup tham khảo của canvas (không chạy trực tiếp được)
    ├── day.html … winter.html   # Trang Tra từ theo từng theme (bản chuẩn)
    └── sotu-old.html, import-old.html, mobile-old.html  # Bố cục Sổ từ / Import / Mobile (style cũ "giấy và mực")
```

## Ý nghĩa token

| Key | Dùng cho |
|---|---|
| `bg` | Nền trang |
| `card` | Nền cửa sổ, card, ô input |
| `ink` | Chữ chính, viền 2px, nền nút chính |
| `acc` | Điểm nhấn: gạch chân từ đích, bóng ô tìm kiếm, Hán Việt |
| `light` | Thanh tiêu đề cửa sổ, dải "Từ của mùa", nền chân trang, hàng đang chọn |
| `mid` | Bóng đổ khối `6px 6px 0` |
| `muted` | Chữ phụ (furigana, nghĩa dịch, chú thích) |
| `sceneBg` | Nền phía sau `hero.svg` |
| `ok` | Viền chip cách dùng đúng (✓) |
| `dark` | `true` thì dùng bảng badge JLPT `dark` |

`chip`, `tagline`, `word` (từ của mùa / hôm nay), `footer` là nội dung chữ riêng của từng theme.

Pixel art chỉ có trong ảnh. Khi hiển thị, luôn đặt `image-rendering: pixelated`. Chữ trong giao diện không dùng font pixel.
