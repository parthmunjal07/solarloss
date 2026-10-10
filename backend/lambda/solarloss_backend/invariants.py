"""Cross-field checks not represented directly by the versioned JSON Schemas.

The v0.1 checks retain their original structural scope. Proposed v0.2 checks
enforce explicit data-shape and availability semantics without selecting
thresholds or validating scientific conclusions.
"""

import math
import re
from datetime import datetime, timedelta
from numbers import Real
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


def validate_experimental_v2_invariants(review: dict[str, Any]) -> None:
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

    provenance = review["provenance"]
    if not _SHA256.fullmatch(provenance["protocol_sha256"]):
        raise InvalidArtifact("provenance.protocol_sha256 must be a lowercase SHA256 digest")
    for field in ("evaluation_population", "label_use", "code_version"):
        _nonempty_string(provenance[field], f"provenance.{field}")
    for field in ("model", "splits", "thresholds", "grouping"):
        if not isinstance(provenance[field], dict) or not provenance[field]:
            raise InvalidArtifact(f"provenance.{field} must contain recorded provenance")
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

    metrics = review["metrics"]
    metric_ids = [metric["id"] for metric in metrics]
    if len(metric_ids) != len(set(metric_ids)):
        raise InvalidArtifact("metrics must have unique metric identifiers")
    for index, metric in enumerate(metrics):
        location = f"metrics[{index}]"
        metric_id = metric["id"]
        if metric["unit"] != _V2_METRIC_UNITS[metric_id]:
            raise InvalidArtifact(f"{location}.unit must be {_V2_METRIC_UNITS[metric_id]}")
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
                    f"{location}.value must be null when availability is unavailable"
                )
            _nonempty_string(metric["reason"], f"{location}.reason")

        if metric_id in _V2_RATIO_METRICS and metric.get("ratio") is None:
            raise InvalidArtifact(f"{location}.ratio is required for {metric_id}")
        ratio = metric.get("ratio")
        if ratio is not None:
            _finite_number(ratio["numerator"], f"{location}.ratio.numerator")
            _finite_number(ratio["denominator"], f"{location}.ratio.denominator")
            if ratio["denominator"] <= 0:
                raise InvalidArtifact(f"{location}.ratio.denominator must be greater than zero")
            _nonempty_string(ratio["numerator_unit"], f"{location}.ratio.numerator_unit")
            _nonempty_string(ratio["denominator_unit"], f"{location}.ratio.denominator_unit")

        coverage = metric["coverage"]
        for field in ("valid_seconds", "observed_labelled_seconds", "wall_span_seconds"):
            value = coverage[field]
            if value is not None:
                _finite_number(value, f"{location}.coverage.{field}")
                if value < 0:
                    raise InvalidArtifact(f"{location}.coverage.{field} cannot be negative")
                if (
                    field != "wall_span_seconds"
                    and coverage["wall_span_seconds"] is not None
                    and value > coverage["wall_span_seconds"]
                ):
                    raise InvalidArtifact(
                        f"{location}.coverage.{field} cannot exceed wall_span_seconds"
                    )

        uncertainty = metric.get("uncertainty")
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
            if uncertainty["kind"] == "not_estimated" and (lower is not None or upper is not None):
                raise InvalidArtifact(
                    f"{location}.uncertainty bounds must be null when kind is not_estimated"
                )
            if uncertainty["kind"] != "not_estimated" and lower is None:
                raise InvalidArtifact(
                    f"{location}.uncertainty bounds are required for an estimated interval"
                )
            if uncertainty["unit"] != metric["unit"]:
                raise InvalidArtifact(f"{location}.uncertainty.unit must match the metric unit")

    series = review["series"]
    downsampling = series["downsampling"]
    for field in ("source_count", "retained_count"):
        value = downsampling.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise InvalidArtifact(f"series.downsampling.{field} must be a non-negative integer")
    if downsampling["retained_count"] > downsampling["source_count"]:
        raise InvalidArtifact("series.downsampling.retained_count cannot exceed source_count")
    if not isinstance(downsampling["gap_markers"], list):
        raise InvalidArtifact("series.downsampling.gap_markers must be a list")

    previous = None
    for index, sample in enumerate(series["samples"]):
        current = _v2_timestamp(sample["timestamp"], f"series.samples[{index}].timestamp")
        if previous is not None and current <= previous:
            raise InvalidArtifact("series.samples timestamps must be strictly increasing")
        previous = current

    for index, evidence in enumerate(review["electrical_evidence"]):
        location = f"electrical_evidence[{index}]"
        for field in ("signal", "unit"):
            _nonempty_string(evidence[field], f"{location}.{field}")
        if isinstance(evidence["measurement"], (int, float)):
            _finite_number(evidence["measurement"], f"{location}.measurement")

    approval_status = review["approval_status"]
    if approval_status != "proposed":
        raise InvalidArtifact(
            "The proposed v0.2 contract has no recorded science-owner approval; "
            "experimental artifacts must keep approval_status='proposed'"
        )
    candidate_ids = set()
    for index, candidate in enumerate(review["candidate_checks"]):
        location = f"candidate_checks[{index}]"
        _nonempty_string(candidate["id"], f"{location}.id")
        if candidate["id"] in candidate_ids:
            raise InvalidArtifact(f"{location}.id must be unique")
        candidate_ids.add(candidate["id"])
        _string_list(candidate["sources"], f"{location}.sources", allow_empty=False)
        if approval_status == "proposed" and candidate["status"] == "owner_approved":
            raise InvalidArtifact(
                f"{location}.status cannot be owner_approved while approval_status is proposed"
            )

    decision = review["decision"]
    _nonempty_string(decision["rule_version"], "decision.rule_version")
    _string_list(decision["reasons"], "decision.reasons", allow_empty=False)
    _string_list(review["limitations"], "limitations", allow_empty=False)
