# Manual test cases

Environment definitions and evidence handling are in the [manual plan](MANUAL_TEST_PLAN.md). Automated browser and CLI results are recorded separately. Each case below is ready for a human run.

## M01 · README quick start

- Requirement US-07. Priority P0. Environment Shell.
- Precondition. Fresh checkout, Python and Node on PATH.
- Test data. README quick start
- Status. NOT EXECUTED.
- Evidence to capture. reports/verification-summary.json

1. Create and activate the virtual environment.
2. Install the Python extras and run npm ci in frontend.
3. Run python scripts/verify.py from the repo root after installing Chromium.

Expected outcome. Every required stage reports PASS. The three named report files open and contain this run’s counts.

## M02 · fixtures/baseline.json

- Requirement US-01. Priority P0. Environment Shell.
- Precondition. Python package installed. Use a scratch folder.
- Test data. fixtures/baseline.json
- Status. NOT EXECUTED.
- Evidence to capture. scratch/baseline/manifest.json

1. Copy the baseline to a scratch model file.
2. Change the project field to a unique printable name.
3. Run check and export on that source, then inspect manifest.json.

Expected outcome. The custom project name and eight components appear. The source and manifest revisions agree.

## M03 · Reorder the component list

- Requirement US-01. Priority P1. Environment Shell.
- Precondition. A valid scratch model is open in a UTF-8 editor.
- Test data. Reorder the component list
- Status. NOT EXECUTED.
- Evidence to capture. Two captured CLI check outputs

1. Run check and save the hash.
2. Reorder the component array and save the file.
3. Close and reopen the editor, then run check again.

Expected outcome. The canonical hash is identical and the saved component order does not affect totals.

## M04 · P-01, 6 mm → 8 mm

- Requirement US-02. Priority P0. Environment Shell.
- Precondition. A baseline scratch copy is available.
- Test data. P-01, 6 mm → 8 mm
- Status. NOT EXECUTED.
- Evidence to capture. comparison.json in scratch comparison

1. Change the last size coordinate from 6 to 8 and the last origin coordinate from −6 to −8.
2. Save and reload the file.
3. Run compare against baseline and read the modified row.

Expected outcome. P-01 is the sole change. Its mass goes from 94.2 to 125.6 kg and assembly delta is +31.4 kg.

## M05 · Thickness 0 mm

- Requirement US-02. Priority P0. Environment Shell.
- Precondition. Copy the baseline to a scratch file.
- Test data. Thickness 0 mm
- Status. NOT EXECUTED.
- Evidence to capture. Captured CLI output

1. Set P-01 size Z to 0.
2. Save and run check.
3. Read the CLI exit and component field path.

Expected outcome. Exit 2 and INPUT_DIMENSION identify P-01.size_mm.Z.

## M06 · 0.001 and 0.0009 mm

- Requirement US-02. Priority P1. Environment Shell.
- Precondition. Copy the baseline to a scratch file.
- Test data. 0.001 and 0.0009 mm
- Status. NOT EXECUTED.
- Evidence to capture. Two captured CLI check outputs

1. Set P-01 size Z to 0.001 and origin Z to −0.001. Check.
2. Repeat with 0.0009 and −0.0009.

Expected outcome. The first passes. The second fails with INPUT_DIMENSION.

## M07 · Truncated JSON

- Requirement US-07. Priority P1. Environment Shell.
- Precondition. Copy the baseline to a scratch file.
- Test data. Truncated JSON
- Status. NOT EXECUTED.
- Evidence to capture. Two captured CLI check outputs

1. Delete the closing brace and save.
2. Run check.
3. Restore the brace and rerun.

Expected outcome. The first run exits 2 with INPUT_READ, then it passes after restoration.

## M08 · S-01 origin Z = 0.001

- Requirement US-05. Priority P0. Environment Shell.
- Precondition. Copy the baseline to a scratch file.
- Test data. S-01 origin Z = 0.001
- Status. NOT EXECUTED.
- Evidence to capture. Two captured CLI check outputs

1. Move S-01 vertically by 0.001 mm.
2. Run check and inspect the error.
3. Restore Z = 0 and rerun.

Expected outcome. The misplaced part is identified by INPUT_PLACEMENT. Face contact passes.

## M09 · S-01 X dimension 1100.001 mm

- Requirement US-05. Priority P0. Environment Shell.
- Precondition. Copy the baseline to a scratch file.
- Test data. S-01 X dimension 1100.001 mm
- Status. NOT EXECUTED.
- Evidence to capture. Two captured CLI check outputs

1. Extend S-01 toward the bulkhead by 0.001 mm.
2. Run check.
3. Restore length to 1100 mm and run check again.

Expected outcome. The first run reports INPUT_OVERLAP naming S-01 and B-01. Exact contact passes.

## M10 · faults/stale_bom

- Requirement US-03. Priority P0. Environment Shell.
- Precondition. Generate fresh demo evidence.
- Test data. faults/stale_bom
- Status. NOT EXECUTED.
- Evidence to capture. frontend/public/data/faults/stale_bom/validation.json

1. Run the documented stale BOM command.
2. Read the expected and actual revision, then find the P-01 MASS result.
3. Compare both masses to the plate calculation.

Expected outcome. Exit 1 with stale BOM revision and 125.6 kg expected versus 94.2 kg actual for P-01.

## M11 · faults/stale_drawing

- Requirement US-04. Priority P0. Environment Shell + Browser.
- Precondition. Generate fresh demo evidence.
- Test data. faults/stale_drawing
- Status. NOT EXECUTED.
- Evidence to capture. frontend/public/data/faults/stale_drawing/validation.json

1. Open the faulty SVG and read the P-01 schedule.
2. Run the corresponding validation command.
3. Find the visible annotation and thickness findings.

Expected outcome. The plan shows 6 mm. The validator expects 8 mm and reports DRAWING_THICKNESS and DRAWING_ANNOTATION.

## M12 · faults/missing_stiffener

- Requirement US-05. Priority P0. Environment Shell.
- Precondition. Generate fresh demo evidence.
- Test data. faults/missing_stiffener
- Status. NOT EXECUTED.
- Evidence to capture. frontend/public/data/faults/missing_stiffener/validation.json

1. Open the source and confirm S-04 exists.
2. Run validation against the incomplete OBJ.
3. Read the inventory finding.

Expected outcome. The expected inventory includes S-04 and the actual inventory omits it. Only model.obj is flagged.

## M13 · faults/wrong_units

- Requirement US-03. Priority P0. Environment Shell.
- Precondition. Generate fresh demo evidence.
- Test data. faults/wrong_units
- Status. NOT EXECUTED.
- Evidence to capture. frontend/public/data/faults/wrong_units/validation.json

1. Open the faulty BOM and inspect the first row.
2. Run validation and inspect its revision and mass fields.
3. Check total mass reconciliation.

Expected outcome. The revision matches. B-01 shows a 1,000× error, and VOLUME, MASS and ASSEMBLY_MASS are raised.

## M14 · faults/duplicate_id

- Requirement US-05. Priority P0. Environment Shell.
- Precondition. Generate fresh demo evidence.
- Test data. faults/duplicate_id
- Status. NOT EXECUTED.
- Evidence to capture. frontend/public/data/faults/duplicate_id/validation.json

1. Run check against the duplicate model.
2. Read the diagnostic.
3. Confirm the report identifies S-03 as duplicated.

Expected outcome. Exit 2 with INPUT_DUPLICATE_ID and the component identifier.

## M15 · Baseline OBJ

- Requirement US-01. Priority P1. Environment Browser.
- Precondition. Built app open with WebGL enabled.
- Test data. Baseline OBJ
- Status. NOT EXECUTED.
- Evidence to capture. Desktop capture and session notes

1. Rotate by dragging across the model.
2. Zoom in twice and then use Reset view.
3. Repeat with keyboard arrows and +/−.

Expected outcome. The camera responds and resets. Eight objects remain available and the page stays usable.

## M16 · S-03, B-01, P-01

- Requirement US-01. Priority P0. Environment Browser.
- Precondition. Structure explorer open at baseline.
- Test data. S-03, B-01, P-01
- Status. NOT EXECUTED.
- Evidence to capture. Desktop capture and session notes

1. Select S-03 from the inspector.
2. Select B-01 from the table.
3. Pick a visible component directly on the mesh.

Expected outcome. Inspector, row selection and highlight follow the same part. S-03 displays 892 × 8 × 68 mm.

## M17 · Stiffener layout revision

- Requirement US-06. Priority P0. Environment Browser.
- Precondition. Revision comparison open.
- Test data. Stiffener layout revision
- Status. NOT EXECUTED.
- Evidence to capture. frontend/public/data/revisions/stiffener_changed/comparison.json

1. Choose Stiffener layout.
2. Inspect rows S-01, S-04 and S-05.
3. Open the position and dimension JSON.

Expected outcome. S-01 modification, S-04 removal and S-05 addition appear. S-01 moves +30 mm in Y and grows +2 mm in Y.

## M18 · QA dashboard

- Requirement US-08. Priority P1. Environment Browser.
- Precondition. Demo generated and served.
- Test data. QA dashboard
- Status. NOT EXECUTED.
- Evidence to capture. QA dashboard and fault screenshot

1. Open QA dashboard.
2. Review healthy rows and the six expected-negative rows.
3. Follow the Stale BOM reproduction link.

Expected outcome. 3/3 healthy, 6/6 expected detections and Precomputed are visible. The linked fault opens with code and commands.

## M19 · Wrong volume conversion and Duplicate ID

- Requirement US-08. Priority P1. Environment Browser.
- Precondition. Fault injection view open.
- Test data. Wrong volume conversion and Duplicate ID
- Status. NOT EXECUTED.
- Evidence to capture. Fault evidence files

1. Switch between the two synthetic scenarios.
2. Read the expected detector and observed finding rows.
3. Open faulty artifact and validation links for each.

Expected outcome. Wrong conversion shows MASS and exit-1 workflow. Duplicate ID shows INPUT_DUPLICATE_ID and the check workflow. Both show the precomputed label.

## M20 · Plate thickness report

- Requirement US-06. Priority P1. Environment Browser.
- Precondition. Engineering report view open.
- Test data. Plate thickness report
- Status. NOT EXECUTED.
- Evidence to capture. HTML report and linked files

1. Select Plate thickness.
2. Open the HTML report and follow the comparison JSON link.
3. Open technical plan and BOM from the report.

Expected outcome. The report shows the revised hash and +31.4 kg impact. The local file links resolve and the plan shows t=8 mm.

## M21 · Structure explorer and report

- Requirement US-08. Priority P1. Environment Browser.
- Precondition. Use a 390 px-wide browser viewport.
- Test data. Structure explorer and report
- Status. NOT EXECUTED.
- Evidence to capture. 390 px screenshot and session notes

1. Verify the header and metrics at 390 px.
2. Scroll the nav to Engineering report, then use the report table.
3. Use Tab to inspect focus behavior.

Expected outcome. The page stays within the viewport. Nav and data table can scroll independently and focus is visible.

## M22 · Baseline inventory without WebGL

- Requirement US-01. Priority P1. Environment Browser.
- Precondition. Use a WebGL-disabled Chromium profile or software configuration.
- Test data. Baseline inventory without WebGL
- Status. NOT EXECUTED.
- Evidence to capture. Capture of fallback state

1. Open the structure.
2. Read the fallback message and try the component selector.
3. Open the OBJ and manifest-linked properties.

Expected outcome. The preview fallback appears, camera controls are disabled, component details and OBJ remain accessible.

## M23 · Only visible P-01 SVG annotation changed

- Requirement US-04. Priority P1. Environment Shell + Browser.
- Precondition. Export a fresh scratch model.
- Test data. Only visible P-01 SVG annotation changed
- Status. NOT EXECUTED.
- Evidence to capture. Edited SVG and CLI validation output

1. In drawing.svg edit the visible thickness annotation only.
2. Open the SVG and confirm it visually changed.
3. Run validate with the unmodified source.

Expected outcome. DRAWING_ANNOTATION appears even though the SVG revision and thickness metadata still match.

## M24 · Thickness revision with baseline candidate bundle

- Requirement US-06. Priority P0. Environment Shell.
- Precondition. Export the baseline to scratch/old.
- Test data. Thickness revision with baseline candidate bundle
- Status. NOT EXECUTED.
- Evidence to capture. Two comparison JSON reports

1. Run compare with a new output folder and --against scratch/old.
2. Inspect comparison.json and exit code.
3. Run again with the fresh revised bundle as candidate.

Expected outcome. The first reports new exports PASS, old candidate FAIL, and exit 1. The second reports both PASS and exit 0.
