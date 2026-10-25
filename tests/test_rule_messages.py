"""The rule text farmers see must never carry developer notes."""
import json
from pathlib import Path

CROPS = Path(__file__).resolve().parent.parent / "knowledge_base" / "crops"
INTERNAL_MARKERS = ("PLATFORM BUGFIX", "second sweep", "bugfix", "audit")


def _rules(obj):
    if isinstance(obj, dict):
        if "condition" in obj:
            yield obj
        for v in obj.values():
            yield from _rules(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _rules(v)


def test_no_condition_carries_a_developer_note():
    bad = []
    for path in sorted(CROPS.glob("*.json")):
        for rule in _rules(json.loads(path.read_text())):
            text = rule["condition"].lower()
            if any(m.lower() in text for m in INTERNAL_MARKERS):
                bad.append((path.name, rule.get("rule_id")))
    assert not bad, bad
