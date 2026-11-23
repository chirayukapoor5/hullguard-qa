"""Generate reproducible positive and intentionally inconsistent evidence bundles."""

import csv
import io
import shutil
from pathlib import Path

from .comparison import compare_models, create_bundle
from .exporters import ARTIFACTS
from .models import ModelError, load_model
from .reporting import Finding, Validation, write_json, write_text
from .validation import validate_bundle

REVISIONS = {
    "baseline": "Baseline",
    "thickness_changed": "Plate thickness revision",
    "stiffener_changed": "Stiffener arrangement revision",
}
FAULTS = (
    (
        "stale_bom",
        "Stale BOM",
        "bom.csv",
        "STALE_REVISION",
        "Baseline BOM retained after the plate edit.",
    ),
    (
        "stale_drawing",
        "Outdated drawing",
        "drawing.svg",
        "DRAWING_THICKNESS",
        "Baseline plan retained after the plate edit.",
    ),
    (
        "missing_stiffener",
        "Missing stiffener",
        "model.obj",
        "COMPONENT_INVENTORY",
        "S-04 removed from the OBJ while the source still expects it.",
    ),
    (
        "wrong_units",
        "Wrong volume conversion",
        "bom.csv",
        "MASS",
        "First BOM row volume and mass inflated 1,000×.",
    ),
    (
        "invalid_thickness",
        "Invalid thickness",
        "model.json",
        "INPUT_DIMENSION",
        "Bottom plate thickness set to zero.",
    ),
    (
        "duplicate_id",
        "Duplicate ID",
        "model.json",
        "INPUT_DUPLICATE_ID",
        "Two stiffeners assigned S-03.",
    ),
)


def check_input(path: Path) -> dict:
    try:
        model = load_model(path)
    except ModelError as error:
        result = Validation(
            "",
            (Finding(error.code, path.name, "", "valid canonical model", str(error)),),
            ("canonical model",),
        )
    else:
        result = Validation(model.revision, (), ("canonical model",))
    return result.as_dict()


def fault_bundle(scenario: str, target: Path, baseline: Path, revised: Path) -> str:
    target.mkdir(parents=True, exist_ok=True)
    source = revised if scenario in {"stale_bom", "stale_drawing"} else baseline
    for filename in (*ARTIFACTS, "model.json"):
        shutil.copyfile(source / filename, target / filename)
    if scenario in {"stale_bom", "stale_drawing"}:
        filename = {"stale_bom": "bom.csv", "stale_drawing": "drawing.svg"}[scenario]
        shutil.copyfile(baseline / filename, target / filename)
    elif scenario == "missing_stiffener":
        # S-04 is the last object in the sorted baseline OBJ.
        path = target / "model.obj"
        kept, separator, _ = path.read_text(encoding="utf-8").partition("o S-04\n")
        if not separator:
            raise ValueError("Missing S-04 in healthy mesh")
        write_text(path, kept)
    elif scenario == "wrong_units":
        path = target / "bom.csv"
        rows = list(csv.reader(io.StringIO(path.read_text(encoding="utf-8"))))
        for field in ("volume_m3", "mass_kg"):
            index = rows[0].index(field)
            rows[1][index] = str(float(rows[1][index]) * 1000)
        stream = io.StringIO(newline="")
        csv.writer(stream, lineterminator="\n").writerows(rows)
        write_text(path, stream.getvalue())
    return f"python -m hullguard validate {target.as_posix()}/model.json {target.as_posix()}"


def generate_evidence(fixtures: Path, output: Path) -> dict:
    baseline = load_model(fixtures / "baseline.json")
    catalog: dict[str, list] = {"revisions": [], "faults": []}
    for key, title in REVISIONS.items():
        model = load_model(fixtures / f"{key}.json")
        target = output / "revisions" / key
        comparison = compare_models(baseline, model) if key != "baseline" else None
        result = create_bundle(model, target, comparison)
        write_json(target / "model.json", model.canonical())
        catalog["revisions"].append(
            {
                "id": key,
                "title": title,
                "directory": f"revisions/{key}",
                "revision": model.revision,
                "validation": result,
            }
        )

    for key, title, filename, detector, description in FAULTS:
        target = output / "faults" / key
        relative = f"faults/{key}"
        if filename == "model.json":
            target.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(fixtures / "faults" / f"{key}.json", target / filename)
            result = check_input(target / filename)
            command = f"python -m hullguard check {target.as_posix()}/model.json"
        else:
            command = fault_bundle(
                key, target, output / "revisions/baseline", output / "revisions/thickness_changed"
            )
            model = load_model(target / "model.json")
            result = validate_bundle(model, target).as_dict()
        write_json(target / "validation.json", result)
        findings = result["findings"]
        observed = sorted({f["code"] for f in findings})
        matched = any(f["code"] == detector and f["artifact"] == filename for f in findings)
        catalog["faults"].append(
            {
                "id": key,
                "title": title,
                "description": description,
                "directory": relative,
                "artifact": filename,
                "expected_detector": detector,
                "observed_detectors": observed,
                "matched": matched,
                "reproduce": command,
                "validation": result,
            }
        )
    write_json(output / "index.json", catalog)
    return catalog


def evidence_passes(catalog: dict, *, faults_only: bool = False) -> bool:
    healthy = all(row["validation"]["status"] == "PASS" for row in catalog["revisions"])
    detected = all(
        row["matched"] and row["validation"]["status"] == "FAIL" for row in catalog["faults"]
    )
    return detected and (faults_only or healthy)
