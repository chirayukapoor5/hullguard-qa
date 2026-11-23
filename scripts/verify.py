"""Run HULLGUARD verification and write evidence under reports/."""

import argparse
import importlib.metadata
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
REPORTS = ROOT / "reports"
PIP_PACKAGES = ("hullguard-qa", "pytest", "pytest-cov", "coverage", "ruff", "defusedxml")
OUTCOMES = ("PASS", "FAIL", "SKIPPED", "BLOCKED")


def probe(command: list[str], cwd: Path = ROOT) -> str | None:
    try:
        process = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return process.stdout.strip() if process.returncode == 0 else None


def installed_packages() -> dict:
    versions = {}
    for package in PIP_PACKAGES:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return versions


class Verification:
    def __init__(self) -> None:
        self.stages: dict[str, dict] = {}
        self.env = {
            **os.environ,
            "COVERAGE_FILE": str(REPORTS / ".coverage"),
            "PYTHONIOENCODING": "utf-8",
            "PYTEST_ADDOPTS": "",
        }

    def record(self, name: str, status: str, **details) -> None:
        assert status in OUTCOMES
        self.stages[name] = {"status": status, **details}
        suffix = f" · {details['reason']}" if "reason" in details else ""
        print(f"[{status}] {name}{suffix}", flush=True)

    def run(self, name: str, command: list[str], cwd: Path = ROOT) -> bool:
        print(f"Running {name}", flush=True)
        log = REPORTS / f"{name}.log"
        label = [Path(command[0]).name, *command[1:]]
        try:
            with log.open("w", encoding="utf-8") as output:
                process = subprocess.run(
                    command,
                    cwd=cwd,
                    env=self.env,
                    stdout=output,
                    stderr=subprocess.STDOUT,
                    check=False,
                    timeout=300,
                )
        except (OSError, subprocess.TimeoutExpired) as error:
            self.record(name, "FAIL", command=label, reason=str(error), log=log.name)
            return False
        status = "PASS" if process.returncode == 0 else "FAIL"
        self.record(name, status, command=label, exit_code=process.returncode, log=log.name)
        if status == "FAIL":
            print(log.read_text(encoding="utf-8", errors="replace")[-9000:], flush=True)
        return status == "PASS"


def combine_junit(names: list[str], output: Path) -> dict:
    aggregate = ET.Element("testsuites")
    totals = dict.fromkeys(("tests", "errors", "failures", "skipped"), 0)
    for name in names:
        path = REPORTS / name
        if not path.exists():
            continue
        root = ET.parse(path).getroot()
        suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
        for suite in suites:
            aggregate.append(suite)
            for key in totals:
                totals[key] += int(suite.get(key, "0"))
    if len(aggregate):
        ET.ElementTree(aggregate).write(output, encoding="utf-8", xml_declaration=True)
    return totals


def coverage_metrics(path: Path) -> dict | None:
    if not path.exists():
        return None
    root = ET.parse(path).getroot()
    covered = sum(int(root.attrib[f"{kind}-covered"]) for kind in ("lines", "branches"))
    valid = sum(int(root.attrib[f"{kind}-valid"]) for kind in ("lines", "branches"))
    return {
        "line_percent": 100 * float(root.attrib["line-rate"]),
        "branch_percent": 100 * float(root.attrib["branch-rate"]),
        "combined_percent": 100 * covered / valid,
        "tool": root.attrib["version"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-browser",
        action="store_true",
        help="Explicitly omit browser checks when Chromium cannot be provisioned",
    )
    args = parser.parse_args()
    REPORTS.mkdir(exist_ok=True)
    for name in (
        "positive-results.xml",
        "fault-results.xml",
        "test-results.xml",
        "coverage.xml",
        "browser-results.xml",
        ".coverage",
    ):
        (REPORTS / name).unlink(missing_ok=True)
    runner = Verification()
    packages = installed_packages()
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    node = shutil.which("node")
    node_version = probe([node, "--version"]) if node else None
    version = re.fullmatch(r"v(\d+)\.(\d+)\.\d+", node_version or "")
    supported = version and (
        int(version[1]) >= 24 or (int(version[1]) == 22 and int(version[2]) >= 12)
    )
    tools_ready = sys.version_info >= (3, 11) and all(packages.values())
    frontend_ready = bool(
        npm and supported and (FRONTEND / "node_modules/vite/package.json").is_file()
    )
    runner.record(
        "python-prerequisites",
        "PASS" if tools_ready else "BLOCKED",
        **({} if tools_ready else {"reason": "Use Python 3.11+ and install .[dev]"}),
    )
    runner.record(
        "frontend-prerequisites",
        "PASS" if frontend_ready else "BLOCKED",
        **(
            {}
            if frontend_ready
            else {"reason": "Use Node 22.12+ or 24+ and run npm ci in frontend"}
        ),
    )

    generated = False
    if tools_ready:
        python = [sys.executable, "-m"]
        runner.run("lint", [*python, "ruff", "check", "."])
        runner.run("format", [*python, "ruff", "format", "--check", "."])
        pytest = [*python, "pytest", "--cov=hullguard", "--cov-report=term"]
        runner.run(
            "positive-tests",
            [*pytest, "-m", "not fault", "--junitxml=reports/positive-results.xml"],
        )
        runner.run(
            "controlled-fault-tests",
            [
                *pytest,
                "-m",
                "fault",
                "--cov-append",
                "--cov-fail-under=85",
                "--cov-report=xml:reports/coverage.xml",
                "--junitxml=reports/fault-results.xml",
            ],
        )
        generated = runner.run("fixture-regression", [*python, "hullguard", "demo"])
    else:
        for stage in (
            "lint",
            "format",
            "positive-tests",
            "controlled-fault-tests",
            "fixture-regression",
        ):
            runner.record(stage, "BLOCKED", reason="Python prerequisites unavailable")

    built = False
    if frontend_ready and generated:
        built = runner.run("frontend-build", [npm, "run", "build"], FRONTEND)
    else:
        runner.record(
            "frontend-build",
            "BLOCKED",
            reason="Requires frontend dependencies and valid fixture evidence",
        )

    if args.skip_browser:
        runner.record("browser-acceptance", "SKIPPED", reason="Explicit --skip-browser option")
    elif not built:
        runner.record("browser-acceptance", "BLOCKED", reason="Frontend build did not pass")
    elif not probe(
        [
            node,
            "--input-type=module",
            "-e",
            "import {chromium} from 'playwright'; import {existsSync} from 'node:fs';"
            "if (existsSync(chromium.executablePath())) console.log('Chromium installed');",
        ],
        FRONTEND,
    ):
        runner.record(
            "browser-acceptance",
            "BLOCKED",
            reason="Run npx playwright install chromium in frontend",
        )
    else:
        runner.run("browser-acceptance", [npm, "run", "test:e2e"], FRONTEND)

    python_results = combine_junit(
        ["positive-results.xml", "fault-results.xml"], REPORTS / "test-results.xml"
    )
    browser_results = combine_junit(["browser-results.xml"], REPORTS / "browser-summary.xml")
    expected = {"PASS", "SKIPPED"}
    status = (
        "PASS" if all(stage["status"] in expected for stage in runner.stages.values()) else "FAIL"
    )
    git = shutil.which("git")
    revision = probe([git, "rev-parse", "HEAD"]) if git else None
    dirty = probe([git, "status", "--porcelain"]) if revision else None
    summary = {
        "status": status,
        "executed_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "source_commit": revision,
        "source_dirty": bool(dirty) if dirty is not None else None,
        "platform": platform.system() + " " + platform.machine(),
        "tools": {
            "python": platform.python_version(),
            "python_packages": packages,
            "node": node_version,
            "npm": probe([npm, "--version"]) if npm else None,
            "playwright": probe(
                [npm, "exec", "--offline", "--", "playwright", "--version"], FRONTEND
            )
            if frontend_ready
            else None,
        },
        "stages": runner.stages,
        "python_results": python_results,
        "coverage": coverage_metrics(REPORTS / "coverage.xml"),
        "browser_results": browser_results,
    }
    (REPORTS / "verification-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Verification {status}. See reports/verification-summary.json.", flush=True)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
