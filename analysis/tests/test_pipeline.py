"""Deterministic synthetic fixtures for pipeline mechanics; not product results."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from solarloss_research.dataset import audit_csv, load_weather_bins
from solarloss_research.model import (
    _trapezoid_seconds,
    evaluate_fault_episodes,
    fit_and_compare,
    find_fault_episodes,
)
from solarloss_research.review import _sample_rows


class AuditTests(unittest.TestCase):
    def test_chunked_audit_counts_rows_duplicates_and_intervals(self) -> None:
        content = (
            "time,Fault,Pg\n"
            "2021-10-01 12:00:00+04:00,0,100\n"
            "2021-10-01 12:00:07+04:00,0,101\n"
            "2021-10-01 12:00:07+04:00,1,90\n"
            "2021-10-01 12:00:21+04:00,0,102\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "measurements.csv"
            path.write_text(content, encoding="utf-8")
            result = audit_csv(path, chunksize=2, expected_frequency_seconds=5.0)
        self.assertEqual(result["row_count"], 4)
        self.assertEqual(result["duplicate_timestamp_count"], 1)
        self.assertEqual(result["source_utc_offsets"], {"+04:00": 4})
        self.assertEqual(result["fault_value_counts"], {"0": 3, "1": 1})
        self.assertEqual(result["interval_seconds"]["median"], 10.5)

    def test_weather_chunk_aggregation_uses_actual_dti_column(self) -> None:
        content = (
            "time,GTI,DTI,TA,TPV\n"
            "2021-10-28 12:00:00+04:00,100,20,25,30\n"
            "2021-10-28 12:00:01+04:00,200,,27,32\n"
            "2021-10-28 12:00:02+04:00,300,60,29,34\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "weather.csv"
            path.write_text(content, encoding="utf-8")
            result = load_weather_bins(path, chunksize=2)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.loc[0, "weather_count"], 3)
        self.assertAlmostEqual(result.loc[0, "GTI"], 200.0)
        self.assertAlmostEqual(result.loc[0, "DTI"], 40.0)
        self.assertAlmostEqual(result.loc[0, "DTI_coverage"], 2 / 300)
        self.assertAlmostEqual(result.loc[0, "TA"], 27.0)


class ModelSelectionTests(unittest.TestCase):
    def test_progressive_selection_and_day_block_uncertainty(self) -> None:
        rows = []
        for day_index in range(20):
            day = pd.Timestamp("2021-01-01").date() + pd.Timedelta(days=day_index)
            for bin_index in range(30):
                reference = 300.0 + 20.0 * bin_index
                rows.append({
                    "bin_start": pd.Timestamp(day, tz="UTC") + pd.Timedelta(hours=8, minutes=5 * bin_index),
                    "local_day": day,
                    "target_power_w": 0.8 * reference + 10.0,
                    "reference_power_w": reference,
                    "healthy": True,
                    "daylight": True,
                    "paired_valid": True,
                })
        result = fit_and_compare(pd.DataFrame(rows))
        self.assertEqual(result["selected_model_name"], "calibrated_linear")
        self.assertIn("capacity_table_arithmetic", result["validation_scores"])
        self.assertEqual(result["model_parameters"]["calibrated_linear"]["training_rows"], 360)
        uncertainty = result["heldout_healthy_block_bootstrap_95pct"]["calibrated_linear"]
        self.assertEqual(uncertainty["status"], "estimated")
        self.assertEqual(uncertainty["independent_blocks"], 4)


class EpisodeTests(unittest.TestCase):
    @staticmethod
    def _ts(seconds: int) -> pd.Timestamp:
        return pd.Timestamp("2021-10-01T08:00:00Z") + pd.Timedelta(seconds=seconds)

    def test_episode_group_keeps_intermittent_zero_pause_but_splits_long_gap(self) -> None:
        target = pd.DataFrame({
            "timestamp": [self._ts(0), self._ts(7), self._ts(35), self._ts(42), self._ts(600)],
            "fault_label": [1.0, 1.0, 4.0, 4.0, 2.1],
        })
        episodes = find_fault_episodes(target, gap_seconds=300)
        self.assertEqual(len(episodes), 2)
        self.assertEqual(episodes[0]["label_counts"], {"1": 2, "4": 2})
        self.assertEqual(episodes[1]["labels"], ["2.1"])

    def test_energy_integrator_uses_elapsed_seconds(self) -> None:
        value = _trapezoid_seconds(np.array([100.0, 200.0, 200.0]), np.array([0.0, 7.0, 17.0]))
        self.assertAlmostEqual(value, 100.0 * 7.0 + 200.0 * 10.0 + 0.5 * 100.0 * 7.0)

    def test_episode_energy_uses_real_time_and_exact_paired_fault_samples(self) -> None:
        times = [self._ts(i) for i in (0, 7, 14, 21, 28)]
        target = pd.DataFrame({"timestamp": times, "fault_label": [1.0] * len(times)})
        paired = pd.DataFrame({
            "timestamp": times,
            "fault_label": [1.0] * len(times),
            "target_power_w": [50.0] * len(times),
            "reference_power_w": [50.0] * len(times),
        })
        estimator = LinearRegression().fit(np.array([[0.0], [100.0]]), np.array([100.0, 100.0]))
        model_info = {"selected_model": {"estimator": estimator, "features": ["reference_power_w"]}}
        episodes, exclusions = evaluate_fault_episodes(
            target,
            paired,
            model_info,
            evaluation_start_day="2021-10-01",
            test_start_day="2021-10-01",
            expected_frequency_seconds=7.0,
        )
        self.assertEqual(exclusions, [])
        self.assertEqual(len(episodes), 1)
        self.assertAlmostEqual(episodes[0]["integrated_elapsed_seconds"], 28.0)
        self.assertAlmostEqual(episodes[0]["positive_only_shortfall_kwh"], 50.0 * 28.0 / 3_600_000.0)

    def test_compact_review_series_keeps_measured_points_and_marks_gaps(self) -> None:
        times = [self._ts(0), self._ts(300), self._ts(1800)]
        bins = pd.DataFrame({
            "bin_start": times,
            "target_power_w": [100.0, 105.0, 110.0],
            "reference_power_w": [50.0, 50.0, 50.0],
        })
        estimator = LinearRegression().fit(np.array([[0.0], [100.0]]), np.array([100.0, 100.0]))
        model_info = {"selected_model": {"estimator": estimator, "features": ["reference_power_w"]}}
        rows = _sample_rows(bins, model_info, [{"start": times[0], "end": times[-1]}])
        self.assertEqual([row["valid"] for row in rows], [True, True, False, True])
        self.assertEqual(rows[2]["timestamp"], (times[1] + pd.Timedelta(minutes=5)).isoformat())


if __name__ == "__main__":
    unittest.main()
