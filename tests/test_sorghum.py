"""
Sorghum rules, from the AgTrail Master Agronomist & Validator Ruleset (section 3):
first weeding flagged outside 14-30 days and blocked after 60, urea top-dress
flagged outside 21-45 and blocked before 14 or after 65, harvest blocked before 85
days and flagged before 100 or after 150, and the yield bands.
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


def _check(operation_id, days_after_planting, extra_history=()):
    return validate_operation(
        crop_id="sorghum",
        history=BASE + list(extra_history),
        new_operation={
            "operation_id": operation_id,
            "date": (PLANTED + timedelta(days=days_after_planting)).isoformat(),
        },
    )


def _ids(issues):
    return {i.rule_id for i in issues}


@pytest.mark.parametrize("day", [14, 20, 30])
def test_first_weeding_inside_the_window_is_clean(day):
    report = _check("weeding_1", day)
    assert not report.blocked and not report.warnings


@pytest.mark.parametrize("day", [10, 31, 45, 60])
def test_first_weeding_outside_the_window_is_flagged_not_blocked(day):
    report = _check("weeding_1", day)
    assert not report.blocked
    assert "sorghum_r4" in _ids(report.warnings)


def test_first_weeding_after_60_days_is_blocked():
    report = _check("weeding_1", 61)
    assert report.blocked
    assert "sorghum_r4_ceiling" in _ids(report.blocking_issues)


@pytest.mark.parametrize("day", [21, 30, 45])
def test_topdress_inside_the_window_is_clean(day):
    report = _check("second_fertilizer", day, [{"operation_id": "weeding_1", "date": "2026-07-05"}])
    assert not report.blocked and not report.warnings


@pytest.mark.parametrize("day", [14, 18, 50, 65])
def test_topdress_just_outside_the_window_is_flagged(day):
    report = _check("second_fertilizer", day, [{"operation_id": "weeding_1", "date": "2026-06-29"}] if day > 14 else [])
    assert not report.blocked
    assert "sorghum_r5" in _ids(report.warnings)


@pytest.mark.parametrize("day", [13, 66, 80])
def test_topdress_far_outside_the_window_is_blocked(day):
    report = _check("second_fertilizer", day)
    assert report.blocked
    assert "sorghum_r5_floor" in _ids(report.blocking_issues)


def test_harvest_before_85_days_is_blocked():
    report = _check("harvest", 84)
    assert report.blocked
    assert "sorghum_r8" in _ids(report.blocking_issues)


@pytest.mark.parametrize("day", [85, 99, 151, 170])
def test_harvest_outside_the_typical_window_is_flagged(day):
    report = _check("harvest", day)
    assert not report.blocked
    assert "sorghum_r8b" in _ids(report.warnings)


@pytest.mark.parametrize("day", [100, 120, 150])
def test_harvest_inside_the_typical_window_is_clean(day):
    report = _check("harvest", day)
    assert not report.blocked and not report.warnings


def test_a_second_harvest_is_blocked():
    report = _check("harvest", 120, [{"operation_id": "harvest", "date": (PLANTED + timedelta(days=110)).isoformat()}])
    assert report.blocked
    assert "sorghum_r9" in _ids(report.blocking_issues)


def test_backdating_is_blocked():
    report = validate_operation(
        crop_id="sorghum",
        history=BASE,
        new_operation={"operation_id": "weeding_1", "date": "2026-06-10"},
    )
    assert report.blocked


@pytest.mark.parametrize(
    "tonnes, severity",
    [(0.0, "block"), (0.3, "warning"), (0.5, "pass"), (1.5, "pass"), (2.8, "pass"),
     (3.5, "warning"), (7.0, "block")],
)
def test_yield_bands_follow_the_ruleset(tonnes, severity):
    assert validate_yield("sorghum", tonnes).severity == severity


def test_a_zero_yield_is_a_loss_event():
    assert validate_yield("sorghum", 0.0).is_loss_event
