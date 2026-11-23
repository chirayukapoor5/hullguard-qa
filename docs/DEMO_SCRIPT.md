# 90-second demo

Open the demo at Structure explorer. Keep the [FreeCAD test evidence](CAD_INTEROP.md) open in a separate tab.

| Time | Action | Talk track |
| --- | --- | --- |
| 0–15 s | Introduce the baseline. | “One structural edit can change geometry, weight, and drawings. HULLGUARD QA checks whether the delivered files describe the same change.” |
| 15–35 s | Rotate the actual OBJ and inspect P-01. | “This synthetic bay has eight solids. The 6 mm bottom plate weighs 94.2 kg using the example density.” |
| 35–55 s | Open Plate editor, enter 8, then Calculate. If there is time, enter 6.125. | “This runs in the browser. At 8 mm the mass grows to 125.6 kg, or +31.4 kg. The revised JSON is downloadable. A 6.125 mm edit gives a different calculated result.” |
| 55–75 s | Open the recorded Stale BOM case and point to P-01. | “The revision hash and content both fail. The BOM still says 94.2 kg. In the CAD regression, the reopened STEP showed the same mismatch after the native box was edited.” |
| 75–90 s | Show the evidence links and manual audit. | “Read the original observed output, the exact reproduction, and the separate human test checklist. The scripted audit has screenshots and console evidence.” |

For a technical follow-up, use the [FreeCAD CLI reproduction](CAD_INTEROP.md) and open the [principal review](PRINCIPAL_REVIEW.md) to discuss which assumptions control the result.
