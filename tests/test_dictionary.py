import pytest
from sqlalchemy import func, select

from app.core.exceptions import AppError
from app.modules.dictionary import service as s
from app.modules.dictionary.models import Kanji, Word, WordSense
from tests.conftest import FIXTURES


async def test_DICT_01_idempotent_seed(seeded):
    before = await seeded.scalar(select(func.count()).select_from(WordSense))
    await s.seed_jmdict(seeded, FIXTURES / "jmdict.json")
    assert await seeded.scalar(select(func.count()).select_from(Word)) == 30
    assert await seeded.scalar(select(func.count()).select_from(WordSense)) == before == 30


async def test_DICT_02_normalization(seeded):
    word = await s.create_word(seeded, "試験", "シ ケン!")
    assert word.kana_norm == "しけん"
    assert "shiken" in word.romaji.replace(" ", "").replace("!", "")
    word = (await s.match(seeded, "緊張", "キンチョウ"))[0]
    assert word.romaji == "kinchou"


async def test_DICT_03_candidate_matching(seeded):
    assert len(await s.match(seeded, "", "はし")) == 3
    assert len(await s.match(seeded, "橋", "ハシ")) == 1
    assert await s.match(seeded, "", "みとうろく") == []


async def test_DICT_04_detail(authorized, seeded):
    client, _ = authorized
    word = (await s.match(seeded, "緊張", "きんちょう"))[0]
    result = await client.get(f"/api/v1/words/{word.id}")
    assert result.status_code == 200
    assert result.json()["senses"][0]["gloss"] == "tension"
    assert (await client.get("/api/v1/words/999999")).status_code == 404
    with pytest.raises(AppError):
        await s.get_word(seeded, -1)


async def test_DICT_05_jlpt_labels(seeded):
    assert (await s.match(seeded, "緊張", "きんちょう"))[0].jlpt_level == "N3"
    assert (await s.match(seeded, "ゆるむ", "ゆるむ"))[0].jlpt_level is None
    await s.seed_jlpt(seeded, FIXTURES / "jlpt.csv")


async def test_DICT_06_kanji_hanviet(seeded):
    assert await seeded.scalar(select(func.count()).select_from(Kanji)) == 20
    await s.seed_kanjidic(seeded, FIXTURES / "kanjidic.json")
    await s.seed_hanviet(seeded, FIXTURES / "hanviet.csv")
    assert (await seeded.get(Kanji, "楽")).hanviet == ["LẠC", "NHẠC"]
    assert (await seeded.get(Kanji, "緊")).strokes == 6


async def test_DICT_07_breakdown(seeded):
    assert await s.kanji_breakdown(seeded, "緊張する") == [
        {"char": "緊", "hanviet": "KHẨN"},
        {"char": "張", "hanviet": "TRƯƠNG"},
    ]
    assert await s.kanji_breakdown(seeded, "ゆるむ") == []
    word = (await s.match(seeded, "緊張", "きんちょう"))[0]
    assert word.hanviet == "KHẨN TRƯƠNG"
