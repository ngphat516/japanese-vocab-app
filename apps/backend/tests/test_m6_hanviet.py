import unicodedata

import pytest

from app.nlp.vietnamese import normalize_tones


@pytest.mark.parametrize(
    "old,new",
    [
        ("HOÁ", "HÓA"),
        ("THUỶ", "THỦY"),
        ("HOẠ", "HỌA"),
        ("TOÀ", "TÒA"),
        ("TOẠ", "TỌA"),
        ("hoạt", "hoạt"),
        ("NGHIỆM", "NGHIỆM"),
        ("quý", "quý"),
        ("già", "già"),
        ("tuổi", "tuổi"),
        ("THUÝ|THUÍ", "THÚY|THÚI"),
        ("", ""),
    ],
)
def test_modern_tones_preserve_spelling(old, new):
    assert normalize_tones(old) == new
    assert normalize_tones(unicodedata.normalize("NFD", old)) == new
    assert normalize_tones(new) == new


async def test_seed_tone_normalization_and_idempotence(db, tmp_path):
    from app.modules.dictionary.models import Kanji
    from app.modules.dictionary.service import seed_hanviet

    path = tmp_path / "readings.csv"
    path.write_text("kanji,hanviet\n化,HOÁ\n水,THUỶ\n", encoding="utf-8")
    await seed_hanviet(db, path)
    assert (await db.get(Kanji, "化")).hanviet == ["HÓA"]
    assert (await db.get(Kanji, "水")).hanviet == ["THỦY"]
    assert await seed_hanviet(db, path) == {"kanji_changed": 0, "words_changed": 0}
