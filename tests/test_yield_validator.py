"""
Tests for engine.yield_validator.validate_yield.

Maize is currently the only crop with yield_validation data populated
(added when maize was reconciled against the AgTrail Master Agronomist &
Validator Ruleset). These tests specifically cover the tier-overlap bug
that was caught and fixed while building this: naive first-match-wins
would have returned the wrong tier for values that match more than one
"greater_than" threshold at once.
"""

import pytest

from engine.yield_validator import validate_yield
from engine.exceptions import CropNotFoundError


def test_zero_yield_is_a_loss_event():
    result = validate_yield("maize", 0)
    assert result.severity == "block"
    assert result.is_loss_event is True


def test_near_total_failure_is_a_warning():
    result = validate_yield("maize", 0.3)
    assert result.severity == "warning"
    assert result.is_loss_event is False


def test_normal_range_passes():
    for value in (0.8, 2.5, 5.0):
        result = validate_yield("maize", value)
        assert result.severity == "pass", f"{value} t/ha should pass"


def test_exceptional_yield_is_a_warning_not_a_block():
    result = validate_yield("maize", 7.0)
    assert result.severity == "warning"


def test_extreme_yield_is_blocked_not_just_warned():
    """
    The actual bug this test guards against: 12 t/ha matches BOTH the
    '> 5.0' warning tier and the '> 10.0' block tier. The engine must
    pick the more specific (higher threshold) match, block, not fall
    back to the first tier it happens to check.
    """
    result = validate_yield("maize", 12.0)
    assert result.severity == "block"


def test_exactly_ten_is_still_a_warning_not_a_block():
    """Boundary check: the block tier is strictly '> 10.0', not '>= 10.0'."""
    result = validate_yield("maize", 10.0)
    assert result.severity == "warning"


def test_crop_without_yield_validation_data_raises_clear_error():
    with pytest.raises(ValueError, match="no yield_validation data"):
        validate_yield("cassava", 5.0)


def test_unrecognized_crop_raises_crop_not_found():
    with pytest.raises(CropNotFoundError):
        validate_yield("durian", 5.0)


def test_sesame_inferred_zero_tier_is_a_loss_event():
    """
    Sesame's source table did not include an explicit 0 t/ha row, unlike
    maize's. This tier was added by inference for consistency, this test
    documents that choice and locks in the resulting behavior.
    """
    result = validate_yield("sesame", 0)
    assert result.severity == "block"
    assert result.is_loss_event is True


def test_sesame_extreme_yield_is_blocked():
    result = validate_yield("sesame", 3.0)
    assert result.severity == "block"


def test_ginger_yield_gap_between_stated_tiers_is_still_covered():
    """
    Ginger's source table left two ranges uncovered (4.0-5.0 and
    25.0-35.0 t/ha), gaps between its own stated bands. Rather than let
    those crash the validator, both were closed using the same approach
    already used for Tomato: extending the nearer warning tier. This
    locks in that both gap values resolve to warning, not an error.
    """
    result_low_gap = validate_yield("ginger", 4.5)
    assert result_low_gap.severity == "warning"

    result_high_gap = validate_yield("ginger", 30.0)
    assert result_high_gap.severity == "warning"


def test_ginger_extreme_yield_is_blocked():
    result = validate_yield("ginger", 40.0)
    assert result.severity == "block"


def test_cashew_zero_yield_is_a_loss_event():
    result = validate_yield("cashew", 0)
    assert result.severity == "block"
    assert result.is_loss_event is True


def test_cashew_extreme_yield_is_blocked():
    """5.0 t/ha/yr matches both the '>1.0' warning and '>4.0' block tiers; block must win."""
    result = validate_yield("cashew", 5.0)
    assert result.severity == "block"


def test_hibiscus_extreme_yield_is_blocked():
    result = validate_yield("hibiscus", 3.0)
    assert result.severity == "block"


# --- Automated gap detection, added in the engine-fixes pass following the
# Medium-priority crop batch ---------------------------------------------
#
# Every gap found in yam.json, groundnut.json, pepper.json, onion.json,
# oil_palm.json, rubber.json, coffee.json, and cotton.json's source yield
# tables was caught by a MANUAL script re-run by hand after authoring each
# file, not by anything in this test suite. That is a process gap, not just
# a data gap: nothing here actually enforced that every crop's tiers cover
# their full range, so a future crop file with an unnoticed gap could ship,
# pass schema validation and pytest cleanly, and only surface the very first
# time a real farmer reports a yield that happens to fall in the hole --
# at which point validate_yield() raises a ValueError instead of returning
# a result. These tests close that gap going forward: any crop file with
# yield_validation data is automatically swept across a fine-grained value
# range and asserted to never raise.

def _crops_with_yield_validation() -> list[str]:
    from engine.loader import list_crops, load_crop
    return [c for c in list_crops() if load_crop(c).get("yield_validation")]


@pytest.mark.parametrize("crop_id", _crops_with_yield_validation())
def test_no_yield_validation_gaps_in_plausible_range(crop_id):
    """
    Sweeps 0 to 100 t/ha in 0.1 steps (fine enough to catch a gap as narrow
    as coffee.json's 0.3-0.4 t/ha band) and asserts every value resolves to
    a tier rather than raising. 100 t/ha comfortably exceeds every crop's
    hard-block ceiling in this knowledge base as of this test being written,
    so this covers the full plausible-and-then-some range, not just the
    Pass tier.
    """
    step = 1
    max_value_x10 = 1000  # 100.0 t/ha, in tenths to keep the loop on integers
    for value_x10 in range(0, max_value_x10 + step, step):
        value = value_x10 / 10
        try:
            validate_yield(crop_id, value)
        except ValueError as e:
            pytest.fail(
                f"{crop_id}: yield_validation has a gap at {value} t/ha -- "
                f"validate_yield() raised instead of returning a tier: {e}"
            )