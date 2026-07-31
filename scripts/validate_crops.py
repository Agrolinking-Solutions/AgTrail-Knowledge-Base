"""
Validate every crop file in knowledge_base/crops/ against knowledge_base/schema.json.

Run from the project root:

    python scripts/validate_crops.py

This does two layers of checking:

1. JSON Schema validation  -- does the file have the required shape/types?
2. Cross-reference checks  -- do operation_id references inside `workflow` and
   `validation_rules` actually exist in the `operations` array? JSON Schema
   alone can't express "this string must match an id defined elsewhere in
   the same document," so we check that by hand.

Exits with a non-zero status code if anything fails, so this is safe to wire
into CI later (e.g. a pre-commit hook or GitHub Action) to stop a malformed
crop file from being merged.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "knowledge_base" / "schema.json"
CROPS_DIR = ROOT / "knowledge_base" / "crops"


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def check_schema(crop_data: dict, validator: Draft202012Validator) -> list[str]:
    errors = []
    for error in sorted(validator.iter_errors(crop_data), key=lambda e: e.path):
        location = " -> ".join(str(p) for p in error.path) or "(root)"
        errors.append(f"[schema] {location}: {error.message}")
    return errors


def check_cross_references(crop_data: dict) -> list[str]:
    errors = []
    operation_ids = {op["operation_id"] for op in crop_data.get("operations", [])}

    for step in crop_data.get("workflow", []):
        op_id = step.get("operation_id")
        if op_id not in operation_ids:
            errors.append(
                f"[xref] workflow step {step.get('step_number')} references "
                f"unknown operation_id '{op_id}'"
            )
        repeat_until = step.get("repeat_until")
        if repeat_until and repeat_until not in operation_ids:
            errors.append(
                f"[xref] workflow step {step.get('step_number')} repeat_until "
                f"references unknown operation_id '{repeat_until}'"
            )

    for rule in crop_data.get("validation_rules", []):
        op_id = rule.get("operation_id")
        # "*" is a reserved wildcard meaning "applies to every operation"
        if op_id != "*" and op_id not in operation_ids:
            errors.append(
                f"[xref] validation_rule '{rule.get('rule_id')}' references "
                f"unknown operation_id '{op_id}'"
            )
        dep_id = rule.get("depends_on_operation_id")
        if dep_id and dep_id not in operation_ids:
            errors.append(
                f"[xref] validation_rule '{rule.get('rule_id')}' references "
                f"unknown depends_on_operation_id '{dep_id}'"
            )

    current_version = crop_data.get("metadata", {}).get("current_version")
    version_history_versions = {
        v.get("version") for v in crop_data.get("version_history", [])
    }
    if current_version not in version_history_versions:
        errors.append(
            f"[xref] metadata.current_version '{current_version}' has no "
            f"matching entry in version_history"
        )

    return errors


def main() -> int:
    if not SCHEMA_PATH.exists():
        print(f"Schema not found at {SCHEMA_PATH}")
        return 1

    schema = load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema)

    crop_files = sorted(CROPS_DIR.glob("*.json"))
    if not crop_files:
        print(f"No crop files found in {CROPS_DIR}")
        return 1

    total_errors = 0
    for crop_file in crop_files:
        crop_data = load_json(crop_file)
        errors = check_schema(crop_data, validator) + check_cross_references(crop_data)

        if errors:
            total_errors += len(errors)
            print(f"\nFAIL  {crop_file.relative_to(ROOT)}")
            for err in errors:
                print(f"       - {err}")
        else:
            crop_name = crop_data.get("metadata", {}).get("name", crop_file.stem)
            print(f"OK    {crop_file.relative_to(ROOT)}  ({crop_name})")

    print()
    if total_errors:
        print(f"{total_errors} error(s) across {len(crop_files)} crop file(s).")
        return 1

    print(f"All {len(crop_files)} crop file(s) valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
