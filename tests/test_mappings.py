"""
Checks for knowledge_base/mappings/: the crop-to-PIS-commodity map and the
state-to-zone map. They are data, so these tests only guard their shape and
that nothing drifts from the crop files.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAPPINGS = ROOT / "knowledge_base" / "mappings"
CROPS_DIR = ROOT / "knowledge_base" / "crops"

PIS_COMMODITIES = {
    "Hibiscus", "Sesame", "Ginger", "Cocoa", "Soybeans", "Cashew Nuts", "Sorghum",
    "Beans (white)", "Beans (red)", "Maize (white)", "Maize (yellow)", "Wheat",
    "Rice", "Rice (local)", "Rice (foreign)", "Meat (beef)", "Meat (goat)",
    "Fish (dried)", "Eggs",
    # Farm crops, added by PIS on 28 Oct 2026 (price only, no forecast; market prices, not farm-gate).
    "Yam", "Groundnut", "Tomato", "Sweet potato", "Onion", "Pepper",
}
GEO_ZONES = {"North West", "North East", "North Central", "South West", "South East", "South South"}
KB_AGRO_ZONES = {"Nigeria - Guinea Savanna", "Nigeria - Sudan Savanna"}


def _load(name):
    return json.loads((MAPPINGS / name).read_text())


def test_every_crop_file_has_exactly_one_commodity_row():
    crop_ids = {p.stem for p in CROPS_DIR.glob("*.json")}
    rows = [r["crop_id"] for r in _load("commodities.json")["crops"]]
    assert sorted(rows) == sorted(set(rows)), "a crop appears twice"
    assert set(rows) == crop_ids


def test_commodity_rows_are_consistent():
    for row in _load("commodities.json")["crops"]:
        if row["price_status"] == "priced":
            assert row["pis_commodity"] in PIS_COMMODITIES, row["crop_id"]
        else:
            assert row["price_status"] == "unpriced", row["crop_id"]
            assert row["pis_commodity"] is None and row["conversion_factor"] is None, row["crop_id"]
        factor = row["conversion_factor"]
        assert factor is None or 0 < factor <= 1.5, row["crop_id"]
        assert row["conversion_note"], row["crop_id"]


def test_unsourced_conversions_are_never_filled_with_a_guess():
    by_crop = {r["crop_id"]: r for r in _load("commodities.json")["crops"]}
    # Rice needs a milling factor (PIS prices milled rice, our yield is paddy) and groundnut needs a shelling
    # percentage (PIS prices shelled nuts, our yield is in-shell); neither is sourced.
    assert by_crop["rice"]["conversion_factor"] is None
    assert by_crop["groundnut"]["conversion_factor"] is None
    assert "shelling" in by_crop["groundnut"]["conversion_note"].lower()
    # Cowpea is dry grain on both sides, which PIS confirmed on 28 Oct 2026.
    assert by_crop["cowpea"]["conversion_factor"] == 1.0


def test_every_new_farm_crop_price_is_labelled_a_market_price():
    by_crop = {r["crop_id"]: r for r in _load("commodities.json")["crops"]}
    for crop in ("yam", "tomato", "pepper", "onion", "ofsp", "cowpea", "groundnut"):
        assert "market price, not a farm-gate price" in by_crop[crop]["conversion_note"].lower(), crop


def test_regions_cover_all_36_states_and_the_fct():
    states = _load("regions.json")["states"]
    names = [s["state"] for s in states]
    assert len(names) == 37 and len(set(names)) == 37
    assert "FCT" in names


def test_regions_use_only_known_zone_names():
    for s in _load("regions.json")["states"]:
        assert s["geo_zone"] in GEO_ZONES, s["state"]
        assert s["agro_zone"] is None or s["agro_zone"] in KB_AGRO_ZONES, s["state"]


def test_pis_price_states_match_the_twelve_pis_covers():
    covered = {s["state"] for s in _load("regions.json")["states"] if s["has_pis_state_prices"]}
    assert covered == {
        "Kano", "Kaduna", "Plateau", "Kogi", "Adamawa", "Borno",
        "Oyo", "Lagos", "Anambra", "Imo", "Rivers", "Delta",
    }


def test_every_assigned_agro_zone_is_flagged_unverified():
    for s in _load("regions.json")["states"]:
        if s["agro_zone"]:
            assert s["agro_zone_review_status"] == "UNVERIFIED", s["state"]
