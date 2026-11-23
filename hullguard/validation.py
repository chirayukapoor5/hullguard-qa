"""Reconcile exported evidence against canonical inputs and independent arithmetic."""

import csv
import io
import json
from collections.abc import Callable
from decimal import Decimal
from math import fsum, isclose, isfinite
from pathlib import Path
from xml.etree.ElementTree import ParseError

from defusedxml.common import DefusedXmlException
from defusedxml.ElementTree import fromstring

from .exporters import ARTIFACTS, BOM_FIELDS, SVG
from .geometry import read_obj
from .models import DENSITY, UNITS, Component, Model, unique_fields
from .reporting import Finding, Validation

DIMENSION_TOLERANCE = 1e-6
MASS_TOLERANCE = 1e-6
VOLUME_TOLERANCE = 1e-12
MAX_ARTIFACT_BYTES = 4_000_000


def reference_values(part: Component) -> tuple[float, float]:
    x, y, z = (Decimal(str(value)) for value in part.size_mm)
    cubic_mm = x * y * z
    volume = cubic_mm * Decimal("1e-9")
    mass = cubic_mm * Decimal(DENSITY[part.material]) / Decimal(1_000_000_000)
    return float(volume), float(mass)


def close(
    actual: object,
    expected: float,
    tolerance: float = DIMENSION_TOLERANCE,
    *,
    relative: float = 1e-12,
) -> bool:
    try:
        number = float(actual)
    except (TypeError, ValueError, OverflowError):
        return False
    return type(actual) is not bool and isclose(
        number, expected, abs_tol=tolerance, rel_tol=relative
    )


def close_vector(actual: object, expected: tuple[float, ...]) -> bool:
    return (
        isinstance(actual, list | tuple)
        and len(actual) == len(expected)
        and all(
            close(value, target, relative=0) for value, target in zip(actual, expected, strict=True)
        )
    )


class ArtifactCheck:
    def __init__(self, model: Model, filename: str, findings: list[Finding]) -> None:
        self.model = model
        self.filename = filename
        self.findings = findings
        self.parts = {part.id: part for part in model.components}

    def expect(
        self, passed: bool, code: str, expected: object, actual: object, component: str = ""
    ) -> None:
        if not passed:
            self.findings.append(Finding(code, self.filename, component, expected, actual))

    def equal(self, code: str, expected: object, actual: object, component: str = "") -> None:
        self.expect(expected == actual, code, expected, actual, component)

    def scalar(
        self,
        code: str,
        expected: float,
        actual: object,
        component: str = "",
        tolerance: float = DIMENSION_TOLERANCE,
        *,
        positive: bool = False,
    ) -> None:
        if positive:
            tolerance = min(tolerance, expected * 1e-6)
        matches = close(actual, expected, tolerance)
        self.expect(
            matches and (not positive or float(actual) > 0), code, expected, actual, component
        )

    def vector(
        self, code: str, expected: tuple[float, ...], actual: object, component: str
    ) -> None:
        self.expect(close_vector(actual, expected), code, expected, actual, component)

    def revision(self, actual: object, component: str = "") -> None:
        self.equal("STALE_REVISION", self.model.revision, actual, component)

    def inventory(self, rows: list[tuple[str, object]]) -> dict:
        values = {}
        for name, row in rows:
            self.expect(name not in values, "DUPLICATE_COMPONENT", "unique ID", name, name)
            values[name] = row
        self.equal("COMPONENT_INVENTORY", sorted(self.parts), sorted(values))
        return values

    def mass_fields(self, p: Component, row: dict) -> None:
        volume, mass = reference_values(p)
        self.equal("KIND", p.kind, row.get("kind"), p.id)
        self.equal("MATERIAL", p.material, row.get("material"), p.id)
        self.scalar("DENSITY", DENSITY[p.material], row.get("density_kg_m3"), p.id)
        self.scalar("THICKNESS", p.thickness_mm, row.get("thickness_mm"), p.id)
        self.scalar("VOLUME", volume, row.get("volume_m3"), p.id, VOLUME_TOLERANCE, positive=True)
        self.scalar("MASS", mass, row.get("mass_kg"), p.id, MASS_TOLERANCE, positive=True)

    @property
    def expected_total(self) -> float:
        return fsum(reference_values(part)[1] for part in self.parts.values())


def check_obj(check: ArtifactCheck, content: str) -> None:
    headers, meshes = read_obj(content)
    check.revision(headers.get("revision"))
    check.equal("UNITS", "mm", headers.get("units"))
    check.inventory(list(meshes.items()))
    for name, part in check.parts.items():
        if name not in meshes:
            continue
        mesh = meshes[name]
        closed = mesh.is_closed_outward_box()
        check.expect(
            closed,
            "MESH_TOPOLOGY",
            "closed, outward triangular box",
            {"vertices": len(mesh.vertices), "faces": len(mesh.faces)},
            name,
        )
        if mesh.vertices:
            low, high = mesh.bounds
            check.vector("POSITION", part.origin_mm, low, name)
            dimensions = tuple(end - start for start, end in zip(low, high, strict=True))
            check.vector("DIMENSIONS", part.size_mm, dimensions, name)


def reject_constant(value: str) -> None:
    raise ValueError(f"Non-finite JSON number {value}")


def finite_decimal(value: str) -> float:
    result = float(value)
    if not isfinite(result):
        raise ValueError(f"Non-finite JSON number {value}")
    return result


def check_manifest(check: ArtifactCheck, content: str) -> None:
    data = json.loads(
        content,
        object_pairs_hook=unique_fields,
        parse_constant=reject_constant,
        parse_float=finite_decimal,
    )
    if not isinstance(data, dict) or not isinstance(data.get("components"), list):
        raise ValueError("manifest requires an object and component array")
    schema = data.get("schema")
    check.expect(type(schema) is int and schema == 1, "MANIFEST_SCHEMA", 1, schema)
    check.equal("PROJECT", check.model.project, data.get("project"))
    check.revision(data.get("revision"))
    check.equal("UNITS", UNITS, data.get("units"))
    check.scalar(
        "ASSEMBLY_MASS",
        check.expected_total,
        data.get("assembly_mass_kg"),
        tolerance=MASS_TOLERANCE,
        positive=True,
    )
    rows = []
    for row in data["components"]:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            raise ValueError("manifest component requires a string ID")
        rows.append((row["id"], row))
    inventory = check.inventory(rows)
    for name, part in check.parts.items():
        if name in inventory:
            row = inventory[name]
            check.vector("POSITION", part.origin_mm, row.get("origin_mm"), name)
            check.vector("DIMENSIONS", part.size_mm, row.get("size_mm"), name)
            check.mass_fields(part, row)


def check_bom(check: ArtifactCheck, content: str) -> None:
    reader = csv.DictReader(io.StringIO(content, newline=""), strict=True)
    if tuple(reader.fieldnames or ()) != BOM_FIELDS:
        raise ValueError("BOM header does not match the schema")
    rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError("BOM row has the wrong number of columns")
    inventory = check.inventory([(row["component_id"], row) for row in rows])
    for row in rows:
        check.revision(row["revision"], row["component_id"])
    for name, part in check.parts.items():
        if name in inventory:
            row = inventory[name]
            check.vector(
                "DIMENSIONS", part.size_mm, [row[f"size_{axis}_mm"] for axis in "xyz"], name
            )
            check.mass_fields(part, row)
    try:
        total = fsum(finite_decimal(row["mass_kg"]) for row in rows)
    except (ValueError, OverflowError):
        total = "invalid numeric row or total"
    check.scalar(
        "ASSEMBLY_MASS", check.expected_total, total, tolerance=MASS_TOLERANCE, positive=True
    )


def check_drawing(check: ArtifactCheck, content: str) -> None:
    root = fromstring(content)
    ns = {"s": SVG}
    if root.tag != f"{{{SVG}}}svg":
        raise ValueError("expected an SVG root element")
    metadata = root.findall("s:metadata", ns)
    views = root.findall("s:svg[@data-view='plan']", ns)
    schedules = root.findall("s:g[@data-view='schedule']", ns)
    if not (len(metadata) == len(views) == len(schedules) == 1):
        raise ValueError("SVG requires one metadata element, plan and component schedule")
    check.revision(metadata[0].get("revision"))
    check.equal("UNITS", "mm", metadata[0].get("units"))
    check.equal("PROJECTION", "XY", metadata[0].get("projection"))
    view = views[0]
    for element, name in ((root, "root"), (view, "plan"), (schedules[0], "schedule")):
        check.equal("DRAWING_EXTRA_TRANSFORM", None, element.get("transform"), name)
    bottom = next(part for part in check.parts.values() if part.kind == "bottom")
    x, y, _ = bottom.origin_mm
    sx, sy, _ = bottom.size_mm
    check.vector("DRAWING_VIEW", (x, y, sx, sy), view.get("viewBox", "").split(), "")
    groups = view.findall("s:g", ns)
    if len(groups) != 1:
        raise ValueError("SVG plan requires one projection group")
    group = groups[0]
    transform = f"translate(0 {2 * y + sy}) scale(1 -1)"
    check.equal("DRAWING_TRANSFORM", transform, group.get("transform"))
    plan = check.inventory(
        [(el.get("data-component"), el) for el in group.findall("s:rect[@data-component]", ns)]
    )
    annotations = check.inventory(
        [
            (el.get("data-component"), el)
            for el in schedules[0].findall("s:text[@data-component]", ns)
        ]
    )
    for name, part in check.parts.items():
        if name in plan:
            rect = plan[name]
            check.equal("DRAWING_EXTRA_TRANSFORM", None, rect.get("transform"), name)
            check.vector(
                "DRAWING_POSITION", part.origin_mm[:2], [rect.get("x"), rect.get("y")], name
            )
            check.vector(
                "DRAWING_SIZE", part.size_mm[:2], [rect.get("width"), rect.get("height")], name
            )
        if name in annotations:
            label = annotations[name]
            check.equal("DRAWING_EXTRA_TRANSFORM", None, label.get("transform"), name)
            check.vector(
                "DRAWING_DIMENSIONS", part.size_mm, label.get("data-size-mm", "").split(), name
            )
            check.scalar(
                "DRAWING_THICKNESS", part.thickness_mm, label.get("data-thickness-mm"), name
            )
            x, y, z = part.size_mm
            visible = f"{name} {x:.10g} × {y:.10g} × {z:.10g} mm t={part.thickness_mm:.10g} mm"
            check.equal(
                "DRAWING_ANNOTATION", visible, " ".join("".join(label.itertext()).split()), name
            )


CHECKS: dict[str, Callable[[ArtifactCheck, str], None]] = dict(
    zip(ARTIFACTS, (check_obj, check_manifest, check_bom, check_drawing), strict=True)
)


def validate_bundle(model: Model, directory: Path) -> Validation:
    findings: list[Finding] = []
    for filename, validator in CHECKS.items():
        check = ArtifactCheck(model, filename, findings)
        try:
            with (directory / filename).open("rb") as stream:
                raw = stream.read(MAX_ARTIFACT_BYTES + 1)
            if len(raw) > MAX_ARTIFACT_BYTES:
                raise ValueError("artifact exceeds the 4 MB input limit")
            validator(check, raw.decode("utf-8"))
        except FileNotFoundError:
            check.equal("ARTIFACT_MISSING", "export file", None)
        except (
            ValueError,
            OSError,
            ParseError,
            DefusedXmlException,
            csv.Error,
            RecursionError,
        ) as error:
            check.equal("ARTIFACT_INVALID", "readable supported artifact", str(error))
    return Validation(model.revision, tuple(findings), ARTIFACTS)
