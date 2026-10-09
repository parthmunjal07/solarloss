import json

import pytest

from conftest import MemoryReviewStore, synthetic_review


def event(path, method="GET", origin=None):
    headers = {"origin": origin} if origin else {}
    return {"rawPath": path, "headers": headers, "requestContext": {"http": {"method": method}}}


def response_json(response):
    return json.loads(response["body"])


def test_health_and_explicit_cors_origin(app):
    response = app.handle_event(event("/api/v1/health", origin="http://localhost:5173"), "req-health")
    assert response["statusCode"] == 200
    assert response_json(response) == {"status": "ok"}
    assert response["headers"]["Access-Control-Allow-Origin"] == "http://localhost:5173"


def test_preflight_rejects_an_unconfigured_origin(app):
    response = app.handle_event(event("/api/v1/reviews/fixture-001", "OPTIONS", "https://attacker.invalid"), "req-cors")
    assert response["statusCode"] == 403
    assert response_json(response)["error"]["code"] == "origin_not_allowed"


def test_experiment_listing_uses_validated_artifact_metadata(app):
    response = app.handle_event(event("/api/v1/experiments"), "req-list")
    assert response["statusCode"] == 200
    item = response_json(response)["experiments"][0]
    assert item["experiment_id"] == "fixture-001"
    assert item["review_id"] == "review_fixture-001"
    assert item["decision_state"] == "supported_change"


def test_valid_review_is_returned_unchanged(app, synthetic_artifact):
    response = app.handle_event(event("/api/v1/reviews/fixture-001"), "req-review")
    assert response["statusCode"] == 200
    assert response_json(response) == synthetic_artifact


@pytest.mark.parametrize("path", [
    "/api/v1/reviews/bad%2Fid",
    "/api/v1/reviews/.hidden",
    "/api/v1/reviews/contains%20space",
])
def test_invalid_review_ids_return_400(app, path):
    response = app.handle_event(event(path), "req-invalid-id")
    assert response["statusCode"] == 400
    assert response_json(response)["error"]["code"] == "invalid_experiment_id"


def test_missing_review_returns_clear_404(app):
    response = app.handle_event(event("/api/v1/reviews/unknown-001"), "req-missing")
    assert response["statusCode"] == 404
    assert response_json(response)["error"] == {
        "code": "review_not_found",
        "message": "No review artifact exists for this experiment",
        "request_id": "req-missing",
    }


def test_malformed_review_is_not_returned(schema_path):
    from solarloss_backend.application import ReviewApplication

    store = MemoryReviewStore({"fixture-001": b"{broken"})
    response = ReviewApplication(store, schema_path=schema_path).handle_event(
        event("/api/v1/reviews/fixture-001"), "req-malformed"
    )
    assert response["statusCode"] == 500
    assert response_json(response)["error"]["code"] == "invalid_review_artifact"


def test_artifact_id_mismatch_is_rejected(schema_path):
    from solarloss_backend.application import ReviewApplication

    review = synthetic_review()
    review["experiment"]["identifier"] = "another-experiment"
    store = MemoryReviewStore({"fixture-001": json.dumps(review).encode("utf-8")})
    response = ReviewApplication(store, schema_path=schema_path).handle_event(
        event("/api/v1/reviews/fixture-001"), "req-mismatch"
    )
    assert response["statusCode"] == 500
    assert response_json(response)["error"]["code"] == "invalid_review_artifact"


@pytest.mark.parametrize("state", ["supported_change", "inconclusive", "insufficient_evidence"])
def test_all_decision_states_are_served_without_backend_inference(state, schema_path):
    from solarloss_backend.application import ReviewApplication

    review = synthetic_review(state)
    store = MemoryReviewStore({"fixture-001": json.dumps(review).encode("utf-8")})
    app = ReviewApplication(store, schema_path=schema_path)
    response = app.handle_event(event("/api/v1/reviews/fixture-001"), "req-state")
    assert response["statusCode"] == 200
    assert response_json(response)["decision"] == review["decision"]


def test_report_is_generated_saved_and_redirected(app, memory_store):
    review_response = app.handle_event(event("/api/v1/reviews/fixture-001"), "req-report-metrics")
    returned_metrics = response_json(review_response)["metrics"]
    response = app.handle_event(event("/api/v1/reviews/fixture-001/report"), "req-report")
    assert response["statusCode"] == 302
    assert response["headers"]["Location"] == "https://reports.example.invalid/fixture-001.html"
    report = memory_store.saved_reports["fixture-001"]
    assert "SYNTHETIC TEST FIXTURE - NOT MEASURED DATA" in report
    assert str(returned_metrics["energy_deficit"]["value"]) in report
    assert str(returned_metrics["deficit_fraction"]["value"]) in report
    assert (
        f"numerator {returned_metrics['deficit_fraction']['numerator']['value']} Wh; "
        f"denominator {returned_metrics['deficit_fraction']['denominator']['value']} Wh"
    ) in report
    assert "500.0" in report
    assert "450.0" in report


def test_report_escapes_artifact_strings(app, memory_store, synthetic_artifact):
    synthetic_artifact["dataset"]["name"] = '<img src=x onerror="alert(1)">'
    synthetic_artifact["dataset"]["source"] = "javascript:alert(1)"
    synthetic_artifact["decision"]["reasons"] = ['<script>alert("test")</script>']
    memory_store.reviews["fixture-001"] = json.dumps(synthetic_artifact).encode("utf-8")
    response = app.handle_event(event("/api/v1/reviews/fixture-001/report"), "req-escape")
    report = memory_store.saved_reports["fixture-001"]
    assert response["statusCode"] == 302
    assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in report
    assert "&lt;script&gt;alert(&quot;test&quot;)&lt;/script&gt;" in report
    assert "<script>alert(" not in report
    assert "<img src=x" not in report
    assert 'href="javascript:' not in report


def test_invalid_artifact_on_listing_is_a_server_error(schema_path):
    from solarloss_backend.application import ReviewApplication

    store = MemoryReviewStore({"fixture-001": b"not-json"})
    response = ReviewApplication(store, schema_path=schema_path).handle_event(
        event("/api/v1/experiments"), "req-list-malformed"
    )
    assert response["statusCode"] == 500
    assert response_json(response)["error"]["code"] == "invalid_review_artifact"
