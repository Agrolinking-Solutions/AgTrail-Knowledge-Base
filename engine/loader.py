"""
Loads crop files from knowledge_base/crops/ and applies regional_overrides
patches on top of the base validation_rules when a region is specified.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .exceptions import CropNotFoundError

ROOT = Path(__file__).resolve().parent.parent
CROPS_DIR = ROOT / "knowledge_base" / "crops"


def load_crop(crop_id: str) -> dict:
    path = CROPS_DIR / f"{crop_id}.json"
    if not path.exists():
        available = ", ".join(list_crops()) or "(none found)"
        raise CropNotFoundError(
            f"No crop file for '{crop_id}' at {path}. Available crops: {available}"
        )
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def list_crops() -> list[str]:
    return sorted(p.stem for p in CROPS_DIR.glob("*.json"))


def get_effective_rules(crop_data: dict, region: Optional[str] = None) -> list[dict]:
    """
    Returns validation_rules with any matching regional_overrides patch applied.

    Convention (documented in schema.json): overrides.validation_rules is a
    list of partial patches keyed by rule_id. Only the fields present in the
    patch are overridden; everything else is inherited from the base rule.
    If no region is given, or no override matches, base rules are returned
    unchanged.
    """
    rules_by_id = {r["rule_id"]: dict(r) for r in crop_data.get("validation_rules", [])}

    if region:
        for override in crop_data.get("regional_overrides", []):
            if override.get("region") != region:
                continue
            patches = override.get("overrides", {}).get("validation_rules", [])
            for patch in patches:
                rule_id = patch.get("rule_id")
                if rule_id in rules_by_id:
                    rules_by_id[rule_id].update(
                        {k: v for k, v in patch.items() if k != "rule_id"}
                    )

    return list(rules_by_id.values())
