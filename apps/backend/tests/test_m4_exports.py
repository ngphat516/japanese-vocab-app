import csv
import io
from types import SimpleNamespace

from app.modules.notebook.exports import anki_html, csv_bytes, project_rows


def test_ruby_boundaries_and_plain_csv():
    source = "では{{緊張[きんちょう]して}}"
    assert anki_html(source) == "では<u><ruby>緊張<rt>きんちょう</rt></ruby>して</u>"
    assert "&lt;script&gt;" in anki_html("<script>")
    row = {
        "word": "緊張",
        "reading": "きんちょう",
        "hanviet": "",
        "jlpt": None,
        "meaning": "tension",
        "meaning_source": "JMdict (en)",
        "examples": [{"ja": source}],
        "note": "",
        "tags": [],
        "sources": [],
    }
    output = next(csv.DictReader(io.StringIO(csv_bytes([row]).decode("utf-8-sig"))))
    assert output["Examples"] == "では緊張して"
    assert output["JLPT"] == ""


def test_compact_meaning_gloss_limit():
    word = SimpleNamespace(id=1, kanji="", kana="ねこ", hanviet="", jlpt_level=None, jmdict_id="1")
    saved = SimpleNamespace(word_id=1, note="", tags=[])
    senses = {1: [{"lang": "eng", "gloss": str(i)} for i in range(6)]}
    row = project_rows([saved], {1: word}, {}, senses, 1)[0]
    assert row["meaning"] == "0\n1\n2"
    assert row["meaning_source"] == "JMdict (en)"
