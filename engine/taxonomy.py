"""
The shared list of farm operation types, and the read-only mapping files the
monitoring hub and PIS fetch (taxonomy, crop-to-commodity, state-to-zone).

Pure functions over the JSON files in knowledge_base/mappings/. No HTTP and no
database, like the rest of engine/.
"""

from __future__ import annotations

import hashlib
import json
import os
from functools import lru_cache
from importlib import metadata
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_BASE_DIR = ROOT / "knowledge_base"
MAPPINGS_DIR = KNOWLEDGE_BASE_DIR / "mappings"

FALLBACK_VERSION = "0.1.0"


@lru_cache(maxsize=None)
def _load_mapping(name: str) -> dict:
    with (MAPPINGS_DIR / name).open(encoding="utf-8") as f:
        return json.load(f)


def taxonomy() -> dict:
    """The 11 shared categories and the operation_id mapping, as the API serves it."""
    return _load_mapping("signal_categories.json")


def commodities() -> dict:
    return _load_mapping("commodities.json")


def regions() -> dict:
    return _load_mapping("regions.json")


def crop_steps(crop_id: str) -> dict:
    """
    The steps a crop's rules know about, in workflow order, each with its shared
    signal category. This is what lets a caller that only knows broad categories
    ("weeding") work out which step a logged operation is ("weeding_1").
    Raises CropNotFoundError for a crop with no file.
    """
    from .loader import load_crop

    crop = load_crop(crop_id)
    names = {op["operation_id"]: op["name"] for op in crop.get("operations", [])}
    steps = []
    for step in sorted(crop.get("workflow", []), key=lambda w: w["step_number"]):
        operation_id = step["operation_id"]
        steps.append(
            {
                "step_number": step["step_number"],
                "operation_id": operation_id,
                "name": names.get(operation_id, operation_id),
                "signal_category": signal_category_for(crop_id, operation_id),
                "required": bool(step.get("required", False)),
            }
        )
    return {"crop_id": crop_id, "steps": steps}


def harvest_estimate(crop_id: str) -> dict:
    """
    What a farm of this crop typically harvests, with its sources, or {"available": False} when the
    crop has no current research behind it yet. Raises CropNotFoundError for a crop with no file.
    """
    from .loader import load_crop

    block = load_crop(crop_id).get("harvest_estimate")
    if not block:
        return {"crop_id": crop_id, "available": False, "reason": "No current research is recorded for this crop yet, so no estimate is given."}
    return {"crop_id": crop_id, "available": True, **block}


def soil_match(crop_id: str, soil: Optional[str]) -> dict:
    """
    How the soil AgTrail recorded for a farm compares with what the crop prefers. Status is one of:
    preferred (the crop's own list names it), avoid (the crop file says the crop does badly on it),
    not_listed (a known soil the crop file neither names nor warns against: no effect), or unknown
    (no soil recorded, or a word we cannot place). Only `avoid` should change a number.
    Raises CropNotFoundError for a crop with no file.
    """
    from .loader import load_crop

    req = load_crop(crop_id).get("soil_requirements", {})
    preferred = list(req.get("texture", []))
    avoid = list(req.get("texture_avoid", []))
    out = {"crop_id": crop_id, "soil": soil, "texture": None, "preferred": preferred, "avoid": avoid}
    key = (soil or "").strip().lower().replace(" ", "_").replace("-", "_")
    texture = _load_mapping("soil_types.json")["soils"].get(key)
    if texture is None:
        return {**out, "status": "unknown", "note": "No usable soil type is recorded for this farm, so the soil is not taken into account."}
    out["texture"] = texture
    if texture in avoid:
        return {**out, "status": "avoid", "note": f"The crop file says {crop_id} does badly on {texture} soil."}
    if texture in preferred or (preferred and preferred[0].startswith("any except")):
        return {**out, "status": "preferred", "note": f"{texture.capitalize()} is a soil this crop does well on."}
    return {**out, "status": "not_listed", "note": f"{texture.capitalize()} is neither listed as preferred nor warned against for this crop, so it does not change the estimate."}


def signal_categories() -> list[str]:
    return [c["id"] for c in taxonomy()["categories"]]


def signal_category_for(crop_id: Optional[str], operation_id: str) -> Optional[str]:
    """
    The shared category for an operation, or None when the operation_id has no
    mapping yet. A crop can override the default for one operation through
    crop_overrides, for example {"rubber": {"tapping": "harvesting"}}.
    """
    data = taxonomy()
    if crop_id:
        override = data.get("crop_overrides", {}).get(crop_id, {}).get(operation_id)
        if override:
            return override
    entry = data["operations"].get(operation_id)
    return entry["signal_category"] if entry else None


def phase_for(crop_id: Optional[str], operation_id: str) -> Optional[str]:
    """
    The phase of a job (pre_planting, planting, post_planting, harvest or post_harvest), or None
    when the job has no mapping or its phase has not been decided yet. A job can name its own
    phase; otherwise it takes the phase of its category.
    """
    data = taxonomy()
    entry = data["operations"].get(operation_id)
    if entry is None:
        return None
    if entry.get("phase"):
        return entry["phase"]
    category = signal_category_for(crop_id, operation_id)
    return next((c.get("phase") for c in data["categories"] if c["id"] == category), None)


def data_hash(root: Path = KNOWLEDGE_BASE_DIR) -> str:
    """
    A short fingerprint of every crop file, the schema and the mapping files.
    It changes whenever the knowledge base data changes, so anything that
    stamps results with the version knows when to recompute them.
    """
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.json")):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:10]


@lru_cache(maxsize=None)
def kb_version() -> str:
    """Package version plus the data fingerprint, for example 0.1.0+3fa9c01b2e."""
    try:
        base = metadata.version("agtrail-knowledge-base")
    except metadata.PackageNotFoundError:
        base = FALLBACK_VERSION
    return f"{base}+{data_hash()}"


def source_commit() -> Optional[str]:
    """The git commit this build came from, when the platform provides it."""
    commit = os.environ.get("SOURCE_COMMIT") or os.environ.get("GIT_COMMIT")
    return commit[:12] if commit else None
