"""
Core validation logic. This is deliberately plain Python, no framework, so it
can be called directly from tests, wrapped by the CLI, or eventually dropped
into a real API without changes.

The central function is validate_operation(). Everything else supports it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
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

    # Workflow-order sanity check. The global-order check above only catches
    # a STRICTLY EARLIER date than the most recent operation. It does nothing
    # for same-date or later-date submissions that still make no sense, e.g.
    # logging land_preparation after harvest already exists in history, even
    # dated today. No individual rule catches this either, since each rule
    # only checks an operation's relationship to its OWN declared dependency,
    # not its position relative to everything else already logged.
    #
    # This check blocks logging a one-time (can_repeat: false) operation if a
    # LATER one-time operation, per the crop's workflow step_number order,
    # has already been logged.
    #
    # Whether a "new cycle" legitimately resets this depends on the crop.
    # For annual, single-harvest crops (maize, cassava, rice: harvest itself
    # is can_repeat false), logging land_clearing again after a harvest is
    # how a real new planting cycle begins, so history from BEFORE the most
    # recent harvest is excluded from this check entirely once a harvest has
    # happened. For crops where harvest itself repeats (cocoa/cashew's
    # recurring seasonal harvest, tomato/hibiscus's multiple picks within one
    # planting), there is no such reset: land_clearing or transplanting
    # reappearing after any harvest is never legitimate in this model, so no
    # exception applies and the full history is checked.
    operations_by_id = {o["operation_id"]: o for o in crop.get("operations", [])}
    workflow_steps = crop.get("workflow", [])
    step_number_by_op = {s["operation_id"]: s["step_number"] for s in workflow_steps}

    harvest_operations = [o for o in crop.get("operations", []) if o.get("category") == "harvest"]
    harvest_is_repeatable = any(o.get("can_repeat") for o in harvest_operations)

    comparison_hist = hist
    if not harvest_is_repeatable:
        harvest_op_ids = {o["operation_id"] for o in harvest_operations}
        harvest_dates = [h.date for h in hist if h.operation_id in harvest_op_ids]
        if harvest_dates:
            most_recent_harvest_date = max(harvest_dates)
            # The cycle-reset exception only applies if THIS operation is
            # dated strictly AFTER the last harvest. If it's dated on or
            # before that harvest, e.g. the same date, this is not a
            # believable "new season," so no exception applies and the
            # FULL history is checked, catching exactly that edge case.
            if op.date > most_recent_harvest_date:
                comparison_hist = [h for h in hist if h.date > most_recent_harvest_date]

    new_op_step = step_number_by_op.get(op.operation_id)
    new_op_can_repeat = operations_by_id.get(op.operation_id, {}).get("can_repeat", False)

    if new_op_step is not None and not new_op_can_repeat:
        for h in comparison_hist:
            h_step = step_number_by_op.get(h.operation_id)
            h_can_repeat = operations_by_id.get(h.operation_id, {}).get("can_repeat", False)
            if h_step is not None and not h_can_repeat and h_step > new_op_step:
                issues.append(
                    ValidationIssue(
                        rule_id="engine-workflow-order",
                        severity="block",
                        message=(
                            f"'{op.operation_id}' cannot be logged now: "
                            f"'{h.operation_id}' has already been logged, and it "
                            f"comes later in the workflow. Inserting an earlier "
                            f"step after a later one has already happened is not "
                            f"allowed, even if the date looks plausible on its own."
                        ),
                    )
                )
                break

    relevant_rules = [r for r in rules if r["operation_id"] in (op.operation_id, "*")]

    for rule in relevant_rules:
        if rule["operation_id"] == "*":
            # The wildcard rule is already covered by the explicit check above.
            continue

        # Occurrence/frequency rules (added in the engine-fixes pass following
        # the Medium-priority crop batch -- see pepper.json's harvest-frequency
        # rule and rubber.json's tapping/stimulation-frequency rules, none of
        # which could be expressed before this existed). This is evaluated
        # independently of dependency/day-offset logic: a rule using this
        # mechanism sets max_occurrences and occurrence_window_days instead of
        # min/max_days_after_dependency, so it's handled here and then skipped
        # for the rest of the loop below.
        max_occ = rule.get("max_occurrences")
        occ_window = rule.get("occurrence_window_days")
        if max_occ is not None and occ_window is not None:
            window_start = op.date - timedelta(days=occ_window - 1)
            same_op_in_window = [
                h for h in hist
                if h.operation_id == op.operation_id and window_start <= h.date <= op.date
            ]
            # +1 counts the new submission itself, since it's about to be logged.
            count_including_new = len(same_op_in_window) + 1
            if count_including_new > max_occ:
                issues.append(
                    ValidationIssue(
                        rule_id=rule["rule_id"],
                        severity=rule["severity"],
                        message=(
                            f"{rule['condition']} ({count_including_new} "
                            f"'{op.operation_id}' entries within the last "
                            f"{occ_window} day(s) as of {op.date}; maximum is "
                            f"{max_occ}.)"
                        ),
                    )
                )
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
            # required_dependency (added in the same engine-fixes pass, see
            # schema.json) defaults to True, preserving the original
            # auto-block-on-missing-dependency behavior for every rule that
            # existed before this field did. A rule that explicitly sets this
            # to False is a SELF-REFERENTIAL interval rule (dep_id equals this
            # rule's own operation_id, checking the gap since the operation's
            # own last occurrence) where having no prior occurrence simply
            # means this is the first one ever -- not a violation to block.
            if rule.get("required_dependency", True) is False:
                continue
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
        window_mode = rule.get("window_mode", "outside")

        if window_mode == "inside":
            # Added in the engine-fixes pass -- see groundnut.json's weeding
            # rule, which needed to warn ONLY inside an interior band (40-60
            # DAP) and could not be expressed with the "outside" logic below.
            # Fires when days_diff falls inside [min, max] (inclusive); either
            # bound may be omitted to leave that side of the band open.
            inside_lower = min_days is None or days_diff >= min_days
            inside_upper = max_days is None or days_diff <= max_days
            if inside_lower and inside_upper:
                issues.append(
                    ValidationIssue(
                        rule_id=rule["rule_id"],
                        severity=rule["severity"],
                        message=(
                            f"{rule['condition']} (logged {days_diff} day(s) "
                            f"after '{dep_id}', inside the flagged "
                            f"{min_days}-{max_days} day window.)"
                        ),
                    )
                )
            continue

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