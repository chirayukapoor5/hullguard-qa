"""Compare revisions by stable component ID and report downstream impact."""

from pathlib import Path

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
    manifest = export_artifacts(model, output)
    validation = validate_bundle(model, output)
    result = validation.as_dict()
    write_json(output / "validation.json", result)
    comparison_path = output / "comparison.json"
    if comparison is not None:
        comparison["validation"] = result
        write_json(comparison_path, comparison)
    else:
        comparison_path.unlink(missing_ok=True)
    write_text(output / "report.html", engineering_html(manifest, validation, comparison))
    return result
