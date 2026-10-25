"""
Harvest estimates: what a farm of a crop typically harvests, with sources. The numbers must be
internally consistent, cited, and match the crop's own timing rules, and a crop with no current
research must say so instead of giving a figure.
"""

import json

import pytest
from fastapi.testclient import TestClient

from api.main import app
from engine import taxonomy
from engine.loader import CROPS_DIR, list_crops, load_crop

client = TestClient(app)
WITH_ESTIMATE = sorted(p.stem for p in CROPS_DIR.glob("*.json") if "harvest_estimate" in json.loads(p.read_text()))


def test_the_seven_researched_crops_have_an_estimate():
    assert WITH_ESTIMATE == ["cassava", "cocoa", "groundnut", "maize", "rice", "sorghum", "soybean"]


@pytest.mark.parametrize("crop", WITH_ESTIMATE)
def test_the_typical_yield_sits_inside_the_normal_range(crop):
    y = load_crop(crop)["harvest_estimate"]["yield_t_per_ha"]

    assert 0 < y["normal_low"] <= y["typical"] <= y["normal_high"]
    assert y["national_recent_low"] <= y["typical"] <= y["national_recent_high"]


@pytest.mark.parametrize("crop", WITH_ESTIMATE)
def test_the_normal_range_never_contradicts_the_yield_checks(crop):
    # The estimate and the validation must agree on what is normal: nothing inside the estimate's
    # normal range may be blocked by the crop's own yield checks.
    from engine.yield_validator import validate_yield

    y = load_crop(crop)["harvest_estimate"]["yield_t_per_ha"]
    for value in (y["normal_low"], y["typical"], y["normal_high"]):
        assert validate_yield(crop, value).severity != "block", (crop, value)


@pytest.mark.parametrize("crop", WITH_ESTIMATE)
def test_every_estimate_is_dated_cited_and_says_what_it_cannot_do(crop):
    b = load_crop(crop)["harvest_estimate"]

    assert b["as_of"].startswith("2026-")
    assert len(b["sources"]) >= 2 and all(s["figure"] and s["year"] for s in b["sources"])
    assert any(s["url"] for s in b["sources"])
    assert any("farm" in c.lower() for c in b["caveats"]) and "not a forecast" in b["method"].lower()
    assert 0 < b["confidence"] <= 1


@pytest.mark.parametrize("crop", [c for c in WITH_ESTIMATE if c != "cocoa"])
def test_the_harvest_window_matches_the_crops_own_timing_rules(crop):
    w = load_crop(crop)["harvest_estimate"]["harvest_window"]
    rules = [r for r in load_crop(crop)["validation_rules"] if r["operation_id"] == "harvest" and r.get("depends_on_operation_id") == w["after"]]
    bounds = {(r.get("min_days_after_dependency"), r.get("max_days_after_dependency")) for r in rules}
    mins = {b[0] for b in bounds if b[0]}
    maxs = {b[1] for b in bounds if b[1]}

    assert w["min_days"] in mins or any(b == (w["min_days"], w["max_days"]) for b in bounds), (crop, bounds)
    assert w["max_days"] in maxs, (crop, bounds)


def test_cocoa_is_per_year_and_has_no_harvest_window():
    b = load_crop("cocoa")["harvest_estimate"]

    assert b["per"] == "year" and b["harvest_window"] is None and b["yield_basis"] == "dry beans"


def test_the_old_expected_yields_that_current_figures_disproved_were_replaced():
    assert "FAO 2024" in load_crop("cassava")["yield_model"]["expected_yield_per_hectare"]
    assert "10 - 15" in load_crop("cassava")["yield_model"]["notes"]  # kept as the record of what it replaced


def test_a_crop_without_research_says_so_and_gives_no_figure():
    without = [c for c in list_crops() if c not in WITH_ESTIMATE][0]

    body = client.get(f"/v1/crops/{without}/harvest-estimate").json()

    assert body["available"] is False and "yield_t_per_ha" not in body and body["reason"]


def test_the_endpoint_serves_the_block_with_caching_and_404s_an_unknown_crop():
    first = client.get("/v1/crops/maize/harvest-estimate")
    body = first.json()

    assert first.status_code == 200 and body["available"] is True and body["yield_t_per_ha"]["typical"] == 2.03
    assert client.get("/v1/crops/maize/harvest-estimate", headers={"If-None-Match": first.headers["etag"]}).status_code == 304
    assert client.get("/v1/crops/not_a_crop/harvest-estimate").status_code == 404
    assert taxonomy.harvest_estimate("maize")["as_of"] == body["as_of"]
