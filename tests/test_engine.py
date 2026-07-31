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
