"""
Suggestions layer, built on top of the same knowledge base data validation
uses (workflow order, validation_rules timing windows), but answering a
different question: not "is this record valid" but "what should this farm
do next, and by when."

Deliberately scoped for v1. It only looks at the next REQUIRED, not-yet-done
step in workflow order, and estimates a due window from whatever
validation_rule matches. It does NOT yet model recurring due dates for
operations that can repeat (e.g. "weed again 3 weeks after the last
weeding") -- once an operation has been logged at least once, this module
stops suggesting it, even if the crop would realistically need it again.
That is a real, deliberate gap: modeling recurrence intervals cleanly is a
separate design problem (weeding_2 isn't just "weeding_1 again", cocoa's
harvest recurs seasonally with no interval encoded anywhere in the schema
yet), and it seemed better to ship an honest, narrower v1 than to guess at
recurrence logic that hasn't been designed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from .history import parse_and_scope_history
from .loader import get_effective_rules, load_crop


@dataclass
class NextStepSuggestion:
    operation_id: str
    status: str  # "due_now" | "upcoming" | "overdue" | "blocked_on_prerequisite" | "no_timing_rule"
    message: str
    depends_on_operation_id: Optional[str] = None
    depends_on_date: Optional[date] = None
    earliest_date: Optional[date] = None
    latest_date: Optional[date] = None
    days_until_due: Optional[int] = None
    days_overdue: Optional[int] = None


@dataclass
class SuggestionReport:
    crop_id: str
    as_of: date
    cycle_status: str  # "in_progress" | "no_outstanding_required_steps"
    suggestion: Optional[NextStepSuggestion] = None


def get_next_steps(
    crop_id: str,
    history: list[dict],
    region: Optional[str] = None,
    as_of: Optional[date] = None,
) -> SuggestionReport:
    """
    Returns the next required, not-yet-logged operation for this farm, with
    an estimate of when it's due, based on the same validation_rules the
    validation engine checks against.

    Raises the same exceptions as validate_operation for a missing crop
    or malformed history data (CropNotFoundError, InvalidOperationDataError).
    """
    crop = load_crop(crop_id)
    rules = get_effective_rules(crop, region)
    as_of = as_of or date.today()

    hist = parse_and_scope_history(history, crop_id)

    # Most recent logged date per operation_id. Used both to check "has this
    # ever been logged" and as the dependency date for timing estimates.
    latest_by_operation: dict[str, date] = {}
    for h in hist:
        if h.operation_id not in latest_by_operation or h.date > latest_by_operation[h.operation_id]:
            latest_by_operation[h.operation_id] = h.date

    workflow = sorted(crop.get("workflow", []), key=lambda s: s["step_number"])

    for step in workflow:
        op_id = step["operation_id"]

        if op_id in latest_by_operation:
            continue  # already logged at least once -- see module docstring on recurrence

        if not step.get("required", False):
            continue  # optional and not done yet: not treated as "next due" in v1

        # This is the next required, not-yet-done step in workflow order.
        suggestion = _estimate_due_window(op_id, rules, latest_by_operation, as_of)
        return SuggestionReport(crop_id=crop_id, as_of=as_of, cycle_status="in_progress", suggestion=suggestion)

    return SuggestionReport(crop_id=crop_id, as_of=as_of, cycle_status="no_outstanding_required_steps", suggestion=None)


def _estimate_due_window(
    op_id: str,
    rules: list[dict],
    latest_by_operation: dict[str, date],
    as_of: date,
) -> NextStepSuggestion:
    candidate_rules = [
        r for r in rules if r["operation_id"] == op_id and r.get("depends_on_operation_id")
    ]

    if not candidate_rules:
        return NextStepSuggestion(
            operation_id=op_id,
            status="no_timing_rule",
            message=(
                f"'{op_id}' is next in the workflow, but there is no timing rule in the "
                f"knowledge base yet to estimate exactly when it's due."
            ),
        )

    # Prefer the narrowest-range rule as the best estimate of the "typical"
    # window (this is usually the warning-severity rule when both a wide
    # block rule and a narrower warning rule exist for the same operation,
    # e.g. maize's harvest: an 80-150 day block plus a 90-120 day warning).
    #
    # Important distinction from the validator: "overdue" here is always
    # relative to whichever rule gets chosen as the typical window, not
    # necessarily the crop's true hard limit. For cassava's harvest, that
    # means a suggestion can say "overdue" once the farm passes the 270-450
    # day typical window, even though cassava_r6 (the actual block rule) has
    # no upper bound at all and the validator would never reject a harvest
    # for being "too late." That's intentional: a reminder nudging someone
    # past the normal window is useful even when the crop itself is more
    # forgiving than that window suggests.
    def _span(rule: dict) -> float:
        lo = rule.get("min_days_after_dependency")
        hi = rule.get("max_days_after_dependency")
        if lo is None or hi is None:
            return float("inf")
        return hi - lo

    chosen = min(candidate_rules, key=_span)
    dep_id = chosen["depends_on_operation_id"]
    dep_date = latest_by_operation.get(dep_id)

    if dep_date is None:
        return NextStepSuggestion(
            operation_id=op_id,
            status="blocked_on_prerequisite",
            message=(
                f"'{op_id}' can't be estimated yet: it depends on '{dep_id}', "
                f"which hasn't been logged."
            ),
            depends_on_operation_id=dep_id,
        )

    min_days = chosen.get("min_days_after_dependency")
    max_days = chosen.get("max_days_after_dependency")
    days_since_dep = (as_of - dep_date).days

    earliest_date = dep_date + timedelta(days=min_days) if min_days is not None else None
    latest_date = dep_date + timedelta(days=max_days) if max_days is not None else None

    if min_days is not None and days_since_dep < min_days:
        days_until_due = min_days - days_since_dep
        return NextStepSuggestion(
            operation_id=op_id,
            status="upcoming",
            message=f"'{op_id}' is expected in about {days_until_due} day(s), around {earliest_date}.",
            depends_on_operation_id=dep_id,
            depends_on_date=dep_date,
            earliest_date=earliest_date,
            latest_date=latest_date,
            days_until_due=days_until_due,
        )

    if max_days is not None and days_since_dep > max_days:
        days_overdue = days_since_dep - max_days
        return NextStepSuggestion(
            operation_id=op_id,
            status="overdue",
            message=f"'{op_id}' is now {days_overdue} day(s) overdue (expected by {latest_date}).",
            depends_on_operation_id=dep_id,
            depends_on_date=dep_date,
            earliest_date=earliest_date,
            latest_date=latest_date,
            days_overdue=days_overdue,
        )

    return NextStepSuggestion(
        operation_id=op_id,
        status="due_now",
        message=f"'{op_id}' is due now, within its expected window.",
        depends_on_operation_id=dep_id,
        depends_on_date=dep_date,
        earliest_date=earliest_date,
        latest_date=latest_date,
    )
