"""Export only changed lemmas from the reviewed 30-sentence M2 sample."""

import json
import re
from pathlib import Path

from app.nlp.furigana import strip_markup
from app.nlp.tokenizer import lemmas


def main():
    source = Path("verification/m2_lemma_sample.md").read_text(encoding="utf-8")
    lines = [
        "# Milestone 3 lemma diff — MANUAL",
        "",
        "Seed20261020; only changed sentences from the same M2 sample. Source/markup unchanged.",
        "",
    ]
    changed = 0
    for section in source.split("## ")[1:]:
        title, body = section.split("\n", 1)
        original = body.split("| Lemma M1")[0].strip()
        row = next(re.finditer(r"^\| (\[.*\]) \| (\[.*\]) \|$", body, re.MULTILINE))
        old = json.loads(row[2])
        new = lemmas(strip_markup(original).replace("__", ""))
        if old != new:
            changed += 1
            lines += [
                "## " + title,
                "",
                original,
                "",
                "| M2 | M3 |",
                "| --- | --- |",
                "| "
                + json.dumps(old, ensure_ascii=False)
                + " | "
                + json.dumps(new, ensure_ascii=False)
                + " |",
                "",
            ]
    lines += [f"Changed sentences: {changed}/30.", ""]
    Path("verification/m3_lemma_diff.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Changed sentences: {changed}/30")


if __name__ == "__main__":
    main()
