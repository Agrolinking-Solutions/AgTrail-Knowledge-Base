"""The shared operation taxonomy, the /v1 reference-data endpoints and the version stamp."""

import json
import re

import pytest
from fastapi.testclient import TestClient

from api.main import app
from engine import taxonomy
from engine.loader import CROPS_DIR

client = TestClient(app)

ELEVEN = {
    "land_preparation", "planting", "weeding", "fertilizer_application", "pest_control",
    "harvesting", "sorting_grading", "cleaning_drying", "processing", "storage", "other",
}


def _all_operation_ids():
    ids = set()
    for path in CROPS_DIR.glob("*.json"):
        for op in json.loads(path.read_text())["operations"]:
            ids.add(op["operation_id"])
    return ids


# ---- the mapping ----

def test_there_are_exactly_the_eleven_shared_categories():
    assert set(taxonomy.signal_categories()) == ELEVEN
    assert len(taxonomy.signal_categories()) == 11


def test_every_operation_in_every_crop_file_has_a_category():
    # Adding a crop with a new operation_id fails here until it is mapped.
    unmapped = sorted(i for i in _all_operation_ids() if taxonomy.signal_category_for(None, i) is None)
    assert unmapped == []


def test_the_mapping_only_uses_known_categories_and_statuses():
    for op_id, entry in taxonomy.taxonomy()["operations"].items():
        assert entry["signal_category"] in ELEVEN, op_id
        assert entry["review_status"] in {"proposed", "needs-decision", "approved"}, op_id
        assert entry["reason"], op_id


def test_no_mapped_operation_is_unused():
    stale = set(taxonomy.taxonomy()["operations"]) - _all_operation_ids()
    assert stale == set(), "mapping lists operations no crop file uses"


def test_nothing_is_marked_approved_until_a_person_approves_it():
    assert taxonomy.taxonomy()["review_status"] == "UNVERIFIED"
    assert all(e["review_status"] != "approved" for e in taxonomy.taxonomy()["operations"].values())


def test_unknown_operation_has_no_category():
    assert taxonomy.signal_category_for("maize", "not_a_real_operation") is None


def test_known_operations_map_as_expected():
    assert taxonomy.signal_category_for("maize", "first_fertilizer") == "fertilizer_application"
    assert taxonomy.signal_category_for("maize", "weeding_1") == "weeding"
    assert taxonomy.signal_category_for("cocoa", "harvest") == "harvesting"


def test_a_crop_override_beats_the_default(monkeypatch):
    patched = json.loads(json.dumps(taxonomy.taxonomy()))
    patched["crop_overrides"] = {"rubber": {"tapping": "other"}}
    monkeypatch.setattr(taxonomy, "taxonomy", lambda: patched)
    assert taxonomy.signal_category_for("rubber", "tapping") == "other"
    assert taxonomy.signal_category_for("maize", "tapping") == "harvesting"


# ---- version stamp ----

def test_health_is_exactly_what_monitors_expect():
    assert client.get("/health").json() == {"status": "ok"}


def test_version_endpoint_reports_the_data_version():
    body = client.get("/v1/version").json()
    assert re.fullmatch(r"\d+\.\d+\.\d+\+[0-9a-f]{10}", body["kb_version"])
    assert body["kb_version"] == taxonomy.kb_version()
    assert "commit" in body


def test_data_hash_changes_when_a_file_changes(tmp_path):
    (tmp_path / "a.json").write_text('{"x": 1}')
    before = taxonomy.data_hash(tmp_path)
    assert taxonomy.data_hash(tmp_path) == before
    (tmp_path / "a.json").write_text('{"x": 2}')
    assert taxonomy.data_hash(tmp_path) != before


def test_commit_comes_from_the_platform_when_present(monkeypatch):
    monkeypatch.setenv("SOURCE_COMMIT", "abcdef0123456789abcdef")
    assert taxonomy.source_commit() == "abcdef012345"
    monkeypatch.delenv("SOURCE_COMMIT")
    monkeypatch.delenv("GIT_COMMIT", raising=False)
    assert taxonomy.source_commit() is None


# ---- endpoints ----

PATHS = ["/v1/taxonomy", "/v1/mappings/commodities", "/v1/mappings/regions"]


@pytest.mark.parametrize("path", PATHS)
def test_reference_endpoints_return_json_with_cache_headers(path):
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["etag"].startswith('"')
    assert "max-age=3600" in response.headers["cache-control"]
    assert response.json()


@pytest.mark.parametrize("path", PATHS)
def test_an_unchanged_copy_gets_an_empty_304(path):
    etag = client.get(path).headers["etag"]
    again = client.get(path, headers={"If-None-Match": etag})
    assert again.status_code == 304
    assert again.content == b""
    assert again.headers["etag"] == etag


@pytest.mark.parametrize("path", PATHS)
def test_a_different_etag_gets_the_full_body(path):
    response = client.get(path, headers={"If-None-Match": '"something-old"'})
    assert response.status_code == 200 and response.content


def test_the_endpoints_serve_the_files_unchanged():
    assert client.get("/v1/taxonomy").json() == taxonomy.taxonomy()
    assert client.get("/v1/mappings/commodities").json() == taxonomy.commodities()
    assert client.get("/v1/mappings/regions").json() == taxonomy.regions()


def test_existing_endpoints_are_untouched():
    assert client.get("/crops").status_code == 200
    assert "maize" in client.get("/crops").json()["crops"]


@pytest.mark.parametrize("path", PATHS)
def test_a_weak_etag_from_a_proxy_still_counts_as_unchanged(path):
    # The platform's proxy rewrites "abc" to W/"abc"; the caller sends that back.
    etag = client.get(path).headers["etag"]
    assert client.get(path, headers={"If-None-Match": "W/" + etag}).status_code == 304


def test_if_none_match_accepts_a_list_and_a_star():
    etag = client.get("/v1/taxonomy").headers["etag"]
    assert client.get("/v1/taxonomy", headers={"If-None-Match": f'"old", W/{etag}'}).status_code == 304
    assert client.get("/v1/taxonomy", headers={"If-None-Match": "*"}).status_code == 304
    assert client.get("/v1/taxonomy", headers={"If-None-Match": '"old", "older"'}).status_code == 200
    assert client.get("/v1/taxonomy", headers={"If-None-Match": ""}).status_code == 200
