"""Deterministic, source-backed provisional v0.2 review exports for V2 cases.

The pinned raw dataset is intentionally not required: this exporter consumes
only committed V2 outputs and preserves their recorded raw-source hashes.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


RAW_NAMES = (
    "dt1_solar_and_meteorological_measurement.csv",
    "dt2_electrical_production_inverter_1_with_faults.csv",
    "dt3_electrical_production_inverter_2.csv",
    "00_metadata_variable.jpg",
)
V2_INPUTS = (
    "results/data_quality_report_v2.json",
    "results/shading_evaluation_v2.json",
    "results/model_comparison_v2.json",
    "results/frozen_parameters_v2.json",
    "results/example_cases_v2.json",
    "results/demo_measured_series_v2.csv",
    "results/five_minute_evaluation_v2.csv",
)
METRIC_IDS = {
    "healthy_mae", "healthy_nmae", "healthy_bias", "episode_recall",
    "healthy_alarm_runs_per_hour", "signed_generation_deviation",
    "positive_only_generation_deviation", "observed_energy", "expected_energy",
}


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _digest(path: Path) -> tuple[str, str, int]:
    data = path.read_bytes()
    return hashlib.md5(data).hexdigest(), hashlib.sha256(data).hexdigest(), len(data)


def _f(value: Any) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"Non-finite value in committed source output: {value!r}")
    return number


def _utc(value: str) -> str:
    """Canonicalize an already-aware source timestamp to UTC Z notation."""
    from datetime import datetime, timezone

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"Source timestamp has no timezone: {value}")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _source_checksums(analysis_dir: Path, quality: dict[str, Any]) -> list[dict[str, Any]]:
    checks = quality["checks"]
    by_name = {item["file"]: item for item in checks}
    if set(by_name) != set(RAW_NAMES) or not all(item["checksum_matches"] for item in checks):
        raise ValueError("Committed V2 source audit does not verify all four pinned source files")

    manifest = _json(analysis_dir / "results" / "package_manifest_v2.json")
    entries: list[dict[str, Any]] = []
    for name in RAW_NAMES:
        item = by_name[name]
        entries.append({
            "file": name,
            "md5": item["md5"],
            "sha256": item["sha256"],
            "role": "pinned Zenodo record 7291380 source file",
            "source_verification": (
                "V2 checksum-verified run and committed independent_verification_v2.json; "
                "raw bytes are not present in this checkout and were not rehashed by this exporter"
            ),
            "byte_count": int(item["bytes"]),
        })

    for relative in V2_INPUTS:
        path = analysis_dir / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        md5, sha256, size = _digest(path)
        expected = manifest.get(relative)
        if expected is None or expected != sha256:
            raise ValueError(f"Committed V2 package manifest mismatch for {relative}")
        entries.append({
            "file": relative,
            "md5": md5,
            "sha256": sha256,
            "role": "committed V2 analysis input",
            "source_verification": "rehashed by this exporter and matched to package_manifest_v2.json",
            "byte_count": size,
        })
    return entries


def _metric(
    metric_id: str, value: float | None, unit: str, population: str,
    definition: str, calculation: str, *, reason: str | None = None,
    valid_seconds: float | None = None,
    observed_labelled_seconds: float | None = None,
    wall_span_seconds: float | None = None,
    ratio: dict[str, Any] | None = None,
    uncertainty: dict[str, Any] | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": metric_id,
        "availability": "estimated" if value is not None else "unavailable",
        "value": value,
        "unit": unit,
        "population": population,
        "definition": definition,
        "calculation": calculation,
        "reason": None if value is not None else reason,
        "coverage": {
            "valid_seconds": valid_seconds,
            "observed_labelled_seconds": observed_labelled_seconds,
            "wall_span_seconds": wall_span_seconds,
        },
        "ratio": ratio,
        "uncertainty": uncertainty,
    }
    return item


def _study_metrics(shading: dict[str, Any], comparison: dict[str, Any]) -> list[dict[str, Any]]:
    weather = comparison["later_healthy_scores"]["weather_assisted_linear"]
    alarm = shading["healthy_stability"]["5"]
    episodes = shading["episode_count"]
    detected = shading["detected_episodes"]
    population = (
        "zero-labelled, supported daylight five-minute bins in the later stability period; "
        f"n={weather['n']} over the committed evaluation output"
    )
    metrics = [
        _metric("healthy_mae", _f(weather["mae_w"]), "W", population,
                "Mean absolute error of model-expected minus measured experimental AC power.",
                "Committed V2 later_healthy_scores.weather_assisted_linear.mae_w."),
        _metric("healthy_nmae", _f(weather["nmae"]), "1", population,
                "Healthy-labelled MAE divided by mean measured experimental AC power.",
                "Committed V2 nMAE; numerator is MAE and denominator is mean_observed_w.",
                ratio={"numerator": _f(weather["mae_w"]), "denominator": _f(weather["mean_observed_w"]),
                       "numerator_unit": "W", "denominator_unit": "W"}),
        _metric("healthy_bias", _f(weather["bias_w"]), "W", population,
                "Mean expected-minus-measured AC power; positive means model prediction is higher.",
                "Committed V2 later_healthy_scores.weather_assisted_linear.bias_w."),
        _metric("episode_recall", detected / episodes, "1",
                f"All {episodes} retrospectively grouped documented shading interventions on one installation.",
                "Fraction of documented intervention episodes with a detector confirmation within the event span.",
                "Detected grouped interventions divided by all grouped interventions; retrospective label overlap rule.",
                ratio={"numerator": detected, "denominator": episodes,
                       "numerator_unit": "episodes", "denominator_unit": "episodes"}),
        _metric("healthy_alarm_runs_per_hour",
                _f(alarm["healthy_alert_runs"]) / _f(alarm["evaluated_healthy_hours"]),
                "alarms/hour", "Later zero-labelled supported healthy-window evaluation population.",
                "Contiguous alert runs whose support is all zero-labelled, divided by evaluated supported hours.",
                "Committed V2 five-minute detector evaluation; mixed-label boundary alerts excluded.",
                ratio={"numerator": int(alarm["healthy_alert_runs"]),
                       "denominator": _f(alarm["evaluated_healthy_hours"]),
                       "numerator_unit": "alarm runs", "denominator_unit": "hours"}),
    ]
    assert len(metrics) == 5 and {item["id"] for item in metrics} <= METRIC_IDS
    return metrics


def _event_metrics(case: dict[str, Any], *, is_labelled: bool) -> list[dict[str, Any]]:
    energy = case["energy"]
    if not energy["available"]:
        unavailable_reason = "The committed V2 event result reports no estimable energy for this case."
        return [
            _metric(metric_id, None, unit, "Event case unavailable in the committed V2 output.",
                    definition, "No integration was performed.", reason=unavailable_reason)
            for metric_id, unit, definition in (
                ("signed_generation_deviation", "kWh", "Expected minus measured AC energy."),
                ("positive_only_generation_deviation", "kWh", "Endpoint-truncated integral of positive expected-minus-measured residual."),
                ("observed_energy", "kWh", "Measured target AC energy."),
                ("expected_energy", "kWh", "Healthy model-expected target AC energy."),
            )
        ]
    valid = _f(energy["valid_seconds"])
    support = _f(energy.get("observed_labelled_support_seconds", energy["valid_seconds"]))
    wall = _f(energy.get("wall_span_coverage", energy["valid_seconds"]))
    wall = support if is_labelled else valid
    coverage = {"valid_seconds": valid, "observed_labelled_seconds": support if is_labelled else None,
                "wall_span_seconds": wall}
    if is_labelled and case.get("placebo", {}).get("status") == "available":
        placebo = case["placebo"]
        lower, upper = map(_f, placebo["empirical_model_error_band_kwh"])
        uncertainty = {
            "kind": "empirical_model_error_band",
            "method": (
                "Signed event deviation minus calibration-only matched-placebo signed-energy "
                "97.5th and 2.5th percentiles, respectively."
            ),
            "unit": "kWh", "lower": lower, "upper": upper,
            "group_count": int(placebo["blocks"]),
            "limitations": [
                "Empirical model-error band, not a confidence interval for true counterfactual loss.",
                f"{placebo['days']} local days; adjacent placebo days may be dependent.",
                "Matching uses calibration-only reference-power and GTI tolerances; the reference is not a true unshaded counterfactual.",
            ],
        }
    else:
        uncertainty = None
    population = (
        "Original source-record intervals within the recorded labelled intervention boundaries; "
        "only adjacent rows with both endpoints labelled, eligible, source-row consecutive, and 0<dt<=18 s."
        if is_labelled else
        "Original source-record intervals in the recorded zero-labelled example window; only eligible adjacent intervals with 0<dt<=18 s."
    )
    metrics = [
        _metric("signed_generation_deviation", _f(energy["signed_energy_kwh"]), "kWh", population,
                "Integral of healthy expected target AC power minus measured target AC power; may be negative.",
                "Trapezoids over actual elapsed UTC seconds on valid consecutive source records; no bridging gaps or unlabelled pauses.",
                uncertainty=uncertainty, **coverage),
        _metric("positive_only_generation_deviation", _f(energy["positive_only_kwh"]), "kWh", population,
                "Integral of endpoint residuals clipped at zero; not recoverable or commercial energy.",
                "Same valid intervals as signed deviation; positive endpoints are clipped before trapezoidal integration, so zero crossing is approximate.",
                **coverage),
        _metric("observed_energy", _f(energy["actual_energy_kwh"]), "kWh", population,
                "Integrated measured target AC energy over the same valid intervals.",
                "Source-derived trapezoidal elapsed-time integral over the same intervals as signed deviation.", **coverage),
        _metric("expected_energy", _f(energy["expected_energy_kwh"]), "kWh", population,
                "Integrated calibrated healthy model-expected target AC energy over the same valid intervals.",
                "Source-derived trapezoidal elapsed-time integral over the same intervals as signed deviation.", **coverage),
    ]
    return metrics


def _review_base(
    experiment_id: str, kind: str, start: str, end: str,
    checksums: list[dict[str, Any]], frozen: dict[str, Any],
    shading: dict[str, Any], comparison: dict[str, Any],
    exporter_sha: str, *, window_context: dict[str, Any],
    metrics: list[dict[str, Any]], samples: list[dict[str, Any]],
    source_count: int, downsampling: str,
    electrical: list[dict[str, Any]], candidates: list[dict[str, Any]],
    limitations: list[str], event_review_reason: str,
) -> dict[str, Any]:
    model = frozen["model_comparison_pre_protected"]["parameters"]["weather_assisted_linear"]
    result = {
        "schema_version": "0.2.0",
        "approval_status": "proposed",
        "review_id": "review_" + experiment_id,
        "experiment": {
            "identifier": experiment_id,
            "type": kind,
            "start": _utc(start),
            "end": _utc(end),
            "event_context": window_context,
        },
        "provenance": {
            "protocol_sha256": frozen["protocol_sha256"],
            "source_checksums": checksums,
            "model": {
                "name": "weather_assisted_linear",
                "target": "experimental inverter target AC Pg, W",
                "predictors": model["features"],
                "intercept_w": _f(model["intercept_w"]),
                "coefficients": {name: _f(value) for name, value in model["coefficients"].items()},
                "training_rows": int(model["training_rows"]),
                "preprocessing": model["preprocessing"],
                "expected_power_semantics": "Calibrated healthy expected target AC power; distinct from raw reference inverter Pg.",
            },
            "splits": frozen["boundaries"],
            "thresholds": {
                "primary_window_minutes": int(frozen["primary_minutes"]),
                "persistence_windows": int(frozen["persistence_windows"]),
                "statistic": "signed healthy calibration residual mean; 99th percentile; floor at zero",
                "by_window_minutes": {str(key): _f(value) for key, value in frozen["thresholds_w"].items()},
                "calibration_population": "known-zero-label eligible windows in 2022-01-26 through 2022-02-07 RET local days",
            },
            "evaluation_population": (
                "Retrospective single-installation V2 analysis; no prospective or fleet-level validation. "
                "Healthy-labelled populations use zero labels and do not rule out unrecorded faults."
            ),
            "grouping": {
                "label_interval": window_context.get("label_interval_utc"),
                "detector_confirmations": window_context.get("detector_confirmations_utc", {}),
                "label_source": window_context.get("label_source"),
                "episode_gap_rule_seconds": 300,
                "event_review_decision": {
                    "availability": "unavailable",
                    "state": None,
                    "reason": event_review_reason,
                },
                "notes": "Label boundaries and detector confirmation times are distinct; confirmation is never backdated.",
            },
            "label_use": "Source Fault labels restrict known-zero fitting/calibration populations and define retrospective episode evaluation only; Fault is never a detector predictor.",
            "exclusions": [],
            "retrospective": True,
            "code_version": (
                f"V2 model code SHA256 {shading['code_sha256']}; "
                f"V3 exporter source SHA256 {exporter_sha}"
            ),
        },
        "metrics": metrics,
        "series": {
            "timestamp_basis": "UTC",
            "power_unit": "W",
            "downsampling": {
                "method": downsampling,
                "source_count": source_count,
                "retained_count": len(samples),
                "gap_markers": [],
            },
            "samples": samples,
        },
        "electrical_evidence": electrical,
        "candidate_checks": candidates,
        "decision": {
            "verdict": "LIMIT",
            "rule_version": "frozen-v2-research-gates-2026-10-10",
            "reasons": [
                "This is the experiment-level research verdict, not an event-level technician or causal decision.",
                (
                    f"The selected five-minute detector recorded {int(shading['healthy_stability']['5']['healthy_alert_runs'])} "
                    f"healthy alert runs over {_f(shading['healthy_stability']['5']['evaluated_healthy_hours']):.4f} supported hours "
                    f"({_f(shading['healthy_stability']['5']['false_alarm_runs_per_healthy_hour']):.5f}/hour), "
                    "above its frozen <=0.05/hour target."
                ),
                "Energy deviation is measured-versus-modelled evidence; the unshaded experimental inverter counterfactual and recoverable electricity are unconfirmed.",
            ],
            "owner_review": None,
            "event_review": {
                "state": None,
                "availability": "unavailable",
                "reason": event_review_reason,
            },
        },
        "limitations": limitations,
    }
    return result


def _electrical_evidence(case: dict[str, Any]) -> list[dict[str, Any]]:
    values = case.get("electrical", {})
    if not values:
        return []
    support = {
        "Va": ("V", "A changed PV-side operating voltage under the matched comparison conditions.",
               "It is operating voltage, not Voc or an IV curve; it does not identify a module or prove a physical fault.", "LIMITED"),
        "Ia": ("A", "A measured DC-current comparison under the matched conditions.",
               "The event matched shift is small and its healthy-envelope rate resembles later zero-labelled operation; it adds little event-specific evidence.", "LIMITED"),
        "Ig": ("A", "Grid current changed alongside AC power output.",
               "Ig is coupled to AC output and is not independent confirmation or a grid-fault diagnosis.", "LIMITED"),
        "Vg": ("V", "Grid-side voltage context was recorded.",
               "No site/OEM threshold or grid-fault ground truth is supplied.", "LIMITED"),
        "Fg": ("Hz", "Grid-frequency context was recorded.",
               "Sampling and missing grid-quality records do not support a grid-event diagnosis.", "LIMITED"),
    }
    rows = []
    for signal, data in values.items():
        unit, supports, does_not_prove, strength = support[signal]
        rows.append({
            "signal": signal,
            "measurement": _f(data["matched_median_delta_from_healthy"]),
            "unit": unit,
            "quality": (
                f"Matched median target-minus-healthy-comparator delta; {int(data['matched_bins'])} "
                f"five-minute bins; {float(data['outside_healthy_envelope_fraction']):.6f} fraction outside the training envelope."
            ),
            "comparison_population": "Training healthy envelope by reference-Pg decile; descriptive match within 20% reference Pg, 20% GTI and 5 C TA where available.",
            "supports": supports,
            "does_not_prove": does_not_prove,
            "alternatives": ["MPPT or inverter operating state", "temperature or irradiance mismatch", "array mismatch or reference/sensor bias"],
            "missing_measurements": ["Inverter status and MPPT logs", "string-resolved telemetry", "sensor calibration/precision records", "independent cell/module measurements"],
            "strength": strength,
        })
    return rows


def _candidate_checks(event: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": "review_inverter_operating_records",
            "observed_fact": "The selected weather-assisted model has a positive measured-versus-expected AC residual in the documented intervention interval; Va also departs from its matched healthy comparator.",
            "hypothesis": "Curtailment, clipping, MPPT behaviour, or another inverter operating condition may contribute to a measured difference.",
            "supporting_evidence": ["Persistent detector evidence overlaps the source label interval.", "Va provides operating-point context."],
            "opposing_evidence": ["The source intervention label documents a shading setup, but the artifact has no inverter status or MPPT records.", "The detector's later healthy alarm rate exceeds the frozen budget."],
            "next_information": ["Review timestamped inverter status, MPPT, clipping, and curtailment records.", "Confirm time synchronization and system configuration."],
            "qualification": "Existing records may be reviewed by the operator; qualified PV personnel interpret array or electrical tests.",
            "safety_constraint": "No disconnection, energized measurement, rooftop access, or repair instruction is implied.",
            "sources": ["https://docs.nlr.gov/docs/fy19osti/73822.pdf"],
            "status": "proposed",
        },
        {
            "id": "verify_measurement_and_reference_context",
            "observed_fact": "The expected series uses inverter-2 raw Pg plus five-minute GTI, DTI and TA, while original V2 exact alignment had no unmatched electrical timestamps.",
            "hypothesis": "Reference-line drift, weather sensor representativeness, or data quality could alter the expected-versus-measured comparison.",
            "supporting_evidence": ["The two inverter lines are nonidentical.", "Weather begins after the electrical record and has observed temporal gaps."],
            "opposing_evidence": ["The committed V2 run reports checksum-verified source files and exact electrical timestamp alignment."],
            "next_information": ["Review acquisition and calibration history, weather sensor exposure, and independent irradiance records."],
            "qualification": "Record review is suitable for the site operator; calibration and field measurements follow the site plan and qualified-personnel requirements.",
            "safety_constraint": "No generic threshold or physical work procedure is provided.",
            "sources": ["https://docs.nlr.gov/docs/fy19osti/73822.pdf", "https://delta-t.co.uk/wp-content/uploads/dlm_uploads/2017/05/SPN1-UM-4.1.pdf"],
            "status": "proposed",
        },
        {
            "id": "request_shading_observation_context",
            "observed_fact": f"The source Fault label is {event['labels'][0]} and its data-paper description is {event['label_descriptions'][0]}.",
            "hypothesis": "The recorded experimental shading intervention is consistent with the measured difference; this is an intervention record, not an algorithmic diagnosis of a field installation.",
            "supporting_evidence": ["Published source label and measured/modelled V2 results agree in time."],
            "opposing_evidence": ["No independent photo, obstruction geometry, or true unshaded target output is present in this artifact."],
            "next_information": ["If reviewing a live site, request timestamped, safely obtained obstruction photographs and shade history; compare only with site records."],
            "qualification": "Qualified site personnel decide whether an inspection is indicated.",
            "safety_constraint": "No rooftop access instruction or module-level cause claim is made.",
            "sources": ["https://doi.org/10.1016/j.dib.2022.108723", "https://iea-pvps.org/wp-content/uploads/2025/02/IEA-PVPS-T13-30-2025-PVFS-ANNEX-Degradation-and-Failure.pdf"],
            "status": "proposed",
        },
    ]


def build_case_exports(analysis_dir: Path) -> dict[str, dict[str, Any]]:
    analysis_dir = analysis_dir.resolve()
    result_dir = analysis_dir / "results"
    shading = _json(result_dir / "shading_evaluation_v2.json")
    comparison = _json(result_dir / "model_comparison_v2.json")
    frozen = _json(result_dir / "frozen_parameters_v2.json")
    examples = _json(result_dir / "example_cases_v2.json")
    quality = _json(result_dir / "data_quality_report_v2.json")
    independent = _json(result_dir / "independent_verification_v2.json")
    protocol_sha = hashlib.sha256((analysis_dir / "EXPERIMENT_PROTOCOL_V2.md").read_bytes()).hexdigest()
    model_sha = hashlib.sha256((analysis_dir / "src/solarloss_research/evaluation_v2.py").read_bytes()).hexdigest()
    if protocol_sha != shading["protocol_sha256"] or protocol_sha != frozen["protocol_sha256"]:
        raise ValueError("V2 protocol does not match its frozen/result SHA256")
    if model_sha != shading["code_sha256"] or not independent.get("all_passed") or not all(independent["checks"].values()):
        raise ValueError("V2 model-code identity or independent verification failed")
    checksums = _source_checksums(analysis_dir, quality)
    exporter_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    study_metrics = _study_metrics(shading, comparison)

    event = next(item for item in shading["episodes"] if item["event_id"] == "shading_01")
    event_case = examples["shading_event"]
    if event_case["event_id"] != event["event_id"]:
        raise ValueError("V2 event example and evaluation JSON identify different events")
    context = {
        "label_interval_utc": {"start": _utc(event["start"]), "end": _utc(event["end"])},
        "detector_confirmations_utc": {
            "1_minute": _utc(event["detection"]["1"]["confirmation_utc"]),
            "5_minute_primary": _utc(event["detection"]["5"]["confirmation_utc"]),
            "15_minute_sensitivity": _utc(event["detection"]["15"]["confirmation_utc"]),
        },
        "label_source": "dt2_electrical_production_inverter_1_with_faults.csv:Fault; source metadata table 3; label 2.1",
        "label_description": event["label_descriptions"][0],
        "detector_latency_seconds_from_first_label": {
            "1_minute": int(event["detection"]["1"]["latency_seconds"]),
            "5_minute_primary": int(event["detection"]["5"]["latency_seconds"]),
            "15_minute_sensitivity": int(event["detection"]["15"]["latency_seconds"]),
        },
    }
    raw_event = [row for row in _read_csv(result_dir / "demo_measured_series_v2.csv")
                 if _utc(row["timestamp"]) >= context["label_interval_utc"]["start"]
                 and _utc(row["timestamp"]) <= context["label_interval_utc"]["end"]]
    if len(raw_event) != int(event["labeled_sample_count"]):
        raise ValueError("Committed measured-series row count does not match the labelled V2 event")
    event_samples = []
    for row in raw_event:
        valid = row["eligible"].strip().lower() == "true"
        event_samples.append({
            "timestamp": _utc(row["timestamp"]),
            "measured_power": _f(row["target_power_w"]),
            "raw_reference_power": _f(row["reference_power_w"]),
            "expected_power": _f(row["expected_power_w"]) if row["expected_power_w"] else None,
            "valid": bool(valid and row["expected_power_w"]),
        })
    if sum(sample["valid"] for sample in event_samples) < int(event["energy"]["interval_count"]):
        raise ValueError("Exported shading series has fewer usable samples than the integrated V2 intervals")

    event_metrics = study_metrics + _event_metrics(event_case, is_labelled=True)
    event_metrics[0]["population"] = "Later zero-labelled daylight population; 24,320 common weather-eligible bins over 235 days."
    event_limitations = [
        f"The experiment-level research verdict is LIMIT; {shading['detected_episodes']}/{shading['episode_count']} retrospective intervention recall does not establish future sensitivity.",
        "Healthy alarm rate is computed on zero-labelled operation; unrecorded faults cannot be ruled out.",
        "Measured-versus-modelled signed deviation is not a causal counterfactual loss estimate.",
        "No confirmed recoverable electricity, repair recovery, financial saving, or commercial claim is available.",
        "The target inverter's unshaded experimental counterfactual is not observed; event-level decision is unavailable.",
        "Electrical observations provide context and do not independently validate physical cause.",
        "Raw source bytes are not present in this checkout; their committed V2 hashes are carried forward without rehashing here.",
    ]
    shading_review = _review_base(
        "shading_01", "documented_shading", event["start"], event["end"], checksums,
        frozen, shading, comparison, exporter_sha, window_context=context,
        metrics=event_metrics, samples=event_samples, source_count=len(raw_event),
        downsampling="None; all original labelled source timestamps retained from the committed 5-second-cadence measured-series excerpt. Energy uses V2 raw-record integration, not the display series.",
        electrical=_electrical_evidence(event), candidates=_candidate_checks(event),
        limitations=event_limitations,
        event_review_reason=(
            f"Unavailable: the event has documented intervention label {event['labels'][0]} and measured-versus-modelled evidence, "
            "but no true unshaded target counterfactual; reference mismatch, operating state and sensor alternatives "
            "are not ruled out. Do not assign supported_change solely from Fault=2.1."
        ),
    )

    healthy_case = examples["healthy_interval"]
    healthy_energy = healthy_case["energy"]
    from datetime import datetime, timedelta, timezone

    healthy_start = datetime.fromisoformat(healthy_case["start"].replace("Z", "+00:00"))
    healthy_end = datetime.fromisoformat(healthy_case["end"].replace("Z", "+00:00"))
    rows = []
    for row in _read_csv(result_dir / "five_minute_evaluation_v2.csv"):
        stamp = datetime.fromisoformat(row["bin_start"].replace("Z", "+00:00"))
        if healthy_start.replace(minute=(healthy_start.minute // 5) * 5, second=0, microsecond=0) <= stamp < healthy_end:
            rows.append((stamp, row))
    rows.sort(key=lambda pair: pair[0])
    if len(rows) != 12 or any(row["known"] != "True" or row["fault_fraction"] != "0.0" for _, row in rows):
        raise ValueError("Healthy comparison must contain 12 known-zero-label five-minute bins")
    healthy_samples = []
    for stamp, row in rows:
        midpoint = stamp + timedelta(seconds=150)
        healthy_samples.append({
            "timestamp": midpoint.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "measured_power": _f(row["target_power_w"]),
            "raw_reference_power": _f(row["reference_power_w"]),
            "expected_power": _f(row["expected_power_w"]),
            "valid": row["eligible"] == "True" and row["quality"] == "True",
        })
    if not all(sample["valid"] for sample in healthy_samples):
        raise ValueError("Healthy comparison has an ineligible display bin")
    healthy_metrics = study_metrics + _event_metrics(healthy_case, is_labelled=False)
    healthy_window_context = {
        "label_interval_utc": None,
        "observed_raw_support_utc": {"start": _utc(healthy_case["start"]), "end": _utc(healthy_case["end"])},
        "label_source": "Known-zero Fault labels in the V2 source; absence of a label is not proof of a physically fault-free system.",
        "detector_calibration_population": True,
        "note": "Comparison interval lies within the frozen detector-calibration dates; it is not an independent post-selection test.",
    }
    healthy_metrics[5]["population"] = "Original source-record intervals in this known-zero-label comparison window; 719 supported intervals over 3,595 seconds."
    healthy_limitations = [
        "This one-hour zero-labelled comparison lies inside the detector calibration period and is not an independent holdout.",
        "Zero Fault labels do not rule out unrecorded faults or prove the plant was physically healthy.",
        "Positive signed or positive-only deviation in a labelled-healthy interval demonstrates model error; it is not recovered energy.",
        "The V2 experiment-level detector verdict remains LIMIT; these interval values do not change the frozen result.",
        "The series contains five-minute means plotted at bin midpoints; energy metrics come from the original supported source records.",
    ]
    healthy_review = _review_base(
        "healthy_20220126_0300", "healthy_stability", healthy_case["start"], healthy_case["end"],
        checksums, frozen, shading, comparison, exporter_sha, window_context=healthy_window_context,
        metrics=healthy_metrics, samples=healthy_samples, source_count=len(rows),
        downsampling="Twelve committed five-minute bin means; each timestamp is the bin midpoint in UTC. Display only; energy is from the original source-record result.",
        electrical=[], candidates=[], limitations=healthy_limitations,
        event_review_reason="Not applicable to a selected zero-labelled comparison interval; no event-level causal state is assigned.",
    )

    gap = examples["insufficient_data"]
    gap_id = "insufficient_data_gap_20211222_20220124"
    gap_record = {
        "case_record_version": "1.0.0",
        "status": "unavailable_for_proposed_v0_2_review",
        "review_id": "review_" + gap_id,
        "experiment_identifier": gap_id,
        "source_case": "example_cases_v2.insufficient_data",
        "source_gap_utc": {"previous_observation": _utc(gap["start"]), "next_observation": _utc(gap["end"])},
        "gap_seconds": _f(gap["gap_seconds"]),
        "energy_deviation": {
            "availability": "unavailable", "value": None, "unit": "kWh",
            "reason": "No supported aligned source intervals occur within the gap; no interpolation or energy integration is performed.",
        },
        "event_review_state": {"availability": "unavailable", "state": None,
                               "reason": "The v0.2 type enum has no data-gap/insufficient-data type; assigning one of its current types would imply unsupported semantics."},
        "provenance": {
            "source_checksums": checksums,
            "v2_result_sha256": {relative: _digest(analysis_dir / relative)[1] for relative in V2_INPUTS},
        },
        "limitations": [
            "This is an explicit unavailability record, not a v0.2 review artifact and must not be passed to the backend preview validator.",
            "The interval is a measured-data gap between adjacent recorded timestamps; its cause is not classified here.",
            "The v0.2 schema has no type for an insufficient-data or data-gap review case and lacks an event-level unavailable state contract.",
        ],
    }
    return {
        "review_shading_01.json": shading_review,
        "review_healthy_20220126_0300.json": healthy_review,
        "review_insufficient_data_gap_20211222_20220124.json": gap_record,
    }


def validate_case_exports(analysis_dir: Path, output_dir: Path) -> list[str]:
    analysis_dir = analysis_dir.resolve()
    schema_path = analysis_dir / "contracts" / "review.schema.v0.2.0.proposed.json"
    schema = _json(schema_path)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    expected_names = (
        "review_shading_01.json",
        "review_healthy_20220126_0300.json",
        "review_insufficient_data_gap_20211222_20220124.json",
    )
    errors: list[str] = []
    for name in expected_names:
        path = output_dir / name
        if not path.is_file():
            errors.append(f"Missing expected case export: {name}")
            continue
        artifact = _json(path)
        if name.endswith("20211222_20220124.json"):
            if artifact.get("status") != "unavailable_for_proposed_v0_2_review":
                errors.append(f"{name}: unsupported data-gap case was not explicitly marked unavailable")
            continue
        for error in validator.iter_errors(artifact):
            errors.append(f"{name}: schema {'.'.join(map(str, error.absolute_path)) or '$'}: {error.message}")
        experiment_id = artifact.get("experiment", {}).get("identifier")
        expected_id = "review_" + str(experiment_id)
        if artifact.get("review_id") != expected_id or path.stem != expected_id:
            errors.append(f"{name}: filename, experiment.identifier, and review_id do not agree")
        if artifact.get("approval_status") != "proposed":
            errors.append(f"{name}: proposed v0.2 artifact must not claim owner approval")
        decision = artifact.get("decision", {})
        if decision.get("event_review", {}).get("availability") != "unavailable":
            errors.append(f"{name}: event-level review state must remain explicitly unavailable")
        if decision.get("verdict") != "LIMIT":
            errors.append(f"{name}: V2 research verdict must remain LIMIT")
        if artifact.get("provenance", {}).get("source_checksums", [{}])[0].get("sha256") is None:
            errors.append(f"{name}: source provenance checksum is missing")
        if len({metric.get("id") for metric in artifact.get("metrics", [])}) != len(artifact.get("metrics", [])):
            errors.append(f"{name}: duplicate metric identifier")
    if not errors:
        expected = build_case_exports(analysis_dir)
        for name in expected_names:
            if not (output_dir / name).is_file():
                continue
            if _json(output_dir / name) != expected[name]:
                errors.append(f"{name}: artifact does not reconcile exactly with committed V2 inputs and exporter")
        for name in expected_names[:2]:
            if not (output_dir / name).is_file():
                continue
            artifact = _json(output_dir / name)
            for metric in artifact["metrics"]:
                if metric["ratio"] is not None:
                    ratio = metric["ratio"]
                    expected_value = ratio["numerator"] / ratio["denominator"]
                    if not math.isclose(metric["value"], expected_value, rel_tol=1e-12, abs_tol=1e-12):
                        errors.append(f"{name}: {metric['id']} value does not equal its recorded ratio")
    return errors


def export_case_exports(analysis_dir: Path, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    exports = build_case_exports(analysis_dir)
    destinations = []
    for name, artifact in exports.items():
        path = output_dir / name
        path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        destinations.append(path)
    return destinations


def main() -> int:
    parser = argparse.ArgumentParser(description="Export and validate source-backed SolarLoss V2 case reviews.")
    parser.add_argument("action", choices=("export", "validate"))
    parser.add_argument("--analysis-dir", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[2] / "results" / "reviews_v3")
    args = parser.parse_args()
    analysis_dir = args.analysis_dir.resolve()
    output_dir = args.output_dir.resolve()
    if args.action == "export":
        paths = export_case_exports(analysis_dir, output_dir)
        print("Wrote " + ", ".join(path.name for path in paths))
        print("The data-gap case is an explicit unavailability record, not a v0.2 review artifact.")
        return 0
    errors = validate_case_exports(analysis_dir, output_dir)
    if errors:
        for error in errors:
            print("ERROR: " + error)
        return 1
    print("V2 shading and healthy review artifacts validated; data-gap case remains explicitly unavailable for v0.2.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
