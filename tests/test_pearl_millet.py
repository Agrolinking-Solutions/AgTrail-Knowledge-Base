"""
Pearl millet rules, from the AgTrail Master Agronomist & Validator Ruleset (section 4):
first weeding or thinning flagged after 21 days and blocked before 5, harvest blocked
before 65 days and flagged outside 75-100, and the yield bands.
"""

from datetime import date, timedelta

import pytest

from engine.validator import validate_operation
from engine.yield_validator import validate_yield

PLANTED = date(2026, 6, 15)
BASE = [
    {"operation_id": "land_clearing", "date": "2026-06-01"},
    {"operation_id": "land_preparation", "date": "2026-06-08"},
    {"operation_id": "planting", "date": PLANTED.isoformat()},
]


def _check(operation_id, days_after_planting):
    return validate_operation(
        crop_id="pearl_millet",
        history=BASE,
        new_operation={"operation_id": operation_id, "date": (PLANTED + timedelta(days=days_after_planting)).isoformat()},
    )


def _ids(issues):
    return {i.rule_id for i in issues}


@pytest.mark.parametrize("day", [5, 14, 21])
def test_first_weeding_inside_the_window_is_clean(day):
    report = _check("weeding_1", day)
    assert not report.blocked and not report.warnings


@pytest.mark.parametrize("day", [22, 35])
def test_a_late_first_weeding_is_flagged_not_blocked(day):
    report = _check("weeding_1", day)
    assert not report.blocked
    assert "pearl_millet_r4" in _ids(report.warnings)


def test_a_first_weeding_before_5_days_is_blocked():
    report = _check("weeding_1", 3)
    assert report.blocked
    assert "pearl_millet_r4_floor" in _ids(report.blocking_issues)


@pytest.mark.parametrize("day", [75, 85, 100])
def test_harvest_inside_the_window_is_clean(day):
    report = _check("harvest", day)
    assert not report.blocked and not report.warnings


@pytest.mark.parametrize("day", [65, 70, 101, 120])
def test_harvest_outside_the_window_is_flagged_not_blocked(day):
    report = _check("harvest", day)
    assert not report.blocked
    assert "pearl_millet_r8b" in _ids(report.warnings)


def test_harvest_before_65_days_is_blocked():
    report = _check("harvest", 64)
    assert report.blocked
    assert "pearl_millet_r8" in _ids(report.blocking_issues)


def test_a_second_harvest_in_the_same_cycle_is_blocked():
    report = validate_operation(
        crop_id="pearl_millet",
        history=BASE + [{"operation_id": "harvest", "date": "2026-09-05"}],
        new_operation={"operation_id": "harvest", "date": "2026-09-10"},
    )
    assert report.blocked


@pytest.mark.parametrize(
    "value, outcome",
    [(0.0, "block"), (0.1, "warning"), (0.3, "pass"), (1.0, "pass"), (2.5, "pass"), (3.0, "warning"), (5.0, "block")],
)
def test_yield_bands(value, outcome):
    assert validate_yield("pearl_millet", value).severity == outcome
