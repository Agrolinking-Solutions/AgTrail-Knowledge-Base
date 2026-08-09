"""
Yield validation, introduced by the AgTrail Master Agronomist & Validator
Ruleset (Agrolinking Solutions, July 2026). This is deliberately separate
from engine.validator, which checks WHEN an operation happened.
This module checks HOW MUCH was reported at harvest (tonnes per hectare),
which is a completely independent question from timing.

A farm operation can be perfectly timed and still report an impossible
yield (a unit typo, an inflated area, or a genuine total crop failure that
should be logged as a loss event rather than a harvest). Nothing in
engine.validator catches any of that, since it never looks at quantity.

Known limitation, stated plainly: the source ruleset ties this to
GPS-polygon-anchored area rather than self-reported area. AgTrail does not
yet implement GPS-based area verification, so a self-reported area could
still be used to game the resulting t/ha figure even with this check in
place. This module catches the clearest cases (implausible yield given
ANY believable area) but is not a complete anti-fraud solution on its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .exceptions import CropNotFoundError
from .loader import load_crop


@dataclass
class YieldValidationResult:
    crop_id: str
    tonnes_per_hectare: float
    severity: str  # "block" | "warning" | "pass"
    is_loss_event: bool
    message: str


def validate_yield(crop_id: str, tonnes_per_hectare: float) -> YieldValidationResult:
    """
    Checks a reported yield (tonnes per hectare) against the crop's
    yield_validation tiers, if the crop file has that section populated.

    Raises CropNotFoundError for an unrecognized crop_id, and ValueError
    if the crop file has no yield_validation section at all (not every
    crop has been through this pass yet -- see each file's version_history).
    """
    crop = load_crop(crop_id)
    yv = crop.get("yield_validation")

    if not yv:
        raise ValueError(
            f"'{crop_id}' has no yield_validation data yet. This check has "
            f"only been added for crops reconciled against the AgTrail "
            f"Master Agronomist & Validator Ruleset so far."
        )

    tiers = yv.get("tiers", [])
    matching = [t for t in tiers if _tier_matches(t, tonnes_per_hectare)]

    if not matching:
        # Shouldn't happen if tiers are well-formed and cover the full
        # range, but fail loudly rather than silently returning nothing.
        raise ValueError(
            f"No yield_validation tier matched {tonnes_per_hectare} t/ha "
            f"for '{crop_id}'. The crop's tiers may have a gap, this "
            f"should be reported, not silently ignored."
        )

    # More than one tier can legitimately match at once. A yield of 12 t/ha
    # for maize is BOTH "> 5.0" (warning) and "> 10.0" (block), since 12
    # exceeds both thresholds. Naive first-match-wins would incorrectly
    # return the warning tier here. The correct choice is always the most
    # specific/extreme matching tier: for "greater_than", that's the one
    # with the highest threshold; for "less_than", the one with the lowest.
    chosen = max(matching, key=_specificity)

    return YieldValidationResult(
        crop_id=crop_id,
        tonnes_per_hectare=tonnes_per_hectare,
        severity=chosen["severity"],
        is_loss_event=chosen.get("is_loss_event", False),
        message=chosen["message"],
    )


def _tier_matches(tier: dict, value: float) -> bool:
    condition_type = tier["condition_type"]
    if condition_type == "equals_zero":
        return value == 0
    if condition_type == "less_than":
        return 0 < value < tier["max"]
    if condition_type == "range":
        return tier["min"] <= value <= tier["max"]
    if condition_type == "greater_than":
        return value > tier["min"]
    raise ValueError(f"Unknown yield_validation condition_type: {condition_type!r}")


def _specificity(tier: dict) -> float:
    """
    Higher return value = more specific/extreme = preferred when multiple
    tiers match the same value. equals_zero and range tiers never overlap
    with anything else in practice, so they get a low, fixed priority;
    greater_than tiers rank by how high their threshold is (higher =
    more specific); less_than tiers rank by how low their threshold is
    (lower max = more specific), inverted here so a lower max still sorts
    higher in this "bigger number wins" comparison.
    """
    condition_type = tier["condition_type"]
    if condition_type == "greater_than":
        return tier["min"]
    if condition_type == "less_than":
        return -tier["max"]
    return -1_000_000  # equals_zero / range: essentially never in a tie, keep them lowest priority
