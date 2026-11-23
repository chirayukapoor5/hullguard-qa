import json

import pytest

from hullguard.models import ModelError, load_model, parse_model


@pytest.mark.parametrize(
    ("key", "value", "code"),
    [
        ("schema", True, "INPUT_SCHEMA"),
        ("schema", 2, "INPUT_SCHEMA"),
        ("units", {"length": "m"}, "INPUT_UNITS"),
        ("materials", {"steel-example": 8000}, "INPUT_MATERIAL"),
        ("project", " ", "INPUT_SCHEMA"),
        ("project", "break\nline", "INPUT_SCHEMA"),
        ("components", [], "INPUT_SCHEMA"),
        ("components", "plate", "INPUT_SCHEMA"),
    ],
)
def test_canonical_schema_rejections(baseline_raw, key, value, code):
    baseline_raw[key] = value
    with pytest.raises(ModelError) as failure:
        parse_model(baseline_raw)
    assert failure.value.code == code


@pytest.mark.parametrize(
    ("key", "value", "code"),
    [
        ("id", "p 1", "INPUT_ID"),
        ("kind", [], "INPUT_KIND"),
        ("material", "aluminium", "INPUT_MATERIAL"),
        ("origin_mm", [0, 0], "INPUT_SCHEMA"),
        ("origin_mm", [0, False, -6], "INPUT_NUMBER"),
        ("origin_mm", [0, 0, float("nan")], "INPUT_NUMBER"),
        ("origin_mm", [0, float("inf"), -6], "INPUT_NUMBER"),
        ("origin_mm", [1_000_001, 0, -6], "INPUT_NUMBER"),
        ("size_mm", [2000, 1000, 0], "INPUT_DIMENSION"),
        ("size_mm", [-1, 1000, 6], "INPUT_DIMENSION"),
        ("size_mm", [2000, 1000, 0.0009], "INPUT_DIMENSION"),
        ("size_mm", [2000.0001, 1000, 6], "INPUT_PRECISION"),
        ("origin_mm", [0, 0, -7], "INPUT_PLACEMENT"),
    ],
)
def test_component_validation(baseline_raw, key, value, code):
    baseline_raw["components"][0][key] = value
    with pytest.raises(ModelError) as failure:
        parse_model(baseline_raw)
    assert failure.value.code == code
    if key in {"origin_mm", "size_mm"}:
        assert "P-01" in str(failure.value)


@pytest.mark.parametrize(
    ("index", "change", "code"),
    [
        (0, {"kind": "side"}, "INPUT_PLACEMENT"),
        (1, {"origin_mm": [0, 1, 0]}, "INPUT_PLACEMENT"),
        (4, {"origin_mm": [-1, 272, 0]}, "INPUT_PLACEMENT"),
        (4, {"origin_mm": [0, 272, 0.001]}, "INPUT_PLACEMENT"),
        (4, {"size_mm": [50, 8, 68]}, "INPUT_PLACEMENT"),
        (4, {"size_mm": [1100.001, 8, 68]}, "INPUT_OVERLAP"),
        (6, {"id": "S-04"}, "INPUT_DUPLICATE_ID"),
    ],
)
def test_placement_rejection(baseline_raw, index, change, code):
    baseline_raw["components"][index].update(change)
    with pytest.raises(ModelError) as failure:
        parse_model(baseline_raw)
    assert failure.value.code == code


def test_missing_part_field_points_to_schema(baseline_raw):
    del baseline_raw["components"][0]["origin_mm"]
    with pytest.raises(ModelError, match="origin_mm"):
        parse_model(baseline_raw)


def test_schema_rejects_excess_component_count(baseline_raw):
    baseline_raw["components"] *= 26
    with pytest.raises(ModelError, match="1–200"):
        parse_model(baseline_raw)


def test_revision_is_invariant_to_order_and_numeric_spelling(baseline_raw):
    original = parse_model(baseline_raw)
    baseline_raw["components"].reverse()
    baseline_raw["components"][-1]["origin_mm"][0] = -0.0
    baseline_raw["materials"]["steel-example"] = 7850.0
    assert parse_model(baseline_raw).revision == original.revision


def test_minimum_thickness_is_supported(baseline_raw):
    baseline_raw["components"][0]["origin_mm"][2] = -0.001
    baseline_raw["components"][0]["size_mm"][2] = 0.001
    model = parse_model(baseline_raw)
    part = next(p for p in model.components if p.id == "P-01")
    assert part.thickness_mm == 0.001
    assert part.maximum_mm == (2000, 1000, 0)


@pytest.mark.parametrize("content", ["{", '{"schema": 1, "schema": 1}', b"\x80"])
def test_corrupt_json_has_read_error(tmp_path, content):
    path = tmp_path / "broken.json"
    path.write_bytes(content.encode() if isinstance(content, str) else content)
    with pytest.raises(ModelError) as failure:
        load_model(path)
    assert failure.value.code == "INPUT_READ"


def test_saved_source_can_be_reloaded_with_bom_marker(tmp_path, baseline):
    path = tmp_path / "saved.json"
    path.write_text(json.dumps(baseline.canonical()), encoding="utf-8-sig")
    assert load_model(path) == baseline
