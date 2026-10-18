"""Import normalized PDF conversion rows with full blocks; OCR runs separately, locally.

Format: {"source": {...}, "rows": [{kanji,kana,lesson_no,order_no,content,raw?}]}.
No reading, meaning, or translation is inferred by this adapter.
"""

import json

from app.core.exceptions import AppError
from app.modules.imports.schemas import NormalizedRow


class NormalizedJSONAdapter:
    formats = ("json",)

    def parse(self, file) -> list[NormalizedRow]:
        payload = file.read(5 * 1024 * 1024 + 1)
        if len(payload) > 5 * 1024 * 1024:
            raise AppError(413, "IMPORT_FILE_TOO_LARGE", "File vượt quá 5 MB")
        document = json.loads(payload.decode("utf-8-sig"))
        if not isinstance(document, dict) or not isinstance(document.get("rows"), list):
            raise TypeError("Expected object with rows array")
        rows = document["rows"]
        if not rows:
            raise AppError(422, "IMPORT_EMPTY", "File không có dòng dữ liệu")
        if len(rows) > 5000:
            raise AppError(422, "IMPORT_TOO_MANY_ROWS", "Tối đa 5.000 dòng")
        source = document.get("source", {})
        result = []
        known = set(NormalizedRow.model_fields)
        for row in rows:
            if not isinstance(row, dict):
                raise TypeError("Every row must be an object")
            raw = {**row.get("raw", {}), "source": source}
            raw.update({k: v for k, v in row.items() if k not in known})
            result.append(NormalizedRow.model_validate({**row, "raw": raw}))
        return result
