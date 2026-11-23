# Documentation QA checklist

Use the checklist when changing the supported model, a command, an evidence format, or the published demo.

| Review | Verification |
| --- | --- |
| Install instructions | Follow the quick start on a clean checkout. Confirm both the Python environment and npm lockfile install. Review the workflow for the other supported OS. |
| Command accuracy | Check each README CLI example against its expected status and generated filename. Run the documented stale BOM example and retain its negative exit code. |
| Engineering values | Verify all worked examples against the rational assembly test and the generated comparison JSON. Confirm unit labels and sign conventions. |
| Local and external links | Check local Markdown targets relative to their document. Verify official references, the source repo, and the actual Pages destination. |
| Screenshots and claims | Match screenshots to the running app and the tested run. Check that coverage covers the stated scope and that displayed results are labeled precomputed. |
| Terminology and audience | Confirm why each detector matters, define BOM and the axes, and explain the example density. Keep instructions usable when read out of order. |
| Troubleshooting | Document browser install, a disabled WebGL fallback, prerequisites, stale revision recovery and negative exit handling. |
| Manual evidence | Count the cases, verify IDs against the traceability matrix, and confirm any completed case has direct execution evidence. |
| Publication | Confirm the published SHA and deployment status. Verify the nested Pages paths for JS, OBJ and HTML links. |

## Troubleshooting checks

- If Python cannot find the development tools, activate the same virtual environment used for `pip install -e ".[dev]"` and rerun verification.
- If the demo cannot load scenario data, run the Python demo generator from the repository root before rebuilding and serving the application.
- If the browser acceptance stage is BLOCKED, install Chromium in the frontend folder and retry. If WebGL is unavailable in a user's browser, the app retains its component inventory and direct OBJ link.
- If a bundle reports STALE_REVISION, compare its source hash with `python -m hullguard check <model>` and regenerate the bundle from the intended source. Check the other findings before assuming regeneration is the whole fix.
- If a report link is missing, keep all files in a single output directory and regenerate the bundle. The report uses relative evidence links.

[Verification record](TEST_EXECUTION_REPORT.md)
