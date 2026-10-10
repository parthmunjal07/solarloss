import hashlib
import json
import math
import os
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .errors import InvalidArtifact
from .invariants import validate_experimental_v2_invariants, validate_structural_invariants

V1_SCHEMA_VERSION = "0.1.0"
EXPERIMENTAL_V2_SCHEMA_VERSION = "0.2.0"
_SCHEMA_SHA256 = re.compile(r"^[a-f0-9]{64}$")


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


def default_experimental_v2_schema_path() -> Path:
    module_path = Path(__file__).resolve()
    for parent in module_path.parents:
        candidate = parent / "artifacts" / "schema" / "review.schema.v0.2.0.proposed.json"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("Could not locate artifacts/schema/review.schema.v0.2.0.proposed.json")


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


def _decode_review(raw: bytes) -> dict[str, Any]:
    try:
        review = json.loads(raw.decode("utf-8"), parse_constant=_reject_non_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise InvalidArtifact("Review artifact is not valid UTF-8 JSON") from exc
    _reject_nonfinite_values(review)
    if not isinstance(review, dict):
        raise InvalidArtifact("Review artifact must be a JSON object")
    return review


def _validate_schema(review: dict[str, Any], schema_file: Path) -> None:
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


def load_versioned_review(
    raw: bytes,
    schema_path: Path | None = None,
    *,
    allow_experimental_v2: bool = False,
    approved_v02_schema_sha256: str | None = None,
    experimental_v2_schema_path: Path | None = None,
) -> dict[str, Any]:
    """Validate a known schema version, keeping the proposed v0.2 path opt-in.

    The production API uses the default (v0.1-only) behavior. Experimental v0.2
    validation is intended for local compatibility checks and report previews.
    """
    review = _decode_review(raw)
    version = review.get("schema_version")
    if version == V1_SCHEMA_VERSION:
        _validate_schema(review, schema_path or default_schema_path())
        validate_structural_invariants(review)
        return review

    if version == EXPERIMENTAL_V2_SCHEMA_VERSION:
        schema_file = experimental_v2_schema_path or default_experimental_v2_schema_path()
        decision = review.get("decision")
        owner_review = decision.get("owner_review") if isinstance(decision, dict) else None
        if review.get("approval_status") == "owner_approved" and not isinstance(owner_review, dict):
            raise InvalidArtifact(
                "The v0.2 artifact claims owner approval but has no recorded science-owner approval object"
            )
        candidate_checks = review.get("candidate_checks")
        if (
            review.get("approval_status") == "proposed"
            and isinstance(candidate_checks, list)
            and any(
                isinstance(candidate, dict) and candidate.get("status") == "owner_approved"
                for candidate in candidate_checks
            )
        ):
            raise InvalidArtifact(
                "candidate checks cannot be owner_approved while approval_status is proposed"
            )
        if not allow_experimental_v2:
            if (
                not approved_v02_schema_sha256
                or not _SCHEMA_SHA256.fullmatch(approved_v02_schema_sha256)
                or review.get("approval_status") != "owner_approved"
            ):
                raise InvalidArtifact(
                    "Review schema 0.2.0 is not enabled for production; it requires an owner-approved "
                    "artifact and the exact approved schema SHA256 deployment gate"
                )
            schema_digest = hashlib.sha256(schema_file.read_bytes()).hexdigest()
            if schema_digest != approved_v02_schema_sha256:
                raise InvalidArtifact(
                    "Review schema 0.2.0 does not match the explicitly approved deployment schema SHA256"
                )
        _validate_schema(review, schema_file)
        validate_experimental_v2_invariants(review, schema_file)
        return review

    raise InvalidArtifact(f"Unsupported review schema version: {version!r}")


def load_review(raw: bytes, schema_path: Path | None = None) -> dict[str, Any]:
    """Load a production-compatible v0.1 artifact; v0.2 remains opt-in experimental."""
    return load_versioned_review(raw, schema_path=schema_path)


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
