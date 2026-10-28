from scripts.build_hanviet_unihan import parse_variants, with_variants


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
