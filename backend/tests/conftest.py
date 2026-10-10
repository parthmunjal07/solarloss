import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "lambda"))

SCHEMA_PATH = ROOT / "artifacts" / "schema" / "review.schema.json"


def synthetic_review(decision_state="supported_change"):
    """Synthetic test fixture only; every value below is invented for unit testing."""
    return {
        "schema_version": "0.1.0",
        "review_id": "review_fixture-001",
        "analysis_version": "synthetic-test-v1",
        "produced_at": "2026-10-09T00:00:00Z",
        "dataset": {
            "name": "SYNTHETIC TEST FIXTURE - NOT MEASURED DATA",
            "source": "https://example.invalid/synthetic-test-fixture",
            "version": "synthetic-only",
            "extraction_date": "2026-10-09",
            "checksums": [
                {
                    "algorithm": "synthetic",
                    "digest": "not-a-real-checksum",
                    "scope": "test fixture only",
                }
            ],
        },
        "experiment": {
            "identifier": "fixture-001",
            "type": "SYNTHETIC TEST TYPE",
            "experimental_system": {
                "identifier": "synthetic-experimental",
                "description": "Synthetic experimental series for tests",
            },
            "reference_system": {
                "identifier": "synthetic-reference",
                "description": "Synthetic reference series for tests",
            },
            "time_window": {"start": "2026-10-09T10:00:00Z", "end": "2026-10-09T11:00:00Z"},
            "label_provenance": {
                "source": "synthetic test fixture",
                "method": "invented for schema tests",
                "label": "SYNTHETIC TEST LABEL",
            },
        },
        "series": {
            "timestamp_basis": "UTC",
            "power_unit": "W",
            "samples": [
                {
                    "timestamp": "2026-10-09T10:00:00Z",
                    "measured_power": 400.0,
                    "raw_reference_power": 500.0,
                    "expected_power": 450.0,
                    "valid": True,
                    "expected_lower_bound": 430.0,
                    "expected_upper_bound": 470.0,
                },
                {
                    "timestamp": "2026-10-09T10:30:00Z",
                    "measured_power": None,
                    "raw_reference_power": None,
                    "expected_power": None,
                    "valid": False,
                },
                {
                    "timestamp": "2026-10-09T11:00:00Z",
                    "measured_power": 320.0,
                    "raw_reference_power": 400.0,
                    "expected_power": 360.0,
                    "valid": True,
                },
            ],
        },
        "metrics": {
            "energy_deficit": {
                "value": 12.5,
                "unit": "Wh",
                "calculation": "Synthetic interval integration for schema tests",
            },
            "deficit_fraction": {
                "value": 0.125,
                "unit": "fraction",
                "numerator": {"value": 12.5, "unit": "Wh"},
                "denominator": {"value": 100.0, "unit": "Wh"},
                "calculation": "Synthetic fixture ratio",
            },
            "coverage": {
                "value": 0.8,
                "unit": "fraction",
                "numerator": {"value": 8, "unit": "intervals"},
                "denominator": {"value": 10, "unit": "intervals"},
            },
            "calibration_error": {
                "value": 5.0,
                "unit": "W",
                "statistic": "synthetic RMSE",
                "evaluation_population": "held_out_healthy",
                "denominator": {"value": 4, "unit": "held-out intervals"},
            },
            "valid_interval_count": 8,
            "total_interval_count": 10,
        },
        "baseline_comparison": {
            "metric": "synthetic held-out RMSE",
            "unit": "W",
            "evaluation_population": "synthetic held-out healthy intervals",
            "simple_baseline": {"name": "Synthetic ratio baseline", "value": 8.0},
            "calibrated_reference": {"name": "Synthetic calibrated reference", "value": 5.0},
            "reported_difference": {"value": 3.0, "unit": "W"},
            "calculation": "Synthetic test values only; no scientific interpretation.",
        },
        "uncertainty": {
            "method": "Synthetic block resampling placeholder for schema tests",
            "independent_blocks": {"count": 2, "unit": "synthetic blocks"},
            "interval": {"level": 0.95, "lower": 1.0, "upper": 24.0, "unit": "Wh"},
            "exploratory": True,
            "limitations": ["Synthetic test fixture; not a measured uncertainty estimate."],
        },
        "quality_checks": [
            {
                "name": "synthetic schema check",
                "status": "passed",
                "detail": "Fixture is labeled synthetic.",
            }
        ],
        "exclusions": [
            {
                "start": "2026-10-09T10:30:00Z",
                "end": "2026-10-09T10:35:00Z",
                "reason": "Synthetic missing interval in a test fixture.",
            }
        ],
        "decision": {
            "state": decision_state,
            "reasons": ["Synthetic decision reason for tests."],
            "rules_version": "synthetic-test-rules",
        },
        "limitations": ["All values in this test fixture are synthetic and are not evidence."],
        "robustness": {
            "status": "evaluated",
            "findings": [
                {
                    "name": "Synthetic robustness check",
                    "status": "reported",
                    "detail": "SYNTHETIC test only; not an observation.",
                    "synthetic": True,
                }
            ],
        },
        "placebo": {"status": "not_evaluated", "findings": []},
    }


def synthetic_experimental_v2_review():
    """Synthetic v0.2 test fixture only; it is not a publishable review artifact."""
    coverage = {
        "valid_seconds": 90.0,
        "observed_labelled_seconds": 100.0,
        "wall_span_seconds": 120.0,
    }

    def metric(
        metric_id,
        value,
        unit,
        *,
        availability="estimated",
        reason=None,
        ratio=None,
        uncertainty=None,
    ):
        result = {
            "id": metric_id,
            "availability": availability,
            "value": value,
            "unit": unit,
            "population": "SYNTHETIC TEST POPULATION ONLY",
            "definition": "Invented for backend tests; not a research definition.",
            "calculation": "Synthetic test value only.",
            "reason": reason,
            "coverage": dict(coverage),
        }
        if ratio is not None:
            result["ratio"] = ratio
        if uncertainty is not None:
            result["uncertainty"] = uncertainty
        return result

    return {
        "schema_version": "0.2.0",
        "approval_status": "proposed",
        "review_id": "review_synthetic-v2",
        "experiment": {
            "identifier": "synthetic-v2",
            "type": "documented_shading",
            "start": "2026-10-09T10:00:00Z",
            "end": "2026-10-09T11:00:00Z",
        },
        "provenance": {
            "protocol_sha256": "a" * 64,
            "source_checksums": [
                {"file": "SYNTHETIC-a.csv", "md5": "b" * 32, "sha256": "c" * 64},
                {"file": "SYNTHETIC-b.csv", "md5": "d" * 32, "sha256": "e" * 64},
            ],
            "model": {"name": "SYNTHETIC MODEL ONLY"},
            "splits": {"description": "Synthetic dates, not research splits."},
            "thresholds": {"description": "No real thresholds; fixture values only."},
            "evaluation_population": "SYNTHETIC TEST POPULATION ONLY",
            "grouping": {"description": "Synthetic grouping placeholder."},
            "label_use": "Synthetic test labels only.",
            "exclusions": [],
            "retrospective": True,
            "code_version": "synthetic-test-code",
        },
        "metrics": [
            metric("healthy_mae", 13.0, "W"),
            metric(
                "healthy_nmae",
                0.013,
                "1",
                ratio={
                    "numerator": 13.0,
                    "denominator": 1000.0,
                    "numerator_unit": "W",
                    "denominator_unit": "W",
                },
            ),
            metric(
                "healthy_bias",
                None,
                "W",
                availability="unavailable",
                reason="SYNTHETIC missing value test.",
            ),
            metric(
                "episode_recall",
                0.75,
                "1",
                ratio={
                    "numerator": 3,
                    "denominator": 4,
                    "numerator_unit": "episodes",
                    "denominator_unit": "episodes",
                },
            ),
            metric(
                "healthy_alarm_runs_per_hour",
                0.1,
                "alarms/hour",
                ratio={
                    "numerator": 1,
                    "denominator": 10,
                    "numerator_unit": "alarm runs",
                    "denominator_unit": "hours",
                },
            ),
            metric(
                "signed_generation_deviation",
                -0.25,
                "kWh",
                uncertainty={
                    "kind": "empirical_model_error_band",
                    "method": "Synthetic band for tests only.",
                    "unit": "kWh",
                    "lower": -0.3,
                    "upper": -0.2,
                    "group_count": 5,
                    "limitations": ["SYNTHETIC test-only uncertainty."],
                },
            ),
            metric("positive_only_generation_deviation", 0.1, "kWh"),
            metric("observed_energy", 0.5, "kWh"),
            metric(
                "expected_energy",
                None,
                "kWh",
                availability="unavailable",
                reason="SYNTHETIC test missing expected-energy value.",
            ),
        ],
        "series": {
            "timestamp_basis": "UTC",
            "power_unit": "W",
            "downsampling": {
                "method": "none; synthetic samples",
                "source_count": 2,
                "retained_count": 2,
                "gap_markers": [],
            },
            "samples": [
                {
                    "timestamp": "2026-10-09T10:00:00Z",
                    "measured_power": 500.0,
                    "raw_reference_power": 550.0,
                    "expected_power": 525.0,
                    "valid": True,
                },
                {
                    "timestamp": "2026-10-09T10:30:00Z",
                    "measured_power": None,
                    "raw_reference_power": None,
                    "expected_power": None,
                    "valid": False,
                },
            ],
        },
        "electrical_evidence": [
            {
                "signal": "Va",
                "measurement": 154.6,
                "unit": "V",
                "quality": "SYNTHETIC quality description.",
                "comparison_population": "SYNTHETIC test population.",
                "supports": "A synthetic operating-point observation only.",
                "does_not_prove": "No fault diagnosis.",
                "alternatives": ["SYNTHETIC alternative."],
                "missing_measurements": ["SYNTHETIC missing measurement."],
                "strength": "LIMITED",
            }
        ],
        "candidate_checks": [
            {
                "id": "synthetic-check-1",
                "observed_fact": "SYNTHETIC observed fact only.",
                "hypothesis": "SYNTHETIC candidate hypothesis only.",
                "supporting_evidence": ["SYNTHETIC support."],
                "opposing_evidence": ["SYNTHETIC alternative evidence."],
                "next_information": ["SYNTHETIC next information."],
                "qualification": "SYNTHETIC qualification boundary.",
                "safety_constraint": "No physical work; synthetic fixture only.",
                "sources": ["https://example.invalid/synthetic-source"],
                "status": "proposed",
            }
        ],
        "decision": {
            "verdict": "LIMIT",
            "rule_version": "synthetic-test-rule",
            "reasons": ["SYNTHETIC decision reason only."],
            "owner_review": None,
        },
        "limitations": ["SYNTHETIC fixture only; no measured or publishable findings."],
    }


class MemoryReviewStore:
    """Test-only storage adapter; never used for product/demo responses."""

    def __init__(self, reviews=None):
        self.reviews = reviews or {}
        self.saved_reports = {}

    def list_experiment_ids(self):
        return sorted(self.reviews)

    def get_review_bytes(self, experiment_id):
        from solarloss_backend.errors import ArtifactNotFound

        if experiment_id not in self.reviews:
            raise ArtifactNotFound(experiment_id)
        return self.reviews[experiment_id]

    def save_report(self, experiment_id, html_body):
        self.saved_reports[experiment_id] = html_body
        return f"https://reports.example.invalid/{experiment_id}.html"


@pytest.fixture
def schema_path():
    return SCHEMA_PATH


@pytest.fixture
def proposed_v2_schema_path():
    return ROOT / "artifacts" / "schema" / "review.schema.v0.2.0.proposed.json"


@pytest.fixture
def synthetic_artifact():
    return synthetic_review()


@pytest.fixture
def memory_store(synthetic_artifact):
    return MemoryReviewStore({"fixture-001": json.dumps(synthetic_artifact).encode("utf-8")})


@pytest.fixture
def app(memory_store, schema_path):
    from solarloss_backend.application import ReviewApplication

    return ReviewApplication(
        memory_store, schema_path=schema_path, allowed_origins=frozenset({"http://localhost:5173"})
    )
