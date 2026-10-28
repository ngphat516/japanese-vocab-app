from pathlib import Path

import pytest

from app.nlp.hanviet import combined_readings
from scripts.build_hanviet_m7c import review_required
from scripts.build_hanviet_unihan import apply_overrides
from scripts.hanviet_sources import score, score_iy_insensitive


def test_locked_readings_win_combined_and_do_not_add_unihan_only_readings():
    result = combined_readings(
        {"容", "森", "税", "治", "込", "甲"},
        {
            "容": ["DONG"],
            "森": ["SÂM"],
            "税": ["THOÁT", "THUẾ"],
            "治": ["TRÌ", "TRỊ"],
            "込": ["LIÊU"],
        },
        {
            "容": (["DUNG"], "unihan"),
            "森": (["CHÙM"], "unihan"),
            "税": (["THUẾ"], "unihan"),
            "治": (["TRỊ"], "unihan"),
            "题": (["ĐỀ"], "unihan"),
        },
    )
    assert result["容"] == (["DONG"], "kanjidic2")
    assert result["森"] == (["SÂM"], "kanjidic2")
    assert result["税"] == (["THUẾ", "THOÁT"], "kanjidic2_unihan")
    assert result["治"][0][0] == "TRỊ"
    assert "题" not in result and "甲" not in result
    locked = apply_overrides(result, Path("data/hanviet_overrides.csv"))
    assert locked["容"] == (["DUNG"], "override")
    assert locked["込"] == ([], "override")
    assert locked["営"] == (["DOANH", "DINH"], "override")
    assert locked["姉"] == (["TỶ"], "override")
    assert "繰" not in locked and "扱" not in locked


def test_iy_diagnostic_preserves_data_and_tone():
    source = {"記": ["KÍ"], "技": ["KĨ"], "寄": ["KI"]}
    standard = {"記": ["KÝ"], "技": ["KỸ"], "寄": ["KÝ"]}
    assert score(source, standard)["first_match"] == 0
    assert score_iy_insensitive(source, standard)["first_match"] == 2
    assert source == {"記": ["KÍ"], "技": ["KĨ"], "寄": ["KI"]}


@pytest.mark.parametrize(
    "char,values,source,k,expected",
    [
        ("森", ["SÂM"], "kanjidic2", ["SÂM"], False),
        ("甲", [], None, [], True),
        ("乙", ["A", "B"], "kanjidic2", ["A", "B"], True),
        ("丙", ["B", "A"], "kanjidic2_unihan", ["A", "B"], True),
        ("丁", ["A", "B"], "kanjidic2_unihan", ["A", "B"], False),
        ("容", ["DUNG"], "override", ["DONG", "DUNG"], False),
        ("繰", ["A"], "kanjidic2_unihan", ["A"], True),
        ("扱", ["A"], "unihan", [], True),
    ],
)
def test_review_four_filter(char, values, source, k, expected):
    assert review_required(char, values, source, k) is expected


async def test_seed_combined_population_idempotence_and_manual_protections(
    authorized, seeded, db, tmp_path
):
    from app.modules.auth.service import current_user
    from app.modules.dictionary import service
    from app.modules.dictionary.models import Kanji

    client, _ = authorized
    user = await current_user(db, client.headers["authorization"][7:])
    user.role = "admin"
    db.add_all(
        [
            Kanji(char="容", hanviet=["DUNG"], hanviet_source="override", meaning=""),
            Kanji(char="题", hanviet=["OLD"], hanviet_source="unihan", meaning=""),
        ]
    )
    await db.flush()
    auto = await service.create_word(db, "森", "もり")
    manual = await service.create_word(db, "森林", "しんりん")
    assert (
        await client.patch(f"/api/v1/words/{manual.id}", json={"hanviet": "MANUAL"})
    ).status_code == 200
    assert (await client.patch("/api/v1/kanji/緊", json={"hanviet": ["PATCH"]})).status_code == 200
    path, overrides = tmp_path / "data.csv", tmp_path / "overrides.csv"
    path.write_text(
        "kanji,hanviet,source\n容,DONG,kanjidic2\n森,SÂM,kanjidic2\n税,THUẾ|THOÁT,kanjidic2_unihan\n緊,OLD,kanjidic2\n込,LIÊU,kanjidic2\n",
        encoding="utf-8",
    )
    overrides.write_text("kanji,hanviet\n容,DUNG\n込,\n题,ĐỀ\n", encoding="utf-8")
    population = {"容", "森", "税", "緊", "込"}
    await service.seed_hanviet(db, path, overrides, population=population)
    assert (await db.get(Kanji, "容")).hanviet == ["DUNG"]
    assert (await db.get(Kanji, "緊")).hanviet == ["PATCH"]
    assert (await db.get(Kanji, "込")).hanviet == []
    outside = await db.get(Kanji, "题")
    assert outside.hanviet == [] and outside.hanviet_source is None
    assert auto.hanviet == "SÂM" and manual.hanviet == "MANUAL"
    assert (await client.get("/api/v1/kanji/税")).json()["hanviet_source"] == "kanjidic2_unihan"
    assert await service.seed_hanviet(db, path, overrides, population=population) == {
        "kanji_changed": 0,
        "words_changed": 0,
    }
