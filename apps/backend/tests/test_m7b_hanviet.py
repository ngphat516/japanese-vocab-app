import pytest

from scripts.evaluate_hanviet_m7b import candidate_combined, passes_gate, reviewed_standard


@pytest.mark.parametrize(
    "char,k,u,expected",
    [
        ("税", ["THOÁT", "THỐI", "THUẾ", "THUÊ"], ["THUẾ"], ["THUẾ", "THOÁT", "THỐI", "THUÊ"]),
        ("治", ["TRÌ", "TRỊ"], ["TRỊ"], ["TRỊ", "TRÌ"]),
        ("森", ["SÂM"], ["CHÙM"], ["SÂM"]),
        ("甲", ["A", "B", "C"], ["X", "C", "B"], ["C", "A", "B"]),
    ],
)
def test_candidate_reorders_first_shared_without_adding_unihan(char, k, u, expected):
    result = candidate_combined({char}, {char: k}, {char: (u, "unihan")})
    assert result[char][0] == expected and k != []
    assert result[char][1] == ("kanjidic2_unihan" if set(k) & set(u) else "kanjidic2")
    assert set(result[char][0]) == set(k)


def test_membership_not_vietnam_reading_controls_population():
    result = candidate_combined(
        {"森", "込"},
        {"森": ["SÂM"], "题": ["ĐỀ"]},
        {"込": (["LIÊU"], "unihan_variant:U+4E00"), "题": (["ĐỀ"], "unihan")},
    )
    assert set(result) == {"森", "込"}
    assert result["込"] == (["LIÊU"], "unihan_variant:U+4E00")


def test_override_wins_candidate_and_blank_override(tmp_path):
    from scripts.build_hanviet_unihan import apply_overrides

    path = tmp_path / "override.csv"
    path.write_text("kanji,hanviet\n森,CUSTOM\n込,\n", encoding="utf-8")
    candidate = candidate_combined({"森", "込"}, {"森": ["SÂM"], "込": ["LIÊU"]}, {})
    assert apply_overrides(candidate, path) == {
        "森": (["CUSTOM"], "override"),
        "込": ([], "override"),
    }


def test_standard_keeps_reviewed_order_overrides_and_blanks(tmp_path):
    path = tmp_path / "review.md"
    path.write_text(
        "| Chữ | Âm |\n| 森 | SÂM / CHÙM |\n| 化 | HOÁ |\n| 込 | — |\n", encoding="utf-8"
    )
    assert reviewed_standard([path], {"森": (["CUSTOM"], "override")}, 3) == {
        "森": ["CUSTOM"],
        "化": ["HÓA"],
        "込": [],
    }
    with pytest.raises(ValueError, match="Expected"):
        reviewed_standard([path], {}, 300)
    with pytest.raises(ValueError, match="Duplicate"):
        reviewed_standard([path, path], {}, 3)


@pytest.mark.parametrize(
    "candidate,current,expected",
    [
        (94.48, 72.58, False),
        (94.48, 98.49, False),
        (95, 94, True),
        (95, 95, False),
    ],
)
def test_gate_requires_95_percent_and_strict_improvement(candidate, current, expected):
    assert (
        passes_gate({"first_match_percent": candidate}, {"first_match_percent": current})
        is expected
    )
