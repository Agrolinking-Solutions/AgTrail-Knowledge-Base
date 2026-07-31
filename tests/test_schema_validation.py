"""
Automated version of scripts/validate_crops.py, so validation runs as part of
the normal test suite (pytest) instead of relying on someone remembering to
run the script by hand.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from validate_crops import (  # noqa: E402
    CROPS_DIR,
    SCHEMA_PATH,
    Draft202012Validator,
    check_cross_references,
    check_schema,
    load_json,
)

CROP_FILES = sorted(CROPS_DIR.glob("*.json"))


@pytest.fixture(scope="module")
def validator():
    schema = load_json(SCHEMA_PATH)
    return Draft202012Validator(schema)


def test_crop_files_exist():
    assert CROP_FILES, f"No crop files found in {CROPS_DIR}"


@pytest.mark.parametrize("crop_file", CROP_FILES, ids=lambda p: p.stem)
def test_crop_matches_schema(crop_file, validator):
    crop_data = load_json(crop_file)
    errors = check_schema(crop_data, validator)
    assert not errors, "\n".join(errors)


@pytest.mark.parametrize("crop_file", CROP_FILES, ids=lambda p: p.stem)
def test_crop_cross_references(crop_file):
    crop_data = load_json(crop_file)
    errors = check_cross_references(crop_data)
    assert not errors, "\n".join(errors)
