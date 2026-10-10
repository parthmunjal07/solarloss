"""Source-reconciliation tests for the Phase 3 review exporter and diagnostics."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
import pytest

ANALYSIS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ANALYSIS / "src"))

from solarloss_research.export_reviews_v3 import (  # noqa: E402
    build_case_exports,
    export_case_exports,
    validate_case_exports,
)
from solarloss_research.detector_diagnostics_v3 import analyze  # noqa: E402


@pytest.fixture(scope="module")
def case_exports():
    return build_case_exports(ANALYSIS)


def test_shading_export_reconciles_to_v2_source_values(case_exports):
    artifact = case_exports["review_shading_01.json"]
    source = json.loads((ANALYSIS / "results" / "example_cases_v2.json").read_text(encoding="utf-8"))["shading_event"]
    metrics = {item["id"]: item for item in artifact["metrics"]}
    assert artifact["experiment"]["identifier"] == "shading_01"
    assert artifact["review_id"] == "review_shading_01"
    assert metrics["signed_generation_deviation"]["value"] == source["energy"]["signed_energy_kwh"]
    assert metrics["positive_only_generation_deviation"]["value"] == source["energy"]["positive_only_kwh"]
    coverage = metrics["signed_generation_deviation"]["coverage"]
    assert coverage == {
        "valid_seconds": source["energy"]["valid_seconds"],
        "observed_labelled_seconds": source["energy"]["observed_labelled_support_seconds"],
        "wall_span_seconds": source["energy"]["observed_labelled_support_seconds"],
    }
    assert artifact["experiment"]["event_context"]["label_interval_utc"]["start"] == "2022-02-08T07:11:02Z"
    assert artifact["experiment"]["event_context"]["detector_confirmations_utc"]["5_minute_primary"] == "2022-02-08T07:20:00Z"
    assert artifact["decision"]["verdict"] == "LIMIT"
    assert artifact["decision"]["event_review"]["availability"] == "unavailable"
    assert artifact["approval_status"] == "proposed"
    assert "recoverable" in " ".join(artifact["limitations"]).lower()


def test_shading_series_preserves_separate_measured_reference_and_expected(case_exports):
    artifact = case_exports["review_shading_01.json"]
    samples = artifact["series"]["samples"]
    assert len(samples) == 2148
    assert all("measured_power" in sample and "raw_reference_power" in sample and "expected_power" in sample for sample in samples)
    assert all(sample["timestamp"].endswith("Z") for sample in samples)
    assert samples == sorted(samples, key=lambda sample: sample["timestamp"])
    assert artifact["provenance"]["model"]["expected_power_semantics"].startswith("Calibrated healthy expected")
    assert all(item["status"] == "proposed" for item in artifact["candidate_checks"])


def test_healthy_case_is_zero_labelled_and_not_called_independent(case_exports):
    artifact = case_exports["review_healthy_20220126_0300.json"]
    metrics = {item["id"]: item for item in artifact["metrics"]}
    assert artifact["experiment"]["type"] == "healthy_stability"
    assert len(artifact["series"]["samples"]) == 12
    assert metrics["signed_generation_deviation"]["value"] == pytest.approx(0.012293236982942487)
    assert metrics["positive_only_generation_deviation"]["value"] == pytest.approx(0.015578431648304622)
    assert artifact["experiment"]["event_context"]["detector_calibration_population"] is True
    assert any("not an independent holdout" in limitation for limitation in artifact["limitations"])
    assert artifact["decision"]["event_review"]["state"] is None


def test_genuine_gap_remains_explicitly_unavailable(case_exports):
    record = case_exports["review_insufficient_data_gap_20211222_20220124.json"]
    assert record["status"] == "unavailable_for_proposed_v0_2_review"
    assert record["gap_seconds"] == 2_848_806.0
    assert record["energy_deviation"]["value"] is None
    assert record["event_review_state"]["state"] is None
    assert "no data-gap" in record["event_review_state"]["reason"]


def test_available_reviews_pass_draft_schema_and_identity(tmp_path, case_exports):
    schema = json.loads((ANALYSIS / "contracts" / "review.schema.v0.2.0.proposed.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for name in ("review_shading_01.json", "review_healthy_20220126_0300.json"):
        artifact = case_exports[name]
        assert list(validator.iter_errors(artifact)) == []
        assert artifact["review_id"] == f"review_{artifact['experiment']['identifier']}"
        for metric in artifact["metrics"]:
            if metric["ratio"] is not None:
                ratio = metric["ratio"]
                assert metric["value"] == pytest.approx(ratio["numerator"] / ratio["denominator"])
    paths = export_case_exports(ANALYSIS, tmp_path)
    assert len(paths) == 3
    assert validate_case_exports(ANALYSIS, tmp_path) == []


def test_review_export_is_byte_for_byte_deterministic(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_paths = export_case_exports(ANALYSIS, first)
    second_paths = export_case_exports(ANALYSIS, second)
    assert [path.name for path in first_paths] == [path.name for path in second_paths]
    for first_path, second_path in zip(first_paths, second_paths):
        assert first_path.read_bytes() == second_path.read_bytes()


def test_detector_diagnostics_reconcile_and_compare_on_shared_support(tmp_path):
    result = analyze(ANALYSIS, tmp_path)
    assert all(result["reconstruction_checks"].values())
    sample = result["common_detector_sample"]
    assert sample["all_candidates_share_identical_eligible_windows"] is True
    assert sample["calibration_windows"] == 1312
    assert sample["later_healthy_windows"] == 22015
    rows = {row["model"]: row for row in result["period_scores_and_alerts"] if row["period"] == "later_healthy"}
    assert rows["weather_ols"]["healthy_alert_runs"] == 153
    assert rows["weather_ols"]["healthy_alert_runs_per_hour"] == pytest.approx(0.08526020150384879)
    assert rows["reference_ols"]["healthy_alert_runs_per_hour"] < 0.05
    assert result["event_detection"]["reference_ols"]["recall"] == 1.0
    assert result["event_detection"]["weather_ols"]["recall"] == 1.0
    assert result["source"]["raw_data_rerun_performed"] is False
    assert (tmp_path / "residual_tail_v3.png").is_file()
    assert (tmp_path / "monthly_residual_alerts_v3.png").is_file()
    assert (tmp_path / "residual_strata_v3.png").is_file()
