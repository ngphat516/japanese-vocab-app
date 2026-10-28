import json

import pytest

from scripts.build_hanviet_unihan import parse_variants, with_variants
from scripts.hanviet_sources import combine, needs_review, parse_kanjidic2, prefer_kanjidic2, score


def test_rain_never_uses_semantic_horse_variant(tmp_path):
    path = tmp_path / "variants.txt"
    path.write_text(
        "U+96E8\tkSemanticVariant\tU+99AD\n"
        "U+7532\tkSpecializedSemanticVariant\tU+99AD\n"
        "U+4E59\tkTraditionalVariant\tU+99AD\n"
        "U+4E19\tkZVariant\tU+99AD\n",
        encoding="utf-8",
    )
    graph = parse_variants(path)
    result = with_variants({"馭": ["NGỰA"]}, graph)
    assert "雨" not in result and "甲" not in result
    assert result["乙"][0] == result["丙"][0] == ["NGỰA"]
    assert with_variants({"雨": ["VŨ"], "馭": ["NGỰA"]}, graph)["雨"] == (["VŨ"], "unihan")


def test_kanjidic2_vietnam_only_all_groups_order_normalization(tmp_path):
    path = tmp_path / "kanjidic2.json"
    path.write_text(
        json.dumps(
            {
                "characters": [
                    {
                        "literal": "化",
                        "readingMeaning": {
                            "groups": [
                                {
                                    "readings": [
                                        {"type": "ja_on", "value": "カ"},
                                        {"type": "vietnam", "value": " hoá "},
                                    ]
                                },
                                {
                                    "readings": [
                                        {"type": "vietnam", "value": "HÓA"},
                                        {"type": "vietnam", "value": "Hoạ"},
                                    ]
                                },
                            ]
                        },
                    },
                    {"literal": "一", "readingMeaning": None},
                ]
            }
        ),
        encoding="utf-8",
    )
    assert parse_kanjidic2(path) == {"化": ["HÓA", "HỌA"]}
    path.write_text('{"characters": []}', encoding="utf-8")
    with pytest.raises(ValueError, match="No vietnam"):
        parse_kanjidic2(path)


def test_source_score_includes_misses_and_all_gold_readings():
    result = score(
        {"雨": ["VÚ", "VŨ"], "易": ["DỊCH"]},
        {"雨": ["VŨ"], "易": ["DỊCH", "DỊ"], "戦": ["CHIẾN"], "込": []},
    )
    assert result["standard_characters"] == 3
    assert result["covered"] == 2 and result["first_match"] == 1
    assert result["contains_first"] == 2 and result["contains_all"] == 1


@pytest.mark.parametrize(
    "k,u,expected", [(90, 89, True), (89, 80, False), (90, 90, False), (91, 92, False)]
)
def test_priority_gate_threshold_and_strict_improvement(k, u, expected):
    assert (
        prefer_kanjidic2(
            {
                "kanjidic2": {"first_match_percent": k, "first_match": k},
                "unihan": {"first_match": u},
            }
        )
        is expected
    )


def test_source_priority_and_blank_override(tmp_path):
    path = tmp_path / "overrides.csv"
    path.write_text("kanji,hanviet\n雨,VŨ\n込,\n", encoding="utf-8")
    direct = {"雨": ["VÚ"], "化": ["X"]}
    variants = {"化": (["Y"], "unihan_variant:U+4E00"), "戦": (["CHIẾN"], "unihan_variant:U+4E00")}
    kanji = {"化": ["HÓA"], "込": ["INCORRECT"]}
    assert combine(direct, variants, kanji, path, True) == {
        "雨": (["VŨ"], "override"),
        "化": (["HÓA"], "kanjidic2"),
        "戦": (["CHIẾN"], "unihan_variant:U+4E00"),
        "込": ([], "override"),
    }
    assert combine(direct, variants, kanji, path, False)["化"] == (["X"], "unihan")


def test_review_filter_missing_conflict_multiple_and_agreement():
    assert needs_review([], [], [])
    assert needs_review(["A"], ["A"], ["B"])
    assert needs_review(["A"], ["A", "B", "C"], ["A"])
    assert not needs_review(["A"], ["A"], ["A", "B"])
    assert not needs_review(["A"], [], ["A"])
    assert not needs_review(["A"], ["A", "B", "C"], ["A", "B", "C"])


async def test_seed_kanjidic_source_protection_and_removed_fallback(db, tmp_path):
    from app.modules.auth.models import User
    from app.modules.dictionary.models import Kanji, KanjiEdit
    from app.modules.dictionary.service import seed_hanviet

    user = User(email="m7@example.com", password_hash="unused", role="admin")
    db.add(user)
    db.add_all(
        [
            Kanji(char="化", hanviet=["MANUAL"], hanviet_source="override", meaning=""),
            Kanji(char="甲", hanviet=["OLD"], hanviet_source="unihan_variant:U+4E00", meaning=""),
        ]
    )
    await db.flush()
    db.add(KanjiEdit(char="化", user_id=user.id, field="hanviet", old={}, new={}))
    await db.flush()
    path = tmp_path / "hanviet.csv"
    path.write_text(
        "kanji,hanviet,source\n化,HÓA,kanjidic2\n雨,VŨ,kanjidic2\n甲,,\n", encoding="utf-8"
    )
    await seed_hanviet(db, path)
    assert (await db.get(Kanji, "化")).hanviet == ["MANUAL"]
    assert (await db.get(Kanji, "雨")).hanviet_source == "kanjidic2"
    assert (await db.get(Kanji, "甲")).hanviet == []
    assert await seed_hanviet(db, path) == {"kanji_changed": 0, "words_changed": 0}
