"""
Yield limits taken from the AgTrail Master Agronomist & Validator Ruleset for the crops
whose files had none (rice, cassava, cocoa) or different ones (sweet potato, cowpea).
"""

import pytest

from engine.yield_validator import validate_yield

CASES = {
    "rice": [(0.0, "block"), (0.5, "warning"), (1.0, "pass"), (6.0, "pass"), (8.0, "pass"), (9.0, "warning"), (12.5, "block")],
    "cassava": [(0.0, "block"), (3.0, "warning"), (5.0, "pass"), (30.0, "pass"), (40.0, "warning"), (55.0, "block")],
    "cocoa": [(0.0, "block"), (0.05, "warning"), (0.1, "pass"), (1.5, "pass"), (2.0, "warning"), (4.0, "block")],
    "ofsp": [(0.0, "block"), (3.0, "warning"), (4.0, "pass"), (18.0, "pass"), (25.0, "pass"), (30.0, "warning"), (41.0, "block")],
    "cowpea": [(0.0, "block"), (0.2, "warning"), (0.3, "pass"), (1.5, "pass"), (2.0, "pass"), (2.5, "warning"), (4.0, "block")],
}


@pytest.mark.parametrize("crop, tonnes, severity", [(c, t, s) for c, rows in CASES.items() for t, s in rows])
def test_yield_bands(crop, tonnes, severity):
    assert validate_yield(crop, tonnes).severity == severity


@pytest.mark.parametrize("crop", list(CASES))
def test_a_zero_yield_is_a_loss_event(crop):
    assert validate_yield(crop, 0.0).is_loss_event


def test_every_crop_file_has_yield_limits():
    from engine.loader import list_crops

    assert [crop for crop in list_crops() if validate_yield(crop, 0.0).severity != "block"] == []
