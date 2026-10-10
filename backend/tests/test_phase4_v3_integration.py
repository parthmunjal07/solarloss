import hashlib
import json
import math
from pathlib import Path

import pytest
from conftest import MemoryReviewStore, synthetic_experimental_v2_review
from solarloss_backend.application import ReviewApplication
from solarloss_backend.errors import InvalidArtifact
from solarloss_backend.report import render_review_report
from solarloss_backend.schema import load_versioned_review

ROOT = Path(__file__).resolve().parents[2]
REVIEWS = ROOT / "analysis" / "results" / "reviews_v3"
SHADING_PATH = REVIEWS / "review_shading_01.json"
HEALTHY_PATH = REVIEWS / "review_healthy_20220126_0300.json"
GAP_PATH = REVIEWS / "review_insufficient_data_gap_20211222_20220124.json"
V02_SCHEMA_PATH = ROOT / "artifacts" / "schema" / "review.schema.v0.2.0.proposed.json"


def _read_candidate(path: Path) -> tuple[bytes, dict]:
    raw = path.read_bytes()
    review = load_versioned_review(raw, allow_experimental_v2=True)
    return raw, review


@pytest.mark.parametrize(
    ("path", "experiment_id", "experiment_type"),
    [
        (SHADING_PATH, "shading_01", "documented_shading"),
        (HEALTHY_PATH, "healthy_20220126_0300", "healthy_stability"),
    ],
)
def test_original_v3_reviews_validate_without_rewriting(path, experiment_id, experiment_type):
    raw, review = _read_candidate(path)
    source_object = json.loads(raw)
    assert review == source_object
    assert review["schema_version"] == "0.2.0"
    assert review["approval_status"] == "proposed"
    assert review["experiment"]["identifier"] == experiment_id
    assert review["review_id"] == f"review_{experiment_id}"
    assert path.name == f"review_{experiment_id}.json"
    assert review["experiment"]["type"] == experiment_type


def test_shading_01_real_source_metrics_reconcile_exactly():
    _, review = _read_candidate(SHADING_PATH)
    metrics = {item["id"]: item for item in review["metrics"]}
    assert metrics["observed_energy"]["value"] == 2.381648888888889
    assert metrics["expected_energy"]["value"] == 2.778697866302768
    assert metrics["signed_generation_deviation"]["value"] == 0.39704897741387934
    assert metrics["positive_only_generation_deviation"]["value"] == 0.3971261454108439
    assert metrics["signed_generation_deviation"]["coverage"]["valid_seconds"] == 10549
    assert metrics["signed_generation_deviation"]["coverage"]["observed_labelled_seconds"] == 10734
    assert math.isclose(
        metrics["expected_energy"]["value"] - metrics["observed_energy"]["value"],
        metrics["signed_generation_deviation"]["value"],
        rel_tol=1e-12,
        abs_tol=1e-12,
    )
    assert metrics["positive_only_generation_deviation"]["value"] >= 0
    uncertainty = metrics["signed_generation_deviation"]["uncertainty"]
    assert uncertainty["kind"] == "empirical_model_error_band"
    assert uncertainty["lower"] == 0.37014211825708937
    assert uncertainty["upper"] == 0.3948064694632774
    assert "not a confidence interval" in " ".join(uncertainty["limitations"]).lower()


def test_shading_01_keeps_research_verdict_event_state_and_timestamps_separate():
    _, review = _read_candidate(SHADING_PATH)
    context = review["experiment"]["event_context"]
    decision = review["decision"]
    assert decision["verdict"] == "LIMIT"
    assert decision["event_review"]["availability"] == "unavailable"
    assert decision["event_review"]["state"] is None
    assert decision["event_review"]["reason"]
    assert context["label_interval_utc"]["start"] == "2022-02-08T07:11:02Z"
    assert context["label_interval_utc"]["end"] == "2022-02-08T10:09:56Z"
    assert context["detector_confirmations_utc"]["5_minute_primary"] == "2022-02-08T07:20:00Z"
    assert (
        context["detector_confirmations_utc"]["5_minute_primary"]
        != context["label_interval_utc"]["start"]
    )
    assert review["provenance"]["grouping"]["event_review_decision"] == decision["event_review"]
    assert review["provenance"]["grouping"]["label_interval"] == context["label_interval_utc"]


def test_shading_samples_preserve_unavailable_expected_values_and_source_scope():
    _, review = _read_candidate(SHADING_PATH)
    samples = review["series"]["samples"]
    assert len(samples) == 2148
    assert sum(sample["valid"] for sample in samples) == 2120
    invalid = [sample for sample in samples if not sample["valid"]]
    assert len(invalid) == 28
    assert all(sample["measured_power"] is not None for sample in invalid)
    assert all(sample["raw_reference_power"] is not None for sample in invalid)
    assert all(sample["expected_power"] is None for sample in invalid)
    checksums = review["provenance"]["source_checksums"]
    assert len({item["file"] for item in checksums}) == len(checksums)
    raw_sources = [
        item for item in checksums if item["role"] == "pinned Zenodo record 7291380 source file"
    ]
    committed_inputs = [item for item in checksums if item["role"] == "committed V2 analysis input"]
    assert raw_sources and all(
        "not rehashed by this exporter" in item["source_verification"] for item in raw_sources
    )
    assert committed_inputs and all(
        "rehashed by this exporter" in item["source_verification"] for item in committed_inputs
    )


def test_healthy_example_retains_zero_label_and_calibration_caveats():
    _, review = _read_candidate(HEALTHY_PATH)
    context = review["experiment"]["event_context"]
    assert context["detector_calibration_population"] is True
    assert context["label_interval_utc"] is None
    assert "not proof" in context["label_source"].lower()
    assert "not an independent" in context["note"].lower()
    assert len(review["series"]["samples"]) == 12
    assert review["decision"]["verdict"] == "LIMIT"
    assert review["decision"]["event_review"]["state"] is None


def test_data_gap_sidecar_is_not_a_v02_review_or_production_listing_entry():
    sidecar = json.loads(GAP_PATH.read_text(encoding="utf-8"))
    assert sidecar["gap_seconds"] == 2848806.0
    assert sidecar["energy_deviation"]["availability"] == "unavailable"
    assert sidecar["energy_deviation"]["value"] is None
    assert sidecar["source_gap_utc"]["previous_observation"]
    assert sidecar["source_gap_utc"]["next_observation"]
    with pytest.raises(InvalidArtifact, match="Unsupported review schema version"):
        load_versioned_review(GAP_PATH.read_bytes(), allow_experimental_v2=True)


def test_actual_v3_review_is_rejected_by_the_production_lambda_api_until_approval():
    store = MemoryReviewStore({"shading_01": SHADING_PATH.read_bytes()})
    app = ReviewApplication(store)
    review_response = app.handle_event(
        {"rawPath": "/api/v1/reviews/shading_01", "requestContext": {"http": {"method": "GET"}}},
        "req-v3-review-gate",
    )
    report_response = app.handle_event(
        {
            "rawPath": "/api/v1/reviews/shading_01/report",
            "requestContext": {"http": {"method": "GET"}},
        },
        "req-v3-report-gate",
    )
    assert review_response["statusCode"] == 500
    assert json.loads(review_response["body"])["error"]["code"] == "invalid_review_artifact"
    assert report_response["statusCode"] == 500
    assert json.loads(report_response["body"])["error"]["code"] == "invalid_review_artifact"
    assert store.saved_reports == {}


def test_approved_schema_hash_gate_serves_v02_api_shape_without_mapping_limit_to_event_state():
    review = json.loads(SHADING_PATH.read_text(encoding="utf-8"))
    schema_sha256 = hashlib.sha256(V02_SCHEMA_PATH.read_bytes()).hexdigest()
    review["approval_status"] = "owner_approved"
    review["decision"]["owner_review"] = {
        "approver": "SYNTHETIC TEST APPROVER; not Rachit and not a real signoff",
        "approved_at": "2026-10-10T00:00:00Z",
        "schema_version": "0.2.0",
        "schema_sha256": schema_sha256,
        "protocol_sha256": review["provenance"]["protocol_sha256"],
        "decision_reference": "SYNTHETIC_TEST_ONLY",
        "scope": "SYNTHETIC test record only; no detector, diagnosis, or maintenance approval.",
    }
    raw = json.dumps(review).encode("utf-8")
    store = MemoryReviewStore({"shading_01": raw})
    app = ReviewApplication(store, approved_v02_schema_sha256=schema_sha256)

    response = app.handle_event(
        {"rawPath": "/api/v1/reviews/shading_01", "requestContext": {"http": {"method": "GET"}}},
        "req-v3-approved-review-shape",
    )
    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == review

    listing = app.handle_event(
        {"rawPath": "/api/v1/experiments", "requestContext": {"http": {"method": "GET"}}},
        "req-v3-approved-list-shape",
    )
    item = json.loads(listing["body"])["experiments"][0]
    assert listing["statusCode"] == 200
    assert item["schema_version"] == "0.2.0"
    assert item["research_verdict"] == "LIMIT"
    assert item["event_review"]["availability"] == "unavailable"
    assert item["event_review"]["state"] is None
    assert "decision_state" not in item

    report_response = app.handle_event(
        {
            "rawPath": "/api/v1/reviews/shading_01/report",
            "requestContext": {"http": {"method": "GET"}},
        },
        "req-v3-approved-report-shape",
    )
    assert report_response["statusCode"] == 302
    report = store.saved_reports["shading_01"]
    assert "Research verdict (experiment/capability scope): LIMIT" in report
    assert "Event review state" in report
    assert "unavailable" in report
    assert "EXPERIMENTAL — PROPOSED CONTRACT" not in report
    assert "not Rachit and not a real signoff" in report


def test_original_shading_review_local_report_shows_both_decision_levels_and_times():
    _, review = _read_candidate(SHADING_PATH)
    report = render_review_report(review, allow_experimental_v2=True)
    assert "Research verdict (experiment/capability scope)" in report
    assert "Event review availability" in report
    assert "LIMIT" in report
    assert "unavailable" in report
    assert "2022-02-08T07:11:02Z" in report
    assert "2022-02-08T07:20:00Z" in report
    assert "not causal loss or recovery" in report
    assert "not recoverable energy" in report
    assert "proposed investigation prompts, not diagnoses" in report


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda review: review["metrics"][1]["ratio"].update(numerator=22.0),
            "ratio numerator divided by denominator must equal value",
        ),
        (
            lambda review: review["provenance"]["grouping"]["detector_confirmations"].update(
                {"5_minute_primary": "2022-02-08T07:19:00Z"}
            ),
            "detector confirmations must match",
        ),
        (
            lambda review: review["series"]["samples"][0].update(expected_power=None),
            "valid cannot be true",
        ),
        (
            lambda review: review["provenance"]["source_checksums"][0].update(
                source_verification="rehashed by exporter"
            ),
            "not one of",
        ),
    ],
)
def test_real_artifact_mutations_fail_candidate_validation(mutate, message):
    review = json.loads(SHADING_PATH.read_text(encoding="utf-8"))
    mutate(review)
    with pytest.raises(InvalidArtifact, match=message):
        load_versioned_review(json.dumps(review).encode("utf-8"), allow_experimental_v2=True)


def test_unavailable_and_not_applicable_metric_states_are_not_zero():
    review = synthetic_experimental_v2_review()
    target = next(item for item in review["metrics"] if item["id"] == "healthy_bias")
    target["availability"] = "not_applicable"
    target["value"] = None
    target["reason"] = "SYNTHETIC out-of-scope metric."
    loaded = load_versioned_review(json.dumps(review).encode("utf-8"), allow_experimental_v2=True)
    assert next(item for item in loaded["metrics"] if item["id"] == "healthy_bias")["value"] is None
    target["value"] = 0.0
    with pytest.raises(InvalidArtifact, match="not of type 'null'"):
        load_versioned_review(json.dumps(review).encode("utf-8"), allow_experimental_v2=True)
