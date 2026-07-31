"""
HTTP API in front of engine.validator.validate_operation.

Run it with:
    uvicorn api.main:app --reload

Then try:
    curl http://127.0.0.1:8000/crops
    curl -X POST http://127.0.0.1:8000/validate -H "Content-Type: application/json" -d @scenarios/maize_valid_planting.json

Interactive docs (generated automatically by FastAPI) are at /docs once
the server is running.
"""

from __future__ import annotations

from datetime import date

from fastapi import FastAPI, HTTPException

from engine.exceptions import CropNotFoundError, InvalidOperationDataError
from engine.loader import list_crops
from engine.suggestions import get_next_steps
from engine.validator import validate_operation

from .schemas import (
    CropsResponse,
    IssueOut,
    SuggestionOut,
    SuggestionsRequest,
    SuggestionsResponse,
    ValidateRequest,
    ValidateResponse,
)

app = FastAPI(
    title="AgTrail Validation Engine API",
    description=(
        "Checks whether a farm operation is valid to log, given a crop's "
        "knowledge base rules and the farm's history so far."
    ),
    version="0.1.0",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/crops", response_model=CropsResponse)
def get_crops() -> CropsResponse:
    return CropsResponse(crops=list_crops())


@app.post(
    "/validate",
    response_model=ValidateResponse,
    responses={
        400: {"description": "Malformed request data (missing or badly formatted field)"},
        404: {"description": "Unrecognized crop_id"},
    },
)
def validate(request: ValidateRequest) -> ValidateResponse:
    try:
        report = validate_operation(
            crop_id=request.crop_id,
            new_operation=request.new_operation.model_dump(),
            history=[h.model_dump() for h in request.history],
            region=request.region,
        )
    except CropNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidOperationDataError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ValidateResponse(
        crop_id=report.crop_id,
        operation_id=report.operation_id,
        date=report.date.isoformat(),
        blocked=report.blocked,
        issues=[IssueOut(rule_id=i.rule_id, severity=i.severity, message=i.message) for i in report.issues],
        warnings=[IssueOut(rule_id=i.rule_id, severity=i.severity, message=i.message) for i in report.warnings],
        blocking_issues=[
            IssueOut(rule_id=i.rule_id, severity=i.severity, message=i.message) for i in report.blocking_issues
        ],
    )


# This is a POST rather than a GET, even though it's conceptually a read-only
# query, because it needs to send a history array as part of the request.
# There's no standard, broadly-supported way to send a body with a GET
# request (most HTTP clients strip it), so POST is the pragmatic choice here,
# same as how complex read queries are commonly handled in real APIs.
@app.post(
    "/suggestions",
    response_model=SuggestionsResponse,
    responses={
        400: {"description": "Malformed request data (missing or badly formatted field)"},
        404: {"description": "Unrecognized crop_id"},
    },
)
def suggestions(request: SuggestionsRequest) -> SuggestionsResponse:
    as_of = None
    if request.as_of:
        try:
            as_of = date.fromisoformat(request.as_of)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"'as_of' must be YYYY-MM-DD, got '{request.as_of}'")

    try:
        report = get_next_steps(
            crop_id=request.crop_id,
            history=[h.model_dump() for h in request.history],
            region=request.region,
            as_of=as_of,
        )
    except CropNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidOperationDataError as e:
        raise HTTPException(status_code=400, detail=str(e))

    suggestion_out = None
    if report.suggestion:
        s = report.suggestion
        suggestion_out = SuggestionOut(
            operation_id=s.operation_id,
            status=s.status,
            message=s.message,
            depends_on_operation_id=s.depends_on_operation_id,
            depends_on_date=s.depends_on_date.isoformat() if s.depends_on_date else None,
            earliest_date=s.earliest_date.isoformat() if s.earliest_date else None,
            latest_date=s.latest_date.isoformat() if s.latest_date else None,
            days_until_due=s.days_until_due,
            days_overdue=s.days_overdue,
        )

    return SuggestionsResponse(
        crop_id=report.crop_id,
        as_of=report.as_of.isoformat(),
        cycle_status=report.cycle_status,
        suggestion=suggestion_out,
    )
