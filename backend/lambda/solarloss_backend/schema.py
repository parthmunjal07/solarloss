import json
import math
import os
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .errors import InvalidArtifact
from .invariants import validate_structural_invariants


def default_schema_path() -> Path:
    configured = os.environ.get("REVIEW_SCHEMA_PATH")
    if configured:
        return Path(configured)

    module_path = Path(__file__).resolve()
    for parent in module_path.parents:
        candidate = parent / "artifacts" / "schema" / "review.schema.json"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("Could not locate artifacts/schema/review.schema.json")


def _reject_non_json_constant(value: str) -> None:
    raise ValueError(f"Invalid JSON numeric constant: {value}")


def _reject_nonfinite_values(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise InvalidArtifact("Review artifact contains a non-finite number")
    if isinstance(value, dict):
        for child in value.values():
            _reject_nonfinite_values(child)
    elif isinstance(value, list):
        for child in value:
            _reject_nonfinite_values(child)


def load_review(raw: bytes, schema_path: Path | None = None) -> dict[str, Any]:
    try:
        review = json.loads(raw.decode("utf-8"), parse_constant=_reject_non_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise InvalidArtifact("Review artifact is not valid UTF-8 JSON") from exc
    _reject_nonfinite_values(review)

    schema_file = schema_path or default_schema_path()
    try:
        schema = json.loads(schema_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Unable to load review schema at {schema_file}") from exc

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(
        validator.iter_errors(review), key=lambda error: ".".join(map(str, error.absolute_path))
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise InvalidArtifact(f"Schema validation failed at {location}: {first.message}")
    if not isinstance(review, dict):
        raise InvalidArtifact("Review artifact must be a JSON object")
    validate_structural_invariants(review)
    return review


def validate_review_for_experiment(review: dict[str, Any], experiment_id: str) -> dict[str, Any]:
    if review["experiment"]["identifier"] != experiment_id:
        raise InvalidArtifact(
            "Artifact experiment.identifier must match the expected experiment id "
            f"'{experiment_id}' (storage key review_{experiment_id}.json); got "
            f"'{review['experiment']['identifier']}'"
        )
    if review["review_id"] != f"review_{experiment_id}":
        raise InvalidArtifact(
            f"Artifact review_id must be 'review_{experiment_id}' to match "
            f"experiment.identifier '{experiment_id}'; got '{review['review_id']}'"
        )
    return review
