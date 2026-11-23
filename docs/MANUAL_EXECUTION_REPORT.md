# Manual case audit · 23 November 2026

All 24 existing cases were inspected and reproduced with scripted shell or browser actions where applicable. **Human manual execution remains 0/24.** The original [case records](MANUAL_TEST_CASES.md) retain their NOT EXECUTED statuses. The scripted run recorded 16 shell results and 10 browser results. M11 and M23 required both.

## Environment and provenance

The run used Windows x64, PowerShell, Python 3.12.10, Node 26.13.0 and Playwright 1.65.1 with Chromium 159.0.8154.6 and SwiftShader. Desktop captures used 1440 × 980. M21 used 390 × 844 and M22 disabled WebGL through browser automation. M01 used a fresh checkout, dependency installation and the complete verifier. M03 saved and re-read the JSON with a script. The editor close/reopen step as performed by a person remains part of the human case.

The verification summary identifies the clean source commit. The shell evidence records CLI commands, expected and actual exits, and observed JSON. The browser evidence records case IDs, runner verdicts, browser builds, viewport sizes, durations, and capture names. Screenshots show the actual browser state after each check.

[Clean verification](../reports/review/verification-summary.json) · [Shell evidence by case](../reports/review/manual-shell.json) · [Browser evidence by case](../reports/review/manual-browser.json)

| Case | Scripted outcome | Observation and evidence |
| --- | --- | --- |
| M01 | PASS · shell | Fresh install and verifier passed. JUnit and coverage reports were present. |
| M02 | PASS · shell | Custom project exported with eight parts and matching source/manifest hashes. |
| M03 | PASS · shell | Reordered file was saved and re-read. Revision and mass stayed the same. |
| M04 | PASS · shell | Editing P-01 from 6 to 8 mm changed its mass from 94.2 to 125.6 kg. Assembly delta +31.4 kg. |
| M05 | PASS · shell | Zero thickness returned exit 2 and INPUT_DIMENSION for P-01.size_mm.Z. |
| M06 | PASS · shell | 0.001 mm passed. 0.0009 mm returned INPUT_DIMENSION. |
| M07 | PASS · shell | Truncated JSON returned INPUT_READ. Restoring the brace passed. |
| M08 | PASS · shell | Lifted S-01 triggered INPUT_PLACEMENT. Restored contact passed. |
| M09 | PASS · shell | 0.001 mm penetration triggered INPUT_OVERLAP for B-01 and S-01. Exact contact passed. |
| M10 | PASS · shell | Stale BOM showed a hash mismatch and 94.2 kg observed versus 125.6 kg expected. |
| M11 | PASS · shell + browser | The stale plan rendered 6 mm. The CLI reported thickness and annotation mismatches. [Capture](../reports/review/M11.png) |
| M12 | PASS · shell | Source retained S-04. Only the OBJ inventory reported it missing. |
| M13 | PASS · shell | A current-hash B-01 row inflated by 1,000× triggered VOLUME, MASS and ASSEMBLY_MASS. |
| M14 | PASS · shell | Duplicate S-03 returned INPUT_DUPLICATE_ID and exit 2. |
| M15 | PASS · browser | Drag, two zoom steps, reset, keyboard orbit, plus/minus and Home were exercised. Reset returned within the rendered-pixel comparison threshold and eight meshes remained. [Capture](../reports/review/M15.png) |
| M16 | PASS · browser | Inspector, table selection and canvas picking agreed. S-03 showed 892 × 8 × 68 mm. [Capture](../reports/review/M16.png) |
| M17 | PASS · browser | S-01 moved +30 mm and grew +2 mm in Y. S-04 removal and S-05 addition appeared. [Capture](../reports/review/M17.png) |
| M18 | PASS · browser | 3/3 healthy and 6/6 expected fault detections were marked precomputed. The reproduction control opened Stale BOM. [Capture](../reports/review/M18.png) |
| M19 | PASS · browser | Wrong conversion and duplicate IDs showed the expected detectors, CLI commands and readable faulty files and validation JSON. [Capture](../reports/review/M19.png) |
| M20 | PASS · browser | Revised source hash and +31.4 kg appeared. The linked comparison, BOM and 8 mm plan were served. [Capture](../reports/review/M20.png) |
| M21 | PASS · browser | The 390 px page stayed within the viewport, nav and table scrolled independently, and Tab showed focus. [Capture](../reports/review/M21.png) |
| M22 | PASS · browser | With WebGL disabled, the inspector and eight-object OBJ remained usable. Camera controls were disabled. [Capture](../reports/review/M22.png) |
| M23 | PASS · shell + browser | The edited note rendered t=8 mm with metadata 6.0. Only DRAWING_ANNOTATION fired. [Capture](../reports/review/M23.png) |
| M24 | PASS · shell | Fresh output passed both times. The baseline candidate returned FAIL/1 and the revised candidate PASS/0. |

## Defects and retests

The original validator missed zero or 1,000×-inflated physical values on a minimum-size test solid, two invalid manifest schema types, and transforms hiding changes to SVG geometry or annotations. All six new challenge assertions failed on the old implementation. An interrupted BOM write also left an earlier PASS beside mixed-revision files. The revised core fixes these issues and retains regression tests. [Adversarial review](PRINCIPAL_REVIEW.md)

The initial audit runner stopped on a Unicode arrow in redirected Windows output, leaving the M23 drawing unavailable. The M15 initial test also compared the encoded screenshots byte-for-byte. The final audit replaced that comparison with observed per-pixel color differences and reran all cases after correcting the output issue. Human verification of visual quality still belongs in M15 and M21.

## Reproduce

From an installed clean checkout, run the following after completing the README's dependency setup.

```sh
python scripts/verify.py
python scripts/audit_manual_shell.py
cd frontend
npx playwright test --config playwright.audit.config.js
```

The shell and audit-browser outputs go under `build/manual-audit/`. Run the shell stage first. It creates the intentionally modified SVG for M23. The Playwright audit has its own configuration and does not contribute to the ordinary browser regression count.
