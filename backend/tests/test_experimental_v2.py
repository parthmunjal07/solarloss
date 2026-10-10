import json

import pytest
from conftest import MemoryReviewStore, synthetic_experimental_v2_review
from solarloss_backend.application import ReviewApplication
from solarloss_backend.errors import InvalidArtifact
from solarloss_backend.report import render_review_report
from solarloss_backend.schema import load_review, load_versioned_review


def _load_v2(review):
    return load_versioned_review(json.dumps(review).encode("utf-8"), allow_experimental_v2=True)


def _event(path):
    return {"rawPath": path, "requestContext": {"http": {"method": "GET"}}}


def test_proposed_schema_is_copied_unchanged_from_science_contract(proposed_v2_schema_path):
    source = (
        proposed_v2_schema_path.parents[2]
        / "analysis"
        / "contracts"
        / ("review.schema.v0.2.0.proposed.json")
    )
    assert proposed_v2_schema_path.read_bytes() == source.read_bytes()


def test_version_dispatch_requires_explicit_experimental_opt_in():
    raw = json.dumps(synthetic_experimental_v2_review()).encode("utf-8")
    with pytest.raises(InvalidArtifact, match="proposed experimental contract"):
        load_review(raw)
    loaded = load_versioned_review(raw, allow_experimental_v2=True)
    assert loaded["schema_version"] == "0.2.0"
    assert loaded["approval_status"] == "proposed"


def test_version_dispatch_rejects_unknown_schema_versions():
    review = synthetic_experimental_v2_review()
    review["schema_version"] = "0.3.0"
    with pytest.raises(InvalidArtifact, match="Unsupported review schema version"):
        load_versioned_review(json.dumps(review).encode("utf-8"), allow_experimental_v2=True)


def test_experimental_path_rejects_unrecorded_owner_approval_claim():
    review = synthetic_experimental_v2_review()
    review["approval_status"] = "owner_approved"
    with pytest.raises(InvalidArtifact, match="no recorded science-owner approval"):
        _load_v2(review)


def test_production_api_does_not_serve_or_render_proposed_v2():
    review = synthetic_experimental_v2_review()
    store = MemoryReviewStore({"synthetic-v2": json.dumps(review).encode("utf-8")})
    app = ReviewApplication(store)
    response = app.handle_event(_event("/api/v1/reviews/synthetic-v2"), "req-v2-gate")
    assert response["statusCode"] == 500
    assert json.loads(response["body"])["error"]["code"] == "invalid_review_artifact"
    assert store.saved_reports == {}
    with pytest.raises(InvalidArtifact, match="explicit experimental rendering"):
        render_review_report(review)


def test_experimental_v2_accepts_negative_signed_energy_and_unavailable_metrics():
    review = _load_v2(synthetic_experimental_v2_review())
    by_id = {metric["id"]: metric for metric in review["metrics"]}
    assert by_id["signed_generation_deviation"]["value"] == -0.25
    assert by_id["expected_energy"]["availability"] == "unavailable"
    assert by_id["expected_energy"]["value"] is None
    assert by_id["expected_energy"]["reason"]


def test_positive_only_energy_cannot_be_negative():
    review = synthetic_experimental_v2_review()
    next(item for item in review["metrics"] if item["id"] == "positive_only_generation_deviation")[
        "value"
    ] = -0.01
    with pytest.raises(InvalidArtifact, match="less than the minimum of 0"):
        _load_v2(review)


def test_metrics_must_have_unique_ids():
    review = synthetic_experimental_v2_review()
    review["metrics"].append(dict(review["metrics"][0]))
    with pytest.raises(InvalidArtifact, match="unique metric identifiers"):
        _load_v2(review)


def test_unavailable_metric_requires_null_value_and_reason():
    review = synthetic_experimental_v2_review()
    target = next(item for item in review["metrics"] if item["id"] == "expected_energy")
    target["value"] = 0
    with pytest.raises(InvalidArtifact, match="not of type 'null'"):
        _load_v2(review)

    target["value"] = None
    target["reason"] = None
    with pytest.raises(InvalidArtifact, match="not of type 'string'"):
        _load_v2(review)


def test_estimated_metric_requires_finite_value_and_null_reason():
    review = synthetic_experimental_v2_review()
    target = next(item for item in review["metrics"] if item["id"] == "signed_generation_deviation")
    target["reason"] = "SYNTHETIC not allowed for estimated value"
    with pytest.raises(InvalidArtifact, match="not of type 'null'"):
        _load_v2(review)


def test_v2_rejects_nonfinite_json_numbers():
    review = synthetic_experimental_v2_review()
    raw = json.dumps(review).replace('"value": -0.25', '"value": NaN').encode("utf-8")
    with pytest.raises(InvalidArtifact, match="valid UTF-8 JSON"):
        load_versioned_review(raw, allow_experimental_v2=True)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda review: review["metrics"][5]["uncertainty"].update(lower=0.3, upper=-0.2),
            "lower cannot exceed upper",
        ),
        (
            lambda review: review["metrics"][0]["coverage"].update(observed_labelled_seconds=121.0),
            "cannot exceed wall_span_seconds",
        ),
        (
            lambda review: review["experiment"].update(identifier="another-id"),
            "review_id must equal",
        ),
        (
            lambda review: review["candidate_checks"][0].update(status="owner_approved"),
            "cannot be owner_approved",
        ),
        (
            lambda review: review["provenance"]["source_checksums"][0].update(sha256="bad"),
            "lowercase SHA256 digest",
        ),
        (
            lambda review: review["series"]["samples"][0].update(
                timestamp="2026-10-09T10:00:00+05:30"
            ),
            "must use UTC",
        ),
        (
            lambda review: review["series"]["samples"][1].update(timestamp="2026-10-09T09:00:00Z"),
            "strictly increasing",
        ),
    ],
)
def test_v2_cross_field_and_provenance_invariants_are_enforced(mutate, message):
    review = synthetic_experimental_v2_review()
    mutate(review)
    with pytest.raises(InvalidArtifact, match=message):
        _load_v2(review)


def test_v2_report_separates_measurement_and_estimate_and_escapes_input():
    review = synthetic_experimental_v2_review()
    review["candidate_checks"][0]["observed_fact"] = '<script>alert("fixture")</script>'
    loaded = _load_v2(review)
    report = render_review_report(loaded, allow_experimental_v2=True)
    assert "EXPERIMENTAL — PROPOSED CONTRACT" in report
    assert "Measured experimental power" in report
    assert "Model-expected power" in report
    assert "Positive-only generation deviation (not recovered energy)" in report
    assert "Unavailable — SYNTHETIC test missing expected-energy value." in report
    assert "proposed investigation prompts, not diagnoses" in report
    assert "SYNTHETIC next information." in report
    assert "SYNTHETIC qualification boundary." in report
    assert "https://example.invalid/synthetic-source" in report
    assert "Content-Security-Policy" in report
    assert "&lt;script&gt;alert(&quot;fixture&quot;)&lt;/script&gt;" in report
    assert "<script>alert(" not in report


def test_unavailable_candidate_check_is_labeled_in_preview():
    review = synthetic_experimental_v2_review()
    review["candidate_checks"][0]["status"] = "unavailable"
    report = render_review_report(_load_v2(review), allow_experimental_v2=True)
    assert "unavailable" in report
    assert "Suppressed because this candidate check is unavailable." in report
    assert "SYNTHETIC candidate hypothesis only." not in report
    assert "proposed investigation prompts, not diagnoses" in report


def test_experimental_compatibility_command_renders_offline_report(tmp_path):
    from backend.validate_artifact import validate_experimental_v2_artifact

    artifact = tmp_path / "review_synthetic-v2.json"
    artifact.write_text(json.dumps(synthetic_experimental_v2_review()), encoding="utf-8")
    report = tmp_path / "experimental-preview.html"
    assert validate_experimental_v2_artifact(artifact, report) == []
    rendered = report.read_text(encoding="utf-8")
    assert "EXPERIMENTAL — PROPOSED CONTRACT" in rendered
    assert "SYNTHETIC TEST POPULATION ONLY" in rendered


def test_experimental_compatibility_command_cannot_overwrite_source(tmp_path):
    from backend.validate_artifact import validate_experimental_v2_artifact

    artifact = tmp_path / "review_synthetic-v2.json"
    artifact.write_text(json.dumps(synthetic_experimental_v2_review()), encoding="utf-8")
    assert validate_experimental_v2_artifact(artifact, artifact) == [
        "Experimental HTML report output cannot overwrite the source artifact."
    ]
