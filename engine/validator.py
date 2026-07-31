"""
Core validation logic. This is deliberately plain Python, no framework, so it
can be called directly from tests, wrapped by the CLI, or eventually dropped
into a real API without changes.

The central function is validate_operation(). Everything else supports it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from .exceptions import InvalidOperationDataError
from .history import FarmOperation, parse_and_scope_history
from .loader import load_crop, get_effective_rules


@dataclass
class ValidationIssue:
    rule_id: str
    severity: str  # "block" or "warning"
    message: str


@dataclass
class ValidationReport:
    crop_id: str
    operation_id: str
    date: date
    blocked: bool
    issues: list = field(default_factory=list)

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def blocking_issues(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "block"]


def validate_operation(
    crop_id: str,
    new_operation: dict,
    history: list[dict],
    region: Optional[str] = None,
) -> ValidationReport:
    """
    Check whether `new_operation` (e.g. {"operation_id": "harvest", "date": "2026-08-01"})
    is a valid record to log for this farm, given everything already logged in `history`.

    Returns a ValidationReport. report.blocked is True if the operation should
    be rejected outright. report.warnings holds anything that should be
    allowed through but flagged for follow-up.

    A note on farms growing more than one crop: if `history` mixes operations
    from multiple crops (e.g. a farm logs both maize and cassava planting in
    one combined list), tag each entry with "crop_id" so this function can
    tell them apart. If any entry in `history` carries a crop_id, only entries
    matching this call's `crop_id` are considered; everything else is ignored,
    including untagged entries, since an untagged entry in an otherwise-tagged
    history is ambiguous and safer to exclude than guess. If NO entry carries
    a crop_id, the whole list is treated as belonging to this one crop (the
    original single-crop-per-farm behavior). Passing a single farm's full
    multi-crop history without crop_id tags will silently mix crops together
    and produce wrong results. This is intentional here, not a bug: it is
    still the caller's responsibility to either tag entries or pre-filter
    history to one crop before calling.

    Raises InvalidOperationDataError if `new_operation` or an entry in
    `history` is missing a required field or has a badly formatted date.
    Raises CropNotFoundError if `crop_id` has no matching knowledge base file.
    """
    crop = load_crop(crop_id)
    rules = get_effective_rules(crop, region)
    known_operation_ids = {o["operation_id"] for o in crop.get("operations", [])}

    op = FarmOperation.from_dict(new_operation, context="new_operation")
    hist = parse_and_scope_history(history, crop_id)

    issues: list[ValidationIssue] = []

    # Reject operation types that don't exist for this crop at all, e.g. a
    # typo or a client sending an operation_id that belongs to a different
    # crop's workflow. Without this check such a submission previously found
    # no matching rules and passed with zero issues, silently.
    if op.operation_id not in known_operation_ids:
        issues.append(
            ValidationIssue(
                rule_id="engine-unknown-operation",
                severity="block",
                message=(
                    f"'{op.operation_id}' is not a recognized operation for "
                    f"'{crop_id}'. Known operations: {', '.join(sorted(known_operation_ids))}."
                ),
            )
        )
        return ValidationReport(
            crop_id=crop_id, operation_id=op.operation_id, date=op.date, blocked=True, issues=issues
        )

    # Global rule, enforced directly rather than by looking it up: no operation
    # may be dated earlier than the most recently logged operation. This is
    # what "no backdating that reorders the sequence" means in practice.
    if hist:
        last_op = max(hist, key=lambda h: h.date)
        if op.date < last_op.date:
            issues.append(
                ValidationIssue(
                    rule_id="global-order",
                    severity="block",
                    message=(
                        f"'{op.operation_id}' is dated {op.date}, which is earlier "
                        f"than the most recently logged operation "
                        f"('{last_op.operation_id}' on {last_op.date}). Backdating "
                        f"that would reorder the sequence is not allowed."
                    ),
                )
            )

    relevant_rules = [r for r in rules if r["operation_id"] in (op.operation_id, "*")]

    for rule in relevant_rules:
        if rule["operation_id"] == "*":
            # The wildcard rule is already covered by the explicit check above.
            continue

        dep_id = rule.get("depends_on_operation_id")
        can_repeat = rule.get("can_repeat", True)

        # A rule with no dependency and can_repeat False means "this operation
        # may only be logged once ever" (e.g. one harvest per annual planting).
        if dep_id is None and can_repeat is False:
            prior = [h for h in hist if h.operation_id == op.operation_id]
            if prior:
                issues.append(
                    ValidationIssue(
                        rule_id=rule["rule_id"],
                        severity=rule["severity"],
                        message=rule["condition"],
                    )
                )
            continue

        if dep_id is None:
            continue

        dep_matches = [h for h in hist if h.operation_id == dep_id]
        if not dep_matches:
            issues.append(
                ValidationIssue(
                    rule_id=rule["rule_id"],
                    severity="block",
                    message=(
                        f"'{op.operation_id}' requires '{dep_id}' to be logged "
                        f"first, and no record of it exists yet."
                    ),
                )
            )
            continue

        dep_op = max(dep_matches, key=lambda h: h.date)
        days_diff = (op.date - dep_op.date).days

        min_days = rule.get("min_days_after_dependency")
        max_days = rule.get("max_days_after_dependency")

        if min_days is not None and days_diff < min_days:
            issues.append(
                ValidationIssue(
                    rule_id=rule["rule_id"],
                    severity=rule["severity"],
                    message=(
                        f"{rule['condition']} (logged {days_diff} day(s) after "
                        f"'{dep_id}'; minimum is {min_days}.)"
                    ),
                )
            )
        elif max_days is not None and days_diff > max_days:
            issues.append(
                ValidationIssue(
                    rule_id=rule["rule_id"],
                    severity=rule["severity"],
                    message=(
                        f"{rule['condition']} (logged {days_diff} day(s) after "
                        f"'{dep_id}'; maximum is {max_days}.)"
                    ),
                )
            )
        # If max_days is None (e.g. cassava's harvest rule), there is no upper
        # bound to violate. That is intentional, not a gap in the check.

    blocked = any(i.severity == "block" for i in issues)

    return ValidationReport(
        crop_id=crop_id,
        operation_id=op.operation_id,
        date=op.date,
        blocked=blocked,
        issues=issues,
    )
