"""
Soybean rules, from IITA's Farmers' Guide to Soybean Production in Northern Nigeria
(2009): weeding at about 2 and 5-6 weeks, maturity in 3-4 months, 2 weeks of drying
before threshing. Every timing rule here is a warning, never a block, because the
guide states no hard limits and none have been invented.
"""

from datetime import date, timedelta

import pytest

from engine.validator import validate_operation
from engine.yield_validator import validate_yield

PLANTED = date(2026, 6, 20)
BASE = [
    {"operation_id": "land_clearing", "date": "2026-06-01"},
    {"operation_id": "land_preparation", "date": "2026-06-08"},
    {"operation_id": "planting", "date": PLANTED.isoformat()},
]


def _check(operation_id, days_after_planting, extra=()):
    return validate_operation(
        crop_id="soybean",
        history=BASE + list(extra),
        new_operation={"operation_id": operation_id,
                       "date": (PLANTED + timedelta(days=days_after_planting)).isoformat()},
    )


def _ids(issues):
    return {i.rule_id for i in issues}


@pytest.mark.parametrize("day", [7, 14, 21])
def test_first_weeding_around_two_weeks_is_clean(day):
    report = _check("weeding_1", day)
    assert not report.blocked and not report.warnings


@pytest.mark.parametrize("day", [3, 30, 60])
def test_a_late_or_very_early_first_weeding_is_flagged_never_blocked(day):
    report = _check("weeding_1", day)
    assert not report.blocked
    assert "soybean_r4" in _ids(report.warnings)


@pytest.mark.parametrize("day", [35, 40, 42])
def test_second_weeding_at_five_to_six_weeks_is_clean(day):
    report = _check("weeding_2", day, [{"operation_id": "weeding_1", "date": "2026-07-04"}])
    assert not report.blocked and not report.warnings


@pytest.mark.parametrize("day", [28, 50])
def test_second_weeding_outside_five_to_six_weeks_is_flagged(day):
    report = _check("weeding_2", day, [{"operation_id": "weeding_1", "date": "2026-07-04"}])
    assert not report.blocked
    assert "soybean_r5" in _ids(report.warnings)


@pytest.mark.parametrize("day", [90, 105, 120])
def test_harvest_in_three_to_four_months_is_clean(day):
    report = _check("harvest", day)
    assert not report.blocked and not report.warnings


@pytest.mark.parametrize("day", [60, 89, 121, 160])
def test_harvest_outside_three_to_four_months_is_flagged_not_blocked(day):
    report = _check("harvest", day)
    assert not report.blocked
    assert "soybean_r8" in _ids(report.warnings)


def test_threshing_before_two_weeks_of_drying_is_flagged():
    harvest = {"operation_id": "harvest", "date": (PLANTED + timedelta(days=100)).isoformat()}
    early = validate_operation(
        crop_id="soybean", history=BASE + [harvest],
        new_operation={"operation_id": "drying_threshing", "date": (PLANTED + timedelta(days=105)).isoformat()},
    )
    assert not early.blocked and "soybean_r10" in _ids(early.warnings)
    on_time = validate_operation(
        crop_id="soybean", history=BASE + [harvest],
        new_operation={"operation_id": "drying_threshing", "date": (PLANTED + timedelta(days=114)).isoformat()},
    )
    assert not on_time.blocked and not on_time.warnings


def test_a_second_harvest_is_blocked():
    harvest = {"operation_id": "harvest", "date": (PLANTED + timedelta(days=100)).isoformat()}
    report = _check("harvest", 110, [harvest])
    assert report.blocked and "soybean_r9" in _ids(report.blocking_issues)


def test_backdating_is_blocked():
    report = validate_operation(crop_id="soybean", history=BASE,
                                new_operation={"operation_id": "weeding_1", "date": "2026-06-10"})
    assert report.blocked


@pytest.mark.parametrize("tonnes, severity",
    [(0.0, "block"), (0.5, "warning"), (0.7, "pass"), (1.2, "pass"), (2.8, "pass"), (3.5, "warning")])
def test_yield_bands(tonnes, severity):
    assert validate_yield("soybean", tonnes).severity == severity


def test_an_absurd_yield_is_at_least_warned_even_though_no_hard_ceiling_exists_yet():
    # No source gives a biological maximum, so none was invented. A very large
    # number still gets flagged for manual review.
    assert validate_yield("soybean", 40.0).severity == "warning"


def test_a_zero_yield_is_a_loss_event():
    assert validate_yield("soybean", 0.0).is_loss_event
