import json
import subprocess
import sys

import pytest

from hullguard.cli import main
from hullguard.scenarios import evidence_passes, generate_evidence


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "hullguard", *map(str, args)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_installed_entry_workflow(fixture_dir, tmp_path):
    baseline = fixture_dir / "baseline.json"
    destination = tmp_path / "exports with spaces"
    exported = run_cli("export", baseline, destination)
    assert exported.returncode == 0, exported.stderr
    assert json.loads(exported.stdout)["status"] == "PASS"
    validated = run_cli("validate", baseline, destination)
    assert validated.returncode == 0, validated.stderr
    assert json.loads(validated.stdout)["checked"] == [
        "model.obj",
        "manifest.json",
        "bom.csv",
        "drawing.svg",
    ]


def test_compare_can_reconcile_old_exports_against_new_source(
    fixture_dir, tmp_path, bundle, capsys
):
    output = tmp_path / "changed"
    args = [
        "compare",
        str(fixture_dir / "baseline.json"),
        str(fixture_dir / "thickness_changed.json"),
        str(output),
        "--against",
        str(bundle),
    ]
    assert main(args) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["validation"]["status"] == "PASS"
    assert data["candidate_validation"]["status"] == "FAIL"
    assert {
        f["artifact"]
        for f in data["candidate_validation"]["findings"]
        if f["code"] == "STALE_REVISION"
    } == {"bom.csv", "drawing.svg", "manifest.json", "model.obj"}
    assert (output / "comparison.json").exists()
    report = (output / "report.html").read_text(encoding="utf-8")
    assert "Change impact" in report
    assert "Candidate export status <strong>FAIL</strong>" in report


def test_compare_fresh_outputs_pass(fixture_dir, capsys, tmp_path):
    assert (
        main(
            [
                "compare",
                str(fixture_dir / "baseline.json"),
                str(fixture_dir / "thickness_changed.json"),
                str(tmp_path),
            ]
        )
        == 0
    )
    data = json.loads(capsys.readouterr().out)
    assert data["delta_mass_kg"] == pytest.approx(31.4)


def test_plain_export_replaces_stale_comparison_sidecar(fixture_dir, tmp_path):
    baseline = str(fixture_dir / "baseline.json")
    changed = str(fixture_dir / "thickness_changed.json")
    destination = str(tmp_path)
    assert main(["compare", baseline, changed, destination]) == 0
    assert (tmp_path / "comparison.json").exists()
    assert main(["export", baseline, destination]) == 0
    assert not (tmp_path / "comparison.json").exists()


def test_cli_distinguishes_invalid_model_from_finding(fixture_dir, tmp_path, capsys):
    bad_model = fixture_dir / "faults/invalid_thickness.json"
    assert main(["export", str(bad_model), str(tmp_path)]) == 2
    assert json.loads(capsys.readouterr().out)["code"] == "INPUT_DIMENSION"
    assert main(["validate", str(fixture_dir / "baseline.json"), str(tmp_path)]) == 1
    assert len(json.loads(capsys.readouterr().out)["findings"]) == 4


def test_check_model_status(fixture_dir, capsys):
    assert main(["check", str(fixture_dir / "baseline.json")]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "PASS"


def test_generate_cli_produces_browser_catalog(fixture_dir, tmp_path, capsys):
    assert main(["demo", "--fixtures", str(fixture_dir), "--out", str(tmp_path)]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert (summary["revisions"], summary["faults"]) == (3, 6)
    catalog = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    for row in catalog["revisions"]:
        assert row["validation"]["status"] == "PASS"
        assert (tmp_path / row["directory"] / "model.obj").is_file()


@pytest.fixture(scope="module")
def fault_evidence(tmp_path_factory, fixture_dir=None):
    from conftest import FIXTURES

    root = tmp_path_factory.mktemp("controlled-faults")
    return root, generate_evidence(FIXTURES, root)


@pytest.mark.fault
@pytest.mark.parametrize(
    ("scenario", "artifact", "detector", "exit_code", "component"),
    [
        ("stale_bom", "bom.csv", "STALE_REVISION", 1, "P-01"),
        ("stale_drawing", "drawing.svg", "DRAWING_THICKNESS", 1, "P-01"),
        ("missing_stiffener", "model.obj", "COMPONENT_INVENTORY", 1, ""),
        ("wrong_units", "bom.csv", "MASS", 1, "B-01"),
        ("invalid_thickness", "model.json", "INPUT_DIMENSION", 2, ""),
        ("duplicate_id", "model.json", "INPUT_DUPLICATE_ID", 2, ""),
    ],
)
def test_faults_fail_for_documented_reason(
    fault_evidence, scenario, artifact, detector, exit_code, component
):
    root, catalog = fault_evidence
    row = next(row for row in catalog["faults"] if row["id"] == scenario)
    directory = root / row["directory"]
    path = directory / "model.json"
    run = run_cli("check", path) if exit_code == 2 else run_cli("validate", path, directory)
    assert run.returncode == exit_code, run.stderr
    result = json.loads(run.stdout)
    assert result["status"] == "FAIL"
    assert result == json.loads((directory / "validation.json").read_text(encoding="utf-8"))
    assert row["matched"]
    assert {f["artifact"] for f in result["findings"]} == {artifact}
    assert any((f["code"], f["component"]) == (detector, component) for f in result["findings"])


def test_catalog_fails_when_expected_detection_is_absent(fixture_dir, tmp_path):
    data = generate_evidence(fixture_dir, tmp_path)
    assert evidence_passes(data)
    data["revisions"][0]["validation"]["status"] = "FAIL"
    assert not evidence_passes(data)
    assert evidence_passes(data, faults_only=True)
    data["faults"][0]["matched"] = False
    assert not evidence_passes(data, faults_only=True)
