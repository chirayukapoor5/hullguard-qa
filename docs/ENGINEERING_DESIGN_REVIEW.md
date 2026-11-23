# Engineering design review

## Source of truth and identity

The canonical JSON stores the project, units, example material table, component IDs, kinds, origins and sizes. The parser normalizes ordering and numeric spelling before computing SHA-256. Exports carry the source revision. Artifact reads always use the supplied source model as their reference. The digest supports revision traceability. It is a content identifier without claims of signing or authenticity.

A stable ID defines a part across revisions. A rename therefore appears as one addition and one removal. Optional structures can be absent from a valid source. A regression comparison or a known-good source is necessary to detect a consistent omission across all representations.

## Units, geometry and test oracles

Lengths and coordinates are millimetres at 0.001 mm precision. The exporter converts each axis to metres before multiplying dimensions and density. The validator multiplies decimal millimetres first and applies an explicit cubic conversion. The tests add hand-derived plate and assembly references and a signed tetrahedron sum over mesh faces. Together these test the unit convention, arithmetic, geometry volume and hand-checkable outputs without using the export calculation as its own oracle.

Axis-aligned boxes permit transparent placement checks with exact rounded bounds and strictly positive overlap on all three axes. Named OBJ meshes let the validator check inventory, vertex bounds and closed outward triangulation. The parser supports a documented generated subset. The plan checks engineering fields, projected rectangles and visible labels. Generic SVG presentation such as arbitrary styling and occlusion needs manual review.

## Failure handling and reproducibility

Canonical input errors use specific code/field diagnostics and exit 2. Bundle findings use exit 1 and include artifact, component, expected and observed values. A wrong hash and incorrect content can be reported together. A failed candidate does not prevent regenerating a fresh revised bundle. Reports capture both outcomes, and validator findings remain useful when another artifact is missing or malformed.

Exports produce a set of files in an output directory. Use a distinct directory for each reviewer or run when concurrent writes are possible. If a process is interrupted halfway through, rerun the export and verify the full bundle before distribution. The machine checks cover the four engineering representations. The generated reports describe those checks and link to their evidence.

## Alternatives and CI boundaries

Python can generate and read this bounded mesh without a full geometry library. Three.js consumes the exported geometry in the browser. A native CAD engine would provide curved topology, rotations and richer geometry, alongside a larger test matrix and dependencies. FreeCAD is a possible future adapter after headless tests on supported platforms and a review of import/export semantics.

A static evidence site provides predictable reviewer access without sending data to a service. The pinned workflow runs Python and the frontend build on Windows and Linux, plus Chromium on Linux. Windows browser results can be reproduced locally. Unit/branch coverage records exercised behavior. Independent test oracles, documented manual charters and format-specific fault tests address risks that coverage alone cannot quantify.

[Domain assumptions](DOMAIN_ASSUMPTIONS.md) · [Test strategy](TEST_STRATEGY.md) · [Verification results](TEST_EXECUTION_REPORT.md)
