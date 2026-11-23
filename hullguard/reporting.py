"""Structured evidence and an offline engineering report."""

import json
from dataclasses import asdict, dataclass
from html import escape
from pathlib import Path


@dataclass(frozen=True)
class Finding:
    code: str
    artifact: str
    component: str
    expected: object
    actual: object


@dataclass(frozen=True)
class Validation:
    revision: str
    findings: tuple[Finding, ...]
    checked: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "status": "FAIL" if self.findings else "PASS",
            "revision": self.revision,
            "checked": self.checked,
            "findings": [asdict(finding) for finding in self.findings],
        }


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


def write_json(path: Path, value: object) -> None:
    write_text(path, json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + "\n")


def inline_json(value: object) -> str:
    return escape(json.dumps(value, ensure_ascii=False))


def engineering_html(manifest: dict, validation: Validation, comparison: dict | None = None) -> str:
    rows = "".join(
        f"<tr><th>{p['id']}</th><td>{p['kind']}</td><td>{p['material']}</td>"
        f"<td>{inline_json(p['size_mm'])}</td><td>{p['mass_kg']:.6f}</td></tr>"
        for p in manifest["components"]
    )
    findings = "".join(
        f"<li><strong>{f.code}</strong> {escape(f.artifact)} {escape(f.component)}. "
        f"Expected <code>{inline_json(f.expected)}</code>. "
        f"Actual <code>{inline_json(f.actual)}</code>.</li>"
        for f in validation.findings
    )
    checks = "<ul>" + findings + "</ul>" if findings else "<p>All checked artifacts reconciled.</p>"
    impact = ""
    if comparison:
        impact = (
            f"<h2>Change impact</h2><p>Assembly mass delta {comparison['delta_mass_kg']:+.6f} kg.</p>"
            '<p><a href="comparison.json">Revision comparison and affected artifacts</a></p>'
            f"<p>Added {inline_json(comparison['added'])}. Removed {inline_json(comparison['removed'])}.</p>"
        )
        if candidate := comparison.get("candidate_validation"):
            impact += (
                f"<p>Candidate export status <strong>{candidate['status']}</strong>. "
                f"{len(candidate['findings'])} findings. Full details are in the comparison JSON.</p>"
            )
    return f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>HULLGUARD QA engineering report</title>
<style>
body{{font:1rem/1.6 system-ui;margin:2rem auto;padding:0 1rem;max-width:64rem;color:#142737}}
table{{border-collapse:collapse;width:100%}}td,th{{text-align:left;padding:.5rem;border-bottom:1px solid #ccd5db}}
code{{overflow-wrap:anywhere}}a{{color:#005865}}.table{{overflow:auto}}
</style>
<main><h1>Engineering report</h1><p>{escape(manifest["project"])}</p>
<p>Source SHA-256 <code>{validation.revision}</code></p>
<p><strong>{validation.as_dict()["status"]}</strong> · {manifest["assembly_mass_kg"]:.6f} kg</p>
<h2>Component inventory</h2><div class="table"><table><thead>
<tr><th>Component</th><th>Kind</th><th>Material</th><th>XYZ dimensions (mm)</th><th>Mass (kg)</th></tr>
</thead><tbody>{rows}</tbody></table></div><h2>Validation findings</h2>{checks}{impact}
<h2>Export evidence</h2><p>
<a href="model.obj">OBJ mesh</a> · <a href="manifest.json">Manifest</a> ·
<a href="bom.csv">Bill of materials</a> · <a href="drawing.svg">Plan drawing</a> ·
<a href="validation.json">Validation JSON</a></p>
<h2>Scope</h2><p>Synthetic axis-aligned solids and schematic dimensions. Engineering strength,
class approval and production drafting are outside scope.</p></main></html>
"""
