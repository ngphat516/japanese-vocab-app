"""ASSUMED format, NOT validated against a real book export.

CSV/XLSX columns: unit,no,word,reading,meaning_vi,examples,usage,collocations,
synonyms,antonyms. examples is JSON [{ja,vi}], usage JSON {context,variants:[
{ja,correct}],vi}, collocations JSON [str], synonyms/antonyms JSON [{text,word_id?}].
Both old and revised editions use this format; edition belongs to the textbook.
Fixtures are invented, not transcribed from commercial books. Unknown columns,
including audio filenames, are preserved as raw. No audio capability is implemented.
"""

import json

from app.modules.imports.schemas import NormalizedRow

from .base import read_table

COLUMNS = {
    "unit",
    "no",
    "word",
    "reading",
    "meaning_vi",
    "examples",
    "usage",
    "collocations",
    "synonyms",
    "antonyms",
}


class MimikaraAdapter:
    def parse(self, file) -> list[NormalizedRow]:
        rows = read_table(file, {"unit", "no", "word", "reading", "meaning_vi"})
        result = []
        for row in rows:
            blocks = [{"type": "meaning", "vi": row["meaning_vi"]}]
            for example in json.loads(row.get("examples") or "[]"):
                blocks.append({"type": "example", **example})
            if row.get("usage"):
                blocks.append({"type": "usage", **json.loads(row["usage"])})
            for column, kind in [
                ("collocations", "collocation"),
                ("synonyms", "synonym"),
                ("antonyms", "antonym"),
            ]:
                if row.get(column):
                    blocks.append({"type": kind, "items": json.loads(row[column])})
            extras = {k: v for k, v in row.items() if k not in COLUMNS}
            if extras:
                blocks.append({"type": "raw", "data": extras})
            result.append(
                NormalizedRow(
                    kanji=row["word"].strip(),
                    kana=row["reading"].strip(),
                    lesson_no=int(row["unit"]),
                    order_no=int(row["no"]),
                    content=blocks,
                    raw=row,
                )
            )
        return result
