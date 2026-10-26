"""Offline Unihan kVietnamese projection. Does not write to the database."""

import argparse
import asyncio
import csv
import hashlib
import json
import random
import re
import unicodedata
from pathlib import Path

HAN = re.compile(r"[一-鿿㐀-䶿豈-﫿\U00020000-\U000323af]")


def parse(path):
    result = {}
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        if not line or line.startswith("#"):
            continue
        code, field, value = line.split("\t", 2)
        if field == "kVietnamese":
            char = chr(int(code.removeprefix("U+"), 16))
            if HAN.fullmatch(char):
                result.setdefault(char, [])
                for reading in value.split():
                    reading = unicodedata.normalize("NFC", reading).upper()
                    if reading not in result[char]:
                        result[char].append(reading)
    return result


def build(path, output, *, version, characters, sample_path):
    header = re.search(r"# Unicode Version ([0-9.]+)", Path(path).read_text(encoding="utf-8-sig"))
    if header and header[1] != version:
        raise ValueError("Unicode version does not match the source header")
    data = parse(path)
    if not data:
        raise ValueError("No kVietnamese readings found")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["kanji", "hanviet"])
        writer.writerows((char, "|".join(data[char])) for char in sorted(data))
    covered = characters & data.keys()
    report = {
        "unicode_version": version,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source": "https://www.unicode.org/Public/" + version + "/ucd/Unihan.zip",
        "license": "Unicode-3.0",
        "dataset_characters": len(data),
        "dataset_multiple_readings": sum(len(v) > 1 for v in data.values()),
        "local_characters": len(characters),
        "covered": len(covered),
        "coverage_percent": 100 * len(covered) / len(characters) if characters else None,
        "local_multiple_readings": sum(len(data[c]) > 1 for c in covered),
        "seed": 20261020,
    }
    sample = random.Random(20261020).sample(sorted(characters), min(30, len(characters)))
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    sample_path.write_text(
        "# Unihan Hán Việt — MANUAL\n\nUnicode "
        + version
        + "; seed20261020. kVietnamese có thể lẫn âm Nôm; chưa seed DB.\n\n| Chữ | Âm |\n| --- | --- |\n"
        + "\n".join(f"| {c} | {' / '.join(data.get(c, [])) or '—'} |" for c in sample)
        + "\n",
        encoding="utf-8",
    )
    output.with_suffix(".metadata.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


async def local_characters():
    from sqlalchemy import select

    from app.db.session import engine
    from app.modules.dictionary.models import Word
    from app.modules.textbooks.models import Entry

    async with engine.connect() as db:
        spellings = (
            await db.scalars(select(Word.kanji).where(Word.id.in_(select(Entry.word_id))))
        ).all()
    await engine.dispose()
    return {c for word in spellings for c in word if HAN.fullmatch(c)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, default=Path("data/hanviet.csv"))
    parser.add_argument("--sample", type=Path, default=Path("verification/m4_hanviet_sample.md"))
    args = parser.parse_args()
    print(
        build(
            args.path,
            args.output,
            version=args.version,
            characters=asyncio.run(local_characters()),
            sample_path=args.sample,
        )
    )
