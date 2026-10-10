"""Bounded exploratory detector diagnostics using committed V2 five-minute results."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from .evaluation_v2 import event_detection


FEATURES = ["reference_power_w", "GTI", "DTI", "TA"]
MODELS = ["reference_ols", "huber", "weather_ols", "weather_ridge_a1"]
ALERT_BUDGET_PER_HOUR = 0.05
RIDGE_ALPHA = 1.0
WINDOW_MINUTES = 5
PERSISTENCE_WINDOWS = 2


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _weather_valid(frame: pd.DataFrame) -> pd.Series:
    valid = frame[["GTI", "DTI", "TA"]].notna().all(axis=1)
    for name in ("weather_coverage", "GTI_coverage", "DTI_coverage", "TA_coverage"):
        valid &= frame[name].ge(0.8)
    return valid


def _eligible(frame: pd.DataFrame, expected: pd.Series, *, weather: bool, domain: list[float]) -> pd.Series:
    valid = frame["quality"] & frame["target_power_w"].ge(0) & frame["reference_power_w"].ge(100)
    valid &= frame["reference_power_w"].between(domain[0], domain[1])
    if weather:
        valid &= _weather_valid(frame)
    valid &= expected.notna() & np.isfinite(expected) & expected.ge(0)
    return valid


def _calculated_models(frame: pd.DataFrame, frozen: dict[str, Any]) -> tuple[dict[str, pd.Series], dict[str, pd.Series], dict[str, Any]]:
    parameters = frozen["model_comparison_pre_protected"]["parameters"]
    domain = frozen["reference_domain_w"]
    actual = frame["target_power_w"].astype(float)
    reference = frame["reference_power_w"].astype(float)
    estimates: dict[str, pd.Series] = {}
    valid: dict[str, pd.Series] = {}
    for key, param_key in (("reference_ols", "calibrated_linear"), ("huber", "huber_reference")):
        model = parameters[param_key]
        prediction = model["intercept_w"] + model["coefficients"]["reference_power_w"] * reference
        estimates[key] = prediction
        valid[key] = _eligible(frame, prediction, weather=False, domain=domain)
    model = parameters["weather_assisted_linear"]
    prediction = pd.Series(model["intercept_w"], index=frame.index, dtype=float)
    for feature, coefficient in model["coefficients"].items():
        prediction += frame[feature].astype(float) * coefficient
    estimates["weather_ols"] = prediction
    valid["weather_ols"] = _eligible(frame, prediction, weather=True, domain=domain)

    train_start, train_end = frozen["boundaries"]["train"]
    train_mask = frame["local_day"].between(train_start, train_end) & frame["healthy"] & frame["quality"] & _weather_valid(frame)
    train = frame.loc[train_mask, FEATURES].astype(float)
    y_train = actual.loc[train_mask]
    if len(train) != int(frozen["populations"]["train"]["weather_bins"]):
        raise ValueError("Weather-model training rows do not reconcile to the frozen V2 population")
    scaler = StandardScaler().fit(train)
    ridge = Ridge(alpha=RIDGE_ALPHA, fit_intercept=True).fit(scaler.transform(train), y_train)
    ridge_prediction = pd.Series(np.nan, index=frame.index, dtype=float)
    all_weather = _weather_valid(frame)
    if all_weather.any():
        ridge_prediction.loc[all_weather] = ridge.predict(scaler.transform(frame.loc[all_weather, FEATURES].astype(float)))
    estimates["weather_ridge_a1"] = ridge_prediction
    valid["weather_ridge_a1"] = _eligible(frame, ridge_prediction, weather=True, domain=domain)
    ridge_info = {
        "features": FEATURES,
        "training_rows": int(len(train)),
        "alpha": RIDGE_ALPHA,
        "standardization": "StandardScaler fit on frozen pre-event weather-eligible training bins only.",
        "intercept_w": float(ridge.intercept_ - np.dot(ridge.coef_, scaler.mean_ / scaler.scale_)),
        "coefficients_on_original_units": {feature: float(coefficient / scale) for feature, coefficient, scale in zip(FEATURES, ridge.coef_, scaler.scale_)},
        "training_mean": {feature: float(value) for feature, value in zip(FEATURES, scaler.mean_)},
        "training_scale": {feature: float(value) for feature, value in zip(FEATURES, scaler.scale_)},
    }
    return estimates, valid, ridge_info


def _score(actual: pd.Series, expected: pd.Series) -> dict[str, float | int]:
    residual = expected - actual
    return {
        "n": int(residual.notna().sum()),
        "mae_w": float(residual.abs().mean()),
        "rmse_w": float(np.sqrt(np.square(residual).mean())),
        "bias_w": float(residual.mean()),
        "median_signed_residual_w": float(residual.median()),
        "p90_signed_residual_w": float(residual.quantile(0.90)),
        "p95_signed_residual_w": float(residual.quantile(0.95)),
        "p97_5_signed_residual_w": float(residual.quantile(0.975)),
        "p99_signed_residual_w": float(residual.quantile(0.99)),
        "positive_residual_fraction": float((residual > 0).mean()),
    }


def _run_detector(frame: pd.DataFrame, expected: pd.Series, eligible: pd.Series, threshold: float) -> pd.DataFrame:
    result = frame[["bin_start", "quality", "healthy", "support_s"]].copy()
    result["expected"] = expected
    result["eligible"] = eligible
    result["residual"] = expected - frame["target_power_w"]
    result["usable"] = result["quality"] & result["eligible"] & result["residual"].notna()
    above = result["usable"] & result["residual"].gt(threshold)
    contiguous = result["bin_start"].diff().dt.total_seconds().eq(WINDOW_MINUTES * 60)
    result["alert"] = above & above.shift(1, fill_value=False) & contiguous
    result["confirmation"] = result["bin_start"] + pd.Timedelta(minutes=WINDOW_MINUTES)
    result["alarm_start"] = result["alert"] & ~(result["alert"].shift(1, fill_value=False) & contiguous)
    result["support_healthy"] = result["healthy"] & result["healthy"].shift(1, fill_value=False) & contiguous
    return result


def _period_table(
    frame: pd.DataFrame, predictions: dict[str, pd.Series], eligibilities: dict[str, pd.Series],
    thresholds: dict[str, float], windows: dict[str, pd.DataFrame], frozen: dict[str, Any],
) -> pd.DataFrame:
    periods = {
        "train": frozen["boundaries"]["train"],
        "selection": frozen["boundaries"]["selection"],
        "calibration": frozen["boundaries"]["calibration"],
        "later_healthy": (frozen["boundaries"]["protected_start"], str(frame.local_day.max())),
    }
    common_weather = _weather_valid(frame)
    rows = []
    for period, (start, end) in periods.items():
        eligible_base = frame["quality"] & frame["healthy"] & frame["local_day"].between(start, end)
        eligible_base &= common_weather
        for model in MODELS:
            mask = eligible_base & eligibilities[model]
            scores = _score(frame.loc[mask, "target_power_w"], predictions[model].loc[mask]) if mask.any() else {"n": 0}
            alarm = windows[model]
            if period == "later_healthy":
                period_mask = alarm["bin_start"].dt.strftime("%Y-%m-%d").between(start, end)
                healthy_window = alarm.loc[period_mask & alarm["usable"] & alarm["healthy"]]
                hours = float(healthy_window["support_s"].sum() / 3600)
                runs = int((alarm.loc[period_mask, "alarm_start"] & alarm.loc[period_mask, "support_healthy"] & alarm.loc[period_mask, "healthy"]).sum())
                false_windows = int((healthy_window["alert"] & healthy_window["support_healthy"]).sum())
                exceedance_fraction = float(healthy_window["residual"].gt(thresholds[model]).mean()) if len(healthy_window) else None
                paired_exceedance_windows = int((alarm.loc[period_mask, "alert"] & alarm.loc[period_mask, "support_healthy"]).sum())
                scores.update({
                    "eligible_healthy_windows": int(len(healthy_window)),
                    "supported_healthy_hours": hours,
                    "healthy_alert_runs": runs,
                    "healthy_alert_runs_per_hour": runs / hours if hours else None,
                    "healthy_alert_window_fraction": false_windows / len(healthy_window) if len(healthy_window) else None,
                    "positive_residual_threshold_exceedance_fraction": exceedance_fraction,
                    "two_window_confirmed_healthy_alert_windows": paired_exceedance_windows,
                    "operational_budget_met_point_estimate": bool(hours > 0 and runs / hours <= ALERT_BUDGET_PER_HOUR),
                })
            else:
                scores["calibration_threshold_w"] = thresholds[model] if period == "calibration" else None
            rows.append({"period": period, "model": model, "threshold_w": thresholds[model], **scores})
    return pd.DataFrame(rows)


def _residual_strata(frame: pd.DataFrame, predictions: dict[str, pd.Series], windows: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    common = frame["quality"] & frame["healthy"] & _weather_valid(frame) & frame["local_day"].ge("2022-02-08")
    base = frame.loc[common].copy()
    base["local_hour"] = base["bin_start"].dt.tz_convert("Indian/Reunion").dt.hour
    # Use stable row-index group labels to keep exact bin membership visible in the CSV outputs.
    monthly_rows = []
    for model in ("reference_ols", "weather_ols", "weather_ridge_a1"):
        eligible = common & windows[model]["usable"]
        for month, idx in frame.loc[eligible].groupby(frame.loc[eligible, "bin_start"].dt.strftime("%Y-%m")).groups.items():
            residual = predictions[model].loc[list(idx)] - frame.loc[list(idx), "target_power_w"]
            day_minutes = windows[model].loc[list(idx)]
            month_hours = float(day_minutes.loc[day_minutes["healthy"] & day_minutes["usable"], "support_s"].sum() / 3600)
            run_count = int((day_minutes["alarm_start"] & day_minutes["support_healthy"] & day_minutes["healthy"]).sum())
            monthly_rows.append({
                "month": month, "model": model, "n": len(residual), "bias_w": float(residual.mean()),
                "mae_w": float(residual.abs().mean()), "p95_signed_residual_w": float(residual.quantile(.95)),
                "p99_signed_residual_w": float(residual.quantile(.99)),
                "positive_residual_fraction": float((residual > 0).mean()),
                "threshold_w": float(windows[model].attrs["threshold_w"]),
                "healthy_alarm_runs": run_count, "supported_healthy_hours": month_hours,
                "healthy_alarm_runs_per_hour": run_count / month_hours if month_hours else None,
            })
    hourly_rows = []
    for model in ("reference_ols", "weather_ols", "weather_ridge_a1"):
        usable = common & windows[model]["usable"]
        temp = frame.loc[usable, ["bin_start", "target_power_w"]].copy()
        temp["local_hour"] = temp["bin_start"].dt.tz_convert("Indian/Reunion").dt.hour
        temp["residual"] = predictions[model].loc[usable] - temp["target_power_w"]
        for hour, group in temp.groupby("local_hour", sort=True):
            hourly_rows.append({"local_hour_RET": int(hour), "model": model, "n": len(group),
                                "bias_w": float(group.residual.mean()), "mae_w": float(group.residual.abs().mean()),
                                "p95_signed_residual_w": float(group.residual.quantile(.95))})
    strata_rows = []
    for feature, label in (("GTI", "irradiance"), ("TA", "ambient_temperature"), ("reference_power_w", "reference_power")):
        base["stratum"] = pd.qcut(base[feature], q=5, duplicates="drop")
        for model in ("reference_ols", "weather_ols", "weather_ridge_a1"):
            eligible = base.index.intersection(windows[model].index[windows[model]["usable"]])
            scoped = base.loc[eligible]
            residual = predictions[model].loc[eligible] - scoped["target_power_w"]
            tmp = scoped[[feature]].copy()
            tmp["residual"] = residual
            for stratum, group in tmp.groupby(pd.qcut(tmp[feature], q=5, duplicates="drop"), observed=True, sort=True):
                strata_rows.append({"stratum_type": label, "stratum": str(stratum), "model": model, "n": len(group),
                                    "bias_w": float(group.residual.mean()), "mae_w": float(group.residual.abs().mean()),
                                    "p95_signed_residual_w": float(group.residual.quantile(.95)),
                                    "positive_residual_fraction": float((group.residual > 0).mean())})
    return pd.DataFrame(monthly_rows), pd.DataFrame(hourly_rows), pd.DataFrame(strata_rows)


def _event_results(shading: dict[str, Any], windows: dict[str, pd.DataFrame]) -> dict[str, Any]:
    results = {}
    for model, frame in windows.items():
        events = []
        for episode in shading["episodes"]:
            episode = {**episode, "start": pd.Timestamp(episode["start"]), "end": pd.Timestamp(episode["end"])}
            outcome = event_detection(episode, frame)
            events.append({"event_id": episode["event_id"], "duration_seconds": episode["duration_seconds"],
                           "detected": outcome["detected"], "confirmation_utc": outcome["confirmation_utc"].isoformat() if outcome["confirmation_utc"] is not None else None,
                           "latency_seconds": outcome["latency_seconds"]})
        detected = [item for item in events if item["detected"]]
        short = [item for item in events if item["duration_seconds"] <= 1800]
        results[model] = {
            "detected_episodes": len(detected), "episode_count": len(events),
            "recall": len(detected) / len(events),
            "median_latency_seconds": float(np.median([item["latency_seconds"] for item in detected])) if detected else None,
            "short_episodes_le_30min": len(short),
            "short_episode_recall": sum(item["detected"] for item in short) / len(short) if short else None,
            "events": events,
        }
    return results


def _feature_diagnostics(frame: pd.DataFrame, frozen: dict[str, Any], ridge_info: dict[str, Any]) -> dict[str, Any]:
    train_start, train_end = frozen["boundaries"]["train"]
    train_mask = frame["local_day"].between(train_start, train_end) & frame["healthy"] & frame["quality"] & _weather_valid(frame)
    train = frame.loc[train_mask, FEATURES].astype(float)
    corr = train.corr()
    standardized = StandardScaler().fit_transform(train)
    corr_weather = train[["GTI", "DTI", "TA"]].corr().to_numpy()
    vif = np.diag(np.linalg.pinv(corr_weather)).tolist()
    full_vif = np.diag(np.linalg.pinv(corr.to_numpy())).tolist()
    train_days = sorted(frame.loc[train_mask, "local_day"].unique())
    split_day = len(train_days) // 2
    matrices = []
    for subset_name, selected_days in (
        ("first_half_training_days", train_days[:split_day]),
        ("second_half_training_days", train_days[split_day:]),
    ):
        row_mask = train_mask & frame["local_day"].isin(selected_days)
        subset = frame.loc[row_mask, FEATURES].astype(float)
        # Fit comparable reference/weather OLS on each chronological half; exploratory sensitivity only.
        target = frame.loc[subset.index, "target_power_w"].astype(float)
        coef = np.linalg.lstsq(np.column_stack([np.ones(len(subset)), subset.to_numpy()]), target.to_numpy(), rcond=None)[0]
        matrices.append({"subset": subset_name, "n": int(len(subset)), "intercept_w": float(coef[0]),
                         "coefficients": {feature: float(value) for feature, value in zip(FEATURES, coef[1:])}})
    return {
        "weather_training_bins": int(len(train)),
        "pearson_correlation_training": {row: {col: float(corr.loc[row, col]) for col in corr.columns} for row in corr.index},
        "weather_feature_vif_training": {feature: float(value) for feature, value in zip(["GTI", "DTI", "TA"], vif)},
        "full_predictor_vif_training": {feature: float(value) for feature, value in zip(FEATURES, full_vif)},
        "standardized_design_condition_number_training": float(np.linalg.cond(standardized)),
        "weather_ols_coefficients_by_training_half": matrices,
        "ridge_model": ridge_info,
        "interpretation": "Correlated predictors and small pre-event calibration span can make weather coefficients sensitive; split-half fits are descriptive and do not estimate a stable causal weather response.",
    }


def analyze(analysis_dir: Path, output_dir: Path) -> dict[str, Any]:
    analysis_dir = analysis_dir.resolve()
    results = analysis_dir / "results"
    frame = pd.read_csv(results / "five_minute_evaluation_v2.csv", parse_dates=["bin_start"])
    for col in ("healthy", "known", "quality", "usable", "eligible"):
        if frame[col].dtype != bool:
            frame[col] = frame[col].astype(str).str.lower().eq("true")
    frame["local_day"] = frame["local_day"].astype(str)
    frame = frame.sort_values("bin_start", kind="stable").reset_index(drop=True)
    shading = _load(results / "shading_evaluation_v2.json")
    comparison = _load(results / "model_comparison_v2.json")
    frozen = _load(results / "frozen_parameters_v2.json")
    predictions, native_eligibilities, ridge_info = _calculated_models(frame, frozen)
    detector_predictions = dict(predictions)
    # The selected V2 model's committed raw-stream aggregate is the exact source for its
    # historic threshold and alerts. Other candidates are recalculated from the committed
    # five-minute measurement fields, on that same strict eligibility support.
    detector_predictions["weather_ols"] = frame["expected_power_w"].astype(float)
    common_detector_eligible = frame["eligible"].copy() & frame["quality"] & _weather_valid(frame)
    for eligible in native_eligibilities.values():
        common_detector_eligible &= eligible
    eligibilities = {model: common_detector_eligible.copy() for model in MODELS}
    common_later = frame["local_day"].ge(frozen["boundaries"]["protected_start"]) & frame["quality"] & frame["healthy"] & _weather_valid(frame)
    thresholds: dict[str, float] = {}
    for model in MODELS:
        cal = frame["local_day"].between(*frozen["boundaries"]["calibration"]) & frame["quality"] & frame["healthy"] & common_detector_eligible
        thresholds[model] = float(max(0.0, (detector_predictions[model].loc[cal] - frame.loc[cal, "target_power_w"]).quantile(.99)))
    windows = {model: _run_detector(frame, detector_predictions[model], eligibilities[model], thresholds[model]) for model in MODELS}
    for model, window in windows.items():
        window.attrs["threshold_w"] = thresholds[model]
    period_df = _period_table(frame, detector_predictions, eligibilities, thresholds, windows, frozen)
    monthly, hourly, strata = _residual_strata(frame, detector_predictions, windows)
    event_metrics = _event_results(shading, windows)

    common = {}
    for model in ("reference_ols", "huber", "weather_ols", "weather_ridge_a1"):
        mask = common_later & predictions[model].notna()
        common[model] = _score(frame.loc[mask, "target_power_w"], predictions[model].loc[mask])
    common_n = int(common_later.sum())
    # These V2 comparisons are an exact check that model formulas and common population were reconstructed correctly.
    expected_common = comparison["common_weather_later_scores"]
    checks = {
        "common_later_population_reconciles": common_n == int(expected_common["weather_assisted_linear"]["n"]),
        "weather_common_mae_reconciles": abs(common["weather_ols"]["mae_w"] - expected_common["weather_assisted_linear"]["mae_w"]) < 1e-7,
        "reference_ols_common_mae_reconciles": abs(common["reference_ols"]["mae_w"] - expected_common["calibrated_linear"]["mae_w"]) < 1e-6,
        "common_calibration_population_reconciles": int((frame["local_day"].between(*frozen["boundaries"]["calibration"]) & frame["healthy"] & common_detector_eligible).sum()) == int(shading["healthy_calibration"]["5"]["evaluated_healthy_windows"]),
    }
    if not all(checks.values()):
        raise ValueError(f"Exploratory reconstruction failed historical common-population checks: {checks}")

    # Mechanism summary: on the exact shared later sample, compare calibration threshold,
    # positive bias/tails and persistence-based alert runs, not MAE alone.
    weather_rate = float(period_df.query("period == 'later_healthy' and model == 'weather_ols'")["healthy_alert_runs_per_hour"].iloc[0])
    ols_rate = float(period_df.query("period == 'later_healthy' and model == 'reference_ols'")["healthy_alert_runs_per_hour"].iloc[0])
    output = {
        "analysis_version": "v3-exploratory",
        "status": "exploratory_only_protected_v2_outcomes_were_inspected",
        "source": {
            "committed_measurements": "analysis/results/five_minute_evaluation_v2.csv",
            "sha256": hashlib.sha256((results / "five_minute_evaluation_v2.csv").read_bytes()).hexdigest(),
            "analysis_code": Path(__file__).resolve().relative_to(analysis_dir.parent).as_posix(),
            "analysis_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "rows": int(len(frame)),
            "raw_dataset_bytes_available_in_current_checkout": False,
            "raw_data_rerun_performed": False,
            "note": "Real committed V2 binned measurements/results were analyzed; new fits and alarms use these records. No claim is made that original 1,990,478-row sources were re-downloaded in this run.",
        },
        "objective_and_selection_rule": {
            "healthy_alarm_run_budget_per_supported_hour": ALERT_BUDGET_PER_HOUR,
            "primary_tradeoff": "Meet point alert budget while retaining grouped episode recall; then compare latency, eligible coverage, short-event recall, residual calibration, and strata stability.",
            "threshold": "Separate 99th percentile of signed known-zero calibration residual means for each 5-minute candidate, two consecutive eligible windows; V2 protected performance has already been inspected, so all outcomes here remain exploratory.",
            "aggregation_note": "These exploratory thresholds are recalibrated on model predictions from committed five-minute bin means. The frozen V2 detector thresholds were calibrated after raw-stream prediction then aggregation and are recorded separately; small differences are expected and are not substituted into historical results.",
            "ridge": "Ridge alpha=1.0 fixed before protected scoring; feature standardization fitted on frozen training rows only; no protected-set hyperparameter selection.",
        },
        "reconstruction_checks": checks,
        "training_feature_diagnostics": _feature_diagnostics(frame, frozen, ridge_info),
        "calibration_thresholds_w": thresholds,
        "frozen_original_thresholds_w": frozen["baseline_thresholds_w"],
        "detector_comparison_note": "The weather OLS detector uses the committed V2 raw-stream aggregate series. Reference OLS, Huber, and Ridge expected powers are reconstructed from committed five-minute input means; each threshold is recalibrated on the exact same source-eligible calibration windows. This common-set rerun is exploratory and does not replace V2 detector results.",
        "common_detector_sample": {
            "calibration_windows": int((frame["local_day"].between(*frozen["boundaries"]["calibration"]) & frame["healthy"] & common_detector_eligible).sum()),
            "later_healthy_windows": int((common_later & common_detector_eligible).sum()),
            "all_candidates_share_identical_eligible_windows": True,
            "eligibility": "Intersection of target/reference support, frozen reference domain, expected-power validity, and weather coverage for all four candidates.",
        },
        "common_later_healthy_sample_count": common_n,
        "common_later_healthy_scores": common,
        "period_scores_and_alerts": _clean_records(period_df),
        "event_detection": event_metrics,
        "mechanism_summary": {
            "weather_vs_reference_ols_common_mae_difference_w": common["weather_ols"]["mae_w"] - common["reference_ols"]["mae_w"],
            "weather_vs_reference_ols_common_bias_difference_w": common["weather_ols"]["bias_w"] - common["reference_ols"]["bias_w"],
            "weather_vs_reference_ols_point_alarm_rate_difference_per_hour": weather_rate - ols_rate,
            "interpretation": "A lower pooled MAE does not constrain positive residual tail shape or temporal clustering. Weather OLS has a lower calibration threshold and a larger positive later-period bias; threshold exceedances persist in runs. This combination explains the observed alert difference descriptively, without proving a unique physical driver.",
        },
        "external_validation": {
            "new_independent_dataset_used": False,
            "recommendation": "Acquire a prospectively frozen site/time holdout with timestamped independently confirmed intervention and clean-operation labels before choosing the detector. PVDAQ candidates require per-system metadata, sensor/label semantics, fault/outage/curtailment review, and licensing/provenance checks; do not pool by name alone.",
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "detector_diagnostics_v3.json").write_text(json.dumps(output, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    period_df.to_csv(output_dir / "period_scores_alerts_v3.csv", index=False)
    monthly.to_csv(output_dir / "monthly_residual_alerts_v3.csv", index=False)
    hourly.to_csv(output_dir / "time_of_day_residuals_v3.csv", index=False)
    strata.to_csv(output_dir / "weather_power_strata_v3.csv", index=False)
    _plot_residuals(frame, detector_predictions, common_later & common_detector_eligible, thresholds, output_dir)
    _plot_monthly(monthly, output_dir)
    _plot_strata(strata, output_dir)
    return output


def _clean_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    records = frame.astype(object).where(pd.notna(frame), None).to_dict(orient="records")

    def clean(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: clean(child) for key, child in value.items()}
        if isinstance(value, list):
            return [clean(child) for child in value]
        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.floating):
            number = float(value)
            return number if np.isfinite(number) else None
        if isinstance(value, np.bool_):
            return bool(value)
        return value

    return clean(records)


def _plot_residuals(frame: pd.DataFrame, predictions: dict[str, pd.Series], common: pd.Series, thresholds: dict[str, float], out: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), constrained_layout=True)
    colors = {"reference_ols": "#267a67", "weather_ols": "#cf6c35", "weather_ridge_a1": "#5269a8"}
    for model, color in colors.items():
        residual = (predictions[model] - frame["target_power_w"]).loc[common & predictions[model].notna()]
        axes[0].hist(residual, bins=70, density=True, histtype="step", linewidth=1.8, color=color, label=model)
        axes[0].axvline(thresholds[model], color=color, linestyle="--", linewidth=1, alpha=.7)
    axes[0].set(title="Later zero-labelled residuals on common weather support", xlabel="Expected − measured AC power (W)", ylabel="Density")
    axes[0].legend(frameon=False, fontsize=8)
    for model, color in (("reference_ols", colors["reference_ols"]), ("weather_ols", colors["weather_ols"])):
        residual = (predictions[model] - frame["target_power_w"]).loc[common]
        residual = residual[np.isfinite(residual)].sort_values().to_numpy()
        q = np.arange(1, len(residual) + 1) / len(residual)
        axes[1].plot(residual, q, color=color, label=model, linewidth=1.8)
        axes[1].axvline(thresholds[model], color=color, linestyle="--", linewidth=1, alpha=.7)
    axes[1].set(xlim=(-100, 150), ylim=(.85, 1), title="Positive tail and separate calibration thresholds", xlabel="Signed residual (W)", ylabel="Empirical cumulative probability")
    axes[1].legend(frameon=False, fontsize=8)
    fig.savefig(out / "residual_tail_v3.png", dpi=160)
    plt.close(fig)


def _plot_monthly(monthly: pd.DataFrame, out: Path) -> None:
    select = monthly[monthly.model.isin(["reference_ols", "weather_ols"])].copy()
    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True, constrained_layout=True)
    for model, label, color in (("reference_ols", "Reference OLS", "#267a67"), ("weather_ols", "Weather OLS", "#cf6c35")):
        part = select[select.model == model]
        axes[0].plot(part.month, part.bias_w, marker="o", label=label, color=color)
        axes[1].plot(part.month, part.healthy_alarm_runs_per_hour, marker="o", label=label, color=color)
    axes[0].axhline(0, color="#777", linewidth=.8)
    axes[1].axhline(ALERT_BUDGET_PER_HOUR, color="#8b3d3d", linestyle="--", linewidth=1, label="Frozen alert budget")
    axes[0].set(ylabel="Mean signed residual (W)", title="Later-period calibration drift by month")
    axes[1].set(ylabel="Healthy alert runs / supported hour", title="Separate per-model thresholds; common weather-eligible population")
    axes[1].tick_params(axis="x", rotation=35)
    axes[0].legend(frameon=False, ncol=2)
    axes[1].legend(frameon=False, ncol=3)
    fig.savefig(out / "monthly_residual_alerts_v3.png", dpi=160)
    plt.close(fig)


def _plot_strata(strata: pd.DataFrame, out: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), constrained_layout=True)
    for ax, (kind, part) in zip(axes, strata.groupby("stratum_type", sort=False)):
        for model, label, color in (("reference_ols", "Reference OLS", "#267a67"), ("weather_ols", "Weather OLS", "#cf6c35")):
            scoped = part[part.model == model]
            ax.plot(range(len(scoped)), scoped.bias_w, marker="o", label=label, color=color)
        ax.axhline(0, color="#777", linewidth=.8)
        ax.set(title=kind.replace("_", " "), xlabel="Ordered fifth", ylabel="Mean expected − measured (W)")
    axes[0].legend(frameon=False, fontsize=8)
    fig.savefig(out / "residual_strata_v3.png", dpi=160)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run bounded exploratory diagnostics on committed V2 measurements.")
    parser.add_argument("--analysis-dir", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[2] / "results" / "detector_diagnostics_v3")
    args = parser.parse_args()
    result = analyze(args.analysis_dir, args.output_dir)
    print(json.dumps({"checks": result["reconstruction_checks"], "output_dir": str(args.output_dir.resolve())}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
