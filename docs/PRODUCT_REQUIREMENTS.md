# Product requirements

A consistency tester needs to verify that a design change makes it from a structural model to the files people use downstream. HULLGUARD gives a software tester controlled data and clear diagnostics, a structural design engineer visible geometry and mass deltas, a QA lead versioned evidence and repeatable gates, and a technical reviewer independently checkable results.

| ID | User outcome | Acceptance measure |
| --- | --- | --- |
| US-01 | A software tester can load and inspect a valid ship-structure fixture. | Baseline exports eight named meshes. Browser picking and the accessible selector show each part's dimensions, material and mass. |
| US-02 | A structural design engineer can edit plate thickness and see the expected mass change. | P-01 goes from 6 to 8 mm and 94.2 to 125.6 kg. Reported assembly delta is 31.4 kg within 1 µkg. |
| US-03 | A tester can identify a stale or numerically incorrect BOM. | Candidate BOM with old source hash yields STALE_REVISION and stale thickness and mass findings. A current-hash conversion fault yields VOLUME/MASS. |
| US-04 | A tester can identify inconsistent drawing dimensions. | Old SVG yields stale revision and thickness findings. Edits to visible text, metadata or projected geometry are independently flagged. |
| US-05 | A tester can identify missing or misplaced components. | The missing S-04 OBJ yields COMPONENT_INVENTORY. Off-bottom and overlapping source parts receive specific placement errors. |
| US-06 | A QA lead can compare model revisions and generate a change-impact report. | JSON shows added, removed and modified identities, dimensions and position deltas, mass, affected artifacts, and validation outcomes for generated and optional candidate bundles. |
| US-07 | A technical reviewer can reproduce a failing case. | Repository commands produce evidence and stable exits 0 for pass, 1 for findings and 2 for invalid input or usage. Controlled CLI runs reproduce all six findings. |
| US-08 | A tester can inspect automated results and perform documented exploratory tests. | Browser exposes scenario status, expected and actual results, reproduction and evidence. The repository provides at least 20 manual cases with an execution status. |

Release checks require passing ordinary regression and controlled-negative assertions, at least 85% combined line/branch Python coverage, a Vite build and a browser acceptance run on a supported target. The deployment surfaces precomputed synthetic artifacts. Native CAD interop and production engineering analysis are outside the release scope.

[Traceability matrix](REQUIREMENTS_TRACEABILITY.md)
