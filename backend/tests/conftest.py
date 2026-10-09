import json
from pathlib import Path
import sys

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
            "checksums": [{"algorithm": "synthetic", "digest": "not-a-real-checksum", "scope": "test fixture only"}],
        },
        "experiment": {
            "identifier": "fixture-001",
            "type": "SYNTHETIC TEST TYPE",
            "experimental_system": {"identifier": "synthetic-experimental", "description": "Synthetic experimental series for tests"},
            "reference_system": {"identifier": "synthetic-reference", "description": "Synthetic reference series for tests"},
            "time_window": {"start": "2026-10-09T10:00:00Z", "end": "2026-10-09T11:00:00Z"},
            "label_provenance": {"source": "synthetic test fixture", "method": "invented for schema tests", "label": "SYNTHETIC TEST LABEL"},
        },
        "series": {
            "timestamp_basis": "UTC",
            "power_unit": "W",
            "samples": [
                {"timestamp": "2026-10-09T10:00:00Z", "measured_power": 400.0, "raw_reference_power": 500.0, "expected_power": 450.0, "valid": True, "expected_lower_bound": 430.0, "expected_upper_bound": 470.0},
                {"timestamp": "2026-10-09T10:30:00Z", "measured_power": None, "raw_reference_power": None, "expected_power": None, "valid": False},
                {"timestamp": "2026-10-09T11:00:00Z", "measured_power": 320.0, "raw_reference_power": 400.0, "expected_power": 360.0, "valid": True},
            ],
        },
        "metrics": {
            "energy_deficit": {"value": 12.5, "unit": "Wh", "calculation": "Synthetic interval integration for schema tests"},
            "deficit_fraction": {"value": 0.125, "unit": "fraction", "numerator": {"value": 12.5, "unit": "Wh"}, "denominator": {"value": 100.0, "unit": "Wh"}, "calculation": "Synthetic fixture ratio"},
            "coverage": {"value": 0.8, "unit": "fraction", "numerator": {"value": 8, "unit": "intervals"}, "denominator": {"value": 10, "unit": "intervals"}},
            "calibration_error": {"value": 5.0, "unit": "W", "statistic": "synthetic RMSE", "evaluation_population": "held_out_healthy", "denominator": {"value": 4, "unit": "held-out intervals"}},
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
        "quality_checks": [{"name": "synthetic schema check", "status": "passed", "detail": "Fixture is labeled synthetic."}],
        "exclusions": [{"start": "2026-10-09T10:30:00Z", "end": "2026-10-09T10:35:00Z", "reason": "Synthetic missing interval in a test fixture."}],
        "decision": {"state": decision_state, "reasons": ["Synthetic decision reason for tests."], "rules_version": "synthetic-test-rules"},
        "limitations": ["All values in this test fixture are synthetic and are not evidence."],
        "robustness": {"status": "evaluated", "findings": [{"name": "Synthetic robustness check", "status": "reported", "detail": "SYNTHETIC test only; not an observation.", "synthetic": True}]},
        "placebo": {"status": "not_evaluated", "findings": []},
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
def synthetic_artifact():
    return synthetic_review()


@pytest.fixture
def memory_store(synthetic_artifact):
    return MemoryReviewStore({"fixture-001": json.dumps(synthetic_artifact).encode("utf-8")})


@pytest.fixture
def app(memory_store, schema_path):
    from solarloss_backend.application import ReviewApplication

    return ReviewApplication(memory_store, schema_path=schema_path, allowed_origins=frozenset({"http://localhost:5173"}))
