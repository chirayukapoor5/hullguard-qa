# Test execution report

## Local verification · 23 November 2026

The Windows run passed from a clean checkout after a fresh Python environment and `npm ci`. It passed formatting, lint, fixture regeneration, the Vite build, both Python test groups, and Chromium acceptance. The evidence snapshot records the verified implementation commit, environment, commands, counts, and stage statuses.

| Check | Observed outcome |
| --- | --- |
| Python ordinary regression tests | 89 passed |
| Python controlled fault tests | 6 passed. Each injected defect produced the required diagnostic. |
| Python totals | 95 passed, 0 failures, 0 skips |
| Python coverage | 99.08% lines, 96.15% branches, 98.44% combined |
| Browser acceptance | 6 passed in Playwright Chromium, including actual OBJ interaction, responsive layout and WebGL fallback |
| Healthy fixture bundles | 3 passed |
| Deliberate fault cases | 6 expected detections. These validator results correctly report FAIL. |

Executed with Python 3.12.10, pytest 9.0.3, pytest-cov 7.1.0, coverage.py 7.17.5, Ruff 0.15.21, Node 26.13.0, npm 11.20.0, Vite 8.3.8, and Playwright 1.65.1. Chromium was the Playwright-provisioned 159.0.8154.6 build with software WebGL for the scripted browser suite.

[Verification summary](../reports/local/verification-summary.json) · [Python JUnit](../reports/local/test-results.xml) · [Cobertura coverage](../reports/local/coverage.xml) · [Browser JUnit](../reports/local/browser-results.xml)

## GitHub Actions and Pages

The first public workflow completed the Ubuntu, Windows, and Pages deployment jobs successfully. The downloaded verification artifacts confirmed 95 Python tests and 98.44% combined coverage on both runners. Ubuntu passed six Chromium tests. Windows CI used the explicit recorded browser skip, and the Windows clean checkout above ran all six separately.

The hosted project path served the static index, JavaScript, validation catalog, eight-object OBJ and the revised engineering report with HTTP 200.

[First publication run](https://github.com/chirayukapoor5/hullguard-qa/actions/runs/45191782400) · [Live demo](https://chirayukapoor5.github.io/hullguard-qa/)

## Interactive and manual scope

The in-app browser review exercised the component selector, camera controls, plate revision comparison, drawing fault selector, and generated HTML report as an agent-operated exploratory session. The baseline loaded eight mesh objects, S-03 displayed matching properties, and the drawing evidence showed DRAWING_THICKNESS. The revised report linked its artifacts and displayed +31.4 kg. The separate scripted suite captured the desktop, mobile, and fault views.

Human manual execution is **0 of 24 cases executed**. Each case is marked **NOT EXECUTED** in the [manual cases](MANUAL_TEST_CASES.md). The agent-operated review and scripted browser checks provide distinct evidence.

[Structure explorer](../reports/local/structure-explorer.png) · [Narrow viewport](../reports/local/structure-mobile.png) · [Fault evidence screen](../reports/local/fault-injection.png)

## Reproduction

```sh
python scripts/verify.py
python -m pytest -m fault
python -m hullguard demo
```

The runner combines both pytest JUnit files into `reports/test-results.xml`, writes `reports/coverage.xml` and `reports/verification-summary.json`, and preserves stage logs. The repository snapshot removes the local workstation hostname from JUnit. The execution results and model evidence are preserved.

The [controlled defect records](DEFECT_REPORTS.md) give the exact input and required detector. During development, the fault acceptance assertions were corrected to compare the persisted JSON with the CLI JSON. The browser controls were also given explicit labels for consistent semantic targeting. A full verification run followed both corrections.

## Remaining validation limits

Browser evidence is scoped to Chromium. Real CAD exchange, naval structural correctness beyond the documented box model, structural analysis, and human exploratory acceptance remain outside the observed results. GitHub Actions keeps separate Linux and Windows execution artifacts.

[GitHub Actions](https://github.com/chirayukapoor5/hullguard-qa/actions) · [Engineering design review](ENGINEERING_DESIGN_REVIEW.md)
