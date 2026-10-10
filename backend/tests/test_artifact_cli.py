import json

from conftest import synthetic_review

from backend.validate_artifact import artifact_identity_errors, validate_artifact


def test_artifact_identity_contract_accepts_matching_filename_and_ids():
    assert artifact_identity_errors(synthetic_review(), "review_fixture-001.json") == []


def test_artifact_identity_contract_reports_each_filename_disagreement():
    review = synthetic_review()
    review["review_id"] = "review_other"
    errors = artifact_identity_errors(review, "review_filename-id.json")
    assert any("Filename identifies experiment 'filename-id'" in error for error in errors)
    assert any("Filename requires review_id 'review_filename-id'" in error for error in errors)
    assert any("review_id must be 'review_fixture-001'" in error for error in errors)


def test_artifact_command_checks_local_api_and_report_and_optional_downloads(tmp_path):
    review = synthetic_review()
    artifact_path = tmp_path / "review_fixture-001.json"
    artifact_path.write_text(json.dumps(review), encoding="utf-8")
    retrieved_path = tmp_path / "api-review.json"
    retrieved_path.write_text(json.dumps(review), encoding="utf-8")

    from solarloss_backend.report import render_review_report

    report_path = tmp_path / "api-report.html"
    report_path.write_text(render_review_report(review), encoding="utf-8")
    assert validate_artifact(artifact_path, retrieved_path, report_path) == []


def test_artifact_command_rejects_nonconforming_filename_without_renaming(tmp_path):
    review = synthetic_review()
    artifact_path = tmp_path / "science-export.json"
    artifact_path.write_text(json.dumps(review), encoding="utf-8")
    errors = validate_artifact(artifact_path)
    assert any("must be review_<experiment_id>.json" in error for error in errors)
