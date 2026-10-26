"""Notebook exports: batched authorized projection, no generated furigana/media."""

import asyncio
import csv
import html
import io
import json
import re
import tempfile
import unicodedata
import zipfile
from pathlib import Path

from app.modules.dictionary import service as dictionary
from app.modules.textbooks import service as textbooks

from . import service

ANKI_MODEL_ID = 2047426001
ANKI_DECK_ID = 2047426002
ANKI_FIELDS = ["Expression", "Reading", "Meaning", "HanViet", "Examples", "Notes", "Source"]
CSV_COLUMNS = [
    "Word",
    "Reading",
    "HanViet",
    "JLPT",
    "Meaning",
    "Examples",
    "Notes",
    "Tags",
    "Source",
]


def source_label(source):
    return f"{source['textbook']} · {source['lesson']} · {source['order_no']}"


async def export_rows(db, user, **filters):
    rows, _ = await service.saved_rows(db, user, **filters)
    ids = [row.word_id for row in rows]
    words = {word.id: word for word in await dictionary.all_by_ids(db, ids)}
    sources = {}
    for entry in await textbooks.notebook_entries(db, user, ids, content=True):
        sources.setdefault(entry["word_id"], []).append(entry)
    senses = await dictionary.senses_many(db, ids)
    return await asyncio.to_thread(project_rows, rows, words, sources, senses, user.id)


def project_rows(rows, words, sources, senses, user_id):
    result = []
    for saved in rows:
        word = words[saved.word_id]
        entries = sources.get(word.id, [])
        meaning = list(
            dict.fromkeys(
                f"{source_label(entry)}: {block['vi']}"
                for entry in entries
                if entry["owner_id"] == user_id
                for block in entry["content"]
                if block["type"] == "meaning" and block.get("vi")
            )
        )
        if not meaning:
            meaning = list(
                dict.fromkeys(
                    f"{'JMdict' if word.jmdict_id else 'Dictionary'} ({s['lang']}): {s['gloss']}"
                    for s in senses.get(word.id, [])
                )
            )
        if not meaning:
            meaning = list(
                dict.fromkeys(
                    f"{source_label(entry)}: {block.get('vi') or block.get('en')}"
                    for entry in entries
                    for block in entry["content"]
                    if block["type"] == "meaning" and (block.get("vi") or block.get("en"))
                )
            )
        examples = []
        key = textbooks.example_key({"kanji": word.kanji, "kana": word.kana})
        for entry in sorted(entries, key=lambda e: e["owner_id"] != user_id):
            for sentence in textbooks.example_sentences(entry["content"], key):
                if sentence not in examples:
                    examples.append(sentence)
                if len(examples) == 2:
                    break
            if len(examples) == 2:
                break
        result.append(
            {
                "id": word.id,
                "word": word.kanji or word.kana,
                "reading": word.kana,
                "hanviet": word.hanviet,
                "jlpt": word.jlpt_level,
                "meaning": "\n".join(meaning),
                "examples": examples,
                "note": saved.note,
                "tags": saved.tags,
                "sources": list(dict.fromkeys(source_label(entry) for entry in entries)),
            }
        )
    return result


def example_text(row):
    return [s["ja"] + (f" — {s['vi']}" if s.get("vi") else "") for s in row["examples"]]


def anki_html(value):
    # Escape imported/user text first; permit only the target-word underline.
    value = html.escape(value)
    value = re.sub(r"\{\{(.*?)\}\}", r"<u>\1</u>", value, flags=re.DOTALL)
    return value.replace("\n", "<br>")


def anki_bytes(rows, user_id):
    import genanki

    model = genanki.Model(
        ANKI_MODEL_ID,
        "Japanese Vocab Notebook v1",
        fields=[{"name": name} for name in ANKI_FIELDS],
        templates=[
            {
                "name": "Recognition",
                "qfmt": "{{Expression}}",
                "afmt": '{{FrontSide}}<hr id="answer">{{Reading}}<br>{{Meaning}}<br>{{HanViet}}<hr>{{furigana:Examples}}<hr>{{Notes}}<br>{{Source}}',
            }
        ],
        css=".card { font-family: sans-serif; font-size: 24px; text-align: left; } ruby rt { font-size: 0.6em; }",
    )
    deck = genanki.Deck(ANKI_DECK_ID, "Sổ từ tiếng Nhật")
    for row in rows:
        notes = f"JLPT: {row['jlpt'] or 'none'}"
        if row["note"]:
            notes += "\n" + row["note"]
        if row["tags"]:
            notes += "\nTags: " + ", ".join(row["tags"])
        fields = [
            row["word"],
            row["reading"],
            row["meaning"],
            row["hanviet"],
            "\n".join(example_text(row)),
            notes,
            "\n".join(row["sources"]),
        ]
        deck.add_note(
            genanki.Note(
                model=model,
                fields=[anki_html(v) for v in fields],
                guid=genanki.guid_for("japanese-vocab-app", user_id, row["id"]),
                tags=[re.sub(r"\s", "_", tag) for tag in row["tags"]],
            )
        )
    with tempfile.TemporaryDirectory(prefix="vocab-export-") as directory:
        path = Path(directory) / "notebook.apkg"
        genanki.Package(deck).write_to_file(str(path))
        return path.read_bytes()


def csv_text(value):
    # Keep note/tag cells textual when the CSV is opened by Excel.
    if value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def csv_bytes(rows):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(CSV_COLUMNS)
    for row in rows:
        writer.writerow(
            [
                csv_text(value)
                for value in [
                    row["word"],
                    row["reading"],
                    row["hanviet"],
                    row["jlpt"] or "none",
                    row["meaning"],
                    " / ".join(example_text(row)),
                    row["note"],
                    ", ".join(row["tags"]),
                    " / ".join(row["sources"]),
                ]
            ]
        )
    return output.getvalue().encode("utf-8-sig")


def markdown_name(row):
    name = unicodedata.normalize("NFKC", row["word"])
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).rstrip(" .")[:100] or "word"
    # Windows reserves device names even when followed by an extension.
    if re.match(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", name, re.IGNORECASE):
        name = "_" + name
    return f"{name}-{row['id']}.md"


def markdown_bytes(rows):
    # JSON string/list literals form a safe, portable subset of YAML frontmatter.
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for row in rows:
            front = {
                key: row[key] for key in ["word", "reading", "jlpt", "hanviet", "tags", "sources"]
            }
            metadata = "\n".join(
                f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in front.items()
            )
            body = f"---\n{metadata}\n---\n\n# {row['word']}\n\n{row['meaning']}\n\n"
            body += "\n\n".join(
                re.sub(r"\{\{(.*?)\}\}", r"<u>\1</u>", value, flags=re.DOTALL)
                for value in example_text(row)
            )
            body += f"\n\n{row['note']}\n"
            archive.writestr(markdown_name(row), body)
    return output.getvalue()


def render(rows, format, user_id):
    if format == "anki":
        return anki_bytes(rows, user_id), "application/octet-stream", "apkg"
    if format == "csv":
        return csv_bytes(rows), "text/csv; charset=utf-8", "csv"
    return markdown_bytes(rows), "application/zip", "zip"
