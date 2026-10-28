"""Lock reviewed M5/M6 readings and apply the explicitly approved M7c batch."""

import csv
from pathlib import Path

from scripts.build_hanviet_unihan import apply_overrides
from scripts.evaluate_hanviet_m7b import REVIEWS, reviewed_standard

BATCH3 = """営 DOANH|DINH, 湿 THẤP, 爆 BỘC|BẠO, 徴 TRƯNG, 彙 VỰNG, 継 KẾ, 般 BAN|BÀN,
仮 GIẢ, 択 TRẠCH, 晩 VÃN, 怖 BỐ, 条 ĐIỀU, 溶 DUNG, 挑 KHIÊU, 剤 TỄ, 拝 BÁI, 推 SUY|THÔI,
締 ĐẾ, 政 CHÍNH, 句 CÚ, 百 BÁCH, 横 HOÀNH, 尚 THƯỢNG, 姉 TỶ"""


def lock(path=Path("data/hanviet_overrides.csv")):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    original = {row["kanji"]: dict(row) for row in rows}
    standard = reviewed_standard(REVIEWS, apply_overrides({}, path))
    added = 0
    for char, values in standard.items():
        if char != "词" and char not in original:
            rows.append({"kanji": char, "hanviet": "|".join(values), "note": "accepted M5/M6"})
            added += 1
    by_char = {row["kanji"]: row for row in rows}
    for item in BATCH3.split(","):
        char, values = item.strip().split(None, 1)
        expected = {"kanji": char, "hanviet": values, "note": "review M7 lô 3"}
        if char not in by_char:
            rows.append(expected)
        elif by_char[char] != expected:
            raise ValueError(f"Batch 3 would change an existing override: {char}")
    assert all(by_char[c] == row for c, row in original.items())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["kanji", "hanviet", "note"])
        writer.writeheader()
        writer.writerows(rows)
    print({"accepted_added": added, "batch3": len(BATCH3.split(",")), "total": len(rows)})


if __name__ == "__main__":
    lock()
