"""
Cocoa, oil palm, cashew, rubber and coffee are perennial, and many orchards were planted long
before they were entered here: for them only maintenance and harvest are logged. The rules that
tie those jobs to the nursery or transplanting apply only when that step was recorded.
"""

from datetime import date, timedelta

import pytest

from engine.validator import validate_operation

BASE = date(2026, 3, 1)


def at(days):
    return (BASE + timedelta(days=days)).isoformat()


def check(crop, history, operation, day):
    return validate_operation(
        crop_id=crop,
        history=[{"operation_id": op, "date": at(d)} for op, d in history],
        new_operation={"operation_id": operation, "date": at(day)},
    )


def says_to_log_first(report):
    return [i for i in report.blocking_issues if "to be logged first" in i.message]


# (crop, operation an established orchard logs, transplanting-based rule that would have blocked it)
ESTABLISHED = [
    ("cocoa", "harvest"), ("cocoa", "fertilizer_application"), ("cocoa", "weeding"), ("cocoa", "pruning"),
    ("oil_palm", "harvest"), ("cashew", "harvest"), ("rubber", "tapping"), ("rubber", "stimulation"), ("coffee", "harvest"),
]


@pytest.mark.parametrize("crop, operation", ESTABLISHED)
def test_an_established_orchard_is_not_blocked_for_lacking_the_establishment_steps(crop, operation):
    report = check(crop, [], operation, 0)

    assert says_to_log_first(report) == [], [i.message for i in report.blocking_issues]


@pytest.mark.parametrize("crop, operation", [("cocoa", "fertilizer_application"), ("cocoa", "weeding"), ("cocoa", "pruning")])
def test_cocoa_maintenance_can_follow_a_harvest_in_the_next_season(crop, operation):
    report = check("cocoa", [("harvest", 0)], operation, 200)

    assert not report.blocked, [i.message for i in report.blocking_issues]


@pytest.mark.parametrize("crop, operation, early, ok", [
    ("cocoa", "harvest", 539, 730), ("oil_palm", "harvest", 899, 1095), ("cashew", "harvest", 899, 1095),
    ("rubber", "tapping", 1824, 2190), ("coffee", "harvest", 899, 1095),
])
def test_the_age_limits_still_apply_when_the_transplanting_was_recorded(crop, operation, early, ok):
    history = [("transplanting", 0)]
    if crop == "cashew":
        history = [("land_clearing", -400), ("land_preparation", -380), ("nursery_establishment", -300), ("transplanting", 0)]
    if crop in ("cocoa", "oil_palm", "coffee"):
        history = [("land_clearing", -400), ("nursery_establishment", -300), ("transplanting", 0)]
    if crop == "rubber":
        history = [("land_clearing", -400), ("planting_material_sourcing", -350), ("transplanting", 0)]
    assert check(crop, history, operation, early).blocked
    assert not check(crop, history, operation, ok).blocked


def test_the_establishment_steps_are_no_longer_required_in_the_workflow():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent / "knowledge_base" / "crops"
    for crop in ("cocoa", "oil_palm", "cashew", "rubber", "coffee"):
        workflow = json.loads((root / f"{crop}.json").read_text())["workflow"]
        required = {w["operation_id"] for w in workflow if w["required"]}
        assert required.isdisjoint({"land_clearing", "land_preparation", "nursery_establishment", "transplanting"}), crop
