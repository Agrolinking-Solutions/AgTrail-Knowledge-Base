"""
Tests for engine.validator.validate_operation.

These deliberately mirror the scenario files in scenarios/, so the CLI and
the test suite are checking the same behavior two different ways.
"""

import pytest

from engine.validator import validate_operation
from engine.exceptions import InvalidOperationDataError, CropNotFoundError


def test_valid_planting_passes_cleanly():
    report = validate_operation(
        crop_id="maize",
        region="Nigeria - Guinea Savanna",
        history=[
            {"operation_id": "land_clearing", "date": "2026-04-01"},
            {"operation_id": "land_preparation", "date": "2026-04-10"},
        ],
        new_operation={"operation_id": "planting", "date": "2026-04-15"},
    )
    assert not report.blocked
    assert not report.warnings


def test_harvest_before_minimum_days_is_blocked():
    report = validate_operation(
        crop_id="maize",
        history=[
            {"operation_id": "land_clearing", "date": "2026-01-01"},
            {"operation_id": "land_preparation", "date": "2026-01-05"},
            {"operation_id": "planting", "date": "2026-01-10"},
        ],
        new_operation={"operation_id": "harvest", "date": "2026-02-01"},
    )
    assert report.blocked
    assert any(i.rule_id == "maize_r8" for i in report.blocking_issues)


def test_missing_prerequisite_is_blocked():
    report = validate_operation(
        crop_id="maize",
        history=[],
        new_operation={"operation_id": "harvest", "date": "2026-06-01"},
    )
    assert report.blocked


def test_duplicate_harvest_on_annual_crop_is_blocked():
    report = validate_operation(
        crop_id="maize",
        history=[
            {"operation_id": "land_clearing", "date": "2026-01-01"},
            {"operation_id": "land_preparation", "date": "2026-01-05"},
            {"operation_id": "planting", "date": "2026-01-10"},
            {"operation_id": "harvest", "date": "2026-04-20"},
        ],
        new_operation={"operation_id": "harvest", "date": "2026-05-01"},
    )
    assert report.blocked
    assert any(i.rule_id == "maize_r9" for i in report.blocking_issues)


def test_backdated_operation_is_blocked():
    report = validate_operation(
        crop_id="maize",
        history=[
            {"operation_id": "land_clearing", "date": "2026-01-01"},
            {"operation_id": "land_preparation", "date": "2026-01-05"},
            {"operation_id": "planting", "date": "2026-01-20"},
        ],
        new_operation={"operation_id": "first_fertilizer", "date": "2026-01-15"},
    )
    assert report.blocked
    assert any(i.rule_id == "global-order" for i in report.blocking_issues)


def test_regional_override_changes_the_outcome():
    """
    Same crop, same dates. Only the region differs. Guinea savanna's window
    (28-35 days) should warn on a 25-day gap; Sudan savanna's window
    (21-28 days) should not.
    """
    history = [
        {"operation_id": "land_clearing", "date": "2026-04-01"},
        {"operation_id": "land_preparation", "date": "2026-04-10"},
        {"operation_id": "planting", "date": "2026-04-15"},
        {"operation_id": "first_fertilizer", "date": "2026-04-20"},
        {"operation_id": "weeding_1", "date": "2026-05-01"},
    ]
    new_operation = {"operation_id": "second_fertilizer", "date": "2026-05-10"}

    guinea = validate_operation("maize", new_operation, history, region="Nigeria - Guinea Savanna")
    sudan = validate_operation("maize", new_operation, history, region="Nigeria - Sudan Savanna")

    assert not guinea.blocked and guinea.warnings
    assert not sudan.blocked and not sudan.warnings


def test_cassava_harvest_has_no_hard_maximum():
    """
    The whole point of the cassava template: a harvest 485 days after planting
    is well past the typical window and should warn, but must NOT block,
    since cassava roots can stay viable in the ground well beyond a year.
    """
    report = validate_operation(
        crop_id="cassava",
        history=[
            {"operation_id": "land_clearing", "date": "2025-01-01"},
            {"operation_id": "land_preparation", "date": "2025-01-20"},
            {"operation_id": "planting", "date": "2025-02-01"},
        ],
        new_operation={"operation_id": "harvest", "date": "2026-06-01"},
    )
    assert not report.blocked
    assert any(i.rule_id == "cassava_r6b" for i in report.warnings)


def test_cassava_harvest_before_minimum_is_still_blocked():
    """
    No hard maximum doesn't mean no floor at all -- cassava harvested at
    30 days would be absurd and should still block.
    """
    report = validate_operation(
        crop_id="cassava",
        history=[
            {"operation_id": "land_clearing", "date": "2026-01-01"},
            {"operation_id": "land_preparation", "date": "2026-01-20"},
            {"operation_id": "planting", "date": "2026-02-01"},
        ],
        new_operation={"operation_id": "harvest", "date": "2026-03-03"},
    )
    assert report.blocked
    assert any(i.rule_id == "cassava_r6" for i in report.blocking_issues)


def test_cocoa_18_month_harvest_claim_is_blocked_despite_marketing_source():
    """
    One promotional source claims CRIN hybrids can bear pods in 18 months
    (547 days). That claim is not corroborated by any other source reviewed,
    so the block stays at the conservative 2 year (730 day) threshold. This
    test locks in that deliberate choice: it should block, with a warning
    explaining why, not silently pass because of the unconfirmed claim.
    """
    report = validate_operation(
        crop_id="cocoa",
        history=[
            {"operation_id": "land_clearing", "date": "2025-01-01"},
            {"operation_id": "nursery_establishment", "date": "2025-01-15"},
            {"operation_id": "transplanting", "date": "2025-06-01"},
        ],
        new_operation={"operation_id": "harvest", "date": "2026-11-30"},
    )
    assert report.blocked
    assert any(i.rule_id == "cocoa_r4" for i in report.blocking_issues)


def test_unknown_operation_id_is_blocked_not_silently_passed():
    """
    Previously, an operation_id that isn't a real operation for this crop
    matched no rules and passed with zero issues. That's a real gap: a typo
    or a client bug sending the wrong operation_id should never sail through
    clean.
    """
    report = validate_operation(
        crop_id="maize",
        history=[{"operation_id": "land_clearing", "date": "2026-01-01"}],
        new_operation={"operation_id": "this_is_not_a_real_operation", "date": "2026-01-05"},
    )
    assert report.blocked
    assert any(i.rule_id == "engine-unknown-operation" for i in report.blocking_issues)


def test_missing_date_field_raises_a_clear_error():
    with pytest.raises(InvalidOperationDataError):
        validate_operation(
            crop_id="maize",
            history=[],
            new_operation={"operation_id": "land_clearing"},
        )


def test_malformed_date_string_raises_a_clear_error():
    with pytest.raises(InvalidOperationDataError):
        validate_operation(
            crop_id="maize",
            history=[],
            new_operation={"operation_id": "land_clearing", "date": "01/05/2026"},
        )


def test_unrecognized_crop_id_raises_a_clear_error():
    with pytest.raises(CropNotFoundError):
        validate_operation(
            crop_id="durian",
            history=[],
            new_operation={"operation_id": "planting", "date": "2026-01-01"},
        )


def test_unrecognized_region_falls_back_to_base_rules():
    """
    An unrecognized region string should never crash or block anything on
    its own. It should just fall back to the base (non-regional) rules.
    """
    report = validate_operation(
        crop_id="maize",
        history=[
            {"operation_id": "land_clearing", "date": "2026-01-01"},
            {"operation_id": "land_preparation", "date": "2026-01-05"},
        ],
        new_operation={"operation_id": "planting", "date": "2026-01-08"},
        region="A Region That Does Not Exist",
    )
    assert not report.blocked


def test_mixed_crop_history_without_tags_is_genuinely_ambiguous():
    """
    This documents real, current behavior, not a bug: if a caller hands over
    combined history from a farm growing two crops without tagging which
    entry belongs to which crop, the engine cannot tell them apart and may
    pick the wrong dependency date. Here it wrongly uses the CASSAVA planting
    date (Mar 15) instead of the correct MAIZE planting date (Jan 10) when
    checking a maize harvest, which understates the true gap (111 days) as
    only 47 days and blocks a harvest that should have passed. This is why
    validate_operation's docstring requires crop_id tags (or pre-filtered
    history) once a farm grows more than one crop.
    """
    mixed_untagged = [
        {"operation_id": "land_clearing", "date": "2026-01-01"},
        {"operation_id": "land_preparation", "date": "2026-01-05"},
        {"operation_id": "planting", "date": "2026-01-10"},  # real maize planting
        {"operation_id": "land_clearing", "date": "2026-03-01"},
        {"operation_id": "land_preparation", "date": "2026-03-10"},
        {"operation_id": "planting", "date": "2026-03-15"},  # a different crop's planting
    ]
    report = validate_operation(
        crop_id="maize",
        history=mixed_untagged,
        new_operation={"operation_id": "harvest", "date": "2026-05-01"},
    )
    assert report.blocked  # documents the wrong-but-current outcome without crop_id tags


def test_mixed_crop_history_with_crop_id_tags_is_correctly_isolated():
    """
    The fix: tagging each history entry with crop_id lets the engine filter
    to just the operations that belong to the crop being validated. With the
    exact same underlying dates as the test above, tagging produces the
    correct result: the maize harvest is checked against the real maize
    planting date (Jan 10, 111 days prior) and passes cleanly.
    """
    mixed_tagged = [
        {"operation_id": "land_clearing", "date": "2026-01-01", "crop_id": "maize"},
        {"operation_id": "land_preparation", "date": "2026-01-05", "crop_id": "maize"},
        {"operation_id": "planting", "date": "2026-01-10", "crop_id": "maize"},
        {"operation_id": "land_clearing", "date": "2026-03-01", "crop_id": "cassava"},
        {"operation_id": "land_preparation", "date": "2026-03-10", "crop_id": "cassava"},
        {"operation_id": "planting", "date": "2026-03-15", "crop_id": "cassava"},
    ]
    report = validate_operation(
        crop_id="maize",
        history=mixed_tagged,
        new_operation={"operation_id": "harvest", "date": "2026-05-01", "crop_id": "maize"},
    )
    assert not report.blocked
    assert not report.warnings


def test_optional_operation_absent_from_history_does_not_wrongly_block():
    """
    Skipping an optional step (gap_filling) should never trigger a false
    missing-prerequisite block on a later required operation, since nothing
    actually depends on gap_filling.
    """
    report = validate_operation(
        crop_id="maize",
        history=[
            {"operation_id": "land_clearing", "date": "2026-01-01"},
            {"operation_id": "land_preparation", "date": "2026-01-05"},
            {"operation_id": "planting", "date": "2026-01-10"},
            # gap_filling deliberately never logged
            {"operation_id": "first_fertilizer", "date": "2026-01-15"},
        ],
        new_operation={"operation_id": "weeding_1", "date": "2026-01-25"},
    )
    assert not report.blocked


# --- Reported bug: land preparation, planting, and harvest could be logged
# in any order, including all on the same date, with nothing catching it.
# Root cause: each rule only checked an operation's relationship to its OWN
# declared dependency, never its position relative to everything ELSE
# already logged. Fixed with a workflow-order sanity check in validate_operation.

def test_reported_bug_land_prep_after_planting_and_harvest_same_date_is_now_blocked():
    """
    The exact scenario reported: land preparation, planting, and harvest all
    logged on the same date. Previously land_preparation logged AFTER
    planting and harvest already existed in history passed with zero
    issues. It must now block.
    """
    report = validate_operation(
        crop_id="maize",
        history=[
            {"operation_id": "land_clearing", "date": "2026-01-01"},
            {"operation_id": "planting", "date": "2026-01-01"},
            {"operation_id": "harvest", "date": "2026-01-01"},
        ],
        new_operation={"operation_id": "land_preparation", "date": "2026-01-01"},
    )
    assert report.blocked
    assert any(i.rule_id == "engine-workflow-order" for i in report.blocking_issues)


def test_reported_bug_planting_after_land_prep_and_harvest_same_date_is_now_blocked():
    """Same bug, different ordering: planting inserted after land_prep and harvest already exist."""
    report = validate_operation(
        crop_id="maize",
        history=[
            {"operation_id": "land_clearing", "date": "2026-01-01"},
            {"operation_id": "land_preparation", "date": "2026-01-01"},
            {"operation_id": "harvest", "date": "2026-01-01"},
        ],
        new_operation={"operation_id": "planting", "date": "2026-01-01"},
    )
    assert report.blocked
    assert any(i.rule_id == "engine-workflow-order" for i in report.blocking_issues)


def test_workflow_order_bug_generalizes_beyond_same_date():
    """
    The bug wasn't really about same-date submissions specifically, it was
    about missing position-in-workflow awareness entirely. Land prep logged
    after planting (a later step), even on a later date than planting
    itself, was never caught before either.
    """
    report = validate_operation(
        crop_id="maize",
        history=[
            {"operation_id": "land_clearing", "date": "2026-01-01"},
            {"operation_id": "planting", "date": "2026-01-10"},
        ],
        new_operation={"operation_id": "land_preparation", "date": "2026-01-15"},
    )
    assert report.blocked
    assert any(i.rule_id == "engine-workflow-order" for i in report.blocking_issues)


def test_workflow_order_check_allows_legitimate_new_season_restart():
    """
    The fix must NOT block a real new planting cycle. Logging land_clearing
    again after a prior harvest, dated after that harvest, is exactly how
    a farmer starts season two on an annual crop, and must still pass.
    """
    report = validate_operation(
        crop_id="maize",
        history=[
            {"operation_id": "land_clearing", "date": "2026-01-01"},
            {"operation_id": "land_preparation", "date": "2026-01-05"},
            {"operation_id": "planting", "date": "2026-01-10"},
            {"operation_id": "harvest", "date": "2026-05-01"},
        ],
        new_operation={"operation_id": "land_clearing", "date": "2026-06-01"},
    )
    assert not report.blocked
    assert not report.issues


def test_workflow_order_check_new_season_restart_same_date_as_harvest_is_not_trusted():
    """
    Edge case caught while building the fix: if the new operation is dated
    the SAME as the last harvest (not clearly after it), the new-season
    exception should NOT apply, since that's indistinguishable from the
    original bug rather than a believable season restart.
    """
    report = validate_operation(
        crop_id="maize",
        history=[
            {"operation_id": "land_clearing", "date": "2026-01-01"},
            {"operation_id": "planting", "date": "2026-01-01"},
            {"operation_id": "harvest", "date": "2026-01-01"},
        ],
        new_operation={"operation_id": "land_clearing", "date": "2026-01-01"},
    )
    assert report.blocked
    assert any(i.rule_id == "engine-workflow-order" for i in report.blocking_issues)


def test_workflow_order_check_does_not_interfere_with_repeatable_operations():
    """Repeatable operations (weeding, fertilizer rounds) must remain free to interleave flexibly."""
    report = validate_operation(
        crop_id="maize",
        history=[
            {"operation_id": "land_clearing", "date": "2026-01-01"},
            {"operation_id": "land_preparation", "date": "2026-01-05"},
            {"operation_id": "planting", "date": "2026-01-10"},
            {"operation_id": "first_fertilizer", "date": "2026-01-15"},
            {"operation_id": "second_fertilizer", "date": "2026-02-05"},
        ],
        new_operation={"operation_id": "weeding_1", "date": "2026-02-10"},
    )
    assert not report.blocked


def test_workflow_order_check_never_resets_for_perennial_crops():
    """
    Cocoa's harvest is repeatable (recurring seasonal harvest), so there is
    no legitimate "new cycle" concept in this model at all. land_clearing
    reappearing after ANY harvest should still block, unlike the annual
    crop case above.
    """
    report = validate_operation(
        crop_id="cocoa",
        history=[
            {"operation_id": "land_clearing", "date": "2024-01-01"},
            {"operation_id": "nursery_establishment", "date": "2024-01-05"},
            {"operation_id": "transplanting", "date": "2024-06-01"},
            {"operation_id": "harvest", "date": "2026-08-01"},
        ],
        new_operation={"operation_id": "land_clearing", "date": "2026-09-01"},
    )
    assert report.blocked
    assert any(i.rule_id == "engine-workflow-order" for i in report.blocking_issues)


def test_workflow_order_check_full_valid_sequence_passes_at_every_step():
    """
    Regression guard: a normal, correctly-ordered farm record, validated one
    step at a time as it's built up, must never trip the new check.
    """
    history = []
    steps = [
        {"operation_id": "land_clearing", "date": "2026-01-01"},
        {"operation_id": "land_preparation", "date": "2026-01-05"},
        {"operation_id": "planting", "date": "2026-01-10"},
        {"operation_id": "first_fertilizer", "date": "2026-01-15"},
        {"operation_id": "weeding_1", "date": "2026-01-25"},
        {"operation_id": "second_fertilizer", "date": "2026-02-10"},
        {"operation_id": "harvest", "date": "2026-05-01"},
        {"operation_id": "drying", "date": "2026-05-03"},
    ]
    for step in steps:
        report = validate_operation(crop_id="maize", history=history, new_operation=step)
        assert not report.blocked, f"Unexpected block at {step['operation_id']}: {report.blocking_issues}"
        history.append(step)


def test_tomato_harvest_can_genuinely_repeat():
    """
    Tomato was built specifically to test a shape none of the other three
    crops cover: a harvest operation that repeats many times within ONE
    planting cycle, not once (maize/cassava) and not across separate
    multi-year seasons (cocoa). A second harvest pick a week after the
    first should pass cleanly, with no once-only rule blocking it.
    """
    history = [
        {"operation_id": "land_clearing", "date": "2026-01-01"},
        {"operation_id": "land_preparation", "date": "2026-01-10"},
        {"operation_id": "nursery_establishment", "date": "2026-01-05"},
        {"operation_id": "transplanting", "date": "2026-02-01"},
        {"operation_id": "first_fertilizer", "date": "2026-02-05"},
        {"operation_id": "weeding_1", "date": "2026-02-15"},
        {"operation_id": "second_fertilizer", "date": "2026-03-05"},
        {"operation_id": "pest_disease_control", "date": "2026-02-10"},
        {"operation_id": "harvest", "date": "2026-04-05"},
    ]
    report = validate_operation(
        crop_id="tomato",
        history=history,
        new_operation={"operation_id": "harvest", "date": "2026-04-12"},
    )
    assert not report.blocked
    assert not report.issues


def test_tomato_harvest_too_early_is_blocked():
    history = [
        {"operation_id": "land_clearing", "date": "2026-01-01"},
        {"operation_id": "land_preparation", "date": "2026-01-10"},
        {"operation_id": "nursery_establishment", "date": "2026-01-05"},
        {"operation_id": "transplanting", "date": "2026-02-01"},
    ]
    report = validate_operation(
        crop_id="tomato",
        history=history,
        new_operation={"operation_id": "harvest", "date": "2026-03-01"},  # 28 days after transplanting
    )
    assert report.blocked
    assert any(i.rule_id == "tomato_r7" for i in report.blocking_issues)


def test_rice_harvest_in_typical_window_passes_cleanly():
    history = [
        {"operation_id": "land_clearing", "date": "2026-01-01"},
        {"operation_id": "land_preparation", "date": "2026-01-10"},
        {"operation_id": "nursery_establishment", "date": "2026-01-05"},
        {"operation_id": "first_fertilizer", "date": "2026-01-20"},
        {"operation_id": "transplanting", "date": "2026-01-26"},
    ]
    report = validate_operation(
        crop_id="rice",
        history=history,
        new_operation={"operation_id": "harvest", "date": "2026-05-06"},  # ~100 days after transplanting
    )
    assert not report.blocked
    assert not report.issues


def test_rice_harvest_too_early_is_blocked():
    history = [
        {"operation_id": "land_clearing", "date": "2026-01-01"},
        {"operation_id": "land_preparation", "date": "2026-01-10"},
        {"operation_id": "nursery_establishment", "date": "2026-01-05"},
        {"operation_id": "first_fertilizer", "date": "2026-01-20"},
        {"operation_id": "transplanting", "date": "2026-01-26"},
    ]
    report = validate_operation(
        crop_id="rice",
        history=history,
        new_operation={"operation_id": "harvest", "date": "2026-03-17"},  # ~50 days after transplanting
    )
    assert report.blocked
    assert any(i.rule_id == "rice_r8" for i in report.blocking_issues)


def test_rice_late_harvest_for_long_duration_variety_is_not_blocked():
    """
    Rice's harvest rule deliberately has no upper block, since long duration
    varieties genuinely take well over 140 days after transplanting. A
    harvest at ~150 days should pass, but still get flagged as outside the
    typical short/medium duration window as a warning, not a rejection.
    """
    history = [
        {"operation_id": "land_clearing", "date": "2026-01-01"},
        {"operation_id": "land_preparation", "date": "2026-01-10"},
        {"operation_id": "nursery_establishment", "date": "2026-01-05"},
        {"operation_id": "first_fertilizer", "date": "2026-01-20"},
        {"operation_id": "transplanting", "date": "2026-01-26"},
    ]
    report = validate_operation(
        crop_id="rice",
        history=history,
        new_operation={"operation_id": "harvest", "date": "2026-06-25"},  # ~150 days after transplanting
    )
    assert not report.blocked
    assert any(i.rule_id == "rice_r8b" for i in report.warnings)


# --- Corrections from the AgTrail Master Agronomist & Validator Ruleset (maize v1.3.0) ---

def test_maize_weeding_before_seven_days_is_now_blocked():
    """
    Previously weeding_1 had no lower bound at all. The master ruleset added
    a hard block under 7 days after planting -- there's nothing to weed yet.
    """
    history = [
        {"operation_id": "land_clearing", "date": "2026-01-01"},
        {"operation_id": "land_preparation", "date": "2026-01-05"},
        {"operation_id": "planting", "date": "2026-01-10"},
    ]
    report = validate_operation(
        crop_id="maize",
        history=history,
        new_operation={"operation_id": "weeding_1", "date": "2026-01-15"},  # 5 days after planting
    )
    assert report.blocked
    assert any(i.rule_id == "maize_r4_floor" for i in report.blocking_issues)


def test_maize_top_dress_after_sixty_days_is_now_blocked():
    """
    Previously second_fertilizer only had a warning-severity rule, so an
    absurdly late top-dress (e.g. 100 days after planting) passed with just
    a soft flag. The master ruleset added a real hard block at 60 days.
    """
    history = [
        {"operation_id": "land_clearing", "date": "2026-01-01"},
        {"operation_id": "land_preparation", "date": "2026-01-05"},
        {"operation_id": "planting", "date": "2026-01-10"},
    ]
    report = validate_operation(
        crop_id="maize",
        history=history,
        new_operation={"operation_id": "second_fertilizer", "date": "2026-04-20"},  # 100 days after planting
    )
    assert report.blocked
    assert any(i.rule_id == "maize_r5_floor" for i in report.blocking_issues)


def test_maize_pesticide_spray_after_tasseling_is_now_blocked():
    """
    New hard block: FAW-context pesticide application after tasseling
    (65 days after planting) is now rejected outright, previously there
    was no upper bound on pest_scouting timing at all.
    """
    history = [
        {"operation_id": "land_clearing", "date": "2026-01-01"},
        {"operation_id": "land_preparation", "date": "2026-01-05"},
        {"operation_id": "planting", "date": "2026-01-10"},
    ]
    report = validate_operation(
        crop_id="maize",
        history=history,
        new_operation={"operation_id": "pest_scouting", "date": "2026-03-21"},  # 70 days after planting
    )
    assert report.blocked
    assert any(i.rule_id == "maize_r7_floor" for i in report.blocking_issues)


def test_maize_fresh_cob_harvest_is_a_genuinely_separate_operation():
    """
    harvest_fresh (green/milk-to-dough cob) is a new operation added per the
    master ruleset, distinct from the existing dry-grain harvest. A fresh
    harvest at 70 days (inside the 65-75 day typical window) should pass
    cleanly, proving the two harvest types don't interfere with each other.
    """
    history = [
        {"operation_id": "land_clearing", "date": "2026-01-01"},
        {"operation_id": "land_preparation", "date": "2026-01-05"},
        {"operation_id": "planting", "date": "2026-01-10"},
    ]
    report = validate_operation(
        crop_id="maize",
        history=history,
        new_operation={"operation_id": "harvest_fresh", "date": "2026-03-21"},  # 70 days after planting
    )
    assert not report.blocked
    assert not report.issues


def test_maize_fresh_cob_harvest_before_sixty_days_is_blocked():
    history = [
        {"operation_id": "land_clearing", "date": "2026-01-01"},
        {"operation_id": "land_preparation", "date": "2026-01-05"},
        {"operation_id": "planting", "date": "2026-01-10"},
    ]
    report = validate_operation(
        crop_id="maize",
        history=history,
        new_operation={"operation_id": "harvest_fresh", "date": "2026-02-09"},  # 30 days after planting
    )
    assert report.blocked
    assert any(i.rule_id == "maize_r8_fresh" for i in report.blocking_issues)


# --- Corrections from the AgTrail Master Agronomist & Validator Ruleset (tomato v1.1.0) ---

def test_tomato_harvest_at_fifty_days_now_passes_cleanly():
    """
    Previously the harvest floor was 55 days (self-sourced), so a 50-day
    harvest would have blocked. The master ruleset corrects the floor to
    45 days with a 50-day typical-window start, so 50 days should now pass
    with zero issues, not block.
    """
    history = [
        {"operation_id": "land_clearing", "date": "2026-01-01"},
        {"operation_id": "land_preparation", "date": "2026-01-10"},
        {"operation_id": "nursery_establishment", "date": "2026-01-05"},
        {"operation_id": "transplanting", "date": "2026-02-01"},
    ]
    report = validate_operation(
        crop_id="tomato",
        history=history,
        new_operation={"operation_id": "harvest", "date": "2026-03-23"},  # 50 days after transplanting
    )
    assert not report.blocked
    assert not report.issues


def test_tomato_staking_after_thirty_days_is_flagged():
    """New rule: staking logged after 30 days after transplanting is a warning."""
    history = [
        {"operation_id": "land_clearing", "date": "2026-01-01"},
        {"operation_id": "land_preparation", "date": "2026-01-10"},
        {"operation_id": "nursery_establishment", "date": "2026-01-05"},
        {"operation_id": "transplanting", "date": "2026-02-01"},
    ]
    report = validate_operation(
        crop_id="tomato",
        history=history,
        new_operation={"operation_id": "staking", "date": "2026-03-13"},  # 40 days after transplanting
    )
    assert not report.blocked
    assert any(i.rule_id == "tomato_r4b" for i in report.warnings)


def test_tomato_post_harvest_handling_beyond_72_hours_is_blocked():
    """
    New rule: aggregating harvested fruit more than 72 hours after the most
    recent harvest pick is a hard block. Checked against the MOST RECENT
    harvest occurrence, which is the correct behavior since harvest repeats.
    """
    history = [
        {"operation_id": "land_clearing", "date": "2026-01-01"},
        {"operation_id": "land_preparation", "date": "2026-01-10"},
        {"operation_id": "nursery_establishment", "date": "2026-01-05"},
        {"operation_id": "transplanting", "date": "2026-02-01"},
        {"operation_id": "harvest", "date": "2026-04-05"},
    ]
    report = validate_operation(
        crop_id="tomato",
        history=history,
        new_operation={"operation_id": "post_harvest_handling", "date": "2026-04-09"},  # 4 days later
    )
    assert report.blocked
    assert any(i.rule_id == "tomato_r_postharvest_block" for i in report.blocking_issues)


# --- Sesame: first crop built directly from the AgTrail Master Agronomist & Validator Ruleset ---

def test_sesame_harvest_too_early_is_blocked():
    history = [
        {"operation_id": "land_clearing", "date": "2026-01-01"},
        {"operation_id": "land_preparation", "date": "2026-01-10"},
        {"operation_id": "planting", "date": "2026-01-15"},
    ]
    report = validate_operation(
        crop_id="sesame",
        history=history,
        new_operation={"operation_id": "harvest", "date": "2026-03-16"},  # 60 days after planting
    )
    assert report.blocked
    assert any(i.rule_id == "sesame_r5" for i in report.blocking_issues)


def test_sesame_harvest_in_typical_window_passes_cleanly():
    history = [
        {"operation_id": "land_clearing", "date": "2026-01-01"},
        {"operation_id": "land_preparation", "date": "2026-01-10"},
        {"operation_id": "planting", "date": "2026-01-15"},
    ]
    report = validate_operation(
        crop_id="sesame",
        history=history,
        new_operation={"operation_id": "harvest", "date": "2026-04-25"},  # 100 days after planting
    )
    assert not report.blocked
    assert not report.issues


def test_sesame_fertilizer_after_forty_five_days_is_blocked():
    history = [
        {"operation_id": "land_clearing", "date": "2026-01-01"},
        {"operation_id": "land_preparation", "date": "2026-01-10"},
        {"operation_id": "planting", "date": "2026-01-15"},
    ]
    report = validate_operation(
        crop_id="sesame",
        history=history,
        new_operation={"operation_id": "first_fertilizer", "date": "2026-03-06"},  # 50 days after planting
    )
    assert report.blocked
    assert any(i.rule_id == "sesame_r4_floor" for i in report.blocking_issues)


# --- Ginger: third crop built from the AgTrail Master Agronomist & Validator Ruleset ---

def test_ginger_harvest_too_early_is_blocked():
    history = [
        {"operation_id": "land_clearing", "date": "2026-01-01"},
        {"operation_id": "land_preparation", "date": "2026-01-10"},
        {"operation_id": "planting", "date": "2026-01-15"},
    ]
    report = validate_operation(
        crop_id="ginger",
        history=history,
        new_operation={"operation_id": "harvest", "date": "2026-06-14"},  # 150 days after planting
    )
    assert report.blocked
    assert any(i.rule_id == "ginger_r4" for i in report.blocking_issues)


def test_ginger_harvest_in_typical_window_passes_cleanly():
    history = [
        {"operation_id": "land_clearing", "date": "2026-01-01"},
        {"operation_id": "land_preparation", "date": "2026-01-10"},
        {"operation_id": "planting", "date": "2026-01-15"},
    ]
    report = validate_operation(
        crop_id="ginger",
        history=history,
        new_operation={"operation_id": "harvest", "date": "2026-09-12"},  # 240 days after planting
    )
    assert not report.blocked
    assert not report.issues


def test_ginger_drying_without_splitting_is_blocked():
    """
    Ginger introduces a genuinely new pattern: a hard block enforced not by
    a timing window but by a missing prerequisite operation entirely.
    Drying (logging 'Dry Split Ginger') without a prior splitting step is
    rejected outright, and this works for free through the existing
    missing-prerequisite check, no new engine code was needed for it.
    """
    history = [
        {"operation_id": "land_clearing", "date": "2026-01-01"},
        {"operation_id": "land_preparation", "date": "2026-01-10"},
        {"operation_id": "planting", "date": "2026-01-15"},
        {"operation_id": "harvest", "date": "2026-09-12"},
    ]
    report = validate_operation(
        crop_id="ginger",
        history=history,
        new_operation={"operation_id": "drying", "date": "2026-09-15"},  # no splitting logged
    )
    assert report.blocked
    assert any(i.rule_id == "ginger_r5" for i in report.blocking_issues)


def test_ginger_drying_after_splitting_passes_cleanly():
    history = [
        {"operation_id": "land_clearing", "date": "2026-01-01"},
        {"operation_id": "land_preparation", "date": "2026-01-10"},
        {"operation_id": "planting", "date": "2026-01-15"},
        {"operation_id": "harvest", "date": "2026-09-12"},
        {"operation_id": "splitting", "date": "2026-09-13"},
    ]
    report = validate_operation(
        crop_id="ginger",
        history=history,
        new_operation={"operation_id": "drying", "date": "2026-09-15"},
    )
    assert not report.blocked
    assert not report.issues


# --- Cashew: fourth crop built from the AgTrail Master Agronomist & Validator Ruleset ---

def test_cashew_first_harvest_before_two_point_five_years_is_blocked():
    history = [
        {"operation_id": "land_clearing", "date": "2024-01-01"},
        {"operation_id": "nursery_establishment", "date": "2024-01-05"},
        {"operation_id": "land_preparation", "date": "2024-03-01"},
        {"operation_id": "transplanting", "date": "2024-04-01"},
    ]
    report = validate_operation(
        crop_id="cashew",
        history=history,
        new_operation={"operation_id": "harvest", "date": "2026-06-10"},  # ~800 days after transplanting
    )
    assert report.blocked
    assert any(i.rule_id == "cashew_r3" for i in report.blocking_issues)


def test_cashew_harvest_past_three_years_passes_cleanly():
    history = [
        {"operation_id": "land_clearing", "date": "2024-01-01"},
        {"operation_id": "nursery_establishment", "date": "2024-01-05"},
        {"operation_id": "land_preparation", "date": "2024-03-01"},
        {"operation_id": "transplanting", "date": "2024-04-01"},
    ]
    report = validate_operation(
        crop_id="cashew",
        history=history,
        new_operation={"operation_id": "harvest", "date": "2027-07-14"},  # ~1200 days after transplanting
    )
    assert not report.blocked
    assert not report.issues


# --- Hibiscus: fifth crop built from the AgTrail Master Agronomist & Validator Ruleset ---

def test_hibiscus_harvest_too_early_is_blocked():
    history = [
        {"operation_id": "land_clearing", "date": "2026-01-01"},
        {"operation_id": "land_preparation", "date": "2026-01-10"},
        {"operation_id": "planting", "date": "2026-01-15"},
    ]
    report = validate_operation(
        crop_id="hibiscus",
        history=history,
        new_operation={"operation_id": "harvest", "date": "2026-03-16"},  # 60 days after planting
    )
    assert report.blocked
    assert any(i.rule_id == "hibiscus_r4" for i in report.blocking_issues)


def test_hibiscus_harvest_in_typical_window_passes_cleanly():
    history = [
        {"operation_id": "land_clearing", "date": "2026-01-01"},
        {"operation_id": "land_preparation", "date": "2026-01-10"},
        {"operation_id": "planting", "date": "2026-01-15"},
    ]
    report = validate_operation(
        crop_id="hibiscus",
        history=history,
        new_operation={"operation_id": "harvest", "date": "2026-05-15"},  # 120 days after planting
    )
    assert not report.blocked
    assert not report.issues


def test_hibiscus_storage_without_drying_is_blocked():
    """Same missing-prerequisite pattern as Ginger's splitting-before-drying rule."""
    history = [
        {"operation_id": "land_clearing", "date": "2026-01-01"},
        {"operation_id": "land_preparation", "date": "2026-01-10"},
        {"operation_id": "planting", "date": "2026-01-15"},
        {"operation_id": "harvest", "date": "2026-05-15"},
    ]
    report = validate_operation(
        crop_id="hibiscus",
        history=history,
        new_operation={"operation_id": "storage", "date": "2026-05-20"},  # no drying logged
    )
    assert report.blocked
    assert any(i.rule_id == "hibiscus_r5" for i in report.blocking_issues)