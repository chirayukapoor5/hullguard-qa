# Independent principal QA review · 23 November 2026

**Recommendation.** Ready for a software testing interview as a bounded demonstrator. The strongest evidence is a reproducible disagreement between canonical design intent and a genuine CAD export. The original and revised validators were challenged with the same inputs. The review does not qualify the tool for production engineering decisions.

| Finding | Observed on original commit `a78f410` | Correction and evidence |
| --- | --- | --- |
| Physical-value tolerance hid scale mistakes | A 0.001 mm cube's BOM passed with zero mass and volume, and also with both values inflated 1,000×. | Require positive observations and cap the absolute tolerance at one part per million of a positive reference. Both adversarial cases now fail with component and assembly findings. |
| Revision and dimensions were insufficient for drawing placement | P-01 drawing geometry or its label could be translated with an extra SVG transform and retain PASS. | Reject transforms outside the generated projection group. Both visible-structure challenge tests now detect the change. |
| Comparisons accepted manifest schema lookalikes | A Boolean true or numeric 1.0 passed as the integer schema version. | Check the exact version type and value. Both variants now raise MANIFEST_SCHEMA. |
| Interrupted publication retained a claim for the old bundle | Injecting a BOM write failure during regeneration left prior validation.json at PASS while revalidation of the directory failed. | Stage and validate before replacing managed files, invalidate earlier attestations before replacing artifacts, serialize writers with a directory lock, and publish validation last. The failure test also confirms that a retry recovers. |

The physical oracle and exporter share the input model and density, so an incorrect modeling assumption can propagate consistently. The regression suite reduces arithmetic coupling with exact hand-derived reference cases, independent decimal reconciliation, and a signed mesh-volume check. The browser editor uses integer micrometres, and its 8 mm download matches the Python-validated fixture. An additional nonfixture edit exercises executable calculation. FreeCAD measures the geometry from two re-read formats, while a separate reference predicts the box volume, bounds and mass. A deliberately restamped STEP file tests the distinction between provenance and physical correctness.

## Residual risks

- Consistent omissions need an expected inventory or comparison revision. Validation of a self-consistent source cannot establish that a vessel requires an omitted component.
- A staged write protects the recorded verdict from an interrupted replacement. Independent readers can still observe a partial directory before the final validation file appears. A killed publisher can leave the lock marker, which should be removed only after confirming the publisher has stopped. Allocate separate output folders for independent runs.
- STEP filenames establish identities for this exchange convention. Broader interoperability needs assembly identity, topology, unit and material mapping tests with a second CAD system and domain-reviewed fixtures.
- The validated SVG subset checks its data, geometry and expected transform hierarchy. Rendering equivalence under arbitrary SVG/CSS and production drafting are outside scope.
- Core and browser results are reproducible. Formal human execution, a second browser engine, and native CAD testing on Linux remain open.

[Regression evidence](TEST_EXECUTION_REPORT.md) · [Manual execution audit](MANUAL_EXECUTION_REPORT.md) · [FreeCAD round trip](CAD_INTEROP.md)
