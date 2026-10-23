"""
Vitamin A cassava rules, from the AgTrail Master Agronomist & Validator Ruleset
(sections 5 and 22): first weeding by 3-4 weeks, NPK at 4-8 weeks (blocked outside
21-90 days), harvest 270-450 days flagged and blocked outside 180-730, processing
within 2 days of harvest (blocked after 4), with an optional certified-stem-source step.
"""

from datetime import date, timedelta

import pytest

from engine.validator import validate_operation
from engine.yield_validator import validate_yield

PLANTED = date(2026, 6, 15)
BASE = [
    {"operation_id": "land_clearing", "date": "2026-06-01"},
    {"operation_id": "land_preparation", "date": "2026-06-08"},
    {"operation_id": "planting_material_sourcing", "date": "2026-06-10"},
    {"operation_id": "planting", "date": PLANTED.isoformat()},
]


def _check(operation_id, days_after_planting, extra_history=()):
    return validate_operation(
        crop_id="vitamin_a_cassava",
        history=BASE + list(extra_history),
        new_operation={"operation_id": operation_id, "date": (PLANTED + timedelta(days=days_after_planting)).isoformat()},
    )


def _ids(issues):
    return {i.rule_id for i in issues}


def test_planting_with_a_recorded_stem_source_is_clean():
    report = validate_operation(
        crop_id="vitamin_a_cassava",
        history=BASE[:3],
        new_operation={"operation_id": "planting", "date": PLANTED.isoformat()},
    )
    assert not report.blocked and not report.warnings


@pytest.mark.parametrize("day", [21, 25, 28])
def test_first_weeding_inside_the_window_is_clean(day):
    report = _check("weeding_1", day)
    assert not report.blocked and not report.warnings


@pytest.mark.parametrize("day", [14, 35])
def test_first_weeding_outside_the_window_is_flagged_not_blocked(day):
    report = _check("weeding_1", day)
    assert not report.blocked
    assert "vitamin_a_cassava_r3" in _ids(report.warnings)


def test_first_weeding_before_14_days_is_blocked():
    report = _check("weeding_1", 10)
    assert report.blocked
    assert "vitamin_a_cassava_r3_floor" in _ids(report.blocking_issues)


@pytest.mark.parametrize("day", [28, 42, 56])
def test_npk_inside_the_window_is_clean(day):
    report = _check("fertilizer_application", day)
    assert not report.blocked and not report.warnings


@pytest.mark.parametrize("day", [21, 70, 90])
def test_npk_outside_the_ideal_window_is_flagged_not_blocked(day):
    report = _check("fertilizer_application", day)
    assert not report.blocked
    assert "vitamin_a_cassava_r4" in _ids(report.warnings)


@pytest.mark.parametrize("day", [20, 91, 120])
def test_npk_outside_21_to_90_days_is_blocked(day):
    report = _check("fertilizer_application", day)
    assert report.blocked
    assert "vitamin_a_cassava_r4_floor" in _ids(report.blocking_issues)


@pytest.mark.parametrize("day", [270, 365, 450])
def test_harvest_inside_the_window_is_clean(day):
    report = _check("harvest", day)
    assert not report.blocked and not report.warnings


@pytest.mark.parametrize("day", [180, 200, 500, 730])
def test_harvest_outside_the_window_is_flagged_not_blocked(day):
    report = _check("harvest", day)
    assert not report.blocked
    assert "vitamin_a_cassava_r6b" in _ids(report.warnings)


@pytest.mark.parametrize("day", [120, 731])
def test_harvest_outside_180_to_730_days_is_blocked(day):
    report = _check("harvest", day)
    assert report.blocked
    assert "vitamin_a_cassava_r6" in _ids(report.blocking_issues)


def test_harvest_can_repeat_in_one_cycle():
    report = _check("harvest", 330, [{"operation_id": "harvest", "date": (PLANTED + timedelta(days=300)).isoformat()}])
    assert not report.blocked


@pytest.mark.parametrize("gap, outcome", [(1, "clean"), (2, "clean"), (3, "warning"), (4, "warning"), (5, "blocked")])
def test_processing_after_harvest(gap, outcome):
    harvest = {"operation_id": "harvest", "date": (PLANTED + timedelta(days=300)).isoformat()}
    report = _check("processing", 300 + gap, [harvest])
    if outcome == "clean":
        assert not report.blocked and not report.warnings
    elif outcome == "warning":
        assert not report.blocked and "vitamin_a_cassava_r8" in _ids(report.warnings)
    else:
        assert report.blocked and "vitamin_a_cassava_r8_ceiling" in _ids(report.blocking_issues)


@pytest.mark.parametrize(
    "value, outcome",
    [(0.0, "block"), (3.0, "warning"), (5.0, "pass"), (30.0, "pass"), (35.0, "warning"), (60.0, "block")],
)
def test_yield_bands(value, outcome):
    assert validate_yield("vitamin_a_cassava", value).severity == outcome
