# Test strategy

Start with the edits that can change engineering decisions without an obvious crash. Reconcile units, component identity and source revisions before evaluating more cosmetic UI behavior. See the [risk register](RISK_REGISTER.md) for priorities.

| Layer | Design and oracle | Execute |
| --- | --- | --- |
| Model input | Valid and invalid equivalence classes. Exercise schema, key duplication, non-finite values, signed positions and dimension boundaries. | `python -m pytest tests/test_model.py` |
| Engineering calculations | 6 and 8 mm hand-calculated masses and an exact fractional assembly total. Seeded property checks exercise linear scaling across all three dimensions. Closed OBJ volume is checked using signed tetrahedra. | `python -m pytest tests/test_engineering.py` |
| Artifacts | Verify current hashes with mutated content, malformed files, stale evidence and deterministic bytestreams. Re-import geometry and inspect actual face and vertex data. | `python -m pytest tests/test_artifacts.py` |
| CLI and regressions | Export and revalidate on a real subprocess, compare revisions and reconcile an old candidate. | `python -m pytest -m "not fault"` |
| Controlled negatives | Assert the exact failure source, category, component, exit code and recorded JSON for six mutations. The harness passes when the expected detector fires. | `python -m pytest -m fault` |
| Browser acceptance | Serve the Vite build and exercise OBJ rendering, picking, keyboard navigation, reports, small screens, and WebGL fallback in Chromium. | `npm run test:e2e` in `frontend/` after building |
| Exploratory sessions | Seek misleading states, project setup friction and readability issues using the [manual plan](MANUAL_TEST_PLAN.md). | Record observations against [case IDs](MANUAL_TEST_CASES.md). |

A clean checkout plus a pinned npm lockfile supports repeatability. The model hash uses its canonical content and stable component order. Test random inputs use a fixed seed. The browser loads generated evidence during build. The expected numeric values in tests are derived separately from the mass implementation.

A failing release gate stays visible. A missing required prerequisite is BLOCKED and returns a nonzero status. An explicit browser-only skip is available for environments that cannot provision Chromium. The Windows CI job makes that selection and the Linux CI job runs browser acceptance.
