"""Export and reconcile editable FreeCAD boxes and per-component STEP solids."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from math import fsum
from pathlib import Path

from hullguard.models import DENSITY, Model, ModelError, load_model, unique_fields
from hullguard.reporting import Finding, Validation, write_json
from hullguard.validation import ArtifactCheck, close, close_vector, reference_values

NATIVE = "model.FCStd"
MANIFEST = "cad-manifest.json"
VOLUME_TOL_MM3 = 1e-9
MASS_FACTOR = 1e-9


def resolve_command(command: str) -> str:
    executable = shutil.which(command)
    if executable is None:
        raise ValueError(
            "FreeCAD console executable unavailable. Set --freecad or HULLGUARD_FREECAD "
            "to the full path of FreeCADCmd.exe or freecadcmd."
        )
    return str(Path(executable).resolve())


def run_worker(
    executable: str, operation: str, directory: Path, model: Model | None = None
) -> dict:
    worker = Path(__file__).with_name("freecad_worker.py").resolve()
    with tempfile.TemporaryDirectory(prefix="hullguard-cad-job-") as temp:
        job = Path(temp) / "job.json"
        result = Path(temp) / "result.json"
        write_json(
            job,
            {
                "directory": str(directory.resolve()),
                "operation": operation,
                "result": str(result),
                "model": model.canonical() if model else None,
            },
        )
        command = (
            f"import runpy; runpy.run_path({ascii(str(worker))})['execute']({ascii(str(job))})\n"
        )
        process = subprocess.run(
            [executable, "--console", "--user-cfg", str(Path(temp) / "user.cfg")],
            input=command,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=120,
            check=False,
        )
        if process.returncode or not result.is_file():
            detail = (process.stderr + "\n" + process.stdout).strip()[-1500:]
            raise ValueError(f"FreeCAD console did not complete the {operation} job: {detail}")
        data = json.loads(result.read_text(encoding="utf-8"))
        if "worker_error" in data:
            raise ValueError(f"FreeCAD {operation}: {data['worker_error']}")
        return data


def file_digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def step_name(component: str) -> str:
    return f"part-{component}.step"


def check_shapes(model: Model, rows: dict, artifact: str, findings: list[Finding]) -> dict:
    check = ArtifactCheck(model, artifact, findings)
    measured = {}
    for ident, part in check.parts.items():
        if ident not in rows:
            continue
        row = rows[ident]
        if artifact == NATIVE:
            check.equal("CAD_EDITABLE", "Part::Box", row["type"], ident)
            check.equal("CAD_LABEL", ident, row["label"], ident)
            check.vector("CAD_BOX_PARAMETERS", part.size_mm, row["parameters_mm"], ident)
        check.equal(
            "CAD_VALID_SOLID",
            (True, 1, "Solid"),
            (row["valid"], row["solid_count"], row["topology"]),
            ident,
        )
        for code, key, expected in (
            ("CAD_POSITION", "origin_mm", part.origin_mm),
            ("CAD_DIMENSIONS", "size_mm", part.size_mm),
            (
                "CAD_CENTROID",
                "centroid_mm",
                tuple(
                    origin + size / 2
                    for origin, size in zip(part.origin_mm, part.size_mm, strict=True)
                ),
            ),
        ):
            observed = row[key]
            check.expect(
                close_vector(observed, expected),
                code,
                expected,
                observed,
                ident,
            )
        expected_volume, expected_mass = reference_values(part)
        observed_volume = row["volume_mm3"]
        inferred_mass = observed_volume * MASS_FACTOR * DENSITY[part.material]
        check.expect(
            observed_volume > 0
            and close(observed_volume, expected_volume / MASS_FACTOR, VOLUME_TOL_MM3),
            "CAD_VOLUME",
            expected_volume / MASS_FACTOR,
            observed_volume,
            ident,
        )
        check.expect(
            inferred_mass > 0 and close(inferred_mass, expected_mass, 1e-9),
            "CAD_MASS",
            expected_mass,
            inferred_mass,
            ident,
        )
        measured[ident] = {**row, "mass_kg_from_cad_volume": inferred_mass}
    observed_total = fsum(row["mass_kg_from_cad_volume"] for row in measured.values())
    check.scalar("CAD_ASSEMBLY_MASS", check.expected_total, observed_total, tolerance=1e-9)
    return {"components": measured, "assembly_mass_kg": observed_total}


def check_provenance(model: Model, directory: Path, findings: list[Finding]) -> None:
    check = ArtifactCheck(model, MANIFEST, findings)
    try:
        manifest = json.loads(
            (directory / MANIFEST).read_text(encoding="utf-8"), object_pairs_hook=unique_fields
        )
        if (
            not isinstance(manifest, dict)
            or type(manifest.get("schema")) is not int
            or manifest["schema"] != 1
            or not isinstance(manifest.get("files"), dict)
        ):
            raise ValueError("expected a schema 1 CAD manifest and file digest map")
        files = manifest["files"]
        expected = {NATIVE, *(step_name(part.id) for part in model.components)}
        check.revision(
            manifest.get("revision") if isinstance(manifest.get("revision"), str) else None
        )
        check.equal("CAD_FILE_INVENTORY", sorted(expected), sorted(files))
        for name in sorted(expected):
            path = directory / name
            if path.is_file():
                actual = file_digest(path)
                expected_digest = files.get(name)
                check.equal(
                    "CAD_DIGEST",
                    expected_digest if isinstance(expected_digest, str) else None,
                    actual,
                    name,
                )
    except (OSError, ValueError) as error:
        check.equal("CAD_MANIFEST", "readable CAD manifest", str(error))


def validate(model: Model, executable: str, directory: Path) -> dict:
    findings: list[Finding] = []
    check_provenance(model, directory, findings)
    parts = {part.id: step_name(part.id) for part in model.components}
    observed = sorted(p.name for p in directory.glob("*.step") if p.is_file())
    step_check = ArtifactCheck(model, "STEP", findings)
    step_check.equal("CAD_FILE_INVENTORY", sorted(parts.values()), observed)
    if not (directory / NATIVE).is_file():
        findings.append(Finding("CAD_NATIVE_MISSING", NATIVE, "", "editable FCStd document", None))
    data = run_worker(executable, "inspect", directory)
    for artifact, message in data["read_errors"].items():
        findings.append(
            Finding("CAD_READ", artifact, "", "readable CAD solid or document", message)
        )
    native = ArtifactCheck(model, NATIVE, findings)
    native_rows = native.inventory([(row["id"], row) for row in data["native"]])
    step_rows = {ident: data["step"][name] for ident, name in parts.items() if name in data["step"]}
    native_measurements = check_shapes(model, native_rows, NATIVE, findings)
    step_measurements = check_shapes(model, step_rows, "STEP", findings)
    evidence = Validation(model.revision, tuple(findings), (MANIFEST, NATIVE, "STEP")).as_dict()
    return {
        **evidence,
        "freecad_version": data["freecad_version"],
        "native": native_measurements,
        "step": step_measurements,
    }


def export(model: Model, executable: str, output: Path) -> dict:
    if output.exists():
        raise ValueError("Choose a new output directory for the CAD bundle.")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".hullguard-cad-", dir=output.parent) as temp:
        staging = Path(temp) / "bundle"
        staging.mkdir()
        created = run_worker(executable, "create", staging, model)
        write_json(
            staging / MANIFEST,
            {
                "schema": 1,
                "revision": model.revision,
                "freecad_version": created["freecad_version"],
                "files": {path.name: file_digest(path) for path in sorted(staging.iterdir())},
            },
        )
        evidence = validate(model, executable, staging)
        if evidence["status"] == "PASS":
            write_json(staging / "cad-validation.json", evidence)
            staging.rename(output)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freecad", default=os.environ.get("HULLGUARD_FREECAD", "FreeCADCmd"))
    commands = parser.add_subparsers(dest="operation", required=True)
    for operation in ("export", "validate"):
        command = commands.add_parser(operation)
        command.add_argument("model", type=Path)
        command.add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        executable = resolve_command(args.freecad)
        model = load_model(args.model)
        function = export if args.operation == "export" else validate
        evidence = function(model, executable, args.directory)
    except (ModelError, ValueError, OSError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"status": "ERROR", "message": str(error)}))
        return 2
    print(json.dumps(evidence, indent=2, allow_nan=False))
    return 0 if evidence["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
