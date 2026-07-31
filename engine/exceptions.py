"""
Exceptions raised by the engine for malformed input, as opposed to normal
domain rule violations (which are represented as ValidationIssue objects on
a ValidationReport, not exceptions).

The distinction matters: a harvest logged too early is a legitimate business
outcome the caller needs to show a farmer. A missing date field or a crop_id
that doesn't exist is a caller bug, and should fail loudly and clearly, not
surface as a generic Python KeyError or ValueError three frames deep.
"""

from __future__ import annotations


class CropNotFoundError(FileNotFoundError):
    """Raised when a requested crop_id has no matching file in knowledge_base/crops/."""


class InvalidOperationDataError(ValueError):
    """
    Raised when an operation dict (either new_operation or an entry in
    history) is missing a required field or has a field in the wrong shape,
    e.g. a date string that isn't in YYYY-MM-DD format.
    """
