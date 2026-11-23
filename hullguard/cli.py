"""Command-line entry point and stable exit statuses."""

import argparse
import json
from pathlib import Path

from .comparison import compare_models, create_bundle
from .models import ModelError, load_model
from .scenarios import check_input, evidence_passes, generate_evidence
from .validation import validate_bundle

OK, FINDINGS, INPUT_ERROR = 0, 1, 2


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="hullguard", description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="Validate a canonical model")
    check.add_argument("model", type=Path)
    export = commands.add_parser("export", help="Generate and validate a bundle")
    export.add_argument("model", type=Path)
    export.add_argument("output", type=Path)
    validate = commands.add_parser("validate", help="Validate an existing bundle")
    validate.add_argument("model", type=Path)
    validate.add_argument("bundle", type=Path)
    compare = commands.add_parser(
        "compare", help="Generate a revised bundle and change-impact report"
    )
    compare.add_argument("baseline", type=Path)
    compare.add_argument("revision", type=Path)
    compare.add_argument("output", type=Path)
    compare.add_argument("--against", type=Path, help="Also reconcile a candidate bundle")
    demo = commands.add_parser("demo", help="Generate positive and controlled negative evidence")
    demo.add_argument("--fixtures", type=Path, default=Path("fixtures"))
    demo.add_argument("--out", type=Path, default=Path("frontend/public/data"))
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "check":
            result = check_input(args.model)
            status = OK if result["status"] == "PASS" else INPUT_ERROR
        elif args.command == "export":
            result = create_bundle(load_model(args.model), args.output)
            status = OK if result["status"] == "PASS" else FINDINGS
        elif args.command == "validate":
            result = validate_bundle(load_model(args.model), args.bundle).as_dict()
            status = OK if result["status"] == "PASS" else FINDINGS
        elif args.command == "compare":
            before, after = load_model(args.baseline), load_model(args.revision)
            result = compare_models(before, after)
            if args.against:
                result["candidate_validation"] = validate_bundle(after, args.against).as_dict()
            current = create_bundle(after, args.output, result)
            candidate = result.get("candidate_validation", current)
            status = OK if current["status"] == candidate["status"] == "PASS" else FINDINGS
        else:
            catalog = generate_evidence(args.fixtures, args.out)
            status = OK if evidence_passes(catalog) else FINDINGS
            result = {
                "status": "PASS" if status == OK else "FAIL",
                "revisions": len(catalog["revisions"]),
                "faults": len(catalog["faults"]),
                "evidence": (args.out / "index.json").as_posix(),
            }
    except (ModelError, OSError, ValueError) as error:
        result = {
            "status": "FAIL",
            "code": getattr(error, "code", "COMMAND_ERROR"),
            "message": str(error),
        }
        status = INPUT_ERROR
    print(json.dumps(result, indent=2, ensure_ascii=True, allow_nan=False))
    return status
