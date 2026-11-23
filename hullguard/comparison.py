"""Compare revisions by stable component ID and report downstream impact."""

from pathlib import Path
from tempfile import TemporaryDirectory

from .calculations import assembly_mass_kg, mass_kg
from .exporters import ARTIFACTS, export_artifacts
from .models import Component, Model, ModelError
from .reporting import engineering_html, write_json, write_text
from .validation import validate_bundle


def component_state(part: Component) -> dict:
    return {
        "id": part.id,
        "kind": part.kind,
        "material": part.material,
        "size_mm": part.size_mm,
        "origin_mm": part.origin_mm,
        "thickness_mm": part.thickness_mm,
        "mass_kg": mass_kg(part),
    }


def compare_models(before: Model, after: Model) -> dict:
    if before.project != after.project:
        raise ModelError("INPUT_PROJECT", "Compare revisions of the same project")
    old = {p.id: p for p in before.components}
    new = {p.id: p for p in after.components}
    added = [component_state(new[name]) for name in sorted(new.keys() - old.keys())]
    removed = [component_state(old[name]) for name in sorted(old.keys() - new.keys())]
    modified = [
        {
            "id": name,
            "before": component_state(old[name]),
            "after": component_state(new[name]),
            "delta_dimensions_mm": [
                round(b - a, 3) for a, b in zip(old[name].size_mm, new[name].size_mm, strict=True)
            ],
            "delta_position_mm": [
                round(b - a, 3)
                for a, b in zip(old[name].origin_mm, new[name].origin_mm, strict=True)
            ],
            "delta_mass_kg": mass_kg(new[name]) - mass_kg(old[name]),
        }
        for name in sorted(old.keys() & new.keys())
        if old[name] != new[name]
    ]
    previous, current = assembly_mass_kg(before), assembly_mass_kg(after)
    return {
        "project": after.project,
        "baseline_revision": before.revision,
        "revised_revision": after.revision,
        "before_mass_kg": previous,
        "after_mass_kg": current,
        "delta_mass_kg": current - previous,
        "added": added,
        "removed": removed,
        "modified": modified,
        "affected_artifacts": (*ARTIFACTS, "validation.json", "report.html")
        if before.revision != after.revision
        else (),
    }


def create_bundle(model: Model, output: Path, comparison: dict | None = None) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    lock = output / ".hullguard-write"
    try:
        lock.mkdir()
    except FileExistsError as error:
        raise OSError(f"Export directory is locked: {output}") from error
    try:
        with TemporaryDirectory(dir=output, prefix=".staging-") as temporary:
            staging = Path(temporary)
            manifest = export_artifacts(model, staging)
            validation = validate_bundle(model, staging)
            result = validation.as_dict()
            reports = ["report.html", "validation.json"]
            if comparison is not None:
                comparison["validation"] = result
                write_json(staging / "comparison.json", comparison)
                reports.insert(0, "comparison.json")
            write_text(staging / "report.html", engineering_html(manifest, validation, comparison))
            write_json(staging / "validation.json", result)

            # Invalidate prior attestations before replacing artifacts. Publish validation last.
            managed_reports = ("validation.json", "report.html", "comparison.json")
            for name in (*ARTIFACTS, *managed_reports):
                if (output / name).is_dir():
                    raise IsADirectoryError(f"Expected a file at {output / name}")
            for name in managed_reports:
                (output / name).unlink(missing_ok=True)
            for name in (*ARTIFACTS, *reports):
                (staging / name).replace(output / name)
    finally:
        lock.rmdir()
    return result
