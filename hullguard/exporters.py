"""Generate machine-readable exports and a schematic XY plan."""

import csv
import io
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path

from .calculations import assembly_mass_kg, mass_kg, volume_m3
from .geometry import write_obj
from .models import DENSITY, Model
from .reporting import write_json, write_text

BOM_FIELDS = (
    "revision",
    "component_id",
    "kind",
    "material",
    "density_kg_m3",
    "size_x_mm",
    "size_y_mm",
    "size_z_mm",
    "thickness_mm",
    "volume_m3",
    "mass_kg",
)
ARTIFACTS = ("model.obj", "manifest.json", "bom.csv", "drawing.svg")
SVG = "http://www.w3.org/2000/svg"
COLORS = {"bottom": "#a6bac9", "side": "#537890", "bulkhead": "#659baa", "stiffener": "#ce8a53"}


def manifest_data(model: Model) -> dict:
    return {
        "schema": 1,
        "project": model.project,
        "revision": model.revision,
        "units": model.canonical()["units"],
        "assembly_mass_kg": assembly_mass_kg(model),
        "components": [
            {
                **asdict(part),
                "density_kg_m3": DENSITY[part.material],
                "thickness_mm": part.thickness_mm,
                "volume_m3": volume_m3(part),
                "mass_kg": mass_kg(part),
            }
            for part in model.components
        ],
    }


def bom_text(model: Model) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(BOM_FIELDS)
    for p in model.components:
        writer.writerow(
            (
                model.revision,
                p.id,
                p.kind,
                p.material,
                DENSITY[p.material],
                *p.size_mm,
                p.thickness_mm,
                f"{volume_m3(p):.16g}",
                f"{mass_kg(p):.16g}",
            )
        )
    return buffer.getvalue()


def drawing_text(model: Model) -> str:
    svg = ET.Element(
        "svg",
        {
            "xmlns": SVG,
            "viewBox": f"0 0 900 {372 + 23 * len(model.components)}",
            "role": "img",
            "aria-labelledby": "drawing-title",
        },
    )
    ET.SubElement(svg, "title", id="drawing-title").text = f"{model.project} · XY plan"
    ET.SubElement(svg, "metadata", {"revision": model.revision, "units": "mm", "projection": "XY"})
    ET.SubElement(svg, "rect", width="100%", height="100%", fill="#f4f8fa")
    ET.SubElement(
        svg,
        "text",
        x="32",
        y="35",
        fill="#163044",
        **{"font-size": "20", "font-family": "sans-serif"},
    ).text = "Structure plan · X/Y · mm"
    ET.SubElement(
        svg,
        "text",
        x="32",
        y="56",
        fill="#40576a",
        **{"font-size": "13", "font-family": "monospace"},
    ).text = f"Source {model.revision[:16]} · schematic"
    bottom = next(part for part in model.components if part.kind == "bottom")
    # Keep the inner viewBox in source millimetres. The group maps increasing Y upward.
    x, y, _ = bottom.origin_mm
    sx, sy, _ = bottom.size_mm
    view = ET.SubElement(
        svg,
        "svg",
        x="32",
        y="70",
        width="836",
        height="219",
        viewBox=f"{x} {y} {sx} {sy}",
        **{"data-view": "plan"},
    )
    projection = ET.SubElement(view, "g", transform=f"translate(0 {2 * y + sy}) scale(1 -1)")
    for p in sorted(model.components, key=lambda part: (part.kind != "bottom", part.id)):
        px, py, _ = p.origin_mm
        dx, dy, _ = p.size_mm
        ET.SubElement(
            projection,
            "rect",
            x=str(px),
            y=str(py),
            width=str(dx),
            height=str(dy),
            fill=COLORS[p.kind],
            stroke="#203648",
            **{
                "vector-effect": "non-scaling-stroke",
                "data-component": p.id,
            },
        )
    schedule = ET.SubElement(
        svg,
        "g",
        fill="#163044",
        **{"font-family": "monospace", "font-size": "15", "data-view": "schedule"},
    )
    ET.SubElement(
        schedule, "text", x="32", y="319"
    ).text = "Component schedule · XYZ dimensions and thickness"
    for index, p in enumerate(model.components):
        text = ET.SubElement(
            schedule,
            "text",
            x="32",
            y=str(347 + 23 * index),
            **{
                "data-component": p.id,
                "data-size-mm": " ".join(map(str, p.size_mm)),
                "data-thickness-mm": str(p.thickness_mm),
            },
        )
        dimensions = " × ".join(f"{value:.10g}" for value in p.size_mm)
        text.text = f"{p.id}    {dimensions} mm    t={p.thickness_mm:.10g} mm"
    return ET.tostring(svg, encoding="unicode") + "\n"


def export_artifacts(model: Model, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    manifest = manifest_data(model)
    write_json(output / "manifest.json", manifest)
    write_text(output / "model.obj", write_obj(model))
    write_text(output / "bom.csv", bom_text(model))
    write_text(output / "drawing.svg", drawing_text(model))
    return manifest
