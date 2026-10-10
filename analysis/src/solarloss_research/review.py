"""Build and validate compact v0.1.0 review artifacts."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from jsonschema import Draft202012Validator, FormatChecker

from .dataset import FILES, RECORD_URL
from .model import BIN_MINUTES, _feature_valid, _predict


def review_identity(experiment_id: str) -> tuple[str, str]:
    """One identity source for review_id and filename; never encode a second ID."""
    import re
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,99}', experiment_id):
        raise ValueError('Invalid experiment identifier')
    review_id = 'review_' + experiment_id
    return review_id, review_id + '.json'


def _clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return pd.Timestamp(value).isoformat()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if math.isfinite(float(value)) else None
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    return value


def _sample_rows(
    bins: pd.DataFrame,
    model_info: dict[str, Any],
    episodes: list[dict[str, Any]],
    *,
    max_samples: int = 1500,
) -> list[dict[str, Any]]:
    if not episodes:
        return []
    model = model_info["selected_model"]
    rows: list[dict[str, Any]] = []
    segment_edges: set[int] = set()
    previous_time: pd.Timestamp | None = None
    for episode_index, episode in enumerate(episodes):
        start = episode["start"].floor(f"{BIN_MINUTES}min")
        end = episode["end"].floor(f"{BIN_MINUTES}min")
        interval = bins.loc[bins["bin_start"].between(start, end, inclusive="both")].copy()
        interval = interval.sort_values("bin_start", kind="stable").reset_index(drop=True)
        if episode_index and rows:
            # Explicit invalid marker prevents line charts from joining separated episodes.
            previous = previous_time or pd.Timestamp(rows[-1]["timestamp"])
            marker = previous + pd.Timedelta(minutes=BIN_MINUTES)
            rows.append({
                "timestamp": marker.isoformat(), "measured_power": None,
                "raw_reference_power": None, "expected_power": None, "valid": False,
            })
        feature_available = _feature_valid(model, interval) if len(interval) else pd.Series(dtype=bool)
        valid = interval[["target_power_w", "reference_power_w"]].notna().all(axis=1) & feature_available
        prediction = np.full(len(interval), np.nan)
        if valid.any():
            prediction[valid.to_numpy()] = _predict(model, interval.loc[valid])
        for i, timestamp in enumerate(interval.index):
            actual_time = pd.Timestamp(interval.loc[i, "bin_start"])
            if previous_time is not None and (actual_time - previous_time).total_seconds() > BIN_MINUTES * 60:
                marker = previous_time + pd.Timedelta(minutes=BIN_MINUTES)
                rows.append({
                    "timestamp": marker.isoformat(), "measured_power": None,
                    "raw_reference_power": None, "expected_power": None, "valid": False,
                })
            is_valid = bool(valid.iloc[i] and np.isfinite(prediction[i]))
            if i == 0:
                segment_edges.add(len(rows))
            rows.append({
                "timestamp": actual_time.isoformat(),
                "measured_power": float(interval["target_power_w"].iloc[i]) if is_valid else None,
                "raw_reference_power": float(interval["reference_power_w"].iloc[i]) if is_valid else None,
                "expected_power": float(prediction[i]) if is_valid else None,
                "valid": is_valid,
            })
            if i == len(interval) - 1:
                segment_edges.add(len(rows) - 1)
            previous_time = actual_time
    if len(rows) <= max_samples:
        return rows
    mandatory = set()
    for i, row in enumerate(rows):
        if not row["valid"]:
            mandatory.add(i)
        if i == 0 or i == len(rows) - 1:
            mandatory.add(i)
    mandatory.update(segment_edges)
    remaining = max(0, max_samples - len(mandatory))
    candidates = [i for i in range(len(rows)) if i not in mandatory]
    if remaining and candidates:
        take = np.linspace(0, len(candidates) - 1, min(remaining, len(candidates)), dtype=int)
        mandatory.update(candidates[i] for i in take)
    return [rows[i] for i in sorted(mandatory)]


def _build_healthy_placebo_artifact(
    *,
    file_checks: list[dict[str, Any]],
    alignment: dict[str, Any],
    bins: pd.DataFrame,
    model_info: dict[str, Any],
    summary: dict[str, Any],
    produced_at: str,
    max_samples: int,
) -> dict[str, Any]:
    """Represent the measured held-out healthy placebo when no post-training fault episode exists."""
    model = model_info["selected_model"]
    test = model_info["splits"]["test"].query("healthy and daylight and paired_valid").copy()
    if len(test) < 2:
        raise ValueError("No eligible held-out healthy placebo intervals are available for a review artifact")
    test = test.sort_values("bin_start", kind="stable").reset_index(drop=True)
    feature_valid = _feature_valid(model, test).to_numpy()
    predicted = np.full(len(test), np.nan, dtype=float)
    if feature_valid.any():
        predicted[feature_valid] = _predict(model, test.loc[feature_valid])
    observed = test["target_power_w"].to_numpy(dtype=float)
    expected = predicted
    times = test["bin_start"].astype("int64").to_numpy(dtype=np.float64) / 1e9
    dt = np.diff(times)
    adjacent_5min = (dt > 0) & (dt <= BIN_MINUTES * 60)
    total_seconds = float(dt[adjacent_5min].sum())
    valid_interval = adjacent_5min & feature_valid[:-1] & feature_valid[1:]
    valid_interval &= np.isfinite(observed[:-1]) & np.isfinite(observed[1:])
    valid_seconds = float(dt[valid_interval].sum())
    if valid_seconds <= 0:
        raise ValueError("No complete adjacent held-out healthy placebo intervals are available")
    residual = expected - observed
    signed_ws = float(np.sum((residual[:-1][valid_interval] + residual[1:][valid_interval]) * 0.5 * dt[valid_interval]))
    positive_ws = float(np.sum((np.maximum(residual[:-1][valid_interval], 0) + np.maximum(residual[1:][valid_interval], 0)) * 0.5 * dt[valid_interval]))
    expected_ws = float(np.sum((expected[:-1][valid_interval] + expected[1:][valid_interval]) * 0.5 * dt[valid_interval]))
    if expected_ws <= 0:
        raise ValueError("Held-out healthy placebo expected energy denominator is not positive")
    coverage = float(valid_seconds / total_seconds) if total_seconds > 0 else 0.0
    valid_count = int(valid_interval.sum())
    total_count = int(adjacent_5min.sum())
    if total_count < 1:
        raise ValueError("Held-out healthy placebo has no adjacent five-minute intervals")
    start = test["bin_start"].min()
    end = test["bin_start"].max() + pd.Timedelta(minutes=BIN_MINUTES)
    sample_rows = _sample_rows(
        bins,
        model_info,
        [{"start": start, "end": end}],
        max_samples=max_samples,
    )
    score = summary["heldout_healthy"]["score"]
    selected = summary["selected_model"]
    checksums = []
    for check in file_checks:
        if not check["checksum_matches"]:
            raise ValueError(f"A verified checksum is required in the artifact for {check['file']}")
        checksums.append({"algorithm": "md5", "digest": check["md5"], "scope": f"Zenodo file {check['file']}"})
    test_shading_count = summary["heldout_test_shading"]["episode_count"]
    metrics_scope = (
        "Held-out healthy placebo diagnostic only; no post-training labelled shading episode is estimable. "
        "This positive residual-energy integral is not a shading estimate."
    )
    placebo = summary["placebo"]
    return {
        "schema_version": "0.1.0",
        "review_id": "review_la-reunion-healthy-placebo-" + pd.Timestamp(produced_at).strftime("%Y%m%d"),
        "analysis_version": summary["analysis_version"],
        "produced_at": produced_at,
        "dataset": {
            "name": "La Réunion rooftop PV electrical production and shading dataset",
            "source": RECORD_URL,
            "version": "v2 (record 7291380; DOI 10.5281/zenodo.7291380)",
            "extraction_date": pd.Timestamp(produced_at).date().isoformat(),
            "checksums": checksums,
        },
        "experiment": {
            "identifier": "la-reunion-heldout-healthy-placebo-" + pd.Timestamp(produced_at).strftime("%Y%m%d"),
            "type": "heldout_healthy_placebo_no_posttraining_shading_episode",
            "experimental_system": {
                "identifier": "inverter-1",
                "description": "Electrical production file dt2; AC grid-injected power Pg in W; held-out bins are documented healthy labels.",
            },
            "reference_system": {
                "identifier": "inverter-2",
                "description": "Electrical production file dt3; nonidentical comparison line; AC grid-injected power Pg in W.",
            },
            "time_window": {"start": start.isoformat(), "end": end.isoformat()},
            "label_provenance": {
                "source": "dt2_electrical_production_inverter_1_with_faults.csv, column Fault",
                "method": "Fault labels identify healthy placebo bins and confirm there are no evaluable post-training shading episodes in the held-out test period; labels are never predictors.",
                "label": f"Held-out healthy placebo; final-test labelled shading episode count={test_shading_count}.",
                "reference": "https://doi.org/10.5281/zenodo.7291380",
            },
        },
        "series": {"timestamp_basis": "UTC", "power_unit": "W", "samples": sample_rows},
        "metrics": {
            "energy_deficit": {
                "value": positive_ws / 3_600_000.0,
                "unit": "kWh",
                "calculation": metrics_scope + " Trapezoidal positive prediction-minus-observation residual over adjacent held-out healthy daylight five-minute-bin means; this is a placebo false-shortfall diagnostic.",
            },
            "deficit_fraction": {
                "value": positive_ws / expected_ws,
                "unit": "1",
                "numerator": {"value": positive_ws / 3_600_000.0, "unit": "kWh"},
                "denominator": {"value": expected_ws / 3_600_000.0, "unit": "kWh"},
                "calculation": "Placebo positive residual energy divided by expected energy over the same eligible healthy intervals; not an experimental shading deficit fraction.",
            },
            "coverage": {
                "value": coverage,
                "unit": "1",
                "numerator": {"value": valid_seconds, "unit": "s"},
                "denominator": {"value": total_seconds, "unit": "s"},
                "calculation": "Valid adjacent held-out healthy daylight five-minute interval seconds divided by available adjacent candidate interval seconds.",
            },
            "calibration_error": {
                "value": float(score["nmae"]),
                "unit": "1",
                "statistic": "held-out healthy nMAE = MAE / mean observed target AC power",
                "evaluation_population": "held_out_healthy",
                "numerator": {"value": float(score["mae_w"]), "unit": "W"},
                "denominator": {"value": float(score["mean_observed_w"]), "unit": "W"},
            },
            "valid_interval_count": valid_count,
            "total_interval_count": total_count,
        },
        "baseline_comparison": {
            "metric": "held-out healthy mean absolute error",
            "unit": "W",
            "evaluation_population": "chronological held-out healthy daylight five-minute bins",
            "simple_baseline": {"name": "capacity ratio from literal Table 1 module ratings (2.10 / 2.04 kWp); source capacity mapping discrepancy is documented", "value": float(model_info["heldout_healthy_scores"]["capacity_table_arithmetic"]["mae_w"])},
            "calibrated_reference": {"name": f"{model_info['selected_model_name']} (healthy training only)", "value": float(model_info["heldout_healthy_scores"][model_info["selected_model_name"]]["mae_w"])},
            "reported_difference": {"value": float(model_info["heldout_healthy_scores"]["capacity_table_arithmetic"]["mae_w"] - model_info["heldout_healthy_scores"][model_info["selected_model_name"]]["mae_w"]), "unit": "W"},
            "calculation": "Both MAEs use the same held-out healthy bins; validation healthy data select the model. This comparison evaluates healthy prediction only.",
        },
        "uncertainty": {
            "method": "No interval estimated for the experimental shading effect because no eligible post-training shading episodes are available. The reported integral is a descriptive placebo diagnostic.",
            "independent_blocks": {"count": 0, "unit": "no independent experimental episode available for a shading-effect interval"},
            "interval": None,
            "not_estimated_reason": "There are zero evaluable post-training shading episodes; healthy placebo blocks are not substituted for experimental episodes.",
            "exploratory": True,
            "limitations": [
                "This artifact reports held-out healthy placebo residuals, not an experimental shading shortfall.",
                "No episode-level uncertainty interval for shading can be estimated because eligible post-training events are absent.",
                "Healthy hourly placebo blocks can be serially dependent.",
            ],
        },
        "quality_checks": [
            {"name": "source_checksums", "status": "passed", "detail": f"Verified pinned-record MD5 and byte size for {len(file_checks)} downloaded source file(s)."},
            {"name": "exact_inverter_timestamp_alignment", "status": "passed" if alignment["exact_coverage_of_smaller_stream"] >= 0.95 else "failed", "detail": f"Exact timestamp intersection covered {alignment['exact_coverage_of_smaller_stream']:.3%} of the smaller unique electrical stream; no nearest-neighbor interpolation was used.", "result": str(alignment["exact_common_timestamps"])},
            {"name": "heldout_healthy_calibration", "status": "passed" if summary["heldout_healthy"]["calibration_valid"] else "failed", "detail": f"Held-out healthy model coverage={summary['heldout_healthy']['selected_model_coverage']:.3%}; nMAE={score['nmae']:.6g}; MAE={score['mae_w']:.6g} W; signed bias={score['bias_w']:.6g} W."},
            {"name": "reference_stability_screen", "status": "reported" if summary["reference_stability"]["status"] == "stable_by_predeclared_screen" else "failed", "detail": summary["reference_stability"]["screen"] + f" Result: {summary['reference_stability']['status']}; monthly relative range={summary['reference_stability']['monthly_relative_range']}."},
            {"name": "experimental_shading_coverage", "status": "not_evaluated", "detail": f"No evaluable post-training labelled shading episodes; final held-out test episode count={test_shading_count}. The placebo integral is not a shading-effect estimate."},
            {"name": "noncausal_interpretation", "status": "reported", "detail": "The healthy placebo diagnostic is a measured model residual; it does not identify physical cause or recoverable commercial energy."},
        ],
        "exclusions": [
            {"start": item["start"].isoformat(), "end": item["end"].isoformat(), "reason": item["reason"]}
            for item in summary["episode_exclusions"]
        ],
        "decision": {"state": summary["decision"]["state"], "reasons": summary["decision"]["reasons"], "rules_version": summary["decision"]["rules_version"]},
        "limitations": [
            "No post-training documented shading episode is estimable in this dataset split; the artifact contains held-out healthy placebo diagnostics only.",
            "The positive placebo residual integral is not a shading shortfall, counterfactual repair yield, or verified commercial energy recovery.",
            "The dataset is a La Réunion experimental installation; no Indian-site performance is inferred.",
            "The two inverter lines are nonidentical; source capacity prose and module-table arithmetic do not reconcile exactly.",
            "A deviation from a healthy-period reference does not establish physical cause.",
        ],
        "robustness": {
            "status": "evaluated" if summary["missingness_sensitivity"].get("status") == "evaluated" else "not_evaluated",
            "findings": [{"name": "missingness_sensitivity", "status": "reported" if summary["missingness_sensitivity"].get("status") == "evaluated" else "not_evaluated", "detail": json.dumps(_clean(summary["missingness_sensitivity"]), separators=(",", ":")), "synthetic": bool(summary["missingness_sensitivity"].get("synthetic", False))}],
        },
        "placebo": {
            "status": "evaluated" if placebo.get("status") == "evaluated" else "not_evaluated",
            "findings": [{"name": "heldout_healthy_placebo_false_shortfall", "status": "reported" if placebo.get("status") == "evaluated" else "not_evaluated", "detail": json.dumps(_clean(placebo), separators=(",", ":"))}],
        },
    }


def build_review_artifact(
    *,
    audits: dict[str, dict[str, Any]],
    file_checks: list[dict[str, Any]],
    alignment: dict[str, Any],
    bins: pd.DataFrame,
    model_info: dict[str, Any],
    summary: dict[str, Any],
    produced_at: str,
    max_samples: int = 1500,
    semantics_approved: bool = False,
) -> dict[str, Any]:
    """Create a strict-schema artifact using actual computed outputs."""
    if not semantics_approved:
        raise ValueError('Science-owner approval of measurement semantics is required before production review export.')
    episodes = summary["episodes"]
    if not episodes:
        raise ValueError('v0.1 mandatory numeric energy_deficit cannot represent unavailable shading. Do not substitute a healthy placebo.')
    shortfall = summary["shortfall"]
    heldout = summary["heldout_healthy"]
    score = heldout["score"]
    if not isinstance(shortfall["positive_only_shortfall_kwh"], (int, float)) or shortfall["expected_energy_kwh"] in (None, 0):
        raise ValueError("Cannot export an energy shortfall without a positive measured expected-energy denominator")
    if score.get("nmae") is None or score.get("mae_w") is None or score.get("bias_w") is None:
        raise ValueError("Cannot export calibration metrics when the held-out healthy evaluation is absent")
    sample_rows = _sample_rows(bins, model_info, episodes, max_samples=max_samples)
    if not sample_rows:
        raise ValueError("No compact samples available for the review artifact")
    selected = summary["selected_model"]
    simple = model_info["heldout_healthy_scores"]["capacity_table_arithmetic"]
    calibrated = model_info["heldout_healthy_scores"][model_info["selected_model_name"]]
    start = min(ep["start"] for ep in episodes)
    end = max(ep["end"] for ep in episodes) + pd.Timedelta(seconds=summary["sample_audit"]["nominal_sampling_interval_seconds"])
    checksums = []
    for check in file_checks:
        if not check["checksum_matches"]:
            raise ValueError(f"A verified checksum is required in the artifact for {check['file']}")
        checksums.append({"algorithm": "md5", "digest": check["md5"], "scope": f"Zenodo file {check['file']}"})

    quality_checks = [
        {
            "name": "source_checksums",
            "status": "passed" if all(x["checksum_matches"] for x in file_checks) else "failed",
            "detail": f"Verified pinned-record MD5 and byte size for {len(file_checks)} downloaded source file(s).",
        },
        {
            "name": "exact_inverter_timestamp_alignment",
            "status": "passed" if alignment["exact_coverage_of_smaller_stream"] >= 0.95 else "failed",
            "detail": f"Exact timestamp intersection covered {alignment['exact_coverage_of_smaller_stream']:.3%} of the smaller unique electrical stream; no nearest-neighbor interpolation was used.",
            "result": str(alignment["exact_common_timestamps"]),
        },
        {
            "name": "heldout_healthy_calibration",
            "status": "passed" if heldout["calibration_valid"] else "failed",
            "detail": f"Held-out healthy model coverage={heldout['selected_model_coverage']:.3%}; nMAE={score['nmae']:.6g}; MAE={score['mae_w']:.6g} W; signed bias={score['bias_w']:.6g} W. Bias is reported as prediction minus observation.",
        },
        {
            "name": "reference_stability_screen",
            "status": "reported" if summary["reference_stability"]["status"] == "stable_by_predeclared_screen" else "failed",
            "detail": summary["reference_stability"]["screen"] + f" Result: {summary['reference_stability']['status']}; monthly relative range={summary['reference_stability']['monthly_relative_range']}.",
        },
        {
            "name": "experimental_coverage",
            "status": "passed" if shortfall["coverage"] >= 0.80 else "failed",
            "detail": f"Elapsed-time coverage of post-training labelled intervals={shortfall['coverage']:.3%}; valid integrated intervals={shortfall['valid_interval_count']}; target labelled samples={summary['sample_audit']['fault_labelled_target_samples']}. This pooled descriptive estimate may include exploratory validation-period episodes; the final held-out test-only episode count is {summary['heldout_test_shading']['episode_count']}.",
        },
        {
            "name": "noncausal_interpretation",
            "status": "reported",
            "detail": "A deviation relative to a healthy-period reference is not proof of a particular physical cause or recoverable commercial energy.",
        },
    ]
    placebo = summary["placebo"]
    placebo_finding = {
        "name": "heldout_healthy_placebo_false_shortfall",
        "status": "reported" if placebo.get("status") == "evaluated" else "not_evaluated",
        "detail": json.dumps(_clean(placebo), separators=(",", ":")),
    }
    robustness_findings = [
        {
            "name": "missingness_sensitivity",
            "status": "reported" if summary["missingness_sensitivity"].get("status") == "evaluated" else "not_evaluated",
            "detail": json.dumps(_clean(summary["missingness_sensitivity"]), separators=(",", ":")),
            "synthetic": bool(summary["missingness_sensitivity"].get("synthetic", False)),
        }
    ]
    interval = shortfall["episode_cluster_bootstrap_95pct_interval_kwh"]
    uncertainty = {
        "method": shortfall["uncertainty_method"],
        "independent_blocks": {"count": shortfall["independent_episode_count"], "unit": "separated experimental shading episodes; no row-level independence assumed"},
        "exploratory": bool(shortfall["uncertainty_exploratory"]),
        "limitations": [
            "The number of independent interventions may be small; episode resampling does not establish population-wide performance.",
            "Within-episode autocorrelation is handled by resampling whole episodes, but between-episode independence is still an assumption.",
        ],
    }
    if interval is None:
        uncertainty["interval"] = None
        uncertainty["not_estimated_reason"] = shortfall["uncertainty_not_estimated_reason"] or "Too few independent episodes for a cluster bootstrap interval."
    else:
        uncertainty["interval"] = {"level": 0.95, "lower": interval[0], "upper": interval[1], "unit": "kWh"}

    capacity_value = shortfall["expected_energy_kwh"]
    artifact = {
        "schema_version": "0.1.0",
        "review_id": "review_la-reunion-shading-" + pd.Timestamp(produced_at).strftime("%Y%m%d"),
        "analysis_version": summary["analysis_version"],
        "produced_at": produced_at,
        "dataset": {
            "name": "La Réunion rooftop PV electrical production and shading dataset",
            "source": RECORD_URL,
            "version": "v2 (record 7291380; DOI 10.5281/zenodo.7291380)",
            "extraction_date": pd.Timestamp(produced_at).date().isoformat(),
            "checksums": checksums,
        },
        "experiment": {
            "identifier": "la-reunion-shading-" + pd.Timestamp(produced_at).strftime("%Y%m%d"),
            "type": "documented_experimental_shading",
            "experimental_system": {
                "identifier": "inverter-1",
                "description": "Electrical production file dt2; line exposed to documented shading labels; AC grid-injected power Pg in W.",
            },
            "reference_system": {
                "identifier": "inverter-2",
                "description": "Electrical production file dt3; nonidentical comparison line; raw AC grid-injected power Pg in W; stability screened on healthy periods.",
            },
            "time_window": {"start": start.isoformat(), "end": end.isoformat()},
            "label_provenance": {
                "source": "dt2_electrical_production_inverter_1_with_faults.csv, column Fault",
                "method": "Use Fault only to restrict model fitting to documented healthy rows and to group/evaluate experimental intervals; never as a predictor.",
                "label": "Numeric shading and no-fault labels documented in Zenodo metadata table 3; grouped into intervention episodes with a predeclared 300-second nonfault-gap rule.",
                "reference": "https://doi.org/10.5281/zenodo.7291380",
            },
        },
        "series": {"timestamp_basis": "UTC", "power_unit": "W", "samples": sample_rows},
        "metrics": {
            "energy_deficit": {
                "value": float(shortfall["positive_only_shortfall_kwh"]),
                "unit": "kWh",
                "calculation": shortfall["energy_method"] + f" This is a pooled post-training descriptive estimate, including exploratory validation-period episodes; final held-out test-only episode count={summary['heldout_test_shading']['episode_count']}. Signed net deviation is reported in model_comparison_results.json because v0.1 has no distinct signed field.",
            },
            "deficit_fraction": {
                "value": float(shortfall["positive_shortfall_fraction"]),
                "unit": "1",
                "numerator": {"value": float(shortfall["positive_only_shortfall_kwh"]), "unit": "kWh"},
                "denominator": {"value": float(capacity_value), "unit": "kWh"},
                "calculation": "positive-only shortfall kWh divided by expected target production kWh over the same valid labelled intervals",
            },
            "coverage": {
                "value": float(shortfall["coverage"]),
                "unit": "1",
                "numerator": {"value": float(shortfall["valid_elapsed_seconds"]), "unit": "s"},
                "denominator": {"value": float(shortfall["labelled_elapsed_seconds"]), "unit": "s"},
                "calculation": "Valid integrated elapsed seconds divided by eligible labelled elapsed seconds; count fields are reported separately.",
            },
            "calibration_error": {
                "value": float(score["nmae"]),
                "unit": "1",
                "statistic": "held-out healthy nMAE = MAE / mean observed target AC power",
                "evaluation_population": "held_out_healthy",
                "numerator": {"value": float(score["mae_w"]), "unit": "W"},
                "denominator": {"value": float(score["mean_observed_w"]), "unit": "W"},
            },
            "valid_interval_count": int(shortfall["valid_interval_count"]),
            "total_interval_count": int(shortfall["total_interval_count"]),
        },
        "baseline_comparison": {
            "metric": "held-out healthy mean absolute error",
            "unit": "W",
            "evaluation_population": "chronological held-out healthy daylight five-minute bins",
            "simple_baseline": {"name": "capacity ratio from literal Table 1 module ratings (2.10 / 2.04 kWp); capacity mapping discrepancy is documented", "value": float(simple["mae_w"])},
            "calibrated_reference": {"name": f"{model_info['selected_model_name']} (healthy training only)", "value": float(calibrated["mae_w"])},
            "reported_difference": {"value": float(simple["mae_w"] - calibrated["mae_w"]), "unit": "W"},
            "calculation": "Both MAEs use the same held-out healthy bins; model choice uses only healthy validation data.",
        },
        "uncertainty": uncertainty,
        "quality_checks": quality_checks,
        "exclusions": [
            {"start": item["start"].isoformat(), "end": item["end"].isoformat(), "reason": item["reason"]}
            for item in summary["episode_exclusions"]
        ],
        "decision": {
            "state": summary["decision"]["state"],
            "reasons": summary["decision"]["reasons"],
            "rules_version": summary["decision"]["rules_version"],
        },
        "limitations": [
            "The dataset is a La Réunion experimental installation; no Indian-site performance is inferred.",
            "A measured deviation from a healthy-period reference is not causal repair attribution.",
            "Positive-only estimated shortfall is not verified commercial energy recovery.",
            "The two inverter lines are nonidentical; the source's capacity text and module table do not reconcile exactly.",
            "Any interval estimates use separated experimental episodes as the independent unit; serial rows are not independent observations.",
        ],
        "robustness": {"status": "evaluated" if summary["missingness_sensitivity"].get("status") == "evaluated" else "not_evaluated", "findings": robustness_findings},
        "placebo": {"status": "evaluated" if placebo.get("status") == "evaluated" else "not_evaluated", "findings": [placebo_finding]},
    }
    artifact['review_id'] = review_identity(artifact['experiment']['identifier'])[0]
    return _clean(artifact)


def validate_review_artifact(artifact: dict[str, Any], schema_path: str | Path) -> list[str]:
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8-sig"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(artifact), key=lambda error: ".".join(map(str, error.absolute_path)))
    return [f"{'.'.join(str(x) for x in error.absolute_path) or '$'}: {error.message}" for error in errors]


def write_review_artifact(artifact: dict[str, Any], path: str | Path, schema_path: str | Path) -> Path:
    errors = validate_review_artifact(artifact, schema_path)
    if errors:
        raise ValueError("Review artifact failed schema validation: " + " | ".join(errors))
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(artifact, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return destination
