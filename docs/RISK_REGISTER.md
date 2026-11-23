# Risk register

Severity describes the consequence if a defect escapes. Likelihood is a project estimate based on how easily an edit or export might introduce the condition. Detectability describes how hard the issue is to spot before using the automated checks. Each is 1–3. Severity 3 affects engineering data, 2 impairs a workflow, and 1 affects presentation only. Likelihood 3 is easy to trigger in normal edits, 2 requires a less common input or sequence, and 1 requires an unusual failure. Detectability 3 is subtle during normal review, 2 is visible with targeted inspection, and 1 is immediately apparent. Priority is S × L × D, with high ≥ 18, medium 8–17, and low ≤ 7. Rankings apply to this synthetic workflow.

| ID | Failure mode | S | L | D | Priority | Control and residual exposure |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| R01 | Wrong mm³ conversion | 3 | 3 | 3 | 27 | Explicit units and independent exact arithmetic. More unit systems would require new oracles. |
| R02 | Invalid thickness or dimensions | 3 | 2 | 2 | 12 | Finite bounds and precision rules. Grade-specific engineering limits are outside scope. |
| R03 | Missing structural element | 3 | 2 | 3 | 18 | ID inventory checks and source comparison. An optional member omitted in every representation needs a baseline or requirement to detect. |
| R04 | Duplicate component ID | 3 | 2 | 2 | 12 | Reject duplicate source and artifact identities. Semantic equivalence between different IDs is outside scope. |
| R05 | Misplaced or overlapping part | 3 | 2 | 3 | 18 | Bottom contact, footprint and intersection checks. Rotations and cut-outs are outside scope. |
| R06 | Stale derivative after change | 3 | 3 | 3 | 27 | Source hash plus content checks. Requires access to the canonical input. |
| R07 | Inconsistent grade/density | 3 | 2 | 3 | 18 | Fixed example material table and artifact density checks. Additional material specifications are outside scope. |
| R08 | Corrupt or incomplete input | 2 | 2 | 1 | 4 | Parse errors and stable exits. A failed disk write can leave partial output, which later checks flag if used. |
| R09 | Incorrect per-part or total mass | 3 | 2 | 3 | 18 | Independent decimal and fractional oracles. Model omissions propagate to the calculated assembly. |
| R10 | Export/import disagreement | 3 | 2 | 3 | 18 | Parse actual OBJ, CSV, SVG, JSON. Other exporters and arbitrary CAD dialects remain outside scope. |
| R11 | Browser cannot render a mesh | 2 | 2 | 1 | 4 | WebGL fallback retains the inventory and mesh link. Actual device coverage remains narrower than CI browser coverage. |

[Requirements traceability](REQUIREMENTS_TRACEABILITY.md)
