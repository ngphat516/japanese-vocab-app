"""Read-only M4 furigana sample from the exact reviewed M2 sentence selection."""

import asyncio
import re
from pathlib import Path

from app.db.session import Session, engine
from app.modules.dictionary import service as dictionary
from app.modules.textbooks.models import Entry, Lesson
from app.modules.textbooks.service import textbook_readings
from app.nlp.furigana import add_furigana


async def sample():
    source = Path("verification/m2_lemma_sample.md").read_text(encoding="utf-8")
    lines = [
        "# M4 furigana — MANUAL",
        "",
        "Same 30 sentences/order; seed20261020. Original OCR retained. Review readings manually.",
        "",
    ]
    async with Session() as db:
        for section in source.split("## ")[1:]:
            title, body = section.split("\n", 1)
            original = body.split("| Lemma M1")[0].strip()
            entry_id = int(re.search(r"Entry (\d+)", title)[1])
            entry = await db.get(Entry, entry_id)
            lesson = await db.get(Lesson, entry.lesson_id)
            readings = await textbook_readings(db, lesson.textbook_id)
            word = await dictionary.get_word(db, entry.word_id)
            if word.kanji:
                readings[word.kanji] = word.kana
            derived = add_furigana(original, readings)
            lines += [
                "## " + title,
                "",
                "| Original | Furigana |",
                "| --- | --- |",
                "| "
                + original.replace("|", "\\|").replace("\n", "<br>")
                + " | "
                + derived.replace("|", "\\|").replace("\n", "<br>")
                + " |",
                "",
            ]
    await engine.dispose()
    Path("verification/m4_furigana_sample.md").write_text("\n".join(lines), encoding="utf-8")
    print("30 reviewed sentences exported")


if __name__ == "__main__":
    asyncio.run(sample())
