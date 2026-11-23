"""Run inside the FreeCAD console with a generated job file."""

import json
from pathlib import Path

NATIVE = "model.FCStd"


def create_document(app, part_module, model, directory):
    doc = app.newDocument("Hullguard")
    try:
        doc.Label = model["project"]
        for part in model["components"]:
            box = doc.addObject("Part::Box", "HullPart")
            box.Label = part["id"]
            box.addProperty("App::PropertyString", "HullguardId", "HULLGUARD")
            box.HullguardId = part["id"]
            box.setEditorMode("HullguardId", 1)
            box.Length, box.Width, box.Height = part["size_mm"]
            box.Placement.Base = app.Vector(*part["origin_mm"])
        doc.recompute()
        doc.saveAs(str(directory / NATIVE))
        for box in doc.Objects:
            part_module.export([box], str(directory / f"part-{box.HullguardId}.step"))
    finally:
        app.closeDocument(doc.Name)


def shape_values(shape):
    while not shape.isNull() and shape.ShapeType == "Compound":
        children = shape.childShapes()
        if len(children) != 1:
            break
        shape = children[0]
    bounds = shape.BoundBox
    solids = shape.Solids
    center = solids[0].CenterOfMass if len(solids) == 1 else None
    return {
        "valid": not shape.isNull() and shape.isValid(),
        "solid_count": len(solids),
        "topology": shape.ShapeType,
        "origin_mm": [bounds.XMin, bounds.YMin, bounds.ZMin],
        "size_mm": [bounds.XLength, bounds.YLength, bounds.ZLength],
        "volume_mm3": shape.Volume,
        "centroid_mm": [center.x, center.y, center.z] if center is not None else [],
    }


def inspect_document(app, filename):
    doc = app.openDocument(str(filename))
    try:
        # Recompute to catch a changed editable parameter even if a saved shape is older.
        for obj in doc.Objects:
            if hasattr(obj, "Shape"):
                obj.touch()
        doc.recompute()
        return [
            {
                **shape_values(obj.Shape),
                "id": getattr(obj, "HullguardId", ""),
                "label": obj.Label,
                "type": obj.TypeId,
                "parameters_mm": [obj.Length.Value, obj.Width.Value, obj.Height.Value]
                if obj.TypeId == "Part::Box"
                else [],
            }
            for obj in doc.Objects
            if hasattr(obj, "Shape")
        ]
    finally:
        app.closeDocument(doc.Name)


def inspect_exports(app, part_module, directory):
    errors = {}
    native = []
    step = {}
    if (directory / NATIVE).is_file():
        try:
            native = inspect_document(app, directory / NATIVE)
        except Exception as error:  # FreeCAD uses several extension-defined exceptions.
            errors[NATIVE] = str(error)
    for filename in sorted(directory.glob("*.step")):
        try:
            step[filename.name] = shape_values(part_module.read(str(filename)))
        except Exception as error:
            errors[filename.name] = str(error)
    return {"native": native, "step": step, "read_errors": errors}


def execute(job_path):
    job = json.loads(Path(job_path).read_text(encoding="utf-8"))
    try:
        import FreeCAD as app
        import Part

        directory = Path(job["directory"])
        version = ".".join(app.Version()[:3])
        if job["operation"] == "create":
            create_document(app, Part, job["model"], directory)
            result = {"freecad_version": version}
        else:
            result = {**inspect_exports(app, Part, directory), "freecad_version": version}
        output = json.dumps(result, indent=2, allow_nan=False)
    except Exception as error:
        output = json.dumps({"worker_error": f"{type(error).__name__}: {error}"})
    Path(job["result"]).write_text(output, encoding="utf-8")
