import json

import pytest
from conftest import synthetic_review
from jsonschema import Draft202012Validator
from solarloss_backend.errors import InvalidArtifact
from solarloss_backend.schema import load_review


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


def test_schema_is_valid_draft_2020_12(schema_path):
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)


def test_ordered_window_and_optional_uncertainty_are_valid(schema_path):
    review = synthetic_review()
    review["uncertainty"].pop("interval")
    review["series"]["samples"][0].pop("expected_lower_bound")
    review["series"]["samples"][0].pop("expected_upper_bound")
    loaded = load_review(json.dumps(review).encode("utf-8"), schema_path)
    assert loaded["uncertainty"].get("interval") is None
    assert "expected_lower_bound" not in loaded["series"]["samples"][0]


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda review: review["experiment"]["time_window"].update(start="2026-10-09T11:00:00Z"),
            "time_window.start must be earlier",
        ),
        (
            lambda review: review["series"]["samples"][1].update(timestamp="2026-10-09T09:30:00Z"),
            "timestamps must be strictly increasing",
        ),
        (
            lambda review: review["metrics"].update(valid_interval_count=11),
            "valid_interval_count cannot exceed",
        ),
        (
            lambda review: review["uncertainty"]["interval"].update(lower=25.0, upper=24.0),
            "interval.lower cannot exceed",
        ),
        (
            lambda review: review["series"]["samples"][0].update(
                expected_lower_bound=471.0, expected_upper_bound=470.0
            ),
            "expected_lower_bound cannot exceed",
        ),
        (
            lambda review: review["exclusions"][0].update(
                start="2026-10-09T10:35:00Z", end="2026-10-09T10:30:00Z"
            ),
            r"exclusions\[0\].start must be earlier",
        ),
    ],
)
def test_structural_invariants_are_rejected(schema_path, mutate, message):
    review = synthetic_review()
    mutate(review)
    with pytest.raises(InvalidArtifact, match=message):
        load_review(json.dumps(review).encode("utf-8"), schema_path)


def test_invalid_experiment_identifier_is_rejected_by_schema(schema_path):
    review = synthetic_review()
    review["experiment"]["identifier"] = "../escape"
    with pytest.raises(InvalidArtifact, match="Schema validation failed at experiment.identifier"):
        load_review(json.dumps(review).encode("utf-8"), schema_path)


def test_required_measurements_may_be_null_for_invalid_sample(schema_path):
    review = synthetic_review()
    sample = review["series"]["samples"][1]
    assert sample["valid"] is False
    assert sample["measured_power"] is None
    assert sample["raw_reference_power"] is None
    assert sample["expected_power"] is None
    assert (
        load_review(json.dumps(review).encode("utf-8"), schema_path)["series"]["samples"][1]
        == sample
    )


def test_expected_bounds_must_be_both_present_or_both_absent(schema_path):
    review = synthetic_review()
    review["series"]["samples"][0].pop("expected_upper_bound")
    with pytest.raises(InvalidArtifact, match="Schema validation failed at series.samples.0"):
        load_review(json.dumps(review).encode("utf-8"), schema_path)
