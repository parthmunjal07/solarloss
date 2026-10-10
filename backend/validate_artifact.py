"""Validate a science export against the backend handoff and exercise API/report code."""

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any

LAMBDA_DIR = Path(__file__).resolve().parent / "lambda"
sys.path.insert(0, str(LAMBDA_DIR))

from solarloss_backend.application import ReviewApplication  # noqa: E402
from solarloss_backend.errors import InvalidArtifact  # noqa: E402
from solarloss_backend.schema import (  # noqa: E402
    load_review,
    load_versioned_review,
    validate_review_for_experiment,
)

_FILENAME_ID = re.compile(r"^review_([A-Za-z0-9][A-Za-z0-9._-]{0,99})\.json$")


class _ArtifactStore:
    """In-memory adapter for a caller-supplied artifact; never used by the product API."""

    def __init__(self, experiment_id: str, raw: bytes) -> None:
        self.experiment_id = experiment_id
        self.raw = raw
        self.report_html: str | None = None

    def list_experiment_ids(self) -> list[str]:
        return [self.experiment_id]

    def get_review_bytes(self, experiment_id: str) -> bytes:
        if experiment_id != self.experiment_id:
            raise KeyError(experiment_id)
        return self.raw

    def save_report(self, experiment_id: str, html_body: str) -> str:
        if experiment_id != self.experiment_id:
            raise KeyError(experiment_id)
        self.report_html = html_body
        return "https://local-validation.invalid/report.html"


def artifact_identity_errors(review: dict[str, Any], filename: str) -> list[str]:
    """Report filename, experiment identifier, and review id disagreements."""
    experiment_id = review["experiment"]["identifier"]
    review_id = review["review_id"]
    errors: list[str] = []
    match = _FILENAME_ID.fullmatch(Path(filename).name)
    if not match:
        errors.append(
            f"Filename '{Path(filename).name}' must be review_<experiment_id>.json; "
            "the validator will not rename the artifact."
        )
    else:
        filename_id = match.group(1)
        if filename_id != experiment_id:
            errors.append(
                f"Filename identifies experiment '{filename_id}', but "
                f"experiment.identifier is '{experiment_id}'."
            )
        expected_filename_review_id = f"review_{filename_id}"
        if review_id != expected_filename_review_id:
            errors.append(
                f"Filename requires review_id '{expected_filename_review_id}', "
                f"but the artifact contains '{review_id}'."
            )
    if review_id != f"review_{experiment_id}":
        errors.append(
            f"review_id must be 'review_{experiment_id}' to match "
            f"experiment.identifier '{experiment_id}', but the artifact contains '{review_id}'."
        )
    return errors


def _rendered_source_values(review: dict[str, Any]) -> list[Any]:
    """Values the report contract promises to display from the source artifact."""
    values: list[Any] = [
        review["schema_version"],
        review["analysis_version"],
        review["produced_at"],
        review["review_id"],
        review["experiment"]["identifier"],
        review["experiment"]["type"],
        review["experiment"]["time_window"]["start"],
        review["experiment"]["time_window"]["end"],
        review["decision"]["state"],
        *review["decision"]["reasons"],
        *review["limitations"],
    ]
    experiment = review["experiment"]
    values.extend(
        [
            experiment["experimental_system"]["identifier"],
            experiment["experimental_system"]["description"],
            experiment["reference_system"]["identifier"],
            experiment["reference_system"]["description"],
            experiment["label_provenance"]["label"],
            experiment["label_provenance"]["source"],
            experiment["label_provenance"]["method"],
        ]
    )
    if "reference" in experiment["label_provenance"]:
        values.append(experiment["label_provenance"]["reference"])

    metrics = review["metrics"]
    energy = metrics["energy_deficit"]
    values.extend([energy["value"], energy["unit"], energy["calculation"]])
    for name in ("deficit_fraction", "coverage"):
        ratio = metrics[name]
        values.extend([ratio["value"], ratio["unit"]])
        for quantity_name in ("numerator", "denominator"):
            values.extend(ratio[quantity_name].values())
    calibration = metrics["calibration_error"]
    values.extend(
        [
            calibration["value"],
            calibration["unit"],
            calibration["statistic"],
            calibration["denominator"]["value"],
            calibration["denominator"]["unit"],
        ]
    )
    values.extend([metrics["valid_interval_count"], metrics["total_interval_count"]])
    baseline = review["baseline_comparison"]
    values.extend([baseline["metric"], baseline["unit"], baseline["evaluation_population"]])
    values.append(baseline.get("calculation", "No comparison calculation detail recorded."))
    for key in ("simple_baseline", "calibrated_reference", "reported_difference"):
        item = baseline.get(key)
        if isinstance(item, dict):
            values.extend(item.values())
    uncertainty = review["uncertainty"]
    values.extend([uncertainty["method"], uncertainty["independent_blocks"]["count"]])
    values.append(uncertainty["independent_blocks"]["unit"])
    values.append(uncertainty["exploratory"])
    values.extend(uncertainty["limitations"])
    if uncertainty.get("interval") is not None:
        values.extend(uncertainty["interval"].values())
    else:
        values.append(uncertainty.get("not_estimated_reason", "No interval recorded."))
    for check in review["quality_checks"]:
        values.extend(check[key] for key in ("name", "status", "detail"))
        if "result" in check:
            values.append(check["result"])
    for exclusion in review["exclusions"]:
        values.extend(exclusion.values())
    for group_name in ("robustness", "placebo"):
        group = review[group_name]
        values.append(group["status"])
        for finding in group["findings"]:
            values.extend(value for key, value in finding.items() if key != "synthetic")
    for sample in review["series"]["samples"]:
        values.append(sample["timestamp"])
        for key in (
            "measured_power",
            "raw_reference_power",
            "expected_power",
            "expected_lower_bound",
            "expected_upper_bound",
        ):
            if sample.get(key) is not None:
                values.append(sample[key])
        values.append("valid" if sample["valid"] else "invalid")
    dataset = review["dataset"]
    values.extend([dataset["name"], dataset["version"], dataset["source"]])
    values.append(dataset.get("extraction_date", "Not recorded"))
    for checksum in review["dataset"]["checksums"]:
        values.extend(checksum.values())
    return values


def report_source_mismatches(review: dict[str, Any], report_html: str) -> list[str]:
    missing = []
    for value in _rendered_source_values(review):
        rendered = html.escape(str(value), quote=True)
        if rendered and rendered not in report_html:
            missing.append(str(value))
    return missing


def _api_event(path: str) -> dict[str, Any]:
    return {"rawPath": path, "requestContext": {"http": {"method": "GET"}}}


def validate_artifact(
    path: Path, retrieved_json: Path | None = None, report_html: Path | None = None
) -> list[str]:
    raw = path.read_bytes()
    review = load_review(raw)
    errors = artifact_identity_errors(review, path.name)

    # Exercise the actual API and report implementation locally with only the
    # caller's file. This does not create a fixture artifact or contact AWS.
    experiment_id = review["experiment"]["identifier"]
    try:
        validate_review_for_experiment(review, experiment_id)
        store = _ArtifactStore(experiment_id, raw)
        app = ReviewApplication(store)
        response = app.handle_event(_api_event(f"/api/v1/reviews/{experiment_id}"), "local-check")
        if response["statusCode"] != 200 or json.loads(response["body"]) != review:
            errors.append("In-process GET review did not return the supplied artifact unchanged.")
        listing = app.handle_event(_api_event("/api/v1/experiments"), "local-check")
        listed = json.loads(listing["body"]).get("experiments", [])
        if (
            listing["statusCode"] != 200
            or len(listed) != 1
            or listed[0]["review_id"] != review["review_id"]
        ):
            errors.append(
                "In-process GET experiments did not expose this validated artifact identity."
            )
        report_response = app.handle_event(
            _api_event(f"/api/v1/reviews/{experiment_id}/report"), "local-check"
        )
        if report_response["statusCode"] != 302 or store.report_html is None:
            errors.append("In-process GET report did not generate a report and redirect.")
        elif report_source_mismatches(review, store.report_html):
            errors.append(
                "In-process report omitted one or more source values covered by the report contract."
            )
    except InvalidArtifact as exc:
        errors.append(str(exc))

    if retrieved_json is not None:
        try:
            retrieved = json.loads(retrieved_json.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"Cannot read API review JSON at {retrieved_json}: {exc}")
        else:
            if retrieved != review:
                errors.append(
                    "API review JSON differs from the supplied artifact after JSON parsing."
                )

    if report_html is not None:
        try:
            report = report_html.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"Cannot read downloaded API report at {report_html}: {exc}")
        else:
            missing = report_source_mismatches(review, report)
            if missing:
                examples = ", ".join(repr(value) for value in missing[:5])
                errors.append(f"Downloaded API report omits source values: {examples}")
    return errors


def validate_experimental_v2_artifact(path: Path, report_output: Path | None = None) -> list[str]:
    """Validate and optionally preview proposed v0.2 locally, without exercising the API."""
    raw = path.read_bytes()
    review = load_versioned_review(raw, allow_experimental_v2=True)
    errors = artifact_identity_errors(review, path.name)
    if errors:
        return errors

    from solarloss_backend.report import render_review_report

    report = render_review_report(review, allow_experimental_v2=True)
    if report_output is not None:
        if report_output.resolve() == path.resolve():
            return ["Experimental HTML report output cannot overwrite the source artifact."]
        report_output.write_text(report, encoding="utf-8")
    return []


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a science-produced JSON artifact and exercise the local review API/report "
            "path without AWS or frontend deployment."
        )
    )
    parser.add_argument("artifact", type=Path, help="Path to review_<experiment_id>.json")
    parser.add_argument("--retrieved-json", type=Path, help="Optional API response JSON to compare")
    parser.add_argument(
        "--report-html", type=Path, help="Optional downloaded API report to inspect"
    )
    parser.add_argument(
        "--experimental-v2",
        action="store_true",
        help="Opt into proposed v0.2 local validation and report preview; never calls the API",
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        help="Optional local HTML preview output; only available with --experimental-v2",
    )
    args = parser.parse_args()

    try:
        if args.experimental_v2:
            if args.retrieved_json or args.report_html:
                parser.error(
                    "--experimental-v2 is offline-only and cannot compare production API downloads"
                )
            errors = validate_experimental_v2_artifact(args.artifact, args.report_output)
            if errors:
                for error in errors:
                    print(f"ERROR: {error}", file=sys.stderr)
                return 1
            print(
                f"Valid experimental v0.2 proposal: {args.artifact.name}; local report rendered; "
                "production API and storage were not exercised."
            )
            if args.report_output:
                print(f"Local experimental report saved to {args.report_output}.")
            return 0
        if args.report_output:
            parser.error("--report-output requires --experimental-v2")
        errors = validate_artifact(args.artifact, args.retrieved_json, args.report_html)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, InvalidArtifact) as exc:
        print(f"Artifact validation failed: {exc}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(
        f"Valid: {args.artifact.name}; filename, experiment.identifier, and review_id agree; "
        "structural checks pass; local API and report preserve the source artifact."
    )
    if args.retrieved_json:
        print("API review JSON matches the supplied artifact.")
    if args.report_html:
        print("Downloaded API report contains the source values covered by the report contract.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
