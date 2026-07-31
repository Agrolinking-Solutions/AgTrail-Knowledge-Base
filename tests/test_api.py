"""
Tests for the API layer, using FastAPI's TestClient so nothing here depends
on a server actually being started somewhere.
"""

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_list_crops():
    resp = client.get("/crops")
    assert resp.status_code == 200
    crops = resp.json()["crops"]
    assert {"maize", "cassava", "cocoa"}.issubset(set(crops))


def test_validate_passes_cleanly():
    resp = client.post(
        "/validate",
        json={
            "crop_id": "maize",
            "region": "Nigeria - Guinea Savanna",
            "history": [
                {"operation_id": "land_clearing", "date": "2026-04-01"},
                {"operation_id": "land_preparation", "date": "2026-04-10"},
            ],
            "new_operation": {"operation_id": "planting", "date": "2026-04-15"},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["blocked"] is False
    assert body["issues"] == []


def test_validate_blocks_early_harvest():
    resp = client.post(
        "/validate",
        json={
            "crop_id": "maize",
            "history": [
                {"operation_id": "land_clearing", "date": "2026-01-01"},
                {"operation_id": "land_preparation", "date": "2026-01-05"},
                {"operation_id": "planting", "date": "2026-01-10"},
            ],
            "new_operation": {"operation_id": "harvest", "date": "2026-02-01"},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["blocked"] is True
    assert any(i["rule_id"] == "maize_r8" for i in body["blocking_issues"])


def test_validate_unrecognized_crop_returns_404():
    resp = client.post(
        "/validate",
        json={
            "crop_id": "durian",
            "history": [],
            "new_operation": {"operation_id": "planting", "date": "2026-01-01"},
        },
    )
    assert resp.status_code == 404
    assert "durian" in resp.json()["detail"]


def test_validate_bad_date_returns_400():
    resp = client.post(
        "/validate",
        json={
            "crop_id": "maize",
            "history": [],
            "new_operation": {"operation_id": "planting", "date": "not-a-date"},
        },
    )
    assert resp.status_code == 400


def test_validate_missing_required_field_returns_422():
    """
    This one is handled by FastAPI/Pydantic itself, before our code ever
    runs, since operation_id is a required field on the request schema.
    Different failure mode from the 400 above (that one is a value that
    passed schema validation but failed our own parsing), worth keeping
    both cases distinct rather than collapsing them into one error type.
    """
    resp = client.post(
        "/validate",
        json={
            "crop_id": "maize",
            "history": [],
            "new_operation": {"date": "2026-01-01"},
        },
    )
    assert resp.status_code == 422


def test_validate_mixed_crop_history_with_tags_is_correctly_isolated():
    resp = client.post(
        "/validate",
        json={
            "crop_id": "maize",
            "history": [
                {"operation_id": "land_clearing", "date": "2026-01-01", "crop_id": "maize"},
                {"operation_id": "land_preparation", "date": "2026-01-05", "crop_id": "maize"},
                {"operation_id": "planting", "date": "2026-01-10", "crop_id": "maize"},
                {"operation_id": "land_clearing", "date": "2026-03-01", "crop_id": "cassava"},
                {"operation_id": "land_preparation", "date": "2026-03-10", "crop_id": "cassava"},
                {"operation_id": "planting", "date": "2026-03-15", "crop_id": "cassava"},
            ],
            "new_operation": {"operation_id": "harvest", "date": "2026-05-01", "crop_id": "maize"},
        },
    )
    assert resp.status_code == 200
    assert resp.json()["blocked"] is False


def test_suggestions_due_now():
    resp = client.post(
        "/suggestions",
        json={
            "crop_id": "maize",
            "history": [
                {"operation_id": "land_clearing", "date": "2026-04-01"},
                {"operation_id": "land_preparation", "date": "2026-04-10"},
            ],
            "as_of": "2026-04-12",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["cycle_status"] == "in_progress"
    assert body["suggestion"]["operation_id"] == "planting"
    assert body["suggestion"]["status"] == "due_now"


def test_suggestions_overdue():
    resp = client.post(
        "/suggestions",
        json={
            "crop_id": "maize",
            "history": [
                {"operation_id": "land_clearing", "date": "2026-04-01"},
                {"operation_id": "land_preparation", "date": "2026-04-10"},
            ],
            "as_of": "2026-05-01",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["suggestion"]["status"] == "overdue"
    assert body["suggestion"]["days_overdue"] == 7


def test_suggestions_cycle_complete():
    resp = client.post(
        "/suggestions",
        json={
            "crop_id": "maize",
            "history": [
                {"operation_id": "land_clearing", "date": "2026-01-01"},
                {"operation_id": "land_preparation", "date": "2026-01-05"},
                {"operation_id": "planting", "date": "2026-01-10"},
                {"operation_id": "first_fertilizer", "date": "2026-01-15"},
                {"operation_id": "weeding_1", "date": "2026-01-25"},
                {"operation_id": "second_fertilizer", "date": "2026-02-10"},
                {"operation_id": "harvest", "date": "2026-05-01"},
                {"operation_id": "drying", "date": "2026-05-03"},
            ],
            "as_of": "2026-05-10",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["cycle_status"] == "no_outstanding_required_steps"
    assert body["suggestion"] is None


def test_suggestions_unrecognized_crop_returns_404():
    resp = client.post("/suggestions", json={"crop_id": "durian", "history": []})
    assert resp.status_code == 404


def test_suggestions_bad_as_of_returns_400():
    resp = client.post(
        "/suggestions",
        json={"crop_id": "maize", "history": [], "as_of": "not-a-date"},
    )
    assert resp.status_code == 400
