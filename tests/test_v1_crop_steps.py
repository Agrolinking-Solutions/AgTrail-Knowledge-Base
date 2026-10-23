"""The /v1 crop steps endpoint and the /v1 copies of the validation endpoints."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app
from engine import taxonomy
from engine.loader import list_crops

client = TestClient(app)
SCENARIOS = Path(__file__).resolve().parent.parent / "scenarios"


def test_steps_come_back_in_workflow_order_with_their_shared_category():
    body = client.get("/v1/crops/sorghum/steps").json()

    ids = [s["operation_id"] for s in body["steps"]]
    assert body["crop_id"] == "sorghum"
    assert ids[:3] == ["land_clearing", "land_preparation", "planting"]
    assert [s["step_number"] for s in body["steps"]] == sorted(s["step_number"] for s in body["steps"])
    by_id = {s["operation_id"]: s for s in body["steps"]}
    assert by_id["weeding_1"]["signal_category"] == "weeding"
    assert by_id["second_fertilizer"]["signal_category"] == "fertilizer_application"


@pytest.mark.parametrize("crop_id", list_crops())
def test_every_crop_has_steps_and_every_step_has_a_category(crop_id):
    steps = taxonomy.crop_steps(crop_id)["steps"]

    assert steps
    assert all(s["signal_category"] for s in steps), [s["operation_id"] for s in steps if not s["signal_category"]]
    assert all(s["name"] for s in steps)


def test_an_unknown_crop_is_a_404():
    assert client.get("/v1/crops/not_a_crop/steps").status_code == 404


def test_steps_use_the_same_etag_caching_as_the_other_reference_data():
    first = client.get("/v1/crops/maize/steps")
    assert first.status_code == 200 and first.headers["etag"]
    assert client.get("/v1/crops/maize/steps", headers={"If-None-Match": first.headers["etag"]}).status_code == 304


def test_v1_crops_matches_the_original_crops_list():
    assert client.get("/v1/crops").json() == client.get("/crops").json()


def test_v1_validate_gives_the_same_answer_as_the_original_address():
    body = json.loads((SCENARIOS / "sorghum_blocked_harvest_too_early.json").read_text())

    original = client.post("/validate", json=body)
    versioned = client.post("/v1/validate", json=body)

    assert versioned.status_code == original.status_code == 200
    assert versioned.json() == original.json()
    assert versioned.json()["blocked"] is True


def test_v1_suggestions_and_yield_match_the_original_addresses():
    suggestion = {"crop_id": "maize", "history": [{"operation_id": "land_clearing", "date": "2026-06-01"}], "as_of": "2026-06-05"}
    assert client.post("/v1/suggestions", json=suggestion).json() == client.post("/suggestions", json=suggestion).json()
    yield_body = {"crop_id": "maize", "tonnes_per_hectare": 3.0}
    assert client.post("/v1/validate-yield", json=yield_body).json() == client.post("/validate-yield", json=yield_body).json()
