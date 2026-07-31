"""
Thin CLI on top of engine.validator.validate_operation, for trying out
scenarios directly from the terminal during development.

Usage:
    python -m engine.cli validate scenarios/maize_valid_planting.json
    python -m engine.cli list-crops
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .loader import list_crops
from .validator import validate_operation


def _load_scenario(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def cmd_validate(args: argparse.Namespace) -> None:
    scenario = _load_scenario(Path(args.scenario))

    report = validate_operation(
        crop_id=scenario["crop_id"],
        new_operation=scenario["new_operation"],
        history=scenario.get("history", []),
        region=scenario.get("region"),
    )

    if report.blocked:
        status = "BLOCKED"
    elif report.warnings:
        status = "PASSED, WITH WARNINGS"
    else:
        status = "PASSED"

    region_note = f" (region: {scenario['region']})" if scenario.get("region") else ""
    print(f"\n{report.crop_id} -> {report.operation_id} on {report.date}{region_note}")
    print(f"Result: {status}\n")

    if report.blocking_issues:
        print("Blocking issues:")
        for issue in report.blocking_issues:
            print(f"  [{issue.rule_id}] {issue.message}")
        print()

    if report.warnings:
        print("Warnings:")
        for issue in report.warnings:
            print(f"  [{issue.rule_id}] {issue.message}")
        print()

    if not report.issues:
        print("No issues found.\n")


def cmd_list_crops(args: argparse.Namespace) -> None:
    crops = list_crops()
    if not crops:
        print("No crop files found in knowledge_base/crops/")
        return
    for crop_id in crops:
        print(crop_id)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="engine", description="AgTrail workflow/validation engine CLI"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    validate_parser = sub.add_parser(
        "validate", help="Validate a single operation against a scenario file"
    )
    validate_parser.add_argument("scenario", help="Path to a scenario JSON file")
    validate_parser.set_defaults(func=cmd_validate)

    list_parser = sub.add_parser(
        "list-crops", help="List available crop ids in the knowledge base"
    )
    list_parser.set_defaults(func=cmd_list_crops)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
