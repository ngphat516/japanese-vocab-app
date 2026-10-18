from app.modules.imports.schemas import NormalizedRow

from .base import read_table

COLUMNS = [
    "lesson",
    "order",
    "kanji",
    "kana",
    "meaning_vi",
    "meaning_en",
    "example_ja",
    "example_vi",
    "note",
]


class CSVTemplateAdapter:
    """UTF-8 CSV or XLSX, first sheet, same named columns as the downloadable template."""

    def parse(self, file) -> list[NormalizedRow]:
        rows = read_table(file, {"lesson", "order", "kanji", "kana"})
        result = []
        for row in rows:
            blocks = []
            if row.get("meaning_vi") or row.get("meaning_en"):
                blocks.append(
                    {
                        "type": "meaning",
                        **{
                            lang: row[f"meaning_{lang}"]
                            for lang in ["vi", "en"]
                            if row.get(f"meaning_{lang}")
                        },
                    }
                )
            if row.get("example_ja"):
                blocks.append(
                    {"type": "example", "ja": row["example_ja"], "vi": row.get("example_vi", "")}
                )
            elif row.get("example_vi"):
                blocks.append({"type": "raw", "data": {"example_vi": row["example_vi"]}})
            if row.get("note"):
                blocks.append({"type": "note", "text": row["note"]})
            extras = {key: value for key, value in row.items() if key not in COLUMNS}
            if extras:
                blocks.append({"type": "raw", "data": extras})
            result.append(
                NormalizedRow(
                    kanji=row["kanji"].strip(),
                    kana=row["kana"].strip(),
                    lesson_no=int(row["lesson"]),
                    order_no=int(row["order"]),
                    content=blocks,
                    raw=row,
                )
            )
        return result
