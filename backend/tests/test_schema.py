import json

import pytest

from solarloss_backend.errors import InvalidArtifact
from solarloss_backend.schema import load_review

from conftest import synthetic_review


def test_synthetic_fixture_validates_against_contract(schema_path):
    review = synthetic_review()
    assert "SYNTHETIC" in review["dataset"]["name"]
    loaded = load_review(json.dumps(review).encode("utf-8"), schema_path)
    assert loaded["series"]["samples"][0]["raw_reference_power"] == 500.0
    assert loaded["series"]["samples"][0]["expected_power"] == 450.0


def test_schema_rejects_missing_metrics_denominator(schema_path):
    review = synthetic_review()
    del review["metrics"]["coverage"]["denominator"]
    with pytest.raises(InvalidArtifact, match="Schema validation failed"):
        load_review(json.dumps(review).encode("utf-8"), schema_path)


def test_schema_rejects_nonfinite_json_numbers(schema_path):
    raw = json.dumps(synthetic_review()).replace("12.5", "NaN", 1).encode("utf-8")
    with pytest.raises(InvalidArtifact, match="valid UTF-8 JSON"):
        load_review(raw, schema_path)


def test_schema_rejects_overflowed_json_number(schema_path):
    raw = json.dumps(synthetic_review()).replace("12.5", "1e999", 1).encode("utf-8")
    with pytest.raises(InvalidArtifact, match="non-finite"):
        load_review(raw, schema_path)


def test_valid_sample_requires_raw_and_calibrated_series_values(schema_path):
    review = synthetic_review()
    review["series"]["samples"][0]["expected_power"] = None
    with pytest.raises(InvalidArtifact, match="Schema validation failed"):
        load_review(json.dumps(review).encode("utf-8"), schema_path)
