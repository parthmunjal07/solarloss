"""Structural checks that JSON Schema cannot express without cross-field logic.

These checks enforce ordering, counts, and identity shape only. They do not
interpret measurements, select thresholds, or validate scientific conclusions.
"""

from datetime import datetime
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
