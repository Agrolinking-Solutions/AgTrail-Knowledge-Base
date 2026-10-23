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
