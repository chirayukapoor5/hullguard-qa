# Case study · HULLGUARD QA

A ship structure can be represented by a 3D model, a bill of materials, engineering drawings and downstream data. A thickness edit changes the represented material volume. Review becomes harder when an export carries the previous value or an apparently current file has the wrong dimensions, units or component set. HULLGUARD QA makes those classes of inconsistency observable in a small, reproducible example.

## Approach

The model is an eight-component rectangular bay with bottom and side plating, a transverse bulkhead and split longitudinal flat bars. One typed model produces four engineering artifacts with a common source revision. A separate validator reads those artifacts back, checking identity, geometry, mass and annotation consistency. The revision tool pairs components by ID, reports changes and can reconcile an exported candidate against the revised source. The Three.js demo uses the actual OBJ and precomputed QA records. A live browser editor recalculates the baseline bottom plate and saves revised canonical JSON. The optional FreeCAD adapter builds editable native boxes and independently reopens their STEP solids for exact-fixture comparisons.

## QA design

Stale exports and mm-to-m conversion errors score highest in the project risk model because both can survive a quick visual review. Identity and placement are also high-impact. The suite tests boundary values, malformed data, round trips and deterministic output. It checks numerical results against hand calculations, a separate decimal conversion and volume reconstructed from mesh triangles. The manual plan gives a tester charters for state drift, accessibility and evidence hand-off.

| Scenario | Verified observation |
| --- | --- |
| Baseline | Eight components, 218.9052256 kg. All four exports reconcile. |
| P-01 plate revision | 6 → 8 mm, 94.2 → 125.6 kg for P-01, +31.4 kg assembly delta. All fresh exports reconcile. |
| Stiffener layout revision | S-01 moves +30 mm in Y and grows 2 mm in Y. S-04 is removed and S-05 is added. Assembly delta is +1.17436 kg. |
| Controlled negative executions | Six intended detector results reproduced by the CLI with specific file, component, code and exit assertions. |

The scripted audit reproduced 24 manual cases using shell and Chromium checks. It records actual outcomes and retains all human statuses as NOT EXECUTED. The adversarial review reproduced false PASS outcomes on the original commit for near-zero BOM values, SVG transforms and manifest schema lookalikes. It also reproduced a stale PASS report after an interrupted export. On genuine CAD data, a restamped old STEP still failed the dimensional and mass checks. [Manual audit](MANUAL_EXECUTION_REPORT.md) · [Adversarial review](PRINCIPAL_REVIEW.md) · [Execution report](TEST_EXECUTION_REPORT.md)

## Trade-offs and extension path

Disjoint axis-aligned boxes make the geometry independently calculable and make intersection errors reproducible. They constrain the model to simple assemblies. A static frontend makes the evidence inspectable with a browser and keeps the fixture source and CLI reproductions in the repository. The FreeCAD round trip covers editable boxes and positioned single-solid STEP exports. Mass uses the documented example density and measured CAD volume. Structural strength, production drawings and domain-qualified vessel geometry remain outside the demonstrated scope.

The next evidence would come from a human exploratory session and an independently reviewed fixture, followed by an exchange check with another CAD system. [FreeCAD round trip](CAD_INTEROP.md)

[Domain assumptions](DOMAIN_ASSUMPTIONS.md) · [Risk register](RISK_REGISTER.md) · [Design review](ENGINEERING_DESIGN_REVIEW.md)
