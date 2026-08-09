"""
Request and response shapes for the API. Kept separate from engine/ on
purpose: engine/ has no framework dependency and should stay that way, these
schemas are the HTTP-facing translation layer on top of it.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class OperationIn(BaseModel):
    operation_id: str = Field(..., description="e.g. 'planting', 'harvest'")
    date: str = Field(..., description="YYYY-MM-DD")
    crop_id: Optional[str] = Field(
        None,
        description=(
            "Only needed if this farm grows more than one crop and history "
            "mixes operations from different crops. See README for details."
        ),
    )


class ValidateRequest(BaseModel):
    crop_id: str = Field(..., description="e.g. 'maize', 'cassava', 'cocoa'")
    new_operation: OperationIn
    history: list[OperationIn] = Field(default_factory=list)
    region: Optional[str] = Field(
        None, description="e.g. 'Nigeria - Guinea Savanna'. Optional."
    )


class SuggestionsRequest(BaseModel):
    crop_id: str = Field(..., description="e.g. 'maize', 'cassava', 'cocoa'")
    history: list[OperationIn] = Field(default_factory=list)
    region: Optional[str] = None
    as_of: Optional[str] = Field(
        None, description="YYYY-MM-DD. Defaults to today if omitted."
    )


class IssueOut(BaseModel):
    rule_id: str
    severity: str
    message: str


class ValidateResponse(BaseModel):
    crop_id: str
    operation_id: str
    date: str
    blocked: bool
    issues: list[IssueOut]
    warnings: list[IssueOut]
    blocking_issues: list[IssueOut]


class ErrorResponse(BaseModel):
    detail: str


class CropsResponse(BaseModel):
    crops: list[str]


class YieldValidateRequest(BaseModel):
    crop_id: str = Field(..., description="e.g. 'maize'")
    tonnes_per_hectare: float = Field(..., description="Reported yield, tonnes per hectare")


class YieldValidateResponse(BaseModel):
    crop_id: str
    tonnes_per_hectare: float
    severity: str
    is_loss_event: bool
    message: str


class SuggestionOut(BaseModel):
    operation_id: str
    status: str
    message: str
    depends_on_operation_id: Optional[str] = None
    depends_on_date: Optional[str] = None
    earliest_date: Optional[str] = None
    latest_date: Optional[str] = None
    days_until_due: Optional[int] = None
    days_overdue: Optional[int] = None


class SuggestionsResponse(BaseModel):
    crop_id: str
    as_of: str
    cycle_status: str
    suggestion: Optional[SuggestionOut] = None
