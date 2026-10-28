from pathlib import Path

from sqlalchemy import select

from app.modules.auth.service import current_user
from app.modules.dictionary import service as dictionary
from app.modules.dictionary.models import Kanji, KanjiEdit
from scripts.build_hanviet_unihan import apply_overrides, parse_variants, with_variants


def test_variants_unique_conflicting_cycles_and_overrides(tmp_path):
    path = tmp_path / "variants.txt"
    path.write_text(
        "U+8C4A\tkTraditionalVariant\tU+8C50\nU+6CA2\tkSemanticVariant\tU+6FA4<kMatthews\nU+7532\tkZVariant\tU+4E59 U+4E19\nU+4E01\tkZVariant\tU+4E02\nU+4E02\tkZVariant\tU+4E01\n",
        encoding="utf-8",
    )
    data = with_variants(
        {
            "豐": ["PHONG"],
            "澤": ["TRẠCH"],
            "乙": ["ẤT"],
            "丙": ["BÍNH"],
            "爽": ["SỬNG"],
            "滝": ["SÔNG"],
        },
        parse_variants(path),
    )
    assert data["豊"] == (["PHONG"], "unihan_variant:U+8C50")
    assert "沢" not in data and "甲" not in data and "丁" not in data
    result = apply_overrides(data, Path("data/hanviet_overrides.csv"))
    assert result["豊"] == (["PHONG"], "override")
    assert result["爽"] == (["SẢNG"], "override")
    assert result["滝"] == ([], "override")


async def test_patch_kanji_source_recomputes_except_manual_words(authorized, seeded, db, tmp_path):
    client, _ = authorized
    user = await current_user(db, client.headers["authorization"][7:])
    word = (await dictionary.match(db, "緊張", "きんちょう"))[0]
    other = await dictionary.create_word(db, "緊迫", "きんぱく")
    assert (await client.patch("/api/v1/kanji/緊", json={"hanviet": ["MỚI"]})).status_code == 403
    user.role = "admin"
    await db.flush()
    await client.patch(f"/api/v1/words/{word.id}", json={"hanviet": "MANUAL"})
    response = await client.patch("/api/v1/kanji/緊", json={"hanviet": [" mới ", "MỚI"]})
    assert response.status_code == 200 and response.json()["hanviet_source"] == "override"
    assert word.hanviet == "MANUAL" and other.hanviet == "MỚI"
    edit = await db.scalar(select(KanjiEdit))
    assert edit.old["hanviet"] == ["KHẨN"] and edit.new["source"] == "override"
    assert (await client.get("/api/v1/kanji/緊")).json()["hanviet_source"] == "override"
    assert (await dictionary.describe(db, other))["kanji_breakdown"][0][
        "hanviet_source"
    ] == "override"
    assert (await client.patch("/api/v1/kanji/a", json={"hanviet": []})).status_code == 422
    assert (await client.patch("/api/v1/kanji/龘", json={"hanviet": []})).status_code == 404
    path = tmp_path / "hanviet.csv"
    path.write_text(
        "kanji,hanviet,source\n緊,OLD,unihan\n豊,PHONG,unihan_variant:U+8C50\n", encoding="utf-8"
    )
    await dictionary.seed_hanviet(db, path)
    assert (await db.get(Kanji, "緊")).hanviet == ["MỚI"]
    assert word.hanviet == "MANUAL"
    assert await dictionary.seed_hanviet(db, path) == {"kanji_changed": 0, "words_changed": 0}


async def test_public_headword_reading_fallback_without_global_override(imported, db):
    from app.modules.textbooks import service as textbooks
    from app.modules.textbooks.schemas import TextbookCreate
    from app.nlp.furigana import READING_OVERRIDES

    client, own, _ = imported
    user = await current_user(db, client.headers["authorization"][7:])
    assert "腹痛" not in READING_OVERRIDES
    user.role = "admin"
    await db.flush()
    book = await textbooks.create_textbook(
        db, user, TextbookCreate(name="Public canonical", visibility="public")
    )
    lesson = await textbooks.ensure_lesson(db, user, book.id, 1)
    word = await dictionary.create_word(db, "腹痛", "ふくつう")
    await textbooks.save_entry(
        db, user, lesson.id, word.id, 1, [{"type": "meaning", "en": "stomachache"}]
    )
    readings = await textbooks.textbook_readings(db, own["id"])
    assert readings["腹痛"] == "ふくつう"
