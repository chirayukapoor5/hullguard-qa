# Technical interview preparation

## 1. What problem does this project test?

“When an engineer changes one part, other representations can still show an older value. I model that as an input–export consistency problem. I check the source revision and then check the engineering content because a current revision label is insufficient evidence on its own.”

## 2. How did you choose the first tests?

“I prioritized conversion errors and stale files. They can look plausible without targeted review. Then I covered component identity and placement, data rejection, independent numerical references, and the end-to-end browser workflow. The risk register ties each choice to a user story and test.”

## 3. How did you independently verify the plate result?

“The area is two square metres. At 6 mm the volume is 0.012 cubic metres, and at 8 mm it is 0.016. With the example density, the masses are 94.2 and 125.6 kg. The validator uses decimal arithmetic in cubic millimetres. A separate test also verifies the full assembly using an exact fraction.”

## 4. Why does a separate test oracle matter?

“Checks that call the same helper twice can agree on a wrong unit conversion. I used hand-calculated values and a different reconciliation path. For the mesh, I reconstructed volume from triangle determinants to check geometry independently of the exporter’s mass calculation.”

## 5. How do you avoid counting overlap twice?

“Each part is an axis-aligned box, and positive overlap on all axes is rejected. Face contact is permitted, so the stiffeners can meet the bulkhead without adding shared volume. I test exact contact and overlap by 0.001 mm.”

## 6. What do you test manually?

“Use the exploratory charters to probe behavior between scripted steps. I would change revisions quickly, use the app without a pointer, and hand a report to another tester to see if they can reproduce a discrepancy. I would record source revision, observations, expected behavior and evidence. This portfolio includes scripted browser acceptance and a written human test suite.”

## 7. What should a defect report contain?

“Name the affected artifact and component, include expected versus observed, and use a minimal reproduction with version and environment. The stale BOM example records the digest mismatch and the numerical consequence rather than leaving the reviewer to infer the bad value.”

## 8. What did you simplify?

“I chose rectangular solids, disjoint volumes and one representative density. The SVG is a schematic projection and schedule. Those decisions make the expected results tractable, while curved plating, welded joints, production drafting and strength calculations require additional models and verified references.”

## 9. How does CI handle deliberate failures?

“I run the ordinary regression and controlled negative groups separately. A scenario must return the expected failure code and exact required finding for its test to pass. CI fails if the expected finding is absent or a required verification step fails.”

## 10. What would a genuine integration with NAPA require?

“I would start with company authorization and supported APIs or export formats, licensed access, and approved test datasets. A domain reviewer would help define identity, units, geometric tolerances and acceptance oracles. The team would need a versioned regression corpus and a supported way to reproduce each integration run. The portfolio uses public context and synthetic data.”
