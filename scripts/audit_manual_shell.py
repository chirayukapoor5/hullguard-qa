"""Scripted reproduction of the shell steps in manual cases M01–M24."""

import argparse
import json
import platform
import subprocess
import sys
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

from hullguard.reporting import write_json

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "fixtures/baseline.json"
CHANGED = "fixtures/thickness_changed.json"
BASE = json.loads((ROOT / BASELINE).read_text(encoding="utf-8"))


class Session:
    def __init__(self, case: str, output: Path):
        self.directory = output / case
        self.directory.mkdir(parents=True, exist_ok=True)
        self.observations = []

    def cli(self, *args, exit_code=0):
        command = [str(arg) for arg in args]
        result = subprocess.run(
            [sys.executable, "-m", "hullguard", *command],
            cwd=ROOT,
            capture_output=True,
            encoding="utf-8",
            check=False,
        )
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            data = result.stdout
        self.observations.append(
            {
                "command": ["python", "-m", "hullguard", *command],
                "expected_exit": exit_code,
                "actual_exit": result.returncode,
                "result": data,
                "stderr": result.stderr,
            }
        )
        assert result.returncode == exit_code, (command, result.returncode, data)
        return data

    def model(self, update=None):
        model = deepcopy(BASE)
        if update:
            update(model)
        file = self.directory / "model.json"
        write_json(file, model)
        return file


def component(model, ident):
    return next(part for part in model["components"] if part["id"] == ident)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def m01(session):
    summary = read(ROOT / "reports/verification-summary.json")
    assert summary["status"] == "PASS" and summary["source_dirty"] is False
    assert all(
        summary["stages"][stage]["status"] == "PASS"
        for stage in (
            "positive-tests",
            "controlled-fault-tests",
            "frontend-build",
            "browser-acceptance",
        )
    )
    for name in ("test-results.xml", "coverage.xml"):
        assert (ROOT / "reports" / name).is_file()
    session.observations.append(
        {
            "verified_commit": summary["source_commit"],
            "python": summary["python_results"],
            "browser": summary["browser_results"],
            "source_dirty": summary["source_dirty"],
        }
    )
    return (
        "Verification summary and both XML reports exist. Setup evidence is the clean-checkout run."
    )


def m02(session):
    model = session.model(lambda data: data.update(project="Audit open bay"))
    checked = session.cli("check", model)
    directory = session.directory / "exports"
    session.cli("export", model, directory)
    manifest = read(directory / "manifest.json")
    assert manifest["project"] == "Audit open bay" and len(manifest["components"]) == 8
    assert checked["revision"] == manifest["revision"]
    return "New project name, eight components and matching canonical revision."


def m03(session):
    path = session.model()
    revision = session.cli("check", path)["revision"]
    model = read(path)
    model["components"].reverse()
    write_json(path, model)
    assert read(path)["components"][0]["id"] == BASE["components"][-1]["id"]
    assert session.cli("check", path)["revision"] == revision
    compare = session.cli("compare", BASELINE, path, session.directory / "reordered")
    assert compare["delta_mass_kg"] == 0 and compare["modified"] == []
    return "Saved and re-read reordered JSON. Revision and mass are unchanged."


def m04(session):
    def edit(data):
        plate = component(data, "P-01")
        plate["size_mm"][2], plate["origin_mm"][2] = 8, -8

    path = session.model(edit)
    assert component(read(path), "P-01")["size_mm"][2] == 8
    result = session.cli("compare", BASELINE, path, session.directory / "revised")
    (change,) = result["modified"]
    assert change["id"] == "P-01" and change["before"]["thickness_mm"] == 6
    assert change["after"]["thickness_mm"] == 8
    assert round(change["before"]["mass_kg"], 1) == 94.2
    assert round(change["after"]["mass_kg"], 1) == 125.6
    assert round(result["delta_mass_kg"], 1) == 31.4
    return "Only P-01 changed. Mass 94.2 to 125.6 kg and assembly delta +31.4 kg."


def expect_input(result, code, content):
    (finding,) = result["findings"]
    assert finding["code"] == code and content in finding["actual"]


def m05(session):
    path = session.model(lambda data: component(data, "P-01")["size_mm"].__setitem__(2, 0))
    expect_input(session.cli("check", path, exit_code=2), "INPUT_DIMENSION", "P-01.size_mm.Z")
    return "Zero thickness returned exit 2 with the exact dimension field."


def m06(session):
    model = deepcopy(BASE)
    plate = component(model, "P-01")
    path = session.directory / "model.json"
    for thickness, expected in ((0.001, 0), (0.0009, 2)):
        plate["size_mm"][2], plate["origin_mm"][2] = thickness, -thickness
        write_json(path, model)
        result = session.cli("check", path, exit_code=expected)
        if expected:
            expect_input(result, "INPUT_DIMENSION", "P-01.size_mm.Z")
    return "0.001 mm passed. 0.0009 mm returned INPUT_DIMENSION."


def m07(session):
    path = session.model()
    full = path.read_text(encoding="utf-8")
    path.write_text(full.rstrip()[:-1], encoding="utf-8")
    expect_input(session.cli("check", path, exit_code=2), "INPUT_READ", "Cannot read")
    path.write_text(full, encoding="utf-8")
    session.cli("check", path)
    return "Truncated JSON returned INPUT_READ. Restoring the brace passed."


def m08(session):
    path = session.model(lambda data: component(data, "S-01")["origin_mm"].__setitem__(2, 0.001))
    expect_input(session.cli("check", path, exit_code=2), "INPUT_PLACEMENT", "S-01")
    session.cli("check", session.model())
    return "Shifted part failed placement. Restored contact passed."


def m09(session):
    path = session.model(lambda data: component(data, "S-01")["size_mm"].__setitem__(0, 1100.001))
    result = session.cli("check", path, exit_code=2)
    expect_input(result, "INPUT_OVERLAP", "S-01")
    assert "B-01" in result["findings"][0]["actual"]
    session.cli("check", session.model())
    return "0.001 mm penetration reported B-01/S-01 overlap. Exact contact passed."


def fault(session, id_):
    directory = Path("frontend/public/data/faults") / id_
    return session.cli("validate", directory / "model.json", directory, exit_code=1)["findings"]


def m10(session):
    findings = fault(session, "stale_bom")
    plate_findings = {f["code"]: f for f in findings if f["component"] == "P-01"}
    assert (
        plate_findings["STALE_REVISION"]["expected"] != plate_findings["STALE_REVISION"]["actual"]
    )
    assert (
        float(plate_findings["MASS"]["actual"]) == 94.2
        and plate_findings["MASS"]["expected"] == 125.6
    )
    return "Stale hash and P-01 mass 94.2 kg observed, 125.6 kg expected."


def m11(session):
    findings = fault(session, "stale_drawing")
    plate_findings = {f["code"]: f for f in findings if f["component"] == "P-01"}
    assert "DRAWING_ANNOTATION" in plate_findings
    assert float(plate_findings["DRAWING_THICKNESS"]["actual"]) == 6
    assert plate_findings["DRAWING_THICKNESS"]["expected"] == 8
    return (
        "Drawing thickness and visible annotation mismatch. Browser check records the visible 6 mm."
    )


def m12(session):
    directory = ROOT / "frontend/public/data/faults/missing_stiffener"
    assert component(read(directory / "model.json"), "S-04")
    (finding,) = fault(session, "missing_stiffener")
    assert finding["artifact"] == "model.obj" and finding["code"] == "COMPONENT_INVENTORY"
    assert "S-04" in finding["expected"] and "S-04" not in finding["actual"]
    return "Canonical source retains S-04. The OBJ inventory omits it."


def m13(session):
    findings = fault(session, "wrong_units")
    assert {f["code"] for f in findings} == {"VOLUME", "MASS", "ASSEMBLY_MASS"}
    mass = next(f for f in findings if f["code"] == "MASS")
    assert mass["component"] == "B-01"
    assert abs(float(mass["actual"]) / mass["expected"] - 1000) < 1e-9
    return "The current-revision B-01 row is inflated 1,000×. Mass and volume checks fired."


def m14(session):
    data = session.cli("check", "frontend/public/data/faults/duplicate_id/model.json", exit_code=2)
    expect_input(data, "INPUT_DUPLICATE_ID", "S-03")
    return "Duplicate S-03 reported with exit 2."


def m23(session):
    session.cli("export", BASELINE, session.directory)
    path = session.directory / "drawing.svg"
    old = path.read_text(encoding="utf-8")
    label = "P-01    2000 × 1000 × 6 mm    t=6 mm"
    assert old.count(label) == 1
    path.write_text(old.replace(label, label.replace("t=6 mm", "t=8 mm")), encoding="utf-8")
    result = session.cli("validate", BASELINE, session.directory, exit_code=1)
    assert [(f["code"], f["component"]) for f in result["findings"]] == [
        ("DRAWING_ANNOTATION", "P-01"),
    ]
    return (
        "The visible note changed to 8 mm. Metadata stayed at 6 mm. Only DRAWING_ANNOTATION fired."
    )


def m24(session):
    previous, current, rerun = (session.directory / name for name in ("old", "new", "confirmed"))
    session.cli("export", BASELINE, previous)
    bad = session.cli("compare", BASELINE, CHANGED, current, "--against", previous, exit_code=1)
    assert bad["validation"]["status"] == "PASS" and bad["candidate_validation"]["status"] == "FAIL"
    assert read(current / "comparison.json") == bad
    good = session.cli("compare", BASELINE, CHANGED, rerun, "--against", current)
    assert good["validation"]["status"] == good["candidate_validation"]["status"] == "PASS"
    assert read(rerun / "comparison.json") == good
    return "Fresh outputs PASS in both comparisons. Old candidate FAIL/1, revised candidate PASS/0."


CASES = (m01, m02, m03, m04, m05, m06, m07, m08, m09, m10, m11, m12, m13, m14, m23, m24)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("build/manual-audit/shell"))
    args = parser.parse_args()
    status = 0
    rows = []
    for case in CASES:
        session = Session(case.__name__.upper(), args.output)
        try:
            result = case(session)
            outcome = "PASS"
        except Exception as error:
            outcome, result = "FAIL", repr(error)
            status = 1
        row = {"id": case.__name__.upper(), "status": outcome, "actual": result}
        print(f"{row['id']} {outcome} {result}")
        write_json(session.directory / "observations.json", {**row, "runs": session.observations})
        rows.append(row)
    write_json(
        args.output / "summary.json",
        {
            "kind": "scripted shell reproduction",
            "python": platform.python_version(),
            "platform": platform.system(),
            "executed_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "cases": rows,
        },
    )
    return status


if __name__ == "__main__":
    raise SystemExit(main())
