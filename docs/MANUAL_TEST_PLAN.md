# Manual test plan

## Entry criteria

Start with a clean checkout, an activated Python environment with development dependencies, and current fixture output from `python -m hullguard demo`. For browser cases, build and serve the demo as described in the [README](../README.md). Use copies of sources and exports under an ignored `build/scratch` directory for destructive case steps.

## Environments

- **Shell** means Windows PowerShell or a Linux terminal with the installed Python package. Read the exit value with `$LASTEXITCODE` in PowerShell or `$?` in a POSIX shell.
- **Browser** means desktop Chromium with WebGL, keyboard and mouse unless the case specifies a narrow viewport or WebGL-disabled profile. Record browser build and hardware or software rendering in the environment entry.
- **Shell + Browser** links the artifact and visible interpretation. Use the same revision and output directory in both.
- **Evidence** from a new manual run should include the commit, source hash, commands or screen actions, actual results, environment and supporting files. Keep separately generated automated results in [Test execution report](TEST_EXECUTION_REPORT.md).

## Exploratory charters

1. **Revision drift, 20 min.** Try a fresh revision stamp on stale content, a correct report with an incorrect BOM, and partial candidate exports. Ask which failure is actionable first and whether an incorrect unit can present plausible values.
2. **Placement and identity, 15 min.** Move a stiffener in small increments at the footprint and overlap boundaries. Reorder input rows and inspect which changes affect identity and the revision digest.
3. **Interaction and fallbacks, 20 min.** Investigate keyboard-only navigation, rapid revision changes, narrow screens and unavailable WebGL. Check that the selected part and displayed properties stay synchronized.
4. **Hand-off, 15 min.** Exchange a comparison bundle with another tester. Use the report links and commands to reproduce a discrepancy and record any missing context.

Mark each case PASS or FAIL only after observing its expected outcome. Use BLOCKED with a dependency explanation and NOT EXECUTED when no run took place. For a failure, capture actual versus expected, reproducibility, scope and severity, then retry after any fix. A test automated by Playwright does not count as a human manual execution.

[Manual cases](MANUAL_TEST_CASES.md) · [Scripted execution report](MANUAL_EXECUTION_REPORT.md) · [Example defect reports](DEFECT_REPORTS.md)
