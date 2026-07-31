"""
Shared history handling for both engine.validator and engine.suggestions.

This was pulled out of validator.py specifically so suggestions.py can reuse
the exact same parsing and crop-scoping logic rather than reimplementing it.
Duplicating this was how the mixed-crop-history bug could have shipped twice
instead of once; keeping it in one place means a future fix only needs to
happen here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from .exceptions import InvalidOperationDataError


@dataclass
class FarmOperation:
    operation_id: str
    date: date
    crop_id: Optional[str] = None  # optional tag, see parse_and_scope_history() below

    @staticmethod
    def from_dict(d: dict, context: str = "operation") -> "FarmOperation":
        if "operation_id" not in d:
            raise InvalidOperationDataError(
                f"{context} is missing required field 'operation_id': {d}"
            )
        if "date" not in d:
            raise InvalidOperationDataError(
                f"{context} ('{d.get('operation_id')}') is missing required field 'date': {d}"
            )
        return FarmOperation(
            operation_id=d["operation_id"],
            date=_parse_date(d["date"], context=context, operation_id=d.get("operation_id")),
            crop_id=d.get("crop_id"),
        )


def _parse_date(value, context: str = "operation", operation_id: Optional[str] = None) -> date:
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError) as e:
        raise InvalidOperationDataError(
            f"{context} ('{operation_id}') has an invalid date '{value}'. "
            f"Dates must be in YYYY-MM-DD format. Original error: {e}"
        ) from e


def parse_and_scope_history(history: list[dict], crop_id: str) -> list[FarmOperation]:
    """
    Parses raw history dicts into FarmOperation objects, then applies the
    same crop-scoping rule validate_operation() documents: if any entry
    carries a crop_id, only entries matching this crop_id are kept
    (including dropping untagged entries, since they're ambiguous once
    tagging is in use at all). If no entry carries a crop_id, the whole
    list is treated as belonging to this one crop.
    """
    raw = [FarmOperation.from_dict(h, context=f"history[{i}]") for i, h in enumerate(history)]
    if any(h.crop_id is not None for h in raw):
        return [h for h in raw if h.crop_id == crop_id]
    return raw
