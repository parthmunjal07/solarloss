"""Cross-field checks not represented directly by the versioned JSON Schemas.

The v0.1 checks retain their original structural scope. Proposed v0.2 checks
enforce explicit data-shape and availability semantics without selecting
thresholds or validating scientific conclusions.
"""

import math
import re
from datetime import datetime, timedelta
from numbers import Real
from pathlib import Path
from typing import Any

from .errors import InvalidArtifact


def _timestamp(value: str, location: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        # FormatChecker normally catches this; keep errors actionable if called
        # independently or if the parser's accepted formats change.
        raise InvalidArtifact(f"Invalid date-time at {location}") from exc


def validate_structural_invariants(review: dict[str, Any]) -> None:
    """Reject unambiguous structural inconsistencies after JSON Schema checks."""
    window = review["experiment"]["time_window"]
    window_start = _timestamp(window["start"], "experiment.time_window.start")
    window_end = _timestamp(window["end"], "experiment.time_window.end")
    if window_start >= window_end:
        raise InvalidArtifact(
            "experiment.time_window.start must be earlier than experiment.time_window.end"
        )

    samples = review["series"]["samples"]
    previous = None
    for index, sample in enumerate(samples):
        current = _timestamp(sample["timestamp"], f"series.samples[{index}].timestamp")
        if previous is not None and current <= previous:
            raise InvalidArtifact(
                "series.samples timestamps must be strictly increasing; "
                f"series.samples[{index}].timestamp is not later than the previous sample"
            )
        previous = current

        lower = sample.get("expected_lower_bound")
        upper = sample.get("expected_upper_bound")
        if lower is not None and lower > upper:
            raise InvalidArtifact(
                f"series.samples[{index}].expected_lower_bound cannot exceed expected_upper_bound"
            )

    metrics = review["metrics"]
    if metrics["valid_interval_count"] > metrics["total_interval_count"]:
        raise InvalidArtifact(
            "metrics.valid_interval_count cannot exceed metrics.total_interval_count"
        )

    interval = review["uncertainty"].get("interval")
    if interval is not None and interval["lower"] > interval["upper"]:
        raise InvalidArtifact("uncertainty.interval.lower cannot exceed uncertainty.interval.upper")

    for index, exclusion in enumerate(review["exclusions"]):
        start = _timestamp(exclusion["start"], f"exclusions[{index}].start")
        end = _timestamp(exclusion["end"], f"exclusions[{index}].end")
        if start >= end:
            raise InvalidArtifact(
                f"exclusions[{index}].start must be earlier than exclusions[{index}].end"
            )


_EXPERIMENT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_MD5 = re.compile(r"^[a-f0-9]{32}$")
_V2_METRIC_UNITS = {
    "healthy_mae": "W",
    "healthy_nmae": "1",
    "healthy_bias": "W",
    "episode_recall": "1",
    "healthy_alarm_runs_per_hour": "alarms/hour",
    "signed_generation_deviation": "kWh",
    "positive_only_generation_deviation": "kWh",
    "observed_energy": "kWh",
    "expected_energy": "kWh",
}
_NONNEGATIVE_V2_METRICS = {
    "healthy_mae",
    "healthy_nmae",
    "episode_recall",
    "healthy_alarm_runs_per_hour",
    "positive_only_generation_deviation",
    "observed_energy",
    "expected_energy",
}
_V2_RATIO_METRICS = {
    "healthy_nmae",
    "episode_recall",
    "healthy_alarm_runs_per_hour",
}
_V2_RATIO_UNITS = {
    "healthy_nmae": ("W", "W"),
    "episode_recall": ("episodes", "episodes"),
    "healthy_alarm_runs_per_hour": ("alarm runs", "hours"),
}
_V2_ENERGY_METRICS = {
    "signed_generation_deviation",
    "positive_only_generation_deviation",
    "observed_energy",
    "expected_energy",
}


def _v2_timestamp(value: Any, location: str) -> datetime:
    current = _timestamp(value, location)
    if current.tzinfo is None or current.utcoffset() != timedelta(0):
        raise InvalidArtifact(f"{location} must use UTC because the series timestamp basis is UTC")
    return current


def _nonempty_string(value: Any, location: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidArtifact(f"{location} must be a non-empty string")


def _finite_number(value: Any, location: str) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, Real)
        or (isinstance(value, float) and not math.isfinite(value))
    ):
        raise InvalidArtifact(f"{location} must be a finite number")


def _string_list(value: Any, location: str, *, allow_empty: bool = True) -> None:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise InvalidArtifact(f"{location} must be a list of strings")
    for index, item in enumerate(value):
        _nonempty_string(item, f"{location}[{index}]")


def _validate_event_context(review: dict[str, Any]) -> None:
    experiment = review["experiment"]
    context = experiment["event_context"]
    experiment_start = _v2_timestamp(experiment["start"], "experiment.start")
    experiment_end = _v2_timestamp(experiment["end"], "experiment.end")
    experiment_type = experiment["type"]

    if experiment_type == "documented_shading":
        interval = context["label_interval_utc"]
        start = _v2_timestamp(
            interval["start"], "experiment.event_context.label_interval_utc.start"
        )
        end = _v2_timestamp(interval["end"], "experiment.event_context.label_interval_utc.end")
        if start >= end:
            raise InvalidArtifact(
                "experiment.event_context.label_interval_utc.start must be before end"
            )
        if (start, end) != (experiment_start, experiment_end):
            raise InvalidArtifact(
                "documented_shading event bounds must match the source label interval"
            )
        _nonempty_string(context["label_source"], "experiment.event_context.label_source")
        _nonempty_string(context["label_description"], "experiment.event_context.label_description")
        confirmations = context["detector_confirmations_utc"]
        latencies = context["detector_latency_seconds_from_first_label"]
        expected_names = {"1_minute", "5_minute_primary", "15_minute_sensitivity"}
        if set(confirmations) != expected_names or set(latencies) != expected_names:
            raise InvalidArtifact(
                "detector confirmation timestamps and latencies must have matching named windows"
            )
        if "5_minute_primary" not in confirmations:
            raise InvalidArtifact("the primary five-minute detector confirmation is required")
        for name in sorted(expected_names):
            confirmation = _v2_timestamp(
                confirmations[name], f"experiment.event_context.detector_confirmations_utc.{name}"
            )
            if not start <= confirmation <= end:
                raise InvalidArtifact(
                    f"detector confirmation {name} must fall within the source label interval"
                )
            latency = latencies[name]
            if isinstance(latency, bool) or not isinstance(latency, int) or latency < 0:
                raise InvalidArtifact(f"detector latency {name} must be a non-negative integer")
            observed_latency = (confirmation - start).total_seconds()
            if latency != observed_latency:
                raise InvalidArtifact(
                    f"detector latency {name} must match its UTC confirmation and label-start timestamps"
                )
    elif experiment_type == "healthy_stability":
        if context["label_interval_utc"] is not None:
            raise InvalidArtifact(
                "healthy_stability cannot invent a source intervention label interval"
            )
        support = context["observed_raw_support_utc"]
        support_start = _v2_timestamp(
            support["start"], "experiment.event_context.observed_raw_support_utc.start"
        )
        support_end = _v2_timestamp(
            support["end"], "experiment.event_context.observed_raw_support_utc.end"
        )
        if (
            support_start >= support_end
            or support_start < experiment_start
            or support_end > experiment_end
        ):
            raise InvalidArtifact(
                "healthy comparison raw support must be ordered inside the experiment window"
            )
        if context["detector_calibration_population"] is not True:
            raise InvalidArtifact(
                "the supplied zero-labelled example must retain its calibration-population status"
            )
        if context["label_source"] and "not proof" not in context["label_source"].lower():
            raise InvalidArtifact(
                "zero-labelled source context must say it is not proof of fault-free operation"
            )
        if "not an independent" not in context["note"].lower():
            raise InvalidArtifact(
                "healthy comparison must retain its non-independent calibration note"
            )


def _validate_provenance(review: dict[str, Any], schema_path: Path | None) -> None:
    provenance = review["provenance"]
    if not _SHA256.fullmatch(provenance["protocol_sha256"]):
        raise InvalidArtifact("provenance.protocol_sha256 must be a lowercase SHA256 digest")
    for field in ("evaluation_population", "label_use", "code_version"):
        _nonempty_string(provenance[field], f"provenance.{field}")

    checksum_files = set()
    for index, checksum in enumerate(provenance["source_checksums"]):
        location = f"provenance.source_checksums[{index}]"
        _nonempty_string(checksum["file"], f"{location}.file")
        if checksum["file"] in checksum_files:
            raise InvalidArtifact(f"{location}.file must be unique")
        checksum_files.add(checksum["file"])
        if not _MD5.fullmatch(checksum["md5"]):
            raise InvalidArtifact(f"{location}.md5 must be a lowercase MD5 digest")
        if not _SHA256.fullmatch(checksum["sha256"]):
            raise InvalidArtifact(f"{location}.sha256 must be a lowercase SHA256 digest")
        if isinstance(checksum["byte_count"], bool) or not isinstance(checksum["byte_count"], int):
            raise InvalidArtifact(f"{location}.byte_count must be a positive integer")
        if checksum["byte_count"] <= 0:
            raise InvalidArtifact(f"{location}.byte_count must be a positive integer")
        _nonempty_string(checksum["role"], f"{location}.role")
        _nonempty_string(checksum["source_verification"], f"{location}.source_verification")
        raw_scope = (
            "V2 checksum-verified run and committed independent_verification_v2.json; raw bytes "
            "are not present in this checkout and were not rehashed by this exporter"
        )
        committed_scope = "rehashed by this exporter and matched to package_manifest_v2.json"
        if checksum["role"] == "pinned Zenodo record 7291380 source file":
            if checksum["source_verification"] != raw_scope:
                raise InvalidArtifact(
                    f"{location} must preserve the historical raw-source verification scope"
                )
        elif checksum["role"] == "committed V2 analysis input":
            if checksum["source_verification"] != committed_scope:
                raise InvalidArtifact(
                    f"{location} must state whether the committed V2 input was rehashed"
                )
        elif checksum["role"] == "synthetic test fixture; not source evidence":
            if (
                checksum["source_verification"]
                != "synthetic test only; hash values are invented and do not verify source files"
            ):
                raise InvalidArtifact(
                    f"{location} synthetic scope must not claim source verification"
                )

    model = provenance["model"]
    _nonempty_string(model["expected_power_semantics"], "provenance.model.expected_power_semantics")
    if "distinct from raw reference" not in model["expected_power_semantics"].lower():
        raise InvalidArtifact(
            "model-expected target power must be distinguished from raw reference power"
        )
    predictors = model["predictors"]
    _string_list(predictors, "provenance.model.predictors", allow_empty=False)
    if len(predictors) != len(set(predictors)):
        raise InvalidArtifact("provenance.model.predictors must be unique")
    if any("fault" in predictor.lower() for predictor in predictors):
        raise InvalidArtifact("source Fault labels cannot be model predictors")
    _finite_number(model["intercept_w"], "provenance.model.intercept_w")
    for name, coefficient in model["coefficients"].items():
        _finite_number(coefficient, f"provenance.model.coefficients.{name}")

    splits = provenance["splits"]
    parsed_splits = {}
    for name in ("train", "selection", "calibration"):
        start_text, end_text = splits[name]
        try:
            split_start = datetime.fromisoformat(start_text).date()
            split_end = datetime.fromisoformat(end_text).date()
        except (TypeError, ValueError) as exc:
            raise InvalidArtifact(f"provenance.splits.{name} must contain two ISO dates") from exc
        if split_start > split_end:
            raise InvalidArtifact(f"provenance.splits.{name} start cannot be after its end")
        parsed_splits[name] = (split_start, split_end)
    if not (
        parsed_splits["train"][1] < parsed_splits["selection"][0]
        and parsed_splits["selection"][1] < parsed_splits["calibration"][0]
        and parsed_splits["calibration"][1]
        < datetime.fromisoformat(splits["protected_start"]).date()
    ):
        raise InvalidArtifact(
            "provenance.splits train, selection, calibration, and protected dates must be disjoint and ordered"
        )

    thresholds = provenance["thresholds"]
    if thresholds["primary_window_minutes"] not in {1, 5, 15}:
        raise InvalidArtifact(
            "provenance.thresholds.primary_window_minutes must name a recorded window"
        )
    if str(thresholds["primary_window_minutes"]) not in thresholds["by_window_minutes"]:
        raise InvalidArtifact("primary detector threshold must be present in by_window_minutes")
    for window, value in thresholds["by_window_minutes"].items():
        _finite_number(value, f"provenance.thresholds.by_window_minutes.{window}")
        if value < 0:
            raise InvalidArtifact(
                f"provenance.thresholds.by_window_minutes.{window} cannot be negative"
            )

    grouping = provenance["grouping"]
    context = review["experiment"]["event_context"]
    if grouping["label_interval"] != context["label_interval_utc"]:
        raise InvalidArtifact(
            "provenance.grouping.label_interval must match experiment.event_context"
        )
    if grouping["detector_confirmations"] != context.get("detector_confirmations_utc", {}):
        raise InvalidArtifact(
            "provenance.grouping detector confirmations must match experiment.event_context"
        )
    if grouping["label_source"] != context["label_source"]:
        raise InvalidArtifact(
            "provenance.grouping.label_source must match experiment.event_context"
        )
    if grouping["event_review_decision"] != review["decision"]["event_review"]:
        raise InvalidArtifact("provenance.grouping event review must match decision.event_review")


def _validate_metric_values(review: dict[str, Any]) -> None:
    metrics = review["metrics"]
    metric_ids = [metric["id"] for metric in metrics]
    if len(metric_ids) != len(set(metric_ids)):
        raise InvalidArtifact("metrics must have unique metric identifiers")
    by_id = {}
    for index, metric in enumerate(metrics):
        location = f"metrics[{index}]"
        metric_id = metric["id"]
        by_id[metric_id] = metric
        if metric["unit"] != _V2_METRIC_UNITS[metric_id]:
            raise InvalidArtifact(f"{location}.unit must be {_V2_METRIC_UNITS[metric_id]}")
        _nonempty_string(metric["population"], f"{location}.population")
        _nonempty_string(metric["definition"], f"{location}.definition")
        _nonempty_string(metric["calculation"], f"{location}.calculation")
        if metric["availability"] == "estimated":
            _finite_number(metric["value"], f"{location}.value")
            if metric["reason"] is not None:
                raise InvalidArtifact(
                    f"{location}.reason must be null when availability is estimated"
                )
            if metric_id in _NONNEGATIVE_V2_METRICS and metric["value"] < 0:
                raise InvalidArtifact(f"{location}.value cannot be negative for {metric_id}")
            if metric_id == "episode_recall" and metric["value"] > 1:
                raise InvalidArtifact(
                    f"{location}.value must be between 0 and 1 for episode_recall"
                )
        else:
            if metric["value"] is not None:
                raise InvalidArtifact(
                    f"{location}.value must be null when availability is {metric['availability']}"
                )
            _nonempty_string(metric["reason"], f"{location}.reason")

        ratio = metric["ratio"]
        if metric_id in _V2_RATIO_METRICS and ratio is None:
            raise InvalidArtifact(f"{location}.ratio is required for {metric_id}")
        if metric_id not in _V2_RATIO_METRICS and ratio is not None:
            raise InvalidArtifact(f"{location}.ratio is not defined for {metric_id}")
        if ratio is not None:
            if metric["availability"] != "estimated":
                raise InvalidArtifact(
                    f"{location}.ratio must be null when the metric is unavailable or not applicable"
                )
            numerator = ratio["numerator"]
            denominator = ratio["denominator"]
            _finite_number(numerator, f"{location}.ratio.numerator")
            _finite_number(denominator, f"{location}.ratio.denominator")
            if denominator <= 0:
                raise InvalidArtifact(f"{location}.ratio.denominator must be greater than zero")
            expected_units = _V2_RATIO_UNITS[metric_id]
            actual_units = (ratio["numerator_unit"], ratio["denominator_unit"])
            if actual_units != expected_units:
                raise InvalidArtifact(f"{location}.ratio units must be {expected_units}")
            if metric["availability"] == "estimated" and not math.isclose(
                numerator / denominator, metric["value"], rel_tol=1e-9, abs_tol=1e-12
            ):
                raise InvalidArtifact(
                    f"{location}.ratio numerator divided by denominator must equal value"
                )

        coverage = metric["coverage"]
        support_values = {}
        for field in ("valid_seconds", "observed_labelled_seconds", "wall_span_seconds"):
            value = coverage[field]
            support_values[field] = value
            if value is not None:
                _finite_number(value, f"{location}.coverage.{field}")
                if value < 0:
                    raise InvalidArtifact(f"{location}.coverage.{field} cannot be negative")
        valid = support_values["valid_seconds"]
        labelled = support_values["observed_labelled_seconds"]
        wall = support_values["wall_span_seconds"]
        if valid is None and (labelled is not None or wall is not None):
            raise InvalidArtifact(
                f"{location}.coverage cannot record denominators without valid_seconds"
            )
        if valid is not None and wall is None:
            raise InvalidArtifact(
                f"{location}.coverage.wall_span_seconds is required when valid_seconds is recorded"
            )
        if labelled is not None and wall is not None and labelled > wall:
            raise InvalidArtifact(
                f"{location}.coverage.observed_labelled_seconds cannot exceed wall_span_seconds"
            )
        if valid is not None and valid > (labelled if labelled is not None else wall):
            denominator_name = (
                "observed_labelled_seconds" if labelled is not None else "wall_span_seconds"
            )
            raise InvalidArtifact(
                f"{location}.coverage.valid_seconds cannot exceed its {denominator_name} denominator"
            )

        uncertainty = metric["uncertainty"]
        if uncertainty is not None:
            lower = uncertainty["lower"]
            upper = uncertainty["upper"]
            if (lower is None) != (upper is None):
                raise InvalidArtifact(f"{location}.uncertainty bounds must both be present or null")
            if lower is not None:
                _finite_number(lower, f"{location}.uncertainty.lower")
                _finite_number(upper, f"{location}.uncertainty.upper")
                if lower > upper:
                    raise InvalidArtifact(f"{location}.uncertainty.lower cannot exceed upper")
            if uncertainty["unit"] != metric["unit"]:
                raise InvalidArtifact(f"{location}.uncertainty.unit must match the metric unit")
            if uncertainty["kind"] == "not_estimated":
                if lower is not None or upper is not None or uncertainty["group_count"] != 0:
                    raise InvalidArtifact(
                        f"{location}.uncertainty not_estimated requires null bounds and zero groups"
                    )
            else:
                if lower is None or uncertainty["group_count"] <= 0:
                    raise InvalidArtifact(
                        f"{location}.uncertainty estimated bounds require a positive group count"
                    )
            if uncertainty["kind"] == "empirical_model_error_band":
                if metric_id != "signed_generation_deviation":
                    raise InvalidArtifact(
                        "empirical model-error band must attach to signed_generation_deviation"
                    )
                limitations = " ".join(uncertainty["limitations"]).lower()
                if (
                    "not a confidence interval" not in limitations
                    or "counterfactual" not in limitations
                ):
                    raise InvalidArtifact(
                        "empirical model-error band must disclaim a counterfactual confidence interval"
                    )

    energy_metrics = {metric_id: by_id.get(metric_id) for metric_id in _V2_ENERGY_METRICS}
    if all(energy_metrics.values()):
        coverages = {
            tuple(
                metric["coverage"][key]
                for key in ("valid_seconds", "observed_labelled_seconds", "wall_span_seconds")
            )
            for metric in energy_metrics.values()
        }
        population_text = [metric["population"].lower() for metric in energy_metrics.values()]
        if review["experiment"]["type"] == "documented_shading" and not all(
            "labelled intervention" in population for population in population_text
        ):
            raise InvalidArtifact(
                "shading energy metrics must describe the source labelled intervention population"
            )
        if review["experiment"]["type"] == "healthy_stability" and not all(
            "zero" in population and "source-record intervals" in population
            for population in population_text
        ):
            raise InvalidArtifact(
                "healthy example energy metrics must describe the zero-labelled source-record population"
            )
        if len(coverages) != 1:
            raise InvalidArtifact(
                "observed, expected, signed, and positive-only energy must use the same coverage support"
            )
        signed = energy_metrics["signed_generation_deviation"]["value"]
        positive = energy_metrics["positive_only_generation_deviation"]["value"]
        observed = energy_metrics["observed_energy"]["value"]
        expected = energy_metrics["expected_energy"]["value"]
        if all(
            isinstance(value, Real) and not isinstance(value, bool)
            for value in (signed, positive, observed, expected)
        ):
            if not math.isclose(expected - observed, signed, rel_tol=1e-9, abs_tol=1e-12):
                raise InvalidArtifact(
                    "expected_energy minus observed_energy must reconcile to signed deviation"
                )
            if positive < 0 or positive + 1e-12 < signed:
                raise InvalidArtifact(
                    "positive-only deviation must be non-negative and no smaller than signed deviation"
                )


def _validate_series(review: dict[str, Any]) -> None:
    series = review["series"]
    downsampling = series["downsampling"]
    for field in ("source_count", "retained_count"):
        value = downsampling[field]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise InvalidArtifact(f"series.downsampling.{field} must be a non-negative integer")
    if downsampling["retained_count"] > downsampling["source_count"]:
        raise InvalidArtifact("series.downsampling.retained_count cannot exceed source_count")
    if downsampling["retained_count"] != len(series["samples"]):
        raise InvalidArtifact(
            "series.downsampling.retained_count must equal the retained sample count"
        )

    previous = None
    start = _v2_timestamp(review["experiment"]["start"], "experiment.start")
    end = _v2_timestamp(review["experiment"]["end"], "experiment.end")
    for index, sample in enumerate(series["samples"]):
        location = f"series.samples[{index}]"
        current = _v2_timestamp(sample["timestamp"], f"{location}.timestamp")
        if previous is not None and current <= previous:
            raise InvalidArtifact("series.samples timestamps must be strictly increasing")
        if not start <= current <= end:
            raise InvalidArtifact(f"{location}.timestamp must fall within the experiment window")
        previous = current
        channel_values = [
            sample[name] for name in ("measured_power", "raw_reference_power", "expected_power")
        ]
        for channel, value in zip(
            ("measured_power", "raw_reference_power", "expected_power"), channel_values, strict=True
        ):
            if value is not None:
                _finite_number(value, f"{location}.{channel}")
        if sample["valid"] and any(value is None for value in channel_values):
            raise InvalidArtifact(
                f"{location}.valid cannot be true when a power channel is unavailable"
            )
        if not sample["valid"] and all(value is not None for value in channel_values):
            raise InvalidArtifact(
                f"{location}.valid=false must identify at least one unavailable power channel"
            )

    previous_gap_end = None
    for index, marker in enumerate(downsampling["gap_markers"]):
        location = f"series.downsampling.gap_markers[{index}]"
        gap_start = _v2_timestamp(marker["start"], f"{location}.start")
        gap_end = _v2_timestamp(marker["end"], f"{location}.end")
        if gap_start >= gap_end:
            raise InvalidArtifact(f"{location}.start must be before end")
        if previous_gap_end is not None and gap_start < previous_gap_end:
            raise InvalidArtifact(
                "series.downsampling.gap_markers must be ordered and non-overlapping"
            )
        duration = marker["duration_seconds"]
        _finite_number(duration, f"{location}.duration_seconds")
        if not math.isclose(
            (gap_end - gap_start).total_seconds(), duration, rel_tol=0, abs_tol=1e-6
        ):
            raise InvalidArtifact(
                f"{location}.duration_seconds must match its UTC boundary timestamps"
            )
        previous_gap_end = gap_end


def _validate_approval(review: dict[str, Any], schema_path: Path | None) -> None:
    approval_status = review["approval_status"]
    owner_review = review["decision"]["owner_review"]
    candidate_statuses = [item["status"] for item in review["candidate_checks"]]
    if approval_status == "proposed":
        if owner_review is not None:
            raise InvalidArtifact(
                "proposed contract artifacts cannot carry an owner-approval record"
            )
        if "owner_approved" in candidate_statuses:
            raise InvalidArtifact(
                "candidate checks cannot be owner_approved while approval_status is proposed"
            )
        return

    if any(
        checksum["role"] == "synthetic test fixture; not source evidence"
        for checksum in review["provenance"]["source_checksums"]
    ):
        raise InvalidArtifact("synthetic test fixtures can never be owner-approved")
    if not isinstance(owner_review, dict):
        raise InvalidArtifact(
            "owner_approved v0.2 requires a recorded science-owner approval object"
        )
    if not _SHA256.fullmatch(owner_review["schema_sha256"]):
        raise InvalidArtifact(
            "decision.owner_review.schema_sha256 must be a lowercase SHA256 digest"
        )
    if not _SHA256.fullmatch(owner_review["protocol_sha256"]):
        raise InvalidArtifact(
            "decision.owner_review.protocol_sha256 must be a lowercase SHA256 digest"
        )
    if owner_review["protocol_sha256"] != review["provenance"]["protocol_sha256"]:
        raise InvalidArtifact(
            "decision.owner_review protocol hash must match provenance.protocol_sha256"
        )
    if schema_path is not None:
        import hashlib

        expected_schema_sha = hashlib.sha256(schema_path.read_bytes()).hexdigest()
        if owner_review["schema_sha256"] != expected_schema_sha:
            raise InvalidArtifact(
                "decision.owner_review schema hash does not match the validated v0.2 schema"
            )
    for index, candidate in enumerate(review["candidate_checks"]):
        if candidate["status"] == "owner_approved":
            approval = candidate.get("approval")
            if not isinstance(approval, dict):
                raise InvalidArtifact(
                    f"candidate_checks[{index}] owner_approved requires its own approval record"
                )
            if approval["schema_sha256"] != owner_review["schema_sha256"]:
                raise InvalidArtifact(
                    f"candidate_checks[{index}] approval must reference the same v0.2 schema"
                )


def validate_experimental_v2_invariants(
    review: dict[str, Any], schema_path: Path | None = None
) -> None:
    """Check only explicit, mechanical v0.2 semantics; do not infer findings."""
    experiment = review["experiment"]
    experiment_id = experiment["identifier"]
    if not _EXPERIMENT_ID.fullmatch(experiment_id):
        raise InvalidArtifact("experiment.identifier has an invalid format")
    if review["review_id"] != f"review_{experiment_id}":
        raise InvalidArtifact("review_id must equal 'review_' plus experiment.identifier")

    start = _v2_timestamp(experiment["start"], "experiment.start")
    end = _v2_timestamp(experiment["end"], "experiment.end")
    if start >= end:
        raise InvalidArtifact("experiment.start must be earlier than experiment.end")

    _validate_event_context(review)
    _validate_provenance(review, schema_path)
    _validate_metric_values(review)
    _validate_series(review)

    for index, evidence in enumerate(review["electrical_evidence"]):
        location = f"electrical_evidence[{index}]"
        for field in (
            "signal",
            "unit",
            "quality",
            "comparison_population",
            "supports",
            "does_not_prove",
        ):
            _nonempty_string(evidence[field], f"{location}.{field}")
        if evidence["measurement"] is not None:
            _finite_number(evidence["measurement"], f"{location}.measurement")
        expected_units = {"Va": "V", "Ia": "A", "Ig": "A", "Vg": "V", "Fg": "Hz"}
        if evidence["unit"] != expected_units[evidence["signal"]]:
            raise InvalidArtifact(
                f"{location}.unit must be {expected_units[evidence['signal']]} for {evidence['signal']}"
            )
        _string_list(evidence["alternatives"], f"{location}.alternatives")
        _string_list(evidence["missing_measurements"], f"{location}.missing_measurements")
        if evidence["signal"] == "Ig" and "independent" not in evidence["does_not_prove"].lower():
            raise InvalidArtifact(
                "Ig evidence must state that it is not independent confirmation of Pg"
            )

    candidate_ids = set()
    for index, candidate in enumerate(review["candidate_checks"]):
        location = f"candidate_checks[{index}]"
        _nonempty_string(candidate["id"], f"{location}.id")
        if candidate["id"] in candidate_ids:
            raise InvalidArtifact(f"{location}.id must be unique")
        candidate_ids.add(candidate["id"])
        _string_list(candidate["sources"], f"{location}.sources", allow_empty=False)
        for field in (
            "observed_fact",
            "hypothesis",
            "qualification",
            "safety_constraint",
        ):
            _nonempty_string(candidate[field], f"{location}.{field}")
        for field in ("supporting_evidence", "opposing_evidence", "next_information"):
            _string_list(candidate[field], f"{location}.{field}", allow_empty=False)

    decision = review["decision"]
    _nonempty_string(decision["rule_version"], "decision.rule_version")
    _string_list(decision["reasons"], "decision.reasons", allow_empty=False)
    _string_list(review["limitations"], "limitations", allow_empty=False)
    if decision["event_review"] != review["provenance"]["grouping"]["event_review_decision"]:
        raise InvalidArtifact(
            "decision.event_review must match the recorded provenance event review"
        )
    _validate_approval(review, schema_path)
