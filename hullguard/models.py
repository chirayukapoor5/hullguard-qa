"""Canonical model, schema validation and fixture placement rules."""

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from itertools import combinations
from math import isfinite
from pathlib import Path
from typing import NewType, cast

ComponentId = NewType("ComponentId", str)
Vector = tuple[float, float, float]
THICKNESS_AXIS = {"bottom": 2, "side": 1, "bulkhead": 0, "stiffener": 1}
DENSITY = {"steel-example": 7850}
ID_PATTERN = re.compile(r"[A-Z][A-Z0-9_-]{0,23}")


class ModelError(ValueError):
    """An invalid model, with a stable code for reports and tests."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Component:
    id: ComponentId
    kind: str
    material: str
    origin_mm: Vector
    size_mm: Vector

    @property
    def thickness_mm(self) -> float:
        return self.size_mm[THICKNESS_AXIS[self.kind]]

    @property
    def maximum_mm(self) -> Vector:
        return cast(
            Vector,
            tuple(
                round(start + size, 3)
                for start, size in zip(self.origin_mm, self.size_mm, strict=True)
            ),
        )


@dataclass(frozen=True)
class Model:
    project: str
    components: tuple[Component, ...]

    def canonical(self) -> dict:
        return {
            "schema": 1,
            "project": self.project,
            "units": {"length": "mm", "mass": "kg", "density": "kg/m3"},
            "materials": DENSITY.copy(),
            "components": [asdict(part) for part in self.components],
        }

    @property
    def revision(self) -> str:
        content = json.dumps(self.canonical(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(content.encode("utf-8")).hexdigest()


UNITS = {"length": "mm", "mass": "kg", "density": "kg/m3"}


def vector(value: object, field: str, *, dimension: bool = False) -> Vector:
    if not isinstance(value, list | tuple) or len(value) != 3:
        raise ModelError("INPUT_SCHEMA", f"{field} must contain three numbers")
    result = []
    for axis, raw in zip("XYZ", value, strict=True):
        label = f"{field}.{axis}"
        if type(raw) not in (float, int) or abs(raw) > 1_000_000 or not isfinite(raw):
            raise ModelError("INPUT_NUMBER", f"{label} must be finite and within ±1,000,000 mm")
        if dimension and raw < 0.001:
            raise ModelError("INPUT_DIMENSION", f"{label} must be at least 0.001 mm")
        if round(raw, 3) != raw:
            raise ModelError("INPUT_PRECISION", f"{label} must use 0.001 mm precision or coarser")
        result.append(float(raw) if raw else 0.0)
    return cast(Vector, tuple(result))


def parse_component(raw: object) -> Component:
    fields = {"id", "kind", "material", "origin_mm", "size_mm"}
    if not isinstance(raw, dict) or raw.keys() != fields:
        raise ModelError(
            "INPUT_SCHEMA", "Each component requires exactly " + ", ".join(sorted(fields))
        )
    ident, kind, material = raw["id"], raw["kind"], raw["material"]
    if not isinstance(ident, str) or not ID_PATTERN.fullmatch(ident):
        raise ModelError(
            "INPUT_ID",
            "Component IDs use 1–24 uppercase letters, digits, _ or - and start with a letter",
        )
    if not isinstance(kind, str) or kind not in THICKNESS_AXIS:
        raise ModelError("INPUT_KIND", f"{ident}: unsupported component kind {kind!r}")
    if not isinstance(material, str) or material not in DENSITY:
        raise ModelError("INPUT_MATERIAL", f"{ident}: unsupported material {material!r}")
    size = vector(raw["size_mm"], f"{ident}.size_mm", dimension=True)
    origin = vector(raw["origin_mm"], f"{ident}.origin_mm")
    return Component(ComponentId(ident), kind, material, origin, size)


def check_placement(components: tuple[Component, ...]) -> None:
    bottoms = [part for part in components if part.kind == "bottom"]
    if len(bottoms) != 1:
        raise ModelError("INPUT_PLACEMENT", "The assembly requires exactly one bottom plate")
    bottom = bottoms[0]
    if bottom.maximum_mm[2] != 0:
        raise ModelError(
            "INPUT_PLACEMENT", f"{bottom.id}: bottom plate upper face must be at Z = 0 mm"
        )
    for part in components:
        if part is bottom:
            continue
        low, high = part.origin_mm, part.maximum_mm
        if low[2] != 0 or any(
            low[i] < bottom.origin_mm[i] or high[i] > bottom.maximum_mm[i] for i in range(2)
        ):
            raise ModelError(
                "INPUT_PLACEMENT",
                f"{part.id}: must sit on the bottom plate within its XY footprint",
            )
        if (
            part.kind == "side"
            and low[1] != bottom.origin_mm[1]
            and high[1] != bottom.maximum_mm[1]
        ):
            raise ModelError(
                "INPUT_PLACEMENT", f"{part.id}: side plate must touch a transverse edge"
            )
        if part.kind == "stiffener" and part.size_mm[0] <= max(part.size_mm[1:]):
            raise ModelError(
                "INPUT_PLACEMENT", f"{part.id}: longitudinal stiffener must be longest along X"
            )
    for a, b in combinations(components, 2):
        if all(
            max(a.origin_mm[i], b.origin_mm[i]) < min(a.maximum_mm[i], b.maximum_mm[i])
            for i in range(3)
        ):
            raise ModelError(
                "INPUT_OVERLAP", f"{a.id} and {b.id} intersect with positive material volume"
            )


def parse_model(raw: object) -> Model:
    if not isinstance(raw, dict) or raw.keys() != {
        "schema",
        "project",
        "units",
        "materials",
        "components",
    }:
        raise ModelError(
            "INPUT_SCHEMA", "Expected schema, project, units, materials and components"
        )
    if type(raw["schema"]) is not int or raw["schema"] != 1:
        raise ModelError("INPUT_SCHEMA", "Only model schema 1 is supported")
    if raw["units"] != UNITS:
        raise ModelError("INPUT_UNITS", "Declare units as length=mm, mass=kg and density=kg/m3")
    if raw["materials"] != DENSITY:
        raise ModelError("INPUT_MATERIAL", "Declare the example steel with density 7850 kg/m3")
    project = raw["project"]
    if (
        not isinstance(project, str)
        or not project.strip()
        or len(project) > 100
        or not project.isprintable()
    ):
        raise ModelError("INPUT_SCHEMA", "Project must be printable text of 1–100 characters")
    rows = raw["components"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= 200:
        raise ModelError("INPUT_SCHEMA", "Provide 1–200 components")
    components = tuple(sorted(map(parse_component, rows), key=lambda part: part.id))
    if len({part.id for part in components}) != len(components):
        counts = {}
        for part in components:
            counts[part.id] = counts.get(part.id, 0) + 1
        duplicates = ", ".join(ident for ident, count in counts.items() if count > 1)
        raise ModelError("INPUT_DUPLICATE_ID", f"Duplicate component IDs: {duplicates}")
    check_placement(components)
    return Model(project.strip(), components)


def unique_fields(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError(f"Duplicate JSON field: {name}")
        result[name] = value
    return result


def load_model(path: Path) -> Model:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=unique_fields)
    except (OSError, ValueError, RecursionError) as error:
        raise ModelError("INPUT_READ", f"Cannot read {path}: {error}") from error
    return parse_model(data)
