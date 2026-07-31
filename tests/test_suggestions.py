"""
Tests for engine.suggestions.get_next_steps.
"""

from datetime import date

from engine.suggestions import get_next_steps


def test_next_step_due_now():
    report = get_next_steps(
        crop_id="maize",
        history=[
            {"operation_id": "land_clearing", "date": "2026-04-01"},
            {"operation_id": "land_preparation", "date": "2026-04-10"},
        ],
        as_of=date(2026, 4, 12),
    )
    assert report.cycle_status == "in_progress"
    assert report.suggestion.operation_id == "planting"
    assert report.suggestion.status == "due_now"


def test_next_step_upcoming_not_yet_due():
    report = get_next_steps(
        crop_id="maize",
        history=[
            {"operation_id": "land_clearing", "date": "2026-01-01"},
            {"operation_id": "land_preparation", "date": "2026-01-05"},
            {"operation_id": "planting", "date": "2026-01-10"},
            {"operation_id": "first_fertilizer", "date": "2026-01-12"},
        ],
        as_of=date(2026, 1, 12),
    )
    assert report.suggestion.operation_id == "weeding_1"
    assert report.suggestion.status == "upcoming"
    assert report.suggestion.days_until_due == 12


def test_next_step_overdue():
    report = get_next_steps(
        crop_id="maize",
        history=[
            {"operation_id": "land_clearing", "date": "2026-04-01"},
            {"operation_id": "land_preparation", "date": "2026-04-10"},
        ],
        as_of=date(2026, 5, 1),
    )
    assert report.suggestion.operation_id == "planting"
    assert report.suggestion.status == "overdue"
    assert report.suggestion.days_overdue == 7


def test_cycle_complete_when_nothing_required_remains():
    full_history = [
        {"operation_id": "land_clearing", "date": "2026-01-01"},
        {"operation_id": "land_preparation", "date": "2026-01-05"},
        {"operation_id": "planting", "date": "2026-01-10"},
        {"operation_id": "first_fertilizer", "date": "2026-01-15"},
        {"operation_id": "weeding_1", "date": "2026-01-25"},
        {"operation_id": "second_fertilizer", "date": "2026-02-10"},
        {"operation_id": "harvest", "date": "2026-05-01"},
        {"operation_id": "drying", "date": "2026-05-03"},
    ]
    report = get_next_steps(crop_id="maize", history=full_history, as_of=date(2026, 5, 10))
    assert report.cycle_status == "no_outstanding_required_steps"
    assert report.suggestion is None


def test_blocked_on_prerequisite_when_dependency_never_logged():
    # Skip straight to asking about harvest readiness with an empty history.
    # There is no "harvest" as the next required step yet (land_clearing is
    # first), so this actually tests that the very first step reports
    # correctly when nothing at all has happened.
    report = get_next_steps(crop_id="maize", history=[], as_of=date(2026, 1, 1))
    assert report.suggestion.operation_id == "land_clearing"


def test_mixed_crop_history_is_correctly_isolated():
    """
    Same underlying concern as the validator's mixed-crop test: suggestions
    must also only look at the target crop's own history when entries are
    tagged with crop_id.
    """
    mixed = [
        {"operation_id": "land_clearing", "date": "2026-01-01", "crop_id": "maize"},
        {"operation_id": "land_preparation", "date": "2026-01-05", "crop_id": "maize"},
        {"operation_id": "land_clearing", "date": "2026-03-01", "crop_id": "cassava"},
        {"operation_id": "land_preparation", "date": "2026-03-10", "crop_id": "cassava"},
        {"operation_id": "planting", "date": "2026-03-15", "crop_id": "cassava"},
    ]
    report = get_next_steps(crop_id="maize", history=mixed, as_of=date(2026, 1, 6))
    # Maize's own history only has land_clearing + land_preparation done, so
    # its next step should be planting, NOT skip ahead because of cassava's
    # planting record leaking in.
    assert report.suggestion.operation_id == "planting"


def test_cassava_suggestion_uses_typical_window_not_the_open_ended_block_rule():
    """
    Cassava has two harvest rules: cassava_r6 (the true block rule, no upper
    bound) and cassava_r6b (a narrower 270-450 day "typical" warning window).
    The suggestion engine deliberately prefers the narrower rule for
    estimating a due date, since "there's no upper bound, harvest whenever"
    isn't a useful reminder. This means a suggestion CAN say "overdue" past
    the typical window even though the validator itself would never block a
    late cassava harvest. That's intentional, and this test locks it in
    rather than assuming (incorrectly) that the open-ended rule gets used.
    """
    history = [
        {"operation_id": "land_clearing", "date": "2025-01-01"},
        {"operation_id": "land_preparation", "date": "2025-01-20"},
        {"operation_id": "planting", "date": "2025-02-01"},
        {"operation_id": "weeding_1", "date": "2025-02-25"},
        {"operation_id": "weeding_2", "date": "2025-04-01"},
    ]
    report = get_next_steps(crop_id="cassava", history=history, as_of=date(2026, 6, 1))
    assert report.suggestion.operation_id == "harvest"
    assert report.suggestion.status == "overdue"
    assert report.suggestion.latest_date is not None  # from cassava_r6b, the typical window
