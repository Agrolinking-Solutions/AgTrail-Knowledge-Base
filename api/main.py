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

import hashlib
from typing import Optional
import json
from datetime import date

from fastapi import FastAPI, HTTPException, Request, Response

from engine import taxonomy as taxonomy_data
from engine.exceptions import CropNotFoundError, InvalidOperationDataError
from engine.loader import list_crops
from engine.suggestions import get_next_steps
from engine.validator import validate_operation
from engine.yield_validator import validate_yield

from .schemas import (
    CropsResponse,
    IssueOut,
    SuggestionOut,
    SuggestionsRequest,
    SuggestionsResponse,
    ValidateRequest,
    ValidateResponse,
    YieldValidateRequest,
    YieldValidateResponse,
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


@app.get("/v1/version", tags=["reference data"])
def get_version() -> dict:
    """
    What version of the knowledge base is running. kb_version changes whenever
    any crop or mapping file changes, so callers that stamp their results with
    it know when to recompute them. commit is only present when the deploy
    platform provides it. (Kept off /health on purpose: /health stays exactly
    as monitors already expect it.)
    """
    return {"kb_version": taxonomy_data.kb_version(), "commit": taxonomy_data.source_commit()}


# Read-only reference data under /v1. The files change only on a deploy, so the
# responses carry an ETag and a one-hour cache lifetime: callers can keep a copy
# and ask "has it changed?" with If-None-Match, getting an empty 304 back.
def _etag_matches(if_none_match: str | None, etag: str) -> bool:
    """
    True when the caller already has this version. Uses weak comparison, as
    HTTP specifies for If-None-Match: a proxy such as the platform's gzip layer
    turns "abc" into W/"abc" on the way out, so the caller sends back W/"abc",
    and that must still count as a match. Also accepts a list of tags and "*".
    """
    if not if_none_match:
        return False
    wanted = etag.removeprefix("W/")
    for candidate in if_none_match.split(","):
        candidate = candidate.strip()
        if candidate == "*" or candidate.removeprefix("W/") == wanted:
            return True
    return False


def _cached_json(request: Request, payload: dict) -> Response:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    etag = '"' + hashlib.sha256(body.encode("utf-8")).hexdigest()[:20] + '"'
    headers = {"ETag": etag, "Cache-Control": "public, max-age=3600"}
    if _etag_matches(request.headers.get("if-none-match"), etag):
        return Response(status_code=304, headers=headers)
    return Response(content=body, media_type="application/json", headers=headers)


_NOT_MODIFIED = {304: {"description": "Unchanged since the ETag in If-None-Match"}}


@app.get("/v1/taxonomy", responses=_NOT_MODIFIED, tags=["reference data"])
def get_taxonomy(request: Request) -> Response:
    """The shared operation categories and the operation_id mapping. Every row is UNVERIFIED until approved."""
    return _cached_json(request, taxonomy_data.taxonomy())


@app.get("/v1/crops/{crop_id}/soil-match", responses={404: {"description": "Unrecognized crop_id"}}, tags=["reference data"])
def get_soil_match(crop_id: str, soil: Optional[str] = None) -> dict:
    """
    How a farm's recorded soil (AgTrail's soil_type, e.g. sandy_loam) compares with what this crop
    prefers: preferred, avoid, not_listed or unknown. Only `avoid` should change an estimate.
    """
    try:
        return taxonomy_data.soil_match(crop_id, soil)
    except CropNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/v1/crops/{crop_id}/harvest-estimate", responses={**_NOT_MODIFIED, 404: {"description": "Unrecognized crop_id"}}, tags=["reference data"])
def get_harvest_estimate(crop_id: str, request: Request) -> Response:
    """
    What a farm of this crop typically harvests per hectare (typical value and normal range), the
    expected harvest window and the sources, as of the date inside. `available` is false for a crop
    with no current research behind it yet. This describes a typical farm, not a forecast for one.
    """
    try:
        return _cached_json(request, taxonomy_data.harvest_estimate(crop_id))
    except CropNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/v1/mappings/commodities", responses=_NOT_MODIFIED, tags=["reference data"])
def get_commodity_mapping(request: Request) -> Response:
    """Which PIS commodity prices each crop, and the yield conversion factor."""
    return _cached_json(request, taxonomy_data.commodities())


@app.get("/v1/mappings/regions", responses=_NOT_MODIFIED, tags=["reference data"])
def get_region_mapping(request: Request) -> Response:
    """Each state's geopolitical zone and default agro-ecological zone."""
    return _cached_json(request, taxonomy_data.regions())


@app.get("/crops", response_model=CropsResponse)
@app.get("/v1/crops", response_model=CropsResponse, tags=["reference data"])
def get_crops() -> CropsResponse:
    return CropsResponse(crops=list_crops())


@app.get("/v1/crops/{crop_id}/steps", responses={**_NOT_MODIFIED, 404: {"description": "Unrecognized crop_id"}}, tags=["reference data"])
def get_crop_steps(crop_id: str, request: Request) -> Response:
    """The crop's steps in workflow order, each with its shared signal category."""
    try:
        return _cached_json(request, taxonomy_data.crop_steps(crop_id))
    except CropNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/v1/validate", tags=["validation"], response_model=ValidateResponse, include_in_schema=True)
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
@app.post("/v1/suggestions", tags=["validation"], response_model=SuggestionsResponse)
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


@app.post("/v1/validate-yield", tags=["validation"], response_model=YieldValidateResponse)
@app.post(
    "/validate-yield",
    response_model=YieldValidateResponse,
    responses={
        400: {"description": "Crop has no yield_validation data yet, or tiers are malformed"},
        404: {"description": "Unrecognized crop_id"},
    },
)
def validate_yield_endpoint(request: YieldValidateRequest) -> YieldValidateResponse:
    try:
        result = validate_yield(request.crop_id, request.tonnes_per_hectare)
    except CropNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return YieldValidateResponse(
        crop_id=result.crop_id,
        tonnes_per_hectare=result.tonnes_per_hectare,
        severity=result.severity,
        is_loss_event=result.is_loss_event,
        message=result.message,
    )
