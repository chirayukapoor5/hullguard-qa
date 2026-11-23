# 90-second demo

Open the running demo at Structure explorer with the baseline selected.

| Time | Action | Talk track |
| --- | --- | --- |
| 0–15 s | Introduce the baseline screen. | “One structural edit affects geometry, mass, and drawings. HULLGUARD QA tests whether those exports describe the same revision.” |
| 15–35 s | Rotate the mesh, then select P-01. | “This is the generated OBJ of an eight-part steel bay. The baseline assembly is 218.905 kg. The 2,000 by 1,000 by 6 mm bottom plate is 94.2 kg.” |
| 35–55 s | Open Revision comparison and select Plate thickness. | “The edited plate is 8 mm and 125.6 kg. Our independent calculation expects an increase of 31.4 kg. The revised mesh highlights the plate and the fresh exports pass.” |
| 55–75 s | Open Fault injection and choose Stale BOM. Point to the P-01 mass finding. | “This is a recorded run on a synthetic fault. The old BOM carries the previous source hash and 94.2 kg. The validator expects 125.6 kg and reports both discrepancies. The command reproduces the finding.” |
| 75–90 s | Show QA dashboard, then Engineering report and its evidence links. | “The positive revisions pass and all six controlled faults trigger their expected findings. Here are the generated files and the report for independent review.” |

If the panel asks for live reproduction, run `python -m hullguard demo`, then the command shown in the fault view. Exit 1 is expected for an artifact inconsistency.
