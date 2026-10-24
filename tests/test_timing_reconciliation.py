"""
Timing limits brought in line with the AgTrail Master Agronomist & Validator Ruleset for
cassava, sweet potato, cowpea, cocoa, cotton and vitamin A maize. Each limit is tested
just inside and just outside its edge. Days are counted from the day planting (or
transplanting) was logged.
"""

from datetime import date, timedelta

import pytest

from engine.validator import validate_operation

BASE = date(2026, 3, 1)


def at(days: int) -> str:
    return (BASE + timedelta(days=days)).isoformat()


def check(crop, history, operation, day):
    """history: [(operation_id, day)], operation: operation_id logged on `day`."""
    return validate_operation(
        crop_id=crop,
        history=[{"operation_id": op, "date": at(d)} for op, d in history],
        new_operation={"operation_id": operation, "date": at(day)},
    )


def verdict(report):
    return "blocked" if report.blocked else ("warning" if report.warnings else "clean")


CASSAVA = [("land_clearing", -20), ("land_preparation", -10), ("planting", 0)]
OFSP = [("land_clearing", -20), ("land_preparation", -10), ("vine_sourcing", -3), ("planting", 0)]
COWPEA = [("land_clearing", -20), ("land_preparation", -10), ("planting", 0)]
COCOA = [("land_clearing", -400), ("nursery_establishment", -300), ("transplanting", 0)]


# ---------------- cassava (section 5) ----------------

@pytest.mark.parametrize("gap, expected", [(10, "clean"), (45, "clean"), (46, "warning"), (60, "warning")])
def test_cassava_planting_is_flagged_not_blocked_beyond_45_days_after_land_prep(gap, expected):
    history = [("land_clearing", -70), ("land_preparation", -60)]
    assert verdict(check("cassava", history, "planting", -60 + gap)) == expected


@pytest.mark.parametrize("day, expected", [(13, "blocked"), (14, "warning"), (21, "clean"), (28, "clean"), (35, "warning")])
def test_cassava_first_weeding(day, expected):
    assert verdict(check("cassava", CASSAVA, "weeding_1", day)) == expected


@pytest.mark.parametrize("day, expected", [(20, "blocked"), (21, "warning"), (28, "clean"), (56, "clean"), (70, "warning"), (91, "blocked")])
def test_cassava_fertilizer(day, expected):
    assert verdict(check("cassava", CASSAVA, "fertilizer_application", day)) == expected


@pytest.mark.parametrize("after, expected", [(1, "clean"), (2, "clean"), (3, "warning"), (4, "warning"), (5, "blocked")])
def test_cassava_processing_after_harvest(after, expected):
    history = CASSAVA + [("harvest", 300)]
    assert verdict(check("cassava", history, "processing", 300 + after)) == expected


def test_the_cassava_harvest_rule_is_left_for_the_ceo():
    # Block before 240 days with no maximum is unchanged, see docs/RULESET_RECONCILIATION.md.
    assert verdict(check("cassava", CASSAVA, "harvest", 239)) == "blocked"
    assert verdict(check("cassava", CASSAVA, "harvest", 900)) == "warning"


# ---------------- sweet potato (section 7) ----------------

@pytest.mark.parametrize("day, expected", [(10, "warning"), (30, "clean"), (45, "clean"), (50, "warning"), (60, "warning"), (61, "blocked")])
def test_ofsp_weeding(day, expected):
    assert verdict(check("ofsp", OFSP, "weeding_1", day)) == expected


@pytest.mark.parametrize("day, expected", [(45, "clean"), (50, "warning"), (60, "warning"), (61, "blocked")])
def test_ofsp_earthing_up(day, expected):
    history = OFSP + [("weeding_1", 21)]
    assert verdict(check("ofsp", history, "reridging", day)) == expected


@pytest.mark.parametrize("day, expected", [(74, "blocked"), (80, "warning"), (84, "warning"), (85, "clean"), (130, "clean"), (131, "warning"), (200, "warning")])
def test_ofsp_harvest_is_blocked_only_before_75_days_and_flagged_outside_85_to_130(day, expected):
    assert verdict(check("ofsp", OFSP, "harvest", day)) == expected


# ---------------- cowpea (section 9) ----------------

@pytest.mark.parametrize("day, expected", [(59, "blocked"), (60, "warning"), (69, "warning"), (70, "clean"), (100, "clean"), (101, "warning"), (150, "warning")])
def test_cowpea_harvest(day, expected):
    assert verdict(check("cowpea", COWPEA, "harvest", day)) == expected


@pytest.mark.parametrize("day, expected", [(20, "blocked"), (21, "warning"), (29, "warning"), (30, "clean"), (60, "clean"), (61, "warning")])
def test_cowpea_insecticide(day, expected):
    assert verdict(check("cowpea", COWPEA, "pest_disease_control", day)) == expected


def test_cowpea_scouting_has_no_early_limit():
    assert verdict(check("cowpea", COWPEA, "pest_scouting", 5)) == "clean"


def test_cowpea_storage_needs_a_drying_step_and_is_flagged_after_7_days():
    history = COWPEA + [("harvest", 80)]
    missing = check("cowpea", history, "storage", 82)
    assert missing.blocked and any("drying_threshing" in i.message for i in missing.blocking_issues)
    late = check("cowpea", history + [("drying_threshing", 81)], "storage", 89)
    assert not late.blocked and any(i.rule_id == "cowpea_r_storage_after_drying" for i in late.warnings)


# ---------------- cocoa (section 15) ----------------

@pytest.mark.parametrize("nursery_days, expected", [(89, "blocked"), (90, "warning"), (99, "warning"), (100, "clean"), (150, "clean"), (151, "warning"), (180, "warning"), (181, "blocked")])
def test_cocoa_nursery_period(nursery_days, expected):
    history = [("land_clearing", -400), ("nursery_establishment", -nursery_days)]
    assert verdict(check("cocoa", history, "transplanting", 0)) == expected


@pytest.mark.parametrize("day, expected", [(539, "blocked"), (540, "warning"), (729, "warning"), (730, "clean"), (2000, "clean")])
def test_cocoa_first_harvest(day, expected):
    assert verdict(check("cocoa", COCOA, "harvest", day)) == expected


@pytest.mark.parametrize("days, expected", [(2, "blocked"), (3, "warning"), (4, "clean"), (7, "clean"), (8, "clean"), (9, "warning"), (10, "warning"), (11, "blocked")])
def test_cocoa_fermentation_length(days, expected):
    history = COCOA + [("harvest", 800), ("fermentation", 801)]
    assert verdict(check("cocoa", history, "drying", 801 + days)) == expected


# ---------------- cotton (section 20) ----------------

@pytest.mark.parametrize("day, expected", [(14, "clean"), (21, "clean"), (22, "warning"), (40, "warning")])
def test_cotton_thinning(day, expected):
    history = [("land_preparation", -10), ("planting", 0)]
    assert verdict(check("cotton", history, "thinning", day)) == expected


# ---------------- vitamin A maize (section 23: same timing as maize) ----------------

VA = [("land_clearing", -50), ("land_preparation", -40), ("planting", 0)]


def test_vitamin_a_maize_planting_long_after_land_prep_is_flagged_not_blocked_like_maize():
    history = [("land_clearing", -80), ("land_preparation", -70)]
    assert verdict(check("vitamin_a_maize", history, "planting", -30)) == "warning"
    assert verdict(check("maize", history, "planting", -30)) == "warning"


@pytest.mark.parametrize("operation, history_extra, day", [
    ("first_fertilizer", [], 20), ("weeding_1", [("first_fertilizer", 3)], 10), ("weeding_1", [("first_fertilizer", 3)], 30),
    ("second_fertilizer", [("first_fertilizer", 3), ("weeding_1", 16)], 12), ("second_fertilizer", [("first_fertilizer", 3), ("weeding_1", 16)], 70),
    ("harvest", [], 70), ("harvest", [], 85), ("harvest", [], 170),
])
def test_vitamin_a_maize_gives_the_same_verdict_as_maize(operation, history_extra, day):
    base = [("land_clearing", -50), ("land_preparation", -40), ("planting", 0)] + history_extra
    assert verdict(check("vitamin_a_maize", base, operation, day)) == verdict(check("maize", base, operation, day))


def test_vitamin_a_maize_drying_is_flagged_after_10_days_like_maize():
    history = VA + [("harvest", 110)]
    assert verdict(check("vitamin_a_maize", history, "drying", 118)) == "clean"
    assert verdict(check("vitamin_a_maize", history, "drying", 121)) == "warning"
