from sqlalchemy import select

from app.modules.dictionary.models import Word, WordSense
from scripts.bench_seed import project, seed_full_jmdict
from tests.conftest import FIXTURES


async def test_bulk_benchmark_projection_matches_production_seed(seeded):
    words, senses, metadata = project(FIXTURES / "jmdict.json")
    projected_words = {row[0]: (row[2], row[3]) for row in words}
    actual_words = {w.id: (w.kanji, w.kana) for w in (await seeded.scalars(select(Word))).all()}
    assert set(projected_words.values()) == set(actual_words.values())
    expected = {(projected_words[w], lang, gloss, order) for w, lang, gloss, order in senses}
    actual = {
        (actual_words[s.word_id], s.lang, s.gloss, s.order)
        for s in (await seeded.scalars(select(WordSense))).all()
    }
    assert expected == actual
    assert metadata["source_entries"] == 30


async def test_bulk_benchmark_loader_copies_all_projected_records(db):
    metadata = await seed_full_jmdict(await db.connection(), FIXTURES / "jmdict.json")
    words = (await db.scalars(select(Word))).all()
    senses = (await db.scalars(select(WordSense))).all()
    assert len(words) == metadata["words"] == 30
    assert len(senses) == metadata["senses"] == 30
    assert all(w.romaji and w.hanviet == "" and w.jlpt_level is None for w in words)
