"""Adversarial regression cases for artifact oracles."""

import csv
import json

import pytest

from hullguard.comparison import create_bundle
from hullguard.models import parse_model
from hullguard.validation import validate_bundle


@pytest.mark.parametrize(("volume", "mass"), [("0", "0"), ("1e-15", "7.85e-12")])
def test_wrong_mass_and_volume_fail_even_below_absolute_tolerance(
    baseline_raw, tmp_path, volume, mass
):
    plate = next(part for part in baseline_raw["components"] if part["kind"] == "bottom")
    plate.update(origin_mm=[0, 0, -0.001], size_mm=[0.001, 0.001, 0.001])
    baseline_raw["components"] = [plate]
    model = parse_model(baseline_raw)
    assert create_bundle(model, tmp_path)["status"] == "PASS"
    bom = tmp_path / "bom.csv"
    with bom.open(newline="", encoding="utf-8") as stream:
        header, row = list(csv.reader(stream))
    row[header.index("volume_m3")] = volume
    row[header.index("mass_kg")] = mass
    with bom.open("w", newline="", encoding="utf-8") as stream:
        csv.writer(stream).writerows([header, row])
    result = validate_bundle(model, tmp_path)
    assert {(f.artifact, f.code) for f in result.findings} == {
        ("bom.csv", "VOLUME"),
        ("bom.csv", "MASS"),
        ("bom.csv", "ASSEMBLY_MASS"),
    }


@pytest.mark.parametrize("schema", [True, 1.0])
def test_manifest_schema_rejects_numeric_lookalikes(baseline, bundle, schema):
    path = bundle / "manifest.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["schema"] = schema
    path.write_text(json.dumps(data), encoding="utf-8")
    assert [f.code for f in validate_bundle(baseline, bundle).findings] == ["MANIFEST_SCHEMA"]


@pytest.mark.parametrize("element", ["rect", "text"])
def test_svg_local_transform_cannot_move_current_geometry_or_annotation(baseline, bundle, element):
    path = bundle / "drawing.svg"
    text = path.read_text(encoding="utf-8")
    tag = (
        next(
            fragment
            for fragment in text.split("<")
            if fragment.startswith(element + " ") and 'data-component="P-01"' in fragment
        )
        .split(">", 1)[0]
        .strip()
        .rstrip("/")
        .strip()
    )
    path.write_text(
        text.replace(f"<{tag}", f'<{tag} transform="translate(120 0)"', 1), encoding="utf-8"
    )
    assert [(f.code, f.component) for f in validate_bundle(baseline, bundle).findings] == [
        ("DRAWING_EXTRA_TRANSFORM", "P-01")
    ]


def test_large_coordinates_keep_absolute_dimension_tolerance(baseline_raw, tmp_path):
    plate = next(part for part in baseline_raw["components"] if part["kind"] == "bottom")
    plate["origin_mm"][0] = 1_000_000
    baseline_raw["components"] = [plate]
    model = parse_model(baseline_raw)
    assert create_bundle(model, tmp_path)["status"] == "PASS"
    path = tmp_path / "manifest.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    # A numerically small absolute shift at a large world coordinate still changes the position.
    data["components"][0]["origin_mm"][0] += 0.000002
    path.write_text(json.dumps(data), encoding="utf-8")
    assert [f.code for f in validate_bundle(model, tmp_path).findings] == ["POSITION"]


def test_failed_publish_does_not_leave_earlier_pass_attestation(
    baseline,
    fixture_dir,
    bundle,
    monkeypatch,
):
    from pathlib import Path

    from hullguard.models import load_model

    revised = load_model(fixture_dir / "thickness_changed.json")
    replace = Path.replace

    def fail_on_bom(path, target):
        if Path(target) == bundle / "bom.csv":
            raise PermissionError("synthetic write interruption")
        return replace(path, target)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "replace", fail_on_bom)
        with pytest.raises(PermissionError, match="synthetic write interruption"):
            create_bundle(revised, bundle)
    assert not (bundle / "validation.json").exists()
    assert not (bundle / "report.html").exists()
    assert validate_bundle(revised, bundle).as_dict()["status"] == "FAIL"
    assert create_bundle(baseline, bundle)["status"] == "PASS"


def test_competing_export_cannot_replace_previous_bundle(baseline, bundle):
    lock = bundle / ".hullguard-write"
    lock.mkdir()
    committed = (bundle / "validation.json").read_bytes()
    with pytest.raises(OSError, match="Export directory is locked"):
        create_bundle(baseline, bundle)
    assert (bundle / "validation.json").read_bytes() == committed
    assert lock.is_dir()
