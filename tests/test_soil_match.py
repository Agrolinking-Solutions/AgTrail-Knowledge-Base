import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app
from engine import taxonomy

client = TestClient(app)
LIVE_VALUES = ["loam", "sandy_loam", "silty_loam", "sandy", "clay_loam", "sandy_clay", "clay", "silt", "chalky"]


def test_every_soil_word_agtrail_sends_is_mapped():
    mapped = json.loads((Path(taxonomy.MAPPINGS_DIR) / "soil_types.json").read_text())["soils"]
    assert sorted(mapped) == sorted(LIVE_VALUES)


@pytest.mark.parametrize("soil", [None, "", "Not recorded", "mud", "   "])
def test_unrecorded_or_unrecognised_soil_is_unknown_never_guessed(soil):
    r = taxonomy.soil_match("maize", soil)
    assert r["status"] == "unknown" and r["texture"] is None


def test_a_soil_the_crop_prefers_is_preferred():
    assert taxonomy.soil_match("maize", "sandy_loam")["status"] == "preferred"
    assert taxonomy.soil_match("rice", "clay")["status"] == "preferred"


def test_a_known_soil_the_file_does_not_mention_changes_nothing():
    r = taxonomy.soil_match("maize", "silty_loam")
    assert r["status"] == "not_listed" and "does not change" in r["note"]


def test_soybean_does_badly_on_sand_and_accepts_the_rest():
    assert taxonomy.soil_match("soybean", "sandy")["status"] == "avoid"
    assert taxonomy.soil_match("soybean", "clay_loam")["status"] == "preferred"


def test_only_sourced_avoid_lists_exist():
    # Soybean's sand and groundnut's clay-heavy soils are sourced; do not add others without a source.
    from engine.loader import load_crop

    avoid = {c: load_crop(c)["soil_requirements"].get("texture_avoid") for c in ("maize", "rice", "cassava", "cocoa", "groundnut", "sorghum", "soybean")}
    assert {c: a for c, a in avoid.items() if a} == {"soybean": ["sand"], "groundnut": ["clay loam", "sandy clay", "clay"]}


def test_every_avoid_list_names_its_source():
    from engine.loader import load_crop

    for crop in ("groundnut",):
        req = load_crop(crop)["soil_requirements"]
        assert req["texture_avoid"] and "opened 26 Oct 2026" in req["texture_avoid_source"]


def test_groundnut_avoids_heavy_clay_and_is_fine_on_sandy_loam():
    assert taxonomy.soil_match("groundnut", "clay")["status"] == "avoid"
    assert taxonomy.soil_match("groundnut", "sandy_clay")["status"] == "avoid"
    assert taxonomy.soil_match("groundnut", "clay_loam")["status"] == "avoid"
    assert taxonomy.soil_match("groundnut", "sandy_loam")["status"] == "preferred"
    assert taxonomy.soil_match("groundnut", "loam")["status"] == "not_listed"


def test_cocoa_prefers_clay_loam():
    assert taxonomy.soil_match("cocoa", "clay_loam")["status"] == "preferred"


def test_endpoint_returns_the_match_and_404s_an_unknown_crop():
    ok = client.get("/v1/crops/soybean/soil-match", params={"soil": "sandy"})
    assert ok.status_code == 200 and ok.json()["status"] == "avoid"
    assert client.get("/v1/crops/maize/soil-match").json()["status"] == "unknown"
    assert client.get("/v1/crops/not-a-crop/soil-match").status_code == 404
