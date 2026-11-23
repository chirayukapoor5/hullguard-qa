import json
import re
from pathlib import Path

import pytest

from hullguard.comparison import create_bundle
from hullguard.geometry import read_obj
from hullguard.models import parse_model
from hullguard.validation import validate_bundle


def mutate(path: Path, before: str, after: str) -> None:
    content = path.read_text(encoding="utf-8")
    assert before in content
    path.write_text(content.replace(before, after, 1), encoding="utf-8")


def test_all_generated_artifacts_are_deterministic(bundle, baseline, tmp_path):
    alternate = tmp_path / "alternate"
    result = create_bundle(baseline, alternate)
    assert result["status"] == "PASS"
    assert set(p.name for p in bundle.iterdir()) == {
        "model.obj",
        "manifest.json",
        "bom.csv",
        "drawing.svg",
        "validation.json",
        "report.html",
    }
    for filename in bundle.iterdir():
        assert filename.read_bytes() == (alternate / filename.name).read_bytes()


@pytest.mark.parametrize(
    ("filename", "before", "after", "code"),
    [
        ("model.obj", "# hullguard units mm", "# hullguard units m", "UNITS"),
        ("model.obj", "f 1 2 4", "f 1 4 2", "MESH_TOPOLOGY"),
        ("model.obj", "f 1 2 4", "f 1 2 3", "MESH_TOPOLOGY"),
        ("model.obj", "f 1 2 4", "f 1 1 2", "MESH_TOPOLOGY"),
        ("model.obj", "v 1100.000 6.000", "v 1099.000 6.000", "POSITION"),
        ("model.obj", "v 1100.000 6.000", "v 1100.000 8.000", "MESH_TOPOLOGY"),
        ("drawing.svg", 'data-thickness-mm="6.0"', 'data-thickness-mm="7.0"', "DRAWING_THICKNESS"),
        (
            "drawing.svg",
            ">P-01    2000 × 1000 × 6",
            ">P-01    2000 × 1000 × 8",
            "DRAWING_ANNOTATION",
        ),
        ("drawing.svg", 'data-component="S-03"', 'data-component="S-09"', "COMPONENT_INVENTORY"),
        (
            "drawing.svg",
            'viewBox="0.0 0.0 2000.0 1000.0"',
            'viewBox="0 0 1900 1000"',
            "DRAWING_VIEW",
        ),
        (
            "drawing.svg",
            'transform="translate(0 1000.0)',
            'transform="translate(0 990)',
            "DRAWING_TRANSFORM",
        ),
        (
            "drawing.svg",
            'width="2000.0" height="1000.0"',
            'width="1800.0" height="1000.0"',
            "DRAWING_SIZE",
        ),
        ("drawing.svg", 'x="1100.0" y="6.0"', 'x="1100.0" y="7.0"', "DRAWING_POSITION"),
        ("bom.csv", ",steel-example,7850,", ",steel-example,8000,", "DENSITY"),
        ("bom.csv", ",steel-example,7850,", ",aluminium,7850,", "MATERIAL"),
        ("bom.csv", ",steel-example,7850,", ",steel-example,wat,", "DENSITY"),
    ],
)
def test_current_revision_does_not_hide_content_errors(
    bundle, baseline, filename, before, after, code
):
    mutate(bundle / filename, before, after)
    findings = validate_bundle(baseline, bundle).findings
    assert any(f.code == code and f.artifact == filename for f in findings)
    assert all(f.code != "STALE_REVISION" for f in findings)


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("model.obj", "o P-01\nv nan 0 0"),
        ("model.obj", "o P-01\nv 1e308 0 0"),
        ("model.obj", "o P-01\nf 1 2 3"),
        ("model.obj", "# hullguard units mm\n# hullguard units m"),
        ("model.obj", "o P-01\no P-01"),
        ("model.obj", "vn 0 0 1"),
        ("manifest.json", "[]"),
        ("manifest.json", '{"components": [1]}'),
        ("manifest.json", '{"components": [], "assembly_mass_kg": NaN}'),
        ("manifest.json", '{"components": [], "assembly_mass_kg": 1e999}'),
        ("drawing.svg", "<svg>"),
        ("drawing.svg", "<img/>"),
        ("drawing.svg", '<svg xmlns="http://www.w3.org/2000/svg"/>'),
        ("bom.csv", "wrong,columns"),
    ],
)
def test_invalid_artifact_is_a_finding(bundle, baseline, filename, content):
    (bundle / filename).write_text(content, encoding="utf-8")
    result = validate_bundle(baseline, bundle).as_dict()
    assert result["status"] == "FAIL"
    assert any(
        f["code"] == "ARTIFACT_INVALID" and f["artifact"] == filename for f in result["findings"]
    )
    json.dumps(result, allow_nan=False)


def test_missing_file_reports_exact_artifact(bundle, baseline):
    (bundle / "bom.csv").unlink()
    (finding,) = validate_bundle(baseline, bundle).findings
    assert (finding.artifact, finding.code) == ("bom.csv", "ARTIFACT_MISSING")


def test_manifest_requires_complete_unique_rows(bundle, baseline):
    path = bundle / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["components"][1] = manifest["components"][0]
    path.write_text(json.dumps(manifest), encoding="utf-8")
    codes = {f.code for f in validate_bundle(baseline, bundle).findings}
    assert codes == {"DUPLICATE_COMPONENT", "COMPONENT_INVENTORY"}


def test_obj_missing_vertices_reports_inventory_and_topology(bundle, baseline):
    path = bundle / "model.obj"
    content = path.read_text(encoding="utf-8")
    path.write_text(re.sub(r"o S-04\n.*", "o S-04\n", content, flags=re.S), encoding="utf-8")
    (finding,) = validate_bundle(baseline, bundle).findings
    assert (finding.code, finding.component) == ("MESH_TOPOLOGY", "S-04")


def test_obj_ignores_extra_comments_and_blank_lines():
    headers, meshes = read_obj("# an explanatory comment\n\n# hullguard units mm")
    assert headers == {"units": "mm"}
    assert not meshes


def test_bom_invalid_mass_and_extra_columns(bundle, baseline):
    path = bundle / "bom.csv"
    lines = path.read_text(encoding="utf-8").splitlines()
    lines[1] = lines[1].rsplit(",", 1)[0] + ",inf"
    path.write_text("\n".join(lines), encoding="utf-8")
    assert {f.code for f in validate_bundle(baseline, bundle).findings} == {"MASS", "ASSEMBLY_MASS"}
    lines[1] += ",extra"
    path.write_text("\n".join(lines), encoding="utf-8")
    assert [f.code for f in validate_bundle(baseline, bundle).findings] == ["ARTIFACT_INVALID"]


def test_project_escapes_markup_in_both_reports(tmp_path, baseline_raw):
    baseline_raw["project"] = "<script>alert(1)</script>"
    model = parse_model(baseline_raw)
    assert create_bundle(model, tmp_path)["status"] == "PASS"
    for filename in ("drawing.svg", "report.html"):
        content = (tmp_path / filename).read_text(encoding="utf-8")
        assert "<script>" not in content
        assert "&lt;script&gt;" in content
