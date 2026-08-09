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
