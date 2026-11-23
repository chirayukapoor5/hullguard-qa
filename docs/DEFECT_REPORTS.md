# Controlled defect reports

These are deliberately introduced defects in synthetic files. The Python CLI reproduced the specified result for each case. Start with `python -m hullguard demo` from the repository root. For exports use `python -m hullguard validate <scenario>/model.json <scenario>` and substitute the path in the evidence column. For invalid inputs use `python -m hullguard check <scenario>/model.json`. The generated evidence folder is `frontend/public/data/faults/`.

| ID | Synthetic change and severity | Expected behavior on healthy data | Observed with fault | Evidence folder |
| --- | --- | --- | --- | --- |
| D01 | Baseline BOM retained after P-01 thickness edit. S3. | All rows carry the changed hash and P-01 shows 125.6 kg. | Exit 1. STALE_REVISION and MASS among findings. P-01 125.6 kg expected, 94.2 kg actual. | `stale_bom` |
| D02 | Baseline plan retained after the plate edit. S3. | Current source hash and P-01 thickness 8 mm. | Exit 1. STALE_REVISION, DRAWING_THICKNESS and annotation/dimension mismatches. Actual t = 6 mm. | `stale_drawing` |
| D03 | S-04 removed from OBJ only. S3. | Export contains eight IDs including S-04. | Exit 1. COMPONENT_INVENTORY shows S-04 omitted. | `missing_stiffener` |
| D04 | B-01 mass and volume multiplied by 1,000. S3. | Mass and volume agree with example density, dimensions and units. | Exit 1. VOLUME, MASS and ASSEMBLY_MASS despite a current revision. | `wrong_units` |
| D05 | P-01 source thickness set to zero. S3. | Positive thickness with valid precision. | Exit 2. INPUT_DIMENSION identifies P-01.size_mm.Z. | `invalid_thickness` |
| D06 | S-04 renamed to an existing S-03. S3. | Stable and unique IDs. | Exit 2. INPUT_DUPLICATE_ID names S-03. | `duplicate_id` |

Each folder contains the faulty artifact, the source and exact `validation.json`. For export faults, regenerating with the current source resolves the discrepancy. For source faults, correct the component field or identifier and run `check` before export.
