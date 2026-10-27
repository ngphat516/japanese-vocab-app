"""Extract vocabulary and token-position examples, without inventing meanings."""

import re
from typing import ClassVar

from app.core.exceptions import AppError
from app.modules.imports.schemas import NormalizedRow
from app.modules.textbooks.blocks import Example
from app.nlp.tokenizer import FORMAL_NOUNS, content_tokens, lemma_reading, tokenize


def validate_text(payload: bytes) -> str:
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise AppError(422, "IMPORT_ENCODING", "TXT phải dùng UTF-8") from None
    if not text.strip() or len(text) > 20_000:
        raise AppError(422, "FREE_TEXT_LENGTH", "Văn bản cần 1–20.000 ký tự")
    return text


class FreeTextAdapter:
    formats: ClassVar[list[str]] = ["txt", "text"]

    def parse(self, file, *, lesson_no=1, include_proper_nouns=False, exclude_jlpt=()):
        text = validate_text(file.read())
        rows = {}
        for sentence in re.findall(r"[^。！？\r\n]+[。！？]*", text):
            tokens = tokenize(sentence)
            starts, offset = [], 0
            for token in tokens:
                starts.append(offset)
                offset += len(token.surface)
            positions = {}
            for index, token in content_tokens(tokens):
                if (
                    ("固有名詞" in token.pos and not include_proper_nouns)
                    or "数詞" in token.pos
                    or token.lemma in FORMAL_NOUNS
                    or (len(token.lemma) == 1 and re.fullmatch(r"[ぁ-ゖァ-ヺー]", token.lemma))
                ):
                    continue
                key = token.normalized_form or token.lemma
                reading = lemma_reading(token.lemma)
                if not reading or not re.fullmatch(r"[ぁ-ゖー]+", reading):
                    continue
                if key not in rows:
                    rows[key] = NormalizedRow(
                        kanji=token.lemma if re.search(r"[一-鿿㐀-䶿]", token.lemma) else "",
                        kana=reading,
                        lesson_no=lesson_no,
                        order_no=len(rows) + 1,
                        content=[{"type": "raw", "data": {"sentences": []}}],
                        raw={
                            "normalized_form": key,
                            "sentences": [],
                            "exclude_jlpt": list(exclude_jlpt),
                        },
                    )
                positions.setdefault(key, []).append(
                    (starts[index], starts[index] + len(token.surface))
                )
            for key, spans in positions.items():
                row = rows[key]
                if len(row.raw["sentences"]) == 2 or sentence in row.raw["sentences"]:
                    continue
                marked = sentence
                for start, end in reversed(spans):
                    marked = marked[:start] + "{{" + marked[start:end] + "}}" + marked[end:]
                row.raw["sentences"].append(sentence)
                row.content[0].data["sentences"].append(sentence)
                row.content.append(Example(type="example", ja=marked))
        if not rows:
            raise AppError(422, "IMPORT_EMPTY", "Không tìm thấy từ nội dung")
        return list(rows.values())
