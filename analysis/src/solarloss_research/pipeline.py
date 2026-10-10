"""End-to-end audit and evaluation entry points shared by the notebook and CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .dataset import (
    FILES,
    audit_csv,
    exact_alignment_report,
    load_electrical,
    load_weather_bins,
    merge_electrical,
    verify_file,
    weather_bin_alignment_report,
)
from .model import evaluate_fault_episodes, fit_and_compare, make_bins, summarize_analysis
from .review import build_review_artifact, write_review_artifact, review_identity


def audit_and_model(
    data_dir: str | Path,
    *,
    include_weather: bool = True,
    chunksize: int = 250_000,
    produced_at: str,
) -> dict[str, Any]:
    """Run the real-byte audit, chronological modelling, and held-out evaluation."""
    root = Path(data_dir)
    target_name = "dt2_electrical_production_inverter_1_with_faults.csv"
    reference_name = "dt3_electrical_production_inverter_2.csv"
    target_path = root / target_name
    reference_path = root / reference_name
    for required in (target_path, reference_path):
        if not required.is_file():
            raise FileNotFoundError(f"Download the verified electrical dataset first: {required}")
    file_checks = [verify_file(target_path, target_name), verify_file(reference_path, reference_name)]
    if not all(check["checksum_matches"] and check["size_matches"] for check in file_checks):
        raise ValueError("Electrical dataset bytes failed Zenodo record size/MD5 verification")
    metadata_path = root / "00_metadata_variable.jpg"
    if metadata_path.is_file():
        metadata_check = verify_file(metadata_path, "00_metadata_variable.jpg")
        if not metadata_check["checksum_matches"] or not metadata_check["size_matches"]:
            raise ValueError("Dataset metadata image failed Zenodo record size/MD5 verification")
        file_checks.append(metadata_check)
    audits = {
        target_name: audit_csv(target_path, chunksize=chunksize, expected_frequency_seconds=5.0),
        reference_name: audit_csv(reference_path, chunksize=chunksize, expected_frequency_seconds=5.0),
    }
    target = load_electrical(target_path, target=True)
    reference = load_electrical(reference_path, target=False)
    alignment = exact_alignment_report(target, reference)
    paired = merge_electrical(target, reference)
    target_intervals = audits[target_name]["interval_seconds"]
    nominal_frequency = target_intervals["median"] or 5.0

    weather_path = root / "dt1_solar_and_meteorological_measurement.csv"
    weather_bins = None
    weather_alignment = {"status": "not_retrieved", "reason": "Weather file not requested or not present."}
    if include_weather and weather_path.is_file():
        weather_check = verify_file(weather_path, "dt1_solar_and_meteorological_measurement.csv")
        file_checks.append(weather_check)
        if not weather_check["checksum_matches"] or not weather_check["size_matches"]:
            raise ValueError("Weather dataset bytes failed Zenodo record size/MD5 verification")
        audits[weather_path.name] = audit_csv(weather_path, chunksize=max(chunksize, 500_000), expected_frequency_seconds=1.0)
        weather_bins = load_weather_bins(weather_path, chunksize=max(chunksize, 500_000))
    bins = make_bins(paired, weather_bins=weather_bins)
    if weather_bins is not None:
        weather_alignment = weather_bin_alignment_report(make_bins(paired), weather_bins)
    model_info = fit_and_compare(bins)
    test_start_day = model_info["split_metadata"]["test_start_day"]
    episodes, exclusions = evaluate_fault_episodes(
        target,
        paired,
        model_info,
        evaluation_start_day=model_info["split_metadata"]["validation_start_day"],
        test_start_day=test_start_day,
        expected_frequency_seconds=float(nominal_frequency),
        weather_bins=weather_bins,
    )
    summary = summarize_analysis(
        bins,
        target,
        paired,
        model_info,
        episodes,
        exclusions,
        expected_frequency_seconds=float(nominal_frequency),
    )
    return {
        "produced_at": produced_at,
        "dataset_file_checks": file_checks,
        "audits": audits,
        "alignment": alignment,
        "weather_alignment": weather_alignment,
        "bins": bins,
        "target": target,
        "reference": reference,
        "paired": paired,
        "weather_bins": weather_bins,
        "model_info": model_info,
        "summary": summary,
    }


def export_results(
    result: dict[str, Any],
    *,
    output_dir: str | Path,
    schema_path: str | Path,
    semantics_approved: bool = False,
) -> dict[str, Path]:
    """Write audit/model JSON and (when estimable) a schema-validated review artifact."""
    import json
    from .dataset import as_json_file

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    summary = result["summary"]
    audit_summary = {
        "produced_at": result["produced_at"],
        "dataset_file_checks": result["dataset_file_checks"],
        "audits": result["audits"],
        "alignment": result["alignment"],
        "weather_alignment": result["weather_alignment"],
        "split_metadata": summary["split_metadata"],
        "sample_audit": summary["sample_audit"],
    }
    model_summary = {
        "analysis_version": summary["analysis_version"],
        "selected_model": summary["selected_model"],
        "model_selection": summary["model_selection"],
        "heldout_healthy": summary["heldout_healthy"],
        "shortfall": summary["shortfall"],
        "heldout_test_shading": summary["heldout_test_shading"],
        "episodes": summary["episodes"],
        "episode_exclusions": summary["episode_exclusions"],
        "reference_stability": summary["reference_stability"],
        "fallback": summary["fallback"],
        "placebo": summary["placebo"],
        "missingness_sensitivity": summary["missingness_sensitivity"],
        "decision": summary["decision"],
    }
    paths = {
        "audit": as_json_file(audit_summary, out / "data_quality_report.json"),
        "model_comparison": as_json_file(model_summary, out / "model_comparison_results.json"),
    }
    if not semantics_approved:
        return paths  # Scientific JSON remains available; no unapproved production review.
    artifact = build_review_artifact(
        audits=result["audits"],
        file_checks=result["dataset_file_checks"],
        alignment=result["alignment"],
        bins=result["bins"],
        model_info=result["model_info"],
        summary=summary,
        produced_at=result["produced_at"],
        semantics_approved=semantics_approved,
    )
    artifact_path = out / review_identity(artifact['experiment']['identifier'])[1]
    paths["review_artifact"] = write_review_artifact(artifact, artifact_path, schema_path)
    return paths
