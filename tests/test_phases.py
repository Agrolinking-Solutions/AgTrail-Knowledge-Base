"""
The five phases the CEO gave: pre-planting, planting, post-planting, harvest and post-harvest.
Most jobs take the phase of their group. Irrigation and pruning are single jobs inside
"something else", so their phase is set on the job. Jobs the CEO has not placed yet have none.
"""

import pytest

from engine import taxonomy

PHASES = ["pre_planting", "planting", "post_planting", "harvest", "post_harvest"]


def categories():
    return {c["id"]: c for c in taxonomy.taxonomy()["categories"]}


def test_the_five_phases_are_listed_in_order():
    assert [p["id"] for p in taxonomy.taxonomy()["phases"]] == PHASES


@pytest.mark.parametrize("category, phase", [
    ("land_preparation", "pre_planting"), ("planting", "planting"),
    ("weeding", "post_planting"), ("fertilizer_application", "post_planting"), ("pest_control", "post_planting"),
    ("harvesting", "harvest"),
    ("sorting_grading", "post_harvest"), ("cleaning_drying", "post_harvest"), ("processing", "post_harvest"), ("storage", "post_harvest"),
])
def test_each_job_group_is_in_the_phase_the_ceo_gave(category, phase):
    assert categories()[category]["phase"] == phase


def test_the_catch_all_group_has_no_phase_of_its_own():
    assert categories()["other"]["phase"] is None


def test_irrigation_and_pruning_are_post_planting_as_the_ceo_corrected():
    # Irrigation follows planting or seeding and continues through growth. Pruning is done in
    # early growth and during growth (and again after harvest for trees), so it sits here too.
    assert taxonomy.phase_for("maize", "irrigation") == "post_planting"
    assert taxonomy.phase_for("cocoa", "pruning") == "post_planting"


@pytest.mark.parametrize("operation, phase", [
    ("land_clearing", "pre_planting"), ("land_preparation", "pre_planting"), ("planting", "planting"), ("transplanting", "planting"),
    ("nursery_establishment", "planting"), ("weeding_1", "post_planting"), ("first_fertilizer", "post_planting"),
    ("pest_disease_control", "post_planting"), ("reridging", None), ("harvest", "harvest"), ("tapping", "harvest"),
    ("drying", "post_harvest"), ("milling", "post_harvest"), ("storage", "post_harvest"),
])
def test_jobs_take_the_phase_of_their_group(operation, phase):
    assert taxonomy.phase_for(None, operation) == phase


def test_a_job_with_no_mapping_has_no_phase():
    assert taxonomy.phase_for("maize", "not_a_real_operation") is None


def test_every_phase_used_is_a_listed_phase():
    data = taxonomy.taxonomy()
    used = {c["phase"] for c in data["categories"] if c["phase"]} | {e["phase"] for e in data["operations"].values() if e.get("phase")}
    assert used <= set(PHASES)


def test_only_jobs_in_the_catch_all_group_lack_a_phase_and_each_is_listed_as_open():
    data = taxonomy.taxonomy()
    without = sorted(op for op in data["operations"] if taxonomy.phase_for(None, op) is None)
    assert without == sorted(data["approval"]["phases_still_open"])
    assert all(data["operations"][op]["signal_category"] == "other" for op in without)


def test_the_phase_is_part_of_what_the_api_serves():
    from fastapi.testclient import TestClient

    from api.main import app

    body = TestClient(app).get("/v1/taxonomy").json()
    assert [p["id"] for p in body["phases"]] == PHASES
    assert {c["id"]: c["phase"] for c in body["categories"]}["harvesting"] == "harvest"
