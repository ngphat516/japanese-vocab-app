import pytest

from scripts.build_hanviet_unihan import build, parse


def test_unihan_offline_dedup_normalization_and_coverage(tmp_path):
    source = tmp_path / "Unihan_Readings.txt"
    source.write_text(
        "# Unicode\nU+79C1\tkVietnamese\ttư tư\nU+91D1\tkVietnamese\tkim câm\nU+91D1\tkDefinition\tgold\n",
        encoding="utf-8",
    )
    assert parse(source) == {"私": ["TƯ"], "金": ["KIM", "CÂM"]}
    report = build(
        source,
        tmp_path / "hanviet.csv",
        version="17.0.0",
        characters={"私", "金", "猫"},
        sample_path=tmp_path / "sample.md",
    )
    assert report["covered"] == 2 and report["local_multiple_readings"] == 1
    assert report["coverage_percent"] == pytest.approx(200 / 3)
    assert "KIM|CÂM" in (tmp_path / "hanviet.csv").read_text(encoding="utf-8")
    assert "chưa seed DB" in (tmp_path / "sample.md").read_text(encoding="utf-8")
