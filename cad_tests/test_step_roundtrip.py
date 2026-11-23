"""Exercise the real FreeCAD runtime and independent engineering references."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from hullguard.models import load_model
from hullguard.reporting import write_json
from scripts.freecad import MANIFEST, export, file_digest, validate

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.fixture(scope="session")
def bundles(freecad, tmp_path_factory):
    parent = tmp_path_factory.mktemp("freecad-bundles")
    prepared = {}
    for name in ("baseline", "thickness_changed"):
        model = load_model(FIXTURES / f"{name}.json")
        output = parent / name
        result = export(model, freecad, output)
        assert result["status"] == "PASS", result["findings"]
        prepared[name] = model, output, result
    return prepared


def record(directory, name, evidence):
    if directory:
        write_json(directory / f"{name}.json", evidence)


def test_baseline_native_and_step_against_hand_calculated_reference(bundles, evidence_directory):
    _, folder, result = bundles["baseline"]
    assert (folder / "model.FCStd").is_file()
    assert len(list(folder.glob("*.step"))) == 8
    for representation in ("native", "step"):
        measured = result[representation]
        plate = measured["components"]["P-01"]
        assert plate["size_mm"] == pytest.approx([2000, 1000, 6])
        assert plate["origin_mm"] == pytest.approx([0, 0, -6])
        assert plate["centroid_mm"] == pytest.approx([1000, 500, -3])
        assert plate["volume_mm3"] == pytest.approx(12_000_000)
        assert plate["mass_kg_from_cad_volume"] == pytest.approx(94.2)
        assert measured["assembly_mass_kg"] == pytest.approx(218.9052256)
    assert result["native"]["components"]["P-01"]["type"] == "Part::Box"
    assert result["native"]["components"]["P-01"]["parameters_mm"] == [2000, 1000, 6]
    record(evidence_directory, "baseline", result)


def test_thickness_revision_preserves_datum_and_reconciles_export(bundles, evidence_directory):
    _, _, result = bundles["thickness_changed"]
    _, _, baseline = bundles["baseline"]
    for representation in ("native", "step"):
        measured = result[representation]
        plate = measured["components"]["P-01"]
        assert plate["size_mm"] == pytest.approx([2000, 1000, 8])
        assert plate["origin_mm"][2] + plate["size_mm"][2] == pytest.approx(0)
        assert plate["centroid_mm"][2] == pytest.approx(-4)
        assert plate["volume_mm3"] == pytest.approx(16_000_000)
        assert plate["mass_kg_from_cad_volume"] == pytest.approx(125.6)
        assert measured["assembly_mass_kg"] - baseline[representation][
            "assembly_mass_kg"
        ] == pytest.approx(31.4)
    assert result["native"]["components"]["P-01"]["parameters_mm"] == [2000, 1000, 8]
    record(evidence_directory, "changed-thickness", result)


def test_missing_step_is_reported_without_inventing_a_missing_native_part(
    bundles,
    freecad,
    tmp_path,
    evidence_directory,
):
    model, original, _ = bundles["baseline"]
    path = shutil.copytree(original, tmp_path / "missing-step")
    (path / "part-S-04.step").unlink()
    result = validate(model, freecad, path)
    assert result["status"] == "FAIL"
    assert {(f["artifact"], f["code"]) for f in result["findings"]} == {
        ("STEP", "CAD_FILE_INVENTORY"),
        ("STEP", "CAD_ASSEMBLY_MASS"),
    }
    assert "S-04" in result["native"]["components"]
    assert "S-04" not in result["step"]["components"]
    record(evidence_directory, "missing-step", result)


def test_stale_native_and_step_fail_revision_and_measurement(
    bundles,
    freecad,
    evidence_directory,
):
    changed, _, _ = bundles["thickness_changed"]
    _, baseline_path, _ = bundles["baseline"]
    result = validate(changed, freecad, baseline_path)
    assert result["status"] == "FAIL"
    codes = {(f["artifact"], f["code"], f["component"]) for f in result["findings"]}
    assert (MANIFEST, "STALE_REVISION", "") in codes
    for artifact in ("model.FCStd", "STEP"):
        assert (artifact, "CAD_DIMENSIONS", "P-01") in codes
        assert (artifact, "CAD_MASS", "P-01") in codes
    record(evidence_directory, "stale-bundle", result)


def test_current_manifest_and_digest_cannot_hide_old_geometry(
    bundles,
    freecad,
    tmp_path,
    evidence_directory,
):
    changed, changed_path, _ = bundles["thickness_changed"]
    _, baseline_path, _ = bundles["baseline"]
    path = shutil.copytree(changed_path, tmp_path / "current-stamp")
    name = "part-P-01.step"
    shutil.copyfile(baseline_path / name, path / name)
    manifest = json.loads((path / MANIFEST).read_text(encoding="utf-8"))
    manifest["files"][name] = file_digest(path / name)
    write_json(path / MANIFEST, manifest)
    result = validate(changed, freecad, path)
    assert result["status"] == "FAIL"
    assert {f["artifact"] for f in result["findings"]} == {"STEP"}
    mass = next(f for f in result["findings"] if f["code"] == "CAD_MASS")
    assert mass["component"] == "P-01"
    assert mass["actual"] == pytest.approx(94.2)
    assert mass["expected"] == pytest.approx(125.6)
    record(evidence_directory, "restamped-step", result)


def test_native_box_can_be_edited_and_resaved_independently_of_step(
    bundles,
    freecad,
    tmp_path,
    evidence_directory,
):
    _, baseline_path, _ = bundles["baseline"]
    changed, _, _ = bundles["thickness_changed"]
    path = shutil.copytree(baseline_path, tmp_path / "edit-native")
    setup = (
        "import FreeCAD as App; "
        f"doc = App.openDocument({ascii(str(path / 'model.FCStd'))}); "
        "plate = next(obj for obj in doc.Objects if obj.HullguardId == 'P-01'); "
        "plate.Height = 8; plate.Placement.Base = App.Vector(0, 0, -8); "
        "doc.recompute(); doc.save(); App.closeDocument(doc.Name)\n"
    )
    shell = subprocess.run(
        [freecad, "--console", "--user-cfg", str(tmp_path / "edit.cfg")],
        input=setup,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )
    assert shell.returncode == 0, shell.stderr
    result = validate(changed, freecad, path)
    assert result["status"] == "FAIL"
    native = result["native"]["components"]["P-01"]
    assert native["parameters_mm"] == [2000, 1000, 8]
    assert native["mass_kg_from_cad_volume"] == pytest.approx(125.6)
    assert result["step"]["components"]["P-01"]["mass_kg_from_cad_volume"] == pytest.approx(94.2)
    assert any(
        f["artifact"] == "STEP" and f["code"] == "CAD_DIMENSIONS" for f in result["findings"]
    )
    assert not any(f["artifact"] == "model.FCStd" for f in result["findings"])
    record(evidence_directory, "native-edit-stale-step", result)


def test_export_refuses_to_replace_existing_evidence(bundles, freecad):
    model, folder, _ = bundles["baseline"]
    before = file_digest(folder / MANIFEST)
    with pytest.raises(ValueError, match="new output directory"):
        export(model, freecad, folder)
    assert file_digest(folder / MANIFEST) == before
